# STATUS — Dependability and Provenance Integrity

> Current-state arc brief. This is not a changelog and grants no implementation
> or operational authority.

**State:** T3 is governance-locked at
`aae0cad0bb05b0e436e213b28abbe0ff05ba2e91`; Ryan granted P1 Execute at
`83f63eb82a18fae38dfe0920146e9e427d39aabb`. The bounded P1 BLOCK-correction
lane is active on `impl/2026-08-17-trapdoor-t3-p1` in
`/tmp/convmem-trapdoor-t3-p1` for draft PR #203. All repository VERIFY rows
remain PENDING; Kiro's read-only implementation re-review is the next gate.

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
| `docs/plans/EXECUTION-dependability-provenance.md` | P1 Execute bookkeeping reconciled to grant `83f63eb82a18fae38dfe0920146e9e427d39aabb`, branch, worktree, and PR #203. |
| `docs/plans/VERIFY-dependability-provenance.md` | Planning stub with predeclared properties; no evidence yet. |
| `provenance.py` + `tests/test_provenance.py` | P1 in-memory policy/envelope/identity/verification substrate and focused tests on the correction branch; not yet merged. |
| `docs/plans/P1-PROVENANCE-MUTATOR-CENSUS.md` | P1 V4m mutator census and consistency-contract baseline; V4m remains PENDING. |
| `CONVMEM_DATA_ROOT/provenance/` | Future durable registry; restore-preflight classification and validator integration remain outside P1 implementation. |
| Normal ingest/distillation | Runtime exists on `main`; rendered/truncated input and provenance are not completely bound. |
| Direct inter-model indexing | Runtime exists; origin fields are caller claims and exported units lose `source_type`. |
| Exact/semantic dedupe | Runtime exists; content/canonical choice can erase an independent assertion. |
| Chroma/export/reconstruction | Runtime exists; no canonical provenance envelope/commitment continuity. |
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
| Stage 1A policy/representation substrate (T3 child slice) | **P1 Execute active; bounded BLOCK correction** | Correct implementation, focused/full validation, Kiro PASS, then Ryan merge/next-gate decision. |
| Stage 1B assertion/exact-dedupe continuity (T3 child slice) | Not authorized | T1/T2 architecture and evidence outputs complete and accepted, then separate Ryan Execute grant; independent assertions survive cross-tier equivalence and retrieval. |
| P1/P2/P3 execution slices | P1 granted and active; P2/P3 not authorized | Separate grants, branches/worktrees, PRs, and review gates; no singular Stage 1 grant. |
| Stage 2 semantic dedupe | Deferred | Separate design and grant. |
| Stage 3 consumer visibility | Deferred beyond Stage 1 minimum | Consumer contract and enforcement boundary reviewed. |
| CG-1/CG-2 assurance integration | Parallel/later | Separate Execute brief after canonical Stage 1 representation is locked. |
| Egress/recovery/operational assurance | Parallel/later | Separate dependability tracks and acceptance criteria. |
| Stage 4 temporal/assembly | Deferred | Reliable metadata and separate acceptance criteria. |
| Stage 5 injected-fault campaign | Deferred | Stage 1 substrate exists and local oracles are stable. |
| Live migration/activation | Out of scope | Separate architecture and exact operational grant. |

## 5. Your role now

**Next lane: Kiro exact-revision implementation re-review.** Confirm the pushed
P1 correction SHA, differential/full-suite result, BLOCK correction, V4m census,
and bounded-finding dispositions. Copilot is not called until Kiro returns PASS;
Ryan then decides the P1 implementation/merge gate. No P2/P3, migration,
Bootstrap, live-data, Chroma, CG-2, Shadow, R2b, or T4/T5 work is authorized.

## 6. What remains before this is live

1. Cursor pushes the bounded P1 correction and reports its exact SHA and tests.
2. Kiro performs the required read-only implementation re-review at that SHA.
3. If Kiro PASSes, Copilot performs the targeted safety/isolation audit; Ryan
   decides the P1 merge/close gate.
4. P2/P3, migration, Bootstrap, CG-2, Shadow, R2b, and T4/T5 require separate
   authorization and are not implied by this lane.

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
| 2026-08-18 | Codex | Ryan P1 Execute active on PR #203; bounded BLOCK correction, V4m baseline, restore boundary, and branch/grant bookkeeping are in progress; VERIFY remains PENDING. |

**TL;DR:** P1 Execute is active only on the named correction branch/PR; the
monitor-controlled authority and bounded verification corrections are being
validated, with V4m and all VERIFY rows still PENDING. Kiro re-review is next;
P2/P3 and live/Bootstrap/T4/T5 work remain unauthorized.
