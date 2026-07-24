# Implementation handoff 1 — independent Office Team probe

| Field | Value |
|---|---|
| Status | Execution-ready scope, blocked on Gate 0 workflow selection and Ryan's execution approval |
| Owner | Cursor implementation lane after explicit assignment; Ryan owns workflow choice, external authorization and merge |
| Purpose | Deliver one valuable Office Team workflow and the evidence needed for a Neutral extraction review |
| ConvMem changes | None in this pass |

## Required inputs — stop if missing

Before creating code, obtain Ryan's approved workflow card:

- real office source/request and sanitized test fixture;
- valuable bounded result;
- human decision and authorized office actor/role;
- completion evidence and independent verification observable;
- explicit exclusions; and
- Office Team repository location/name plus approval to create it.

Business value selects the workflow. Do not invent a toy probe or choose a lower
value workflow because its records are easier to generalize.

## Scope

Create the real Office Team repository and implement exactly one cycle:

```text
source/request -> evidence -> observation -> action proposal
-> human decision -> completion -> verification
-> restart/recover -> derived-index replay
```

Assume Python for the first pass because the reference implementation and its
tested leaf mechanics are Python; return to Ryan if the selected office workflow
requires another runtime.

### Task 1 — Project identity and ownership

- Hand-write an office-local `project_profile.toml` (not a universal schema) and
  the minimum role cards needed by the chosen workflow.
- Give Office Team unique project, config, data, secrets and CLI identities.
- Resolve all paths from explicit office config; do not read `CONVMEM_*`,
  `~/.config/convmem`, `~/.local/share/convmem` or the ConvMem checkout.
- Lock/vend dependencies inside Office Team's reproducible install. No editable
  ConvMem install, symlink, `PYTHONPATH`, local checkout index or subprocess.

**Done when:** an isolated temp environment loads the profile and initializes a
fresh office data root with ConvMem inaccessible.

### Task 2 — Office-local durable records

- Define only the fields the selected workflow needs for evidence, observation,
  action proposal, human decision, completion and verification.
- Copy/adapt the canonical JSON + SHA-256 mechanics and durable append behavior;
  record their ConvMem source commit and local changes.
- Choose deterministic evidence identity from the real source's business key and
  test duplicate delivery.
- Append canonical records to an office-owned JSONL ledger with flush/`fsync`
  before any derived write.
- Accept office actors/policy from the office application. Do not copy
  `VALID_SIGNERS`, engineering domains, `site`, agent-model requirements or
  ConvMem proposal states by default.

**Done when:** one fixture produces the full durable relationship chain and a
fresh process reads identical semantic IDs, hashes and links.

### Task 3 — Replaceable derived projection

- Build the smallest derived index the valuable workflow needs. Use a thin
  office-owned Chroma adapter only if the workflow benefits from semantic search;
  identity/relationship lookup alone is acceptable when sufficient.
- Keep collection names, model choice and metadata mapping office-owned.
- Implement replay from the canonical ledger into a fresh empty projection.
- Make projection apply idempotent for the fixture's duplicate and restart cases.

**Done when:** deleting only the disposable derived index and replaying the ledger
recreates equivalent projected IDs, relationships and required retrieval output.

### Task 4 — Human decision, completion and verification

- Pause for the real human decision at the workflow's authorized boundary; tests
  may use an explicit fixture decision, not a hidden default.
- Record completion separately from the decision.
- Verify the declared observable after completion and append a durable pass/fail
  record linked to the result being checked.
- Do not generalize these record kinds or lifecycle states during this pass.

**Done when:** the business result and independent verification are visible after
restart and projection replay.

### Task 5 — Independence and comparison evidence

- Add `tests/independence/test_first_workflow_without_convmem.py` following
  [EXTRACTION-PROBE.md](EXTRACTION-PROBE.md#standalone-operational-independence-test).
- Run with isolated HOME/XDG/PATH/PYTHONPATH, no ConvMem editable install or
  symlink, the ConvMem checkout denied/absent, and a fresh office database.
- Assert all durable writes remain below the Office Team data root and no ConvMem
  database path is opened.
- In the PR/handoff, classify every copied or newly written mechanism as
  `[reused-as-is]`, `[adapted]`, `[office-specific]`,
  `[new-and-maybe-general]` or `[shared-change]` and compare it with
  [NEUTRAL-CORE-CANDIDATES.md](NEUTRAL-CORE-CANDIDATES.md).

**Done when:** workflow, restart, replay and operational-independence tests pass,
and the comparison identifies evidence without extracting any code.

## Required acceptance checks

- [ ] The approved valuable business result is produced.
- [ ] Office profile/config and role cards load from Office Team only.
- [ ] Office ledger and derived database initialize under a fresh temp data root.
- [ ] Six durable workflow records form the expected relationship chain.
- [ ] Duplicate source delivery preserves canonical evidence identity.
- [ ] A new process recovers IDs, hashes, payloads and links.
- [ ] A deleted derived index rebuilds solely from the ledger.
- [ ] The complete workflow passes with ConvMem source, config, database,
      environment, CLI and processes unavailable.
- [ ] No file or data is read from or written to ConvMem Engineering.
- [ ] No Neutral repository/package/schema/framework is created.
- [ ] No ConvMem Engineering code is changed.
- [ ] The handoff reports candidate similarities and differences without claiming
      extraction approval.

## Out of scope

- Neutral Core repository or package extraction;
- changes to ConvMem Engineering;
- generic Project Profile, role-contract or workflow schemas;
- scheduling, Gmail, background agents, UI, marketing automation or client intake;
- ConvMem CLI, MCP, watch, ask/query orchestration, backup or deployment transfer;
- shared ranking weights, source-trust policy or a general completion lifecycle;
- a second office workflow.

## Stop and return to Ryan

- Gate 0 inputs or repository-creation authority are missing.
- The real value cannot be delivered without an out-of-scope product capability.
- A proposed dependency resolves through ConvMem or an unpinned local artifact.
- The office ledger cannot be made canonical before projection.
- Passing requires a ConvMem `[shared-change]`; report the exact blocker and the
  “would ConvMem need this without Office Team?” evidence instead of changing it.
- The selected workflow exposes sensitive client data that cannot be represented
  by a safe fixture.

## Handoff after implementation

Report the business outcome, test commands/results, all storage locations,
dependency provenance, largest remaining independence risk, and a candidate
comparison. Then stop for Ryan's Neutral extraction-gate review. Do not create
Neutral or refactor ConvMem in the same pass.

**TL;DR:** After Ryan selects the real office workflow and authorizes the
repository, Cursor should build one office-owned ledger-first cycle with restart,
replay and a ConvMem-absent independence test, record the comparison evidence, and
stop before any Neutral extraction or ConvMem change.
