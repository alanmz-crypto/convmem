# Arc Brief — Claude Watch Parity

> **Arc: Claude Watch Parity. State: CLOSED (`NO_GATE2_ROUTE`).** Claude
> transcripts remain searchable through explicit Gate 1 on-demand indexing;
> automatic incremental capture did not advance.

## 1. What This Was For

Claude Code sessions needed a supported path into ConvMem. Gate 1 delivered
explicit `convmem index --file` support. Gate 2 investigated automatic
incremental capture, but its sandbox launcher accumulated more safety and
maintenance cost than the additional automation justified.

Ryan closed Gate 2 as `NO_GATE2_ROUTE` on 2026-09-20. This is a value and
maintenance decision, not proof that descriptor-bound namespaces are
impossible.

## 2. Final System Design

```text
Claude JSONL
    -> Gate 1 adapter on main
    -> explicit convmem index --file
    -> normal ConvMem corpus

Automatic watch / Gate 2 route
    -> CLOSED (NO_GATE2_ROUTE)
```

The session-close Track A ritual remains the supported way to capture Claude
sessions. No Claude watcher, production route, live canary, or activation was
created by this arc.

## 3. What Exists Right Now

| Surface | Final state |
|---|---|
| Claude Gate 1 adapter and containment harness | Merged through PRs #310 and #311; supported on-demand path |
| Gate 2 prefix/spec/isolated route | Preserved only in tagged experimental history; never production-routed |
| Namespace launcher | Preserved at `milestone/claude-watch-parity-final-experiment`; not accepted |
| Live-source canary | Never executed |
| Production watcher/source/service configuration | Unchanged |

### Review progression

- `10322a6` — first Security Review **FAIL**, six findings.
- `e007a22` — local-safety implementation input; never an accepted or reviewed
  checkpoint.
- `52bdc02` — second Security Review **FAIL**, ten findings.
- `95ef122` — third Security Review **FAIL**, three findings; preserved by the
  final-experiment tag and contains `52bdc02` in its ancestry.

The reviews increasingly confirmed basic namespace mount protections while
continuing to find High launcher defects. Gate 1 already met the product need,
each replacement review required a separate exception while Copilot was
unavailable, and the homegrown sandbox policy imposed disproportionate
maintenance cost.

## 4. Completion State

| Milestone | Final outcome |
|---|---|
| Gate 1 on-demand indexing | **DONE — MERGED AND SUPPORTED** |
| Gate 2 design investigation | **DONE — PRESERVED FOR REFERENCE** |
| Gate 2 implementation experiment | **DONE — REJECTED AFTER SECURITY REVIEW** |
| Gate 2 disposition | **CLOSED — `NO_GATE2_ROUTE`** |
| Kiro review lane | **CLOSED — STOOD DOWN** |
| Live and production operations | **CLOSED WITHOUT EXECUTION** |

## 5. Your Role

This arc has no active implementation or review lane. Do not resume Gate 2 from
its experimental branches. A future automatic-capture proposal requires a new
arc, architecture, threat model, and Ryan grant.

For supported Gate 1 follow-ups, use the separately scoped issues:

- [#316](https://github.com/alanmz-crypto/convmem/issues/316) — invalid UTF-8
  handling in metadata discovery and ordinary parsing.
- [#317](https://github.com/alanmz-crypto/convmem/issues/317) — read-only audit
  of merged Gate 1 containment and evidence boundaries.

Neither issue authorizes implementation or live transcript access.

## 6. What Remains

Nothing remains inside Claude Watch Parity. Issues #316 and #317 are separate
Gate 1 maintenance work and do not reopen this arc.

## 7. Hard Stops

- Do not merge, cherry-pick, or activate the tagged Gate 2 launcher or route.
- Do not treat a tagged experimental tip as accepted security evidence.
- Do not add Claude watcher/source/service configuration under this arc.
- Do not access a real Claude transcript without a separately named resource
  and operation grant.
- Do not infer authority for #316 or #317 from this closeout.

## 8. Relationship to ConvMem

Gate 1 is a normal on-demand adapter path and remains part of ConvMem. Gate 2
was an isolated automation experiment. Its closure does not change Kiro or
Codex incremental production routes, Arc Codex gates, issue #268, issue #314,
or issue #315.

## 9. Preserved Design and Evidence

The abandoned plans remain available without adding them to `main`:

```bash
git show milestone/claude-watch-parity-execute-handoff:docs/plans/ARCHITECTURE-claude-watch-parity.md
git show milestone/claude-watch-parity-execute-handoff:docs/plans/EXECUTION-claude-watch-parity-boundary.md
git show milestone/claude-watch-parity-execute-handoff:docs/plans/STATUS-claude-watch-parity.md
git show milestone/claude-watch-parity-execute-handoff:docs/inter-model/CODEX-2026-09-20-claude-watch-parity-boundary-review-handoff.md
```

| Preservation tag | Exact commit | Meaning |
|---|---|---|
| `milestone/claude-watch-parity-reviewed-plan` | `2f09469` | Kiro-reviewed normative plan |
| `milestone/claude-watch-parity-execute-handoff` | `dc5427e` | Final planning and Execute handoff state |
| `milestone/claude-watch-parity-local-safety` | `e007a22` | Unreviewed local-safety input |
| `milestone/claude-watch-parity-first-security-fail` | `10322a6` | First Security Review failure |
| `milestone/claude-watch-parity-final-experiment` | `95ef122` | Final experiment; includes second FAIL `52bdc02` |
| `milestone/claude-watch-parity-pre-boundary` | `a5ccc68` | Older corrective lineage |

## 10. Update Log

| Date | Who | Milestone-level change |
|---|---|---|
| 2026-09-20 | Ryan / Codex | Closed Gate 2 as `NO_GATE2_ROUTE`; retained Gate 1 on-demand indexing and preserved experimental history by tag. |

**TL;DR [Arc Claude Watch Parity]:** Gate 1 on-demand Claude indexing is the
supported result. Gate 2 automatic capture is closed as `NO_GATE2_ROUTE`, Kiro
is stood down, and the rejected experiment remains available through immutable
tags only.
