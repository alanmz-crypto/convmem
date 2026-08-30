# Architecture Direction — Naturalistic ConvMem Product-Value Study

> **REVIEW REQUIRED — NOT AUTHORIZED FOR IMPLEMENTATION.** This is an
> architecture draft for Kiro design review. It authorizes no Agent A/B run,
> no corpus mutation, no target-registry population, and no production change.
>
> **Arc:** none (ad-hoc) — Portland / ConvMem product-value evaluation
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

## 4. Lifecycle state machine

The study is an append-only sequence of frozen artifacts. A later state may
read an earlier artifact but may not rewrite it. Any violation enters `INVALID`
or `DIAGNOSTIC`; it does not silently restart the study.

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
                   ┌───────────────┬──────┼───────────────┐
                   ▼               ▼      ▼               ▼
              POSITIVE       NULL/EQUIVALENT  NEGATIVE  BLOCKED/NON-ESTIMABLE

Any state ── protocol violation ──► INVALID
Any state ── evidence/identity failure ──► DIAGNOSTIC
```

### State authority and transition conditions

| State | Authority | Required transition evidence |
|---|---|---|
| `FRAME_FROZEN` | Ryan-approved study owner | Frame, policies, environment, order rule, and hashes are immutable. |
| `OBSERVATION_OPEN` | Mechanical controller | Only prospectively selected episodes are observed; no replacement episodes. |
| `EPISODE_EVIDENCE_SEALED` | Evidence recorder/controller | Complete raw-source manifest, timestamps, hashes, and snapshot identities exist. |
| `TARGET_ADJUDICATION` | Blind target assessor(s) | Assessor access excludes ConvMem capture/retrieval and C0/C1 results. |
| `TARGET_REGISTRY_SEALED` | Study owner after audit | Every episode has a census entry, including explicit zero-target entries. |
| `CENSUS_ACCEPTED` / `SAMPLE_SEALED` | Mechanical sampler | Census or fixed probability sample is reproducible and unsampled rows remain. |
| `PROBES_SEALED` | Probe author + study controller | Probe, acceptable response, scoring key, and leakage audit are frozen. |
| `C0C1_READY` | Mechanical controller | Common artifacts and manifests match; only ConvMem availability differs. |
| `EXECUTION_COMPLETE` | Mechanical controller | Fresh Agent-B sessions, frozen order, full traces, and terminal statuses exist. |
| `SCORING_LOCKED` | Blinded scorer | Condition labels are masked while primary outcomes are scored. |
| `ANALYSIS_READY` | Analysis owner | Identity chain is complete and all information thresholds are evaluated. |

`ZERO_ELIGIBLE_TARGETS` is an episode status inside the sealed registry, not a
study failure. It has no C0/C1 target trial unless the approved probe family
defines a target-independent continuation task.

## 5. Authority and role boundaries

| Role | May read | May write | Must not do |
|---|---|---|---|
| **Study owner / Ryan** | All study artifacts and review reports | Frame/policy approval and final study disposition | Change frozen artifacts after exposure; delegate merge authority. |
| **Study controller** | Manifests, mechanical run state, environment metadata | State transitions, hashes, run records | Act as Agent B, select targets, edit probes, or add context. |
| **Raw-evidence recorder** | Ordinary Agent-A outputs and permitted source metadata | Immutable raw-evidence manifest and source copies | Filter for interesting content or inspect ConvMem success to decide retention. |
| **Target adjudicator** | Complete raw evidence and versioned eligibility rules | Target census, rationale, ambiguity status, strata labels | Read ConvMem capture/rank, C0/C1 outputs, or expected treatment advantage. |
| **Probe author** | Sealed registry partition, raw evidence, predeclared probe families | Probe definitions and sealed acceptable-response key | Read ConvMem search results, capture labels, condition outcomes, or treatment order. |
| **Agent-B executor** | Ordinary files/repository/GitHub/transcripts, assigned probe, normal tools; C1 additionally has frozen ConvMem | Agent-B transcript, actions, output, and trace | Read registry, answer key, controller internals, or an earlier Agent-B session. |
| **Scorer** | Frozen Agent-B outputs, raw evidence, sealed rubric/key, bounded traces | Target and episode scores | Change scoring rules after seeing condition labels or use retrieval rank as truth. |
| **Kiro** | Architecture and review evidence | Design-review verdict and required revisions | Implement runtime or experiment code. |
| **Codex** | Existing plans and methodology evidence | Architecture draft | Run Agent A/B or authorize implementation. |
| **Cursor** | Only after Ryan acceptance | Future implementation | Start from this draft without the acceptance gate. |

The assessor multiplicity decision is intentionally unresolved: independent
duplicate adjudication with disagreement review is the stronger default, but
the minimum acceptable design (two full assessors, or one assessor plus a
blinded duplicate audit) requires Kiro review.

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

Ambiguous candidates are retained in the adjudication record with a reason and
resolution status. They are not silently converted to zero targets or silently
included in the evaluable primary set.

## 9. Outcome-blind adjudication and sealed registry

The target assessor receives the complete raw-evidence manifests and the frozen
eligibility/unitization rules through a view that excludes ConvMem stores,
retrieval traces, capture labels, target-specific search results, C0/C1
outputs, and treatment order. Technical metadata needed to prove access
separation is retained in an audit log.

The sealed `TargetRegistry` contains one episode entry for every selected
episode and, where applicable, target records with at least:

- immutable `target_id` and `episode_id`;
- supporting source/span IDs and evidence manifest digest;
- target value/ground truth partitioned from the executor-visible view;
- target class and naturally observed secondary-stratum labels;
- temporal validity/currentness and provenance requirement;
- eligibility rationale, unitization rationale, and duplicate links;
- adjudication status, ambiguity/disagreement record, and assessor identity;
- registry policy version, creation time, and registry digest.

The registry is sealed before any target-specific probe is created, sample is
drawn, or C0/C1 result is observed. Capture status is an additional later
field; it cannot change registry membership.

The registry is the authoritative study census. The ledger/raw evidence owns
the ordinary facts; Chroma is a frozen ConvMem treatment projection. No
retrieval result can mint or delete a target.

## 10. Census versus probability sampling

A census is mandatory whenever the prospectively frozen workload ceiling makes
complete adjudication and probing feasible. The ceiling and decision rule must
be fixed before the target count is known; it cannot be raised after seeing a
favorable roster.

If sampling is allowed by that rule:

- seal the full registry first, including zero-target episodes and unsampled
  targets;
- derive the sampler seed from a precommitted study seed plus immutable study
  and registry identities;
- use a fixed sample-size/allocation rule and record inclusion probability for
  every sampled target;
- retain the complete unsampled roster and its digest;
- never stratify or oversample on capture status, retrieval success,
  memorability, searchability, semantic interest, or expected C1 advantage;
- make the analysis aware of the sampling design, especially where a sampled
  target set is used to estimate an episode score.

The architecture does not yet choose whether a large registry is handled by
within-episode target sampling, whole-episode sampling, or a two-stage design.
That choice affects the episode estimand and is a Kiro review question.

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

The probe author may read sealed raw evidence and the adjudicated target record,
but not ConvMem capture/search output, C0/C1 outcomes, or treatment order. The
Agent-B view contains neither the registry nor the answer key. The controller
must not paste an answer-bearing handoff or target inventory into either
condition.

The leakage audit checks at least:

- answer values and source-span text are not copied into the probe unless the
  ordinary task legitimately exposes them to both conditions;
- source-path, ledger-ID, rank, ConvMem, condition, and treatment cues are
  absent unless part of the ordinary task;
- no C0/C1 transcript, score, capture label, or retrieval rank was available to
  author or executor;
- the probe asks for a realistic task outcome rather than a memorization
  recital;
- the acceptable-response key was sealed before execution and condition labels
  were masked during primary scoring.

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

Both fresh Agent-B conditions receive identical, immutable:

- Agent-A raw artifacts and ordinary evidence;
- filesystem, repository, GitHub state, and ordinary tools;
- model/build/settings, readable roots, network policy, and budget;
- context-gap schedule and probe;
- execution order manifest and scoring policy.

Only C1 receives normal ConvMem availability against the frozen study snapshot.
C0 has no ConvMem retrieval or memory context but retains legitimate ordinary
transcripts, files, repository history, GitHub, and other permitted tools.

The controller is mechanical. It cannot answer, search on behalf of Agent B,
paste a target, or repair a condition after execution. C0/C1 order is randomly
assigned or counterbalanced according to the frame rule and frozen before the
first Agent-B trial. Every trial uses a genuinely fresh Agent-B session.

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

### Provisional primary outcome

The recommended starting point for Kiro review is an episode-level bounded
continuation utility score derived from the predeclared behavioral rubric. Each
episode contributes at most one normalized score per condition, formed from its
eligible target probes without target-count weighting across episodes. The
target-level correctness/currentness/provenance components remain secondary
diagnostics unless the final architecture justifies a different primary.

The default estimand is therefore two-part:

1. **Opportunity component:** prevalence and density of eligible targets across
   all prospectively selected episodes, including zero-target episodes.
2. **Conditional product component:** the episode-level C1−C0 continuation
   effect among episodes with at least one eligible, evaluable target.

This makes the conditioning set pre-treatment and visible. It does not pretend
that a zero-target episode supplied an unobserved recovery outcome.

### Alternatives that remain open

- **All-episode opportunity-weighted effect:** assign a declared zero effect
  contribution to zero-target episodes, representing expected benefit per
  ordinary episode. This must not be described as a treatment failure.
- **Two-part primary report:** retain opportunity prevalence and conditional
  effect as co-primary quantities, with no single composite.
- **Task-level primary:** use a naturally occurring continuation-task success
  outcome when the task rubric itself is sufficiently stable, with target
  results as supporting diagnostics.

The architecture records enough information to compute these alternatives from
the same sealed artifacts, but does not silently choose among them.

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

If the observation window completes with no target-bearing evaluable episode,
the opportunity result may still be descriptive, but the ConvMem product effect
is `BLOCKED / NON-ESTIMABLE`, not a null.

## 16. Interpretable null and information model

The frozen frame exposes, without selecting values opportunistically:

- smallest meaningful per-episode C1−C0 advantage;
- equivalence or non-inferiority margin, if that form is chosen;
- minimum number of target-bearing episodes;
- minimum total information/target count for secondary estimates;
- precision criterion for a usable interval;
- confidence/randomization procedure and treatment of ties;
- sparse/non-estimable terminal rule.

The terminal interpretation is:

- `COMPLETE — POSITIVE`: valid estimate meets the meaningful positive
  criterion and the precision/information rule;
- `COMPLETE — NULL / EQUIVALENT`: valid estimate is sufficiently precise to
  exclude the meaningful-advantage interval under the frozen null rule;
- `COMPLETE — NEGATIVE`: valid estimate favors C0 under the frozen negative
  criterion;
- `BLOCKED / NON-ESTIMABLE`: too few episodes/targets or intervals too wide;
  no product verdict;
- `DIAGNOSTIC`: identity, completeness, or instrumentation failure prevents
  interpretation;
- `INVALID`: a protocol invariant was violated.

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

Freeze and hash:

- `EpisodeFrame` and selected-episode schedule;
- population, retention, and context-gap rules;
- eligibility/unitization policy and adjudicator access policy;
- probe families and high-level behavioral scoring vocabulary;
- C0/C1 environment and order policy;
- census/sampling policy and workload threshold;
- primary/secondary outcome definitions and null/information framework.

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
- randomized/counterbalanced condition order;
- information thresholds and analysis procedure.

After this point, no stage may modify an earlier artifact because of a C0/C1
result.

## 20. Reuse versus new components

| Architecture component | Existing foundation | Disposition |
|---|---|---|
| Raw evidence capture | v3 controller events/replies/raw files; evidence recorder; `index_runner.py` | Reuse with episode/source identity and completeness linkage. |
| Corpus/snapshot identity | `eval_corpus/capture.py`; run manifests; v3 background/C1 hashes | Reuse with study-generation binding. |
| Retrieval/provenance traces | `ask.py`, `query.py`, `ask --trace` | Reuse as diagnostics; add target/probe linkage without making traces authoritative. |
| Fresh isolated Agent-B execution | Historical Portland C0/C1 plan and harness | Reuse as bounded execution foundation; do not treat old fixed questions as design. |
| C0/C1 symmetry | Historical run manifest and v3 environment controls | Reuse with natural probe/episode manifests and frozen order. |
| Action/latency accounting | `scripts/experiments/portland-baseline/action_counter.py` | Reuse with ordinary-work action taxonomy and controller exclusion. |
| Paired results | `eval_corpus/paired_stats.py` and `runner.py` | Extend for episode clusters, unequal target counts, zero states, and margin-based verdicts. |
| Capture states | v3 admissibility labels and capture validation | Reuse only as post-registry diagnostics; never as selection logic. |
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
4. one registry entry per selected episode, including zero-target entries;
5. unique target IDs, resolvable source spans, duplicate decisions, and sealed
   registry digest;
6. census/sample reproducibility, inclusion probabilities, and unsampled-row
   preservation;
7. probe/key separation, answer-leakage detection, and treatment-cue absence;
8. natural-capture-only enforcement and capture-after-registry ordering;
9. exact C0/C1 environment equality except for frozen ConvMem availability;
10. fresh Agent-B sessions, frozen order, no controller-as-agent actions, and
    complete trace/action records;
11. independent scoring labels and frozen null/information parameters;
12. reconstruction of every final result through the identity chain;
13. terminal-state distinctions among invalid, diagnostic, sparse,
    zero-target, positive, null/equivalent, and negative outcomes.

Verification should replay a controlled fixture for mechanics, but controlled
fixtures cannot be substituted for the eventual naturalistic evidence.

## 22. Review questions and escalation boundary

### Luna has justified

- episode-first denominator and no replacement of selected episodes;
- raw evidence and sealed registry as study authority;
- capture/retrieval/uplift separation;
- two-stage freeze sequence before downstream exposure;
- C0/C1 symmetry and fresh-session boundary;
- explicit terminal states and no product verdict from sparse evidence;
- no service split and no use of v3 target construction.

### Kiro should challenge

1. Should primary target census use two independent adjudicators, one assessor
   plus blinded duplicate audit, or another disagreement design?
2. Is the provisional two-part estimand the right default, and how should a
   zero-target episode contribute to any single headline effect?
3. Should the primary episode score be a normalized within-episode target
   utility, a behavioral continuation-task result, or a two-level report?
4. What prework workload rule makes census mandatory, and what probability
   sampling design remains valid for an episode-primary estimand?
5. What probe-family constraints ensure realistic continuation without making
   the task answer-bearing or trivia-like?
6. What evidence is sufficient to label current/stale/superseded or
   cross-domain status as a reliable secondary stratum?

### Sol is not required now

No current issue is a construct-level conflict requiring another Sol pass. A
future Sol adjudication is warranted only if Kiro and the architecture owner
produce materially conflicting, written positions on the zero-target
estimand, the meaningful-advantage margin, or another construct-defining
choice. Routine implementation difficulty is not an escalation trigger.

## 23. Next gate

This document is ready for Kiro design review. After Kiro review, Ryan decides
whether to accept the architecture and authorize a separate implementation
phase. Only then may Cursor implement the methodology layer.

**Next sequence:** Codex architecture draft → Kiro design review → Ryan
acceptance → Cursor implementation.

