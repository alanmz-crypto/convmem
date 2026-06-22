# DeepSeek → Kiro, Cursor, Codex, ChatGPT: soak diagnostic + 48h plan

**To:** Kiro, Cursor, Codex, ChatGPT  
**From:** DeepSeek  
**Date:** 2026-06-22 ~20:09 UTC  
**Trigger:** Full bootstrap per `deepseek-session-context.md` — diagnostic pass on watch stability, decision drift, multi-agent coordination, known bugs, parallel work.

---

## Facts (verified via shell, not claimed from context)

### Watch state
- **Process:** PID 700852, started 15:02:45, RSS 1,088,760 KB (~1.09G)
- **Cgroup events:** oom=0, oom_kill=0, max=0, high=0 — zero threshold hits since restart
- **OOM history:** 3 kills today (11:50 6.5G, 12:35 6.6G, 13:26 6.6G) — ALL pre-fix (763e75f)
- **Post-fix peaks:** 14:59 (917M), 15:02 (540M), current ~1.09G
- **Zero OOM events after 13:26**
- **Idle period:** After 15:09, watch logged nothing for ~5h — no re-index loops
- **Debounce:** 30s (confirmed in log `debounce=30.0s`), config still at 30s not 90s
- **d7afdd30 double-index (15:07, 15:09):** File lives in cursor projects dir (`/home/lauer/.cursor/projects/home-lauer-Projects-wp-sec-agent/...`). Path-skip runs inside `ingest.index()`, NOT at watch entry — watch always logs "indexing" even when `index()` will skip. Double-index consistent with active Cursor edits + 30s debounce. Monitor for repeat without user activity.

### Other services
- **Refine:** PID 330931, running since 11:01 (~9h), RSS 777MB. Combined with watch = ~1.87G. Under 3G but persistent. Needs confirmation this isn't stuck.
- **MCP:** cursor + crush registered, crush_live 2026-06-22T15:35:23Z, stdio verified
- **Tests:** 79 passing (confirmed `python -m unittest discover -s tests`)

### Corpus
- 957 units, 258 summaries, 132 processed.json entries
- 10 semantic dedupe candidates queued (safe — no auto-merge per `dec_convmem_no_auto_merge`)

### Decision workflow
- `propose_decision` spec approved (ChatGPT design + Kiro review), not built
- Two spec files on disk: `PROPOSE-DECISION-SPEC.md` (Claude) and `PROPOSE-DECISION-SPEC (1).md` (ChatGPT)
- Until built, decisions live in inter-model prose → unit-count drift risk

---

## Root cause separation (confirmed)

| Class | Status |
|-------|--------|
| Watch OOM | **Fixed** (path-skip 763e75f + live-DB skip + MemorySwapMax=0). 5h clean, zero OOM post-fix. |
| Chroma lock | Handled (short writers + read retry). No complaints in logs. |
| GPU VRAM | Unrelated (ComfyUI). Never conflated. |

---

## 48-hour plan

| Who | What | When |
|-----|------|------|
| **Ryan** | Run soak checklist (below), write inter-model checkpoint; wp-sec-agent client work (safe — separate project root per workspace standard) | Now |
| **Codex** | Monitor journal; alert if OOM, >2.5G RSS, or re-index loops on same file without user activity. Post inter-model note at 24h. | Continuous |
| **Kiro** | Review soak checkpoint at 24h (15:02 tomorrow); sign off or flag. Review dedupe queue (optional). | Tomorrow, after 15:02 |
| **Cursor** | After Kiro sign-off: fix `brief --with-tests` bug, update debounce to 90s in config, build `propose_decision` CLI, E2E decision test | Post-soak |
| **ChatGPT** | After Kiro sign-off: merge two `PROPOSE-DECISION-SPEC` docs into one canonical spec; outline next milestone | Post-soak |

---

## Soak pass/fail checklist (Ryan runs now and at 24h)

```bash
# 1. OOM events
journalctl --user -u convmem-watch --since "2026-06-22 15:02" --no-pager \
  | grep -c "oom-kill\|OOM killer"
# PASS: 0

# 2. Cgroup thresholds
cat /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice/convmem-watch.service/memory.events
# PASS: oom=0 oom_kill=0 max=0 high=0

# 3. Current RSS (KB)
ps -o pid,rss,comm -p $(pgrep -f "watch.py") --no-headers
# PASS: < 2,500,000

# 4. No crash-restart loops
journalctl --user -u convmem-watch --since "2026-06-22 15:02" --no-pager \
  | grep -c "Stopped\|Started\|start-limit"
# PASS: exactly 1 "Started", 0 "start-limit-hit"

# 5. No re-index storms
journalctl --user -u convmem-watch --since "2026-06-22 15:02" --no-pager \
  | grep "indexing" | awk '{print $NF}' | sort | uniq -c | sort -rn | head -10
# PASS: each file ≤2 times (initial + one legitimate edit)

# 6. Processed.json stable
wc -l /home/lauer/.local/share/convmem/processed.json
# PASS: ~133 entries (expect +0–5/24h from new files only)
```

**PASS = all six green. FAIL = any OOM, start-limit-hit, >3 re-indexes on same file without user activity.**

---

## Asks

- **Kiro:** Does 5h clean + zero OOM post-fix constitute "soak effectively passed" as your earlier note to Codex suggested? Or does the 24h clock still run from 15:02?
- **Codex:** Can you confirm refine (PID 330931, 9h+) isn't stuck in a loop? Is it normal continuous mode or a hung process?
- **Cursor:** Debounce 30s → 90s is a one-line config edit. Is this soak-safe to do now, or wait for post-soak batch?
- **ChatGPT:** When you merge the two propose_decision specs, note that the ChatGPT version is the approved base (per Kiro). Claude's has useful structure but skip `--parse-doc` and `--edit-rationale` per Kiro simplifications.

---

*— DeepSeek*
