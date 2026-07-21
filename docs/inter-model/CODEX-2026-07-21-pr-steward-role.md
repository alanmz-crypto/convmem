# PR Steward Delivery role (v0.1)

**To:** GitHub Copilot audit lane (audit), Kiro (sign-off), Ryan (merge + separate deploy)
**From:** Cursor (execution of governance/protocol runbook)
**Date:** 2026-07-21
**Branch:** `docs/2026-07-21-pr-steward-role`
**PR:** _(fill after open — tip SHA stays external)_

**Live ops:** `convmem brief` only. Do not treat this post as corpus truth.

---

## Review target

**Exact artifact:** the final pushed tip of branch `docs/2026-07-21-pr-steward-role`, identified by literal commit SHA in the external review request / PR comment. A tracked file cannot name its own commit SHA. Both the GitHub Copilot audit lane and Kiro must review that same immutable tip. Verdicts are returned externally and are not committed back into the reviewed artifact. Any new commit or base change after PASSes stales both reviews unless fresh PASSes are obtained.

---

## What changed

| Surface | Change |
|---------|--------|
| [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md) | PR Steward Delivery-role overlay: activation/brief, judgment boundary, owns, must/must-not, exhaustive GitHub mutation allowlist, report-don't-fix, escalation, v0.1 maturity, jargon |
| [`AGENT-ROLES.md`](../AGENT-ROLES.md) | Delivery role vocabulary; PR Steward subsection; one-line Codex default-actor note |
| [`config/agent-protocol.md`](../config/agent-protocol.md) `TEAM_CHARTER` | Compressed existing prose; pinned PR Steward routing row + brief-bound clause; ≤350 words |
| [`tests/test_team_charter_protocol.py`](../../tests/test_team_charter_protocol.py) | Positive anchors + banned-dump strings for PR Steward |
| Five TEAM_CHARTER surfaces | Regenerated; ChatGPT pack / mcp-shell unchanged by design |

---

## Ask

| Who | Ask |
|-----|-----|
| **GitHub Copilot audit lane** | PASS/FAIL on literal tip + base SHA: Delivery-role ≠ Role/Lane; mutation allowlist fidelity; compact budget + fitness; generated-surface parity; no deploy |
| **Kiro** | Sign-off that the same tip preserves governing design intent and lane boundaries |
| **Ryan** | After both PASSes on same tip+base: merge; **separately** authorize `deploy-agent-protocol.sh` if live surfaces should carry the overlay |

---

## Out of scope

- `docs/role-charters.md`
- Live deploy / external agent-surface writes
- R2b implementation (PR #65 architecture is merged; R2b implementation remains separate and unauthorized)
- Ledger `convmem record`

---

## Bootstrap authority

PR merge makes the charter canonical **in-repo**. Agents claiming the overlay in practice still require Ryan's separate deploy authorization.
