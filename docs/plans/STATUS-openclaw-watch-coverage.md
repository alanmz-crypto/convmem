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
| Existing `convmem watch` | Enabled and active as `convmem-watch.service`; runs from the dedicated clean `main` worktree at `dc79eeb` with effective limits `MemoryMax=4G`, `MemoryHigh=3G`, `MemorySwapMax=0` |
| Repository-knowledge coverage (W0–W6 corrective) | Merged on `main` by GitHub PR `#322` at `dc79eeb`: root-bound IDs, exact JSON source spans, lossless bounded windows, identity-aware and retry-idempotent reconciliation/retirement, real watchdog/subprocess/public-query E2E |
| Manifest inventory | The current manifest classifies the five reviewed OpenClaw planning files added by PR `#327`, classifies the two opt-in guardrail and two circuit-breaker test files outside W0 as unrelated, removes three unrelated classifications retired by PR `#330`, and carries current hashes for all admitted files changed through PR `#328`; Git-clean audit PASS is restored at 75 include / 169 exclude / 1227 unrelated / 68 `required_when_present` (2 present, 66 absent) / 0 unclassified across 1471 tracked paths |
| Live configuration | `watch.repository_knowledge_manifests` points to the manifest in `/home/lauer/Projects/convmem/.worktrees/runtime-main`; rollback backups were captured before activation |
| OpenClaw planning bytes | Architecture, execution, milestone overlay, README, and STATUS are on `main` through PR `#327`; this closure admits them as documentary repository knowledge. The separate partial implementation branch remains unaccepted and is not admitted |
| Writer-coverage inventory | Ryan-authorized correction complete; 18 routes inventoried and A12 passes |
| Live watch activation | PASS at the deployed `dc79eeb` boundary: startup reconciliation indexed all 70 then-admitted paths into 1,115 units; vector retrieval returned the architecture; excluded-path hits are zero; governance/authority hashes are unchanged. The runtime worktree has not been advanced to later `main` commits |
| Post-activation soak | The first systemd run lasted 2d 14h 49m with a 1.8 GiB peak and no service failure. A clean local `systemctl` stop ended it on 2026-09-24 at 04:34 CDT while Switchboard verification was active; after that lane finished, the already-authorized unit was enabled and restarted at 05:14 CDT from the unchanged `dc79eeb` runtime. Post-restart debounce/reconciliation completed with no warning or restart and a roughly 470 MiB peak. This does not close the separate watch-OOM risk |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Product scope and current-state audit | DONE in planning | — |
| Architecture and execution plan | KIRO PASS at `19dea97` | — |
| Kiro design review | PASS at `19dea97` | — |
| Ryan Execute grant | AUTHORIZED 2026-09-21 for W0–W6 at `19dea97` | live activation excluded |
| W0–W6 implementation | MERGED / PASS at `dc79eeb` | — |
| Isolated A1–A11 | PASS | — |
| A12 writer scan | PASS | Ryan authorized the inventory/count correction |
| Final targeted Bugbot review | PASS at `324ab17` | no remaining findings |
| GitHub PR | MERGED as `#322` | — |
| Reviewed OpenClaw planning bytes | PRESENT and classified in the current manifest | live runtime promotion remains separate |
| OpenClaw T0–T5 implementation bytes | PARTIAL / UNACCEPTED on a separate branch | separate OpenClaw Execute and acceptance gates |
| Live activation | PASS | — |
| `WATCH_COVERAGE=PASS` | BLOCKED | 66 required-when-present implementation/Gate W paths remain absent; deployed runtime is intentionally still at `dc79eeb` |

## 5. Your Role

**If Ryan sent you after this closure:** preserve the clean runtime worktree and
live service configuration. Do not fast-forward the runtime worktree merely
because repository `main` advanced: the manifest and every newly admitted file
must first pass together in one reviewed clean commit, followed by a separately
authorized runtime promotion and retrieval/exclusion check. The next code work
belongs to the separate OpenClaw T0–T5 arc.

## 6. What Remains Before Live Coverage

1. Any promotion of the dedicated runtime worktree beyond `dc79eeb` receives a
   separate exact authorization and repeats manifest, retrieval, exclusion,
   service-health, and governance checks.
2. Approved OpenClaw T0–T5 implementation bytes complete their separate
   Execute and acceptance gates and land with matching manifest entries/hashes
   in the same reviewed commit.
3. The runtime worktree advances to that accepted merge and the live watcher
   reconciles it; only then may the remaining coverage verdict be reconsidered.

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
| 2026-09-21 | Bugbot / Codex | Final targeted Bugbot review PASS at `324ab17`; GitHub PR `#322` opened for Ryan-owned merge. |
| 2026-09-21 | Ryan / Codex | PR `#322` merged at `dc79eeb`; exact-grant live activation indexed all 70 admitted paths, passed retrieval/exclusion/non-bypass checks, and left only absent OpenClaw T0–T5 bytes blocking complete coverage. |
| 2026-09-24 | Codex | Post-activation review kept the manifest exact across PRs `#327`–`#330`, restored the cleanly stopped service after Switchboard verification finished, and documented the separate merge, runtime-promotion, and T0–T5 gates. |

**TL;DR [Arc OpenClaw Watch Coverage]:** W0–W6 is merged and live at the
deployed `dc79eeb` boundary. This closure classifies the five later reviewed
OpenClaw planning files without advancing production. Full coverage remains
blocked on accepted T0–T5 bytes, matching manifest hashes, and a separately
authorized runtime promotion.
