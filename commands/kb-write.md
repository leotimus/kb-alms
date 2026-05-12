---
description: Add a structured episode to the kb graph with the right entity type and group_id.
argument-hint: <decision|pattern|bug|config|preference|event> <free-text body>
---

Add an episode to the kb-memory graph capturing: $ARGUMENTS

Procedure:

1. **Parse the type** from the first argument:
   - `decision` → `ArchitecturalDecision`
   - `pattern` → `CodePattern`
   - `bug` → `BugPattern`
   - `config` → `ProjectConfig`
   - `preference` → `TeamPreference`
   - `event` → `Event`

   If the first argument is none of these, ask the user which type fits before writing.

2. **Pick the group_id:**
   - `TeamPreference` and clearly-cross-project gotchas → `team-prefs`.
   - Everything else → `<project>-notes` (basename of the git root + `-notes` suffix).
   - **Never write to the canonical `<project>` or `<project>-docs` groups.** Those are reserved for the indexer so the indexed corpus stays reproducible from source. Writing there silently mutates entity summaries via dedup and can invalidate file-derived edges via bi-temporal contradiction (the read-many / write-one rule).

3. **Choose `source`:**
   - `decision`, `bug`, `config` → `source="json"` with structured fields:
     - decision: `{decision, rationale, affected_components}`
     - bug: `{symptom, root_cause, fix_strategy, where_seen}`
     - config: `{key, value, scope, why_not_in_vcs}`
   - `pattern`, `preference`, `event` → `source="text"` with a clear paragraph.

4. **Check for contradictions before writing.** Run a quick `search_nodes` on the same keywords against the target group. If a prior episode contradicts the new one, write anyway *and* explicitly state in the new episode's body what is being superseded — Graphiti's bi-temporal layer will invalidate the old edge.

5. **Call `add_memory`** with a descriptive `name` (≤80 chars, includes the entity type) and the prepared `episode_body`. Then confirm to the user with the new episode's id and the group it landed in.

Don't write episodes for ephemeral state, anything derivable from `git log`, or anything already in CLAUDE.md.
