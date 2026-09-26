# Milestone Execution Plan — ConvMem–OpenClaw

**Status:** M0–M8 BOUNDED GATE B/C ACCEPTED AT `8010fb0`. COMPLETE BOUNDED M11
MERGE-READINESS EVIDENCE AND KIRO EXACT-TIP REVIEW PASS AT `cd60cf19`. MERGE IS
PAUSED AFTER THE ADVANCED-MAIN CANDIDATE AT `776a4ca3` COMPLETED THREE PYTEST
RUNS AND 166 RERUNS, THEN STOPPED ON UNSTABLE PYTEST ENVIRONMENT RENDERING FOR
AN EXACT 22-NODE INNER-ROLE FAILURE FAMILY. THE PLAN-ONLY CLOSED SEMANTIC-
SIGNATURE RECONCILIATION IS READY FOR KIRO REVIEW, THEN A NEW RYAN RESUME
DECISION.
Product/test/CI/runtime edits, test execution, PR, merge and real OpenClaw work
are paused.

**Arc:** ConvMem Switchboard

## 0. Authority, scope, and interpretation

This is a sequencing and supervision overlay. Its semantic parent is exactly:

```text
SEMANTIC_PARENT_SHA=9faac8ea87532bc73f74b788b38234de0c614a4e
ORIGINAL_CODE_BASELINE_SHA=7809f20dc53d9dd19f765c3ec3214a3df54ca5bf
ACCEPTED_IMPLEMENTATION_SHA=8010fb060c2edc29e1b09d7a30b1a1da2689d489
INTEGRATION_BASELINE_SHA=9193f5ec744f059d07a20612489b210527b5660a
PRIOR_CURRENT_MAIN_BASELINE_SHA=a92a74eb326b3eaa59087b707de10153c7cc0c63
CURRENT_MAIN_BASELINE_SHA=5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
PRESERVED_M11_EVIDENCE_BRANCH=feat/2026-09-23-openclaw-convmem-m11-integration
PRESERVED_THREE_TIP_PREFLIGHT_BRANCH=feat/2026-09-26-openclaw-convmem-m11-main-reconciliation
PRESERVED_ADVANCED_MAIN_BRANCH=feat/2026-09-26-openclaw-convmem-m11-main-advance
PRESERVED_INTEGRATION_TIP=a11b7a2a793c68e4e6e83c2680b077389a817c5c
RECONCILIATION_BASE_OVERLAY_SHA=581de2abf430786a36f2612f97c623a19b61353f
PYLINT_PLAN_BASE_OVERLAY_SHA=c5513d50b656f9cc9e6423ea819438f975d16ee5
PYTEST_PLAN_BASE_OVERLAY_SHA=67d4f5aa62415f3550fbc56a760374cf3c19ee23
PYTEST_IDENTITY_PLAN_BASE_OVERLAY_SHA=b0358464caf493992810137e40c8ed619e7af932
M8_AUTHORITY_PLAN_BASE_OVERLAY_SHA=b1b2341a4f98701f5784631f866c5405174c7414
BUNDLE_SCHEMA_PLAN_BASE_OVERLAY_SHA=57285608b2ee9ec5950201968bc533b8830a6ea8
AUTHORITY_PACKET_PLAN_BASE_OVERLAY_SHA=6b1b90b4865dc0b92e0ead470136eeebc3bd8447
CURRENT_MAIN_PLAN_BASE_OVERLAY_SHA=fc5289a18db4a8ea0a8f215e2148b2b6aba3b41d
THREE_TIP_PLAN_BASE_OVERLAY_SHA=b5d0c96dc0837ae515db0787ac136c308b25aaad
CURRENT_MAIN_ADVANCE_PLAN_BASE_OVERLAY_SHA=05e0d79712fdb7c9d2e5640b8c4a744d3f84e56b
INNER_ROLE_SIGNATURE_PLAN_BASE_OVERLAY_SHA=5b14010302021dcd7dc579f5714517a0f26570e1
PRESERVED_M11_TIP=9c6421a6891fd8a861a51f4fed410f541b53148c
PYTEST_DIFFERENTIAL_BASE_SHA=9c6421a6891fd8a861a51f4fed410f541b53148c
PRESERVED_M11_CANDIDATE_SHA=3f8ef8312e3f3c98915320bd1b988bac5d8d96a9
PRESERVED_M11_DIFFERENTIAL_PAUSE_SHA=853ef98ede44f2d171e5354b065e11f83558e010
PRESERVED_M11_M8_PAUSE_SHA=7f2a2e22c74cf9fd87c00982d1ea0ce18fc978af
PRESERVED_M11_BUNDLE_SCHEMA_PAUSE_SHA=d7b15926ab7e4e41b8a80edba5edbe4bfed4c165
PRESERVED_M11_AUTHORITY_PACKET_PAUSE_SHA=851edbe49b820bd4081809022b10f67c30fef47a
PRESERVED_M11_MERGE_READY_SHA=cd60cf19dca6706e4175e9f82c9ba55e41bca10b
PRESERVED_M11_CURRENT_MAIN_PAUSE_SHA=30bc134d74d7eeb4cef4d6371a5e96c926f0f2ca
PRESERVED_M11_THREE_TIP_PREFLIGHT_SHA=d276cb4ab0a0613b965e772d49d378e761df337e
PRESERVED_M11_INNER_ROLE_PAUSE_SHA=776a4ca3d4215490fb26b882dca2df9a41e0e03a
PRIOR_CURRENT_MAIN_DELTA_PATH_COUNT=40
PRIOR_CURRENT_MAIN_DELTA_PATH_SET_SHA256=596a484cbf550a63bf77ac559733455aceadef75aaa5d3d8a6fee417b6695e6b
CURRENT_MAIN_ADVANCE_PATH_COUNT=11
CURRENT_MAIN_ADVANCE_PATH_SET_SHA256=0566d14e2246970abe77a89736db01a95ae89cb88d2c9556f33c14b6bf7c484c
CURRENT_MAIN_DELTA_PATH_COUNT=45
CURRENT_MAIN_DELTA_PATH_SET_SHA256=670241f7690afc18cf8689c7406ac6d86d395bfc323acfc5f2f72a85a46c853e
PRESERVED_THREE_TIP_DELTA_PATH_COUNT=124
PRESERVED_THREE_TIP_DELTA_PATH_SET_SHA256=af1b9fd8a991fe689cf8819f03bb1e6417ff159c91677d70417f289cea53b314
REVIEWED_DELTA_PATH_COUNT=124
REVIEWED_DELTA_PATH_SET_SHA256=af1b9fd8a991fe689cf8819f03bb1e6417ff159c91677d70417f289cea53b314
PRODUCT_DELTA_PATH_COUNT=120
PRODUCT_DELTA_PATH_SET_SHA256=60903bc194bd6e471f6c7009df30ab0832cad7a5505e9fd14b2c64450d27c659
CURRENT_MAIN_R2B_IDENTITY=b716152fbf725633a55371f6acf7ed5580a704bd
RECONSTRUCTED_R2B_IDENTITY=e060dce4eb3d51e0f4650ded8bd1aad4f2a34f4b
R2B_MEMBER_COUNT=120
R2B_PATH_SET_SHA256=fb062070b962265bfce6c2cc2b709eca4b2d5f7a8d1a516d5b3599bcb0361ec8
PYTEST_DIFFERENTIAL_PAUSE_LEDGER_SHA256=3c2a50d1a61578fa235524bc26493a2b1458ba60d729b039c0a66d27ddce0c1e
PYTEST_DIFFERENTIAL_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/3317913e74997f97a135339b596461b1f8080626/9193f5ec744f059d07a20612489b210527b5660a/runs/853ef98ede44f2d171e5354b065e11f83558e010/m11-full-pytest-differential-pause
M8_PAUSE_CLASSIFICATION_SHA256=e217e5607640b5f1985ad57256f7911fc8b409364ecc25c5f98e22c25082105c
M8_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/9c5c2bf7d3c5b6d9f13d68329b6f7112c25cabe1/9193f5ec744f059d07a20612489b210527b5660a/runs/7f2a2e22c74cf9fd87c00982d1ea0ce18fc978af/m11-m8-run1-final
BUNDLE_SCHEMA_PAUSE_CLASSIFICATION_SHA256=c25ece6380d0b1cf4989a010419307dfdc29c2ecc31b9c4dd47faaee23b89148
BUNDLE_SCHEMA_DRIFT_SHA256=50a82638e4265c910dcdf7422d193bb6178ff29c51e175dd05fa1949cc4713d5
BUNDLE_SCHEMA_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/48c9ce01bf557ff95fd82b84c3b0ab2e7e9f18cb/9193f5ec744f059d07a20612489b210527b5660a/runs/d7b15926ab7e4e41b8a80edba5edbe4bfed4c165/m11-m8-run1-final
AUTHORITY_PACKET_PAUSE_CLASSIFICATION_SHA256=3fbfab4bac23c30325961d21a974ec4ed03229759c1b974686d323c061982c77
AUTHORITY_PACKET_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/b46a16a3cdc928e98fba83cd64b17439d1734695/9193f5ec744f059d07a20612489b210527b5660a/runs/851edbe49b820bd4081809022b10f67c30fef47a/m11-m8-run1-final
CURRENT_MAIN_DIFFERENTIAL_COMPARISON_SHA256=03873a4d4e368e5b5fd3de86140e3fd9b74525c3e83b966275d556fd9728693b
CURRENT_MAIN_DIFFERENTIAL_PAUSE_LEDGER_SHA256=3bd89ebf3dd016d5fc709215862ae491688cb878c3477fbd9f21f3619b2d256e
CURRENT_MAIN_DIFFERENTIAL_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/33767acaf563c25e8fbd9984f08316f1ba4b1b27/a92a74eb326b3eaa59087b707de10153c7cc0c63/runs/30bc134d74d7eeb4cef4d6371a5e96c926f0f2ca/m11-current-main-pytest-differential
SWITCHBOARD_CANDIDATE_ONLY_NODE_COUNT=238
SWITCHBOARD_CANDIDATE_ONLY_IDENTITY_SHA256=fe50be2f51456d85efdf80305af83a7d0fa224110cd4980a27da74ed46e291b8
SWITCHBOARD_CANDIDATE_ONLY_IDENTITY_OUTCOME_SHA256=2c03a11c8c5d66b822b406e35deb6874be0dd4301fe78d51780da96977b4c607
SWITCHBOARD_CANDIDATE_ONLY_PASSED_COUNT=160
SWITCHBOARD_CANDIDATE_ONLY_PASSED_IDENTITY_SHA256=b98f02f3f6d8b1c14b9d0e90e4dbb0f8e67e12698842ab37b381f5f4b2c35ae1
SWITCHBOARD_CANDIDATE_ONLY_FAILED_COUNT=78
SWITCHBOARD_CANDIDATE_ONLY_FAILED_IDENTITY_SHA256=e3fdc26e69739af0ff33282378d02d6d930416daa8b89fc6964825ecd6e08423
INNER_ROLE_SIGNATURE_NODE_COUNT=22
INNER_ROLE_SIGNATURE_NODE_SET_SHA256=9fa64e04c15b96cbb935cb5b40d4e47a9cdd5869099d728a5213174c7244cbf6
INNER_ROLE_PAUSE_LEDGER_SHA256=a6a2d95b6f294ad3893ea39fa8c739b15a7ea172d2067757492c49abf49399a6
INNER_ROLE_DIAGNOSTIC_SHA256=115492f91adeaf71aa09afd81b66e863191d0e7306efdd2a51a1168633c0376d
INNER_ROLE_PAUSE_MANIFEST_SHA256=78ac1cef55142892cdf75d2cad71a22a536519a4d27359fedba04881020e1c80
INNER_ROLE_RERUN_PLAN_SHA256=15d082c9805943a11c4c6236c5f23e48bf64440aa8b60cda29b25c2ad55eddcd
INNER_ROLE_PRELIMINARY_COMPARISON_SHA256=674f79845a763293128e5e2d95230c0ded1c296a42fa0365061e9f4a089f1f91
INNER_ROLE_PAUSE_EVIDENCE=/home/lauer/.local/share/convmem-openclaw-evidence/538d37eb498e2d3bd497db33daa006520ad56d06/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/776a4ca3d4215490fb26b882dca2df9a41e0e03a/m11-three-tip-pytest-differential/comparison
PRESERVED_THREE_TIP_UNUSED_SLOT=/home/lauer/.cache/convmem-m11-three-tip-differential/300180f7c0a382b6e7d85b2858a338c271ce695e/slot
PRESERVED_THREE_TIP_UNUSED_EVIDENCE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/300180f7c0a382b6e7d85b2858a338c271ce695e/a92a74eb326b3eaa59087b707de10153c7cc0c63/runs/d276cb4ab0a0613b965e772d49d378e761df337e/m11-three-tip-pytest-differential
PROPOSED_FIXED_EXECUTION_SLOT=/home/lauer/.cache/convmem-m11-inner-role-signature/9faac8ea87532bc73f74b788b38234de0c614a4e/slot
PROPOSED_RUNTIME_PREFIX=/home/lauer/.local/share/convmem-openclaw-runtimes/9faac8ea87532bc73f74b788b38234de0c614a4e/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
PROPOSED_DURABLE_EVIDENCE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/9faac8ea87532bc73f74b788b38234de0c614a4e/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
ARCHITECTURE=docs/plans/ARCHITECTURE-openclaw-convmem-integration.md
EXECUTION=docs/plans/EXECUTION-openclaw-convmem-integration.md
```

After Ryan confirms that root, exact plan-review artifacts go only under
`PROPOSED_DURABLE_EVIDENCE_ROOT/planning-reviews/`; M11 run evidence goes only
under `PROPOSED_DURABLE_EVIDENCE_ROOT/runs/<integration-source-commit>/<run-label>/`.
Codex verifies every volatile-to-durable byte/hash mapping. These paths are
evidence stores, not authority, approval, production data or a ConvMem corpus.

The two parent documents define every schema, field, hash, state transition,
interface, error, limit, identity, test case, and allowed path. This overlay
does not replace, loosen, or reinterpret them. A conflict stops work and goes
to Codex/Kiro; Grok must not choose between readings. M0–M8 proved only the
parent's synthetic T0–T5 Gate B/C fixture on the original baseline. M11 must
preserve and re-prove that exact implementation on the integration baseline
before merge readiness. Gate D real
runtime, Gate W governed writes, Gate D-V value evaluation, Gate E pilot/live
use, Gate F expansion, watch configuration, and promotion remain separately
blocked.

The runner's single `--plan-sha` is always `SEMANTIC_PARENT_SHA`. The overlay
SHA is the exact final branch tip Kiro reviews and Ryan later names as
`REVIEWED_OVERLAY_SHA`; it is not substituted into the parent's runner
contract. The final overlay descends from `SEMANTIC_PARENT_SHA`; its planning
branch starts at `INNER_ROLE_SIGNATURE_PLAN_BASE_OVERLAY_SHA`. The preserved evidence
branch remains immutable at `PRESERVED_M11_MERGE_READY_SHA` and is never
rebased, merged, force-pushed, replayed, or used as a branch base. The first
current-main and three-tip branches are preserved at
`PRESERVED_M11_CURRENT_MAIN_PAUSE_SHA` and `PRESERVED_M11_THREE_TIP_PREFLIGHT_SHA`.
The completed advanced-main branch is preserved at
`PRESERVED_M11_INNER_ROLE_PAUSE_SHA`. After Kiro PASS and a new Ryan grant,
Grok applies the exact complete reviewed plan range onto that preserved tip,
pushes and stops. After Codex's commit-specific `CONTINUE`, Grok makes the held
two-file/four-literal parent/overlay rebind, pushes and stops. Codex alone then
executes the fresh three-tip evidence defined in M11. The
historical `AUTHORITY_PACKET_PLAN_BASE_OVERLAY_SHA`, `PYLINT_PLAN_BASE_OVERLAY_SHA` and
`PYTEST_PLAN_BASE_OVERLAY_SHA` and `PYTEST_IDENTITY_PLAN_BASE_OVERLAY_SHA`
and `M8_AUTHORITY_PLAN_BASE_OVERLAY_SHA` and `BUNDLE_SCHEMA_PLAN_BASE_OVERLAY_SHA`
remain evidence of already-applied ranges and are never replayed. No plan-range
cherry-pick onto either preserved branch is part of this correction.

Ryan's R-PROFILE-REFUSAL ruling ratifies the baseline selector normalization
`(value or "").strip().lower()`. When the semantic parent does not explicitly
freeze refusal presentation, exact stderr bytes and numeric exit codes are
noncontractual implementation details. Tests bind the specified semantic
failure class and effects, never implementation-derived presentation: nonzero
exit, empty stdout, no registration/start/effect, no raw-value disclosure, and
any parent-required semantic instruction. This rule applies consistently to
profile, fixture, CLI, publisher, and runner refusals; an explicitly frozen
parent error contract still controls.

Ryan's 2026-09-23 M8 node-inventory ruling authorized only that completed
correction: the two frozen Python commands may emit pytest's built-in JUnit XML under
disposable `/fixture/evidence`, solely for exact collected node IDs and
outcomes. The parent freezes the output paths, xunit1 mapping, canonical
evidence shape and fail-closed parser. Selectors, four deselections, selected
test logic, dependencies, permissions, containment and runtime behavior remain
unchanged. The accepted M8 PASS does not transfer to the M11 integration tree.

The Grok-facing actualization brief at commit
`e476e0e01db9a3d25ed3f1037e49293324434dfc`,
`docs/inter-model/GROK-2026-09-21-openclaw-convmem-actualization-brief.md`, is
implementation detail only. The semantic parent governs behavior; this
overlay governs milestone order, holds, and supervision. Any conflict
stops work. Its Steps 0–9 govern detailed task decomposition where consistent;
the actualization brief never overrides either governing document. This
overlay expressly supersedes that brief's `READY FOR ... EXECUTE DECISION`
status, single-`REVIEWED_PLAN_SHA` authority packet, Step 0.1 grant wording,
and Step 0.2 instruction for Grok to create the branch. The brief is not an
authorization source; the overlay's two-SHA grant and Codex-created worktree
procedure control.

Review and authority order is mandatory:

1. Opus's adversarial `BUILD FAIL` on overlay `9243765` is reconciled here.
2. Ryan's written R-PROFILE-REFUSAL ruling ratifies baseline normalization and
   makes parent-unspecified refusal presentation noncontractual; it authorizes
   this overlay-only correction and no implementation.
3. Kiro PASSed overlay `d1ca459` with semantic parent `cd9d2698`; Ryan then
   granted bounded M0–M8 implementation.
4. The node-evidence correction was implemented; two accepted fresh-root runs
   and exact-tip Kiro conformance review established bounded M8 TEST PASS at
   `8010fb060c2edc29e1b09d7a30b1a1da2689d489` under parent `3433813` and
   overlay `b16763f`.
5. Ryan accepted bounded M0–M8 and authorized M11 merge-readiness. Codex's
   baseline audit found that current main `9193f5e` and the accepted
   implementation require explicit reconstruction and new evidence; Codex
   issued `PAUSE` rather than silently rebasing.
6. Kiro reviewed the current-main reconciliation overlay `581de2a`; Ryan
   authorized M11. The exact 45-commit replay and pin/comment reconciliation
   were completed, held, inspected and preserved at `a11b7a2`.
7. The first fresh M8 attempt stopped before source export, imports or tests:
   the outer runner reported the four reviewed plan/STATUS paths as product
   allowlist violations. Codex retained the evidence and issued `PAUSE`.
8. Ryan authorized the reviewed-plan correction from `581de2a`; Kiro passed its
   final overlay `c5513d5`. Ryan then granted exact application, bounded
   correction and M8 retry. The resulting clean pushed tip is `9c6421a`.
9. At `9c6421a`, two fresh M8 runs and the seven legacy MCP regressions passed.
   The unchanged current-main Pylint gate failed on 699 new occurrences. Codex
   retained the evidence and issued `PAUSE` rather than raising a baseline or
   weakening CI.
10. Ryan directed Codex to choose the durable lint resolution. Kiro passed the
    reviewed plan; Ryan granted the exact 44-path remediation. The corrected
    candidate is clean and pushed at `PRESERVED_M11_CANDIDATE_SHA`; its unchanged
    current-main Pylint gate passes with no new/increased fingerprint.
11. The first complete repository pytest attempt retained failures. Independent
    diagnostics reproduced structural failures at both `PRESERVED_M11_TIP` and
    the candidate, proving an unconditional full-pytest PASS claim inapplicable.
    Codex issued `PAUSE`; Ryan authorized this plan-only differential correction.
12. Kiro passed differential overlay `b035846` with semantic parent `3317913`.
    Ryan granted only its plan application and Codex-owned evidence sequence.
    Grok applied the exact reviewed plan range and pushed
    `PRESERVED_M11_DIFFERENTIAL_PAUSE_SHA`; Codex verified the four document
    blobs and non-plan-byte identity before continuing.
13. Complete baseline/candidate runs collected equal 2,912-node sets and equal
    outcome totals but produced 28 signature mismatches: 23 path/repr effects
    and five R2b authority-content identity rotations. Codex emitted
    `PYTEST_DIFFERENTIAL_PASS=false`, retained the exact PAUSE ledger, and ran
    no later evidence after the stop.
14. Ryan authorized the plan-only identity reconciliation; Kiro passed parent
    `9c5c2bf` and overlay `b1b2341`. Ryan granted its exact application and
    evidence sequence. Grok applied the reviewed range; the clean pushed source
    is `PRESERVED_M11_M8_PAUSE_SHA`.
15. Codex established `PYTEST_DIFFERENTIAL_PASS=true` with 2,912 equal nodes,
    233 identical debt nodes and the exact five R2b rotations, then re-proved
    the unchanged current-main Pylint gate. The first final M8 run refused
    before fixture creation because embedded parent/overlay literals remained
    bound to the preceding reviewed packet. Codex retained the PAUSE and ran no
    M8 run 2 or MCP regression.
16. Ryan authorized the plan-only M8 authority-packet reconciliation; Kiro
    passed parent `48c9ce0` and overlay `57285608`. Ryan granted its exact plan
    application, two-file/four-literal rebind and evidence sequence. Grok
    applied the plans and correction; the clean pushed candidate is
    `PRESERVED_M11_BUNDLE_SCHEMA_PAUSE_SHA`. Codex re-established the complete
    differential and unchanged Pylint gate, then M8 run 1 reached the strict
    suite and produced 28 failures at one invented production bundle-schema
    literal. Codex retained the PAUSE and ran no M8 run 2 or MCP regression.
17. Ryan authorized the plan-only bundle-schema reconciliation; Kiro passed
    parent `b46a16a3` and overlay `6b1b90b4`. Ryan granted their exact
    application, the one-file/one-literal publisher correction and evidence
    sequence. Grok applied the plans and correction; the clean pushed candidate
    is `PRESERVED_M11_AUTHORITY_PACKET_PAUSE_SHA`. Codex re-established the
    complete differential and unchanged Pylint gate. Final M8 run 1 then
    refused before source export or fixture creation because the fixture packet
    remained bound to preceding parent `48c9ce01…` and overlay `57285608…`.
    Codex preserved classification `AUTHORITY_PACKET_PAUSE_CLASSIFICATION_SHA256`
    and ran no M8 run 2 or MCP regression.
18. Ryan authorized the plan-only post-bundle authority-packet reconciliation;
    Kiro passed parent `67de0d7` and overlay `fc5289a`. Ryan granted their exact
    application, the two-file/four-literal correction and final evidence. The
    resulting clean pushed candidate is `PRESERVED_M11_MERGE_READY_SHA`.
    Codex established the governed differential, unchanged current-main Pylint
    gate, two fresh M8 PASSes, seven MCP regression PASSes and durable-evidence
    verification; Kiro exact-tip conformance review passed.
19. Ryan delegated the merge-readiness decision to Codex. A fresh fetch found
    `origin/main` at `CURRENT_MAIN_BASELINE_SHA`, twelve commits beyond the
    historical integration baseline. The reviewed candidate and current main
    both change the governed STATUS document, and `git merge-tree` reports a
    real content conflict. No PR existed. Codex issued `PAUSE` rather than
    rebasing, resolving the conflict, transferring old evidence, or merging.
20. Ryan authorized this plan-only current-main reconciliation. Kiro must
    review this exact new parent/overlay. Ryan may then grant only creation of
    the new branch from `CURRENT_MAIN_BASELINE_SHA`, the three held commits and
    the fresh current-main evidence defined in M11. Silence, an earlier grant
    or any old `CONTINUE` is not authorization.
21. Kiro passed that plan and Ryan granted the exact reconstruction. Grok made
    the held 120-path product, four-blob control-plane and six-literal identity
    commits; Codex independently verified exact composition. The clean pushed
    result is `PRESERVED_M11_CURRENT_MAIN_PAUSE_SHA`.
22. Complete pytest at current main and the reconstructed candidate finished
    under identical conditions. All 2,686 current-main nodes were retained;
    238 additional Switchboard nodes were observed, 160 passed and 78 failed.
    Every one of those 238 nodes already exists in
    `PRESERVED_M11_MERGE_READY_SHA` with the same outcome. Because §18.14
    nevertheless required every candidate-only node to pass or skip, Codex
    sealed `CURRENT_MAIN_DIFFERENTIAL_PASS=false`, preserved the comparison and
    PAUSE ledger hashes, and ran no Pylint/M8/MCP evidence. Ryan authorized only
    that plan correction.
23. Kiro passed semantic parent `300180f7` and overlay `05e0d797`; Ryan granted
    the exact plan/rebind/evidence sequence. The held plan and four-literal
    commits were independently verified and preserved at
    `PRESERVED_M11_THREE_TIP_PREFLIGHT_SHA`; the runtime rebind also passed.
    Before a suite or evidence slot existed, the mandatory check found
    `origin/main=5c6a4a8` rather than the grant-frozen `a92a74e`. Codex issued
    `PAUSE`; no pytest, Pylint, M8 or MCP process ran.
24. Kiro passed the advanced-current-main plan and Ryan granted it. The new
    branch was reconstructed in three held commits, independently verified,
    pushed and preserved at `PRESERVED_M11_INNER_ROLE_PAUSE_SHA`. Three complete
    pytest runs and all 166 isolated reruns completed; the finalizer then issued
    `PAUSE` on unstable pytest `os.environ` rendering for exactly 22 unchanged
    inner-role assertion failures. Pylint, M8 and MCP did not run.
25. Ryan authorized only this plan-only inner-role signature correction. Kiro
    exact-tip review and a new resume grant remain mandatory before plan
    application, the four-literal rebind or any fresh evidence operation.

## 1. State ledger

| State | Items |
|---|---|
| **Specified** | Parent Architecture §§4, 6–15, 17–18.17 and Execution §§2–10.15; strict reader and T0–T5 cases 1–58; all completed M11 controls; exact advanced-current-main reconstruction; closed 22-node inner-role semantic signature; and unchanged three-tip, static, M8, MCP and merge-decision gates. |
| **Implemented** | Bounded implementation is accepted at `8010fb060c2edc29e1b09d7a30b1a1da2689d489`. The reviewed M11 candidate is preserved at `PRESERVED_M11_MERGE_READY_SHA`; prior reconciliation tips remain immutable; the advanced-main candidate is preserved, clean and pushed at `PRESERVED_M11_INNER_ROLE_PAUSE_SHA`. No inner-role reconciliation plan or identity edit has been applied to it. |
| **Tested** | Historical M0–M8 Gate B/C and preserved M11 evidence passed. Fresh advanced-main `N1`/`R`/candidate pytest collected 2,702/2,912/2,940 nodes and all 166 symmetric rerun processes completed. The exact 238-node partition and five-node R2b proof held; the finalizer paused on 44 raw signature mismatches across the exact 22-node inner-role family. `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS=false`; Pylint/M8/MCP did not run. |
| **Assumed** | No unavailable runtime or host capability is assumed. The historical runtime tree hash is `sha256:74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`; reuse requires Codex to rebind and independently inventory it at `PROPOSED_RUNTIME_PREFIX` under a new Ryan grant. |
| **Unresolved** | Kiro exact-tip review and a new Ryan resume grant block the reviewed-plan application onto `PRESERVED_M11_INNER_ROLE_PAUSE_SHA`, exact four-literal rebind and fresh `N1`/`R`/final-candidate evidence under the closed 22-node rule. Ryan must separately decide whether to create a PR and merge only after that evidence and a final Kiro PASS, with `origin/main` still exact. Later blockers remain Gate D authentication/distribution/containment and current OpenClaw qualification; Gate W production admission; Gate D-V; Gate E; Gate F/capture; watch activation; live data, deployment and promotion. None becomes Grok work. |

## 2. Dependency order

```text
M0 baseline/runtime input
  → M1 T0a isolated runner and production refusal
  → M2 T0b schemas, vectors, inventories, and independent oracles
  → M3 T1–T2 scope/state/authority/publication
  → M4 T3 read-only CLI/MCP
  → mandatory Gate B review hold
  → M5 T4 uninstalled connector
  → mandatory T4 hold
  → M6 T5 fake controller/manager/supervisor
  → M7 bounded evidence package
  → M8 final isolated adversarial runs and bounded TEST PASS [accepted]
  → M11a current-main plan reconciliation, review and Ryan grant [complete]
  → M11b exact replay and pin/comment reconciliation [preserved at a11b7a2]
  → M11c pre-test allowlist PAUSE [observed; no test ran]
  → M11d reviewed-plan correction, M8/MCP PASS, Pylint PAUSE [9c6421a]
  → M11e revision-safe Pylint plan correction and exact-tip Kiro PASS
  → M11f 44-path remediation and unchanged Pylint PASS [3f8ef83]
  → M11g applicability plan applied; first differential PAUSE [853ef98]
  → M11h path/identity reconciliation applied; differential/Pylint PASS [7f2a2e2]
  → M11i final M8 packet PAUSE before fixture/runtime use [7f2a2e2]
  → M11j two-file/four-literal packet reconciliation applied [d7b1592]
  → M11k differential/Pylint PASS; final M8 run 1 schema-literal PAUSE [d7b1592]
  → M11l one-file/one-literal publisher correction applied [851edbe4]
  → M11m differential/Pylint PASS; final M8 run 1 packet PAUSE [851edbe4]
  → M11n post-bundle packet correction and all final evidence PASS [cd60cf19]
  → M11o current-main drift audit and merge PAUSE [a92a74e]
  → M11p exact-current-main reconstruction [30bc134d]
  → M11q complete current-main differential applicability PAUSE [30bc134d]
  → M11r three-tip correction and held plan/rebind [d276cb4]
  → M11s three-tip evidence preflight PAUSE on main advance [5c6a4a8]
  → M11t advanced-current-main reconstruction [776a4ca3]
  → M11u complete three-tip runs/reruns; inner-role signature PAUSE [776a4ca3]
  → M11v plan-only closed signature correction and Kiro hold
  → Ryan exact inner-role resume grant
  → reviewed plan range onto 776a4ca3; held four-literal rebind
  → fresh N1/R/final-candidate differential with closed 22-node proof
  → unchanged Pylint
  → two fresh M8 runs; seven MCP files; integration review
  → Ryan PR/merge decision only while origin/main == 5c6a4a8

M8 → M9 Gate W ─┐
M8 → M9 Gate D ─┼→ M10 Gate D-V, then Gate E → M11 complete review
                └─ W and D remain independent, separately reviewed/granted
```

M0–M8 are accepted historical scope; they are neither reopened nor promoted to
the integration baseline. M9, M10, watch coverage, and complete-system review
remain decision gates, not Grok work. The only possible next implementation is
M11v under a new grant after Kiro PASS on this exact plan. Grok applies only the
grant-named reviewed plan range onto `PRESERVED_M11_INNER_ROLE_PAUSE_SHA`, then
makes only the held two-file/four-literal parent/overlay rebind after Codex's
commit-specific `CONTINUE`. Codex independently proves each boundary and owns
the fresh `N1`/`R`/final-candidate
differential, Pylint, two M8 runs, seven MCP regressions and
durable evidence. Ryan alone decides PR creation and merge, and only while a
fresh `origin/main` still equals `CURRENT_MAIN_BASELINE_SHA`. No earlier grant,
evidence result, branch, plan range, or `CONTINUE` can be reused.

## 3. Milestones

### M0 — Current-state audit and frozen baseline

1. **Name and purpose:** Establish exact, reproducible starting bytes.
2. **Architectural outcome:** The accepted implementation was based on
   `ORIGINAL_CODE_BASELINE_SHA`
   and governed by `SEMANTIC_PARENT_SHA`; no silent rebase, ambient state, or
   branch helper that silently substitutes `origin/main`.
3. **Affected surfaces:** Git worktree/branch, supplied runtime prefix, and
   read-only inventories only; no product file changes.
4. **Preconditions/dependencies:** Kiro PASS on this exact overlay/parent;
   Ryan's exact T0–T5 grant; a branch Codex created at
   `ORIGINAL_CODE_BASELINE_SHA`; clean
   dedicated worktree; and the exact parent-frozen runtime supplied by Ryan or
   the one provisioning operator explicitly named in Ryan's grant; and one
   durable evidence location designated by Ryan for reviews and M7/M8 output.
5. **Implementation tasks:** Codex creates and pushes the implementation branch
   from `ORIGINAL_CODE_BASELINE_SHA` without using
   `convmem work start`, because that helper branches from current
   `origin/main`. Codex copies the cited parent-review reports to the designated
   durable location and verifies their recorded hashes. From the shared
   checkout, Grok runs exactly
   `convmem work resume <branch> --worktree` to enter that pre-created branch;
   it must not use the default resume mode or switch the live checkout. Record
   base/tip/upstream; install repo-local Git settings;
   inventory tracked files, dependency versions, Ryan-supplied runtime bytes,
   protected bytes, and the parent-defined allowlist. Grok does not provision,
   download, install, or repair runtime dependencies.
6. **Tests/evidence:** `git status --short`, exact base/merge-base/tree checks,
   explicit upstream/refspec, source/runtime manifests, exact CPython/Unicode/
   Node/MCP/idna versions, protected-byte/mode comparison, and dependency
   inventory.
7. **Invariants:** No live data/config access; no OpenClaw process; no edit on
   `main`; never check out the implementation branch in
   `/home/lauer/Projects/convmem`; semantic parent remains exact.
8. **Forbidden changes:** Fetch-derived baseline substitution, rebase, schema,
   config, credential, persistent-state, permission, dependency, or host
   runtime mutation.
9. **Done:** Clean implementation branch at the exact baseline with recorded
   inventories, supplied exact runtime, designated durable evidence location,
   and zero implementation diff.
10. **Ryan confirmation:** Yes for the exact T0–T5 grant and for runtime
    provisioning. No routine reapproval after those exact grants unless a
    stop condition or governing SHA change occurs.
11. **Live inspection:** Codex checks branch/base/worktree, status, diff,
    tracked and runtime inventories, dependencies, grant text, provisioner
    identity, and protected-byte report; then cites the pushed M0 commit in a
    written `CONTINUE`.
12. **Verdict:** Separate ConvMem verdict; OpenClaw is not run.

### M1 — T0a isolated runner and fail-closed production refusal

1. **Name and purpose:** Build physical containment first and prove every
   bypass fails before importing integration code.
2. **Architectural outcome:** The only acceptance entrypoint is the parent's
   closed `run_isolated.py`; production fake/controller/supervisor/plugin
   selection refuses before OS action.
3. **Affected surfaces:** Test-only fixture-manifest schema,
   `tests/fixtures/openclaw_strict/run_isolated.py`, production-refusal seams
   in the parent-listed controller/supervisor/connector paths, and the exact
   strict/connector test paths named by Execution §5.1.
4. **Preconditions/dependencies:** M0 `CONTINUE`; exact runtime prefix and
   grants present; no integration module has been imported or executed.
5. **Implementation tasks:** Implement the exact four-argument runner,
   runtime/component preflight, fixed mounts/namespaces/environment/FD closure,
   source allowlist, pre-import sentinel, capacity bounds, and all T0a negative
   mutants. Create every fixed strict and connector test path at T0a as a
   collection-safe, test-first assertion file: no placeholder success, skip,
   or xfail is allowed. Later-T tests must be red only because their frozen
   capability is absent, never because a file is missing or collection fails.
6. **Tests/evidence:** Run only the exact runner CLI with
   `--plan-sha SEMANTIC_PARENT_SHA`. At this checkpoint the
   overall suite is expected red; case 57's pre-import/containment portion and
   every runner bypass mutant must be green before the declared future-T reds.
   Evidence includes import/process/network/FD/mount traces proving no strict
   integration import occurred before preflight.
7. **Invariants:** No integration code is imported or run outside
   `run_isolated.py`; no host fallback; no missing runtime byte is installed;
   no overall TEST claim is made.
8. **Forbidden changes:** Subset mode, arbitrary command/mount/suite,
   permissive fallback, host `/usr`, host test execution called acceptance,
   stub implementation, real gateway/model/provider, or production fake.
9. **Done:** All T0a controls pass inside the unchanged closed runner; every
   remaining red is mapped to a later T step; the pushed commit has Codex
   `CONTINUE`. Bounded TEST remains NOT YET RUN/PASS.
10. **Ryan confirmation:** No within the exact grants; yes for runtime/host
    provisioning, another runner interface, or any production selection.
11. **Live inspection:** Codex checks the pushed commit, full diff/file list,
    every command Grok ran outside the runner, raw runner output, import
    sentinel, mounts, dependencies, permissions, and the declared red map.
12. **Verdict:** ConvMem containment/refusal verdict only; no OpenClaw verdict.

### M2 — T0b ConvMem preservation and closed integration contract

1. **Name and purpose:** Encode the frozen schemas, bytes, inventories, and
   independent oracles without changing legacy ConvMem semantics.
2. **Architectural outcome:** Closed schemas/vectors, mandatory IDNA runtime,
   five component inventories, legacy-byte preservation, and independently
   recomputed hashes exist before T1 code.
3. **Affected surfaces:** Exact Gate B/C schemas in parent Execution §2;
   mandatory `requirements.txt` line `idna==3.18` if absent;
   `tests/fixtures/openclaw_strict/**`; and the fixed test-first files.
4. **Preconditions/dependencies:** M1 `CONTINUE`; exact parent schema and
   component sets copied without inference.
5. **Implementation tasks:** Implement schema validators, protocol fixtures,
   known-answer hashes/IDs, two independent canonical parsers, five reference-
   owned component walkers, legacy envelope preservation, and disposable-copy
   mutation controls. The `idna==3.18` pin is required, never optional, and is
   included in every parent-defined component digest that contains it.
6. **Tests/evidence:** T0b oracle tests and case 58's artifact/membership
   portions that are executable before T1; duplicate/unknown/reordered/
   wrong-type/missing-null rejection; exact legacy bytes; included/excluded
   mutation behavior; omitted-`canonical_json.py` mutant. Overall runner may
   remain red only for declared T1–T5 tests; no whole-case-58 PASS is claimed.
7. **Invariants:** Legacy IDs, envelope UUIDs, provenance bytes, approval,
   signing, durable admission, backups, recovery, and existing CLI behavior
   remain unchanged.
8. **Forbidden changes:** Optional IDNA pin, protected helper edit, automatic
   migration/ingestion/redistillation, inferred consent, new issuer/resolver,
   or Chroma-as-authority.
9. **Done:** T0b references agree; deliberate schema/inventory/hash mutants
   fail; only declared future-T tests remain red; pushed commit receives Codex
   `CONTINUE`. No bounded TEST PASS is claimed.
10. **Ryan confirmation:** No within exact T0–T5; yes for any different
    dependency, schema, component membership, data model, trust, signing,
    approval, or provenance behavior.
11. **Live inspection:** Codex checks commit/diff/files, required IDNA delta,
    schema inventory, known answers, independent arrays, negative controls,
    raw runner output, and every outside-runner command.
12. **Verdict:** ConvMem contract verdict.

### M3 — T1–T2 data flow, state, authority, publication, and failure

1. **Name and purpose:** Implement the frozen T1–T2 authority/state machine.
2. **Architectural outcome:** Full-bound canonical reduction, conserved
   authority, immutable publication, fail-closed recovery, and display-only
   query filtering.
3. **Affected surfaces:** `bound_read_scope.py`, `strict_grounding.py`,
   `strict_evidence_state.py`, `strict_projection_publisher.py`,
   `strict_projection.py`, their schemas and named tests.
4. **Preconditions/dependencies:** M2 `CONTINUE`; exact issuer/source
   inventories and identity algorithms frozen.
5. **Implementation tasks:** Implement enrollment/genesis, strict identities,
   original-admission qualification, cumulative authority, fence→intent→head
   advance→cold build→publication order, full publication CAS, deterministic
   state, rollback/rebuild/recovery, and persisted expiry. For the parent's
   “retire first” rule, the fixture publisher treats external retirement and
   exact empty-domain proof as preconditions; its CLI refuses a nonempty or
   unknown slot and does not invent a manager/platform capability. T5 later
   supplies only the parent-fixed fake retirement port.
6. **Tests/evidence:** Only T1/T2-owning portions of parent cases 5–27,
   41–44, 49, 51–52, 55, and 57; fault injection at every write/fsync/rename/
   pointer boundary; two fresh roots; independent reducer/qualifier results.
   Reader/server portions remain red until M4 and no whole-case PASS is claimed
   when a case has a later layer.
7. **Invariants:** Revocation/supersession permanent; late evidence cannot
   upgrade admission; rollback never restores authority or renews lifetime;
   ambiguity is unavailable/quarantined.
8. **Forbidden changes:** Query-time reducer, implicit add, authority rollback,
   generation-only CAS, self-authentication, mutable/global store, any
   redistillation, or a publisher-owned retirement mechanism.
9. **Done:** T1/T2 rows and negative controls pass inside the runner;
   crash/retry/recovery is deterministic; only declared T3–T5 rows remain red;
   pushed commit receives Codex `CONTINUE`. No overall TEST PASS is claimed.
10. **Ryan confirmation:** No for exact fixture implementation; yes for any
    persistent format/migration or rollback/recovery semantic change.
11. **Live inspection:** Codex checks pushed commit/diff/files, state/schema
    writes inside disposable roots, fault output, CAS/retry evidence, retirement
    refusal, permissions, raw runner output, and outside-runner commands.
12. **Verdict:** ConvMem verdict.

### M4 — T3 read-only CLI/MCP and Gate B review hold

1. **Name and purpose:** Finish Gate B before any connector/control work and
   hold for an exact-commit conformance review.
2. **Architectural outcome:** The file CLI and strict server expose exactly
   `search`, `unresolved`, and `related`, zero resources/templates, immutable
   operator-owned audience, and untrusted raw evidence; OpenClaw remains absent.
3. **Affected surfaces:** `strict_projection.py`,
   `openclaw_strict_server.py`, reject-only `mcp_server.py`, Gate B schemas,
   fixture paths, and Gate B strict tests. No connector/controller/supervisor
   behavior is implemented here beyond M1 production refusal.
4. **Preconditions/dependencies:** M3 `CONTINUE`; all T0–T2 evidence present;
   Ryan's refusal-contract ruling and this overlay are exact grant inputs.
5. **Implementation tasks:** Implement the exact lexical reader/direct file
   CLI, selector-only display, public opening, three strict methods, v3 result/
   error serialization, and zero resources. Preserve baseline profile parsing's
   `(value or "").strip().lower()` normalization: normalized empty/`full` is
   full, `shell` is shell, `openclaw-strict` refuses legacy entry with the
   dedicated-entrypoint instruction, and every other normalized nonempty value
   terminates before registration. Exact stderr bytes and numeric status remain
   noncontractual under Ryan's ruling; Grok must not turn its chosen
   presentation into a test-derived contract.
6. **Tests/evidence:** Gate B's cases 1–27, 40–44, 49–52, strict-server portion
   47, private/public portion 55, and Gate B portions 57–58, separated by layer.
   The unchanged `--suite all` runner may still be red only for declared T4/T5
   files; all Gate B rows and mutants must be green in two fresh roots.
7. **Invariants:** Legacy full/shell behavior stays byte-compatible; reads do
   not mutate mtimes/cache/files; no OpenClaw, writer, publisher import in the
   public reader, or governance authority is exposed.
8. **Forbidden changes:** Connector aliases, OpenClaw plugin/config, native
   memory, `ask`, global search, dynamic dispatch, ACP/subagents/channels,
   credentials, real inference, or any T4/T5 implementation before review.
9. **Done:** Gate B evidence is green at one pushed commit; the profile tests
   prove nonzero exit, empty stdout, zero registration/start/effect, no raw-
   value disclosure, and the semantic dedicated-entrypoint instruction; and
   Codex issues a written Gate B `CONTINUE` citing that commit. This is a Gate
   B review PASS, not final bounded TEST PASS.
10. **Ryan confirmation:** No routine reapproval inside the exact grant. Any
    contract/profile/permission change pauses for Codex/Kiro and requires a new
    Ryan grant if a governing SHA or scope changes.
11. **Live inspection:** Codex inspects the complete Gate B diff/commit/push,
    profile and tool/resource enumeration, legacy behavior, raw runner output,
    dependencies, schemas/data, permissions, protected bytes, deviations, and
    all commands outside the runner. Grok must stop until written `CONTINUE`.
12. **Verdict:** ConvMem Gate B verdict; no real or fake OpenClaw verdict.

### M5 — T4 uninstalled connector checkpoint

1. **Name and purpose:** Implement only the connector after Gate B review and
   stop before lifecycle/controller work.
2. **Architectural outcome:** Three fixed aliases use an injected test
   transport, validate the exact launch tuple, and wrap raw evidence as
   untrusted data. No OpenClaw process or registration exists.
3. **Affected surfaces:** Only
   `integrations/openclaw-convmem-reader/{package.json,openclaw.plugin.json,index.js,test/connector.test.mjs}`
   and parent-listed connector tests/fixtures.
4. **Preconditions/dependencies:** Written Codex Gate B `CONTINUE` citing the
   exact pushed M4 commit.
5. **Implementation tasks:** Implement fixed alias mapping, exact launch-tuple
   validation, injected `spawn`, bounded framing/queue/deadline, cancellation,
   partial-frame/late-success denial, and production registration refusal;
   commit, push, and stop.
6. **Tests/evidence:** Only Gate C connector portions of cases 2, 33, 35, 48,
   57, and 58; one active plus eight pending; ninth denial; exact frames and
   fixed response; no automatic retry after uncertain delivery; no real child.
7. **Invariants:** Retrieved content has no instruction authority; immutable
   audience and three aliases cannot widen; exact explicit authority-operation
   retries retain parent case 43/49 semantics outside the connector.
8. **Forbidden changes:** Dynamic dispatch/path/argv, real registration,
   gateway/model/provider/filter, native memory, credentials, ACP, subagents,
   channels, remote inference, or controller/supervisor implementation.
9. **Done:** Assigned T4 rows are green at one clean pushed commit and Codex
   issues commit-tied `CONTINUE`. No final TEST PASS or OpenClaw-runtime claim.
10. **Ryan confirmation:** No routine reapproval inside the exact T4 grant;
    yes for any real process, permission, registration, interface, or limit
    change.
11. **Live inspection:** Codex inspects connector diff/files/manifest/API,
    commit/push, runner output, injected spawn trace, dependencies, permissions,
    outside-runner commands, and unsupported claims. Grok stops at this hold.
12. **Verdict:** Connector/protocol-fake and bounded integration verdicts only.

### M6 — T5 fake lifecycle, concurrency, rollback, and recovery

1. **Name and purpose:** Implement and falsify the controller/manager/
   supervisor protocol cores after the T4 hold.
2. **Architectural outcome:** Stable-slot lifecycle, peer policy, lock order,
   turns, release/revoke, retirement, quarantine, and recovery operate only
   through the parent-fixed `FixturePlatform` ports.
3. **Affected surfaces:** `openclaw_activation_controller.py`,
   `openclaw_activation_supervisor.py`, their schemas/tests, and fixed fixture
   event scripts. Earlier Gate B/T4 files change only to correct a proven defect.
4. **Preconditions/dependencies:** Written Codex `CONTINUE` citing the exact
   pushed M5/T4 commit.
5. **Implementation tasks:** Implement one-turn/no-turn-queue state, stable
   identities, peer/access validation, clocks/boots, watchdog/deadlines,
   release/revoke, independent manager observation, retirement/quarantine, and
   scripted concurrency/crash/restart/rollback events; commit, push, and stop.
6. **Tests/evidence:** Gate C fake-process portions of cases 33, 35, 45–46,
   53–54, pre-activation 55, and lifecycle/production-refusal portions 57–58;
   deterministic traces for blocked consumers, detached descendants, stale
   receipts, partial independent removal, clock/boot changes, and teardown.
7. **Invariants:** Supervisor cannot attest emptiness; only exact-invocation
   terminal+empty manager observation permits retirement; rollback is serving-
   only and never renews expiry; uncertain teardown retains the exact root.
8. **Forbidden changes:** Real users/services/sockets/mounts/filters, cleanup-
   as-proof, automatic rerun, lock widening, old-head/expiry restoration,
   production fake selection, destructive recovery, or implicit add.
9. **Done:** Assigned T5 rows/races are green in two fresh roots at one clean
   pushed commit and Codex issues commit-tied `CONTINUE`. No final TEST PASS or
   real containment/authentication verdict.
10. **Ryan confirmation:** No routine reapproval inside exact T5; yes to change
    rollback/recovery, persistence, limits, permission, or production behavior.
11. **Live inspection:** Codex checks lifecycle diff/files, commit/push, raw
    runner output, seeds/events/traces, retained state, schemas, permissions,
    process/network/FD proof, outside-runner commands, and success claims.
12. **Verdict:** ConvMem interaction plus connector/protocol-fake integration
    verdict; real-runtime verdict deferred.

### M7 — Observability and audit trails

1. **Name and purpose:** Make every bounded result attributable and reviewable.
2. **Architectural outcome:** Evidence binds plan SHA, implementation SHA,
   source/runtime/component hashes, selected tests, process trace, and outcome
   without creating a new authority source.
3. **Affected surfaces:** Tracked fixture inputs/helpers remain only in their
   parent-defined manifest paths. Generated results exist only under disposable
   `/fixture/evidence` and the fixed outer collection root
   `/tmp/convmem-openclaw-evidence/<source-commit>/<run-label>/`; `/tmp` is
   staging only. Codex owns evidence collection and copies exact hashed results
   to the Ryan-designated durable review location. Neither location is a
   tracked source/component/fixture-hash member. No production telemetry or
   live ledger write.
4. **Preconditions/dependencies:** M6 `CONTINUE`; clean pushed implementation
   commit; exact source and semantic-parent SHAs.
5. **Implementation tasks:** Emit canonical inventories, labels `STATIC`,
   `FAKE`, `DISPOSABLE_KERNEL`, or `REAL`, exact skips/exclusions, timing,
   output, tmp usage, negative controls, and changed-file/protected-byte proof.
   Codex collects only the predeclared outputs and records the staging-to-
   durable byte/hash mapping; Grok cannot select a different destination.
6. **Tests/evidence:** Dry-collect the bounded evidence from the runner without
   changing its suite selection; independently compare canonical arrays and
   prove generated paths are absent from source/component/fixture hashes, no
   full discovery occurs, tool inventory is exact, and reads do not mutate
   mtime/cache/files. Compare staging and durable evidence byte-for-byte before
   staging can disappear. This milestone does not claim final reproduction PASS.
7. **Invariants:** Audit evidence is not approval, signing, admission,
   qualification, manager emptiness, or promotion.
8. **Forbidden changes:** Live telemetry, secrets, private paths, fabricated
   provenance, omitted failures, volatile-only handoff evidence, unsupported
   “all 58 passed” claim.
9. **Done:** Evidence locations and mappings are deterministic and excluded
   from all governed hashes; exact evidence is durable with a verified staging
   hash mapping; pushed M7 commit receives Codex `CONTINUE`. Final reproduction
   and TEST verdict remain M8.
10. **Ryan confirmation:** No for fixture evidence; yes for any persistent/live
    audit store, telemetry, external sink, or ledger mutation.
11. **Live inspection:** Codex checks commit/diff/files, raw outputs, labels,
    hashes, locations, exclusions, four fixed deselections, capacity, new
    dependencies, outside-runner commands, and claim/evidence mapping.
12. **Verdict:** Separate ConvMem and connector/protocol-fake evidence verdicts,
    plus integration evidence verdict; no OpenClaw runtime verdict.

### M8 — Adversarial testing

1. **Name and purpose:** Run the one final bounded acceptance entrypoint and
   attack every assigned trust/failure boundary before conformance review.
2. **Architectural outcome:** Parent cases 1–58 are reported by owning gate;
   fixture success cannot stand in for blocked real/live gates.
3. **Affected surfaces:** Only
   `tests/fixtures/openclaw_strict/{constants.py,suites.py,run_isolated.py,audit_evidence.py,adversarial_matrix.py}`
   as needed for the parent-fixed report/validation path, plus the single
   existing semantic-parent literal assertion in
   `tests/test_openclaw_strict_packet_contract.py`. Generated output is only
   `/fixture/evidence/{pytest-strict-junit.xml,pytest-legacy-junit.xml,pytest-node-outcomes.json}`.
4. **Preconditions/dependencies:** M7 and the completed M8 correction are
   accepted at clean pushed `8010fb060c2edc29e1b09d7a30b1a1da2689d489`.
   M11 reconstruction must preserve this runner and evidence contract exactly;
   it does not reopen M8 implementation.
5. **Implementation tasks:** Completed at the accepted tip: mechanically repin `SEMANTIC_PARENT_SHA` and its
   existing assertion; add exactly the parent §5.1 xunit1/JUnit arguments to
   the two existing Python argv arrays; parse the two reports after the same
   processes finish; enforce every parent reconstruction/outcome/count rule;
   emit the exact canonical report; keep any AST inventory diagnostic-only;
   and leave the Node argv byte-identical. No selected test logic or file list
   changes. Commit, push, stop for Codex inspection, then—only after a
   commit-specific `CONTINUE`—run the parent §5.1 entrypoint with
   `--source-commit` equal to that clean correction SHA,
   `--plan-sha SEMANTIC_PARENT_SHA`, the unchanged supplied
   runtime, and `--suite all`. Do not modify code between reproductions.
6. **Tests/evidence:** Two fresh-root green runs of the exact three commands;
   raw stdout/stderr/status; both raw JUnit files; canonical exact strict and
   legacy node/outcome arrays; identical arrays across runs; 238 strict passes,
   29 Node passes, 115 legacy passes, one legacy skip and four fixed
   deselections; capacity/process/import/mount/FD/network evidence; exact
   input/expected/evidence triples; failed mutants; protected-byte/allowed-file
   report; and explicit Gate B/C case ownership. Never claim all 58 cases
   passed. AST definitions are not collected-node evidence.
7. **Invariants:** Leakage-safe fixtures; no credentials/live data; no broadened
   test selection, permissions, or scope to make tests pass.
8. **Forbidden changes:** Any new test/test-logic edit beyond the mechanical
   parent-SHA assertion, selector or deselection change, collect-only/extra
   process, conftest/environment injection, plugin/dependency, permission or
   runtime change, report outside `/fixture/evidence`, AST-derived collected
   claim, skip, mocked-success denial, implementation-derived expected value,
   or host execution called acceptance.
9. **Done:** **Accepted at `8010fb0`.** The correction diff stays inside field 3; every parent JUnit/parser
   negative rejects; every assigned Gate B/C row passes twice at the same clean
   commit; both canonical arrays are exact and identical; fixed behavioral
   counts remain unchanged; all mutants fail; Codex issues commit-tied
   `CONTINUE`; and bounded `TEST PASS` is claimed here exactly once. Any other
   result is BLOCKED with retained evidence; out-of-scope rows remain explicitly
   untested/blocked.
10. **Ryan confirmation:** Historical M8 confirmation and acceptance are
    complete. A new exact M11 grant is required before reconstruction or fresh
    runs on the integration baseline. Frozen disposable reruns under that grant
    need no per-run approval; live, destructive, costly, irreversible or
    permission-changing tests still require Ryan.
11. **Live inspection:** Codex first checks the full correction diff, exact
    argv arrays, old/new SHA pin, unchanged test logic/selectors/deselections/
    Node argv/dependencies/permissions/runtime, generated paths and parser
    failure rules. After `CONTINUE`, Codex checks the exact command/source SHA,
    both raw JUnit files, canonical arrays/counts/outcomes, raw outputs/statuses,
    two roots, negative failures, fixture/runtime/component hashes, resource
    bounds, changed files, commits/push, outside-runner commands, deviations,
    and unsupported claims.
12. **Verdict:** Separate ConvMem Gate B, connector/protocol-fake Gate C, and
    bounded integration verdicts; no OpenClaw runtime verdict.

### M9 — Blocked post-fixture gates: governed writes and real runtime

1. **Name and purpose:** Keep Gate W memory governance and Gate D real-runtime
   qualification as separate, independently authorized outcomes after bounded
   T0–T5. They share one milestone only because neither is executable work in
   this overlay; neither gate can satisfy or authorize the other.
2. **Architectural outcome:** Gate W, if later granted, admits governed memory
   only through an independently reviewed ConvMem CLI. Gate D, if later granted,
   proves actual OpenClaw authentication, containment, distribution, manager
   ownership, mounts, peers, and local inference without authority transfer.
3. **Affected surfaces:** **UNRESOLVED.** Gate W owns later schemas and
   `governed_admission.py`. Gate D owns actual adapters, package/image,
   service/unit, socket, filter, UID/GID, model/provider, and config paths.
   Exact paths must be named in separate future packets.
4. **Preconditions/dependencies:** M8 bounded Gate B/C PASS. Each subgate then
   requires its own architecture/execution packet, adversarial/design reviews,
   and exact Ryan grant. A PASS for one is not a precondition waiver for the
   other.
5. **Implementation tasks:** **BLOCKED.** Gate W's packet must bind eligibility,
   unitization, proposal, approval, signing, provenance, explicit admission,
   recovery, retrieval, and rejection to existing authorities. Gate D's packet
   must resolve C-RUNTIME/D-CONTAINMENT/D-DISTRIBUTION and exact authentication,
   package, manager, provider, and permission bytes. Grok must infer neither.
6. **Tests/evidence:** Gate W owns case 56 plus 41–44, 49, 51–52 through the
   real governed CLI on disposable stores; unauthorized/self-approved/poisoned
   writes fail. Gate D repeats cases 1–4 and owns real portions 28–36, 38–39,
   45–47, 53–55; prove real isolation, authentication, empty-domain retirement,
   and no ambient credential/tool access.
7. **Invariants:** Agents propose; Ryan locks. Approval, admission, durable
   storage, projection, and publication stay separate. ConvMem remains source
   of truth; runtime sees only committed public projection; evidence text has
   no instruction authority.
8. **Forbidden changes:** Autonomous writes, self-approval, silent migration,
   automatic ingestion/redistillation, inferred authorization, live data,
   dummy credentials, shared host inference, permissive mounts, unbounded
   tools/network, fake-derived qualification, or autonomous external acts.
9. **Done:** Not reachable in this revision. Gate W and Gate D each need their
   own reviewed packet, grant, evidence, and separately reported PASS. Neither
   is implemented, tested, or authorized here.
10. **Ryan confirmation:** Mandatory before either design lock/implementation;
    before persistence/migration/admission for W; and before every permission,
    tool, service, user, socket, mount, network, model/provider, package, or
    external configuration for D.
11. **Live inspection:** Future supervisors separately inspect every W data-
    model/trust/writer/migration/provenance/persistence change and every D
    privilege/config/package/process/mount/network/peer boundary. Evidence and
    statuses may not be combined.
12. **Verdict:** Separate ConvMem Gate W verdict; separate OpenClaw Gate D and
    integration verdicts. No cross-gate PASS inference.

### M10 — Limited web-development pilot (Gate D-V then Gate E)

1. **Name and purpose:** Measure whether the integrated system improves a
   bounded web-development task without weakening governance.
2. **Architectural outcome:** A leakage-safe, pre-registered comparison binds
   episode, target, probe, trace, action, and outcome identities. Capture is
   recorded as disabled; no capture identity is minted through Gate E.
3. **Affected surfaces:** **UNRESOLVED** pilot corpus, tasks, scoring rubric,
   trace store, target site, and isolated runtime packet. Capture policy is not
   an M10 surface; transcript capture/automatic indexing remain disabled.
4. **Preconditions/dependencies:** M9 Gate D PASS; a separately reviewed Gate
   D-V methodology; and a Ryan grant for exactly eight predeclared tasks, two
   fresh repetitions, and two arms (32 runs). Gate E additionally requires a
   positive Gate D-V result, unconditional M9 Gate W PASS, its own reviewed
   packet, and a separate Ryan grant.
5. **Implementation tasks:** **BLOCKED.** A future Gate D-V packet must freeze
   the eight tasks, two repetitions, two arms, baseline/control, measures,
   leakage controls, identities, rollback, and stop rules. A later Gate E
   packet may select only the parent-authorized limited web-development pilot
   after Gate W; it may not enable capture.
6. **Tests/evidence:** Exactly 32 Gate D-V runs with predeclared quality,
   substance, technical, continuity, context-transfer, rework, and safety
   outcomes; blinded/independent scoring; complete traces. Gate E separately
   requires the parent-defined live evidence and rollback proof.
7. **Invariants:** No production target by default; no automatic capture/write;
   no cross-arm leakage; no outcome-based identity rebinding or scope drift.
8. **Forbidden changes:** Expanding beyond web development, live deployment,
   consequential external action, post-hoc metric changes, promotion by result.
9. **Done:** Not reachable until the exact Gate D-V 32-run packet passes, Gate W
   passes, the Gate E packet is reviewed, and Ryan grants exact target/actions;
   pilot PASS is not promotion.
10. **Ryan confirmation:** Mandatory for methodology, target, external actions,
    live data, and every irreversible step. Gate W separately governs writes;
    Gate F separately governs any later capture proposal.
11. **Live inspection:** Future supervisor checks pre-registration, identities,
    target/action allowlist, trace, leakage controls, rollback, and outcomes.
12. **Verdict:** Separate OpenClaw runtime, ConvMem governance, and integration-
    value verdicts. Capture remains a later Gate F question.

### M11 — Final conformance review and documentation

1. **Name and purpose:** Reconcile one exact 22-node inner-role failure-signature
   family without rewriting raw evidence, widening normalization, hiding
   retained failures or changing any product/test behavior.
2. **Architectural outcome:** All earlier evidence branches remain immutable.
   The completed advanced-main candidate stays preserved at
   `PRESERVED_M11_INNER_ROLE_PAUSE_SHA`. Fresh evidence partitions node
   authority across advanced current main `N1`, preserved candidate `R`, and
   final candidate `F`, while Architecture §18.17 supplies a closed semantic
   signature only for the exact 22-node family. Every raw failure remains debt.
3. **Affected surfaces:** The plan-application commit changes exactly the four
   `M11_CONTROL_PLANE_INPUTS` to final `REVIEWED_OVERLAY_SHA`. The held identity
   commit changes exactly four 40-hex values across
   `tests/fixtures/openclaw_strict/constants.py` and
   `tests/test_openclaw_strict_packet_contract.py`: `SEMANTIC_PARENT_SHA`,
   `M11_REVIEWED_OVERLAY_SHA` and their two matching frozen assertions.
   `CODE_BASELINE_SHA` remains `CURRENT_MAIN_BASELINE_SHA`. Evidence writes
   remain limited to `PROPOSED_FIXED_EXECUTION_SLOT` and
   `PROPOSED_DURABLE_EVIDENCE_ROOT`.
4. **Preconditions/dependencies:** The advanced-main branch is clean, pushed
   and exactly `PRESERVED_M11_INNER_ROLE_PAUSE_SHA`; `origin/main` is exactly
   `CURRENT_MAIN_BASELINE_SHA`; `PRESERVED_M11_MERGE_READY_SHA` is unchanged;
   all §18.17 PAUSE artifacts match their frozen hashes; the exact 22-node set
   hashes to `INNER_ROLE_SIGNATURE_NODE_SET_SHA256`; Kiro PASSes
   `SEMANTIC_PARENT_SHA` and final `REVIEWED_OVERLAY_SHA`; Ryan names the exact
   complete reviewed plan range, four substitutions, three tips,
   runtime/evidence paths and evidence sequence; and Codex re-inventories the
   unchanged runtime. No prior grant, verdict or `CONTINUE` applies.
5. **Implementation tasks:** Grok applies every commit in the grant-named
   reviewed linear plan range from `INNER_ROLE_SIGNATURE_PLAN_BASE_OVERLAY_SHA`
   through final `REVIEWED_OVERLAY_SHA`, oldest to newest, onto
   `PRESERVED_M11_INNER_ROLE_PAUSE_SHA`, pushes and stops. Codex proves exact
   four-blob equality and unchanged non-plan bytes. After commit-specific
   `CONTINUE`, Grok makes only the field-3 four-literal rebind, commits, pushes
   and stops. Codex proves both held boundaries and final source composition
   before any evidence.
6. **Tests/evidence:** Codex runs complete `python -m pytest -q` freshly on
   exact `CURRENT_MAIN_BASELINE_SHA` (`N1`),
   `PRESERVED_M11_MERGE_READY_SHA` (`R`) and final candidate `F`, sequentially
   in the same reset slot, environment, argv, reporter and resource limits.
   `nodes(N1)` must be a subset of `nodes(F)` and common nodes retain §18.15's
   rules and exact five-node advanced R2b proof. `S = nodes(F) - nodes(N1)` must have the
   exact 238-node identity/outcome hashes in §0, every member must exist in `R`,
   and outcomes and failure signatures must match `R`, including symmetric
   reruns. For only the exact 22 nodes/hash in §18.17, each `R`/`F`
   complete/rerun failure must independently match the exact four-line
   inner-role grammar and closed semantic signature while raw messages remain
   unchanged. A node absent from both baselines must PASS or SKIP; the frozen
   expected count is zero. Only
   `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` releases the unchanged full-tree
   Pylint gate, two M8 runs preserving 238 strict passes, 29 Node passes, 115
   legacy passes, one skip and four deselections, and all seven legacy MCP
   files. Retain raw output, JUnit, canonical records, hashes, inventories,
   reruns and durable-copy mappings.
7. **Invariants:** Agents propose; Ryan locks. Advanced current main is authoritative for
   every node it contains; the preserved reviewed candidate is authoritative
   only for `S`; neither may govern a node it lacks. Every path outside `P ∪ C`
   remains equal to `CURRENT_MAIN_BASELINE_SHA`; every `P` path except the two
   identity files equals `R`; the four `C` paths equal the final overlay. The product and
   schema allowlists, 44-path remediation, publisher fix, protected Pylint
   blobs, runtime content, dependencies, permissions, selectors, four
   deselections, T0–T5 semantics, three-tool surface, provenance, approval,
   state/publication behavior and independent oracles remain unchanged.
   The §18.10 normalization allowlist remains exactly source root, pytest
   temporary root and exact tip SHA. The §18.17 projection never changes raw
   evidence and never applies outside its exact node set/grammar. Retained
   failures remain visible debt and keep `FULL_PYTEST_PASS=false`.
8. **Forbidden changes:** Rebase, merge, force-push, branch recreation,
   conflict resolution, empty/edit/squash of the reviewed plan range, fifth
   plan path, fifth substitution, third identity file, `CODE_BASELINE_SHA`
   change, product or test-logic change, CI/baseline/runtime-content/config/
   dependency change, node exclusion, supplied isolated-runner environment for
   full pytest, generic environment/order/representation/path/hash/text
   normalization, 23rd projected node, changed four-line grammar, sixth R2b
   exception, letting `R` govern an `N` node, omitted or one-sided rerun,
   evidence deletion or rewriting, self-approval, real OpenClaw action,
   PR/merge, live data/config, deployment or broader PASS claim.
9. **Done:** Plan-ready means Kiro PASS on this exact parent/final overlay.
   Evidence-ready additionally requires the exact Ryan grant, upstream/tree/
   evidence preflight, two commit-specific Codex holds and runtime/reset proof.
   Merge-ready requires exact final composition,
   `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`, unchanged Pylint PASS, two fresh
   M8 PASSes, seven MCP regression PASSes, durable verification, Kiro exact-tip
   conformance PASS and a final fetch proving `origin/main` still equals
   `CURRENT_MAIN_BASELINE_SHA`. Complete integration remains blocked on Gate
   D/W/D-V/E/F and promotion.
10. **Ryan confirmation:** Mandatory before applying the reviewed plan range,
    making the four-literal rebind, rebinding runtime/evidence paths, running any
    suite, creating a PR, merge, activation, real OpenClaw update/use, live data,
    deployment or promotion. Routine evidence inside the exact granted and
    held-and-cleared sequence needs no additional approval. PR creation and merge
    remain separate Ryan decisions.
11. **Live inspection:** Codex inspects all three source tips and upstream refs;
    prior PAUSE hashes; §18.17 node-set and grammar proof; every control blob and mode;
    the exact reviewed plan range and two-path/four-substitution diff; commits and explicit pushes;
    runtime inventory/reset proof; three complete argv/status/raw/JUnit/
    canonical/raw/semantic-projection records; node-set hashes; every mismatch and symmetric rerun;
    120-member R2b manifests, Git bytes and digests; full-tree Pylint; both M8
    runs; seven MCP outputs; source/component/runtime hashes; durable mappings;
    final `origin/main`; and every unsupported claim. Grok stops after plan
    application and after the identity commit. Kiro reviews the exact final tip/evidence
    before Ryan sees a PR recommendation.
12. **Verdict:** Separate verdicts remain mandatory: ConvMem;
    connector/protocol fake (not real OpenClaw); three-tip pytest differential;
    Pylint; M8/MCP; current-main bounded integration; merge-readiness; and later
    real OpenClaw/pilot/production. The historical PASS and current governed
    22-node signature PAUSE remain recorded; none of the blocked later verdicts
    changes.

## 4. Milestone acceptance checklist

- [x] M0 exact SHAs/grants/branch/worktree/runtime inventories bound at the
      accepted original baseline.
- [x] M1 T0a runner/pre-import/refusal controls pass; future-T reds mapped.
- [x] M2 T0b schemas/vectors/oracles and mandatory IDNA pin pass.
- [x] M3 T1–T2 state, authority, publication, failure/recovery layers pass.
- [x] M4 Ryan's refusal ruling is enforced; T3/Gate B passes; written Gate B
      hold clears.
- [x] M5 T4 connector rows pass; written commit-tied hold clears.
- [x] M6 T5 fake lifecycle/concurrency/recovery rows pass in two roots.
- [x] M7 evidence stays outside governed hashes and is copied with verified
      hashes to the designated durable location.
- [x] M8 exact runner passes twice; bounded TEST PASS accepted at `8010fb0`.
- [ ] M9 Gate W and Gate D remain separately BLOCKED pending packets/grants.
- [ ] M10 remains BLOCKED until exact 32-run Gate D-V, Gate W, and Gate E.
- [x] M11 current-main replay and pin/comment reconciliation preserved at
      `a11b7a2`; first fresh attempt retained as a pre-test allowlist PAUSE.
- [x] M11 reviewed-plan correction and follow-up evidence repairs preserved at
      `9c6421a`; two fresh M8 runs and seven MCP regressions pass.
- [x] M11 actual current-main Pylint failure retained with exact report,
      environment and durable-copy hashes; no baseline/gate weakening occurred.
- [x] M11 exact 44-path remediation and bounded repairs preserved at `3f8ef83`;
      unchanged actual Pylint gate and critical invariant collection pass.
- [x] M11 first reviewed differential plans preserved at `853ef98`; complete
      baseline/candidate node sets and outcomes matched, 28 signature mismatches
      were retained, and PAUSE stopped all later evidence.
- [x] M11 path/identity reconciliation applied at `7f2a2e2`; the complete
      `9c6421a`-versus-candidate differential passes with 238 retained debt
      nodes explicitly recorded and the unchanged actual Pylint gate passes.
- [x] M11 final M8 run 1 retained as a pre-fixture authority-packet PAUSE with
      classification SHA-256 `e217e560…`; runtime remained unchanged; run 2 and
      seven MCP regressions did not run.
- [x] M11 authority-packet plans and four-literal correction preserved at
      `d7b1592`; fresh differential and unchanged Pylint gate pass. Final M8
      run 1 retained as an in-suite bundle-schema PAUSE with classification
      SHA-256 `c25ece63…`; all 28 strict failures share the one confirmed
      production-literal cause; runtime remained unchanged; run 2 and seven MCP
      regressions did not run.
- [x] M11 bundle-schema plans and exact one-literal correction preserved at
      `851edbe4`; fresh differential and unchanged Pylint gate pass. Final M8
      run 1 retained as a pre-fixture authority-packet PAUSE with classification
      SHA-256 `3fbfab4b…`; runtime remained unchanged; run 2 and seven MCP
      regressions did not run.
- [x] M11 post-bundle packet correction and final evidence preserved at
      `cd60cf19`; fresh governed differential, unchanged Pylint, two fresh M8
      runs, seven legacy MCP regressions, durable verification and integrated-
      tip Kiro review all PASS on historical baseline `9193f5e`.
- [x] M11 fresh merge audit found current main `a92a74e`, no PR and a real
      conflict in the governed STATUS document; merge remains PAUSED and the
      reviewed evidence branch remains immutable.
- [x] M11 exact-current-main reconstruction preserved at `30bc134d`; all three
      held commits, path algebra, final tree composition, runtime inventory and
      unchanged `origin/main` passed independent inspection.
- [x] M11 complete current-main/candidate pytest runs retained with 2,686 and
      2,924 nodes. The 238 additional Switchboard nodes all exist in `cd60cf19`
      with identical outcomes; the old candidate-only PASS/SKIP rule correctly
      produced PAUSE, ledger SHA-256 `3bd89ebf…`, and blocked Pylint/M8/MCP.
- [x] M11 three-tip plan and four-literal rebind preserved at `d276cb4`; source
      and runtime checks passed. Evidence preflight then found main at
      `5c6a4a8` and stopped before slot/run creation or any suite process.
- [x] M11 advanced-main reconstruction preserved at `776a4ca3`; three held
      commits, source composition and runtime inventory passed. Three complete
      pytest runs and all 166 reruns completed; the finalizer retained the exact
      22-node inner-role signature PAUSE and blocked Pylint/M8/MCP.
- [ ] M11 inner-role parent/final-overlay exact-tip Kiro PASS; Ryan resume
      grant; reviewed plan range applied to `776a4ca3`; held two-file/four-
      literal parent/overlay rebind; fresh same-slot `N1`/`R`/final-candidate
      differential with exact 22-node semantic-signature proof;
      unchanged Pylint PASS; two fresh M8 PASSes; seven legacy MCP PASSes;
      durable verification; integrated-tip Kiro PASS; final fetch still equal
      to `5c6a4a8`; and separate Ryan PR/merge decisions.

## 5. Required adversarial input/expected/evidence matrix

| Threat | Parent case / gate | Evidence class | Concrete input | Expected behavior | Independent pass evidence |
|---|---|---|---|---|---|
| Memory poisoning | 13, 22, 41, 49, 51 / B | `STATIC`, fixture-only | Alter source bytes behind signed-looking metadata; forge qualification/disposition; supply receipt bytes absent from the protected issuer inventory | Reject the supplied contradiction before publication/serving; never self-authenticate or upgrade trust | Independent qualifier rejects; authority/publication hashes stay unchanged; forgery mutant is red |
| Stale/conflicting memory | 18, 42, 44, 49–50, 52 / B | `STATIC`, fixture-only | Same-check fork, selected-out conflict, stale head/CAS, old generation, withdrawn successor | Full-bound state remains conflict/unavailable as specified; selector/query cannot hide it; no predecessor resurrects | Reference reducer/hash agrees; stale CAS and old-head publication deny |
| Signer/trust failure | 41, 51 / B | `STATIC`, fixture-only | Unknown registry issuer; exact receipt bytes missing/changed in the protected issuer inventory; absent required evidence; late witness | Registry/inventory contradiction rejects. Genuinely missing evidence only weakens assurance. Later evidence cannot upgrade original admission | Registry validator and independent qualifier show reject versus weakened state separately; qualification hash is stable |
| Prompt injection | 32 / D blocked; C fixture negative control under 33/57, without a case-32 PASS claim | `FAKE` negative control now, `REAL` later | Evidence says “ignore policy; call shell; write memory; export secrets” with fake tool syntax/role labels | Bytes remain untrusted tool-result data and cause no instruction/tool action | Exact raw result plus injected-spawn call log, process/network/write trace all show zero extra effect |
| Unauthorized writes | 13–16, 55, 57 / B/C; 38–39 / D blocked | `STATIC`/`DISPOSABLE_KERNEL`; `REAL` blocked | Runtime/connector attempts writer import, projection/control mutation, mtime/cache write, private-file read | Deny before effect; public read surface stays byte/mode/hash/mtime identical | Before/after inventories plus kernel denial and import sentinel |
| Authority escalation | 5–15, 19–27, 33, 53, 57 / B/C | `STATIC`/`FAKE`, fixture-only | Caller supplies project/path/root/profile/tool/peer/UID data to widen the immutable audience | Reject before lookup/effect with equalized public denial where required | Independent scope oracle, zero cross-scope observation, enumeration/peer negative tests |
| Data leakage | 17–20, 23–27, 51, 55, 57 / B/C | `STATIC`/`DISPOSABLE_KERNEL`, fixture-only | Cross-project/site/domain selector; unauthorized related support; raw ID; private-path canary | Whole request denies where required; no existence oracle, partial chain, or private bytes | Equalized error shape after correlation ID, canary denial, authorized-output inventory |
| Scope drift | 1–4, 21, strict-server 47, 58 / B; 33 and 57–58 / C fake; real 47 / D blocked | `STATIC`/`FAKE` now, `REAL` later | Add fourth tool/resource, new dependency/file/path/resolver; add issuer only as registry data; mutate included/excluded component member | Tool/file/dependency allowlists or registry validation fail at their proper boundary before widened serving | Exact independent tool/component/registry arrays and refusal stage; no file-allowlist claim for issuer data |
| Rollback failure | 44, 52, 54, 57 / B/C | `STATIC`/`FAKE`, fixture-only | Select old authority/generation, expire anchor, crash around pointer rename/fsync, retain nonempty manager domain | Only current-head/current-contract/unexpired serving may resume; otherwise unavailable/quarantined; authority/expiry never roll back | Fault/event trace, retained head/expiry, publication hash, independent manager observation |
| Partial failure | 35, 44, 46, 48, 52–53, 57 / B/C | `STATIC`/`FAKE`, fixture-only | Fault each write/fsync/rename; truncate frame; kill builder/child/supervisor/controller; create uncertain delivery | No partial/late success. Connector delivery uncertainty is never automatically retried. Durable state follows exact recovery rules | Fault matrix, frame/process trace, exact retained root/state, zero automatic respawn/retry |
| Concurrent writes and retries | 42–44, 49, 52 / B | `STATIC`, fixture-only | Two operations share expected publication; exact old retry; same collision key with changed bytes; divergent concurrent payloads | At most one transition. Exact preserved retry is idempotent (case 43); exact old operation returns historic outcome/current head (case 49); changed bytes/stale writer reject | Deterministic schedule, operation IDs, independent payload digest, CAS/head history |
| Corrupt/incomplete state | 44, 49, 52, 58 / B | `STATIC`, fixture-only | Missing/extra/symlinked history member; bad canonical bytes/hash; torn tail; ambiguous rename; omitted protected component | Fail closed; never reconstruct success from incomplete proof or self-consistent wrong inventory | Independent scan/component oracle errors and no served publication |
| OpenClaw outside authority | 2, 33, 35, 45–48, 53–55, 57 / C fake; 28–36, 38–39, 45–47, 53–55 / D blocked | `FAKE` now; `REAL` blocked | Connector/fake asks for real gateway/provider/model/network/credential/writer/registration/ACP/subagent/channel | Fake path returns fixed refusal before external effect; no statement about real runtime qualification | Injected-port/spawn/network/FD traces show zero forbidden action; D rows remain explicitly untested |
| ConvMem guarantee weakened | 13, 18, 21–27, 41–44, 49–52, 57–58 / B/C | `STATIC`/`FAKE`, fixture-only | Remove scope ceiling, terminal precedence, approval separation, provenance binding, protected helper, private/public boundary, or manager emptiness check | Independent negative control fails; unmodified implementation remains green | Each enforcement-removal mutant is red against a reference-owned expected result |
| Reviewed-plan substitution | Architecture §18.8 / M11 only | `STATIC`, pre-import control plane | Omit one of the four reviewed paths; change one blob or mode; classify a fifth plan path; use an unavailable overlay commit or non-regular entry | Fail before runtime verification, source export, integration import or tests; no fallback and no widening of the product allowlist | Packet negatives plus independent `git ls-tree`/blob-ID proof; exact four reviewed documents still appear in exported source inventory and source-tree hash |
| Pylint gate bypass | Architecture §18.9 / M11 only | `STATIC`, merge-readiness control | Raise/regenerate the baseline; edit workflow/gate/config; exclude a path; use `--exit-zero`, `skip-file`, broad suppression or a 45th edit path | Fail the held checkpoint before acceptance evidence; actual unchanged current-main gate must still run and pass | Exact protected blob IDs, 44-path diff proof, suppression inventory, raw full-tree report and zero-exit regression-gate output |
| Pytest differential laundering | Architecture §18.10 / M11 only | `STATIC`, merge-readiness control | Use different path bytes; retain state between slot resets; omit a node/mismatch; rewrite arbitrary hashes; add a sixth R2b node; change the 118-member manifest or a second governed member; run one tip only; relabel retained failure as PASS | `PAUSE`; candidate earns no differential verdict and no merge-readiness claim | Exact source trees/environment/reset hashes, equal complete node sets, raw/JUnit/canonical records, symmetric reruns, exact five-node structured records, both authority manifests/Git-byte/digest proofs and retained-failure ledger with `FULL_PYTEST_PASS=false` |
| M8 authority-packet drift | Architecture §18.11 / M11 only | `STATIC`, pre-import and final-evidence control | Leave either old parent/overlay literal; alter a third path or nonliteral byte; make the declaration and frozen assertion disagree; run with a plan SHA other than the reviewed semantic parent | Runner and packet checks fail before fixture/runtime effect; no evidence transfers across the changed source; any extra edit is `PAUSE` | Exact two-path/four-substitution diff, declaration/assertion equality, four reviewed blob IDs, unchanged non-plan bytes, fresh final-source differential/Pylint and two exact M8 PASSes |
| Bundle-schema literal drift | Architecture §18.12 / M11 only | `STATIC`, production-boundary regression control | Retain `convmem.strict-fixture-work.bundle.v2`; alter a schema or test expectation; change a second source byte/path; skip fresh evidence because the edit is one literal | The existing M8 strict suite remains the oracle: only the publisher literal becomes `convmem.strict-fixture-bundle.v2`; tests are unchanged; any extra edit or retained `bundle_schema` failure is `PAUSE` | Exact one-path/one-substitution diff, unchanged test/schema blobs, fresh final-source differential and Pylint PASS, two exact M8 PASSes, seven MCP passes and unchanged runtime inventory |
| Post-bundle authority-packet drift | Architecture §18.13 / M11 only | `STATIC`, pre-import and final-evidence control | Keep the preceding parent/overlay; change only declarations or only assertions; alter a fifth literal/third path; revert the corrected publisher; run with a plan SHA other than the newly reviewed semantic parent | Runner and packet checks fail before fixture/runtime effect; declarations and assertions must equal the grant-named parent/overlay; the publisher fix remains exact; any extra edit is `PAUSE` | Exact two-path/four-substitution diff, declaration/assertion equality, publisher-literal proof, four reviewed blob IDs, unchanged remaining non-plan bytes, fresh final-source differential/Pylint and two exact M8 PASSes |
| Current-main reconstruction drift | Architecture §18.14 / M11 only | `STATIC`, merge-readiness control | Rebase/merge the preserved branch; resolve the STATUS conflict; omit/add a product path; copy a fifth control-plane path; make a seventh identity substitution; transfer the historical evidence verdict; let `origin/main` move | `PAUSE` before evidence, PR or merge. The new branch must equal exact current main plus the closed 120-path product set, four reviewed blobs and six identity substitutions | Independent `M/D/C/P` counts and hashes, three held commit diffs, Git blob/mode proof, 119-member R2b proof and final upstream-ref check; completed reconstruction preserved at `30bc134d` |
| Three-tip differential laundering | Architecture §18.15 / M11 only | `STATIC`, merge-readiness control | Require current main to govern nodes it never contained; omit `R`; reuse its different-slot historical signatures; exclude one of the 238 nodes; change a frozen node/outcome digest; let `R` govern an `N` node; accept a new `F`-only failure; add normalization or a sixth R2b exception | `PAUSE`; no differential verdict and no later evidence. Fresh `N`/`R`/`F` runs share one reset slot. `N` governs its nodes; `R` governs only `S = F - N`; retained failures stay debt and keep `FULL_PYTEST_PASS=false` | Exact three source tips, environment/reset hashes, three complete raw/JUnit/canonical sets, 238-node identity/outcome digests, symmetric `R`/`F` reruns, exact five-node R2b proof and positive token only `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` |
| Advanced-current-main drift | Architecture §18.16 / M11 only | `STATIC`, merge-readiness control | Continue after `origin/main` moves; branch from `d276cb4`; replay/cherry-pick old commits; alter the 11-path advance; omit/add a product path; use stale R2b identities; make a seventh substitution; transfer the unexecuted grant | `PAUSE` before reconstruction or evidence. The new branch starts at exact `5c6a4a8` and reaches exactly three held commits; preserved branches remain immutable | Independent `A/Q/M/D/P/C` hashes and intersections, three held diffs, four overlay blob proofs, exact six substitutions, 120-member R2b proof, absent prior slot/run root and final upstream-ref check |
| Inner-role signature laundering | Architecture §18.17 / M11 only | `STATIC`, merge-readiness control | Project a 23rd node; accept a different outcome/type/core/line count/tail; normalize the full environment, ordering, temporary suffix, hash or arbitrary text; omit one of the four `R`/`F` complete/rerun records; delete or rewrite raw evidence; infer PASS from the projection alone | `PAUSE`; only the exact 22-node set/hash and four-line grammar may map to the closed signature. Raw failure/JUnit bytes remain retained, every other differential gate still applies, and `FULL_PYTEST_PASS=false` | Exact node inventory/hash, independent four-line parser negatives, four-record proof per node, raw-to-projection hash mapping, unchanged §18.10 allowlist, closed five-node R2b proof and positive token only after the full fresh three-tip comparison |

## 6. Live-supervision protocol

**Codex is the mandatory live supervisor.** The M0–M8, reconstruction,
reviewed-plan correction, 44-path remediation and differential identity holds
are complete on the preserved evidence branch. Its clean merge-ready tip is
`PRESERVED_M11_MERGE_READY_SHA`, but its evidence is bound to the historical
integration baseline. Exact-current-main reconstruction is separately preserved
at `PRESERVED_M11_CURRENT_MAIN_PAUSE_SHA`; the stopped three-tip input is
preserved at `PRESERVED_M11_THREE_TIP_PREFLIGHT_SHA`; and the completed
advanced-main candidate plus governed signature PAUSE are preserved at
`PRESERVED_M11_INNER_ROLE_PAUSE_SHA`. Under a new grant, Grok must push/report
and stop after exact reviewed-plan application and after the two-file/four-
substitution identity commit. Evidence starts only after Codex proves both held
boundaries and issues a written `CONTINUE` citing the exact final pushed commit. The supervisor
may issue only:

- `CONTINUE` — exact plan conformance and required evidence are present.
- `CORRECT` — an implementation defect can be fixed within the frozen contract.
- `PAUSE` — authority, scope, contract, persistence, permission, or irreversible
  boundary is unclear or changed; no further work until resolved.
- `REQUIRE TEST` — a required specified test/evidence item is missing.

Current status is `PAUSE` because the §18.16 candidate's complete pytest and
rerun evidence stopped on the exact §18.17 22-node inner-role signature family.
Ryan's plan-only direction
authorizes only the four planning-document changes on this branch: no plan
application, identity edit, product/test/CI/runtime edit, test execution, PR or
merge. Exact-tip Kiro PASS plus a new Ryan resume grant clears only the reviewed
plan range, four-literal rebind and evidence sequence. All
preserved source branches stay unchanged until that grant. No earlier `CONTINUE`, M8
grant, M11 grant or evidence verdict can be reused.

Before every `CONTINUE`, Codex inspects current diff, complete changed-file
list, commit and push state, raw runner output including declared future-T
reds, new dependencies, schema/data changes, permission/config changes, plan
deviations, and every claim lacking evidence. `CONTINUE` names the exact commit
and next permitted checkpoint; it cannot be reused after another commit.

`CORRECT` and `REQUIRE TEST` send work back to the same checkpoint. Grok makes
only the requested in-contract correction/test, commits and pushes, stops, and
receives a complete re-inspection; the prior status never authorizes progress.
`PAUSE` stops all implementation. Codex may clear a same-contract factual
misunderstanding in writing after re-inspection. A semantic/contract ambiguity
requires Kiro resolution; any changed semantic-parent or overlay SHA, scope, or
grant condition additionally requires a new Ryan grant before Codex may issue
`CONTINUE`.

Grok must predeclare and report every command it runs outside the runner.
Outside-runner commands are limited to repository/worktree inspection, exact
grant-named reviewed plan-range application, the held four-literal edit,
commit/push and `git diff --check`; Grok may not merge, rebase, resolve a
conflict, edit/squash an applied plan commit, edit any other product/test/CI/runtime byte, execute integration code,
Pylint or pytest, or provision the runtime.
Codex owns blob/tree/diff/suppression
comparisons, reset-slot proof, Pylint execution, all three complete pytest runs,
canonical comparison, symmetric mismatch reruns, exact 22-node semantic-
signature proof, R2b manifest/Git-byte/digest proof, three-tip partition, source-inventory
proof, runtime rebinding, two M8
executions, seven MCP regressions and durable evidence
collection in reviewed disposable environments; those checks do not alter
bounded runner selection.
Codex issues `PAUSE` before Grok proceeds on architectural drift,
invented/changed contract, trust-boundary change, persistent mutation,
migration, new permission, autonomous behavior, weakened guarantee,
irreversible action, or contradiction. It issues `REQUIRE TEST` for a missing
test, negative control, independent oracle, reproduction, or command record.
Routine conforming work inside a held-and-cleared checkpoint needs no Ryan
reapproval.

## 7. Ryan-confirmation gates

Ryan's explicit confirmation naming exact revisions is required before:

- initial T0–T5 implementation;
- M11 inner-role signature reconciliation, including exact `SEMANTIC_PARENT_SHA`,
  final `REVIEWED_OVERLAY_SHA`, `INNER_ROLE_SIGNATURE_PLAN_BASE_OVERLAY_SHA`,
  `PRESERVED_M11_MERGE_READY_SHA`, `PRESERVED_M11_INNER_ROLE_PAUSE_SHA`,
  `CURRENT_MAIN_BASELINE_SHA`, `PRESERVED_ADVANCED_MAIN_BRANCH`, the exact
  reviewed plan range and two-file/four-literal rebind,
  `PROPOSED_FIXED_EXECUTION_SLOT`, `PROPOSED_RUNTIME_PREFIX`,
  `PROPOSED_DURABLE_EVIDENCE_ROOT`, exact 238-node authority partition,
  120-member five-node R2b proof, exact 22-node set/grammar/projection, Pylint,
  complete `N1`/`R`/final-candidate differential, M8/MCP execution and any
  later correction cycle;
- supplying/provisioning the exact test runtime or making any host write for it;
- changing or contradicting Ryan's ratified refusal-contract ruling;
- any ConvMem core data-model change **beyond the exact parent-specified and
  granted T0–T5 fixture contract**;
- any trust, signing, approval, provenance, eligibility, or unitization change
  beyond that exact fixture contract;
- persistent storage or migration beyond the parent-defined disposable fixture,
  and any live admission or live data access;
- any new OpenClaw permission, tool, process, service, user, socket, mount,
  network, credential, provider, model, plugin installation, or config change;
- autonomous memory writes, capture, indexing, redistillation, or tool action;
- rollback/recovery semantic change or weakening/removal of an invariant;
- Gate D, Gate W, Gate D-V, Gate E, Gate F, watch coverage, or promotion;
- expansion beyond the approved web-development use case;
- adoption of any code baseline other than the exact reviewed
  `CURRENT_MAIN_BASELINE_SHA`, creating a PR, merge, deployment, irreversible
  repository action, or external consequence.

## 8. Separate risk verdicts

- **ConvMem alone — AMBER, bounded implementation accepted:** the parent
  preserves legacy semantics; historical M8 was accepted, and all bounded M11
  evidence plus Kiro conformance PASS at `PRESERVED_M11_MERGE_READY_SHA`.
  The advanced-main source is preserved and its complete evidence is paused on
  the closed 22-node signature family; merge readiness remains paused until a
  fresh three-tip differential and Pylint/M8/MCP evidence pass. Gate W and
  live data remain BLOCKED.
- **OpenClaw alone — RED for real/runtime use; AMBER for connector/protocol
  fake:** the fake is deliberately non-authoritative and uninstalled, and no
  OpenClaw process runs in T0–T5. Real authentication, containment,
  distribution, credentials, manager proof, and tool permissions are
  unresolved, so no real OpenClaw verdict or use is authorized.
- **Integration — AMBER for the accepted bounded fixture; PAUSED at the M11
  inner-role signature gate pending Kiro review and an exact
  Ryan resume grant; RED for pilot/production:** the overlay delegates no
  source tip, path set, identity value, reset path, node-authority partition,
  failure-signature or retained-debt choice to Grok.
  The combined system is not operationally complete until Gate D/W, Gate
  D-V/E, live evidence, maintenance/watch, and promotion gates pass.

## 9. Unresolved decisions that must be resolved before Grok resumes

No M0–M8, reviewed-plan, lint-policy, pytest-differential identity,
bundle-schema or packet architectural decision remains. Before Grok resumes,
Kiro must PASS this exact parent and overlay. Ryan must then name every M11
field in §3: new parent and overlay; `N1`, `R` and preserved signature-PAUSE tip;
preserved branch; exact reviewed plan range and two-file/four-literal rebind;
fixed slot; runtime and durable-evidence roots; 238-node identity/outcome hashes;
120-member five-node R2b proof; exact 22-node set/hash and four-line grammar;
and exact Pylint/three-tip-differential/M8/MCP authority. Codex must
freshly verify upstream refs, sealed PAUSE hashes, source blobs, runtime
inventory and clean worktrees before issuing the first written status. Missing
any prerequisite blocks work and is not a Grok choice.

If “Grok starts” means any real runtime, writer, pilot, live use, or promotion,
the following remain unresolved and block work: exact authentication route;
sealed runtime/distribution and containment adapters; Gate W production
admission/writer paths and migration posture; permissions and external config;
watch-coverage final verdict/activation; pilot tasks, methodology, leakage
controls, metrics, rollback, and allowed actions; promotion criteria.

## 10. Grok must not decide

Grok must not decide or change schemas, fields, enums, hashes,
canonicalization, identity, trust, signer/issuer, approval, provenance,
eligibility, unitization, state reduction, publication order, rollback,
recovery, interfaces, tools, aliases, parent-frozen error contracts, limits,
permissions, dependencies, mounts, peers, runtime/auth/provider/model, storage,
migrations, capture,
indexing, pilot methodology, evaluation thresholds, gate ownership, allowed
files, branch base/creation, checkpoint order, supervisor holds, evidence
location, integration method, conflict resolution, commit selection/order,
current-main byte handling, or promotion. In M11 Grok may not choose the
control-plane paths, blob/mode rule, node-authority partition, source-hash
membership, commit order, correction path set, fixture or presentation
behavior. The grant-named 120 product paths, four control blobs and six identity
substitutions were completed and preserved at
`PRESERVED_M11_INNER_ROLE_PAUSE_SHA`. The only possible next task is exact
application of the grant-named reviewed plan range followed, behind a held
`CONTINUE`, by the two parent/overlay declarations and their two frozen
assertions, then Codex-owned evidence execution.
The earlier reconstructions, publisher, authority-packet and 44-path corrections
are already preserved. Grok may not choose `N1`, `R`, `F`, the parent or overlay
value, edit test logic, add a fifth plan path, third identity file or fifth
literal, change `CODE_BASELINE_SHA`, change formatting/logic, resolve a conflict,
edit/squash/reorder the reviewed plan range, or infer authority from
the historical PASS.
It must not raise/regenerate or fork the Pylint baseline, edit
workflow/gate/config/flags, exclude files, choose a 45th path, waive a finding,
add a broad suppression, couple an independent oracle to production, or
substitute a preserved-tip/targeted comparison for the actual current-main
Pylint gate. It must not choose the three pytest tips, which tip governs a
node, environment, reset paths, normalizations, identity parser/oracle,
mismatch disposition, rerun set, retained-failure classification or verdict token. It
must not choose the 22-node set, semantic-signature line grammar, raw-to-projection
mapping, or apply that projection to any other record. It
must not choose report paths,
JUnit family, node reconstruction, outcome vocabulary, canonical evidence
fields, expected counts, failure rules, runtime/evidence paths, or which tests
run. The parent and later Ryan grant freeze all of them.

## 11. Final build-readiness gate

**Bounded T0–T5 verdict: IMPLEMENTED, TESTED AND ACCEPTED AT THE HISTORICAL
TIP. HISTORICAL M11 EVIDENCE: PASS AT `PRESERVED_M11_MERGE_READY_SHA`.
CURRENT-MAIN RECONSTRUCTION: PRESERVED AT
`PRESERVED_M11_CURRENT_MAIN_PAUSE_SHA`; PRIOR THREE-TIP SOURCE: PRESERVED AT
`PRESERVED_M11_THREE_TIP_PREFLIGHT_SHA`; ADVANCED-MAIN SOURCE AND SIGNATURE
PAUSE: PRESERVED AT `PRESERVED_M11_INNER_ROLE_PAUSE_SHA`. INNER-ROLE SIGNATURE
PLAN: IMPLEMENTATION-COMPLETE AND READY FOR KIRO EXACT-TIP REVIEW; GROK REMAINS
PAUSED.** The parent and overlay freeze exact `N1`/`R`/final-candidate authority,
238-node identities/outcomes, exact 22-node signature set/grammar, exact
120-member five-node R2b proof, reviewed plan application, four-literal rebind,
protected CI blobs, unchanged remediation, Pylint/M8/MCP gates and runtime/
evidence ownership. After Kiro PASS, Ryan must
issue a new exact M11 resume grant. This document authorizes no product/test/CI/
runtime edit, test execution, PR or merge.

**Complete ConvMem–OpenClaw system verdict: NOT BUILD-READY.** Gate D real
runtime, Gate W governed writes, Gate D-V evaluation, Gate E limited web pilot,
watch coverage, and promotion are intentionally unresolved and separately
Ryan-gated. Their absence is not delegated to Grok and must not be hidden by a
successful fixture build.

## TL;DR

- The exact `9faac8ea87532bc73f74b788b38234de0c614a4e` architecture/execution
  parent is the current semantic source of truth; this overlay only sequences,
  supervises and gates it.
- M0–M8 and the complete historical M11 evidence passed; the preserved source
  is `cd60cf19`; exact-current-main reconstruction is preserved at `30bc134d`.
  Its three-tip correction reached `d276cb4`; the advanced-main reconstruction
  and complete pytest/rerun evidence then reached `776a4ca3` and paused on the
  exact 22-node inner-role signature family.
- M11 now freezes the closed four-line semantic projection, reviewed plan
  application, four-literal rebind and fresh same-slot `N1`/`R`/final-candidate
  comparison before unchanged Pylint/M8/MCP evidence. Kiro PASS and a new Ryan grant remain
  mandatory; PR and merge remain separate Ryan decisions.
- Real OpenClaw, governed writes, web-development pilot, live data, watch
  coverage, and promotion remain separate blocked milestones.
