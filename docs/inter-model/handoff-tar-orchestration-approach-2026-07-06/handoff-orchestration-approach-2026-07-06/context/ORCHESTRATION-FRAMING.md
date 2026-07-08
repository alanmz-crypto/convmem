# Orchestration framing (for Claude review)

**Ryan's description:**

> A local, event-driven, human-gated multi-agent software supervisor with shared memory.

**Professional terms:**

| Term | convmem today |
|------|---------------|
| Agent orchestration | **Partial** — manual handoff, no task queue |
| Supervisor–worker | **Not built** — Ryan is the supervisor |
| Human-in-the-loop | **Strong** — `record --approve-last` |
| Policy guardrails | **Strong** — `agent-protocol.md`, write_lane |
| Event-driven automation | **Partial** — watch, digest timer Mon 09:00 |
| MCP tool layer | **Strong (read-only)** |
| Multi-agent SDLC | **Pilot stage** — Willowy Hollow bug sprint |

---

## Stability tiers (from Cursor assessment 2026-07-06)

| Tier | Experiment | Ready? |
|------|------------|--------|
| **1** | Manual Crush→Codex→Kiro with `sync-willowyhollow-handoff.sh` | **Yes now** |
| **2** | Same loop 3–5× without re-teaching ingest/record | **2–4 weeks habit soak** |
| **3** | Event-driven supervisor waking agents | **Needs new thin orchestrator** — build in lab first |

**convmem prod:** ~85% daily-ready; ~75% whole-vision.  
**convmem-lab:** ~70% spike-complete; ~25% graduated to prod (by design).

---

## One-command handoff (Track A + B)

```bash
bash ~/Projects/convmem/scripts/sync-willowyhollow-handoff.sh
```

Indexes: Crush `crush.db`, latest Kiro `messages.jsonl`, latest Codex `rollout-*.jsonl`, findings + audit via sync scripts.
