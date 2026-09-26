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
| Architecture direction | **BOUNDED BUILD/TEST PASS** for synthetic T0–T5; Architecture §18.17 and Execution §10.15 now freeze a plan-only, closed 22-node inner-role semantic-signature reconciliation without changing T0–T5 semantics |
| Bounded implementation | **ACCEPTED** at `8010fb060c2edc29e1b09d7a30b1a1da2689d489` over original baseline `7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`; two M8 runs and exact-tip Kiro conformance passed |
| Current-main baseline | Historical M11 evidence is bound to `9193f5ec744f059d07a20612489b210527b5660a`; prior current main was `a92a74e`; exact fetched current main is now `5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d` and must remain fixed through PR/merge consideration |
| M11 reviewed candidate | **BOUNDED MERGE-READINESS EVIDENCE PASS / PRESERVED, CLEAN AND PUSHED** at `cd60cf19dca6706e4175e9f82c9ba55e41bca10b`; Kiro exact-tip PASS, but no PR or merge followed |
| Merge applicability | **PAUSED.** The advanced-main candidate is preserved at `776a4ca3`; complete pytest and all symmetric reruns ran, but the finalizer rejected 22 unchanged inner-role failures whose pytest-rendered environment tails varied. No verdict transfers |
| First current-main reconciliation | **PRESERVED.** The first reconstruction is at `30bc134d`; its applicability correction and four-literal rebind are clean/pushed at `d276cb4`. The authorized evidence preflight then paused before slot/run creation because main moved |
| Advanced-main reconciliation | **DONE / PRESERVED at `776a4ca3`.** The exact 120-path product, four reviewed control blobs and six identity substitutions were applied as three held commits from `5c6a4a8`; source composition and runtime inventory passed |
| Differential applicability | **PAUSED / PLAN CORRECTION ONLY.** Fresh same-slot `5c6a4a8`/`cd60cf19`/`776a4ca3` execution and 166 reruns completed. Exactly 22 packet-contract failures retained one assertion but varied only in pytest's rendered `os.environ` tail; §18.17 closes the admissible semantic projection |
| Runtime/evidence | Runtime tree SHA-256 `74a12c…` remained unchanged. The sealed PAUSE ledger SHA-256 is `a6a2d95b…`; the exact 22-node sorted-NUL identity-set SHA-256 is `9fa64e04…`. Fresh parent/`5c6a4a8`-bound paths and evidence require Kiro PASS and a new Ryan grant |
| Installed OpenClaw capability | Last probed at `2026.3.2`, while a newer release was identified. M11 does not run or change OpenClaw; before any Gate D test, the installed distribution must be deliberately updated or pinned and freshly capability-probed/reviewed |
| Related arc | [`STATUS-openclaw-watch-coverage.md`](STATUS-openclaw-watch-coverage.md) — separate arc, covers ConvMem watching OpenClaw's *committed repo files*, not this runtime connector |

## 4. Completion State

| Milestone | Status | Blocking on |
|---|---|---|
| Architecture direction and bounded fixture contract | **DONE — BUILD PASS** | Current-main reconstruction does not reopen semantics |
| M0–M8 implementation and Gate B/C evidence | **DONE — TEST PASS / ACCEPTED** at `8010fb0` | Applies only to the exact historical baseline/revisions/runtime/evidence |
| M11 replay and pin reconciliation | **DONE / PRESERVED at `a11b7a2`** | no acceptance transfer; branch remains unmerged |
| M11 reviewed-plan allowlist correction | **DONE / PRESERVED at `9c6421a`** | exact-blob/product-allowlist/source-inventory checks passed |
| M11 fresh M8 and MCP evidence | **PASS at `9c6421a`** | two M8 runs and seven legacy MCP regressions pass; exact-tip acceptance withheld because Pylint failed |
| M11 Pylint remediation | **IMPLEMENTED / PYLINT PASS at `3f8ef83`** | correction remains unmerged; exact source is preserved and pushed |
| M11 full-pytest differential | **PASS at `851edbe4`** | `PYTEST_DIFFERENTIAL_PASS=true`; 238 retained failures/errors remain explicit debt and `FULL_PYTEST_PASS=false` |
| M11 final M8 authority reconciliation | **DONE / PRESERVED at `d7b1592`** | earlier exact two-file/four-literal rebind applied; fresh differential and unchanged Pylint gate passed |
| M11 bundle-schema reconciliation | **DONE / PRESERVED at `851edbe4`** | exact one-file/one-literal publisher correction applied; fresh differential and unchanged Pylint gate pass |
| M11 post-bundle authority-packet reconciliation | **DONE / EVIDENCE PASS at `cd60cf1`** | exact four-literal correction, differential, Pylint, two M8 runs, seven MCP regressions, durable verification and Kiro PASS completed |
| M11 first current-main reconstruction | **DONE / PRESERVED at `30bc134d`** | exact source composition passed; no PR or merge is authorized |
| M11 first current-main differential | **PAUSED / HISTORICAL** | complete `a92a74e`/`30bc134d` runs exposed the inapplicable candidate-only rule; sealed ledger SHA-256 `3bd89ebf…` |
| M11 three-tip correction | **DONE / PRESERVED at `d276cb4`** | plan/rebind verified and runtime qualified; preflight stopped before testing when main advanced |
| M11 advanced-main reconstruction | **DONE / PRESERVED at `776a4ca3`** | three held reconstruction commits, source composition and runtime inventory passed |
| M11 advanced-main differential | **PAUSED AFTER COMPLETE RUNS/RERUNS** | 22 exact packet-contract nodes require the reviewed §18.17 semantic-signature rule; `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS=false`, and Pylint/M8/MCP did not run |
| Merge readiness | **PAUSED FOR REVIEWED EVIDENCE** | requires exact-tip Kiro PASS, new Ryan grant, reviewed plan application and four-literal rebind, fresh three-tip differential, unchanged Pylint, two M8 runs, seven MCP regressions, durable verification, Kiro integrated-tip PASS and unchanged `origin/main` |
| Phase 1A/1B real OpenClaw operation | **BLOCKED** | Gate D runtime qualification and later production gates |
| Child-agent inheritance question | **UNANSWERED** | requires observing a real OpenClaw dispatch run after Phase 1B lands |
| Transcript capture | **BLOCKED** | independent poison-transcript/Chroma upsert crash-loop fix; explicitly out of scope for this phase |

## 5. Your Role

**If Ryan sent you here:** review only the plan-only inner-role signature
reconciliation. Confirm `N1=5c6a4a8`, preserved reviewed candidate
`R=cd60cf1`, preserved evidence PAUSE input `H1=776a4ca3`, the sealed PAUSE
hashes and exact 22-node set/hash. Confirm §18.17 accepts only the four-line
inner-role assertion grammar, preserves raw records, adds no generic
normalization, keeps the five-node R2b rule independent, and requires fresh
same-slot evidence plus unchanged Pylint/M8/MCP gates. Do not apply plans, edit
identity literals, run a suite, create a PR, merge, update/run OpenClaw or touch
live data.

## 6. What Remains Before This Arc Is Live

1. Kiro performs exact-tip binary design/scope review of the revised semantic
   parent, milestone overlay and this STATUS.
2. If Kiro passes, Ryan decides whether to grant the exact reviewed plan range
   onto preserved `776a4ca3`, four frozen parent/overlay identity substitutions,
   fixed slot and new parent/current-main-bound runtime and evidence roots.
3. Under that grant, Grok applies only the reviewed plan range, pushes and
   stops; after Codex verification and a commit-specific `CONTINUE`, Grok makes
   only the exact two-file/four-literal rebind, then pushes and stops again.
4. Codex proves final tree composition, then runs fresh complete pytest at
   `N1`, `R` and the final candidate in one reset slot. The exact 22-node closed
   signature proof supplements, but does not replace, the 238-node partition,
   five-node R2b proof and all other differential gates. Only a three-tip PASS
   releases the unchanged Pylint gate, two fresh M8 runs and seven MCP
   regressions. Kiro reviews the exact resulting tip and durable evidence.
5. `origin/main` must still equal `5c6a4a8` before PR creation and merge
   consideration. Ryan alone decides PR and merge; any main movement restarts
   reconciliation rather than permitting an inferred rebase.
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
- No plan application, four-literal rebind or suite until Kiro passes the exact
  inner-role signature plan and Ryan issues a new resume grant.
- No rebase, merge, force-push or conflict resolution of the reviewed
  `cd60cf1` or `d276cb4` branch; preserve both as inputs.
- No PR or merge if `origin/main` differs from `5c6a4a8`.
- Never add the four reviewed documents to a product allowlist or remove them
  from source export, source inventory or `source_tree_sha256`.
- Never raise or regenerate the Pylint baseline, change the workflow/gate,
  exclude Switchboard paths, or replace the actual current-main gate with a
  preserved-tip comparison.
- No lint-remediation edit outside the exact 44 paths in Architecture §18.9;
  no broad suppression or shared helper that weakens independent oracles.
- Never describe identical retained repository failures as a full-pytest PASS;
  never compare through different path strings, retain state between reset-slot
  uses, widen signature/hash normalization, extend the five-node R2b set, skip
  an asymmetric rerun or use the differential verdict to waive Pylint/M8/MCP.
- Never require a current-main baseline to define outcomes for Switchboard nodes
  it does not contain; never use that correction to exclude those nodes, waive
  their failures or let the preserved candidate govern a current-main node.
- Never apply the inner-role projection outside the exact 22-node set; never
  accept a different core assertion, line count, outcome/type or tail grammar;
  never delete or rewrite raw messages; never add environment/order/temp/hash
  normalization or a sixth R2b exception.

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
| 2026-09-26 | Codex | Advanced-main reconstruction is preserved at `776a4ca3`; three complete pytest runs and 166 reruns paused on unstable pytest environment rendering for an exact 22-node inner-role failure family, so a closed semantic-signature plan now awaits Kiro and a new Ryan grant. |
| 2026-09-26 | Codex | Three-tip candidate `d276cb4` passed held source/runtime checks, but its evidence preflight stopped before execution when main advanced to `5c6a4a8`; a new deterministic reconstruction plan now awaits Kiro and a new Ryan grant. |
| 2026-09-26 | Codex | Exact-current-main reconstruction is preserved at `30bc134d`; complete pytest paused on 238 pre-existing Switchboard nodes absent from current main, so a closed three-tip applicability correction now awaits Kiro and a new Ryan grant. |
| 2026-09-26 | Codex | Bounded M11 evidence and Kiro review passed at `cd60cf1`; merge paused because current main advanced to `a92a74e` and conflicts in governed STATUS, so an exact plan-only reconstruction now awaits Kiro and a new Ryan grant. |
| 2026-09-25 | Codex | Bundle-schema correction, differential and Pylint pass at `851edbe4`; final M8 then refused pre-fixture on the stale parent/overlay packet, so an exact two-file/four-literal plan now awaits Kiro and a new Ryan grant. |
| 2026-09-25 | Codex | Fresh differential and Pylint evidence pass at `d7b1592`; final M8 run 1 exposed one invented publisher bundle-schema literal behind all 28 strict failures, so an exact one-file/one-literal plan now awaits Kiro and a new Ryan grant. |
| 2026-09-25 | Codex | Differential and Pylint evidence pass at `7f2a2e2`; final M8 paused before fixture creation on stale parent/overlay literals, so a plan-only exact two-file authority-packet reconciliation now awaits Kiro and a new Ryan grant. |
| 2026-09-24 | Codex | First governed differential paused at `853ef98` on 28 signature mismatches; the plan now requires identical reset paths and a closed five-node independently derived R2b identity disposition. |
| 2026-09-24 | Codex | Pylint now passes at preserved candidate `3f8ef83`; merge readiness is paused while a plan-only `9c6421a`-versus-candidate full-pytest differential awaits Kiro review and a new Ryan grant. |
| 2026-09-24 | Codex | Replaced the self-invalidating fixed plan-commit count with the complete reviewed linear range from `c5513d5` through Ryan's grant-named final overlay. |
| 2026-09-24 | Codex | M11 is preserved at `9c6421a` with M8/MCP PASS and Pylint PAUSE; the plan now freezes an exact 44-path remediation that keeps the current-main gate and baseline unchanged. |
| 2026-09-24 | Codex | M11 replay/pinning is preserved at `a11b7a2`; first M8 attempt paused pre-import on the four reviewed control documents; a plan-only exact-blob/unchanged-product-allowlist correction now awaits Kiro and a new Ryan resume grant. |
| 2026-09-23 | Codex | Bounded M0–M8 is accepted at `8010fb0`; M11 is paused before current-main reconstruction while the plan-only `9193f5e` reconciliation awaits exact-tip Kiro review and a new Ryan integration decision. |
| 2026-09-23 | Codex | Exact-tip Kiro PASS at `d1ca459`; bounded execution overlay and PR #327 are ready for Ryan's two-SHA Execute decision. Separate implementation branch is partial through M3/T1–T2; no TEST PASS or live authorization. |
