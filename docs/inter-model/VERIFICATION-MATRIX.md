# Verification matrix — global convmem protocol (Gap 8)

**Updated:** 2026-06-29

Tracks alien-workspace and edge-case scenarios from the global protocol planner. Log results in `SOAK-REPORT-2026-06-25.md` or append rows here.

## Matrix

| # | Scenario | Surface | Pass criteria | Status |
|---|----------|---------|---------------|--------|
| 1 | Alien WP repo | Cursor | MCP `brief()` or shell `doctor` before repo survey | **PASS** (Ryan retest ×2) |
| 2 | Alien WP repo | Kiro | `doctor` → MCP `brief` / shell ritual; no permission prompts | **PASS** (Ryan retest) |
| 3 | Alien WP repo | Crush | Shell `doctor` → `brief` → `unresolved`; permissions auto-allow | **PASS** (Ryan retest; model-dependent — see CRUSH-VERIFY.md) |
| 4 | Alien WP repo | Continue `cn --auto` | MCP `brief()` first; Tier-A local models (daily **qwen2.5-coder:14b**, heavy **qwen3-coder:30b**) | **PASS** (30b #10/#20); 14b **FAIL** (#19) |
| 5 | Blank dir `/tmp/test-empty` | Cursor | `convmem.mdc` in always-applied rules; agent runs convmem unprompted | **PASS** (2026-06-29) — `alwaysApply` on global `convmem.mdc`; agent root moved to `/tmp/test-empty`; ritual before dir survey |
| 6 | Blank dir `/tmp/test-empty` | Codex | `~/.codex/AGENTS.md` drives `doctor → brief → unresolved` | **PASS** (2026-06-29 `codex exec`; first cmd `convmem doctor`) |
| 7 | convmem repo | Cursor | Global rule + trimmed `AGENTS.md` — no conflicting double ritual | **PASS** — `AGENTS.md` defers to global (10 lines, no duplicate Tier A); Codex + Crush soaks 2026-06-29 run ritual once |
| 8 | Codex alien WP repo | Codex | `doctor → brief → unresolved` before repo survey | **PASS** (2026-06-29 `codex exec` willowyhollow-practice; full ritual then git/stack) |
| 9 | Continue IDE extension | Continue | Agent mode; MCP `brief` on convmem question | **TODO** (optional) — CLI `cn --auto` PASS (#4); extension soak: [`CONTINUE-VERIFY.md`](CONTINUE-VERIFY.md) |
| 10 | Post-deploy health | CLI | `convmem doctor` exit 0 | **PASS** |
| 11 | Kiro permissions merge | Deploy script | All shell patterns from example present after deploy | **PASS** (deploy verify) |

## How to run

### Alien WP (rows 1–4)

Dir: `~/WordPress/willowyhollow-practice/` or `~/WordPress/pavlomassage-practice/`

Prompt (unprompted): *What's the current state of this project?*

### Blank dir (rows 5–6)

```bash
mkdir -p /tmp/test-empty && cd /tmp/test-empty
```

Open in Cursor or Codex; same unprompted prompt. Global config must load without repo `AGENTS.md`.

### Codex alien (row 8)

1. Open alien WP repo in Codex.
2. Unprompted project-state query.
3. Pass: `convmem doctor` (or `bash -lc 'convmem doctor'`) → `brief` → `unresolved` before repo survey.
4. If `convmem ask` fails: confirm `~/.codex/AGENTS.md` deployed; in convmem repo: `cp .codex/config.toml.example .codex/config.toml`.

### Continue grading

After `cn --auto` soak:

```bash
bash ~/Projects/convmem/scripts/grade-continue-session.sh --at 'YYYY-MM-DD_HH-MM'
# or
bash ~/Projects/convmem/scripts/grade-continue-session.sh ~/.continue/sessions/<id>.json
```

See `CONTINUE-VERIFY.md`.

## Ryan manual checklist

- [x] Trim `~/.continue/config.yaml` — `rules:` session-close only ([config/continue-rules-session-close.example.yaml](../../config/continue-rules-session-close.example.yaml))
- [x] Tier-A models merged into `~/.continue/config.yaml` ([config/continue-models-tier-a.example.yaml](../../config/continue-models-tier-a.example.yaml))
- [ ] Continue smoke: `cn --auto` + **qwen2.5-coder:14b** alien dir (daily driver — **FAIL** headless #19; retest interactive)
- [x] Continue smoke: `cn --auto` + **qwen3-coder:30b** alien dir (**PASS** #20 regression)
- [ ] Continue smoke: `cn --auto` + **qwen3.6-27b-iq3-32k** / **iq3-crush** (#21–22 FAIL headless; optional interactive retest)
- [x] Codex alien soak (row 8) — **PASS** 2026-06-29 (`codex exec`, full ritual first)
- [x] Codex blank-dir soak (row 6) — **PASS** 2026-06-29
- [x] Cursor blank-dir runtime soak (row 5) — **PASS** 2026-06-29 (agent in `/tmp/test-empty`)
- [x] convmem repo double-load check (row 7) — **PASS** 2026-06-29
- [ ] Optional ledger record — draft in `LATEST.md` § Optional close
