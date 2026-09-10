# Review Handoff: Arc Codex Kiro JSONL Production Canary — consolidated

**Date:** 2026-09-10
**Author:** Kiro (design/verification lane)
**For:** Codex (plan owner) → Ryan (P1 authorization decision)
**Authorization:** Ryan, 2026-09-10 — bounded design review of the canary plan
(review-only; Kiro is non-implementing)

> **Arc: Codex.** This is a *review* handoff, not an implementation brief. Kiro
> made **no code or plan edits** this session — every action was read-only
> verification. The one artifact Kiro authored is this handoff document.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `BLOCKED_ON_RYAN` — design review closed PASS; P1 harness Execute not yet authorized |
| **Branch** | `plan/2026-09-10-codex-jsonl-production-canary` |
| **Tip SHA** | `8b48a39a0c843db58f5cd8e1b958ba3ef4824181` (plan + all 3 corrections) |
| **Push status** | pushed to origin |
| **PR** | not opened (planning branch; PR is Ryan-gated) |
| **Ryan GATE** | Ryan decides whether to authorize hermetic **P1** Cursor Execute. **P2** additionally needs the dedicated session grown to 61–109 accepted messages + a separate grant digest. |
| **Merged prerequisite** | Incremental JSONL feature is on `main` via PR #293 (`881133d`) + #294, **disabled by default** |

---

## What this covers (the whole review arc, consolidated)

This single document replaces the need to trace the chat. It records the
original plan, every Kiro verdict, the exact corrections, and the read-only
environment findings — so Codex/Ryan can act without reconstruction.

### 1. Original plan (Codex-authored)

Two documents on the canary branch:
- [`ARCHITECTURE-codex-jsonl-production-canary.md`](../plans/ARCHITECTURE-codex-jsonl-production-canary.md)
- [`EXECUTION-codex-jsonl-production-canary.md`](../plans/EXECUTION-codex-jsonl-production-canary.md)

Design intent: a **two-grant** canary — P1 builds a *separate one-shot,
exact-resource canary boundary* (hermetic, temporary roots only); P2 later runs
it **once** against one new Kiro source under a fresh Ryan-approved grant digest.
It deliberately does **not** widen the existing scratch `IsolationBoundary`.

### 2. Kiro verdict history

| Tip | Verdict | Summary |
|-----|---------|---------|
| `95f1523` | **PASS_WITH_CORRECTIONS** | Design sound; 3 corrections (1 code-precision, 2 minor). |
| `8b48a39` | **PASS (review closed)** | All 3 corrections verified accurate; docs-only delta, no design change. |

### 3. The three corrections (all applied at `8b48a39`, all verified)

- **C1 — append boundary off-by-one (code-verified, load-bearing).**
  Original said "below 110 / crosses 110." Kiro recomputed against the actual
  `chunk_messages` loop (`ingest.py:211`, `step = size - overlap = 50`, break
  when `i + size >= n`):

  | N (accepted messages) | chunks | starts |
  |---|---|---|
  | 60 | 1 | 0 |
  | 61–109 | 2 | 0, 50 |
  | **110** | **2** | **0, 50** |
  | 111 | 3 | 0, 50, 100 |

  So **N=110 is still a valid two-chunk append state**; the third chunk (start
  100) first appears at **N ≥ 111**. Fixed in all four sites (Arch §8, Exec
  P1-T7, P2-T4, P2-A5). The **61–109 baseline window is correct and unchanged.**

- **C2 — embed model tag.** Original asserted `nomic-embed-text:latest` as the
  config value; config actually stores `nomic-embed-text` (no tag). Corrected to
  "canonicalize the configured alias to the exact installed tag (expected
  `nomic-embed-text:latest`) and pin the digest in the grant." **Verified
  against reality:** the installed tag *is* `nomic-embed-text:latest`, digest
  `0a109f422b47`.

- **C3 — jargon glossary.** The `plan-jargon-glossary` steering requires a
  `## Jargon TL;DR` at the end of `docs/plans/*` docs. Both plans now carry one.
  (Noted as a not-yet-repo-enforced convention when first flagged, not a
  blocker; applied anyway.)

### 4. Seven review questions — all answered satisfactorily

1. Separate boundary **preserves** (does not weaken) the scratch isolation
   contract. ✓
2. A dedicated runner outside `convmem index` is the right way to keep watcher
   activation impossible (Gate-0 proves inactive by 3 methods). ✓
3. Exact-resource grant + source-scoped rollback capsule + one-shot nonce are
   sufficient authority boundaries. ✓ (underlying source-scoped Chroma
   primitives verified genuinely single-source).
4. 61–109 is the correct baseline window; append boundary corrected via C1. ✓
5. Five selected faults add real storage-seam evidence without repeating the
   44-transition hermetic matrix. ✓
6. Call ceilings are conservative and fail-closed **before** spend (in-process
   counter guard, not post-run tally). ✓ (`deepseek-v4-flash` paid-provider
   risk confirmed real → credential-scrub + loopback-only correctly motivated).
7. Mixed-visibility pass condition is honest and defers activation SLOs. ✓
   (`ServingIndexRepository` verified present).

---

## Environment readiness (read-only Gate-0 pre-checks, 2026-09-10)

| Gate-0 item | State | Detail |
|---|---|---|
| #9 local models installed | ✅ ready | `llama3.1:8b` (`46e0c10c039e`), `nomic-embed-text:latest` (`0a109f422b47`) — present with digests; **no pull needed** |
| Default-off invariant | ✅ holds | `[index.incremental_jsonl]` table **absent** from `~/.config/convmem/config.toml` → true no-op; confirms #293/#294 landed disabled |
| #6 watcher inactive | ✅ inactive | `systemctl --user is-active convmem-watch.service` → `inactive`; no real watcher process |
| **P2-T0 session size** | ❌ **blocks P2** | Dedicated session `sess_2628159e…` = **16 accepted** (1 user + 15 assistant) despite 57 raw lines. Needs **45 more accepted** (~22–23 benign exchanges) to reach the 61 floor. **No growth since the `95f1523` freeze.** |

### P1 dependency pre-check — clean (P1 is purely additive)

Every primitive the hermetic P1 harness builds against already exists on
`origin/main`, so **no prerequisite refactor** is needed:

- Source-scoped rollback: `chroma_store.py` `snapshot_source_rows` (656),
  `restore_source_rows` (690), `delete_units_for_source` (504),
  `delete_summaries_for_source` (634) — all `where={"source_path": …}` scoped.
- Isolation guard: `incremental_jsonl_isolation.py` `known_production_roots`
  (79), `IsolationBoundary` (251), `resolve_mutable` (309),
  `require_fake_provider` (332).
- Serving probe: `serving_index_repository.py` `ServingIndexRepository` (59).
- Default-off route: `incremental_jsonl.py` `maybe_route_incremental` (1372),
  `ELIGIBLE_FORMAT = "jsonl_kiro_session"` (42).
- Fault mapping: `DURABLE_TRANSITIONS` (56), 22 named transitions present.

### P1-A9 fault mapping — pre-verified coherent

| Plan fault (Arch §9 / P1-T5) | Durable-transition seam |
|---|---|
| 1. summary committed, unit not | `summary_upsert` → `unit_upsert` |
| 2. unit committed, prune incomplete | `unit_upsert` → `summaries_prune`/`units_prune` |
| 3. prune complete, checkpoint not published | `units_prune` → `checkpoint_publish` |
| 4. checkpoint published, follower incomplete | `checkpoint_publish` → `export_reconcile`/`dedupe_reconcile` |
| 5. followers published, processed not committed | `dedupe_reconcile` → `processed_publish` |

All five land on real named seams — P1-A9 is satisfiable as written.

---

## Two implementer notes for Codex/Cursor (Gate-0 semantics, not plan defects)

1. **Gate-0 #6 error-vs-inactive.** `systemctl --user is-active` exits
   **non-zero** when a unit is inactive — that is normal. The preflight must
   treat literal `inactive` stdout as a **confirmed negative (pass)**, and
   reserve the "unknown/error = failure" rule for cases where state genuinely
   cannot be determined (systemd unreachable, ambiguous output). Do not misread
   a non-zero exit on `inactive` as an error-failure. The plan's three-method
   requirement already covers this — just wire the exit-code handling correctly.
2. **C2 pin.** The grant should pin embed model digest `0a109f422b47`
   (`nomic-embed-text:latest`) and summarize/distill fallback `46e0c10c039e`
   (`llama3.1:8b`) — both confirmed installed.

---

## What NOT to do (scope firewall — unchanged from plan)

- Do not enable persistent config, start/install the watcher, add the canary to
  `convmem index`, use a paid/nonlocal provider, pull models, index another
  source, migrate/rebuild a legacy source, or continue from evidence to
  activation.
- Do not widen or bypass `IsolationBoundary` to accept production roots.
- P1 stops at pushed hermetic evidence for Kiro exact-tip review. PR is
  Ryan-gated. P2 does not exist merely because P1 merges.

---

## Next actions (ordered)

1. **Ryan:** decide whether to authorize hermetic **P1** Cursor Execute
   (P1-T0…T8, acceptance P1-A1…A14). PASS on the plan does **not** auto-authorize.
2. **Ryan/anyone:** grow the dedicated Kiro session `sess_2628159e…` via
   ordinary benign conversation to **61–109 accepted messages** (needs ~45 more
   accepted / ~22–23 exchanges), then stop using it and freeze fresh
   source+metadata identity for the P2 grant.
3. **Cursor (on P1 grant):** build the canary boundary + launcher + tests
   hermetically; push an exact tip.
4. **Kiro:** exact-tip P1 review (rerun the hermetic matrix; confirm the
   isolation guard stays production-denying, default-off route unchanged,
   `watch.py` untouched).
5. **Ryan:** after P1 merges + Kiro P1 PASS + session ready → approve the exact
   P2 grant digest for one live run.

---

## Related files

| What | Path |
|------|------|
| Architecture (corrected) | `docs/plans/ARCHITECTURE-codex-jsonl-production-canary.md` |
| Execution plan (corrected) | `docs/plans/EXECUTION-codex-jsonl-production-canary.md` |
| Integration STATUS | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Prior integration review | `docs/inter-model/CURSOR-2026-09-10-jsonl-production-integration-review.md` |
| Routing pointer | `docs/inter-model/LATEST.md` |

---

## TL;DR

- **[Arc Codex]** Canary **design review is closed PASS at `8b48a39`.** All three
  Kiro corrections (C1 append off-by-one, C2 embed-tag, C3 glossary) applied and
  verified; delta was docs-only, no design change.
- **Environment is P1-ready:** models installed with digests, config default-off,
  watcher inactive, and every P1 harness dependency already exists on `main`
  (additive build). Fault mapping P1-A9 pre-verified.
- **P2 is blocked on session growth:** dedicated session sits at **16/61**
  accepted messages — needs ~45 more.
- **Gates:** P1 Cursor Execute is Ryan's next decision; P2 needs session growth +
  a separate grant digest. Kiro made no code changes — review lane only.
