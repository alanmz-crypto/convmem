# Bug sprint success criteria — Willowy Hollow Tier 1 evidence

**Sprint:** Willowy Hollow practice (`willowyhollow-practice`, `:8081`)  
**Measures:** Tier 1 **shared memory bus** only — no Tier 1.5 scoring, no Tier 3 prod wiring during sprint  
**Approach doc:** [ORCHESTRATION-APPROACH-2026-07-06.md](ORCHESTRATION-APPROACH-2026-07-06.md)

---

## Checks (tick during sprint)

| # | Check | Pass criterion | During sprint |
|---|-------|----------------|---------------|
| 1 | Zero Track A skips | Every handoff indexes chat, not log-only | |
| 2 | Codex retrieval | Never asks Ryan to re-paste Crush findings | |
| 3 | Umbrella record | One `record --approve-last` at sprint end, not per-finding | |
| 4 | Kiro discipline | No volunteered `record` unless Ryan cues | |
| 5 | **Unrestated retrieval** | Successor surfaces archive content Ryan did not restate | evidence: |

**Verdict rule:** Fewer than 4/5 → Tier 1 ceremony not earned. Check 5 failing alone = Tier 1 adds durability only, not capability.

**Handoff command:**

```bash
bash ~/Projects/convmem/scripts/sync-willowyhollow-handoff.sh
```

---

## Scoring (Ryan — sprint end)

Fill this block when the sprint ends. **`tier_1_5_gate: UNLOCKED`** is the sole trigger for Tier 1.5 triage-scoring build (pass or fail on checks both unlock).

```
scored_date: YYYY-MM-DD
verdict: pass | fail | inconclusive    # pass = 4+/5 checks
```

| # | Result | Note |
|---|--------|------|
| 1 | pass / fail / n/a | |
| 2 | pass / fail / n/a | |
| 3 | pass / fail / n/a | |
| 4 | pass / fail / n/a | |
| 5 | pass / fail / n/a | evidence: `<ledger id or quote if pass>` |

```
tier_1_5_gate: LOCKED | UNLOCKED
```

Until `tier_1_5_gate: UNLOCKED` appears above, Tier 1.5 code stays out of scope.

---

## Check 5 evidence log (optional, during sprint)

Record moments as they happen — copy into scoring row 5 at sprint end.

| When | Lane | What successor surfaced | Ryan had not restated? |
|------|------|---------------------------|------------------------|
| | | | |
