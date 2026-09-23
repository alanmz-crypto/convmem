# Arc Brief — ConvMem Switchboard (OpenClaw + ConvMem integration)

> **Every model working on this arc must read this file at session start.**

## 1. What This Is For

OpenClaw is the user-facing orchestrator; ConvMem is the shared, read-only
evidence and memory layer. This arc designs and lands the connector that lets
OpenClaw — and the agents it dispatches — query ConvMem's memory at runtime,
without letting unscoped retrieval, prompt-injection escalation,
external-channel compromise, or unsafe transcript capture weaken ConvMem's
authority or integrity.

**Done means:** a version-adapted, read-only OpenClaw-to-ConvMem connector is
live, with server-enforced project/site/domain scope as a hard ceiling,
`related()` performing post-traversal authorization, `ask()` gated until
synthesized-result handling is proven safe, and no durable write/approve
capability exposed to OpenClaw. The still-open question of whether OpenClaw's
*dispatched child agents* automatically inherit ConvMem access is answered by
observing a real OpenClaw run, not assumed from design alone.

## 2. System Design

```text
OpenClaw (orchestrator)
  │
  ├─ dispatches child agents to do tasks
  │     └─ open question: do these children get an MCP connection to
  │         ConvMem, or start with no memory access? (unanswered — needs
  │         an observed real run, see §6)
  │
  └─ read-only, scoped MCP connector to ConvMem
        Option A (chosen): strict profile, project/site/domain scope bound
        by the server instance; tool args may only narrow, never widen;
        resources absent by default; related() denies all-or-nothing when
        any node is out of scope.

ConvMem (shared memory, unchanged authority)
  ├─ ledger owns durable facts; Chroma is a rebuildable serving projection
  └─ durable writes remain Ryan-approved CLI operations only
```

Key invariants (from `ARCHITECTURE-openclaw-convmem-integration.md`):
OpenClaw is coordinator, never durable-memory authority; a bound scope is a
hard ceiling callers can only narrow; an omitted selector inherits the bound
scope rather than becoming unscoped or erroring; `cross_domain=true` is
rejected under a bound scope; `related()` authorizes after traversal, before
rendering, and denies all-or-nothing; transcript capture is a separate,
blocking data-integrity phase gated behind the poison-transcript/Chroma
crash-loop fix, not ordinary wiring.

## 3. What Exists Right Now

| Surface | State |
|---|---|
| Architecture direction | Drafted 2026-09-20 by Codex; chooses Option A (version-adapted read-only connector) over a broker or OpenClaw-native-memory-primary design |
| Kiro review | **Not started** |
| Ryan approval | **Not given** |
| Execution plan | **Does not exist yet** — architecture-only; no `EXECUTION-openclaw-convmem-integration.md` |
| Implementation | **None** — no code, no live connector, no OpenClaw MCP wiring |
| Installed OpenClaw capability | Probed at `2026.3.2`: no `openclaw mcp` command exposed yet, no `~/.openclaw/openclaw.json`; capability discovery must precede any configuration |
| Related arc | [`STATUS-openclaw-watch-coverage.md`](STATUS-openclaw-watch-coverage.md) — separate arc, covers ConvMem watching OpenClaw's *committed repo files*, not this runtime connector |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Architecture direction drafted | DONE | — |
| Kiro design/adversarial review | **NOT STARTED** | needs to be scheduled against the exact committed revision |
| Ryan approval of direction | **NOT GIVEN** | Kiro review first |
| Execution plan (Cursor) | **NOT STARTED** | Ryan approval first — architecture explicitly says "do not implement from this architecture document alone" |
| Phase 0 (perimeter + capability lock) | NOT STARTED | execution plan |
| Phase 1A (isolated read-only smoke) | NOT STARTED | Phase 0 |
| Phase 1B (scoped normal operation) | NOT STARTED | full tool/resource/scope/related/perimeter review |
| Child-agent inheritance question | **UNANSWERED** | requires observing a real OpenClaw dispatch run after Phase 1B lands |
| Transcript capture | **BLOCKED** | independent poison-transcript/Chroma upsert crash-loop fix; explicitly out of scope for this phase |

## 5. Your Role

**If Ryan sent you here:** this arc is still pre-review. Do not implement
against the architecture document alone — per its own downstream handoff,
Cursor only shapes an execution plan *after* HITL (Kiro + Ryan) approval.
If you are Kiro: perform the read-only PASS/FAIL adversarial review listed in
`ARCHITECTURE-openclaw-convmem-integration.md` §"Adversarial review matrix"
against the exact committed revision. If you are anyone else: the next
unblocking action is getting that review scheduled, not writing code.

## 6. What Remains Before This Arc Is Live

1. Kiro performs the adversarial PASS/FAIL review against the committed
   architecture revision (14 test cases listed in the architecture doc).
2. Ryan approves or rejects the architecture direction.
3. Cursor authors an execution plan and implementation slices from the
   approved direction (not before).
4. Phase 0 → 1A → 1B land in order, each gated on the prior phase's evidence.
5. A real OpenClaw run is observed to settle whether dispatched child agents
   inherit ConvMem access by default; that observation becomes its own
   Kiro-reviewed design decision, not an assumption.
6. Transcript capture stays out of scope until the independent
   poison-transcript/Chroma crash-loop data-integrity issue is separately
   resolved and verified.

## 7. Hard Stops

- No implementation from the architecture document alone — execution plan
  required first, and only after Kiro PASS + Ryan approval.
- No durable ConvMem write/approve capability exposed to OpenClaw.
- No unscoped retrieval; a bound project/site/domain scope is a hard ceiling.
- No `ask()` exposure to OpenClaw until synthesized-result handling is
  independently verified.
- No transcript capture before the independent data-integrity gate clears.
- No OpenClaw plugin-tools/native-memory bridge into ACP workers without
  separate review.
- No OpenClaw upgrade without separate authorization.

## 8. Relationship to ConvMem and OpenClaw

This arc supplies the runtime *query* path (OpenClaw → ConvMem, read-only).
[`STATUS-openclaw-watch-coverage.md`](STATUS-openclaw-watch-coverage.md)
supplies the maintenance-knowledge plane (ConvMem watching OpenClaw's own
committed repo files). The two are independent — this arc can be designed
and reviewed without watch coverage, but the child-agent observation step in
§6 is more useful once watch coverage is live, since it gives a concrete
example (e.g. a Gmail CLI recipe) to check whether a dispatched agent
actually reaches for it.

## 9. Key Files

| Purpose | Path |
|---|---|
| Architecture | `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md` |
| Execution | *(does not exist yet — created after Ryan approval)* |
| Arc status | `docs/plans/STATUS-openclaw-convmem-integration.md` (this file) |
| Human-language orientation | `docs/plans/README-openclaw-convmem-integration.md` |
| Sibling arc | `docs/plans/STATUS-openclaw-watch-coverage.md` |

## 10. Update Protocol

Keep this file a current-state snapshot. Overwrite sections 3–6 after Kiro
review, Ryan approval, execution planning, or implementation. Do not append
session narrative. Add one line below per milestone-level change.

| Date | Who | Change |
|---|---|---|
| 2026-09-23 | Claude | Created this STATUS file; named the arc "ConvMem Switchboard" (matching the now-locked-in product name) at Ryan's direction. Architecture is still pre-Kiro-review; no execution plan or implementation exists. |
