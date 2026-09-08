#!/usr/bin/env python3
"""Inspect scoped Git worktrees; apply only selected, revalidated cleanup decisions."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid


class Unsafe(RuntimeError):
    pass


def run(argv, cwd=None, codes=(0,), input_data=None):
    result = subprocess.run(argv, cwd=cwd, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, capture_output=True, timeout=120, input=input_data)
    if result.returncode not in codes:
        raise Unsafe(f"{argv[0]} failed (exit {result.returncode}); result is unknown")
    return result


def git(repo, *args, codes=(0,), input_data=None):
    return run(["git", "-C", str(repo), *args], codes=codes, input_data=input_data)


def sha(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, sort_keys=True, ensure_ascii=True).encode()
    return hashlib.sha256(value).hexdigest()


def inside(path, root):
    return path == root or root in path.parents


def common(repo):
    value = Path(os.fsdecode(git(repo, "rev-parse", "--git-common-dir").stdout).strip())
    return str((Path(repo) / value).resolve())


def worktrees(repo):
    result = []
    for block in git(repo, "worktree", "list", "--porcelain", "-z").stdout.split(b"\0\0"):
        fields = {}
        for field in block.split(b"\0"):
            if field:
                key, _, value = os.fsdecode(field).partition(" ")
                fields[key] = value
        if "worktree" in fields:
            result.append(fields)
    return result


def discover(repos, roots):
    candidates = set()
    for repo in repos:
        candidates.update(row["worktree"] for row in worktrees(repo))
    for root in roots:
        if not Path(root).is_dir():
            raise Unsafe("scan root missing")
        for directory, dirs, files in os.walk(root, followlinks=False):
            if ".git" in files or ".git" in dirs:
                candidates.add(directory)
                dirs[:] = []
    rows = []
    for path in sorted(candidates):
        try:
            rows.append({"path": str(Path(path).resolve()), "git_common_dir": common(path), "primary": worktrees(path)[0]["worktree"]})
        except (Unsafe, OSError) as error:
            rows.append({"path": path, "error": str(error)})
    return rows


def policy_from(path):
    policy = json.loads(Path(path).read_text())
    if policy.get("version") != 1 or not policy.get("repos") or not policy.get("allowed_roots"):
        raise Unsafe("policy requires version, repos, and allowed_roots")
    for root in policy["allowed_roots"]:
        if not Path(root).is_absolute() or Path(root) == Path("/"):
            raise Unsafe("allowed roots must be specific absolute paths")
    for field in ("metadata_paths", "activity_ignore_components", "disposable_ignored_components"):
        for name in policy.get(field, []):
            if not name or Path(name).is_absolute() or ".." in Path(name).parts or any(c in name for c in "*?["):
                raise Unsafe("path exceptions must be literal relative paths")
    if policy.get("min_age_seconds", 3600) < 0:
        raise Unsafe("invalid inactivity threshold")
    for repo in policy["repos"]:
        if not Path(repo["path"]).is_absolute() or not repo.get("base_ref") or not repo.get("rules_checked"):
            raise Unsafe("each repo requires an absolute path, explicit base_ref, and checked repo rules")
    return policy


def activity_from(path):
    activity = json.loads(Path(path).read_text())
    age = time.time() - activity["checked_at"]
    if not activity.get("complete") or not activity.get("source") or not 0 <= age <= 300:
        raise Unsafe("active-task inventory is incomplete or older than five minutes")
    return activity


def is_metadata(path, policy):
    return any(path == item or path.startswith(item.rstrip("/") + "/") for item in policy.get("metadata_paths", []))


def disposable_generated(item, policy):
    return item["kind"] == "ignored" and any(part in policy.get("disposable_ignored_components", []) for part in Path(item["path"]).parts)


def changes(path):
    records = git(path, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored").stdout.split(b"\0")
    result = []
    i = 0
    while i < len(records):
        record = records[i]
        i += 1
        if not record:
            continue
        code, name = os.fsdecode(record[:2]), os.fsdecode(record[3:])
        result.append({"status": code, "path": name.rstrip("/"), "kind": "ignored" if code == "!!" else "untracked" if code == "??" else "tracked"})
        if "R" in code or "C" in code:
            if i >= len(records) or not records[i]:
                raise Unsafe("incomplete rename status")
            result.append({"status": code, "path": os.fsdecode(records[i]), "kind": "tracked"})
            i += 1
    # status/diff deliberately ignore these index flags; compare actual bytes as well.
    flagged = []
    for record in git(path, "ls-files", "-v", "-z").stdout.split(b"\0"):
        if record and (chr(record[0]).islower() or record[:1] == b"S"):
            flagged.append((os.fsdecode(record[2:]), chr(record[0])))
    omitted = set()
    skipped_missing = [name for name, tag in flagged if tag.upper() == "S" and not os.path.lexists(Path(path) / name)]
    if skipped_missing and git(path, "config", "--bool", "core.sparseCheckout", codes=(0, 1)).stdout.strip() == b"true":
        included = git(path, "sparse-checkout", "check-rules", "-z", input_data=b"\0".join(os.fsencode(name) for name in skipped_missing) + b"\0").stdout
        omitted = set(skipped_missing) - {os.fsdecode(name) for name in included.split(b"\0") if name}
    known = {item["path"] for item in result}
    for name, _ in flagged:
        if name in known or name in omitted:
            continue
        entries = [entry for entry in git(path, "ls-files", "--stage", "-z", "--", name).stdout.split(b"\0") if entry]
        if len(entries) != 1:
            raise Unsafe("flagged index entry is unmerged or ambiguous")
        meta, _ = entries[0].split(b"\t", 1)
        mode, blob, stage = meta.decode().split()
        if stage != "0":
            raise Unsafe("flagged index entry is unmerged")
        actual = Path(path) / name
        expected = git(path, "cat-file", "blob", blob).stdout
        if mode == "120000":
            matches = actual.is_symlink() and os.fsencode(os.readlink(actual)) == expected
        elif mode in ("100644", "100755"):
            matches = actual.is_file() and not actual.is_symlink() and actual.read_bytes() == expected and bool(actual.stat().st_mode & 0o111) == (mode == "100755")
        else:
            raise Unsafe("flagged index entry has an unsupported mode")
        if not matches:
            result.append({"status": "!F", "path": name, "kind": "tracked"})
    return result


def file_state(path):
    if path.is_symlink():
        return ["symlink", os.readlink(path)]
    if path.is_file():
        return ["file", path.stat().st_mode & 0o777, sha(path.read_bytes())]
    if path.is_dir():
        return ["directory", [(item.name, file_state(item)) for item in sorted(path.iterdir())]]
    if not path.exists():
        return ["missing"]
    raise Unsafe("unsupported filesystem object")


def latest_activity(path, policy):
    latest = int(git(path, "log", "-1", "--format=%ct").stdout)
    ignored = set(policy.get("activity_ignore_components", [])) | {".git"}
    for directory, dirs, files in os.walk(path, followlinks=False):
        dirs[:] = [name for name in dirs if name not in ignored]
        for name in files:
            if name not in ignored:
                latest = max(latest, (Path(directory) / name).lstat().st_mtime)
    return latest


def ancestor(repo, head, base):
    return git(repo, "merge-base", "--is-ancestor", head, base, codes=(0, 1)).returncode == 0


def integration(repo, head, base, branch, github_repo):
    if ancestor(repo, head, base):
        return {"kind": "ancestor"}
    fork = git(repo, "merge-base", head, base).stdout.decode().strip()
    paths = [os.fsdecode(p) for p in git(repo, "diff", "--no-renames", "--name-only", "-z", fork, head).stdout.split(b"\0") if p]
    if paths and git(repo, "diff", "--quiet", head, base, "--", *paths, codes=(0, 1)).returncode == 0:
        return {"kind": "exact", "paths": paths}
    if branch and github_repo:
        prs = json.loads(run(["gh", "pr", "list", "--repo", github_repo, "--state", "merged", "--head", branch.removeprefix("refs/heads/"), "--limit", "100", "--json", "number,url,headRefOid,mergeCommit"]).stdout)
        if len(prs) >= 100:
            raise Unsafe("PR result may be truncated; resolve the exact PR")
        for pr in prs:
            merge = (pr.get("mergeCommit") or {}).get("oid")
            if pr.get("headRefOid") == head and merge and ancestor(repo, merge, base):
                return {"kind": "merged_pr", "url": pr["url"], "head": head, "merge": merge}
    return {"kind": "unproven", "paths": paths}


def protected(branch, paths, policy):
    text = "/".join([branch, *paths])
    return any(re.search(r"(?:^|[/_.-])" + re.escape(token) + r"(?:$|[/_.-])", text, re.I) for token in policy.get("protected_tokens", []))


def snapshot(repo, record, policy, activity, reviews):
    path = Path(record["worktree"])
    root = Path(repo["path"]).resolve()
    real = path.resolve()
    base = git(root, "rev-parse", "--verify", repo["base_ref"] + "^{commit}").stdout.decode().strip()
    gitdir = common(root)
    if common(path) != gitdir or not any(inside(real, Path(p).resolve()) for p in policy["allowed_roots"]):
        raise Unsafe("candidate repository or allowed root mismatch")
    if path.absolute() != real or path.is_symlink() or not (path / ".git").is_file():
        raise Unsafe("candidate must be a registered linked worktree without path aliases")
    head = git(path, "rev-parse", "HEAD").stdout.decode().strip()
    branch = git(path, "symbolic-ref", "--quiet", "HEAD", codes=(0, 1)).stdout.decode().strip()
    dirty = changes(path)
    state = {
        "repo": str(root), "path": str(path), "realpath": str(real), "git_common_dir": gitdir,
        "head": head, "base_ref": repo["base_ref"], "base": base, "branch": branch,
        "directory_identity": [path.stat().st_dev, path.stat().st_ino],
        "common_identity": [Path(gitdir).stat().st_dev, Path(gitdir).stat().st_ino],
        "registration": (path / ".git").read_text(),
        "status": dirty, "files": {item["path"]: ["disposable_generated"] if disposable_generated(item, policy) else file_state(path / item["path"]) for item in dirty},
        "index_diff": sha(git(path, "diff", "--cached", "--binary", "HEAD").stdout),
        "worktree_diff": sha(git(path, "diff", "--binary").stdout),
        "latest_activity": latest_activity(path, policy),
    }
    fingerprint = sha(state)
    candidate = {**state, "id": sha([gitdir, str(real)])[:24], "fingerprint": fingerprint}
    active = [Path(p).resolve() for p in activity.get("active_paths", [])] + [Path.cwd().resolve()]
    if real == root or "locked" in record or "prunable" in record or any(inside(p, real) or inside(real, p) for p in active):
        return {**candidate, "decision": "active", "evidence": {"kind": "active_or_locked"}}
    if time.time() - state["latest_activity"] < policy.get("min_age_seconds", 3600):
        return {**candidate, "decision": "recent", "evidence": {"kind": "recent"}}
    proof = integration(root, head, base, branch, repo.get("github_repo"))
    significant = [item for item in dirty if not disposable_generated(item, policy)]
    classification = "clean" if not significant else "metadata_only" if all(is_metadata(item["path"], policy) for item in significant) else "real_diff"
    ready = proof["kind"] != "unproven" and classification == "clean"
    if classification == "metadata_only" and proof["kind"] in ("ancestor", "merged_pr"):
        ready = True
    review = reviews.get(candidate["id"])
    if review and review.get("fingerprint") == fingerprint and review.get("base") == base:
        required_paths = {item["path"] for item in significant}
        if proof["kind"] == "unproven":
            required_paths.update(proof.get("paths", []))
        covered = all(any(name == p or name.startswith(p.rstrip("/") + "/") for p in review.get("source_paths", [])) for name in required_paths)
        if covered and review.get("index_and_untracked_reviewed") is True and review.get("kind") in ("exact_integrated", "superseded") and all(review.get(k) for k in ("purpose", "source_paths", "base_paths", "observations")):
            ready = True
            proof = {"kind": review["kind"], "review": review}
    decision = "eligible" if ready else "protected" if protected(branch, [i["path"] for i in dirty] + proof.get("paths", []), policy) else "review_required"
    return {**candidate, "classification": classification, "decision": decision, "evidence": proof}


def inspect(policy, activity, reviews=None):
    output = {"version": 1, "run_id": str(uuid.uuid4()), "checked_at": time.time(), "policy_hash": sha(policy), "candidates": [], "errors": []}
    seen = set()
    for repo in policy["repos"]:
        try:
            records = worktrees(repo["path"])
            primary = Path(records[0]["worktree"]).resolve()
            for record in records:
                real = Path(record["worktree"]).resolve()
                if real == primary or str(real) in seen:
                    continue
                seen.add(str(real))
                try:
                    output["candidates"].append(snapshot(repo, record, policy, activity, reviews or {}))
                except (Unsafe, OSError, ValueError, subprocess.TimeoutExpired) as error:
                    output["errors"].append({"repo": repo["path"], "path": record["worktree"], "error": str(error)})
        except (Unsafe, OSError, ValueError, subprocess.TimeoutExpired) as error:
            output["errors"].append({"repo": repo["path"], "error": str(error)})
    return output


@contextmanager
def repo_lock(gitdir):
    with (Path(gitdir) / "codex-worktree-cleanup.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Unsafe("another cleanup owns this repository lock")
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def journal_event(path, run_id, candidate, phase, **values):
    event = {"run_id": run_id, "candidate": candidate["id"], "path": candidate["path"], "phase": phase, "time": time.time(), **values}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def journal_read(path):
    if not path.exists():
        return []
    try:
        return [json.loads(line) for line in path.read_text().splitlines()]
    except (ValueError, OSError):
        raise Unsafe("journal is unreadable or incomplete; preserve it and reconcile manually")


def apply(manifest, policy_path, activity_path, reviews, selected, journal, allow_delete=False, resume=False):
    if not allow_delete or not selected:
        raise Unsafe("apply requires --allow-delete and explicit candidate IDs within existing authorization")
    policy = policy_from(policy_path)
    if sha(policy) != manifest["policy_hash"]:
        raise Unsafe("cleanup policy changed; inspect again")
    candidates = {item["id"]: item for item in manifest["candidates"]}
    if not set(selected) <= candidates.keys():
        raise Unsafe("candidate was not inspected")
    control_paths = (journal, policy_path, activity_path)
    journal = Path(journal).resolve()
    for item in manifest["candidates"]:
        if any(inside(form, Path(item["realpath"])) for value in control_paths for form in (Path(value).absolute(), Path(value).resolve())):
            raise Unsafe("journal and control files must be outside every candidate")
    journal.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    history = [row for row in journal_read(journal) if row["run_id"] == manifest["run_id"]]
    if history and not resume:
        raise Unsafe("this run has journal entries; use --resume to reconcile")
    outcomes = []
    for candidate_id in dict.fromkeys(selected):
        item = candidates[candidate_id]
        try:
            if item["decision"] != "eligible":
                raise Unsafe("candidate is not eligible")
            with repo_lock(item["git_common_dir"]):
                current_policy = policy_from(policy_path)
                if sha(current_policy) != manifest["policy_hash"]:
                    raise Unsafe("authorization policy changed during apply")
                activity = activity_from(activity_path)
                if common(item["repo"]) != item["git_common_dir"]:
                    raise Unsafe("repository identity changed")
                records = worktrees(item["repo"])
                matches = [r for r in records if str(Path(r["worktree"]).resolve()) == item["realpath"]]
                prior = [row for row in history if row["candidate"] == candidate_id]
                if not matches and not os.path.lexists(item["path"]):
                    if not prior:
                        raise Unsafe("candidate disappeared without a recorded operation")
                    phase = "already_verified" if any(r["phase"] == "removed" for r in prior) else "absent_operation_unknown"
                    journal_event(journal, manifest["run_id"], item, phase)
                    outcomes.append({"id": candidate_id, "status": phase})
                    continue
                if len(matches) != 1 or Path(matches[0]["worktree"]).resolve() == Path(records[0]["worktree"]).resolve():
                    raise Unsafe("worktree registration changed")
                repo = next(r for r in current_policy["repos"] if str(Path(r["path"]).resolve()) == item["repo"])
                fresh = snapshot(repo, matches[0], current_policy, activity, reviews)
                if fresh["fingerprint"] != item["fingerprint"] or fresh["decision"] != "eligible":
                    raise Unsafe("candidate, base, activity, or evidence changed; inspect again")
                size_kib = int(run(["du", "-sk", item["path"]]).stdout.split()[0])
                free_before = os.statvfs(item["repo"]).f_bavail * os.statvfs(item["repo"]).f_frsize
                journal_event(journal, manifest["run_id"], item, "started", fingerprint=item["fingerprint"], classification=item["classification"], evidence=item["evidence"], status=item["status"], du_kib=size_kib, free_before=free_before)
                # Refresh after potentially long du/fsync, immediately before the destructive command.
                current_policy = policy_from(policy_path)
                if sha(current_policy) != manifest["policy_hash"]:
                    raise Unsafe("authorization policy changed after operation preparation")
                fresh = snapshot(repo, matches[0], current_policy, activity_from(activity_path), reviews)
                if fresh["fingerprint"] != item["fingerprint"] or fresh["decision"] != "eligible":
                    raise Unsafe("candidate changed after operation preparation")
                args = ["worktree", "remove"]
                if item["classification"] != "clean":
                    args.append("--force")
                result = git(item["repo"], *args, "--", item["path"], codes=(0, 1, 128))
                journal_event(journal, manifest["run_id"], item, "command_returned", exit_code=result.returncode)
                absent = not os.path.lexists(item["path"]) and not any(str(Path(r["worktree"]).resolve()) == item["realpath"] for r in worktrees(item["repo"]))
                if result.returncode != 0 or not absent:
                    raise Unsafe("remove or readback failed; preserve result and reconcile")
                free_after = os.statvfs(item["repo"]).f_bavail * os.statvfs(item["repo"]).f_frsize
                journal_event(journal, manifest["run_id"], item, "removed", du_kib=size_kib, df_bytes=free_after - free_before)
                outcomes.append({"id": candidate_id, "status": "removed", "du_kib": size_kib, "df_bytes": free_after - free_before})
        except (Unsafe, OSError, ValueError, StopIteration, subprocess.TimeoutExpired) as error:
            outcomes.append({"id": candidate_id, "status": "retained_or_unknown", "reason": str(error)})
    return {"run_id": manifest["run_id"], "outcomes": outcomes, "removed_count": sum(row["status"] == "removed" for row in outcomes), "du_kib": sum(row.get("du_kib", 0) for row in outcomes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    discovery = commands.add_parser("discover")
    discovery.add_argument("--repo", action="append", default=[])
    discovery.add_argument("--root", action="append", default=[])
    for name in ("inspect", "apply"):
        command = commands.add_parser(name)
        command.add_argument("--policy", required=True)
        command.add_argument("--activity", required=True)
        command.add_argument("--reviews")
        command.add_argument("--output", required=True)
        if name == "apply":
            command.add_argument("--manifest", required=True)
            command.add_argument("--candidate", action="append", required=True)
            command.add_argument("--journal", required=True)
            command.add_argument("--allow-delete", action="store_true")
            command.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "discover":
            print(json.dumps(discover(args.repo, args.root), ensure_ascii=True, indent=2))
            return
        reviews = json.loads(Path(args.reviews).read_text()) if args.reviews else {}
        output = Path(args.output).absolute()
        output_real = output.resolve()
        if args.command == "apply":
            manifest = json.loads(Path(args.manifest).read_text())
            if output.resolve() == Path(args.journal).resolve():
                raise Unsafe("result and journal must use different paths")
            for item in manifest["candidates"]:
                for value in (args.manifest, args.output, args.reviews):
                    if value and any(inside(form, Path(item["realpath"])) for form in (Path(value).absolute(), Path(value).resolve())):
                        raise Unsafe("manifest, review and result files must be outside every candidate")
        output.parent.mkdir(parents=True, exist_ok=True)
        # Reserve a new report before apply; never follow or overwrite an existing output.
        with output.open("x", encoding="utf-8") as handle:
            if args.command == "inspect":
                result = inspect(policy_from(args.policy), activity_from(args.activity), reviews)
            else:
                result = apply(manifest, args.policy, args.activity, reviews, args.candidate, args.journal, args.allow_delete, args.resume)
            handle.write(json.dumps(result, ensure_ascii=True, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if json.loads(output_real.read_text()) != result:
            raise Unsafe("result file readback failed")
        unresolved = len(result.get("errors", [])) + sum(row["status"] in ("retained_or_unknown", "absent_operation_unknown") for row in result.get("outcomes", []))
        print(json.dumps({"output": str(output_real), "run_id": result["run_id"], "errors": unresolved, "removed_count": result.get("removed_count")}))
        if unresolved:
            raise SystemExit(2)
    except (Unsafe, OSError, ValueError, subprocess.TimeoutExpired) as error:
        parser.exit(1, "Cleanup did not complete: " + str(error) + "\n")


if __name__ == "__main__":
    main()
