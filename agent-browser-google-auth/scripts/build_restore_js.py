#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from urllib.parse import urlparse


def normalize_domain(domain: str) -> str:
    return domain.lstrip(".").lower()


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: build_restore_js.py <auth_file> <base_url>", file=sys.stderr)
        return 1

    auth_path = Path(sys.argv[1])
    base_url = sys.argv[2]

    if not auth_path.exists():
        print(f"auth file not found: {auth_path}", file=sys.stderr)
        return 2

    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    origin = f"{parsed.scheme}://{parsed.netloc}"

    state = json.loads(auth_path.read_text(encoding="utf-8"))

    lines: list[str] = []

    for cookie in state.get("cookies", []):
        domain = normalize_domain(cookie.get("domain", ""))
        if domain != host:
            continue

        cookie_line = f"{cookie['name']}={cookie['value']}; path=/"
        lines.append(f"document.cookie = {json.dumps(cookie_line)};")

    for item in state.get("origins", []):
        if item.get("origin") != origin:
            continue

        for storage in item.get("localStorage", []):
            key = storage.get("name", "")
            value = storage.get("value", "")
            lines.append(
                f"localStorage.setItem({json.dumps(key)}, {json.dumps(value)});"
            )

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
