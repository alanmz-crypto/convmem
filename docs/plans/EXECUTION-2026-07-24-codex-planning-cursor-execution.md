# Execution Plan: Codex Planning, Cursor Execution

## Planning Status

| Field | Value |
|-------|-------|
| **Phase** | Execution Planning |
| **Characters** | Task Decomposer, Dependency Mapper, Scope Guardian |
| **Functions** | Planner |
| **Lanes** | OpenAI Codex authors this plan; Cursor is the downstream implementation lane; Kiro and GitHub Copilot retain independent review duties |
| **Authority** | Ryan approved the Architecture Direction at `2ed7060`; this Execution Plan awaits Kiro review and Ryan HITL approval |
| **Probe Version** | v1 (current contract; implementation migrates the live Planning OS to v2) |

**Source:** Ryan-approved
[`ARCHITECTURE-codex-planning-cursor-execution.md`](ARCHITECTURE-codex-planning-cursor-execution.md)
at `2ed7060`.

**Goal:** Make Codex the default author of ConvMem planning artifacts and keep
Cursor as the separate implementation writer, with actor-neutral HITL stops,
independent review, generated-surface parity, and no inferred authority.

## Human consequence

After this arc, Ryan can give Codex a planning request, approve the resulting
direction and execution plan, and then hand the bounded work to Cursor. Cursor
will no longer be expected to create the governing architecture it implements.
Kiro remains the design/sign-off lane; the GitHub Copilot audit lane remains a
conditional technical reviewer; Ryan alone advances phases, merges, deploys,
and records durable conclusions.

No arrow grants the receiving lane permission to merge, deploy, write the
ledger, or self-advance the phase.

## Entry gates

Cursor may enter Execute only after all of the following are true:

1. Kiro reviews this exact Execution Plan tip and issues written PASS.
2. If Kiro rejects this plan, the rejection goes to Ryan before Codex may
   revise or resubmit it.
3. Ryan approves this exact Execution Plan tip for implementation.
4. The approved Architecture, Execution Plan, and VERIFY stub are available on
   the implementation base. The default route is that Ryan merges the planning
   artifacts to `main`, then Cursor starts from the refreshed `origin/main`.
5. Ryan names any waiver from the exact file set or task sequence in writing.

A GitHub Copilot audit PASS on the later implementation does not substitute
for Kiro design sign-off on this governing plan.

## Scope lock and exact file set

### Authored governance and Planning OS files

Cursor may edit these files for the stated responsibility only:

| Path | Required change |
|------|-----------------|
| `docs/inter-model/TEAM-CHARTER-2026-07-06.md` | Move Architecture, Execution, VERIFY-plan, and Revise planning ownership to Codex; retain Cursor implementation; add rejection, review, PR Steward, and three-arc classification boundaries. |
| `docs/AGENT-ROLES.md` | Name Codex's planning responsibility without making Planner a new role or granting audit/implementation/PR authority; retain Cursor implementation. |
| `docs/PLANNING-PROTOCOL.md` | Change doctrine from “Cursor follows plans” to Codex authors approved plans and Cursor executes them; retain HITL state transitions. |
| `docs/planning/ARCHITECTURE-PLANNING.md` | Codex planning lane, Kiro review route, Probe v2, actor-neutral stop. |
| `docs/planning/EXECUTION-PLANNING.md` | Codex planning lane, Kiro rejection-to-Ryan route, Cursor downstream execution, Probe v2, actor-neutral stop. |
| `docs/planning/EXECUTE-TASK.md` | Cursor implementation lane; Codex remains upstream planner rather than post-handoff auditor; separate PR Steward grant; Probe v2 and actor-neutral stop. |
| `docs/planning/VERIFY-PLANNING.md` | Codex predeclares VERIFY checks/stub; Cursor supplies mechanical evidence; Kiro or Ryan-named independent lane signs; Copilot is targeted when warranted; Ryan gates; Probe v2 and actor-neutral stop. |
| `docs/planning/REVISE-PLANNING.md` | Codex owns plan revision; implementation findings return through Ryan; Probe v2 and actor-neutral stop. |
| `docs/planning/CONTRACT.md` | Human mirror of Planning Guide Contract v2, including exact Probe v2 enforcement and actor-neutral HITL marker. |
| `planning_contract.py` | Contract/Probe v2 constants, actor-neutral stop marker, exact Probe v2 validation, and v2 diagnostics/docstrings. |
| `docs/MODEL-WORKFLOW.md` | Route planning to Codex, implementation to Cursor, discovery/neutral framing to Crush; describe Grok only as a replaceable model inside Cursor. |
| `config/agent-protocol.md` | Add a compact Codex-planning route while preserving the 360-word TEAM_CHARTER ceiling and all existing Sol-High/PR Steward anchors. |

### Authored fitness-test files

| Path | Required change |
|------|-----------------|
| `tests/test_planning_guide_contract.py` | Update fixtures and assertions for Contract/Probe v2; prove a stale Probe v1 guide and missing actor-neutral stop both fail. |
| `tests/test_team_charter_protocol.py` | Add compact-slice anchors for Codex planning and Cursor implementation while retaining the 360-word ceiling and existing gate tests. |
| `tests/protocol_slice_helpers.py` | Add both Copilot generated instruction surfaces to exact TEAM_CHARTER parity checks. |
| `tests/test_planning_lane_ownership.py` | **New.** One focused fitness test for live lane ownership, Kiro/Copilot non-substitution, rejection routing, arc classification, PR Steward separation, and banned stale live phrases. |

### Generated surfaces expected to change

These files must be changed only by
`bash scripts/generate-agent-protocol.sh`, never hand-edited:

- `config/agent-protocol-mcp.txt`
- `config/cursor-rules-convmem.mdc.example`
- `config/codex-agents-convmem.example.md`
- `config/kiro-steering-convmem.example.md`
- `config/copilot-agents-convmem.example.md`
- `config/copilot-instructions-convmem.example.md`
- `config/crush-rules-convmem.example.md`

The generator also rewrites the following files, but this arc expects them to
remain byte-identical because they do not consume `TEAM_CHARTER`:

- `config/agent-protocol-mcp-shell.txt`
- `docs/chatgpt-pack/custom-instructions.txt`
- `docs/chatgpt-pack/README.md`

Any diff in those three files is a STOP, not an invitation to expand scope.

### Evidence-only file

- `docs/plans/VERIFY-codex-planning-cursor-execution.md` — Cursor may replace
  pending cells with mechanical evidence after implementation. Changing its
  scope, observables, or sign-off rules routes to Ryan and Codex.

### Immutable during Cursor execution

- `docs/plans/ARCHITECTURE-codex-planning-cursor-execution.md`
- `docs/plans/EXECUTION-2026-07-24-codex-planning-cursor-execution.md`

Cursor must not revise the governing plans it is implementing.

## Contract and lane mapping

### Planning Guide Contract v2

`planning_contract.py` remains the executable source of truth. Implement v2 as
one atomic migration:

1. Set `CONTRACT_VERSION = "v2"` and `PROBE_VERSION = "v2"`.
2. Replace `Cursor must stop here.` with the required marker
   `Active phase lane must stop here.`; retain `Await HITL.`.
3. Validate that every active phase guide's Phase Initialization contains the
   exact current Probe Version value, not merely the field label.
4. Keep the existing required headings and metadata fields unchanged.
5. Update diagnostics and docstrings to identify Contract v2.
6. Update every active guide to Probe v2 and the actor-neutral stop in the same
   commit. Mixed v1/v2 guides are never an accepted intermediate tip.
7. Mirror those semantics in `docs/planning/CONTRACT.md` and focused tests.

Do not add orchestration state, a role DSL, or a general transaction/state
machine to the contract.

### Phase ownership after migration

| Phase/artifact | Active responsibility | Independent boundary |
|----------------|-----------------------|----------------------|
| Architecture Planning | Codex authors one direction and stops | Kiro reviews; Ryan approves |
| Execution Planning | Codex decomposes the approved direction and stops | Kiro rejection goes to Ryan before Codex revises; Ryan approves |
| VERIFY plan/stub | Codex predeclares checks during planning | Codex cannot self-sign |
| Execute Task | Cursor implements the approved plan and supplies mechanical evidence | Material mismatch returns to Ryan/Codex; no silent replanning |
| Verify execution | Cursor runs mechanical checks | Kiro or Ryan-named independent lane signs; Copilot audits targeted technical properties when warranted; Ryan gates |
| Revise Planning | Codex revises plans after Ryan routes findings | No implementation in the revision lane |

Characters such as Risk Reviewer remain cognitive styles, not authority. Model
weights remain replaceable implementation details, not lanes.

## Ordered tasks

| ID | Deliverable | Depends on | Execution lane | Gate |
|----|-------------|------------|----------------|------|
| **T1** | Contract/Probe v2 and all five phase guides migrate atomically to the neutral stop and target lane mapping | Entry gates | Cursor | Focused contract tests; doctor reports Contract v2; no mixed probes |
| **T2** | Full charter, lane registry, planning doctrine, model routing, and compact protocol agree on Codex planning / Cursor implementation and all carry-forward boundaries | T1 | Cursor | Lane-ownership fitness test; compact slice ≤360 words |
| **T3** | Fitness tests cover the live source chain; canonical protocol is regenerated into all applicable surfaces and is byte-idempotent | T2 | Cursor | Focused protocol tests; exact parity on seven execution surfaces; three non-consuming outputs unchanged |
| **T4** | Complete mechanical verification, tabletop scenarios, branch evidence, and implementation handoff; fill only mechanical cells in the VERIFY stub | T3 | Cursor | Full suite, doctor/doctor-v1, diff/path checks, pushed exact tip; stop for Ryan |

Tasks are serial because T2 text depends on the v2 phase contract and T3
generated output depends on the final canonical protocol. No parallel writer is
authorized.

## Ordered edits

### T1 — Contract and phase guides

1. Add failing/updated v2 cases in `tests/test_planning_guide_contract.py`,
   including a stale Probe v1 rejection.
2. Change `planning_contract.py` to Contract/Probe v2 and exact probe-value
   validation.
3. Update `docs/planning/CONTRACT.md`.
4. Update the five active phase guides together, preserving their phase-specific
   responsibilities and changing only lane ownership needed by this direction.
5. Update `docs/PLANNING-PROTOCOL.md` doctrine and workflow wording.
6. Run the focused planning-contract tests and `convmem doctor` before T2.

### T2 — Governing ownership sources

1. Update the full charter Mermaid nodes and prose: Codex creates/revises
   Architecture and Execution plans; Cursor builds only after Ryan authorization.
2. Add a governing Planning row/route without creating a new agent product,
   engineering Role, or Delivery role.
3. State the non-substituting boundaries in their authoritative homes:
   - Kiro rejection of an Execution Plan goes to Ryan before Codex revises.
   - Copilot implementation-audit PASS cannot replace Kiro sign-off on the
     governing plan.
   - The full charter retains the general rule that PR Steward activation is a
     separate Ryan grant and is never inferred. For this governance arc, the
     implementation brief and VERIFY require any such grant only after Ryan
     reviews Cursor's implementation handoff; do not globally prohibit a
     separately authorized Steward from delivering other docs-only work.
   - During the three-arc observation period, Crush proposes the defect
     classification and Ryan confirms it; the artifact author does not classify
     its own defects definitively.
4. Preserve verbatim intent in the full charter:
   “No arrow grants the receiving lane permission to merge, deploy, write the
   ledger, or self-advance the phase.”
5. Update `docs/AGENT-ROLES.md` without adding Planner/Reviewer rows to the
   agent table: Codex's lane description and routing prose carry planning;
   Functions remain in phase guides.
6. Update `docs/MODEL-WORKFLOW.md`: Codex is the default planning surface;
   Crush/Qwen remains discovery, neutral framing, and optional synthesis;
   Cursor with a Ryan-selected Grok or other model remains implementation.
7. Update only the canonical `TEAM_CHARTER` slice in
   `config/agent-protocol.md`. Add the compact planning row and shorten redundant
   PR Steward prose as needed without changing its protected anchors or raising
   the 360-word ceiling.

The compact protocol need not duplicate every full-charter carry-forward. It
must give the unambiguous planning route and link the full charter; detailed
rejection/classification/Steward sequencing stays in its authoritative full
charter and phase guides.

### T3 — Fitness functions and generated surfaces

1. Add `tests/test_planning_lane_ownership.py` with exact positive anchors and
   stale-live-text bans across the charter, lane registry, phase guides,
   Planning Protocol, Model Workflow, and canonical protocol.
2. Extend `tests/test_team_charter_protocol.py` with a Codex-planning anchor and
   preserved Cursor-implementation anchor; do not raise `WORD_CEILING = 360`.
3. Extend `tests/protocol_slice_helpers.py` parity coverage to:
   - `config/copilot-agents-convmem.example.md`
   - `config/copilot-instructions-convmem.example.md`
4. Run `bash scripts/generate-agent-protocol.sh` once after canonical edits.
5. Run it a second time under the hash check below to prove byte idempotence.
6. Confirm only the seven consuming generated surfaces changed and all seven
   contain the exact canonical `TEAM_CHARTER` body once.

### T4 — Evidence and handoff

1. Run the focused commands, then the full suite and doctor checks below.
2. Execute and record each tabletop scenario in the VERIFY stub with post-change
   `file:line` evidence.
3. Record the exact implementation base, subject tip, branch, changed-path set,
   and command exit codes.
4. Commit in coherent units and push immediately after every commit with an
   explicit refspec.
5. Fill mechanical VERIFY cells only. Do not fill Kiro, Copilot, BugBot, or
   Ryan verdict cells on their behalf.
6. Stop and hand off to Ryan. Do not open a PR, comment to trigger BugBot,
   activate PR Steward, deploy generated files, merge, or write the ledger
   without the corresponding separate authority.

## Generated-surface command and idempotence proof

Run from the repository root:

```bash
bash scripts/generate-agent-protocol.sh

protocol_outputs=(
  config/agent-protocol-mcp.txt
  config/agent-protocol-mcp-shell.txt
  config/cursor-rules-convmem.mdc.example
  config/codex-agents-convmem.example.md
  config/kiro-steering-convmem.example.md
  config/copilot-agents-convmem.example.md
  config/copilot-instructions-convmem.example.md
  docs/chatgpt-pack/custom-instructions.txt
  docs/chatgpt-pack/README.md
  config/crush-rules-convmem.example.md
)
sha256sum "${protocol_outputs[@]}" > /tmp/convmem-protocol-first.sha256
bash scripts/generate-agent-protocol.sh
sha256sum -c /tmp/convmem-protocol-first.sha256
```

The second generator run and hash check must exit `0`.

## Focused verification commands

```bash
python -m pytest -q \
  tests/test_planning_guide_contract.py \
  tests/test_planning_lane_ownership.py \
  tests/test_team_charter_protocol.py \
  tests/test_bounded_autonomy_protocol.py \
  tests/test_doctor_alone_before_brief.py \
  tests/test_mcp_after_tier_a.py \
  tests/test_mcp_shell_profile.py

convmem doctor
convmem doctor --v1

git diff --check
```

Stale live ownership text must return no matches in the named live sources:

```bash
if rg -n \
  'Cursor creates architecture plan|Cursor creates execution plan|Cursor revises architecture|Cursor revises execution plan|Cursor owns architecture, execution planning, and implementation|Codex read-only if Ryan requests (direction|plan) audit|Codex audit is post-handoff only|Architecture, planning, cross-doc, long reasoning — default lead' \
  docs/inter-model/TEAM-CHARTER-2026-07-06.md \
  docs/AGENT-ROLES.md \
  docs/PLANNING-PROTOCOL.md \
  docs/planning \
  docs/MODEL-WORKFLOW.md \
  config/agent-protocol.md; then
  echo 'FAIL: stale live lane assignment found'
  exit 1
fi
```

The generator's non-consuming outputs must have no diff against the
implementation base:

```bash
git diff --exit-code <implementation-base-sha> -- \
  config/agent-protocol-mcp-shell.txt \
  docs/chatgpt-pack/custom-instructions.txt \
  docs/chatgpt-pack/README.md
```

## Full verification commands

Run only after focused verification passes:

```bash
python -m pytest -q
git diff --check
git status --short
```

Any unrelated existing test failure is reported with its exact command and
output; it is not fixed as a drive-by change.

## Manual tabletop scenario evidence

Cursor records PASS/FAIL and post-change `file:line` evidence for each scenario
in the VERIFY stub. These are repository-local traces; they do not require or
authorize deployment of user-level rules.

| ID | Scenario | Required route |
|----|----------|----------------|
| S1 | Ryan asks for a cross-cutting plan | Codex authors Architecture Direction on a planning branch, Kiro reviews, and the phase stops for Ryan; no implementation. |
| S2 | Ryan approves an Execution Plan and Cursor finds a material authorization mismatch | Cursor stops and returns the mismatch to Ryan/Codex; it does not replan or broaden scope. |
| S3 | Kiro rejects the Execution Plan | Rejection goes to Ryan; Codex cannot revise until Ryan routes it back. |
| S4 | Copilot issues PASS on the implementation but no Kiro plan PASS exists | The governing plan gate remains blocked; Copilot cannot substitute for Kiro. |
| S5 | Ryan has reviewed Cursor's implementation and wants Codex to deliver the PR | PR Steward remains inactive until Ryan issues a new, bounded grant naming the repository, base, scope, and mutations. |
| S6 | A defect is found during the three-arc observation period | Crush proposes `planning escape`, `implementation defect`, `review discovery`, or `lane violation`; Ryan confirms; the artifact author does not decide. |
| S7 | A receiving lane sees a passing test or review | No merge, deploy, ledger write, or phase self-advance authority is inferred. |

## External review and review sequencing

Because this arc changes executable doctor-contract behavior in
`planning_contract.py`, Execute should record BugBot as `required` unless Ryan
changes the final scope so the diff is genuinely docs-only. BugBot and Copilot
are independent and non-substituting.

The required order is:

1. Kiro PASS on this governing Execution Plan tip.
2. Ryan approval to implement.
3. Cursor implementation, tests, commits, pushes, and mechanical handoff.
4. Ryan reviews the implementation handoff.
5. If Ryan wants PR Steward, Ryan issues a separate bounded grant now—not
   before or by inference from this plan.
6. A PR-native BugBot result must match the accepted subject tip; every finding
   is fixed or Ryan accepts it in writing.
7. GitHub Copilot performs the targeted implementation audit when Ryan invokes
   it. Copilot PASS does not replace Kiro's plan sign-off or BugBot evidence.
8. Kiro or another Ryan-named independent lane supplies the applicable final
   design/technical sign-off, then Ryan owns the GATE and merge decision.

No PR creation, review-trigger comment, external deployment, or GitHub mutation
is authorized by this Execution Plan.

## Stop conditions

Cursor stops and reports to Ryan if any of these occur:

- Kiro has not passed this exact plan tip, or Ryan has not approved it.
- The implementation base does not contain the approved Architecture,
  Execution Plan, and VERIFY stub.
- A required change falls outside the exact authored/generated/evidence file
  set above.
- Contract/Probe v2 cannot land atomically across all active guides.
- The compact protocol cannot retain all protected semantics within 360 words.
- A generated non-consuming output changes.
- A material architecture, scope, authorization, security, or public-contract
  decision appears.
- A focused or full gate fails for a reason inside scope and the correction
  would change the approved direction.
- BugBot is required but no separately authorized PR/comment route exists, or
  BugBot evidence does not match the subject tip.
- A deployment, merge, PR Steward activation, ledger write, or self-advance
  would be needed.

## Rollback

- **Before merge:** Ryan can reject or abandon the implementation branch; no
  deployed surface changes because deployment is out of scope.
- **After merge but before deployment:** revert the governance arc as one
  reviewed change, restore Contract/Probe v1 and all five guides together,
  regenerate from the reverted canonical protocol, and rerun focused/full
  gates. Never leave mixed v1/v2 guides.
- **After a separately authorized deployment:** first land and verify the
  repository revert; Ryan must then separately authorize deployment of the
  reverted generated artifacts. Do not use destructive reset or ad hoc edits
  to user-level rules.
- **Observation-period outcome:** three-arc evidence may justify a new
  architecture decision, but it never silently reverses this one.

## Cursor implementation brief

```text
WHO
Cursor is the sole implementation writer for this arc. Codex authored the
approved Architecture and Execution plans. Kiro owns governing plan sign-off;
Copilot owns only a separately invoked targeted audit; Ryan owns every gate.

WHAT
Implement docs/plans/EXECUTION-2026-07-24-codex-planning-cursor-execution.md
exactly: Contract/Probe v2, Codex planning, Cursor execution, independent
review, canonical protocol regeneration, fitness tests, and evidence.

WHEN / BASE
Begin only after Kiro PASS and Ryan approval of the exact Execution Plan tip.
Default: Ryan merges the planning artifacts to main; fetch origin and use
`convmem work start feat codex-planning-cursor-execution --worktree` from that
updated origin/main. Confirm the approved plans are present before editing.

WHY
Separate governing plan authorship from implementation without weakening Kiro,
Copilot, BugBot, Ryan, deployment, merge, or ledger gates.

HOW
Execute T1 through T4 serially. Edit only the exact file set. Generate surfaces
only with scripts/generate-agent-protocol.sh. Run focused tests, doctor,
doctor --v1, full pytest, diff/path checks, and tabletop scenarios. Commit in
coherent units and push each commit immediately with an explicit refspec.

MUST NOT
Do not revise the Architecture or Execution Plan; deploy generated rules; open
or mutate a PR; trigger BugBot; activate PR Steward; merge; write the ledger;
self-sign; self-advance; or treat Copilot PASS as Kiro plan approval. A material
mismatch returns to Ryan/Codex. Fill only mechanical VERIFY evidence.

HANDOFF
Return branch, base SHA, tip SHA, commits, exact changed paths, command exit
codes, tabletop results, residuals, and the external-review applicability row.
Then stop for Ryan. PR Steward, if desired, requires a new Ryan grant after
Ryan reviews this implementation handoff.
```

## Arc VERIFY companion

- Path: `docs/plans/VERIFY-codex-planning-cursor-execution.md`
- Status: stub with predeclared checks; mechanical evidence pending Execute
- Template: `docs/plans/VERIFY-TEMPLATE.md`
- Independent sign-off and Ryan GATE remain pending after mechanical work

## Execute entry

First task: T1 only after Kiro PASS and Ryan approval of this exact Execution
Plan tip. No self-transition is authorized.

Active phase lane must stop here. Await HITL.
