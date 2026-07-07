# Handoff: Orchestration approach review — is Tier 1 the right path?

**Date:** 2026-07-06 (evening)  
**From:** Cursor Auto (convmem session) + Ryan  
**To:** Claude Cloud (Opus or Sonnet)  
**Purpose:** After team-charter rollout, Ryan challenged whether **Tier 1 manual handoff** is meaningfully different from today's multi-chat workflow. Validate sequencing (Tier 1→2→3), naming honesty, and when to build a thin orchestrator. **No code edits** — return structured markdown Ryan can merge.

**Status:** closed — merged 2026-07-06  
**Owner:** Claude Cloud (review) → Ryan (merge) → Cursor (integration)  
**Merged into:** [ORCHESTRATION-APPROACH-2026-07-06.md](ORCHESTRATION-APPROACH-2026-07-06.md)

**Prior review (same day):** [HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md](HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md) → merged as [TEAM-CHARTER-2026-07-06.md](TEAM-CHARTER-2026-07-06.md). **This handoff is the follow-up** — not re-litigate roles; judge **architecture trajectory**.

---

## Context (90 seconds)

Ryan is preparing a **Willowy Hollow bug sprint** using the HITL lane model (Crush → Codex → Kiro → Cursor) with **convmem** as shared memory.

We shipped Tier 1 tooling today: team charter, handoff scripts, Codex rollout ingest, `convmem-index-prod.sh`, bug triage doc. `doctor` passes; Tier 1 experiment is **go**.

Ryan then asked how models observe each other. Answer: **they don't** — successors read an indexed archive; Ryan triggers the next lane. Ryan replied:

> *We have this already in one form. Models are not observers in session; they are successors reading a shared archive; I trigger the next model.*

**Ryan wants Claude to confirm we're on the right approach** before investing more in Tier 1 habit soak vs accelerating Tier 3 orchestrator.

---

## Read order in this archive

1. `HANDOFF.md` (this file)
2. `ORCHESTRATION-TIER-GAP.md` — Ryan's critique + Cursor's honest Tier 1 vs Tier 3 split
3. `TEAM-CHARTER-2026-07-06.md` — merged role charter (reference; do not re-audit lanes unless gaps affect orchestration)
4. `context/ORCHESTRATION-FRAMING.md` — professional terms + stability tiers
5. `context/MODEL-WORKFLOW.md` — prod/lab, write guards, index-prod wrapper
6. `context/WILLOWYHOLLOW-SESSION-LOOP.md` — bug sprint loop + handoff script
7. `context/agent-protocol.md` — TEAM_CHARTER slice (always-loaded rules)
8. `ledger-ids.txt` — anchors for optional record suggestion

---

## What Claude Cloud should judge

### 1. Is Tier 1 worth running as a distinct experiment?

Ryan's layman view: Tier 1 ≈ "open next chat app + paste." Cursor claims incremental value: **search/ask over indexed chat**, lane charter, ledger chain, guards.

- Agree with Ryan, Cursor, or **split the difference**?
- What **measurable outcome** from the bug sprint proves Tier 1 paid off? (e.g. Codex never asked Ryan to paste Crush output; zero Track A skips)
- If payoff is small, should Ryan **relabel** the effort (memory bus, not orchestration)?

### 2. Tier sequencing — hold, skip, or jump?

| Option | Description |
|--------|-------------|
| **A** | Continue Tier 1 → Tier 2 habit gate → then Tier 3 (current plan) |
| **B** | Run bug sprint on Tier 1 **in parallel** with Tier 3 design spike in convmem-lab |
| **C** | **Skip Tier 2** — build minimal orchestrator after one successful handoff |
| **D** | **Stop orchestration framing** — convmem stays memory-only; Ryan keeps manual scheduling |

Recommend one option with rationale.

### 3. Tier 3 minimum component (design only)

What is the **smallest** addition beyond convmem that makes lay observers say "that's different"?

Consider:

- Sprint state file (`lane`, `status`, `finding_ids`)
- Hook on `convmem index` completion → enqueue next lane prompt
- Ryan approval step before auto-wake (still HITL)
- What **must not** be built (full agent messaging, write-capable MCP, autonomous record)

Return a **one-page Tier 3 sketch** — components, events, human gates.

### 4. Naming and expectations

- Should public/docs stop saying "event-driven orchestration" for Tier 1?
- How should Ryan describe the project to a layperson **today** vs **after Tier 3**?

### 5. Risks of the current path

- **Ceremony fatigue** — scripts/phrasebook without retrieval habit
- **False progress** — charter shipped feels like orchestration shipped
- **Premature Tier 3** — auto-trigger on broken Track A ingest
- **Never building Tier 3** — memory layer good enough, orchestrator starved

---

## Expected output

1. **Verdict:** Tier 1 sequencing correct / adjust / pivot to memory-only
2. **Bug sprint success criteria** — 3–5 concrete checks (not role table)
3. **Tier 3 sketch** — minimal orchestrator (markdown diagram welcome)
4. **Naming recommendation** — what to call Tier 1 vs Tier 3 publicly
5. **Optional:** `convmem record` block (Ryan runs manually) — only if durable conclusion warranted

Return **markdown only** — no code, no bulk index, no prod writes.

---

## Constraints

- Single user, single workstation; local-first
- MCP read-only on prod; durable writes = Ryan `record --approve-last`
- **Handoff ≠ record**
- convmem-lab for Tier 3 spikes; prod for memory bus
- Team roles **settled** — see TEAM-CHARTER; this review is **trajectory**, not lane reassignment

---

## Ledger anchors (`ledger-ids.txt`)

| Ledger id | Topic |
|-----------|-------|
| `dec_prop_20260623_161428_c311` | Protocol root (fallback) |
| `dec_prop_20260629_213047_8f73` | Linker Phase 2 held |
| `obs_806985bc5697` | Agent-habit / coordination gate |
| `dec_prop_20260706_192446_9ca8` | write_lane SKIP + restic refresh |
| `dec_prop_20260706_185537_f731` | Team-roles audit (charter merged) |

---

## Ryan → Claude Cloud prompt

> Read `HANDOFF.md` and `ORCHESTRATION-TIER-GAP.md`. We shipped the HITL team charter and Tier 1 handoff tooling today. Ryan says Tier 1 still feels like "I open the next chat and paste" — successors + archive + human trigger. Is Tier 1→2→3 the right approach, or should we pivot? What should the bug sprint prove? Sketch minimal Tier 3. Markdown only.

---

## Files in this archive

```
handoff-orchestration-approach-2026-07-06/
├── HANDOFF.md
├── RYAN-PROMPT.txt
├── ORCHESTRATION-TIER-GAP.md
├── TEAM-CHARTER-2026-07-06.md
├── ledger-ids.txt
├── context/
│   ├── ORCHESTRATION-FRAMING.md
│   ├── MODEL-WORKFLOW.md
│   ├── WILLOWYHOLLOW-SESSION-LOOP.md
│   └── agent-protocol.md
└── scripts/
    ├── sync-willowyhollow-handoff.sh
    └── convmem-index-prod.sh
```

**Tarball (repo root, gitignored):** `handoff-orchestration-approach-2026-07-06.tar.gz`

**Excluded:** full findings log, prod Chroma, secrets, PDFs, full source trees.
