#!/usr/bin/env python3
"""Detect candidate CI/CD and deployment surfaces from repository markers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


TEXT_LIMIT = 2_000_000


def relative(repo: Path, path: Path) -> str:
    return str(path.relative_to(repo))


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")[:TEXT_LIMIT]
    except (OSError, UnicodeDecodeError):
        return ""


def workflow_files(repo: Path) -> list[Path]:
    root = repo / ".github" / "workflows"
    if not root.exists():
        return []
    return sorted([*root.glob("*.yml"), *root.glob("*.yaml")])


def matching_workflows(repo: Path, workflows: list[Path], pattern: str) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    return [relative(repo, path) for path in workflows if regex.search(read_text(path))]


def existing(repo: Path, names: tuple[str, ...]) -> list[str]:
    return [name for name in names if (repo / name).exists()]


def detect(repo: Path) -> dict[str, Any]:
    workflows = workflow_files(repo)
    action_evidence = [relative(repo, path) for path in workflows]

    vercel = existing(repo, (".vercel/project.json", "vercel.json"))
    vercel += matching_workflows(repo, workflows, r"\bvercel\b")

    cloud_run = existing(repo, ("service.yaml", "service.yml", "cloudbuild.yaml"))
    cloud_run += matching_workflows(
        repo,
        workflows,
        r"deploy-cloudrun|gcloud\s+run\s+deploy|run\.googleapis\.com|google-github-actions/deploy-cloudrun",
    )

    cloudflare = existing(repo, ("wrangler.toml", "wrangler.json", "wrangler.jsonc"))
    cloudflare += matching_workflows(repo, workflows, r"\bwrangler\b|cloudflare")

    github_pages = matching_workflows(repo, workflows, r"deploy-pages|configure-pages|github-pages")

    def surface(candidate: bool, evidence: list[str]) -> dict[str, Any]:
        return {"candidate": candidate, "evidence": sorted(set(evidence))}

    return {
        "repo": str(repo),
        "surfaces": {
            "github_actions": surface(bool(workflows), action_evidence),
            "vercel": surface(bool(vercel), vercel),
            "cloud_run": surface(bool(cloud_run), cloud_run),
            "cloudflare": surface(bool(cloudflare), cloudflare),
            "github_pages": surface(bool(github_pages), github_pages),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.expanduser().resolve()
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise SystemExit(f"not a git worktree: {repo}")
    print(json.dumps(detect(repo), ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
