# Verify Plan — Safe Harbor

> **Arc: Safe Harbor. T1 MERGED; FINAL-TIP EVIDENCE RECORDED.** Candidate `0c7b4e263dff12f8e1a6b2d485616153ed096b66` passed CI and Copilot's integration delta review (82%, static). Ryan accepted that review as the BugBot outage exception for that exact candidate, then squash-merged PR #387 as `05aa2c8`. BugBot reviewed no SHA. V2–V6 remain NOT RUN; no live grant is implied.

```text
Planning Status
Phase:        T1 delivery complete; T2 granted, V2 NOT RUN
Characters:   Implementer, Test-First Reviewer
Function:     T1 evidence and acceptance record
Lanes:        Cursor implemented; Copilot audited; Ryan accepted exception and merged
Authority:    T1 completed; T2 isolated implementation/evidence granted in execution section 9
```

**Historical reviewed subject:** `677c8a0d17618166c454b4523d6767e48cfa330a`, base `db8aebbfb9ac20afb081bd43bf42315a1524ac9b`. T1 runtime changes are at `496792fad80d9759ca26e5cbf2ad7d6cd60bc28e`; subsequent CI correction changed the test harness and derived inventory. Initial candidates remain historical. **Successor correction code:** `8b410445ac55f3a5dafede030a40f26c318ae784` (tests only; parent chain `0347328` → `95486a6` → `8b41044`). Copilot's delta review PASSed the corrections at `2977c4531cf446974b0c86994dbca757715dca76` (85%, static). **Integration:** merge commit `c624e2f39a2f76a18eacca76d9affb7f7dff6f50`, parents `5d0209033c50adb48d7d39f107aa84504514f29e` (branch) and main `5550def70c72bc7a60f0c5216b46cd4cf629f5d2`. Its final candidate `0c7b4e2` received fresh CI and the integration review recorded below; the earlier PASS was not automatically transferred.

**PR:** [#387](https://github.com/alanmz-crypto/convmem/pull/387), squash-merged by Ryan at `05aa2c86e2d01c9a9f5259b1f505833d7f28563d` on 2026-10-12 05:13:16 UTC. The squash and final candidate have identical trees.

**Direction:** [ARCHITECTURE-safe-harbor.md](ARCHITECTURE-safe-harbor.md), approved at `5ea16a6`.

**Plan:** [EXECUTION-safe-harbor.md](EXECUTION-safe-harbor.md).

**Goal:** demonstrate the approved guard/recovery behavior without extending coverage or claiming unperformed recovery.

## Human consequence

T1's incident retention and admission changes are landed source. Evidence preservation, validated owner release and unavailable/tombstoned approval-recovery handling remain later planned tasks. Rollout, actual recovery qualification and arc closure remain separate.

Who: Cursor supplied isolated T1 evidence; GitHub supplied final-tip CI; Copilot supplied independent static reviews; Ryan accepted the outage exception and merged. Codex records the results here, preserving the distinction between evidence for T1 and unrun later tasks.

## Scope lock

In scope: execution T1–T5 and their named production entrypoints under isolated fixture configuration. Out of scope: live corpus, service activation, new backup repositories, drive writes, live restore, T4/V4k, v3 activation, global freeze or broad permission changes.

## Verification design

- **Independent oracle:** fixture logical rows/documents/vectors/tombstones and export bytes; separate event reduction; durable marker/evidence file hashes; fresh-process admission results. Source identity and file existence alone do not prove behavior.
- **Failure injection:** barriers around native admission/recheck, every preservation/replacement and release publication edge; process termination/restart; short write, ENOSPC and fsync failures. Hardware power-loss durability is not implied by process-kill trials.
- **Negative controls:** no-op preflight, overwrite-single-incident marker, copy-over-original retry, census-only release, stale-disposition replay, approval retry that assumes a failed append rolled back, and state recheck moved outside the guard. Each must fail the corresponding independent assertion.
- **Dual-path coverage:** CLI add/upsert and indexed approval, CLI/direct approval recovery, guarded native mutation, audit, recover/reconcile/clear script and watch's recovery caller. Restic tests cover all five distinct consumers. Name any inaccessible path as a gap.

## V0 — Preconditions and external review

**Plan prerequisites satisfied:** Ryan accepted the plan and explicitly approved v2 B-E4.1 at `dca13a59a2edf649ac6a19777f572645bea8674e`, including all five consumer outcomes, with ownership unchanged. This is approval metadata, not runtime evidence.

**T1 grant satisfied:** the completed T1/Cursor scope and corrections are recorded in execution section 8. **T2 grant recorded:** Ryan subsequently granted isolated T2 implementation and V2 evidence; section 9 records its boundary. T3–T5 have no grant. The external-review row below describes T1 only; T2's candidate/review does not yet exist and remains required.

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

**IMPLEMENTED; final-source pytest/pylint evidence PENDING (Codex run).** Cursor implemented T2 under execution section 9 on `fix/2026-10-12-safe-harbor-t2`. External review and Ryan acceptance are not started; T1's tip-specific outage acceptance does not transfer.

**Required evidence:** Target/profile/affected-path equality and coverage; prod/lab bypass behavior; changed config; all five consumer outcomes; old versus future snapshots; no future-triggered backup/fallback; unchanged exemptions. Require effect assertions through actual callers and existing numeric error mapping.

### Source identity

| Role | SHA | Content |
|---|---|---|
| Start | `9664878b4b4a64e86b98bbf25e041aa5393fea96` | T2 grant docs |
| Implementation | `77a590bed4a24ab5e84eec3e943c95e8179d3111` | gate binding, resolver freshness, five consumers, tests |
| Lint/structure | `262573ec10adf525a0e6f0eb3a554b87b43ac452` | pylint-neutral layout of admission helpers |
| **Final source** | `44e29f6d943c98a2425c21901c310c52ca5c5b1a` | layout-only `convmem.py` change + derived R2b inventory |

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

The four uid-0 `lchown` failures are **not waived**: the uid-1000 run above passed the same restore class, but without a captured exit status. Final ordinary-user evidence must close them.

**Controls observed in those runs:** refusals (wrong profile, target B vs backup A, export symlink escape, config swap and `restic.env` edit after admission, spoofed skip, future same-day and next-day, day crossing, missing Restic) left fixture Chroma, events, approved rows and export unchanged. Success controls reached the intended mutation (old snapshot → backup → write; isolated exception). **No-op-gate negative control:** with the real preflight replaced on the same workflow, the future-snapshot write mutates and the unchanged-state assertion fails as intended.

### Final evidence at `44e29f6` — PENDING

Codex runs the uid-1000 isolated pytest selections and the pylint gate against `44e29f6`, capturing each command's own return code. Results will be recorded here; until then V2 has **no final-source pytest status**. Because `44e29f6` is AST-equal to `262573e`, the observations above remain semantically attributable, but they do not substitute for a captured status.

### Unrun / residual

- **T4 proof outstanding:** direct Python callers of `propose_decision.recover_approval()` / `approve_and_ingest()` are not gated (chain: helper → `ingest_approved_ledger` → `open_production_write_store`). Unknown/absent/tombstone classification, serialized recheck, completion uncertainty, export completion and retry stay with T4. The event-only recovery success path was exercised only to admission (T4 classifier then returned "needs human review" with state unchanged); no faithful event-only completion success was produced.
- Canary consumers (`incremental_jsonl_canary*`) inherit the future-time refusal; not separately exercised.
- Production rollout requires an explicit v2 profile and data root in `restic.env`; none was inspected or changed.
- No production CLI/MCP/doctor, corpus, config, key, backup repository, provider, service or drive was touched. Snapshot eligibility is not demonstrated recoverability.

## V3 — Preservation and bounded restore (T3)

**NOT RUN.** Original bytes write-once; preservation complete before replacement; pinned source generations; all interruption/IO failure windows; restore aborts initiating mutation even after clean census; only incident-bound existing repair may cross quarantine; persistent census failure remains contained.

## V4 — Release and stale-vector proof (T3)

**NOT RUN.** Complete current incident set and Ryan disposition binding; added-finding invalidation; durable disposition before marker removal; truncated event tail and uncertain unlink/fsync behavior; strict source-watermark oracle. Before the remainder of T3 implementation, record the pinned-backend monotonicity/queue-purge/restart demonstration, including a valid releasable control and a same-ID changed-vector fixture demonstrating the census blind spot and refusal. Failure stops T3; it is not census-only PASS. Release-publication assertions must include file fsync, parent-directory fsync on creation and required newly created directory entries; inject directory-fsync failure and require containment to remain before marker removal. Process restart is not power-loss proof.

## V5 — Approval recovery (T4)

**NOT RUN.** Cold/warm caches; unknown/absent/tombstoned/conflicting/matching states; direct and CLI callers; actual lease/governed/native/export order; forced forget/refine competition; target substitution; partial Chroma/export/event completion and retry. Cover failure before completion append, partial record, complete record with failed fsync, and durable record followed by interrupted return. An unsuccessful invocation may leave APPROVED; assert truthful uncertain-outcome reporting, authoritative reread/reduction before retry, durability establishment before success, no duplicate approval/blind re-upsert, no hidden export loss and no automatic malformed-tail deletion. Readable bytes alone do not prove durability. All cases remain unrun.

Explicitly cover new-log creation versus append to an existing durable log: file fsync in both, parent-directory fsync for creation, and durable publication of any newly created directory entries. Inject each required directory-fsync failure; require uncertain-outcome reporting and authoritative retry without duplicate approval, not a false APPROVAL_STARTED assertion. These are scheduled assertions, not executed evidence.

## V6 — Integrated handoff and independent sign-off (T5)

**NOT RUN.** All required cases and negative controls accounted for at the implementation tip; policy docs synchronized; no production/drive/provider access; truthful scope/operational prerequisites; written independent verdict with residuals and Ryan gate. Reviewers perform no cleanup or corrective live operations.

## Evidence log

| When | Runner | Subject | Command / case | Result | Pointer |
|---|---|---|---|---|---|
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
| pending | Codex, uid 1000 | final source `44e29f6` | isolated pytest selections + pylint gate with captured return codes | PENDING | V2 final evidence |

SKIP does not satisfy a required safety claim. No session-start health result fills a runtime or recovery row. V2 final-source status is pending; V3–V6 stay NOT RUN.

## Merge reading

- [Execution plan](EXECUTION-safe-harbor.md)
- [Architecture](ARCHITECTURE-safe-harbor.md)
- [Current STATUS](STATUS-safe-harbor.md)
- [Active routing](../inter-model/LATEST.md)

## TL;DR

[Arc Safe Harbor] T1 evidence, exact-tip outage acceptance and merge remain recorded. T2 is implemented at final source `44e29f6` (AST-equal to `262573e`; shadow inventory byte-identical to grant). Prior isolated runs show passing counts but no captured pytest exit; final uid-1000 pytest/pylint status is pending Codex's run. T4 direct-caller proof, external review, V3–V6 and live operations remain open.
