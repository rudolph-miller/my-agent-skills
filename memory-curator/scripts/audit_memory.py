#!/usr/bin/env python3
"""Inventory a Codex MEMORY.md without modifying or echoing sensitive content."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any


GROUP_RE = re.compile(r"^# Task Group:\s*(.+)$")
TASK_RE = re.compile(r"^## Task \d+:\s*(.+)$")
ROLLOUT_RE = re.compile(r"rollout_summaries/[^ )]+")
SNAPSHOT_PATTERNS = (
    re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE),
    re.compile(r"\bPR\s*#?\d+\b", re.IGNORECASE),
    re.compile(r"\b(?:run|job|revision|version)[ _:#-]*\d+\b", re.IGNORECASE),
    re.compile(r"https?://"),
    re.compile(r"\b20\d{2}-\d{2}-\d{2}\b"),
)
NORMALIZE_PATTERNS = (
    re.compile(r"https?://\S+"),
    re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\b"),
)


@dataclass
class Group:
    title: str
    start_line: int
    task_count: int = 0
    rollout_refs: set[str] = field(default_factory=set)
    snapshot_signals: int = 0


def normalize_bullet(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("- ") or len(stripped) < 24:
        return None
    value = stripped.lower()
    for pattern in NORMALIZE_PATTERNS:
        value = pattern.sub("<x>", value)
    value = re.sub(r"\s+", " ", value)
    return value


def inventory(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    groups: list[Group] = []
    current: Group | None = None
    rollouts: set[str] = set()
    normalized: dict[str, list[int]] = {}

    for line_number, line in enumerate(lines, start=1):
        group_match = GROUP_RE.match(line)
        if group_match:
            current = Group(group_match.group(1), line_number)
            groups.append(current)
            continue
        if TASK_RE.match(line) and current:
            current.task_count += 1

        refs = set(ROLLOUT_RE.findall(line))
        rollouts.update(refs)
        if current:
            current.rollout_refs.update(refs)
            current.snapshot_signals += sum(bool(pattern.search(line)) for pattern in SNAPSHOT_PATTERNS)

        bullet = normalize_bullet(line)
        if bullet:
            fingerprint = hashlib.sha256(bullet.encode()).hexdigest()[:12]
            normalized.setdefault(fingerprint, []).append(line_number)

    base = path.parent
    missing = sorted(ref for ref in rollouts if not (base / ref).exists())
    missing_fingerprints = [hashlib.sha256(ref.encode()).hexdigest()[:12] for ref in missing]
    duplicates = [
        {"fingerprint": fingerprint, "count": len(line_numbers), "lines": line_numbers[:20]}
        for fingerprint, line_numbers in normalized.items()
        if len(line_numbers) >= 2
    ]
    duplicates.sort(key=lambda item: (-item["count"], item["fingerprint"]))

    group_rows = [
        {
            "title_fingerprint": hashlib.sha256(group.title.encode()).hexdigest()[:12],
            "start_line": group.start_line,
            "task_count": group.task_count,
            "rollout_ref_count": len(group.rollout_refs),
            "snapshot_signals": group.snapshot_signals,
        }
        for group in groups
    ]
    group_rows.sort(key=lambda item: (-item["task_count"], -item["snapshot_signals"]))

    return {
        "source_file": path.name,
        "source_path_fingerprint": hashlib.sha256(str(path).encode()).hexdigest()[:12],
        "line_count": len(lines),
        "task_group_count": len(groups),
        "task_count": sum(group.task_count for group in groups),
        "rollout_reference_count": len(rollouts),
        "missing_rollout_reference_count": len(missing),
        "missing_rollout_reference_fingerprints": missing_fingerprints,
        "groups": group_rows,
        "duplicate_bullet_fingerprints": duplicates,
    }


def render_markdown(result: dict[str, Any], top: int) -> str:
    output = [
        "# Memory audit",
        "",
        f"- Lines: {result['line_count']}",
        f"- Task groups: {result['task_group_count']}",
        f"- Tasks: {result['task_count']}",
        f"- Rollout references: {result['rollout_reference_count']}",
        f"- Missing rollout references: {result['missing_rollout_reference_count']}",
        "",
        "## Largest groups",
        "",
        "| Start | Tasks | Rollouts | Snapshot signals | Group fingerprint |",
        "| ---: | ---: | ---: | ---: | --- |",
    ]
    for group in result["groups"][:top]:
        output.append(
            f"| {group['start_line']} | {group['task_count']} | "
            f"{group['rollout_ref_count']} | {group['snapshot_signals']} | "
            f"`{group['title_fingerprint']}` |"
        )
    output.extend(
        [
            "",
            "## Duplicate bullet candidates",
            "",
            "Only fingerprints and line numbers are shown to avoid reproducing sensitive content.",
            "",
        ]
    )
    for item in result["duplicate_bullet_fingerprints"][:top]:
        output.append(
            f"- `{item['fingerprint']}`: {item['count']} occurrences; lines {item['lines']}"
        )
    return "\n".join(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("memory", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--top", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = inventory(args.memory.resolve())
    if args.format == "markdown":
        print(render_markdown(result, max(args.top, 0)))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
