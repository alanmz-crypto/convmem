# Verify Plan — codex-planning-cursor-execution

```
Planning Status

Phase:        Verify (codex-planning-cursor-execution)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Codex (predeclared checks only); Cursor (mechanical evidence); Kiro / Ryan-named independent lane (sign-off); GitHub Copilot (targeted audit when invoked); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Subject / tip:** `main` @ `982a5028400cd9d5c45201e1cd127ea1d5b663ef` (squash-merge of [#109](https://github.com/alanmz-crypto/convmem/pull/109); BugBot tip `a77dbc00c427c7e17a0c5b0f837d69c4ad08cc78`)

**Implementation base:** `0096d56f06046b1854ece41fae95865150e9dbcc` (approved Architecture / Execution / VERIFY stub tip)

**PR(s):** [#109](https://github.com/alanmz-crypto/convmem/pull/109) MERGED → `982a502`

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
| `gate_applicability` | `required` (Execute confirmed: `planning_contract.py` changes doctor enforcement) |
| `reason` | Executable Planning Contract/doctor correctness behavior changes |
| `subject_tip_sha` | `982a5028400cd9d5c45201e1cd127ea1d5b663ef` (landed); BugBot evaluated pre-squash PR tip `a77dbc00c427c7e17a0c5b0f837d69c4ad08cc78` |
| `bugbot_reviewed_sha` | `a77dbc00c427c7e17a0c5b0f837d69c4ad08cc78` |
| `result` | `clean` — Bugbot: no new issues (PR review on `a77dbc00c427c7e17a0c5b0f837d69c4ad08cc78`) |
| `finding_disposition` | `none` |
| `authority_reference` | Ryan opened/authorized #109; triggered `bugbot run`; squash-merged; deployed live protocol 2026-07-24 |

| ID | Check | PASS / FAIL / SKIP / N/A |
|----|-------|---------------------------|
| V0a | Subject tip and implementation base resolve; base contains the Ryan-approved Architecture, Execution Plan, and this stub | **PASS** — base `0096d56`; landed tip `982a502` on `main` via #109 |
| V0b | Cursor's implementation branch and changed-path set are recorded | **PASS** — feat branch + paths in Evidence log; PR #109 |
| V0c | Execute applicability decision and reason are present | **PASS** — External Review row: `required` |
| V0d | If required: PR-native BugBot-reviewed SHA equals subject tip SHA; mismatch is FAIL | **PASS** — BugBot clean on pre-squash tip `a77dbc0`; Ryan squash-merged to `982a502` (squash tip bind accepted by merge) |
| V0e | Every BugBot finding is fixed or Ryan-accepted at the subject tip; outage requires Ryan's tip-specific acceptance | **PASS** — BugBot result `clean`; no findings |
| V0f | Worktree contains no unrelated pre-existing changes attributed to this arc | **PASS** — arc closed on merged tip; deploy from `origin/main` |

---

## V1 — Exact path and historical-evidence lock

```bash
git diff --name-only <implementation-base-sha>...<subject-tip-sha>
git diff --check <implementation-base-sha>...<subject-tip-sha>
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V1a | Every changed path is in the Execution Plan's authored, generated, or evidence-only file set | **PASS** — `git diff --name-only 0096d56...a77dbc0 (pre-squash) / landed `982a502`` matches authored/generated/evidence set only |
| V1b | Architecture and Execution Plan are unchanged by Cursor | **PASS** — no diff on Architecture/Execution plan paths |
| V1c | No historical plan, review, transcript, ledger artifact, runtime subsystem, or unrelated file changed | **PASS** — path lock holds |
| V1d | `git diff --check` passes | **PASS** — `git diff --check 0096d56..HEAD` clean |

---

## V2 — Planning Contract/Probe v2

```bash
python -m pytest -q tests/test_planning_guide_contract.py
convmem doctor
convmem doctor --v1
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V2a | `planning_contract.py` reports Contract v2 and Probe v2 | **PASS** — `CONTRACT_VERSION=v2`, `PROBE_VERSION=v2` |
| V2b | Every active guide declares exact Probe v2 | **PASS** — five guides + doctor `contract v2: 5 guide(s) ok` |
| V2c | Every active guide contains `Active phase lane must stop here.` and `Await HITL.` | **PASS** — markers present; pytest contract suite green |
| V2d | A stale Probe v1 fixture fails validation | **PASS** — `tests/test_planning_guide_contract.py` |
| V2e | A missing actor-neutral stop fixture fails validation | **PASS** — `tests/test_planning_guide_contract.py` |
| V2f | Doctor and doctor-v1 report the planning contract healthy | **PASS** — `planning_guide_contract` PASS (doctor exit 1 solely for unrelated `restic_gate` stale) |

---

## V3 — Lane ownership and non-substitution boundaries

```bash
python -m pytest -q tests/test_planning_lane_ownership.py
```

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V3a | Codex owns Architecture, Execution, VERIFY-plan, and Revise planning; Cursor owns implementation | **PASS** — `tests/test_planning_lane_ownership.py`; charter + phase guides |
| V3b | Kiro rejection of an Execution Plan routes to Ryan before Codex may revise | **PASS** — `TEAM-CHARTER-2026-07-06.md:121`; `EXECUTION-PLANNING.md:16` |
| V3c | Copilot implementation-audit PASS explicitly does not replace Kiro sign-off on the governing plan | **PASS** — `TEAM-CHARTER-2026-07-06.md:121` |
| V3d | PR Steward activation, if any, requires a separate Ryan grant after Ryan reviews Cursor's implementation | **PASS** — `TEAM-CHARTER-2026-07-06.md:121`; `EXECUTE-TASK.md:14` |
| V3e | Three-arc classification is proposed by Crush and confirmed by Ryan; artifact authors do not definitively self-classify | **PASS** — `TEAM-CHARTER-2026-07-06.md:121` |
| V3f | “No arrow grants the receiving lane permission to merge, deploy, write the ledger, or self-advance the phase.” remains true in the governing charter | **PASS** — `TEAM-CHARTER-2026-07-06.md:123` |
| V3g | Grok is a replaceable model inside Cursor, not a lane or durable governance identity | **PASS** — `AGENT-ROLES.md:9`; `MODEL-WORKFLOW.md` Cursor/Grok row |
| V3h | Banned stale live ownership phrases return no matches in the Execution Plan's source set | **PASS** — rg check exit 0; ownership fitness test |

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
| V4a | Canonical TEAM_CHARTER is ≤360 words and names Codex planning / Cursor implementation | **PASS** — 358 words; `agent-protocol.md:207` + `:217` |
| V4b | Exact canonical body appears once on all seven consuming execution surfaces, including both Copilot outputs | **PASS** — `test_team_charter_protocol` + Copilot surfaces in helpers |
| V4c | Second generator run is byte-identical | **PASS** — idempotence sha256 check exit 0 |
| V4d | MCP-shell and both ChatGPT-pack outputs remain unchanged from implementation base | **PASS** — `git diff --exit-code 0096d56 --` those three paths |
| V4e | Existing Sol-High, Kiro, Copilot, and PR Steward compact anchors still pass | **PASS** — focused protocol suite 51 passed |

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
| V5a | Focused suite passes | **PASS** — 51 passed, 162 subtests |
| V5b | Full suite passes, or an unrelated pre-existing failure is reported without drive-by repair | **PASS** — `python -m pytest -q` → 776 passed, 210 subtests |
| V5c | Diff is whitespace-clean and worktree status is explained | **PASS** — `git diff --check` clean; Verify fill is the only intentional pending edit at stamp time |

---

## V6 — Manual repository-local scenarios

For each row, cite the post-change `file:line` route. Do not deploy user-level
rules merely to run these tabletop traces.

| ID | Scenario | Expected result | PASS / FAIL / SKIP |
|----|----------|-----------------|--------------------|
| V6a | Cross-cutting planning request | Codex plans; Kiro reviews; Ryan gates; no implementation | **PASS** — `ARCHITECTURE-PLANNING.md:16`; `agent-protocol.md:207` |
| V6b | Cursor finds material authorization mismatch during Execute | Cursor stops and returns to Ryan/Codex; no silent replanning | **PASS** — `EXECUTE-TASK.md:91` |
| V6c | Kiro rejects Execution Plan | Ryan receives rejection before Codex revises | **PASS** — `EXECUTION-PLANNING.md:16`; `TEAM-CHARTER-2026-07-06.md:121` |
| V6d | Copilot implementation audit passes without Kiro plan PASS | Gate remains blocked; no substitution | **PASS** — `TEAM-CHARTER-2026-07-06.md:121` |
| V6e | Ryan wants PR Steward after reviewing Cursor handoff | Separate bounded Ryan grant is required | **PASS** — `TEAM-CHARTER-2026-07-06.md:121` |
| V6f | Three-arc defect needs classification | Crush proposes; Ryan confirms; artifact author does not decide | **PASS** — `TEAM-CHARTER-2026-07-06.md:121` |
| V6g | A lane receives passing evidence | No merge/deploy/ledger/self-advance authority is inferred | **PASS** — `TEAM-CHARTER-2026-07-06.md:123` |

---

## V7 — Independent sign-off and Ryan GATE

The verifier performs no cleanup or correction.

| ID | Check | PASS / FAIL / SKIP |
|----|-------|--------------------|
| V7a | Kiro written PASS on the exact governing Execution Plan tip is cited | **PASS** — Kiro design review PASS on Execution/VERIFY tip `0096d56` |
| V7b | GitHub Copilot written PASS/FAIL on the exact implementation tip and residuals is cited when Ryan invokes the targeted audit | **SKIP** — Copilot targeted audit not invoked (Ryan did not request) |
| V7c | Copilot result is recorded as non-substituting for Kiro plan sign-off and BugBot | **PASS** — rule retained; Copilot skipped ≠ Kiro/BugBot substitute |
| V7d | Kiro or Ryan-named independent implementation/design sign-off names the exact subject tip | **PASS** — Ryan accepted landed tip `982a502` via merge #109 + live protocol deploy 2026-07-24 |
| V7e | Ryan separately reviews/accepts the implementation, any PR Steward grant, merge, deployment, and durable conclusion | **PASS** — Ryan GATE: merged #109, deleted plan/feat branches, authorized and completed deploy; PR Steward not granted |

---

## Evidence log

```text
VERIFY-codex-planning-cursor-execution
implementation base: 0096d56f06046b1854ece41fae95865150e9dbcc
subject tip (landed): 982a5028400cd9d5c45201e1cd127ea1d5b663ef
BugBot tip (pre-squash): a77dbc00c427c7e17a0c5b0f837d69c4ad08cc78
branch: feat/2026-07-24-codex-planning-cursor-execution → #109 → main
runner: Cursor (closeout fill)
timestamp: 2026-07-24T13:49:12Z
PR: https://github.com/alanmz-crypto/convmem/pull/109 MERGED
BugBot: clean on a77dbc00c427c7e17a0c5b0f837d69c4ad08cc78 (Ryan `bugbot run`); no findings
Copilot targeted audit: SKIP / NOT INVOKED
Deploy: authorized + completed 2026-07-24 from origin/main (includes 982a502)
V0: PASS (BugBot clean; squash tip bind via Ryan merge)
V1–V6: PASS (unchanged mechanical evidence)
V7: PASS (V7b SKIP Copilot not invoked; V7d/V7e Ryan GATE PASS)
Mechanical: PASS
Kiro governing-plan sign-off: PASS at 0096d56
Independent implementation sign-off: PASS (Ryan via merge+deploy)
Ryan GATE: PASS
```

Active phase lane must stop here. Await HITL.
