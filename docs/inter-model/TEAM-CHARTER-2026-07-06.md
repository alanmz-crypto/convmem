# HITL team charter — full review (Claude Cloud)

**To:** all Tier A/B agents + Ryan  
**From:** Claude Cloud (review) · Cursor (integration)  
**Date:** 2026-07-06  
**Status:** active  
**Always-loaded subset:** `config/agent-protocol.md` → `TEAM_CHARTER` section (via `generate-agent-protocol.sh` + `deploy-agent-protocol.sh`)  
**Source:** [HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md](HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md)

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

## 4. Revised team charter (full table)

| Phase | Owner (lane, not model) | Must not do |
|-------|-------------------------|-------------|
| Bug discovery | **Crush** (shell + MCP read) | self-approve fixes; write `record` |
| Independent audit | **Codex** (shell, no MCP) | new `logs/*.md` unless Ryan asks; substantial implementation Cursor can execute |
| Design / sign-off | **Kiro** | volunteer `record` at task end — `--signer kiro-review` only on Ryan's cue |
| Implementation (convmem infra) | **Cursor** | client WP stack in same session as convmem infra |
| Implementation (client WP) | **Cursor / Ryan** | convmem ledger writes |
| Shared memory ingest | **Whoever closes session** | Track A **and** B — never one alone |
| Durable conclusions | **Ryan only** | agents never `--approve-last`; one umbrella record per sprint |
| Conflict adjudication (token-scarce) | **Sol-High** (GPT-sol / Copilot Sol-High class) | routine execution; single-reviewer FAIL; drafting; re-audits; any call without a conflict summary |
| Orchestration / strategy | **ChatGPT / Claude Cloud** | code edits; prod writes |
| Synthesis retrieval | **DeepSeek API** (`convmem ask`) | primary bug author |

**Phrasebook:**

- **Ingest your chat** → index session transcript (Track A)
- **Index the log** → findings/audit markdown only (Track B)
- **Ingest everything** → both tracks
- **Find a stopping point** / **wrap up** / **park it** → soft close: stabilize, push, verbal summary, Track A. **No record block.** See `SESSION-CLOSE-RECORD.md § Stopping point`.
- **Closing** / **end session** / **record block** → hard close: Track A + output `convmem record` block for Ryan to run

**Willowy Hollow one-command handoff:**

```bash
bash ~/Projects/convmem/scripts/sync-willowyhollow-handoff.sh
```

### Delegate by comparative advantage

Substantial implementation belongs to **Cursor**. Hand off with complete scope, constraints, affected surfaces, acceptance tests, stop conditions, and required evidence — do not leave Cursor to reverse-engineer intent from a thin note.

**Codex** owns investigation, feasibility and safety auditing, evidence verification, and targeted rechecks — **not** implementation chunks Cursor can execute effectively. Do not burn Codex (or Sol-High) cycles on mindless coding work that is Cursor's comparative advantage.

**TL;DR:** large implementation → Cursor; investigation/audit → Codex.

### Sol-High conflict gate (hard precondition)

**Sol-High may only be invoked when Codex and Kiro (or R1) have issued genuinely conflicting verdicts on the same artifact.** Soft convention ("used only for unresolved conflicts") is insufficient — this is a **hard gate**.

Before any Sol-High / GPT-sol / Copilot Sol-High call, the calling agent **must** produce a written conflict summary as a literal prompt prefix (not a private judgment). Checklist — all boxes required:

1. **Same artifact** named (PR, branch tip SHA, or file set under review).
2. **Verdict A** pasted (who + PASS/FAIL/defer + key rationale).
3. **Verdict B** pasted (who + PASS/FAIL/defer + key rationale).
4. **Specific disagreement** stated in one sentence (what claim A and B cannot both be true).
5. Confirm the call is **not** for: routine execution, a single-reviewer FAIL, drafting, or a re-audit of uncontested findings.

If any checklist item is missing, **do not invoke Sol-High** — route to Cursor (implementation), Codex (audit/recheck), or Kiro (design sign-off) instead.

**Non-example (PR #52 pattern — do not call Sol-High):** Codex alone issues FAIL; Kiro correctly defers or has not issued a conflicting verdict; there is no A-vs-B disagreement. That is a single-reviewer FAIL awaiting Cursor fix or Kiro sign-off — **not** a conflict. Invoking Sol-High here wastes scarce tokens.

**Shared surface:** this gate lives in the always-loaded `TEAM_CHARTER` slice (`config/agent-protocol.md`) so Cursor, Kiro, and Codex all see the same rule.

---

## 5. Risks

**Fourth reviewer before fixes?** No — Crush → Codex → Kiro is sufficient if Codex audits **every** finding slated for implementation, not a sample. Volume (82 findings) makes partial audit the real risk. Sol-High is **not** a routine fourth reviewer — only a conflict adjudicator under the hard gate above.

**Naming risk:** "DeepSeek" in operator language → future router keys off wrong tier. Fix vocabulary now (compact charter in always-loaded rules).

**Token scarcity / mis-delegation:** Burning Sol-High or Codex on large Cursor-shaped implementation (or calling Sol-High on a single FAIL with no opposing verdict) wastes scarce high-cost capacity. Comparative-advantage handoff + Sol-High checklist are the mitigations.

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
