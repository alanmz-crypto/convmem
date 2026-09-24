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
| Architecture direction | **BOUNDED BUILD/TEST PASS** for synthetic T0–T5; the current plan correction freezes the M11-only reviewed-plan control-plane rule without changing T0–T5 semantics |
| Bounded implementation | **ACCEPTED** at `8010fb060c2edc29e1b09d7a30b1a1da2689d489` over original baseline `7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`; two M8 runs and exact-tip Kiro conformance passed |
| Current-main baseline | `9193f5ec744f059d07a20612489b210527b5660a`; accepted implementation and current main have no product-path overlap, but acceptance does not transfer without reconstruction and fresh evidence |
| M11 reconstruction | Exact 45-commit replay plus pin/comment reconciliation are **PRESERVED, CLEAN AND PUSHED** at `a11b7a2a793c68e4e6e83c2680b077389a817c5c` on `feat/2026-09-23-openclaw-convmem-m11-integration` |
| M11 allowlist correction | **PLAN-ONLY / PAUSED.** The first M8 attempt stopped before imports or tests because the four reviewed plan/STATUS blobs were treated as product edits. Ryan authorized only the two-commit plan reconciliation from overlay `581de2abf430786a36f2612f97c623a19b61353f`; Kiro exact-tip review and a new Ryan resume grant are next |
| Runtime/evidence | Historical and rebound runtime/evidence are retained. They are not authorized inputs for another run until the new reviewed parent/overlay and parent-bound paths are named in a Ryan resume grant |
| Installed OpenClaw capability | Last probed at `2026.3.2`, while a newer release was identified. M11 does not run or change OpenClaw; before any Gate D test, the installed distribution must be deliberately updated or pinned and freshly capability-probed/reviewed |
| Related arc | [`STATUS-openclaw-watch-coverage.md`](STATUS-openclaw-watch-coverage.md) — separate arc, covers ConvMem watching OpenClaw's *committed repo files*, not this runtime connector |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Architecture direction and bounded fixture contract | **DONE — BUILD PASS** | Current-main reconstruction does not reopen semantics |
| M0–M8 implementation and Gate B/C evidence | **DONE — TEST PASS / ACCEPTED** at `8010fb0` | Applies only to the exact historical baseline/revisions/runtime/evidence |
| M11 replay and pin reconciliation | **DONE / PRESERVED at `a11b7a2`** | no acceptance transfer; branch remains unmerged |
| M11 reviewed-plan allowlist correction | **PLAN-ONLY / PAUSED** | exact-tip Kiro review, then a new Ryan resume grant naming the new parent/overlay and preserved branch tip |
| M11 fresh evidence and regressions | **NOT STARTED** | requires the reviewed correction on the preserved branch, Codex control-plane/source-inventory proof, and explicit Ryan retry authority |
| Merge readiness | **NOT YET PROVEN** | requires exact control-plane blob proof, unchanged product allowlists, rebound runtime, two fresh M8 passes, seven MCP regressions, Pylint and Kiro integrated-tip PASS |
| Phase 1A/1B real OpenClaw operation | **BLOCKED** | Gate D runtime qualification and later production gates |
| Child-agent inheritance question | **UNANSWERED** | requires observing a real OpenClaw dispatch run after Phase 1B lands |
| Transcript capture | **BLOCKED** | independent poison-transcript/Chroma upsert crash-loop fix; explicitly out of scope for this phase |

## 5. Your Role

**If Ryan sent you here:** review the exact two-commit M11 allowlist plan
reconciliation. Confirm that the four reviewed documents are separately
blob-validated yet remain inside the full source export/inventory/hash, and that
the product allowlists and T0–T5 semantics do not change. Do not edit product or
test code, retry M8, provision/rebind a runtime, merge, update/run OpenClaw, or
touch live data. Kiro must first PASS the final overlay; only a later Ryan grant
may authorize applying the plans and bounded correction to preserved tip
`a11b7a2`. Real OpenClaw operation remains separately blocked by Gate D/W and
later gates.

## 6. What Remains Before This Arc Is Live

1. Kiro performs exact-tip binary design/scope review of the new semantic parent,
   milestone overlay and current-state STATUS.
2. If Kiro passes, Ryan decides whether to grant resumption on preserved tip
   `a11b7a2`, naming the exact parent/overlay, integration baseline/branch,
   rebound runtime prefix and durable evidence root.
3. Under that grant, Grok applies the exact two reviewed plan commits to the
   preserved branch and stops; Codex proves all four blobs equal the reviewed
   overlay and all non-plan bytes still equal `a11b7a2`.
4. After a commit-specific `CONTINUE`, Grok makes only the frozen twelve-path
   correction and stops. Codex proves exact control-plane validation, unchanged
   product allowlists and full source-export/inventory/hash inclusion.
5. Only under explicit retry authority, Codex rebinds/verifies the frozen
   runtime, runs M8 twice plus seven MCP regressions and Pylint, preserves durable
   evidence, and obtains Kiro exact-tip conformance review. Ryan alone decides
   merge.
6. Gate D/W, then Gate D-V and Gate E, remain separate later decisions. Before
   Gate D, deliberately update or pin OpenClaw and perform a fresh capability
   probe/review; no earlier version observation is qualification.
7. A real OpenClaw run is observed to settle whether dispatched child agents
   inherit ConvMem access by default; that observation becomes its own
   Kiro-reviewed design decision, not an assumption.
8. Transcript capture stays out of scope until the independent
   poison-transcript/Chroma crash-loop data-integrity issue is separately
   resolved and verified.

## 7. Hard Stops

- No implementation from the architecture or review alone — the execution plan,
  exact-tip Kiro PASS, and exact applicable Ryan grant are all required.
- No durable ConvMem write/approve capability exposed to OpenClaw.
- No unscoped retrieval; a bound project/site/domain scope is a hard ceiling.
- No `ask()` exposure to OpenClaw until synthesized-result handling is
  independently verified.
- No transcript capture before the independent data-integrity gate clears.
- No OpenClaw plugin-tools/native-memory bridge into ACP workers without
  separate review.
- No OpenClaw upgrade without separate authorization.
- No product/test correction or M8 retry until Kiro passes the exact plan tip
  and Ryan issues a new resume grant.
- Never add the four reviewed documents to a product allowlist or remove them
  from source export, source inventory or `source_tree_sha256`.

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
| Execution | `docs/plans/EXECUTION-openclaw-convmem-integration.md` and the T0–T5 milestone overlay |
| Arc status | `docs/plans/STATUS-openclaw-convmem-integration.md` (this file) |
| Human-language orientation | `docs/plans/README-openclaw-convmem-integration.md` |
| Sibling arc | `docs/plans/STATUS-openclaw-watch-coverage.md` |

## 10. Update Protocol

Keep this file a current-state snapshot. Overwrite sections 3–6 after Kiro
review, Ryan approval, execution planning, or implementation. Do not append
session narrative. Add one line below per milestone-level change.

| Date | Who | Change |
|---|---|---|
| 2026-09-24 | Codex | M11 replay/pinning is preserved at `a11b7a2`; first M8 attempt paused pre-import on the four reviewed control documents; a plan-only exact-blob/unchanged-product-allowlist correction now awaits Kiro and a new Ryan resume grant. |
| 2026-09-23 | Codex | Bounded M0–M8 is accepted at `8010fb0`; M11 is paused before current-main reconstruction while the plan-only `9193f5e` reconciliation awaits exact-tip Kiro review and a new Ryan integration decision. |
| 2026-09-23 | Codex | Exact-tip Kiro PASS at `d1ca459`; bounded execution overlay and PR #327 are ready for Ryan's two-SHA Execute decision. Separate implementation branch is partial through M3/T1–T2; no TEST PASS or live authorization. |
