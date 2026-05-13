---
name: memory-protocol
description: Use when working in a repo with the kb-memory MCP attached and the task is non-trivial (multi-file changes, design decisions, debugging, indexing, anything that produces or consumes durable knowledge). Encodes the read/write loop, the file-memory-vs-kb-graph split, bi-temporal discipline, and token-budget heuristics so Claude uses the graph reflexively without over-querying.
---

# kb-memory protocol

Two persistent memory systems coexist. Use the right one or both:

## File-memory vs kb-graph — one-line rule

| System | Use for | Cost |
|---|---|---|
| **File memory** (`~/.ccs/.../memory/MEMORY.md` + per-fact `.md`) | Stable, cross-project facts: *user* preferences, persistent gotchas, references to external systems. Loaded into every conversation. | Cheap to load, doesn't scale past ~150-char index lines. |
| **kb graph** (`memory` MCP — write: `add_memory`; semantic read: `search_nodes`, `search_memory_facts`; browse/discover: `list_groups`, `get_episodes`) | Project-specific knowledge that benefits from semantic search and contradiction handling: `ArchitecturalDecision`, `CodePattern`, `APISurface`, `Dependency`, `BugPattern`, `ProjectConfig`, `TeamPreference`, `Event`, `Topic`. Queried on demand. | Pays a round-trip + ~10 entity summaries per query. Free to grow large. |

**Default placement:** project-scoped → graph; user-scoped or cross-project → file. **Exception:** a high-priority cross-project gotcha (e.g. `COPYFILE_DISABLE=1` for macOS-tar-to-Linux) may live in *both* — file for guaranteed recall, graph in a `team-prefs` group for semantic discovery. Treat duplication as a deliberate exception, not the default.

## Reading the graph — when to search

**Search at session start when** the user's first prompt is substantive:
- Mentions a feature, module, or subsystem by name
- Asks "how does X work" / "where is Y" / "design Z"
- Implements / refactors / debugs across more than one file
- References a prior decision ("we discussed this", "the way we set it up")

**Skip when:**
- Single-line edit, rename, typo fix, dependency bump
- Pure read ("what's in this file", "show me the diff")
- Mechanical refactor with no design choices
- The current `git diff` is all that's needed to answer

**How to query:**
1. `search_nodes` first with 2–4 keywords from the prompt, filtered by relevant `group_ids` (the project group + its `-docs` sibling, plus any cross-project group like `team-prefs`).
2. If matches look promising, follow up with `search_memory_facts` on the strongest entity names to pull relationships.
3. Review any `ArchitecturalDecision` or `TeamPreference` nodes returned — these are committed decisions; don't contradict without flagging.

**Discover & browse (not semantic):**
- `list_groups()` — enumerate every `group_id` in the graph with `episode_count` + `latest_episode_at` (newest first; `counts=True` adds `entity_count`). Use it when you're unsure which groups exist for this project, or to sanity-check that the indexed corpus you expect is actually there before searching.
- `get_episodes(group_ids=[...], max_episodes=N, offset=M, include_content=False)` — list episodes newest-first. With **no** `group_ids` it spans the whole graph (latest activity anywhere). This is chronological browsing — "what was recorded recently" — not semantic lookup; reach for `search_nodes` / `search_memory_facts` for that. `include_content=False` keeps the response cheap when you only need titles/sources.

**Group convention (read-many, write-one):**

| Group | Source | Written by |
|---|---|---|
| `<project>` | Code + configs | `scripts/index.py` only — **never via `add_memory`** |
| `<project>-docs` | Project wiki / markdown | `scripts/index.py` only — **never via `add_memory`** |
| `<project>-notes` | Curated decisions, patterns, configs captured mid-session | `add_memory` — **write target for project-specific facts** |
| `<project>-exp-<tag>` | Experimental indexing runs | `scripts/index.py --tag` |
| `team-prefs` (cross-project) | Conventions, gotchas, style — applies everywhere | `add_memory` for cross-project `TeamPreference` writes |

The indexed canonical groups (`<project>`, `<project>-docs`) are reserved for the indexer so they stay reproducible from source. Session writes go to `<project>-notes` (project-specific) or `team-prefs` (cross-project). Writing to the canonical groups via `add_memory` silently pollutes the indexed corpus — entity dedup mutates summaries, and bi-temporal contradiction can invalidate correct file-derived edges (the read-many / write-one rule).

This is enforced, not just advised: a `PreToolUse` hook in this plugin **blocks** `add_memory` calls whose `group_id` isn't a `-notes` group / `team-prefs` / on `$KB_WRITE_ALLOWLIST`, and the Graphiti MCP server does the same server-side (`GRAPHITI_WRITE_GUARD=notes-only`, on by default — accepts only `-notes` groups + `GRAPHITI_WRITE_ALLOWLIST`). If a write is denied, that's the guard working — re-issue it against `<project>-notes`; don't try to route around it.

Multi-group queries are cheap: `group_ids=["<project>", "<project>-docs", "<project>-notes", "team-prefs"]`.

## Writing to the graph — when to add_memory

**Always target `<project>-notes` (project-specific facts) or `team-prefs` (cross-project) — never the indexed canonical groups.** See the group-convention table above.

Write reflexively — *during* the turn that surfaces the fact, not at session end. Specifically:

- **ArchitecturalDecision** — the user accepted a design proposal, picked a framework, or settled a trade-off. Use `source="json"` with `{decision, rationale, affected_components}`.
- **CodePattern** — a non-obvious naming/error/data-flow convention emerged that future code should match.
- **BugPattern** — a debugging session ended with a fix; record symptom + root cause + fix strategy.
- **ProjectConfig** — a port, env var, default, or feature flag that isn't in version control or is non-obvious from it.
- **TeamPreference** — the user said "always do X" / "never do Y" about style, commits, reviews. Cross-project → write to `team-prefs` group.
- **Event** — deployment, incident, milestone with a date.

**Don't write:**
- Code patterns derivable from `git log` / `git blame` / reading the file
- Ephemeral task state (in-progress work, current conversation context)
- Anything already in CLAUDE.md or the wiki

**Anti-pattern:** "I'll remember this" with no `add_memory` call. If it's worth remembering, it's worth one tool call now.

## Bi-temporal discipline — when to invalidate

Graphiti edges are bi-temporal (`valid_at` / `invalid_at`). When the world changes, **add a new contradicting episode** — do *not* delete the old one; the graph will mark the old edge invalid while preserving history.

**Trigger situations:**
- A previous `ArchitecturalDecision` is being overridden in this task. Write the new decision and reference what it supersedes.
- A `ProjectConfig` value changed (port, env var, default). Write the new value with current context.
- A `BugPattern` fix recipe turned out to be wrong. Write the corrected recipe; flag the prior one as superseded in the rationale field.

**Trigger phrases from the user:** "actually we changed that", "we used to do X but now…", "scratch that", "the old way doesn't work anymore". Each is a write signal, not a read signal.

## Token-budget heuristics

Every `search_nodes` returns up to ~10 entities with full summaries — meaningful context. Budget rules:

- One pre-emptive `search_nodes` per substantive turn is fine. A second is fine if the first surfaced a strong lead. Past two, you're probably searching too broadly — narrow the keyword instead.
- After a long search-tool sequence (>5 calls), summarize what you learned and `add_memory` it before continuing. The transcript is volatile; the graph is durable.
- Don't query inside tight tool loops (e.g. fixing one type error per file). Query once at the planning stage, then act.

## Stale-fact drift — trust observation over recall

A memory naming a specific function, file, flag, or port is a claim about *when it was written*. Before recommending it:
- Memory names a path → check the file exists.
- Memory names a function/flag → grep for it.
- Memory summarizes architecture → spot-check one load-bearing claim.

If recall conflicts with current code, **trust the code** and update or remove the stale memory rather than acting on it.
