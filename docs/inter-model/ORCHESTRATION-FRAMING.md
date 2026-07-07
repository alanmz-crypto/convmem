# Orchestration framing

**Ryan's north-star:**

> A local, event-driven, human-gated multi-agent software supervisor with shared memory.

**Honest status (2026-07-06):** Tier 1 is **not orchestration** — it is a **shared memory bus with lane discipline**. Reserve "orchestration" for Tier 3 (notify + state file). See [ORCHESTRATION-APPROACH-2026-07-06.md](ORCHESTRATION-APPROACH-2026-07-06.md).

---

## Professional terms

| Term | convmem today |
|------|---------------|
| Shared memory bus | **Tier 1 — yes** — Chroma, handoff scripts, search/ask |
| Agent orchestration | **Tier 3 — not built** — manual handoff only today |
| Supervisor–worker | **Not built** — Ryan is the supervisor |
| Human-in-the-loop | **Strong** — `record --approve-last` |
| Policy guardrails | **Strong** — `agent-protocol.md`, write_lane |
| Event-driven automation | **Partial** — watch re-index, digest timer Mon 09:00 |
| MCP tool layer | **Strong (read-only)** |
| Multi-agent SDLC | **Pilot** — Willowy Hollow bug sprint |

---

## Stability tiers

| Tier | Name | Experiment | Ready? |
|------|------|------------|--------|
| **1** | Shared memory bus | Manual Crush→Codex→Kiro + `sync-willowyhollow-handoff.sh` | **Yes — bug sprint** |
| **1.5** | Proactive discovery | `unresolved()` triage surfacing (post-sprint gate) | **Deferred** — see sprint checklist |
| **2** | Habit soak | 3 clean handoffs without Track A/B or record mistakes | 2–4 weeks after Tier 1 evidence |
| **3** | Orchestration | State file + notify on index completion | **Lab design spike** — not prod |

**convmem prod:** ~85% daily-ready. **convmem-lab:** spikes disposable by design.

---

## One-command handoff (Track A + B)

```bash
bash ~/Projects/convmem/scripts/sync-willowyhollow-handoff.sh
```

Indexes: Crush `crush.db`, latest Kiro `messages.jsonl`, latest Codex `rollout-*.jsonl`, findings + audit via sync scripts.

---

## Related

- [BUG-SPRINT-SUCCESS-2026-07-06.md](BUG-SPRINT-SUCCESS-2026-07-06.md) — sprint evidence checklist
- [TEAM-CHARTER-2026-07-06.md](TEAM-CHARTER-2026-07-06.md) — lane table
