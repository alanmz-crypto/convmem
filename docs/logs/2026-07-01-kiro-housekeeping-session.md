# 2026-07-01 Kiro session: housekeeping (telemetry, fixes, obs cleanup)

## Work performed

1. **P1c synthesis_failed telemetry** (`55bc381`)
   - Added `_log_synthesis_failure()` to `ask.py` — appends JSONL to `~/.local/share/convmem/synthesis_failures.jsonl`
   - Never raises; silently swallows telemetry errors
   - Gate detection: count failures in last 7 days; >=3 triggers P1c streaming work

2. **Wired synthesis_gate into `convmem doctor`** (`1935091`)
   - New check: `[PASS] synthesis_gate: 0 failures in 7d (gate: >=3 triggers P1c)`
   - Flips to FAIL when gate triggers

3. **Fixed `_first_sentence()` for --propose summaries** (`404019d`)
   - Skips LLM preamble patterns (Based on..., According to..., Here is/are..., All ... cited)
   - Strips markdown bold/italic and list markers
   - Requires >20 chars for substance
   - Reduced max_len 200 → 120
   - Tested against actual --propose trial output that triggered the issue

4. **Fixed `test_eval_golden` golden eval** (`a7b0890`)
   - Root cause: Rich ANSI escape codes in subprocess output broke panel boundary detection
   - Fix: set `NO_COLOR=1 TERM=dumb` in subprocess env
   - Score restored to 8/10 (pass bar met)
   - Q02 and Q10 are genuine retrieval misses, not parsing bugs

5. **Resolved 7 informational observations** (via `convmem verify --result pass`)
   - `obs_8a8df8e92318` — Kiro uses steering + shell (Tier A)
   - `obs_e4c18899fcac` — MCP JSON uses env vars not hardcoded keys
   - `obs_5584910584ee` — Kiro MCP config at ~/.kiro/settings/mcp.json
   - `obs_d348798e5fdd` — convmem add accepts observation type only
   - `obs_95aa7676bd8b` — MCP wiring doesn't guarantee ritual execution
   - `obs_ed3c403d56fa` — test observation (stale)
   - `obs_a170bc316c7c` — Kiro CLI uses pacman on Arch Linux

## Test suite status

- 170 tests, 1 failure (`test_ask_passes_site` — pre-existing, caused by uncommitted `mcp_server.py` changes from another model, not our work)
- Golden eval: 8/10 PASS (was 2/10 before ANSI fix)

## Unresolved count

14 → 7. Remaining:
- 6 client-site staging2 security headers (separate lane)
- 1 synthesis plan pointer (open by design until Phase 2 gates pass)

## Commits (all pushed)

| SHA | Message |
|-----|---------|
| `55bc381` | feat: add synthesis_failed telemetry for P1c gate detection |
| `1935091` | feat: wire synthesis_gate into convmem doctor |
| `404019d` | fix: tighten _first_sentence() for --propose summaries |
| `a7b0890` | fix: golden eval ANSI parsing — set NO_COLOR+TERM=dumb in subprocess |
