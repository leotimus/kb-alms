# kb-alms

A Claude Code plugin that wires Claude into a Graphiti-backed knowledge-graph memory MCP and ships the read/write protocol that makes the memory loop tight instead of leaky.

It bundles the MCP connection + the protocol Claude should follow into one installable unit, so memory usage is consistent across machines and projects.

## What it ships

| Piece | Purpose |
|---|---|
| `.mcp.json` | Bundles the `memory` MCP at `${KB_MEMORY_URL}` with bearer auth from `${MEMORY_MCP_TOKEN}`. Both are environment variables — nothing host-specific is committed. |
| `skills/memory-protocol/SKILL.md` | The rule-of-thumb Claude follows: file-memory vs graph split, when to read, when to write, bi-temporal triggers, token budget, stale-fact handling. |
| `commands/kb-search.md` | `/kb-search <keywords>` — guided multi-group search across `<project>`, `<project>-docs`, `<project>-notes`, and `team-prefs`. |
| `commands/kb-write.md` | `/kb-write <type> <body>` — structured `add_memory` to `<project>-notes` (or `team-prefs` for cross-project preferences); never to the indexed canonical groups. Checks for contradictions before writing. |
| `hooks/hooks.json` + `hooks/guard-add-memory.py` | `PreToolUse` hook on `add_memory` that **blocks** writes to indexer-owned groups. Allows `*-notes`, `team-prefs`, anything in `$KB_WRITE_ALLOWLIST`, or no `group_id` (server falls back to its default); denies the rest with a fix-it message. Fail-open on parse errors. |

## Requirements

- Claude Code with plugin support
- A reachable Graphiti MCP endpoint (self-hosted or otherwise)
- `KB_MEMORY_URL` — the MCP URL (e.g. `https://your-graphiti-host/mcp`)
- `MEMORY_MCP_TOKEN` — bearer token for that endpoint
- `KB_WRITE_ALLOWLIST` *(optional)* — comma-separated group IDs the write-guard hook should let through in addition to `*-notes` / `team-prefs`. Use it for a deliberate one-off seed of a canonical group.

Export both (the allowlist is optional) in your shell — or set them in your Claude env — before starting Claude Code:

```bash
export KB_MEMORY_URL=https://your-graphiti-host/mcp
export MEMORY_MCP_TOKEN=...   # ask the endpoint owner for a token
```

## Install

This repo doubles as a single-plugin marketplace (`.claude-plugin/marketplace.json`):

```bash
# from a marketplace
/plugin marketplace add leotimus/kb-alms
/plugin install kb-memory@kb-alms

# or from a local checkout
git clone https://github.com/leotimus/kb-alms.git
/plugin marketplace add ./kb-alms
/plugin install kb-memory@kb-alms
```

Verify the MCP is connected:

```
/mcp
```

You should see `memory` listed.

## Scope (v0.2)

Skill + commands + one hook: the `add_memory` write-guard above. It's deliberately the *only* hook so far — it enforces a hard, well-settled rule (never write the indexer-owned groups) rather than nudging behaviour, and it fails open. Still on the follow-up list: a `UserPromptSubmit` keyword reminder and a `Stop` write-suggestion (both are *nudges*, not invariants, so they wait until the conventions around them settle).

The hook is the **fast-feedback** layer — it only protects sessions that have this plugin installed. The durable wall is server-side: the Graphiti MCP image in `alms-memory` honours `GRAPHITI_PROTECTED_GROUPS` and rejects the same writes for every client. Run both.
