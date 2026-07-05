---
inclusion: manual
name: builder-reference
description: Scoped builder digests for convmem architecture, retrieval, and debugging.
---

# Builder reference

Read the relevant digest in `docs/builder-reference/` before making changes to
convmem architecture, retrieval, or debugging workflow.

## Tier A

- `ousterhout-builder-digest.md` for module boundaries and protocol surfaces
- `manning-builder-digest.md` for ranking, chunking, retrieval, and evaluation
- `zeller-builder-digest.md` for reproduction, triage, and verification
- `hard-parts-builder-digest.md` for trade-offs, data ownership, and split decisions
- `ddia-builder-digest.md` for ledger/Chroma ownership, watch stream, single-writer
- `arch-patterns-python-builder-digest.md` for repository, UoW, F1 refine queue
- `evolutionary-architectures-builder-digest.md` for fitness functions, thresholds, ownership

## Use

Prefer this steering file when the task is scoped to architecture or agent
behavior. Keep it separate from the main convmem protocol so the session ritual
stays lean.
