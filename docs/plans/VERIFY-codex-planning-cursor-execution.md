# Verify Plan — codex-planning-cursor-execution

```
Planning Status

Phase:        Verify (codex-planning-cursor-execution)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Codex (predeclared checks only); Cursor (mechanical evidence); Kiro / Ryan-named independent lane (sign-off); GitHub Copilot (targeted audit when invoked); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Subject / tip:** `<implementation branch and exact tip SHA>`  
**Implementation base:** `<exact SHA containing approved planning artifacts>`  
**PR(s):** `<pending; no PR authority is granted by the plan>`  
**Architecture:**
[`ARCHITECTURE-codex-planning-cursor-execution.md`](ARCHITECTURE-codex-planning-cursor-execution.md)  
**Execution:**
[`EXECUTION-2026-07-24-codex-planning-cursor-execution.md`](EXECUTION-2026-07-24-codex-planning-cursor-execution.md)  
**Goal:** Prove the governance arc establishes Codex planning, Cursor
implementation, independent review, actor-neutral HITL stops, and exact
generated-surface parity without deployment or authority expansion.

**Report format:** For every row, record **PASS / FAIL / SKIP** and one line of
exact evidence. BugBot-only V0 rows may use **N/A (exempt)** only when Execute
recorded a valid exemption. An applicable SHA mismatch is **FAIL**, never SKIP.

**GATE** = Ryan process step; not a mechanical agent PASS.

**Flow:** Complete V0–V7 → Mechanical PASS|FAIL → independent sign-off → Ryan
GATE.

---

## Human consequence (read this first)

**Consequence:** If this arc passes, Ryan can approve plans from Codex and hand
their bounded implementation to Cursor while retaining independent Kiro,
Copilot, BugBot, merge, deployment, and ledger gates. If any ownership or
authorization check fails, the existing workflow remains authoritative.

### 5 Ws

| | |
|---|---|
| **Who** | Codex plans; Cursor implements; Kiro signs governing design; Copilot audits targeted implementation properties; Crush proposes observation-period classifications; Ryan confirms and gates. |
| **What** | A governance and Planning Contract v2 migration, not a runtime feature or agent orchestrator. |
| **When** | Verify the exact post-implementation tip before merge or deployment. |
| **Why** | Separate planning from implementation without collapsing independent review or human authority. |
| **How** | Contract tests, lane fitness tests, generated parity, full regression, tabletop traces, and exact-tip review evidence. |

**TL;DR:** Acceptance requires one coherent v2 rule chain, Cursor-only
implementation, independent sign-off, and no inferred external authority.

**Honest limits / caveats:** This repository-local verification does not prove
deployed user-level rules changed; deployment is deliberately excluded and
requires a separate Ryan authorization.

### Merge reading

- Architecture:
  [`ARCHITECTURE-codex-planning-cursor-execution.md`](ARCHITECTURE-codex-planning-cursor-execution.md)
- Execution:
  [`EXECUTION-2026-07-24-codex-planning-cursor-execution.md`](EXECUTION-2026-07-24-codex-planning-cursor-execution.md)
- This VERIFY: self
- Full charter:
  [`../inter-model/TEAM-CHARTER-2026-07-06.md`](../inter-model/TEAM-CHARTER-2026-07-06.md)
- Active handoff: [`../inter-model/LATEST.md`](../inter-model/LATEST.md) — name
  the applicable active bullet at fill time

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Exact authored, test, generated, and VERIFY evidence files named in the Execution Plan | Product/runtime features; backup, write-gate, dedupe, purge, retrieval, Neutral/Office Team work |
| Contract/Probe v2 and five active phase guides | Generic orchestration, role DSL, new lane, or model pinning |
| Full charter, lane registry, model routing, compact protocol | Historical plans/reviews/transcripts/ledger rewrites |
| Seven consuming generated surfaces | User-level rule deployment; MCP registration; external configuration |
| Mechanical evidence and independent review | Merge, ledger write, phase self-advance, or inferred PR authority |

---

## V0 — Preconditions and external review

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse <implementation-base-sha>
git status --short
convmem doctor
```

### External Review evidence input

Execute must fill this row. The plan expects `required` because
`planning_contract.py` changes executable doctor behavior; Verify confirms but
does not re-decide applicability.

| Field | Value |
|-------|-------|
| `gate_applicability` | `required` (planned; Execute confirms) |
| `reason` | Executable Planning Contract/doctor correctness behavior changes |
| `subject_tip_sha` | `<pending>` |
| `bugbot_reviewed_sha` | `<pending>` |
| `result` | `<clean | findings | unreachable>` |
| `finding_disposition` | `<per finding: fixed | ryan_accepted | none>` |
| `authority_reference` | `<separate Ryan PR/comment grant or n/a>` |

| ID | Check | PASS / FAIL / SKIP / N/A |
|----|-------|---------------------------|
| V0a | Subject tip and implementation base resolve; base contains the Ryan-approved Architecture, Execution Plan, and this stub | Pending |
| V0b | Cursor's implementation branch and changed-path set are recorded | Pending |
| V0c | Execute applicability decision and reason are present | Pending |
| V0d | If required: PR-native BugBot-reviewed SHA equals subject tip SHA; mismatch is FAIL | Pending |
| V0e | Every BugBot finding is fixed or Ryan-accepted at the subject tip; outage requires Ryan's tip-specific acceptance | Pending |
| V0f | Worktree contains no unrelated pre-existing changes attributed to this arc | Pending |

---

## V1 — Exact path and historical-evidence lock

```bash
git diff --name-only <implementation-base-sha>...<subject-tip-sha>
git diff --check <implementation-base-sha>...<subject-tip-sha>
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V1a | Every changed path is in the Execution Plan's authored, generated, or evidence-only file set | Pending |
| V1b | Architecture and Execution Plan are unchanged by Cursor | Pending |
| V1c | No historical plan, review, transcript, ledger artifact, runtime subsystem, or unrelated file changed | Pending |
| V1d | `git diff --check` passes | Pending |

---

## V2 — Planning Contract/Probe v2

```bash
python -m pytest -q tests/test_planning_guide_contract.py
convmem doctor
convmem doctor --v1
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V2a | `planning_contract.py` reports Contract v2 and Probe v2 | Pending |
| V2b | Every active guide declares exact Probe v2 | Pending |
| V2c | Every active guide contains `Active phase lane must stop here.` and `Await HITL.` | Pending |
| V2d | A stale Probe v1 fixture fails validation | Pending |
| V2e | A missing actor-neutral stop fixture fails validation | Pending |
| V2f | Doctor and doctor-v1 report the planning contract healthy | Pending |

---

## V3 — Lane ownership and non-substitution boundaries

```bash
python -m pytest -q tests/test_planning_lane_ownership.py
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V3a | Codex owns Architecture, Execution, VERIFY-plan, and Revise planning; Cursor owns implementation | Pending |
| V3b | Kiro rejection of an Execution Plan routes to Ryan before Codex may revise | Pending |
| V3c | Copilot implementation-audit PASS explicitly does not replace Kiro sign-off on the governing plan | Pending |
| V3d | PR Steward activation, if any, requires a separate Ryan grant after Ryan reviews Cursor's implementation | Pending |
| V3e | Three-arc classification is proposed by Crush and confirmed by Ryan; artifact authors do not definitively self-classify | Pending |
| V3f | “No arrow grants the receiving lane permission to merge, deploy, write the ledger, or self-advance the phase.” remains true in the governing charter | Pending |
| V3g | Grok is a replaceable model inside Cursor, not a lane or durable governance identity | Pending |
| V3h | Banned stale live ownership phrases return no matches in the Execution Plan's source set | Pending |

---

## V4 — Canonical protocol and generated parity

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

python -m pytest -q \
  tests/test_team_charter_protocol.py \
  tests/test_bounded_autonomy_protocol.py \
  tests/test_doctor_alone_before_brief.py \
  tests/test_mcp_after_tier_a.py \
  tests/test_mcp_shell_profile.py
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V4a | Canonical TEAM_CHARTER is ≤360 words and names Codex planning / Cursor implementation | Pending |
| V4b | Exact canonical body appears once on all seven consuming execution surfaces, including both Copilot outputs | Pending |
| V4c | Second generator run is byte-identical | Pending |
| V4d | MCP-shell and both ChatGPT-pack outputs remain unchanged from implementation base | Pending |
| V4e | Existing Sol-High, Kiro, Copilot, and PR Steward compact anchors still pass | Pending |

---

## V5 — Focused and full regression

```bash
python -m pytest -q \
  tests/test_planning_guide_contract.py \
  tests/test_planning_lane_ownership.py \
  tests/test_team_charter_protocol.py \
  tests/test_bounded_autonomy_protocol.py \
  tests/test_doctor_alone_before_brief.py \
  tests/test_mcp_after_tier_a.py \
  tests/test_mcp_shell_profile.py

python -m pytest -q
git diff --check
git status --short
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V5a | Focused suite passes | Pending |
| V5b | Full suite passes, or an unrelated pre-existing failure is reported without drive-by repair | Pending |
| V5c | Diff is whitespace-clean and worktree status is explained | Pending |

---

## V6 — Manual repository-local scenarios

For each row, cite the post-change `file:line` route. Do not deploy user-level
rules merely to run these tabletop traces.

| ID | Scenario | Expected result | PASS / FAIL / SKIP |
|----|----------|-----------------|--------------------|
| V6a | Cross-cutting planning request | Codex plans; Kiro reviews; Ryan gates; no implementation | Pending |
| V6b | Cursor finds material authorization mismatch during Execute | Cursor stops and returns to Ryan/Codex; no silent replanning | Pending |
| V6c | Kiro rejects Execution Plan | Ryan receives rejection before Codex revises | Pending |
| V6d | Copilot implementation audit passes without Kiro plan PASS | Gate remains blocked; no substitution | Pending |
| V6e | Ryan wants PR Steward after reviewing Cursor handoff | Separate bounded Ryan grant is required | Pending |
| V6f | Three-arc defect needs classification | Crush proposes; Ryan confirms; artifact author does not decide | Pending |
| V6g | A lane receives passing evidence | No merge/deploy/ledger/self-advance authority is inferred | Pending |

---

## V7 — Independent sign-off and Ryan GATE

The verifier performs no cleanup or correction.

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V7a | Kiro written PASS on the exact governing Execution Plan tip is cited | Pending |
| V7b | GitHub Copilot written PASS/FAIL on the exact implementation tip and residuals is cited when Ryan invokes the targeted audit | Pending |
| V7c | Copilot result is recorded as non-substituting for Kiro plan sign-off and BugBot | Pending |
| V7d | Kiro or Ryan-named independent implementation/design sign-off names the exact subject tip | Pending |
| V7e | Ryan separately reviews/accepts the implementation, any PR Steward grant, merge, deployment, and durable conclusion | Pending — Ryan GATE |

---

## Evidence log

```text
VERIFY-codex-planning-cursor-execution
implementation base: <sha>
subject tip: <sha>
branch: <branch>
runner: Cursor
timestamp: <ISO-8601>
V0: pending
V1: pending
V2: pending
V3: pending
V4: pending
V5: pending
V6: pending
V7: pending
Mechanical: PENDING
Kiro governing-plan sign-off: PENDING
Copilot targeted audit: PENDING / NOT YET INVOKED
BugBot: PENDING
Independent implementation sign-off: PENDING
Ryan GATE: PENDING
```

Active phase lane must stop here. Await HITL.
