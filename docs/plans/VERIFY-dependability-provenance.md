# VERIFY — Dependability and Provenance Integrity

```text
Status:       PLANNING STUB — ALL IMPLEMENTATION EVIDENCE PENDING
Subject:      Future Stage 1 implementation at the reviewer-recorded SHA
Architecture: ARCHITECTURE-dependability-provenance.md
Execution:    EXECUTION-dependability-provenance.md
Authority:    This file is not an Execute grant or implementation PASS
```

## Human consequence and five Ws

No provenance implementation has passed. These rows predeclare the evidence a
future implementation must produce so a model cannot redefine success after
seeing results.

| Field | Answer |
|---|---|
| Who | Cursor implements only after Ryan grants Execute; Kiro reviews design; Copilot audits safety/isolation; Ryan decides merge. |
| What | A bounded proof that provenance integrity is conservative and continuous across the transformations ConvMem controls. |
| When | After Stage 0 architecture lock, against one exact implementation SHA. |
| Why | Current ingest, dedupe, export/reconstruction, and generation boundaries can lose or misstate provenance. |
| How | Property tests, round-trip fixtures, negative controls, cold tamper tests, lifecycle traces, and independent review. |

**Planning result:** PENDING. No row below is PASS until exact command output and
artifacts are recorded for the implementation revision.

## Scope lock

| In scope | Out of scope |
|---|---|
| Policy/envelope, input binding, ingest propagation, dedupe preservation, CG-1/CG-2 continuity, retrieval visibility | Live migration, Chroma/corpus mutation, Shadow/R2b operations, CG-2 activation |
| Root/derivation/property tests and malformed/legacy behavior | Cryptographic identity, automatic elevation, factual truth, downstream action gate |
| Existing-ranking isolation | Ranking or temporal-policy changes |

## Verification design

| Element | Required oracle |
|---|---|
| Integrity calculation | Independent table/exhaustive oracle over `untrusted < agent < trusted` and transformer caps |
| Input completeness | Byte hashes over raw records, exact consumed views, complete provider payload, selection parameters, and fixed recipe |
| Commitment continuity | Canonical fixture digest compared at every durable/serving boundary |
| Dedupe lifecycle | Assertion IDs and provenance commitments before/after exact and semantic candidate handling |
| CG-1 | Manifest inspection plus cold omission/tamper negative controls |
| CG-2 | Serving result compared with request-frozen selected manifest row; no recomputation |
| Retrieval | Per-result assertion/provenance contract; no aggregate integrity |
| Isolation | Diff/file inventory and no-live-mutation evidence |

## V0 — Review and revision binding

| ID | Check | Result |
|---|---|---|
| V0a | Kiro records `git rev-parse HEAD` and PASS/FAIL with blocking findings. | PENDING |
| V0b | Copilot targeted audit reviews the same SHA. | PENDING |
| V0c | Ryan records architecture lock and separate Execute grant. | PENDING |
| V0d | Implementation VERIFY records exact implementation SHA and baseline. | PENDING |
| V0e | Every existing-code path named by the plan resolves from repository root; planned new paths are explicitly labeled planned. | PENDING |
| V0f | T1–T5 remain represented, with T3 owning provenance/compatibility and no T4/T5 runtime or cloud-policy action implied. | PENDING |
| V0g | P1, P2, and P3 each have a distinct Ryan grant, implementation branch/worktree, PR, and gate; no single grant covers multiple slices. | PENDING |

## V0A — Separate execution-slice authorization

| Slice | Required authorization record | Required branch/PR separation | Result |
|---|---|---|---|
| P1 policy/identity | Ryan Execute grant naming P1 scope | `feat/2026-08-15-provenance-policy` and its own PR | PENDING |
| P2 bindings/continuity | Ryan Execute grant naming P2 scope | `feat/2026-08-15-provenance-bindings` and its own PR | PENDING |
| P3 assertion/dedupe/retrieval | Ryan Execute grant naming P3 scope | `feat/2026-08-15-provenance-assertion-continuity` and its own PR | PENDING |

These are reserved targets only; this planning branch creates none of them.

## V1 — Root authority and policy ownership

| ID | Required check | Negative control | Result |
|---|---|---|---|
| V1a | One policy function owns root and derivation integrity. | Search proves no adapter/caller duplicate calculator. | PENDING |
| V1b | Initial production verified-channel inventory is empty. | Transcript role/path/process/source type cannot verify origin. | PENDING |
| V1c | Empty inputs cannot mint `agent` or `trusted`. | Construct every empty/missing-input form. | PENDING |
| V1d | Caller claims cannot self-upgrade. | Claim `user`, `trusted_tool`, `verified`, and `trusted` in text/metadata. | PENDING |
| V1e | Legacy/malformed/unknown-policy records become untrusted. | Remove each required envelope field and use future policy version. | PENDING |
| V1f | Producer fields accept only the closed enums and grant no direct authority. | Try unknown classes/assurances and caller-supplied `verified`; validation fails or result is unknown/untrusted. | PENDING |
| V1g | Verified producer identity is not factual truth or a preservation contract. | Use verified-producer fixture with untrusted input and lossy transform; result remains untrusted. | PENDING |

## V2 — Transformer-aware monotonicity

Normative property for every supported derivation:

```text
I(output) = meet(I(all completely bound dynamic inputs), transformer_cap)
```

| ID | Required check | Result |
|---|---|---|
| V2a | Exhaustive/property tests cover every input lattice value and transformer class. | PENDING |
| V2b | Tested lossless packaging can preserve, but never exceed, least input integrity. | PENDING |
| V2c | Every LLM summarize/distill/rewrite output is capped at `agent`. | PENDING |
| V2d | Any untrusted contributor makes output untrusted. | PENDING |
| V2e | Partial/unknown ancestry makes output untrusted. | PENDING |
| V2f | Repeated transformations are monotone and never rise. | PENDING |
| V2g | Deterministic but lossy operations do not preserve trust without an explicit tested contract. | PENDING |
| V2h | Recursive recomputation verifies every parent/ancestor, policy, recipe, and required binding before using integrity. | PENDING |
| V2i | Missing ancestor, cycle, parent/commitment mismatch, or unavailable historical policy/recipe yields `untrusted`. | PENDING |

## V3 — Exact transformation-boundary binding

| ID | Required check | Negative control | Result |
|---|---|---|---|
| V3a | Binding includes stable source locator and full raw-record hash. | Same content at different records remains distinguishable. | PENDING |
| V3b | Binding includes each exact rendered/truncated consumed view. | Change one consumed byte; commitment changes. | PENDING |
| V3c | Binding includes message order, selection, chunk, and truncation parameters. | Reorder or change budget; commitment changes. | PENDING |
| V3d | Binding includes complete provider payload and fixed recipe/config hash. | Change prompt/tool/retrieval input; payload hash changes. | PENDING |
| V3e | Requested/resolved provider/model, fallback, temperature, and transformer version are bound. | Trigger fallback; identity/commitment reflects resolved path. | PENDING |
| V3f | Secrets are excluded without excluding semantics-bearing request bytes. | Fixture scans serialized envelope for test credential and required payload bytes. | PENDING |
| V3g | `complete` means supported-boundary inputs, not universal model causality. | Documentation and schema avoid impossible claim. | PENDING |
| V3h | Acknowledged success is emitted only by the named authoritative durable-write boundary. | Provider completion, projection visibility, index upsert, client receipt, or retrieval alone cannot satisfy the acknowledgement claim. | PENDING |
| V3i | Migration semantics are explicit and permission-neutral. | N-1/dry-run/backup-before-write/atomic rollback are specified; future versions reject; no live migration is run in this arc. | PENDING |

## V4 — Representation continuity

| ID | Required check | Negative control | Result |
|---|---|---|---|
| V4a | Canonicalization is versioned and deterministic across process restarts. | Field order/Unicode/null variants have specified behavior. | PENDING |
| V4b | Unit → Chroma → export → reconstruction preserves envelope/commitment exactly. | Remove/alter flat or canonical field; degrade/fail as specified. | PENDING |
| V4c | Flat metadata cannot override canonical envelope. | Give scalar cache a more favorable tier than recomputation. | PENDING |
| V4d | Effective-integrity cache mismatch degrades to untrusted. | Tamper only the cache. | PENDING |
| V4e | Old consumers cannot silently drop provenance and return trusted. | Run old/missing-field fixture. | PENDING |
| V4f | Representation, propagation, export, and reconstruction continuity are mandatory. | Remove a required field; fail/degrade to untrusted rather than advisory PASS. | PENDING |

## V5 — Dedupe and assertion identity

| ID | Required check | Result |
|---|---|---|
| V5a | Identical cross-provenance content remains independently auditable. | PENDING |
| V5b | Low-integrity duplicate cannot lower/erase a trusted assertion. | PENDING |
| V5c | High-integrity duplicate cannot elevate/erase an untrusted assertion. | PENDING |
| V5d | Equivalence creates no aggregate trusted assertion. | PENDING |
| V5e | Semantic cross-provenance tombstone requires human adjudication and retains both audit assertions. | PENDING |
| V5f | Storage optimization cannot destroy provenance identity. | PENDING |
| V5g | Assertion IDs are content-independent random 128-bit values, monitor-minted, atomically reserved, collision-checked, and immutable. | Caller attempts to mint, rewrite, recycle, or force a colliding ID. | PENDING |
| V5h | Export → reconstruction → re-import preserves a valid ID/commitment pair as idempotent replay only. | Round-trip comparison of ID, canonical envelope, and commitment; replay adds no assertion or corroborator. | PENDING |
| V5i | Same content without a valid existing ID/commitment pair becomes a new independent assertion. | Ingest identical content twice from different roots. | PENDING |
| V5j | Parent IDs and commitments match resolved parents. | Alter/remove parent commitment or bind the wrong parent ID. | PENDING |
| V5k | Invalid identity replay cannot retain, overwrite, alias, or mutate the supplied existing ID. | Supply an existing ID with missing/malformed/mismatching commitment or divergent envelope; identity-preserving import fails. If content is retained, it receives a fresh monitor ID and untrusted provenance. | PENDING |
| V5l | A parent edge is immutable identity plus expected commitment, not content equivalence. | Replace a parent with same-content assertion under another ID; recursive verification returns untrusted. | PENDING |

## V6 — Parallel/later assurance: CG-1 immutable continuity and cold validation

V6 is required before end-to-end arc closure, but it follows the locked Stage 1
representation under a separate Execute brief. It is not allowed to redefine or
delay the Stage 1 vocabulary/policy substrate.

| ID | Required check | Negative control | Result |
|---|---|---|---|
| V6a | New-schema candidate/manifest identity includes required provenance commitment. | Compare otherwise-identical candidates with different commitments. | PENDING |
| V6b | Cold validation requires the commitment; it does not compare only present keys. | Omit the field from a new-schema row; cold open fails. | PENDING |
| V6c | Altered envelope/commitment or unknown schema fails closed. | Tamper each independently. | PENDING |
| V6d | Legacy generation is explicitly untrusted, not inferred upward. | Open legacy fixture under compatibility path. | PENDING |
| V6e | CG-1 durability PASS is never surfaced as provenance/truth PASS. | Contract/docs assertion test. | PENDING |

## V7 — Stage 1 retrieval isolation and parallel/later CG-2 serving

| ID | Required check | Negative control | Result |
|---|---|---|---|
| V7a | Stage 1 retrieval returns provenance per assertion. | Mixed-integrity result set has no aggregate trusted label. | PENDING |
| V7b | Existing ranking/source-trust scores do not feed effective integrity. | Hold evidence fixed and vary ranking/path metadata. | PENDING |
| V7c | Temporal/supersession status does not feed integrity. | Vary timestamps/superseded state with same provenance. | PENDING |
| V7d | Later CG-2 serves the same assertion/commitment selected by its request-frozen authority vector. | Mutate follower copy; compare against selected manifest. | PENDING |
| V7e | Later CG-2 does not recompute, aggregate, elevate, or discard provenance. | Search and fixture comparison. | PENDING |

## V8 — Laundering and lifecycle faults

| ID | Fault case | Expected result | Result |
|---|---|---|---|
| V8a | Untrusted external chunk → LLM summary | untrusted | PENDING |
| V8b | Trusted code/tool echoes untrusted input | untrusted | PENDING |
| V8c | Same root summarized by two models | one root lineage; no independent corroboration/elevation | PENDING |
| V8d | Derivation omits one parent | untrusted/incomplete | PENDING |
| V8e | Untrusted retrieval → conversation → recapture → distill | never rises above untrusted | PENDING |
| V8f | Prompt/content says `origin=trusted` | no metadata effect | PENDING |
| V8g | Provider omission/value/fallback fault | explicit incomplete/degraded result; no elevation | PENDING |
| V8h | Child envelope/commitment remains valid-looking while an ancestor is removed | recursive verification returns untrusted; child is not treated as a new root | PENDING |

## V9 — Regression, documentation, and no-live-mutation proof

| ID | Required evidence | Result |
|---|---|---|
| V9a | Focused provenance tests and full pytest pass at exact SHA. | PENDING |
| V9b | Formatting/static checks and `git diff --check` pass. | PENDING |
| V9c | Changed-file inventory contains only authorized implementation/docs/tests. | PENDING |
| V9d | Existing retrieval ranking behavior is unchanged. | PENDING |
| V9e | No live corpus/Chroma mutation, Shadow activation, R2b capture, or CG-2 operational action occurred. | PENDING |
| V9f | Runnable documentation distinguishes reference commands from commands requiring Ryan grant. | PENDING |
| V9g | New checks are justified by a distinct failure window, owner, or oracle. | Existing standing checks are reused; no duplicate governance ceremony is introduced. | PENDING |

## V9A — Parallel/later broad assurance tracks

Egress, backup/restore, recovery, endurance, SLO, and general operational fault
campaigns require separate plans and grants. They are neither Stage 1 substrate
checks nor substitutes for mandatory provenance representation continuity.

## V10 — Independent sign-off

| ID | Required evidence | Result |
|---|---|---|
| V10a | Kiro implementation design verdict names exact SHA. | PENDING |
| V10b | Copilot safety/isolation verdict names the same SHA. | PENDING |
| V10c | Material conflicting PASS/FAIL, if any, follows the team-charter Sol-High gate. | PENDING |
| V10d | Residual risks name consequence, owner, and disposition. | PENDING |
| V10e | Ryan decides merge; migration/activation remains a separate grant. | PENDING |

## Evidence log

```text
2026-08-15 — Planning stub created. No implementation evidence, PASS verdict,
migration authority, activation authority, or downstream enforcement claimed.
```

**TL;DR:** This is a predeclared verification contract, not evidence of a
working implementation. Every implementation row remains pending.
