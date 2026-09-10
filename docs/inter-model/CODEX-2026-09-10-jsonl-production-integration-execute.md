# Implementation Handoff: Kiro JSONL Incremental Production Integration

**Arc:** Codex

**Date:** 2026-09-10

**Author:** Codex architecture lane

**For:** Cursor implementation lane

**Authorization:** Ryan, 2026-09-10, after Kiro's exact-tip PASS at `84ec51a`

---

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` — Execute authorized; implementation absent |
| **Reviewed plan base** | `84ec51a863256304a2ba1d3ef71050b9dabc3f3a` on `plan/2026-09-09-codex-jsonl-production-integration` |
| **Implementation branch** | Create `feat/2026-09-10-codex-jsonl-production-integration` from the pushed planning branch tip containing this handoff |
| **Push status** | Planning branch pushed; Cursor must push the explicit feature refspec immediately after every commit |
| **PR** | Not opened; Execute does not authorize PR creation |
| **Ryan GATE** | None for T0–T6; stop after pushed evidence for Kiro. Everything operational remains separately gated |
| **Track A ingest** | Do not run: this Execute explicitly prohibits `convmem index`, including session indexing |

## What to build

Implement the reviewed incremental state machine for the production Kiro JSONL
adapter behind an absent/false-by-default feature flag. Existing uncheckpointed
sources must refuse with `bootstrap_required`; crash replay must reuse durable
prepared outputs and converge or restore both real-Chroma collections and
followers without touching another source.

**Why this exists:** repeated indexing of an append-heavy Kiro transcript
currently retransforms stable history. This slice creates a disabled, reviewed
route that can later reduce model and embedding cost, but it does not activate
that route or spend against a live source.

## Normative specification and order

Read these before the first edit:

1. `docs/plans/STATUS-codex-jsonl-production-integration.md`
2. `docs/plans/ARCHITECTURE-codex-jsonl-production-integration.md`
3. `docs/plans/EXECUTION-codex-jsonl-production-integration.md`

The Architecture is normative. Execute T0–T6 in order. T0 is the first
executable gate and must pass before importing production modules in tests:
fresh tokenized temporary roots, resolved-path and symlink containment,
production-resource rejection, credential scrubbing, network/provider denial,
and crash-process/descendant containment. Stop if T0 cannot prove that boundary.

After T0:

1. add default-off configuration and exact Kiro eligibility;
2. add complete-prefix capture, adapter byte ranges, and versioned state;
3. split transform/build from commit and durably cache complete outputs;
4. add governed real-Chroma apply, source-scoped before-images, replay/rollback,
   unconditional incremental prune, and checkpoint-first follower
   reconciliation;
5. integrate the default-off ingest route and refresh canonical writer
   inventories; and
6. generate exact-tip VERIFY evidence and stop for Kiro.

If code reveals a concrete contradiction with the reviewed authority or lock
model, stop with the smallest reproduction. Do not redesign around it.

## Frozen scope

The exact `May change` list in the Execute plan is the file-scope grant. In
particular, it permits the new deep module, narrow Kiro adapter/ingest/config/
store seams, focused tests, canonical writer-inventory regeneration, VERIFY,
STATUS, LATEST, and the completion handoff.

Execute must not:

- edit live config or access production Chroma, processed state, exports,
  dedupe queues, locks, attestations, census, or source transcripts;
- run `convmem index`, `convmem add`, `convmem verify`, the golden evaluation,
  or any unscoped repository-wide suite that may read live corpus state;
- start, stop, reload, or invoke the watcher or another service;
- call local, network, or paid providers, open sockets, or use credentials;
- bootstrap, migrate, backfill, rebuild, purge, garbage-collect, roll back,
  canary, or activate production state;
- change retrieval, ranking, chunk parameters, prompts, model selection,
  unrelated adapters, query-side generation filtering, or parser-RSS scope;
- open or merge a PR; or
- weaken a failing gate to make evidence pass.

## Evidence and acceptance

The acceptance contract is A1–A12 in the Execute plan. The final evidence must
include:

- exhaustive both-side subprocess crashes for every declared durable
  transition, with coverage that fails when a side is missing;
- exact incremental/replay/rollback versus clean-rebuild authority comparisons;
- frontier-bounded summarize, distill, summary-embed, and unit-embed counters,
  including zero-call replay of durable prepared output;
- real Chroma only under temporary isolated roots and cross-source sentinels at
  every prune/rollback crash point;
- absent/false legacy parity, non-Kiro refusal, `bootstrap_required`, and
  explicit force/supersede refusal;
- processed/export/dedupe follower ordering and zero-call repair;
- focused compatibility, safe-reindex, watch, exclusion/lock, config, C3/R2b
  inventory/revision, and scratch regressions;
- compileall, Pylint, `git diff --check`, static scope audit, and process/open-
  file/path audit; and
- `docs/plans/VERIFY-codex-jsonl-production-integration.md` recording the exact
  tip, commands, counts, transition names, call counters, exclusions, limits,
  and any incidents.

## Stop and hand back

When T0–T6 pass, update the STATUS snapshot and LATEST, commit, push the explicit
feature refspec, and give Kiro the exact tip plus the VERIFY document. Do not
open a PR. Kiro must independently reproduce evidence and answer the seven
review questions in the Execute plan. Kiro PASS still does not enable the
feature; Ryan separately decides PR, merge, bootstrap/canary, and activation.

## Related files

| What | Path |
|---|---|
| Arc snapshot | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Reviewed architecture | `docs/plans/ARCHITECTURE-codex-jsonl-production-integration.md` |
| Authorized T0–T6 plan | `docs/plans/EXECUTION-codex-jsonl-production-integration.md` |
| Prior scratch evidence | `docs/inter-model/VERIFY-jsonl-incremental-scratch-prototype.md` |
| Prior live-source evidence | `docs/inter-model/VERIFY-jsonl-incremental-live-source-canary.md` |

## Picking up checklist

- [ ] Run the required ConvMem doctor/brief/unresolved orientation without
      indexing anything.
- [ ] Read STATUS, Architecture, Execute, and this handoff.
- [ ] Confirm the reviewed plan base is present in the new feature branch.
- [ ] State Goal / role / system state / next action and **Arc: Codex**.
- [ ] Run T0 first; stop on failure.
- [ ] Push every commit with an explicit refspec.
- [ ] Stop at pushed evidence for exact-tip Kiro review.

## TL;DR

- Ryan authorized Cursor to implement the reviewed default-off production
  slice through T0–T6 only.
- Execute is hermetic and evidence-only: no live data, indexing, providers,
  watcher action, PR, bootstrap, canary, migration, or activation.
- Cursor starts a feature branch from this pushed planning handoff, passes T0
  first, and stops after pushed VERIFY evidence for Kiro.
