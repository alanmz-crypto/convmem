# [Arc Codex] Kiro JSONL Production-Integration Plan Review

**Date:** 2026-09-09

**Author:** Codex architecture/planning lane

**For:** Kiro design-review lane

**Authorization:** Ryan, 2026-09-09 — author a bounded production-integration
architecture and Execute plan; stop before Cursor implementation

---

## Resume state

| Field | Value |
|---|---|
| **State** | `BLOCKED_ON_KIRO_REVIEW` |
| **Branch** | `plan/2026-09-09-codex-jsonl-production-integration` |
| **Tip SHA** | Use the pushed branch tip and report the exact reviewed SHA |
| **Push status** | Pushed to `origin` after every commit |
| **PR** | Not opened; Ryan has not authorized a PR |
| **Ryan GATE** | Kiro reviews the plan; Ryan separately accepts it and grants Cursor Execute |
| **Track A ingest** | Intentionally not run: the current planning grant explicitly prohibits live indexing |

## What to review

Codex designed the production bridge from the reviewed scratch/live-source
prototype to the existing Kiro ingest path. The proposed outcome is incremental
reuse and zero-repeat-call crash replay behind a default-off feature flag,
without enabling production or changing chunking/retrieval behavior.

Start with:

1. [`ARCHITECTURE-codex-jsonl-production-integration.md`](../plans/ARCHITECTURE-codex-jsonl-production-integration.md)
2. [`EXECUTION-codex-jsonl-production-integration.md`](../plans/EXECUTION-codex-jsonl-production-integration.md)
3. [`STATUS-codex-jsonl-production-integration.md`](../plans/STATUS-codex-jsonl-production-integration.md)

The merged supporting evidence is:

- [`VERIFY-jsonl-incremental-scratch-prototype.md`](VERIFY-jsonl-incremental-scratch-prototype.md)
- [`VERIFY-jsonl-incremental-live-source-canary.md`](VERIFY-jsonl-incremental-live-source-canary.md)

## Chosen architecture

- Integrate at `ingest._index_one_file`, after normal format detection and
  exclusion checks. Manual and watcher routes stay unified.
- Missing/false configuration keeps the legacy whole-file path. Exact Kiro
  JSONL is the only eligible v1 adapter.
- Lift the reviewed source-prefix, continuity, frontier, generation, checkpoint,
  and replay rules into a production module; do not import the scratch package.
- Add a durable content-addressed prepared-output cache before any Chroma write,
  preventing repeated summarize/distill/embed cost after a crash.
- Add a source-scoped exact before-image journal around both Chroma collections.
  A torn apply rolls forward from prepared outputs or rolls back to the prior
  checkpoint manifest.
- Publish checkpoint authority before reconciling units export, dedupe events,
  and `processed.json`; publish `processed.json` last.
- Refuse already-indexed sources without checkpoints as `bootstrap_required`.
  No silent rebuild or model spending.
- Keep full fallback separately default-off; mutation, rotation, truncation, or
  fingerprint drift returns `rebuild_required` unless a later operation/cost
  grant enables it.

## Questions for Kiro

Issue a written `PASS`, `PASS_WITH_CORRECTIONS`, or `FAIL` at the exact branch
tip. Please independently answer:

1. Is the checkpoint/transaction/prepared-cache/before-image authority split
   coherent for real Chroma?
2. Can a torn summary/unit/prune operation always roll forward or restore the
   exact prior source projection without touching another source?
3. Is checkpoint-before-followers and `processed.json`-last the right ordering?
4. Does default-off parity plus `bootstrap_required` prevent accidental spend
   and adoption of unverifiable legacy rows?
5. Is the mixed-read window disclosed honestly enough, and is deferring query-
   side generation filtering acceptable for this first disabled slice?
6. Does the Execute plan test every durable transition, zero-call replay,
   clean-rebuild equality, writer coverage, and live-path isolation?
7. Is any requirement internally contradictory with the current lock order,
   writer session, Shadow mutation history, or source exclusion behavior?

If a correction is required, cite the smallest exact section and expected
replacement. Do not implement code, run live indexing, activate the watcher,
or invoke providers.

## Scope boundary

This planning branch may contain only Architecture, Execute, STATUS, routing,
and review-handoff documentation. It does not authorize Cursor, a PR, live
configuration, a source bootstrap, a canary, migration, providers, indexing,
watcher/service actions, or activation.

## What happens after review

- Kiro PASS → Ryan decides whether to accept and issue a separate bounded
  Cursor Execute grant.
- Corrective verdict → Codex revises planning only and returns a new exact tip.
- FAIL → stop; no implementation.

## TL;DR

- Arc Codex planning is ready for independent Kiro review at the pushed branch
  tip.
- The plan adds default-off Kiro-only routing, durable transform reuse, and
  checkpoint-governed real-Chroma replay/rollback.
- Nothing operational is authorized; Kiro reviews, then Ryan decides whether
  Cursor may implement.
