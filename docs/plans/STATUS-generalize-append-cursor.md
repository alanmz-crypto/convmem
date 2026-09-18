# Arc Brief — Generalize the Append Cursor

> **Arc: Codex.** Current-state snapshot for the stopped Copilot format extension.
> This plan is independent of the still-gated Arc Codex P2 canary and does not
> grant production use.

## 1. What This Is For (product goal)

ConvMem should avoid paying to transform unchanged transcript history after
small appends, while preserving full source coverage, exact replay, and
governed projection writes. The conditional Copilot `events.jsonl` extension
tested whether the landed incremental coordinator could safely serve one more
JSONL format. Kiro PASSed the plan at `9e2d0ef` and its post-#286-merge
reconciliation at `53e7b42`. The granted local writer trace then showed a new
inode on every action. The merged coordinator refuses reuse on that change.
After Kiro's evidence recheck, Ryan chose **`NO_COPILOT_ROUTE` under the
current contract** on 2026-09-18. This closes the Copilot proposal, not the
shared scanner or the separately gated Arc Codex production work.

## 2. System Design (how the pieces connect)

```text
exact detected JSONL format + normal parser identity
                    |
          closed capability registry
                    |
       format-specific complete-prefix view
                    |
      existing incremental coordinator
      source/sidecar continuity + overlap frontier
      durable prepared cache + rollback journal
                    |
          governed writer/pruner
                    |
       checkpoint, then derived followers
```

Source bytes and parse-relevant sidecars are input authority. The checkpoint
is processing/recovery authority. Chroma and processed/export/dedupe files
are followers. A complete selected prefix may gain a pure append; it may not
be rewritten, truncated, replaced, or semantically changed before commit.
Unknown formats remain on the legacy path or refuse. Eligibility is a
reviewed code capability, never a broad user-config format list.

## 3. What Exists Right Now (file map)

| Surface | Current state |
|---|---|
| `incremental_jsonl.py` | On `main` through PR #307; default-off, format-specific coordinator and replay. Normal production route remains Kiro-only; isolated Codex routes require `CONVMEM_INCREMENTAL_ROOT`. |
| `incremental_jsonl_formats.py` | On `main`; closed Kiro/Codex capability registry with version, parser module, snapshot, and optional sidecar path. No Copilot entry. |
| `adapters/jsonl_prefix.py` | On `main`; complete-line scanner, byte ranges, outcomes, and `CompletePrefixView`. |
| `adapters/kiro_session_jsonl.py` | Existing `parse_complete_prefix()` provider and compatibility oracle. |
| `adapters/jsonl_io.py` | Common whole-file legacy JSONL iterator; scanner lives in `jsonl_prefix.py`. |
| `adapters/copilot_session_jsonl.py` | Whole-file parser with `workspace.yaml` and `session.start` metadata; no prefix capability or proven writer contract. |
| Codex rollout, history, Cursor adapters | Codex history/rollout complete-prefix adapters and fresh isolated route landed via PR #307. Rolling production history remains excluded; Cursor writer contract is unknown. |
| `ARCHITECTURE-generalize-append-cursor.md` | Original Kiro PASS at `9e2d0ef`; Kiro targeted PASS at post-merge plan tip `53e7b42`. |
| `EXECUTION-generalize-append-cursor.md` | Reviewed historical proposal; its E0 gate did not pass and E1–E4 are not authorized. |
| `.claude/worktrees/agent-…` under shared ROOT | Locked by a live harness; polluted R2b scan. Verification must use a clean worktree outside ROOT. |

The 2026-09-17 `origin/main` `18f63db` full-suite baseline has one
deterministic golden retrieval failure and zero R2b failures. It is unrelated
to this planning change; see the execution plan for the exact count.

## 4. Completion State

| Milestone | State | Next owner |
|---|---|---|
| Candidate inventory and design | Complete on pushed `plan/2026-09-17-generalize-append-cursor` at `9e2d0ef` | — |
| Architecture/Execute review | Kiro PASS on original `9e2d0ef` and targeted PASS on the post-merge plan at exact tip `53e7b42`, checked against `main` `d657767`; neither review granted Execute | — |
| Cross-arc coordination | Complete: Codex reconciled the merged base and the local trace; Ryan closed the Copilot proposal | — |
| #286 shared base | [PR #307](https://github.com/alanmz-crypto/convmem/pull/307) squash-merged to `main` as `d657767`; its registry/scanner are the base for this Copilot proposal and Kiro confirmed the revised plan uses them | — |
| Copilot metadata condition | Unresolved for any future design: the merged coordinator revalidates sidecar digest only within a captured run and does not store it in the checkpoint. A future Copilot route would need explicit cross-run parse-relevant metadata binding and tests for `workspace.yaml` id changes and `session.start` precedence. | No active owner |
| Shared-code base | Issue #286 landed as `d657767`; its registry/scanner remain on `main` and are unaffected by this stop | — |
| E0 writer-contract evidence | Kiro confirmed exact byte-prefix preservation, inode replacement on every action, and unexpected `read_agent` execution. The current coordinator returns `source_replaced_or_rotated` before checking the matching prefix. E0 did not pass; Ryan closed the candidate as `NO_COPILOT_ROUTE`. Kiro's additional claim that sidecar digest changes independently refuse cross-run reuse was not supported by the checkpoint/continuity code. Hosted behavior remains unknown and needs no probe for this closed proposal. | Closed |
| E1–E4, bootstrap, canary, activation | Not started and not authorized for this Copilot proposal | None |

## 5. Your Role

**Current role:** preserve `NO_COPILOT_ROUTE` for the Copilot candidate. No
further E0 trace, hosted call, E1–E4 implementation, or substitute format is
authorized. The [local trace handoff](../inter-model/CODEX-2026-09-18-copilot-e0-local-trace-handoff.md)
and [coordination handoff](../inter-model/CODEX-2026-09-18-append-cursor-ownership-handoff.md)
are historical evidence. A future attempt requires a new Ryan scope decision,
a revised continuity/metadata design, and Kiro review.

**For separate Arc Codex operational work:** consult the existing
`STATUS-codex-jsonl-production-integration.md` and its Ryan gates. This
stopped proposal provides no P2, bootstrap, watcher, or configuration authority.

## 6. Reopening Conditions (no active route)

There is no remaining Copilot Execute sequence. Reopening would require Ryan
to choose a new scope after measuring the value of Copilot transcript reuse;
Codex would then need to design continuity for byte-preserving inode
replacement and cross-run metadata binding, Kiro would review that design,
and Ryan would decide any new evidence or implementation grant. The saved
local trace is under `/tmp/convmem-copilot-e0-local.farpf1dl/`; no hosted
trace was run or authorized. No alternate format inherits this proposal.

## 7. Hard Stops

| Stop | Owner | Blocks |
|---|---|---|
| `NO_COPILOT_ROUTE` | Ryan | The current Copilot proposal, further E0 trace, E1–E4, and substitute formats |
| New scope and shared-code writer | Ryan, after a reviewed new design | Any future Copilot coordinator, adapter, test, or config implementation |
| Bootstrap cost/authority | Ryan | Adopting or rebuilding already-indexed sources |
| P2/live canary | Existing Arc Codex gates + Ryan | Production source, Chroma, or provider operations |
| Activation | Ryan | Live config and watcher route |

No gate implies another.

## 8. Relationship to ConvMem

This stopped proposal concerned Arc Codex's ingestion efficiency/recovery
mechanism. It did not alter retrieval ranking, semantic calibration, R2b
attestation, Shadow Ledger, or the source/projection authority direction.
Trapdoor Hunt issue #286's Codex-format implementation landed on `main` as
`d657767`. That shared registry/scanner remains available to its existing
routes; the Copilot candidate adds no route or work in that arc.

## 9. Key Design Files

| Purpose | Path |
|---|---|
| Format-extension design | `docs/plans/ARCHITECTURE-generalize-append-cursor.md` |
| Proposed bounded Execute | `docs/plans/EXECUTION-generalize-append-cursor.md` |
| Existing Kiro design | `docs/plans/ARCHITECTURE-codex-jsonl-production-integration.md` |
| Existing Arc Codex state/gates | `docs/plans/STATUS-codex-jsonl-production-integration.md` |
| Coordinator | `incremental_jsonl.py` |
| Adapter seam | `adapters/jsonl_io.py`, `adapters/kiro_session_jsonl.py`, `adapters/copilot_session_jsonl.py` |
| Source handoff | `docs/inter-model/CODEX-2026-09-17-generalize-append-cursor-handoff.md` at `439b5fc` (separate branch) |
| Distinct Codex-format implementation | [PR #307](https://github.com/alanmz-crypto/convmem/pull/307), squash-merged as `d657767` on `main` |

## 10. How to Update This Brief

After each milestone, overwrite sections 3–6 with current state and the next
lane. Remove completed checklist items. Add one milestone-level Update Log
line. Keep this file a snapshot, not a session diary.

### Update Log

| Date | Who | Milestone change |
|---|---|---|
| 2026-09-17 | Codex | Created the conditional one-format architecture and proposed Execute packet for Kiro review; no implementation authority |
| 2026-09-18 | Kiro / Codex | Kiro PASSed planning tip `9e2d0ef` with metadata-evidence and shared-code-owner conditions; Codex verified the local and remote tip; Ryan's Execute decision is next |
| 2026-09-18 | Codex | Reassessed the pushed #286 integration successor and handed Codex Sol a single-owner recommendation; Ryan's ownership and E0 decisions remain pending |
| 2026-09-18 | Ryan / Codex | Ryan selected the authoring Codex Sol-medium lane for cross-arc coordination; shared-code writer and E0 gates remain pending |
| 2026-09-18 | Ryan / Codex | Ryan delegated the writer choice; Codex assigned the existing #286 Cursor integrator through branch disposition and deferred Copilot E0 |
| 2026-09-18 | Codex | Prepared exact-tip Copilot and Kiro read-only recheck handoffs for the unmerged #286 integration successor |
| 2026-09-18 | Kiro / Codex | Kiro returned exact-tip PASS on #286 integration with 116 passing focused tests; Copilot audit remains pending |
| 2026-09-18 | Copilot / Codex | Copilot returned exact-tip FAIL on #286 documentation acceptance while affirming runtime safety; bounded Cursor docs correction and fresh reviews are next |
| 2026-09-18 | Cursor / Codex | Cursor pushed three-doc correction at `19d34a5`; Codex verified clean diff-check and issued fresh exact-tip Copilot/Kiro recheck handoffs |
| 2026-09-18 | Kiro / Codex | Kiro PASSed corrected #286 exact tip `19d34a5` for S0–S3 continuity and routing; Copilot audit remains pending |
| 2026-09-18 | Copilot / Codex | Copilot PASSed corrected #286 exact tip `19d34a5`; both reviewers now PASS and Ryan's PR decision is next |
| 2026-09-18 | Ryan / Codex | Ryan authorized PR steward; PR #307 opened at reviewed `19d34a5` with initial CI pending and merge reserved to Ryan |
| 2026-09-18 | Codex | PR #307 reached mergeable state with all six checks PASS and no unresolved threads; Ryan owns merge |
| 2026-09-18 | Ryan / Codex | Ryan squash-merged #286 as `d657767`; Codex reconciled the Copilot plan with the landed registry/scanner for targeted Kiro recheck |
| 2026-09-18 | Kiro / Codex | Kiro PASSed post-merge plan tip `53e7b42` against `main` `d657767`; E0 remains ungranted pending Ryan's bounded action/provider choice |
| 2026-09-18 | Ryan / Codex | Ryan granted a bounded preliminary offline local Copilot writer trace; full E0 eligibility, hosted proof, and E1–E4 remain gated |
| 2026-09-18 | Cursor / Codex | Local trace preserved prior bytes but replaced the inode on every action and fired an unexpected tool call; E0 did not pass and targeted Kiro evidence recheck is next |
| 2026-09-18 | Kiro / Codex | Kiro confirmed the decisive inode refusal; Codex found its separate sidecar-refusal claim does not follow from checkpoint or continuity code, leaving Ryan's stop-or-replan decision pending |
| 2026-09-18 | Ryan / Codex | Ryan stopped the Copilot proposal as `NO_COPILOT_ROUTE` under the current contract; no hosted trace, E1–E4, or substitute format was granted |

## TL;DR

- [Arc Codex] Ryan closed the Copilot append-cursor proposal as
  `NO_COPILOT_ROUTE` after E0 found byte-preserving inode replacement on every
  action. The shared registry/scanner on `main` and separate Arc Codex gates
  remain as they were. No Copilot implementation or hosted operation is
  authorized.
