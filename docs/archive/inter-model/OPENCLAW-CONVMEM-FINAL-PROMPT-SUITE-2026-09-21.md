# Archived final-review prompts [Arc ConvMem Switchboard]

**Status:** HISTORICAL / NOT A RESUME OR EXECUTE INSTRUCTION.
**Owner:** Codex documentation closeout; active Switchboard supervision remains separate.
**Sunset:** Retained for provenance only; never use this archive to choose the next checkpoint.

Preserved verbatim from the uncommitted 2026-09-21 prompt suite on 2026-09-24.
The old Kiro-next, M3, gate and SHA statements below are historical, not current.
Original payload SHA-256: `31a42946793bdea4fe34d400b2cead3ba61e34ffe95b16d08d0d56e5a21c2247`.
For current routing, read [Switchboard STATUS](../../plans/STATUS-openclaw-convmem-integration.md).

<!-- BEGIN VERBATIM ORIGINAL -->
# OpenClaw ↔ ConvMem final prompt suite

## RESUME HERE — Ryan's break, 2026-09-21 [Arc none]

> **NEXT ACTION ON RETURN: Kiro exact-tip sign-off of `cd9d269`. ASTRA HAS ALREADY PASSED IT.**
> The corrective edit and final Astra review are complete. Do not restart the `2aa66a8` edit,
> rerun Astra, or reopen planning merely for missing implementation evidence.

Use [Kiro sign-off prompt](#kiro-sign-off-prompt) below with the exact SHA, bundle and completed
Astra report listed here. The earlier edit/Astra prompts are historical inputs, not work to repeat.
Ryan requested this visible resume marker before taking a break; adding it does not start Kiro,
edit the architecture, or grant Execute.

- Current planning SHA: `cd9d2698b7423f907b552bc9118a0af523018ca9`.
- Branch: `plan/2026-09-20-openclaw-convmem-final-readiness`.
- Worktree: `/tmp/convmem-openclaw-final-readiness`.
- Exact bundle: `/tmp/openclaw-convmem-final-readiness-cd9d2698b7423f907b552bc9118a0af523018ca9.zip`.
- Verified bundle SHA-256: `2d0b0810947e4caedff5c77c0c89a5e02fd72bad293bad98127a4aff5050c9c2`.
- Gates: **BUILD PASS (Astra exact-tip specification review complete; Kiro still required),
  TEST NOT YET RUN, LIVE-DATA BLOCKED, PROMOTION BLOCKED**.
- Completed report: `/tmp/astra-final-cd9d2698b7423f907b552bc9118a0af523018ca9/STAGE-1-REVIEW.md`.
  Its `REVIEWED_PLAN_SHA` and `REVIEWED_BUNDLE_SHA256` match this target; it states BUILD PASS
  and no remaining BUILD blocker. Report SHA-256:
  `b923847c95ed48351ad20dc4f829c1d4c09a98ffc1ad361872abeafdda1d2941`.
  The marker verified report identity/verdict, not a second architectural review.
- On return: verify the branch has not advanced and whether Kiro has already reviewed this tip.
  If not, request Kiro's exact-tip decision. After Kiro PASS, Ryan alone decides any Execute grant.

**Retain these four editorial guardrails; they are not new blockers or a reason to redo the edit:**

1. No-edit outcome: verify/reuse the current SHA and bundle; no empty commit or needless rebuild/push.
2. Real denial evidence concerns the disposable sandbox's physical boundary. Fake peer/role/manager
   behavior uses independent model oracles, not a new requirement for Gate D production enforcement.
3. A coherent, complete, testable normative contract can resolve an architectural contradiction.
   Mere assurances cannot; executable conformance remains TEST work, not prerequisite proof for BUILD.
4. With the harness prohibited, keep TEST NOT YET RUN. Existing configured Git authentication may
   support an explicitly authorized planning-branch push only; no credential inspection, auth setup,
   or OpenClaw/provider credential use.

**Stop after this reminder.** Resume substantive work only when Ryan returns and requests it.
The reference draft remains uncommitted; neither planning file nor the review bundle changed.

**Status:** Working reference draft; uncommitted
**Arc:** none (ad-hoc integration)
**Purpose:** Freeze the bounded-BUILD prompt design and the exact final-review
handoff for the third architectural edit.

## Governing principle

We do not require perfection before implementation.

The final planning cycle decides whether the architecture is safe and
sufficiently complete for bounded, isolated implementation by Cursor/Grok.

The review must distinguish:

1. `BUILD BLOCKER`
2. `SAFE TO DEFER INTO ISOLATED IMPLEMENTATION`
3. `LIVE-DATA/PROMOTION BLOCKER`
4. `NON-BLOCKING UNCERTAINTY`

A BUILD PASS is allowed when core state semantics, authority, provenance,
fixture containment, rollback, and recovery are sufficiently defined; Grok has
no unresolved architectural decision; remaining deficiencies are observable,
testable, owned, and correctable; and implementation can avoid live data,
production systems, credentials, and uncontrolled external services.

BUILD readiness does not imply live-data or promotion readiness.

## Revision variables

Every handoff must carry these exact values:

```text
PLAN_SHA=<exact planning commit>
PLAN_BRANCH=<exact planning branch>
BUNDLE_PATH=<exact review bundle>
BUNDLE_SHA256=<exact bundle SHA-256>
PARENT_PLAN_SHA=<immediate parent planning SHA>
CODE_BASELINE_SHA=7809f20dc53d9dd19f765c3ec3214a3df54ca5bf
```

After an edit, all later prompts consume the editor's new SHA and bundle.
No later prompt may continue to cite an older planning revision.

## Current exact-target final review prompt

Use this prompt for the fresh Astra review of the third edit. It is tied to
the exact revision supplied by the editor, rather than to an older planning
SHA or to the editor's provisional `BUILD BLOCKED — ARCHITECTURE` label.

```text
You are Astra performing the final independent adversarial review of the
ConvMem + OpenClaw planning event.

This is intended to be the last review needed before a bounded implementation
decision. Your job is to decide whether Cursor/Grok can begin the explicitly
scoped fixture implementation safely. Do not keep the project in planning in
search of theoretical perfection. Do not lower a genuine blocker merely
because implementation is desired.

Review exactly this revision:

- Planning SHA: 0f1216f7249c0066dafb6fc9ef2aafa9845a7264
- Planning branch: plan/2026-09-20-openclaw-convmem-final-readiness
- Planning worktree: /tmp/convmem-openclaw-final-readiness
- Architecture: docs/plans/ARCHITECTURE-openclaw-convmem-integration.md
- Execution plan: docs/plans/EXECUTION-openclaw-convmem-integration.md
- Immediate parent planning SHA: 9b106b908b944f8bd4c3f417b576dc13884f2503
- Code baseline: 7809f20dc53d9dd19f765c3ec3214a3df54ca5bf

Use the two files at the exact planning SHA. If a review bundle is supplied,
verify that its contents and SHA correspond to
0f1216f7249c0066dafb6fc9ef2aafa9845a7264 before relying on it.
Do not silently review the current checkout, an earlier bundle, or an
uncommitted copy.

The governing principle is:

WE DO NOT REQUIRE PERFECTION BEFORE IMPLEMENTATION.

The decision is whether the architecture is safe and sufficiently complete
for bounded, isolated implementation. The target implementation is the
fixture-capable, read-only ConvMem projection and the explicitly listed
OpenClaw connector/control fixtures in the execution plan. The plan also
contains later requirements for an actual installed OpenClaw runtime, sealed
distribution, host containment, live-data use, and promotion. Determine from
the frozen scope which requirements are needed before this bounded BUILD and
which belong to later gates. Do not treat the phrase "complete integration"
as the BUILD scope unless the plan actually requires Grok to implement it now.

The edited packet reports these remaining findings. Treat them as claims to
verify, not as automatic decisions:

- C-RUNTIME: the inspected OpenClaw authentication path rejects the selected
  credential-free local-provider configuration.
- D-CONTAINMENT: concrete isolation and independent retirement enforcement
  remain unqualified.
- D-DISTRIBUTION: sealed runtime/model artifacts and effective runtime
  inventory remain missing.

The edit also claims to have frozen these architectural changes. Verify that
the claims are real, coherent, and usable by an implementer:

- cumulative authority and rollback serve only the current authority head;
- canonical verification state is independent of retrieval filters;
- byte grounding, authenticated capture receipts, and bounded provenance
  claims are explicit;
- external retirement ownership, persistent freshness, and serialized
  release/revocation are explicit;
- approval, explicit `add --file`, admission, and projection are separate;
- private qualification occurs outside OpenClaw's runtime.

Do not accept a change log, evidence list, or acceptance-case count as proof
by itself. Check the actual contracts, state transitions, ownership rules,
file scope, and tests in both planning files.

Use exactly these issue classifications for every remaining issue:

1. BUILD BLOCKER
2. SAFE TO DEFER INTO ISOLATED IMPLEMENTATION
3. LIVE-DATA/PROMOTION BLOCKER
4. NON-BLOCKING UNCERTAINTY

For every issue classified SAFE TO DEFER INTO ISOLATED IMPLEMENTATION, give
all of the following:

- why deferral is safe for the named fixture scope;
- the observable failure that would reveal the issue;
- the exact acceptance test, including the negative control where relevant;
- the correction owner and exact correction location;
- the correction path and the gate where it must be completed;
- why it cannot contaminate authority, provenance, security, rollback,
  recovery, or the architecture;
- the stop condition that converts it to a BUILD BLOCKER;
- an explicit statement that Grok does not need to choose an architecture to
  implement the current scope.

Never classify an issue SAFE TO DEFER if Grok would have to invent or choose
authority, schema, interface, state transition, authentication route,
containment boundary, artifact format, rollback rule, recovery rule, or
acceptance criteria.

Apply this decision rule to the three reported findings:

- C-RUNTIME is SAFE TO DEFER only if the frozen T0-T5 fixture can run against
  an explicit fake/local test contract without selecting, approximating, or
  hiding the real OpenClaw authentication route. The unresolved real route
  must be isolated to a named later gate with an exact acceptance test. If the
  fixture scope depends on the real route, or if the plan leaves Grok to pick
  credentials, provider semantics, or a fallback, it is a BUILD BLOCKER. A
  fixture fake may test the frozen protocol only; it does not resolve
  C-RUNTIME, prove actual OpenClaw compatibility, or authorize a live route.

- D-CONTAINMENT is SAFE TO DEFER only if the fixture has a concrete,
  testable containment contract and the fake manager/controller/supervisor
  tests exercise the required failure, retirement, empty-domain, and
  no-ambient-access behavior. Missing host or deployment proof may remain a
  later LIVE-DATA/PROMOTION blocker when the fixture does not depend on it.
  If the fixture can escape its disposable scope, or Grok must choose the
  UID, mount, socket, process, network, or retirement semantics, it is a
  BUILD BLOCKER.

- D-DISTRIBUTION is SAFE TO DEFER only if the fixture uses explicit,
  reproducible artifacts and manifests already defined by the plan, and Grok
  does not need to choose the production image, model, argv, configuration,
  inventory, or sealing boundary. Missing proof of the eventual sealed
  distribution is a later gate blocker only when it cannot affect the
  bounded fixture. Otherwise it is a BUILD BLOCKER.

Keep these gates separate:

- BUILD: may the frozen bounded implementation begin?
- TEST: are the specified disposable acceptance tests run and passing?
- LIVE-DATA: may real ConvMem data, production configuration, or live
  credentials be accessed?
- PROMOTION: may an external system, channel, gateway, model provider, or
  consequential data be affected?

Use explicit values for each gate: PASS, BLOCKED, or NOT YET RUN. A valid
result may be BUILD=PASS while TEST=NOT YET RUN, LIVE-DATA=BLOCKED, and
PROMOTION=BLOCKED. BUILD PASS never implies production readiness.

Perform the complete fresh-Astra checklist from architecture section 17 and
report each item separately:

1. Continuity/publication: genesis, admission, fence, unavailable head,
   rebuild, rollback, retry, crash points, no hash cycle, no authority
   rollback, no lost disposition/witness, no ABA publication success.
2. State/retrieval: full canonical bound state, fork precedence, unresolved
   predicate, selected-out conflicts, no retrieval-filter state reduction,
   support union, completeness metadata, no cross-audience influence.
3. Identity/provenance: no remint/reuse, unchanged envelopes, exact byte
   grounding, authenticated receipt issuance, frozen original admission,
   registered non-LLM closure, no late witness or LLM closure upgrade.
4. Ownership/concurrency: stable slot and lineage, independent scope
   digests, UID separation, lock order, controller/supervisor distinction,
   manager-empty retirement/quarantine, death/stale-receipt/concurrent-
   publish/blocked-consumer cases.
5. Freshness/release: revoke, clock rollback, suspend, same-boot restart,
   rebuild/rollback, new-boot review, and no promise to retract committed
   bytes or renew evidence by restart.
6. Closed runtime: verify or refute the authentication-path evidence and
   identify whether a compatible route is needed for BUILD or only for a
   later runtime gate; check CWD/HOME/temp/network/FD/mount/dependency/image
   closure and effective inventory.
7. Explicit writes/recovery: trace every caller family through the planned
   engine or refusal; reject implicit add, copied signer/marker, Chroma
   authority, automatic legacy migration, restore bypass, lost-backup, and
   writer-guard bypass; separate fixture behavior from Gate W production.
8. Packet completeness: compare architecture and execution inventories,
   schemas, fields, CLI verbs, file owners, gate owners, tests, and issue
   classifications. A newly discovered architecture choice is a BUILD
   BLOCKER; a proposed remedy alone does not earn BUILD PASS.

Treat the two passing static routing tests as routing/document evidence only.
Treat the reproduced authentication probe as evidence of the reported
compatibility issue, then decide whether that issue blocks the bounded scope
under the rules above. Neither result validates an unimplemented integration.

Re-attack the parent-to-target change from
9b106b908b944f8bd4c3f417b576dc13884f2503 to
0f1216f7249c0066dafb6fc9ef2aafa9845a7264. Ask explicitly:

WHAT DID THIS REVISION BREAK THAT WAS PREVIOUSLY SOUND?

Exercise regressions against the newly frozen authority-head/rollback rule,
canonical verification state, byte grounding and receipts, retirement and
freshness ownership, explicit ingestion/admission/projection separation, and
private qualification. Also check that the new fixture boundary has not
silently weakened no-ambient-credentials, physical scope isolation, legacy
compatibility, rollback, recovery, or promotion controls.

Do not initiate another architecture-review/edit cycle merely because a
runtime artifact, production distribution, or live-data proof is still
missing. Continue planning only if:

- a genuine BUILD BLOCKER remains;
- the bounded fixture scope itself is unsafe or incomplete;
- the proposed implementation requires an unresolved architectural choice;
- the edit introduced a regression that changes the BUILD decision; or
- a supposedly deferred issue lacks an observable test, correction path, or
  architecture-contamination stop condition.

If only SAFE TO DEFER INTO ISOLATED IMPLEMENTATION and/or NON-BLOCKING
UNCERTAINTY issues remain, BUILD must PASS. Do not return BUILD BLOCKED merely
because the complete live integration is not ready.

Return exactly this structure:

FINAL ASTRA REVIEW
REVIEWED_PLAN_SHA: 0f1216f7249c0066dafb6fc9ef2aafa9845a7264
REVIEWED_PARENT_SHA: 9b106b908b944f8bd4c3f417b576dc13884f2503
REVIEWED_SCOPE: FIXTURE_IMPLEMENTATION | COMPLETE_INTEGRATION | AMBIGUOUS
BUILD: PASS | BLOCKED | NOT YET DECIDED
TEST: PASS | BLOCKED | NOT YET RUN
LIVE_DATA: PASS | BLOCKED | NOT YET RUN
PROMOTION: PASS | BLOCKED | NOT YET RUN

DECISION:
<one paragraph stating whether Grok can start the frozen bounded scope and
why the remaining findings do or do not block it>

CHECKLIST_17_RESULTS:
<items 1 through 8, each PASS, FAIL, or INCOMPLETE with evidence>

REMAINING_ISSUES:
<one row per issue with: id, exact classification, evidence, affected gate,
safe-deferral rationale if applicable, observable failure, exact acceptance
test, correction owner/location, correction path, contamination stop
condition, and whether Grok would need an architectural decision>

REGRESSION_RESULTS:
<parent-to-target regression matrix and the answer to what this revision broke>

REQUIRED_NEXT_ACTION:
<Kiro exact-tip review if BUILD=PASS; otherwise the smallest architectural edit
needed to remove each BUILD BLOCKER>

If BUILD=PASS, include these exact sentences verbatim:

Grok can begin implementation without making an architectural decision.
Known deferred issues do not authorize Grok to redesign the architecture.

Do not implement code, modify the plans, configure OpenClaw, access live
ConvMem data, install packages, start gateways, use credentials, or perform
external actions. This is a review of the exact planning revision.
```

The final Astra run must save its complete report at this concrete path (or a
new concrete path returned in the Astra handoff):

```text
/tmp/astra-final-0f1216f7249c0066dafb6fc9ef2aafa9845a7264/STAGE-1-REVIEW.md
```

The architectural editor may proceed only after verifying that the report
exists and states `REVIEWED_PLAN_SHA:
0f1216f7249c0066dafb6fc9ef2aafa9845a7264`. The literal placeholder
`<ASTRA_FINAL_REVIEW_REPORT_PATH>` is never a valid input.

## Final-cycle sequence

1. Fresh Astra adversarial review of the current packet.
2. Codex architectural edit using Astra's findings and candidate remedies.
3. Optional fresh Astra review only if the edit is substantively architectural.
4. Kiro exact-tip binary PASS/FAIL.
5. Ryan Execute grant.
6. Cursor/Grok bounded implementation.

Do not initiate another architecture cycle merely because an issue remains
imperfect. Reopen planning only for a genuine BUILD BLOCKER, an unresolved
architectural decision, or a regression that changes the build decision.

## Final corrective edit prompt after bounded BUILD PASS

Use the following prompt for the last possible architectural edit after
planning revision `2aa66a8753db3be6adce7cb17533eae96aee609d`. The packet already
has `BUILD=PASS` for bounded fixture implementation. Preserve that green light
unless focused scrutiny finds a concrete contradiction in the fixture
contract.

```text
You are Codex performing the final corrective edit for the ConvMem + OpenClaw
bounded fixture implementation plan.

The current packet already has BUILD=PASS for bounded fixture implementation.
Do not reopen planning for perfect confidence, unexecuted test results, real
OpenClaw compatibility, host deployment proof, sealed production distribution,
live-data access, or promotion readiness.

CURRENT TARGET

- Planning SHA: 2aa66a8753db3be6adce7cb17533eae96aee609d
- Branch: plan/2026-09-20-openclaw-convmem-final-readiness
- Worktree: /tmp/convmem-openclaw-final-readiness
- Architecture: docs/plans/ARCHITECTURE-openclaw-convmem-integration.md
- Execution plan: docs/plans/EXECUTION-openclaw-convmem-integration.md
- Parent SHA: 0f1216f7249c0066dafb6fc9ef2aafa9845a7264
- Bundle: /tmp/openclaw-convmem-final-readiness-2aa66a8753db3be6adce7cb17533eae96aee609d.zip
- Bundle SHA-256: ebbc2d8cf3344cd6c82cb9793c0d137d8f72cf36dd1595ff2398d58467e03d92
- Code baseline: 7809f20dc53d9dd19f765c3ec3214a3df54ca5bf
- Parent Astra report: /tmp/astra-final-0f1216f7249c0066dafb6fc9ef2aafa9845a7264/STAGE-1-REVIEW.md

Verify the exact current files, commit, branch, and bundle before editing. The
parent Astra report reviewed 0f1216f..., not this current target, so it is not
an exact-tip certification of 2aa66a8....

CURRENT GATES

- BUILD: PASS for bounded fixture implementation
- TEST: NOT YET RUN
- LIVE-DATA: BLOCKED
- PROMOTION: BLOCKED

Preserve these statuses unless the focused scrutiny below proves that the
bounded fixture contract itself is contradictory or unsafe. Missing execution
evidence is TEST work. Real authentication, host containment, sealed runtime
distribution, Gate W production writes, live ConvMem data, and promotion are
later gates.

FIRST DECISION: EDIT OR NO EDIT

If the focused issues are only unexecuted, unmeasured, or later-gate
qualifications, return NO EDIT REQUIRED, preserve BUILD=PASS, and request the
required exact-tip Astra review of the current SHA.

Edit only if a concrete contradiction means that the bounded fixture cannot
run safely within its frozen scope, the runner contract is incoherent, the
manager does not independently model membership, the safety tests cannot
falsify a bad implementation, or Grok must choose an architecture.

Do not change BUILD to BLOCKED merely because the runner has not been executed,
capacity numbers are unmeasured, or production qualification is absent.

FOCUSED SCRUTINY

1. Runner executability

Inspect the bubblewrap boundary, mounts, environment, runtime inventory,
dependency closure, and teardown. Decide whether the pinned Python/Node
dependencies can run under the stated restrictions without hidden host
dependencies or extra mounts.

If provisioning or execution evidence is missing but the contract is coherent,
leave BUILD=PASS and record TEST=NOT YET RUN with the exact test and correction
path. If the contract is inherently contradictory, freeze the smallest
coherent dependency, mount, environment, or teardown rule in both plans and
add an exact acceptance test and negative control. Do not add unbounded host
access or weaken isolation.

2. Capacity limits

Treat the 600-second suite deadline, 16 MiB output ceiling, and 256 MiB
private `/tmp` limit as unmeasured choices, not demonstrated capacity.

If they are merely unvalidated, preserve BUILD=PASS and make TEST measure them.
If a limit is inherently incompatible with the fixture scope, define the
measurement method, failure behavior, and acceptance threshold. Keep these
limits separate from protocol deadlines, authority rules, and evidence
freshness; do not relax those invariants to fit the harness.

3. Independent manager and supervisor behavior

Verify that the fake manager is independent of the supervisor. Supervisor
death, a stop acknowledgement, or a cleanup callback must not manufacture an
empty-domain result. Detached descendants and outstanding model work must
remain in modeled membership until independent manager events remove them.

If the contract or tests allow supervisor events to synthesize manager truth,
repair the ownership and event rules in both plans. Add cases for supervisor
death, stop acknowledgement, cleanup callback, detached descendants,
outstanding work, independent removal, and genuine empty-domain observation.

4. Independent safety tests

Hash-reference walkers must independently enforce the frozen inventory; they
must not obtain expected hashes from the implementation under test.

Containment tests must observe real denials and exercise failing bypass
controls; mocked `access denied` responses alone are insufficient.

File-mutation tests must mutate disposable copies and never protected source
files.

If the test contract cannot falsify a bad implementation, repair the test
oracle, fixtures, negative controls, or evidence requirements. Do not broaden
implementation scope merely to make tests easier.

5. Protocol fake versus real runtime

Preserve the distinction between a protocol fake and compatibility evidence.
The fake must not authenticate, select a provider, or become
production-selectable. Real OpenClaw authentication, host enforcement, sealed
distribution, and Gate W remain outside this edit unless a concrete fixture
dependency proves the fixture cannot run without one.

Do not use dummy credentials, hidden fallbacks, ambient host access, or a fake
provider as evidence of production compatibility.

REPAIR STANDARD

For every actual bounded BUILD contradiction, record:

BLOCKER_ID:
FAILED_BUILD_CRITERION:
WHY_CURRENT_CONTRACT_FAILS:
MINIMUM_REPAIR:
FILES_AND_SECTIONS_CHANGED:
FROZEN_FIXTURE_CONTRACT:
EXACT_ACCEPTANCE_TEST:
NEGATIVE_CONTROL:
ROLLBACK_OR_RECOVERY_BEHAVIOR:
OWNER_AND_CORRECTION_PATH:
REGRESSION_TEST:
NEW_STATUS: RESOLVED | REMAINS_BLOCKED

Do not mark a contradiction resolved by adding prose, repeating the finding,
or claiming future evidence. Mark it RESOLVED only when the plans define a
coherent implementation contract and Grok can implement it without making an
architectural decision.

Edit only:

- docs/plans/ARCHITECTURE-openclaw-convmem-integration.md
- docs/plans/EXECUTION-openclaw-convmem-integration.md

Preserve the existing authority, provenance, rollback, recovery, lifecycle,
scope, and legacy-behavior invariants. Preserve BUILD=PASS when no true
fixture blocker remains. Preserve TEST=NOT YET RUN, LIVE-DATA=BLOCKED, and
PROMOTION=BLOCKED.

Add a regression matrix answering:

WHAT DID THIS EDIT BREAK THAT WAS PREVIOUSLY SOUND?

At minimum test authority-head continuity, canonical verification, byte
grounding, receipts, retirement/freshness, explicit ingestion/admission/
projection, physical isolation, no ambient credentials, legacy behavior,
rollback, recovery, and fixture/live-data/promotion separation.

ANTI-INFINITE-LOOP RULE

Do not edit merely because the runner is unexecuted, capacity is unmeasured,
or production qualification is unfinished. Continue editing only for a
concrete contradiction, unsafe fixture behavior, unresolved architecture, or a
regression that changes BUILD.

VALIDATION AND HANDOFF

Before handoff, verify both plans, run document consistency checks and
`git diff --check`, rebuild and verify the exact bundle, commit, and push the
planning branch. Do not run the implementation harness, access live ConvMem
data, use credentials, start gateways, or promote anything.

Return exactly:

FINAL CORRECTIVE EDIT HANDOFF
PARENT_PLAN_SHA: 2aa66a8753db3be6adce7cb17533eae96aee609d
EDIT_STATUS: APPLIED | NO_EDIT_REQUIRED
NEW_PLAN_SHA: <new SHA or current SHA if no edit>
NEW_PLAN_BRANCH: <branch>
NEW_BUNDLE_PATH: <exact bundle path>
NEW_BUNDLE_SHA256: <exact bundle SHA-256>
CODE_BASELINE_SHA: 7809f20dc53d9dd19f765c3ec3214a3df54ca5bf
BUILD_STATUS: PASS | BLOCKED
TEST_STATUS: PASS | BLOCKED | NOT YET RUN
LIVE_DATA_STATUS: BLOCKED
PROMOTION_STATUS: BLOCKED
REPAIR_RECORDS: <records, or NONE>
FOCUSED_SCRUTINY_RESULT: <runner, capacity, manager, test-oracle, and runtime-boundary findings>
REGRESSION_RESULT: <what broke, or evidence that nothing broke>
FINAL_ASTRA_REVIEW_REQUIRED: YES
FINAL_ASTRA_REVIEW_REASON: <focused exact-tip review of fixture and hash contracts before Kiro>
NEXT_LANE: Astra

If BUILD_STATUS is PASS, include these exact sentences:

Grok can begin implementation without making an architectural decision.
Known deferred issues do not authorize Grok to redesign the architecture.

If BUILD_STATUS is BLOCKED, identify only the concrete fixture contradiction
that caused the downgrade. Do not list unexecuted tests, unmeasured capacity,
live-data qualification, or promotion readiness as BUILD blockers.
```

## Final exact-tip Astra handoff after `cd9d269`

Use this as the one final Astra review before Kiro. It verifies the corrective
runner edit at its exact tip and does not reopen planning for unexecuted tests,
unmeasured capacity, or later production qualification.

```text
You are Astra performing the final exact-tip adversarial review of the
ConvMem + OpenClaw bounded fixture implementation plan.

This is the final review before Kiro’s exact-tip decision. The current packet
already reports BUILD=PASS for bounded fixture implementation. Verify that
decision against the revised contracts, but do not search for theoretical
perfection or require implementation evidence before BUILD.

REVIEW EXACTLY THIS REVISION

- Parent SHA: 2aa66a8753db3be6adce7cb17533eae96aee609d
- Reviewed SHA: cd9d2698b7423f907b552bc9118a0af523018ca9
- Branch: plan/2026-09-20-openclaw-convmem-final-readiness
- Worktree: /tmp/convmem-openclaw-final-readiness
- Architecture: docs/plans/ARCHITECTURE-openclaw-convmem-integration.md
- Execution plan: docs/plans/EXECUTION-openclaw-convmem-integration.md
- Bundle: /tmp/openclaw-convmem-final-readiness-cd9d2698b7423f907b552bc9118a0af523018ca9.zip
- Bundle SHA-256: 2d0b0810947e4caedff5c77c0c89a5e02fd72bad293bad98127a4aff5050c9c2
- Code baseline: 7809f20dc53d9dd19f765c3ec3214a3df54ca5bf

Use the bundle and both planning files at the exact reviewed SHA. Verify the
bundle contents and manifest before relying on the editor’s claims. The prior
Astra report for 0f1216f is not certification of this tip.

CURRENT GATES

- BUILD: PASS for bounded fixture implementation, pending this review
- TEST: NOT YET RUN
- LIVE-DATA: BLOCKED
- PROMOTION: BLOCKED

Keep these gates separate. BUILD PASS does not imply TEST PASS, live-data
authorization, production readiness, or promotion authorization.

DECISION STANDARD

The question is whether Cursor/Grok can implement the frozen disposable
fixture scope without making an architectural decision.

Do not convert BUILD to BLOCKED merely because:

- the implementation harness has not run;
- capacity limits are not measured;
- the full repository test suite is not claimed;
- four legacy tests require forbidden hook/Git/systemd subprocesses;
- real OpenClaw authentication is unqualified;
- host containment is not production-proven;
- sealed runtime/model distribution is incomplete; or
- live-data and promotion remain blocked.

Convert BUILD to BLOCKED only if the revised fixture contract is inherently
contradictory or unsafe, or if Grok must choose an unresolved architecture.

Use exactly these classifications:

- BUILD BLOCKER
- SAFE TO DEFER INTO ISOLATED IMPLEMENTATION
- LIVE-DATA/PROMOTION BLOCKER
- NON-BLOCKING UNCERTAINTY

For every SAFE-TO-DEFER issue provide why deferral is safe, the observable
failure, exact acceptance test, negative control, correction owner/location,
correction path, architecture-contamination analysis, and stop condition.
Never defer an issue that requires Grok to invent authority, schema, state,
interface, authentication, containment, artifact, rollback, recovery, or
acceptance behavior.

VERIFY B-RUNNER-CLOSURE

Verify that the fixture dependencies now have one closed, inventoried runtime
boundary:

- interpreter, packages, loader, libraries, and data bytes are all bound by
  one runtime inventory;
- `/usr` is mounted from the supplied prefix’s inventoried `sysroot/usr`;
- no host-library fallback or unlisted mount is possible;
- mount mapping, versions, resolved dependencies, file modes, and hashes are
  checked before implementation imports;
- removing or changing a copied dependency fails preflight;
- adding an unlisted file fails preflight;
- proposing a host `/usr` bind fails preflight;
- refusal retains uncertain teardown evidence without changing authority head
  or expiry.

Check the actual architecture and execution contracts, not only the repair
record. Determine whether the negative controls could catch a real bypass.

VERIFY B-RUNNER-SUITES

Verify that acceptance commands are compatible with the closed runner:

- the three bounded suites are named exactly;
- the four incompatible hook/Git/systemd legacy nodes are explicitly excluded;
- strict imports are separated from legacy compatibility imports;
- all required strict cases remain selected;
- full discovery fails when forbidden;
- extra deselection fails;
- a missing safety node fails;
- hook/Git/systemd launch attempts fail;
- strict writer imports fail when forbidden;
- selected legacy behavior remains mandatory;
- no full-repository or excluded-node coverage is claimed.

Verify that selection and exclusion rules are independently checked and cannot
simply agree with the implementation under test.

FOCUSED SAFETY REVIEW

- The 600-second suite deadline, 16 MiB output ceiling, and 256 MiB private
  `/tmp` limit remain unmeasured. Treat this as TEST work unless the limits
  make the fixture inherently impossible. Keep capacity separate from
  protocol deadlines and evidence freshness.
- The fake manager must remain independent of the supervisor. Supervisor
  death, stop acknowledgement, or cleanup callback must not manufacture an
  empty-domain result. Detached descendants and outstanding model work remain
  until independent manager events remove them.
- Hash-reference walkers must own expected inventories independently.
- Containment tests must observe real denials and failing bypass controls, not
  only mocked `access denied` responses.
- File-mutation tests must mutate disposable copies, never protected source
  files.
- The protocol fake must not authenticate, select a provider, or become
  production-selectable. Real authentication, host enforcement, sealed
  distribution, Gate W, live data, and promotion remain later gates.

REGRESSION REVIEW

Compare parent 2aa66a8753db3be6adce7cb17533eae96aee609d with target
cd9d2698b7423f907b552bc9118a0af523018ca9. Ask:

WHAT DID THIS REVISION BREAK THAT WAS PREVIOUSLY SOUND?

Attempt regressions against authority-head continuity, canonical verification,
byte grounding, receipts, retirement/freshness, explicit ingestion/admission/
projection, manager/supervisor ownership, physical isolation, no ambient
credentials, legacy behavior, rollback, recovery, independent inventories,
test oracles, and fixture/live-data/promotion separation.

The reported 174 document checks and 148 bundle-manifest checks are packaging
and preservation evidence only. The implementation harness has not run.

FINAL STOP CONDITION

Do not recommend another architecture-edit cycle merely because tests are
unexecuted, capacity is unmeasured, or production qualification is unfinished.
If no BUILD BLOCKER remains, BUILD stays PASS and this is the final planning
review. Proceed to Kiro on this exact SHA.

If a genuine BUILD BLOCKER remains, name the exact failed fixture criterion,
evidence, and smallest required architectural correction. Do not invent a new
review loop for a later-gate issue.

RETURN EXACTLY

FINAL ASTRA EXACT-TIP REVIEW
REVIEWED_PARENT_SHA: 2aa66a8753db3be6adce7cb17533eae96aee609d
REVIEWED_PLAN_SHA: cd9d2698b7423f907b552bc9118a0af523018ca9
REVIEWED_BUNDLE_SHA256: 2d0b0810947e4caedff5c77c0c89a5e02fd72bad293bad98127a4aff5050c9c2
BUILD: PASS | BLOCKED
TEST: PASS | BLOCKED | NOT YET RUN
LIVE_DATA: BLOCKED
PROMOTION: BLOCKED
B_RUNNER_CLOSURE: PASS | FAIL | SAFE TO DEFER
B_RUNNER_SUITES: PASS | FAIL | SAFE TO DEFER
FOCUSED_MANAGER_INDEPENDENCE: PASS | FAIL | SAFE TO DEFER
FOCUSED_TEST_ORACLES: PASS | FAIL | SAFE TO DEFER
PROTOCOL_FAKE_BOUNDARY: PASS | FAIL | SAFE TO DEFER
REMAINING_ISSUES: <classified issues with evidence and exact tests>
REGRESSION_RESULT: <what broke, or evidence that nothing broke>
DECISION: <whether the frozen bounded fixture can proceed and why>
REQUIRED_NEXT_ACTION: <Kiro exact-tip review if BUILD=PASS; otherwise the
smallest correction for each genuine BUILD BLOCKER>

Save the complete report at:
/tmp/astra-final-cd9d2698b7423f907b552bc9118a0af523018ca9/STAGE-1-REVIEW.md

If BUILD=PASS, include these exact sentences:

Grok can begin implementation without making an architectural decision.
Known deferred issues do not authorize Grok to redesign the architecture.

Do not edit the plans, implement code, run the harness, access live ConvMem
data, configure OpenClaw, use credentials, start gateways, or promote anything.
```

## Fresh Astra review prompt

```text
You are Astra, the independent adversarial reviewer of the ConvMem + OpenClaw
architecture.

Arc: none (ad-hoc integration).

Review only this exact packet:

- Planning SHA: <PLAN_SHA>
- Planning branch: <PLAN_BRANCH>
- Bundle: <BUNDLE_PATH>
- Bundle SHA-256: <BUNDLE_SHA256>
- Code baseline: <CODE_BASELINE_SHA>

The goal is not perfection before implementation.

Determine whether the architecture is safe and sufficiently complete for
bounded, isolated fixture implementation by Cursor/Grok without Grok making an
architectural decision.

Do not confuse imperfect with unsafe, product uncertainty with a BUILD
blocker, live-data safety with fixture safety, or an implementation detail with
an architectural decision. Do not weaken a real blocker merely because the
team wants to begin implementation.

Preserve separate gates:

- BUILD: may bounded isolated implementation begin?
- TEST: may disposable fixture tests run with defined acceptance criteria?
- LIVE-DATA: may real ConvMem data or live configuration be accessed?
- PROMOTION: may external systems, channels, websites, or consequential data
  be affected?

For every remaining issue, assign exactly one:

- BUILD BLOCKER
- SAFE TO DEFER INTO ISOLATED IMPLEMENTATION
- LIVE-DATA/PROMOTION BLOCKER
- NON-BLOCKING UNCERTAINTY

A SAFE-TO-DEFER classification requires:

- why deferral is safe;
- the observable failure that would reveal the issue;
- the exact acceptance test;
- the correction owner and location;
- the correction path;
- proof that it cannot contaminate authority, security, or architecture;
- a stop condition if it becomes architectural.

Re-attack prior remedies. Also ask:

“What did this revision break that was previously sound?”

Compare parent and target revisions. Check legacy behavior, approval and
provenance, qualified handles, bounded traversal, strict tool/resource
exposure, physical scope isolation, OpenClaw lifecycle controls, rollback, and
the live-data/promotion boundary.

Do not recommend another review merely because the design is imperfect. If
only SAFE-TO-DEFER or NON-BLOCKING issues remain, BUILD must PASS.

Report BUILD, TEST, LIVE-DATA, and PROMOTION separately. A BUILD PASS may
coexist with LIVE-DATA=BLOCKED and PROMOTION=BLOCKED.

If BUILD passes, state exactly:

“Grok can begin implementation without making an architectural decision.”

Also state exactly:

“Known deferred issues do not authorize Grok to redesign the architecture.”

Do not implement code, configure OpenClaw, access live data, start gateways,
install plugins, make model calls, or perform external actions.
```

## Architectural editor prompt

```text
You are Codex in the architecture/planning lane for ConvMem + OpenClaw.

Arc: none (ad-hoc integration).

Inputs:

- Current planning SHA: <PLAN_SHA>
- Current bundle: <BUNDLE_PATH>
- Astra report: <ASTRA_REPORT_PATH>
- Parent planning SHA: <PARENT_PLAN_SHA>
- Code baseline: <CODE_BASELINE_SHA>

Read the complete Astra report and evidence.

Resolve genuine BUILD BLOCKERS while preserving the principle that perfection
is not required before bounded implementation. Do not edit merely to eliminate
every uncertainty.

Treat Astra #3's surviving candidate solutions as design inputs. For every
finding, record the finding, candidate remedy, Adopt/Modify/Reject decision,
evidence-based reason, cross-finding interactions, frozen owner, schema,
interface, state rule, acceptance test, gate, rollback, and stop condition.

Produce one coherent architecture, not isolated fixes.

Treat Astra's BUILD pass/fail criteria as the repair specification. For every
finding that prevents BUILD=PASS, identify the exact failed criterion, the
contract or decision that is missing, and the smallest change that makes that
criterion true. Then implement that change in both plans and add the exact
acceptance evidence that will allow the next reviewer to verify it.

Do not respond to a BUILD blocker by merely adding prose, repeating the
finding, moving it to a later gate, or adding an evidence heading. A blocker
is resolved only when the frozen architecture, implementation scope, owner,
test, and stop condition together remove the reason the criterion failed.
If the blocker cannot be resolved without inventing facts or making an
unverified architectural choice, leave it classified as BUILD BLOCKER and
explain precisely why an edit cannot safely resolve it.

For each Astra BUILD blocker, add a repair record with this shape:

BLOCKER_ID:
FAILED_BUILD_CRITERION:
WHY_THE_CURRENT_PLAN_FAILS:
REQUIRED_ARCHITECTURAL_REPAIR:
FILES_AND_SECTIONS_CHANGED:
FROZEN_IMPLEMENTATION_CONTRACT:
EXACT_ACCEPTANCE_TEST:
NEGATIVE_CONTROL:
ROLLBACK_OR_RECOVERY_BEHAVIOR:
OWNER_AND_CORRECTION_PATH:
REGRESSION_TEST:
NEW_STATUS: RESOLVED | REMAINS_BLOCKED

The repair record must be consistent with the actual architecture and
execution plan. Do not mark `RESOLVED` unless the change removes the blocker
from the bounded implementation path and Grok can implement it without making
an architectural decision.

For the current reported findings, focus the repair on the blocking reason:

- C-RUNTIME: either freeze a real, compatible route required by the bounded
  fixture, with its no-ambient-credential and acceptance contract, or isolate
  the unresolved installed-runtime route completely behind a later gate. Do
  not claim resolution from a failed probe, a dummy credential, a hidden
  fallback, or a fake provider that only tests protocol behavior.
- D-CONTAINMENT: either freeze the fixture's concrete containment and
  retirement contract and test its failure behavior, or explicitly prove that
  the missing host/deployment controls cannot affect the disposable fixture.
  Do not claim resolution from general statements about isolation.
- D-DISTRIBUTION: either freeze the reproducible fixture artifacts and
  manifests needed by Grok, or isolate the unresolved sealed production
  image/model/inventory behind a later gate. Do not leave Grok to choose an
  image, model, argv, configuration, inventory, or sealing boundary.

The purpose of the edit is to make the reason for BUILD PASS true, not merely
to make the packet appear more complete.

Classify every remaining issue as BUILD BLOCKER, SAFE TO DEFER INTO ISOLATED
IMPLEMENTATION, LIVE-DATA/PROMOTION BLOCKER, or NON-BLOCKING UNCERTAINTY.

SAFE-TO-DEFER is permitted only with a safety rationale, observable failure,
exact acceptance test, correction owner and path, proof of no architecture
contamination, and a stop condition. Grok may not be left to invent authority,
schemas, interfaces, security boundaries, state transitions, rollback, or
acceptance criteria.

Edit only:

- docs/plans/ARCHITECTURE-openclaw-convmem-integration.md
- docs/plans/EXECUTION-openclaw-convmem-integration.md

Preserve ConvMem authority, OpenClaw coordination, physical scope isolation,
immutable read-only fixture projections, legacy behavior, and separate
LIVE-DATA and PROMOTION gates.

Add a parent-to-target regression matrix:

| Previously sound property | Changed section | Regression attempted | Result/evidence |
|---|---|---|---|

The final packet must include frozen architecture and invariants,
implementation scope, explicit non-goals, allowed/protected files, acceptance
tests, known deferred issues, stop conditions, rollback, and Cursor evidence
requirements.

If no BUILD BLOCKER remains, state exactly:

“Grok can begin implementation without making an architectural decision.”

Also state exactly:

“Known deferred issues do not authorize Grok to redesign the architecture.”

Do not initiate another review cycle merely because the packet is imperfect.

Before handoff, verify the changed files, run git diff --check, rebuild and
verify the exact review bundle, commit, and push the new planning revision.

Return:

FINAL PLANNING HANDOFF
PARENT_PLAN_SHA: <old SHA>
NEW_PLAN_SHA: <new SHA>
NEW_PLAN_BRANCH: <branch>
NEW_BUNDLE_PATH: <bundle path>
NEW_BUNDLE_SHA256: <bundle SHA-256>
CODE_BASELINE_SHA: <code baseline>
CHANGE_CLASS: NONE | EDITORIAL_ONLY | SUBSTANTIVE_ARCHITECTURAL
FINAL_ASTRA_REVIEW_REQUIRED: YES | NO
FINAL_ASTRA_REVIEW_REASON: <reason>
BUILD_STATUS: PASS | BLOCKED
NEXT_LANE: Astra | Kiro | Ryan
```

## Optional final Astra review prompt

Use only when the editor reports `SUBSTANTIVE_ARCHITECTURAL` and
`FINAL_ASTRA_REVIEW_REQUIRED: YES`.

```text
You are Astra performing the final bounded-BUILD review of a revised
ConvMem + OpenClaw planning packet.

Review only:

- Parent planning SHA: <PARENT_PLAN_SHA>
- New planning SHA: <NEW_PLAN_SHA>
- Bundle: <NEW_BUNDLE_PATH>
- Bundle SHA-256: <NEW_BUNDLE_SHA256>
- Code baseline: <CODE_BASELINE_SHA>

This review exists only to determine whether the edit changed the BUILD
decision. Do not search for theoretical perfection.

Re-attack every earlier BUILD BLOCKER, every adopted or modified solution,
every cross-finding interaction, every regression in the parent-to-target
matrix, and every failure newly introduced by this edit.

Ask explicitly:

“What did this revision break that was previously sound?”

Use only these classifications:

- BUILD BLOCKER
- SAFE TO DEFER INTO ISOLATED IMPLEMENTATION
- LIVE-DATA/PROMOTION BLOCKER
- NON-BLOCKING UNCERTAINTY

For every SAFE-TO-DEFER issue, require the safety rationale, observable
failure, exact acceptance test, correction owner, correction path, and
architecture-contamination stop condition.

Do not recommend another cycle merely because the design is imperfect. If no
BUILD BLOCKER remains, BUILD must PASS.

Report BUILD, TEST, LIVE-DATA, and PROMOTION separately.

If BUILD passes, state exactly:

“Grok can begin implementation without making an architectural decision.”

Also state exactly:

“Known deferred issues do not authorize Grok to redesign the architecture.”
```

## Kiro sign-off prompt

```text
You are Kiro in the formal design and scope-review lane.

Review this exact final planning SHA: <FINAL_PLAN_SHA>

Issue binary PASS or FAIL for bounded fixture implementation.

Do not fail merely because SAFE-TO-DEFER or NON-BLOCKING issues remain. Fail
only for a BUILD BLOCKER, inadequate fixture containment, undefined fixture
rollback/recovery, an unresolved architectural decision, unsafe deferral, or
missing acceptance/correction criteria.

Verify every SAFE-TO-DEFER issue has its required safety case. Verify that
LIVE-DATA/PROMOTION blockers remain separate.

A PASS means:

“Grok can begin implementation without making an architectural decision.”

It does not authorize implementation. Ryan must issue the Execute grant.
```

## Cursor/Grok build prompt

```text
You are Cursor, the sole implementation writer, using Grok for bounded
implementation.

Execution requires all three on the same planning SHA:

- Astra BUILD PASS: <FINAL_PLAN_SHA>
- Kiro PASS: <FINAL_PLAN_SHA>
- Ryan Execute grant: <EXACT_GRANT>

Read the frozen architecture and execution plan completely.

Known deferred issues are accepted implementation inputs. They do not authorize
Grok to redesign the architecture.

Grok may resolve only ordinary implementation details and corrections whose
owner, interface, acceptance test, and correction path are already frozen.
Stop and return to Codex/Kiro for any authority, schema, interface, security,
state, rollback, scope, or acceptance decision.

Implement only the frozen T0–T5 fixture scope. Use disposable roots and avoid
live ConvMem data, production systems, credentials, uncontrolled network,
external channels, real gateways, model providers, live capture, and
promotion paths.

Run the exact acceptance, negative-control, rollback, and legacy-compatibility
tests. Return changed-file proof, test evidence, deferred-issue observations,
correction-path results, rollback evidence, and proof that live paths were
absent. Do not merge, activate, promote, or claim live readiness.
```
