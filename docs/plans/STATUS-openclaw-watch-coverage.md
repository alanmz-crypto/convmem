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
| Existing repository coverage | Only active `docs/inter-model/*.md` is directly indexable; ordinary plans/code/tests/schema/JS/TOML remain unsupported |
| OpenClaw T0–T5 design | Kiro-approved at `cd9d2698b7423f907b552bc9118a0af523018ca9`; separate arc and not Execute-authorized by this work |
| Watch architecture | Kiro PASS at exact plan `19dea97368408ee0b179c05c942306f6d8f1a2e8` |
| Watch execution plan | W0–W6 authorized by Ryan on 2026-09-21; implementation not started |
| Machine-readable inventory/schema | Missing; W0 implementation |
| Repository adapter/indexer/sync | Missing; W1–W3 implementation |
| Isolated E2E acceptance | Missing; W4 implementation |
| Live watch activation | Not authorized and not attempted |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Product scope and current-state audit | DONE in planning | — |
| Architecture and execution plan | KIRO PASS at `19dea97` | — |
| Kiro design review | PASS at `19dea97`; prior `4fe8662` FAIL blockers closed | PASS does not authorize Execute |
| Ryan Execute grant | AUTHORIZED 2026-09-21 for W0–W6 at `19dea97` | live activation excluded |
| W0–W6 implementation | NOT STARTED | Cursor implementation lane |
| Implementation verification | NOT STARTED | W0–W4 |
| Merge | NOT STARTED | review and Ryan |
| Required OpenClaw bytes in watched checkout | PARTIAL/MISSING | separate OpenClaw plan/implementation landing |
| Live activation | NOT AUTHORIZED | merged implementation + exact external-change grant |
| `WATCH_COVERAGE=PASS` | BLOCKED | all preceding gates |

## 5. Your Role

**If Ryan sent you to review planning:** inspect the exact branch tip against
the user requirement and the Kiro-approved OpenClaw plan. Verify the manifest,
Git-clean byte authority, parser bounds, updates/retirement, exclusions,
provenance, non-bypass acceptance, and strict separation from T0–T5 and live
activation. Return PASS or FAIL; do not implement.

**If Ryan sent you to implement:** the grant is active for W0–W6 against
`19dea97368408ee0b179c05c942306f6d8f1a2e8`. Implement only the execution
allowlist. Do not change OpenClaw T0–T5, live config, or the watch service.

**If Ryan sent you to activate:** require exact manifest path, config value,
service, resource limits, pre-state/rollback, and retrieval needles. Back up
config and do not touch OpenClaw user data or authority state.

## 6. What Remains Before Live Coverage

1. Cursor implements W0–W6 from the bounded Execute handoff and produces
   focused acceptance evidence.
2. The final implementation tip receives focused review and acceptance.
3. Ryan decides PR creation and merge.
4. Approved OpenClaw planning/implementation bytes land in the watched checkout
   and the exact manifest is updated in the same reviewed commits.
5. Ryan grants the exact live config edit and service restart.
6. Startup sync, retrieval needles, exclusion controls, and governance
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

**TL;DR [Arc OpenClaw Watch Coverage]:** Ryan authorized Cursor to implement
and test W0–W6 against Kiro-reviewed `19dea97`. Live configuration, restart,
activation, merge, and `WATCH_COVERAGE=PASS` remain separately gated, with
OpenClaw T0–T5 strictly separate.
