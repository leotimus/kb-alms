---
description: Search the kb graph for nodes and facts relevant to the current task across project + docs + team-prefs groups.
argument-hint: <query keywords> [--group <id>] [--project <name>]
---

Search the kb-memory graph for context relevant to: $ARGUMENTS

Procedure:

1. **Resolve groups.** If `--project <name>` was passed, target `["<name>", "<name>-docs", "<name>-notes", "team-prefs"]`. If `--group <id>` was passed, use exactly that. Otherwise infer the project from the current working directory (basename of the git root) and use `["<basename>", "<basename>-docs", "<basename>-notes", "team-prefs"]`. The `-notes` group holds session-curated facts written via `/kb-write` and must be queried alongside the indexed canonical groups so reads see everything.

   If the inferred names look uncertain (e.g. the basename doesn't obviously match an indexed corpus), call `list_groups()` once first and pick the closest-matching `group_id`s from the result — cheaper than fanning a search across guessed names.

2. **Run `search_nodes`** with the user's query keywords against the resolved groups. Limit to 10 results.

3. **If any node looks load-bearing** (an `ArchitecturalDecision`, `BugPattern`, `ProjectConfig`, or a high-summary entity), follow up with `search_memory_facts` using the entity's name to pull relationships.

4. **Report back concisely:**
   - Group up to 5 most relevant nodes with one-line summaries.
   - Call out any `ArchitecturalDecision` / `TeamPreference` explicitly — those are committed decisions.
   - List any facts with `valid_at` / `invalid_at` that affect interpretation.
   - If nothing relevant turned up, say so plainly and suggest broader keywords.

Do not over-fetch. If the first query returns clearly-irrelevant results, narrow the keywords and try once more rather than fanning out across groups.
