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
