# STATUS — Dependability and Provenance Integrity

> Current-state arc brief. This is not a changelog and grants no implementation
> or operational authority.

**State:** Architecture package drafted; review required; no implementation
authorized.

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
  │ I(output) <= meet(all inputs, transformer cap)
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
| `docs/plans/ARCHITECTURE-dependability-provenance.md` | Drafted on the planning branch; review required. |
| `docs/plans/EXECUTION-dependability-provenance.md` | Stage 1 decomposition drafted; explicitly not authorized. |
| `docs/plans/VERIFY-dependability-provenance.md` | Planning stub with predeclared properties; no evidence yet. |
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
| Stage 0 architecture package | **Draft** | Kiro PASS, targeted Copilot audit disposition, Ryan lock. |
| Stage 1 provenance substrate | Not authorized | Separate Ryan Execute grant; all Stage 1 VERIFY rows pass. |
| Stage 2 semantic dedupe | Deferred | Separate design and grant. |
| Stage 3 consumer visibility | Deferred beyond Stage 1 minimum | Consumer contract and enforcement boundary reviewed. |
| Stage 4 temporal/assembly | Deferred | Reliable metadata and separate acceptance criteria. |
| Stage 5 injected-fault campaign | Deferred | Stage 1 substrate exists and local oracles are stable. |
| Live migration/activation | Out of scope | Separate architecture and exact operational grant. |

## 5. Your role now

**Next lane: Kiro design review.** Review the planning branch at one exact HEAD.
Challenge the integrity rules, transformation completeness definition, commitment
continuity, assertion-preserving dedupe, CG-1/CG-2 separation, implementation
boundaries, and whether the defeater register is complete. Return a written
PASS/FAIL with blocking versus non-blocking findings. Do not implement runtime
code or mutate live data.

After Kiro, the Copilot audit lane performs only the targeted safety/isolation
and continuity review. Ryan adjudicates and locks architecture. Cursor does not
begin until Ryan separately grants Execute.

## 6. What remains before this is live

1. Kiro reviews the exact planning tip.
2. Copilot audits safety/isolation and provenance continuity at the same tip.
3. Codex revises planning findings if Ryan requests changes.
4. Ryan locks Stage 0 and separately authorizes or rejects Stage 1 execution.
5. Cursor re-traces current `main`, implements the bounded Stage 1 slice, and
   produces the VERIFY packet without live migration.
6. Kiro reviews implementation design/result; Copilot performs targeted final
   audit; Ryan decides merge.
7. A later plan decides whether/how legacy data migrates. Merge alone never
   authorizes migration, CG-2 activation, Shadow activation, or R2b capture.

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
| 2026-08-15 | Codex Sol-High | Drafted the Stage 0 provenance architecture package for independent review; no implementation authorized. |

**TL;DR:** The provenance architecture is drafted but not approved. Kiro reviews
the exact branch tip next; no production channel is verified and no runtime or
live-data work is authorized.
