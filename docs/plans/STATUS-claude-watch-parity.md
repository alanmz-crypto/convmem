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
| `adapters/claude_session_jsonl.py` | Gate 1 adapter is on `origin/main` at squash merge `aadf137` (PR #310; reviewed branch tip `ab8a9e16`). Real-transcript `index --file` acceptance is still `NOT_RUN`. |
| `adapters/detect.py` | Claude `jsonl_claude_session` registration is on `origin/main` through PR #310. |
| `docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` | PR #310 landed the Ryan-authorized revision/digest metadata rebind; route payloads stayed unchanged. |
| `adapters/jsonl_prefix.py` | Complete-line boundary, byte-range, and line-outcome helpers on `main`. |
| `incremental_jsonl_formats.py` | Kiro production set and isolated Codex set on `main`; no Claude spec or isolated set. |
| `incremental_jsonl.py` | Existing coordinator, default Kiro-only route; no Claude-specific core work needed. |
| `scratch_jsonl_prototype/live_source_canary.py` | Reviewed Kiro exact-source canary pattern; its engine is Kiro-specific. |
| `docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md` | Gate 2 plan Kiro PASS with Execute conditions at exact reviewed commit `a811f58`; the plan text is unchanged by this status update. |
| `docs/inter-model/CODEX-2026-09-18-claude-gate1-real-smoke-handoff.md` | Cursor handoff for hermetic isolated smoke preparation; no live source or run grant. |
| `claude_gate1_smoke.py` and smoke worker/tests | Synthetic CLI path on pushed `feat/2026-09-18-claude-gate1-real-smoke` at `e4e41ca`; seven focused tests pass, but configured output containment is not yet proven fail-closed. Not on `main`. |
| `docs/inter-model/CODEX-2026-09-18-claude-gate1-smoke-containment-corrective-handoff.md` | Cursor corrective brief for pre-import config/output containment and adversarial scratch tests; no live-source grant. |
| Production `[sources].paths` / `[watch].extra_paths` | Claude absent; no change authorized. |

The isolated Codex JSONL integration landed through PR #307 (`d657767`). The
current `origin/main` checked for this handoff was `aadf137` (PR #310). Neither
that substrate nor the merged Gate 1 adapter authorizes automatic Claude capture.

## 4. Completion State

| Milestone | State | Next gate |
|---|---|---|
| Arc assignment | **CONFIRMED** by Ryan, 2026-09-18 | — |
| Gate 1 on-demand adapter | **MERGED** via PR #310 at `aadf137`, after Kiro exact-tip PASS at `ab8a9e16` | Original real-transcript acceptance still `NOT_RUN`; finish smoke containment correction, then Ryan exact-source grants |
| Gate 1 synthetic smoke | **PUSHED / CORRECTIVE OPEN** at `e4e41ca`; seven hermetic tests pass, but output-path fail-closed evidence is incomplete | Cursor closes containment gap; targeted safety audit of exact tip before real indexing |
| Incremental substrate | **ON `main`** through PR #307; isolated Codex route exists | — |
| Gate 2 execution plan | **KIRO PASS WITH CONDITIONS** at `a811f58` | Ryan bounded Execute grant |
| Isolated Claude format and canary | **NOT STARTED** | Gate 1 merged and reviewed, Ryan bounded Execute grant |
| Exact-source live canary | **NOT AUTHORIZED** | Separate Ryan source grant after hermetic implementation |
| Production promotion and watch wiring | **NOT AUTHORIZED** | Ryan decision after reviewed canary evidence |

## 5. Your Role (read this to know what you're here to do)

**Cursor Gate 1 containment-corrective lane (next):** use the [corrective handoff](../inter-model/CODEX-2026-09-18-claude-gate1-smoke-containment-corrective-handoff.md).
The synthetic CLI smoke exists and passes, but its worker validates the source
without proving every configured output path is scratch-confined before index
imports. Add that fail-closed preflight and adversarial `tmp_path` tests on the
existing smoke branch. Stop before live-source access and return the pushed
tip for targeted GitHub Copilot isolation audit. The missing real-source
acceptance remains `files_processed=1`, `units_indexed>0` on a Ryan-granted
transcript, not synthetic parser/CI coverage.

**Ryan decision lane:** may separately name one exact file and authorize a
read-only fingerprint preflight; after the content-free packet and containment
review, separately authorize or decline one bounded real-source smoke. Kiro
also PASSed the Gate 2 plan at `a811f58` with conditions; its bounded isolated Execute grant remains a
separate decision. None of these grants implies production promotion.

**Cursor implementation lane:** start only after the Gate 1 adapter is merged
and Kiro-reviewed and Ryan grants Execute. Recheck Gate 1's mapper before the
first edit. State in VERIFY that `CONVMEM_INCREMENTAL_ROOT` enables one shared
Kiro+Codex+Claude isolated set; assert default Kiro-only routing and unchanged
Kiro/Codex behavior. Keep the live canary `NOT_RUN` without an exact Ryan grant
and inactive watcher. Lock the production-code diff to the Claude adapter and
`incremental_jsonl_formats.py`; stop at evidence for review.

**Ryan:** own the live-source grant and the later production promotion decision.

## 6. What Remains Before Live (sequential)

1. Cursor corrects the pushed synthetic Gate 1 CLI smoke so effective config,
   output paths, locks, and caches fail closed under scratch before index
   imports; targeted GitHub Copilot safety audit reviews the exact tip.
2. Ryan may name one exact Claude transcript for read-only fingerprinting;
   after a content-free packet and containment review, Ryan separately grants
   or declines one bounded real-source smoke. Record
   `files_processed=1` and nonzero `units_indexed` or an honest FAIL/NOT_RUN;
   do not equate merge with full real-source acceptance.
3. Ryan separately decides a bounded isolated Gate 2 Execute grant against
   reviewed plan `a811f58`, carrying Kiro's four conditions. Cursor then adds
   prefix parsing, the Claude format spec, isolated eligibility,
   tests, and an isolated canary harness; Kiro reviews the exact implementation.
4. Ryan may authorize one frozen Claude transcript for the **Gate 2** read-only canary capture.
   Arrange an inactive watcher window or suitable host, run the canary in a
   fresh scratch root, and review content-free evidence.
5. Ryan separately decides production-route promotion and watch/source wiring.
   Define a bounded operational acceptance and rollback plan before activation.

## 7. Hard Stops (models cannot cross)

| Stop | Owner | Blocks |
|---|---|---|
| Gate 1 exact-source preflight and one-shot smoke | Ryan | Reading or indexing a real Claude transcript; merged code and hermetic prep do not grant this |
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
| Gate 1 adapter specification | `docs/inter-model/CURSOR-2026-09-17-claude-transcript-adapter-handoff.md` on `origin/main` (not on this older planning-branch base) |
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
| 2026-09-18 | Codex | PR #310 merged Gate 1 at `aadf137`; routed still-open real-transcript acceptance to Cursor for hermetic preparation and Ryan exact-source grants. |
| 2026-09-18 | Codex | Synthetic Gate 1 smoke pushed at `e4e41ca`; routed incomplete config/output containment evidence to Cursor for correction before real indexing. |

**TL;DR [Arc Claude Watch Parity]:** Gate 1 adapter is on `main`; synthetic CLI
smoke passes, but configured output containment needs a corrective and audit.
Real-transcript acceptance remains `NOT_RUN`; Ryan owns exact-source grants.
Gate 2 Execute, its live
canary, and production watch capture remain separate Ryan gates.
