# PRE-G6 V2 Bounded Implementation Plan

> **Status:** `PRE-G6 V2 IMPLEMENTATION PLAN READY FOR RYAN REVIEW`
>
> **Arc:** Naturalistic ConvMem product-value evaluation
>
> **Planning only.** This document authorizes no implementation, G6/T0 freeze,
> Ryan-value selection, naturalistic evidence access, live registry, Agent A/B,
> scoring, or product inference. Each implementation slice requires a separate
> Ryan grant and a fresh independent review before the next slice may be granted.

## 1. Authority and inspected repository basis

The semantic SSoT is the exact PRE-G6 V2 contract at commit
`9f4791c2744c02d742fdb9c0fa1e9dd150591ac1`, canonical JCS digest
`917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e`
(47,330 bytes). Reconciled explanatory planning is commit
`6e6b43feec0b9c96eb809336f29cede7b59ffc4b`. The two commits are separate Git
authorities; neither is an ancestor of the other. Implementers must use the JSON
contract when prose differs.

This plan inspected current `origin/main` code, not only planning claims:

- `eval_naturalistic/` V1 contracts, adjudication, probe, analysis, and G5 dry run;
- all currently routed adapters under `adapters/`;
- `provenance.py`, `provenance_binding.py`, `canonical_json.py`;
- `eval_corpus/capture.py`, `eval_corpus/runner.py`, and `eval_corpus/paired_stats.py`;
- `serving_index_repository.py` and Naturalistic tests.

The locked V2 artifact package is not on current `main`; the current runtime has
no `EvidenceSealManifestV2`, `OpaqueResolverManifestV2`,
`AdjudicationEvidenceViewV1`, `ImplementationManifestV2`,
`ScorerRuntimeSealV2`, `ControllerEvidencePackageV2`,
`C0C1EqualityManifestV2`, `SessionIsolationManifestV2`, or
`ConditionOrderManifestV2` implementation.

## 2. Current-code → V2 gap matrix

Classification vocabulary: **conformant**, **bounded modification**, **missing**,
**replace conflict**, and **later-stage deferred**.

| V2 obligation | Current evidence | Classification | Required disposition |
|---|---|---|---|
| Exact canonical artifact hashing and unknown-field rejection | `eval_naturalistic/digest.py`, `base.py`, `contracts.py` | **Conformant foundation** | Reuse canonical JSON/digest helpers; give V2 schemas a separate namespace and never reinterpret V1 bytes as V2. |
| I1 occurrence/physical/native/revision/lineage/snapshot identity | `EvidenceSourceV1` has only `source_id`, class, locator, times, content digest, optional version | **Replace conflict** | Introduce V2 identity types; a locator/hash cannot stand in for occurrence or physical identity. |
| I1 evidence-complete envelope and raw/canonical/profile/adapter commitments | `RawEvidenceManifestV1` binds a source list plus completeness state | **Bounded modification** | Preserve sealing mechanics; replace the V1 evidence body with V2 envelope commitments and condition-neutral availability. |
| Issue #263 source-present/verbatim-unavailable distinction | V1 completeness is `complete/partial/missing`; no orthogonal presence/verbatim/summary/result axes | **Missing** | Add independent enums and invariant; never infer absence from query/extraction failure. |
| I2 nine-dimensional capability vector and per-use reduction | No Naturalistic capability type or reduction function | **Missing** | Add typed vector, total per-use predicates, and fail-closed unknown/unsupported behavior. |
| I2 adapter/source-class evidence profiles | Existing adapters emit lossy canonical message dicts | **Replace conflict at V2 boundary** | Keep legacy ingest outputs unchanged; add separate evidence adapters/profiles that preserve raw envelope, native IDs when real, snapshot identity, omissions, and implementation digest. |
| I3 read-only opaque resolver | No resolver in `eval_naturalistic`; query/ask are retrieval paths with broader authority | **Missing** | New bounded resolver over sealed P1 packages only; no Chroma writes, searchable corpus, or independent evidence DB. |
| I4 P1/P2 firewall | V1 P1 schemas reject unknown fields, but no canonical alias normalization or V2 field deny policy | **Missing** | Central normalize-then-deny validator for canonical fields, known aliases, and unknown aliases. |
| I5 `AdjudicationEvidenceViewV1` and RoleAccess | `build_evidence_adjudication_view()` returns sources including locators; tests only exclude capture material | **Replace conflict** | New constant-shape typed view and role-gated serializer; resolver-derived fields, aliases, paths, timing, retry, failure, and order signals denied. |
| Dual blinded adjudication, disagreement, role collision | `adjudication.py` and tests implement two submissions, resolution, sealing, and author/adjudicator collision | **Bounded modification** | Reuse workflow mechanics only after the new view/access boundary and P2 post-adjudication join are enforced. |
| I6 existence/multiplicity/resolvability/evaluability/integrity axes | `EpisodeRegistryStatus` is one combined status and aggregation uses scalar `eligible_target_count` | **Replace conflict** | Add orthogonal state plus `known_count/lower_bound/upper_bound`; adapt registry/analysis views. |
| Unknown/unbounded multiplicity propagation | No bound object; missing/ambiguous states do not carry finite or null upper bounds | **Missing** | Propagate lower/upper opportunity bounds; null upper blocks dependent point estimates/T10. |
| I7 parent-complete transitive provenance | `validate_analysis_lineage()` compares one digest; V1 artifact header has one parent | **Replace conflict** | Add immutable parent DAG, complete consumed-input inventory, recursive contamination propagation, and normative-use gate. |
| Existing provenance substrate | `provenance.py` has strict canonical envelopes and recursive verification; `provenance_binding.py` preserves projection commitments | **Bounded modification** | Reuse primitives/patterns, not existing authority labels; add Naturalistic study influence classes and legacy/unknown taint policy. |
| I8 14-component implementation manifest and amendment | No Naturalistic implementation manifest | **Missing** | Add complete component inventory, behavior/environment/contract digests, replacement differential, and invalidation rules. |
| Probe/key separation and leakage checks | `probe_construction.py` has author/adjudicator separation, key partition, leakage checks, sealed bundle | **Bounded modification** | Preserve G3 behavior; bind to V2 registry parents and mechanical key proof. |
| I9 `ScorerRuntimeSealV2` and mechanical target key instantiation | V1 has `ScoringKeyV1`; no scorer binary/environment binding or substitution proof | **Missing** | Add frozen semantic template seal plus later target substitution map/digests/no-extra-fields validation. |
| I10 controller package/equality/session/order manifests | `dry_run_mechanics.py` compares tools, roots, model, budget, stopping and uses synthetic session strings | **Replace conflict** | New typed manifests covering every locked nested path, real freshness evidence, order freeze, and only the declared treatment difference. |
| I11 informative missingness | Analysis reports incomplete/ambiguous counts but does not test correlation with treatment/source/complexity/adapter/resolution | **Missing** | Add predeclared strata, integrity diagnostics, symmetry-vs-informative-missingness distinction, and fail-closed changed-comparison result. |
| Episode-first denominator, one score per episode, zero-target distinction | `analysis.py` and tests enforce these synthetic mechanics | **Conformant foundation** | Leave G1–G5 behavior intact; extend through V2 adapters rather than rewrite it. |
| Live controller, live evidence snapshots, Agent A/B and outcome scoring | Explicitly absent/unauthorized | **Later-stage deferred** | Do not implement in PRE-G6 conformance grants. |

## 3. Adapter capability mapping

Legacy `adapters.parse()` remains an ingest/search normalization API. V2 must
add an evidence-specific adapter interface rather than widening those dicts and
silently changing existing indexing semantics.

| Source class / current adapter | What current parser retains | V2 capability conclusion | Exact work |
|---|---|---|---|
| Crush SQLite (`sqlite_crush`) | session ID, role, text parts, timestamp, workspace, assistant model/provider; query orders by row `id` but discards it | Native message identity may exist but is not preserved; physical instance, revision/as-of, raw parts, omissions and completeness are absent | Preserve DB-instance identity and schema fingerprint, native message row ID/namespace, session ID, raw part envelope, capture as-of, and deletion/reuse limitations. Do not upgrade to `NATIVE_UNIQUE` until reuse/migration behavior is evidenced. |
| OpenCode SQLite (`sqlite_opencode`) | message/session IDs are read; message ID is discarded; ordered text parts, timestamp, model/provider retained | Stable native IDs are plausible but not presently authoritative; part material and source-instance binding are lost | Preserve message and part IDs, local DB instance, raw `message`/`part` JSON, ordering and schema version. Declare `DECLARED`/`UNKNOWN` dimensions until issuer guarantees are proven. |
| Cursor transcript JSONL (`jsonl_cursor`) | role/text only; timestamps forced null; tool-only turns dropped | No stable per-record identity or completeness | Mint local snapshot-scoped occurrence tokens from file instance + byte/line occurrence; capability remains `DERIVED`, not invented native identity; declare dropped tool material. |
| Codex rollout JSONL | role/text/timestamp/source type; raw event identity and tool events omitted | Snapshot-scoped occurrence identity only unless a real event ID is retained | Add byte/line occurrence, raw event envelope, event kind and explicit omission inventory; never treat content hash as identity. |
| Codex prompt history JSONL | session ID, user text, timestamp; prompt-only marker | Deliberately incomplete evidence | Preserve native session claim and line occurrence; `PARTIAL_KNOWN`; never use as full transcript authority. |
| Kiro/Copilot session JSONL | session/workspace, role/text/timestamp; tool events skipped | Session binding exists; record identity/completeness absent | Add raw line occurrence and skipped-event inventory; use derived occurrence identity unless provider record ID is present and verified. |
| Continue JSON | session/workspace and user/assistant text; timestamps absent, tool/context/prompt logs omitted | Partial-known snapshot with no stable native record ID | Snapshot-scoped occurrence identity and explicit omission commitments; fail primary use when material depends on omitted context/tools. |
| Aider Markdown | session header time and parsed user/assistant blocks; generated positions only | No universal native record ID or revision | Use file physical instance + byte-span occurrence; `DERIVED`, current/as-of capture only, partial-known if parser filters metadata. |
| Inter-model/Kiro Markdown | section/file-derived units, file timestamp, path-derived metadata; truncation for steering | File/section occurrence is locally derivable, not provider-native; steering is intentionally truncated | Bind file instance/revision digest and byte/heading span; mark truncation/material gaps; never claim full evidence envelope for truncated content. |
| Kiro/OpenWebUI/Cursor SQLite variants | heterogeneous session/content metadata, several discarded blob/row details | Unsupported for V2 until separately profiled | Fail closed with an explicit unsupported capability profile; legacy indexing may continue outside study authority. |

Every profile must state acceptance/rejection, ordering, duplicate handling,
authorship, chronology/timezone, reply structure, validity, unknown extensions,
attachments/blobs, tool/referenced material, omissions, canonicalization profile,
adapter implementation digest, and all nine capability dimensions. Unsupported
does not mean source absent.

## 4. Dependency-ordered implementation slices

Each slice is a separate grant. Expected paths are planning targets; Cursor may
propose a narrower file placement during its grant, but may not change artifact
semantics or cross slice boundaries without Ryan approval.

### V2-00 — Exact authority import and conformance harness

- **Purpose:** establish the byte-exact contract and executable conformance
  oracle on an implementation branch.
- **Parent:** locked `9f4791c…`; reconciled prose `6e6b43f…`; this approved plan.
- **Files:** exact-byte transplant of `docs/plans/artifacts/naturalistic-pre-g6-contract-v2*` and validator from `9f4791c`; new `tests/test_naturalistic_v2_contract_authority.py` only.
- **Outputs:** digest/byte-count proof, schema/conformance execution, test mapping for every locked verification-control ID.
- **Closes:** single canonical authority and test-oracle availability; no runtime behavior.
- **Tests/adversaries:** JCS trailing byte, locked digest, schema unknown field,
  all canonical conformance cases.
- **Non-goals:** no contract edits, V2 runtime classes, Ryan values, evidence.
- **STOP:** any byte/digest mismatch or any conformance case without an executable expectation.
- **Review:** exact-byte independent review.
- **Blocks:** every later slice and P0; does not itself satisfy P0/G6/T0.

### V2-01 — P1 identity and evidence seal core

- **Purpose:** implement I1 without any resolver behavior.
- **Parent:** V2-00 PASS.
- **Files:** new `eval_naturalistic/v2/identity.py`, `evidence.py`, `contracts.py`,
  `validators.py`; focused tests/fixtures.
- **Artifacts:** occurrence reference, physical instance, lineage edge,
  `EvidenceSealManifestV2`, `EvidenceAvailabilityManifestV2`, envelope commitments.
- **Closes:** clone/restore/import/native-ID reuse/revision semantics; Issue #263
  orthogonal P1 availability; raw/canonical/profile/adapter commitments.
- **Tests/adversaries:** clone/restore separation, native-ID reuse, duplicate bytes,
  provider edit vs recreate, revision mismatch, post-seal mutation/deletion,
  source-present/verbatim-unavailable.
- **Non-goals:** adapter-specific extraction, P2 resolver, adjudication.
- **STOP:** any identity inferred from hash/locator alone or any availability collapse.
- **Review:** identity/evidence-contract review.
- **Blocks:** P1, P2, P3, G6, T0.

### V2-02 — Evidence adapter profiles and capability vectors

- **Purpose:** implement I2 for a closed initially supported source list.
- **Parent:** V2-01 PASS; `D_SOURCE_001` remains unselected.
- **Files:** new `eval_naturalistic/v2/adapters/` interface/profiles; bounded
  wrappers around existing `adapters/`; no behavior change to legacy parsers.
- **Artifacts:** adapter profile, implementation identity, nine-axis capability
  vector and per-use decision.
- **Closes:** Crush/OpenCode plus JSONL/Markdown-like profile semantics; explicit unsupported profile.
- **Tests/adversaries:** unsupported adapter, malformed/truncated envelope,
  missing stable native ID, attachment loss, extension fields, schema drift,
  source-present/verbatim-unavailable.
- **Non-goals:** choosing admitted source classes or assurance policy.
- **STOP:** any universal/native ID invention, silent omission, or scalar assurance authority.
- **Review:** per-adapter capability review.
- **Blocks:** P1 completeness, P2, P3, G6/T0.

### V2-03 — P2 opaque resolver and P1/P2 firewall

- **Purpose:** implement I3 and I4 as one authority seam.
- **Parent:** V2-01 and V2-02 PASS.
- **Files:** new `eval_naturalistic/v2/resolver.py`, `firewall.py`, resolver contracts/tests.
- **Artifacts:** `OpaqueResolverManifestV2`, canonical `resolver_result`,
  `capability_vector`, input/output/implementation digests.
- **Closes:** read-only compute-once resolution and structural P1 denial.
- **Tests/adversaries:** exact/summary/no-match/evidence-unavailable/error,
  ambiguity, input mutation, resolver hash mismatch, unsupported source,
  canonical fields plus known/unknown aliases at P1.
- **Non-goals:** search index, Chroma write, shadow corpus, target census.
- **STOP:** any write path/new evidence store, nondeterministic output without bound
  inputs, or P2 field accepted on P1.
- **Review:** resolver authority/isolation review.
- **Blocks:** P2, P3, G6/T0.

### V2-04 — Blinded P3 access boundary and post-adjudication join

- **Purpose:** implement I5 and make existing adjudication mechanics consume only
  the authorized view.
- **Parent:** V2-03 PASS.
- **Files:** new `eval_naturalistic/v2/adjudication_view.py`, `role_access.py`;
  bounded integration in `eval_naturalistic/adjudication.py` or a V2 facade.
- **Artifacts:** `AdjudicationEvidenceViewV1`, `RoleAccessManifestV2`, sealed
  adjudication sets and explicit post-resolution P2 join record.
- **Closes:** constant schema/order, alias/path/retry/timing/failure/queue
  noninterference, dual submission before resolver join.
- **Tests/adversaries:** resolver result/capability leak, aliases, path/locator,
  retry/timing/queue/failure variation, stable output shape and bytes, early join.
- **Non-goals:** live adjudication or registry population.
- **STOP:** any adjudicator-visible value/shape/order/timing determined by P2.
- **Review:** independent noninterference/access-control review.
- **Blocks:** P3, later T stages, G6/T0.

### V2-05 — Orthogonal target state and multiplicity bounds

- **Purpose:** implement I6 in registry and aggregation inputs.
- **Parent:** V2-04 PASS.
- **Files:** new `eval_naturalistic/v2/target_state.py`, `registry.py`; bounded
  V2 adapters in `analysis.py`.
- **Artifacts:** `TargetRegistryV2`, `RegistryQualityReportV2`, bound records.
- **Closes:** existence, multiplicity, resolvability, evaluability, integrity;
  finite lower/upper propagation and null-upper blocking.
- **Tests/adversaries:** known target plus unknown additional targets, exact and
  finite bounds, unbounded upper, unknown-not-zero, contradictory bounds,
  target-rich episode weight.
- **Non-goals:** choosing `D_MULTIPLICITY_001` bound sources.
- **STOP:** recovered count used as total, invalid bounds accepted, or unbounded
  dependent estimand given a point estimate.
- **Review:** registry/estimand review.
- **Blocks:** P3, T3/T9/T10, G6/T0.

### V2-06 — Transitive study provenance firewall

- **Purpose:** implement I7 over every normative influence.
- **Parent:** V2-00; integration fixtures also consume V2-01/V2-05 outputs.
- **Files:** new `eval_naturalistic/v2/study_provenance.py`; reuse strict
  primitives from `provenance.py`; tests for all descendant classes.
- **Artifacts:** parent-complete influence DAG, prospective-summary provenance,
  normative-use decision and contamination reason.
- **Closes:** legacy/unknown transitive taint over summaries, embeddings, tags,
  rankings, candidate IDs, caches, expansions, metadata and derived features.
- **Tests/adversaries:** stripped legacy descendant, missing grandparent,
  incomplete consumed inputs, unrecorded hidden/external context, cycles,
  clean independent reconstruction.
- **Non-goals:** truth certification or bit-identical LLM replay.
- **STOP:** unknown lineage accepted normatively or descendant cleansed by copying/stripping.
- **Review:** independent provenance-closure review.
- **Blocks:** P0/P1/P3 and every later normative stage, G6/T0.

### V2-07 — Implementation manifest and amendment enforcement

- **Purpose:** implement I8 and bind every behavior-relevant component.
- **Parent:** V2-00; after V2-01–V2-06 review for their real identities.
- **Files:** new `eval_naturalistic/v2/implementation_manifest.py`, amendment tests.
- **Artifacts:** `ImplementationManifestV2`, amendment/differential record.
- **Closes:** 14 required components, extensions, environment/contract/content
  digests, new identity for every behavior change, dependent invalidation.
- **Tests/adversaries:** unlisted component, parser/canonicalizer replacement,
  same profile with changed code, rare/error-path differential missing,
  after-Agent-A amendment.
- **Non-goals:** declaring two builds behaviorally equivalent without the locked review path.
- **STOP:** incomplete inventory or unchanged identity after behavior-relevant change.
- **Review:** manifest completeness/amendment review.
- **Blocks:** P0 and all runtime seals, G6/T0.

### V2-08 — Scorer runtime seal and mechanical key instantiation

- **Purpose:** implement I9 while preserving G3 key partitioning.
- **Parent:** V2-05, V2-06, V2-07 PASS.
- **Files:** new `eval_naturalistic/v2/scorer_seal.py`, `key_instantiation.py`;
  bounded facade over `probe_construction.py`.
- **Artifacts:** `ScorerRuntimeSealV2`, template and substitution proof,
  `ScoringKeyManifestV2`.
- **Closes:** frozen scorer semantics vs later mechanical target material.
- **Tests/adversaries:** unlisted substitution, extra field, target-specific
  partial credit/provenance exception, scorer digest change, natural target
  exposure to scorer author.
- **Non-goals:** target-key creation from natural evidence or live scoring.
- **STOP:** semantic choice in target instantiation or scorer runtime not manifest-bound.
- **Review:** scorer/key independence review.
- **Blocks:** T4/T8, G6/T0.

### V2-09 — Controller evidence package and C0/C1 readiness manifests

- **Purpose:** implement I10 as hermetic packaging/validation only.
- **Parent:** V2-03, V2-06, V2-07 PASS.
- **Files:** new `eval_naturalistic/v2/controller_package.py`, `arm_equality.py`,
  `session_isolation.py`, `condition_order.py`; do not add a live runner.
- **Artifacts:** all four named V2 manifests and qualification report.
- **Closes:** controller-side resolve/package once, RFC8785 equality for every
  locked path, sole treatment difference, freshness/order proofs.
- **Tests/adversaries:** every required nested path missing/mismatch, retry/cache
  asymmetry, reused session, order mutation, prior trial material, controller action.
- **Non-goals:** launching sessions, mounting ConvMem, Agent B.
- **STOP:** self-reported equality, unknown path, or undeclared arm difference.
- **Review:** environment-isolation/noninterference review.
- **Blocks:** T5/T6/T7, G6/T0.

### V2-10 — Informative-missingness integrity layer

- **Purpose:** implement I11 independently of any product estimator values.
- **Parent:** V2-02, V2-03, V2-05, V2-09 PASS.
- **Files:** new `eval_naturalistic/v2/missingness.py`; bounded V2 integration in
  analysis reporting.
- **Artifacts:** missingness integrity report with predeclared grouping inputs
  and `PASS/DIAGNOSTIC_REVIEW/INTEGRITY_FAILURE` state.
- **Closes:** treatment, source class, content complexity, adapter behavior and
  resolution behavior checks; symmetry is necessary but not sufficient.
- **Tests/adversaries:** treatment-correlated, source-correlated,
  complexity-correlated and resolver-correlated missingness; sparse cells;
  comparison-changing loss.
- **Non-goals:** choosing statistical thresholds or inferring product value.
- **STOP:** missingness collapsed into zero/ordinary bounds or a changed comparison allowed.
- **Review:** independent measurement-integrity review.
- **Blocks:** T6/T9/T10, G6/T0.

### V2-11 — Full hermetic conformance integration

- **Purpose:** prove implementation conformance without naturalistic evidence.
- **Parent:** V2-01 through V2-10 PASS at exact tips.
- **Files:** `tests/test_naturalistic_v2_conformance.py`, synthetic fixture package,
  verification command/document update only if Ryan separately includes it.
- **Outputs:** traceability matrix from every locked invariant/control and I1–I11
  to code/test; exact implementation manifest; no live artifacts.
- **Tests/adversaries:** the complete list in §8 plus cross-slice generation and
  amendment invalidation.
- **Non-goals:** live snapshot, registry, Agent A/B, outcomes, G6/T0.
- **STOP:** any uncovered invariant, non-hermetic dependency, flaky side channel,
  incomplete 14-component manifest, or failing test.
- **Review:** fresh independent full-package review at one exact revision.
- **Blocks:** implementation verification; only Ryan may then reconsider G6/T0.

## 5. Dependency graph

```text
V2-00 exact authority/harness
 ├─ V2-01 P1 identity/evidence ─ V2-02 adapters/capabilities ─ V2-03 resolver/firewall
 │                                                        ├─ V2-04 blind P3 view ─ V2-05 target bounds
 │                                                        └─ V2-09 controller manifests
 ├─ V2-06 transitive provenance ───────────────────────────┤
 └─ V2-07 implementation manifest (final identities need 01–06)

V2-05 + V2-06 + V2-07 ─ V2-08 scorer/key seal
V2-02 + V2-03 + V2-05 + V2-09 ─ V2-10 missingness
V2-01 … V2-10 ─ V2-11 full hermetic conformance
V2-11 PASS + fresh review ─► Ryan may reconsider (but is not granted) G6/T0
```

## 6. Fourteen-component implementation-manifest map

| Required component ID | Planned repository implementation | Existing code reused/bound |
|---|---|---|
| `adapter` | `eval_naturalistic/v2/adapters/` | legacy `adapters/` behind evidence wrappers only |
| `parser_extractor` | adapter profile extractor implementation | current format-specific parsers where lossless enough |
| `canonicalizer` | V2 evidence canonicalization profile | `canonical_json.py`, `eval_naturalistic/digest.py` |
| `resolver` | `v2/resolver.py` | none; query/ask explicitly not authority |
| `adjudication_view_builder` | `v2/adjudication_view.py` | adjudication workflow mechanics only |
| `snapshot_packager` | P1 seal/package builder plus later controller package | `eval_corpus/capture.py` identity/copy primitives only |
| `registry_builder` | `v2/registry.py` | bounded adjudication merge/seal logic |
| `sampler` | existing V1 census/sample code after V2 parent binding | G1–G5 contracts/fixtures |
| `probe_builder` | V2 facade over `probe_construction.py` | G3 role/leakage mechanics |
| `key_instantiator` | `v2/key_instantiation.py` | V1 key partition only |
| `scorer` | `v2/scorer_seal.py` identity for future scorer runtime | analysis rubric structures; no live scorer |
| `controller` | V2 package/readiness validators | synthetic `dry_run_mechanics.py` as test precedent only |
| `replay_order` | `v2/condition_order.py` plus replay/order identity | none conformant |
| `aggregator_information_gate` | V2 facade over `analysis.py` plus bounds/missingness | episode-primary aggregation and pending-slot gate |

Every row must bind component ID, implementation version, content digest,
build/environment digest, behavioral-contract digest and bound stage. Runtime
dependencies that can change acceptance, rejection, ordering, rare paths,
attachments, errors or outputs are extension components, not invisible libraries.

## 7. Exact first recommended implementation grant

**Grant:** `V2-00 — Exact authority import and conformance harness` only.

**Authorized if Ryan grants it:** Cursor may create an implementation branch
from current `origin/main`, transplant the locked artifact package from
`9f4791c2744c02d742fdb9c0fa1e9dd150591ac1` without byte changes, and add one
hermetic test module that proves the digest, byte count, schema, validator and
all published conformance cases execute at the branch tip.

**Required outputs:**

1. exact `917ad129…` JCS digest and 47,330-byte proof;
2. unchanged contract/schema/conformance/validator package;
3. test-to-control mapping with no invented semantic expectation;
4. `pytest` PASS for the new focused tests and existing Naturalistic suite;
5. commit, push, exact-tip handoff for fresh independent review.

**Explicitly excluded:** runtime modules; V1 edits; adapter work; resolver;
manifest values; Ryan decisions; natural evidence; G6/T0; Agent A/B; scoring.

**STOP:** any need to modify canonical bytes, resolve a semantic ambiguity, or
change a conformance expectation. Such a finding returns to Ryan as an
architecture/repository gap; Cursor must not repair the contract.

This is the smallest safe first grant because every later slice needs a locally
executable, byte-exact oracle, while the import itself adds no study behavior.

## 8. Hermetic adversarial test minimum

V2-11 must include, with earlier ownership shown in parentheses:

- clone/restore identity separation and native-ID reuse (V2-01);
- source mutation/revision mismatch (V2-01);
- unsupported adapter and source-present/verbatim-unavailable (V2-02);
- resolver ambiguity and resolver hash mismatch (V2-03);
- P1/P2 canonical and alias firewall (V2-03);
- resolver state leakage through field, alias, locator, retry, timing, failure,
  shape, and queue/order side channels (V2-04);
- known target plus unknown additional multiplicity and unbounded multiplicity (V2-05);
- transitive legacy descendant and incomplete prospective-summary provenance (V2-06);
- unlisted component and implementation amendment (V2-07);
- target-specific non-mechanical key change (V2-08);
- C0/C1 nested equality mismatch, retry/cache asymmetry, and session reuse (V2-09);
- treatment/source/complexity/adapter/resolution-correlated missingness (V2-10).

All fixtures are synthetic and local. No test may read the production corpus,
naturalistic transcripts, live Chroma, live registry, or external study state.

## 9. Ryan-decision dependencies

Implementation may create typed slots, validators, synthetic values and
`PENDING`/`NOT_APPLICABLE` handling. It may not select a value. All registry
values become mandatory only at `P0_T0_CONSTRUCT_FREEZE`; unresolved required
values make P0 `INVALID_NOT_STARTED` and block G6/T0.

| Decision ID | Earliest work before selection | Concrete value first required | Stage blocked if unresolved |
|---|---|---|---|
| `D_IDENTITY_001` | V2-01 types, capability predicates, fixtures | P0 manifest instance/admitted use | P0/P1 |
| `D_LINEAGE_001` | V2-01 issuance modes and local/unknown behavior | P0 source policy | P0/P1 |
| `D_SOURCE_001` | V2-02 profiles for any candidate source class | P0 nonempty admitted list | P0/P1 |
| `D_ASSURANCE_001` | V2-02 per-use reducer with injected policy | P0 primary-use policy | P0/P1/P3 |
| `D_ATTACHMENT_001` | V2-02 attachment states/validators | P0 per-source mapping | P0/P1 |
| `D_MATERIAL_001` | V2-02 material-span enforcement slots | P0 target-use policy | P0/P3/T4 |
| `D_RESOLVER_001` | V2-03/V2-04 fixed-policy validator and fixtures | P0 value (`V2_FIXED_POLICY`) | P0/P2/P3 |
| `D_MULTIPLICITY_001` | V2-05 bounds types and unbounded blocker | P0 allowed bound sources/validator | P0/P3/T9/T10 |
| `D_RETENTION_001` | schemas, digest/access/deletion validation | P0 retention instance | P0/P1 |
| `D_AMEND_001` | V2-07 fixed amendment engine | P0 value (`V2_FIXED_POLICY`) | P0/all stages |
| `D_RELIABILITY_001` | existing pending slots plus V2 typed total mapping | P0 sparse rule | P0/T8–T10 |
| `D_RELIABILITY_002` | scorer-seal/gate slots and synthetic fixtures | P0 statistic/gate | P0/T8–T10 |
| `D_PRODUCT_001`, `D_PRODUCT_002` | typed validation only | P0 product/null contract | P0/T10 |
| `D_INFO_001`, `D_INFO_002` | typed validation/information-state tests | P0 information floors | P0/T10 |
| `D_PRECISION_001` | supported-method schema and injected calculator interface | P0 complete method parameters | P0/T10 |
| `D_SAMPLING_001`, `D_SAMPLING_002` | sampler validators and synthetic census/sample fixtures | P0 workload/design values | P0/T3 |
| `D_FRAME_001` | schedule/count-or-duration schema and no-extension checks | P0 episode count/window | P0/P1 |

No slice may convert a synthetic fixture value into a default, recommendation,
or frozen study value.

## 10. Review gates and stage blocking summary

Estimated gates are review events, not elapsed-time promises:

1. V2-00 exact-byte review.
2. V2-01 identity/evidence review.
3. V2-02 per-adapter capability review.
4. V2-03 resolver/firewall isolation review.
5. V2-04 blinded noninterference review.
6. V2-05 registry/estimand review.
7. V2-06 transitive provenance review.
8. V2-07 implementation/amendment inventory review.
9. V2-08 scorer/key-separation review.
10. V2-09 controller/environment isolation review.
11. V2-10 missingness/measurement review.
12. V2-11 fresh exact-tip full conformance review.

No gate is inherited from a different revision. A FAIL returns only the failed
slice for correction; it does not reopen locked architecture or authorize a
later slice. G5C and the G1–G5 synthetic methodology remain closed and unchanged.

## 11. Explicit STOP boundary

The implementation-planning lane ends with this review package. It does not:

- modify runtime code or locked V2 bytes;
- choose any Ryan decision value;
- authorize any listed implementation slice;
- authorize G6/T0, naturalistic evidence access, evidence snapshots, live
  registry execution, Agent A/B, scoring, analysis, or product disposition;
- turn Chroma, a resolver, an adapter cache, or a controller package into a
  second evidence authority;
- reopen G1–G5 synthetic methodology or G5C.

The only next action permitted by this document is Ryan reviewing the plan and,
if he chooses, issuing a separate grant for **V2-00 only**. After full V2-11
conformance and fresh independent review, the result is merely evidence for a
later Ryan G6/T0 reconsideration, never an automatic grant.

**Required status:** `PRE-G6 V2 IMPLEMENTATION PLAN READY FOR RYAN REVIEW`

**TL;DR:** Current G1–G5 mechanics remain reusable behind new V2 authority
boundaries. Eleven separately reviewed implementation slices take the repo from
an exact contract oracle through P1/P2/P3, provenance, scorer, controller and
missingness conformance. The first proposed grant is exact-byte authority import
and tests only; this plan authorizes no implementation or live study activity.
