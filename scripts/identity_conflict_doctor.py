#!/usr/bin/env python3
"""Audit and optionally clean identity conflicts for a specific user_id."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROXY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROXY_ROOT))

from infrastructure import get_memory, resolve_user_id

try:
    from canonical_identity import CANONICAL_USER_ID, CANONICAL_NAME, USER_ALIASES  # type: ignore
except Exception:
    CANONICAL_USER_ID = "default"
    CANONICAL_NAME = "Mark"
    USER_ALIASES = ["mark", "Mark"]


def normalize(value: str) -> str:
    return (value or "").strip().lower()


def collect_identity_preferences(memory, user_id: str) -> List[Dict]:
    prefs = memory.get_preferences(user_id=user_id) or []
    return [p for p in prefs if p.get("category") in {"name", "preferred_name"}]


def summarize_conflicts(rows: List[Dict]) -> Dict[str, Dict]:
    summary: Dict[str, Dict] = {}
    for row in rows:
        pref = str(row.get("preference", "")).strip()
        if not pref:
            continue
        key = normalize(pref)
        item = summary.setdefault(key, {"preference": pref, "count": 0, "max_confidence": 0.0, "latest": ""})
        item["count"] += 1
        try:
            item["max_confidence"] = max(float(item["max_confidence"]), float(row.get("confidence", 0.0)))
        except Exception:
            pass
        latest = str(row.get("updated_at", ""))
        if latest > str(item.get("latest", "")):
            item["latest"] = latest
    return summary


def postgres_cleanup(memory, user_id: str, allowed: set[str]) -> int:
    with memory.conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM learned_preferences
            WHERE user_id = %s
              AND category IN ('name', 'preferred_name')
              AND lower(preference) <> ALL(%s)
            """,
            (user_id, list(sorted(allowed))),
        )
        deleted = cur.rowcount
        memory.conn.commit()
        return deleted


def sqlite_cleanup(memory, user_id: str, allowed: set[str]) -> int:
    conn = memory._get_sqlite_conn()
    if not conn:
        return 0
    rows = conn.execute("SELECT key, value FROM user_preferences").fetchall()
    deleted = 0
    for row in rows:
        key = row["key"]
        if not key.startswith(f"{user_id}::"):
            continue
        body = key.split("::", 1)[1]
        if not (body.startswith("name:") or body.startswith("preferred_name:")):
            continue
        _, pref = body.split(":", 1)
        if normalize(pref) in allowed:
            continue
        conn.execute("DELETE FROM user_preferences WHERE key = ?", (key,))
        deleted += 1
    conn.commit()
    conn.close()
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit/clean identity conflicts")
    parser.add_argument("--user-id", default=CANONICAL_USER_ID, help="Target user_id")
    parser.add_argument("--apply", action="store_true", help="Apply cleanup instead of dry-run")
    parser.add_argument("--canonical-name", default=CANONICAL_NAME, help="Canonical name to keep")
    args = parser.parse_args()

    user_id = resolve_user_id(args.user_id)
    canonical_name = args.canonical_name.strip() or CANONICAL_NAME
    aliases = {normalize(canonical_name)}
    aliases.update(normalize(alias) for alias in USER_ALIASES or [])

    memory = get_memory()
    if not memory:
        print("ERROR: memory backend unavailable")
        return 2

    rows = collect_identity_preferences(memory, user_id)
    summary = summarize_conflicts(rows)

    print(json.dumps({
        "user_id": user_id,
        "canonical_name": canonical_name,
        "names": sorted(summary.values(), key=lambda v: (v.get("latest", ""), v.get("max_confidence", 0.0)), reverse=True),
        "conflict": len(summary) > 1,
        "apply": bool(args.apply),
    }, indent=2))

    if not args.apply:
        return 0

    deleted = 0
    if memory.conn:
        deleted = postgres_cleanup(memory, user_id, aliases)
    elif getattr(memory, "_sqlite_enabled", False):
        deleted = sqlite_cleanup(memory, user_id, aliases)

    memory.learn_preference("name", canonical_name, confidence=0.99, user_id=user_id)
    print(json.dumps({
        "status": "applied",
        "user_id": user_id,
        "deleted_conflicts": deleted,
        "canonical_written": canonical_name,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
