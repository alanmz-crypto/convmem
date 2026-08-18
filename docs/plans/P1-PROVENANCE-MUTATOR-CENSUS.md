# P1 provenance mutator census and consistency baseline

**Arc:** Trapdoor Hunt
**Who:** P1 implementation lane
**What:** The P1 census of mutators that can change the in-memory provenance
authority, plus the consistency mechanism selected for this slice.
**Why:** This is the required V4m planning baseline. It is not final universal
capture evidence and does not mark V4m PASS.

## P1 authority set

| Mutator | Authority state affected | Consistency mechanism | P1 status |
|---|---|---|---|
| `ProvenanceRegistry.mint()` / `_store_record()` | Assertion envelope, monitor-minted identity, commitment, record graph | `RLock` serializes publication; copy-on-write immutable authority snapshot | Covered by P1 baseline |
| `ProvenanceRegistry.import_replay()` | Existing assertion identity/commitment replay path | One operation pin validates the candidate against one immutable snapshot; existing rows are never overwritten | Covered by P1 baseline |
| `register_policy()` | Historical policy semantic bytes and allowlist | Copy-on-write snapshot publication; policy digest is snapshot-bound | Covered by P1 baseline |
| `register_recipe()` | Historical transformer recipe semantic bytes | Copy-on-write snapshot publication; recipe digest is snapshot-bound | Covered by P1 baseline |
| `register_schema_semantics()` | Historical schema/binding semantic bytes | Copy-on-write snapshot publication; schema semantic digest is snapshot-bound | Covered by P1 baseline |
| monitor-owned verified-channel fixture | Verified-channel inventory used by root elevation | Inventory is included in the immutable authority/policy snapshot; production inventory defaults empty | Synthetic fixture only; real Bootstrap is later scope |

## Consistency contract

1. Every P1 authority mutation publishes a new immutable snapshot. A snapshot
   contains records, policy/recipe history, schema semantics, and the verified
   channel inventory together; verification never mixes those surfaces.
2. An R8 operation pins one snapshot for its complete traversal. Publication of
   a newer snapshot does not invalidate the active operation.
3. P1 performs no implementation-controlled reclamation. An active pin cannot
   be removed; a later reclamation mechanism must either retain every pinned
   generation or detect loss and fail closed/restart without substitution.
4. Caller envelope fields are data, not authority. Root elevation requires an
   exact match to the monitor-owned inventory tuple; the empty inventory leaves
   production roots untrusted.
5. The P1 census and contract cover only this in-memory authority. They do not
   prove that every future durable writer participates in one complete-data
   capture/sealing cut.

## Outside the P1 authority set

The following current or planned surfaces are not P1 provenance mutators and
remain subject to a later phase re-census before they can be included in a
final V4m evidence claim:

- normal ingest, observe, distill, refine, and direct inter-model indexing;
- `knowledge_units.jsonl`, Chroma, export/reconstruction, and retrieval;
- CG-1/CG-2 generation and serving-authority publication;
- Shadow/R2b capture paths;
- `complete_data_restore.py`, backup workflows, and live-data replacement.

## P2 revalidation

P2 adds the following projection-bound writers to the census.  They carry the
P1 envelope and commitment but do not become authority:

| Mutator | Projection state affected | Consistency mechanism | P2 disposition |
|---|---|---|---|
| `ingest._commit_chunk_to_stores()` | Normal-ingest unit, Chroma metadata, and JSONL export | Existing source fence, production writer lease, export lock, and one unit envelope/commitment derived before the projection writes | Revalidated for P2 continuity; not final V4m evidence |
| `inter_model_index.index_inter_model_messages()` | Direct inter-model unit, Chroma metadata, and JSONL export | Existing source fence, production writer lease, export lock, and one unit envelope/commitment derived before the projection writes | Revalidated for P2 continuity; caller labels remain claims |
| `ChromaStore.add_unit()` / `update_unit()` / `update_unit_metadata()` | Chroma projection rows | Projection envelope/commitment self-consistency gate; provenance continuity cannot be removed from an existing bound row | Revalidated for P2 continuity; registry authority remains separate |
| `eval_corpus.reconstruct.build_canonical_unit()` | Canonical reconstruction/export package | Rebuild derives from the serialized envelope and commitment; malformed or absent provenance is explicitly untrusted | Revalidated for P2 continuity; no authority import |

This revalidation does not prove that the current locks capture one complete
logical authority state across every future writer.  P3 and any later CG-1,
restore, or serving writer must re-census its paths.  Final universal V4m
evidence remains `PENDING` until the final writer set and overlap controls are
known.

## P3 revalidation

P3 changes existing projection-bound writers but introduces no new
manifest-bound authority writer:

| Mutator | P3 continuity obligation | P3 disposition |
|---|---|---|
| `ingest_dedupe.evaluate_ingest_batch()` | Exact suppression is identity-preserving replay only; distinct, missing, or malformed provenance remains independently accepted. | Revalidated in P3 tests; V4m remains pending |
| `ChromaStore.add_unit()` / `update_unit()` / `update_unit_metadata()` | A physical projection slot may not replace a bound assertion with a distinct or missing identity; exact identity/commitment replay remains allowed. | Revalidated in P3 tests; V4m remains pending |
| `refine.job_chroma_dedupe()` / semantic tombstone path | Automatic or approved dedupe cannot tombstone across distinct provenance identities. | Revalidated in P3 tests; V4m remains pending |
| `query.py`, `evidence.py`, `ledger.py`, and `ask.py` retrieval paths | Ranking, ledger, and projection dedupe retain distinct validated assertion identities and only collapse legacy twins or exact assertion replays. | Revalidated in P3 tests; V4m remains pending |

P3 does not add a new capture/sealing writer or claim final universal V4m
evidence.  The final writer set, universal coverage, and overlap controls remain
an arc-closure obligation.

This boundary is deliberate. P2/P3 and any future restore integration must add
or revise entries for writers they introduce or change, then revalidate the
consistency mechanism before T3 closure. The existing complete-data-v2 writer
census remains useful context but is not substituted as proof of universal
provenance capture participation.

## Disposition

**P1 census baseline: complete for the P1 in-memory authority set.**
**V4m: PENDING.** Final V4m evidence requires the final implemented
manifest-bound writer set, universal mutator coverage or one universally entered
immutable staging boundary, and the required adversarial overlap evidence before
T3 closure.
