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
| Shared-boundary finding #2 | Open; coordinator pathname authority remains on the branch |
| Namespace architecture | This docs-only branch; Kiro review pending |
| Live-source canary | `NOT_RUN`; no exact source grant |
| Production watch/source routing | Absent and unauthorized |

## 4. Completion State

| Milestone | State | Next gate |
|---|---|---|
| Gate 1 | **MERGED** | remains on-demand |
| Gate 2 original implementation | **SECURITY FAIL** at `10322a6` | superseded by corrective work |
| Five local findings | **CORRECTED / UNREVIEWED** at `e007a22b24754a93d9cbd15d02269d422d371c4a` | integrate with reviewed boundary solution |
| Finding #2 architecture | **READY_FOR_KIRO_REVIEW** after conditional-FAIL corrections | Kiro PASS or correction |
| Namespace implementation | **NOT AUTHORIZED** | Ryan Execute grant after plan PASS |
| Exact-tip security audit | **NOT_RUN** | fresh Ryan exception after implementation |
| Live canary / promotion | **NOT AUTHORIZED** | separate later decisions |

## 5. Your Role

**Kiro:** review the corrected namespace decision, unbound snapshot vault,
per-run digest revalidation, durable quarantine, Claude-compatible fixed mount,
watch-root disjointness, host-owned capture,
explicit merged/runtime baselines, CI skip semantics, and `NO_GATE2_ROUTE`
exit. Confirm that coordinator, isolation, and Chroma runtime files remain
outside the implementation slice while the expected Claude format-registry
addition stays visible.

**Ryan:** after Kiro's verdict, either grant the bounded namespace Execute or
close Gate 2 at Gate 1 on-demand support.

**Cursor:** no further implementation until that grant.

## 6. What Remains Before Live

1. Kiro reviews the exact planning tip.
2. Ryan accepts the namespace dependency or selects `NO_GATE2_ROUTE`.
3. If granted, Cursor implements from verified
   `e007a22b24754a93d9cbd15d02269d422d371c4a` without shared-code
   changes.
4. OpenAI Security Review audits the exact implementation tip under a fresh
   exception while Copilot is unavailable.
5. Kiro reviews the same passing tip.
6. Ryan separately decides PR, exact-source canary, production route, and watch
   wiring. None is implied by earlier gates.

## 7. Hard Stops

| Stop | Owner | Blocks |
|---|---|---|
| Namespace Execute | Ryan | any new Gate 2 code |
| Security-review substitution | Ryan | OpenAI review of a successor SHA |
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
| 2026-09-20 | Codex | Moved snapshots to an unbound vault and added tamper-proof digest revalidation, durable quarantine, and application-specific host identity; Kiro review next. |

**TL;DR [Arc Claude Watch Parity]:** Gate 1 is merged; five local Gate 2
correctives are pushed but unreviewed. Finding #2 now has a namespace design
ready for Kiro; Gate 2 remains closed.
