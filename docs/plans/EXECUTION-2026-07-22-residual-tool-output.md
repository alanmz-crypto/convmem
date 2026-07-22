# Execution: Residual tool-output (Crush cost)

| Field | Value |
|---|---|
| Status | **Blocked on HITL** — do not start Tasks 0–3 until Ryan accepts [ARCHITECTURE-residual-tool-output.md](ARCHITECTURE-residual-tool-output.md) |
| Architecture | [ARCHITECTURE-residual-tool-output.md](ARCHITECTURE-residual-tool-output.md) |
| VERIFY | Create `VERIFY-residual-tool-output.md` from template only after Execute is authorized |
| Parent closed | Stage 4 — [EXECUTION-stage4-context-compression.md](EXECUTION-stage4-context-compression.md) stays CLOSED |

## Human consequence

Each task below exists to lower Crush token spend without making agents blind to
failures. Skipping measurement (Task 2) means we might ship a rule that feels
virtuous but does not change your bill.

## Preconditions

1. Architecture direction **accepted** (Ryan; Kiro review recommended).
2. Stage 4 remains CLOSED — no digest re-load, no compact-brief reopen.
3. Work on a `feat/` or `plan/` branch; Ryan merges; agents do not merge `main`.

## Tasks (after accept)

### Task 0 — Baseline honesty

- Confirm Crush auto-summarize is not disabled (`disable_auto_summarize` unset / off).
- Snapshot standing context byte totals (expect ~23KB / ~6k tokens class).
- Freeze comparison baseline: Stage 4 Post 1–3 mean prompt ~103.5k (band ~98–107k).

**Done when:** short note in VERIFY or handoff with numbers, not adjectives.

### Task 1 — Thin Crush tool-hygiene rule

- Add `config/crush-rules-tool-output-hygiene.example.md` (or equivalent name matching deploy patterns).
- Deploy path: same as other Crush rules via `scripts/deploy-agent-protocol.sh` into `~/.config/crush/rules/`.
- Content constraints:
  - Hard guidance for `bash` / `view` / `grep` output kept in chat (line/byte budgets).
  - Prefer ranged reads (`head`/`tail`/`sed -n`, `view` offset/limit).
  - **Failure exception:** non-zero exit → show exit + last N lines; never silent truncate of failures.
  - Do not strip ritual / charter / doctor-first text.

**Done when:** example + deploy wired; Crush restart guidance noted (hooks/rules load at process start).

### Task 2 — Measure

- Run ≥3 comparable Crush / `deepseek-v4-flash` routine sessions (same class as Stage 4 posts).
- Extract `prompt_tokens` / `completion_tokens` / cost from Crush telemetry.
- Compare mean prompt to Post 1–3 band.

**Done when:** table in VERIFY; PASS only if mean prompt drops meaningfully vs ~100k **or** Ryan accepts a documented miss with next step.

### Task 3 — MCP clips only if needed

- Open only if Task 2 mean prompt still ≳90k **and** breakdown shows fat MCP JSON dumps.
- Reuse existing clip helpers; no parallel “evidence budget” product name.
- Re-measure after.

**Done when:** either skipped with evidence, or small shared truncate + re-measure.

### Close

- Update architecture/execution status; leave Stage 4 untouched.
- Optional: one Active-handoff line in `docs/inter-model/LATEST.md` after land.

## Explicitly out of scope

- Next semantic-dedupe similarity bands / Phase D
- R2b live capture
- GitHub.com Copilot billing settings
- Reopening Stage 4 digest demotion

## Stop conditions

- HITL reject → stop immediately.
- Task 2 shows no savings and MCP not implicated → stop; report; do not invent Task 4.
