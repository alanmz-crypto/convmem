# Arc Brief — OpenClaw Watch Coverage

> **Every model working on this arc must read this file at session start.**

## 1. What This Is For

ConvMem must automatically retain safe repository knowledge needed to
understand, maintain, test, and repair the ConvMem + OpenClaw integration. A
future agent should retrieve that knowledge without Ryan manually supplying
the right folders.

**Done means:** an exact reviewed inventory covers every required current file;
clean committed eligible bytes become retrievable through ConvMem watch and
normal indexing; excluded material remains unavailable; proposal, approval,
provenance, and durable-ingestion controls remain intact; and safe live
activation evidence passes under a separate grant.

## 2. System Design

```text
reviewed Git commit
  ├─ exact file bytes
  └─ hash-pinned scope manifest
          │
          ▼
  scope + Git-clean validation ── reject exclusions/unlisted/dirty bytes
          │
          ▼
  repository content chunker (never executes or summarizes with an LLM)
          │
          ▼
  convmem index --file child
          │
          ▼
  normal provenance + writer + processed/source replacement
          │
          ▼
  normal ConvMem retrieval

proposal / approval / authority / capture / publication surfaces
          └──────────── byte-identical before and after ────────────┘
```

Key invariants: closed exact-file inventory; exclusions win; Git-clean hashes;
documentary claimed provenance only; source-scoped replacement; inert
decision-shaped text; no live OpenClaw profile/data/config; no T0–T5 change.

## 3. What Exists Right Now

| Surface | State |
|---|---|
| Existing `convmem watch` | On `main`; recursive observer, debounce, normal `index --file` child, existing memory/timeout containment |
| Repository-knowledge coverage (W0–W6 corrective) | Implemented on `fix/2026-09-21-openclaw-watch-coverage-refinement`: root-bound IDs, exact JSON source spans, lossless bounded windows, identity-aware and retry-idempotent reconciliation/retirement, real watchdog/subprocess/public-query E2E |
| Manifest inventory | Git-clean audit PASS: 70 include / 169 exclude / 1226 unrelated / 68 `required_when_present` / 0 unclassified across 1465 tracked paths |
| Example config | Commented `watch.repository_knowledge_manifests` only; live config untouched |
| OpenClaw T0–T5 design | Kiro-approved at `cd9d2698b7423f907b552bc9118a0af523018ca9`; still absent; listed as `required_when_present` |
| Writer-coverage inventory | Ryan-authorized correction complete; 18 routes inventoried and A12 passes |
| Live watch activation | Not authorized and not attempted |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Product scope and current-state audit | DONE in planning | — |
| Architecture and execution plan | KIRO PASS at `19dea97` | — |
| Kiro design review | PASS at `19dea97` | — |
| Ryan Execute grant | AUTHORIZED 2026-09-21 for W0–W6 at `19dea97` | live activation excluded |
| W0–W6 implementation | PASS ON CORRECTIVE BRANCH | final review required |
| Isolated A1–A11 | PASS | — |
| A12 writer scan | PASS | Ryan authorized the inventory/count correction |
| Merge | NOT STARTED | review and Ryan; do not open a PR from this lane |
| Required OpenClaw bytes in watched checkout | MISSING | separate OpenClaw plan/implementation landing |
| Live activation | NOT AUTHORIZED | merged implementation + exact external-change grant |
| `WATCH_COVERAGE=PASS` | BLOCKED | review + merge + OpenClaw bytes + live grant |

## 5. Your Role

**If Ryan sent you to review this implementation:** inspect the corrective
branch tip against Kiro-reviewed `19dea97`. Confirm Git-clean authority,
root-bound documentary identity, exact JSON source preservation, real watcher
subprocess/public-query evidence, identity-safe retirement, and A1–A12.
Return PASS or FAIL; do not implement, merge, or activate.

**If Ryan sent you to activate:** refuse unless a later grant names the exact
manifest path, config value, service, limits, pre-state, and rollback.

## 6. What Remains Before Live Coverage

1. Focused review of the corrective implementation tip.
2. Ryan decides PR creation and merge. Do not open a PR from this lane.
3. Approved OpenClaw planning/implementation bytes land in the watched checkout
   and the exact manifest is updated in the same reviewed commits.
4. Ryan grants the exact live config edit and service restart.
5. Startup sync, retrieval needles, exclusion controls, and governance
   before/after hashes pass; then `WATCH_COVERAGE=PASS`.

## 7. Hard Stops

- No implementation before Kiro PASS and Ryan's exact Execute grant.
- No live config, watcher restart, or live corpus mutation under W0–W6.
- No OpenClaw reader/runtime/connector implementation in this arc.
- No broad repository parser, suffix admission, dirty/untracked bytes, or
  weakening of an exclusion.
- No real secret, authority record, corpus, database, OpenClaw profile,
  workspace, memory, or transcript in fixtures or tests.
- No claim of coverage from observer attachment without retrieval evidence.
- No authority/proposal/approval/admission/capture/publication mutation.

## 8. Relationship to ConvMem and OpenClaw

This arc supplies the maintenance-knowledge plane. The separately approved
OpenClaw T0–T5 plan supplies a disposable reader/runtime fixture. Later live
runtime and promotion gates remain separate. Watch coverage can be implemented
without T0–T5, but final coverage stays blocked until the required current
OpenClaw files exist in the watched checkout and are indexed.

## 9. Key Files

| Purpose | Path |
|---|---|
| Architecture | `docs/plans/ARCHITECTURE-openclaw-watch-coverage.md` |
| Execution | `docs/plans/EXECUTION-openclaw-watch-coverage.md` |
| Arc status | `docs/plans/STATUS-openclaw-watch-coverage.md` |
| Later verification | `docs/plans/VERIFY-openclaw-watch-coverage.md` |
| Frozen OpenClaw architecture | `cd9d2698:docs/plans/ARCHITECTURE-openclaw-convmem-integration.md` |
| Frozen OpenClaw execution | `cd9d2698:docs/plans/EXECUTION-openclaw-convmem-integration.md` |

## 10. Update Protocol

Keep this file a current-state snapshot. Overwrite sections 3–6 after review,
implementation, merge, or activation. Do not append session narrative. Add one
milestone-level line below. A fresh model should orient from this file alone.

## Update Log

| Date | Who | Change |
|---|---|---|
| 2026-09-21 | Codex | Created the watch-only arc brief and draft W0–W6 planning boundary. |
| 2026-09-21 | Kiro / Codex | Exact-tip `4fe8662` review found two blockers; corrective removes the Gate W file overlap and freezes root-aware routing for re-review. |
| 2026-09-21 | Kiro | Exact-tip `19dea97` corrective re-review PASS; both blockers closed without regression; Execute remains Ryan-gated. |
| 2026-09-21 | Ryan / Codex | Ryan authorized bounded W0–W6 implementation at Kiro-reviewed `19dea97`; live activation remains separately gated. |
| 2026-09-21 | Cursor | Allowlisted W0–W6 implemented on `feat/2026-09-21-openclaw-watch-coverage`; isolated A1–A11 PASS; A12 blocked on off-allowlist writer inventory; live watch not activated. |
| 2026-09-21 | Codex | Corrective implementation closed six review defects plus identity-transition ingest; real watcher E2E and A1–A12 pass; review remains required and live watch remains off. |
| 2026-09-21 | Codex | Targeted Bugbot follow-up found two residual defects; lossless aggregate windows and retry-idempotent retirement now have direct regressions. |

**TL;DR [Arc OpenClaw Watch Coverage]:** Corrected W0–W6 passes A1–A12 and the
focused regression suite on the corrective branch. Review, merge, required
OpenClaw bytes, and an exact live-activation grant still gate
`WATCH_COVERAGE=PASS`; live watch remains off.
