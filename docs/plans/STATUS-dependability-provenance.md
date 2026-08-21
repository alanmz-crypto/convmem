# STATUS — Dependability and Provenance Integrity

> Current-state arc brief. This is not a changelog and grants no implementation
> or operational authority.

**State:** **T3 CLOSED — `RYAN_T3_CLOSE — PASS`; LATER-GATE ROWS DEFERRED**.
P1, P2, and P3 are complete/merged; the locked T3 technical
basis remains `aae0cad0bb05b0e436e213b28abbe0ff05ba2e91`. P4 evidence was
accepted and squash-merged at `37c6aabde0dd8f1b7cc190d36a8a19d7a07b8c34`, and
the residual evidence record was accepted and squash-merged at
`66926ac2e68f045e9f36fd26157a3d2ca07b9608`.

The final V4m correction was implemented on [PR #211](https://github.com/alanmz-crypto/convmem/pull/211)
at exact candidate `6dc50d9ec56e016a32c7eddf3d66636b41923ed8` and
squash-merged at `6b9f6d7544710e81f67ae9d6a15e5a8982a7ce6c`. Prepared governance
closeout basis: `50052e6a3cb3f48ec53a0ebcfb4132a76da94b28`; this successor
records the final Ryan-close bookkeeping. Against that same
candidate, V4m, V9a, and V9d were accepted as PASS for T3 closure; Kiro and Copilot
both PASSed, and Sol-High was not invoked because there was no material
reviewer conflict. The hermetic full suite was baseline `1382 passed, 3
skipped, 0 failures` and candidate `1387 passed, 3 skipped, 0 failures`;
Golden Eval remained `8/10` on both; Restic and temporary-path checks passed
on both; Pylint, `py_compile`, and `git diff --check` passed.

The closed T3 package is now on an unmerged main-integration candidate in
[PR #221](https://github.com/alanmz-crypto/convmem/pull/221), created from
`origin/main` `8df2849959d01f9c41542a6388388e049f43b74c`, refreshed through
`9381efee3a80032c57dd9a9d499b2f81281a5d94`, and the frozen Trapdoor tip
`3ac2384d484bdb99d4ecd23f26c17264a7246adb`. This is integration and regression
validation only; it does not reopen T3. T3-satisfied and governance-satisfied
VERIFY rows remain `PASS`; deferred later-gate rows remain `PENDING` with
explicit deferral records. Arc Trapdoor Hunt and its later gates remain
separately governed.

## 1. What this project is for

ConvMem currently transforms conversations and inter-model documents into
durable, retrievable knowledge units, but their durable representation does not
preserve enough evidence to distinguish authenticated origin, caller claims,
mixed inputs, or LLM-created rewrites. The product goal is to make provenance
integrity conservative, continuous, and visible without conflating it with
truth, recency, ranking, serving authority, or downstream permission to act.

Success means an assertion cannot become more authoritative merely because it
was summarized, embedded, deduplicated, rebuilt, placed in an immutable
generation, served by CG-2, or retrieved by an agent.

## 2. How the planned system works

```text
source record(s)
  │ stable locator + raw hash + exact consumed-view hash
  ▼
supported transformation boundary
  │ complete provider payload + fixed recipe + producer/transformer cap
  ▼
canonical provenance envelope
  │ I(output) = meet(all completely bound inputs, transformer cap)
  │ provenance_commitment = hash(canonical authoritative envelope)
  ▼
knowledge unit ─→ Chroma ─→ export ─→ reconstruction
                              │
                              ▼
                    CG-1 immutable manifest/cold validation
                              │
                              ▼
                    CG-2 request-frozen serving authority
                              │
                              ▼
                    retrieval: provenance per assertion
```

Independent assertions remain independent even when their content is exactly or
semantically equivalent. Generative transforms cap at `agent`; incomplete
ancestry and all current unauthenticated roots are `untrusted` for security
decisions.

## 3. What exists on disk now

| Surface | Current state |
|---|---|
| `docs/plans/ARCHITECTURE-dependability-provenance.md` | Locked T3 technical basis `aae0cad0bb05b0e436e213b28abbe0ff05ba2e91`; unchanged in P1 correction lane. |
| `docs/plans/EXECUTION-dependability-provenance.md` | P1/P2/P3, P4 evidence, residual evidence, final V4m correction, and T3 close are complete/merged; later gates remain separate. |
| `docs/plans/VERIFY-dependability-provenance.md` | T3 closure record: satisfied rows are `PASS`; deferred later-gate rows intentionally remain `PENDING`. |
| `docs/plans/P4-VERIFY-EVIDENCE.md` | Merged P4 deterministic evidence packet for implementation `6ec5b6c031ae8fdedbd90ef1392232d25f0bfaf1`; 57 PASS candidates and 32 PENDING entries are recorded without VERIFY promotion. |
| `docs/plans/T3-RESIDUAL-CLOSURE-EVIDENCE.md` | Historical merged PR #209 residual packet; its original V4m/V9a/V9d limitation is superseded by the final exact-SHA evidence recorded below, without rewriting the historical packet. |
| `PR #211 final V4m evidence` | Exact candidate `6dc50d9ec56e016a32c7eddf3d66636b41923ed8`, merged at `6b9f6d7544710e81f67ae9d6a15e5a8982a7ce6c`; V4m/V9a/V9d are accepted PASS rows for closed T3. |
| `PR #213 post-close hardening` | Runtime writer-attestation enforcement candidate `f069c780a257d2e68075c06806b0913b35aeac2d`, merged at `013f692442029a0d64326b3504e6216f320ff595`; T3 remains CLOSED and deferred rows remain PENDING. |
| `provenance.py` + `tests/test_provenance.py` | P1 in-memory policy/envelope/identity/verification substrate and focused tests; merged through PR #203. |
| `docs/plans/P1-PROVENANCE-MUTATOR-CENSUS.md` | P1 mutator census and consistency-contract baseline; final V4m universal evidence is accepted in PR #211. |
| `CONVMEM_DATA_ROOT/provenance/` | Future durable registry; restore-preflight classification and validator integration remain outside P1 implementation. |
| Normal ingest/distillation | P2 binds rendered/truncated input, provider payload, and conservative provenance metadata; full authority/production trust remains unavailable. |
| Direct inter-model indexing | P2 preserves `source_type` as claimed classification and carries provenance through export; caller claims do not elevate authority. |
| Exact/semantic dedupe | P3 preserves independently provenance-bearing assertions; content equivalence cannot erase, merge, or alter their authority. |
| Chroma/export/reconstruction | P2/P3 carry self-consistent envelope/commitment pairs through projections and reconstruction; disagreement remains degraded/untrusted and authority stays in the registry. |
| CG-1 | Immutable generation and cold-validation machinery exists; provenance commitment is not a required immutable field. |
| CG-2 | Serving-authority implementation is on `main`; it does not yet carry the planned commitment contract. |
| Authenticated origin channel | **None identified.** |
| Provenance policy module | Missing. |
| Production provenance migration | Not designed or authorized. |

The architecture is grounded in `ingest.py`, `distill.py`, `llm.py`, adapters,
`inter_model_index.py`, `ingest_dedupe.py`, `refine.py`,
`eval_corpus/reconstruct.py`, CG-1 generation contract/builder/store, and CG-2
serving authority/repository.

## 4. Completion state

| Milestone | State | Exit condition |
|---|---|---|
| P0 CI Merge Gate | Prerequisite; outside Full Fathom Five | Full tests, Pylint, and CodeQL are required before ordinary merges. |
| Full Fathom Five parent structure | **Frozen for review**; FF1/T1 → FF2/T2 → FF3/T3 → FF4/T4 → FF5/T5 | Each arc has one contract, owner, oracle, exit state, and explicit non-goals; further findings remain bounded review findings. |
| Trust Arc T1–T5 planning sequence | Retained; T1/T2 are mandatory completed predecessors to any T3 grant; Stage 1A/1B is the T3 child slice | T1 architecture output and T2 evidence/gap output must be complete and accepted before T3 implementation; T4/T5 follow T3 in the parent sequence; no runtime/activation/cloud-policy change follows from this package. |
| Stage 0 architecture package | **Locked** at `aae0cad0bb05b0e436e213b28abbe0ff05ba2e91` | No further architecture edits in P1 correction lane. |
| Stage 1A policy/representation substrate (T3 child slice) | **P1 complete/merged** | P1 implementation, focused/full validation, Kiro PASS, Copilot PASS, and PR #203 merge complete; T3 closure accepted. |
| Stage 1B assertion/exact-dedupe continuity (T3 child slice) | **P3 complete/merged** | P3 implementation, focused/full validation, Kiro PASS, Copilot PASS, and PR #205 merge complete; T3 closure accepted. |
| P1/P2/P3 execution slices | **P1/P2/P3 complete/merged** | P3 implementation and review/merge gates are complete; P4 evidence is complete/merged. |
| T3 P4 verification/evidence | **Complete/merged** | PR #207 merged at `37c6aab…`; 57 PASS candidates and 32 PENDING entries were recorded without promoting VERIFY rows. |
| T3 residual closure evidence | **Complete/merged** | PR #209 merged at `66926ac…`; V3f/V3h/V8c/V8e/V8g received PASS-candidate evidence, with the original limitations retained in that historical packet. |
| T3 final closure evidence | **Complete/merged; T3 CLOSED** | PR #211 merged at `6b9f6d7…`; `RYAN_T3_CLOSE — PASS` recorded; satisfied rows are PASS and later-gate rows remain explicitly deferred/PENDING. |
| Stage 2 semantic dedupe | Deferred | Separate design and grant. |
| Stage 3 consumer visibility | Deferred beyond Stage 1 minimum | Consumer contract and enforcement boundary reviewed. |
| CG-1/CG-2 assurance integration | Parallel/later | Separate Execute brief after canonical Stage 1 representation is locked. |
| Egress/recovery/operational assurance | Parallel/later | Separate dependability tracks and acceptance criteria. |
| Stage 4 temporal/assembly | Deferred | Reliable metadata and separate acceptance criteria. |
| Stage 5 injected-fault campaign | Deferred | Stage 1 substrate exists and local oracles are stable. |
| Live migration/activation | Out of scope | Separate architecture and exact operational grant. |

## 5. Your role now

**Current lane: closed T3 main-integration review; later stages remain separately
gated.** The
P1/P2/P3 implementation slices, P4 evidence, residual evidence, and final V4m
correction are complete/merged. PR #211's exact implementation candidate
`6dc50d9ec56e016a32c7eddf3d66636b41923ed8` is merged at
`6b9f6d7544710e81f67ae9d6a15e5a8982a7ce6c`; Kiro and Copilot both PASSed on
that candidate. V3f, V3h, V4m, V8c, V8e, V8g, V9a, and V9d are accepted as
PASS. Ryan recorded `RYAN_T3_CLOSE — PASS`; satisfied rows are now PASS and
deferred rows remain PENDING with explicit later-gate owners. A post-T3 bounded
hardening correction then added runtime writer-attestation enforcement in PR #213,
merged at `013f692442029a0d64326b3504e6216f320ff595`; this did not reopen T3 or
change any formal VERIFY disposition.
The integration candidate composes this frozen result with current-main Runway
Ledger and CI/protocol changes without altering either architecture. The final
dispositions for every remaining row are in §6a; no new implementation or
evidence lane is authorized. Migration, Bootstrap,
live-data/Chroma mutation, CG-1/CG-2, Shadow, R2b, and T4/T5 remain
unauthorized.

## 6. What remains before this is live

1. P1 is merged at PR #203 merge commit `836e83960e834327868fedef0368366622869db7`.
2. P2 is complete/merged at implementation head
   `182f122614311df649ab0614ae6d26e9108646eb`, PR #204 merge commit
   `017d1247685c858ad96bb47cc61582234d9ae1aa`; Kiro and Copilot both passed.
3. P3 is complete/merged at implementation head
   `8aa687724cdedf22b4b602f09cbc5e053d22d046`, PR #205 merge commit
   `ebe0dfc9a17a4288892dce6f10cd6744f6d27315`; Kiro and Copilot both passed.
4. P4 — the Stage 1 verification packet and compatibility closure — is complete
   and merged at PR #207 merge commit `37c6aabde0dd8f1b7cc190d36a8a19d7a07b8c34`.
   The tested implementation is `6ec5b6c031ae8fdedbd90ef1392232d25f0bfaf1`,
   the evidence candidate is `b7b5fe0b82285fd522cb9e6e3ed54722ac29007f`, and
   the packet records 57 PASS candidates / 32 PENDING entries. Its historical
   pending states were reconciled by the final T3 close; later-gate rows remain
   explicitly deferred.
5. Residual closure evidence is merged at PR #209 commit
   `66926ac2e68f045e9f36fd26157a3d2ca07b9608`; its historical packet records
   V3f/V3h/V8c/V8e/V8g as PASS candidates and preserves the then-current
   V4m/V9a/V9d limitation.
6. The final exact-SHA V4m correction is merged through PR #211 at
   `6b9f6d7544710e81f67ae9d6a15e5a8982a7ce6c`, with implementation candidate
   `6dc50d9ec56e016a32c7eddf3d66636b41923ed8`. V4m, V9a, and V9d now have
   PASS evidence on that same candidate; Kiro and Copilot PASSed.
7. Ryan recorded `RYAN_T3_CLOSE — PASS`; T3 is CLOSED. Deferred rows remain
   live `PENDING` requirements under their separately authorized later gates.
   No subsequent implementation phase is authorized by this record.
8. Post-T3 bounded hardening correction PR #213 is merged at
   `013f692442029a0d64326b3504e6216f320ff595` from candidate
   `f069c780a257d2e68075c06806b0913b35aeac2d`; Kiro and Copilot both PASSed.
   The correction strengthens runtime enforcement of the existing V4m boundary;
   it does not reopen T3 or authorize any deferred gate.

## 6a. Final T3 closure dispositions

Ryan accepted this classification with `RYAN_T3_CLOSE — PASS`. The pre-close
state is retained for traceability. Satisfied rows are recorded as `PASS` in
the VERIFY contract; rows whose requirements belong to later gates remain
`PENDING` there because the schema has no formal `DEFERRED` value.

| VERIFY row | Pre-close state | Final disposition | Evidence or deferral basis | T3 closure blocker? |
|---|---|---|---|---|
| V0a | PENDING | Satisfied governance record | Kiro PASS against the final reviewed candidate `6dc50d9…` | No |
| V0b | PENDING | Satisfied governance record | Copilot PASS against the same final candidate | No |
| V0c | PENDING | Satisfied governance record | Locked T3, accepted grants, and serial phase gates are recorded | No |
| V0f | PENDING | Satisfied governance record | Accepted T1/T2 predecessor and T3 child-slice history is preserved | No |
| V0h | PENDING | Satisfied governance record | Frozen FF1–FF5 parent hierarchy is preserved | No |
| V1h | PENDING | Deferred — Verified Ingress Bootstrap | Bootstrap remains separately gated; current production remains untrusted-only | No; separate gate |
| V3f | PENDING | PASS | Final exact-SHA serialized-envelope secret scan and semantic-hash evidence | No |
| V3g | PENDING | Satisfied by locked scope | The architecture expressly makes no universal model-causality claim | No |
| V3h | PENDING | PASS | Final exact-SHA supported-profile durability/acknowledgement evidence | No |
| V3i | PENDING | Deferred — migration | Migration implementation and execution remain separately gated | No; migration gate |
| V4g | PENDING | Deferred — complete-data recovery | Future provenance restore-preflight integration remains outside T3 implementation | No; later recovery gate |
| V4h | PENDING | Deferred — complete-data recovery | Registry-versus-sidecar restore validation is a later recovery obligation | No; later recovery gate |
| V4i | PENDING | Deferred — complete-data recovery | Full authority recovery integration is outside the completed Stage 1 lane | No; later recovery gate |
| V4j | PENDING | Deferred — complete-data recovery | Ryan-gated bulk authority recovery is not part of this T3 implementation | No; later recovery gate |
| V4k | PENDING | Deferred — recovery/rollback | Selected-generation and rollback publication require the later recovery lane | No; later recovery gate |
| V4l | PENDING | Deferred — T5 fault work | Broad recovery interruption/fault-injection work remains later scope | No; T5 gate |
| V4m | PENDING | PASS | Final exact-SHA code-derived census, universal boundary, and overlap evidence | No |
| V7d | PENDING | Deferred — CG-2 | Request-frozen follower serving is a separate CG-2 gate | No; CG-2 gate |
| V7e | PENDING | Deferred — CG-2 | CG-2 non-recomputation/non-aggregation is separately authorized | No; CG-2 gate |
| V8c | PENDING | PASS | Final exact-SHA same-root corroboration/elevation negative control | No |
| V8e | PENDING | PASS | Final exact-SHA untrusted retrieval/recapture/distill chain | No |
| V8g | PENDING | PASS | Final exact-SHA provider omission/fallback negative controls | No |
| V8i | PENDING | Deferred — complete-data recovery | Full registry-plus-projection restore evidence remains later recovery scope | No; later recovery gate |
| V8j | PENDING | Deferred — complete-data recovery | Missing/partial registry recovery requires the later restore oracle | No; later recovery gate |
| V8l | PENDING | Deferred — recovery/projection lifecycle | Full authority-first recovery lifecycle remains separately gated | No; later recovery gate |
| V9a | PENDING | PASS | Final exact-SHA hermetic full suite: baseline 1382 passed/3 skipped; candidate 1387 passed/3 skipped; zero failures | No |
| V9d | PENDING | PASS | Final exact-SHA retrieval/dedupe regression suite passed; Golden Eval remained 8/10 | No |
| V10a | PENDING | Satisfied governance record | Kiro PASS is recorded for the final exact candidate | No |
| V10b | PENDING | Satisfied governance record | Copilot PASS is recorded for the final exact candidate | No |
| V10c | PENDING | Satisfied governance record | No material Kiro/Copilot conflict occurred; Sol-High gate was not triggered | No |
| V10d | PENDING | Satisfied governance record | Residual risks and their later owners/gates are recorded here and in the evidence history | No |
| V10e | PENDING | PASS — `RYAN_T3_CLOSE` | Ryan recorded the final governance gate; migration/activation remain separate | No; later gates remain separate |

**Final readiness:** no technical T3 closure blocker remains. T3 is CLOSED;
deferred later-gate obligations remain live and unauthorized.

## 7. Hard stops and residual limitations

- No production channel is currently `verified`.
- Do not infer trust from role, path, `author_model`, `source_type`, confidence,
  process attestation, R2b package integrity, Shadow events, CG-1 durability, or
  CG-2 serving authority.
- Do not alter runtime code, ranking, live configuration, Chroma/corpus data,
  Shadow, R2b, CG-2 activation, or downstream agent policy in planning.
- Do not claim factual truth, TMA-NM end-to-end non-malleability, or downstream
  action enforcement.
- Legacy records remain unknown/untrusted for security decisions unless a future
  authenticated evidence path proves otherwise.
- A commitment proves canonical evidence continuity, not truth.

## 8. Relationship to other arcs

| Arc/control | Relationship |
|---|---|
| CG-1 | Supplies durable immutable generations; must require and cold-validate the provenance commitment. Durability is not trustworthiness. |
| CG-2 | Supplies request-frozen serving authority; must pass provenance unchanged. Serving authority is not provenance integrity. |
| R2b | Authorizes and binds capture packages; does not establish semantic origin inside captured content. No live capture. |
| Shadow Ledger | Observes mutation events; cannot prove the writer assigned origin correctly. Remains disabled. |
| JudgeBench | Future deterministic temporal/provenance rubrics may use it; no blended LLM temporal judge in Stage 1. |
| Existing source trust | Retrieval-priority heuristic only; unchanged and excluded from integrity calculation. |
| Temporal validity | Separate later policy; no forced winner without reliable version metadata. |

## 9. Key files and review order

1. `docs/plans/ARCHITECTURE-dependability-provenance.md` — normative design,
   assurance claims, evidence limits, and defeaters.
2. `docs/plans/EXECUTION-dependability-provenance.md` — bounded Stage 1 work and
   stop conditions; not an Execute grant.
3. `docs/plans/VERIFY-dependability-provenance.md` — predeclared evidence rows,
   currently all pending.
4. `docs/plans/STATUS-dependability-provenance.md` — this current-state snapshot.
5. Separate CG-2 architecture package — serving-authority constraints, not owned
   or modified by this arc.

## 10. Update protocol and log

Keep this file a current-state snapshot. When a milestone changes, overwrite
Sections 3–6, preserve hard boundaries, and add one milestone-level line below.
Do not append session narrative.

| Date | Lane | Milestone change |
|---|---|---|
| 2026-08-15 | Codex Sol-High | Tightened monitor-minted identity, idempotent replay, and invalid-ID/commitment failure semantics for final lock review. |
| 2026-08-15 | Codex Sol-High | Added the restore-preflight STATE_SPECS/writer-census and separate-validator contract for the provenance registry; implementation remains unauthorized. |
| 2026-08-15 | Codex Sol-High | Retained T1–T5 and strengthened T3 provenance, acknowledgement, and migration boundaries; clean-SHA rereview required. |
| 2026-08-16 | Codex Sol-High | Added capture/sealing consistency as a mechanism-neutral condition and V4m; runtime remains unauthorized and exact-revision rechecks remain pending. |
| 2026-08-16 | Codex Sol-High | Added the P1 planning precondition to census every manifest-bound mutator; existing writer/Restic leases remain implementation context, not proof of V4m. |
| 2026-08-18 | Codex | PR #203 merged P1 at `836e83960e834327868fedef0368366622869db7`; P2 remains unauthorized and VERIFY remains PENDING. |
| 2026-08-18 | Cursor | Ryan granted P2 from closeout `809de5c6b296ea56428cf766bab4eb8912cafff3`; PR #204 is in progress for current-ingest and projection continuity, with VERIFY still PENDING. |
| 2026-08-18 | Codex | PR #204 P2 implementation `182f122614311df649ab0614ae6d26e9108646eb` merged at `017d1247685c858ad96bb47cc61582234d9ae1aa`; P3 remains unauthorized and VERIFY remains PENDING. |
| 2026-08-18 | Codex | Ryan granted P3 from closeout `6be6b353740b58b9652dccc1335906fdacd4e568`; branch/worktree created and Draft PR creation is pending before implementation. |
| 2026-08-18 | Codex | Dedicated P3 Draft [PR #205](https://github.com/alanmz-crypto/convmem/pull/205) recorded; functional work remains limited to the authorized P3 scope and VERIFY remains PENDING. |
| 2026-08-18 | Codex | PR #205 P3 implementation `8aa687724cdedf22b4b602f09cbc5e053d22d046` squash-merged at `ebe0dfc9a17a4288892dce6f10cd6744f6d27315`; P4 remains unauthorized and VERIFY remains PENDING. |
| 2026-08-18 | Codex | Ryan granted P4 from `6ec5b6c031ae8fdedbd90ef1392232d25f0bfaf1`; deterministic evidence is collected on Draft PR #207, Kiro PASSed, Copilot found stale handoff/status bookkeeping, and bounded same-tip documentation re-review is pending. |
| 2026-08-18 | Codex | PR #207 P4 evidence candidate `b7b5fe0b82285fd522cb9e6e3ed54722ac29007f` squash-merged at `37c6aabde0dd8f1b7cc190d36a8a19d7a07b8c34`; 57 PASS candidates / 32 PENDING entries recorded, all repository VERIFY rows remain PENDING, and T3 closure is not granted. |
| 2026-08-18 | Codex | PR #209 residual evidence candidate `d796be0ad6fb0c86bf46cf34519a8332252fce1e` squash-merged at `66926ac2e68f045e9f36fd26157a3d2ca07b9608`; V3f/V3h/V8c/V8e/V8g remain PASS candidates, V4m/V9a/V9d remain PENDING blockers, and all repository VERIFY rows remain PENDING. |
| 2026-08-19 | Codex | Ryan recorded `RYAN_T3_CLOSE — PASS` after PR #211 final evidence; T3 is CLOSED, satisfied rows are PASS, and later-gate rows remain explicitly deferred/PENDING. |
| 2026-08-20 | Codex | Post-T3 bounded hardening correction PR #213 merged at `013f692442029a0d64326b3504e6216f320ff595`; runtime V4m enforcement strengthened, T3 remains CLOSED, and deferred rows are unchanged. |
| 2026-08-21 | Codex | Draft PR #221 candidate `59c0775310bfc4372aaa2d4eafccf05534ea0c58`, based on main through `9381efe…` and integrating frozen closed T3 `3ac2384d…`, passed the exact-SHA hermetic full suite (1,445 passed, 3 skipped, 230 subtests), focused P1–P3/V4m/Runway tests (125 passed), V9d regression (61 passed), Golden Eval (8/10), Restic (18 passed), temporary-path control, Pylint regression gate, `py_compile`, `git diff --check`, and current CI invariant manifest; no migration, live-data/Chroma mutation, Bootstrap, CG-2 activation, Shadow/R2b activation, or T4/T5 work occurred, independent review remains required, and no main merge is authorized. |

**TL;DR:** T3 remains CLOSED; draft PR #221 is the isolated main-integration candidate, with deferred gates unchanged and merge reserved for Ryan.
