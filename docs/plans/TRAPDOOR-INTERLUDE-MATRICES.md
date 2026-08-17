# Arc Trapdoor Interlude Hunt — Claim, Evidence, and Trapdoor Bridge Matrices

```text
Status: DRAFT — FF1/T1 not accepted; FF2/T2 not started; all VERIFY rows PENDING
Arc:    Arc Trapdoor Interlude Hunt
Base:   d10e1d5f4993f60a32142115f8b8c0f0f9ea4481
```

This file is the canonical matrix artifact. It is planning evidence, not a
runtime contract and not an implementation grant.

## Part A — FF1/T1 Trust Baseline claim matrix

Severity labels are proposed for Ryan review. No numerical operational target
is implied.

| Claim ID | Property | Scope | Acknowledgement boundary | Failure consequence | Severity | Owner | Oracle | Degraded state | Notes / assumptions |
|---|---|---|---|---|---|---|---|---|---|
| T1-ACK | An acknowledged durable write survives the failure class named by its boundary. | Authoritative durable write and its recovery surface. | Named durable-write boundary only; provider/index/client success is insufficient. | Caller believes memory exists when authoritative state did not commit. | critical | Durable-write owner | Boundary-specific commit/reopen/recovery evidence; existing CG-1/write contracts are inputs. | write unknown or failed; do not report acknowledged success. | Must not be defined by `doctor PASS`. |
| T1-GEN | A published authority generation is internally complete and cannot silently mix generations. | Complete-data generation, manifest, registry, JSONL, Chroma, and selected pointer. | Publication of the selected complete generation. | Recovery or serving combines incompatible state. | critical | Generation/manifest owner | Manifest identity, component digest agreement, selected-generation restore proof. | `BLOCKED`, quarantined, or authority unavailable. | Restore-side coherence is distinct from capture-side coherence. |
| T1-CAP | A generation sealed as complete came from one consistent logical source state. | Capture/sealing cut across manifest-bound authoritative sources. | Generation sealing/publication boundary. | An impossible composite becomes authoritative despite individually valid parts. | critical | Capture/sealing owner | Consistency proof, immutable/staged source, or retry/reject/quarantine negative control. | retry, reject, or quarantine; no complete authority. | Maps to Trapdoor R8.2/V4m. |
| T1-REC | Incomplete, unverifiable, or mismatched recovery fails closed. | Restore preflight, authority store, projections, and recovery publication. | Recovered authority publication. | Corrupt or partial recovery is treated as healthy. | critical | Restore/recovery owner | Scratch restore, closed state classification, registry/JSONL/Chroma agreement. | `BLOCKED`, quarantine, or `provenance_store_unavailable`; live authority unchanged. | Validators do not repair. |
| T1-ID | Authoritative identity cannot be reconstructed merely from a projection or content equivalence. | Assertion identity and durable authority. | Identity-preserving import/replay boundary. | Projection or same-content injection aliases or overwrites an assertion. | critical | Assertion-authority owner | Identity/commitment replay and projection-loss negative controls. | fresh untrusted identity or quarantine; never caller-supplied elevation. | Existing T3 identity regime remains upstream design. |
| T1-TRANS | Transformations, exports, rebuilds, and restores cannot silently elevate provenance integrity. | Ingest, distill, inter-model, Chroma/export/reconstruction, CG-1, CG-2. | Current representation creation and publication. | Untrusted or unknown content becomes trusted through a pipeline step. | critical | Provenance-transform owner | Monotonic integrity/origin propagation and continuity checks. | `untrusted`, `unknown`, or degraded; no elevation. | Does not assert factual truth. |
| T1-SCHEMA | Unsupported future or malformed durable schemas fail conservatively. | Durable files, manifests, envelopes, and loaders. | Load/validate boundary. | New semantics are silently reinterpreted under an old reader. | critical | Schema/compatibility owner | Version/schema negative controls and explicit rejection. | reject, `unknown`, or quarantine. | No migration operation belongs here. |
| T1-MIG | Migration cannot silently reinterpret durable meaning. | Schema migration and compatibility window. | Separately authorized migration write boundary. | Data changes meaning without approval or rollback. | critical | Migration owner | Dry-run, N-1 contract, backup-before-write, atomic replacement, rollback evidence. | reject, needs migration, or preserve old state. | T3 has a planning contract; implementation remains separate. |
| T1-BACK | Backup and restore claims cover the authoritative state that matters. | Complete-data-v2 root, authority store, manifest, history, JSONL, Chroma. | Snapshot/capture and verified restore boundary. | A valid-looking backup omits the authority needed to trust recovery. | critical | Backup/recovery owner | Snapshot identity/path/tag/tree evidence plus application-level authority validation. | no trusted recovery; quarantine or degraded authority. | Restic evidence is not semantic provenance proof. |
| T1-PROVIDER | Provider or projection completion is not confused with durable acknowledgement. | LLM/provider, embedding, index, Chroma, and durable write orchestration. | Only authoritative durable boundary may acknowledge. | A transient/provider result is reported as durable memory. | high | Write orchestration owner | Failure injection or contract trace separating provider, projection, and durable result. | unknown/pending; no acknowledgement. | Provider availability is not content truth. |
| T1-DEG | Missing authoritative state is visible as degraded/untrusted, not silently healthy. | Missing registry, stale history, unknown schema, incomplete ancestry, failed restore. | Every trust/authority decision using missing evidence. | Consumers act on an unproved state. | critical | Trust-state owner | Negative controls for missing/unknown evidence and visible state/report. | `unknown`, `untrusted`, `BLOCKED`, quarantine, or named degraded state. | State names must be concrete at each boundary. |

### FF1 acceptance checklist

- Ryan accepts or revises the severity vocabulary.
- Every `critical` claim has one owner, one oracle, and one degraded state.
- No claim relies on `doctor PASS` as its oracle.
- No numerical RPO/RTO/SLO or performance target has entered the matrix.
- Ryan records FF1 acceptance at the exact commit containing this matrix.

## Part B — FF2/T2 Existing Evidence + Failure-Gap Matrix

This is the initial evidence inventory. It is not yet accepted; classifications
must be checked against exact evidence revisions during FF2.

| Claim ID | Existing evidence | Evidence revision / identity | Coverage | Failure window covered | Evidence limit | Smallest missing oracle | Expected degraded state | Owner |
|---|---|---|---|---|---|---|---|---|
| T1-ACK | Existing durable-write and generation contracts; Trapdoor acknowledgement boundary; CG-1 generation machinery. | Trapdoor `8f037a50`; main CG-1/backup plans. | PARTIAL | Named durable boundary and ordinary generation persistence are designed/tested in predecessor work. | Does not yet prove the new provenance authority or every provider-to-ack path. | Claim-specific crash/reopen evidence at the authoritative write boundary. | unknown or failed acknowledgement. | Durable-write owner |
| T1-GEN | Complete-data v2 manifest/state classification; CG-1 pointer/previous retention and CG-2 generation tests. | `docs/plans/VERIFY-complete-data-backup-correction-v2.md`; `VERIFY-cg2-production-activation.md`. | PARTIAL | Existing generation/pointer and restore-component checks. | Does not yet bind the planned provenance registry and all components to one selected authority generation. | End-to-end selected-generation oracle including future registry. | `BLOCKED`/quarantine. | Generation/manifest owner |
| T1-CAP | Tier-1 writer census explicitly passes its inventory while universal snapshot participation is not claimed. | `docs/plans/COMPLETE-DATA-V2-TIER1-WRITER-CENSUS.md`. | PARTIAL | Identifies durable/derived writers and the known coverage boundary. | Does not prove all manifest-bound mutations are quiesced or cut consistently during sealing. | Capture mutation negative control or equivalent consistency proof. | retry/reject/quarantine. | Capture/sealing owner |
| T1-REC | Complete-data restore preflight, closed `STATE_SPECS`, unknown-top-level blocking, restore drill, and CG-2 fail-closed recovery tests. | Main restore/CG-2 plans; restore drill evidence is bound to an older tip. | PARTIAL | Missing/wrong-path/unknown state and isolated restore behavior. | No authoritative provenance registry exists on main; old drill evidence is not current T3 proof. | Registry-aware scratch restore and authority publication oracle. | `BLOCKED`, quarantine, live authority unchanged. | Restore/recovery owner |
| T1-ID | Existing stable ledger IDs and CG-2 logical accounting preserve some domain identities. | `ledger_ids.py`; `VERIFY-cg2-production-activation.md`. | PARTIAL | Ledger IDs and serving logical identity in their existing domains. | Content/projection IDs are not a monitor-minted provenance assertion authority. | Identity-preserving replay and projection-alias negative controls. | fresh untrusted identity or quarantine. | Assertion-authority owner |
| T1-TRANS | Existing Shadow/CG-2/restore plans separate projection, serving, and durability claims. | `VERIFY-shadow-ledger-phase0.md`; `VERIFY-cg2-production-activation.md`. | PARTIAL | Some projection and authority separations. | No provenance envelope or monotonic transform calculation exists. | T3 transformer-aware propagation and continuity oracle. | untrusted/unknown. | Provenance-transform owner |
| T1-SCHEMA | Existing file-generation/hash/schema gates reject some unknown or malformed durable state. | `hash_schema_gate.py`; complete-data and CG-1 plans. | PARTIAL | Existing generation/schema validation. | Does not cover the planned provenance envelope/policy/recipe versions. | Future/malformed provenance-schema fixture matrix. | reject or quarantine. | Schema/compatibility owner |
| T1-MIG | T3 architecture states N-1, reject-future, dry-run, backup-before-write, atomic replacement, and rollback. | Trapdoor `8f037a50`, T3 migration section and V3i. | PARTIAL | Planning contract exists. | No implementation or evidence for provenance migration; no live migration authorized. | Contract-level matrix plus later separately granted implementation evidence. | reject/needs migration/preserve old state. | Migration owner |
| T1-BACK | Restic complete-data-v2 gate, path/tag/tree evidence, offsite copy and restore-preflight plans. | Current main backup plans; current doctor snapshot is operational evidence only. | PARTIAL | Snapshot selection, path identity, and restore evidence for current durable surfaces. | Planned provenance registry is not yet in the root and semantic authority validation is absent. | Registry-included snapshot plus application-level validator and selected-generation proof. | no trusted recovery/quarantine. | Backup/recovery owner |
| T1-PROVIDER | Existing plans distinguish provider/index/client completion from durable acknowledgement. | Trapdoor acknowledgement section and current write paths. | PARTIAL | Contract vocabulary and some boundary distinctions. | No complete cross-path oracle covers every provider failure and acknowledgement path. | Focused boundary trace/fault oracle after claim owner accepts scope. | unknown; no acknowledgement. | Write orchestration owner |
| T1-DEG | Existing restore uses `BLOCKED`, quarantine, `ADVISORY`, and unknown-state handling; T3 names `provenance_store_unavailable`. | Complete-data plans; Trapdoor `8f037a50`. | PARTIAL | Existing recovery degradation and planned T3 provenance degradation. | Not yet one accepted cross-arc vocabulary with per-claim owner/oracle. | FF1 accepted state mapping plus negative controls per boundary. | named state, never healthy default. | Trust-state owner |

### FF2 classification rules

`PARTIAL` does not mean “almost sufficient.” It means the evidence proves a
narrower claim and must not be cited for the unproved portion. The two older
restore-drill artifacts are `STALE` for current T3 proof where their subject
SHA is not current; they remain historical evidence only.

## Part C — Trapdoor Bridge

| Accepted T1 claim | T2 evidence / gap | Existing T3 requirement | Existing T3 VERIFY row | Bridge disposition |
|---|---|---|---|---|
| T1-ACK | Existing boundary is partial; focused authoritative-write oracle remains. | T3 acknowledgement boundary and migration boundary. | V3h, V3i | Preserve; T2 must name the missing boundary oracle before any T3 grant. |
| T1-GEN | Existing generation and restore proof is partial without registry binding. | Registry manifest, selected-generation recovery. | V4g–V4l | Confirms R8.1/R8.2; no redesign. |
| T1-CAP | Writer census passes inventory but does not prove universal participation. | Consistent logical source state before sealing. | V4m | Confirms V4m is a prerequisite oracle, not a guarantee from census alone. |
| T1-REC | Existing restore fails closed for known surfaces; provenance authority is absent. | Separate registry recovery, quarantine, live authority unchanged. | V4h–V4j, V8i–V8l | Preserve and explicitly mark implementation gap. |
| T1-ID | Existing ledger/logical IDs are not provenance authority. | Monitor-minted assertion identity and immutable parent commitments. | V5a–V5l | Confirms T3 identity boundary; no projection aliasing. |
| T1-TRANS | No current provenance propagation oracle. | Meet-plus-transformer-cap monotonicity and continuity. | V1–V4, V8a–V8h | T2 must classify this gap as a distinct T3 implementation prerequisite. |
| T1-SCHEMA | Existing schema gates are partial. | Versioned canonical envelope/policy/recipe and reject-future behavior. | V1e–V1f, V3i, V4a | Preserve; no migration operation. |
| T1-MIG | T3 migration contract is designed but unimplemented. | N-1/dry-run/backup/atomic rollback contract. | V3i | Treat as planning dependency only, not implementation authorization. |
| T1-BACK | Current backup evidence covers existing authority surfaces, not future registry. | Registry inside complete-data-v2 and application-level validator. | V4g–V4j, V8i–V8l | Confirm backup evidence cannot substitute for provenance validation. |
| T1-PROVIDER | Provider-vs-ack distinction is contractual but not fully evidenced. | Authoritative durable boundary only may acknowledge. | V3h, V8g | Preserve and require distinct oracle if FF2 confirms gap. |
| T1-DEG | Existing fail-closed states are partial across boundaries. | Untrusted/unknown/quarantine/degraded provenance semantics. | V1b–V1f, V8h–V8l | Map concrete states; do not collapse to generic error. |

### Bridge completion rule

The bridge is complete only when Ryan accepts FF1 and FF2, every mapped T3 row
has an upstream claim and evidence/gap disposition, and no row implies runtime
authorization. Any T3 contradiction is a bounded review finding, not an
automatic architecture rewrite.

**TL;DR:** The matrices define the trust contract, audit current proof, and
connect accepted prerequisites to existing Trapdoor T3 rows without granting
implementation.
