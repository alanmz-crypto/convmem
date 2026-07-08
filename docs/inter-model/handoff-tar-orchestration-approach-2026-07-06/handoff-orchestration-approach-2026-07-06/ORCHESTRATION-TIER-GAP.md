# Orchestration tier gap — what Tier 1 is vs what Ryan already had

**Date:** 2026-07-06  
**Status:** open — for Claude Cloud review  
**Relates to:** `TEAM-CHARTER-2026-07-06.md`, `HANDOFF-CLAUDE-CLOUD-2026-07-06-orchestration-approach-review.md`

---

## Ryan's observation (layman-correct)

After charter rollout and bug-sprint prep, Ryan noted that **Tier 1 today** looks a lot like **how things already work**:

| Tier 1 behavior | Already familiar? |
|-----------------|-------------------|
| Models are **not** observers of each other in session | Yes — separate apps, separate chats |
| Models are **successors** reading a shared archive | Partially — Ryan pasted logs before; now `convmem search/ask` |
| **Ryan triggers** the next model (open app, paste cue, ingest) | Yes — same human scheduler |

**Ryan's question:** Are we taking the right approach, or building ceremony around a workflow that isn't meaningfully new until **models trigger each other**?

---

## Cursor's honest framing (for Claude to validate or reject)

### What Tier 1 actually adds (incremental, not revolutionary)

1. **Retrieval** — next model queries indexed prior chat + logs instead of Ryan re-pasting
2. **Lane policy** — charter: Crush finds, Codex audits, Kiro signs, Cursor implements
3. **Evidence chain** — ledger ids, `related()`, approved `record` blocks
4. **Guards** — prod/lab write_lane, Track A vs B, handoff ≠ record
5. **Handoff scripts** — `sync-willowyhollow-handoff.sh`, `convmem-index-prod.sh`

### What Tier 1 does **not** add

- No agent-to-agent messaging
- No task queue or lane locks
- No "Crush finished → wake Codex"
- No live observer in another model's session
- `watch` only re-indexes files (~90s debounce) — does not route work

### North-star vs built

Ryan's vision phrase:

> Local, **event-driven**, human-gated multi-agent software supervisor with shared memory.

| Component | Built? |
|-----------|--------|
| Shared memory | **Yes** (~85% daily-ready) |
| Human-gated ledger | **Yes** |
| Policy / lanes | **Yes** (charter shipped 2026-07-06) |
| Event-driven routing | **No** (Tier 3 deferred) |
| Supervisor | **Ryan** (not automated) |

**Tier 1** tests: *Can successors reliably read the archive?*  
**Tier 3** tests: *Can the system route without Ryan opening the next app?*

---

## Phased roadmap (current plan)

| Tier | Goal | Gate |
|------|------|------|
| **1** | Manual handoff + shared memory | **Ready now** — Willowy Hollow bug sprint |
| **2** | 3 clean handoffs (Track A+B, no wrong record) | Habit soak 2–4 weeks |
| **3** | Thin orchestrator on index/handoff events | **Not built** — lab first |

**Hypothesis:** Reliable memory + lane discipline is prerequisite for auto-triggering. Otherwise Codex fires on stale/missing Crush chat (already happened: Track A skipped).

**Counter-hypothesis (Ryan may hold):** Tier 1 payoff is too small vs manual multi-chat; should spec orchestrator **now** or accept convmem as memory-only, not "orchestration."

---

## What Claude should decide

1. **Is Tier 1 → 2 → 3 sequencing correct**, or should Ryan skip/jump?
2. **Minimum viable delta** — what must the bug sprint prove for Tier 1 to be worth it?
3. **Tier 3 component sketch** — what exists beyond convmem (sprint state file? queue? webhook on index?) — **design only**
4. **Rename honesty** — should we stop calling Tier 1 "orchestration" and call it "shared memory + roles"?
5. **When to build** — habit gate vs pain threshold (Ryan still switches apps every handoff)

---

## Shipped since first HITL handoff (same day)

- `TEAM-CHARTER-2026-07-06.md` merged; `TEAM_CHARTER` in `agent-protocol.md`
- `scripts/convmem-index-prod.sh` — lab→prod index wrapper
- Codex `rollout-*.jsonl` adapter; `--supersede` re-index
- `WILLOWYHOLLOW-BUG-TRIAGE-2026-07-06.md` — prioritized fix plan (indexed)
- Git: `3bad9ab` (charter), `350e54d` (index-prod wrapper) — 2 commits ahead of origin at handoff time
- Approved: `dec_prop_20260706_192446_9ca8` (write_lane SKIP)

**Bug sprint status:** Tier 1 pilot **running** — Crush discovery, Ryan manual lane switches, practice stack `:8081` up.

---

## Related

- [TEAM-CHARTER-2026-07-06.md](TEAM-CHARTER-2026-07-06.md) — roles (prior Claude review)
- [HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md](HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md) — first review (team roles)
- [handoff-tar-hitl-2026-07-06/](handoff-tar-hitl-2026-07-06/) — prior tar staging
