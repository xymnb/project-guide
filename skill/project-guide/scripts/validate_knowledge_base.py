from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
CONFIG = SKILL_ROOT / "project-guide.local.json"


def fail(message: str) -> int:
    print(f"ERROR: {message}")
    return 1


def main() -> int:
    if not CONFIG.is_file():
        print("NOT_CONFIGURED: optional local knowledge base is not configured")
        return 0

    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"invalid JSON: {exc}")

    if not data.get("enabled", False):
        print("DISABLED: local knowledge base routing is disabled")
        return 0

    root_value = data.get("knowledge_base_root")
    if not isinstance(root_value, str) or not root_value.strip():
        return fail("knowledge_base_root must be a non-empty string")

    root = Path(root_value)
    if not root.is_dir():
        return fail(f"knowledge_base_root does not exist: {root}")

    routes = data.get("routes")
    if not isinstance(routes, dict) or not routes:
        return fail("routes must be a non-empty object")

    errors: list[str] = []
    checked = 0
    for key, entries in routes.items():
        if not isinstance(key, str) or not key:
            errors.append("route key must be a non-empty string")
            continue
        if not isinstance(entries, list) or not entries:
            errors.append(f"{key}: route must be a non-empty list")
            continue

        for entry in entries:
            if not isinstance(entry, str) or not entry.strip():
                errors.append(f"{key}: route entry must be a non-empty string")
                continue

            rel = Path(entry)
            if rel.is_absolute() or ".." in rel.parts:
                errors.append(f"{key}: route must stay under knowledge base root: {entry}")
                continue
            if "90 原始资料" in rel.parts:
                errors.append(f"{key}: automatic routes may not target 90 原始资料: {entry}")
                continue

            target = root / rel
            checked += 1
            if not target.is_file():
                errors.append(f"{key}: missing document: {entry}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"OK: {checked} routed documents exist under configured knowledge base")
    return 0


if __name__ == "__main__":
    sys.exit(main())
