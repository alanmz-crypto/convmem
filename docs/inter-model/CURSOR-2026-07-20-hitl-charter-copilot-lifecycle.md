# HITL charter — Copilot lifecycle addendum + corrective repairs

**To:** GitHub Copilot audit lane (audit), Kiro (sign-off), Ryan (approve deploy)
**From:** Kiro (initial corrective execution) · GitHub Copilot (finish corrections)
**Date:** 2026-07-20
**Branch:** `docs/2026-07-19-hitl-charter-delegation-sol-high-gate`
**PR:** [#54](https://github.com/alanmz-crypto/convmem/pull/54)
**Original handoff (0d2cbf7):** [`CURSOR-2026-07-19-hitl-charter-delegation-sol-high.md`](CURSOR-2026-07-19-hitl-charter-delegation-sol-high.md) — preserved at `0d2cbf7`; not modified by this corrective commit.

**Live ops:** `convmem brief` only. Do not treat this post as corpus truth.

---

## Review target

**Exact artifact:** the final pushed tip of branch `docs/2026-07-19-hitl-charter-delegation-sol-high-gate`, identified by literal commit SHA in the external review request. A tracked file cannot name its own commit SHA. Both the GitHub Copilot audit lane and Kiro must review that same immutable tip. Verdicts are returned externally and are not committed back into the reviewed artifact.

---

## Why a corrective commit was needed

The `dc65fef` addendum (Kiro, 2026-07-20) introduced these issues that required repair before same-SHA reviews could be requested:

| Issue | Detail |
|-------|--------|
| Invalid Mermaid | `\n` in node labels is not valid Mermaid syntax; diagram would not render |
| Sol-High = Copilot audit lane conflation | Compact slice and full charter treated Sol-High as synonymous with the Copilot audit lane rather than a separate scarce resource |
| `defer` as valid verdict | Five-field template allowed `PASS\|FAIL\|defer` — but `defer` is never an opposing written verdict and must not satisfy the gate |
| Auth-R1 as universal policy | Authorization codes (R1–R8) are specific to the embedding-eval execution plan; they were presented as general policy rather than a labeled worked example |
| DeepSeek R1 ambiguity | Bare "R1" was ambiguous between DeepSeek R1 (model) and Auth-R1 (phase code) |
| GitHub Copilot + OpenAI Codex conflated | One table row merged the governing Copilot audit lane with the OpenAI Codex product surface and its tooling paths |

**Prior "no extra review" waiver is void** because the corrective commit changes reviewer identity and role allocation (Codex → Copilot audit lane), mandatory stages → conditional routing, and the Sol-High conflict pair definition — these are not cosmetic edits.

---

## What this corrective commit changes (relative to dc65fef)

| Surface | Change |
|---------|--------|
| [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md) | Valid Mermaid TD flowchart (decision diamonds, `<br/>` labels); Sol-High removed from lifecycle diagram and separated in prose; auth codes demoted to labeled worked example with `Auth-R1`…`Auth-R8` prefix; DeepSeek R1 vs Auth-R1 disambiguation added; Sol-High gate requires PASS or FAIL only (`defer` disqualifies); DeepSeek R1 model output added as disqualifier; five-field template updated with exact semantic labels; Jargon TL;DR updated |
| [`config/agent-protocol.md`](../config/agent-protocol.md) `TEAM_CHARTER` | ≤360 words; Sol-High explicitly "separate scarce resource, not the same as Copilot audit lane"; five-field gate uses exact semantic field names matching full charter; `defer` excluded in three places |
| [`docs/AGENT-ROLES.md`](../AGENT-ROLES.md) | **GitHub Copilot audit lane** and **OpenAI Codex** are now separate rows; Codex row retains all its own tooling paths; Copilot row is governing conditional audit lane |
| [`CURSOR-2026-07-19-hitl-charter-delegation-sol-high.md`](CURSOR-2026-07-19-hitl-charter-delegation-sol-high.md) | Restored to exact `0d2cbf7` content — the Copilot addendum that was appended in `dc65fef` is removed; historical `0d2cbf7` post is the canonical record for that commit |
| `tests/test_team_charter_protocol.py` | New fitness test: five execution surfaces, ChatGPT pack omission, five-field semantic anchors, 360-word ceiling, `defer` not treated as valid opposing verdict |
| Generated surfaces | Regenerated after corrective edits; idempotence verified (second run produces no diff) |

## Finish corrections after `404bf6b`

- Restored Ryan's full specialist-review, architecture, execution-plan, implementation, evaluation, and promotion topology instead of treating the compressed Stage 0–8 diagram as the governing lifecycle.
- Corrected the embedding-project worked example: Authorization R1 is tracked implementation; R2a/R2b are isolation and immutable capture; C0 freezes evaluation inputs; R3/R4/R5/R7/R8 retain their supplied phase meanings. The Gate 1/Gate 2 runbook is linked only for the constraints it actually defines.
- Made Kiro explicitly non-implementing and review-required in the full charter, compact protocol, bounded-autonomy rule, and role registry.
- Removed remaining "Copilot Sol-High class" language and separated the GitHub Copilot audit lane from the Sol-High adjudicator by name.
- Changed same-SHA closeout so verdicts are returned externally against the final immutable tip rather than committed into—and thereby changing—the reviewed artifact.

**Not changed:** `deploy-agent-protocol.sh` not run. PR #54 title/body not edited (left as audit-history). PR #52 R2a implementation is independent — do not block or auto-resume it.

---

## Corrective commit range

| SHA | Description |
|-----|-------------|
| `0d2cbf7` | Original: comparative advantage + Sol-High gate (Codex framing) |
| `dc65fef` | Copilot addendum (issues listed above — superseded by this corrective commit) |
| `404bf6b` | Initial precision repairs by Kiro |
| Finish correction | Restores Ryan's lifecycle topology, corrects authorization semantics, and makes Kiro's non-implementation boundary explicit |

---

## Ask

| Who | Ask |
|-----|-----|
| **GitHub Copilot audit lane** | Audit the final immutable tip: lifecycle topology fidelity; authorization-example accuracy; separation of the Copilot audit lane and Sol-High adjudicator; complete five-field gate; generated-surface parity; tests and compact budget. |
| **Kiro** | Read-only sign-off that the same tip preserves governing design intent, lane allocation, authorization boundaries, and the explicit Kiro non-implementation boundary. |
| **Ryan** | After both verdicts on same tip SHA: approve `bash scripts/deploy-agent-protocol.sh` |

---

## Same-SHA review binding

Verdicts are bound to the tip SHA at time of review. If any further corrective commit is made after verdicts are issued, each reviewer must explicitly state whether their verdict carries forward after inspecting the delta — silence does not constitute carry-forward.

---

## Out of scope

- Deploying live agent surfaces (`deploy-agent-protocol.sh` not run)
- Modifying PR #54 title or body
- PR #52 R2a implementation — may proceed independently without waiting for PR #54

---

## Deploy block status

| Item | State |
|------|--------|
| Canonical charter + protocol SSoT | Corrected on branch |
| Generated surfaces | Regenerated; idempotence verified |
| Deploy live configs | **Blocked** — needs GitHub Copilot audit + Kiro sign-off + Ryan |
| GitHub Copilot audit | Requested — same tip SHA |
| Kiro sign-off | Requested — same tip SHA |
| PR #52 | Independent — may proceed |

---

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| **GitHub Copilot audit lane** | Governing conditional technical-review lane; VS Code Copilot; separate from Sol-High |
| **OpenAI Codex** | Separately installed product; not the governing audit lane; retains its own tooling paths |
| **Sol-High adjudicator** | Separate scarce conflict-resolution resource invoked only under the hard gate |
| **Authorization R1 … R8** | Historical phase codes in the embedding-project worked example; not universal policy terms |
| **DeepSeek R1** | The adversarial-review model; unrelated to Authorization R1 |
| **Same-SHA review binding** | Both reviewers must assess the exact same branch tip; further commits stale prior verdicts unless explicitly carried forward |
