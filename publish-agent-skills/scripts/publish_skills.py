#!/usr/bin/env python3
"""Publish committed skill directories atomically to one or more target roots."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from typing import Any
import uuid


FRONTMATTER_RE = re.compile(r"\A---\r?\n(?P<body>.*?)\r?\n---(?:\r?\n|\Z)", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*['\"]?([^'\"\s]+)['\"]?\s*$", re.MULTILINE)


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def resolve_commit(source_root: Path, commit: str) -> str:
    result = run(["git", "rev-parse", "--verify", f"{commit}^{{commit}}"], cwd=source_root)
    return result.stdout.decode().strip()


def safe_extract(archive: bytes, destination: Path) -> None:
    archive_path = destination / "archive.tar"
    archive_path.write_bytes(archive)
    with tarfile.open(archive_path) as handle:
        for member in handle.getmembers():
            relative = PurePosixPath(member.name)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe archive path: {member.name}")
            target = destination.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise ValueError(f"unsupported archive member: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = handle.extractfile(member)
            if source is None:
                raise ValueError(f"cannot read archive member: {member.name}")
            target.write_bytes(source.read())
            target.chmod(member.mode & 0o777)
    archive_path.unlink()


def extract_skill(source_root: Path, commit: str, skill: str, destination: Path) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", skill):
        raise ValueError(f"invalid skill name: {skill}")
    archive = run(
        ["git", "archive", "--format=tar", commit, "--", skill], cwd=source_root
    ).stdout
    safe_extract(archive, destination)
    skill_dir = destination / skill
    validate_structure(skill_dir, skill)
    return skill_dir


def validate_structure(skill_dir: Path, expected_name: str) -> None:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError(f"missing SKILL.md: {skill_dir}")
    content = skill_file.read_text(encoding="utf-8")
    frontmatter = FRONTMATTER_RE.match(content)
    if frontmatter is None:
        raise ValueError(f"missing YAML frontmatter for {expected_name}")
    match = NAME_RE.search(frontmatter.group("body"))
    if not match or match.group(1) != expected_name:
        raise ValueError(f"frontmatter name mismatch for {expected_name}")


def run_validator(validator: Path, skill_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(validator), str(skill_dir)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"validator failed for {skill_dir}: {detail}")


def manifest(root: Path) -> dict[str, dict[str, Any]] | None:
    if not root.exists():
        return None
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"target skill must be a real directory: {root}")
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink inside skill is not supported: {path}")
        if not path.is_file():
            continue
        relative = str(path.relative_to(root))
        result[relative] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mode": path.stat().st_mode & 0o777,
        }
    return result


def copy_to_stage(source: Path, target_root: Path, skill: str, token: str) -> Path:
    stage = target_root / f".codex-publish-{skill}-{token}"
    if stage.exists():
        shutil.rmtree(stage)
    try:
        shutil.copytree(source, stage, copy_function=shutil.copy2)
    except Exception:
        remove_path(stage)
        raise
    return stage


def remove_path(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def validate_target_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved == Path(resolved.anchor):
        raise ValueError(f"refusing filesystem root target: {resolved}")
    return resolved


def nearest_existing_directory(path: Path) -> Path | None:
    probe = path
    while not probe.exists():
        if probe.parent == probe:
            return None
        probe = probe.parent
    return probe if probe.is_dir() else probe.parent


def git_target_state(target_root: Path, skill: str) -> dict[str, Any] | None:
    probe = nearest_existing_directory(target_root)
    if probe is None:
        return None
    root_result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=probe,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if root_result.returncode != 0:
        return None
    repo_root = Path(root_result.stdout.strip()).resolve()
    target = target_root / skill
    try:
        relative = target.relative_to(repo_root)
    except ValueError:
        return None
    status_result = subprocess.run(
        [
            "git",
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignored=matching",
            "--",
            str(relative),
        ],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if status_result.returncode != 0:
        detail = status_result.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"cannot inspect target git state: {detail}")
    entries = [entry for entry in status_result.stdout.split(b"\0") if entry]
    return {
        "repo_root": str(repo_root),
        "dirty": bool(entries),
        "entry_count": len(entries),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--skill", action="append", required=True)
    parser.add_argument("--target-root", action="append", required=True, type=Path)
    parser.add_argument("--validator", required=True, type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = args.source_root.expanduser().resolve()
    commit = resolve_commit(source_root, args.commit)
    skills = list(dict.fromkeys(args.skill))
    if len(args.target_root) != 1:
        raise ValueError("exactly one --target-root is required per invocation")
    targets = [validate_target_root(args.target_root[0])]
    validator = args.validator.expanduser().resolve()
    if not validator.is_file():
        raise ValueError(f"validator does not exist: {validator}")

    with tempfile.TemporaryDirectory(prefix="publish-agent-skills-") as temp_name:
        temp_root = Path(temp_name)
        source_dirs: dict[str, Path] = {}
        source_manifests: dict[str, dict[str, dict[str, Any]]] = {}
        for skill in skills:
            skill_dir = extract_skill(source_root, commit, skill, temp_root)
            run_validator(validator, skill_dir)
            source_dirs[skill] = skill_dir
            source_manifest = manifest(skill_dir)
            if source_manifest is None:
                raise ValueError(f"empty extracted skill: {skill}")
            source_manifests[skill] = source_manifest

        plan = []
        for target_root in targets:
            for skill in skills:
                existing = manifest(target_root / skill)
                git_state = git_target_state(target_root, skill)
                if args.apply and git_state is not None and git_state["dirty"]:
                    raise RuntimeError(
                        f"refusing dirty git target: {target_root / skill} "
                        f"({git_state['entry_count']} status entries)"
                    )
                status = "missing" if existing is None else (
                    "identical" if existing == source_manifests[skill] else "different"
                )
                plan.append(
                    {
                        "target_root": str(target_root),
                        "skill": skill,
                        "before": status,
                        "git_state": git_state,
                    }
                )

        backups: list[tuple[Path, Path | None]] = []
        stages: list[Path] = []
        cleanup_warnings: list[str] = []
        token = uuid.uuid4().hex[:12]
        try:
            if args.apply:
                for target_root in targets:
                    target_root.mkdir(parents=True, exist_ok=True)
                for target_root in targets:
                    for skill in skills:
                        target = target_root / skill
                        stage = copy_to_stage(source_dirs[skill], target_root, skill, token)
                        stages.append(stage)
                        backup = target_root / f".codex-backup-{skill}-{token}"
                        if backup.exists():
                            remove_path(backup)
                        previous: Path | None = None
                        if target.exists() or target.is_symlink():
                            if target.is_symlink():
                                raise ValueError(f"refusing symlink target: {target}")
                            os.replace(target, backup)
                            previous = backup
                        backups.append((target, previous))
                        os.replace(stage, target)
                        if manifest(target) != source_manifests[skill]:
                            raise RuntimeError(f"manifest mismatch after publish: {target}")
        except Exception as publish_error:
            rollback_errors: list[str] = []
            for target, backup in reversed(backups):
                try:
                    remove_path(target)
                    if backup is not None and backup.exists():
                        os.replace(backup, target)
                except Exception as rollback_error:
                    rollback_errors.append(f"{target}: {rollback_error}")
            if rollback_errors:
                detail = "; ".join(rollback_errors)
                raise RuntimeError(
                    f"publish failed ({publish_error}); rollback incomplete: {detail}"
                ) from publish_error
            raise
        else:
            if args.apply:
                for _, backup in backups:
                    if backup is None:
                        continue
                    try:
                        remove_path(backup)
                    except Exception as cleanup_error:
                        cleanup_warnings.append(f"{backup}: {cleanup_error}")
        finally:
            for stage in stages:
                try:
                    remove_path(stage)
                except Exception as cleanup_error:
                    cleanup_warnings.append(f"{stage}: {cleanup_error}")

        for item in plan:
            target = Path(item["target_root"]) / item["skill"]
            current = manifest(target)
            item["after"] = "identical" if current == source_manifests[item["skill"]] else (
                "missing" if current is None else "different"
            )

    output = {
        "source_root": str(source_root),
        "source_commit": commit,
        "applied": args.apply,
        "cleanup_warnings": cleanup_warnings,
        "skills": skills,
        "targets": plan,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
