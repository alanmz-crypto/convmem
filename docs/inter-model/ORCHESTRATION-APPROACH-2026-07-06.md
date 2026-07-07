# Orchestration approach — merged decision (Claude Cloud review)

**Date:** 2026-07-06  
**Status:** active — merged from Claude Cloud review  
**Reviewer:** Claude Cloud  
**Problem statement:** [ORCHESTRATION-TIER-GAP.md](ORCHESTRATION-TIER-GAP.md) (closed)  
**Handoff:** [HANDOFF-CLAUDE-CLOUD-2026-07-06-orchestration-approach-review.md](HANDOFF-CLAUDE-CLOUD-2026-07-06-orchestration-approach-review.md) (closed)

---

## Verdict: Option B

**Ryan is right** — Tier 1 as built is not meaningfully different from manual multi-chat in *human workload*. Successors read an archive; Ryan triggers the next app. The archive is more durable and searchable, but the scheduler role is unchanged.

**Option B adopted:** Run the bug sprint on Tier 1 for real evidence; spike Tier 3 **design** in convmem-lab in parallel (no prod wiring).

| Option | Verdict |
|--------|---------|
| **A** — Full habit soak before Tier 3 | Rejected — risks "never build Tier 3" |
| **B** — Sprint + lab design spike | **Adopted** |
| **C** — Skip to Tier 3 after one handoff | Rejected — Track A skip proves substrate not trustworthy enough |
| **D** — Memory-only, abandon orchestration | Premature — Tier 3 differentiator not yet tested |

---

## Naming (effective immediately)

| Tier | Honest name | Do not call it |
|------|-------------|----------------|
| **1** | **HITL shared memory bus with lane discipline** | orchestration |
| **1.5** | Proactive discovery (deferred — post-sprint) | orchestration |
| **2** | Habit soak (3 clean handoffs) | orchestration |
| **3** | Orchestration (notify + state file) | — until notify ships |

Reserve **"orchestration"** for when the system acts on its own initiative (even notify-only). See [ORCHESTRATION-FRAMING.md](ORCHESTRATION-FRAMING.md).

---

## Bug sprint success criteria

Full checklist: [BUG-SPRINT-SUCCESS-2026-07-06.md](BUG-SPRINT-SUCCESS-2026-07-06.md)

| # | Check | Pass criterion |
|---|-------|----------------|
| 1 | Zero Track A skips | Every handoff indexes chat, not log-only |
| 2 | Codex retrieval | Never asks Ryan to re-paste Crush findings |
| 3 | Umbrella record | One `record --approve-last` at sprint end |
| 4 | Kiro discipline | No volunteered `record` unless Ryan cues |
| 5 | **Unrestated retrieval** | Successor surfaces archive content Ryan did not restate |

**Verdict:** Fewer than 4/5 → Tier 1 ceremony not earned. Check 5 failing alone = strongest evidence Tier 1 adds durability only, not capability.

**Tier 1.5 gate:** `tier_1_5_gate: UNLOCKED` in the sprint checklist when Ryan scores all five checks (pass or fail). That unlocks Tier 1.5 build — not habit-soak weeks.

---

## Tier 3 minimum sketch (lab-only until graduation)

**Layperson difference:** System notices lane completion and taps Ryan with the next step staged — Ryan still opens every app by hand.

```
Crush finishes → convmem index (existing)
       ↓ index completion
sprint-state.json { lane, status, finding_ids, next_lane }
       ↓ file watch / hook
Notify-only: "Codex lane ready — N findings indexed. Suggested prompt: …"
       ↓ Ryan reads
Ryan approves/edits → opens Codex, pastes prompt
```

**Must not build:** agent-to-agent messaging, auto-open apps, auto-invoke models, autonomous `record`, queue/retry.

**Lab spike:** `~/Projects/convmem-lab/docs/spikes/TIER3-NOTIFY-2026-07-06.md`

**Graduation gate:** Checks 1–5 scored + memory reliability (especially 1 + 2).

---

## Tier 1.5 — deferred until sprint scored

Proactive `unresolved()` surfacing at session start — **not during sprint** (confounds check 5 attribution; raw surfacing risks alert fatigue).

**Build trigger:** `tier_1_5_gate: UNLOCKED` in [BUG-SPRINT-SUCCESS-2026-07-06.md](BUG-SPRINT-SUCCESS-2026-07-06.md).

**Build order (post-gate):**

1. Triage scoring on `unresolved_payload` — `surfacing_tier`: log | surface | silent
2. Protocol ritual — surface only `surface` tier unprompted after `brief`
3. Own success criteria — signal-to-noise over N sessions

---

## Tier map (three capabilities)

| Capability | What it is | Tier |
|------------|------------|------|
| Retrieval on prompt | `search` / `ask` when Ryan or model asks | **1** (sprint tests this) |
| Proactive discovery | Model surfaces stale/unverified work unprompted | **1.5** (post-sprint) |
| Completion notify | System notices index done, stages next prompt | **3** (lab design now) |

---

## Related

- [TEAM-CHARTER-2026-07-06.md](TEAM-CHARTER-2026-07-06.md) — lanes (settled)
- [WILLOWYHOLLOW-SESSION-LOOP.md](../WILLOWYHOLLOW-SESSION-LOOP.md) — sprint loop
- [MODEL-WORKFLOW.md](../MODEL-WORKFLOW.md) — prod/lab cheat sheet
