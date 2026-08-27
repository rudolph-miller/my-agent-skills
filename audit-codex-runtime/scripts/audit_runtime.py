#!/usr/bin/env python3
"""Read-only allowlist audit for Codex config and session metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib
from typing import Any


def read_toml(path: Path | None, keys: tuple[str, ...]) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_file():
        raise FileNotFoundError(f"TOML file does not exist: {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {key: data.get(key) for key in keys}


def nested(mapping: Any, *keys: str) -> Any:
    value = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def audit_session(path: Path) -> dict[str, Any]:
    session_meta: dict[str, Any] | None = None
    turn_context: dict[str, Any] | None = None

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("type") == "session_meta" and session_meta is None:
                payload = item.get("payload")
                if isinstance(payload, dict):
                    session_meta = payload
            elif item.get("type") == "turn_context":
                payload = item.get("payload")
                if isinstance(payload, dict):
                    turn_context = payload

    meta = session_meta or {}
    turn = turn_context or {}
    role = meta.get("agent_role")
    if role is None:
        role = nested(meta, "source", "subagent", "thread_spawn", "agent_role")

    return {
        "path": str(path),
        "session_id": meta.get("id") or meta.get("session_id"),
        "thread_source": meta.get("thread_source"),
        "agent_role": role,
        "agent_path": meta.get("agent_path")
        or nested(meta, "source", "subagent", "thread_spawn", "agent_path"),
        "parent_thread_id": meta.get("parent_thread_id")
        or nested(meta, "source", "subagent", "thread_spawn", "parent_thread_id"),
        "cwd": turn.get("cwd") or meta.get("cwd"),
        "cli_version": meta.get("cli_version"),
        "model": turn.get("model"),
        "effort": turn.get("effort")
        or nested(turn, "collaboration_mode", "settings", "reasoning_effort"),
        "multi_agent_version": turn.get("multi_agent_version"),
        "multi_agent_mode": turn.get("multi_agent_mode"),
    }


def recent_sessions(root: Path, limit: int) -> list[Path]:
    if not root.is_dir():
        raise FileNotFoundError(f"sessions root does not exist: {root}")
    files = [path for path in root.rglob("rollout-*.jsonl") if path.is_file()]
    files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return files[:limit]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--agent-config", action="append", type=Path, default=[])
    parser.add_argument("--session", action="append", type=Path, default=[])
    parser.add_argument("--sessions-root", type=Path)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sessions = list(args.session)
    if args.sessions_root:
        sessions.extend(recent_sessions(args.sessions_root, max(args.limit, 0)))

    missing_sessions = [path for path in sessions if not path.is_file()]
    if missing_sessions:
        raise FileNotFoundError(f"session file does not exist: {missing_sessions[0]}")
    unique_sessions = list(dict.fromkeys(path.resolve() for path in sessions))
    result = {
        "static_config": read_toml(
            args.config,
            ("model", "model_reasoning_effort", "approval_policy", "sandbox_mode"),
        ),
        "agent_configs": [
            {
                "path": str(path),
                "evidence_level": "declared_file_only",
                "values": read_toml(
                    path,
                    ("name", "model", "model_reasoning_effort", "description"),
                ),
            }
            for path in args.agent_config
        ],
        "sessions": [audit_session(path) for path in unique_sessions],
    }
    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
