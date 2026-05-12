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

## Requirements

- Claude Code with plugin support
- A reachable Graphiti MCP endpoint (self-hosted or otherwise)
- `KB_MEMORY_URL` — the MCP URL (e.g. `https://your-graphiti-host/mcp`)
- `MEMORY_MCP_TOKEN` — bearer token for that endpoint

Export both in your shell (or set them in your Claude env) before starting Claude Code:

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

## Scope (v0.1)

Skill + commands only. **No hooks** in this slice — the rules need to settle before automating them. Hooks (`UserPromptSubmit` keyword reminder, `Stop` write-suggestion) are tracked as follow-up work.
