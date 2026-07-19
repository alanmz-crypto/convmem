# Builder reference (on-demand)

Read digests from `~/.config/crush/builder-reference/` (or repo
`docs/builder-reference/`) when touching:

- module boundaries, CLI surfaces, or MCP handlers
- ranking, chunking, or evaluation behavior
- triage, reproduction, or verification flow
- service splits, data ownership, ingest/watch boundaries
- automated checks, fitness functions, or threshold gates

Do **not** load these for routine reversible work (docs, tests, small
refactors). Digests are on-demand — they are not standing Crush context.
