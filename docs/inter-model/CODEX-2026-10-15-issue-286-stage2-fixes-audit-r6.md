# [Arc Codex #286] Stage 2 safety re-audit — round 6

**Verdict: FAIL at `d5d10b54c98cacafd886707f3e1e39246322823d`.**

**Auditor:** Codex, under Ryan's explicit round-6 request. **Implementation owner:** Cursor.
**Date:** 2026-10-15, America/Chicago. **Specification:** Claude round 25 at `8121f68d83bf49d58ded76cef30d15beae87a343`.

Corrective 19 closes both round-5 findings in the unchanged original probes. All seven original round-4 tests pass, including the original lock sequence. Thirteen original round-5 tests pass; its obsolete `reserve`-based control fails as expected, and Cursor's replacement passes with the requested ten events.

The additional `SourceCaptureError` classification change **widens retry admission**: alternating real capture errors now reset failure counters, permitting a later paid retry that the previous revision refuses. Separately, the final code follow-up leaves the committed coverage inventory stale. These findings need disposition before accepting this exact tip.

## Scope and exact revisions

- **Audited implementation:** fetched `origin/fix/2026-10-12-issue-286-stage2-wedge-fixes`, exactly `d5d10b54c98cacafd886707f3e1e39246322823d`. Reviewed the seven-file delta from round-5 tip `a89f5739c5fbfbf59827fbe85accb6d42b36c142`: corrective code `8da61de`, inventory/baseline `c252b22`, and code follow-up `d5d10b5`.
- **Normative corrective:** Claude's round-25 section in `docs/inter-model/CLAUDE-2026-10-12-issue-286-stage2-fixes-verify.md`, read with `git show 8121f68:...` from the fetched handoff branch. No subsequent Claude verdict is substituted for independent testing.
- **Report branch:** `docs/2026-10-15-issue-286-stage2-fixes-audit-r6`, created using `convmem work start ... --worktree` from fetched `origin/main` at `c6f07241ccf1a71d9d874fee963a37b04091b3ce`. This report is the only tracked change. No PR, merge, implementation edit, runtime promotion, or activation is authorized by this audit.
- **Arc orientation:** read the Arc Codex STATUS brief, prior round-5 report, and local reproduction/verification guidance. The STATUS brief's older operational narrative is not evidence of current deployment. The branch's conflict with main is explicitly outside this audit.

All implementation line references below refer to `d5d10b5`. The shared checkout was not switched or edited.

## R6-F1 — Medium: finer capture-error codes weaken the existing retry hold

**Locations:** `incremental_jsonl.py:2703–2705` and `:2973–2979`; `incremental_retry_state.py:337–354`.

The new catch assigns `exc.code` to `last_failure_code` and returns a refusal result. The router then passes that specific code to `record_incremental_retry_failure`. That function uses exact error-code equality for **both** the same-prefix `consecutive` counter and `source_consecutive`. Before this change, these capture failures shared `unexpected_SourceCaptureError`.

Changing the stored code is therefore a retry-policy change, not just a diagnostic improvement. Alternating `source_truncated` and `validated_prefix_mutated` resets both counters to one. Capture fails before a paid-attempt reservation, so `attempts_on_prefix` remains zero and cannot close the gap.

**Independent reproduction:** `test_alternating_real_capture_errors_do_not_reopen_admission` in `/home/lauer/.kiro/audit-286-r6/harness/test_audit_r6.py`.

1. Create a fresh admitted scratch Codex rollout using the repository route fixture and fake providers. Save its bytes. There is no checkpoint or pending transaction.
2. Before each invocation, restore those same bytes in place. Thus admission sees the same complete prefix and inode each time.
3. Wrap the real format parser. After parsing the captured bytes, alternately truncate the live source to its metadata line or change one valid message byte without changing the inode or length. Return the real parsed view. The actual `_capture` and `_revalidate_live_prefix` detect the fault; neither error classification, admission, nor accounting is mocked.
4. Invoke six times, recording the real retry state after each failure. Remove the parser wrapper, restore the original bytes, and invoke once more without any state clear or operator release.

**At `d5d10b5`:** all six capture attempts run. Their stored codes alternate between `source_truncated` and `validated_prefix_mutated`; both counters stay at one. Each route call raises `live_route_refused`, but the persisted gate does not hold the next invocation. The seventh, quiet call returns `processed`, performs **two fake summaries**, and clears retry state.

**At baseline `a89f573`, with the identical probe:** only two capture attempts run. Both store `unexpected_SourceCaptureError`, reaching `consecutive=source_consecutive=2`. The remaining four attempts and the final quiet retry refuse before capture. There are **zero fake summaries**, and retry state remains.

This is a deterministic coordinator/router admission regression. No transform runs during the faulty captures, and the eventual transform consumes a restored valid source. The finding is the lost hold and additional admitted work, not corrupted output. The probe deliberately invokes the route repeatedly; it does not claim that the watcher automatically retries a terminal quarantine. A first-call `live_route_refused` marker can be stricter for that outer watcher while the persisted coordinator hold is weaker for subsequent invocations.

**Required correction:** retain the previous capture-failure grouping for admission/accounting, or provide an explicitly reviewed retry-equivalent grouping while preserving specific codes as diagnostics. Cover alternating capture failures and existing retry records when changing the accounting key. No fix was made in this audit.

## R6-F2 — Low: the final follow-up invalidates the committed coverage inventory

**Artifact:** `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json`, refreshed by Cursor at `c252b22`, before the last `incremental_retry_state.py` change at `d5d10b5`.

At the requested tip, the committed `code_revision` is `d2e43fba10446658e9d92a5888e9a7829c2e615e`, while the independent resolver and regenerated in-memory inventory produce `9f2861e3e3fa5deaf078bb8be8603bf54feb9715`. These are inventory content identities, not branch commit SHAs.

Five existing tests fail on that mismatch:

- `tests/test_r2b_v2_corrective_viii.py::R2bV2CorrectiveVIIIIdentityTests::test_committed_inventory_matches_authority_content_identity`
- `tests/test_r2b_v2_corrective_viii.py::R2bV2CorrectiveVIIIRegressionGuard::test_inventory_artifact_exists_on_disk`
- `tests/test_r2b_v2_implementation_revision.py::R2bV2ImplementationRevisionTests::test_committed_inventory_matches_resolved_implementation_identity`
- `tests/test_r2b_v2_implementation_revision.py::R2bV2ImplementationRevisionTests::test_production_coverage_uses_committed_inventory_without_dual_mock`
- `tests/test_r2b_v2_implementation_revision.py::R2bV2ImplementationRevisionTests::test_regenerated_inventory_matches_on_disk_artifact`

At exact `c252b22f090087f3a180f3f64ea03cffbfce2e27`, both affected modules pass all 18 tests under the same runner. The only subsequent tracked change is the retry-state follow-up. This establishes stale evidence at the requested tip, independently of the later merge with main. The canary baseline test passes at `d5d10b5`.

**Required correction:** regenerate the coverage inventory after the final code change and rerun these identity checks. This is stale acceptance evidence, not a demonstrated writer-gate bypass. The retry-admission finding independently requires FAIL even after the inventory is refreshed.

## Split, shortcut, and replacement-control rulings

**Read-only split: PASS for the reviewed implementation and exercised cases.** `check_incremental_retry_gates` only inspects/reads the retry-state path and applies refusals; it does not call the write-availability probe, reserve, clear, or publish a file. Nine additional direct probes cover missing state, an empty object, benign state, corrupt JSON, a directory at the state path, prefix cap, same-error hold, source-wide hold, and an injected read-permission failure. Each checks unchanged directory entries, file bytes, and modification times while making every retry writer/availability helper fail if invoked. All nine pass. The directory refusal confirms the final `d5d10b5` follow-up.

**Ordering and lock coverage: PASS.** `run()` invokes the read-only check at `:2697` before the shortcut at `:2698`, inside the source-lock region. Pending transactions take the enforcing gate at `:2694`; they do not enter the shortcut. The router retains the lock through success-clear/failure-accounting and releases it afterward. The original round-4 lock, concurrency, failed-accounting cap, success-clear, snapshot, and cache controls all pass unchanged.

**Source revalidation and prior findings: PASS for the reproductions.** The shortcut calls `_revalidate_live_prefix` at `:2640` immediately before constructing `unchanged`; a caught capture/incremental error falls through to the full path. All three original truncate/rewrite/rotate cases now refuse with retry state retained and zero additional fake summaries in both arms. All four seeded hold/corruption cases and the natural source-hold case also agree with the full path. Thus R5-F1 and R5-F2 close for their original reproductions.

Retained differential controls cover clean unchanged, append, partial tail, oversized source, bootstrap against an existing checkpoint, processed lineage changes, dropped/excluded processed entries, transform fingerprint changes, and session identity mismatch. They pass. No additional shortcut-only success/work/evidence divergence was found in these checks. This is bounded evidence, not a claim to have exhausted every source/filesystem interleaving; R6-F1 is independent of the shortcut and reproduces without a checkpoint.

**Cursor's replacement control: PASS.** Spying `_check_live_retry_admission_if_needed` is appropriate for the coordinator-level sequence: the module-level check is also invoked internally by each enforcing gate. Counting those nested calls as additional top-level admission phases would misdescribe the sequence. The observed events are exactly:

```text
check, capture, gate, work, account, gate, work, account, gate, gate
fake summaries = persisted attempts_on_prefix = 2
```

The replacement asserts the source lock at each phase, unchanged retry bytes around the early check, and lock release after every invocation. The independent nine-case test separately covers the module helper's no-write contract. The obsolete original round-5 spy requires `kw['reserve']`, which the new API intentionally removes; its one expected failure is not a new implementation finding.

## Executed evidence and isolation limits

Scratch root: `/home/lauer/.kiro/audit-286-r6/`. Implementation worktree: `code/`, detached at `d5d10b5`. Inventory baseline: `inventory-base/`, detached at `c252b22`. The retained round-5 `code/` worktree supplies exact `a89f573` for the new differential probe. Report worktree: `docs/`. Runners, probes, and output files are in `harness/`.

The test runner uses `env -i`, private HOME/TMPDIR, fake providers, closed-port provider URLs, disabled plugin autoload/bytecode/pytest cache, and a pre-import Python audit hook denying network calls and live-data-path opens and restricting Python writes to scratch. Repository fixtures redirect config and writer defaults. Real scratch Chroma, retry state, and OS locks are exercised. This boundary is not exhaustive native-library syscall auditing.

- Original round-4 file, unchanged: **7 passed**, 2.36 s; `r4-results.txt`.
- Original round-5 file, unchanged: **13 passed, 1 expected obsolete-control failure**, 8.66 s; `r5-results.txt`.
- Cursor's round-5 replacement plus retained Claude rounds 23/24: **28 passed**, 12.49 s; `retained-results.txt`.
- New round-6 probes: **9 passed, 1 failed** (R6-F1), 1.86 s; `r6-results.txt`.
- Identical new capture-failure probe at `a89f573`: **1 passed, 9 deselected**, 1.54 s; `baseline-results.txt`.
- Focused route/recovery/inventory suite: **110 passed, 5 failed** (R6-F2), 19.75 s; `focused-results.txt`.
- Both inventory modules at `c252b22`: **18 passed**, 9.66 s; `inventory-baseline-results.txt`.
- `git diff --check a89f573 d5d10b5`: PASS. The implementation worktree remained clean.

No full-suite rerun, production canary, live indexing, config/service change, or implementation correction was performed. Track A indexing was withheld because Ryan's task-specific restriction prohibits live indexing/provider calls; no ledger record was written.

**Auditor scope deviation:** after the required doctor/brief/unresolved orientation, I also ran `convmem "issue 286 round 5 shortcut retry admission audit"`. That corpus search ran outside the isolated test runner, used the embedding/search path (`query.py` calls `ollama_embed`), emitted a Hugging Face Hub warning, and returned corpus results. It should have been omitted under this task's no-provider restriction. It was disclosed in chat; no further corpus searches or indexing calls followed. Accordingly, this report claims provider/network isolation for the tests, **not** zero provider or external activity for the entire session. It does not assert a production-write census for that orientation search. The safety verdict rests on the isolated probes and pinned local code, not the search results.

## Reproduction

Use a new unused `--basetemp` on each invocation. The runners pin their code worktrees; they do not use the shared checkout.

```bash
bash /home/lauer/.kiro/audit-286-r6/harness/run-tests.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r6/harness/reproduce-r4 \
  -q -s /home/lauer/.kiro/audit-286-r4/harness/test_audit_r4.py

bash /home/lauer/.kiro/audit-286-r6/harness/run-tests.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r6/harness/reproduce-r5 \
  -q -s /home/lauer/.kiro/audit-286-r5/harness/test_audit_r5.py

bash /home/lauer/.kiro/audit-286-r6/harness/run-tests.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r6/harness/reproduce-control \
  -q -s tests/test_zz_codex_audit_r5.py

bash /home/lauer/.kiro/audit-286-r6/harness/run-tests.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r6/harness/reproduce-r6 \
  -q -s /home/lauer/.kiro/audit-286-r6/harness/test_audit_r6.py

bash /home/lauer/.kiro/audit-286-r6/harness/run-baseline.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r6/harness/reproduce-baseline \
  -q -s /home/lauer/.kiro/audit-286-r6/harness/test_audit_r6.py -k alternating

bash /home/lauer/.kiro/audit-286-r6/harness/run-tests.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r6/harness/reproduce-inventory \
  -q tests/test_r2b_v2_corrective_viii.py tests/test_r2b_v2_implementation_revision.py

bash /home/lauer/.kiro/audit-286-r6/harness/run-inventory-base.sh \
  --basetemp=/home/lauer/.kiro/audit-286-r6/harness/reproduce-inventory-base \
  -q tests/test_r2b_v2_corrective_viii.py tests/test_r2b_v2_implementation_revision.py
```

SHA-256 identities:

```text
original test_audit_r4.py  fb7726ec3fa4170314568928d230d872e0f6364ac18e1463b002a3bb176e64bd
original test_audit_r5.py  80123bdfd265bcb37d20638f9b9a38ffc109e4afff7a86094bf6a368dcf45e94
new test_audit_r6.py       4fe4ea54d5c6537541ef6e9e8899fccfeeaac9f8f14457655a025c6266de118d
run-tests.sh              4920c381fa9bed36f29c2e3a4570db34d2431760da4cd308d2eea330a7ad3859
run-baseline.sh           e3fcaaab4c2b66cb96afd2b91ae6342ef8ea97c6325e2facb59816954310175a
sitecustomize.py          2030c2ecc8452457112fcc360b249fc35d1cfa16c9e392a835515fef35c3ab14
```

## [Arc Codex #286] Handoff

I finished: round-6 safety re-audit at exact `d5d10b5` — **FAIL**.
Next step: disposition the capture-error retry widening and refresh the final inventory after authorized correction.
Next lane: Ryan; Cursor for implementation if authorized.
See my work: this report's R6-F1 reproduction and R6-F2 identity-check results.

Branch: `docs/2026-10-15-issue-286-stage2-fixes-audit-r6`. Commit and explicit-refspec push confirmation are supplied in the chat handoff. No PR was requested or created.

Optional later PR title: **Document remaining retry-policy and inventory gaps in Stage 2**.

Optional later PR description: Codex's 2026-10-15 round-6 report lets Ryan disposition Cursor's exact `d5d10b5` corrective before acceptance. Both round-5 findings close and the replacement lock control passes. A new baseline differential demonstrates that specific capture-error codes weaken the existing retry hold; five existing checks also find the final inventory stale. This is a report-only change with scratch reproduction commands. **TL;DR:** [Arc Codex #286] FAIL; preserve capture-failure accounting semantics and refresh inventory after the final code change.

## TL;DR

- [Arc Codex #286] **FAIL at `d5d10b5`:** alternating capture errors no longer build the former hold; a quiet retry performs work that `a89f573` refuses.
- The final follow-up also leaves the coverage inventory stale: five identity checks fail, while all 18 tests in those modules pass at `c252b22`.
- Original round 4 passes 7/7; round 5 passes its 13 applicable tests; Cursor's replacement control and the prior shortcut reproductions pass. Test execution was isolated; the separate orientation-search scope deviation is disclosed above.

<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc orientation, no activation authority -->
<!-- src: /home/lauer/.kiro/audit-286-r5/docs/docs/inter-model/CODEX-2026-10-15-issue-286-stage2-fixes-audit-r5.md — prior findings and baseline -->
<!-- src: /home/lauer/.kiro/audit-286-r6/code/incremental_jsonl.py, /home/lauer/.kiro/audit-286-r6/code/incremental_retry_state.py — exact d5d10b5 implementation -->
<!-- src: /home/lauer/.kiro/audit-286-r6/harness/test_audit_r6.py, /home/lauer/.kiro/audit-286-r6/harness/r6-results.txt, /home/lauer/.kiro/audit-286-r6/harness/baseline-results.txt, /home/lauer/.kiro/audit-286-r6/harness/focused-results.txt, /home/lauer/.kiro/audit-286-r6/harness/inventory-baseline-results.txt — independent reproduction evidence -->
