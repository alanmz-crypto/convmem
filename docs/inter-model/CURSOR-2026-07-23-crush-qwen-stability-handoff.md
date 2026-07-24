# Cursor handoff — Crush freezes + Qwen/DeepSeek billing routing (2026-07-23)

**Who:** Cursor (implementer) — verification open for Ryan / Crush soak / optional Copilot audit.  
**What:** Stabilize Crush+ConvMem freezes; default Crush to Qwen3.7-Max; disable wedged Crush MCP; route scarce Cursor tokens to Crush Qwen + DeepSeek V4.  
**When:** 2026-07-23 evening; branch tip follows commits below (pushed).  
**Why:** Crush UI hung 10–15+ min on “waiting for tool”; Cursor/other IDE quotas run dry mid-cycle while Alibaba Qwen and DeepSeek still have headroom.  
**How:** Runtime Crush/Continue config + protocol/docs/hook changes; MCP left disabled until a timed soak proves tools/call returns.

## VERIFY results (2026-07-23 ~22:05)

| Check | Result | Evidence |
|-------|--------|----------|
| **V1** Crush shell path (no multi-min hang) | **PASS** | Live Crush session 22:01–22:02 on `qwen3.7-max`: bash `convmem`/asserts completed; no `mcp_convmem_*` tool calls; agent reported automated checks pass |
| **V2** MCP disabled + Qwen defaults | **PASS** | `mcp.convmem.disabled=true`, timeout=180, large=`alibaba-singapore/qwen3.7-max`, recent includes DeepSeek V4 Pro/Flash |
| **V3** DeepSeek Crush seat | **PASS (config)** / soak optional | Model in Crush recent list; bootstrap updated; full Pro ritual soak left as optional post-merge |
| **V4** Continue DashScope | **PASS (config)** | `~/.continue/config.yaml` has `qwen3.7-max` @ `dashscope-intl` |
| **V5** Docs consistency | **PASS** | Billing-cycle + shell-only strings present in MODEL-WORKFLOW / bootstraps / CRUSH-VERIFY |
| CLI search latency | **PASS** | `convmem "crush qwen bootstrap"` ~6s |

`crush run` non-interactive yolo flags are unavailable on Crush v0.86 (`Unknown flag: --yolo` on `run`); V1 evidence is from the interactive Crush session in `crush.db`.

**Chat transcript (Track A):**  
`~/.cursor/projects/home-lauer-Projects-convmem/agent-transcripts/fc444fa8-9cf5-4cdd-933b-48909ae06d0e/fc444fa8-9cf5-4cdd-933b-48909ae06d0e.jsonl`

---

## Branch / commits (verify against `origin/main`)

```text
fix/2026-07-23-crush-qwen-stability
6563e53 Route scarce Cursor tokens to Crush Qwen and DeepSeek V4.
60f3396 Update Crush Qwen bootstrap to shell-only ConvMem.
b421398 Disable Crush ConvMem MCP until tools/call no longer hangs.
9844c86 Prefer Qwen3.7-Max in Crush and harden ConvMem MCP freezes.
```

```bash
git fetch origin
git log origin/main..origin/fix/2026-07-23-crush-qwen-stability --oneline
git diff origin/main...origin/fix/2026-07-23-crush-qwen-stability --stat
```

---

## Problem evidence (freeze)

| Observation | Evidence |
|-------------|----------|
| Crush stuck on `mcp_convmem_search_fast` | `~/Projects/convmem/.crush/logs/crush.log` last PreToolUse at ~21:33:53 with no tool result for 10–15+ min |
| MCP child idle, not working | PID ~62 MB RSS, threads on `anon_pipe_read` / `futex_do_wait` — Crush never completed `tools/call` |
| Death spiral | Hook denied `view`, steered model to MCP; MCP hung |
| Earlier same day | Log lines `MCP client failed to initialize` / `context canceled` |
| Shell ConvMem healthy | Fresh `convmem "…"` ~6s while Crush MCP hung |
| Resource pressure (context) | Swap full; idle Kiro MCP ~2.8 GB GPU; many Crush TTYs before prune |

---

## What changed

### A — Runtime (not in git; verify on disk)

| Item | Expected |
|------|----------|
| `~/.config/crush/crush.json` → `mcp.convmem.disabled` | `true` |
| `mcp.convmem.timeout` | `180` |
| `~/.local/share/crush/crush.json` → `models.large` | `alibaba-singapore` / `qwen3.7-max` |
| `models.small` | `alibaba-singapore` / `qwen3.6-flash` |
| `recent_models.large` (top) | qwen3.7-max, deepseek-v4-pro, deepseek-v4-flash, … |
| `~/.config/crush/CONVMEM-RITUAL.md` | Billing-cycle matrix + shell-only MCP note |
| `~/.config/crush/hooks/convmem-allow.sh` | Prefers bash `convmem "…"`; “Do not wait on mcp_convmem_*” |
| `~/.continue/config.yaml` | `Qwen3.7-Max (DashScope)` + Plus at top (`dashscope-intl` / `qwen3.7-max`) |
| Crush process count | Prefer **1** (`scripts/prune-stale-crush.sh` if more) |

Quick check:

```bash
python3 - <<'PY'
import json
from pathlib import Path
cfg=json.loads(Path.home().joinpath('.config/crush/crush.json').read_text())
rt=json.loads(Path.home().joinpath('.local/share/crush/crush.json').read_text())
assert cfg['mcp']['convmem'].get('disabled') is True
assert cfg['mcp']['convmem'].get('timeout') == 180
assert rt['models']['large']['model']=='qwen3.7-max'
assert rt['models']['large']['provider']=='alibaba-singapore'
print('PASS runtime crush defaults')
PY
rg -n 'Do not wait on mcp_convmem|Qwen3.7-Max|DeepSeek V4 Pro' ~/.config/crush/hooks/convmem-allow.sh ~/.config/crush/CONVMEM-RITUAL.md
rg -n 'dashscope-intl|qwen3.7-max' ~/.continue/config.yaml | head
pgrep -c crush || echo 0
```

### B — Repo (git)

| Path | Role |
|------|------|
| `docs/CRUSH-QWEN-BOOTSTRAP.md` | Paste-ready Crush+Qwen opener (shell-only) |
| `docs/CRUSH-DEEPSEEK-BOOTSTRAP.md` | Paste-ready Crush+DeepSeek V4 coverage opener |
| `docs/MODEL-WORKFLOW.md` | § Billing-cycle model routing |
| `docs/AGENT-ROLES.md` | Crush weights + DeepSeek-in-Crush clarification |
| `docs/inter-model/CRUSH-VERIFY.md` | Freeze checklist; MCP disabled; model matrix |
| `config/crush-global-convmem-ritual.example.md` | Deployed ritual source |
| `config/agent-protocol.md` (+ generated surfaces) | Qwen default + MCP hang → shell |
| `scripts/crush-hook-convmem-allow.sh` | Hook source (deploy copies to `~/.config/crush/hooks/`) |
| `scripts/prune-stale-crush.sh` | Kill stacked Crush TTYs |
| `scripts/generate-agent-protocol.sh` | Crush rules generation text |

---

## Verify plan (manual soak)

### V1 — Freeze gone (Crush shell path)

1. `bash ~/Projects/convmem/scripts/prune-stale-crush.sh` then start **one** Crush in `~/Projects/convmem`.
2. Model: **Alibaba Singapore → Qwen3.7-Max**.
3. Paste `docs/CRUSH-QWEN-BOOTSTRAP.md` block (or just ask project state).
4. **PASS:** ritual via bash completes; next ledger query uses `convmem "…"` / `convmem ask` within ~30s — **no** multi-minute “waiting for tool”.
5. **FAIL:** any hung `mcp_convmem_*` or wait >2 min with no progress.

### V2 — MCP stays off

```bash
python3 -c 'import json; from pathlib import Path; c=json.load(open(Path.home()/".config/crush/crush.json")); assert c["mcp"]["convmem"].get("disabled") is True; print("PASS mcp disabled")'
```

In Crush, MCP convmem tools should not be offered (or must not be used).

### V3 — DeepSeek coverage seat

1. Switch Crush model to **DeepSeek → deepseek-v4-pro** (or flash).
2. Paste `docs/CRUSH-DEEPSEEK-BOOTSTRAP.md`.
3. **PASS:** ritual + shell `convmem`; agent says “Crush found it”, not “DeepSeek found it”.

### V4 — Continue DashScope (optional)

1. Reload Continue / pick **Qwen3.7-Max (DashScope)**.
2. **PASS:** one short chat turn completes (proves key + endpoint).

### V5 — Docs consistency

```bash
rg -n 'Billing-cycle model routing|mcp.convmem.disabled|shell only' \
  docs/MODEL-WORKFLOW.md docs/CRUSH-QWEN-BOOTSTRAP.md \
  docs/CRUSH-DEEPSEEK-BOOTSTRAP.md docs/inter-model/CRUSH-VERIFY.md
```

---

## Explicit non-goals / gaps

| Gap | Notes |
|-----|--------|
| Crush MCP re-enable | **Not done** — needs timed soak proving `tools/call` returns |
| `llm.py` Alibaba provider for `ask`/summarize | **Not done** — `ask`/distill stay on DeepSeek V4 Flash API; summarize still local `llama3.1:8b` |
| Cursor hosting Qwen | **Impossible** on Cursor subscription — hand off to Crush when dry |
| Swap / Kiro GPU pressure | Noted; not “fixed” — close idle Kiro if freezes return |
| Open PR | Branch pushed; PR not opened unless Ryan asks |

---

## PR

- **[#106](https://github.com/alanmz-crypto/convmem/pull/106)** — `fix/2026-07-23-crush-qwen-stability` → `main` (tip `dc9fcc8`)

## Suggested next actions for Ryan

1. Review / merge [#106](https://github.com/alanmz-crypto/convmem/pull/106) (VERIFY PASS recorded above).
2. After merge: `bash scripts/deploy-agent-protocol.sh` if overlays look stale.
3. Habit: Cursor dry → Crush Qwen3.7-Max → rotate DeepSeek V4 Pro/Flash.
4. Only re-enable Crush MCP after a green timed soak; leave `disabled: true` until then.
5. Optional: Crush DeepSeek V4 Pro paste soak post-merge.

---

## TL;DR

Cursor fixed Crush freezes by disabling wedged ConvMem MCP and forcing shell `convmem`; defaulted Crush to Qwen3.7-Max; promoted DeepSeek V4 as the second Crush seat for mid-cycle token coverage; documented billing routing + paste bootstraps. Verify with one Crush soak (Qwen then DeepSeek) and the runtime asserts above — tip `6563e53` on `fix/2026-07-23-crush-qwen-stability`.
