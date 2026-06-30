---
status: superseded
ledger: dec_prop_20260623_215943_5abe
# Superseded by ROADMAP.md (2026-06-30). Kept for history.
---

# convmem Roadmap — Lauer (draft — superseded)

> **Archival record only** — frozen planner text from **before 2026-06-30 graduation**.  
> **Do not execute** checklists, gaps, or "graduate" steps below.  
> **Active roadmap:** [`ROADMAP.md`](ROADMAP.md) · **Session contract:** [`config/agent-protocol.md`](../config/agent-protocol.md)

Internal references to `ROADMAP-DRAFT` in the body are part of this snapshot, not live pointers.

---

## Historical record (2026-06-24 → 2026-06-30)

**→ Superseded by [`ROADMAP.md`](ROADMAP.md).**

North-star for **one workstation**: transcripts, Chroma, and daemons all live on the machine where Cursor/Kiro/Continue run.

**Planner state (indexed):** P0 through **P1b complete**. Golden eval **10/10**. Test suite **127/127**. Retrieval layer is good enough — next gate is **how agents actually work**, not more search.

---

## Completed (do not reopen)

| Phase | What shipped |
|-------|----------------|
| Watch soak | PASS — RSS ~99 MB (brief 2026-06-29); was ~3.5 GB |
| doctor v0 + v1 | `convmem doctor` / `--v1` — [`doctor.py`](../doctor.py), [`tests/test_doctor.py`](../tests/test_doctor.py) |
| F2a | Store API, ask `--evidence` citation dedupe, `ledger_id` index |
| P1a | `convmem unresolved` CLI; `recency_boost` in [`evidence.py`](../evidence.py); JSONL upsert sync in [`observe.py`](../observe.py) |
| P1b | Golden eval 10/10; **127 tests** (README still says 28 — fix on graduate) |
| Protocol | Global rollout: [`config/agent-protocol.md`](../config/agent-protocol.md), verification matrix, [`SOAK-REPORT-2026-06-25.md`](inter-model/SOAK-REPORT-2026-06-25.md) |
| Cheap wins | [`brief.py`](../brief.py) `unresolved_count`; [`AGENTS.md`](../AGENTS.md) → pointer to agent-protocol |
| Beyond planner | Cross-project digest, Kiro/Codex adapters, Crush ritual hooks |

---

## Where we are now

```text
Now:             graduate ROADMAP-DRAFT → ROADMAP.md + README hygiene
P1c:             ask streaming Phase 1 — partial synthesis on timeout (no API change)
P2 (gated):      MCP unresolved/open — agent habit only
P2-stream (gated): ask streaming Phase 2 — streamable HTTP + ask_stream (client pre-flight)
P3:              expansion backlog
```

**P2 gate clarified:** Eval proves retrieval works. P2 is about **agent habit** (PATH, steering, Bash instead of MCP) — not search quality.

**P1c / P2-stream:** Orthogonal to P2 — improves `ask` when synthesis hits the 45s wall. Spec: [`inter-model/PLAN-2026-06-29-streaming-synthesis.md`](inter-model/PLAN-2026-06-29-streaming-synthesis.md). Relates to protocol ledger `dec_prop_20260623_161428_c311`.

---

## Session workflow (use this daily)

```text
convmem doctor          # health
convmem unresolved      # what's still open?
convmem ask "…"         # needs: source ~/.config/convmem/env.local (DEEPSEEK_API_KEY)
```

MCP today: `brief`, `search_fast`, `ask`, `related`, `stats` — read-only.

---

## P1c — Ask streaming (Phase 1) — ship next

**Problem:** `convmem ask` uses a 45s synthesis timeout; on timeout the user gets raw citations only (`synthesis_failed: True`). DeepSeek/Ollama support streaming but [`llm.py`](../llm.py) hardcodes `stream: False`.

**Phase 1** (~60 lines, **no API surface change**):
- Add `generate_stream()` in `llm.py`
- Collect tokens in `ask.py`; on timeout return **partial synthesis** + `[Synthesis interrupted]` instead of citation dump
- MCP `ask` tool, CLI, return dict shape unchanged
- Worst case degrades to today's behavior (empty buffer)

**Done when:** timeout during long `ask` returns partial answer; existing tests pass; optional unit test with mocked stream + timer.

Full design: [`PLAN-2026-06-29-streaming-synthesis.md`](inter-model/PLAN-2026-06-29-streaming-synthesis.md).

---

## P2 — agent workflow (gated)

Ship **only if** graded sessions ([`grade-continue-session.sh`](../scripts/grade-continue-session.sh)) or Cursor transcripts show agents ignoring CLI/MCP after a week of AGENTS.md workflow:

1. MCP `unresolved`
2. MCP `open` ([`open_source.py`](../open_source.py))
3. `brief(compact=true)`

**Do not ship** because eval failed — it didn't. Ship because agents still take shortcuts.

---

## P2-stream — Ask streaming (Phase 2) — gated on client pre-flight

**After Phase 1 ships.** Progressive token delivery to MCP clients via streamable HTTP.

| Piece | Notes |
|-------|-------|
| `run_ask_stream()` | Async events: citations → tokens → done ([`ask.py`](../ask.py)) |
| MCP `ask_stream` tool | New tool; existing `ask` stays for backward compat |
| Transport | `CONVMEM_TRANSPORT=streamable-http` or config `[mcp]` stanza |
| **Pre-flight gate** | Stub `ask_stream` with delayed yields; confirm Cursor/Crush render progressively — if client buffers, Phase 2 UX gain is nil |

~140 lines. Do not build until pre-flight passes. Spec: same plan doc.

---

## P3 — later

OpenClaw, dedupe approval UI, hybrid retrieval, `export --redact`, domain backfill in brief, rerank/CUDA if latency matters.

**Cross-project digest (2026-06-29):** [`scripts/cross-project-digest.sh`](../scripts/cross-project-digest.sh) — read-only weekly reporter; optional `--propose` queues drafts. Weekly timer: [`systemd/convmem-cross-project-digest.timer.example`](../systemd/convmem-cross-project-digest.timer.example). Pilot: [`docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md`](inter-model/CROSS-PROJECT-DIGEST-PILOT.md).

---

## Success criteria (current)

| Check | Status |
|-------|--------|
| Watch RAM | ✓ ~82 MB |
| Doctor | ✓ exit 0 |
| Search / eval | ✓ 10/10 golden |
| Agent habit | **In soak** — observe ~1 week |
| MCP P2 | Pending gate |

---

## Gaps (missed or partial)

| Gap | Severity | Notes |
|-----|----------|-------|
| ROADMAP not graduated | Doc | Still draft; README test count stale |
| Agent habit | P2 gate | Matrix mostly PASS; Continue qwen2.5/qwen3.6 still FAIL unprompted brief |
| recency on plain search | Partial P1a | Only `ask --evidence`, not `query.py` / `search_fast` |
| P2 MCP tools | Intentional | Shell `unresolved` interim; no MCP wrapper yet |
| 47 inventory pending | Hygiene | Sources not indexed |
| rerank at runtime | Check | Example config `true`; brief reports `false` |
| backfill_domain off | Hygiene | Not in default refine jobs |
| dedupe / redact | P3 | Queue review + `export --redact` not built |

## Open (out of planner scope)

| Item | Lane |
|------|------|
| staging2 CSP (14 unresolved obs) | Client |
| `convmem ask` in shell | `source env.local` for DeepSeek key |
| `examples/decisions-session-2026-06-18.jsonl` | Pending decision file |

---

## Graduate to ROADMAP.md

**Done (2026-06-30).** See [`ROADMAP.md`](ROADMAP.md). The steps below are historical.

1. Rename this file → `ROADMAP.md`
2. Link from [`README.md`](../README.md)
3. Keep [`AGENTS.md`](../AGENTS.md) as the live session contract

---

## Avoid

- Hybrid retrieval / embed upgrades — eval passes; no evidence of recall failure
- MCP auto-writes; auto-merge dedupe; cloud corpus
- P2 MCP tools "because we planned them" — gate on agent habit only
- convmem infra work masquerading as client deploy (CSP, etc.)
