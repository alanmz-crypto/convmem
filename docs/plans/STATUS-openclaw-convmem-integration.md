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
| Architecture direction | **BOUNDED BUILD/TEST PASS** for synthetic T0–T5; Architecture §18.21 and Execution §10.19 now freeze a plan-only final-M8 legacy-count correction after the §18.20 differential and paired seeded-Pylint evidence passed without changing T0–T5 semantics |
| Bounded implementation | **ACCEPTED** at `8010fb060c2edc29e1b09d7a30b1a1da2689d489` over original baseline `7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`; two M8 runs and exact-tip Kiro conformance passed |
| Current-main baseline | Historical M11 evidence is bound to `9193f5ec744f059d07a20612489b210527b5660a`; prior current main was `a92a74e`; exact fetched current main is now `5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d` and must remain fixed through PR/merge consideration |
| M11 reviewed candidate | **BOUNDED MERGE-READINESS EVIDENCE PASS / PRESERVED, CLEAN AND PUSHED** at `cd60cf19dca6706e4175e9f82c9ba55e41bca10b`; Kiro exact-tip PASS, but no PR or merge followed |
| Merge applicability | **PAUSED.** Fresh three-tip and paired seeded-Pylint evidence passed at `9da6dd98`; final M8 run 1 completed all three suites but stopped on exact legacy-count drift because two passing current-main safety nodes raised the unchanged selected legacy suite from 116/115 to 118/117. Run 2/MCP did not run; no verdict transfers |
| First current-main reconciliation | **PRESERVED.** The first reconstruction is at `30bc134d`; its applicability correction and four-literal rebind are clean/pushed at `d276cb4`. The authorized evidence preflight then paused before slot/run creation because main moved |
| Advanced-main reconciliation | **DONE / PRESERVED at `776a4ca3`.** The exact 120-path product, four reviewed control blobs and six identity substitutions were applied as three held commits from `5c6a4a8`; source composition and runtime inventory passed |
| Differential applicability | **PASS / PRESERVED at `9da6dd98`.** Fresh same-slot `5c6a4a8`/`cd60cf19`/final execution, 166 reruns, the 238-node partition, five-node R2b proof and exact 22-node semantic projection passed; `FULL_PYTEST_PASS=false` remains explicit |
| Pylint applicability | **PASS / PRESERVED at `9da6dd98`.** Paired `N1`/final execution under sole addition `PYTHONHASHSEED=0` reproduced exact 458/29 `R0401`/69 `R0801`/240, 429 non-`R0401`, protected-gate zero and all three frozen semantic hashes |
| Runtime/evidence | Runtime tree SHA-256 `74a12c…` remained unchanged. The current final-M8 PAUSE ledger SHA-256 is `73005d7a…`; complete manifest SHA-256 is `51bf7fef…`; exact two-node diagnostic SHA-256 is `a025ada8…`. Fresh parent/`5c6a4a8`-bound paths and successor evidence require Kiro PASS and a new Ryan grant |
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
| M11 advanced-main differential | **PASS / PRESERVED at `65bbfd6f`** | the reviewed 22-node rule and all other fresh differential gates passed; retained failures remain explicit and `FULL_PYTEST_PASS=false` |
| M11 first reconstruction Pylint correction | **IMPLEMENTED / PRESERVED at `c71d37a`** | historical input to the accepted §18.19 correction |
| M11 Pylint acceptance-drift correction | **IMPLEMENTED / DIFFERENTIAL PASS at `caec5c6`** | exact one-file/two-transformation correction and fresh three-tip evidence pass; Pylint source/pair regression is closed |
| M11 Pylint `R0401` determinism correction | **IMPLEMENTED / EVIDENCE PASS at `9da6dd98`** | reviewed plan and four-literal rebind landed; fresh three-tip and paired seeded-Pylint evidence passed |
| M11 final-M8 legacy-count correction | **PLAN ONLY / NOT AUTHORIZED** | §18.21/§10.19 preserve the governed 118/117 observation and freeze one later fixture path with exactly two integer substitutions; run 2/MCP remain blocked pending Kiro review and a new Ryan grant |
| Merge readiness | **PAUSED FOR REVIEWED M8 COUNT PLAN AND FRESH EVIDENCE** | requires exact-tip Kiro PASS, new Ryan grant, reviewed plan application onto `9da6dd98`, four-literal rebind, exact one-path/two-integer count correction, fresh three-tip differential, paired seeded Pylint, two M8 runs, seven MCP regressions, durable verification, Kiro integrated-tip PASS and unchanged `origin/main` |
| Phase 1A/1B real OpenClaw operation | **BLOCKED** | Gate D runtime qualification and later production gates |
| Child-agent inheritance question | **UNANSWERED** | requires observing a real OpenClaw dispatch run after Phase 1B lands |
| Transcript capture | **BLOCKED** | independent poison-transcript/Chroma upsert crash-loop fix; explicitly out of scope for this phase |

## 5. Your Role

**If Ryan sent you here:** review only the plan-only final-M8 legacy-count drift
correction. Confirm `N1=5c6a4a8`, preserved reviewed candidate `R=cd60cf1`,
preserved M8-count PAUSE candidate `9da6dd98`, PAUSE-ledger SHA-256
`73005d7a…`, manifest SHA-256 `51bf7fef…` and diagnostic SHA-256
`a025ada8…`. Confirm §18.21 preserves the exact two added passing
`test_shadow_writer_coverage_scan.py` nodes; requires every previously accepted
legacy node unchanged; freezes exactly 118 collected / 117 passed / one skip /
four unchanged deselections; permits only the later two integer substitutions
in `tests/fixtures/openclaw_strict/constants.py`; and still requires fresh
three-tip, paired seeded-Pylint, M8 and MCP evidence. Do not apply plans, edit
fixtures/source/tests, run an acceptance suite, create a PR, merge, update/run
OpenClaw or touch live data.

## 6. What Remains Before This Arc Is Live

1. Kiro performs exact-tip binary design/scope review of the revised semantic
   parent, milestone overlay and this STATUS.
2. If Kiro passes, Ryan decides whether to grant the exact reviewed plan range
   onto preserved `9da6dd98`, four frozen parent/overlay identity substitutions,
   the exact one-path/two-integer legacy-count correction, fixed slot and new
   parent/current-main-bound runtime and evidence roots.
3. Under that grant, Grok applies only the reviewed plan range, pushes and
   stops; after separate Codex inspections and commit-specific `CONTINUE`
   statuses, Grok makes only the exact four-literal rebind and then only the
   `116→118` / `115→117` substitutions inside
   `EXPECTED_LEGACY_JUNIT_COUNTS`, pushing and stopping after each. No selector,
   deselection, test-function, parser or other source correction is eligible.
4. Codex proves final tree composition, then runs fresh complete pytest at
   `N1`, `R` and the final candidate in one reset slot. The exact 22-node closed
   signature proof supplements, but does not replace, the 238-node partition,
   five-node R2b proof and all other differential gates. Only a three-tip PASS
   releases paired full-tree Pylint at `N1` and final source under the sole
   environment addition `PYTHONHASHSEED=0`. Exact 458/29 `R0401`/69 `R0801`/240
   counts, cross-tip semantic hashes, protected-gate zero and retained raw
   output then release two fresh M8 runs. Each must produce 118/117/one skip/
   four deselections and the historical legacy array plus exactly the two named
   passing nodes. Seven MCP regressions follow. Kiro reviews the exact resulting
   tip and durable evidence.
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
- No plan application, four-literal rebind, count correction or acceptance
  suite until Kiro passes the exact §18.21 plan and Ryan issues a new resume
  grant.
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
- For the §18.21 correction, no source/test/CI/baseline/runtime-content or
  configuration edit beyond the separately held four parent/overlay literals
  and the later exact `116→118` / `115→117` substitutions in the one named
  fixture-constants path; no selector/deselection/test-function/parser change,
  no seed other than `0`, no environment delta besides `PYTHONHASHSEED=0`, no
  raw-report rewriting and no semantic normalization beyond the exact frozen
  record projections and canonical encodings.
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
| 2026-09-26 | Codex | Fresh differential and paired seeded Pylint passed at `9da6dd98`; final M8 run 1 paused on two added passing current-main safety nodes, so §18.21 now freezes the exact 118/117 successor count and one-path/two-integer correction before a complete fresh evidence sequence. |
