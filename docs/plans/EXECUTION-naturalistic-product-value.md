# Execution Plan — Naturalistic ConvMem Product-Value Study

> **EXPLANATORY PROJECTION ONLY — NOT AUTHORIZED FOR IMPLEMENTATION OR
> EXECUTION.** This plan translates locked PRE-G6 Contract V2 into separately
> grantable stages for human readability. It authorizes no code, no Agent-A or
> Agent-B run, no episode collection, no target adjudication, no target-directed
> recapture, and no product conclusion.
>
> **Arc:** Naturalistic ConvMem product-value evaluation
>
> **Canonical semantic SSoT:**
> [`docs/plans/artifacts/naturalistic-pre-g6-contract-v2.json`](artifacts/naturalistic-pre-g6-contract-v2.json)
> at locked commit `9f4791c2744c02d742fdb9c0fa1e9dd150591ac1` (digest
> `917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e`).
> This prose document and
> [`ARCHITECTURE-naturalistic-product-value.md`](ARCHITECTURE-naturalistic-product-value.md)
> are explanatory projections only. When they conflict with the canonical JSON,
> the JSON wins.

## Planning status and human consequence

PRE-G6 Contract V2 is **architecture-locked** (Ryan, 2026-08-31). The locked
contract operationalizes a serial, fail-closed study workflow. The important
consequence for Ryan is that no downstream lane can begin ordinary work, target
adjudication, probe construction, or paired execution merely because an earlier
artifact exists: each transition has a named authority, a sealed manifest, and
a separate grant.

**Goal:** maintain an independently reviewable execution projection aligned to
locked V2 so a bounded implementation plan can be prepared separately.

**System state:** G1–G5 methodology machinery is on `main` (synthetic dry-run
only). PRE-G6 V2 architecture is locked at `9f4791c`. Implementation,
G6/T0, and live study remain **unauthorized**
(`implementation_authorized`, `g6_authorized`, `t0_authorized` all `false` in
the locked contract).

**Next gate:** independent planning-doc review → bounded implementation-plan/
grant preparation → Ryan approval. G6/T0 reconsideration requires a **separate**
Ryan grant after implementation verification — not implied by this lock.

## 1. Locked architecture decisions

The following are inherited constraints, not choices for a later implementer
to reopen:

1. Two independent adjudicators review the complete target census. A
   disagreement is resolved by a blinded third adjudicator or a blinded
   consensus procedure frozen before adjudication. Disagreement rate is a
   registry-quality metric.
2. The census is preferred whenever prospectively feasible. If sampling is
   necessary, whole-episode probability sampling is preferred; individual
   target sampling may not change episode weight or favor target-rich episodes.
3. The primary presentation is co-primary and two-part: opportunity prevalence
   across all selected episodes, including zero-target episodes, plus the
   episode-level C1−C0 continuation benefit among target-bearing/evaluable
   episodes.
4. The conditional outcome is one bounded, normalized within-episode
   continuation-utility score per episode and condition. Target-level outcomes
   are secondary diagnostics.
5. Zero-target episodes remain in the EpisodeFrame and opportunity analysis.
   They do not automatically contribute a zero treatment effect and do not
   enter the conditional product-effect numerator.
6. Raw evidence manifests and the sealed TargetRegistry are authoritative for
   target membership only after P1 seal, P2 resolution, and P3 blinded registry
   seal. ConvMem capture, retrieval, and traces are later diagnostics or
   treatment material; they cannot mint or delete targets.
7. A probe author may see the sealed target record and minimum raw context
   needed for realistic construction and may therefore know target content.
   That is not called answer blindness. The author may not author a target
   they adjudicated. An independent leakage reviewer must sign every
   target-specific probe before freeze. The scoring key is separately sealed.
8. Sparse episode evidence and scorer disagreement are explicit reliability
   states. They cannot silently receive ordinary confidence or produce a
   product verdict.
9. No numerical value is invented by this plan for a meaningful advantage,
   equivalence margin, information floor, sparse floor, scorer floor, sampling
   threshold, or precision/confidence criterion.

## 2. Stage dependency graph and global rules

**Authoritative sequence** (locked V2 `stage_graph`):

```text
P0_T0_CONSTRUCT_FREEZE
  └─► P1_T1_EVIDENCE_SEAL
        └─► P2_OPAQUE_RESOLUTION
              └─► P3_T2_BLINDED_ADJUDICATION_REGISTRY_SEAL
                    └─► T3_SAMPLE_SEAL
                          └─► T4_PROBE_KEY_SCORER_SEAL
                                └─► T5_C1_SNAPSHOT_CAPTURE_DIAGNOSIS
                                      └─► T6_C0_C1_READINESS
                                            └─► T7_EXECUTION
                                                  └─► T8_MASKED_SCORING
                                                        └─► T9_AGGREGATION
                                                              └─► T10_INFORMATION_GATE
```

P2 is a distinct authority-producing stage (`resolver_result`,
`capability_vector`). It must not be folded into P1 or P3.

**Legacy explanatory mapping** (sections §3–§13 below retain older T0–T10
headings for continuity; grants and dependencies must use V2 IDs):

| Locked V2 stage | Legacy plan section | Primary authority / artifact |
|---|---|---|
| `P0_T0_CONSTRUCT_FREEZE` | §3 T0 | Construct freeze, decision registry, role access |
| `P1_T1_EVIDENCE_SEAL` | §4 T1 | Occurrence/revision/snapshot/evidence envelope |
| `P2_OPAQUE_RESOLUTION` | *(new — split from old T2)* | `OpaqueResolverManifestV2` |
| `P3_T2_BLINDED_ADJUDICATION_REGISTRY_SEAL` | §5 T2 | Target registry over `AdjudicationEvidenceViewV1` |
| `T3_SAMPLE_SEAL` | §6 T3 | Census/sample freeze |
| `T4_PROBE_KEY_SCORER_SEAL` | §7 T4 | Probe/key/scorer seal |
| `T5_C1_SNAPSHOT_CAPTURE_DIAGNOSIS` | §8 T5 | C1 snapshot and capture diagnosis |
| `T6_C0_C1_READINESS` | §9 T6 | C0/C1 qualification |
| `T7_EXECUTION` | §10 T7 | Agent-B paired execution |
| `T8_MASKED_SCORING` | §11 T8 | Blinded scoring |
| `T9_AGGREGATION` | §12 T9 | Episode aggregation |
| `T10_INFORMATION_GATE` | §13 T10 | Information/null gate |

The implementation grants may develop and test their own mechanics in
parallel only where the dependency table permits it. Live study artifacts
follow the serial V2 chain above. A later grant may not repair an earlier
sealed artifact; it must produce `INVALID`, `DIAGNOSTIC`, or
`BLOCKED / NON-ESTIMABLE` according to the failure rule and stop.

Every artifact that affects eligibility, sampling, probing, scoring, treatment
assignment, or analysis is content-addressed with a SHA-256 digest and bound to
the prior artifact identities. Every actor/session has a stable identity and
role, and every transition records authority, timestamp, input digests, output
digests, and software/environment identity.

The controller is a mechanical state machine. It may validate, hash, seal,
assign, and record; it may not answer for Agent B, search on Agent B's behalf,
select interesting targets, edit a frozen probe, add context, or choose a
favorable analysis rule.

## 3. P0 / T0 — Construct freeze and study preregistration

> **V2 stage:** `P0_T0_CONSTRUCT_FREEZE` (legacy name: T0)

### Purpose and entry authority

P0 instantiates locked construct semantics as one frozen registration before
ordinary work begins. Ryan is the study owner and must approve the registration.
The controller verifies completeness mechanically. **No Agent A may begin before
P0 freeze verification passes.**

### Required T0 content

The `StudyFrame` and `T0FreezeManifest` must instantiate, without leaving an
implicit choice to a later actor:

- ordinary-work episode population, prospectively selected episode rule, and
  inclusion/exclusion criteria;
- fixed episode count or fixed observation window, including the event/time
  rule that closes an episode;
- context-gap schedule and any allowed timing trigger;
- model, build, system/prompt settings, ordinary tools, network policy,
  readable roots, repository/GitHub access, and raw-evidence retention;
- C0 definition: ordinary evidence/tools with no ConvMem retrieval or memory
  context;
- C1 definition: the same environment with normal ConvMem against the frozen
  study snapshot and no target-directed repair;
- eligibility and unitization protocol, including the mechanical stable-subject,
  truth/currentness, recovery-evaluability, ambiguity, and duplicate procedure;
- two adjudicator identities, independent submission rule, blinded disagreement
  resolution method, and registry-quality metrics;
- probe-author, leakage-reviewer, scorer, and controller identities/roles,
  overlap prohibitions, allowed evidence views, and scoring-key partition;
- census preference, workload ceiling, and the whole-episode sampling rule if
  the census is not feasible;
- scoring vocabulary, bounded normalized within-episode score contract,
  target-level secondary outcomes, sparse reliability states, and scorer
  reliability statistic/gate slots;
- the authoritative two-part co-primary estimand and zero-target handling;
- null/information parameter slots: meaningful advantage, equivalence margin,
  target-bearing episode information floor, secondary information floor,
  precision/confidence rule, sparse reliability rule, scorer-reliability rule,
  and terminal disposition rule;
- terminal-state vocabulary and allowed transitions, including
  `COMPLETE — POSITIVE`, `COMPLETE — NULL / EQUIVALENT`,
  `COMPLETE — NEGATIVE`, `BLOCKED / NON-ESTIMABLE`, `DIAGNOSTIC`, and
  `INVALID`.

The frame must also specify which parameters are construct-defining versus
operational. T0 cannot defer a choice by leaving a prose placeholder that
permits a result-dependent value. A slot may remain pending only while the
study is `FRAME_DRAFT`; it must have a frozen value or an explicitly frozen
non-applicability rule before `FRAME_FROZEN`.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| Accepted architecture; Ryan's study registration; environment inventory; workload benchmark | `StudyFrame`, `RoleAccessManifest`, `T0FreezeManifest` | Study ID, frame version, creator/approver IDs, creation/seal time, SHA-256 of each artifact, parent architecture SHA, exact model/build/settings and environment digest |
| Frozen episode selection rule | Selected episode schedule | Selection seed/rule digest, position, episode IDs, scheduled window, no-replacement constraint |
| Frozen estimand and scoring contract | Parameter registry | Slot name, value or explicit pending-before-freeze status, evidence/authority field, construct flag, seal digest |

### Invariants and negative tests

- A frame with missing role identity, overlap rule, terminal state, environment
  field, estimand component, or parameter slot cannot transition to
  `FRAME_FROZEN`.
- A post-freeze byte edit, role substitution, treatment-definition edit,
  order-rule edit, or threshold edit changes the digest and is rejected.
- A schedule that permits replacement after an uninteresting episode is
  rejected.
- A sampling rule that chooses individual targets by capture, retrieval,
  memorability, searchability, semantic interest, or expected C1 advantage is
  rejected.
- A role graph in which a target adjudicator can author that target's probe,
  or in which the leakage reviewer is not independent, is rejected.
- An empty or result-dependent numerical slot is a T0 failure, not a later
  analysis decision.

### Stop condition

T0 stops as `INVALID / NOT STARTED` for an incomplete or mutable frame. It is
`BLOCKED` only when a required external authority or environment fact cannot
be obtained without Ryan's decision. No ordinary work or implementation grant
may proceed from either state.

## 4. P1 / T1 — Evidence seal

> **V2 stage:** `P1_T1_EVIDENCE_SEAL` (legacy section title: T1 natural episode
> collection)

### Purpose and operating rule

P1 executes only the prospectively selected ordinary-work episodes in the
frozen schedule. It retains every selected episode, including boring episodes,
episodes with no temporal change, and episodes later found to have zero
eligible targets. No replacement episode may be substituted because a result
looks uninteresting or unfavorable.

The recorder seals admissible ordinary evidence under P1 authority. Outputs
include `EvidenceSealManifestV2`, `EvidenceAvailabilityManifestV2`, and
`AdjudicationEvidenceViewV1`. P1 identity bindings must carry occurrence,
physical instance, revision/as-of, lineage, evidence snapshot, envelope
digests, canonicalization profile, and adapter implementation identity — not
merely `source ID/class/locator + digest + counts/times + snapshot`.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| Frozen `StudyFrame` and selected schedule | Immutable `EpisodeRecord` for every selected episode | `episode_id`, frame digest, schedule position, start/end timestamps, environment/session identity, recorder identity, terminal state |
| Ordinary episode sources and permitted snapshots | `EvidenceSealManifestV2`, envelope commitments, `AdjudicationEvidenceViewV1` | Occurrence reference, physical instance, revision/as-of, evidence snapshot, envelope/canonical/profile/adapter digests, condition-neutral availability |
| Controller event log | Episode terminal record | Controller/session identity, state-transition evidence, failure explanation, no-replacement attestation |

### Required terminal handling

T1 records an explicit observation disposition for every selected episode:

- `EPISODE_OBSERVED_COMPLETE` — all T0-permitted raw evidence is captured and
  sealed;
- `EVIDENCE_INCOMPLETE` — one or more required sources are missing, with the
  missing-source explanation and manifest digest;
- `INSTRUMENTATION_FAILURE` — the recorder/controller failed, with the failure
  trace and whatever evidence was safely retained.

T2 must later refine every selected episode to an explicit registry/analysis
   status, including `ZERO_ELIGIBLE_TARGETS`. An episode never disappears
   because its T1 disposition was incomplete or its content produced no target.

### Invariants, negative tests, and stop condition

- The recorder cannot inspect ConvMem capture success to decide whether to
  retain, complete, or replace an episode.
- A missing source cannot be represented as a complete manifest.
- A manifest digest must change if source bytes, event bounds, completeness,
  or source identity changes.
- A replacement schedule, unsealed raw source, duplicate episode ID, or
  unexplained instrumentation gap is a gate failure.
- T1 stops the affected episode as `DIAGNOSTIC` for instrumentation/identity
  failure. If the missing evidence prevents any valid downstream inference,
  it is retained and the affected product analysis may become
  `BLOCKED / NON-ESTIMABLE`; it is never relabeled zero.

## 5. P2 — Opaque resolution

> **V2 stage:** `P2_OPAQUE_RESOLUTION` (new distinct stage — not present in
> legacy T0→T1→T2 model)

P2 consumes P1-sealed evidence and produces `OpaqueResolverManifestV2`,
including canonical `resolver_result` and `capability_vector` authority.
Resolver outputs are hidden from adjudicators via the locked role-access and
P1/P2 canonical-field firewalls. P2 must complete before P3 registry seal.

## 6. P3 / T2 — Blinded adjudication and registry seal

> **V2 stage:** `P3_T2_BLINDED_ADJUDICATION_REGISTRY_SEAL` (legacy section
> title: T2 blind complete target census)

### Purpose and access boundary

P3 discovers and adjudicates the complete natural target census from
`AdjudicationEvidenceViewV1` — the complete **authorized condition-neutral
evidence view**, not unrestricted P1/P2 internals. Two independent adjudicators
each review that blind view and frozen rules, independently enumerate/adjudicate
candidates, and submit before seeing the other decision. The ConvMem store,
`OpaqueResolverManifestV2`, `resolver_result`, `capability_vector`, resolver
paths/locators, resolver failures/retries/timing, capture state, retrieval
traces, target-specific search results, C0/C1 outcomes, treatment order, and
downstream scores are unread and uninspected for census decisions.

### Mechanical adjudication procedure

Each adjudicator records, for every candidate:

1. natural origin and immutable supporting spans;
2. stable semantic subject, proposition/state, and validity interval;
3. truth/currentness status supported by frozen evidence at the relevant time;
4. a predeclared recovery/continuation probe-family mapping and observable
   later scoring target;
5. ambiguity resolution using only frozen evidence and rules;
6. smallest independently scorable unit, duplicate links, and parent/derived
   relationships.

The final candidate disposition is exactly one of:

- `ELIGIBLE` — all admissibility seams pass and a later score is supportable;
- `INELIGIBLE` — no natural/local support, non-semantic content, or no valid
  scoring path under the frozen rules;
- `AMBIGUOUS_NON_EVALUABLE` — substantive candidate remains unresolved on
  subject, truth/currentness, unitization, or later evaluability after the
  allowed evidence view.

Only `ELIGIBLE` enters the eligible target count. The other two dispositions
remain in the adjudication ledger with reasons, so they cannot silently become
zero or alter the denominator through undocumented judgment.

### Registry output and resolution

The `TargetRegistry` has one episode entry for every selected episode. Target
rows contain immutable IDs, raw span IDs and manifest digest, target value and
ground-truth partition, class/strata labels, temporal/provenance requirements,
unitization and duplicate links, both adjudication records, disagreement
reason, blinded resolution, assessor identities, policy version, and registry
digest.

If A/B disagree, the frozen mechanism is used:

- **Third-adjudicator path:** a third person sees the authorized evidence view,
  rules, and the two submitted decisions but not treatment/result material or
  P2 resolver internals, then records the resolution; or
- **Blinded consensus path:** a predeclared facilitator runs a blinded
  resolution procedure with no treatment/result access and records the rule,
  participants, and outcome.

The registry-quality report records overall and seam-specific agreement,
disagreement rate, resolution rate, ambiguity rate, duplicate/unitization
rate, and missing-evidence rate. It must not report only the resolved roster.

### Invariants, negative tests, and stop condition

- The complete census means no target-bearing candidate can be omitted by
  relying only on a prefiltered list from one adjudicator.
- Capture-dependent inclusion, retrieval-dependent exclusion, adjudicator
  access to treatment/result material, an unsealed candidate edit, or a
  disagreement resolved by the original probe author is rejected.
- Every selected episode gets a registry entry. A true all-zero census entry is
  `ZERO_ELIGIBLE_TARGETS`, never missing and never `EVIDENCE_INCOMPLETE`.
- Registry sealing is one-way. A later target edit creates a new invalid
  generation and cannot mutate the sealed census.

T3 stops as `INVALID` for access or seal violations, `DIAGNOSTIC` for identity
or evidence-recording failures, and `BLOCKED / NON-ESTIMABLE` if valid evidence
cannot support a target-bearing/evaluable set. None of these states authorizes
probe construction against an unsealed registry.

## 7. T3 — Census/sample freeze

### Rule

If the T0 workload rule says a census is feasible, retain every eligible target
and every episode in the sealed registry. If sampling is prospectively
permitted, sample complete episodes using the frozen episode-preserving
probability rule, and retain all eligible targets within each selected episode.
The whole-episode preference prevents target-rich episodes from receiving more
primary weight merely because they contain more rows.

The full registry, including zero-target episodes and unsampled episodes/targets,
remains preserved. Individual-target sampling is not the default. It is allowed
only if a separately frozen design proves that the episode-primary weighting is
unchanged and no target-rich preference is introduced.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| Sealed `TargetRegistry`; T0 workload rule | `CensusAcceptance` or `EpisodeSampleManifest` | Registry digest, frame digest, census/sample rule version, sample seed, sampler identity, selected episode IDs, inclusion probabilities, decision reason |
| Complete registry | Unsampled-roster preservation | Full registry digest, unsampled episode/target IDs, count and digest, proof that no row was deleted or edited |
| Frozen analysis contract | Sampling-analysis binding | Design-weight/episode-weight rule identity, target inclusion relationship, co-primary A population definition |

### Invariants, negative tests, and stop condition

- The sample seed is derived only from precommitted study identity, registry
  identity, and the frozen rule; it cannot use capture, target class,
  retrieval, or expected outcome.
- A target picked manually, a target-rich episode silently split, missing
  zero-target episodes, or an unsampled roster that cannot be reconstructed is
  rejected.
- A sample manifest cannot be created before registry sealing or changed after
  probe/result material exists.

The stage stops `INVALID` for discretionary selection or post-seal edits,
`DIAGNOSTIC` for manifest/identity failure, and `BLOCKED / NON-ESTIMABLE` when
the frozen design cannot identify the episode-primary population. A census is
not downgraded to a sample after seeing the roster.

## 8. T4 — Probe and scoring-key construction

> **V2 stage:** `T4_PROBE_KEY_SCORER_SEAL`

### Role contract

Target-specific probe construction begins only after T2 registry sealing and
T3 census/sample freeze. The probe author may read the sealed target record and
the minimum raw context necessary to construct a realistic continuation or
recovery task. The author may necessarily know the target content; the plan
does not claim answer blindness.

The hard invariant is:

> No individual may author the probe for a target they adjudicated.

The probe author remains blind to ConvMem capture/retrieval, treatment order,
C0/C1 outcomes, scorer decisions, and any result-derived material. An
independent leakage reviewer, who is neither the probe author nor an
adjudicator for that target, reviews and signs every probe before freeze.

The scoring key is kept in a separately sealed scorer partition. The Agent-B
view, controller, probe author, and leakage reviewer do not receive the key
after its sealed submission except as expressly required by their declared
role; scorer access begins only in T8.

### Construction requirements

- Probe families and scoring vocabulary were frozen at T0; target-specific
  wording is instantiated from the sealed registry and permitted raw context.
- Prefer realistic continuation/recovery tasks that require a decision,
  artifact, workflow continuation, or current work answer. Direct trivia
  recall is secondary unless the frozen architecture explicitly permits it.
- The probe must not expose answer content, answer-bearing paraphrase, source
  path, source-location hint, treatment cue, or ConvMem cue. An exception is
  allowed only when the ordinary task legitimately exposes the same information
  to both conditions and the exception is documented before freeze.
- The key defines correctness, currentness, provenance/grounding,
  unsupported-claim handling, and continuation utility without relying on
  retrieval rank as truth.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| Sealed registry/sample; T0 probe family and rubric | `ProbeManifest` | `probe_id`, target/episode IDs, registry/sample digest, family/rubric version, author ID, prompt digest, permitted context digest, seal time |
| Author's sealed key submission | `ScoringKeyManifest` in separate partition | Key ID/digest, target/probe IDs, key-author ID, scorer-role access policy, seal time; key values not in Agent-B view |
| Independent leakage review | `LeakageReviewManifest` | Reviewer ID, probe/key digests, checklist results, exception record if any, sign-off time, review tool/version |

### Invariants, negative tests, and stop condition

- Probe author/adjudicator identity collision is a hard failure.
- Probe text containing answer content, answer-bearing paraphrase, source path,
  location hint, treatment, or ConvMem cue is rejected by the leakage fixture
  unless the frozen ordinary-task exception applies.
- A probe or key edited after sign-off has a new digest and cannot enter T5.
- A probe constructed from capture status, retrieval rank, C0/C1 output, or
  treatment order is rejected.
- A missing key, unreviewed probe, or key visible in the Agent-B package stops
  the stage.

The stage stops `INVALID` for role, leakage, or post-freeze violations,
`DIAGNOSTIC` for an isolated review/instrumentation failure, and
`BLOCKED / NON-ESTIMABLE` if no valid probe can support an eligible target.

## 8. T5 — Natural ConvMem capture diagnosis and C1 freeze

### Rule

Only after the registry, census/sample, probes, and scoring key are sealed may
the study identify the natural ConvMem state. Normal Agent-A capture and the
accepted background defined at T0 are retained. There is no target-directed
recapture, rewriting, routing, note creation, query treatment, or repair.

The `C1SnapshotManifest` must prove that C1 contains only naturally produced
study material plus the background explicitly accepted at T0. A target-specific
addition, repair, or post-census reindex is not accepted background merely
because it improves retrieval; it makes the snapshot invalid for this study.

Each registry target receives a later capture diagnostic such as `CAPTURED`,
`ABSENT_FROM_CONVMEM`, `AMBIGUOUS_CAPTURE`, or `MALFORMED_CAPTURE`. All states
remain in the primary end-to-end denominator. Capture status cannot change
target membership or probe eligibility.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| Sealed registry/sample/probes; normal Agent-A corpus state | `ConvMemCaptureState` | Registry digest, target ID, source/capture identity, capture rubric version, read-only diagnostic trace, assessor identity, state digest |
| Frozen normal ConvMem state and accepted background | `C1SnapshotManifest` | Corpus/export/processed/Chroma or serving-generation identities, `serving_index_repository.py` generation identity where applicable, package and source digests, snapshot time, study/frame digest |
| Capture diagnostics | Capture audit | Complete target roster including uncaptured targets, no-recapture attestation, diagnostic counts and digests |

### Invariants, negative tests, and stop condition

- A capture-dependent registry edit, target-directed reindex, target-directed
  note, or selected-target repair is rejected.
- C1 cannot be formed from a mutable or incomplete ConvMem snapshot.
- An uncaptured target must have a row; it cannot be dropped from the primary
  denominator.
- The capture assessor cannot see C0/C1 outcomes or alter the key/probe.

The stage stops `INVALID` on target-directed mutation or snapshot substitution,
`DIAGNOSTIC` on capture instrumentation/identity failure, and
`BLOCKED / NON-ESTIMABLE` if the C1 state cannot be frozen without changing the
study treatment. No C1 failure authorizes a recapture.

## 9. T6 — C0/C1 environment qualification and order freeze

### Symmetry proof

The controller mechanically proves that C0 and C1 receive the same:

- sealed raw evidence and ordinary files;
- repository, GitHub, filesystem, readable-root, and network policy;
- model, build, prompt/settings, budget, stopping rules, and tool versions;
- context gap, probe, scoring policy, and session initialization;
- execution manifest and allowed ordinary tools.

Only C1 receives normal ConvMem availability against the immutable T5 snapshot.
C0 has no ConvMem retrieval or memory context. The controller cannot answer,
search, paste a target, select a source, or act as Agent B.

The fresh-session mechanism is verified to create real, distinct session IDs.
The Agent-B package contains neither the registry nor the scoring key, and the
controller proves no prior-trial transcript or condition result is mounted.
Randomized or counterbalanced C0/C1 order is frozen before the first trial.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| T0 environment/order policy; T5 C1 snapshot; T4 probes | `C0C1EnvironmentManifest` | Per-condition package digests, tool/model/build/settings identities, readable roots/network policy, ConvMem availability bit, budget/stopping identity |
| Fresh-session mechanism | `SessionIsolationManifest` | Controller ID, real session IDs, process/container identity where applicable, prior-session absence proof, Agent-B package digest |
| Frozen order rule | `ConditionOrderManifest` | Randomization/counterbalance rule, seed, assignment per pair, freeze time/digest, no-result-before-freeze attestation |
| Mechanical comparison | `EnvironmentQualificationReport` | Equality comparison, sole intended C0/C1 difference, verifier identity/version, pass/fail digest |

### Invariants, negative tests, and stop condition

- Any C0/C1 tool, readable-root, network, model, budget, prompt, gap, or
  stopping-rule difference other than ConvMem availability is a qualification
  failure.
- A reused Agent-B context/session, registry/key exposure, controller action on
  behalf of Agent B, or mutable C1 snapshot is rejected.
- Changing order after observing an outcome is rejected.
- A qualification report cannot be generated from self-reported equality alone;
  it needs manifest comparison and a fresh-session check.

T6 stops `INVALID` for asymmetry, prior-trial leakage, or order mutation,
`DIAGNOSTIC` for incomplete instrumentation, and `BLOCKED / NON-ESTIMABLE` if
the common environment cannot be established. No Agent-B trial may begin.

## 10. T7 — Agent-B paired execution

### Operating rule

T7 executes each selected target/probe pair in both C0 and C1 only after T6
passes. Every condition is a genuinely fresh Agent-B session. The controller
enforces the frozen package and terminal rules but never answers, selects a
search, pastes a target, or repairs a trial.

For every trial retain the complete raw evidence: probe/prompt, session ID,
condition assignment, model/build/settings, tool manifest, model-selected
actions, tool outputs, complete transcript, final answer/artifact, action
count, latency, provenance trace, and terminal disposition. A failed or
uninteresting trial is retained; it is not replaced.

### Required terminal dispositions

Each selected trial ends as one explicit state, for example:

- `TRIAL_COMPLETE` — final output and trace are complete;
- `TRIAL_AGENT_FAILURE` — Agent B failed or stopped under the frozen rule;
- `TRIAL_TOOL_FAILURE` — an allowed tool failed, with trace;
- `TRIAL_INSTRUMENTATION_FAILURE` — capture/controller evidence is incomplete;
- `TRIAL_PROTOCOL_INVALID` — an invariant was violated.

These trial states do not rewrite target eligibility or turn missing evidence
into a zero-target episode.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| T4 `ProbeManifest`/key digest; T5 `C1SnapshotManifest`; T6 environment/order manifests | `AgentBTrialRecord` for C0 and C1 | Trial ID, pair/episode/target/probe IDs, condition/order identity, fresh session ID, package digests, start/end times, terminal state |
| Session/tool controller | `AgentBTrace` and action/latency record | Full prompt/transcript/tool outputs, tool versions, model-selected action evidence, action count, latency definition, provenance/trace digest |
| Controller terminal check | Execution manifest | Complete selected-trial roster, missing-trial explanation, no-replacement attestation, overall execution digest |

### Invariants, negative tests, and stop condition

- Every selected pair has exactly one C0 and one C1 trial unless the frozen
  terminal rule records an explicit failure.
- Reusing a prior Agent-B context, injecting registry/key content, controller
  answer/search, target-directed reindex, or condition-specific repair is a
  hard failure.
- Missing prompt, session ID, action trace, output, timing, or provenance is
  not silently completed from memory.
- The complete execution manifest must include failed and zero-opportunity
  episode relationships where applicable.

T7 stops `INVALID` for protocol or context leakage, `DIAGNOSTIC` for trace or
instrumentation loss, and `BLOCKED / NON-ESTIMABLE` if enough paired trials
cannot be identified under the frozen design. It does not authorize reruns
chosen for favorable outcomes.

## 11. T8 — Blinded scoring

### Scoring and reliability rule

Two independent scoring roles score the complete eligible/evaluable target set
and derive the bounded episode score with condition labels masked. Each scorer
uses the sealed key and frozen rubric and submits independently before seeing
the other's decisions. Disagreements are resolved by the frozen blinded third
scorer or blinded consensus procedure.

The score record covers correctness, currentness, provenance/grounding,
unsupported claims, realistic continuation utility, and permitted effort/
latency diagnostics. Retrieval rank and capture state are not scoring truth.

The reliability report records raw agreement and scale-appropriate checks:
weighted kappa for ordinal/categorical dimensions and an intraclass-correlation
or equivalent predeclared statistic for the bounded episode score. The exact
statistic and minimum acceptable scorer-reliability gate were slots in T0 and
must be frozen before scoring begins.

Sparse evidence also receives the frozen `score_reliability` state, at minimum
distinguishing `RELIABILITY_ACCEPTABLE`, `RELIABILITY_SPARSE`,
`RELIABILITY_NON_ESTIMABLE`, and `RELIABILITY_NOT_APPLICABLE` for zero-target
episodes. A sparse score may be retained descriptively, but cannot silently
receive ordinary confidence or become a zero effect.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| Sealed key/rubric; blinded trial records; raw evidence required by rubric | Independent `TargetScoreSet` and `EpisodeScoreSet` | Score version, scorer IDs, masked condition package digest, trial/probe/target/episode IDs, key/rubric digests, score and reliability states |
| Second scorer and resolution role | `ScoringReliabilityReport` | Agreement counts, scale/statistic identity, gate value, resolution records, scorer-role identities, report digest |
| Frozen sparse rule | Sparse disposition report | Evidence basis, episode reliability states, inclusion/disposition rule, no-result-change attestation |

### Invariants, negative tests, and stop condition

- A scorer who sees condition labels, treatment order, capture status, or future
  results is removed from the affected scoring set and the set is diagnostic.
- A key edited after trial execution or exposed to Agent B invalidates the
  affected scoring generation.
- Reliability below the frozen gate does not yield a product verdict. Affected
  primary scores become `BLOCKED / NON-ESTIMABLE`; an isolated secondary
  dimension may be `DIAGNOSTIC`.
- Sparse episodes cannot be silently excluded, down-weighted, or reclassified
  after seeing C1−C0 results.

T8 stops `INVALID` for scoring-key or masking violations, `DIAGNOSTIC` for
isolated scoring instrumentation failure, and `BLOCKED / NON-ESTIMABLE` when
the primary score is not reliably interpretable. Low scorer reliability is
never a product null or positive result.

## 12. T9 — Episode aggregation

### Co-primary A — opportunity prevalence/density

Use all prospectively selected episodes in the EpisodeFrame, including
`ZERO_ELIGIBLE_TARGETS`. Report the prevalence of episodes with at least one
eligible target and the predeclared opportunity density summary. If T3 used an
episode sample for an estimand beyond the observed frame, apply only the
frozen episode-sampling analysis rule and retain zero-opportunity episodes in
the population definition.

No missing, incomplete, ambiguous, or zero-target state may be collapsed into
one convenient denominator. `EVIDENCE_INCOMPLETE` is not zero.

### Co-primary B — conditional episode continuation benefit

For each target-bearing/evaluable episode in the frozen conditional analysis
set, use exactly one bounded normalized within-episode continuation-utility
score for C0 and one for C1, then form the paired C1−C0 episode contribution
under the T0 estimator. The within-episode rule may combine target-level
diagnostics only through the frozen aggregation contract. Raw target count
cannot determine episode weight.

The report must display episode count, target-bearing/evaluable count, sparse
reliability states, incomplete/ambiguous counts, paired contribution coverage,
and target-level secondary diagnostics. Zero-target episodes remain visible in
co-primary A and do not receive an invented treatment score in co-primary B.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| T1 EpisodeFrame/records; T2 registry; T3 census/sample | Opportunity analysis input | Frame, episode roster, registry/sample digests, zero-target and incomplete-state counts |
| T8 accepted target/episode scores and reliability report | `EpisodeAggregationReport` | Score-set digest, reliability gate result, one-score-per-episode proof, conditional-set rule/digest, estimator/version identity |
| Full identity chain | Analysis lineage manifest | All parent artifact digests from frame through trial, score, and aggregation |

### Invariants, negative tests, and stop condition

- Target-rich episodes cannot be weighted more heavily through extra target
  rows.
- An all-zero observation window is not classified as product null.
- Recomputing with a changed score normalization, conditional set, sparse rule,
  or threshold is rejected as a new analysis generation, not accepted as a
  correction.
- Any episode included in co-primary B must have the required paired scores or
  a frozen explicit terminal disposition.

T9 stops `INVALID` for post-result estimator or membership changes,
`DIAGNOSTIC` for lineage/aggregation defects, and `BLOCKED / NON-ESTIMABLE`
when the frozen conditional set or reliable score cannot be formed. It may
still produce the descriptive opportunity report when valid.

## 13. T10 — Information and null gate

### Pre-result gate

Before any product conclusion, the analysis owner applies the T0-frozen:

- meaningful-advantage rule;
- equivalence/null rule and margin;
- minimum target-bearing episode information rule;
- secondary information rule;
- precision/confidence or randomization criterion;
- sparse-episode disposition;
- scorer-reliability disposition;
- treatment of ties, missing pairs, and terminal trial states.

No threshold, margin, confidence rule, sparse rule, or inclusion rule may be
adapted because the results are sparse, unfavorable, or inconvenient. There is
no extension of the observation window after results are seen.

### Allowed terminal interpretations

- `COMPLETE — POSITIVE`: valid co-primary analysis meets the frozen meaningful
  positive criterion and information/precision rule.
- `COMPLETE — NULL / EQUIVALENT`: valid analysis is sufficiently informative
  under the frozen null rule to exclude the meaningful-advantage interval.
- `COMPLETE — NEGATIVE`: valid analysis meets the frozen criterion favoring C0.
- `BLOCKED / NON-ESTIMABLE`: evidence, precision, sparse reliability, or scorer
  reliability is insufficient for a product verdict.
- `DIAGNOSTIC`: an identity, completeness, instrumentation, or isolated
  secondary scoring failure prevents interpretation of the affected result.
- `INVALID`: a protocol invariant or freeze boundary was violated.

The final report contains both co-primary components and their information
states. An all-episode opportunity-weighted effect, if computed, is explicitly
secondary and cannot replace the two-part presentation.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| T0 parameter registry; T9 aggregation; reliability reports | `InformationGateReport` | Every parameter digest, estimator/score version, data/lineage digest, gate calculation, analysis owner ID |
| Frozen terminal-state rule | `StudyDisposition` | Exact terminal label, rationale, unresolved diagnostics, report digest, no-adaptation attestation |

### Invariants, negative tests, and stop condition

- A threshold edited after seeing results, an adaptive observation-window
  extension, a post-result sparse exclusion, or a result-dependent null margin
  is `INVALID`.
- A valid but insufficient information set is `BLOCKED / NON-ESTIMABLE`, never
  `COMPLETE — NULL / EQUIVALENT`.
- An identity or source failure that prevents reconstruction is `DIAGNOSTIC`
  or `INVALID` according to whether the frozen protocol was violated.

T10 is the only stage that can produce a product disposition, and only when
both co-primary reporting and all frozen information gates pass.

## 14. Grant decomposition and authorization boundaries

Every row below is separately authorizable. Completing one row does not grant
the next row. The live-study rows require a fresh explicit Ryan authorization
after implementation and dry-run verification.

| Grant | Scope | Depends on | Output/gate | Explicitly not authorized |
|---|---|---|---|---|
| G1 Methodology substrate and artifact schemas | Implement content-addressed IDs, freeze manifests, role/access manifests, state transitions, immutable artifact readers/writers | Plan accepted | Schema tests and hash/seal fixtures | Live episode data, ConvMem mutation, Agent A/B |
| G2 Adjudication/registry machinery | Implement complete-census views, mechanical admissibility procedure, dual decisions, disagreement resolution, registry seal | G1 | Registry fixture and access-separation tests | Real target census, capture inspection, study execution |
| G3 Probe/leakage machinery | Implement probe/key partitions, role overlap checks, leakage checklist/reviewer sign-off, probe freeze | G1–G2 | Leakage and key-separation fixtures | Real target probes, treatment exposure |
| G4 Analysis/statistical machinery | Implement bounded within-episode score contract, sparse states, scorer reliability records, co-primary aggregation, information gate slots | G1; architecture decisions | Synthetic paired fixtures; no chosen live numerical values | Product conclusion, real scoring |
| G5 Dry-run/fixture verification | Exercise P0–T10 mechanics with synthetic episodes, zero-targets, duplicates, leakage, asymmetry, failures, and full lineage | G1–G4 | Independent dry-run PASS report; no natural evidence | Prospective freeze, Agent A/B, live ConvMem |
| G6 Actual prospective study freeze | Ryan instantiates and approves P0 construct-freeze values, roles, schedule/window, environments, order, parameter slots, and terminal rules | G5 PASS; PRE-G6 V2 locked; bounded implementation verified; Ryan authorization | `ConstructFreezeManifestV2` and P0 verification | Agent A before gate; no result collection |
| G7 Agent-A episode execution | Collect only the selected ordinary episodes and seal P1 evidence | G6 | P1 complete episode/evidence bundle | Replacement episodes, target selection, B trials |
| G8 P2 resolution + P3 target census | P2 opaque resolution; two independent adjudicators complete blind census over `AdjudicationEvidenceViewV1`; resolve disagreements | G7 | P3 sealed `TargetRegistryV2` and quality report | Probe construction before seal; capture-based decisions |
| G9 Census/sample, probe, capture, and C1 readiness | Apply T3; construct/review T4 probes; freeze T5 natural snapshot; qualify T6 | G8; staged sub-gates | Sample/probe/key/capture/environment manifests | Target-directed recapture; B execution before T6 PASS |
| G10 Agent-B paired execution | Run both fresh conditions for the selected pairs with complete traces | G9/T6 PASS | T7 execution bundle and terminal roster | Controller answers/searches; reused context; replacement trials |
| G11 Scoring and analysis | Blind T8 scoring/reliability, T9 aggregation, T10 information/null gate | G10 | Co-primary report and allowed disposition | Threshold changes, product claim before gate |

Cursor may receive only a bounded grant naming one row and its exact output
contract. Ryan owns the transition from implementation/dry-run grants to G6–G11
live study grants. Codex does not send work to Cursor from this plan.

## 15. Reuse and new-component implementation map

The map is a planning boundary, not authorization to edit these modules.

| Study need | Reuse or new component | Boundary and required proof |
|---|---|---|
| Immutable ConvMem/corpus snapshot | Reuse `eval_corpus/capture.py` and `serving_index_repository.py` | Reuse capture/manifest and serving-generation identity; bind to the study generation; never make Chroma or a serving projection target authority |
| Existing indexing anchors | Reuse `inter_model_index.py` and `serving_index_repository.py` where ordinary indexing/serving mechanics apply | Verify source/projection identity and writer boundaries; no target-directed indexing or registry mutation |
| Retrieval/provenance diagnostics | Reuse `ask.py`, `query.py`, and existing trace interfaces | Diagnostics only; P1/P3 sealed authority remains authoritative — Chroma/retrieval cannot certify study truth |
| Latency harness | Reuse `eval_corpus/runner.py` latency conventions | Add the study's ordinary-work action taxonomy and controller-exclusion proof; do not claim an action counter module exists |
| Paired statistics and runner conventions | Reuse `eval_corpus/paired_stats.py` and `eval_corpus/runner.py` | Extend only behind the episode-level, unequal-target, zero-state, reliability, and margin contracts |
| Raw evidence recorder/controller | Historical v3 controller event/reply/raw-file conventions | Historical/to-be-relocated foundation; the exact current implementation path must be verified during G1/G5 before live use |
| Historical Portland C0/C1 harness | Historical/to-be-relocated foundation; no current reusable path verified | Do not reuse old fixed questions as design; revalidate fresh-session and symmetry behavior in fixtures |
| Obsolete cited paths | `scripts/experiments/portland-baseline/action_counter.py` and `index_runner.py` are absent at the corrected tip | They are not reusable modules. Any recovered historical artifact must be explicitly relocated, reviewed, and renamed before use |
| Artifact IDs, freeze/seal state, and role access | New methodology substrate | New schemas and mechanical checks for `StudyFrame`, `EpisodeRecord`, `RawEvidenceManifest`, state transitions, access audit, and lineage |
| Complete target registry and adjudication | New adjudication/registry machinery | New independent full-census views, admissibility decision records, duplicate/unitization rules, disagreement resolution, and registry-quality metrics |
| Probe/key/leakage lifecycle | New probe/leakage machinery | New role-separated views, leakage reviewer/sign-off, key partition, probe freeze, and treatment-cue checks |
| Naturalistic trial controller | New study controller layer | New fresh-session, package-symmetry, order, terminal-state, and no-controller-action checks; must remain a mechanical adapter |
| Sparse/scorer reliability | New scoring reliability layer | New score-state vocabulary, inter-rater records, scale-appropriate statistic, threshold slot, and fail-closed disposition |
| Co-primary episode analysis | New analysis contract around reused paired-stat foundations | New opportunity prevalence/density, one-score-per-episode aggregation, conditional paired effect, zero-target preservation, and T10 gate |

No new service or microservice is justified. The architectural boundary is
authority and artifact state within the existing local monolith; deployment
splitting is out of scope.

## 16. Consolidated verification matrix

The following matrix is the minimum evidence package for independent review.
Each row must be verified at the exact implementation/artifact tip used for
the stage. A passing fixture does not authorize live study use by itself.

| Stage | Input authority | Required output/hash/identity | Core invariants | Adversarial negatives | Stop disposition |
|---|---|---|---|---|---|
| T0 | Accepted architecture; Ryan registration; environment/workload evidence | Frozen frame, role manifest, schedule, parameter registry, all digests and approver IDs | Complete fields; no result-dependent slots; no replacement; roles and terminals explicit | Post-freeze edit; missing slot; adjudicator/probe overlap; capture-based sample rule | `INVALID / NOT STARTED` or `BLOCKED` |
| T1 | Frozen frame/schedule; ordinary work | Episode records and complete raw manifests with source/session/snapshot digests | Every selected episode retained; completeness explicit; no ConvMem-based retention | Replace boring episode; omit zero-opportunity episode; mark partial manifest complete | `DIAGNOSTIC` / `BLOCKED` |
| T2 | Sealed raw evidence; frozen rules | Two full adjudication sets, blinded resolution, registry and quality report digests | Mechanical seam decisions; raw-only; one episode row each; registry one-way seal | Capture-dependent exclusion; unsealed target edit; single-assessor shortcut; duplicate drift | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T3 | Sealed registry; T0 sample rule | Census acceptance or episode sample manifest; seed, probabilities, unsampled digest | Census if feasible; whole-episode sampling; zero rows preserved; no discretionary picking | Target-rich episode overweight; manual target pick; missing zero-target episode | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T4 | Sealed registry/sample; T0 probe families | Probe/key/leakage manifests and digests; role IDs | Realistic task; author knows boundary honestly; author ≠ adjudicator; separate key/reviewer | Answer/paraphrase/path/location leakage; treatment/ConvMem cue; identity collision | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T5 | Sealed probes/sample; normal ConvMem state | Capture-state map and immutable C1 snapshot manifest | Natural capture only; uncaptured targets retained; registry unchanged | Target-directed reindex; recapture; capture-based deletion; mutable snapshot | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T6 | T0 environment/order; T4/T5 packages | C0/C1 comparison, fresh-session proof, order manifest, qualification digest | Same evidence/tools/model/gap/budget; only C1 ConvMem; no registry/key B access | Tool asymmetry; reused session; prior-trial leakage; controller acts as B | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T7 | Qualified packages/order; selected probes | Full paired trial traces, IDs, actions, latency, provenance, terminal roster | Fresh pair; no replacement; explicit trial terminal state; complete raw evidence | Reused Agent-B context; controller answer/search; missing action trace; condition repair | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T8 | Masked trial outputs; sealed key/rubric | Independent target/episode scores, reliability report, sparse states | Complete scoring set; independent raters; frozen statistic/gate; no low-reliability verdict | Unmasked scorer; post-result key edit; sparse exclusion; below-gate positive/null | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T9 | Episode frame/registry/sample; accepted scores | Opportunity and conditional reports; one-score proof; lineage digest | All-zero not null; no target-count episode weighting; co-primary split preserved | Post-result score normalization; target-rich overweight; missing zero rows | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T10 | Frozen parameter registry; T9 outputs; reliability reports | Information gate and final allowed disposition with all parent digests | No threshold/observation adaptation; valid insufficient data is blocked | Post-result threshold change; extension for unfavorable sparsity; false null | `INVALID` / `DIAGNOSTIC` / `BLOCKED` or complete label |

### Required adversarial verification set

The dry-run and later implementation verification must include named controls
for at least the following:

1. **Capture-dependent target exclusion:** mark an eligible raw target
   uncaptured; verify it remains in the registry, sample/census, and primary
   denominator.
2. **Unsealed target edit:** mutate a target after registry seal; verify digest
   mismatch and `INVALID`, with no downstream reuse.
3. **Probe answer leakage:** inject answer content and an answer-bearing
   paraphrase; verify leakage review rejects both.
4. **Source leakage:** inject source path and source-location hint; verify
   rejection unless the frozen ordinary-task exception is present.
5. **Adjudicator/probe-author collision:** assign the same identity; verify
   T4 hard failure even if adjudication happened before probe construction.
6. **C0/C1 tool asymmetry:** remove or add one ordinary tool/readable root;
   verify T6 fails rather than reporting C1 uplift.
7. **Reused Agent-B context:** mount a prior session/transcript; verify fresh
   session and package checks fail.
8. **Target-directed reindexing:** add or rewrite a selected target's ConvMem
   material; verify T5 rejects the snapshot as non-natural.
9. **Missing zero-target episode:** drop an all-zero episode from the registry
   or opportunity file; verify T2/T9 fail.
10. **Target-rich episode overweighting:** duplicate target rows within one
    episode; verify T9 retains one episode contribution and detects the
    manipulated lineage.
11. **Post-result threshold change:** alter meaningful advantage, equivalence,
    sparse, scorer, or precision threshold after scoring; verify T10 marks the
    analysis `INVALID` and never recomputes a favorable verdict.
12. **Controller-as-agent:** make the controller provide an answer/search;
    verify T6/T7 reject the trial.
13. **Low scorer reliability:** force below-gate disagreement; verify scores
    remain diagnostic and the product conclusion is `BLOCKED / NON-ESTIMABLE`.
14. **All-zero window:** construct a valid observation window with no eligible
    target; verify opportunity reporting remains descriptive and product effect
    is not called null.

## 17. Still-unresolved numerical and product-contract choices

This plan identifies, but does not choose, the following values. Each must be
resolved prospectively and bound into T0 or the explicitly named pre-scoring
freeze. None may be selected merely for convenience.

| Choice | Freeze point | Evidence needed before choice | Acceptance authority | Construct-defining? |
|---|---|---|---|---|
| Meaningful per-episode C1−C0 advantage | T0 before Agent A | Product decision use, score calibration, expected episode variance, and a pre-study measurement/pilot rationale independent of live outcomes | Ryan after Kiro plan/measurement review | Yes |
| Equivalence/null margin | T0 before Agent A | Smallest practically important difference, score error/reliability, and the intended null claim | Ryan after Kiro review | Yes |
| Minimum target-bearing/evaluable episodes | T0 before Agent A | Design/precision analysis, expected paired-episode variance, scorer reliability, and finite-sample behavior | Ryan after Kiro review | Estimand/information-defining |
| Minimum secondary information/target count | T0 before Agent A | Secondary diagnostic precision needs and target-level score reliability | Ryan after Kiro review | No, but analysis-defining |
| Sparse-episode reliability floor/rule | T0 before Agent A | Evidence per episode, rubric sensitivity, pilot inter-rater behavior, and stability of normalized scores | Ryan with Kiro review; scorer lead supplies evidence | Measurement/estimand-defining |
| Scorer-reliability statistic and minimum gate | Statistic at T0; gate before T8 scoring | Scale type, independent scoring pilot, agreement distribution, and appropriateness of weighted kappa/ICC or equivalent | Ryan after Kiro review; scorer lead proposes | Measurement-defining |
| Census-versus-sampling workload threshold | T0 before target count | Fixture/benchmark cost for complete dual adjudication and probe construction; no roster knowledge | Ryan after Kiro operational review | Operational, but can affect estimand |
| Confidence/precision criterion | T0 before Agent A | Decision risk, estimator behavior, planned interval/randomization method, and pre-study simulation | Ryan after Kiro review | Product-inference-defining |
| Fixed episode count/observation window | T0 before Agent A | Ordinary-work population, feasible capture window, expected opportunity rate, and operational constraints | Ryan | Study-population-defining |
| Whole-episode sampling allocation/weights, if needed | T0 before registry use | Population frame, selection probabilities, episode-weight preservation proof | Ryan after Kiro sampling review | Estimand-defining |

The meaningful-advantage and equivalence choices are construct-level. If Kiro
and Ryan later produce materially conflicting written positions on either, a
bounded Sol adjudication may be appropriate. Sol is not invoked by this plan
or by ordinary implementation difficulty.

## 18. Exact questions for independent execution-plan review

Kiro's independent review should answer each question with `PASS`, `FAIL`, or
an explicitly bounded requested correction tied to this plan revision:

1. Does T0 enumerate every architecture-required freeze item and prevent Agent
   A from beginning before the mechanical freeze gate passes?
2. Does T1 retain every selected episode and distinguish complete evidence,
   incomplete evidence, instrumentation failure, and later zero-target status?
3. Does T2 implement two independent adjudicators over the complete census,
   with a mechanical subject/evaluability procedure and blinded disagreement
   resolution that cannot consult ConvMem or outcomes?
4. Does T3's whole-episode sampling rule preserve the episode-primary
   estimand, zero-target visibility, and unsampled-roster authority without
   target-rich overweighting?
5. Does T4 accurately represent the probe author's necessary knowledge of
   target content while enforcing the hard adjudicator/probe-author invariant,
   independent leakage review, exact leakage checklist, and separate key?
6. Do T5 and T6 prevent target-directed recapture, prove natural C1 state, and
   mechanically establish C0/C1 symmetry except for ConvMem availability?
7. Do T7's fresh-session and terminal-state controls prevent controller-as-
   Agent-B behavior, prior-trial leakage, replacements, and incomplete traces?
8. Does T8 define independent masked scoring, disagreement resolution,
   scale-appropriate reliability checks, sparse states, and fail-closed
   below-gate dispositions without inventing numerical floors?
9. Does T9 preserve the authoritative two-part co-primary presentation,
   use one bounded normalized score per episode/condition, keep target-level
   outcomes secondary, and preserve zero-target episodes correctly?
10. Does T10 prevent post-result threshold changes, adaptive extension, false
    null conclusions, and conflation of invalid/diagnostic/blocked states?
11. Are G1–G11 separately grantable, with Ryan authorization required before
    live T0, Agent A, census, Agent B, scoring, or analysis work?
12. Are every reuse-map path and every historical/to-be-relocated claim
    accurately labeled at the corrected architecture tip?
13. Does the verification matrix cover all requested adversarial cases and
    identify the correct failure disposition for each?
14. Does any remaining choice now constitute a genuine construct-level conflict
    requiring Sol, or can the choice remain a bounded later Ryan/Kiro decision?

## 19. Review and authorization sequence

```text
PRE-G6 Contract V2 locked (Ryan, 2026-08-31 @ 9f4791c)
        ↓
G6 planning reconciled to locked V2 (this document)
        ↓
Independent planning-doc review
        ↓
Bounded implementation-plan/grant preparation
        ↓
Ryan implementation grant approval
        ↓
Cursor bounded implementation + independent verification
        ↓
Ryan explicit separate G6/T0 reconsideration (not implied by architecture lock)
```

No branch, plan, dry-run PASS, or architecture lock is an implicit grant to run
Agent A/B or collect natural episodes. G6/T0 remain unauthorized until Ryan
issues a separate grant after implementation verification.

## 20. Implementation obligations not yet verified

Architecture lock does not prove runtime conformance. Forward obligations for
any bounded implementation plan include: richer P1 evidence identity; P2
resolver semantics and P1/P2 firewall; capability vector; unknown target
multiplicity bounds; transitive provenance firewall; scorer/runtime binding;
`ControllerEvidencePackageV2`; `C0C1EqualityManifestV2`;
`SessionIsolationManifestV2`; `ConditionOrderManifestV2`; informative-missingness
checks. G1–G5 on `main` is synthetic dry-run only.

## 21. Exit criteria for this planning lane

- [x] PRE-G6 Contract V2 architecture locked at `9f4791c` / digest `917ad129…`.
- [x] G6 planning prose reconciled to locked V2 stage graph and authority model.
- [x] P0–T10 stages specify authority, artifacts, identities, invariants,
      negative tests, and stop dispositions (V2 IDs with legacy mapping).
- [x] Grant decomposition separates methodology, adjudication, probes,
      analysis, dry-run, freeze, Agent A, P2/P3 census, Agent B, and scoring/analysis.
- [x] Reuse/new-component map identifies verified anchors and obsolete paths.
- [x] Adversarial verification includes capture exclusion, sealing, leakage,
      role collision, symmetry, context reuse, reindexing, zero targets,
      target-rich weighting, and post-result threshold changes.
- [x] Numerical/product-contract choices remain explicitly unresolved with
      evidence, authority, freeze point, and construct status.
- [ ] Independent planning-doc review.
- [ ] Bounded implementation-plan/grant preparation and Ryan approval.
- [ ] Independent implementation verification before any G6/T0 reconsideration.
- [ ] Ryan execution-plan acceptance.
- [ ] Any implementation or live-study grant.

**Next sequence:** Kiro independent execution-plan review → Ryan acceptance →
bounded Cursor implementation grants.
