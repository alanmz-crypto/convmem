# Arc Brief — Claude Watch Parity

> **Arc: Claude Watch Parity.** Read this brief before working on Claude
> transcript capture. State the product goal, your role, current system state,
> and next action before substantive work.

---

## 1. What This Is For (product goal)

Claude Code sessions should become searchable without paying to transform an
entire growing transcript on every append. Gate 1 provides explicit, on-demand
`convmem index --file` capture. Gate 2 adds a Claude complete-prefix contract
and proves incremental reuse under isolation before Ryan considers automatic
watch capture.

**Done means:** the Claude adapter and isolated incremental route have passed
focused tests and a reviewed, exact-source canary; Ryan has separately decided
whether to promote Claude into production routing and add `~/.claude/projects`
to watch. A plan, code merge, or canary PASS alone does not activate watching.

## 2. System Design (how the pieces connect)

```text
Claude ~/.claude/projects/<slug>/<uuid>.jsonl (read-only source)
                   |
                   v
       Gate 1 adapter: user/assistant text only
       strip injected wrappers; skip sidechains and non-text blocks
                   |
                   v
       parse_complete_prefix: complete lines + byte ranges
                   |
       isolated root only: ISOLATED_CLAUDE_FORMATS
                   v
       existing incremental coordinator -> scratch writer/Chroma
                   |
                   v
       content-free, exact-source canary evidence -> Kiro review
                   |
                   v
       Ryan-only production route and watch/source decision
```

The source bytes are input authority; the incremental checkpoint is processing
and recovery authority; Chroma and exports are derived projections. In this
phase, `KIRO_ROUTE_FORMATS` remains exactly `{jsonl_kiro_session}`. Claude is
eligible only under the existing explicit isolation boundary. The Kiro-only
scratch canary is a safety pattern, not a Claude parser or execution engine.

## 3. What Exists Right Now (file map)

| Surface | Current state |
|---|---|
| `adapters/claude_session_jsonl.py` | Missing on the planning base; Gate 1 on-demand adapter is approved for Cursor but not landed. |
| `adapters/detect.py` | No Claude classification or parser registration. |
| `adapters/jsonl_prefix.py` | Complete-line boundary, byte-range, and line-outcome helpers on `main`. |
| `incremental_jsonl_formats.py` | Kiro production set and isolated Codex set on `main`; no Claude spec or isolated set. |
| `incremental_jsonl.py` | Existing coordinator, default Kiro-only route; no Claude-specific core work needed. |
| `scratch_jsonl_prototype/live_source_canary.py` | Reviewed Kiro exact-source canary pattern; its engine is Kiro-specific. |
| `docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md` | Gate 2 plan on `plan/2026-09-18-claude-watch-parity`, awaiting Kiro review. |
| Production `[sources].paths` / `[watch].extra_paths` | Claude absent; no change authorized. |

The isolated Codex JSONL integration is on `main` at planning base
`d657767` (PR #307). That landed substrate does not authorize Claude capture.

## 4. Completion State

| Milestone | State | Next gate |
|---|---|---|
| Arc assignment | **CONFIRMED** by Ryan, 2026-09-18 | — |
| Gate 1 on-demand adapter decision | **APPROVED** (Option 2); code not on planning base | Cursor implementation on a green base, then Kiro code review |
| Incremental substrate | **ON `main`** through PR #307; isolated Codex route exists | — |
| Gate 2 execution plan | **DRAFT ON PUSHED PLAN BRANCH** | Kiro design review |
| Isolated Claude format and canary | **NOT STARTED** | Gate 1 merged, Kiro plan PASS, Ryan bounded Execute grant |
| Exact-source live canary | **NOT AUTHORIZED** | Separate Ryan source grant after hermetic implementation |
| Production promotion and watch wiring | **NOT AUTHORIZED** | Ryan decision after reviewed canary evidence |

## 5. Your Role (read this to know what you're here to do)

**Kiro review lane:** review the Gate 2 plan on its exact pushed tip. Check
that Claude cannot enter the default production set, Gate 1 is a prerequisite,
the canary binds one authorized source without content leakage, and promotion
stays with Ryan. Return written PASS or specific conditions.

**Cursor implementation lane:** start only after Kiro plan review and Ryan's
bounded Execute grant. Build and test the Claude prefix/spec and isolated
canary; stop at evidence. Do not infer watch authorization from implementation.

**Ryan:** own the live-source grant and the later production promotion decision.

## 6. What Remains Before Live (sequential)

1. Land and review the Gate 1 Claude on-demand adapter on a green base.
2. Kiro reviews this Gate 2 plan; Ryan grants bounded isolated implementation.
3. Cursor adds prefix parsing, the Claude format spec, isolated eligibility,
   tests, and an isolated canary harness; Kiro reviews the exact implementation.
4. Ryan may authorize one frozen Claude transcript for read-only canary capture.
   Arrange an inactive watcher window or suitable host, run the canary in a
   fresh scratch root, and review content-free evidence.
5. Ryan separately decides production-route promotion and watch/source wiring.
   Define a bounded operational acceptance and rollback plan before activation.

## 7. Hard Stops (models cannot cross)

| Stop | Owner | Blocks |
|---|---|---|
| Gate 1 adapter review | Kiro | Claude prefix implementation against an absent/unstable adapter |
| Gate 2 plan review + Execute grant | Kiro + Ryan | Cursor isolated implementation |
| Exact live-source grant | Ryan | Reading a live Claude transcript for the canary |
| Production promotion | Ryan | Adding Claude to `KIRO_ROUTE_FORMATS` or watch/source paths |
| Arc boundary | Ryan | Changes to Arc Codex plans, STATUS, canary grants, or operational state |

## 8. Relationship to ConvMem (the bigger picture)

This arc reuses the incremental JSONL coordinator and isolation seam landed for
Kiro/Codex. It owns Claude's format, content hygiene, and evidence for eventual
watch participation. Arc Codex retains its own Kiro-source canary and finish
line. No retrieval, chunking, provider, ledger, or production configuration
change is part of this planning phase.

## 9. Key Design Files (for deep dives)

| Purpose | Path |
|---|---|
| Gate 2 execution plan | `docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md` |
| Gate 1 adapter specification | `docs/inter-model/CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` (available in the shared checkout; not yet on this planning base) |
| Gate 1 decision | `docs/inter-model/KIRO-2026-09-18-claude-transcript-corpus-decision-brief.md` (available in the shared checkout; not yet on this planning base) |
| Sequencing decision | `docs/inter-model/KIRO-2026-09-18-claude-watch-parity-next-steps-handoff.md` (untracked in the shared checkout at plan time) |
| Existing canary pattern | `docs/inter-model/CODEX-2026-09-09-jsonl-incremental-live-source-canary-execute.md` |
| Runtime format registry | `incremental_jsonl_formats.py` |
| Shared prefix helpers | `adapters/jsonl_prefix.py` |
| Arc Codex boundary | `docs/plans/STATUS-codex-jsonl-production-integration.md` (read-only reference) |

Any later arc architecture file must use the matching suffix
`ARCHITECTURE-claude-watch-parity.md`.

## 10. How to Update This Brief (departure protocol)

Keep this a current-state snapshot. After a milestone changes state, overwrite
sections 3–6, preserve the live gates, and add one milestone-level line below.
Do not append a session diary. A fresh model should be able to read only this
brief and identify the next authorized action.

## Update Log

| Date | Who | Milestone-level change |
|---|---|---|
| 2026-09-18 | Codex | Created Ryan-confirmed Claude Watch Parity arc and Gate 2 plan for Kiro review; no implementation or live grant. |

**TL;DR [Arc Claude Watch Parity]:** Gate 1 is approved but not landed. The
isolated Gate 2 plan awaits Kiro review; Claude production routing and watch
capture remain Ryan-gated.
