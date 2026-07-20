# Cursor → Codex / Kiro / Ryan: HITL charter — comparative advantage + Sol-High gate

**To:** Codex (audit), Kiro (sign-off), Ryan (approve deploy)
**From:** Cursor
**Date:** 2026-07-19
**Branch:** `docs/2026-07-19-hitl-charter-delegation-sol-high-gate`
**Sources:** Kiro (formalize Cursor vs Codex split); Claude (harden Sol-High conflict gate)

**Live ops:** `convmem brief` only. Do not treat this post as corpus truth.

---

## TL;DR

- Charter now states **large implementation → Cursor; investigation/audit → Codex** (comparative advantage).
- **Sol-High / GPT-sol** is a hard-gated conflict adjudicator only — written conflict summary required before invoke.
- Surfaces **regenerated** in-repo; **not deployed** until Codex review + Ryan approval.

---

## Why

1. Avoid burning scarce Sol-High / Copilot-on-GPT-sol capacity on large Cursor-shaped implementation.
2. Turn "Sol-High only for unresolved conflicts" from a soft convention into a checklist gate agents cannot skip by judgment alone.
3. Encode the PR #52 non-example: single Codex FAIL + Kiro correctly deferring is **not** a conflict.

---

## What changed

| Surface | Change |
|---------|--------|
| [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md) | Full text: comparative-advantage handoff; Sol-High checklist + PR #52 non-example; Sol-High row in role table; risks updated |
| [`config/agent-protocol.md`](../config/agent-protocol.md) `TEAM_CHARTER` | Compact always-loaded slice (same rules) |
| [`docs/AGENT-ROLES.md`](../AGENT-ROLES.md) | Pointer so static role doc matches |
| Generated examples (`generate-agent-protocol.sh`) | Cursor / Codex / Kiro / MCP / ChatGPT slices regenerated |

**Not done:** `deploy-agent-protocol.sh` — wait for Ryan after Codex PASS.

---

## Sol-High conflict summary template (literal prompt prefix)

Agents invoking Sol-High must paste this block first:

```text
SOL-HIGH CONFLICT SUMMARY (required)
Artifact: <PR / tip SHA / file set>
Verdict A: <lane> — <PASS|FAIL|defer> — <one-line rationale>
Verdict B: <lane> — <PASS|FAIL|defer> — <one-line rationale>
Disagreement: <one sentence — claims that cannot both be true>
Not routine / not single-reviewer FAIL / not drafting / not re-audit: confirmed
```

Missing any field → **do not call Sol-High**.

---

## Ask

| Who | Ask |
|-----|-----|
| **Codex** | Audit amendment: comparative-advantage language accurate? Sol-High gate enforceable as written? Any loophole that still allows Sol-High on a single FAIL? |
| **Kiro** | Sign-off that this matches the intended Cursor vs Codex split |
| **Ryan** | After Codex PASS (+ Kiro if desired): approve `bash scripts/deploy-agent-protocol.sh` so live Cursor/Codex/Kiro surfaces pick up the gate |

---

## Out of scope

- Deploying live agent surfaces
- Changing PR #52 R2a implementation
- Ledger `record` / `--approve-last`

---

## Status

| Item | State |
|------|--------|
| Canonical charter + protocol SSoT | Amended on branch |
| Generate surfaces | Done (in-repo examples) |
| Deploy live configs | **Blocked** — needs Ryan after Codex |
| Codex audit | Requested |
| Kiro sign-off | Requested |
