# [Arc Claude Watch Parity] Boundary Architecture Review Handoff

**For:** Kiro

**Lane:** design review only

**Implementation/live authority:** none

## Review target

Review the exact pushed tip of `plan/2026-09-20-claude-watch-parity-boundary`.

Primary files:

- `docs/plans/ARCHITECTURE-claude-watch-parity.md`
- `docs/plans/EXECUTION-claude-watch-parity-boundary.md`
- `docs/plans/STATUS-claude-watch-parity.md`

## Decision

The plan chooses a descriptor-bound bubblewrap namespace for Gate 2 finding #2.
The existing coordinator runs unchanged at `/canary-root`; the launcher passes
the already-open scratch root and exact source via bubblewrap fd-bind options.
Shared-code authority changes are rejected for this slice because they would
touch the production Chroma writer and `convmem.py add` path.

Cursor's five local corrections are separately pushed at
`e007a22b24754a93d9cbd15d02269d422d371c4a`; they are
inputs, not accepted evidence. Gate 2 still has no PASS.

## Review questions

1. Does `--bind-fd` provide the right authority boundary for root replacement
   without persisting fd paths?
2. Is the filesystem/environment allowlist narrow enough?
3. Are host Gate 0 and worker namespace checks placed correctly?
4. Is bubblewrap 0.12.0+ a reasonable host prerequisite for this optional
   canary?
5. Are the regression matrix and `NO_GATE2_ROUTE` exit sufficient?
6. Does the plan preserve Kiro/Codex/shared-writer behavior by leaving shared
   runtime files untouched?

Return PASS or specific blocking corrections on the full exact SHA. Review
grants no implementation, PR, live source, canary, routing, watcher, or
activation action.

**TL;DR [Arc Claude Watch Parity]:** Review the namespace architecture only;
Gate 2 remains closed and shared runtime code remains unchanged.
