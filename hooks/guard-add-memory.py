#!/usr/bin/env python3
"""PreToolUse guard for the kb-memory plugin: keep `add_memory` off the
indexer-owned canonical groups.

Session writes belong in `<project>-notes` (or `team-prefs` for
cross-project preferences). The canonical `<project>` and `<project>-docs`
groups are reserved for the indexer (`scripts/index.py`) so the indexed
corpus stays reproducible from source — writing there silently mutates
entity summaries via dedup and can invalidate correct file-derived edges
via bi-temporal contradiction. See the `memory-protocol` skill and the
alms-memory wiki page `Concurrent-Writes-and-Protection`.

A write is ALLOWED when any of these holds:
  - no `group_id` is passed (the server falls back to `GRAPHITI_GROUP_ID`,
    which deployments set to a `-notes` group);
  - `group_id` ends with `-notes`;
  - `group_id` == `team-prefs`;
  - `group_id` is listed in `$KB_WRITE_ALLOWLIST` (comma-separated) — the
    escape hatch for a deliberate seed.

Anything else is denied with an actionable message.

Fail-open by design: any parse/IO error -> allow. A guard must never wedge
a session. The MCP-server-side guard (`GRAPHITI_PROTECTED_GROUPS`) is the
hard wall that also covers non-plugin clients; this hook is just fast UX.
"""

import json
import os
import sys


def _allowed(group_id: str) -> bool:
    if not group_id:
        return True
    if group_id.endswith("-notes"):
        return True
    if group_id == "team-prefs":
        return True
    allowlist = {
        g.strip()
        for g in os.environ.get("KB_WRITE_ALLOWLIST", "").split(",")
        if g.strip()
    }
    return group_id in allowlist


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0  # fail open

    if not isinstance(data, dict):
        return 0

    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    group_id = str(tool_input.get("group_id") or "").strip()

    if _allowed(group_id):
        return 0

    suggestion = group_id[:-5] if group_id.endswith("-docs") else group_id
    reason = (
        f"Refusing add_memory to group '{group_id}': that group is indexer-owned "
        f"(written only by scripts/index.py), so an interactive write there can "
        f"silently mutate or invalidate facts extracted from source. Session "
        f"memory goes to a '-notes' group or 'team-prefs' — retry with "
        f"group_id='{suggestion}-notes'. For a deliberate seed, add the group to "
        f"$KB_WRITE_ALLOWLIST. See the memory-protocol skill / "
        f"Concurrent-Writes-and-Protection."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
