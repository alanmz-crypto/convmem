# [Arc Codex #286] Stage 2 safety re-audit — round 5

**Verdict: FAIL at `a89f5739c5fbfbf59827fbe85accb6d42b36c142`.**

**Auditor:** Codex, under Ryan's explicit safety re-audit request. **Date:** 2026-10-15 UTC.
**Implementation owner:** Cursor. **Supplied verification:** Claude round 24, PASS.

Correctives 17–18 close both round-4 findings in the unchanged original probes. Cursor's adapted lock control is valid: the extra admission event is a refusal-only check, not a second reservation. However, the pre-capture shortcut omits live-source revalidation and can acknowledge an invalidated prefix as unchanged. It also bypasses retry refusals and deletes their evidence when a checkpoint matches. The latter behavior predates this delta, but contradicts the current full path and remains within Ryan's explicitly requested shortcut/gate audit.

This report supplies reproducible evidence for disposition. It authorizes no implementation, merge, deployment, live indexing, provider call, or production canary. No PR was created.

## Exact revisions and scope

- **Implementation:** fetched `origin/fix/2026-10-12-issue-286-stage2-wedge-fixes` at exactly `a89f5739c5fbfbf59827fbe85accb6d42b36c142`. Read the seven-file delta from round-4 tip `74c8ee7`, including corrective 17 (`e73d88d`), corrective 18 (`7f8daab`), regenerated inventory/baseline, retained tests, and Kiro's intervening lock-order review. All implementation line references below refer to `a89f573`.
- **Claude's supplied report:** `docs/inter-model/CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md` at exactly `382264d3fda251d170872572d42da3e9d3c0c1b1`, fetched on `origin/docs/2026-10-12-issue-286-stage2-fixes-handoff`. Read round 24 and the retained round-23 probes; extracted and independently executed the seven round-24 appendix cases. Claude's full-suite, coverage, and leak-census claims remain supplied evidence, not this audit's independently reproduced results.
- **Prior evidence:** Codex's round-4 report at `d6b93ff` and the original `/home/lauer/.kiro/audit-286-r4/harness/test_audit_r4.py`. That test file was executed directly, unchanged, and its SHA-256 remains `fb7726ec3fa4170314568928d230d872e0f6364ac18e1463b002a3bb176e64bd`.
- **Report branch:** `docs/2026-10-15-issue-286-stage2-fixes-audit-r5`, created with `convmem work start ... --worktree` from fetched `origin/main` at `c6f07241ccf1a71d9d874fee963a37b04091b3ce`, initially pushed before editing. This report is the only tracked change.

Read the Arc Codex STATUS brief and local verification/reproduction guidance. Its older operational narrative is not evidence of current deployment. This is a bounded delta audit, not a fresh audit of unrelated arcs or all historical Stage 2 findings. Kiro's review concerns `74c8ee7`; no same-revision Kiro/Copilot conflict exists here and no adjudication was invoked.

## R5-F1 — Medium: the new shortcut acknowledges a source that changed after its read

**Locations:** `incremental_jsonl.py:2570–2640`, especially `:2591–2616`; compare `_capture` at `:829` and `_revalidate_live_prefix` at `:832–875`.

The shortcut reads source bytes and their device/inode, parses the selected prefix, and compares that in-memory snapshot with the checkpoint. Its shared guard checks session identity, eligibility, processed lineage, and continuity against those already-read bytes. Neither the shortcut nor the shared guard invokes `_revalidate_live_prefix`. The full capture path does, before returning its snapshot.

**Reproduction:** commit an admitted scratch Codex rollout through the real route. Wrap only the real format parser: after it parses the already-read bytes, mutate the actual scratch source once, before returning the original parsed view. Run three independent cases: truncate to the session-meta line, rewrite a valid message-line byte with unchanged length/inode, or replace the path with a different inode containing the same bytes. Run each from fresh fixtures with the shortcut enabled and with only the shortcut disabled. The probe does not replace revalidation, admission, the shared helper, or the result with stubs.

**Observed at `a89f573`, for all three cases:**

- Shortcut enabled: route returns `('skipped', 0, 0, 0, 0)` from an `unchanged` result; zero additional fake summaries; no retry-state record.
- Shortcut disabled: route raises `IncrementalJsonlError` with code `unexpected_SourceCaptureError`; zero additional fake summaries; failure accounting retains retry state. The underlying full-path revalidation detects the source change.
- At prior tip `74c8ee7`, which has no pre-capture shortcut, the identical interleavings refuse and retain state in both arms. This is a new regression in correctives 17–18, not a changed assertion about an old behavior.

The coordinator lock serializes indexers; it does not prevent a source producer or another filesystem actor from replacing, truncating, or rewriting the transcript. These are deterministic fault interleavings, not a measured frequency claim. The demonstrated impact is a false successful no-op and missing refusal/accounting; no new Chroma corruption or paid call during the raced invocation was observed. A later invocation may detect the change, but that does not restore equivalence for the completed invocation.

**Required correction:** make the shortcut perform the same source-prefix/identity revalidation before accepting `unchanged`, with fail-closed error handling that preserves the pre-capture refusal ordering and avoids orphan snapshots. Retain deterministic truncate/rewrite/rotate tests. No correction was made in this audit.

## R5-F2 — Medium: matching checkpoints bypass retry refusals and erase their evidence

**Locations:** `incremental_jsonl.py:2673–2676,2941–2944`; `_unchanged_prereturn_refusal` at `:2513–2556`; refusal rules in `incremental_retry_state.py:252–284`.

The successful shortcut returns before the `reserve=False` gate. The route wrapper then unconditionally clears `retry_state.json` for `unchanged`. The shared helper does not check retry evidence. A valid checkpoint therefore makes a corrupt state, prefix cap, same-error hold, or source-wide hold disappear, whereas disabling only the shortcut makes the current full path refuse and preserve it.

**Direct state probes:** after a real scratch commit, with no pending transaction, install each of four states separately: malformed retry JSON; three attempts on the matching prefix; two consecutive matching errors; or three source-wide consecutive errors. Invoke the route three times.

- Shortcut enabled: all three calls return `skipped`; the first deletes the evidence; zero extra fake summaries.
- Shortcut disabled: malformed JSON produces `retry_state_unavailable` on every call; each hold produces `live_route_refused` on every call. The original bytes remain exact; zero extra fake summaries.

**Natural-state reproduction, with no fabricated retry JSON:**

1. Commit the scratch rollout and save its bytes.
2. Append a distinct invalid-UTF-8 complete line before each of three calls. The real capture and failure-accounting paths produce `source_consecutive=3`; no transaction remains.
3. Restore the original committed bytes in place, preserving the inode. Do not clear retry state or invoke an operator-release function.
4. Invoke the route, then append one valid Codex record and invoke it again.

With the shortcut, step 4 first returns `skipped` and deletes the real hold; the subsequent append returns `processed` and performs **one additional fake summary**. With the shortcut disabled, both calls return `live_route_refused`, the hold remains, and there are **zero additional fake summaries**. The restoration is an injected source change, not an authorized retry-state release. This demonstrates actual re-admission after the implicit clear, rather than only different status labels.

**Historical qualification:** the unchanged path at `74c8ee7` also cleared these states and allowed the subsequent append. This is **inherited behavior, not a newly introduced retry-cap regression**. Corrective 17 adds a refusal-only gate to the full path but leaves the shortcut exempt. Thus the round-24 statement that shortcut and full path agree is incomplete, and the current route still fails the requested keep-retry-state check. The eight passing baseline equality assertions do not establish safe baseline handling of holds; the printed observations establish that both old-revision arms bypass them.

**Required correction:** preserve unavailable retry evidence and applicable holds before returning a successful no-op, without reserving a paid attempt for a clean unchanged prefix. If an exception for checkpoint-matching sources is intended, it needs an explicit disposition that accounts for evidence deletion and source-wide release; it cannot be inferred from zero work in that one invocation. No correction was made here.

## Lock-control ruling and round-4 disposition

**Cursor's adapted lock control: PASS.** The original test fails only at its final sequence assertion; all lock, provider-scope, call-count, and release assertions before it pass. The adapted repository copy passes, and an independent probe records `reserve` values, capture ordering, exact retry bytes around the refusal-only check, and the final reservation count:

```text
fresh attempt:  gate(False) -> capture -> gate(True) -> work -> accounting
pending replay: gate(True) -> work -> accounting
held replay:    gate(True), refuses
held replay:    gate(True), refuses
fake summaries = persisted attempts_on_prefix = 2
```

Both successful gate calls, capture, work, and accounting hold the source lock. `gate(False)` does not change existing retry bytes or leave a reservation. The lock is acquirable after every invocation. There is **one additional admission event**, not two checks on every attempt: the first failure leaves a pending PREPARING transaction, so later invocations use the one-gate replay branch. Cursor's nine-event expectation is correct for this fixture. The unchanged original concurrency probes also pass: a competing caller cannot enter during accounting, and eight callers with failed accounting publication perform only three fake summaries.

**Round-4 R4-F1: closed for the original reproduction.** After two failed transforms, malformed retry JSON is preserved across three further calls, all returning `retry_state_unavailable`, with the summary count fixed at two. R5-F2 covers a different checkpointed, no-transaction case.

**Round-4 R4-F2: closed.** Six calls through the original transform-failure scenario leave zero snapshot files and bytes throughout; only the first two perform a fake summary. The hold no longer publishes a full snapshot on each refused call.

**Shared-helper checks that pass:** Claude's original round-24 cases agree between shortcut and full path for a clean unchanged prefix, legacy lineage, dropped/excluded processed entries, and changed transform fingerprint. Both first-run and post-commit session-identity mismatch cases refuse and log without new work or retained snapshots. Independent controls also confirm clean unchanged and incomplete-tail calls make zero new summaries; a valid append makes one in both arms; an oversized source refuses in both arms; a bootstrap grant against an existing checkpoint skips the shortcut and returns `bootstrap_not_required`, with zero extra summaries.

These passing checks establish the moved guard coverage for the exercised scenarios. They do not cover the omitted source revalidation or retry evidence in R5-F1/F2.

## Execution evidence and isolation

Implementation worktree: `/home/lauer/.kiro/audit-286-r5/code`, detached at the exact target. Report worktree: `/home/lauer/.kiro/audit-286-r5/docs`. Harness and outputs: `/home/lauer/.kiro/audit-286-r5/harness/`. The shared checkout was not switched or edited.

The runner retains the round-4 isolation approach: `env -i`, private HOME/TMPDIR, fake provider functions, closed-port provider URLs, disabled plugin autoload/bytecode/pytest cache, and a pre-import Python audit hook denying network calls and production-path opens while restricting Python writes to scratch. Repository fixtures redirect config and writer defaults. Real scratch Chroma, state files, and OS locks are exercised. The boundary is not a claim of exhaustive native-library syscall auditing.

Independent results:

- **Original round-4 harness, unchanged:** 6 passed, 1 failed, 2.52 s. The sole failure is the superseded lock-sequence assertion described above.
- **Retained corrective/Claude probes:** 24 passed, 6.96 s. Files: `tests/test_zz_codex_audit_r4.py`, `tests/test_zz_claude_verify23.py`, and the extracted round-24 appendix.
- **Focused route/recovery/inventory suite:** 115 passed, 19.45 s. Files: `test_incremental_jsonl_live_boundary.py`, `test_incremental_jsonl_codex_rollout_route.py`, `test_issue_286_stage2_wedge_probes.py`, `test_issue_286_stage2_corrective12.py`, `test_r2b_v2_corrective_viii.py`, `test_r2b_v2_implementation_revision.py`, `test_shadow_writer_coverage_scan.py`, `test_shadow_writer_gate_c3.py`, `test_incremental_jsonl_canary_baseline.py` (all under `tests/`).
- **Final independent round-5 probes:** 6 passed, 8 failed, 7.77 s. Three source-race cases fail for R5-F1; four retry-state cases and one natural-hold case fail for R5-F2. Reservation semantics and five nonfaulted/bootstrap controls pass.
- **Same final eight differential cases at `74c8ee7`:** 8 passed, 6 deselected, 7.39 s. Source races refuse; hold-clearing occurs in both baseline arms. This distinguishes new and inherited behavior rather than treating every passing equality check as safety evidence.
- **Whitespace and checkout:** `git diff --check 74c8ee7 a89f573` passed; the exact-tip implementation worktree remained clean.

No full-suite rerun, coverage census, deployment-state census, or production canary was performed. No live indexing, provider requests, production data writes, config/service changes, or implementation fixes were performed. Required startup doctor/brief/unresolved checks were orientation only; doctor exited 0. Track A indexing is deliberately withheld under Ryan's task-specific scratch-only/no-live-indexing/no-provider-calls restriction. No ledger record was written.

## Reproduce

The original round-4 file remains at its requested path. New probes live in scratch, not the report branch. Each command should use a new, unused `--basetemp` under the round-5 scratch root.

```bash
# Original harness unchanged against a89f573 (expected: 6 pass, sequence assertion fails).
bash /home/lauer/.kiro/audit-286-r5/harness/run-tests.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r5/harness/reproduce-original \
  -q -s /home/lauer/.kiro/audit-286-r4/harness/test_audit_r4.py

# Independent findings and controls (expected: 8 fail, 6 pass).
bash /home/lauer/.kiro/audit-286-r5/harness/run-tests.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r5/harness/reproduce-r5 \
  -q -s /home/lauer/.kiro/audit-286-r5/harness/test_audit_r5.py

# Identical differential cases at retained round-4 revision 74c8ee7.
bash /home/lauer/.kiro/audit-286-r5/harness/run-baseline.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r5/harness/reproduce-baseline \
  -q -s /home/lauer/.kiro/audit-286-r5/harness/test_audit_r5.py \
  -k 'unchanged_preserves_gate or natural_source_hold or revalidates_source'
```

The baseline lacks the new shortcut method; the probe uses a no-op method returning `None` in both baseline arms, leaving the old full path intact. At the target, the enabled arm uses the real method and the disabled arm changes only that method to return `None`. Each arm starts with its own fresh source/store and restores monkeypatches afterward.

Final artifact SHA-256 values:

- `test_audit_r5.py`: `80123bdfd265bcb37d20638f9b9a38ffc109e4afff7a86094bf6a368dcf45e94`.
- `test_claude24.py`: `e93821adf4c11b81f27fcb175cad3c081506f60ff6c784331503914d212b3042`.
- `run-tests.sh`: `79bd1013a135d47af4e99fb13b22b11dc39aef06da35dadaf31d21342efc3d23`.
- `run-baseline.sh`: `ac2438ca8519af3abb6bdc22575573a02b66427a3a7e6f30b123a9a48485826f`.
- `sitecustomize.py`: `59054a46cc46d142a2898c7ce8b137b5df054a8c71e78e5fc863e8b5ec7ddb23`.

Final outputs: `original-results.txt`, `retained-results.txt`, `focused-results.txt`, `final-results.txt`, and `baseline-final-results.txt` under the round-5 harness directory. Earlier diagnostic runs remain alongside them. The scenarios above describe the real state transitions and fault injection needed to reconstruct the tests if local scratch files are unavailable.

## [Arc Codex #286] Handoff

I finished: round-5 safety re-audit at exact `a89f573` — **FAIL**.
Next step: Ryan dispositions the two findings and routes corrections/recheck.
Next lane: Ryan; Cursor for implementation if authorized.
See my work: this report's R5-F1 and R5-F2 reproduction evidence.

Branch: `docs/2026-10-15-issue-286-stage2-fixes-audit-r5`. Final commit and explicit-refspec push verification are supplied in the chat handoff. No PR was requested or created.

### Optional PR text for later use

**Title:** Document unchanged-path safety gaps in Stage 2 indexing

**Description:** Ryan can use this round-5 FAIL report to disposition the remaining shortcut gaps before accepting Stage 2. Codex audited Cursor's exact `a89f573` implementation on 2026-10-15, reran the unchanged round-4 harness and Claude's round-24 appendix, and compared independent probes with the full path and prior revision. The old findings close and the adapted lock control passes. The new shortcut omits source revalidation; inherited retry-hold clearing also contradicts the current full path. Only this report changes.

Validation: 24 retained tests and 115 focused route/recovery/inventory tests pass. New probes yield six passes and eight failures across two findings. Baseline comparisons distinguish the source-race regression from inherited hold-clearing. Scratch only; no full-suite or production run.

**TL;DR:** [Arc Codex #286] Documentation only; FAIL on source revalidation and retry-evidence preservation, with prior blockers closed.

## TL;DR

- [Arc Codex #286] **FAIL at `a89f573`:** the shortcut acknowledges source changes the full path refuses, and clears retry evidence the current full path preserves.
- Source-race acceptance is new since round 4. Hold-clearing is inherited; a natural hold can be cleared and subsequent transform work re-admitted.
- Both original round-4 blockers close; Cursor's adapted lock control is valid. Report only, scratch probes retained, no PR or live operation.

<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc orientation, no activation authority -->
<!-- src: /home/lauer/.kiro/audit-286-r4/docs/docs/inter-model/CODEX-2026-10-15-issue-286-stage2-fixes-audit-r4.md, /home/lauer/.kiro/audit-286-r5/harness/test_audit_r5.py, /home/lauer/.kiro/audit-286-r5/harness/final-results.txt, /home/lauer/.kiro/audit-286-r5/harness/baseline-final-results.txt — prior findings and independent reproductions -->
<!-- src: /home/lauer/.local/share/convmem/worktrees/docs-2026-10-12-issue-286-stage2-fixes-handoff/docs/inter-model/CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md — supplied round-24 verification at 382264d -->
