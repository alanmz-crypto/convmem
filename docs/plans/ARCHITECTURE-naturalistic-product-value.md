# Architecture Direction — Naturalistic ConvMem Product-Value Study

> **CORRECTIVE DESIGN ACCEPTED — IMPLEMENTATION NOT AUTHORIZED.** Kiro PASSed
> the co-versioned architecture/execution package at exact `b6a1ccf`; its two
> wording-only corrections are `fde840b`. Ryan accepted that corrected design
> on 2026-08-30. This acceptance authorizes no G5C implementation, parameter
> selection or freeze, Agent A/B run, natural evidence access, target-registry
> population, G6/T0 transition, corpus mutation, scoring, or product conclusion.
>
> **Arc:** Naturalistic ConvMem product-value evaluation
>
> Protocol v3 is closed at `RERUN3 V3 FAILURE PUBLISHED` (closure SHA
> `9ba7237`). Its K1–K10 seed-construction evidence remains protocol-feasibility
> evidence only and is not part of this study.

## 1. Product question and consequence

The study asks:

> Does adding ConvMem improve meaningful recovery and continuation performance
> during ordinary ongoing work, relative to the same fresh agent with the same
> ordinary evidence and tools but without ConvMem?

The unit of natural work is a prospectively selected **episode**. The unit of
memory opportunity is a naturally arising **target** discovered from complete
ordinary evidence after Agent A work. The product comparison is C1 (normal
ConvMem availability against a frozen study snapshot) versus C0 (the same
ordinary environment without ConvMem).

The architecture therefore separates three questions that the old controlled
seed protocol combined:

1. Did ordinary work produce an eligible recovery opportunity?
2. Did normal ConvMem capture and retrieve the opportunity?
3. Did fresh Agent B use the available information to continue the work
   correctly, currently, and with adequate provenance?

Only the third question is the product-value comparison. The first two are
preserved as upstream and component diagnostics, never as eligibility gates.

## 2. Scope and non-goals

### In scope

- prospective episode-frame definition and retention;
- complete timestamped raw-evidence preservation;
- natural target eligibility, unitization, and blinded adjudication;
- sealed target census and reproducible sampling;
- leakage-safe continuation/recovery probe construction;
- natural-capture classification after registry sealing;
- fresh, symmetric C0/C1 execution against a frozen ConvMem snapshot;
- episode-primary and target-secondary outcome records;
- zero-target, sparse, null, positive, negative, diagnostic, and invalid states;
- immutable identity and provenance from ordinary work to final result;
- verification gates for a later implementation.

### Out of scope

- changing ConvMem capture, retrieval, ranking, or storage behavior;
- another Protocol-v3 instance or any K1–K10 seed construction;
- JudgeBench as a target universe;
- specially rewriting, tagging, routing, indexing, or manufacturing notes for
  selected targets;
- product promotion, merge authority, or ledger decisions;
- a microservice split. This is a study-methodology boundary inside the
  existing local system.

## 3. Architectural principles

1. **Episode-first denominator.** The selected episode frame is fixed before
   outcomes. Every selected episode remains represented, including zero-target
   episodes.
2. **Raw evidence is study truth.** Target membership comes only from complete,
   timestamped ordinary evidence and predeclared rules. Chroma and retrieval
   traces are derivatives and diagnostics.
3. **Capture is not eligibility.** An eligible target remains in the registry
   when ConvMem fails to capture it.
4. **Freeze before exposure.** Every artifact that can affect eligibility,
   sampling, probing, or scoring is sealed before the downstream result that
   could bias it exists.
5. **Separate outer results.** Target capture, retrieval, Agent-B uptake, and
   episode continuation are distinct records; no single status hides the
   failure stage.
6. **Primary aggregation is episode-level.** Target-rich episodes cannot gain
   more primary weight merely by producing more target rows.
7. **Zero is a real state.** Zero eligible targets, missing evidence, failed
   adjudication, capture failure, and Agent-B failure are different states.
8. **One local authority.** The study controller orchestrates a state machine;
   it does not become a second source of truth or a second agent surface.
9. **Complete-census adjudication.** Every candidate in the complete target
   census receives two independent adjudications from raw evidence. Disputes
   are resolved by a blinded third adjudicator or a predeclared blinded
   consensus procedure, and disagreement is retained as a registry-quality
   metric.
10. **Reliability is explicit.** Sparse episode evidence and scorer
    disagreement produce visible reliability states. They cannot silently
    receive the confidence of well-supported episodes or yield a product
    verdict without passing the frozen reliability gate.
11. **The registry is the opportunity authority.** The sealed
    `TargetRegistry`, derived only from Agent-A raw episode evidence under the
    frozen adjudication rule, is the sole denominator ledger. Later capture,
    execution, evaluability, or scoring records reference it but cannot change
    its membership.
12. **Missingness is observed, not discarded.** Natural ConvMem capture,
    per-arm trial-evidence capture, and per-arm score evaluability are separate
    axes. Valid-but-missing outcomes remain in the fixed opportunity
    denominator and enter the frozen bounds procedure.
13. **Invalidity is not missingness.** Protocol, isolation, environment,
    lineage, registry-mutation, or scorer-blinding failures invalidate the
    affected trial or study. They are never assigned latent scores or bounded
    away.
14. **No authoritative scalar.** The first naturalistic study reports a
    structured product-result tuple: opportunity prevalence, complete-pair
    effect with bounds where needed, and full capture/evaluability/failure
    accounting. Any scalar is secondary and assumption-dependent.
15. **Paired replay has one intended difference.** C0 and C1 start from one
    sealed pre-trial state in fresh sessions with mechanically compared
    environments. The only intended treatment difference is C1 access to the
    frozen ConvMem surface.

## 4. Lifecycle state machine

The study is an append-only sequence of frozen artifacts. A later state may
read an earlier artifact but may not rewrite it. Orchestration success is not
evidence of content completeness: every transition is established from the
serialized artifact against the frozen schema and policy. Before freeze,
incompleteness remains in or returns to `FRAME_DRAFT`. After freeze, no
in-place rollback exists: a permissible correction requires a new generation,
while a digest mismatch, handed-off-artifact mismatch, isolation breach, or
registry mutation is an integrity incident.

```text
FRAME_DRAFT
    │ frame + policies frozen before ordinary work
    ▼
FRAME_FROZEN ──► OBSERVATION_OPEN ──► EPISODE_EVIDENCE_SEALED
                                           │
                                           ▼
                                  TARGET_ADJUDICATION
                                           │
                                           ▼
                                  TARGET_REGISTRY_SEALED
                                           │
                              ┌────────────┴────────────┐
                              ▼                         ▼
                       CENSUS_ACCEPTED          SAMPLE_SEALED
                              └────────────┬────────────┘
                                           ▼
                                    PROBES_SEALED
                                           ▼
                                    C0C1_READY
                                           ▼
                                  EXECUTION_COMPLETE
                                           ▼
                                  SCORING_LOCKED
                                           ▼
                                  ANALYSIS_READY
                                           │
                                           ▼
                              ORTHOGONAL STATE ASSESSMENT
                                           │
                                           ▼
                               DERIVED FINAL DISPOSITION
```

The assessment record has five orthogonal axes rather than one overloaded
terminal enum:

- `protocol_validity`: valid, invalid, or unresolved;
- `information_sufficiency`: sufficient, sparse, or insufficient;
- `missingness_comparability`: complete, bounded, inconclusive bounds, or not
  applicable;
- `scorer_integrity`: valid, invalid/unblinded, or unresolved;
- `scorer_reliability`: acceptable, below threshold, or not applicable.

The final disposition is derived mechanically in this precedence order:

1. protocol, isolation, lineage, registry, or freeze invalidity;
2. environment or scorer-integrity invalidity;
3. insufficient opportunity or information;
4. below-threshold scorer reliability or valid missingness whose frozen bounds
   are inconclusive;
5. only then, positive, null/equivalent, or negative effect interpretation.

The derived label may use the existing compact vocabulary, but it must carry
machine-readable reason codes and the complete orthogonal state record. A
generic `BLOCKED / NON-ESTIMABLE` label without its reason and precedence path
is not a sufficient study result.

### State authority and transition conditions

| State | Authority | Required transition evidence |
|---|---|---|
| `FRAME_FROZEN` | Ryan-approved study owner | One atomic manifest passes structural validation, is hashed from canonical serialized bytes, and is append-only logged before execution can resolve. |
| `OBSERVATION_OPEN` | Mechanical controller | Only prospectively selected episodes are observed; no replacement episodes. |
| `EPISODE_EVIDENCE_SEALED` | Evidence recorder/controller | Complete raw-source manifest, timestamps, hashes, and snapshot identities exist. |
| `TARGET_ADJUDICATION` | Blind target assessor(s) | Assessor access excludes ConvMem capture/retrieval and C0/C1 results. |
| `TARGET_REGISTRY_SEALED` | Study owner after audit | Every episode has a census entry, including explicit zero-target entries. |
| `CENSUS_ACCEPTED` / `SAMPLE_SEALED` | Mechanical sampler | Census or fixed probability sample is reproducible and unsampled rows remain. |
| `PROBES_SEALED` | Probe author + study controller | Probe, acceptable response, scoring key, and leakage audit are frozen. |
| `C0C1_READY` | Mechanical controller | One sealed pre-trial state has two fresh replay packages; mechanical comparison proves the only intended difference is C1 ConvMem access. |
| `EXECUTION_COMPLETE` | Mechanical controller | Fresh paired sessions, frozen randomized execution order, complete per-arm evidence/capture/evaluability records, and terminal statuses exist. |
| `SCORING_LOCKED` | Blinded scorer | Structurally matched, condition-neutral packages and randomized presentation order are scored without condition-correlated metadata or form. |
| `ANALYSIS_READY` | Analysis owner | Identity chain, orthogonal states, complete-pair estimate, missingness bounds, reason codes, and all frozen information gates are present. |

`ZERO_ELIGIBLE_TARGETS` is an episode status inside the sealed registry, not a
study failure. It has no C0/C1 target trial unless the approved probe family
defines a target-independent continuation task.

## 5. Authority and role boundaries

| Role | May read | May write | Must not do |
|---|---|---|---|
| **Study owner / Ryan** | All study artifacts and review reports | Frame/policy approval and final study disposition | Change frozen artifacts after exposure; delegate merge authority. |
| **Study controller** | Manifests, mechanical run state, environment metadata | State transitions, hashes, run records | Act as Agent B, select targets, edit probes, or add context. |
| **Structural freeze validator** | Canonical serialized manifest bytes and frozen schema/policy | Independent validation report and re-derived digest | Trust orchestration success, consume mutable builder objects, import execution/capture/scoring modules, or repair the manifest. |
| **Raw-evidence recorder** | Ordinary Agent-A outputs and permitted source metadata | Immutable raw-evidence manifest and source copies | Filter for interesting content or inspect ConvMem success to decide retention. |
| **Target adjudicator A/B** | Complete raw evidence and versioned eligibility rules | Independent target census decision, rationale, ambiguity status, strata labels | Read ConvMem capture/rank, C0/C1 outputs, or expected treatment advantage; see the other adjudicator's decision before submitting. |
| **Probe author** | The sealed target record and the minimum raw context needed to construct a realistic task, plus predeclared probe families | Probe definition; submits the scoring key to a separately sealed scorer partition | Claim answer blindness; read ConvMem search results, capture labels, condition outcomes, treatment order, or scorer decisions; author a target they adjudicated. |
| **Leakage reviewer** | Frozen probe, the author-visible target/context view, and the leakage checklist; no ConvMem or outcome material | Independent leakage review/sign-off before probe freeze | Be the probe author or target adjudicator for that target; reveal answer or source/treatment/ConvMem cues to Agent B. |
| **Agent-B executor** | Ordinary files/repository/GitHub/transcripts, assigned probe, normal tools; C1 additionally has frozen ConvMem | Agent-B transcript, actions, output, and trace | Read registry, answer key, controller internals, or an earlier Agent-B session. |
| **Scorer** | Frozen Agent-B outputs, raw evidence, sealed rubric/key, bounded traces | Target and episode scores | Change scoring rules after seeing condition labels or use retrieval rank as truth. |
| **Analysis owner** | Sealed registry, valid trial/evaluability records, masked scores, and frozen analysis contract | Structured result tuple, bounds, orthogonal states, and derived disposition | Change registry membership, classify protocol failures as missing outcomes, or choose a favorable scalar or threshold. |
| **Scoring dispute resolver** | The same condition-neutral package and sealed rubric supplied to initial scorers | Blinded resolution record | Be either initial scorer, see condition identity, or use capture/retrieval metadata to break a tie. |
| **Kiro** | Architecture and review evidence | Design-review verdict and required revisions | Implement runtime or experiment code. |
| **Codex** | Existing plans and methodology evidence | Architecture draft | Run Agent A/B or authorize implementation. |
| **Cursor** | Only after Ryan acceptance | Future implementation | Start from this draft without the acceptance gate. |

Two independent adjudicators operate over the complete candidate census. They
submit decisions separately, without seeing the other's work, and use the same
frozen admissibility procedure in §8. A disagreement is resolved only by a
third blinded adjudicator or by a blinded consensus procedure that was named
and frozen before adjudication. The registry retains both original decisions,
the resolution, the disagreement reason, and agreement/disagreement rates by
eligibility seam. This is a registry-quality metric, not a reason to reduce
the census to one assessor plus an audit.

The probe author is not answer-blind in the fictional sense: seeing the sealed
target record and the minimum raw context needed to construct a realistic task
necessarily permits knowledge of the underlying target content. The safety
boundary is instead that the author cannot expose that content or any
treatment/memory cue to Agent B, and cannot author a probe for a target they
adjudicated. A separate leakage reviewer must sign off every target-specific
probe before freeze. The reviewer and author remain blind to ConvMem capture,
retrieval, treatment order, future C0/C1 outcomes, and downstream scores.

## 6. Prospective episode frame

`EpisodeFrame` is a versioned, hashed artifact frozen before ordinary work.
It contains:

- study ID and frame version;
- ordinary-work population/type and inclusion/exclusion rules;
- episode count or fixed observation window;
- context-gap schedule and any event/time trigger rule;
- model, prompt, tool, network, readable-root, and environment manifest;
- raw-evidence retention policy;
- C0/C1 treatment assignment and counterbalance rule;
- predeclared outcome families, scoring roles, information thresholds, and
  sampling policy;
- frame digest, creator, approval time, and authority record.

The inclusion rule applies before selection. Once an episode is selected, later
boringness, lack of temporal change, lack of cross-domain material, zero targets,
or apparent lack of ConvMem value cannot remove or replace it. An operational
failure is retained with its status and routed to `DIAGNOSTIC` or
`BLOCKED/NON-ESTIMABLE`, depending on whether product inference remains
possible.

Each episode receives an immutable `episode_id` and an `EpisodeRecord` containing
frame version, selection position, scheduled window, observed timestamps,
environment identity, raw-evidence status, target count, and terminal status.

## 7. Complete raw-evidence layer

After Agent A work, the recorder seals all admissible ordinary evidence before
target adjudication. The evidence set may include conversation/transcript
events, tool calls and outputs, files and notes created during ordinary work,
repository state, GitHub-visible state, and other sources explicitly permitted
by the frozen frame.

`RawEvidenceManifest` binds:

- `episode_id` and source identity;
- source class, path or locator, and admissibility decision;
- content digest and byte/record count where applicable;
- event-time and capture-time bounds;
- repository/GitHub/filesystem/snapshot identity;
- producer/tool identity and provenance fields;
- completeness status and any missing-source explanation;
- manifest digest, seal time, and recorder authority.

The manifest records missing or unavailable evidence explicitly. A partial
manifest cannot be presented as a complete census input. No selected target is
rewritten, retagged, specially routed, specially indexed, or turned into a
study note.

## 8. Natural target eligibility and unitization

An eligible target is a naturally occurring proposition, state, decision,
constraint, preference, commitment, unresolved question, or provenance-bearing
claim in ordinary raw evidence that can be evaluated during a later
recovery/continuation task. Eligibility is determined from raw evidence and
predeclared rules, not from ConvMem output or anticipated treatment advantage.

### Eligibility rules

A candidate is eligible only when all of the following hold:

1. **Ordinary origin:** it exists in an admissible Agent-A source without
   evaluator-authored content or target-directed transformation.
2. **Local support:** one or more immutable source spans support the claim/state
   with enough surrounding context to interpret it.
3. **Identity:** the claim has a stable subject and can be distinguished from
   unrelated or merely stylistic text.
4. **Evaluability:** correctness, currentness, provenance/grounding, or
   continuation relevance can be scored under the frozen rubric.
5. **Non-duplication:** it is not only a repeated rendering of an already
   registered semantic unit.
6. **Non-leakage:** eligibility does not depend on capture, retrieval rank,
   searchability, memorability, or a known C0/C1 result.

The categories above are labels for naturally observed cases, not quotas. A
study does not fail because one or more categories never occur.

### Unitization

- Use the smallest independently scorable proposition or state. Split a
  conjunction when components can differ in truth, currentness, provenance, or
  continuation consequence.
- Merge duplicate mentions with the same semantic claim and validity interval;
  retain all supporting spans and their timestamps.
- Preserve parent/derived relationships when a decision, commitment, or current
  state depends on another registered unit.
- Do not create a target by combining unrelated spans merely because the
  combination would be useful to ConvMem.
- A derived decomposition may clarify a raw target; it may not add information
  absent from ordinary evidence.
- A provenance-sensitive target requires a source identity and the evidence
  needed to judge grounding. A temporal target requires a validity time or an
  explicit `currentness=unknown` status.

### Mechanical admissibility procedure

Each adjudicator applies the following decision tree independently to every
candidate found in the complete raw-evidence view. The decision record cites
the candidate span, the surrounding context used, the applicable rule, and a
yes/no/ambiguous result for each seam; it cannot contain a result-derived or
capture-derived rationale.

1. **Natural origin and local support.** Confirm that the candidate is present
   in an admissible ordinary source and cite immutable supporting span IDs.
   Evaluator-authored text, target-directed transformations, purely stylistic
   text, or a candidate with no locally interpretable support is `INELIGIBLE`.
2. **Stable semantic subject.** Record the subject identity, proposition/state,
   and validity interval needed to distinguish this item from unrelated text.
   If the text is substantive but the subject cannot be resolved from the
   frozen evidence and permitted local context, record
   `AMBIGUOUS_NON_EVALUABLE`; a merely non-semantic fragment is
   `INELIGIBLE`.
3. **Truth/current-state determinability.** Using only frozen raw evidence,
   record whether the proposition/state is supported as true, false,
   superseded, contradictory, or explicitly unknown at the relevant time.
   Cite event times and source spans. An unknown status is admissible only if
   it is itself supported by the evidence and the frozen scoring rubric
   defines how it is scored. Otherwise the candidate is
   `AMBIGUOUS_NON_EVALUABLE`, not silently eligible.
4. **Recovery/continuation evaluability.** Identify a predeclared probe family
   that can ask the later agent to continue or recover the work and identify
   the observable response/artifact that can be scored. If no such mapping can
   be made without adding information or relying on a future result, record
   `AMBIGUOUS_NON_EVALUABLE`.
5. **Ambiguity resolution.** The adjudicator may resolve ambiguity only by
   consulting the frozen raw evidence, its manifest, and the frozen rules.
   If the ambiguity remains after that view, preserve the candidate with the
   ambiguity reason and exclude it from the eligible denominator.
6. **Unitization and duplicate check.** Split independently scorable claims;
   merge repeated mentions only when subject, semantic claim, and validity
   interval match; retain all supporting spans. If unitization cannot be
   completed without an undocumented semantic choice, record
   `AMBIGUOUS_NON_EVALUABLE`.

The final candidate result is exactly one of `ELIGIBLE`, `INELIGIBLE`, or
`AMBIGUOUS_NON_EVALUABLE`. Only `ELIGIBLE` enters the target census count.
`INELIGIBLE` and `AMBIGUOUS_NON_EVALUABLE` remain in the adjudication ledger
with reasons, so discretionary seams cannot silently alter the denominator.
The two independent decisions are compared only after both are sealed; any
disagreement follows the blinded resolution rule above.

Ambiguous candidates are retained in the adjudication record with a reason and
resolution status. They are not silently converted to zero targets or silently
included in the evaluable primary set.

## 9. Outcome-blind adjudication and sealed registry

Each candidate and each selected episode is adjudicated independently by two
identified adjudicators over the complete raw-evidence manifests and the
frozen eligibility/unitization rules. Each adjudicator's view excludes ConvMem
stores, retrieval traces, capture labels, target-specific search results,
C0/C1 outputs, treatment order, and the other adjudicator's pending decision.
Technical access metadata is retained in an audit log. After both decisions
are sealed, disagreements are resolved by the frozen blinded third-adjudicator
or blinded-consensus procedure; neither procedure may consult treatment or
result material.

The sealed `TargetRegistry` contains one episode entry for every selected
episode and, where applicable, target records with at least:

- immutable `target_id` and `episode_id`;
- supporting source/span IDs and evidence manifest digest;
- target value/ground truth partitioned from the executor-visible view;
- target class and naturally observed secondary-stratum labels;
- temporal validity/currentness and provenance requirement;
- eligibility rationale, unitization rationale, and duplicate links;
- both independent adjudication records, adjudication status, ambiguity and
  disagreement record, blinded resolution record, and assessor identities;
- registry policy version, creation time, and registry digest.

The registry is sealed before any target-specific probe is created, sample is
drawn, or C0/C1 execution begins. It is the sole opportunity-denominator
authority. Every later capture, trial, evaluability, score, bound, and failure
record references a registry entry; none may mint, delete, or reclassify one.
Capture status is an additional later field and cannot change membership.

The registry is the authoritative study census. The ledger/raw evidence owns
the ordinary facts; Chroma is a frozen ConvMem treatment projection. No
retrieval result can mint or delete a target.

## 10. Census versus probability sampling

A census is mandatory whenever the prospectively frozen workload ceiling makes
complete adjudication and probing feasible, and is preferred whenever
prospectively feasible. The ceiling and decision rule must be fixed before the
target count is known; it cannot be raised after seeing a favorable roster.

If sampling is allowed by that rule, prefer whole-episode probability sampling
so that the episode-primary estimand keeps episode weight independent of target
count:

- seal the full registry first, including zero-target episodes and unsampled
  targets;
- derive the sampler seed from a precommitted study seed plus immutable study
  and registry identities;
- use a fixed episode sample-size/allocation rule and record the inclusion
  probability for every selected episode and its targets;
- retain the complete unsampled roster and its digest;
- never stratify or oversample on capture status, retrieval success,
  memorability, searchability, semantic interest, or expected C1 advantage;
- make the analysis aware of the sampling design. Individual-target sampling
  is not the default and is permitted only if a prospectively frozen design
  proves that it preserves episode weighting and does not favor target-rich
  episodes.

The execution plan must freeze the exact whole-episode rule, or justify an
alternative probability design, before the registry is observed.

## 11. Leakage-safe continuation/recovery probes

Probe families are specified before Agent A so their purpose and scoring intent
cannot be tuned to observed targets. Target-specific instantiation occurs only
after `TargetRegistry` sealing and any approved sample selection.

The preferred probe is a realistic continuation or recovery task: Agent B must
make a decision, produce an artifact, continue a workflow, or answer a current
work question using ordinary evidence. Direct “what was the fact?” recall is a
secondary diagnostic, not the primary product outcome.

Each `ProbeRecord` binds:

- immutable `probe_id`, `target_id`, and `episode_id`;
- probe-family/version and task context;
- Agent-B-visible prompt and ordinary evidence manifest;
- sealed acceptable-response/behavioral key in a separate scorer partition;
- correctness, currentness, provenance, unsupported-claim, and continuation
  scoring rules;
- target/sample inclusion probability where relevant;
- author, seal time, prompt digest, key digest, and leakage-audit result.

The probe author may read the sealed target record and the minimum raw context
needed for realistic construction. This necessarily means the author may know
the underlying target content; the protocol does not call this answer-blind.
The author may not read ConvMem capture/search output, C0/C1 outcomes,
treatment order, or scorer decisions, and may not author a target they
adjudicated. The Agent-B view contains neither the registry nor the answer key.
The controller must not paste an answer-bearing handoff or target inventory
into either condition.

An independent leakage reviewer, who is neither the probe author nor an
adjudicator for that target, reviews and signs off every target-specific probe
before freeze. The review checks that the Agent-B-visible probe does not reveal
answer content, an answer-bearing paraphrase, a source path, a source-location
hint, a treatment cue, or a ConvMem cue. Any exception because the ordinary
task legitimately exposes information to both conditions must be documented
and frozen before execution. The scoring key remains in a separately sealed
partition whose digest is visible for integrity but whose contents are not
available to the author, reviewer, controller, or Agent B beyond their
declared role.

> **Hard role-separation invariant:** No individual may author the probe for a
> target they adjudicated.

The leakage audit checks at least:

- answer values, answer-bearing paraphrases, source-span text, source paths,
  and source-location hints are not exposed by the probe unless the ordinary
  task legitimately exposes them to both conditions;
- ConvMem, condition, treatment, retrieval-rank, and capture cues are absent
  unless part of the ordinary task;
- no C0/C1 transcript, score, capture label, or retrieval rank was available to
  author, reviewer, or executor;
- the probe asks for a realistic task outcome rather than a memorization
  recital;
- the acceptable-response key was sealed before execution and condition labels
  were masked during primary scoring.

Role separation is required where it prevents information leakage, preserves
zero-discretion mechanics, or controls motivated judgment. Shared canonical
serialization and digest primitives are permitted trusted-kernel components;
completeness and policy validation must remain independent of the builders and
stages whose claims are checked. Different sessions are the minimum
calibration/study scorer separation; different identities or model families
are preferred where practical, but role labels alone do not establish
methodological independence.

## 12. Natural capture and component diagnostics

Normal Agent-A ConvMem behavior is allowed. No target receives special content
rewriting, routing, indexing, note creation, or query treatment. After the
registry is sealed, a diagnostic capture assessor may classify each registry
target against the frozen ConvMem snapshot using a versioned capture rubric.

Capture state is separate from outcome state. Candidate states include:

- `CAPTURED` — ordinary ConvMem material supports the target with traceable
  source identity;
- `ABSENT_FROM_CONVMEM` — eligible raw target has no qualifying captured unit;
- `AMBIGUOUS_CAPTURE` — possible support exists but identity/provenance is not
  determinable;
- `MALFORMED_CAPTURE` — a purported unit exists but fails structural or
  provenance checks.

All four states remain in the primary end-to-end denominator. Later diagnostics
may additionally distinguish retrieval miss, retrieval-rank miss, uptake miss,
unsupported claim, stale use, and continuation failure.

## 13. C0/C1 treatment model

Both conditions replay one sealed pre-trial state in fresh sessions or process
state. They receive identical, immutable:

- Agent-A raw artifacts and ordinary evidence;
- filesystem, repository, GitHub state, and ordinary tools;
- model/build/settings, readable roots, network policy, and budget;
- context-gap schedule and probe;
- execution policy, scoring policy, budget, and stopping rules.

Only C1 receives normal ConvMem availability against the frozen study snapshot.
C0 has no ConvMem retrieval or memory context but retains legitimate ordinary
transcripts, files, repository history, GitHub, and other permitted tools.

The controller is mechanical. It cannot answer, search on behalf of Agent B,
paste a target, retry selectively, or repair a condition after execution. C0
and C1 share no mutable conversational/session state, writable cache,
rate-limit state, database row, or cross-arm artifact. External mutable
services are snapshotted/replayed identically or excluded. Execution order is
randomized or counterbalanced under a frozen seed and is distinct from scorer
presentation order. Every trial uses a genuinely fresh Agent-B session.

Mechanical manifest comparison, not a human assertion of “same environment,”
must prove treatment symmetry. A difference in model/build/settings, prompt,
tools, readable roots, budget, stopping rule, replayed external state, or
environment policy invalidates the affected pair. The only intended treatment
difference is C1 access to the frozen ConvMem surface.

## 14. Outcome model and episode-primary estimand

### Outcome dimensions

The common scoring vocabulary contains:

- correctness of the answer/decision/artifact;
- currentness at the task time;
- provenance/grounding adequacy;
- unsupported or overconfident claims;
- realistic continuation-task success;
- actions/effort and latency where measurable.

Retrieval rank and capture state are diagnostic variables, not product-value
outcomes.

### Primary outcome contract

The primary score is a bounded, normalized within-episode continuation-utility
score derived from the predeclared behavioral rubric. Each episode contributes
at most one score per condition under the frozen within-episode aggregation
rule. Target-level correctness/currentness/provenance components remain
secondary diagnostics. Target-rich episodes cannot receive more primary weight
merely by producing more target rows.

The authoritative product result is a structured tuple, not one scalar:

1. **Opportunity prevalence:** target-bearing episodes over the complete
   prospectively fixed `EpisodeFrame`, plus target density and zero-target
   count. Membership comes only from the sealed `TargetRegistry`.
2. **Complete-pair conditional effect:** the paired episode-level C1−C0 effect
   among registry opportunities with valid, captured, score-evaluable outcomes
   in both arms. The report labels this conditioning explicitly; it is not the
   product's unconditional effect.
3. **Denominator accounting and bounds:** per-arm trial-evidence capture,
   per-arm score evaluability, mutually exclusive frozen failure reasons, and
   deterministic worst/best-case or approved sensitivity bounds across valid
   missing outcomes using the frozen score support. Bounds operate on one
   episode-opportunity contribution per target-bearing episode; target rows are
   secondary inputs to the frozen within-episode aggregation rule.

The analysis degrades gracefully from complete-pair estimate, to bounded
estimate, to inconclusive bounds. A C0/C1 missingness asymmetry is reported as
a co-primary process result and may widen or make the bounds inconclusive; it
does not trigger a lone cliff-edge tolerance that discards all comparison.
Any tolerance or decision threshold is a T0 value, not selected here.
Every permitted sensitivity procedure and analyst choice it exposes must also
be frozen before evidence exposure; “approved sensitivity” is not post-result
discretion.

### Secondary derived summaries

- `P_opp × Effect_evaluable` is an extrapolated opportunity-effect statistic.
  Because `P_opp` includes all target-bearing episodes while the effect is
  estimated only in complete pairs, it assumes the evaluable subset's effect
  transports to non-evaluable opportunities. It does **not** assign those
  opportunities zero effect.
- `P_evaluable × Effect_evaluable` describes the observed evaluable
  contribution and effectively assigns zero contribution outside that set; it
  is not a product-effect estimand.
- A naturally occurring continuation-task summary may be reported when the
  task rubric is sufficiently stable, with target results as diagnostics.

Every scalar is secondary, named with its assumptions, and forbidden as the
authoritative first-study result unless a separately validated utility model
with prospectively frozen weights later earns its own review and authority.

### Sparse-episode reliability

Every episode/condition score carries an architecture-level
`score_reliability` state in addition to its numeric score and terminal status.
At minimum the state vocabulary distinguishes `RELIABILITY_ACCEPTABLE`,
`RELIABILITY_SPARSE`, `RELIABILITY_NON_ESTIMABLE`, and
`RELIABILITY_NOT_APPLICABLE` for zero-target episodes. A sparse episode may be
retained with a descriptive normalized score, but it must not silently receive
the same epistemic confidence as a well-supported episode, and it must not be
treated as a zero effect.

The execution plan must prospectively freeze the evidence rule that separates
these states and the disposition of `RELIABILITY_SPARSE` in conditional
analysis. No episode may be removed, down-weighted, or reclassified after the
condition results are known. If the frozen reliability rule leaves the
conditional product effect non-estimable, the product conclusion is
`BLOCKED / NON-ESTIMABLE`, not null.

### Continuation-score reliability

Two independent scoring roles score the complete eligible/evaluable scoring
set from structurally identical, condition-neutral packages. Condition names,
session/episode identifiers, filenames/paths, latency, tool counts, raw tool
traces, retrieval-only blocks, and other condition-correlated form or metadata
are stripped or symmetrically normalized before presentation. Within-pair
presentation order is independently randomized and logged. If an LLM scores,
episode content is untrusted input and is isolated from scoring instructions;
calibration and study scoring use disjoint material and different sessions at
minimum. Scorers apply the frozen rubric independently and do not see the
other score before submission. Disagreements use a blinded third scorer or a
predeclared blinded consensus procedure. The scoring manifest records raw
agreement and a scale-appropriate reliability check: weighted kappa for
ordinal/categorical dimensions and an intraclass-correlation or equivalent
predeclared statistic for the bounded episode score. The exact statistic and
minimum acceptable reliability gate must be frozen before scoring begins.

If the gate fails, affected scores remain available as diagnostic evidence but
cannot support a product verdict. The frozen disposition is
`BLOCKED / NON-ESTIMABLE` when the primary episode score is not reliably
interpretable, or `DIAGNOSTIC` for an isolated secondary dimension; low scorer
reliability must never silently become a product null or positive result.

## 15. Zero-target and non-evaluable episodes

Every episode receives one explicit registry status:

- `TARGETS_PRESENT`;
- `ZERO_ELIGIBLE_TARGETS`;
- `EVIDENCE_INCOMPLETE`;
- `TARGET_ADJUDICATION_AMBIGUOUS`;
- `TARGETS_PRESENT_BUT_NOT_EVALUABLE`;
- `PROTOCOL_INVALID`.

Zero-target episodes contribute to frame retention, opportunity-density
reporting, and the information available about how often memory opportunities
arise. They do not automatically contribute a zero success score or enter the
conditional target-effect numerator.

`EVIDENCE_INCOMPLETE` is not zero. `TARGET_ADJUDICATION_AMBIGUOUS` is not zero.
Capture failure is not target absence. Agent-B failure is not target absence.
The analysis must report these counts separately and must not collapse them
into a convenient denominator.

For every registry opportunity, the outcome ledger records three distinct
axes in order:

1. natural ConvMem capture diagnostic (`CAPTURED`, absent, ambiguous, or
   malformed), which describes the C1 memory surface and never changes target
   membership;
2. trial-evidence capture by arm, with one frozen reason code per failed arm;
3. score evaluability by arm, with one frozen reason code per non-evaluable
   arm and a paired-score record only when both arms are valid and evaluable.

Valid post-treatment outcome missingness is analytically boundable. A wrong
environment, isolation breach, scorer unblinding, registry mutation, wrong
frozen state, lineage/hash mismatch, or other protocol-integrity failure is not
missing data: it invalidates the affected pair or study and never enters the
bounds procedure.

If the observation window completes with no target-bearing evaluable episode,
the opportunity result may still be descriptive, but the ConvMem product effect
is `BLOCKED / NON-ESTIMABLE`, not a null.

## 16. Interpretable null and information model

The atomic frozen manifest exposes, without selecting values opportunistically:

- smallest meaningful per-episode C1−C0 advantage;
- equivalence or non-inferiority margin, if that form is chosen;
- minimum number of target-bearing episodes;
- minimum total information/target count for secondary estimates;
- precision criterion for a usable interval;
- sparse-episode reliability rule and scorer-reliability minimum gate;
- confidence/randomization procedure and treatment of ties;
- score support and deterministic missing-outcome bounds procedure;
- frozen failure/reason taxonomy and orthogonal-state precedence;
- sparse/non-estimable terminal rule.

The derived terminal interpretation is evaluated only after the precedence
rules in §4:

- `COMPLETE — POSITIVE`: valid estimate meets the meaningful positive
  criterion and the precision/information rule;
- `COMPLETE — NULL / EQUIVALENT`: valid estimate is sufficiently precise to
  exclude the meaningful-advantage interval under the frozen null rule;
- `COMPLETE — NEGATIVE`: valid estimate favors C0 under the frozen negative
  criterion;
- `BLOCKED / NON-ESTIMABLE`: valid evidence has too few opportunities,
  insufficient information, or bounds too wide for the frozen decision rule;
  the exact reason code is mandatory and no product verdict is emitted;
- `DIAGNOSTIC`: a permitted diagnostic or secondary measurement is unavailable
  without invalidating the primary comparison; the exact axis/reason is kept;
- `INVALID`: a protocol, isolation, environment, lineage, registry, freeze, or
  scorer-blinding invariant was violated. Invalid evidence is excluded from
  outcome bounds and cannot support an effect interpretation.

No numerical margin is selected in this draft. A convenient executable value is
not evidence of product meaning.

## 17. Natural secondary strata

Secondary labels are assigned from raw evidence under the same blind registry
process. They are optional observations, not seed requirements:

- `current_at_probe`, `stale_at_probe`, `superseded`, `contradictory`, or
  `unknown` temporal status;
- cross-domain relevance when the evidence and continuation task naturally span
  domain boundaries;
- unresolved/committed/decided state;
- source/provenance class and evidence completeness;
- target class such as fact, decision, constraint, preference, commitment, or
  continuation state.

The absence of a stratum is reported as zero observed cases. The controller must
not generate episodes, targets, or probes merely to populate a stratum.

## 18. Identity and provenance chain

The canonical chain is:

```text
EpisodeFrame
  → EpisodeRecord
  → RawEvidenceManifest
  → TargetRegistry
  → Census/SampleManifest
  → ProbeManifest + ScoringKey
  → ConvMemCaptureState
  → C0/C1 Environment + Trial
  → Agent-B Trace
  → Action/Latency Record
  → Target Score
  → Episode Outcome
  → Study Analysis
```

Every link has a stable ID, parent identity, source digest, creation/seal time,
policy/version identity, and responsible role. The study manifest binds the
digests of all frozen generations. A reviewer can start at any final outcome and
reconstruct the ordinary raw source and every transformation that followed.

Target ground truth and scoring keys are sealed partitions: their existence and
digests are visible for integrity, but their values are not visible to Agent B.
Retrieval traces may be retained for diagnostics, but they never replace the
raw-evidence or registry link.

## 19. Freeze sequence

### Before Agent A

The following content is one atomic, content-addressed study configuration. A
partial freeze is not a durable state. The structural validator consumes the
canonical serialized bytes, checks required content rather than status flags,
and writes the digest to an append-only externally timestamped log. The
execution entry point must refuse to resolve without that logged digest. A
second responsible role re-derives the digest from the exact artifact to be
handed downstream and mechanically verifies the isolation boundary.

Freeze and hash together:

- `EpisodeFrame` and selected-episode schedule;
- population, retention, and context-gap rules;
- eligibility/unitization policy and adjudicator access policy;
- two independent adjudicator identities, disagreement resolution, and
  registry-quality metrics;
- probe families and high-level behavioral scoring vocabulary;
- probe-author, leakage-reviewer, scorer, and scoring-key separation;
- sparse-episode and continuation-score reliability states, statistics, and
  gate slots;
- natural-capture, per-arm trial-capture, and per-arm score-evaluability axes;
- fixed failure/reason taxonomy, boundable-versus-invalid classification, and
  orthogonal-state precedence;
- bounded score support, complete-pair estimator, missing-outcome bounds
  procedure, and structured no-authoritative-scalar reporting contract;
- C0/C1 sealed replay, environment equality, mutable-service, isolation/reset,
  execution-order, and scorer-presentation-order policies;
- census/sampling policy and workload threshold;
- primary/secondary outcome definitions and null/information framework.

Historical or synthetic calibration evidence used to justify any parameter
must be identified and hashed with a disjointness statement. Natural study
corpus contents, index/statistics, prior study queries/results, capture logs,
opportunity prevalence, episode counts, or study-identifying metadata must be
technically unreachable to any T0 parameter-setting process. Isolation is
verified by failed resolution/authentication or absent mounts, not by an agent
promise.

### After Agent A, before ConvMem/result inspection

Freeze and hash:

- complete raw evidence for every selected episode;
- source/snapshot identities and completeness status;
- target census, target ground truth, currentness, provenance requirements,
  ambiguity, and natural strata;
- registry completeness audit.

Capture-state review must occur only after the registry is sealed and must not
change registry membership.

### Before Agent B

Freeze and hash:

- census acceptance or reproducible sample;
- probe prompts, behavioral tasks, acceptable responses, and scoring key;
- leakage audit and role-access audit;
- C0/C1 environment manifests and frozen ConvMem snapshot;
- randomized/counterbalanced execution order and independently randomized
  scorer presentation order;
- condition-neutral scorer package transform and its validation report;
- information thresholds and analysis procedure.

After this point, no stage may modify an earlier artifact because of a C0/C1
result.

## 20. Reuse versus new components

| Architecture component | Existing foundation | Disposition |
|---|---|---|
| Raw evidence capture | v3 controller events/replies/raw files and evidence-recorder conventions | Historical foundation only; exact current implementation path is to be relocated or built with episode/source identity and completeness linkage. No `index_runner.py` exists at this tip. |
| Corpus/snapshot identity | `eval_corpus/capture.py`; `serving_index_repository.py` | Reuse immutable capture/manifest and serving-generation identity with study-generation binding. |
| Existing indexing anchors | `inter_model_index.py`; `serving_index_repository.py` | Reuse only for ordinary indexing/serving projection mechanics; neither becomes target-registry authority. |
| Retrieval/provenance traces | `ask.py`, `query.py`, `ask --trace` | Reuse as diagnostics; add target/probe linkage without making traces authoritative. |
| Fresh isolated Agent-B execution | Historical Portland C0/C1 plan and harness; no current reusable path verified | Historical/to-be-relocated foundation only; do not treat old fixed questions as design. |
| C0/C1 symmetry | Historical run manifest and v3 environment controls | Historical/to-be-relocated controls; reinstantiate as natural probe/episode manifests and frozen order. |
| Action/latency accounting | `eval_corpus/runner.py` latency harness | Reuse latency-measurement conventions; add a new ordinary-work action taxonomy and controller-exclusion layer. The cited `scripts/experiments/portland-baseline/action_counter.py` does not exist at this tip. |
| Paired results | `eval_corpus/paired_stats.py` and `eval_corpus/runner.py` | Extend for episode clusters, unequal target counts, zero states, reliability states, and margin-based verdicts. |
| Capture states | `eval_corpus/capture.py`; serving-generation identity from `serving_index_repository.py` | Reuse only as post-registry diagnostics; never as selection logic. |
| JudgeBench | Offline frozen semantic calibration | Optional scorer support only; never the target universe or primary product oracle. |
| Natural episode frame | None found | New methodology artifact. |
| Natural target registry | None found | New methodology artifact and authority boundary. |
| Leakage-safe probe lifecycle | Isolation/freeze precedents only | New methodology artifact with role/access audit. |
| Episode-primary/zero analysis | None found | New estimand and analysis contract. |

The architecture keeps these as one study-methodology boundary in the existing
local monolith. A separate service is not justified by the current failure
mode; the hard boundary is authority and artifact state, not deployment.

## 21. Verification requirements for later implementation

The future implementation must provide checks for:

1. frame immutability, selected-episode retention, and prework order freeze;
2. raw-source completeness, timestamp/hash consistency, and snapshot identity;
3. assessor access exclusion from ConvMem/result material;
4. mechanical stable-subject, truth/currentness, recovery-evaluability, and
   ambiguity decisions for every candidate;
5. two independent full-census adjudications, blinded disagreement resolution,
   and registry-quality metrics;
6. one registry entry per selected episode, including zero-target entries;
7. unique target IDs, resolvable source spans, duplicate decisions, and sealed
   registry digest;
8. census/whole-episode-sample reproducibility, inclusion probabilities, and
   unsampled-row
   preservation;
9. probe/key separation, independent leakage sign-off, answer/paraphrase/path/
   location/treatment/ConvMem leakage detection, and treatment-cue absence;
10. natural-capture-only enforcement and capture-after-registry ordering;
11. exact C0/C1 sealed-state replay equality except for frozen ConvMem access,
    including cache/database/external-service and execution-order controls;
12. fresh Agent-B sessions, no controller-as-agent actions, separate natural
    capture/trial-capture/evaluability axes, and complete trace/action records;
13. deterministic worst/best-case bounds for valid missing outcomes and proof
    that protocol/environment failures cannot enter those bounds;
14. condition-neutral scoring packages, independent presentation order,
    independent masked scoring, scale-appropriate reliability statistics,
    scorer-reliability gate, and frozen null/information parameters;
15. structural manifest validation from serialized bytes, exact-artifact hash
    re-derivation, and injected tamper/mismatch/isolation failures;
16. reconstruction of every final result through the identity chain;
17. orthogonal-state and reason-code precedence before any positive,
    null/equivalent, or negative outcome.

Verification should replay a controlled fixture for mechanics, but controlled
fixtures cannot be substituted for the eventual naturalistic evidence.

## 22. Review questions and escalation boundary

### Accepted D1–D6 corrective direction

- episode-first denominator and no replacement of selected episodes;
- raw evidence and sealed registry as study authority;
- capture/retrieval/uplift separation;
- two-stage freeze sequence before downstream exposure;
- C0/C1 symmetry and fresh-session boundary;
- two independent adjudicators over the complete census with blinded dispute
  resolution;
- structured result tuple, bounded normalized episode score, deterministic
  missing-outcome bounds, and explicit sparse/scorer reliability states;
- probe-author knowledge boundary, independent leakage review, and hard
  adjudicator/probe-author separation;
- census preference and whole-episode sampling when sampling is necessary;
- explicit terminal states and no product verdict from sparse evidence;
- no service split and no use of v3 target construction.

### Kiro should challenge

1. What prework workload rule makes census mandatory, and what evidence should
   justify any deviation from preferred whole-episode sampling?
2. What probe-family constraints ensure realistic continuation without making
   the task answer-bearing or trivia-like?
3. What evidence is sufficient to label current/stale/superseded or
   cross-domain status as a reliable secondary stratum?
4. Does the missingness contract preserve the opportunity denominator, report
   per-arm capture/evaluability, degrade from complete-pair estimate to bounds
   to inconclusive bounds, and exclude invalid trials from all bounds?
5. Are the orthogonal states, mandatory reason codes, and precedence rules
   sufficient to prevent a generic non-estimable sink or an effect verdict
   after protocol/environment/scorer failure?
6. Does paired replay establish treatment symmetry mechanically without
   over-prescribing infrastructure, and does it fail closed for shared state or
   non-replayable external services?
7. Does G5 need any additional synthetic fault beyond the amendment's bounded
   acceptance matrix before it can regain PASS?

### Sol is not required now

No current issue is a construct-level conflict requiring another Sol pass. A
future Sol adjudication is warranted only if Kiro and the architecture owner
produce materially conflicting, written positions on a construct-defining
choice such as the meaningful-advantage/equivalence contract. Routine
implementation difficulty, sparse data, or scorer disagreement is not an
escalation trigger by itself.

## 23. Next gate

Kiro PASSed exact corrective revision `b6a1ccf`, and Ryan accepted it with the
wording-only corrections at `fde840b`. The next possible action is a separately
authorized bounded G5C implementation slice. Design acceptance itself grants no
implementation, G6/T0, parameter freeze, natural evidence access, Agent A/B,
scoring, or product interpretation.

The gate remains **C**. It escalates to **D / constructed-panel redesign** only
if the opportunity registry cannot be constructed without treatment/capture-
derived information, or genuinely paired C0/C1 replay cannot be achieved
without uncontrolled environment differences.

**Next sequence:** separate Ryan G5C implementation grant, if any → bounded
synthetic implementation → fresh independent review → later fresh Ryan G6/T0
decision, if warranted.
