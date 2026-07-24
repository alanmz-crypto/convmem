# Shortest gated path to Neutral Core v0

| Field | Value |
|---|---|
| Status | Proposed architecture direction; awaiting HITL |
| Question | What sequence reaches Neutral Core as soon as evidence permits, but not earlier? |
| Chosen path | Valuable bounded Office Team workflow → independent local implementation → comparison → conditional extraction |
| Current stop | Gate 0: Ryan selects and approves the office workflow |

## Options considered

| Option | Consequence | Decision |
|---|---|---|
| Extract a Neutral framework now | Fast repository creation, but current engineering assumptions become accidental public policy and the ledger/replay contract is guessed. | **Reject.** Violates the two-domain evidence rule. |
| Build the complete Office Team product, then compare | Maximizes domain evidence but delays the boundary decision behind scheduling, integrations, UI and unrelated product work. | **Reject.** Too much work before reassessment. |
| Build one valuable bounded office workflow independently, then compare | Produces business value and the minimum second-domain evidence while temporary duplication keeps both apps reversible. | **Choose.** Shortest evidence-based path. |

## Phase 0 — Approve the probe input

Ryan selects a real office workflow using the card in
[EXTRACTION-PROBE.md](EXTRACTION-PROBE.md#selection-rule). Record its value,
human decision, completion evidence, verification observable and exclusions.

**Gate 0 passes when:** a business-valued workflow and bounded outcome are explicit.

**If it fails:** stop. Do not substitute a toy memory demo.

## Phase 1 — Establish an independent Office Team runtime

Create the real Office Team repository. Hand-write its local Project Profile/config
and role cards; choose unique config, data, secrets and CLI identities. Copy or
reimplement only the narrow mechanics required by the approved workflow. Do not
import ConvMem, package ConvMem, create Neutral, or change ConvMem Engineering.

The initial source of truth is an office-owned append-only ledger. Any Chroma or
other search database is a derived projection under the office data root.

**Gate 1 passes when:** the profile/config loads and a fresh office ledger/index
initialize in an isolated environment with the ConvMem checkout inaccessible.

**If it fails:** fix only the office-local dependency or path; do not generalize
ConvMem to make the test pass.

## Phase 2 — Complete the one bounded workflow

Implement only the approved request→evidence→observation→proposal→human
decision→completion→verification cycle. Preserve each transition durably, then
restart and rebuild the derived index from the ledger.

**Gate 2 passes when:** the business outcome is delivered, the full standalone
independence test passes, records survive a fresh process, and replay recreates
equivalent derived records and relationship results.

**If it fails:** keep work in Office Team. A failure supplies implementation
evidence but never authorizes Neutral extraction.

## Phase 3 — Compare responsibilities, not filenames

For every candidate, compare the two working implementations using
[NEUTRAL-CORE-CANDIDATES.md](NEUTRAL-CORE-CANDIDATES.md). Separate mechanism from
policy and identify contract tests that would move unchanged.

**Gate 3 — Neutral extraction — passes for a mechanism only when:**

1. responsibility and observable behavior are the same in both applications;
2. domain assumptions can be removed, not replaced with flags;
3. tests transfer unchanged and run with both app repositories absent;
4. sharing removes meaningful duplication without moving policy;
5. each app can deploy and store data independently; and
6. migration from each local implementation is explicit and reversible.

Candidates marked “needs a second workflow” stay local regardless of how central
they appear. If the passing candidates do not form a useful standalone slice,
stop with two independent applications and temporary duplication.

## Phase 4 — Create Neutral only after Gate 3

Create a separate Neutral repository only for the coherent passing slice. Move
the shared contract tests with it. Keep application adapters and domain tests in
their applications. Test Neutral with both application repositories inaccessible.

Then migrate one application at a time:

1. pin a Neutral release/snapshot in a branch;
2. run the application's local contract, migration and independence tests;
3. compare old and new durable/derived behavior;
4. cut over with a rollback path; and
5. upgrade the second application separately.

No application deletes its local implementation until its migration passes.

**Gate 4 passes when:** both applications consume independently pinned Neutral
artifacts, retain project-owned storage and policy, and pass with the other app
and Neutral source checkout absent.

## Realistic post-extraction distribution

| Option | Independence and provenance | Trade-off | Recommendation |
|---|---|---|---|
| Versioned package artifact | Each app locks an immutable version plus artifact hash from a Neutral-owned release; runtime/install does not consult an app checkout or local `file://` index. | Requires small packaging/release work only after a real core exists. | **Preferred steady state** if both apps can install the same artifact reproducibly. |
| Pinned vendored snapshot | Neutral source is copied into each app; commit records Neutral commit/tag, tree or archive hash and local patches. | Strong offline independence and simplest bootstrap, but upgrades are manual and drift is easier. | **Acceptable first extraction** when release infrastructure would be disproportionate. |
| Live source arrangement | Editable install, symlink, submodule not materialized into the release, shared checkout path or local package index. | Makes another checkout/environment part of the runtime or install chain. | **Reject.** It fails operational independence. |

The extraction review chooses between the first two based on the actual slice. It
does not design a package system now.

## Upgrade and ownership rules

- Each app pins a version/snapshot and records origin commit plus artifact/tree
  hash in its dependency provenance.
- Neutral changes require Neutral contract tests and application adapter tests;
  upgrades are explicit reviewed changes, never floating resolution.
- Data migrations ship as versioned, application-invoked operations with backup,
  dry-run/verification and rollback rules owned by each app.
- Domain translation stays in app adapters. A new application need never import
  another application's adapter.
- Neutral has its own source/release authority. Neither application's checkout,
  database, virtual environment or service acts as the upstream runtime.
- A change useful to only one app stays in that app until independent evidence
  clears the extraction gate again.

## Risks and reversibility

| Risk | Smallest response | Reversibility |
|---|---|---|
| Probe chosen for clean architecture, not value | Gate 0 requires a valuable result and business-value tie-break | Select another bounded workflow before code |
| Temporary copies drift | Record source provenance and compare behavior after Gate 2 | Copies are app-local and can be replaced independently |
| Chroma becomes the de facto core | Ledger is canonical; projection must rebuild from it | Replace projection adapter without changing durable records |
| Premature “common” record schema | Office defines local records first; compare invariants later | Keep divergent record adapters |
| Extraction creates migration risk | One app migrates at a time with old implementation retained | Roll back the consuming app's pin/cutover |
| Only trivial helpers qualify | Require a useful coherent slice | Defer the Neutral repository at no runtime cost |

## Unresolved decisions at this gate

- Which office workflow wins on business value.
- Whether its first useful retrieval need requires Chroma or only identity/graph
  lookup.
- The common record envelope, stable-ID grammar and completion semantics.
- Whether the qualifying Neutral slice is large enough to justify a repository.
- Package artifact versus vendored snapshot after the slice and release burden are
  known.
- How ConvMem Engineering's existing split JSONL/Chroma state migrates if a
  ledger-first seam ultimately qualifies.

## Sequence-change assessment

Current repository evidence does not justify changing the proposed sequence. It
does justify a stricter reading of it: ledger-first write/replay is not a ready
core hidden inside ConvMem, because the current observation and approved-decision
paths use different durability orders and recovery models. That seam therefore
stays office-local through the first workflow even though it is central to the
eventual target.

The only implementation-level assumption added here is Python for the first
Office Team pass, because that makes the audited leaf mechanics directly
comparable and is reversible. If the selected business workflow requires another
runtime, Gate 0 must revisit that assumption before repository creation.

**TL;DR:** Approve one valuable office workflow, build it as an independent
ledger-first application, prove restart/replay and zero ConvMem coupling, compare
the two implementations, and create Neutral only if the passing mechanisms form a
useful standalone slice; otherwise keep the safe duplication.
