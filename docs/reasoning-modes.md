# Reasoning Modes

Answers one question: **How should I think?**

Cognitive modes the single planner adopts per phase. These are not agent
personalities and not engineering **Roles** (those live in
[`role-charters.md`](role-charters.md)).

---

## Revise Planning

Adopt all modes simultaneously during revision.

| Mode | Reasoning style | Borrows from |
|------|-----------------|--------------|
| **Plan Auditor** | Adversarial; every claim needs evidence or `UNVERIFIED(owner)` | Codex lane discipline, Role 6 (Tech Writer) |
| **Claims Verifier** | file:line citation before confident prose | [`retro-template.md`](retro-template.md) §2 |
| **Risk Reviewer** | repro-before-fix; name residual risks | Role 5 (SRE), Zeller digest |
| **Prioritizer** | drop stale P0s; branch vs `main` honesty | Role 7 judgment |
| **Process Steward** | countermeasures must land in register, charter, or code — prose-only is not a valid destination | retro loop, standing register |

When auditing process claims, also load engineering **Roles** via
[`role-charters.md`](role-charters.md), [`role-mapping.md`](role-mapping.md),
and [`standing-checks-register.md`](standing-checks-register.md).

---

## Architecture Planning

*TBD — Architect, Systems Thinker, Risk Reviewer (placeholder).*

---

## Execution Planning

*TBD — Task Decomposer, Dependency Mapper (placeholder).*

---

## Execute Task

Adopt Implementer + Test-First Reviewer during normal implementation. Add
Debug Investigator when the active failure branch applies.

| Mode | Reasoning style | Borrows from |
|------|-----------------|--------------|
| **Implementer** | Minimal scoped change; match repo conventions; respect lane must-nots | [`EXECUTE-TASK.md`](planning/EXECUTE-TASK.md), [`AGENT-ROLES.md`](AGENT-ROLES.md) |
| **Test-First Reviewer** | Adversarial self-check before handoff — would independent review accept this? | Codex lane discipline, `pytest` / doctor gates |
| **Debug Investigator** | Repro-before-fix; isolate; compare pass/fail; no architectural conclusions before repro | [`zeller-builder-digest.md`](builder-reference/zeller-builder-digest.md), Role 5 (SRE) |
