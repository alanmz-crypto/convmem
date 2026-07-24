# Architecture Direction: Codex Planning, Cursor Execution

## Planning Status

| Field | Value |
|-------|-------|
| **Phase** | Architecture Planning |
| **Characters** | Architect, Systems Thinker, Risk Reviewer |
| **Functions** | Planner |
| **Lanes** | OpenAI Codex authors this direction; Kiro design review and GitHub Copilot audit remain independent; Cursor is downstream implementer |
| **Authority** | Awaiting Ryan HITL approval |
| **Baseline** | `origin/main` at `df2ad28` on 2026-07-24 |

**Source:** Ryan's request to make Codex the default planning lane and keep
Cursor/Grok as the writing lane.

**Problem:** ConvMem currently concentrates architecture planning, execution
planning, and implementation in Cursor while other current routing text also
names Crush/Qwen as the default planning lead; the desired workflow needs one
clear planning owner, one separate implementation owner, and reviewers who do
not sign off their own work.

## Human consequence

Ryan should receive plans from Codex before Cursor changes tracked product
files. Cursor should receive an approved, executable plan instead of having to
create the governing architecture and then implement it. Kiro and the GitHub
Copilot audit lane retain their existing independent review functions, and Ryan
retains every authorization, deployment, merge, and durable-record gate.

This change is motivated by separation of duties and recent planning-stage
misses described in Ryan's handoff. It does not assume Codex is infallible and
does not turn Codex into the governing reviewer of its own plans.

## Current repository evidence

| Surface | Current behavior | Why it must change together |
|---------|------------------|-----------------------------|
| Full team lifecycle | The governing charter routes architecture planning, execution planning, and implementation to Cursor (`docs/inter-model/TEAM-CHARTER-2026-07-06.md:81`, `:92`, `:101`, `:119`). | Leaving any planning node behind would preserve split ownership and ambiguous handoffs. |
| Planning phase guides | Architecture and Execution Planning name Cursor as the active lane and Codex as optional read-only audit (`docs/planning/ARCHITECTURE-PLANNING.md:16`, `:140`; `docs/planning/EXECUTION-PLANNING.md:16`, `:130`). | Future plan authors follow these executable guides, so the charter alone cannot perform the migration. |
| Planning doctrine and contract | The kernel says “Cursor follows” plans (`docs/PLANNING-PROTOCOL.md:41`), while Contract v1 and its Python source require the literal stop marker `Cursor must stop here.` (`docs/planning/CONTRACT.md:39`; `planning_contract.py:27`). | Actor-specific contract text would contradict a Codex planning lane and make otherwise correct guides fail doctor. |
| Lane registry | Codex is presently described as PR Steward when assigned and explicitly not the governing audit lane; Cursor is the implementer (`docs/AGENT-ROLES.md:9`, `:15`). | Codex needs an explicit planning responsibility without inheriting audit, implementation, or automatic PR authority. |
| Compact protocol | The always-loaded table assigns implementation to Cursor, audit to Copilot, and design review to Kiro, but has no planning row (`config/agent-protocol.md:207-211`). | Every surface needs the same short planning route without duplicating the full lifecycle. |
| Model routing | The billing-cycle guide names Crush/Qwen3.7-Max the default lead for architecture and planning and names Cursor for large implementation (`docs/MODEL-WORKFLOW.md:90`, `:96`). | Model availability guidance must not override lane ownership. Grok is a Cursor model choice, not a new governance lane. |
| Fitness checks | Contract tests hard-code Cursor's stop marker (`tests/test_planning_guide_contract.py:25`); protocol tests enforce generated-surface parity (`tests/test_team_charter_protocol.py`). | The migration needs executable drift detection, not prose-only agreement. |

Historical plans, reviews, and handoffs accurately describe the lane assignment
at the time they were written. They are evidence, not migration targets.

## System boundary

### In scope

- Default authorship of Architecture Direction, Execution Plan, VERIFY plan,
  and plan-revision artifacts.
- The handoff boundary between an approved plan and tracked implementation.
- Full charter, lane registry, phase guides, planning doctrine/contract,
  compact protocol source, generated protocol examples, model-routing guidance,
  and their drift tests.
- Review routing and explicit HITL stops around those artifacts.

### Out of scope

- Changing implementation ownership away from Cursor.
- Making Grok a durable lane or pinning governance to one transient model.
- Making Codex the GitHub Copilot audit lane, Kiro sign-off lane, merge owner,
  ledger writer, or automatic PR Steward.
- Changing product code, backup behavior, write gates, dedupe, purge, or any
  currently active implementation arc.
- Rewriting historical plans, reviews, ledger evidence, or agent transcripts.
- Creating a generic multi-agent orchestrator, role DSL, or automated handoff
  service.
- Deploying generated rules into user-level agent configuration; deployment is
  a separate, exact Ryan-authorized external change after repository review.

### Deferred with owner

- The precise Grok model used inside Cursor remains an operational choice in
  `docs/MODEL-WORKFLOW.md`, owned by Ryan's current subscription/model routing.
- Any future automated orchestration remains a separate architecture decision.
- PR Steward assignments remain explicit, bounded Ryan grants under the
  existing charter.

## Constraints and invariants

1. **Planner and implementer are separate by default.** Codex authors the
   governing plan; Cursor writes tracked implementation code, tests, scripts,
   configuration, generated runtime surfaces, and implementation commits.
2. **Planner and reviewer are not collapsed.** Kiro retains governing design
   review/sign-off. GitHub Copilot retains conditional code-grounded safety,
   isolation, evidence-integrity, and targeted verification work.
3. **Ryan remains the authority boundary.** Codex cannot advance Architecture
   Planning to Execution Planning, authorize Cursor, deploy rules, merge, or
   write durable conclusions on its own.
4. **Codex planning does not auto-activate PR Steward.** The Delivery-role
   overlay still requires an explicit bounded assignment from Ryan.
5. **Cursor executes; it does not silently replace the approved direction.** If
   implementation reveals a material scope, architecture, authorization,
   security, or public-contract change, Cursor stops and routes the finding
   back to Codex planning and Ryan.
6. **Verification remains independently legible.** Codex authors the VERIFY
   contract or stub; Cursor supplies mechanical implementation evidence; Kiro
   and/or the Copilot audit lane supply the independent verdict required by the
   applicable gate. Codex does not issue the governing verdict on its own plan.
7. **Characters are not lanes.** Codex may use risk-review reasoning while
   planning, but that does not confer the Copilot audit lane's authority.
8. **Model weights are not lanes.** “Cursor/Grok” means Cursor is the durable
   lane and Grok is a replaceable model choice within it.
9. **One authoritative rule per property.** The full charter owns lifecycle
   responsibility, phase guides own phase behavior, the lane registry owns
   capabilities/must-nots, and the canonical protocol supplies a compact
   always-loaded route. Other docs point rather than invent competing rules.
10. **No silent contract mutation.** Replacing the actor-specific HITL marker
    changes Planning Guide Contract semantics and therefore requires Contract
    and Probe v2 with corresponding doctor/test updates.

## Options considered

| Option | Summary | Rejected because |
|--------|---------|------------------|
| A — Keep Cursor planning and implementation; strengthen post-implementation audit | Preserve the current lifecycle and ask reviewers to catch more after Cursor writes. | It leaves architecture and execution concentrated in one lane and addresses planning-stage omissions only after they become implementation cost. |
| **B — Codex plans; Cursor executes; Kiro/Copilot review** | Codex owns plan artifacts, Cursor owns implementation, existing independent reviewers and Ryan gates remain. | **Chosen.** It creates a clear handoff and separation of duties without inventing a lane or weakening current safety authority. |
| C — Make Cursor/Grok a new writer lane and Codex both planner and auditor | Encode the model name into governance and consolidate planning plus review in Codex. | Model availability is volatile, and self-review would recreate the concentration this change is intended to remove. |

## Chosen direction

Adopt Option B as the default lifecycle. Codex becomes the named planning lane
for Architecture Planning, Execution Planning, VERIFY-plan authorship, and
Revise Planning. Cursor remains the sole default implementation lane and may
use Grok or another Ryan-selected model without changing the charter. Kiro
continues design review/sign-off, the GitHub Copilot audit lane continues its
conditional technical-review duties, Crush remains the discovery and neutral-
framing lane, and Ryan continues to authorize every phase transition and
external or durable action.

The migration must update the complete live rule chain in one reviewed arc:
the governing charter and registry, Planning OS guides and doctrine, Planning
Guide Contract v2, the compact protocol source and regenerated examples,
model-routing guidance, and fitness tests. It must not sweep historical
artifacts. Repository changes land before any separately authorized deployment
of generated user-level rules.

## Target artifact lifecycle

```text
Ryan request / discovery evidence
            |
            v
Codex Architecture Direction --------> Kiro design review
            |
        Ryan HITL
            |
            v
Codex Execution Plan + VERIFY contract
            |
        Ryan HITL
            |
            v
Cursor implementation + mechanical evidence
            |
            +--------------------------> Copilot targeted audit (when warranted)
            +--------------------------> Kiro design/sign-off gate
            |
        Ryan review / merge / record
            |
     finding changes direction
            |
            +--------------------------> Codex Revise/Architecture Planning
```

No arrow grants the receiving lane permission to merge, deploy, write the
ledger, or self-advance the phase.

## Public seams and ownership

| Artifact or decision | Default author/owner | Required boundary |
|----------------------|----------------------|-------------------|
| Discovery brief and repo-grounded facts | Crush or authorized investigator | Facts may inform but do not approve architecture. |
| Architecture Direction | Codex | Stops for Ryan; Kiro reviews design. |
| Execution Plan | Codex | Starts only after architecture approval; stops before implementation. |
| VERIFY plan/stub | Codex | Defines observables before implementation; cannot self-sign. |
| Tracked implementation and mechanical evidence | Cursor | Must follow approved plan or stop on material deviation. |
| Safety/isolation/code audit | GitHub Copilot audit lane | Conditional, targeted, and independent; no implementation ownership. |
| Design review/sign-off | Kiro | Non-implementing and review-required. |
| Phase authorization, merge, deployment, durable conclusion | Ryan | Never inferred from a plan or passing test. |
| Bound-brief PR lifecycle | PR Steward when explicitly assigned | Overlay does not enlarge Codex planning or implementation authority. |

## Planning contract direction

Contract v2 should make the common HITL stop actor-neutral. The required intent
becomes:

```text
Active phase lane must stop here.
Await HITL.
```

Phase metadata still names the responsible lane explicitly, so neutrality does
not hide ownership. This change lets Architecture, Execution, Verify, Revise,
and Execute guides share one enforceable stop contract while assigning Codex or
Cursor according to the phase. Contract v2 must not add a general state machine
or orchestration framework.

## Required fitness properties

The downstream Execution Plan must attach one authoritative check to each
property:

| Property | Required evidence |
|----------|-------------------|
| Codex is the planning owner | Full charter, lane registry, and planning guides agree; a focused test/anchor fails if the planning assignment disappears or returns to Cursor/Crush. |
| Cursor is the implementation owner | Execute guide, charter, compact protocol, and tests retain Cursor; no planning edit grants Codex tracked implementation by default. |
| Review stays independent | Text and tests preserve Kiro design review and Copilot conditional audit; no Codex self-sign route is introduced. |
| HITL stops are actor-neutral and enforced | Contract/Probe v2, Python source, human mirror, fixtures, and all active phase guides agree on the new stop marker. |
| Generated surfaces do not drift | Protocol generation is idempotent and every checked generated surface equals the canonical slice. |
| Model routing cannot override lanes | `MODEL-WORKFLOW.md` names Codex planning and Cursor implementation; Grok is described only as a model choice inside Cursor. |
| Historical evidence is preserved | Diff contains no bulk edits to completed plans, reviews, transcripts, or ledger artifacts. |
| Deployment remains separate | Repository acceptance requires no writes to user-level Cursor, Codex, Kiro, Crush, MCP, or Copilot configuration. |

In addition to focused tests and the full suite, the change needs three manual
scenario checks before merge:

1. A planning request routes Codex to a docs-only planning branch and stops at
   Ryan HITL without implementation.
2. An approved execution handoff routes Cursor to implementation without
   reopening the governing direction; a material mismatch routes upstream.
3. A verification request separates Codex's predeclared checks, Cursor's
   mechanical evidence, and Kiro/Copilot's independent verdict.

## Rollout and evidence review

Treat the new default as a reversible three-arc observation period, not as a
claim that one model will always outperform another. For each of the next three
eligible implementation arcs, the handoff should classify material rework as:

- **planning escape:** a missing boundary, authorization rule, failure mode, or
  verification observable that was reasonably discoverable before execution;
- **implementation defect:** Cursor departed from an adequate approved plan or
  introduced a code/test defect;
- **review discovery:** a genuinely new fact that neither planning nor
  implementation could reasonably establish earlier;
- **lane violation:** planning, implementation, review, or authority crossed
  the assigned boundary.

After three arcs, Ryan reviews the evidence. Changes to the default require a
new explicit architecture decision; no automatic rollback or silent exception
is authorized. A one-off lane waiver must name the artifact, actor, scope, and
expiration.

## Risks and reversibility

- **More handoffs may add latency.** Keep plan artifacts bounded and require
  only the reviewers appropriate to the risk; do not add a new review body.
- **Codex may over-plan.** Phase guides must retain tight scope, single chosen
  direction, executable acceptance criteria, and the HITL stop. Cursor may
  return ambiguity rather than inventing architecture.
- **Governance text may drift.** Update the live source chain together and add
  fitness checks; generated examples come only from the canonical protocol.
- **Old documents will still name Cursor planning.** Preserve them as dated
  evidence and make current routers point to the new live rules rather than
  rewriting history.
- **Grok availability may change.** Keeping Cursor as the lane makes model
  substitution operationally reversible without another charter migration.
- **The split may not improve outcomes.** The three-arc classification provides
  evidence for a later decision, while the repository change itself is
  reversible through a reviewed follow-up.

## Success criteria

This direction is successfully implemented only when:

- a fresh agent can identify Codex as planning owner and Cursor as
  implementation owner from every live routing surface;
- Architecture, Execution, VERIFY-plan, Revise, and Execute phase boundaries
  name the correct lane and stop at Ryan's gate;
- Kiro and the Copilot audit lane retain their current independent authority;
- Contract/Probe v2 and doctor enforce the actor-neutral stop marker;
- generated protocol examples are current and generation is idempotent;
- focused tests, full tests, and manual lifecycle scenarios pass;
- no historical artifact or unrelated runtime subsystem changes; and
- no user-level protocol deployment occurs without separate exact Ryan
  authorization.

## Downstream handoff

After Ryan approves this direction, Codex should enter Execution Planning and
produce:

`docs/plans/EXECUTION-2026-07-24-codex-planning-cursor-execution.md`

That plan must define the exact file set, ordered edits, Contract/Probe v2
migration, generated-surface command, focused and full verification commands,
manual scenario evidence, rollback, and the final Cursor implementation brief.
It should also create the required VERIFY stub for this governance arc.

Review routing for the approved Execution Plan:

- **Kiro:** confirm separation of planning, implementation, review, and Ryan
  authority; reject accidental new roles or self-signoff.
- **GitHub Copilot audit lane:** after Cursor implementation, check source-to-
  generated parity, stale live references, contract/doctor enforcement, and
  any authorization widening. This is a targeted governance/safety audit, not
  routine drafting.
- **Cursor:** implement only the approved Execution Plan; stop on a material
  architecture or authorization discrepancy.
- **Ryan:** approve direction and execution separately, authorize any external
  deployment separately, and alone merge or record the conclusion.

No Execution Plan, implementation, generated deployment, merge, or durable
record is authorized by this Architecture Direction.

Active phase lane must stop here. Await HITL.
