---
status: active
ledger: dec_prop_20260623_215943_5abe
# Graduate → ROADMAP.md after ~1 week CLI soak (see "Now" below).
---

# convmem Roadmap — Lauer

North-star for the **canonical miniPC host**.

**Planner state (indexed):** P0 through **P1b complete**. Golden eval **10/10**. Test suite **127/127**. Retrieval layer is good enough — next gate is **how agents actually work**, not more search.

---

## Completed (do not reopen)

| Phase | What shipped |
|-------|----------------|
| Watch soak | PASS — ~82 MB flat (not 3.5 GB) |
| doctor v0 + v1 | `convmem doctor` / `--v1` — commit e30667c, 302a9a9 |
| F2a | Store API, ask `--evidence` citation dedupe, `ledger_id` index |
| P1a | `convmem unresolved` CLI; `recency_boost` in [`evidence.py`](../evidence.py); JSONL upsert sync in [`observe.py`](../observe.py) |
| P1b | [`tests/fixtures/golden_questions.jsonl`](../tests/fixtures/golden_questions.jsonl) + [`tests/test_eval_golden.py`](../tests/test_eval_golden.py) — 10/10 in ~27s |
| Cheap wins | [`AGENTS.md`](../AGENTS.md) session start: **doctor → unresolved → ask**; [`brief.py`](../brief.py) shows unresolved count |

---

## Where we are now

```text
Now (~1 week):   live CLI workflow soak; graduate ROADMAP-DRAFT → ROADMAP.md
P2 (gated):      MCP unresolved/open — ONLY if agents still bypass CLI despite 10/10 eval
P3:              expansion backlog
```

**P2 gate clarified:** Eval proves retrieval works. P2 is about **agent habit** (PATH, steering, Bash instead of MCP) — not search quality. Kiro lesson: even good tools get skipped without explicit session rules.

---

## Session workflow (use this daily)

```text
convmem doctor          # health
convmem unresolved      # what's still open?
convmem ask "…"         # needs: source ~/.config/convmem/env.local (DEEPSEEK_API_KEY)
```

MCP today: `brief`, `search_fast`, `ask`, `related`, `stats` — read-only.

---

## P2 — agent workflow (gated)

Ship **only if** graded sessions ([`grade-continue-session.sh`](../scripts/grade-continue-session.sh)) or Cursor transcripts show agents ignoring CLI/MCP after a week of AGENTS.md workflow:

1. MCP `unresolved`
2. MCP `open` ([`open_source.py`](../open_source.py))
3. `brief(compact=true)`

**Do not ship** because eval failed — it didn't. Ship because agents still take shortcuts.

---

## P3 — later

OpenClaw, dedupe approval UI, hybrid retrieval, `export --redact`, domain backfill in brief, rerank/CUDA if latency matters.

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

## Open (out of planner scope)

| Item | Lane |
|------|------|
| staging2 CSP deploy | Client / willowyhollow — tracked in MCP decisions, not convmem infra |
| `convmem ask` in shell | Requires `source ~/.config/convmem/env.local` for `DEEPSEEK_API_KEY` |

---

## Graduate to ROADMAP.md

After ~1 week CLI soak with no surprises:

1. Rename this file → `ROADMAP.md`
2. Link from [`README.md`](../README.md)
3. Keep [`AGENTS.md`](../AGENTS.md) as the live session contract

---

## Avoid

- Hybrid retrieval / embed upgrades — eval passes; no evidence of recall failure
- MCP auto-writes; auto-merge dedupe; cloud corpus
- P2 MCP tools "because we planned them" — gate on agent habit only
- convmem infra work masquerading as client deploy (CSP, etc.)
