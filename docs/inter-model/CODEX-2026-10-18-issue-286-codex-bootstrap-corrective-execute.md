# [Arc Codex #286] Cursor Execute — existing Codex rollout bootstrap

**Date:** 2026-10-18. **Author:** Codex. **For:** Cursor implementation lane.
**Authorization:** Ryan explicitly authorized Cursor T1–T5 implementation and hermetic verification of reviewed revision `942390001bca407c1c28e9972c443ee7612e1c1b`, incorporating Kiro's non-blocking precision notes, with existing operational prohibitions retained.

## Resume state

- **State:** `IN_PROGRESS` — T1 complete (`ec11b10`), T2 complete (`1dc1eff3dcfdae43e68624adc7f2749de1f377f1`), T3–T5 not started.
- **Reviewed plan branch:** `plan/2026-10-18-issue-286-codex-bootstrap-corrective`.
- **Reviewed plan SHA:** `942390001bca407c1c28e9972c443ee7612e1c1b`.
- **Code baseline:** `483373f1cef2142847fcd9c276196593a72a0ecf`.
- **Implementation branch:** `fix/2026-10-18-issue-286-codex-bootstrap` (worktree active; Kiro planning checkout separate).
- **Planning push status:** reviewed plan is on origin; this handoff is delivered on the same planning branch. Use the exact handoff commit supplied by Ryan/Codex when picking up.
- **PR:** not opened; no PR authority.
- **Ryan GATE before T1:** satisfied by the grant above, subject to startup protocol and scope/baseline checks. Production gates remain closed.

## Review and authority provenance

Kiro passed the direction at `e0e91bd32f96bce1f8c109a84005ed547d8655ff`. Ryan approved it and requested execution planning. Kiro then returned **PASS, no blockers**, for the execution plan and companions at `942390001bca407c1c28e9972c443ee7612e1c1b`. Ryan supplied both written reviews in this conversation; no separate review file is claimed.

Ryan's subsequent grant was:

> Authorize Cursor T1–T5 implementation and hermetic verification of reviewed revision 942390001bca407c1c28e9972c443ee7612e1c1b, incorporating Kiro’s non-blocking precision notes. Existing operational prohibitions remain in force.

This supersedes the reviewed documents' historical “implementation not authorized” labels for **Cursor T1–T5 only**. It does not authorize Codex implementation or any live action. The pinned plan's substantive scope, task dependencies, contracts, and stop conditions remain binding.

## What to build

Enable a reviewed one-shot route to adopt the three exact existing Codex rollouts while preserving source/transform identity, paid-attempt ceilings, initial-plus-one recovery, and unrelated compatible writers' data. Today's shipped entrypoint is Kiro-only and cannot perform A1.

Read the [execution plan](../plans/EXECUTION-issue-286-codex-bootstrap-corrective.md) at the reviewed SHA before editing. Execute its five tasks **serially**:

1. **T1:** format-bound v2 grant and genuinely read-only preflight; Kiro v1 compatibility.
2. **T2:** durable reservation/invocation authority and cumulative paid accounting.
3. **T3:** enforced writer cooperation, preparation lease, and scoped watcher deferral.
4. **T4:** exact-prefix coordinator execution and source-only recovery/follower completion.
5. **T5:** integrated hermetic evidence and separate implementation/live-readiness results.

Use the plan's named integration points and file scope. In particular, correct the entrypoint's default-Kiro `source_state_id` call, support recovery from a reserved ordinal-1 operation with no transaction, and classify valid coordination deferral before retry mutation and CLI exit 91. Do not generalize ordinary `bootstrap_required` into deferral.

## Kiro precision notes incorporated into this grant

These clarify the reviewed plan; they do not change its scope or dependencies:

1. **Busy preparation lease:** `source_writer_busy` is terminal for the current invocation. Return once without spinning, retrying inside that invocation, waiting indefinitely, or consuming initial authority/provider permits. A later caller invocation must perform fresh preflight. A stalled legacy writer is never killed by bootstrap.
2. **Deferral exit status:** when selecting the dedicated value in T3, prove in VERIFY V6 that it is disjoint from the actual timeout/native/signal status set used by the child and parent, as well as 0/1/91. Checking only “not 91” is insufficient. Record the chosen constant and exact paths tested.
3. **Recovery/cutover boundary:** the §5 inventory requires evidence that existing recovery/cutover callers are disjoint or safely refused through shared guards. It grants no edits to Recovery Authority policy or those callers' business logic. If closure needs such changes, stop and return the exact gap to Ryan/Codex before broadening scope.
4. **VERIFY V0:** the `EXECUTE-TASK.md` fields are intentional: applicability, reason, subject SHA, BugBot-reviewed SHA, result, finding disposition, and authority reference. Keep them. The no-PR restriction means PR-native review remains a later gate; do not invent an exemption for runtime/concurrency changes.

## Pickup and branch discipline

Follow the canonical doctor-first startup protocol; a failed startup gate stops pickup. Read the [current Arc Codex brief](../plans/STATUS-codex-jsonl-production-integration.md) and state Goal / role / system state / next action and Arc Codex identity.

Fetch origin and resolve the exact published handoff revision supplied with this handoff. Verify it contains the reviewed plan commit and has only documentation changes since that commit. Confirm the implementation code tree still matches baseline `483373f1`; do not silently move to newer main code. Material baseline drift returns to Ryan/Codex.

Create the implementation branch from that pinned handoff revision and attach it through `convmem work resume <branch> --worktree` before the first edit. Do not switch or clean the shared checkout, reuse another lane's worktree, or touch runtime-main. If the named branch already exists, inspect its owner/state before resuming; do not overwrite it.

Push each commit immediately with an explicit refspec:
`git push -u origin fix/2026-10-18-issue-286-codex-bootstrap:refs/heads/fix/2026-10-18-issue-286-codex-bootstrap`.
Do not merge, force-push, or create a PR.

## Verification and acceptance

Fill [VERIFY-issue-286-codex-bootstrap-corrective.md](../plans/VERIFY-issue-286-codex-bootstrap-corrective.md) for the exact implementation tip. Follow each task's evidence gate and the plan's V0–V8 mapping. Applicable skipped proofs block mechanical PASS.

- Establish external network/filesystem isolation and temporary HOME/config/data before importing path-caching modules. Use synthetic transcripts, fake transports, and real temporary Chroma only. Redirect synthesis-failure logging before exercising failures.
- Prove identity and v1 regressions, every durable crash boundary, permits before sends, cumulative caps, one recovery, lock-order/liveness rules, writer coverage, deferral behavior, and foreign-byte-preserving rollback with independent oracles and negative controls.
- Record exact commands, interpreter, exit codes, test counts, evidence paths, subject SHA, and residual owners. Use metadata/counts only; never print transcript/prompt/provider-response content.
- Keep `IMPLEMENTATION_EVIDENCE`, independent review, PR/merge readiness, and `LIVE_READINESS` separate. The actual outer 3,000-call enforcement contract and compatible writer deployment remain owner-supplied live prerequisites. No fake gate or checked boolean may stand in for their enforcement.
- No baseline relaxation, unrelated refactor, generic admission/budget redesign, or another arc's policy edits. Stop on an uncovered writer or material contract mismatch and return evidence to Ryan/Codex.

The current grant authorizes the scoped hermetic tests. It does not authorize a host-default full suite that can reach production state. Follow the reviewed plan's isolation requirement before any broader tests.

## Operational prohibitions and later gates

No A1 bootstrap, A2 resumption, other production indexing, real provider/embedding calls, deployment, runtime-main/live-config change, watcher stop/restart, quarantine clearing, transcript/source mutation, PR, or Part B work. Code and test changes are authorized only in the isolated implementation checkout under T1–T5.

Kiro's reported doctor PASS during direction review does not diagnose A2's earlier `ledger_documents: database is locked` incident or authorize resumption. A1 stays parked even after a bare “go A1.” Any later live run needs reviewed compatible code/deployment, proven writer and outer-budget enforcement, fresh health/source/backup evidence, exact numeric caps, and Ryan's separate execution grant. Preserve the 4 GB RSS/new-doctor-FAIL stops; never kill another lane's process.

## Handoff after implementation

Stop for exact-tip independent review. Return the implementation branch and full SHA, push status, T1–T5 evidence/results, the VERIFY path, and remaining live gates with owners. Do not claim live readiness from hermetic PASS. No PR or review-trigger comment is authorized here; obtain the applicable later grant before entering that lifecycle.

**Next lane now:** Cursor T3. **Resume state:** `IN_PROGRESS` (T2 landed at `1dc1eff3dcfdae43e68624adc7f2749de1f377f1`).

**TL;DR:** [Arc Codex] Ryan authorizes Cursor's reviewed T1–T5 implementation and hermetic verification, including Kiro's precision notes. All production and PR prohibitions remain; A1 is parked and A2 is stopped.

<!-- src: ../plans/EXECUTION-issue-286-codex-bootstrap-corrective.md — reviewed at 942390001bca407c1c28e9972c443ee7612e1c1b -->
<!-- ref: ../plans/VERIFY-issue-286-codex-bootstrap-corrective.md, ../plans/STATUS-codex-jsonl-production-integration.md, ./LATEST.md — execution evidence and routing -->
