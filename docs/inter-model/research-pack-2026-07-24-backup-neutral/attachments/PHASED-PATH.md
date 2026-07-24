# Shortest gated path to Neutral Core v0

| Field | Value |
|---|---|
| Status | Proposed architecture direction; awaiting HITL |
| Question | What sequence reaches Neutral Core as soon as evidence permits, but not earlier? |
| Chosen path | Bounded policy workflow → independent Office implementation → comparison → approved local convergence proof → conditional extraction |
| Current stop | Gate 0: Ryan authorizes the Office Team repository/pass and the office authorities identify the real policy artifact |

## Options considered

| Option | Consequence | Decision |
|---|---|---|
| Extract a Neutral framework now | Fast repository creation, but current engineering assumptions become accidental public policy and the ledger/replay contract is guessed. | **Reject.** Violates the two-domain evidence rule. |
| Build the complete Office Team product, then compare | Maximizes domain evidence but delays the boundary decision behind scheduling, integrations, UI and unrelated product work. | **Reject.** Too much work before reassessment. |
| Build one independently valuable bounded office workflow, compare, then prove local parity where justified | Produces business value and the minimum second-domain evidence; bounded convergence can prove a missing common seam without sharing code prematurely. | **Choose.** Shortest reliable path toward a real Neutral slice. |

## Master path

1. Approve the bounded Office Team policy/procedure workflow.
2. Create the operationally independent Office Team runtime.
3. Complete the six-record ledger-first workflow.
4. Pass restart, replay and Independence v0.
5. Compare responsibilities and tests with ConvMem Engineering.
6. Classify candidates as directly qualified, convergence-required,
   another-workflow-required or project-owned.
7. Perform only separately approved application-local convergence work.
8. Run identical portable candidate contract tests against both applications.
9. Extract Neutral Core v0 only when the passing mechanisms form a coherent
   useful slice.
10. Migrate each application independently to a pinned Neutral artifact.
11. Complete Independence v1 hardening.

## Phase 0 — Authorize the locked policy probe

Use the approved office policy/procedure change card in
[EXTRACTION-PROBE.md](EXTRACTION-PROBE.md#gate-0-workflow-card--approved-office-policy-or-procedure-change)
unless a concrete artifact or authority blocker is found. Ryan authorizes the
repository and implementation pass. The Owner–Practitioner and Managing
Co-operator identify the real policy artifact, request, approval boundary,
completion action and safe fixture.

**Gate 0 passes when:** Ryan authorizes the repository/pass, the office authorities
and real policy artifact are named, and the input can be represented safely.

**If it fails:** stop. Do not substitute a toy memory demo.

## Phase 1 — Establish an independent Office Team runtime

Create the real Office Team repository. Hand-write `PROJECT-PROFILE.md` for
purpose, human roles, authorities, workflow, exclusions and assumptions. Create a
separate `config.toml` for project identity, config/data/secrets roots,
ledger/projection paths and runtime settings. Neither is a universal schema.
Copy or reimplement only the narrow mechanics required by the approved workflow.
Do not import ConvMem, package ConvMem, create Neutral, or change ConvMem
Engineering.

The initial source of truth is an office-owned append-only ledger. Any Chroma or
other search database is a derived projection under the office data root.

**Gate 1 passes when:** the human profile and machine config load from Office Team
only and a fresh office ledger/index initialize in an isolated environment with
the ConvMem checkout inaccessible.

**If it fails:** fix only the office-local dependency or path; do not generalize
ConvMem to make the test pass.

## Phase 2 — Complete the one bounded workflow

Implement exactly six records: evidence (containing/referencing the request and
previous policy), observation, action proposal, Owner–Practitioner decision,
Managing Co-operator completion and verification. Apply the single-writer,
complete-line, fail-closed crash-tail and independent projection-progress rules
from the probe. Preserve each transition durably, then restart and rebuild the
derived index from the ledger.

**Gate 2 passes when:** the approved policy artifact is updated, exactly six
records survive a fresh process, replay recreates equivalent derived records and
relationships, crash-tail/projection retry tests pass, and Independence v0 passes.

**If it fails:** keep work in Office Team. A failure supplies implementation
evidence but never authorizes Neutral extraction.

## Phase 3 — Compare and route responsibilities

For every candidate, compare the two working implementations using
[NEUTRAL-CORE-CANDIDATES.md](NEUTRAL-CORE-CANDIDATES.md). Separate mechanism from
policy and identify the smallest portable observable contract for each plausible
shared mechanism. Route each candidate to: directly qualified, bounded convergence
proof, another workflow, or project-owned.

**Gate 3 passes when:** every candidate has one route with written evidence; any
convergence candidate has a minimal contract, portable tests, an independently
useful ConvMem rationale and a separately reviewable scope. Candidates needing
another workflow stay local regardless of centrality.

## Phase 4 — Prove portable parity, converging locally only when needed

Every directly qualified or convergence candidate must run the same portable
contract-test bundle against installed/snapshotted builds of both applications
with both source repositories unavailable to the test environment. Direct
candidates require no application change before that test.

For each separately approved convergence candidate:

1. keep the Office Team and ConvMem implementations local;
2. implement or adapt only the smallest contract in ConvMem Engineering when
   ConvMem would benefit from the exact behavior without Office Team;
3. do not share source, domain policy, signers, configuration or workflows;
4. run that same portable contract-test bundle against both application builds;
   and
5. keep a candidate local if parity requires domain flags or broader refactoring.

Ledger-first append and replayable projection are explicit candidates for this
phase because ConvMem's observation and approved-decision paths do not currently
provide one coherent counterpart. Common envelope fields, provenance links,
verification durability and explicit storage injection may follow only if Gate 3
finds the same responsibility.

**Gate 4 passes per candidate when:** both independent local implementations pass
the same portable observable contract tests with source repositories unavailable.
For a convergence candidate, the ConvMem change must also be independently
valuable. This gate proves parity; it does not extract code.

## Phase 5 — Create Neutral only after direct or convergence proof

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

**Gate 5 passes when:** both applications consume independently pinned Neutral
artifacts, retain project-owned storage and policy, and pass with the other app
and Neutral source checkout absent.

## Phase 6 — Complete Independence v1 hardening

After the first workflow, convergence and migration are stable, add OS-level
mount/access denial, comprehensive subprocess interception and filesystem auditing
where portable. These strengthen proof that neither application or Neutral source
checkout is an undeclared runtime dependency without delaying the first useful
office workflow.

**Gate 6 passes when:** the hardening tests fail on deliberate forbidden access and
pass for each released application in its isolated environment.

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
| Probe expands into unrelated office infrastructure | Gate 0 locks the smallest independently valuable policy revision and its exclusions | Stop rather than add integrations |
| Temporary copies drift | Record source provenance and compare behavior after Gate 2 | Copies are app-local and can be replaced independently |
| Chroma becomes the de facto core | Ledger is canonical; projection must rebuild from it | Replace projection adapter without changing durable records |
| Premature “common” record schema | Office defines local records first; compare invariants later | Keep divergent record adapters |
| Convergence becomes a ConvMem refactor | Gate 3 requires a minimal portable contract and independent ConvMem benefit; each candidate needs separate approval | Reject or narrow the candidate without affecting Office Team |
| Extraction creates migration risk | One app migrates at a time with old implementation retained | Roll back the consuming app's pin/cutover |
| Only trivial helpers qualify | Require a useful coherent slice | Defer the Neutral repository at no runtime cost |

## Unresolved decisions at this gate

- Which real office policy artifact and sanitized request instantiate the locked
  workflow.
- Which people fill Owner–Practitioner and Managing Co-operator for that artifact.
- Whether its first useful retrieval need requires Chroma or only identity/graph
  lookup.
- The common record envelope, stable-ID grammar and completion semantics.
- Whether the qualifying Neutral slice is large enough to justify a repository.
- Package artifact versus vendored snapshot after the slice and release burden are
  known.
- How ConvMem Engineering's existing split JSONL/Chroma state migrates if a
  ledger-first seam ultimately qualifies.

## Sequence-change assessment

Current repository evidence justifies one bounded sequence correction. Ledger-first
write/replay is not a ready core hidden inside ConvMem, because the observation and
approved-decision paths use different durability orders and recovery models. The
Office implementation therefore remains local through the probe; after comparison,
a separately approved ConvMem-local parity pass may prove the same contract before
extraction. This closes the prior path's dead end without authorizing a general
ConvMem refactor.

The only implementation-level assumption added here is Python for the first
Office Team pass, because that makes the audited leaf mechanics directly
comparable and is reversible. If the selected business workflow requires another
runtime, Gate 0 must revisit that assumption before repository creation.

**TL;DR:** Run the locked six-record policy workflow independently, compare and
route candidates, prove any genuinely shared-but-different seam through separately
approved local parity work, and extract Neutral only after identical portable
contracts form a useful slice; complete Independence v1 after migration.
