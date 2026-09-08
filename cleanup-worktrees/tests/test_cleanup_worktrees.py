import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("cleanup", Path(__file__).parents[1] / "scripts/cleanup_worktrees.py")
cleanup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleanup)


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "code").write_text("baseline\n")
        (self.repo / ".gitignore").write_text("ignored/\nnode_modules/\n")
        self.git("add", ".")
        self.git("commit", "-m", "base")
        self.work = self.root / "work"
        self.git("worktree", "add", "-b", "feature", str(self.work))
        self.policy = {"version": 1, "repos": [{"path": str(self.repo), "base_ref": "main", "rules_checked": True}], "allowed_roots": [str(self.root)], "metadata_paths": [".serena", ".agent-browser"], "activity_ignore_components": ["node_modules"], "disposable_ignored_components": ["node_modules"], "protected_tokens": ["rc", "config"], "min_age_seconds": 0}
        self.policy_path = self.root / "policy.json"
        self.activity_path = self.root / "activity.json"
        self.journal = self.root / "reports/run.jsonl"
        self.save_policy()
        self.activity = {"complete": True, "source": "isolated fixture", "checked_at": time.time(), "active_paths": []}
        self.save_activity()

    def git(self, *args, repo=None, check=True):
        return subprocess.run(["git", "-C", str(repo or self.repo), *args], check=check, capture_output=True, text=True)

    def save_policy(self):
        self.policy_path.write_text(json.dumps(self.policy))

    def save_activity(self):
        self.activity["checked_at"] = time.time()
        self.activity_path.write_text(json.dumps(self.activity))

    def inspect(self, reviews=None):
        return cleanup.inspect(self.policy, self.activity, reviews)

    def candidate(self, manifest=None):
        manifest = manifest or self.inspect()
        self.assertEqual(manifest["errors"], [])
        self.assertEqual(len(manifest["candidates"]), 1)
        return manifest["candidates"][0]

    def apply(self, manifest, reviews=None, **kwargs):
        return cleanup.apply(manifest, self.policy_path, self.activity_path, reviews or {}, [self.candidate(manifest)["id"]], self.journal, allow_delete=True, **kwargs)

    def test_clean_ancestor_remove_and_idempotent_resume(self):
        manifest = self.inspect()
        self.assertEqual(self.candidate(manifest)["evidence"]["kind"], "ancestor")
        result = self.apply(manifest)
        self.assertEqual(result["removed_count"], 1)
        self.assertFalse(self.work.exists())
        self.assertEqual(len(cleanup.worktrees(self.repo)), 1)
        self.assertEqual(self.apply(manifest, resume=True)["outcomes"][0]["status"], "already_verified")
        self.assertEqual(self.apply(manifest, resume=True)["removed_count"], 0)
        self.assertEqual(self.git("branch", "--list", "feature").stdout.strip(), "feature")

    def test_squash_exact_then_post_merge_change_is_not_integrated(self):
        for value in ["one\n", "two\n"]:
            (self.work / "code").write_text(value)
            self.git("add", "code", repo=self.work)
            self.git("commit", "-m", value.strip(), repo=self.work)
        self.git("merge", "--squash", "feature")
        self.git("commit", "-m", "squashed")
        self.assertEqual(self.candidate()["evidence"]["kind"], "exact")
        (self.work / "later").write_text("not integrated\n")
        self.git("add", "later", repo=self.work)
        self.git("commit", "-m", "after PR", repo=self.work)
        self.assertEqual(self.candidate()["decision"], "review_required")

    def test_merged_pr_must_match_current_head(self):
        (self.work / "code").write_text("branch\n")
        self.git("add", "code", repo=self.work)
        self.git("commit", "-m", "branch", repo=self.work)
        self.policy["repos"][0]["github_repo"] = "example/repo"
        old_run = cleanup.run
        base = self.git("rev-parse", "main").stdout.strip()
        def run(argv, *args, **kwargs):
            if argv[0] == "gh":
                return subprocess.CompletedProcess(argv, 0, json.dumps([{"headRefOid": base, "mergeCommit": {"oid": base}, "url": "https://example.invalid/pr/1"}]).encode(), b"")
            return old_run(argv, *args, **kwargs)
        with patch.object(cleanup, "run", run):
            self.assertEqual(self.candidate()["decision"], "review_required")

    def test_metadata_only_is_allowed_but_mixed_source_is_retained(self):
        (self.work / ".serena").mkdir()
        (self.work / ".serena/project.yml").write_text("local metadata")
        self.assertEqual(self.candidate()["classification"], "metadata_only")
        (self.work / "code").write_text("uncommitted source\n")
        self.assertEqual(self.candidate()["decision"], "review_required")
        self.git("restore", "code", repo=self.work)
        self.assertEqual(self.apply(self.inspect())["removed_count"], 1)

    def test_staged_untracked_and_unknown_ignored_are_not_discarded(self):
        cases = [("staged", "code"), ("untracked", "new"), ("ignored", "ignored/private")]
        for kind, rel in cases:
            path = self.work / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("unique value\n")
            if kind == "staged":
                self.git("add", rel, repo=self.work)
            self.assertEqual(self.candidate()["decision"], "review_required")
            if kind == "staged":
                self.git("restore", "--staged", "--worktree", rel, repo=self.work)
            else:
                path.unlink()

    def test_known_generated_files_do_not_make_clean_worktree_active(self):
        folder = self.work / "node_modules"
        folder.mkdir()
        (folder / "dependency").write_text("generated")
        item = self.candidate()
        self.assertEqual(item["classification"], "clean")
        self.assertEqual(item["decision"], "eligible")

    def test_active_and_recent_are_protected_even_if_integrated(self):
        self.activity["active_paths"] = [str(self.work)]
        self.assertEqual(self.candidate()["decision"], "active")
        self.activity["active_paths"] = []
        self.policy["min_age_seconds"] = 3600
        self.assertEqual(self.candidate()["decision"], "recent")

    def test_missing_base_and_failed_git_are_unknown(self):
        self.policy["repos"][0]["base_ref"] = "missing"
        result = self.inspect()
        self.assertEqual(result["candidates"], [])
        self.assertEqual(len(result["errors"]), 1)
        with patch.object(cleanup, "integration", side_effect=cleanup.Unsafe("diff failed")):
            self.policy["repos"][0]["base_ref"] = "main"
            self.assertEqual(self.inspect()["candidates"], [])

    def test_rc_boundary_and_integrated_protection_order(self):
        self.assertFalse(cleanup.protected("feature/src/search", [], self.policy))
        self.assertTrue(cleanup.protected("feature/rc/search", [], self.policy))
        self.git("branch", "-m", "rc/change", repo=self.work)
        self.assertEqual(self.candidate()["decision"], "eligible")

    def test_policy_base_and_working_change_invalidate_manifest(self):
        manifest = self.inspect()
        self.policy["metadata_paths"] = []
        self.save_policy()
        with self.assertRaises(cleanup.Unsafe):
            self.apply(manifest)
        self.policy["metadata_paths"] = [".serena", ".agent-browser"]
        self.save_policy()
        (self.work / "new").write_text("another writer")
        self.assertEqual(self.apply(manifest)["removed_count"], 0)
        self.assertTrue(self.work.exists())

    def test_mutation_after_journal_start_is_detected(self):
        (self.work / ".serena").mkdir()
        (self.work / ".serena/meta").write_text("metadata")
        manifest = self.inspect()
        original = cleanup.journal_event
        def write(*args, **kwargs):
            original(*args, **kwargs)
            if args[3] == "started":
                (self.work / "code").write_text("concurrent source edit")
        with patch.object(cleanup, "journal_event", write):
            self.assertEqual(self.apply(manifest)["removed_count"], 0)
        self.assertEqual((self.work / "code").read_text(), "concurrent source edit")

    def test_lock_contention_retains_candidate(self):
        manifest = self.inspect()
        lockfile = Path(self.candidate(manifest)["git_common_dir"]) / "codex-worktree-cleanup.lock"
        child = subprocess.Popen(["python3", "-c", "import fcntl,sys,time; f=open(sys.argv[1],'a'); fcntl.flock(f,fcntl.LOCK_EX); print('locked',flush=True); time.sleep(30)", str(lockfile)], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            self.assertEqual(self.apply(manifest)["removed_count"], 0)
        finally:
            child.terminate()
            child.wait()
            child.stdout.close()
        self.assertTrue(self.work.exists())

    def test_journal_protection_and_failed_start_persistence(self):
        manifest = self.inspect()
        self.journal = self.work / "journal.jsonl"
        with self.assertRaises(cleanup.Unsafe):
            self.apply(manifest)
        self.journal = self.root / "journal.jsonl"
        with patch.object(cleanup, "journal_event", side_effect=OSError("disk full")):
            self.assertEqual(self.apply(manifest)["removed_count"], 0)
        self.assertTrue(self.work.exists())

    def test_interrupted_removal_is_not_counted_as_success(self):
        manifest = self.inspect()
        original = cleanup.journal_event
        def write(*args, **kwargs):
            if args[3] == "command_returned":
                raise KeyboardInterrupt()
            original(*args, **kwargs)
        with patch.object(cleanup, "journal_event", write), self.assertRaises(KeyboardInterrupt):
            self.apply(manifest)
        self.assertFalse(self.work.exists())
        result = self.apply(manifest, resume=True)
        self.assertEqual(result["removed_count"], 0)
        self.assertEqual(result["outcomes"][0]["status"], "absent_operation_unknown")
        self.assertEqual(self.apply(manifest, resume=True)["removed_count"], 0)

    def test_superseded_review_requires_exact_snapshot_and_all_dirty_paths(self):
        (self.work / "code").write_text("superseded implementation")
        first = self.candidate()
        review = {"fingerprint": first["fingerprint"], "base": first["base"], "kind": "superseded", "purpose": "replace old behavior", "source_paths": ["code"], "base_paths": ["code"], "observations": ["isolated fixture comparison"], "index_and_untracked_reviewed": True}
        reviews = {first["id"]: review}
        item = self.candidate(self.inspect(reviews))
        self.assertEqual(item["decision"], "eligible")
        (self.work / "new").write_text("not reviewed")
        self.assertEqual(self.candidate(self.inspect(reviews))["decision"], "review_required")

    def test_stale_activity_inventory_rejects_apply(self):
        manifest = self.inspect()
        self.activity["checked_at"] = time.time() - 301
        self.activity_path.write_text(json.dumps(self.activity))
        self.assertEqual(self.apply(manifest)["removed_count"], 0)
        self.assertTrue(self.work.exists())

    def test_same_path_and_head_in_another_repository_is_rejected(self):
        manifest = self.inspect()
        self.git("worktree", "remove", str(self.work))
        other = self.root / "other"
        self.git("clone", str(self.repo), str(other))
        self.git("worktree", "add", "--detach", str(self.work), repo=other)
        self.assertEqual(self.apply(manifest)["removed_count"], 0)
        self.assertTrue(self.work.exists())

    def test_base_update_invalidates_inspection(self):
        manifest = self.inspect()
        (self.repo / "later").write_text("new base")
        self.git("add", "later")
        self.git("commit", "-m", "new base")
        self.assertEqual(self.apply(manifest)["removed_count"], 0)
        self.assertTrue(self.work.exists())

    def test_rename_keeps_both_paths_in_evidence(self):
        self.git("mv", "code", "renamed", repo=self.work)
        item = self.candidate()
        self.assertEqual({row["path"] for row in item["status"]}, {"code", "renamed"})
        self.assertEqual(item["decision"], "review_required")

    def test_cli_does_not_recreate_removed_worktree_for_result(self):
        manifest = self.inspect()
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))
        result = subprocess.run(["python3", str(Path(cleanup.__file__)), "apply", "--policy", str(self.policy_path), "--activity", str(self.activity_path), "--manifest", str(manifest_path), "--candidate", self.candidate(manifest)["id"], "--journal", str(self.journal), "--output", str(self.work / "result.json"), "--allow-delete"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.work.exists())
        self.assertFalse((self.work / "result.json").exists())

    def test_index_flags_cannot_hide_unique_working_content(self):
        for flag in ["assume-unchanged", "skip-worktree"]:
            with self.subTest(flag=flag):
                self.git("update-index", "--" + flag, "code", repo=self.work)
                (self.work / "code").write_text("hidden change")
                self.assertEqual(self.git("status", "--porcelain", repo=self.work).stdout, "")
                item = self.candidate()
                self.assertEqual(item["decision"], "review_required")
                self.assertIn("code", [row["path"] for row in item["status"]])
                self.git("update-index", "--no-" + flag, "code", repo=self.work)
                self.git("restore", "code", repo=self.work)

    def test_review_must_cover_unintegrated_head_and_dirty_content(self):
        (self.work / "unmerged").write_text("unique committed work")
        self.git("add", "unmerged", repo=self.work)
        self.git("commit", "-m", "unmerged", repo=self.work)
        (self.work / "code").write_text("superseded dirty work")
        item = self.candidate()
        review = {"fingerprint": item["fingerprint"], "base": item["base"], "kind": "superseded", "purpose": "fixture", "source_paths": ["code"], "base_paths": ["code"], "observations": ["only dirty code reviewed"], "index_and_untracked_reviewed": True}
        self.assertEqual(self.candidate(self.inspect({item["id"]: review}))["decision"], "review_required")
        review["source_paths"].append("unmerged")
        self.assertEqual(self.candidate(self.inspect({item["id"]: review}))["decision"], "eligible")

    def test_linked_management_worktree_is_protected(self):
        self.policy["repos"][0]["path"] = str(self.work)
        self.assertEqual(self.candidate()["decision"], "active")

    def test_resume_unknown_cli_is_not_success(self):
        manifest = self.inspect()
        self.journal.parent.mkdir()
        cleanup.journal_event(self.journal, manifest["run_id"], self.candidate(manifest), "started")
        self.git("worktree", "remove", str(self.work))
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))
        result = subprocess.run(["python3", str(Path(cleanup.__file__)), "apply", "--policy", str(self.policy_path), "--activity", str(self.activity_path), "--manifest", str(manifest_path), "--candidate", self.candidate(manifest)["id"], "--journal", str(self.journal), "--output", str(self.root / "result.json"), "--allow-delete", "--resume"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["errors"], 1)


if __name__ == "__main__":
    unittest.main()
