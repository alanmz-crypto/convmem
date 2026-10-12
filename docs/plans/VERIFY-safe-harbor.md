# Verify Plan — Safe Harbor

> **Arc: Safe Harbor. TWO REVIEW-EVIDENCE CORRECTIONS AUTHORIZED; NOT RUN.** Draft PR #387 has green CI at `677c8a0` and Copilot static PASS (72%) with advisories. Ryan directed the isolation-cleanup and audit/writer-contention corrections before merging. Historical results below do not close those gaps. Both BugBot attempts failed on quota; V2–V6 remain NOT RUN.

```text
Planning Status
Phase:        Execute Task — two T1 test corrections authorized; evidence pending
Characters:   Implementer, Test-First Reviewer
Function:     Implementer
Lanes:        Cursor collected isolated V1; Kiro signs off later; Ryan owns gates
Authority:    Ryan: correct both before merging; execution section 8; T2–T5 not granted
```

**Reviewed subject:** `677c8a0d17618166c454b4523d6767e48cfa330a`, base `db8aebbfb9ac20afb081bd43bf42315a1524ac9b`. T1 runtime changes are at `496792fad80d9759ca26e5cbf2ad7d6cd60bc28e`; subsequent CI correction changed the test harness and derived inventory. Initial candidates remain historical. The newly authorized correction must record its own code revision, evidence and successor review; no prior PASS automatically transfers.

**PRs:** draft #387. Not merge-ready.

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
- **Negative controls:** no-op preflight, overwrite-single-incident marker, copy-over-original retry, census-only release, stale-disposition replay, approval retry that assumes a failed append rolled back, and state recheck moved outside the guard. Each must fail the corresponding independent assertion.
- **Dual-path coverage:** CLI add/upsert and indexed approval, CLI/direct approval recovery, guarded native mutation, audit, recover/reconcile/clear script and watch's recovery caller. Restic tests cover all five distinct consumers. Name any inaccessible path as a gap.

## V0 — Preconditions and external review

**Plan prerequisites satisfied:** Ryan accepted the plan and explicitly approved v2 B-E4.1 at `dca13a59a2edf649ac6a19777f572645bea8674e`, including all five consumer outcomes, with ownership unchanged. This is approval metadata, not runtime evidence.

**T1 grant satisfied:** Ryan subsequently granted the proposed T1/Cursor isolated implementation and its specified V1 evidence; execution section 8 records the boundary. T2–T5 have no grant.

Isolated V1 ran. Production CLI, MCP, session indexing, Restic, providers, services and external drives were not invoked.

| Field | Value |
|---|---|
| `gate_applicability` | `required` |
| `reason` | T1 changes quarantine persistence, admission control flow, and lock ordering |
| `subject_tip_sha` | prior reviewed candidate `677c8a0d17618166c454b4523d6767e48cfa330a`; successor correction pending |
| `bugbot_reviewed_sha` | `n/a` |
| `result` | not satisfied — authorized attempts at `0bcf50e` and `677c8a0` both hit quota and reviewed no SHA |
| `finding_disposition` | BugBot: none (no review); Copilot: two test advisories directed to correction by Ryan |
| `authority_reference` | execution section 8; Ryan granted the two-test correction, not a BugBot outage acceptance |

An applicable SHA mismatch remains FAIL. This row does not make the branch merge-ready.

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
| Audit holds the native lock across publication while a concurrent guarded write does not land | Historical run PASS; contention proof INCOMPLETE: writer readiness was not established before releasing the audit. Authorized correction pending |
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

Ryan's instruction: **"correct both before merging"**. The bounded grant and acceptance requirements are in execution section 8. Both corrections, their positive assertions and the contention negative control are **NOT RUN / NOT IMPLEMENTED** at this grant record. Preserve the historical rows; record successor evidence before closing either gap.

**Remote evidence at the prior subject:** GitHub pytest, pylint, secret scan and CodeQL passed at `677c8a0`; [pytest job](https://github.com/alanmz-crypto/convmem/actions/runs/38196201314/job/114639276462). Codex read the check state; this was not a local rerun. The second authorized [BugBot attempt](https://github.com/alanmz-crypto/convmem/pull/387#issuecomment-6117256790) failed on quota (request `ea440898-d96f-4d3e-b3c3-a7c2d1c6a0a5`), reviewed no SHA and authorizes no further retry. Scope remains T1; no other Copilot advisory is silently added to this correction grant.

## V2 — Target binding and freshness (T2)

**NOT RUN.** Target/profile/affected-path equality and coverage; prod/lab bypass behavior; changed config; all five consumer outcomes; old versus future snapshots; no future-triggered backup/fallback; unchanged exemptions. Require effect assertions through actual callers and existing numeric error mapping.

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

SKIP does not satisfy a required safety claim. No session-start health result fills a runtime or recovery row. V2–V6 stay NOT RUN.

## Merge reading

- [Execution plan](EXECUTION-safe-harbor.md)
- [Architecture](ARCHITECTURE-safe-harbor.md)
- [Current STATUS](STATUS-safe-harbor.md)
- [Active routing](../inter-model/LATEST.md)

## TL;DR

[Arc Safe Harbor] Candidate `677c8a0` has green CI and Copilot's static PASS with advisories. Ryan authorized two test-evidence corrections; successor assertions, CI and focused review are pending. BugBot reviewed no SHA. V2–V6, merge, deployment and arc closure stay ungranted.
