# Execution Plan — Stage 4 Context Compression

```text
Planning Status

Phase:        Closed
Characters:   Cursor → Kiro (architecture) → Ryan
Lanes:        Cursor shipped Task 1; Ryan closed arc
Authority:    Stage 4 CLOSED (Ryan 2026-07-19)
```

**Architecture SSoT:** [`ARCHITECTURE-stage4-context-compression.md`](ARCHITECTURE-stage4-context-compression.md)
**Shipped:** PR [#46](https://github.com/alanmz-crypto/convmem/pull/46) → `main` @ `bd037b8`

## Closure (Ryan 2026-07-19)

Stage 4 is **closed**. The digest-demotion lever shipped and was measured. The
~100k residual prompt cost is tools / history / protocol — **not** brief or
digests. Chasing that residual requires a **new arc** with its own baseline,
not Stage 4 Task 3.

| Gate | Result |
|---|---|
| Pre-telemetry (T1–T6) | PASS — mean ~112.4k prompt, ~99.7% input |
| Architecture HITL | ACCEPT (Kiro) + approach A |
| Task 1 demotion | Shipped PR #46 |
| Task 2 post-telemetry | PASS as evidence — mean ~103.5k prompt (~8% drop), still ~99.8% input |
| Task 3 | **Not opened** — brief deferred permanently for this arc; residual out of scope |

### Task 2 numbers (post-demotion)

| Session | Shape | Prompt | Completion | Cost |
|---|---|---:|---:|---:|
| Post-1 | LATEST.md (docs) | 97,833 | 145 | $0.0147 |
| Post-2 | synthesis pointers (docs) | 105,591 | 345 | $0.0237 |
| Post-3 | `render_doctor_text` smoke | 107,098 | 99 | $0.0163 |

## Accepted gates (historical)

| # | Decision |
|---|---|
| 1 | Telemetry gate PASS (6 Crush tasks, ~99.7% input) |
| 2 | Primary cut = Crush always-loaded builder digests → on-demand |
| 3 | Keep ritual + compact Crush convmem rules always-on |
| 4 | Reuse `brief.py` gather; compact render only if still needed after demotion — **not needed** |
| 5 | No parallel brief; no unverifiable % savings claims |
| 6 | Measure post-demotion Crush tasks before claiming success — **done** |

## Task 1 — Crush digest demotion (approach A) — SHIPPED

Runtime + deploy/verify updated so digests live under
`~/.config/crush/builder-reference/`, standing paths are ritual + `rules/` +
CRUSH.md, thin pointer in `rules/builder-reference-pointer.md`.

## Explicit non-goals (closed arc)

- Compact brief (wrong lever; <2% of residual).
- Protocol / tool-dump residual chase (future arc only).
- STALE HANDOFF mtime heuristic (separate bug).
- WordPress / external mutation.

## Completion criteria

**Met.** Stage 4 CLOSED.
