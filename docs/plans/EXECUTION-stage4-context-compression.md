# Execution Plan — Stage 4 Context Compression

```text
Planning Status

Phase:        Execution Planning (draft under Architecture HITL hold)
Characters:   Cursor → Codex (optional audit) → Ryan
Lanes:        Cursor drafts/implements after HITL; Ryan accepts
Authority:    Blocked until ARCHITECTURE-stage4-context-compression.md HITL accept
```

**Architecture SSoT (draft):** [`ARCHITECTURE-stage4-context-compression.md`](ARCHITECTURE-stage4-context-compression.md)
**Plan branch:** `plan/2026-07-19-stage4-context-compression`
**Worktree:** `~/Projects/convmem-wt-stage4-context-compression`

## Do not start until

Ryan accepts (or revises) the architecture direction. This file is a **ready-to-shape** skeleton so HITL can see the intended tasks. It is not authorization to edit Crush config or protocol.

## Accepted gates (from architecture draft)

| # | Decision |
|---|---|
| 1 | Telemetry gate already PASS (6 Crush tasks, ~99.7% input) |
| 2 | Primary cut = Crush always-loaded builder digests → on-demand |
| 3 | Keep ritual + compact Crush convmem rules always-on |
| 4 | Reuse `brief.py` gather; compact render only if still needed after demotion |
| 5 | No parallel brief; no unverifiable % savings claims |
| 6 | Measure 3 matched Crush tasks before claiming success |

## Proposed task sequence (post-HITL)

### Task 0 — baseline snapshot

- Record Crush `global_context_paths` and byte totals (already in architecture profile).
- Record three baseline Crush session `prompt_tokens` on matched small tasks (or reuse T3/T5-style verified-clean if Ryan prefers no extra work).

### Task 1 — Crush digest demotion

- Remove the seven `builder-reference-*.md` entries (and redundant `rules/` directory load if it double-counts) from Crush `global_context_paths`.
- Add/ensure a thin Crush pointer rule mirroring Cursor `builder-reference.mdc`: read digests when architecture/retrieval/infra design is in scope.
- Deploy via existing Crush config/deploy path — no hand-edited one-off forks.
- Verification: Crush session starts without digests in standing context; architecture-tagged task still finds digests via pointer.

### Task 2 — post-demotion telemetry

- Run 3 comparable routine Crush / DeepSeek V4 Flash tasks (same shapes as Stage 4 sample).
- Extract `prompt_tokens` / `completion_tokens` from `.crush/crush.db`.
- PASS if mean prompt drops materially vs T1–T6 baseline **and** no safety/orientation regression (doctor, protocol ritual still followed).

### Task 3 — only if residual still input-dominated

- Protocol redundancy trim (word ceiling; Ryan approval) **or**
- Compact `render_brief_markdown` variant using same gather (optional CLI/MCP flag) — never a second gather path.

### Task 4 — close

- Update parent [`EXECUTION-token-efficient-bounded-autonomy.md`](EXECUTION-token-efficient-bounded-autonomy.md) Stage 4 pointer to this arc’s accepted status.
- Track A index; no record block unless Ryan asks.

## Explicit non-goals (this execution)

- Implementing compact brief before Task 2 evidence.
- Fixing STALE HANDOFF mtime heuristic (separate bug).
- WordPress probation or external authorization changes.
- Merging to `main` (Ryan only).

## Completion criteria

- Architecture HITL accept + Task 1 shipped + Task 2 telemetry reported; **or**
- Ryan stops after architecture reject / deliberate hold.

Cursor must stop here until architecture HITL.
Await HITL.
