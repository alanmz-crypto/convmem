---
status: active
ledger: dec_prop_20260623_215943_5abe
---

# convmem Roadmap — Lauer (canonical miniPC)

North-star: local evidence bus on the **canonical miniPC host**. **Operate-and-document** — not foundation-build.

Test count at publish: run `convmem brief --with-tests` (currently **159**).

---

## Closed — do not reopen

| Phase | What shipped |
|-------|----------------|
| P0 | Watch soak PASS (~99 MB RSS); `doctor` v0+v1; F2a store API |
| P1a | `convmem unresolved`; `recency_boost` on `ask --evidence`; JSONL upsert sync |
| P1b | Golden eval 10/10 |
| Protocol | Global rollout — [`config/agent-protocol.md`](../config/agent-protocol.md), verification matrix, soak closed |
| Chroma write path | `PersistentClient`-only; `record --approve-last` index regression test — commit `4c82f35` |

Daily ritual: `doctor` → `unresolved` → `ask` / `record --approve-last`.

---

## Pre-live-write gate (Restic)

Before any live Chroma upsert or write-path merge:

1. Last Restic snapshot of `~/.local/share/convmem/chroma` must cover corpus **as of today**.
2. If stale → run a fresh Restic snapshot, then proceed.
3. If Restic cannot snapshot → **block** live upsert.

Corpus rollback: [`RECOVER.md`](RECOVER.md). If `restic` is not on PATH, ensure a Tier-1 data backup exists before live writes.

---

## Session workflow

```text
convmem doctor
convmem unresolved
convmem ask "…"          # source ~/.config/convmem/env.local
```

MCP (read-only): `brief`, `search_fast`, `ask`, `related`, `stats`.

---

## Optional gates (manual — do not build unless triggered)

| Gate | Trigger | Action |
|------|---------|--------|
| **P1c** | ≥3 `synthesis_failed` / week on `ask` | Phase 1 streaming synthesis — [`PLAN-2026-06-29-streaming-synthesis.md`](inter-model/PLAN-2026-06-29-streaming-synthesis.md) |
| **P2** | New FAIL in [`VERIFICATION-MATRIX.md`](inter-model/VERIFICATION-MATRIX.md) | MCP `unresolved` / `open`; agent-habit fixes only |
| **P2-stream** | After P1c + client pre-flight | Streamable HTTP + `ask_stream` — same plan doc |

**rerank:** Manual spot-check only — eyeball `config.toml` vs `brief`; no automation.

---

## P3 — later

OpenClaw, dedupe approval UI, hybrid retrieval, `export --redact`, domain backfill in brief, rerank/CUDA if latency matters.

Cross-project digest: [`scripts/cross-project-digest.sh`](../scripts/cross-project-digest.sh), pilot [`CROSS-PROJECT-DIGEST-PILOT.md`](inter-model/CROSS-PROJECT-DIGEST-PILOT.md).

---

## Hygiene (pinned)

| Item | Rule |
|------|------|
| Pending inventory | **>20 pending** → index pass (daily ritual check) |
| Unsigned decision session files | Delete from `examples/` when never approved into ledger |

---

## Open (out of planner scope)

| Item | Lane |
|------|------|
| staging2 CSP (unresolved obs) | Client |
| `convmem ask` in shell | `source env.local` for DeepSeek key |

---

## Avoid

- Monolithic Chroma+protocol commits
- `_debug_log` in repo
- P2 MCP without matrix FAIL or habit evidence
- Hybrid retrieval without eval regression
- convmem infra work masquerading as client deploy

---

Supersedes [`ROADMAP-DRAFT.md`](ROADMAP-DRAFT.md) (2026-06-30). Session contract: [`AGENTS.md`](../AGENTS.md) → [`config/agent-protocol.md`](../config/agent-protocol.md).
