import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("align_policy", Path(__file__).parents[1] / "scripts/align_claude_policy.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class PolicyTests(unittest.TestCase):
    def test_preserve_unmanaged_lines_and_line_endings(self):
        before = b"private instruction\r\nold\r\nlast without newline"
        after = policy.align(before, [{"before": "old", "after": "new"}])
        self.assertEqual(after, b"private instruction\r\nnew\r\nlast without newline")
        self.assertEqual(policy.align(after, [{"before": "old", "after": "new"}]), after)

    def test_unknown_duplicate_or_conflicting_line_fails(self):
        for data in [b"other\n", b"old\nold\n", b"old\nnew\n", b"new\nnew\n"]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                policy.align(data, [{"before": "old", "after": "new"}])

    def test_backup_readback_and_concurrent_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "CLAUDE.md"
            target.write_bytes(b"old\n")
            backup = policy.publish(target, b"old\n", b"new\n", root / "backups")
            self.assertEqual(Path(backup).read_bytes(), b"old\n")
            self.assertEqual(target.read_bytes(), b"new\n")
            target.write_bytes(b"concurrent edit\n")
            with self.assertRaises(ValueError):
                policy.publish(target, b"new\n", b"next\n", root / "backups")
            self.assertEqual(target.read_bytes(), b"concurrent edit\n")


if __name__ == "__main__":
    unittest.main()
