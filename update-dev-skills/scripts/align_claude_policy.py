#!/usr/bin/env python3
"""Align managed policy lines from a committed source without copying private globals."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

ASSET = "dev/assets/global/claude-policy-lines.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def align(data, rules):
    lines = data.decode("utf-8").splitlines(keepends=True)
    for rule in rules:
        old, new = rule["before"], rule["after"]
        old_at = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == old]
        new_at = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == new]
        if len(old_at) == 1 and not new_at:
            i = old_at[0]
            lines[i] = new + lines[i][len(old):]
        elif old_at or len(new_at) != 1:
            raise ValueError("managed line missing, duplicated, or conflicting; inspect before applying")
    return "".join(lines).encode("utf-8")


def publish(target, before, after, backup_dir):
    if target.is_symlink() or not target.is_file():
        raise ValueError("target must be a regular file, not a symlink")
    mode = stat.S_IMODE(target.stat().st_mode)
    backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = backup_dir / ("CLAUDE." + digest(before) + ".md")
    if backup.exists():
        if backup.read_bytes() != before:
            raise ValueError("backup content does not match")
    else:
        with backup.open("xb") as handle:
            os.chmod(backup, 0o600)
            handle.write(before)
            handle.flush()
            os.fsync(handle.fileno())
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
            name = Path(handle.name)
            os.chmod(name, mode)
            handle.write(after)
            handle.flush()
            os.fsync(handle.fileno())
        if target.is_symlink() or target.read_bytes() != before:
            raise ValueError("target changed during preparation; inspect again")
        os.replace(name, target)
        name = None
        if target.read_bytes() != after:
            raise ValueError("target readback mismatch; inspect before recovery")
    finally:
        if name is not None:
            name.unlink(missing_ok=True)
    return str(backup)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        sha = subprocess.check_output(["git", "-C", str(args.source_root), "rev-parse", "--verify", args.commit + "^{commit}"], text=True).strip()
        rules = json.loads(subprocess.check_output(["git", "-C", str(args.source_root), "show", sha + ":" + ASSET]))
        if args.target.is_symlink() or not args.target.is_file():
            raise ValueError("target must be an existing regular file")
        before = args.target.read_bytes()
        after = align(before, rules)
        backup = None
        if args.apply and before != after:
            if args.backup_dir is None:
                raise ValueError("--backup-dir is required for apply")
            backup = publish(args.target, before, after, args.backup_dir)
        print(json.dumps({"source_commit": sha, "target": str(args.target), "before_sha256": digest(before), "after_sha256": digest(after), "status": "identical" if before == after else ("applied" if args.apply else "different"), "backup": backup}))
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, "Policy alignment failed: " + str(error) + "\n")


if __name__ == "__main__":
    main()
