# [Arc Codex #286] Stage 2 safety re-audit — round 8

**Verdict: PASS against `a5fb7d794d2e2dac379c377b6beba7a1f438795c`, tree `c7d4b78e59b60746e182c8e61b588a9df8aabd0f`. No new actionable findings in the requested scope. R7-F1 is closed.**

**Auditor:** Astra, under Ryan's explicit round-8 audit request. **Implementation owner:** Cursor. **Date:** 2026-10-16, America/Chicago.

This audit evaluates corrective 22's recovery embedding preparation against the earlier R7-F1 failure. It is a bounded safety recheck, not production activation authority or a full-suite certification. The report is the only tracked deliverable; no implementation was changed.

## Target and provenance

- Exact audited commit: `a5fb7d794d2e2dac379c377b6beba7a1f438795c` on the Stage 2 wedge-fix implementation branch.
- Exact audited tree: `c7d4b78e59b60746e182c8e61b588a9df8aabd0f`.
- The subsequent real two-parent merge, `d5f765a05dbb74d2786e2f15ae6bb0824ac38dba`, has this identical tree. The code verdict carries to that tree-identical merge; tests here ran at `a5fb7d7`.
- Report branch: `docs/2026-10-16-issue-286-stage2-fixes-audit-r8`, created with `convmem work start` from fetched `origin/main` at `c6f07241ccf1a71d9d874fee963a37b04091b3ce` in an independent clone. The helper pushed the branch before the first report edit.
- Read the Arc Codex STATUS brief, local AGENTS instructions, branching/hygiene rules, the round-7 FAIL report, and Claude's round-29 corrective design on the handoff branch. Claude's prior suite results are context, not independent evidence claimed here.
- Implementation checkout: `/home/lauer/.cache/audit-286-r8/code`. Report checkout: `/home/lauer/.cache/audit-286-r8/repository`. Harness and retained console output: `/home/lauer/.kiro/audit-286-r8/`.

## R7-F1 — High, closed: rebuild recovery reaches real embedding admission outside write scopes

**Previous impact:** missing-row and base-row recovery always refused before transport because embedding ran under C1 and a production Chroma session. Event-only and marker repair worked.

**Reproducer:** `bash /home/lauer/.kiro/audit-286-r8/harness/run-selected.sh provider`.

The round-7 test and child probe were copied unchanged. They preserve the actual `llm.ollama_embed`, its provider admission, and its write-scope rejection, replacing only HTTP transport with an in-memory response. All four cases pass in **53.27 s**:

- `create_absence`: `retry_chroma`, one fake HTTP call, embedding entry at C1 depth 0/session depth 0.
- `base_retry`: `retry_chroma`, one fake HTTP call, depths 0/0.
- `event_only`: `approve`, one fake HTTP call, depths 0/0.
- `marker_repair`: `repair_marker`, one fake HTTP call, depths 0/0.

Evidence: `evidence/provider.log`. Every recorded embedding entry satisfies the boundary; the two rebuild paths now reach transport and finish. This closes the exact deterministic failure reported in round 7.

## Transport failure, retry, and document/vector identity

**Reproducer:** `bash /home/lauer/.kiro/audit-286-r8/harness/run-selected.sh deferral`.

The new external probe uses the same real recovery scenarios and real embedding gate. It first makes only the HTTP transport raise `RuntimeError('R8_TRANSPORT_DOWN')`; it restores transport for the next recovery in the rebuild cases. The fixture, admission, Chroma, locks, event authority, export, and publication remain real and confined to scratch.

**Result: 4 passed, 64.82 s.** Both `create_absence` and `base_retry` refuse with the promised `recovery deferred (embedding unavailable: RuntimeError: R8_TRANSPORT_DOWN); nothing was written, retry` message, leave the compared state unchanged, and retain `APPROVAL_STARTED`. Each next recovery makes one successful fake transport call, returns `retry_chroma`, and publishes exactly one APPROVED event. Event-only and marker-only cases each encounter one failed transport call, still complete, and preserve their stored document and vector. All embedding entries are at C1/session depths 0/0.

Both rebuilt rows pass exact provider-to-native document/vector identity. Persisted values have maximum absolute difference `5.960464477539063e-08` from the explicitly float32-converted response; the final test permits at most `1e-7`. That observed difference is one float32 ULP at these magnitudes. Evidence: `evidence/deferral-final.log`.

The unchanged-state assertion compares SHA-256 of the exact bytes of the event log, approved intent ledger, pending queue, and export, plus all logical Chroma rows: IDs, documents, metadata (including proposal markers), and embedding hashes. It does not assert unchanged physical SQLite/HNSW file bytes, mtime, or guard housekeeping files. The claimed no-write result is no recovery corpus/publication mutation.

The strengthened identity probe uses a nonconstant, text-dependent 768-dimensional vector. It checks that the provider prompt exactly equals the stored document and that the document/vector passed to `ChromaStore._native` exactly equal the successful fake transport response. It then reads the persisted vector and checks its dimensions and values against float32 storage, with maximum absolute error at most `1e-7`. This catches a stale or unrelated vector without treating ordinary float storage precision as a different semantic embedding.

Audit-harness diagnostics are retained rather than discarded. The first hash assertion compared unrounded Python floats to the dump's six-decimal float32 representation and failed both rebuild cases. After correcting that serialization comparison, one constant-vector base-row run failed strict float32 equality; an instrumented rerun passed exact equality. The final probe uses the stronger native-boundary identity check and a nonconstant vector, reports the actual storage error, and retains the earlier outputs in `deferral-harness-normalization-error.log`, `deferral-vector-investigation.log`, and `deferral-base-diagnostic.log`. No product code changed during this investigation.

## Lock order and what T4 proves

**Static ruling:** recovery still takes governed lock → C1 → production Chroma session → native recovery guard. Corrective 22 moves embedding between governed authority loading and C1 acquisition. `_recover_approval_locked` owns the existing session/native-guard body; `_recover_approval_impl` still acquires C1 before calling it. Live-state classification and apply/validate/export/publish remain in one native critical section. Export acquisition is nested under an already-held C1, so the provider fix does not reintroduce the earlier lock-order inversion. Recovery takes no source lock.

`_prepare_recovery_embedding` and `ingest_observation` both normalize the governed intent through `normalize_ledger_record` and form text through `ledger_unit_document`. The prepared vector is explicitly passed as `precomputed_embedding`; the prepare path chooses it instead of calling the provider. The dynamic native-boundary assertions cover both absent-row add and base-row update.

**Once-only signal check:** an audit-only copy of the concurrency worker records calls to its existing signal writer without changing synchronization. The unchanged recovery-first race assertions run against both real competitors. Both pass (**33.59 s** total), and each child emits exactly:

```text
recovery:   INSPECTED
competitor: PRE_FLOCK, NB_BLOCKED, ACQUIRED
```

Reproducer: `bash /home/lauer/.kiro/audit-286-r8/harness/run-selected.sh signals`. Evidence: `evidence/signals.log`, with full race diagnostics in the launcher's scratch directory.

The observer's `NB_BLOCKED` may refer to the first contended C1 acquisition, not necessarily the native guard. The race independently probes the native guard from another process while recovery is stopped at `INSPECTED`, verifies that recovery remains alive, and rejects early competitor acquisition. The retained round-7 sensitivity control deliberately releases only the native guard while leaving C1 held; it must fail at the independent guard probe. Thus C1 does not conceal a missing native guard at that barrier. This is bounded interleaving evidence, not exhaustive concurrency proof.

**Targeted concurrency result: 23 passed, 136.30 s.** The entire `tests/test_safe_harbor_t4_concurrency_real.py` module and the unchanged round-7 sensitivity test pass, including real forget/refine races, competitor-first refusal, the deliberately unsafe out-of-lock control, post-wait config revalidation, pipe protocol, and diagnostic handling. The native-guard-only fault is detected at exactly `assert probe_payload.get("acquired") is False`. Reproducer: `bash /home/lauer/.kiro/audit-286-r8/harness/run-selected.sh race`. Evidence: `evidence/race.log`.

## Retained round-4, round-5, and round-6 checks

**Reproducer:** `bash /home/lauer/.kiro/audit-286-r8/harness/run-selected.sh original`.

Result: **44 passed, one expected obsolete-control failure**, 15.32 s. The selection contains the unchanged round-4/5/6 tests and Cursor's already-tracked adapted round-5 control. The original counts remain round 4: 7 passed; round 5: 13 passed plus one obsolete spy failure; round 6: 10 passed; adapted round 5: 14 passed.

The sole failure is `test_r7_original_r5.py::test_adapted_lock_sequence_has_correct_reservation_semantics`, which still expects `reserve=False` on an enforcing-gate call that was replaced by a read-only admission helper. It is the exact anticipated obsolete test from the brief, not a product finding. The original test was neither edited nor marked xfail. The run exits 1 and this report explicitly qualifies that result. Cursor's adapted control and the independent round-6 read-only helper checks pass.

The alternating truncate/rewrite fault remains capped at two captures, with retained state and zero summaries after refusal. Shortcut and full-path source-race controls refuse, ordinary unchanged/append controls behave as expected, and the original lock/accounting/cache controls pass. Evidence: `evidence/original.log`. A duplicate parent-lane run overlapped because of delayed approval delivery; it reproduced the same 44-pass/one-obsolete-failure result in `original-root.log` and adds no independent coverage claim.

Byte identity before and after execution is recorded in `evidence/unchanged-probe-hashes.json`. SHA-256 of the original source probes:

```text
r4 fb7726ec3fa4170314568928d230d872e0f6364ac18e1463b002a3bb176e64bd
r5 80123bdfd265bcb37d20638f9b9a38ffc109e4afff7a86094bf6a368dcf45e94
r6 4fe4ea54d5c6537541ef6e9e8899fccfeeaac9f8f14457655a025c6266de118d
r7 test f4e6f53b5c9092cf3dfb80b6aed91b7486e57a75bd31122b1d3a2e256856ba18
r7 child 171dc6df2f7d5e573dfe7148976aa576cb3d698cc1d2845dd1a18d0dda785322
```

**Final inventory recheck: PASS, 27 tests, 11.67 s.** The parent Codex lane ran the same isolated runner at the pinned checkout, selecting R2b corrective-viii/implementation-revision identity, incremental canary baseline, and Shadow writer coverage. The launcher returned 0. Evidence: `evidence/inventory-root.log`. Reproducer: `bash /home/lauer/.kiro/audit-286-r8/harness/run-selected.sh inventory`. This preserves closure of R6-F2 at corrective 22's final inventory tree.

## Isolation, limitations, and trade-off

All test runs use the pinned unmodified CI launcher's `run_ci()` through the round-7 target-selection adapter, with `python -I -S -B`. Only selection and the disk-backed evidence parent differ from the full launcher. The full CI suite and round-7's entire 103-case recovery selection were not rerun; the exact targeted selections above define this verdict.

Each launcher starts with `env -i`, scratch HOME/TMPDIR, no API keys, disabled user-site/plugin autoload/bytecode/cache, and scratch config. The retained Python audit fence refuses network sockets, production data/config/session paths, and writes outside audit scratch; T4 children inherit their own pre-import network-refusal hook. Only in-memory HTTP transport is used. These are cooperative test boundaries, not native-library syscall auditing.

Pinned Restic is **0.19.0**, `/home/lauer/.cache/issue286-restic-bin/restic`, SHA-256 `ae7fe58ab3511f830fd31d157158620b209522ff1332b119199d2e938d72338c`; it was independently hashed and checked by the launcher. Worktrees and outer suite directories are disk-backed under `~/.cache`, not `/tmp`.

The production/shared checkout was not edited or switched. No corpus indexing, watch/refine/monitor operation, live config change, real provider transport, PR, or merge was performed. Session ingestion is deliberately omitted under Ryan's specific no-indexing instruction. The requested audit fixtures exercise scratch product routes only.

**Largest trade-off:** every `APPROVAL_STARTED` recovery now attempts an embedding before knowing whether live state needs it. Event-only and marker-only completion therefore incur an unused local Ollama attempt and can wait for its timeout, although an exception does not prevent their completion. That attempt occurs under the governed authority lock, but outside C1 and the Chroma session. `APPROVED` verification does not prepare an embedding. The design preserves one native critical-section pass and the existing T4 barrier semantics.

## [Arc Codex #286] Handoff

I finished: [Arc Codex #286] round-8 bounded safety re-audit — PASS, R7-F1 closed.
Next step: Ryan dispositions this audit alongside the other required reviews; production authority remains separate.
Next lane: Ryan, with the Safe Harbor review lane for recovery acceptance as planned.
See my work: this report's verdict and reproducible recovery/deferral/race evidence.

Report branch: `docs/2026-10-16-issue-286-stage2-fixes-audit-r8`. Commit and explicit-refspec push identity are supplied in the chat handoff. No PR was requested or created.

Optional later PR title: **Document the Stage 2 recovery safety recheck**.

Optional later PR description: Astra's 2026-10-16 round-8 audit gives Ryan a bounded verdict on Cursor's Stage 2 corrective-22 tree. It checks the real embedding admission boundary, provider-failure deferral and retry, stored document/vector identity, T4 lock signaling, and retained regression probes. This change adds only the audit report. **TL;DR:** [Arc Codex #286] Review the scoped result before accepting recovery changes; production activation remains separately gated.

**TL;DR:** [Arc Codex #286] PASS on the exact corrective-22 tree, carrying to its tree-identical two-parent merge. R7-F1 closes; transport-failure retry, document/vector identity, T4 lock/signals, and inventories pass. The retained round-5 obsolete spy fails as expected; no new product finding or production authority is implied.

<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc context, not production authority -->
<!-- src: /home/lauer/.cache/audit-286-r8/code/propose_decision.py, /home/lauer/.cache/audit-286-r8/code/observe.py, /home/lauer/.cache/audit-286-r8/code/chroma_write_guard.py — exact implementation audited -->
<!-- src: /home/lauer/.kiro/audit-286-r8/harness/_r8_deferral_probe.py, /home/lauer/.kiro/audit-286-r8/harness/test_r8_signals.py, /home/lauer/.kiro/audit-286-r8/evidence — independent probes and retained results -->
