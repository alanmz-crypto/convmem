# Arc Brief — Claude Watch Parity

> **Arc: Claude Watch Parity.** Claude transcripts are searchable on demand;
> automatic incremental capture remains closed.

## 1. What This Is For

Claude Code sessions should be searchable without repeatedly transforming the
entire growing transcript. Gate 1 provides explicit on-demand indexing. Gate 2
must prove isolated incremental reuse and containment before Ryan considers any
automatic watch route.

## 2. System Design

```text
Claude JSONL -> Gate 1 adapter -> complete-prefix parser
      -> exact-source capture -> descriptor-bound bwrap namespace
      -> unchanged incremental coordinator in /canary-root
      -> content-free evidence -> Security Review -> Kiro -> Ryan
```

Source bytes are input authority. Checkpoints are replay authority. Chroma and
exports are derived. Default routing stays Kiro-only.

## 3. What Exists Right Now

| Surface | State |
|---|---|
| Gate 1 adapter and containment harness | On `main` through PRs #310 and #311 |
| Gate 2 prefix/spec/isolated route | Branch-only; not production-routed |
| Local safety corrective | Pushed at `e007a22b24754a93d9cbd15d02269d422d371c4a`; findings #1 and #3–#6 addressed; 43 focused tests reported passing |
| Shared-boundary finding #2 | Architecture resolved without shared-runtime edits; namespace implementation pending |
| Namespace architecture | Kiro PASS carried forward to exact normative plan `2f09469`; C1–C4 incorporated |
| Live-source canary | `NOT_RUN`; no exact source grant |
| Production watch/source routing | Absent and unauthorized |

## 4. Completion State

| Milestone | State | Next gate |
|---|---|---|
| Gate 1 | **MERGED** | remains on-demand |
| Gate 2 original implementation | **SECURITY FAIL** at `10322a6` | superseded by corrective work |
| Five local findings | **CORRECTED / UNREVIEWED** at `e007a22b24754a93d9cbd15d02269d422d371c4a` | integrate with reviewed boundary solution |
| Finding #2 architecture | **KIRO PASS** carried forward to `2f09469`; C1–C4 normative | complete |
| Namespace implementation | **AUTHORIZED / NOT_STARTED** from `e007a22` | Cursor implements and stops for Security Review |
| Exact-tip security audit | **NOT_RUN** | OpenAI Security Review after Cursor returns one pushed exact tip |
| Live canary / promotion | **NOT AUTHORIZED** | separate later decisions |

## 5. Your Role

**Cursor:** implement the bounded namespace from exact base `e007a22` under
normative plan `2f09469` and C1–C4. Use a clean external worktree, touch only
the authorized canary/test/evidence surfaces, push with an explicit refspec, and
stop for OpenAI Security Review. No PR or live source.

**Ryan:** no action until Cursor returns a pushed exact tip, unless Cursor hits a
stop condition and returns `NO_GATE2_ROUTE`.

## 6. What Remains Before Live

1. Cursor implements from verified `e007a22` under C1–C4 without shared-code
   changes and pushes the exact tip.
2. OpenAI Security Review audits the exact implementation tip named by Cursor;
   Copilot remains unavailable.
3. Kiro reviews the same passing tip.
4. Ryan separately decides PR, exact-source canary, production route, and watch
   wiring. None is implied by earlier gates.

## 7. Hard Stops

| Stop | Owner | Blocks |
|---|---|---|
| Namespace Execute | **CLEARED for bounded handoff only** | shared-code or scope widening remains blocked |
| Exact review target | Cursor | Security Review cannot start until one pushed successor SHA exists |
| Exact source | Ryan | reading a real Claude transcript |
| PR stewardship | Ryan | opening a PR |
| Promotion and watch wiring | Ryan | any production route/config/service change |

## 8. Relationship to ConvMem

The arc reuses the shared incremental coordinator but does not modify it. The
namespace gives that existing runtime a fixed scratch filesystem view. Arc
Codex production gates, issue #314, issue #315, and production watcher/OOM work
remain separate.

## 9. Key Design Files

- `docs/plans/ARCHITECTURE-claude-watch-parity.md`
- `docs/plans/EXECUTION-claude-watch-parity-boundary.md`
- `docs/inter-model/VERIFY-claude-watch-parity-gate2.md` on the local-safety branch
- `docs/inter-model/CODEX-2026-09-18-claude-watch-parity-gate2-execute.md` on the original planning branch

## 10. Update Log

| Date | Who | Milestone-level change |
|---|---|---|
| 2026-09-20 | Codex | Ryan granted bounded namespace Execute from `e007a22` under Kiro-PASSed plan `2f09469`; Cursor next. |

**TL;DR [Arc Claude Watch Parity]:** Gate 1 is merged; Gate 2 architecture has
Kiro PASS and bounded namespace Execute is authorized from `e007a22` under
C1–C4. Cursor implements next; live and production gates remain closed.
