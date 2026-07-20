# HITL team charter — full review (Claude Cloud)

**To:** all Tier A/B agents + Ryan  
**From:** Claude Cloud (review) · Cursor (integration)  
**Date:** 2026-07-06  
**Amended:** 2026-07-19 — Copilot lifecycle, conditional routing, Sol-High Copilot↔Kiro gate (corrected 2026-07-20)
**Status:** active  
**Always-loaded subset:** `config/agent-protocol.md` → `TEAM_CHARTER` section (via `generate-agent-protocol.sh` + `deploy-agent-protocol.sh`)  
**Source:** [HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md](HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md)

**Naming note (2026-07-19):** The governing technical-review lane is now **GitHub Copilot** / **Copilot**. Historical posts and error inventory rows that say "Codex" are preserved as-is — they record what happened at the time. Codex-specific tooling references (session paths, `bash -lc` sandbox retry, `CODEX-DEEPSEEK-VERIFY.md`, `codex_rollout_jsonl`) remain unchanged as product/tooling aliases.

---

## 1. Verdict: team roles mostly correct

The canonical role table holds up. Every lane in the Willowy Hollow sprint graded **Correct** or **Mostly correct** — no critical gap. The weakness is **naming**, not assignment: operators saying "DeepSeek" when they mean **Crush lane** could misroute a future supervisor.

---

## 2. Role confusion map

| Confusing phrase | What it actually means | Why it matters |
|------------------|------------------------|----------------|
| "DeepSeek is hunting bugs" | **Crush** (Tier A) hunting bugs using DeepSeek V4 weights | DeepSeek *row* = Tier B synthesis API (`convmem ask`). Routing "bug task → DeepSeek" hits wrong surface. |
| "Index what you wrote" | Ambiguous Track A vs Track B | Caused models to index findings log only, skip chat. Fixed via phrasebook — recurrence risk if phrasebook not default. |
| "Session close" | Some models inferred "propose record" | Handoff (`index`) ≠ ledger approval (`record --approve-last`). |

**Fix:** name by **lane**. "Crush found it" not "DeepSeek found it." "Ingest the chat" not "index what you wrote."

---

## 3. Error inventory

### Confirmed errors (protocol/ops — no corpus corruption)

| Error | Impact | Status |
|-------|--------|--------|
| Track A skipped, only log indexed | Next model lost chat context | Fixed — phrasebook + Track A/B table |
| Kiro offered `record` at task end | False session-close signal | Fixed — Kiro-specific rule |
| Codex `history.jsonl` indexed | Lost assistant turns | Fixed — `codex_rollout_jsonl` adapter |
| Per-finding record impulse | Ledger noise | Fixed — umbrella-record-only |
| Uncommitted prod work | Git drift | Not memory error — commit separately |

Lab smoke (`smoke-synthesis.sh`, PASS 2026-07-06): no prod Chroma corruption when guards used.

### Not errors

- `--propose` draft `2c96` rejected — pipeline worked; draft wrong on merit
- Lab `LATEST.md` ≠ prod — intentional
- 37% index coverage — gap, not wrong data
- `write_lane` FAIL lab cwd + prod config — guard working
- Linker Phase 2 held — deferred by design

---

## 4. Governing lifecycle and lane charter (amended 2026-07-19)

### Governing lifecycle

The following flow shows the standard review-and-implementation pipeline. **GitHub Copilot audit-lane nodes are conditional** — they apply "when warranted" or "when necessary", not on every task. Sol-High is a separate scarce adjudicator invoked only under a hard conflict gate (see §4 Sol-High gate).

```mermaid
flowchart TD
  A["Stage 0: Ryan — task intake + authorization scope"] --> B
  B["Stage 1: Crush — discovery, search, findings (Tier A)"] --> C
  C{"Copilot audit warranted?"}
  C -- "yes" --> D["Stage 2: GitHub Copilot audit lane —<br/>code / safety / isolation review"]
  C -- "no" --> E
  D --> E["Stage 3: Kiro — design review + sign-off"]
  E --> F{"Substantial implementation?"}
  F -- "yes" --> G["Stage 4: Cursor — implementation<br/>(complete handoff packet)"]
  F -- "no" --> H
  G --> H{"Copilot verify warranted?"}
  H -- "yes" --> I["Stage 5: GitHub Copilot audit lane —<br/>targeted post-impl verification"]
  H -- "no" --> J
  I --> J["Stage 6: Kiro — milestone sign-off"]
  J --> K["Stage 7: Track A handoff (all surfaces)"]
  K --> L["Stage 8: Ryan — merge to main +<br/>record approve-last"]
```

**Lane responsibilities in this flow:**
- **Crush** — facts, framing, corpus search, surface findings; does not self-approve or write `record`
- **GitHub Copilot audit lane** — code-grounded technical review; conditional; does not implement, does not infer live authorization
- **Cursor** — architecture, planning, implementation; receives complete handoff packet from upstream lanes
- **Kiro** — governing design review and final gate sign-off; uses `--signer kiro-review` only on Ryan's cue
- **Claude / ChatGPT** — methodology review, synthesis when needed; no code edits or prod writes
- **Ryan** — authorization gating, deploy decision, merge to `main`, final disposition; only lane that runs `--approve-last`

**Sol-High is not in this flow.** It is a separate scarce token resource invoked only when the GitHub Copilot audit lane and Kiro have issued materially conflicting written verdicts on the same artifact and same revision. See §4 Sol-High gate.

**Stage narrative (brief):**

- **Stage 0** — Ryan defines task + authorization scope. Note: "R1" here refers to the first authorization phase code in the embedding-eval execution plan (see §4 worked example below) — distinct from DeepSeek R1 (the model), which is unrelated to task intake.
- **Stage 1** — Crush (Tier A shell + MCP read) discovers, searches, surfaces findings.
- **Stage 2** — GitHub Copilot audit lane (when warranted): independent code / safety / isolation audit. Does not implement; does not infer live authorization.
- **Stage 3** — Kiro: design review and sign-off.
- **Stage 4** — Cursor (when substantial implementation is needed): executes with complete handoff packet (scope, constraints, surfaces, acceptance tests, stop conditions, evidence).
- **Stage 5** — GitHub Copilot audit lane (when necessary): targeted post-impl verification or recheck.
- **Stage 6** — Kiro: milestone sign-off. Checks implementation matches design intent.
- **Stage 7** — Whoever closes: Track A session index + Track B if a log was written. Handoff ≠ record.
- **Stage 8** — Ryan only: merges to `main`, runs `record --approve-last`, tags milestones.

---

### Role table (governing — forward-looking)

| Phase | Owner (lane) | Must not |
|-------|--------------|----------|
| Bug discovery | **Crush** (shell + MCP read) | self-approve fixes; write `record`; merge to `main` |
| Independent audit (when warranted) | **GitHub Copilot** | new `logs/*.md` unless Ryan asks; merge to `main`; substantial implementation Cursor can execute; infer live authorization from scope |
| Design / sign-off | **Kiro** | volunteer `record` at task end; merge to `main`; create `feat/`/`fix/` branches |
| Implementation (convmem) | **Cursor** | client WP in same session; merge to `main` |
| Implementation (client WP) | **Cursor / Ryan** | convmem ledger writes |
| Memory ingest | **Whoever closes session** | Track A **and** B — never one alone |
| Durable conclusions | **Ryan only** | per-finding records; agents never `--approve-last` |
| Merge to `main` | **Ryan only** | agents never merge or force-push `main` |
| Conflict adjudication (token-scarce) | **Sol-High** (GPT-sol / Copilot Sol-High class) | routine execution; single-reviewer FAIL; drafting; re-audits; call without written conflict summary |
| Orchestration / strategy | **ChatGPT / Claude Cloud** | code edits; prod writes |
| Synthesis retrieval | **DeepSeek API** (`convmem ask`) | primary bug author |

---

### Lane routing (work-type to default lane)

| Work type | Default lane | Copilot involvement |
|-----------|-------------|---------------------|
| Large implementation | **Cursor** | Not involved — do not route implementation to Copilot |
| Investigation / feasibility | **Crush** | May escalate to Copilot audit when warranted |
| Safety / isolation audit | **GitHub Copilot** | Primary; targeted scope only |
| Evidence verify / recheck | **GitHub Copilot** | Targeted; do not rerun uncontested findings |
| Design review | **Kiro** | Not involved |
| Conflict adjudication | **Sol-High** | Only under hard gate (see below) |
| Ledger write / approve | **Ryan** | Not involved |

---

### Copilot invocation rule

**Allow-list — invoke Copilot when:**
- Independent safety or isolation audit is warranted (not every task)
- Targeted post-implementation verification needed (Stage 5)
- Evidence verification on a specific contested finding

**Do-not-invoke list:**
- Substantial implementation that Cursor can execute
- Routine execution or mindless coding work
- Re-auditing uncontested findings
- Drafting documents or protocol text
- As a replacement for a missing Cursor handoff packet

Do not burn Copilot (or Sol-High) cycles on work that belongs to Cursor's comparative advantage: large implementation with complete scope, constraints, affected surfaces, acceptance tests, stop conditions, and required evidence.

---

### Authorization sequence — worked example (embedding-eval execution plan)

The authorization phase codes below are **specific to the embedding-model evaluation execution plan** ([`docs/plans/EXECUTION-embedding-model-eval.md`](../plans/EXECUTION-embedding-model-eval.md)). They are cited here as a worked example of how a multi-phase authorized task looks — they are **not** universal policy terms that apply to all convmem work.

**Disambiguation:** "R1" in this context means the first authorization phase of this specific execution plan (task intake + adversarial diagnosis). It is entirely distinct from **DeepSeek R1** (the language model), which has no role in task authorization.

| Code | Meaning in this plan |
|------|----------------------|
| **Auth-R1** | Task intake, adversarial diagnosis, initial scope |
| **Auth-R2a** | Isolated config/dirs phase (hermetic; no live corpus writes) |
| **Auth-R2b** | Extended isolation variant |
| **B-Accept** | Acceptance gate for Auth-R2a/R2b output before live corpus contact |
| **C0** | Checkpoint before live corpus writes begin |
| **Auth-R3** | Controlled live phase with gated corpus writes |
| **Auth-R4–R5** | Extended live phases |
| **Auth-R7** | Pre-promotion verification |
| **Auth-R8** | Cleanup; promotion requires a fresh Auth-R1 |

No agent may infer live authorization from outcome or task context — authorization must be explicit in the brief or Ryan's instruction. Auth-R1 adversarial diagnosis is **not** a Sol-High conflict-summary substitute (see §4 Sol-High gate).

---

### Phrasebook

- **Ingest your chat** → index session transcript (Track A)
- **Index the log** → findings/audit markdown only (Track B)
- **Ingest everything** → both tracks
- **Find a stopping point** / **wrap up** / **park it** → soft close: stabilize, push, verbal summary, Track A. **No record block.** See `SESSION-CLOSE-RECORD.md § Stopping point`.
- **Closing** / **end session** / **record block** → hard close: Track A + output `convmem record` block for Ryan to run

**Willowy Hollow one-command handoff:**

```bash
bash ~/Projects/convmem/scripts/sync-willowyhollow-handoff.sh
```

---

### Sol-High conflict gate (hard precondition — revised 2026-07-20)

**Sol-High is a separate scarce adjudicator.** It is not a step in the normal lifecycle and is not the same as the GitHub Copilot audit lane. Sol-High may only be invoked under the hard gate below.

**Hard gate:** Sol-High may only be invoked when the **GitHub Copilot audit lane** and **Kiro** have each issued a **written verdict** (PASS or FAIL — not defer, not silence, not abstention) on the **same review target and the same revision**, and those verdicts are **materially in conflict**.

Before any Sol-High / GPT-sol call, the calling agent **must** produce a written conflict summary as a literal prompt prefix. All five fields are required:

1. **Same artifact** — PR number, branch tip SHA, or file set under review. Both verdicts must be against this exact artifact.
2. **GitHub Copilot audit-lane written verdict** — PASS or FAIL + key rationale. (Not defer; not silence; not a comment from a different revision.)
3. **Kiro written verdict** — PASS or FAIL + key rationale. (Not defer; not silence; not a comment from a different revision.)
4. **Material proposition in conflict** — one sentence stating the specific factual claim that both verdicts cannot simultaneously be true.
5. **Negative confirmation** — explicitly confirm the call is not for: single-reviewer FAIL, deferral by either reviewer, abstention, silence, missing verdict, incomplete verdict, or verdicts against different revisions.

**Disqualifying conditions (any one blocks Sol-High):**
- Only one reviewer has issued a written PASS or FAIL
- Either reviewer deferred, abstained, was silent, or did not review the same revision
- A verdict is incomplete or references a different artifact
- The disagreement is about scope or framing, not a material factual conflict on the artifact
- Auth-R1 adversarial diagnosis is the only opposing input — task intake is not a review verdict
- DeepSeek R1 (the model) output is the only opposing input — model output is not a lane verdict

**`defer` is never an opposing written verdict.** A reviewer who defers has not issued a verdict. Deferral by either lane means the gate is not met — route to the deferring lane for resolution first.

If any field is missing or a disqualifying condition applies, **do not invoke Sol-High**. Route to: Cursor (implementation), GitHub Copilot audit lane (recheck), or Kiro (design sign-off).

**Non-example (PR #52 pattern — do not call Sol-High):** A Codex audit (under today's Copilot lane rule) issues FAIL; Kiro correctly defers or has not issued a written verdict on the same revision — there is no A-vs-B material conflict. That is a single-reviewer FAIL awaiting Cursor fix or Kiro sign-off, not a conflict. Invoking Sol-High here wastes scarce tokens.

**Conflict summary template** (paste as literal prompt prefix before any Sol-High call):

```text
SOL-HIGH CONFLICT SUMMARY (required — all fields must be present)
Artifact: <PR number / branch tip SHA / file set — exact>
GitHub Copilot audit-lane verdict: <PASS|FAIL> — <one-line rationale>
Kiro verdict: <PASS|FAIL> — <one-line rationale>
Material proposition in conflict: <one sentence — the specific factual claim both verdicts cannot both be true>
Negative confirmation: not single-FAIL / not deferral / not abstention / not silence / not missing / not incomplete / not different revision — confirmed
```

**Shared surface:** this gate lives in the always-loaded `TEAM_CHARTER` slice (`config/agent-protocol.md`) so Cursor, Kiro, and the Copilot audit lane all see the same rule.

---

## 5. Risks

**Fourth reviewer before fixes?** No — Crush → Copilot → Kiro is sufficient if Copilot audits **every** finding slated for implementation, not a sample. Volume (82 findings) makes partial audit the real risk. Sol-High is **not** a routine fourth reviewer — only a conflict adjudicator under the hard gate above.

**Naming risk:** "DeepSeek" in operator language → future router keys off wrong tier. Fix vocabulary now (compact charter in always-loaded rules). Similarly, "Codex" in operator language for the audit lane should migrate to "Copilot" in forward-looking instructions; historical posts are preserved as-is.

**Token scarcity / mis-delegation:** Burning Sol-High or Copilot on large Cursor-shaped implementation (or calling Sol-High on a single FAIL with no opposing verdict) wastes scarce high-cost capacity. Comparative-advantage routing + Sol-High checklist are the mitigations.

**Authorization inference:** Agents must not infer live authorization from task context or outcome. Authorization must be explicit (R-code in brief or Ryan's instruction). R1 adversarial diagnosis is not a Sol-High conflict-summary substitute.

**Ledger noise:** Collapse per-finding Crush verification records before umbrella sprint record, or umbrella summarizes noisy ledger.

---

## 6. Experiment readiness

| Tier | Description | Ready? |
|------|-------------|--------|
| **1** | **Shared memory bus** — manual Crush→Codex→Kiro handoff with indexed archive | **Yes — bug sprint** ([BUG-SPRINT-SUCCESS-2026-07-06.md](BUG-SPRINT-SUCCESS-2026-07-06.md)) |
| **1.5** | Proactive discovery (`unresolved()` triage surfacing) | **Deferred** — post-sprint; gate = `tier_1_5_gate: UNLOCKED` in sprint checklist |
| **2** | 3+ clean handoffs without Track A/B or record correction | **2–4 weeks habit soak** — checklist §7 |
| **3** | **Orchestration** — state file + notify on index (no auto-invoke) | **Lab design spike** — not prod until Tier 1 evidence |

**Do not call Tier 1 "orchestration."** See [ORCHESTRATION-APPROACH-2026-07-06.md](ORCHESTRATION-APPROACH-2026-07-06.md).

---

## 7. Tier 2 handoff habit checklist

Goal: **3 consecutive clean handoffs** before Tier 2 habit is proven.

| Handoff # | Track A indexed? | Track B if log? | Record offered wrongly? | Phrasebook used? |
|-----------|------------------|-----------------|-------------------------|------------------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

Ryan fills after each model switch. "Clean" = all yes except Record (must be no unless Ryan said record block).

---

## 8. Optional record (Ryan runs manually)

```bash
convmem record \
  --relates-to dec_prop_20260705_151004_1e00 \
  --summary "Team-roles audit: sprint lanes confirmed; Crush≠DeepSeek naming fixed in protocol SSoT" \
  --rationale "Claude Cloud review found no critical role errors; compact TEAM_CHARTER in agent-protocol + full doc indexed; phrasebook and lane table deployed to all surfaces via generate/deploy." \
  --author claude-cloud
convmem record --approve-last
```

---

## Related

- [docs/AGENT-ROLES.md](../AGENT-ROLES.md)
- [docs/MODEL-WORKFLOW.md](../MODEL-WORKFLOW.md)
- [docs/WILLOWYHOLLOW-SESSION-LOOP.md](../WILLOWYHOLLOW-SESSION-LOOP.md)

---

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| **Lane** | Agent surface + capability tier + must-not rules (not a job title) |
| **GitHub Copilot audit lane** | Governing conditional technical-review lane (formerly "Codex" in pre-2026-07-19 posts); VS Code Copilot surface; not the same as Sol-High |
| **Sol-High** | GPT-sol / Copilot Sol-High class; scarce conflict adjudicator only under hard gate; separate from the Copilot audit lane |
| **Crush lane** | Tier A shell agent for bug discovery; may run DeepSeek V4 weights but is still Crush |
| **DeepSeek R1** | The DeepSeek R1 language model — entirely distinct from Authorization R1 below |
| **Auth-R1 … Auth-R8** | Authorization phase codes for the embedding-eval execution plan only; see worked example §4 and [`EXECUTION-embedding-model-eval.md`](../plans/EXECUTION-embedding-model-eval.md) |
| **Track A** | Session chat index (`convmem index --file <transcript>`) |
| **Track B** | Log artifact index (`logs/*.md` via sync scripts) |
| **Tier A / B / C** | Capability tiers: shell+MCP / MCP-only / paste-only; defined in `config/agent-protocol.md` |
| **Handoff ≠ record** | Track A session index at handoff; `convmem record --approve-last` only when Ryan says record block |
| **Comparative advantage** | Large implementation → Cursor; investigation/audit/safety → Copilot audit lane |
