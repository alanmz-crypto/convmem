# Handoff: HITL multi-agent orchestration lab — team roles audit for Claude Cloud

**Date:** 2026-07-06  
**From:** Cursor Auto (convmem session)  
**To:** Claude Cloud (Opus or Sonnet)  
**Purpose:** Review whether Ryan's Willowy Hollow + convmem work used **correct agent team roles**, whether **convmem-lab introduced errors**, and advise on a **competent team design** before a supervised multi-agent SDLC experiment. **No code edits** — return structured markdown Ryan can merge.

**Status:** open  
**Owner:** Claude Cloud (review) → Ryan (merge)  
**Sunset:** after role charter merged or experiment starts

---

## Context (60 seconds)

Ryan is preparing a **human-in-the-loop multi-agent orchestration pilot**:

> Local, event-driven, human-gated multi-agent software supervisor with shared memory.

**convmem (prod)** is the shared memory bus + policy + HITL ledger (~85% operationally ready).  
**convmem-lab** is the disposable coordination sandbox (~70% spike-complete; little graduated to prod).

The **live experiment** is Willowy Hollow practice (`willowyhollow-practice`, `:8081`): a Crush/DeepSeek code-review sprint (~82 findings), Codex audit, Kiro review, Cursor implementation of convmem ingest/protocol. **DeepSeek (via Crush) is actively hunting bugs** on the practice stack now.

Ryan needs Claude to judge: **Did we use the right team? Did the lab create errors? What team should run the next phase?**

---

## Read order in this archive

1. `HANDOFF.md` (this file)
2. `TEAM-ROLES-CANONICAL.md` — static role table from prod
3. `TEAM-ROLES-SPRINT-AUDIT.md` — what actually happened vs canon
4. `LAB-ERRORS-AND-GUARDRAILS.md` — lab mistakes, near-misses, what passed
5. `context/ORCHESTRATION-FRAMING.md` — professional terms + stability tiers
6. `context/MODEL-WORKFLOW.md` — prod vs lab cheat sheet
7. `context/WILLOWYHOLLOW-SESSION-LOOP.md` — client session loop + handoff script
8. `scripts/sync-willowyhollow-handoff.sh` — one-command Track A+B ingest
9. `ledger-ids.txt` — anchors for record suggestions

---

## What Claude Cloud should judge

### 1. Team role correctness

- Is the **static role table** (`AGENT-ROLES.md`) still right for a multi-agent SDLC pilot?
- **Crush running DeepSeek V4** for bug review — is that "Crush lane" or a mistaken "DeepSeek agent" role?
- **Codex** as independent verifier (audit markdown) — correct lane?
- **Kiro** as design reviewer / signer — correct, or over-scoped?
- **Cursor** as implementer on convmem infra — correct separation from client WP work?
- **DeepSeek API** (`convmem ask` synthesis) — should it ever touch bug-finding?
- **ChatGPT / Claude Cloud** — orchestration vs enrichment: who owns strategy charter?
- **Ryan** — human gate: is the split between handoff (`index`) vs record (`approve-last`) clear enough?

### 2. Errors introduced in the lab or sprint

Review `LAB-ERRORS-AND-GUARDRAILS.md` and flag:
- Protocol mistakes that **corrupted memory** (skipped chat ingest, wrong track, fake record ids)
- **Role bleed** (model did another agent's job badly)
- **Prod/lab cross-lane** risks (write guard — did we violate?)
- **convmem-lab** synthetic data or smoke failures that invalidate conclusions
- Things that are **not errors** (intentional lab/prod divergence, rejected `--propose` draft `2c96`)

### 3. Recommended team charter for next phase

Return a **role assignment table** for:

| Phase | Suggested owner | Must not do |
|-------|-----------------|-------------|
| Bug discovery | ? | ? |
| Independent audit | ? | ? |
| Design / sign-off | ? | ? |
| Implementation | ? | ? |
| Shared memory ingest | ? | ? |
| Durable conclusions | ? | ? |
| Orchestration / strategy | ? | ? |

Include **phrasebook** Ryan should use (ingest your chat / index the log / ingest everything / record block).

### 4. Experiment readiness

- Tier 1 (manual handoff experiment): ready now?
- Tier 2 (habit soak 2–4 weeks): what evidence is still missing?
- Tier 3 (event-driven supervisor): what new component is required beyond convmem?

---

## Expected output

1. **Verdict:** team roles mostly correct / need realignment / critical gaps
2. **Role confusion map** — where names (DeepSeek vs Crush) mislead operators
3. **Error inventory** — confirmed errors vs acceptable noise
4. **Revised team charter** (table + 1-page operating rules)
5. **Risks** — what breaks if DeepSeek keeps hunting bugs without Codex/Kiro in loop
6. **Optional:** `convmem record` block suggestion (Ryan runs manually) — only if a durable conclusion is warranted

Return **markdown only** — no code changes, no bulk index, no prod writes.

---

## Constraints

- Single user, single workstation; local-first corpus
- MCP read-only on prod; durable writes = `convmem record` + `--approve-last` (Ryan only)
- **Handoff ≠ record** — session ingest is not ledger approval
- **One umbrella record** at sprint end for bug review — not per-finding records
- Linker Phase 2 / autonomous supervisor **explicitly deferred** (habit gate)
- convmem-lab: **no MCP registration**; disposable fixtures

---

## Ledger anchors (`ledger-ids.txt`)

| Ledger id | Topic |
|-----------|-------|
| `dec_prop_20260623_161428_c311` | Protocol root (fallback `--relates-to`) |
| `dec_prop_20260629_213047_8f73` | Plans vs records; linker Phase 2 held |
| `dec_prop_20260629_150527_46f0` | Cross-project synthesis Phase 0 |
| `dec_prop_20260705_151004_1e00` | Lab S1–S5 + lab-reference shipped |
| `dec_prop_20260705_152603_2c96` | `--propose` trial draft **rejected** (not an error) |
| `obs_806985bc5697` | Agent-habit / coordination gate (open thread) |

---

## Ryan → Claude Cloud prompt

> Read `HANDOFF.md`, then `TEAM-ROLES-SPRINT-AUDIT.md` and `LAB-ERRORS-AND-GUARDRAILS.md`. We are preparing a HITL multi-agent orchestration experiment with convmem as shared memory. DeepSeek-in-Crush is hunting bugs on Willowy Hollow practice now. Tell us if our team roles have been correct, what errors the lab or sprint created, and what team charter we need for a competent final result. Markdown only.

---

## Files in this archive

```
handoff-hitl-orchestration-lab-2026-07-06/
├── HANDOFF.md
├── RYAN-PROMPT.txt
├── TEAM-ROLES-CANONICAL.md
├── TEAM-ROLES-SPRINT-AUDIT.md
├── LAB-ERRORS-AND-GUARDRAILS.md
├── ledger-ids.txt
├── context/
│   ├── AGENT-ROLES.md
│   ├── agent-protocol.md
│   ├── MODEL-WORKFLOW.md
│   ├── ROADMAP.md
│   ├── SYNTHESIS-STATUS.md
│   ├── LATEST.md
│   ├── ORCHESTRATION-FRAMING.md
│   ├── WILLOWYHOLLOW-SESSION-LOOP.md
│   ├── WILLOWYHOLLOW-TLDR.md
│   ├── convmem-lab-LAB.md
│   └── lab-reference-NOTES.md
├── scripts/
│   ├── sync-willowyhollow-handoff.sh
│   ├── sync-willowyhollow-findings-index.sh
│   └── sync-willowyhollow-audit-index.sh
└── willowyhollow/
    ├── AUDIT-EXCERPT.md
    └── FINDINGS-EXCERPT.md
```

**Tarball (repo root, gitignored):** `handoff-hitl-orchestration-lab-2026-07-06.tar.gz`

**Excluded:** full findings log, prod Chroma, secrets, PDFs, full source trees.
