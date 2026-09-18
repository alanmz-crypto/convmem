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
| `adapters/claude_session_jsonl.py` | Gate 1 adapter is on open PR #310 at exact Kiro-PASSed tip `ab8a9e16`; absent from `origin/main` at this handoff. |
| `adapters/detect.py` | Claude registration is on PR #310 only, not `origin/main`. |
| `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` | PR #310 rebinds revision/digest metadata; route payloads unchanged. PR body reports Ryan authorization for this cross-arc update; confirm at merge. |
| `adapters/jsonl_prefix.py` | Complete-line boundary, byte-range, and line-outcome helpers on `main`. |
| `incremental_jsonl_formats.py` | Kiro production set and isolated Codex set on `main`; no Claude spec or isolated set. |
| `incremental_jsonl.py` | Existing coordinator, default Kiro-only route; no Claude-specific core work needed. |
| `scratch_jsonl_prototype/live_source_canary.py` | Reviewed Kiro exact-source canary pattern; its engine is Kiro-specific. |
| `docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md` | Gate 2 plan Kiro PASS with Execute conditions at exact reviewed commit `a811f58`; the plan text is unchanged by this status update. |
| Production `[sources].paths` / `[watch].extra_paths` | Claude absent; no change authorized. |

The isolated Codex JSONL integration landed through PR #307 (`d657767`). The
current `origin/main` checked for this handoff was `63cd3bc` (PR #309). Neither
that substrate nor Gate 1 PR #310 authorizes automatic Claude capture.

## 4. Completion State

| Milestone | State | Next gate |
|---|---|---|
| Arc assignment | **CONFIRMED** by Ryan, 2026-09-18 | — |
| Gate 1 on-demand adapter | **KIRO CODE PASS / PR OPEN** at `ab8a9e16` (#310); not on `main`; final PR pytest pending at handoff | Ryan confirms final CI and cross-arc R2b rebind, then decides merge |
| Incremental substrate | **ON `main`** through PR #307; isolated Codex route exists | — |
| Gate 2 execution plan | **KIRO PASS WITH CONDITIONS** at `a811f58` | Ryan bounded Execute grant |
| Isolated Claude format and canary | **NOT STARTED** | Gate 1 merged and reviewed, Ryan bounded Execute grant |
| Exact-source live canary | **NOT AUTHORIZED** | Separate Ryan source grant after hermetic implementation |
| Production promotion and watch wiring | **NOT AUTHORIZED** | Ryan decision after reviewed canary evidence |

## 5. Your Role (read this to know what you're here to do)

**Ryan decision lane (next):** use the [PR decision handoff](../inter-model/CODEX-2026-09-18-claude-watch-parity-gate1-pr-decision-handoff.md).
Kiro reports code PASS at exact Gate 1 tip `ab8a9e16`; PR #310 is open and
awaiting final CI at this handoff. Confirm the R2b inventory metadata rebind,
then decide merge. Kiro also PASSed the Gate 2 plan at `a811f58` with
conditions; a bounded isolated Execute grant is a separate decision after
Gate 1 lands. It does not select a live source or authorize production
promotion.

**Cursor implementation lane:** start only after the Gate 1 adapter is merged
and Kiro-reviewed and Ryan grants Execute. Recheck Gate 1's mapper before the
first edit. State in VERIFY that `CONVMEM_INCREMENTAL_ROOT` enables one shared
Kiro+Codex+Claude isolated set; assert default Kiro-only routing and unchanged
Kiro/Codex behavior. Keep the live canary `NOT_RUN` without an exact Ryan grant
and inactive watcher. Lock the production-code diff to the Claude adapter and
`incremental_jsonl_formats.py`; stop at evidence for review.

**Ryan:** own the live-source grant and the later production promotion decision.

## 6. What Remains Before Live (sequential)

1. Ryan verifies final PR #310 CI and unchanged Kiro-PASSed Gate 1 tip,
   confirms the R2b inventory rebind, and decides merge.
2. After Gate 1 lands, update this snapshot from the merged tree. Ryan then
   decides a bounded isolated Execute grant against the reviewed `a811f58`
   plan, carrying Kiro's four conditions.
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
| Gate 1 PR/merge | Ryan | Claude prefix implementation against an unmerged adapter; Kiro reported code PASS at `ab8a9e16` |
| Bounded Execute grant | Ryan | Cursor isolated implementation; Kiro plan review passed at `a811f58` |
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
| 2026-09-18 | Codex | Recorded Kiro PASS with Execute conditions on exact plan tip `a811f58`; next gate is Ryan's bounded Execute decision. |
| 2026-09-18 | Codex | Gate 1 adapter found on pushed `cbdc88b` branch but not `main`; routed exact-tip code review to Kiro before Execute. |
| 2026-09-18 | Codex | Routed Kiro-PASSed Gate 1 PR #310 at `ab8a9e16` to Ryan for final CI and merge decision; Execute remains separate. |

**TL;DR [Arc Claude Watch Parity]:** Gate 1 passed Kiro's exact-tip code review
and PR #310 awaits Ryan's decision after final CI; it is not on `main`. The
isolated Gate 2 plan passed Kiro review at `a811f58`; Execute, live-source
canary, and production watch capture remain separate Ryan gates.
