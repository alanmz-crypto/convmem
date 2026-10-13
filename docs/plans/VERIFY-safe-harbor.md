# Verify Plan — Safe Harbor

> **Arc: Safe Harbor. T1/T2 ACCEPTED AND MERGED; CORRECTED T3 PROOF RETURNED.** The V2 acceptance/squash record remains authoritative for T2. The corrected T3 ordering-gate evidence at `93d4e34` has nine qualified passes and focused lint exit 0, with exclusions and limits below. Historical reviews retain their exact scopes. V3, the remainder of V4, V5/V6 are NOT RUN; owner acceptance and any remaining T3 grant are pending.

```text
Planning Status
Phase:        T3 corrected proof returned; owner decision pending
Characters:   Implementer, Reviewer
Function:     Record qualified proof, failed attempts and evidence limits
Lanes:        Cursor/Codex jointly corrected proof; Ryan receives results
Authority:    T3 proof-only grant; no remaining implementation or live grant
```

**Historical reviewed subject:** `677c8a0d17618166c454b4523d6767e48cfa330a`, base `db8aebbfb9ac20afb081bd43bf42315a1524ac9b`. T1 runtime changes are at `496792fad80d9759ca26e5cbf2ad7d6cd60bc28e`; subsequent CI correction changed the test harness and derived inventory. Initial candidates remain historical. **Successor correction code:** `8b410445ac55f3a5dafede030a40f26c318ae784` (tests only; parent chain `0347328` → `95486a6` → `8b41044`). Copilot's delta review PASSed the corrections at `2977c4531cf446974b0c86994dbca757715dca76` (85%, static). **Integration:** merge commit `c624e2f39a2f76a18eacca76d9affb7f7dff6f50`, parents `5d0209033c50adb48d7d39f107aa84504514f29e` (branch) and main `5550def70c72bc7a60f0c5216b46cd4cf629f5d2`. Its final candidate `0c7b4e2` received fresh CI and the integration review recorded below; the earlier PASS was not automatically transferred.

**PR:** [#387](https://github.com/alanmz-crypto/convmem/pull/387), squash-merged by Ryan at `05aa2c86e2d01c9a9f5259b1f505833d7f28563d` on 2026-10-12 05:13:16 UTC. The squash and final candidate have identical trees.

**Direction:** [ARCHITECTURE-safe-harbor.md](ARCHITECTURE-safe-harbor.md), approved at `5ea16a6`.

**Plan:** [EXECUTION-safe-harbor.md](EXECUTION-safe-harbor.md).

**Goal:** demonstrate the approved guard/recovery behavior without extending coverage or claiming unperformed recovery.

## Human consequence

T1's incident retention and T2's operation-bound preflight are landed source. Evidence preservation, validated owner release and unavailable/tombstoned approval-recovery handling remain later planned tasks. Rollout, actual recovery qualification and arc closure remain separate.

Who: Cursor supplied T1/T2 implementation evidence; GitHub supplied CI; Copilot/Codex reviews and Ryan's exact acceptances retain their scopes below. Cursor/Codex jointly corrected the T3 proof; the qualified result is returned without claiming independent review. V3, the remainder of V4, V5/V6 remain unrun.

## Scope lock

In scope: execution T1–T5 and their named production entrypoints under isolated fixture configuration. Out of scope: live corpus, service activation, new backup repositories, drive writes, live restore, T4/V4k, v3 activation, global freeze or broad permission changes.

## Verification design

- **Independent oracle:** fixture logical rows/documents/vectors/tombstones and export bytes; separate event reduction; durable marker/evidence file hashes; fresh-process admission results. Source identity and file existence alone do not prove behavior.
- **Failure injection:** barriers around native admission/recheck, every preservation/replacement and release publication edge; process termination/restart; short write, ENOSPC and fsync failures. Hardware power-loss durability is not implied by process-kill trials.
- **Negative controls:** no-op preflight, overwrite-single-incident marker, copy-over-original retry, census-only release, stale-disposition replay, approval retry that assumes a failed append rolled back, and state recheck moved outside the guard. Each must fail the corresponding independent assertion.
- **Dual-path coverage:** CLI add/upsert and indexed approval, CLI/direct approval recovery, guarded native mutation, audit, recover/reconcile/clear script and watch's recovery caller. Restic tests cover all five distinct consumers. Name any inaccessible path as a gap.

## V0 — Preconditions and external review

**Plan prerequisites satisfied:** Ryan accepted the plan and explicitly approved v2 B-E4.1 at `dca13a59a2edf649ac6a19777f572645bea8674e`, including all five consumer outcomes, with ownership unchanged. This is approval metadata, not runtime evidence.

**T1 grant satisfied:** the completed T1/Cursor scope and corrections are recorded in execution section 8. **T2 grant recorded:** Ryan subsequently granted isolated T2 implementation and V2 evidence; section 9 records its boundary. T3 now has only the separate proof/evidence grant in execution section 10; remaining T3 and T4/T5 have no grant. The external-review row below describes T1 only. T2's historical Copilot audits and final Codex review are recorded in V2; Ryan resolved its separate BugBot gate with the final-tip exception recorded below.

Isolated V1 ran. Production CLI, MCP, session indexing, Restic, providers, services and external drives were not invoked.

| Field | Value |
|---|---|
| `gate_applicability` | `required` |
| `reason` | T1 changes quarantine persistence, admission control flow, and lock ordering |
| `subject_tip_sha` | `0c7b4e263dff12f8e1a6b2d485616153ed096b66` |
| `bugbot_reviewed_sha` | `n/a` — both attempts hit quota and reviewed no SHA |
| `result` | satisfied by Ryan's written exact-tip acceptance of Copilot as the BugBot outage exception; not a BugBot PASS |
| `finding_disposition` | two test advisories corrected and delta-PASSed at `2977c45`; final integration delta PASS at `0c7b4e2` (82%, static), no blocking/new actionable regression |
| `authority_reference` | Ryan's exact acceptance quoted in Final-tip CI, review and owner acceptance below; subsequently Ryan merged PR #387 |

Acceptance is bound to the named candidate. Codex confirmed the squash commit has the same tree; this does not transfer evidence to future edits or authorize deployment.

## V1 — Incident authority (T1)

**Historical run RECORDED by Cursor for runtime `fa82028b762e5564eed9f2884336ccfb0e3caf73`.** Isolated pytest exit 0: `41 passed in 40.45s`. Interpreter `/home/lauer/miniforge3/bin/python` 3.13.12; chromadb 1.5.9; numpy 2.4.4. Fixture roots were pytest temporary directories under `/tmp`, with `HOME`, `XDG_*`, `CONVMEM_CONFIG` and `CONVMEM_ROOT` pointed at a fresh `/tmp/safe-harbor-t1-*` directory and `CONVMEM_T1_ISOLATED=1`. The suite refuses `/home/lauer/.local/share/convmem` and `runtime-main`. Codex did not rerun these tests during the static handoff check.

**Corrected run RECORDED for runtime `496792fad80d9759ca26e5cbf2ad7d6cd60bc28e`.** Isolated pytest exit 0: `43 passed in 43.56s`. Same interpreter and isolation as the historical run (`/tmp/safe-harbor-t1-2J2Z`). The initial 41-test run does not by itself accept these three checks.

Command:

```bash
iso=$(mktemp -d /tmp/safe-harbor-t1-XXXX)
mkdir -p "$iso/home" "$iso/config" "$iso/data" "$iso/cache"
export HOME="$iso/home" XDG_CONFIG_HOME="$iso/config" XDG_DATA_HOME="$iso/data" \
  XDG_CACHE_HOME="$iso/cache" CONVMEM_CONFIG="$iso/config/config.toml" \
  CONVMEM_ROOT="$iso/root" CONVMEM_T1_ISOLATED=1
unset DEEPSEEK_API_KEY OPENAI_API_KEY
python -m pytest tests/test_safe_harbor_t1.py tests/test_chroma_write_guard.py -q --tb=line
```

| Case | Result |
|---|---|
| Incident A then B, including two findings on one segment; fresh-process admission refused | PASS. The isolated overwrite publisher left only finding B; `assert_findings_retained` raised `missing findings` for A, which is the expected control failure. The real publisher then kept both ids and a fresh process stayed refused |
| Missing marker versus null, scalar, empty object, unknown schema, invalid set, wrong target, unreadable file, and recognized legacy bytes preserved on adoption | PASS |
| Canonical aliases share one guard and lock; a competing legacy guard directory is reported and no empty canonical authority is created | PASS, including real `ChromaStore` construction through the alias |
| Audit failure, then pass, skipped, and diagnostic error, leaves the marker in place | PASS |
| `recover()` and guarded write recheck after the lock, using a ready/release barrier rather than a timed guess | PASS |
| Audit holds the native lock across publication while a concurrent guarded write does not land | Historical run PASS; contention proof INCOMPLETE: writer readiness was not established before releasing the audit. Corrected at `8b41044`; see the review-evidence correction below |
| Short write, file fsync failure, and directory fsync failure raise containment unavailable, do not claim a durable stop, and do not apply the requested mutation | PASS |
| Ordinary clear and the guard/audit doctor checks do not rewrite a present or malformed marker | PASS |
| Existing guard regression file, including restore, quarantine, and audit behavior that T1 still allows | PASS (`tests/test_chroma_write_guard.py`, included in the 43) |
| Alias and canonical `ChromaStore` construction share one client-cache identity; the alias write is visible to the older client; a competing lexical guard still refuses and creates no canonical authority | PASS |
| Persisted schema-valid empty incident set: fresh-process admission refused, requested summary absent, marker bytes unchanged; a missing marker still admits | PASS |

Gaps, not passes:

- Process barriers and injected fsync failures are not hardware power-loss proof.
- A directory fsync failure can leave marker bytes visible while the operation reports containment unavailable. Callers must not treat that file as a durable stop.
- Successful segment restore can still continue the caller's write. Making every restore stick as an incident is T3, and it was not implemented.
- The full default pytest suite and production doctor were not run locally. GitHub CI runs `python -m pytest -q` with `CONVMEM_CONFIG` pointed at an empty CI config.

## CI correction

PR #387’s pytest job on `0bcf50e` failed in two ways. The T1 tests required `CONVMEM_T1_ISOLATED=1`, which standard pytest does not set. The committed writer-coverage inventory did not match the identity of this branch merged with main `db8aebb` (watch-diagnosis #385).

The tests now create a fresh home, config, and data directory for each test and its children, then still refuse production corpus, production home, and runtime-main paths. They do not skip. `write_v2_inventory_file()` regenerated `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` after merging main. Route policy and the identity algorithm were not edited. The regenerated `code_revision` is `43a3944df8d6264dfc3a25016ab9b48111f69688`.

Local command, with `HOME=/home/lauer` and `CONVMEM_T1_ISOLATED` unset:

```bash
python -m pytest tests/test_safe_harbor_t1.py tests/test_chroma_write_guard.py \
  tests/test_r2b_v2_corrective_viii.py tests/test_r2b_v2_implementation_revision.py -q --tb=line
```

Result: exit 0, `61 passed in 50.90s`. Interpreter `/home/lauer/miniforge3/bin/python` 3.13.12.

## Copilot review and authorized evidence correction

**Static review:** GitHub Copilot audit lane, exact subject `677c8a0d17618166c454b4523d6767e48cfa330a`, base `db8aebbfb9ac20afb081bd43bf42315a1524ac9b`; PASS at 72% confidence with advisories. No tests were executed by the reviewer. This is independent audit evidence, not Cursor BugBot or automatic satisfaction of its gate. The review identified two concrete test-evidence gaps that Codex checked and Ryan directed Cursor to correct:

- **Isolation cleanup:** `monkeypatch.undo()` in `test_publication_failure_aborts_before_mutation` also undoes the autouse fixture's environment isolation. The affected calls use scratch paths; no production mutation was demonstrated. The 61-pass report remains a test outcome, not proof that the fixture isolation stayed in force throughout every fault case.
- **Concurrency proof:** `test_audit_publication_excludes_a_concurrent_writer` releases the audit immediately after launching the writer. It does not establish that the writer reached and contended on the actual native lock before publication.

Ryan's instruction: **"correct both before merging"**. The bounded grant and acceptance requirements are in execution section 8. At the grant record, both corrections were not implemented; the historical rows above are preserved. Successor evidence follows.

### Review-evidence correction — successor evidence

**Subject:** test code `8b410445ac55f3a5dafede030a40f26c318ae784` on `fix/2026-10-11-safe-harbor-t1`. Only `tests/test_safe_harbor_t1.py` changed (`0347328..8b41044`); runtime code, the worker, CI workflows and the inventory are untouched. Interpreter `/home/lauer/miniforge3/bin/python` 3.13.12; chromadb 1.5.9; numpy 2.4.4. No production CLI, MCP, doctor, indexing, Restic, provider, service or drive operation ran.

**Isolation cleanup (fixed at `95486a6`).** `test_publication_failure_aborts_before_mutation` now gives the file-fsync, short-write and directory-fsync injections each their own `monkeypatch.context()`. It snapshots the fixture's `HOME`, XDG, `CONVMEM_CONFIG` and `CONVMEM_ROOT` values. Before every later project call it asserts those values, `Path.home()`, the production-path refusal and the absence of the removed provider keys. It also asserts each patched method is restored after its scope. Control `test_shared_undo_is_detected_as_lost_isolation` applies the old shared `undo()` and requires the isolation assertion to fail with `fixture isolation changed`; no project call follows it.

**Audit/writer contention (fixed at `8b41044`).** The writer child replaces `chroma_write_guard.fcntl` in its own process with a pass-through probe. The probe reports the first failed nonblocking and the first successful exclusive `flock` on the guard lock file through an inherited pipe: event kind, lock-file device and inode, whether the call ran inside `ChromaWriteGuard.native_write`, and whether `QUARANTINE.json` existed. The parent blocks on that pipe for up to 60 s using `select`; no sleep is used as proof. With the audit paused at its existing in-lock barrier, the proof requires all of the following:

- the writer's first event is `contended`, inside `native_write`, on the same device and inode the parent stats;
- the audit is still paused, no marker exists, and the parent's own nonblocking `flock` on that file is refused;
- only then is the audit released; events end as `contended`, `acquired`, and the marker already exists at `acquired`;
- the audit reports `fail`, the writer exits non-zero with a quarantine refusal, and `during-audit` is absent from `chroma.sqlite3`.

Child processes are killed in `finally` on every outcome. After the runs, `pgrep` found no leftover test children.

Observed events (scratch capture run outside the repository through the same helpers): positive `[contended (38, 635835) native_write=True marker=False, acquired (38, 635835) native_write=True marker=True]`.

**Negative control.** `test_unlocked_audit_pause_fails_the_contention_proof` uses a test-only audit child that waits at a barrier *before* taking the native lock, then audits under the lock. The writer's first event is `acquired` inside `native_write`, with no marker and the audit still paused. `assert_writer_contended_while_audit_paused` then fails with `writer acquired the native lock while the audit was paused; no contention` (raw scratch run: 1 failed in 2.39 s, no timeout; events `[acquired (38, 635543) native_write=True marker=False]`). The test requires that failure. The writer's own under-lock reconcile then refuses on the torn segment (`no validated save exists`). That is separate existing containment, not the audit.

Commands (worktree cwd):

```bash
# affected cases, standard pytest, real HOME, isolation flag unset (5 repeats of the contention pair: all 2 passed)
env -u CONVMEM_T1_ISOLATED -u DEEPSEEK_API_KEY -u OPENAI_API_KEY HOME=/home/lauer \
  /home/lauer/miniforge3/bin/python -m pytest tests/test_safe_harbor_t1.py -q --tb=short \
  -k "contention or concurrent_writer or publication_failure_aborts or shared_undo" -p no:cacheprovider

# regression set, standard pytest, real HOME (same files as the CI correction)
env -u CONVMEM_T1_ISOLATED -u DEEPSEEK_API_KEY -u OPENAI_API_KEY HOME=/home/lauer \
  /home/lauer/miniforge3/bin/python -m pytest tests/test_safe_harbor_t1.py tests/test_chroma_write_guard.py \
  tests/test_r2b_v2_corrective_viii.py tests/test_r2b_v2_implementation_revision.py -q --tb=line -p no:cacheprovider

# defense in depth: outer HOME/XDG/CONVMEM roots also under a fresh /tmp/safe-harbor-t1-bnMa
python -m pytest tests/test_safe_harbor_t1.py tests/test_chroma_write_guard.py -q --tb=line -p no:cacheprovider
```

| Run | Result |
|---|---|
| Affected cases (4) | exit 0, `4 passed, 17 deselected in 4.92s` |
| Contention pair, five repeats | exit 0 each, `2 passed` |
| Regression set, standard pytest, `HOME=/home/lauer` | exit 0, `63 passed in 50.57s` |
| Defense-in-depth outer isolation | exit 0, `45 passed in 49.69s` |
| `pylint tests/test_safe_harbor_t1.py` (4.0.6) | exit 0, after adding `too-many-lines` to the file's existing disable list |

The real-`HOME` run is the primary evidence, because an outer temporary home would hide a lost-isolation regression. A first regression attempt inside the agent command sandbox ran as uid 0. `test_read_error_blocks_and_is_not_absence` then failed its existing root precondition (`1 failed, 62 passed`). The recorded run is the same command as uid 1000. Process barriers and pipes order processes; they are not hardware power-loss proof.

**Remote evidence at the prior subject:** GitHub pytest, pylint, secret scan and CodeQL passed at `677c8a0`; [pytest job](https://github.com/alanmz-crypto/convmem/actions/runs/38196201314/job/114639276462). Codex read the check state; this was not a local rerun. The second authorized [BugBot attempt](https://github.com/alanmz-crypto/convmem/pull/387#issuecomment-6117256790) failed on quota (request `ea440898-d96f-4d3e-b3c3-a7c2d1c6a0a5`), reviewed no SHA and authorizes no further retry. Scope remains T1; no other Copilot advisory is silently added to this correction grant.

### Copilot delta review of the corrections

GitHub Copilot audit lane: **PASS, 85% confidence, static**, at exact subject `2977c4531cf446974b0c86994dbca757715dca76`. Codex relayed the verdict and recorded it in execution section 8. It covers the two test corrections only. It is not BugBot, not a review of the integration below, and not owner acceptance.

## Bounded branch update — integration evidence

**Why:** PR #387 conflicted with main `5550def` (PR #388, Codex rollout admission, off by default), so pull-request CI did not run on successors after `677c8a0`. Ryan authorized this bounded update (execution section 8).

**Merge:** `git merge --no-ff 5550def70c72bc7a60f0c5216b46cd4cf629f5d2` into `fix/2026-10-11-safe-harbor-t1` at `5d0209033c50adb48d7d39f107aa84504514f29e`. Result: merge commit `c624e2f39a2f76a18eacca76d9affb7f7dff6f50`. Merge base `db8aebb`; main's delta is the single PR #388 commit. Remote main and branch were rechecked before merging; no rebase or force-push.

| File | Resolution |
|---|---|
| `docs/inter-model/LATEST.md` | Conflict. Kept the Safe Harbor entry, then main's current Arc Codex PR #388 entry. Main had itself replaced the superseded 2026-10-09 Codex entry, so that entry was dropped. Versus main, the only difference is the added Safe Harbor entry |
| `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` | Conflict, generated. Took main's file, then ran the existing `write_v2_inventory_file()` on the merged tree. Versus main, only the 37 `code_revision` values and `inventory_digest` changed; routes and policy are identical |
| `doctor.py` | Auto-merged; the only source file both sides changed. The T1 diff (`db8aebb`→`5d02090`) and main's diff (`db8aebb`→`5550def`) each reappear unchanged when the merged file is compared with the other parent. Main adds `_check_incremental_refusals` and its registration; T1 changes the bodies of `_check_chroma_write_guard` and `_check_chroma_audit`. All three remain registered in `run_doctor`; `py_compile` passes. No semantic conflict |
| Other files | Changed on one side only; taken from that side. No Safe Harbor test or runtime file changed in the merge. The two corrected tests are intact |

**Inventory generator:** `eval_corpus/r2b_v2/coverage/inventory.py:write_v2_inventory_file()`, unmodified. Its identity is `compute_implementation_revision()`, a content manifest of governed source, not git HEAD. Its import closure (`chroma_write_store`, `config`, shadow modules) defines only unexpanded path constants at import time. It ran with `HOME`, XDG, `CONVMEM_CONFIG` and `CONVMEM_ROOT` under a fresh `/tmp/safe-harbor-inv-fJZC` (empty config; no files created under its home or data directories) and provider keys unset.

| Value | Main `5550def` | T1 `5d02090` | Integrated |
|---|---|---|---|
| `code_revision` | `6d7f85c93eae8858a2b0fc8f6df1389680360c95` | `43a3944df8d6264dfc3a25016ab9b48111f69688` | `87b8144dff3a6ec45fad5ef8a82e332d17bb4698` |
| `inventory_digest` | `85719da4…8f03e` | `55c7ae2e…3b8a` | `e7f544a0cc2c0bb985c8f67a1942d84f15542c8597070ca06c0d5d991f6862b0` |

On the merged tree, `verify_inventory_matches_tip()` and `verify_shadow_inventory_unchanged()` both returned `[]`. Missing categories, unlisted ctor/generation sites, undocumented sinks and route-sink errors are all empty.

**Regression at `c624e2f`** (worktree source, `/home/lauer/miniforge3/bin/python` 3.13.12, chromadb 1.5.9, numpy 2.4.4, uid 1000, `CONVMEM_T1_ISOLATED` unset):

```bash
env -u CONVMEM_T1_ISOLATED -u DEEPSEEK_API_KEY -u OPENAI_API_KEY HOME=/home/lauer \
  /home/lauer/miniforge3/bin/python -m pytest tests/test_safe_harbor_t1.py tests/test_chroma_write_guard.py \
  tests/test_r2b_v2_corrective_viii.py tests/test_r2b_v2_implementation_revision.py -q --tb=line -p no:cacheprovider
```

| Run | Result |
|---|---|
| Standard pytest, real `HOME`, T1 + guard + R2b identity | exit 0, `63 passed in 58.22s` |
| Defense in depth: T1 + guard with outer roots under `/tmp/safe-harbor-t1-Hao3` | exit 0, `45 passed in 41.47s` |
| `pylint` 4.0.6 `doctor.py` merged vs main's `doctor.py` | 14 findings each; same set except the `too-many-lines` count text (pre-existing message) |
| `pylint tests/test_safe_harbor_t1.py` | 0 findings |
| Leftover test children after runs | none |

The real-home run keeps uid 1000, so the chmod read-failure test keeps its meaning; the uid-0 sandbox was not used for recorded results. `tests/test_doctor.py` and PR #388's tests were not run locally because they are not shown fully isolated. GitHub CI runs the default suite. The disabled PR #388 feature was not activated. No production CLI, MCP, doctor, indexing, provider, Restic, service or drive operation ran.

## Final-tip CI, review and owner acceptance

**Final candidate:** `0c7b4e263dff12f8e1a6b2d485616153ed096b66`. **Landed source:** squash `05aa2c86e2d01c9a9f5259b1f505833d7f28563d`, PR #387, 2026-10-12 05:13:16 UTC. Codex checked GitHub's merged head/commit and compared the two trees: no diff.

**CI:** [pytest/pylint/secret-scan run](https://github.com/alanmz-crypto/convmem/actions/runs/38204173954) succeeded on the final candidate. [Pytest job](https://github.com/alanmz-crypto/convmem/actions/runs/38204173954/job/114663870324): `2970 passed, 75 skipped, 8 warnings, 252 subtests passed in 1989.89s`. Analyze (Python/actions) and CodeQL also succeeded. Codex read completed checks and the pytest log; no additional local suite was run for this record.

**Independent review:** Copilot audit lane, final-tip integration delta **PASS, 82% confidence**, static only. The review found no blocking/new actionable integration regression: `doctor.py` retains both parents' changes; derived inventory preserves routes/policy; main's incremental caller still uses the guarded writer path; routing retains both arcs. It builds on the full T1 audit at `677c8a0` and the two-test corrective delta PASS at `2977c45`. It does not re-audit PR #388's upstream design or prove hardware/power-loss durability. Codex separately confirmed the T1 guard/store/script/test files were unchanged by integration and the inventory differs from main only in derived identity/digest. The CLI review is not PR-native BugBot; BugBot reviewed no SHA.

**Ryan's exact-tip outage acceptance, supplied in this conversation:**

> I accept Copilot’s review as the BugBot outage exception for PR #387 at 0c7b4e263dff12f8e1a6b2d485616153ed096b66.

Ryan then reported “squash merge done”; GitHub confirmed MERGED with the head/commit above. This closes T1's delivery/review gate. It grants no T2–T5 implementation, production activation or live recovery. Older writers remain incompatible with the new authority, and T1 has no validated release workflow.

## V2 — Target binding and freshness (T2)

**T2 / V2 ACCEPTED AND MERGED.** The acceptance record below supersedes historical pending/draft routing in the evidence chronology. B1, F1/F2 and the governed-path blocker are closed in their pinned scopes. Successful event-only completion remains **NOT proven** (accepted V2 exclusion; T4 prerequisite).

### T2 final-tip CI, owner acceptance and squash mapping

- **Accepted subject:** `eb06c97df2cfe9de3627fd8672b9e3b7c277c963`, the final head of [PR #389](https://github.com/alanmz-crypto/convmem/pull/389). Runtime/evidence and bounded Codex delta PASS (95%) are pinned to `dac925f33d4ebd7482c0536408b9be12f51d6106`; the successor adds documentation only. This records an owner exception, not a claim that BugBot or the reviewer reviewed another SHA.
- **Final-head GitHub CI:** all six reported checks SUCCESS: pytest (3.12), pylint (3.12), secret-scan, Analyze (actions), Analyze (python) and CodeQL. [Test/lint run 38338522890](https://github.com/alanmz-crypto/convmem/actions/runs/38338522890) completed pytest at 2026-10-13 03:20:17 UTC; [CodeQL run 38338518783](https://github.com/alanmz-crypto/convmem/actions/runs/38338518783) also passed. No local tests were rerun for this documentation closeout.
- **Ryan's written acceptance:** “I accept the Codex review and T2/V2 at eb06c97df2cfe9de3627fd8672b9e3b7c277c963, including its documented evidence limitations, as the BugBot outage exception.”
- **External-review fields:** `gate_applicability=required`; `subject_tip_sha=eb06c97df2cfe9de3627fd8672b9e3b7c277c963`; `bugbot_reviewed_sha=n/a`; `result=satisfied by Ryan's written exact-tip outage exception`; `finding_disposition=B1/F1/F2 and final governed-path blocker closed in their recorded scopes; evidence exclusions retained`. BugBot hit quota and reviewed no SHA. No paid retry or PR-native Copilot request was made for this final candidate.
- **Observed merge:** GitHub reports MERGED at 2026-10-13 03:43:09 UTC (2026-10-12 local), squash `458b9f6bb0bf98048c11ac0baf46a2340dcdcbf3`. `git diff --stat eb06c97df2cfe9de3627fd8672b9e3b7c277c963 458b9f6bb0bf98048c11ac0baf46a2340dcdcbf3` is empty: identical trees. This maps the accepted candidate to main, not to any later runtime deployment.
- **Limits retained:** event-only completion success excluded; initial ambient/interrupted attempts remain unqualified; process/failure-injection evidence is not hardware power-loss proof. T3–T5, V3–V6 and all live operations remain ungranted/unperformed by this delivery.

### Historical T2 delivery and correction evidence

**Required evidence:** Target/profile/affected-path equality and coverage; prod/lab bypass behavior; changed config; all five consumer outcomes; old versus future snapshots; no future-triggered backup/fallback; unchanged exemptions. Require effect assertions through actual callers and existing numeric error mapping.

### Source identity

| Role | SHA | Content |
|---|---|---|
| Start | `9664878b4b4a64e86b98bbf25e041aa5393fea96` | T2 grant docs |
| Implementation | `77a590bed4a24ab5e84eec3e943c95e8179d3111` | gate binding, resolver freshness, five consumers, tests |
| Lint/structure | `262573ec10adf525a0e6f0eb3a554b87b43ac452` | pylint-neutral layout of admission helpers |
| **Final source** | `44e29f6d943c98a2425c21901c310c52ca5c5b1a` | layout-only `convmem.py` change + derived R2b inventory |
| Docs | `39cfccb` | policy docs, VERIFY/STATUS/LATEST |
| **Final fixture** | `2459acd2a6c12b0833ce67c85c80558ab9e00334` | event-only recovery fixture via real interrupted approval; tests only |

`2459acd` changes only `tests/_safe_harbor_t2_cli.py` and `tests/test_safe_harbor_t2.py`; production `.py` files are identical to `44e29f6`. The R2b implementation identity still resolves to `ff34015873d86e2f9e8849c6b58c8e8b850db0a4` (equal to every inventory route), and the shadow inventory still matches `9664878` byte-for-byte (`cmp` exit 0).

Source files changed from start: `restic_snapshot.py`, `backup_workflows.py`, `restic_gate.py`, `runtime_guard.py`, admission parts of `chroma_write_store.py` and `convmem.py`; tests `tests/test_safe_harbor_t2.py`, `tests/_safe_harbor_t2_cli.py` (new), `tests/test_write_gate_effect.py`, `tests/test_record_review_cli.py` (patched to the bound preflight; no assertion removed, no skip). Policy docs: ROADMAP, RECOVER, role-mapping and the v2 exit-25 row.

**Layout-only proof (`262573e` → `44e29f6`):** `ast.dump(ast.parse())` of `convmem.py` at both SHAs is equal (`ast_equal True`); no other source file changed. Behavior and route policy are therefore identical to `262573e`.

**Inventory proofs at `44e29f6`:** `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json` is byte-identical to `9664878` (`cmp` exit 0); every pinned `convmem.py` / `chroma_write_store.py` line is at its start-SHA position. The R2b inventory was regenerated only by `write_v2_inventory_file()` under isolated HOME/XDG/CONVMEM settings: `code_revision` `ff34015873d86e2f9e8849c6b58c8e8b850db0a4`, `inventory_digest` `52b64101…fa80`; `verify_inventory_matches_tip()` and `verify_shadow_inventory_unchanged()` both returned `[]`, script exit 0. Its diff from start touches only `code_revision`/`inventory_digest` lines (0 other changed lines). No writer route was added: the listed and actual `production_chroma_write_session` / `open_production_write_store` call sites are equal.

### What is implemented

- **Bound admission:** `add --upsert`, indexed `record --approve-last` / `--approve` and `propose_decision --recover` enter `chroma_write_store.admitted_write_operation()`: shared writer lease → one config load and digest → `restic_gate.preflight_operation()` → mutation. Nested write sessions reuse the admitted config; a config or `restic.env` edit after admission refuses (20, or 24 if the target moved). The `record` alias does not expose `--recover`; the exposed recovery CLI is `propose_decision --recover`.
- **Preflight:** explicit `complete-data-v2` profile required (legacy/v3 → 20); Chroma target equality and containment of Chroma, write-guard, export, events, queue, approved rows, locks and schema-gate paths in the data root (mismatch or symlink escape → 24).
- **Skip:** `CONVMEM_SKIP_RESTIC_GATE=1` refused unless `CONVMEM_RESTIC_GATE_EXCEPTION=isolated-test|isolated-lab` and canonical isolation from both `$HOME` and passwd-home production roots. cwd, lab-looking names, confirm variables or `CONVMEM_ROOT` alone are refused.
- **Freshness (B-E4.1) inside the resolver:** one instant per resolution; future → 25 `future_snapshot_time` with no backup, dry-run success or older fallback; old/missing → backup then fresh-instant re-resolution; day crossing → one fresh resolution, then 25 `day_boundary_crossed`.
- **Five consumers:** live ensure/write FAIL/25; check-only probe keeps its reachability PASS with `eligibility: "unchecked"`; local health FAIL/25; offsite health WARN with resolver code 25; offsite copy FAIL/25 before copy.

### Isolated evidence collected (prior source states)

All runs used `/home/lauer/miniforge3/bin/python` 3.13.12, scratch `restic 0.19.0` repositories created inside the test temp root, and HOME/XDG/`CONVMEM_CONFIG`/`CONVMEM_ROOT`/`CONVMEM_RESTIC_ENV`/`RESTIC_CACHE_DIR` set to fresh `/tmp` paths before any project import, with provider credentials and gate-skip variables unset. Tests also self-isolate through an autouse fixture.

**Exit-status caveat:** the pytest commands below were piped through `tail`; the recorded shell status is `tail`'s, so **no pytest exit code was captured** for them. Their passing counts are kept as observed output only.

| Source state | Runner | Selection | Observed output | Pytest exit |
|---|---|---|---|---|
| `77a590b` tree | Cursor sandbox (uid 0) | T2 + `test_write_gate_effect` + `test_record_review_cli` + `test_restic_gate` | `64 passed` | not captured (tail) |
| `77a590b` tree | Cursor sandbox (uid 0) | `test_restic_snapshot`, `test_backup_workflows`, `test_restic_offsite`, `test_runtime_guard`, `test_chroma_write_guard` | `86 passed, 4 failed` — four restore cases failed on `lchown` under uid 0 | not captured (tail) |
| `77a590b` tree | Cursor, uid 1000, temp HOME | the restore class, integrated offsite flow, `test_safe_harbor_t1`, `test_chroma_write_guard` | `60 passed` | not captured (tail) |
| `262573e` tree (twice) | Cursor sandbox (uid 0) | R2b/shadow coverage scans + T2 + caller tests + `test_restic_gate` + `test_runtime_guard` | `133 passed` | not captured (tail) |
| `262573e` tree | Cursor sandbox | `pylint $(git ls-files '*.py')` → `scripts/pylint_regression_gate.py ci --base-ref 9664878` | gate PASS, 460 findings, no new | `gate_exit=0` captured directly |

The four uid-0 `lchown` failures stay recorded as history. They were closed by Codex's captured ordinary-user regression run below, not by an environment waiver.

**Controls observed in those runs:** refusals (wrong profile, target B vs backup A, export symlink escape, config swap and `restic.env` edit after admission, spoofed skip, future same-day and next-day, day crossing, missing Restic) left fixture Chroma, events, approved rows and export unchanged. Success controls reached the intended mutation (old snapshot → backup → write; isolated exception). **No-op-gate negative control:** with the real preflight replaced on the same workflow, the future-snapshot write mutates and the unchanged-state assertion fails as intended.

### Final evidence at `44e29f6` — captured (Codex)

Runner `/tmp/safe_harbor_t2_collect.py` started each command as a direct subprocess and recorded its own return code (no pipelines). Every run used uid 1000, an environment built from a clean allowlist, and fresh isolated HOME/XDG/ConvMem/Restic/cache roots under the run directory; no production configuration, service or data. Interpreter `/home/lauer/miniforge3/bin/python` 3.13.12; pytest 9.1.1, chromadb 1.5.9, numpy 2.4.4, pylint 4.0.6, astroid 4.0.4. Source fingerprint `fecee6bc…3297` was identical before and after each run. These results supersede the uncaptured statuses above.

| Batch | Selection | Result | Exit | Evidence |
|---|---|---|---|---|
| Focused | `test_r2b_v2_coverage`, `test_shadow_writer_coverage_scan`, `test_shadow_writer_gate_c3`, `test_t3_residual_closure`, `test_r2b_v2_corrective_viii`, `test_safe_harbor_t2`, `test_write_gate_effect`, `test_record_review_cli`, `test_restic_gate`, `test_runtime_guard` | `133 passed, 2 warnings in 288.86s` (multiprocessing fork deprecation) | pytest **0** | `/tmp/safe-harbor-t2-final-focused-if1yg4e5/{result.json,pytest.log,pytest.xml}` |
| Regression | `test_safe_harbor_t1`, `test_chroma_write_guard`, `test_restic_snapshot`, `test_backup_workflows`, `test_restic_offsite` (includes the four former `lchown` cases) | `103 passed, 1 warning in 444.68s` (expected `WARN_LEGACY_ONLY`) | pytest **0** | `/tmp/safe-harbor-t2-final-regression-yra4l3ig/{result.json,pytest.log,pytest.xml}` |
| Lint | `python -m pylint <all tracked .py> --output-format=json`, then `scripts/pylint_regression_gate.py ci` vs `9664878` | `Pylint regression gate PASS (461 findings, 239 fingerprints; no new/increased vs baseline)` | pylint raw **30** (findings present, expected); gate **0** | `/tmp/safe-harbor-t2-final-lint-2_kqd6r_/{result.json,gate.log,pylint-report.json}` |

Together the two initial batches selected **236 distinct cases**. That focused run executed the previous direct-ingest version of the event-only test, which is kept as history.

### Refresh at test/fixture tip `2459acd` — captured (Codex)

Same runner, uid 1000, clean-allowlist environment and isolated roots. Source fingerprint `5ac369de…` was unchanged during both runs. Production files are identical to `44e29f6`, so the 133 + 103 results above remain attributable to the runtime source.

| Batch | Selection | Result | Exit | Evidence |
|---|---|---|---|---|
| Refresh | `test_safe_harbor_t2`, `test_write_gate_effect`, `test_record_review_cli`, `test_restic_gate` (includes the interrupted-approval fixture) | `64 passed in 284.85s`, no warnings | pytest **0** | `/tmp/safe-harbor-t2-final-refresh-4kpdiqod/{result.json,pytest.log,pytest.xml}` |
| Lint | full pylint, then regression gate vs `9664878` | `Pylint regression gate PASS (465 findings, 239 fingerprints; no new/increased vs baseline)` | pylint raw **30**; gate **0** | `/tmp/safe-harbor-t2-final-lint-pw4yih6o/{result.json,gate.log}` |

The 64 refreshed cases overlap the focused batch. They re-confirm the affected T2/caller cases at `2459acd` and are **not** additional unique tests. No default full suite and no live operation was run.

### Event-only recovery: corrected fixture and evidence gap

**Fixture (`2459acd`, tests only):** test hook `fail_after_chroma_ingest` replaces `propose_decision._mark_approved_unlocked` with a raise. The real CLI `record --approve <pid>` therefore runs admission, APPROVAL_STARTED, the approved row and the real Chroma ingest, then stops before publishing APPROVED (exit 1, "Approval apply deferred for recovery"). The test then proves:

1. the event log has APPROVAL_STARTED and no APPROVED for the proposal; the approved row exists; exactly one live Chroma unit carries the proposal marker;
2. that unit's `content_hash` differs from the PROPOSED event's `proposed_content_hash`;
3. `propose_decision --recover <pid>` on a future snapshot refuses with 25 `future_snapshot_time`, leaving Chroma and all governed files unchanged;
4. with the clock past that snapshot, admission passes (no BLOCKED), and the unchanged classifier returns its existing "needs human review" outcome (exit 1) with state unchanged.

The CLI, event writer, classifier and Chroma are real; only embeddings are faked. The obsolete direct-ingest helper mode was removed.

**OPEN evidence limitation — no event-only completion success control.** Under current code, a governed decision ingested through this path cannot satisfy the classifier's `approve` branch. Reason: the two hash views over the same record disagree.

- `recovery_action()` returns `approve` only when the live marker equals the proposal and `live_hash == proposed_hash` (`propose_decision.py:97-100`).
- `proposed_content_hash` is `ledger_content_hash(proposal_to_ledger(...))` (`propose_decision.py:477-478`; row shape `:366-390`). That dict has no `title`, `notes` or `result`, so they canonicalize as `null` (`ledger_content_hash.py:21-33`). The recovery fallback hashes the approved row, which has the same shape (`propose_decision.py:254-256`).
- The live `content_hash` is computed during ingestion from the normalized unit. There, `title` defaults to a summary-derived string and `notes`/`result` to `""` (`ledger.py:183-186`, `:249-250`, `:294-315`).

The finding is limited to records produced by these current paths; it makes no claim about arbitrary historical data. Aligning the views is a T4 prerequisite, e.g. comparing against the approved row's ingestion-side hash. It is neither implemented nor authorized here; classifier behavior is unchanged. The existing `approve` coverage (`test_n9_marker_and_hash_append_approved`) mocks `live_decision_snapshot`. Recovery with actual effects through the gate is covered by the `retry_chroma` path (`test_cli_recover_succeeds_on_current_snapshot`).

### Unrun / residual

- **T4 proof outstanding:** direct Python callers of `propose_decision.recover_approval()` / `approve_and_ingest()` are not gated (chain: helper → `ingest_approved_ledger` → `open_production_write_store`). Unknown/absent/tombstone classification, serialized recheck, races, completion uncertainty, export completion, retry and the hash-view normalization above stay with T4, ungranted.
- Canary consumers (`incremental_jsonl_canary*`) inherit the future-time refusal; not separately exercised.
- Production rollout requires an explicit v2 profile and data root in `restic.env`; none was inspected or changed.
- No production CLI/MCP/doctor, corpus, config, key, backup repository, provider, service or drive was touched. Snapshot eligibility is not demonstrated recoverability.

### Independent final-tip review — correction required

**Authority / provenance:** Ryan authorized “final-tip review, including the documented evidence limitation.” GitHub Copilot audit lane reviewed the complete T2 candidate at **`05c7706e54b77f9ef5b41a1c206b29bec012e405`**, relative to grant `9664878b4b4a64e86b98bbf25e041aa5393fea96`, on 2026-10-12. It read frozen Git exports and captured evidence only, with view/grep/glob tools; shell, edits and MCP were disabled. No tests or live probes were rerun. Session `05163236-dff7-4940-b4fa-6d2a79ffd054`; scratch packet `/tmp/safe-harbor-t2-review-26eoqy0o` (report `review.txt`, manifest `manifest.json`). The material findings are preserved here so that the scratch packet is not the authority.

**Verdict: FAIL, narrow — 75% confidence.** One local blocker; the reviewer rates the defect about 90% certain. No architectural reopening was requested. The remaining acceptance limit is stated separately below. This verdict is pinned to the reviewed subject, not transferred to a later documentation or code commit. It is Copilot audit evidence, not PR-native BugBot or an outage exception. No T2 PR, BugBot-reviewed SHA, or owner tip-specific outage acceptance exists.

**B1 — recovery entrypoint rejected by the census (local blocker).** At the reviewed subject, `convmem.py:1342` enters admission with `propose_decision.recover`, which is absent from `writer_census.KNOWN_ENTRYPOINTS` (`writer_census.py:30-38`). Admission acquires the shared lease (`chroma_write_store.py:840-848`); the lease calls `record_writer_open` (`:474-476`). If the census directory and valid header are present, that function rejects the unknown label (`writer_census.py:278-285`) before the gate/recovery body runs. The outer CLI catch then reports deferred recovery with exit 1 (`convmem.py:1347-1350`). The census-absent scratch configuration returns before the allowlist check, so passing V2 did not expose this integration regression.

Codex independently checked this source chain and agrees. No production census inspection was performed. The predecessor reached existing allowlisted governed/write boundaries; the newly introduced outer label causes the regression. Smallest proposed correction: use the existing `propose_decision.write` label, add an isolated actual recovery case with a valid census header and a control that detects the rejected label, and regenerate only the derived R2b identity fields if required. Do not expand the census allowlist or route policy. This is a correction proposal, not a new implementation grant.

**Event-only limitation — reviewer disposition, owner decision pending.** Copilot independently confirmed the proposal-versus-ingestion hash mismatch and that it predates T2. It classified this as a **bounded T4 prerequisite, not a T2 runtime blocker**: the real interrupted-approval fixture proves future-gate refusal and admitted human-review behavior, and retry-Chroma proves an admitted recovery mutation. It does **not** prove successful event-only completion. Before accepting V2 with that exclusion, Ryan must explicitly accept the limited evidence and require T4 hash-view alignment plus a real event-only success control. Review authorization is not that acceptance. The recommendation applies only to the demonstrated current ingestion path, not arbitrary historical records; the approved contract is not silently weakened here.

**Advisories / bounded carryovers (not additional reviewer blockers):**

- The no-op preflight control exercises `add --upsert`; indexed approval and recovery do not each have an equivalent control. The retry-Chroma success assertion checks a new unit and changed files; explicitly asserting the matching APPROVED event would strengthen it.
- Post-admission config/env refusal reaches the callers' existing deferred exit 1, rather than the helper's 20/24 codes. The reviewer calls this fail-closed and advisory; preserve the distinction rather than claiming uniform CLI codes. Expected-preview config comparison covers Chroma, not every preview field.
- Already-APPROVED recovery is gated too, and has no effect-free control. No ungated no-op exemption is claimed.
- Direct/helper and unbound compatibility-gate callers remain outside this named CLI proof; do not silently expand T2 to fix them. In particular `eval_corpus/r2b_capture_auth.py` still uses the legacy unbound gate. Classification/retry/export work stays at the named T4 seam; any other consumer expansion needs its own scope.
- The review confirmed target/path binding, shared freshness semantics and all five outcomes, production skip refusal within the cooperative boundary, retained exemptions, derived-only R2b changes, and the recorded 133/103/64 test results. It did not supply new runtime, CI, power-loss, production or recovery-qualification evidence.

**Documentation correction (Codex):** the opening of this file and V0 still said V2 NOT RUN / no candidate, contradicting V2's captured results. The current-state wording is corrected with this review record; historical T1 evidence is retained.

**Subsequent owner decision:** Ryan authorized the proposed bounded correction and evidence exclusion: “authoized: Next step: Authorize the bounded correction and decide the evidence exclusion.” Execution section 9 records the exact scope. Successful event-only completion is excluded from T2 acceptance evidence, with hash-view alignment plus real success proof retained as a T4 prerequisite. This is not overall V2 acceptance or a claim of successful completion. The review's preceding owner-decision request is historical; the missing evidence itself remains missing.

### B1 correction — implementation and isolated evidence

**Runtime/test subject:** `964c1decb1a8366226ad45345ae26ed909542569` (parent `c188a09`). Copilot reviewed final candidate `82f25efb4696325afa83298fae0e1ca698f1d7fe`, its documentation-only successor, and PASSed the B1 delta below. The original FAIL remains pinned to `05c7706`.

**Change:**

- Production: only `convmem.py:1342`. Recovery now enters `_admitted_operation("propose_decision.write", governed=True, ...)` instead of `"propose_decision.recover"`. This is the existing allowlisted label.
- Unchanged: `writer_census.py`, `KNOWN_ENTRYPOINTS`, route policy, `propose_decision.py`, hashing and the classifier. No line shifts.
- Tests: only `tests/test_safe_harbor_t2.py` and `tests/_safe_harbor_t2_cli.py`.
- Derived identity: `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` was regenerated only by `write_v2_inventory_file()` under isolated HOME/XDG/ConvMem settings. New values are `code_revision` `05362dba8c1f950e467b9e4f5696c91da1078735` and `inventory_digest` `62240f8aaba6bcb7e4f5fa96207e69eb0224485e14c35a128abc7632ff664d20`. The diff touches only those derived lines. `verify_inventory_matches_tip()` and `verify_shadow_inventory_unchanged()` both returned `[]`. The shadow inventory is byte-identical to `c188a09` (`cmp` exit 0).

**Census fixture (real, not membership-only):** each test arms the real census through the routed CLI `writer-census-start --chroma-root <fixture chroma>`. That call writes a valid header bound to the fixture HOME's actual writer gate and returns verdict `ARMED`, with no events yet. Recovery then runs through the real `propose_decision --recover` CLI subprocess. The proposal is left at APPROVAL_STARTED by a real `--no-index` approval. Admission is read back from the census `session-events.jsonl`: every `open` carries entrypoint `propose_decision.write` and the armed `census_id`, and each `close` nonce matches an `open` nonce. There are no runtime knobs, skips or production paths. The census lives under the per-test isolated HOME.

**Controls (same workflow, armed census):**

1. **Positive, current snapshot:** exit 0, `Recovered <pid>: retry_chroma`, one new Chroma unit carrying the proposal marker, exactly one matching APPROVED event, and census open/close admission recorded.
2. **Future snapshot:** exit 25 `future_snapshot_time`. Two kinds of evidence are kept separate:
   - *Telemetry:* the census does record the admitted open/close. The lease is taken before the preflight, which is expected.
   - *Logical state:* fixture Chroma plus `knowledge_units`, `pending_decisions`, `decisions-approved` and `pending_decision_events` are equal before and after, with no APPROVED event.
3. **Old-label negative control:**
   - *Setup:* the test-only CLI harness hook `recover_old_label` (in `tests/_safe_harbor_t2_cli.py`; it never ships) re-admits the same workflow under `propose_decision.recover`.
   - *Refusal:* the actual census rejects it with exit 1 and `writer entrypoint is not allowlisted`. No census events are written and logical state is unchanged.
   - *Positive assertions fail:* both the success assertion and the census-admission assertion raise `AssertionError`.
   - *Recovery without the hook:* the same proposal then recovers successfully, with census admission recorded.

**Evidence collection:** Cursor ran `/tmp/safe_harbor_t2_b1_collect.py` (temporary, not in the repo) as uid 1000, outside the agent sandbox.

- *Environment:* the runner was started via `env -i PATH=/usr/bin:/bin HOME=/tmp/nonexistent-home`. Each command ran as a direct subprocess with its return code recorded (no pipelines), under a clean-allowlist environment and fresh HOME/XDG/ConvMem/Restic/cache roots set before project import, with providers scrubbed.
- *Versions:* `/home/lauer/miniforge3/bin/python` 3.13.12; pytest 9.1.1, chromadb 1.5.9, numpy 2.4.4, pylint 4.0.6, astroid 4.0.4.
- *Source integrity:* the source fingerprint (all tracked `.py` plus both inventories) was `59773d19…cab1` before and after every run; `git diff --exit-code` was clean.
- *Concurrency:* runs were sequential, with no concurrent edits.

| Batch | Selection | Result | Exit | Evidence |
|---|---|---|---|---|
| New cases | `tests/test_safe_harbor_t2.py -k "armed_census or old_recover_label"` | `3 passed, 45 deselected in 37.79s` | pytest **0** | `/tmp/safe-harbor-t2-b1-new-ljyjud9l/{result.json,pytest.log,pytest.xml}` |
| Affected | `test_safe_harbor_t2`, `test_write_gate_effect`, `test_record_review_cli`, `test_restic_gate`, `test_runtime_guard`, `test_writer_census`, `test_governed_recovery_and_writers`, `test_shadow_writer_gate_c3`, `test_r2b_v2_coverage`, `test_shadow_writer_coverage_scan`, `test_t3_residual_closure`, `test_r2b_v2_corrective_viii` | `153 passed, 2 warnings in 339.06s` (multiprocessing fork deprecation); includes the 3 new cases | pytest **0** | `/tmp/safe-harbor-t2-b1-affected-grrn45j9/{result.json,pytest.log,pytest.xml}` |
| Lint | full pylint, then `scripts/pylint_regression_gate.py ci` vs `9664878` | `Pylint regression gate PASS (466 findings, 239 fingerprints; no new/increased vs baseline)` | pylint raw **30**; gate **0** | `/tmp/safe-harbor-t2-lint-2dr2w9xh/{result.json,gate.log}` |

No default full suite, no `test_safe_harbor_t1`/`test_restic_snapshot`/`test_backup_workflows`/`test_restic_offsite` rerun, and no production health command or live operation was run. The earlier 103-case regression batch at `44e29f6` predates this label change.

**Scope:**

- *Evidence exclusion:* per Ryan, T2 evidence does **not** prove successful event-only completion. The hash-view mismatch stays a T4 normalization plus real success-control prerequisite, and the interrupted-approval refusal/human-review fixture is unchanged.
- *What this commit is not:* overall V2 acceptance, a T4 grant, merge permission or a BugBot exception.
- *Advisories:* the earlier advisories remain unaddressed. The one exception is the retry-Chroma APPROVED-event assertion, which the armed-census positive control now makes explicitly.

### Independent B1 delta review — PASS

**Exact reviewed subject:** `82f25efb4696325afa83298fae0e1ca698f1d7fe` (code/tests `964c1decb1a8366226ad45345ae26ed909542569`), compared with the original FAIL at `05c7706e54b77f9ef5b41a1c206b29bec012e405`. GitHub Copilot audit lane completed this authorized static delta on 2026-10-12 at 08:45 UTC in the same review session `05163236-dff7-4940-b4fa-6d2a79ffd054`. Frozen Git exports and captured evidence only; tools limited to view/grep/glob, no shell, writes, MCP or test reruns. Packet: `/tmp/safe-harbor-t2-review-26eoqy0o/delta-82f25ef/{manifest.json,review.txt}`. Material conclusions are preserved here; the temporary packet is not the sole record.

**Verdict: PASS for B1 delta — 88% confidence. No blockers.** B1 is fixed by the one-line reuse of the existing allowlisted entrypoint. The census policy and nested lease are unchanged. The positive control reaches actual recovery and APPROVED; the future case reaches census admission but leaves logical state unchanged after gate refusal; the old-label control actually reproduces the census refusal before the same proposal succeeds without the hook. No hidden bypass was found. The reviewer checked the evidence logs: 153 affected cases include the 3 new cases; pytest exits 0; lint raw 30 with regression gate 0. It supplied no new runtime, CI, production or power-loss evidence.

**Provenance and scope:** Codex independently confirmed the one-line source delta, derived-only R2b field changes, byte-unchanged Shadow inventory, and equality of code/tests between `964c1de` and reviewed `82f25ef`. The original full-review FAIL remains pinned to `05c7706`; this delta closes its B1, not all future acceptance gates. This later documentation record is not automatically a new exact-tip PASS. No T2 BugBot-reviewed SHA or outage exception exists.

**Non-blocking dispositions:**

- Corrected the stale `964c1de` review-subject shorthand: it is the runtime/test subject; `82f25ef` is the actual delta-reviewed final candidate.
- Recover and approve now share the census/attestation label `propose_decision.write`, as authorized; those labels alone no longer distinguish the commands.
- The old-label control's success assertion first fails on the exit code. Unit and APPROVED sub-assertions are exercised on the passing path; do not claim each independently fails under the control.
- Earlier non-blocking advisories remain, except the new positive test now explicitly checks APPROVED. No new implementation is authorized by carrying them forward.
- The reviewer also noted the separate R2b live-attestation set (`eval_corpus/r2b_v2/coverage/proof.py:55-66`) lacks `propose_decision.write`. Codex confirmed the omission and that the grant base already used this label in `propose_decision.py:549/581/747`. This is a pre-existing owner-routed compatibility concern, not a reason to expand the current census fix or claim R2b live acceptance. The R2b owner or later T4 planning must disposition it.
- Ryan's exclusion of event-only successful completion from V2 evidence remains bounded; the underlying hash mismatch and actual success proof stay with T4. No success is inferred from this PASS.

**Next:** Ryan decides overall V2 acceptance and PR/review authority. The required PR-native BugBot gate remains unsatisfied. No further Copilot delta is requested for this documentation-only review record. Merge, T3–T5 and live operations remain unauthorized.

### Draft PR, direct review and target-binding correction grant

**[Arc Safe Harbor] Exact subject:** `0cff1578b881d890234adad6b9cb93a110ec1d48`, runtime/tests `964c1de`, draft [PR #389](https://github.com/alanmz-crypto/convmem/pull/389). Local/remote/PR identity and draft state were checked before this documentation-only grant update. Ryan authorized PR creation and one BugBot trigger. That [trigger](https://github.com/alanmz-crypto/convmem/pull/389#issuecomment-6121632772) received a [usage-limit reply](https://github.com/alanmz-crypto/convmem/pull/389#issuecomment-6121635935), request `462c15e8-21c8-4c73-a59c-f8626f0b2340`; **no SHA was reviewed**. No PR-native Copilot request was submitted. Ryan then requested a budget-conscious review without Copilot.

**Codex static assessment: correction required, 90% confidence in the alias finding.** Source at `0cff157` shows `config.py:467-482,610-628` retains alias spellings; `chroma_write_store.py:863-881` checks resolved preflight paths but saves the original config. `verify_admitted_operation_unchanged` at `789-814` checks file bytes, not alias targets, and the factory at `932-942` consumes the original path again. `chroma_store.py:146` resolves it on open. `convmem.py:425-426` likewise forwards the configured export path. A symlink retarget between preflight and use can leave config/env hashes unchanged while redirecting the destination. This is static reasoning, **not a reproduced incident or measured likelihood**. Existing tests at `tests/test_safe_harbor_t2.py:983-1002` alter config/env bytes and do not establish alias-retarget refusal. The bounded grant requires an actual workflow reproduction/control before declaring the correction proven; counter-evidence returns to Codex/Ryan.

**Owner authorization:** “authorized: Next step: Authorize the bounded target-binding correction and CodeQL disposition.” The [execution handoff](EXECUTION-safe-harbor.md#target-binding-correction--owner-authorized) contains the exact source boundary, effect/control requirements and stop. Cursor's correction is **NOT_STARTED / GRANTED**; no new runtime or regression result is supplied by this record. The earlier independent reviews are not automatically a PASS for changed code, and Codex's assessment is not independent third-party review.

**CodeQL #6 disposition — COMPLETE:** GitHub reported `py/clear-text-storage-sensitive-data` at `tests/test_safe_harbor_t2.py:226`, source at `217`. At this tip, `self.password` is a `pathlib.Path` assigned at `205`; the environment writer persists that scratch filename as `RESTIC_PASSWORD_FILE`. It does not serialize password contents. The fixture separately creates a fixed synthetic test password and chmods it 0600 (`206-207`). Codex assessed the reported flow as a false positive (95% confidence). Under Ryan's authorization, Codex dismissed [alert #6](https://github.com/alanmz-crypto/convmem/security/code-scanning/6) with reason `false positive` and a source-based comment. GitHub confirmed both alert and PR instance `dismissed` at `2026-10-12T10:34:24Z`. No code change, query suppression or scanning-policy change was used.

**CI at the reviewed source:** GitHub pytest (3.12), pylint (3.12), secret-scan and Analyze (Python/actions) passed. After dismissal, the CodeQL check also reports SUCCESS. Cursor Bugbot remains neutral/no review. These are read-back results for `0cff157`, not tests rerun by Codex and not evidence for the pending correction. Normal branch CI must evaluate the correction successor.

**Next / limits:** Cursor delivered the bounded correction and isolated evidence below. Codex performs a static delta on successor **`a18df48025cac77de8bda2db5a761f4744a9a963`** and reports CI. Keep draft #389 open. No paid reviewer request, overall V2 acceptance, external-gate waiver, merge, T3–T5 or live operation is implied.

### Target-binding correction evidence — captured (Cursor)

**Runtime/tests subject:** `a18df48025cac77de8bda2db5a761f4744a9a963` on `fix/2026-10-12-safe-harbor-t2`, parent grant docs `1cc24a4ccd42addeee48a96d518c04775070040c`. Reviewed pre-correction source remains pinned at `0cff1578b881d890234adad6b9cb93a110ec1d48` / runtime `964c1de`.

**What changed:** admitted operations now pin canonical `chroma_dir` and `units_export` in the configuration handed to consumers, recheck resolved targets after preflight (including unchanged config/env bytes), open production stores on the admitted Chroma path, and report post-admission refusals through the existing gate exit path in `_admitted_operation`. Scope: `chroma_write_store.py`, `convmem.py` export plumbing, isolated T2 CLI fixtures/tests only.

**Reproduction (alias retarget):** config names a Chroma symlink with target A eligible in Restic; after successful preflight the symlink is repointed to corpus B without editing config/env. Real `add --upsert` refuses with exit **24** / `operation_config_changed`; logical Chroma in A and B, events/approved rows and exports stay unchanged. **Positive control:** stable alias reaches a real mutation in A while B's Chroma view stays unchanged (shared export file may update; Chroma oracle used). **Export control:** export symlink retargeted outside the protected root after preflight refuses before writing outside. **Factory path:** `open_production_write_store` refuses the same drift under an active admitted operation. **Negative control:** test-only `unbound_retarget_chroma_alias` hook restores pre-correction binding; the retarget redirects the write into B and fails the unchanged-A oracle.

**Commands (cloud VM, uid 1000, isolated HOME/XDG/CONVMEM/Restic roots; `RESTIC_TEST_BIN=/tmp/restic` restic 0.19.0; Python 3.12 + user site packages):**

```bash
export RESTIC_TEST_BIN=/tmp/restic PYTHONPATH="$HOME/.local/lib/python3.12/site-packages"
python3 -m pytest tests/test_safe_harbor_t2.py -k "alias or export_alias or open_production" -q --tb=line
python3 -m pytest tests/test_safe_harbor_t2.py tests/test_write_gate_effect.py \
  tests/test_record_review_cli.py tests/test_safe_harbor_t1.py \
  -k "alias or canonical or contention" tests/test_r2b_v2_implementation_revision.py -q --tb=line
```

| Batch | Result | Exit |
|---|---|---|
| New target-binding cases (5) | `5 passed` | pytest **0** |
| Binding + T1 alias/contention + R2b identity (10 selected) | `10 passed` | pytest **0** |
| `test_r2b_v2_implementation_revision` committed inventory | `1 passed` | pytest **0** |

Log: `/opt/cursor/artifacts/t2-target-binding-pytest.log` (10-case batch). No production CLI/MCP/doctor, corpus, provider, service, drive or real backup repository access. Process barriers are not power-loss proof.

**Derived R2b inventory:** regenerated under isolated HOME/XDG/CONVMEM; `code_revision` `dc714d0ac40fffdb90f7aed5f7a42148bbbcca8a`, `inventory_digest` `5cbc5a9931a1924bd3f2064f5a9a4f8477a94aa1f74035f408937f47f5163589`; `route_sink_evidence_errors` `[]`; shadow inventory byte-unchanged vs grant tip.

**CI:** pending on pushed successor (normal draft #389 workflow). BugBot reviewed no SHA on prior tips; no new trigger requested.

### Codex target-binding delta — correction required

**[Arc Safe Harbor] Subject and method:** static delta of grant `1cc24a4ccd42addeee48a96d518c04775070040c` to recovered candidate `255c040308b41c41af0b40a3af8c290794052523`, runtime/tests `a18df48025cac77de8bda2db5a761f4744a9a963`, on 2026-10-12. No tests, production CLI/MCP, indexing, paid review or live operation ran in this review. Percentages are confidence in the stated conclusion, not incident likelihood. This is not independent third-party review or final-tip gate acceptance.

**Recovery:** the downloaded Git bundle passed verification against prerequisite `1cc24a4`; its SHA-256 is `49e96590da894a0c88a63643c17c6335b46a0d0629da052b915757110e542933`. Codex imported the three commits, fast-forwarded only the clean T2 worktree and pushed `255c040` to the existing draft #389. No rebase, main integration or shared-checkout switch occurred. The R2b JSON differs only in `code_revision` and `inventory_digest` fields (static JSON comparison); this is not a rerun of its verifier.

**Verdict: correction required.** The direction remains unchanged. Two local implementation/evidence obligations remain within the existing target-binding grant:

1. **F1 — canonical pinning bypasses T1's competing-location refusal (95%, static).** At this subject, `AdmittedWriteOperation.config()` replaces the configured Chroma spelling with the resolved path (`chroma_write_store.py:735`). Both admitted production factories also select `op.chroma_dir` (`:993-1004`, `:1049-1061`), and `open_chroma_for_write` constructs the guard from that argument (`:665`). T1 detects competing legacy guard state by comparing the *requested spelling's* sibling guard directory with the canonical one (`chroma_write_guard.py:1036-1042`). Passing only the canonical path makes those locations identical. A stable configured alias with an unresolved marker beside the alias, and no marker beside the canonical store, therefore loses this refusal; neither a config edit nor an alias retarget is needed. The new target recheck compares resolved paths only (`chroma_write_store.py:809-829`). Existing T1 coverage explicitly passes the alias to the guard (`tests/test_safe_harbor_t1.py:434-460`), so it does not cover this new factory path. Preserve original-path conflict validation while keeping client/cache and actual write targets pinned. Add effect-based isolated coverage through the admitted CLI and both production factories; require refusal, unchanged marker/corpus/governed state and no empty replacement authority. Keep the stable alias without conflicting state as a successful control. This is a source-grounded regression, not a runtime reproduction by Codex.

2. **F2 — required downstream export and regression evidence is incomplete (95%).** The only export-retarget hook acts immediately after admission, before store construction (`tests/_safe_harbor_t2_cli.py:130-149`); its test (`tests/test_safe_harbor_t2.py:1103-1131`) proves early refusal, not the grant's separately required retarget after store construction. Add that case through the real export consumer, preserving its allowed outcome: refusal at a checked boundary or writing the already pinned authorized destination, with no outside write and no rollback claim for earlier effects. The reported second pytest command applies `-k "alias or canonical or contention"` to every listed file. None of `tests/test_r2b_v2_implementation_revision.py`'s class/test names matches it; the command also omits most existing approve/recover binding cases. Run the affected cases explicitly under the existing isolation contract, including T1 stale-client/competing-location cases, the named T2 caller regressions and inventory checks. Retain exact node selections, commands, source/backend identity, exit statuses and effects; retain the existing accepted event-only success exclusion.

**Evidence qualification:** the transferred `/home/lauer/Downloads/t2-target-binding-pytest.log` (SHA-256 `e4d2651d8cce574f6a2fbff54d55d4e3a56668184b8726a4d53b1bc3443a0a5f`) contains only progress dots and `10 passed, 85 deselected in 50.84s`. It contains no command, node list, versions, SHA or exit-status capture. Cursor's separate five-case and one-case results above remain reported, not independently corroborated by this log. The five-case selection overlaps the ten-case selection. The negative-control prose above also needs qualification: its assertions keep A unchanged and prove B changed (`tests/test_safe_harbor_t2.py:1096-1098`); it does not fail an unchanged-A oracle. The wrong-target effect is the useful control.

**Scope cleanup (local, 95%):** `convmem.py:720` changes the unbound monitor's export path despite the grant being limited to necessary bound-caller plumbing. Revert that unrelated change and unused helper imports in verify/forget; clean up the now-unused `admitted` assignments in `_admission_steps`. Preserve the intended post-admission numeric refusal behavior. These do not justify a new policy or architecture round.

**Cursor continuation:** resume the existing T2 branch at the documentation commit containing this review, with a clean worktree and matching remote. Address F1/F2 and the scope cleanup under the unchanged section 9 target-binding grant; do not reopen B1, the accepted event-only exclusion or T3–T5. Update existing evidence/routing, regenerate only derived inventory if affected, commit/push each commit and return the successor for a bounded Codex delta plus fresh CI. No paid review, trigger/comment, merge or live operation. If the correction requires a production file outside the existing grant, return that exact dependency before editing it.

### F1/F2 target-binding correction — captured (Cursor)

**Grant start:** `3c6f728d56a2cd99a191d86e5d2f75c1c41cb3f0`. **Runtime/tests subject:** `cdebf64b487ffa27d61955df9739204829864fe0` on `fix/2026-10-12-safe-harbor-t2`.

**What changed:** admitted operations keep **canonical** `chroma_dir` / `units_export` in pinned config and open production stores on `op.chroma_dir`. The original Chroma spelling is carried as `configured_chroma_dir` for `verify_competing_guard_locations()` (existing `ChromaWriteGuard.require_not_quarantined()` on the alias spelling) before either production factory opens a client. Export retarget after store construction is covered via `retarget_export_alias_after_store` on the real `add --upsert` export consumer. `configured_units_export` is also recorded but unused; export consumers receive the canonical pinned path. Scope cleanup: unrelated unbound monitor path reverted to configured expanduser; unused `admitted_units_export_path` imports removed from verify/forget; unused `admitted` flag removed from `_admission_steps`.

**Invalid development runs (not accepted evidence):** early shell pytest without outer-isolated subprocess env; first target-binding batch had **1 failed** (`test_open_production_write_store_refuses_competing_alias_guard` before fix) and **invalid exit capture** (`| tee` masked pytest exit 0). An eight-case pass in the same mode does not satisfy the grant isolation contract.

**Accepted runner:** `/tmp/safe_harbor_t2_collect.py` — direct subprocess per batch, `subprocess.returncode` only (no pipelines), uid **1000**, clean allowlist env and fresh HOME/XDG/CONVMEM/Restic/cache roots under each run directory before any project import. Interpreter `/home/lauer/miniforge3/bin/python` **3.13.12**; restic **0.19.0**; pytest **9.1.1** (from env). Evidence directory **`/tmp/safe-harbor-t2-f1f2-20261012T130410Z`** (`summary.json`, per-batch logs).

| Batch | Selection | Result | Exit |
|---|---|---|---|
| Inventory | `write_v2_inventory_file()` then regression | derived `code_revision` `638cf8d3…`, digest `0479842d…`; `route_sink_evidence_errors` `[]` | **0** |
| Target binding | `tests/test_safe_harbor_t2.py -k "alias or export_alias or competing or open_production"` | **9 passed**, 48 deselected | pytest **0** |
| Regression | 24 explicit nodes (T2 alias/export/competing/caller, `test_write_gate_effect`, `test_record_review_cli`, four T1 alias/competing-location cases, `test_r2b_v2_implementation_revision`) | **42 passed** | pytest **0** |
| Lint | full pylint JSON + `scripts/pylint_regression_gate.py ci` vs `9664878` | gate **PASS** (459 findings, 239 fingerprints) | pylint raw **30**; gate **0** |

**Controls:** competing alias-local quarantine refuses on the CLI with unchanged logical state; both factories additionally assert refusal before `PersistentClient` using a spy; stable alias still mutates A; export retarget after preflight and after store open refuses with 24 / unchanged fixtures; unbound negative control still redirects write into B; preflight retarget and factory alias-drift cases retained.

**CI / integration:** draft **#389** reports **CONFLICTING** with `main` (`mergeStateStatus` **DIRTY** at grant tip `3c6f728`); resolving or merging `main` is **not** in this grant. Only CodeQL has been observed on the conflicted branch; fresh merge-result pytest CI is pending a separately authorized integration.

### Codex F1/F2 correction delta and complete isolated evidence — PASS

**[Arc Safe Harbor] Scope / subject:** bounded delta from `3c6f728d56a2cd99a191d86e5d2f75c1c41cb3f0` to Cursor runtime/tests `cdebf64b487ffa27d61955df9739204829864fe0`, reviewed at docs successor `721fd17fcc6b454a6bd435c1ece13da14b77f7fb`, on 2026-10-12. **PASS (90% confidence in the bounded conclusion).** This closes F1/F2 and the named cleanup; it is neither independent external review nor overall V2 acceptance. Subsequent edits in this record change documentation only.

- **F1 closed:** `chroma_write_store.py:715-742,847-863,984-1001,1026-1044,1083-1101` retains the original Chroma spelling for the existing quarantine/competing-location check before either production factory opens its client, while config and actual store arguments stay canonical. CLI effects prove the marker and logical state unchanged and no new canonical authority; both factory spies prove no client opened. A stable alias without conflicting guard state still succeeds. This reuses the guard rather than adding a release mechanism.
- **F2 closed:** `admitted_units_export_path` rechecks the admitted inputs before yielding the pinned export path (`chroma_write_store.py:835-844`). The test-only after-store hook (`tests/_safe_harbor_t2_cli.py:159-170`) retargets after real factory construction. The real add path refuses with 24 / `operation_config_changed`, unchanged logical fixtures and no outside export. No physical read-only or rollback claim is made. The actual unbound negative control still writes B while A stays unchanged.
- **Cleanup / inventory:** unrelated monitor export behavior and unused imports/flag are restored or removed. R2b JSON differs from the grant only in identity fields; policy, routes, shadow inventory and identity algorithm are unchanged. Its source-location allowlist still requires the unchanged dry-run constructor at `convmem.py:699`; two comments preserve that coordinate. The comment's “read-only client” describes dry-run intent, not physical immutability. The source-line coupling remains an existing maintenance cost; no inventory redesign is part of this correction.

**Qualified results (85 distinct cases, zero failures/skips):** Cursor's final 42-case regression passed in 175.04 s, and Codex's disjoint supplemental 43-case batch passed in 215.91 s, both exit 0. Together they cover the entire 57-case T2 file, write-gate effect tests, record-review CLI tests, four T1 alias/competing-location cases, three native stale-client cases and the full R2b implementation-revision file. The 9-case focused pass overlaps the 42 and is not added again. Full default pytest was not run.

The supplement was selected by AST-reading T2's top-level test names, excluding the 17 explicit T2 names already in the 42-case batch, then adding the two native-guard function selectors (one is parametrized). The captured earlier and final 42-case argv lists are identical. Exact executed selectors follow; both were launched as direct subprocesses in the task worktree, not pasted into an ambient shell.

<details>
<summary>Exact 42-case argv</summary>

```text
/home/lauer/miniforge3/bin/python \
  -m \
  pytest \
  tests/test_safe_harbor_t2.py::test_cli_add_succeeds_with_unchanged_chroma_alias \
  tests/test_safe_harbor_t2.py::test_cli_chroma_alias_retarget_refused_after_preflight \
  tests/test_safe_harbor_t2.py::test_control_unbound_target_lets_alias_retarget_mutate \
  tests/test_safe_harbor_t2.py::test_cli_export_alias_retarget_refused_after_preflight \
  tests/test_safe_harbor_t2.py::test_cli_export_alias_retarget_refused_after_store_open \
  tests/test_safe_harbor_t2.py::test_cli_add_refuses_competing_alias_guard_location \
  tests/test_safe_harbor_t2.py::test_open_production_write_store_refuses_retargeted_alias \
  tests/test_safe_harbor_t2.py::test_open_production_write_store_refuses_competing_alias_guard \
  tests/test_safe_harbor_t2.py::test_production_chroma_write_session_refuses_competing_alias_guard \
  tests/test_safe_harbor_t2.py::test_cli_approve_refused_before_any_approval_state \
  tests/test_safe_harbor_t2.py::test_cli_approve_succeeds_on_current_snapshot \
  tests/test_safe_harbor_t2.py::test_cli_recover_refused_on_future_snapshot \
  tests/test_safe_harbor_t2.py::test_cli_recover_succeeds_on_current_snapshot \
  tests/test_safe_harbor_t2.py::test_cli_recover_with_armed_census_succeeds_on_current_snapshot \
  tests/test_safe_harbor_t2.py::test_cli_recover_with_armed_census_refused_on_future_snapshot \
  tests/test_safe_harbor_t2.py::test_control_old_recover_label_refused_by_armed_census \
  tests/test_safe_harbor_t2.py::test_cli_event_only_recovery_refused_before_approved_event \
  tests/test_write_gate_effect.py \
  tests/test_record_review_cli.py \
  tests/test_safe_harbor_t1.py::test_canonical_alias_shares_one_guard_and_competing_legacy_refuses \
  tests/test_safe_harbor_t1.py::test_competing_legacy_guard_location_refuses_adoption \
  tests/test_safe_harbor_t1.py::test_alias_store_shares_the_canonical_client_cache \
  tests/test_safe_harbor_t1.py::test_competing_legacy_location_refuses_an_alias_store \
  tests/test_r2b_v2_implementation_revision.py \
  -q \
  --tb=line
```
</details>

<details>
<summary>Exact disjoint 43-case argv</summary>

```text
/home/lauer/miniforge3/bin/python \
  -m \
  pytest \
  tests/test_safe_harbor_t2.py::test_snapshot_freshness_one_instant_timezone_and_rollover \
  tests/test_safe_harbor_t2.py::test_resolver_refuses_future_newest_and_requested \
  tests/test_safe_harbor_t2.py::test_resolver_never_falls_back_to_older_current_snapshot \
  tests/test_safe_harbor_t2.py::test_resolver_stale_reason \
  tests/test_safe_harbor_t2.py::test_five_consumers_under_future_snapshot \
  tests/test_safe_harbor_t2.py::test_five_consumers_same_day_current_pass \
  tests/test_safe_harbor_t2.py::test_old_snapshot_backs_up_then_fresh_post_backup_resolution \
  tests/test_safe_harbor_t2.py::test_control_reusing_pre_backup_clock_fails_post_backup_resolution \
  tests/test_safe_harbor_t2.py::test_legacy_warn_and_v3_resolution_stay_compatible \
  tests/test_safe_harbor_t2.py::test_gate_admits_bound_current_v2_target \
  tests/test_safe_harbor_t2.py::test_gate_requires_explicit_v2_profile \
  tests/test_safe_harbor_t2.py::test_gate_refuses_chroma_target_mismatch \
  tests/test_safe_harbor_t2.py::test_gate_refuses_symlinked_export_escaping_data_root \
  tests/test_safe_harbor_t2.py::test_gate_refuses_future_snapshot_without_backup \
  tests/test_safe_harbor_t2.py::test_gate_missing_restic_is_21 \
  tests/test_safe_harbor_t2.py::test_gate_day_boundary_forces_one_fresh_resolution \
  tests/test_safe_harbor_t2.py::test_skip_without_isolated_context_is_refused \
  tests/test_safe_harbor_t2.py::test_skip_unrecognized_value_is_refused \
  tests/test_safe_harbor_t2.py::test_skip_with_unknown_context_is_refused \
  tests/test_safe_harbor_t2.py::test_skip_refused_when_target_is_production_shaped_under_home \
  tests/test_safe_harbor_t2.py::test_skip_refused_for_passwd_home_production_root \
  tests/test_safe_harbor_t2.py::test_isolated_lab_requires_lab_data_root \
  tests/test_safe_harbor_t2.py::test_isolated_test_exception_admits_without_restic \
  tests/test_safe_harbor_t2.py::test_cli_add_upsert_refused_on_future_snapshot \
  tests/test_safe_harbor_t2.py::test_cli_add_upsert_succeeds_on_current_snapshot \
  tests/test_safe_harbor_t2.py::test_control_noop_preflight_lets_mutation_through \
  tests/test_safe_harbor_t2.py::test_cli_plain_add_stays_ungated \
  tests/test_safe_harbor_t2.py::test_cli_no_index_approve_stays_ungated \
  tests/test_safe_harbor_t2.py::test_cli_config_swap_after_preflight_refused_on_both_targets \
  tests/test_safe_harbor_t2.py::test_cli_profile_edit_after_preflight_refused \
  tests/test_safe_harbor_t2.py::test_cli_profile_target_mismatch_refused \
  tests/test_safe_harbor_t2.py::test_cli_skip_spoof_refused_and_isolated_exception_allowed \
  tests/test_safe_harbor_t2.py::test_cli_missing_restic_is_21 \
  tests/test_chroma_write_guard.py::test_stale_writer_and_a_newer_save_from_another_process \
  tests/test_chroma_write_guard.py::test_write_is_refused_when_another_client_pins_a_stale_system \
  -q \
  --tb=short
```
</details>

**Isolation and identity:** uid 1000; Python 3.13.12, Chroma 1.5.9, numpy 2.4.4, pytest 9.1.1, Restic 0.19.0, pylint 4.0.6 / astroid 4.0.4. Each qualified run constructed an environment allowlist (PATH, locale/timezone, temporary HOME/XDG/CONVMEM/Restic/cache/TMPDIR, task PYTHONPATH, PYTHONNOUSERSITE and PYTHONDONTWRITEBYTECODE) before collection/project imports. No inherited provider keys or production config. The supplemental run also set a temporary XDG_RUNTIME_DIR. Each captured its actual subprocess return code.

Cursor final root-Python fingerprint before/after: `5a4f0a021c7920b508ee429a9915756697566200b67935853e19a296ca5efdf1`. Codex supplement fingerprint before/after and sealed commit checkout: `0cdfa12aaf4769b82b3d7b20ba899c1982ea9b8b68ca776d39ec96df277138c4`. The latter hashes 565 selected files (all tracked Python plus the inventory/baseline entries), in git ls-files order, as path + NUL + bytes + NUL. Documentation-only successors do not change those bytes.

**Captured local records:** `/tmp/safe-harbor-t2-f1f2-20261012T130410Z/{summary,regression,target_binding,lint_gate}.json` and associated logs; `/tmp/safe-harbor-t2-supplement-z7rz4cwo/{result.json,pytest.log}`. These are local scratch records, not uploaded CI artifacts; this tracked section preserves subjects, commands, outcomes and limits. Final lint regression gate: exit 0, 459 findings / 239 fingerprints, no new/increased findings versus `9664878`; raw pylint 30 is not itself a clean lint result.

**Failed/diagnostic runs retained:** earlier non-allowlisted collection runs are not accepted isolation evidence, including the failed factory case whose pipeline obscured the exit. Intermediate isolated runs failed inventory/lint due to stale generated identity, missing lint-gate arguments, new lint warnings, and the unchanged constructor moving from line 699 to 697 after unused-import cleanup. The broader 84-pass/1-fail diagnostic also encountered that inventory coordinate mismatch while source was still changing; it is not the final proof. The final qualified 42+43 batches above follow the coordinate correction/regeneration and unchanged-source check. No production probe was used to investigate those development runs.

**Next boundary (superseded for integration):** the pre-integration preview at grant tip identified only the generated R2b inventory as conflicting with main `8a7cdab`; the bounded integration grant below closed that gap.

### T2 branch integration with pinned main — captured isolated evidence (pre-merge tree)

**[Arc Safe Harbor] Scope / subject:** bounded integration from grant parent `181dfd18a2c0dc50745d74b45cc12fa37e916a82` with pinned main `8a7cdab16420893fe26a2648d1d03f2b84d8589d`, evidenced on the pending-merge tree before merge commit `551b16c13b66c8e3133402bdf6c0370d3efd35a5`. **Isolated batches PASS** (inventory regen exit 0, pytest exit 0, lint regression gate exit 0). This is not independent external review, not overall V2 acceptance, and does not transfer earlier review PASS to the integrated tip.

**Coordinator identity (static):** of 31 files changed on one parent only, Codex confirmed 19 task-only and 12 main-only paths are byte-identical to their respective pinned parents; `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` is the sole file differing on both sides. Main's merged `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json` update is retained (not byte-identical to the pre-integration task parent). No new route or identity policy was introduced.

**Non-qualified development run (not accepted evidence):** an early inventory regeneration used a login shell with inherited ambient environment (`/tmp/safe-harbor-t2-integration-20261012T234506Z`); Codex interrupted the Cursor invocation; that attempt is not accepted evidence.

**Qualified evidence root:** `/tmp/safe-harbor-t2-integration-evidence-20261012T234749Z/` (`summary.json`, `inventory_regen.json`/`.log`, `affected_pytest.json`/`.log`, `pylint-raw.json`, `lint_gate.json`/`.log`). Coordinator: Codex, uid 1000, clean allowlist before every project import/subprocess via corrected `/tmp/safe_harbor_t2_integration_collect.py` (temporary runner only; not tracked).

**Inventory (regenerated, idempotent):** `code_revision` `46801f24cfc626bef5403b386ab45a2ce1733cf6`, `inventory_digest` `6bee348681128b78ce544dcbd7025db94fa12c92d8329e18bc64a913f67eaff7`, file sha256 `b80587a9fc6d5d173ba6fb93d73953dfc2dd11b34354d25c01b4415e5406eaab`; `route_sink_evidence_errors` and `missing_categories` empty before and after regen.

**Source fingerprint (sealed pre-merge bytes):** `20e4850be3c8fda4cd69cbd4deab721b66024120655961b9ec207483948ea825` before and after (`source_stable: true`). Safe Harbor implementation bytes remain at reviewed runtime `cdebf64b487ffa27d61955df9739204829864fe0` on the task side of the merge.

**Affected pytest (85 cases, one combined selection):** exit 0, `85 passed in 391.54s`. Full argv in `summary.json` / `affected_pytest.json` — entire `tests/test_safe_harbor_t2.py`, `tests/test_write_gate_effect.py`, `tests/test_record_review_cli.py`, `tests/test_r2b_v2_implementation_revision.py`, four T1 alias/competing-location nodes, two native stale-client nodes; `-q --tb=line`.

**Lint:** full pylint JSON exit **30** (not a clean lint result); `scripts/pylint_regression_gate.py ci` exit **0** against pinned main baseline `8a7cdab` with `--pylint-status 30`: 454 findings / 239 fingerprints, none new or increased.

**Versions:** Python 3.13.12, pytest 9.1.1, numpy 2.4.4, Chroma 1.5.9, Restic 0.19.0 (see `summary.json`).

**Merge commit (integration source SHA):** `551b16c13b66c8e3133402bdf6c0370d3efd35a5`, parents `181dfd18a2c0dc50745d74b45cc12fa37e916a82` and `8a7cdab16420893fe26a2648d1d03f2b84d8589d`. Pushed to `fix/2026-10-12-safe-harbor-t2`.

**CI routing:** checks publish on [draft PR #389](https://github.com/alanmz-crypto/convmem/pull/389) for its current head; status recorded in STATUS/LATEST at docs handoff is a point-in-time observation only — GitHub check runs are the mutable authority. Codex has completed the bounded integration delta below and monitors remaining CI without moving the sealed tip solely to transcribe live status.

**Codex bounded integration delta — PASS (90%) with limitation:** reviewed candidate `0c3e6c7500fab1e2334ce4864e2521c5d1b506b1` (integration source `551b16c`) against both pinned parents. The only shared-file resolution is derived R2b JSON; task-only and main-only blobs match their respective parents, including main's shadow-policy update. The committed checkout reproduces the evidence fingerprint `20e4850b…` exactly. The qualified **85-case** selection did **not** include `tests/test_shadow_writer_coverage_scan.py`; it is historical evidence on unchanged Python, not full integration CI acceptance.

**GitHub CI failure at `080b5f88553bd0917eadc24d73e7967850aecec0` (run `38325044536`):** `pytest (3.12)` **1 failed**, 2995 passed, 121 skipped — sole failure `tests/test_shadow_writer_coverage_scan.py::test_static_scan_matches_inventory_routing`. Pylint, secret-scan and CodeQL passed. Log `/tmp/safe-harbor-t2-ci-38325044536-failed.log`. Cause: stale shadow inventory session call-site lines for `convmem.add` / `convmem.verify` (`421`/`525` in inventory vs actual `420`/`523`); metadata only, not runtime behavior.

### Shadow session call-site coordinate correction — captured isolated evidence

**[Arc Safe Harbor] Scope:** mechanical metadata fix on integration tip `080b5f8` before successor commit; Python fingerprint unchanged (`67b465b90b3c969a99e1d3ccced75ec7e90d9fd6a7e08fa2410591c400fd3678`).

**Pre-correction proof:** `/tmp/safe-harbor-t2-shadow-coord-20261013T005040Z` — `test_static_scan_matches_inventory_routing` exit **1** under uid-1000 allowlist.

**Correction:** `docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json` only — `production_chroma_write_session_call_sites` and matching `sites` records for `convmem.add` and `convmem.verify` updated to `convmem.py:420` and `convmem.py:523` (snippets unchanged). Regenerated R2b via `write_v2_inventory_file()` (idempotent second regen exit 0).

**Shadow → R2b identity:** shadow line-coordinate metadata **does** change derived R2b identity when regenerated: `code_revision` `84a9c83ff9592b60249068b7d035ebb42f329471`, `inventory_digest` `ff1e5f119339362bcf1929ea4fcd91c178fd14f96ce0313a2f0215ba6e1c7a97`, file sha256 `361690f04bb8895d160b733598659058f6727d73a7abbba4bb5412c4efad9cf5` (was `46801f24…` / `6bee3486…` / `b80587a9…`). Route count remains 36; route entries reflect updated shadow refs (location evidence, not routing-class changes).

**Post-correction pytest:** `/tmp/safe-harbor-t2-shadow-coord-20261013T005048Z` — exit **0**, `17 passed in 1.63s` for `tests/test_shadow_writer_coverage_scan.py`, `tests/test_r2b_v2_implementation_revision.py`, `tests/test_shadow_writer_gate_c3.py::test_all_writer_session_sites_inventoried`, `tests/test_shadow_writer_gate_c3.py::test_static_scan_zero_legacy_production_factory_calls`. Full argv in `post_pytest.json`.

**Next boundary:** fresh GitHub CI on the correction successor; final-tip external-review disposition, Ryan V2 acceptance/PR merge, deployment and T3–T5 remain ungranted. Event-only completion-success exclusion remains accepted; proof belongs to T4.

### Fresh final T2 review — governed-path identity FAIL

**Reviewed subject/base:** `45a1f002239644371d4813f3f010ece72c6fb865` / `8a7cdab16420893fe26a2648d1d03f2b84d8589d`. Fresh in-session Codex reviewer, followed by the coordinating Codex's source check; **FAIL, narrow (95% confidence in the static conclusion)**. This is neither BugBot nor Copilot evidence. No tests, production probes or edits by the reviewer; previous B1/F1/F2 remain closed in their stated scopes.

**CI at this subject:** [run `38329309684`](https://github.com/alanmz-crypto/convmem/actions/runs/38329309684), pytest **2996 passed, 121 skipped, 8 warnings, 252 subtests**, 1897.91s; pylint and secret-scan pass. CodeQL run `38329308857` also passes. Captured pytest log `/tmp/safe-harbor-t2-ci-38329309684-pytest.log`. Green CI did not exercise the counterexample below.

**Finding / source at subject:** original config `/data/chroma-link -> /data/store/chroma` puts existing governed files in `/data`. CLI preview reads that configuration (`convmem.py:1298,1366,1374`) and preflight enumerates its governed paths (`chroma_write_store.py:940-942`; `convmem.py:2062`). `AdmittedWriteOperation.config()` substitutes the canonical Chroma directory (`chroma_write_store.py:728-740`), passed to approval/recovery (`convmem.py:1395-1397,1342-1343`). `propose_decision.py:27-36` and `conflict_events.py:21-30` derive queue/approved/event/lock roots from that directory's parent; `hash_schema_gate.py:30,34` uses the same root. Consequently the actual call reads `/data/store` instead of the admitted original `/data`; approval/recovery can report the proposal absent (`propose_decision.py:623-627,235-244`). Recheck resolves original config again (`chroma_write_store.py:811-816`) and preview comparison only checks canonical Chroma equality (`convmem.py:2096-2104`). No retarget or configuration edit is needed. Existing alias fixtures share one parent (`tests/test_safe_harbor_t2.py:1039-1052`) and miss it.

**Limit:** this is a static path-identity finding, not a claim of a dynamically reproduced outside-root mutation. Runtime reproduction and actual downstream effects are required by [the owner-authorized correction](EXECUTION-safe-harbor.md#t2-governed-path-identity-correction--owner-authorized). Correction evidence is **NOT RUN** at this record. No final-tip PASS, outage exception, V2 acceptance or phase advancement is inferred.

### Governed-path identity correction — isolated evidence

**[Arc Safe Harbor] Authorship / subject:** Cursor implemented the bounded correction after grant `02e6fd2dfdef077ac1ed10cfafe96fda94e9771f`; Codex inspected and ran the qualified evidence. The final tracked-Python fingerprint is `3b9a72dfd575514e9240f730baa229591889c249e3f6bb63680ec2596c264c48` (sorted tracked Python paths plus NUL-delimited contents, SHA-256). The only production behavior change is `AdmittedWriteOperation.config()` preserving `configured_chroma_dir` for governed-file derivation. Both factories still open `op.chroma_dir`; returned `units_export` stays canonical. No new production helper, schema, gate policy or T4 behavior.

**Procedure correction / excluded attempts:** the first Cursor invocation ran several pytest attempts without the required outer pre-import allowlist, including a pipeline that hid pytest's return code; Codex stopped it and its children. Those attempts are not accepted evidence. Early fixture failures included reading TOML as JSON, observing the old fixture corpus, and mistakenly using the excluded event-only state. The initial full-run script was interrupted and is incomplete. There is no qualified claim about those attempts' pre-import isolation. Cursor then made static edits only; Codex controlled all accepted execution through `/tmp/safe-harbor-t2-governed-correction/evidence.py`. The original-runtime reproduction was obtained afterward in a scratch source copy, not before the initial edit; no claim of that ordering is made.

**Qualified isolation:** uid 1000; fresh temporary HOME/XDG/config/root/Restic/cache/TMPDIR with a clean allowlist before collection, imports, generation and every subprocess. No inherited provider credentials. Captured `environment.json`, each command's actual return code and stdout/stderr, dependency probe and source fingerprint before/after are in each directory below. No full default local suite. Python 3.13.12, Chroma 1.5.9, numpy 2.4.4, pytest 9.1.1; scratch Restic uses `/home/lauer/.local/bin/restic` (0.19.0). The qualified runs do not exercise production CLI/MCP/services/drives/corpus or manual session indexing.

- **Original-runtime sensitivity:** `/tmp/safe-harbor-t2-governed-reproduce-5c2eeb79`, exit **1**, **2 failed / 59 deselected**, 24.94s. Current tests/harness in a scratch source copy with `chroma_write_store.py` restored from `02e6fd2`; indexed approval fails with `Proposal not found`, retry-Chroma recovery with `Proposal not found in event log`. This is the actual old implementation, not an invented refusal. Earlier qualified reproduction `/tmp/safe-harbor-t2-governed-reproduce-qiq4xjgr` showed the same failures before test-helper cleanup.
- **Corrected focused evidence:** `/tmp/safe-harbor-t2-governed-focused-v4db8zfu`, exit **0**, **4 passed / 57 deselected**, 59.73s. Two real positive workflows plus two test-only old-canonicalization controls. Positives check the exact proposal in original queue/approved/events and canonical Chroma, all six alternate governed paths unchanged, exact canonical client paths, admission covering actual intended paths, and armed-census recovery. Negative controls fail those same effect assertions with the actual old path substitution and expose the alternate lock creation. Event-only completion success remains excluded.
- **Final affected suite:** `/tmp/safe-harbor-t2-governed-affected-gq7d_vio` — exit **0**, **98 passed**, 448.16s. Full T2, write-gate effect and record-review CLI files; four T1 alias/competing-location cases, two native stale-client cases, shadow scan/C3 coverage and R2b identity. Exact argv is in `affected.json`; tracked-Python fingerprint is unchanged before/after and matches the final focused/lint source. The earlier qualified run `/tmp/safe-harbor-t2-governed-affected-vs64nfj_` passed **98 cases**, exit 0, 442.18s, before test-helper cleanup; overlapping evidence, not 98 additional cases.
- **Final lint:** `/tmp/safe-harbor-t2-governed-lint-c3ucw2_3`; raw pylint **30**, regression gate **0**, **456 findings / 239 fingerprints**, no new/increased findings versus pinned main `8a7cdab`. Baseline unchanged. Earlier lint `/tmp/safe-harbor-t2-governed-lint-283u2__x` failed on six test-helper findings; those were corrected without a waiver.
- **Derived inventory:** `/tmp/safe-harbor-t2-governed-regen-xd3vsoqb`, both generator runs exit **0** and hashes equal. `code_revision=0df4d7882822db4af1f1abda8d41cc26a3892b6f`, `inventory_digest=dbe8d7dda7c6c1eb461a11e509195bd9f5a000ef88de5fdf86b947add92f5ae3`. All 36 route records are unchanged after removing their derived revision fields; shadow inventory is byte-identical to the grant tip. No identity algorithm/policy/allowlist change.

**Committed source/evidence:** `dac925f33d4ebd7482c0536408b9be12f51d6106`, pushed to the T2 task branch. All qualified final focused/affected/lint summaries match the committed Python fingerprint above.

**Independent in-session Codex bounded delta — PASS (95%) at `dac925f33d4ebd7482c0536408b9be12f51d6106`:** same reviewer who found the blocker at `45a1f00`; static correction review, no new tests or production probes. HEAD matched the subject and worktree was clean. Preserving configured spelling at `chroma_write_store.py:743` aligns governed consumers with admission; factories still explicitly use canonical `op.chroma_dir` at `:1035,1092`, export pin and all earlier rechecks remain. Four new cases (`tests/test_safe_harbor_t2.py:1257` onward), real faulty-substitution controls, final captured 98-case/lint results and derived-only inventory delta support closure. No actionable correction regression found. Initial ambient attempts/interrupted run remain excluded; no assertion of their isolation or absence of incidental access. The PASS is pinned to its exact subject; this documentation successor is not an automatic transfer of an external-review gate.

**Boundary at that correction handoff (historical):** fresh final-tip CI and Ryan's review/V2 acceptance were pending. They are now resolved in the V2 acceptance record above; the old `45a1f00` CI never substituted for final-head CI. T3–T5 and live operations remain ungranted.

### Historical prepared T2 draft PR text — now opened as #389

Title: **Bind risky writes to their backup target and reject future snapshots**

Copy-ready body (links are relative to the repository root):

```markdown
The named risky-write and approval-recovery CLI paths now check their resolved target against the backup context and refuse future snapshots. Recovery also works with an armed writer census. Existing index/plain-add exemptions remain unchanged.

Who: Cursor implemented Safe Harbor T2; Codex coordinated evidence and Copilot's independent review. When: 2026-10-12. Why: prevent a snapshot for another target or a suspicious future time from admitting the named operations. How: reuse existing admission and v2 resolver interfaces, enforce production-skip refusal, and synchronize the gate policy docs.

**TL;DR:** T2 binds the named CLI operations to v2 backup eligibility. It does not demonstrate restoration or successful event-only recovery.

## Merge reading

- [T2 evidence and independent reviews](docs/plans/VERIFY-safe-harbor.md#independent-b1-delta-review--pass)
- [Current arc status](docs/plans/STATUS-safe-harbor.md)
- [Execution contract and grants](docs/plans/EXECUTION-safe-harbor.md#9-cursor-t2-execute-handoff--owner-granted)

## Evidence and limits

- Initial runtime: 133 focused + 103 distinct regression cases passed; fixture refresh: 64 overlapping cases passed.
- Corrected runtime/tests `964c1decb1a8366226ad45345ae26ed909542569`: 153 affected cases passed, including 3 new armed-census controls; pytest exit 0, lint regression gate exit 0 (raw pylint 30).
- Copilot full review at `05c7706` found B1; delta PASS (88%) at `82f25efb4696325afa83298fae0e1ca698f1d7fe` closes it. Later review-record edits do not transfer exact-tip review automatically.
- Owner accepted the event-only success evidence exclusion. T4 must align hash views and prove real success; no T4 implementation grant is implied.
- Fresh PR CI and final-tip PR-native BugBot evidence remain pending. No T2 outage exception exists.
- No production health checks, restoration qualification or live operations; T3–T5 and deployment remain unauthorized. Not merge-ready.
```


## V3 — Preservation and bounded restore (T3)

**NOT RUN.** Original bytes write-once; preservation complete before replacement; pinned source generations; all interruption/IO failure windows; restore aborts initiating mutation even after clean census; only incident-bound existing repair may cross quarantine; persistent census failure remains contained.

### T3 initial authoring checkpoint — not accepted, not executed

Cursor’s first text-only draft is retained for provenance. Static inspection found contract violations before test execution: repair sidecar instead of prior publication in the sole incident authority; reconstruction of missing snapshot evidence from live state; incomplete manifest/digest/path binding; inadequate stale-disposition binding; missing repair resumption and failure-window evidence. The new launcher also needs bootstrap/import and exit-status corrections. These are implementation defects under the existing T3 grant, not a new direction decision. No new tests/runtime probes were executed. Cursor correction is required before supervised evidence. This checkpoint is not a T3/V3/V4 PASS or merge candidate.

## V4 — Release and stale-vector proof (T3)

### Pinned-backend ordering gate — isolated proof (2026-10-13)

**Cursor delivery verdict at `8c4ad911922d967ccbcdd2fd6e4ba8b40e0c2f55`: DEMONSTRATED (not accepted by the Codex review below).** On the pinned Chroma **1.5.9** / **hnswlib 0.8.0** backend under synthetic scratch fixtures. Cursor proposed closing the execution section 10 / Kiro A1 backend ordering gate; Codex found proof gaps and leaves it open. It is **not** V4 acceptance, not V3 preservation/repair evidence, and not production release authorization.

**Cursor-reported runner / environment (isolation claim unqualified; see R2 below):** Cursor; uid **1000**; `/home/lauer/miniforge3/bin/python` **3.13.12**; **numpy 2.4.4**; disposable roots under pytest `tmp_path` with scrubbed provider credentials and no production `HOME`, corpus, Restic, doctor, MCP or indexing. Cursor described child workers as inheriting the same allowlist; R2 identifies the actual ambient-environment inheritance and qualification gap.

**Command (exact):**

```bash
cd /home/lauer/Projects/convmem/.worktrees/feat-2026-10-12-safe-harbor-t3-backend-proof
env -u DEEPSEEK_API_KEY -u OPENAI_API_KEY -u ANTHROPIC_API_KEY \
  /home/lauer/miniforge3/bin/python -m pytest tests/test_safe_harbor_t3_backend_proof.py \
  -v --tb=line -p no:cacheprovider
```

**Result:** exit **0**; **5 passed in 4.41s** (2026-10-13 local). `pylint -sn` on the two proof modules reported no new findings beyond a duplicate-code note between test and worker embedding helpers.

**Harness:** `tests/test_safe_harbor_t3_backend_proof.py` implements a **test-local** strict empty-changed-set predicate aligned with execution E1 (saved vector watermark, matching metadata/vector segment identities, zero `embeddings_queue` rows with `seq_id` above the saved watermark, segment signature/digest equality, `vector_census` lost/extra zero, and subprocess embedding reads). `evaluate_census_only_predicate` is the deliberate blind-spot control. No production `SNAPSHOT.json`, quarantine release, or preservation/repair code was added.

**Demonstrated observations (pinned backend):**

| Case | Outcome |
|---|---|
| Backend identity | `chromadb==1.5.9`, `PersistentClient`, SQLite `max_seq_id` + `embeddings_queue` watermarks recorded |
| Mutation sequence | add → metadata update → embedding update → upsert → delete → reinsert; watermarks monotonic; queue length drops after vector sync (`sync_threshold=3`) |
| Restart | fresh subprocess `restart_ping` preserves terminal watermarks (not power-loss proof) |
| Valid releasable control | quiescent synced generation admits strict predicate after restart |
| Stale-vector control | same-ID embedding change with restored older vector segment: **`vector_census` lost=0** but subprocess read shows stale vector; strict predicate **refuses** (`watermark_drift` / embedding mismatch) |
| Census-only control | admits the stale fixture; fails independent safety assertion in-test |
| Binding / negative | wrong segment id, missing watermark, and empty-queue + digest mismatch refuse without client open |

**Limits / still NOT RUN for V4 overall:** Ryan disposition binding, added-finding invalidation, durable disposition-before-marker-removal, truncated event tail, directory-fsync failure injection, and production `events.jsonl` release publication. V3 remains NOT RUN. A passing gate does not authorize remaining T3 implementation without a new grant.

**NOT RUN (remainder).** Complete current incident set and Ryan disposition binding; added-finding invalidation; durable disposition before marker removal; truncated event tail and uncertain unlink/fsync behavior; production release-publication fsync assertions. Process restart evidence above is not hardware power-loss proof.

### Codex review of the T3 proof — NOT DEMONSTRATED

**Subject:** `8c4ad911922d967ccbcdd2fd6e4ba8b40e0c2f55`, exactly matching local and remote proof branch at review. **Verdict: NOT DEMONSTRATED for the complete ordering gate (95% confidence in this review conclusion, not incident probability).** This is a local proof/harness correction, not evidence that the approved release architecture is impossible. Remaining T3 implementation is not authorized. Cursor may correct the harness/evidence within the existing proof-only scope; return results before any runtime implementation.

**Method:** static code/diff and captured fixture-artifact reads only. No tests or backend probes rerun, no production CLI/MCP/indexing, no paid reviewer. This is a Codex static review, not a BugBot/Copilot service verdict. No production runtime file changed in Cursor's delivery.

**Evidence retained:** `/tmp/safe-harbor-t3-pytest.log` records five passes in 4.41s. The saved fixture JSON under `/tmp/safe-harbor-t3-bind2-ppA3/tmp/pytest-of-lauer/pytest-1/` reports `(metadata, vector)` positions `(1,0),(2,0),(3,3),(4,3),(5,3),(6,6)`, queue lengths `1,2,1,2,3,1`, terminal restart `(6,6)`, and stale refusal `watermark_drift meta=4 vec=4 saved=2`. These support the observed examples. They are not a captured process return-code record, source/harness fingerprint or proof that the exact documented launcher provided the required outer isolation. No production access is asserted to have occurred.

**R1 — The tested predicate is not the accepted client-free release predicate (interface/proof blocker, 98%).** At the reviewed tip, `tests/test_safe_harbor_t3_backend_proof.py:217-233` adds inode-bearing `segment_signature` equality and then opens a Chroma client through the worker to compare fixture-supplied `expected_embeddings`. The accepted E1 inputs are persistent source/state evidence; validation forbids client opening (`EXECUTION:125,132`). `chroma_write_guard.py:363-376` includes inode and mtime in this signature, and existing restoration replaces files (`:1402-1407`). The valid control (`tests/test_safe_harbor_t3_backend_proof.py:339-358`) checks the unchanged generation after restart, not the same generation copied into replacement files, so it misses legitimate restore rejection from inode change. The stale refusal in the captured run is genuinely watermark-based, which is retained; that does not establish faithful admission for restored good bytes. **Correction:** separate the persisted-input predicate from independent vector/content assertions; no Chroma open or fixture gold vectors inside the candidate predicate. Use content/collection/segment/source binding per the accepted contract, with a scratch same-generation replacement positive control. Run byte/content observations separately before any replay-capable client open and label subsequent mutating fixture reads.

**R2 — The promised isolation/identity evidence is not established by this harness (local proof-safety blocker, 95%).** `VERIFY`'s launcher only removes three keys; the fixture (`tests/test_safe_harbor_t3_backend_proof.py:244-272`) sets roots after pytest startup/collection and uses a denylist. `_worker` (`:103-112`) copies the remaining ambient environment rather than building an allowlist. XDG_RUNTIME_DIR and backend-selecting environment are not controlled. Worker `_require_isolated` checks environment roots, but its actual `chroma`/output argv (`tests/_safe_harbor_t3_backend_worker.py:185-207`) are not constrained to the fixture root, and uid is reported rather than enforced. The backend test (`tests/test_safe_harbor_t3_backend_proof.py:288-310`) records a literal `PersistentClient` label rather than inspecting the actual API/segment/native backend; no schema/native-origin evidence is captured. Existing `/tmp` nesting suggests an outer environment may have been used, but the report neither preserves nor documents it sufficiently to qualify that claim. **Correction:** a reproducible stdlib launcher builds/records the clean environment before pytest/imports, workers validate actual resolved input/output paths and uid, and actual backend/schema/native identity is recorded. Remain within the two granted harness files and synthetic data; no live probe is needed.

**R3 — Required semantics and sensitivity checks are incomplete (local proof blocker, 95%).** `tests/test_safe_harbor_t3_backend_proof.py:325-328` accepts constant watermarks and merely compares queue minimum/maximum; a queue that only grows would pass its purported purge check. The observed trace does purge, but the assertion does not enforce that property. No test proves each real semantic mutation advances the metadata evidence, validates delete/reinsert content after restart, or isolates two collections as required by section 10. All cases use one collection. The digest control (`:444-449`) permits a signature mismatch; its saved result is `segment_signature_mismatch`, so it does not exercise the digest check. Likewise `metadata_claims_n99=True` (`:392`) is supplied by the test rather than asserted against an observed row. **Correction:** assert per-operation logical outcomes and evidence advancement; demonstrate a real adjacent queue decrease and the absence of later relevant operations using raw queue rows; cover two collections; assert the exact refusal reason for missing/mismatched evidence. Isolate digest/content corruption from incidental inode/mtime changes, and exercise the proposed predicate versus the faulty census-only predicate against the same independent stale-state assertion.

**Evidence/routing correction:** preserve Cursor's original report and failed attempts as history. Capture exact commands, return codes, source/harness hashes, actual backend/environment and raw observations for the corrected run. Report a partial/unavailable result honestly rather than setting a global DEMONSTRATED label in one binding-test fixture. Keep STATUS/LATEST and the cross-arc row aligned; full V4 and V3/V5/V6 remain NOT RUN.

**Stop rule:** one bounded correction and delta against R1–R3, with existing T1/T2 runtime and accepted contracts unchanged. Do not broaden into preservation/repair/release implementation, install dependencies, invoke paid reviewers, open a PR, merge or operate on production. A failed or unsupported predicate returns to Codex/Ryan; no census-only substitute.

### T3 R1–R3 corrected proof — qualified evidence

**[Arc Safe Harbor] Result returned on 2026-10-13: DEMONSTRATED in the pinned synthetic fixtures (90% confidence in this bounded conclusion).** R1–R3 corrections are committed at `93d4e344c8959ed0176b3a9b39af7be3f638f148`, on `feat/2026-10-12-safe-harbor-t3-backend-proof`, from clean review-record parent `2f00e8c283b5c87726d3efb8f5588e4be970fee4`. Only the two granted proof files change executable behavior; production runtime is unchanged from the merged T2 baseline. This delivers the ordering-gate evidence for Ryan's decision. It does not accept full V4 or grant the remainder of T3.

**Authorship and review boundary:** Cursor Composer authored the correction; Codex stopped an unsafe probe session, made further bounded harness corrections, and ran the qualified launcher. This is jointly corrected proof and supervised verification, **not an independent Codex review of unchanged Cursor work**. The original review remains pinned to `8c4ad91`; no external-review PASS is inferred for this successor.

**Reproduce from the proof worktree:**

```bash
/home/lauer/miniforge3/bin/python -I -S -B tests/_safe_harbor_t3_backend_worker.py run-proof
```

The stdlib bootstrap enforces isolated/no-site/no-bytecode flags and uid 1000, creates a fresh root, and starts pytest and focused pylint with a recorded clean allowlist before package/project imports. It uses child flags `-s -B`, allowing the pinned installed packages while disabling user site and bytecode. It sets fresh HOME, every XDG root including runtime, ConvMem config/root/Restic-env, Restic cache and TMPDIR; no provider credentials are inherited. The fixture config is empty and its Restic env is absent. Workers validate actual resolved input/output paths before opening a store. Each subprocess has a 300-second limit; no final-run timeout occurred.

**Final qualified run:** `/tmp/safe-harbor-t3-s9ejarj3`. Launcher exit **0**; pytest exit **0**, **9 passed in 8.08s** (captured subprocess elapsed 8.311729s); focused pylint exit **0**, no messages (4.395689s). `summary.json` holds exact child argv, statuses, timeout, flags and before/after hashes. `environment.json`, `pytest.log`, `pylint.log`, and per-case `fixture/pytest-tmp/test_*0/v4-backend-proof-evidence.json` retain raw evidence. Local `/tmp` artifacts are not a durable backup; this committed summary and the reproducible harness preserve the decision-relevant result.

**Actual identity:** uid 1000; `/home/lauer/miniforge3/bin/python` 3.13.12; pytest 9.1.1; chromadb 1.5.9; hnswlib 0.8.0; numpy 2.4.4. The actual client is `chromadb.api.client.Client`, its server is `chromadb.api.rust.RustBindingsAPI`, and its native binding type is checked against the loaded native module. The module origin is `/home/lauer/miniforge3/lib/python3.13/site-packages/chromadb_rust_bindings/chromadb_rust_bindings.abi3.so`, SHA256 `a9794735847c3a78c15931d869cee8368fddbb10048c3d098bc09a14130075ad`. SQLite schema digest is `c96a6b960fc8366bb3b0051a268ebd85ccc5d2ca5280a06effc0930a6bd052d5`; observed migration versions are `[1,1,1,2,2,2,3,3,4,4,5,5,6,6,7,8,9,10]`. The source manifest also binds collection and metadata/vector segment IDs, saved vector watermark, backend identity and segment content digests.

Before/after SHA256 values are identical:

```text
test_safe_harbor_t3_backend_proof.py
6d70830d58ee1b9670b21dc1f7c5929d7597d2e2032468421a6618422d430c5e
_safe_harbor_t3_backend_worker.py
c82994c4ea9b5398a93ebc6a84251c0bc08970bbef3205128f1084ef9f2c5558
chroma_write_guard.py (unchanged production source)
63b228d9e9f05b798b4141bc818d034c9e4528bf79fe280ffb696257bcef0d73
```

**R1 — predicate fidelity and sensitivity corrected.** `evaluate_persisted_release_predicate` consumes persisted identity, watermark, queue and content evidence without opening a Chroma client or accepting fixture gold vectors. It requires structural validation and census as additional conditions. Missing evidence refuses; there is no missing-sequence-to-zero or first-segment fallback. Content digests replace inode-bearing equality. The valid fixture admits after native restart and after copying the same generation into replacement files; a fresh client-free observer records identical content. Separate safety assertions inspect persisted HNSW float32 vectors via header/label metadata, comparing every normalized component. The stale fixture is inspected before any replay-capable client open. The same admission-plus-independent-safety workflow passes for the valid strict case, refuses the stale strict case, and fails its safety assertion when the deliberately faulty census-only predicate admits that stale case.

**R2 — isolation and actual identity corrected.** The recorded bootstrap replaces ambient-environment inheritance. The test module refuses unsafe entry before pytest/project imports. Controls invoke the actual worker with an outside input, outside output and symlink escape; each refuses without creating the outside destination. A simulated uid-zero check refuses (the real process remains uid 1000). Actual API/native/schema identity and resolved fixture paths are captured rather than supplied as literal success labels. This qualifies the final launcher run, not the excluded earlier Cursor probes below.

**R3 — semantic operations and collection-specific controls corrected.** The real add → metadata/document update → embedding update → same-ID upsert → delete → reinsert trace asserts logical IDs/content/metadata/full normalized vectors and strictly advancing metadata evidence at each mutation. Its observed `(metadata, saved-vector)` positions are `(1, absent), (2,2), (3,2), (4,2), (5,5), (6,5)`. Queue lengths are `1,1,2,3,1,2`; the asserted adjacent decrease removes rows 2,3,4 and retains row 5. Raw topic/sequence rows are recorded, not just min/max counts. After fresh restart, metadata is 6, saved-vector is 5, and one newer operation remains pending: the client presents the reinserted vector while persisted segment `a` is still absent. The proof records this distinction; restart is not treated as a forced save or a releasable state.

The synced positive fixture has metadata/vector/source position **100/100/100**, no later relevant queue row, passing structural validation/census and matching digests. The stale fixture has source **100**, current metadata/vector **102/102**, old segment vectors and observed metadata `n=99`; the strict predicate refuses with `watermark_drift meta=102 vec=102 saved=100`. The census-only control admits and fails the independent vector safety assertion. Two-collection coverage admits unchanged A after B mutates. Exact controls observe `collection_id_mismatch`, `segment_identity_mismatch`, `missing_vector_watermark`, `sequence_evidence_missing`, `chromadb_version_mismatch`, `sqlite_schema_digest_mismatch` and `segment_digest_mismatch`. Mtime-only changes still admit. Missing-row SQL deletion and unsupported-sequence cases are explicitly synthetic fault injections, not claimed as natural purge evidence.

**Unexpected results and exclusions — preserved:**

- The first Cursor session ran ad-hoc package/client probes before the required clean allowlist, including fixed `/tmp/chk-chroma`. Codex stopped that dispatched process (SIGTERM, exit 143), inspected the transcript, and resumed Cursor with text-only instructions. Its probes and early test/lint attempts are **excluded** from qualified evidence. Visible store targets were in `/tmp`; this does **not** establish that the entire attempt had no global or production side effects. No production corpus target appears in the inspected commands. Raw transcript: `/tmp/safe-harbor-t3-cursor-correction-retry.jsonl` and matching `.stderr`; subsequent text-only continuations are `/tmp/safe-harbor-t3-cursor-text-only.jsonl` and `/tmp/safe-harbor-t3-cursor-text-fix.jsonl`. The initial CLI startup failure is preserved in `/tmp/safe-harbor-t3-cursor-correction.jsonl`/`.stderr`.
- Qualified development run `/tmp/safe-harbor-t3-bc7e8ssr`: pytest **1**, **3 passed, 3 failed**, pylint **28**. Native Chroma preallocates 100 HNSW slots for a two-row fixture; the unchanged structural validator rejects `data_level0.bin` 20400 versus expected 408 bytes and `length.bin` 400 versus expected 8. Another failed assertion incorrectly expected the latest reinsert to be saved after restart despite metadata 6/vector 5 and a pending operation. The correction distinguishes saved state from client replay and fills the positive fixture's initial capacity with **real native inserts** (two target IDs plus 98 padding IDs). No runtime validator change or truncation/normalization of backend files was used to obtain PASS.
- Qualified development run `/tmp/safe-harbor-t3-c7mlhylq`: pytest **1**, **7 passed, 2 failed**, pylint **2**; Codex had removed a still-used `segment_vector_synced` import. The import was restored. This was a harness defect, not a backend result.
- Qualified earlier successor `/tmp/safe-harbor-t3-qikcwppx`: pytest **0**, **9 passed in 8.19s**, pylint **0**. Superseded by the final run above after bootstrap-flag enforcement and actual native-module identity refinements. It is not nine additional distinct cases.

**Limits and next decision:** the observations support the strict oracle in these pinned synthetic cases, not arbitrary backend states or hardware durability. The existing structural validator still conservatively rejects small stores with unused native capacity; that release-availability limitation is carried to later T3 planning, not silently fixed here. No preservation, repair, quarantine release, fsync-failure lifecycle or full V4 implementation exists in this proof. Process restart is not power-loss evidence. No full default suite or GitHub CI was run. Ordinary unqualified pytest entry intentionally refuses before project imports; therefore standard-suite/CI integration is **not demonstrated** and this branch is not declared merge-ready. No dependency, inventory, policy, production runtime, service, drive, backup or permission change was made. Ryan receives the proof and decides acceptance and any remaining T3 grant; no automatic advance.

#### Copy-ready PR text — not authorization to open

**Title:** Prove recovery watermarks with isolated persisted-state checks

```markdown
Safe Harbor now has reproducible evidence for the strict recovery-release oracle on pinned synthetic Chroma stores. This adds proof fixtures only, not a production release path.

Who: Cursor authored the correction; Codex made bounded harness corrections and captured qualified evidence. This is not an independent review.
What/when: R1–R3 proof correction, source 93d4e344c8959ed0176b3a9b39af7be3f638f148, delivered 2026-10-13 on feat/2026-10-12-safe-harbor-t3-backend-proof.
Why/how: client-free persisted-state admission, independent stale-vector controls, clean pre-import isolation and real mutation/purge/restart observations replace the incomplete original proof.

TL;DR: Nine isolated cases and focused pylint pass; owner acceptance and remaining T3 implementation are separate. Small-store validation and standard-suite integration remain limitations.

## Merge reading

- [Evidence and exclusions](docs/plans/VERIFY-safe-harbor.md#t3-r1r3-corrected-proof--qualified-evidence)
- [Current scope and next decision](docs/plans/STATUS-safe-harbor.md)
- [Proof-only grant](docs/plans/EXECUTION-safe-harbor.md#10-cursor-t3-pinned-backend-proof--owner-granted)

## Evidence

- [x] Qualified launcher: pytest exit 0, 9 passed in 8.08s; focused pylint exit 0.
- [x] Valid replacement-generation admission and stale refusal; census-only negative control fails the independent safety assertion.
- [x] Source/harness hashes stable; runtime unchanged; excluded attempts disclosed.
- [ ] Full suite / CI / merge readiness not established. Unsafe ordinary proof invocation refuses.
- [ ] No preservation/repair/release, full V4, PR-native review, merge or deployment approval.
```

### T3 isolation investigation and independent ordering-gate review

**2026-10-13, Codex inspection (90% in the narrow command finding):** inspected the complete recorded tool calls of `/tmp/safe-harbor-t3-cursor-correction-retry.jsonl` (SHA256 `3f317f92e6f1c5121edaf6d62873b8efe764db064ad4a809a47b5f270d88275e`) once: 14 shell calls, 14 edits, 11 reads, 13 greps. All edits targeted the two permitted proof files. Unqualified Chroma probes used explicit temporary stores or `/tmp/chk-chroma`; no recorded production corpus target, ConvMem command, service, backup/key or provider action was found. Early failed launcher attempts and the final interrupted invocation without a result remain excluded from proof. Subsequent text-only correction sessions contain no shell calls.

This is **not proof of zero side effects**: inherited environment/startup, temporary-root selection and import-time cache/telemetry effects lack a complete trace. Installed Chroma’s product telemetry module computes a HOME-derived cache path at import and may create an identifier. The expected production cache file was absent when inspected; that does not establish past absence. No production corpus inspection or cleanup was attempted. Inspection stops here unless new concrete evidence appears. Scratch command inventory: `/tmp/safe-harbor-t3-independent-2wdkhyw8/isolation-inspection.json`.

**Independent Kiro review: PASS, 82%, at exact proof tip `e08100ff1c2fe8474f897d6ae3d3c55e5b1c7e5f`, source `93d4e344c8959ed0176b3a9b39af7be3f638f148`.** A fresh Kiro session had only read tools, no MCP/hooks, and inspected pinned source/evidence. R1 persisted-only predicate/copied-generation positive/independent stale control PASS 85%; R2 pre-import allowlist/real backend identity PASS 82%; R3 mutation advancement/purge/restart/collection binding PASS 85%. No blocker or required correction for the accepted ordering prerequisite. It supports **isolated T3 implementation only**, not V4 acceptance or merge/live readiness.

The review keeps small-store validation and CI integration limitations open. It did not execute tests or prove power-loss durability and could not open every per-case JSON path; recorded output and source assertions supply the remaining support. A first dispatch failed read-tool trust configuration and delivered no substantive verdict; the read-only retry completed exit 0. Full local verdict: `/tmp/safe-harbor-t3-independent-2wdkhyw8/verdict.txt`, successful trace `review-retry.jsonl`. No paid Copilot/BugBot trigger was issued.

**Owner continuation:** Ryan’s instruction to investigate once, obtain the bounded independent review, then proceed is satisfied. [EXECUTION section 11](EXECUTION-safe-harbor.md#11-cursor-remaining-t3--conditional-owner-grant-satisfied) grants isolated T3 implementation with Cursor authoring and Codex-supervised clean-bootstrap execution. V3/remainder-V4 remain NOT RUN until actual implementation evidence exists; no T4/T5 or live grant follows.

## V5 — Approval recovery (T4)

**NOT RUN.** Cold/warm caches; unknown/absent/tombstoned/conflicting/matching states; direct and CLI callers; actual lease/governed/native/export order; forced forget/refine competition; target substitution; partial Chroma/export/event completion and retry. Cover failure before completion append, partial record, complete record with failed fsync, and durable record followed by interrupted return. An unsuccessful invocation may leave APPROVED; assert truthful uncertain-outcome reporting, authoritative reread/reduction before retry, durability establishment before success, no duplicate approval/blind re-upsert, no hidden export loss and no automatic malformed-tail deletion. Readable bytes alone do not prove durability. All cases remain unrun.

Explicitly cover new-log creation versus append to an existing durable log: file fsync in both, parent-directory fsync for creation, and durable publication of any newly created directory entries. Inject each required directory-fsync failure; require uncertain-outcome reporting and authoritative retry without duplicate approval, not a false APPROVAL_STARTED assertion. These are scheduled assertions, not executed evidence.

## V6 — Integrated handoff and independent sign-off (T5)

**NOT RUN.** All required cases and negative controls accounted for at the implementation tip; policy docs synchronized; no production/drive/provider access; truthful scope/operational prerequisites; written independent verdict with residuals and Ryan gate. Reviewers perform no cleanup or corrective live operations.

## Evidence log

| When | Runner | Subject | Command / case | Result | Pointer |
|---|---|---|---|---|---|
| 2026-10-13 | Codex-supervised corrected harness, uid 1000, clean allowlist; Python 3.13.12 / chromadb 1.5.9 | source `93d4e344c8959ed0176b3a9b39af7be3f638f148` | stdlib `-I -S -B` launcher; nine proof cases and focused pylint | qualified pytest **0**, **9 passed in 8.08s**; pylint **0**; stable hashes | [Corrected proof](#t3-r1r3-corrected-proof--qualified-evidence), `/tmp/safe-harbor-t3-s9ejarj3` |
| 2026-10-13 | Cursor, miniforge Python 3.13.12, uid 1000; chromadb 1.5.9; numpy 2.4.4; hnswlib 0.8.0 | proof branch `feat/2026-10-12-safe-harbor-t3-backend-proof` (parent `324dfc5`) | `pytest tests/test_safe_harbor_t3_backend_proof.py -v --tb=line -p no:cacheprovider` under reported disposable roots | historical Cursor **DEMONSTRATED** claim, exit 0, `5 passed in 4.41s`; Codex review rejected full gate/isolation qualification | V4 original report and R1–R3 review |
| 2026-10-11 | Cursor, isolated miniforge Python 3.13.12 | runtime `fa82028b762e5564eed9f2884336ccfb0e3caf73` | `pytest tests/test_safe_harbor_t1.py tests/test_chroma_write_guard.py -q --tb=line` under temporary HOME/XDG/CONVMEM_CONFIG | historical PASS, exit 0, `41 passed in 40.45s`; does not close the three correction gaps | V1 historical paragraph |
| 2026-10-11 | Cursor, isolated miniforge Python 3.13.12; chromadb 1.5.9; numpy 2.4.4 | runtime `496792fad80d9759ca26e5cbf2ad7d6cd60bc28e` | same pytest command under `/tmp/safe-harbor-t1-2J2Z` | PASS, exit 0, `43 passed in 43.56s`. Expected control failure: overwrite publisher dropped finding A | V1 corrected table |
| 2026-10-11 | Cursor | corrected runtime parent; review tip is the evidence commit | BugBot exact-tip review | not satisfied — usage limit, no reviewed SHA | draft #387 |
| 2026-10-11 | Cursor, miniforge Python 3.13.12 | CI correction after merging `db8aebb` | standard pytest of T1, guard, and R2b identity tests; `CONVMEM_T1_ISOLATED` unset; `HOME=/home/lauer` | PASS, exit 0, `61 passed in 50.90s` | CI correction section |
| 2026-10-11 | Cursor | same tree | `write_v2_inventory_file()` | regenerated `code_revision` `43a3944df8d6264dfc3a25016ab9b48111f69688`; route policy unchanged | inventory artifact |
| 2026-10-11 | Cursor, miniforge Python 3.13.12; uid 1000 | test code `8b410445ac55f3a5dafede030a40f26c318ae784` | standard pytest of T1, guard, and R2b identity tests; `CONVMEM_T1_ISOLATED` unset; `HOME=/home/lauer` | PASS, exit 0, `63 passed in 50.57s`. Expected control failures: old shared undo loses isolation; pre-lock audit pause yields `acquired`, not `contended` | Review-evidence correction section |
| 2026-10-11 | Cursor, same interpreter | same | T1 + guard with outer roots under `/tmp/safe-harbor-t1-bnMa` | PASS, exit 0, `45 passed in 49.69s` | Review-evidence correction section |
| 2026-10-11 | GitHub Copilot audit lane (relayed by Codex) | `2977c4531cf446974b0c86994dbca757715dca76` | static delta review of the two corrections | PASS, 85%; not BugBot | Copilot delta review section |
| 2026-10-11 | Cursor, same interpreter, uid 1000 | integration merge `c624e2f39a2f76a18eacca76d9affb7f7dff6f50` (main `5550def`) | `write_v2_inventory_file()` isolated; tip verification | `code_revision` `87b8144dff3a6ec45fad5ef8a82e332d17bb4698`, digest `e7f544a0…62b0`; verify `[]` | Integration evidence section |
| 2026-10-11 | Cursor, same interpreter, uid 1000 | same | standard pytest T1 + guard + R2b identity, real `HOME`; outer-isolated T1 + guard | PASS, `63 passed in 58.22s`; PASS, `45 passed in 41.47s` | Integration evidence section |
| 2026-10-12 | Cursor, miniforge 3.13.12, restic 0.19.0 scratch | T2 trees `77a590b` / `262573e` | scoped isolated pytest selections (V2 table) | observed `64` / `86 passed, 4 failed (uid 0 lchown)` / `60` (uid 1000) / `133` passed; **pytest exit not captured** (piped to `tail`) | V2 isolated evidence |
| 2026-10-12 | Cursor | `262573e` tree | pylint regression gate vs `9664878` | PASS, `gate_exit=0` captured | V2 isolated evidence |
| 2026-10-12 | Cursor | final source `44e29f6` | AST equality vs `262573e`; shadow `cmp`; `write_v2_inventory_file()` + both verifiers | `ast_equal True`; `cmp` exit 0; verifiers `[]`, exit 0 | V2 source identity |
| 2026-10-12 | Codex, uid 1000, clean-allowlist env | final source `44e29f6` | focused pytest (10 files) | PASS, pytest exit 0, `133 passed, 2 warnings in 288.86s` | V2 final evidence |
| 2026-10-12 | Codex, same | same | regression pytest (5 files, incl. former `lchown` cases) | PASS, pytest exit 0, `103 passed, 1 warning in 444.68s` | V2 final evidence |
| 2026-10-12 | Codex, same | same | pylint + regression gate vs `9664878` | pylint raw 30; gate exit 0 PASS, 461 findings / 239 fingerprints, none new | V2 final evidence |
| 2026-10-12 | Cursor | fixture `2459acd` | `py_compile` + pylint on the two changed test files; R2b identity and shadow `cmp` | compile 0; pylint 0, no messages; identity `ff340158…` unchanged; `cmp` 0 | V2 event-only section |
| 2026-10-12 | Codex, uid 1000, clean-allowlist env | test/fixture `2459acd` (runtime = `44e29f6`) | refresh pytest (4 files, overlaps focused batch) | PASS, pytest exit 0, `64 passed in 284.85s` | V2 refresh |
| 2026-10-12 | Codex, same | same | pylint + regression gate vs `9664878` | pylint raw 30; gate exit 0 PASS, 465 findings / 239 fingerprints, none new | V2 refresh |
| 2026-10-12 | Cursor | B1 `964c1de` | isolated `write_v2_inventory_file()` + both verifiers; shadow `cmp` vs `c188a09` | `code_revision` `05362dba…`, digest `62240f8a…`; verifiers `[]`; `cmp` 0 | V2 B1 correction |
| 2026-10-12 | Cursor, uid 1000, clean-allowlist env | B1 `964c1de` | new armed-census positive/future/old-label cases | PASS, pytest exit 0, `3 passed, 45 deselected in 37.79s` | V2 B1 correction |
| 2026-10-12 | Cursor, same | same | affected T2/caller/census/inventory pytest (12 files) | PASS, pytest exit 0, `153 passed, 2 warnings in 339.06s` | V2 B1 correction |
| 2026-10-12 | Cursor, same | same | pylint + regression gate vs `9664878` | pylint raw 30; gate exit 0 PASS, 466 findings / 239 fingerprints, none new | V2 B1 correction |
| 2026-10-12 | Cursor, cloud VM uid 1000 | target-binding `a18df48025cac77de8bda2db5a761f4744a9a963` | pytest selections above | PASS, pytest exit 0, `5` + `10` cases | Target-binding correction section |
| 2026-10-12 | Cursor, uid 1000, `/tmp/safe_harbor_t2_collect.py` | F1/F2 `cdebf64b487ffa27d61955df9739204829864fe0` | inventory + 9 target-binding + 42 regression + lint gate | all batch exits **0** | F1/F2 correction section |
| 2026-10-12 | Cursor, isolated generator env | same | `write_v2_inventory_file()` + `test_r2b_v2_implementation_revision` | `dc714d0a…`, digest `5cbc5a99…`; verifier `[]` | Target-binding correction section |
| 2026-10-12 | Codex coordinator, uid 1000, `/tmp/safe-harbor-t2-integration-evidence-20261012T234749Z` | pre-merge integrated tree; runtime `cdebf64`; merge `551b16c` | inventory regen + 85-case combined pytest + pylint raw 30 + gate vs `8a7cdab` | inventory **0**, pytest **0** (`85 passed in 391.54s`), gate **0**; fingerprint `20e4850b…` stable | T2 branch integration section |
| 2026-10-12 | — | early dev inventory attempt | login-shell regen `/tmp/safe-harbor-t2-integration-20261012T234506Z` | **not accepted** — inherited ambient env | T2 branch integration section |
| 2026-10-13 | GitHub Actions `38325044536` | head `080b5f8` | full `pytest (3.12)` | **1 failed** — shadow static scan vs inventory routing | Shadow coordinate section |
| 2026-10-13 | Cursor, uid 1000, `/tmp/safe-harbor-t2-shadow-coord-20261013T005040Z` | pre-fix `080b5f8` | `test_static_scan_matches_inventory_routing` | exit **1** (expected) | Shadow coordinate section |
| 2026-10-13 | Cursor, uid 1000, `/tmp/safe-harbor-t2-shadow-coord-20261013T005048Z` | shadow metadata fix + R2b regen | 17-case scan/R2b/C3 selection | all exits **0** | Shadow coordinate section |

SKIP does not satisfy a required safety claim. No session-start health result fills a runtime or recovery row. V2's earlier correction/integration rows are historical; final owner acceptance and squash mapping are recorded above. The corrected T3 ordering-gate evidence is returned separately, with its exclusions and limitations. V3, the remainder of V4, V5 and V6 stay NOT RUN.

## Merge reading

- [Execution plan](EXECUTION-safe-harbor.md)
- [Architecture](ARCHITECTURE-safe-harbor.md)
- [Current STATUS](STATUS-safe-harbor.md)
- [Active routing](../inter-model/LATEST.md)

## TL;DR

[Arc Safe Harbor] The qualified proof remains nine passes plus focused lint. The bounded isolation inspection found no explicit production target but cannot prove zero ambient effects. Independent Kiro PASS (82%) at `e08100ff` satisfies the prerequisite for Ryan’s conditional isolated T3 grant. V3/remainder-V4 are unrun; no implementation acceptance or live authority is implied.

### T3 supervised development checkpoint — not acceptance

Cursor text-only drafts were inspected and run by Codex through the clean stdlib launcher at uid 1000. Codex also corrected bootstrap/import ordering and two missing-state distinctions; Codex is therefore a contributing author, not an independent implementation reviewer. No production command or resource was used by these runs.

Qualified failed runs (all under disposable `/tmp/safe-harbor-t3-suite-*` roots):
- `kx9j4vhe`: 14 setup errors (missing pytest temp parent), focused pylint exit 28.
- `rdgp09re`: 14 failures (initial snapshot has no persisted vector watermark), focused pylint exit 28. Capture now records unavailable evidence rather than fabricating a release watermark.
- `d79cxcse`: 14 failures (absent marker incorrectly treated as unreadable authority), focused pylint exit 0. Missing and unknown remain distinct.
- `i_fpuwvt`: 10 passed / 4 failed in 34.21 s, pytest exit 1; focused pylint exit 0 (guard, T3 test, launcher only). Remaining failures expose three incorrectly targeted tests and one expected conservative refusal with pending metadata. No success is inferred from these runs.

The current tests still lack the complete deterministic crash/fault matrix and an actual same-ID stale-vector release negative control. The earlier timing-only kill and parent-only monkeypatch are not accepted evidence. Implementation, V3/V4, final-tip review, and owner acceptance remain pending.
