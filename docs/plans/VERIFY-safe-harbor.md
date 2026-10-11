# Verify Plan — Safe Harbor

> **Arc: Safe Harbor. STUB — NOT RUN.** Created with the execution-plan draft; no implementation, experiment, restore or live-operation authority follows. No check below is a PASS.

```text
Planning Status
Phase:        Execution Planning (future Verify companion only)
Characters:   Task Decomposer, Dependency Mapper, Scope Guardian
Function:     Planner
Lanes:        Cursor collects later evidence; Kiro signs off; Ryan owns gates
Authority:    Drafting only; post-Execute verification remains pending
```

**Subject / implementation tip:** not yet assigned.

**PRs:** none.

**Direction:** [ARCHITECTURE-safe-harbor.md](ARCHITECTURE-safe-harbor.md), approved at `5ea16a6`.

**Plan:** [EXECUTION-safe-harbor.md](EXECUTION-safe-harbor.md).

**Goal:** demonstrate the approved guard/recovery behavior without extending coverage or claiming unperformed recovery.

## Human consequence

If implemented and accepted, guarded failures remain contained with evidence until validated owner disposition; unavailable/tombstoned approval state cannot silently become a retry. This is a planned consequence, not shipped behavior. Rollout, actual recovery qualification and closure remain separate.

Who: Codex authored this stub; Cursor supplies implementation evidence later. What/when: verification map for the first execution-plan draft. Why/how: bind each safety claim to fixture effects, fault cases and an exact reviewed revision before acceptance.

## Scope lock

In scope: execution T1–T5 and their named production entrypoints under isolated fixture configuration. Out of scope: live corpus, service activation, new backup repositories, drive writes, live restore, T4/V4k, v3 activation, global freeze or broad permission changes.

## Verification design

- **Independent oracle:** fixture logical rows/documents/vectors/tombstones and export bytes; separate event reduction; durable marker/evidence file hashes; fresh-process admission results. Source identity and file existence alone do not prove behavior.
- **Failure injection:** barriers around native admission/recheck, every preservation/replacement and release publication edge; process termination/restart; short write, ENOSPC and fsync failures. Hardware power-loss durability is not implied by process-kill trials.
- **Negative controls:** no-op preflight, overwrite-single-incident marker, copy-over-original retry, census-only release, stale-disposition replay and state recheck moved outside the guard. Each must fail the corresponding independent assertion.
- **Dual-path coverage:** CLI add/upsert and indexed approval, CLI/direct approval recovery, guarded native mutation, audit, recover/reconcile/clear script and watch's recovery caller. Restic tests cover all five distinct consumers. Name any inaccessible path as a gap.

## V0 — Preconditions and external review

All **PENDING / NOT RUN**: exact implementation subject SHA; later Ryan task grant; approved plan and v2 B-E4.1 disposition; isolated roots/providers/repositories; relevant backend/interpreter versions; runtime external-review applicability and evidence copied from Execute.

Execute supplies `gate_applicability`, `reason`, `subject_tip_sha`, `bugbot_reviewed_sha`, `result`, `finding_disposition` and `authority_reference` under the existing Execute gate. Runtime work requires exact-tip evidence; this planning-only stub is not such evidence. An applicable SHA mismatch is FAIL, never silently skipped.

## V1 — Incident authority (T1)

**NOT RUN.** Full unresolved-set retention, same-segment additions, legacy/malformed markers, canonical alias conflict, lock/restart admission, audit FAIL followed by PASS/skipped, and failed publication. Evidence must distinguish successful containment from containment unavailable.

## V2 — Target binding and freshness (T2)

**NOT RUN.** Target/profile/affected-path equality and coverage; prod/lab bypass behavior; changed config; all five consumer outcomes; old versus future snapshots; no future-triggered backup/fallback; unchanged exemptions. Require effect assertions through actual callers and existing numeric error mapping.

## V3 — Preservation and bounded restore (T3)

**NOT RUN.** Original bytes write-once; preservation complete before replacement; pinned source generations; all interruption/IO failure windows; restore aborts initiating mutation even after clean census; only incident-bound existing repair may cross quarantine; persistent census failure remains contained.

## V4 — Release and stale-vector proof (T3)

**NOT RUN.** Complete current incident set and Ryan disposition binding; added-finding invalidation; durable disposition before marker removal; truncated event tail and uncertain unlink/fsync behavior; strict source-watermark oracle. A same-ID changed-vector fixture must demonstrate the census blind spot and refusal. Prove the chosen backend's sequence semantics or mark the task FAIL/blocked, not census-only PASS.

## V5 — Approval recovery (T4)

**NOT RUN.** Cold/warm caches; unknown/absent/tombstoned/conflicting/matching states; direct and CLI callers; actual lease/governed/native/export order; forced forget/refine competition; target substitution; partial Chroma/export/event completion and retry. No successful event or hidden export loss on failure.

## V6 — Integrated handoff and independent sign-off (T5)

**NOT RUN.** All required cases and negative controls accounted for at the implementation tip; policy docs synchronized; no production/drive/provider access; truthful scope/operational prerequisites; written independent verdict with residuals and Ryan gate. Reviewers perform no cleanup or corrective live operations.

## Evidence log

Empty. Later record subject SHA, runner, timestamp, command/case, PASS/FAIL/SKIP and a short evidence pointer for each row. SKIP does not satisfy a required safety claim. No session-start health result fills a runtime or recovery row.

## Merge reading

- [Execution plan](EXECUTION-safe-harbor.md)
- [Architecture](ARCHITECTURE-safe-harbor.md)
- [Current STATUS](STATUS-safe-harbor.md)
- [Active routing](../inter-model/LATEST.md)

## TL;DR

[Arc Safe Harbor] This is the unexecuted V0–V6 evidence map for the proposed implementation. It contains no PASS, completed drill, deployment grant or arc-closure claim.
