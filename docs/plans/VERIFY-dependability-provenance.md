# VERIFY — Dependability and Provenance Integrity

```text
Status:       PLANNING CONTRACT — FINAL T3 EVIDENCE MERGED; ALL REPOSITORY VERIFY ROWS PENDING; RYAN_T3_CLOSE PENDING
Subject:      Future Stage 1 implementation at the reviewer-recorded SHA
Architecture: ARCHITECTURE-dependability-provenance.md
Execution:    EXECUTION-dependability-provenance.md
Authority:    This file is not an Execute grant or implementation PASS
```

## Human consequence and five Ws

No repository VERIFY row has passed. The merged P4 evidence packet tested
implementation `6ec5b6c031ae8fdedbd90ef1392232d25f0bfaf1` and records 57 PASS
candidates / 32 PENDING entries, but those recommendations do not promote any
row. These rows predeclare the evidence a future implementation must produce so
a model cannot redefine success after seeing results.

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
| V0f | T1 Trust Baseline and T2 existing-proof inventory/gap analysis are completed and accepted before any T3/provenance implementation grant; Stage 1A/1B is the T3 child slice, and T4/T5 remain parent-sequence work after T3 with no runtime or cloud-policy action implied. | PENDING |
| V0g | P1, P2, and P3 each have a distinct Ryan grant, implementation branch/worktree, PR, and gate; no single grant covers multiple slices. | PENDING |
| V0h | P0 is outside Full Fathom Five; the canonical parent hierarchy is FF1/T1 → FF2/T2 → FF3/T3 → FF4/T4 → FF5/T5, and the parent structure is frozen against automatic scope additions. | PENDING |

## V0A — Separate execution-slice authorization

| Slice | Required authorization record | Required branch/PR separation | Result |
|---|---|---|---|
| P1 policy/identity | Ryan Execute grant naming P1 scope | `impl/2026-08-17-trapdoor-t3-p1`, PR #203 | PENDING |
| P2 bindings/continuity | Ryan Execute grant naming P2 scope | `impl/2026-08-18-trapdoor-t3-p2`, PR #204 | PENDING |
| P3 assertion/dedupe/retrieval | Ryan T3 P3 Execute grant from `6be6b353740b58b9652dccc1335906fdacd4e568` | `impl/2026-08-18-trapdoor-t3-p3`, PR #205; implementation head `8aa687724cdedf22b4b602f09cbc5e053d22d046`, squash-merged at `ebe0dfc9a17a4288892dce6f10cd6744f6d27315` | PENDING |

P1, P2, and P3 have distinct grants, branches, worktrees, and PRs. P3
implementation has merged, but repository VERIFY evidence remains pending.

## V1 — Root authority and policy ownership

| ID | Required check | Negative control | Result |
|---|---|---|---|
| V1a | One policy function owns root and derivation integrity. | Search proves no adapter/caller duplicate calculator. | PENDING |
| V1b | Initial production verified-channel inventory is empty and therefore real production roots/descendants are explicitly untrusted-only. | Transcript role/path/process/source type cannot verify origin; any non-synthetic production root remains `untrusted`. | PENDING |
| V1c | Empty inputs cannot mint `agent` or `trusted`. | Construct every empty/missing-input form. | PENDING |
| V1d | Caller claims cannot self-upgrade. | Claim `user`, `trusted_tool`, `verified`, and `trusted` in text/metadata. | PENDING |
| V1e | Legacy/malformed/unknown-policy records, schema/binding identifiers resolving to different semantic specification bytes, or policy/recipe identifiers resolving to different semantic bytes, become untrusted. | Remove each required envelope field, use a future policy/schema version, replace schema/binding/policy/recipe bytes while retaining the identifier, or alter `schema_semantics_sha256`; verification fails closed. | PENDING |
| V1f | Producer fields accept only the closed enums and grant no direct authority. | Try unknown classes/assurances and caller-supplied `verified`; validation fails or result is unknown/untrusted. | PENDING |
| V1g | Verified producer identity is not factual truth or a preservation contract. | Use verified-producer fixture with untrusted input and lossy transform; result remains untrusted. | PENDING |
| V1h | A separately approved Verified Ingress Bootstrap is designed and evidenced before Stage 3 claims a non-degenerate production integrity lattice or exposes `agent`/`trusted` as operational production capabilities. | Treat a real production root as above `untrusted` without the bootstrap; the root and descendants remain `untrusted`, while synthetic fixtures remain non-production evidence. | PENDING |

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
| V2h | Recursive recomputation verifies every parent/ancestor, schema semantic specification, policy, recipe, and required binding before using integrity, with the entire operation pinned to one immutable authority generation and policy/recipe-history snapshot. | PENDING |
| V2i | Missing ancestor, cycle, parent/commitment mismatch, unavailable historical policy/recipe/schema semantics, loss or mutation of the bound snapshot, bound-state integrity failure, or loss of an actively pinned state yields `untrusted` or a restarted operation; publication of a newer generation alone does not invalidate the pinned traversal, and no favorable mixed-snapshot or substituted-state result is possible. Negative control: reclaim or compact the bound generation/snapshot during an active pin; the operation must detect loss and fail closed/restart, or the pin-retention mechanism must prevent reclamation. | PENDING |

## V3 — Exact transformation-boundary binding

| ID | Required check | Negative control | Result |
|---|---|---|---|
| V3a | Binding includes stable source locator and full raw-record hash. | Same content at different records remains distinguishable. | PENDING |
| V3b | Binding includes each exact rendered/truncated consumed view. | Change one consumed byte; commitment changes. | PENDING |
| V3c | Binding includes message order, selection, chunk, and truncation parameters. | Reorder or change budget; commitment changes. | PENDING |
| V3d | Binding includes complete provider payload and fixed recipe/config hash. | Change prompt/tool/retrieval input; payload hash changes. | PENDING |
| V3e | Requested/resolved provider/model, fallback, temperature, transformer version, and immutable transformer artifact/build identity are bound; the artifact identity is mandatory for a transformer eligible for the `trusted` cap. | Trigger fallback or substitute an artifact under the same mutable version label; identity/commitment reflects the resolved path and trusted-cap validation fails without the immutable artifact identity. | PENDING |
| V3f | Secrets are excluded without excluding semantics-bearing request bytes. | Fixture scans serialized envelope for test credential and required payload bytes. | PENDING |
| V3g | `complete` means supported-boundary inputs, not universal model causality. | Documentation and schema avoid impossible claim. | PENDING |
| V3h | Acknowledged success is emitted only by the named authoritative durable-write boundary under a declared supported persistence profile covering the filesystem, mount, storage, and database semantics relied on by that boundary. | Provider completion, projection visibility, index upsert, client receipt, or retrieval alone cannot satisfy the acknowledgement claim; an unknown/unsupported profile or unproven persistence semantics returns failure/unknown. | PENDING |
| V3i | Migration semantics are explicit and permission-neutral: every authorized migration supplies an old-to-new semantic mapping for the durable representation and old-state fixture evidence demonstrating preservation of durable meaning, including envelope, assertion ID, commitment, and parent-edge semantics; the semantic inventory covers every durable meaning-bearing category, including presence/default behavior, value/enum domains, IDs, commitments, parent edges, policy/recipe references, and extensible/unknown fields where applicable; no live migration is run in this arc. | Omit or alter one mapping, declared category, or fixture/property case, or accept an unmapped or intentionally changed meaning; the migration fails closed as rejected, quarantined, or `needs migration`. N-1/dry-run/backup-before-write/atomic rollback remain required procedural controls; future versions reject. | PENDING |

## V4 — Representation continuity

| ID | Required check | Negative control | Result |
|---|---|---|---|
| V4a | A strict validated typed-envelope acceptance profile precedes canonicalization; the envelope/binding/canonicalization contract has immutable semantic identity; canonicalization then uses one normative, versioned ConvMem profile/serializer and is deterministic across process restarts. | Duplicate keys, invalid/lone Unicode surrogates, NaN/Infinity, out-of-schema numbers, undefined representations, or same-version/different-semantic schema bytes are rejected before canonicalization; serializer golden vectors still fail after serializer-library drift, and no cross-implementation portability is assumed. | PENDING |
| V4b | Unit → Chroma → export → reconstruction preserves envelope/commitment exactly. | Remove/alter flat or canonical field; degrade/fail as specified. | PENDING |
| V4c | Flat metadata cannot override canonical envelope. | Give scalar cache a more favorable tier than recomputation. | PENDING |
| V4d | Effective-integrity cache mismatch degrades to untrusted. | Tamper only the cache. | PENDING |
| V4e | Old consumers cannot silently drop provenance and return trusted. | Run old/missing-field fixture. | PENDING |
| V4f | Representation, propagation, export, and reconstruction continuity are mandatory. | Remove a required field; fail/degrade to untrusted rather than advisory PASS. | PENDING |
| V4g | Future complete-data-v2 preflight names `provenance/` in `STATE_SPECS` and `writer_census_for_root()` as a required Tier-1 durable path, and `docs/RECOVER.md` classifies it accordingly. | Valid registry present in a complete-data-v2 scratch restore returns non-BLOCKED for the provenance path. | PENDING |
| V4h | Registry manifest validation is separate from `.convmem-backup-evidence.json` capture-evidence validation. | Valid sidecar evidence with missing/invalid registry manifest fails or quarantines; neither validator substitutes for the other. | PENDING |
| V4i | Authority recovery verifies registry directory completeness, registry/history identity and commitments, the assertion graph, and continuity before entering recovered-authority state; when projections are present, their generation/commitment agreement is checked, and JSONL/Chroma agreement is required before projection activation or serving. | A valid registry with missing or broken Chroma enters `AUTHORITY_RECOVERED_PROJECTION_PENDING` and keeps projection-backed serving blocked; a stale or mismatched projection is quarantined rather than used. | PENDING |
| V4j | Registry recovery is a distinct Ryan-gated bulk operation; missing/incomplete authority recovery leaves live authority unchanged, while valid authority with unavailable projections remains explicitly projection-pending and not serving-ready. | Item-by-item import cannot preserve caller IDs; missing registry produces observable quarantine/degraded state without blanket live downgrade; missing projection cannot activate retrieval or serving. | PENDING |
| V4k | Recovery binds authoritative registry, policy/recipe history, graph, continuity evidence, and every activated projection to one explicitly selected complete-data-v2 generation/manifest commitment; rollback publication also requires trusted continuity evidence not derived solely from the candidate generation or rollbackable authority set, binding the previous externally accepted generation/manifest commitment to the target generation/manifest commitment, reason, and fresh rollback-grant identity. | Individually valid components from different generations, a stale projection after authority change, or a valid older generation without a named Ryan rollback grant and independent continuity evidence, remain quarantined/blocked and cannot activate or publish. | PENDING |
| V4l | Crash interruption at every durable write, rename, manifest, pointer, recovery, projection-rebuild, and activation boundary follows the normative R8.2 transition/failure table and leaves either the prior complete authority generation with its valid serving fence or a complete replacement whose projections remain explicitly pending and blocked. | Inject interruption at each boundary and each recovery transition; no mixed, missing, partially selected, or stale-fallback authority/projection state may become serving-ready. | PENDING |
| V4m | Capture/sealing consistency: a provenance generation is sealed only from one consistent logical source state, with every manifest-bound authority component covered by the consistency proof. P1 must lock the complete mutator census and consistency mechanism; each later phase must revalidate the census for writers it introduces or changes; V4m reaches PASS only after the final implemented writer set has universal evidence covering every mutator class and representative overlaps, or proves every authoritative writer enters one immutable staging boundary, before T3 arc closure. | Mutate a manifest-bound authoritative source in each classified mutator class and across representative class overlaps, including writers introduced or changed by later phases; without universal staging or equivalent proof, any bypass or incoherent candidate must retry, reject, or quarantine and may not become complete authority. | PENDING |

## V5 — Dedupe and assertion identity

| ID | Required check | Result |
|---|---|---|
| V5a | Identical cross-provenance content remains independently auditable. | PENDING |
| V5b | Low-integrity duplicate cannot lower/erase a trusted assertion. | PENDING |
| V5c | High-integrity duplicate cannot elevate/erase an untrusted assertion. | PENDING |
| V5d | Equivalence creates no aggregate trusted assertion. | PENDING |
| V5e | Semantic cross-provenance tombstone requires human adjudication and retains both audit assertions. | PENDING |
| V5f | Storage optimization cannot destroy provenance identity. | PENDING |
| V5g | Assertion IDs are content-independent UUIDv4 values with 122 random payload bits, monitor-minted, atomically reserved, collision-checked, and immutable. **Negative control:** caller attempts to mint, rewrite, recycle, or force a colliding ID. | PENDING |
| V5h | Export → reconstruction → re-import preserves a valid ID/commitment pair as idempotent replay only. **Negative control:** round-trip comparison of ID, canonical envelope, and commitment; replay adds no assertion or corroborator. | PENDING |
| V5i | Same content without a valid existing ID/commitment pair becomes a new independent assertion. **Negative control:** ingest identical content twice from different roots. | PENDING |
| V5j | Parent IDs and commitments match resolved parents. **Negative control:** alter/remove parent commitment or bind the wrong parent ID. | PENDING |
| V5k | Invalid identity replay cannot retain, overwrite, alias, or mutate the supplied existing ID. **Negative control:** supply an existing ID with missing/malformed/mismatching commitment or divergent envelope; identity-preserving import fails. If content is retained, it receives a fresh monitor ID and untrusted provenance. | PENDING |
| V5l | A parent edge is immutable identity plus expected commitment, not content equivalence. **Negative control:** replace a parent with same-content assertion under another ID; recursive verification returns untrusted. | PENDING |

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
| V8i | Complete-data-v2 restore contains a valid `provenance/` registry and normally captured JSONL/Chroma recovery components | Updated restore preflight classifies the registry as required Tier-1; valid authority may become projection-pending when a rebuildable projection is absent, but projection-backed serving remains blocked | PENDING |
| V8j | Registry directory is missing or partial | `BLOCKED`/quarantine; no recovered authority publishes and live authority is unchanged. This is distinct from a valid registry with a missing projection, which remains projection-pending. | PENDING |
| V8k | Historical schema/binding semantic specification, policy, or recipe registry is stale or unavailable, or an identifier resolves to semantic bytes different from its committed digest | recursive recomputation returns `untrusted`; no caller-supplied ID elevates and no same-ID semantic replacement is accepted | PENDING |
| V8l | Registry, JSONL export, and Chroma rebuild disagree | Authority may remain recovered only as `AUTHORITY_RECOVERED_PROJECTION_PENDING`; projection activation and projection-backed serving fail closed, and no stale or prior projection generation may serve against the recovered authority | PENDING |

## V9 — Regression, documentation, and no-live-mutation proof

| ID | Required evidence | Result |
|---|---|---|
| V9a | Focused provenance tests and full pytest pass at exact SHA. | PENDING |
| V9b | Formatting/static checks and `git diff --check` pass. | PENDING |
| V9c | Changed-file inventory contains only authorized implementation/docs/tests. | PENDING |
| V9d | Existing retrieval ranking behavior is unchanged. | PENDING |
| V9e | No live corpus/Chroma mutation, Shadow activation, R2b capture, or CG-2 operational action occurred. | PENDING |
| V9f | Runnable documentation distinguishes reference commands from commands requiring Ryan grant. | PENDING |
| V9g | New checks are justified by a distinct failure window, owner, or oracle. **Negative control:** existing standing checks are reused; no duplicate governance ceremony is introduced. | PENDING |

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
