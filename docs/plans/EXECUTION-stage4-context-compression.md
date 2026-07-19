# Execution Plan — Stage 4 Context Compression

```text
Planning Status

Phase:        Execution Planning
Characters:   Cursor → Codex (optional audit) → Ryan
Lanes:        Cursor implements after Ryan authorizes Task 1; Ryan accepts
Authority:    Architecture ACCEPT (Kiro 2026-07-19, approach A locked).
              Task 1 Crush/config edits still need Ryan authorize.
```

**Architecture SSoT:** [`ARCHITECTURE-stage4-context-compression.md`](ARCHITECTURE-stage4-context-compression.md)
**Plan branch:** `plan/2026-07-19-stage4-context-compression`
**Worktree:** `~/Projects/convmem-wt-stage4-context-compression`

## Do not start Task 1 until

Ryan authorizes Task 1 (Crush filesystem + `global_context_paths` edit). Architecture
direction is accepted; this file is the locked task shape.

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

### Task 1 — Crush digest demotion (approach A — locked)

Kiro required fix: `global_context_paths` currently **double-loads** digests — once via
`~/.config/crush/rules/` (directory glob of all 10 files) and again via seven individual
`builder-reference-*.md` entries. Removing only the seven entries leaves digests loaded
through `rules/`. Approach **(A)** is mandatory:

1. **Move** the seven files
   `~/.config/crush/rules/builder-reference-*.md` →
   `~/.config/crush/builder-reference/` (sibling directory; create if absent).
2. **Set** `options.global_context_paths` to exactly:
   ```json
   [
     "~/.config/crush/CONVMEM-RITUAL.md",
     "~/.config/crush/rules/",
     "~/.config/crush/CRUSH.md"
   ]
   ```
   After the move, `rules/` retains only always-on non-digests:
   `00-convmem-ritual.md`, `convmem.md`, `ksweep-routing.md`.
3. **Add** a thin Crush pointer under `rules/` (or CRUSH.md) mirroring Cursor
   `builder-reference.mdc`: when architecture / retrieval / infra design is in scope,
   read digests from `~/.config/crush/builder-reference/` (and/or
   `docs/builder-reference/` in-repo).
4. Deploy via existing Crush config/deploy path — no one-off undocumented forks.
5. **Verification:** (a) no `builder-reference-*.md` remains under `rules/`;
   (b) standing Crush session does not include digest bodies;
   (c) architecture-scoped task can still open digests via the pointer path.

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

- Architecture HITL accept (done) + Ryan Task 1 authorize + Task 1 shipped + Task 2
  telemetry reported; **or**
- Ryan stops / holds before Task 1.

Cursor must stop here until Ryan authorizes Task 1.
Await HITL (Task 1 authorize).
