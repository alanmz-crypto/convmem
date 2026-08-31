# Execution Plan — Naturalistic ConvMem Product-Value Study

> **CORRECTIVE AMENDMENT — REVIEW REQUIRED — NOT AUTHORIZED FOR
> IMPLEMENTATION OR EXECUTION.** Ryan accepted D1–D6 as the G5 corrective
> design direction on 2026-08-30. This plan amendment authorizes no code,
> parameter freeze, G6/T0 transition, Agent-A or Agent-B run, natural evidence
> access, episode collection, target adjudication, scoring, target-directed
> recapture, or product conclusion.
>
> **Arc:** Naturalistic ConvMem product-value evaluation
>
> **Architecture SSoT:**
> [`ARCHITECTURE-naturalistic-product-value.md`](ARCHITECTURE-naturalistic-product-value.md)
> in the same corrective-amendment revision submitted to Kiro. The review
> handoff binds both files to one exact commit digest.

## Planning status and human consequence

The accepted D1–D6 direction is operationalized below as a bounded corrective
to G5's synthetic composition claim. The important consequence for Ryan is
that an incomplete frame, mutable opportunity denominator, unclassified
failure, asymmetric replay environment, or missing stage guarantee cannot be
labeled successful merely because an isolated validator or downstream stage
passes.

**Goal:** produce an independently reviewable execution contract for a
naturalistic C0/C1 ConvMem product-value study.

**Codex role:** translate the accepted architecture into schemas, gates,
grant boundaries, and verification obligations. Codex does not implement or
run the study.

**System state:** G1–G5 implementation is landed, but G5's compositional PASS
is reopened at verdict C because the nominal T0_T2 path accepted an incomplete
prospective frame. D1–D6 are accepted as design direction; their mechanics are
not implemented or independently reviewed. G6/T0 remains closed.

**Next gate:** Kiro independently reviews the exact corrective architecture and
execution revision; Ryan then accepts or revises it. Any later implementation
requires a separate bounded grant.

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
3. The authoritative product result is a structured tuple: opportunity
   prevalence across the fixed frame; complete-pair C1−C0 continuation effect
   with deterministic bounds for valid missing outcomes; and full per-arm
   capture/evaluability/failure accounting. No scalar is authoritative.
4. The conditional outcome is one bounded, normalized within-episode
   continuation-utility score per episode and condition. Target-level outcomes
   are secondary diagnostics.
5. Zero-target episodes remain in the EpisodeFrame and opportunity analysis.
   They do not automatically contribute a zero treatment effect and do not
   enter the conditional product-effect numerator.
6. Raw evidence and the sealed TargetRegistry are authoritative for target
   membership. ConvMem capture, retrieval, and traces are later diagnostics
   or treatment material; they cannot mint or delete targets.
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
10. The sealed raw-evidence `TargetRegistry` is the sole opportunity and
    denominator authority. Later capture/evaluability/score records may only
    reference it.
11. Natural ConvMem capture, per-arm trial-evidence capture, and per-arm score
    evaluability are distinct axes. Valid missing outcomes are boundable;
    protocol/environment/isolation/scorer-integrity failures are invalid and
    never enter bounds.
12. Final dispositions are mechanically derived from orthogonal protocol,
    information, missingness/comparability, and scorer-reliability states using
    frozen precedence.
13. C0/C1 use paired replay from one sealed pre-trial state in fresh sessions;
    mechanical comparison proves C1 ConvMem access is the sole intended
    difference.

## 2. Stage dependency graph and global rules

```text
T0 Study freeze
  └─► T1 Natural episode collection
        └─► T2 Blind complete target census
              └─► T3 Census/sample freeze
                    └─► T4 Probe/key construction
                          └─► T5 Natural capture + C1 snapshot
                                └─► T6 C0/C1 qualification
                                      └─► T7 Agent-B paired execution
                                            └─► T8 Blinded scoring
                                                  └─► T9 Episode aggregation
                                                        └─► T10 Information/null gate
```

Future implementation grants may develop and test their own mechanics in
parallel only where the dependency table permits it. Live study artifacts
follow the serial chain above. A later grant may not repair an earlier sealed
artifact. It records the orthogonal state axes and derives the allowed
disposition under the frozen precedence rule.

Every artifact that affects eligibility, sampling, probing, scoring, treatment
assignment, or analysis is content-addressed with a SHA-256 digest and bound to
the prior artifact identities. Every actor/session has a stable identity and
role, and every transition records authority, timestamp, input digests, output
digests, and software/environment identity.

The controller is a mechanical state machine. It may validate, hash, seal,
assign, and record; it may not answer for Agent B, search on Agent B's behalf,
select interesting targets, edit a frozen probe, add context, or choose a
favorable analysis rule.

All later stage-specific stop labels are shorthand inputs to the orthogonal
state record, not a flat final enum. A defect discovered before exposure may be
`BLOCKED / NOT STARTED`; a post-freeze protocol, isolation, environment,
lineage, registry, or scorer-blinding breach is `INVALID`; valid-but-missing
outcomes retain per-arm reason codes for bounds; and an unavailable secondary
diagnostic may be `DIAGNOSTIC` only when it cannot affect treatment assignment,
primary outcome validity, or the fixed denominator. The precedence in T10
derives the sole final study disposition.

Scorer integrity and scorer reliability are different axes: condition/package
unblinding, key mutation, or scoring-context contamination is protocol
`INVALID`; valid independent scoring below the frozen agreement threshold is
`BLOCKED` with a reliability reason; disagreement isolated to a non-primary
secondary dimension may be `DIAGNOSTIC`.

## 3. T0 — Study preregistration and freeze

### Purpose and entry authority

T0 instantiates the accepted architecture as one frozen study registration
before ordinary work begins. Ryan is the study owner and must approve the
registration. The controller verifies completeness mechanically. **No Agent A
may begin before T0 freeze verification passes.**

### Required T0 content

The `StudyFrame` and `T0FreezeManifest` form one atomic, content-addressed
configuration and must instantiate, without leaving an implicit choice to a
later actor:

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
- the structured result tuple, complete-pair estimator, bounded score support,
  deterministic missing-outcome bounds/sensitivity procedure, zero-target
  handling, and prohibition on an authoritative scalar;
- separate natural-capture, per-arm trial-evidence-capture, and per-arm
  score-evaluability axes;
- fixed reason taxonomy distinguishing valid missing outcomes from protocol,
  environment, isolation, lineage, registry, freeze, and scorer-integrity
  invalidity;
- orthogonal protocol validity, information sufficiency, missingness/
  comparability, scorer integrity, and scorer reliability records, plus
  final-disposition precedence;
- paired sealed-state replay, reset/isolation, mutable external-service,
  execution-order, and scorer-presentation-order policies;
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

A structural validator must consume the canonical serialized bytes, reject
missing or placeholder content even when status flags claim completion, and
re-derive the digest independently of orchestration. Shared canonical
serialization and hash primitives are allowed; stage builders and
capture/execution/scoring modules are not. A second responsible role verifies
that the exact serialized artifact handed downstream matches the logged freeze
digest and that forbidden natural corpus/index paths are mechanically
unreachable. Execution entry points refuse to resolve without the valid,
append-only-logged digest.

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

## 4. T1 — Natural episode collection

### Purpose and operating rule

T1 executes only the prospectively selected ordinary-work episodes in the
frozen schedule. It retains every selected episode, including boring episodes,
episodes with no temporal change, and episodes later found to have zero
eligible targets. No replacement episode may be substituted because a result
looks uninteresting or unfavorable.

The recorder captures the complete admissible ordinary evidence defined by T0:
conversation/transcript events, tool calls and outputs, files/notes created in
ordinary work, repository state, GitHub-visible state, and explicitly allowed
source metadata. Capture-time and event-time are distinct fields.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| Frozen `StudyFrame` and selected schedule | Immutable `EpisodeRecord` for every selected episode | `episode_id`, frame digest, schedule position, start/end timestamps, environment/session identity, recorder identity, terminal state |
| Ordinary episode sources and permitted snapshots | `RawEvidenceManifest` plus immutable source copies/references | Source ID/class/locator, content digest, byte/record count where applicable, event/capture bounds, repository/GitHub/filesystem identity, producer/tool identity, completeness status, manifest digest |
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

## 5. T2 — Blind complete target census

### Purpose and access boundary

T2 discovers and adjudicates the complete natural target census from the sealed
raw evidence. Two independent adjudicators each review the complete evidence
view and frozen rules, independently enumerate/adjudicate candidates, and
submit before seeing the other decision. The ConvMem store, capture state,
retrieval traces, target-specific search results, C0/C1 outcomes, treatment
order, and downstream scores are unread and uninspected for census decisions.

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

- **Third-adjudicator path:** a third person sees the raw evidence, rules, and
  the two submitted decisions but not treatment/result material, then records
  the resolution; or
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

T2 stops as `INVALID` for access or seal violations, `DIAGNOSTIC` for identity
or evidence-recording failures, and `BLOCKED / NON-ESTIMABLE` if valid evidence
cannot support a target-bearing/evaluable set. None of these states authorizes
probe construction against an unsealed registry.

## 6. T3 — Census/sample freeze

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

## 7. T4 — Probe and scoring-key construction

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

The controller forks C0 and C1 from one sealed pre-trial state and
mechanically proves that they receive the same:

- sealed raw evidence and ordinary files;
- repository, GitHub, filesystem, readable-root, and network policy;
- model, build, prompt/settings, budget, stopping rules, and tool versions;
- context gap, probe, scoring policy, and session initialization;
- execution manifest and allowed ordinary tools.

The pair shares no mutable conversational/session state, writable cache,
database row, rate-limit state, or cross-arm artifact. Time-varying external
services are snapshotted/replayed identically or excluded. Execution-order
randomization is frozen independently of scorer-presentation order.

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
| External-state/reset policy | `ReplayIsolationReport` | Sealed pre-trial-state digest, per-arm reset evidence, cache/database/external-service comparison, exclusion reasons, verifier identity |

### Invariants, negative tests, and stop condition

- Any C0/C1 tool, readable-root, network, model, budget, prompt, gap, or
  stopping-rule difference other than ConvMem availability is a qualification
  failure.
- Any shared mutable state, non-replayed external dependency, or cross-arm
  carryover is an environment-invalidity failure, not a missing outcome.
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

### Required terminal and evaluability records

Each selected trial ends as one explicit state and a separate arm-level
evidence-capture/evaluability record, for example:

- `TRIAL_COMPLETE` — final output and trace are complete;
- `TRIAL_AGENT_FAILURE` — Agent B failed or stopped under the frozen rule;
- `TRIAL_TOOL_FAILURE` — an allowed tool failed, with trace;
- `TRIAL_INSTRUMENTATION_FAILURE` — capture/controller evidence is incomplete;
- `TRIAL_PROTOCOL_INVALID` — an invariant was violated.

These trial states do not rewrite target eligibility or turn missing evidence
into a zero-target episode.

The frozen reason taxonomy classifies `TRIAL_AGENT_FAILURE` or
`TRIAL_TOOL_FAILURE` as boundable outcome missingness only when the pair passed
all protocol/environment/isolation checks and the rubric defines a latent
bounded score. `TRIAL_PROTOCOL_INVALID`, wrong environment, shared state,
scorer unblinding, registry mutation, or lineage/freeze mismatch is invalid,
never boundable.

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

T7 records protocol validity, per-arm capture/evaluability, and reason codes.
Invalid pairs stop before scoring; valid missing outcomes remain for T9 bounds.
It does not authorize reruns chosen for favorable outcomes.

## 11. T8 — Blinded scoring

### Scoring and reliability rule

Two independent scoring roles score the complete eligible/evaluable target set
from structurally identical, condition-neutral packages. Condition names,
session/episode IDs, filenames/paths, latency, tool counts, raw tool traces,
retrieval-only blocks, and other condition-correlated form or metadata are
stripped or symmetrically normalized. Pair presentation order is randomized
under its own frozen seed. If an LLM scores, transcript content is untrusted
input isolated from scoring instructions, and calibration/study contexts are
disjoint. Each scorer uses the sealed key and frozen rubric and submits before
seeing the other's decisions. Disagreements are resolved by the frozen blinded
third scorer or consensus procedure.

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
| Sealed key/rubric; blinded trial records; raw evidence required by rubric | Independent `TargetScoreSet` and `EpisodeScoreSet` | Score version, scorer IDs, condition-neutral package/transform digest, randomized presentation-order identity, trial/probe/target/episode IDs, key/rubric digests, score and reliability states |
| Second scorer and resolution role | `ScoringReliabilityReport` | Agreement counts, scale/statistic identity, gate value, resolution records, scorer-role identities, report digest |
| Frozen sparse rule | Sparse disposition report | Evidence basis, episode reliability states, inclusion/disposition rule, no-result-change attestation |

### Invariants, negative tests, and stop condition

- A scorer who sees condition labels, treatment order, capture status,
  condition-correlated form/metadata, or future results invalidates the
  affected scoring generation; this is not score missingness.
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

### Co-primary B — complete-pair effect and missing-outcome bounds

For each target-bearing episode with valid, score-evaluable outcomes in both
arms, use exactly one bounded normalized within-episode continuation-utility
score for C0 and one for C1, then form the paired C1−C0 episode contribution
under the T0 estimator. Raw target count cannot determine episode weight.

Every target-bearing episode has one immutable `episode_opportunity_id` linked
to its registry rows. Every such episode without a complete valid pair remains
in the denominator ledger. Target rows are secondary inputs to the frozen
within-episode aggregation rule, not additional primary denominator units.
Report C0 and C1 trial-capture and score-evaluability rates
separately, with frozen mutually exclusive reasons. Apply the deterministic
worst/best-case or prospectively frozen sensitivity procedure only to valid
missing outcomes over the frozen score support. Report the complete-pair
estimate and bounds together; if the bounds span the frozen decision region, the
missingness/comparability state is inconclusive rather than a product null.

The report must display episode count, target-bearing/evaluable count, sparse
reliability states, incomplete/ambiguous counts, paired contribution coverage,
and target-level secondary diagnostics. Zero-target episodes remain visible in
co-primary A and do not receive an invented treatment score in co-primary B.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| T1 EpisodeFrame/records; T2 registry; T3 census/sample | Opportunity analysis input | Frame, episode roster, registry/sample digests, zero-target and incomplete-state counts |
| T7 validity/capture/evaluability ledger; T8 accepted scores and reliability report | `EpisodeAggregationReport` | Registry denominator digest, per-arm rates/reasons, score-set digest, one-score-per-episode proof, complete-pair estimator, bounds/support identity, reliability result |
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
- Invalid trials cannot receive latent scores or enter the bounds calculation.
- A tolerance alarm cannot replace the frozen bounds procedure or silently
  suppress a decision-informative bound.

T9 emits analysis artifacts and intervals, never a product disposition. It
stops `INVALID` for post-result estimator or membership changes,
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
- treatment of ties, valid missing pairs, bounds, and invalid terminal states;
- orthogonal-state reason taxonomy and precedence.

No threshold, margin, confidence rule, sparse rule, or inclusion rule may be
adapted because the results are sparse, unfavorable, or inconvenient. There is
no extension of the observation window after results are seen.

### Derived terminal interpretations

The controller derives the disposition in this order: protocol/isolation/
lineage/registry/freeze invalidity; environment or scorer-integrity invalidity;
insufficient opportunity/information; valid missingness with inconclusive
bounds; only then effect interpretation.

- `COMPLETE — POSITIVE`: valid co-primary analysis meets the frozen meaningful
  positive criterion and information/precision rule.
- `COMPLETE — NULL / EQUIVALENT`: valid analysis is sufficiently informative
  under the frozen null rule to exclude the meaningful-advantage interval.
- `COMPLETE — NEGATIVE`: valid analysis meets the frozen criterion favoring C0.
- `BLOCKED / NON-ESTIMABLE`: valid evidence is insufficient or valid
  missing-outcome bounds are inconclusive; exact reason codes are required.
- `DIAGNOSTIC`: an allowed diagnostic/secondary measurement is unavailable
  without invalidating the primary evidence; exact reason codes are required.
- `INVALID`: a protocol, isolation, environment, lineage, registry, freeze, or
  scorer-blinding invariant was violated. Invalid evidence is never bounded.

The final report contains the structured tuple: opportunity prevalence,
complete-pair effect plus bounds, and full capture/evaluability/failure
accounting. Any opportunity-weighted scalar is explicitly secondary, names its
transportability or zero-contribution assumption, and cannot replace the tuple.

### Inputs, outputs, and identity requirements

| Input authority | Output artifact | Required identity binding |
|---|---|---|
| T0 parameter registry; T9 aggregation; reliability reports | `InformationGateReport` | Every parameter digest, estimator/score version, data/lineage digest, gate calculation, analysis owner ID |
| Frozen state/reason/precedence rule | `StudyDisposition` | Orthogonal states, exact derived label and reason codes, precedence path, unresolved diagnostics, report digest, no-adaptation attestation |

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
| G4 Landed analysis/statistical baseline | Existing bounded episode scores, sparse/reliability records, aggregation, and information slots; this landed baseline is not re-granted by the amendment | G1; prior grants | Existing synthetic fixtures | New corrective mechanics, product conclusion, real scoring |
| G5C Corrective implementation and dry-run | Make only the changes to landed G1–G4 machinery required for structural completeness, immutable opportunity authority, separate capture/evaluability axes, valid-vs-invalid classification, deterministic bounds, orthogonal state/reason precedence, paired replay, and an individual T0–T10 boundary ledger; then rerun corrected G5 | Kiro-reviewed amendment; separate Ryan implementation grant | Independent corrected-scope G5 PASS report at exact revision; synthetic evidence only | Prospective freeze, live parameter values, Agent A/B, natural corpus/index, live ConvMem, scoring, product conclusion |
| G6 Actual prospective study freeze | Ryan instantiates and approves T0 values, roles, schedule/window, environments, order, parameter slots, and terminal rules | Corrected G5C PASS; Kiro plan review; fresh Ryan authorization | `FRAME_FROZEN` and T0 verification | Agent A before gate; no result collection |
| G7 Agent-A episode execution | Collect only the selected ordinary episodes and seal raw evidence | G6 | T1 complete episode/evidence bundle | Replacement episodes, target selection, B trials |
| G8 Target census | Two independent adjudicators complete and seal the raw-evidence census; resolve disagreements | G7 | T2 sealed `TargetRegistry` and quality report | Probe construction before seal; capture-based decisions |
| G9 Census/sample, probe, capture, and C1 readiness | Apply T3; construct/review T4 probes; freeze T5 natural snapshot; qualify T6 | G8; staged sub-gates | Sample/probe/key/capture/environment manifests | Target-directed recapture; B execution before T6 PASS |
| G10 Agent-B paired execution | Run both fresh conditions for the selected pairs with complete traces | G9/T6 PASS | T7 execution bundle and terminal roster | Controller answers/searches; reused context; replacement trials |
| G11 Scoring and analysis | Blind T8 scoring/reliability, T9 aggregation/bounds, T10 information/null gate | G10 | Structured result tuple and allowed derived disposition | Threshold changes, scalar headline, product claim before gate |

Cursor may receive only a bounded grant naming one row and its exact output
contract. Ryan owns the transition from implementation/dry-run grants to G6–G11
live study grants. Codex does not send work to Cursor from this plan.

`G5C` is one bounded corrective grant over the landed baseline; it is not a
retroactive G4 grant and does not reopen unrelated G1–G4 scope. Its internal
`StageBoundaryLedger` must record, for each individual T0 through T10 boundary,
the canonical input digest, required predicates, output digest, validator
result, and next-stage assumptions. The existing grouped `T0_T2`, `T3_T5`,
`T6_T7`, and `T8_T10` statuses may remain as summaries only; they cannot be the
sole evidence for composition.

## 15. Reuse and new-component implementation map

The map is a planning boundary, not authorization to edit these modules.

| Study need | Reuse or new component | Boundary and required proof |
|---|---|---|
| Immutable ConvMem/corpus snapshot | Reuse `eval_corpus/capture.py` and `serving_index_repository.py` | Reuse capture/manifest and serving-generation identity; bind to the study generation; never make Chroma or a serving projection target authority |
| Existing indexing anchors | Reuse `inter_model_index.py` and `serving_index_repository.py` where ordinary indexing/serving mechanics apply | Verify source/projection identity and writer boundaries; no target-directed indexing or registry mutation |
| Retrieval/provenance diagnostics | Reuse `ask.py`, `query.py`, and existing trace interfaces | Diagnostics only; raw evidence and TargetRegistry remain authoritative |
| Latency harness | Reuse `eval_corpus/runner.py` latency conventions | Add the study's ordinary-work action taxonomy and controller-exclusion proof; do not claim an action counter module exists |
| Paired statistics and runner conventions | Reuse `eval_corpus/paired_stats.py` and `eval_corpus/runner.py` | Extend only behind the episode-level, unequal-target, zero-state, reliability, and margin contracts |
| Raw evidence recorder/controller | Historical v3 controller event/reply/raw-file conventions | Historical/to-be-relocated foundation; the exact current implementation path must be verified during G1/G5C before live use |
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
| T0 | Accepted architecture; Ryan registration; environment/workload evidence | Atomic serialized manifest, role/schedule/parameter records, logged/re-derived digest, isolation report | Structural content complete; no placeholder/status shortcut; exact handed artifact; execution refuses absent freeze | Partial frame; placeholder marked complete; post-freeze tamper; handed-artifact mismatch; mounted forbidden study path | `INVALID / NOT STARTED`, integrity incident, or `BLOCKED` |
| T1 | Frozen frame/schedule; ordinary work | Episode records and complete raw manifests with source/session/snapshot digests | Every selected episode retained; completeness explicit; no ConvMem-based retention | Replace boring episode; omit zero-opportunity episode; mark partial manifest complete | `DIAGNOSTIC` / `BLOCKED` |
| T2 | Sealed raw evidence; frozen rules | Two full adjudication sets, blinded resolution, registry and quality report digests | Mechanical seam decisions; raw-only; one episode row each; registry one-way seal | Capture-dependent exclusion; unsealed target edit; single-assessor shortcut; duplicate drift | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T3 | Sealed registry; T0 sample rule | Census acceptance or episode sample manifest; seed, probabilities, unsampled digest | Census if feasible; whole-episode sampling; zero rows preserved; no discretionary picking | Target-rich episode overweight; manual target pick; missing zero-target episode | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T4 | Sealed registry/sample; T0 probe families | Probe/key/leakage manifests and digests; role IDs | Realistic task; author knows boundary honestly; author ≠ adjudicator; separate key/reviewer | Answer/paraphrase/path/location leakage; treatment/ConvMem cue; identity collision | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T5 | Sealed probes/sample; normal ConvMem state | Capture-state map and immutable C1 snapshot manifest | Natural capture only; uncaptured targets retained; registry unchanged | Target-directed reindex; recapture; capture-based deletion; mutable snapshot | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T6 | T0 replay/isolation/order policy; T4/T5 packages | Sealed-state comparison, fresh-session/reset proof, external-state report, execution-order digest | Same state/tools/model/gap/budget/external replay; only C1 ConvMem; no shared mutable state | Tool/root mismatch; reused session/cache/DB row; non-replayed service; controller acts as B | `INVALID`, or pre-execution `BLOCKED / NOT STARTED` |
| T7 | Qualified packages/order; selected probes | Full paired traces plus per-arm validity/capture/evaluability/reason ledger | Fresh pair; no replacement; missingness distinct from invalidity | Protocol failure labeled missing; missing trace silently repaired; condition-specific retry | `INVALID`, valid missing outcome, or explicit diagnostic |
| T8 | Condition-neutral trial packages; sealed key/rubric | Independent scores, presentation-order/transform digest, reliability report | Structurally matched packages; independent randomized order; frozen reliability; untrusted-content boundary | Condition-correlated form/metadata; scorer prompt injection; calibration context overlap; below-gate verdict | `INVALID` / `DIAGNOSTIC` / `BLOCKED` |
| T9 | Fixed registry denominator; T7 validity/evaluability; accepted scores | Opportunity report, per-arm process accounting, complete-pair estimate, deterministic bounds | Every opportunity accounted; invalid evidence excluded from bounds; no target-count weighting | Drop asymmetric failures; bound protocol invalidity; tolerance-only cliff; missing zero rows | `INVALID` / `DIAGNOSTIC` / bounded or inconclusive result |
| T10 | Frozen parameter/state/reason/precedence registry; T9 outputs | Structured result tuple and derived disposition with full lineage | Precedence applied before effect; no scalar headline; no threshold adaptation | Product verdict after protocol/scorer failure; generic sink; post-result rule change | `INVALID` / `DIAGNOSTIC` / `BLOCKED` or complete label |

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
15. **Incomplete nominal T0_T2 frame:** begin from a schema-verified fixture in
    which every prospective slot is explicitly `PENDING`; populate only a
    subset and verify `run_g5_end_to_end()` fails before T0_T2 success.
16. **False completeness flag:** mark an empty/placeholder slot complete;
    verify serialized-content validation rejects it despite the status flag.
17. **Stage-local corruption sweep:** corrupt each T0–T10 stage input in turn;
    verify that stage fails closed and no later stage repairs, ignores, or
    replaces the missing guarantee.
18. **Boundary composition proof:** on the full happy path, assert at every
    boundary that the prior output actually satisfies each guarantee the next
    stage assumes, rather than asserting only a success return value.
19. **Freeze/hand-off tamper:** alter serialized bytes after freeze or hand the
    second validator a different artifact; verify digest mismatch, execution
    refusal, and integrity-incident handling.
20. **Arm/result-dependent opportunity rule:** make registry membership consult
    arm, capture, retrieval, or C0/C1 outcomes; verify manifest or lifecycle
    validation rejects it before execution.
21. **Asymmetric valid missingness:** create different C0/C1 trial-capture or
    evaluability rates; verify every registry row remains, per-arm rates and
    reasons are reported, bounds are deterministic, and an effect is emitted
    only when the frozen decision rule permits it.
22. **Invalid-versus-boundable separation:** inject an environment/isolation/
    freeze failure and a valid missing outcome; verify only the latter enters
    bounds and invalidity wins disposition precedence.
23. **Disposition precedence:** combine protocol invalidity, sparse
    information, scorer failure, and an apparently positive effect; verify the
    derived result follows the frozen precedence and retains every reason.
24. **Paired-replay mismatch:** vary a readable root, shared cache/database
    state, mutable external-service response, or execution order after freeze;
    verify qualification rejects the pair before scoring.

The G5 corrective also requires an import-boundary check showing that the T0
structural validator does not import execution, capture, or scoring modules.
The validator may share only canonical serialization/schema identifiers and
the cryptographic digest primitive. All scenarios remain synthetic-only.

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
| Bounded score support and decision-informative-bounds criterion | T0 before Agent A | Rubric range proof, synthetic behavior under missingness patterns, and product decision region | Ryan after Kiro methodology review | Estimand/inference-defining |
| Any capture/evaluability asymmetry alarm or sensitivity parameter | T0 before Agent A | Synthetic missingness qualification and evidence independent of live outcomes | Ryan after Kiro methodology review | Interpretation-defining; not an estimator cliff |
| Failure/reason enum and orthogonal-state precedence | T0 before Agent A | Synthetic coverage of every boundable, invalid, diagnostic, sparse, scorer, and environment branch | Ryan after Kiro review | Protocol/interpretation-defining |
| Paired replay and external-service acceptance policy | T0 before Agent A | Adversarial qualification showing fresh state, no carryover, and repeatable external evidence | Ryan after Kiro environment review | Identification-defining |

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
9. Does T9 preserve the sealed registry denominator, report per-arm capture and
   evaluability, compute the complete-pair effect and deterministic bounds for
   valid missing outcomes, and exclude invalid trials from bounds?
10. Does T10 derive dispositions from orthogonal states and exact reasons in
    the required precedence, prevent a generic non-estimable sink, and prohibit
    an authoritative scalar or effect verdict after an invalidity?
11. Are G1–G11 separately grantable, with Ryan authorization required before
    live T0, Agent A, census, Agent B, scoring, or analysis work?
12. Are every reuse-map path and every historical/to-be-relocated claim
    accurately labeled at the corrected architecture tip?
13. Does corrected G5 cover the original incomplete-frame composition defect,
    false completeness flags, every-stage corruption, boundary guarantees,
    validator tamper, arm-dependent registry rules, asymmetric missingness,
    invalid-vs-boundable separation, precedence, and replay mismatch?
14. Does any remaining choice now constitute a genuine construct-level conflict
    requiring Sol, or can the choice remain a bounded later Ryan/Kiro decision?
15. Is the state machine's distinction between editable incompleteness and a
    post-freeze integrity incident sufficient and mechanically testable?
16. Do scorer-package normalization and untrusted-transcript controls prevent
    condition disclosure without removing task content needed by the rubric?

## 19. Review and authorization sequence

```text
Corrective architecture/execution amendment (Codex) — this revision
        ↓
Kiro exact-revision architecture/execution review
        ↓
Ryan amendment acceptance or bounded correction request
        ↓
Separate Ryan grant for bounded G5 corrective implementation, if accepted
        ↓
Corrected G5 synthetic PASS and independent review
        ↓
Fresh Ryan decision on any G6/T0 planning grant
```

No branch, plan, or dry-run PASS is an implicit grant to run Agent A/B or
collect natural episodes. The live study remains review-required.

## 20. Exit criteria for this planning lane

- [x] Ryan accepted D1–D6 as corrective design direction.
- [x] Architecture and execution amendments incorporate D1–D6 without choosing
      live parameter values.
- [x] Architecture and execution amendments are co-versioned for one exact
      Kiro review revision.
- [x] T0–T10 stages specify authority, artifacts, identities, invariants,
      negative tests, and stop dispositions.
- [x] Grant decomposition separates methodology, adjudication, probes,
      analysis, dry-run, freeze, Agent A, census, Agent B, and scoring/analysis.
- [x] Reuse/new-component map identifies verified anchors and obsolete paths.
- [x] Corrected G5 verification includes the original incomplete-frame defect,
      structural validation, full-stage corruption/composition, tamper,
      asymmetric missingness/bounds, invalidity separation, precedence, and
      replay mismatch.
- [x] Numerical/product-contract choices remain explicitly unresolved with
      evidence, authority, freeze point, and construct status.
- [ ] Kiro independent execution-plan review.
- [ ] Ryan execution-plan acceptance.
- [ ] Any implementation or live-study grant.

**Next sequence:** Kiro exact-revision corrective review → Ryan
acceptance/revision decision → only then a separately authorized bounded G5
implementation slice. Gate remains C; G6/T0 remains closed.
