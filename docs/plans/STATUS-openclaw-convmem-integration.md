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
| Architecture direction | **BOUNDED BUILD/TEST PASS** for synthetic T0–T5; the plan-only post-bundle authority-packet reconciliation preserves the publisher fix and freezes only four 40-hex substitutions across two fixture/test files plus fresh final-source evidence |
| Bounded implementation | **ACCEPTED** at `8010fb060c2edc29e1b09d7a30b1a1da2689d489` over original baseline `7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`; two M8 runs and exact-tip Kiro conformance passed |
| Current-main baseline | `9193f5ec744f059d07a20612489b210527b5660a`; accepted implementation and current main have no product-path overlap, but acceptance does not transfer without reconstruction and fresh evidence |
| M11 integration branch | The reviewed bundle-schema plans and exact one-literal publisher fix are **PRESERVED, CLEAN AND PUSHED** at `851edbe49b820bd4081809022b10f67c30fef47a` on `feat/2026-09-23-openclaw-convmem-m11-integration`; pre-remediation comparison tip remains `9c6421a6891fd8a861a51f4fed410f541b53148c` |
| M11 verification | Complete runs at `9c6421a` and `851edbe4` have identical 2,912-node/outcome totals; all 238 retained failures/errors are closed, so `PYTEST_DIFFERENTIAL_PASS=true` and `FULL_PYTEST_PASS=false`. The unchanged current-main Pylint gate **PASS** has 458 findings and no new/increased fingerprint |
| M11 final M8 evidence | **PAUSED BEFORE SOURCE EXPORT/FIXTURE CREATION.** M8 run 1 exited 2 because the command used reviewed parent `b46a16a3…` while the fixture packet still requires preceding parent `48c9ce01…`. No integration import, runtime use or test occurred; run 2 and seven MCP regressions did not run. Architecture §18.13 and Execution §10.11 freeze only the exact two-file/four-literal correction and fresh evidence sequence |
| Runtime/evidence | Runtime tree SHA-256 `74a12c…` remained byte/mode-identical after the refusal. The durable PAUSE classification hashes to `3fbfab4b…`. Another plan application, source/test edit or run requires Kiro exact-tip PASS and a new Ryan grant |
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
| M11 post-bundle authority-packet reconciliation | **PLAN-ONLY / NOT AUTHORIZED** | Kiro exact-tip review and new Ryan grant for four 40-hex substitutions across two files plus fresh final-source evidence |
| Merge readiness | **NOT YET PROVEN** | requires fresh final-source differential and Pylint PASS, two M8 PASSes, seven MCP regressions, durable verification and Kiro integrated-tip PASS |
| Phase 1A/1B real OpenClaw operation | **BLOCKED** | Gate D runtime qualification and later production gates |
| Child-agent inheritance question | **UNANSWERED** | requires observing a real OpenClaw dispatch run after Phase 1B lands |
| Transcript capture | **BLOCKED** | independent poison-transcript/Chroma upsert crash-loop fix; explicitly out of scope for this phase |

## 5. Your Role

**If Ryan sent you here:** review the exact post-bundle authority-packet
reconciliation. Confirm `851edbe4` is clean and pushed, its four plan blobs equal
reviewed overlay `6b1b90b4`, its one-literal publisher correction is exact, and
its fresh differential and Pylint evidence pass. Confirm M8 run 1 supplied
parent `b46a16a3…` but refused before source export/fixture creation because
`constants.py` and its frozen packet assertions still bind parent `48c9ce01…`
and overlay `57285608…`. Confirm the correction permits exactly four 40-hex
substitutions across `constants.py` and `test_openclaw_strict_packet_contract.py`,
with no other test logic or source edit, and requires Grok to stop after plan
application and after the packet correction. Codex must then repeat the complete
differential, unchanged Pylint gate, two fresh M8 runs and seven MCP regressions.
Do not edit product/CI/runtime files, run another suite, merge, update/run OpenClaw or touch live data.
Only a later Ryan grant may resume the preserved implementation branch. Real
OpenClaw remains blocked by Gate D/W and later gates.

## 6. What Remains Before This Arc Is Live

1. Kiro performs exact-tip binary design/scope review of the revised semantic
   parent, milestone overlay and this current-state STATUS, including the exact
   two-file/four-literal boundary and fresh final-source evidence sequence.
2. If Kiro passes, Ryan decides whether to grant resumption on preserved
   candidate `851edbe4`, naming the exact parent/overlay, differential baseline
   `9c6421a`, integration branch, fixed slot, runtime/evidence roots, PAUSE
   evidence/hash and exact source correction.
3. Under that grant, Grok applies only the newly reviewed plan range after
   `6b1b90b4` and stops. Codex proves the four final reviewed blobs and every
   non-plan byte. A commit-specific `CONTINUE` then permits only the two
   grant-named identity declarations and their two frozen assertions; Grok
   pushes and stops again for exact diff inspection. Test logic must not change.
4. Codex repeats the complete repository differential at baseline `9c6421a`
   and the corrected final candidate in the identical fixed-slot environment,
   including all symmetric reruns and the closed five-node R2b proof. It then
   reruns the unchanged current-main Pylint gate.
5. Only after both gates pass does Codex run M8 twice and all seven MCP
   regressions at the final source, preserve durable evidence and obtain Kiro
   exact-tip conformance review. Ryan alone decides merge.
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
- No authority-packet correction or M8 retry until Kiro passes the exact plan
  tip and Ryan issues a new resume grant; no test edit beyond the two frozen
  40-hex assertion values is authorized.
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
