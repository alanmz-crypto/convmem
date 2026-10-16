# [Arc Codex #286] Stage 2 safety re-audit — round 7

**Verdict: FAIL at `d0510f8aeaf5424712814610cf61fa3cf2eac975`.**

**Auditor:** Codex, under Ryan's explicit round-7 audit request. **Implementation owner:** Cursor. **Date:** 2026-10-16, America/Chicago.

Corrective 20 closes the retry-accounting finding R6-F1, and the final inventory refresh closes R6-F2. Corrective 21 repairs the reported C1 acquisition order and its existing mocked recovery tests pass. However, real embedding admission still prevents Safe Harbor recovery from rebuilding missing or stale Chroma rows. The same recovery cases pass on merged main. The tests conceal this conflict by replacing the entire embedding function, including its lock checks.

This report contains **one High finding, R7-F1**. It does not authorize implementation, production operations, a PR, or a merge.

## Scope and evidence identity

- **Implementation audited:** `fix/2026-10-12-issue-286-stage2-wedge-fixes`, pinned to `d0510f8aeaf5424712814610cf61fa3cf2eac975`. Reviewed the main integration at `c19b73d`, capture-accounting correction `71fa518`, corrective-21 code delta `3e0caf9..be8ec2d`, and final inventory commit `d0510f8`.
- **Independent comparison:** merged main `c6f07241ccf1a71d9d874fee963a37b04091b3ce`, which contains the Safe Harbor delivery brought into this branch. The identical new recovery probe ran on both revisions.
- **Prior review considered:** Claude's round-28 PASS in `docs/inter-model/CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md` on fetched `origin/docs/2026-10-12-issue-286-stage2-fixes-handoff`. Its full-suite results are prior evidence, not results independently reproduced here.
- **Report branch:** `docs/2026-10-16-issue-286-stage2-fixes-audit-r7`, created from fetched `origin/main` at `c6f0724` using `convmem work start`. This report is its only tracked change.
- **Workspaces:** an independent clone and detached implementation/control worktrees under `/home/lauer/.cache/audit-286-r7/`; harnesses and retained output under `/home/lauer/.kiro/audit-286-r7/`. The shared checkout was neither edited nor switched.

The Arc Codex STATUS brief was read for product context. Ryan's exact task and pinned revisions define this audit; the brief's older operational narrative is not evidence of current deployment.

## R7-F1 — High: recovery that needs an embedding is blocked by the branch's provider lock guard

**Impact:** an admitted `APPROVAL_STARTED` recovery that must create an absent Chroma row or update a valid base row cannot complete. It raises a `RuntimeError` before transport. Repeating recovery encounters the same conflict. Event-only completion and marker-only repair still work. This is a recovery availability regression; the reproduction does not demonstrate corrupt output or paid calls.

**Locations at `d0510f8`:**

- `propose_decision.py:883` acquires `governed_lock(cfg)` then `index_write_flock(cfg)`.
- `propose_decision.py:893` opens the recovery Chroma session; `:902` enters the native recovery critical section.
- `propose_decision.py:844–845` selects `retry_chroma` and calls `_recovery_apply_intent`.
- `propose_decision.py:595` invokes `observe.ingest_observation`, which calls `prepare_observation_ingest` at `observe.py:465`.
- The changed/base and missing-row branches request an embedding at `observe.py:345` and `:362`.
- `llm.py:155` invokes `reject_provider_under_write_scope`; `purge_locks.py:102–105` rejects C1 or a production Chroma session being held.

Thus both branches deterministically reach the provider guard with **C1 depth 1 and Chroma session depth 1**. Corrective 21's earlier C1 acquisition solves the export-lock acquisition error but does not reconcile recovery's embedding preparation with the branch's provider-scope rule. Simply removing C1 would not resolve the session-depth conflict and would reintroduce the earlier lock-order failure.

**Why the existing tests pass:** `tests/_safe_harbor_t2_cli.py:67–70` assigns `llm.ollama_embed = _fake_embed`; the T4 common helper installs that fake. This bypasses the production check entirely. The standard success matrix can therefore be green while these production paths cannot succeed.

### Independent reproducer

Harness files:

- `/home/lauer/.kiro/audit-286-r7/harness/test_r7_recovery_provider.py`
- `/home/lauer/.kiro/audit-286-r7/harness/_r7_recovery_probe.py`

The test uses the existing isolated T4 fixture, real admission, signed/approved intent, real scratch Chroma, recovery code, locks, validation, export, and publication. In the child it saves the **original** `llm.ollama_embed` before installing the usual fixture fakes, then restores that function through a scope-recording wrapper. Only `llm.requests.post` is replaced with an in-memory response returning the fixture's deterministic embedding. The actual lock check and provider-attempt accounting stay in place. Network refusal remains installed, and there are no API keys.

Run:

```bash
bash /home/lauer/.kiro/audit-286-r7/harness/run-selected.sh provider
bash /home/lauer/.kiro/audit-286-r7/harness/run-selected.sh provider \
  /home/lauer/.cache/audit-286-r7/main-control
```

**Result at `d0510f8`: 2 failed, 2 passed (53.80 s).**

- `create_absence`: `RuntimeError: provider calls are forbidden under the index write lock or a Chroma write session`; observed depths `(1, 1)`; **0 fake HTTP calls**.
- `base_retry`: identical error and depths; **0 fake HTTP calls**.
- `event_only`: PASS, action `approve`, no embedding needed.
- `marker_repair`: PASS, action `repair_marker`, no embedding needed.

**Identical probe at main `c6f0724`: 4 passed (55.32 s).** Both rebuild cases complete with action `retry_chroma` and one fake HTTP call each. The absent-row case also checks Chroma/export identity and final APPROVED publication. Main has no C1/session-depth counters, so the probe's fallback zero values there are not evidence that main holds no native lock.

Evidence: `evidence/provider-tip.log` and `evidence/provider-main.log` under the round-7 harness root, including complete call stacks and per-case JSON results; `evidence/r7-f1-differential.json` collects the eight outcomes.

**Required disposition:** reconcile recovery's embedding preparation with the existing no-provider-under-C1/session invariant while preserving admitted authority, live-state revalidation, and serialized apply/validate/export/publication. Retain a regression test that exercises the real embedding gate and mocks transport below it. Do not waive the invariant or remove the recovery locks merely to make the current fake pass. No implementation was changed in this audit.

## Previous findings and retained harnesses

**R6-F1: closed.** The unchanged alternating-fault probe at `d0510f8` performs only two captures: truncate, then rewrite. Both failures are recorded as `unexpected_SourceCaptureError`; `consecutive=source_consecutive=2`. All subsequent calls, including the quiet call after restoring the original source bytes, raise `live_route_refused`. Retry state remains and **0 fake summaries** occur. Specific outward capture diagnostics do not become distinct accounting buckets.

**R6-F2: closed.** All 27 selected inventory identity, canary-baseline, and Shadow writer-scan checks pass. The final inventory follows corrective 21 and matches the resolved implementation identity.

The original round-4, round-5, and round-6 test files were copied byte-for-byte, executed at the pinned tip, and compared with the originals afterward. Their source directories were not edited. SHA-256:

```text
r4 fb7726ec3fa4170314568928d230d872e0f6364ac18e1463b002a3bb176e64bd
r5 80123bdfd265bcb37d20638f9b9a38ffc109e4afff7a86094bf6a368dcf45e94
r6 4fe4ea54d5c6537541ef6e9e8899fccfeeaac9f8f14457655a025c6266de118d
```

Original r4: **7 passed**. Original r5: **13 passed, 1 expected obsolete-control failure**. Original r6: **10 passed**. Cursor's adapted r5 file: **14 passed**. Combined: **44 passed, 1 expected failure**, 15.02 s (`evidence/original.log`).

All three round-5 truncate/rewrite/rotate races refuse in both shortcut and full-path arms with retained state and zero additional summaries. Seeded corruption/holds, the natural source hold, and unchanged-path differential controls pass. The original r4 lock, concurrency, accounting, clear, snapshot, and cache controls pass.

**Cursor's adapted reservation control: PASS.** Its top-level read-only admission spy is valid; it checks unchanged retry bytes and actual source-lock ownership. The sequence remains:

```text
check, capture, gate, work, account, gate, work, account, gate, gate
fake summaries = attempts_on_prefix = 2
```

The original r5 control still expects `reserve=False` on the removed enforcing-gate call. Its failure is the anticipated obsolete test, not a new product finding. The unchanged r6 nine-case probe independently confirms the read-only admission helper does not mutate state.

## Main integration, corrective 21, and T4 observer ruling

**Import resolution: PASS.** The top-level imports in `propose_decision.py` match main, including `math`, `re`, and `dataclass`. An AST comparison preserves all 65 function/class definitions; only `_recover_approval_impl`, `ingest_approved_file`, and `ingest_approved_ledger` differ. The recovery-specific `from observe import ingest_observation` remains present inside `_recovery_apply_intent`; the approved-ledger path retains the branch's prepare/commit imports. The new probe reaches the real embedding gate, so this is not a missing-import failure. Evidence: `evidence/recovery-ast-comparison.json`.

**Lock ordering: PASS for the reviewed paths.** Recovery now takes governed lock → C1 → production Chroma session → native recovery guard, and acquires the export lock while C1 is already held. Nested export acquisition therefore does not acquire C1 from inside a Chroma session. Recovery takes no source lock. Source-scoped incremental apply/purge continues to take the source lock before C1. The T4 mutation helpers now take C1 before opening their production sessions, and the file-generation dedupe fixture binds the apply call to its scratch live config. These ordering corrections coexist with R7-F1; correct lock order does not make provider work inside that scope valid.

The native guard implementation, event-authority implementation, and CI bootstrap/launcher are unchanged from merged main. The branch's guarded-store wrapper and provider-scope enforcement are the relevant integration seam; R7-F1 demonstrates an actual conflict there.

**Revised competitor observer: acceptable for the combined protocol, with a narrower event meaning.** `PRE_FLOCK/NB_BLOCKED/ACQUIRED` can now describe the first contended C1 acquisition rather than the native guard acquisition. The events alone no longer prove the competitor is blocked specifically on the native guard. However, the existing recovery-first test still separately probes the native guard from another process at the inspection barrier, requires that probe to be blocked, confirms the recovery holder is alive, rejects early competitor acquisition, and checks final state/publication. The faulty out-of-lock control appropriately releases **both** OS locks; releasing only the native guard would let C1 conceal the intended unsafe interleaving.

**Independent sensitivity control: PASS.** A copied scratch concurrency worker deliberately releases only the native guard immediately before `INSPECTED`, while asserting C1 is still held. The unchanged recovery-first race gets past the revised observer's C1 `NB_BLOCKED`, then fails exactly at `assert probe_payload.get("acquired") is False`. This demonstrates that C1 does not mask a missing native guard at the tested barrier. The audit test expects that precise assertion and passes (15.57 s; `evidence/observer.log`). It is bounded barrier evidence, not an exhaustive proof of every lock interleaving.

The first version of this audit-only sensitivity assertion incorrectly expected traceback stringification to include source text. The underlying race already detected the intended guard gap. I corrected the assertion to read the failing source line and reran it; the initial diagnostic is retained as `evidence/observer-harness-assertion-error.log`.

## Executed suites and isolation

The runner calls the pinned, unmodified `tests/_safe_harbor_t3_worker.py` **`run_ci()`** with `python -I -S -B`. Its small external adapter selects pytest targets and changes the evidence parent from `/tmp` to disk-backed `~/.cache/audit-286-r7/evidence`; it does not change bootstrap, the `full_ci` environment profile, fixtures, config logic, or product code. This is a **targeted CI-launcher run**, not a full-suite claim. Selection manifests and the adapter are in `harness/`.

Pinned Restic: **0.19.0**, `/home/lauer/.cache/issue286-restic-bin/restic`, SHA-256 `ae7fe58ab3511f830fd31d157158620b209522ff1332b119199d2e938d72338c`, independently checked and validated again by the launcher.

- Retained originals plus adapted controls: **44 passed, 1 expected obsolete failure**.
- Recovery/T4 concurrency, terminal, order, refusal, publication, dedupe, and proposal suite: **103 passed, 5 subtests passed**, 905.43 s (`evidence/recovery.log`).
- Write-guard/source-lock/corrective regression selection: **56 passed**, 58.97 s.
- Final inventory identity/baseline/coverage selection: **27 passed**, 11.16 s.
- New real-embedding recovery probe: **2 failed, 2 passed at tip; 4 passed at main**.
- Native-guard-gap sensitivity control: **1 passed** (expected detection of the injected defect).
- `git diff --check c6f0724 d0510f8`: PASS. Tracked implementation files remain unchanged.

Each run starts with `env -i`, scratch HOME/TMPDIR, no API keys, disabled user-site/plugin autoload/bytecode/cache, and the launcher's scratch config. An additional Python audit hook denies sockets, live-path opens, and writes outside scratch; T4 children also install their own inherited network-refusal hook. The new provider probe substitutes only in-memory HTTP transport. These are cooperative test boundaries, not exhaustive native-library syscall auditing.

The required read-only doctor/brief/unresolved startup ran before isolation. No corpus search, indexing, watch/refine/monitor service command, production mutation, live config change, external provider transport, PR, or merge was performed. Session ingestion was omitted under Ryan's explicit no-indexing restriction. No `/tmp` worktree or outer suite directory was created by this runner.

### Reproduction and retained evidence

```bash
bash /home/lauer/.kiro/audit-286-r7/harness/run-selected.sh original
bash /home/lauer/.kiro/audit-286-r7/harness/run-selected.sh recovery
bash /home/lauer/.kiro/audit-286-r7/harness/run-selected.sh regressions
bash /home/lauer/.kiro/audit-286-r7/harness/run-selected.sh inventory
bash /home/lauer/.kiro/audit-286-r7/harness/run-selected.sh provider
bash /home/lauer/.kiro/audit-286-r7/harness/run-selected.sh provider \
  /home/lauer/.cache/audit-286-r7/main-control
bash /home/lauer/.kiro/audit-286-r7/harness/run-selected.sh observer
```

Every invocation gets a fresh suite directory and basetemp. Complete output is retained in `/home/lauer/.kiro/audit-286-r7/evidence/`; launcher summaries, scratch states, and race diagnostics remain under `/home/lauer/.cache/audit-286-r7/evidence/`. The latter can be removed after review; they are not production data. Original-copy identities are in `evidence/original-hashes.json`.

## [Arc Codex #286] Handoff

I finished: round-7 safety re-audit of exact `d0510f8` — **FAIL**, one High recovery finding.
Next step: Ryan dispositions R7-F1; an authorized correction must preserve the lock/provider invariants and pass the real-embedding probe.
Next lane: Ryan; Cursor for implementation if authorized.
See my work: this report's R7-F1 reproducer and main-versus-tip results.

Report branch: `docs/2026-10-16-issue-286-stage2-fixes-audit-r7`. Commit/push identity is supplied in the chat handoff. No PR requested or created.

Optional later PR title: **Document recovery failure found in the Stage 2 safety audit**.

Optional later PR description: Codex's 2026-10-16 round-7 audit gives Ryan a reproducible FAIL against Cursor's exact `d0510f8` Stage 2 branch. The prior retry-accounting and inventory findings close, and the corrected lock order and race observer pass their checks. A transport-only fake exposes a branch-specific failure: real embedding admission blocks missing/base-row recovery while C1 and the Chroma session are held; the identical probe passes on merged main. This change adds only the audit report. **TL;DR:** [Arc Codex #286] One High recovery finding requires disposition before accepting the branch.

## TL;DR

- [Arc Codex #286] **FAIL at `d0510f8`: R7-F1, High.** Missing/base-row recovery reaches the real embedding gate under C1 and a Chroma session and always refuses; existing whole-function fakes conceal it.
- The identical new probe passes all four cases on main; at the branch tip the two rebuild cases fail and the two no-embedding controls pass.
- R6-F1 and R6-F2 close. The unchanged retained probes, adapted reservation control, corrected lock order, and T4 observer sensitivity support their scoped PASS rulings.

<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc context; no production authority -->
<!-- src: /home/lauer/.cache/audit-286-r7/code/propose_decision.py, /home/lauer/.cache/audit-286-r7/code/observe.py, /home/lauer/.cache/audit-286-r7/code/llm.py, /home/lauer/.cache/audit-286-r7/code/purge_locks.py — exact audited implementation -->
<!-- src: /home/lauer/.kiro/audit-286-r7/harness/test_r7_recovery_provider.py, /home/lauer/.kiro/audit-286-r7/harness/_r7_recovery_probe.py, /home/lauer/.kiro/audit-286-r7/evidence/provider-tip.log, /home/lauer/.kiro/audit-286-r7/evidence/provider-main.log — independent differential reproduction -->
<!-- src: /home/lauer/.kiro/audit-286-r7/evidence/original.log, /home/lauer/.kiro/audit-286-r7/evidence/recovery.log, /home/lauer/.kiro/audit-286-r7/evidence/regressions.log, /home/lauer/.kiro/audit-286-r7/evidence/inventory.log, /home/lauer/.kiro/audit-286-r7/evidence/observer.log — retained checks and observer sensitivity -->
