# Web-development agent system — Stage −1a value baseline

**Arc:** none (ad-hoc)

**Source:** Ryan authorization on 2026-09-19 after Claude adversarial review and Kiro review session `896029c1-74b8-4ed6-9fe1-a223bc726ed0`

**Authority:** Stage −1a observation and these two planning artifacts are authorized. Stage −1b construction is not authorized.

**Stop:** collect and classify real-task evidence; return to Ryan before any sandbox, checker, broker, verifier, contract system, or other implementation.

## Problem

The project wants agents to produce consistently strong web-development work
across sites. The preceding proposal grew into a control platform before showing
which recurring failures, if any, that platform would prevent. The cheapest
decisive move is to observe current work before selecting a mechanism.

## Architecture direction

Measure approximately ten real practice tasks under the current workflow. Do
not add controls during the observation window. Classify observed outcomes, and
allow the evidence to justify at most one narrowly targeted Stage −1b proposal.

This is a value-discovery gate, not an implementation pilot and not evidence of
general web-development improvement.

## System boundary

### In scope

- Real Willowy Hollow practice tasks that would happen without this study.
- Lightweight observation using
  [the baseline template](TEMPLATE-webdev-stage-minus-one-baseline.md).
- Coarse task type, site/tier, elapsed time, outcome, failure class, and human
  correction.
- Evidence sufficient to explain the classification without retaining private
  client data, credentials, database dumps, or WordPress admin-list captures.
- A post-sample decision by Ryan: close, defer, or authorize one targeted
  Stage −1b investigation or control proposal.

### Out of scope

- Sandbox, capability broker, drift checker, browser verifier, task-contract
  system, authority compiler, resource registry, or learning/writeback system.
- Manufactured unsafe operations or seeded failures during the baseline.
- Staging, production, deploy, remote Git, SSH, or live-database mutations.
- Changes to the current `AGENTS.md`, stack, synchronization, deployment, or
  review workflow.
- Claims that ten tasks estimate failure prevalence or generalize across sites,
  agents, models, environments, or task classes.

## Constraints and invariants

- The current workflow remains the baseline. Observation must not alter agent
  permissions, prompts, required guidance, review requirements, or tools.
- Log only real tasks. Do not create tasks to make a proposed control appear
  useful.
- Approximately ten completed tasks is a weak discovery sample. The presence
  of a failure establishes that the class occurred; absence does not establish
  that it is rare or impossible.
- If ten qualifying tasks do not occur within one week, extend the observation
  window rather than lowering the sample.
- Task mix matters. Every entry carries a coarse type plus site and tier.
- No task may broaden existing authority. WordPress database mutations still
  require the established backup-before-mutation discipline.
- The practice `public_html/` tree is disposable; the higher-severity reach
  paths are deploy-source repositories, Git pushes, loaded SSH credentials,
  SiteGround, and remote WordPress/database access.
- The production-unlock work is the priority. Observation may free-ride on that
  work; new enforcement must not be introduced immediately before launch.
- The Cursor canvas is reference-only. This Git-tracked note and template are
  the durable planning artifacts.

## Options considered

| Option | Summary | Decision |
| --- | --- | --- |
| A — Bounded Stage 0 | Build contracts, authority views, capability enforcement, verifier, evidence policy, and fixtures around one practice task. | Rejected: proves plumbing before value and creates a platform skeleton. |
| B — Simultaneous Stage −1 | Log real tasks while also building a structural sandbox and drift script. | Rejected: construction begins before the baseline identifies either failure class. |
| C — Stage −1a first | Observe current work; conditionally propose at most one mechanism after a real failure identifies the need. | Chosen: lowest cost, reversible, and directly falsifies the need for near-term investment. |

## Observation method

Use one copy of the baseline template per observation window. Record tasks in
completion order. A qualifying task:

- is real client/practice work;
- reaches a meaningful completion or explicit stop;
- is not created for the study;
- records the agent/model actually used;
- has enough evidence to classify its outcome.

Use these coarse failure classes:

- `UNSAFE` — attempted or completed mutation outside authorized scope.
- `WRONG_OUTPUT` — artifact failed the stated task or required substantial
  correction.
- `SLOW` — avoidable agent/workflow overhead dominated the task.
- `NONE` — accepted without a material failure.

Multiple classes may apply. `NONE` requires a short acceptance basis; it is
not assumed from silence.

## Interpretation and decision rule

After approximately ten completed tasks:

1. Group observations by failure class, task type, site, and tier.
2. Identify repeated failure mechanisms, not merely repeated symptoms.
3. For each candidate intervention, ask whether it would have prevented the
   observed failure without introducing comparable cost or launch risk.
4. Recommend one of:
   - **close current investment** — no recurring actionable failure emerged;
   - **defer** — evidence is insufficient or the launch window makes change
     unsafe;
   - **propose one Stage −1b target** — a recurring failure and plausible
     narrow prevention mechanism are both evidenced.
5. Ryan alone authorizes any Stage −1b work.

Closing current investment means no control-system build is justified now. It
does not assert that the unobserved failure probability is zero; a later real
incident may reopen the question.

## Conditional Stage −1b requirements

These are requirements for a future proposal, not authorized work.

### If an unsafe reach failure appears

Write a one-page threat model before proposing enforcement:

- protected asset;
- actual reach path;
- agent capabilities;
- structural controls;
- conventional controls;
- bypass assumptions.

The model must focus on the demonstrated path. Bind mounts and local
`stack_wp` wrapping do not by themselves protect deploy-source pushes, loaded
credentials, or remote operations.

### If stale or contradictory facts cause wrong output

Propose a drift check only for facts causally connected to the observed
failure. Exclude intentionally environment-specific page and UAGB block IDs,
and account for WPCode cache-rebuild timing. A generic AGENTS-to-runtime
comparison is not pre-approved.

## Durable principles

These survive regardless of the baseline result:

- Structural enforcement is stronger than model refusal when the threat model
  and protected path are correct.
- A no-op needs evidence that no change was the correct outcome.
- Conflict handling must not silently choose a winner.
- A human waiver remains a waiver; it must not be reported as technical PASS.

## Risks and reversibility

- **Sampling bias:** launch work may overrepresent urgent tasks. Mitigation:
  retain task-type and site/tier tags and avoid prevalence claims.
- **Observer effect:** logging may make reviewers more careful. Mitigation:
  do not change workflow, prompts, or acceptance rules.
- **Hindsight rationalization:** a proposed mechanism may be attached after the
  outcome. Mitigation: name the exact observed failure and explain the causal
  prevention path.
- **Privacy leakage:** evidence may contain client or administrator data.
  Mitigation: use concise textual evidence; do not retain admin-list
  screenshots, database dumps, credentials, tokens, or private form content.
- **Opportunity cost:** logging may compete with launch. Mitigation: keep each
  entry short and stop collecting detail that does not affect classification.
- **Reversibility:** the note and template can be removed with no runtime
  effect. No site or tool behavior changes in Stage −1a.

## Downstream handoff

- Current action: observe qualifying real tasks with the template.
- Decision owner: Ryan.
- Earliest construction step: a separately authorized, evidence-bound Stage
  −1b proposal after baseline review.
- No automatic transition to Execution Planning or implementation.

## TL;DR

- Observe approximately ten real practice tasks before building any umbrella
  control machinery.
- A discovered failure may justify one narrow follow-up; absence only closes
  current investment, not the possibility of future incidents.
- Protect launch work: logging is authorized, construction is not.
