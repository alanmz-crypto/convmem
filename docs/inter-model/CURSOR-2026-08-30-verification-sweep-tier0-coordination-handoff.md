# Coordination Handoff: [Arc Recent-Completions Verification Sweep] Tier-0 re-verification

**Date:** 2026-08-30
**Author:** Cursor (drafting lane)
**For:** Ryan (routing) · Kiro · Copilot audit-lane
**Authorization:** Ryan, 2026-08-30 (proxy GATE — “use your best judgement for my choices”)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `AUTHORIZED — verdicts pending` |
| **Branch** | `docs/2026-08-30-2026-08-30-verification-sweep-tier0-handoffs` |
| **Push status** | push after commit |
| **PR** | not opened |
| **Ryan GATE** | Route briefs to reviewers; accept GAP closures after verdicts |
| **Track A ingest** | Cursor agent transcript for this session |

---

## Ryan GATE (locked)

```text
Tier-0 framing: live-main risk first (Option B)
Tier-0 locked: #253 → #221 → #202
Tier-1: scheduled immediately after Tier-0 verdicts execute
Drafting lane: Cursor
```

**Rationale:** Active Copilot scope-limit on live write-gating (#221) outranks
ruleset/doc attestation gap (#202). #253 is first — routing surfaces are the
trust map.

---

## Execution order

| Seq | Item | Handoff | Primary lane | Landed SHA |
|-----|------|---------|--------------|------------|
| 1 | PR #253 project-state reconciliation | [253 claims attestation](CURSOR-2026-08-30-verification-sweep-253-claims-attestation-handoff.md) | **Kiro** (+ Copilot if code-grounded claim fails) | `a924d3887329dd51f1e0ac917f8ab21bae513c57` |
| 2 | PR #221 Trapdoor T3 integration | [221 trapdoor integration](CURSOR-2026-08-30-verification-sweep-221-trapdoor-integration-handoff.md) | **Copilot audit-lane + Kiro** (both required) | `722141d31e586151f361ef7006ad74c71cdff534` |
| 3 | PR #202 CodeQL arc closeout | [202 CodeQL closeout](CURSOR-2026-08-30-verification-sweep-202-codeql-closeout-handoff.md) | **Kiro + Copilot audit-lane** | `d10e1d5f4993f60a32142115f8b8c0f0f9ea4481` |

Execute **in sequence**. Do not parallelize #221 before #253 completes — downstream
routing may change if #253 claims fail.

---

## Tier-1 queue (after Tier-0 verdicts)

Schedule immediately after Tier-0 GAP rows close or Ryan accepts residual risk:

#250 CG-2 Execute-close · #240 D4 · #239 D3 · Recovery Authority review
binding · #243 writer attestation — per original 17-row inventory Tier 1.

---

## What NOT to do

- Do not merge, patch, or reopen #252 / R2b implementation from this arc.
- Do not let Cursor, Claude, or ChatGPT render final PASS/FAIL — only Copilot
  audit-lane and Kiro close GAP rows.
- Do not draft duplicate briefs from a second lane.

---

## Related files

| What | Path |
|------|------|
| Parent coordination | this file |
| Brief 1 (#253) | `CURSOR-2026-08-30-verification-sweep-253-claims-attestation-handoff.md` |
| Brief 2 (#221) | `CURSOR-2026-08-30-verification-sweep-221-trapdoor-integration-handoff.md` |
| Brief 3 (#202) | `CURSOR-2026-08-30-verification-sweep-202-codeql-closeout-handoff.md` |
| Reconciliation source | `CODEX-2026-08-30-project-state-reconciliation-handoff.md` |
| CodeQL VERIFY baseline | `docs/plans/VERIFY-codeql-complex-therapy.md` |

**TL;DR:** [Arc Recent-Completions Verification Sweep] Three Tier-0 reviewer briefs,
fixed order `#253 → #221 → #202`; Copilot + Kiro execute; Tier-1 follows.
