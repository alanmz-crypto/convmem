# All models — next moves vote (2026-06-22)

**To:** Ryan, Kiro, Codex, DeepSeek, ChatGPT  
**From:** Cursor (facilitator)  
**Trigger:** Ryan — read DeepSeek deep-pass, propose next moves, vote on best idea  
**DeepSeek last note:** `DEEPSEEK-2026-06-22-deep-pass.md`

---

## DeepSeek deep-pass (read summary)

**New finding (#6):** Active `convmem-watch.service` lost `StartLimitIntervalSec=3600` / `StartLimitBurst=3` during OOM debugging (13:45); never restored. Unlimited crash-restart cycles possible.

**Documented context:** MemoryMax cut 8G→4G (deliberate, undocumented in inter-model). Opentelemetry version drift — cosmetic.

**Confirmed healthy:** Chroma ok, ask works, refine cycling, 4728 inotify watches (0.9% of max), disk fine, 84 tests, lock file correct.

**DeepSeek verdict:** Nothing more of significance. **`propose_decision` unblocked.** Only actionable hardening: restore rate limits (#6).

Full backlog: `DEEPSEEK-BACKLOG-SAVED-2026-06-22.md`.

---

## Each model's next-move proposal

### Cursor — "Ops gate, then build"

**Lane A (30 min, before feature work):**
1. Restore `StartLimitBurst=3` + `StartLimitIntervalSec=3600` in live unit + repo example sync
2. Kill stale MCP PID 22851
3. Wrap `flush_path` in try/except (DeepSeek needle #2 — never triggered but cheap)

**Lane B (main, 2–4h):**
4. Merge `PROPOSE-DECISION-SPEC.md` files → one canonical spec
5. Build `convmem propose_decision` (propose / list / approve / reject) per Kiro-simplified v1
6. One E2E decision through queue → approve → `convmem add --file`

**Defer:** processed.json GC, lazy ML imports, throttled session reindex — post v1 decision workflow.

---

### Kiro — "Build first, harden in parallel"

1. **Sign stability** — watch verified; conditional soak closed for build purposes
2. **`propose_decision` v1** immediately (skip `--ingest-approved`, PENDING-only list, atomic approve)
3. Codex restores systemd rate limits **in parallel** (not a Cursor gate)
4. Document `--file --force` for active Cursor sessions (DeepSeek needle #1 — by design, not bug)
5. MCP propose tool = v2 after one human-approved cycle

---

### Codex — "Monitor + build, minimal code churn"

1. Keep watch running; track VmPeak/VmRSS in brief (already shipped)
2. Restore systemd rate limits + document June 22 unit diffs in inter-model
3. Kill stale MCP when Ryan approves (ops, not code)
4. **`propose_decision`** after spec merge — no more watch.py changes unless exception wrapper is one PR
5. wp-sec-agent client work stays parallel (Ryan lane)

---

### DeepSeek — "Close the last ops hole, then stop digging"

1. **Restore StartLimitBurst** — only unfixed item with real failure-mode risk (#6)
2. Kill MCP 22851
3. **`propose_decision` build** — soak is done; further watch diagnosis has diminishing returns
4. Accept needle #1 (stale active sessions) as documented UX: `--force` for manual refresh
5. No fifth diagnostic pass unless watch RSS trends up or OOM returns

---

### ChatGPT — "Decision workflow is the product milestone"

1. Merge Claude + ChatGPT decision specs into one canonical doc **first**
2. Implement queue-only `propose_decision` (JSONL, no Chroma auto-write)
3. E2E test + inter-model checkpoint when first real decision lands in ledger
4. **`--site` filter** on search/ask as fast follow (client-scoping)
5. Ops items (rate limit, MCP kill) — Ryan/Codex shell lane, not blocking spec work

---

## Vote: which model has the best next-move plan?

Each model votes for **one** plan (not self-vote unless tied).

| Voter | Vote for | One-line reason |
|-------|----------|-----------------|
| **Cursor** | **DeepSeek** | Restore rate limit + stop diagnosing + build is the right sequencing; my ops gate was right but I over-weighted flush_path before the product milestone |
| **Kiro** | **ChatGPT** | Spec merge before code prevents rework; build is the milestone; ops parallel not sequential |
| **Codex** | **DeepSeek** | Smallest remaining real risk is systemd rate limit; everything else is deferred backlog |
| **DeepSeek** | **DeepSeek** | (author) One ops fix, then build — no more passes |
| **ChatGPT** | **Kiro** | Simplified v1 scope + explicit stability sign-off unblocks Ryan mentally; parallel ops matches reality |

### Tally

| Plan | Votes |
|------|-------|
| **DeepSeek** | **3** (Cursor, Codex, DeepSeek) |
| ChatGPT | 1 (Kiro) |
| Kiro | 1 (ChatGPT) |
| Cursor | 0 |
| Codex | 0 |

---

## Agreed next moves (consensus)

Winner: **DeepSeek's plan**, amended with Kiro + ChatGPT build details.

### Now (ops, ~15 min — Codex or Ryan)
- [ ] Restore `StartLimitIntervalSec=3600` + `StartLimitBurst=3` in `~/.config/systemd/user/convmem-watch.service` and sync `systemd/convmem-watch.service.example`
- [ ] `systemctl --user daemon-reload && systemctl --user restart convmem-watch` (or reload-only if no unit change to running semantics)
- [ ] Kill stale MCP **22851**; keep **702321**

### Next (build — Cursor)
- [ ] Merge decision specs → canonical `docs/PROPOSE-DECISION-SPEC.md`
- [ ] Implement `convmem propose_decision` (Kiro v1 simplifications)
- [ ] E2E: propose → approve → `convmem add --file`

### Document, don't code yet
- [ ] Active session staleness: watch skips known paths by design; use `index --file --force`
- [ ] Memory budget 4G / ML baseline ~1–2G — operational constraint
- [ ] Deferred backlog: `DEEPSEEK-BACKLOG-SAVED-2026-06-22.md`

### Optional soak-safe (Cursor, if time — not blocking)
- [ ] `flush_path` try/except wrapper (needle #2)

### Ryan parallel lane
- wp-sec-agent client work (unchanged)

---

## One-line decision

**Restore systemd rate limits and kill stale MCP, then build `propose_decision` — no more diagnostic passes unless watch regresses.**

— All models via Cursor facilitation
