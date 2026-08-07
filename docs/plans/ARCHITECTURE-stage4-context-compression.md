# Architecture: Stage 4 — Evidence-Driven Context Compression

```text
Planning Status

Phase:        Closed
Characters:   Architect, Systems Thinker, Risk Reviewer → Cursor → Ryan
Functions:    Planner
Lanes:        Cursor shipped Task 1; Ryan closed arc 2026-07-19
Authority:    Stage 4 CLOSED (Ryan) — residual deferred to a future separate arc
Probe Version: v1
```

| Field | Value |
|---|---|
| Status | **CLOSED (2026-07-19)** — digest demotion shipped (PR #46) + measured; residual (~100k) out of scope |
| Parent arc | [`ARCHITECTURE-token-efficient-bounded-autonomy.md`](ARCHITECTURE-token-efficient-bounded-autonomy.md) Stage 4 deferral |
| Evidence | Pre: 6 Crush tasks ~99.7% input. Post: 3 Crush tasks mean ~103.5k prompt (~8% drop vs ~112.4k) |
| Owner | Ryan owns durable conclusions and merge to `main` |
| Objective | Cut standing input-context cost without cutting safety, retrieval quality, or charter gates |
| Outcome | Primary lever (Crush always-loaded digests → on-demand) met. Compact brief rejected. Residual = tools/history/protocol → new arc if chased later |
| Promotion gate | Met and closed |

**Execution:** [`EXECUTION-stage4-context-compression.md`](EXECUTION-stage4-context-compression.md)

## Decision (recommended path — pending HITL)

**Primary lever is not `brief`.** On the surface where Stage 4 telemetry was collected (Crush), ~97% of configured always-loaded global context is the seven builder digests. `convmem brief --stdout-only` is ~1.5k tokens. Compressing brief alone cannot explain or fix the ~84–149k prompt tokens per routine task.

Recommended direction (one path):

1. **Crush standing context:** Stop always-loading builder digests via `global_context_paths`. Match Cursor’s thin pointer pattern (`builder-reference.mdc` → read digests when architecture work needs them). Keep ritual + compact Crush convmem rules always-on.
2. **Protocol:** Profile always-loaded protocol slices for duplication vs digests; trim only proven redundancy; hard ceiling and Ryan approval before growing standing text.
3. **`brief`:** Optional later compact *render* path only — same `gather_brief_data` / `gather_brief_payload`, alternate `render_*` — and only after Crush digest demotion is measured. Do not fork gather logic.
4. **Tool-output budgets:** Deferred until post-demotion telemetry shows tool dumps dominate residual cost.

## Why this is an architecture decision

The hard-to-change part is **what every session pays for before any task work**. Wrong cuts create false-PASS orientation (missing safety/domain rules) or silent retrieval amnesia (agents stop seeing builder constraints when they need them). Right cuts move expensive, rarely-needed text to on-demand load without changing decision rights.

## Telemetry gate (satisfied)

Six comparable Crush / `deepseek-v4-flash` routine tasks (docs update, test add, docs verify×2, small refactor, smoke test):

| Task | Prompt | Completion | % input |
|---|---:|---:|---:|
| T1 LATEST.md refresh | 118,606 | 440 | 99.6% |
| T2 collection_count smoke | 148,856 | 582 | 99.6% |
| T3 MODEL-WORKFLOW recon | 83,094 | 229 | 99.7% |
| T4 unused import | 91,906 | 262 | 99.7% |
| T5 tldr recon | 87,441 | 123 | 99.9% |
| T6 parse_ts smoke | 144,307 | 339 | 99.8% |

**Mean input share ~99.7%.** Zero-change tasks still cost ~83–87k prompt tokens. Input context dominates; Stage 4 is authorized by the parent arc’s evidence rule.

## Standing-context profile (2026-07-19, Auto)

Rough token estimate = bytes / 4 (prose; not provider-exact).

| Layer | Bytes | ~Tokens | Notes |
|---|---:|---:|---|
| Crush builder digests (7 files, always-loaded) | 109,286 | ~27,300 | **97.2%** of Crush `global_context_paths` stack |
| Crush CRUSH.md + CONVMEM-RITUAL.md | 3,168 | ~800 | Keep |
| `config/agent-protocol.md` | 16,308 | ~4,100 | Always-loaded on protocol surfaces |
| Cursor `convmem.mdc` | 13,057 | ~3,300 | Cursor stack (no full digests) |
| Cursor `builder-reference.mdc` | 1,235 | ~300 | Thin pointer — digests on demand |
| `convmem brief --stdout-only` | 5,787 | ~1,450 | Small vs Crush digests |

Crush `global_context_paths` currently lists ritual, the `rules/` directory, each digest file, and CRUSH.md — digests are therefore standing cost on **every** Crush turn, including routine reversible work that never needs Ousterhout/DDIA.

**Double-load (Kiro):** Digests appear both under `rules/` (directory glob) and as
seven individual path entries. If Crush does not dedup, standing digest cost may be
~54k tokens, not ~27k. Demotion must move digests **out of** `rules/` into
`~/.config/crush/builder-reference/` (approach A) — removing only the individual
entries is insufficient. Exact post-demotion `global_context_paths` is locked in
[`EXECUTION-stage4-context-compression.md`](EXECUTION-stage4-context-compression.md) Task 1.

Residual prompt after ~27k–54k digest estimate still leaves substantial tokens (tools,
history, file reads, MCP dumps). Demoting digests is necessary but may not be
sufficient; post-change telemetry decides the next cut.

## `brief.py` boundary (must reuse)

Existing split (do not parallelize):

| Function | Role |
|---|---|
| `gather_brief_data` | Collect corpus/service/handoff/project facts |
| `gather_brief_payload` | MCP/programmatic wrapper + coordination metadata |
| `render_brief_markdown` | Human/CLI markdown only |

Any compact orientation path must:

- call the same gather functions;
- change only render (or a documented render variant);
- preserve mandatory safety/domain signals already in gather (unresolved, standing due, stale handoff, watch risks, MCP status);
- remain semantically equivalent for session orientation — not a second brief product.

## Options compared

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| A. Compact brief only | Small PR; uses gather/render boundary | Wrong dominant cost on Crush | Reject as primary |
| B. Demote Crush digests to on-demand | Largest measured standing cut; matches Cursor | Must preserve discoverability for architecture work | **Recommend** |
| C. Trim always-loaded protocol | Helps all surfaces | Risk of cutting gates; needs word ceiling | Secondary, gated |
| D. Cap tool/search dumps now | May cut residual | No post-digest evidence yet | Defer |
| E. Do nothing | Zero risk | Leaves ~99.7% input waste proven | Reject |

## Constraints

- No parallel brief implementation.
- Do not cut mandatory safety/domain rules from always-loaded protocol.
- Agents never merge `main`; Ryan owns HITL and merge.
- WordPress / external mutation unchanged by this arc.
- Parent arc Stage 3 bounded autonomy remains; this arc only addresses standing context.
- Surface variance is allowed in *load strategy* (always vs on-demand), not in *authority gates*.

## Risks

| Risk | Mitigation |
|---|---|
| Architecture tasks miss digests | Keep thin pointer + “read digest when touching architecture/retrieval” in Crush rules (Cursor pattern) |
| False savings (tokens move into tool reads of digests) | Measure Crush prompt totals on 3 matched tasks after demotion |
| Protocol trim removes a hard gate | Diff review + doctor + no cut without Ryan approval |
| Mtime STALE HANDOFF false positive distracts | Separate bug; out of Stage 4 scope |

## Rejected alternatives

- Inventing a % savings target before post-change telemetry (parent architecture already rejected unverifiable percentages).
- Loading digests into brief instead of Crush globals (moves cost; does not remove it).
- New CLI/`brief --tiny` as a second product without gather reuse.

## Exit criteria (this phase)

- Direction artifact complete — **done**.
- HITL ACCEPT (Kiro) + approach A — **done**.
- Task 1 shipped (PR #46 / `bd037b8`) — **done**.
- Task 2 post-demotion telemetry — **done** (Ryan closed Stage 4 2026-07-19).
- Task 3 not opened — residual is a **separate future arc**, not Stage 4 continuation.

Stage 4 CLOSED. No further runtime work under this arc.
