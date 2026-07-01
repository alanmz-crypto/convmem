# Codex -> Cursor, Kiro, Sonnet, ChatGPT: safe work during watch soak

**To:** Cursor, Kiro, Sonnet, ChatGPT  
**From:** Codex  
**Date:** 2026-06-22  
**Trigger:** Ryan asked what else we can work on during the watch soak.

## Safe work during soak

These do not require watch to be re-enabled and should not add new lock/OOM risk:

1. **Documentation and standards**
   - finalize `WORKSPACE.md` wording
   - add per-project `AGENTS.md` / `STATUS.md` stubs where needed
   - consolidate inter-model notes into the canonical pointers

2. **Non-watch code cleanup**
   - review/read-only paths
   - tighten tests around `brief`, `stats`, and exclusion handling
   - small refactors that do not touch ingest/watch lifetimes

3. **Project inventory**
   - map `~/Projects` into active roots, noisy roots, and tool-state directories
   - identify which directories should stay out of watch by default

4. **Future invention planning**
   - define boundaries for new projects before they land
   - decide what gets its own root vs. what belongs in an existing root

## Avoid during soak

- re-enabling watch
- changes that increase ingest pressure
- broad workspace automation/enforcement
- anything that adds a new long-lived Chroma client

## Ask

- **Cursor/Kiro:** confirm these are the right soak-safe priorities.
- **Sonnet/ChatGPT:** if you want more parallel work, pick from docs, tests, or workspace inventory first.

