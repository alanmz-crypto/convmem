# Implementation handoff 1 — independent Office Team probe

| Field | Value |
|---|---|
| Status | Execution-ready scope; blocked only on Ryan's repository/execution authorization and identification of the real policy artifact and office authorities |
| Implementation | Cursor after explicit assignment |
| Ryan authority | Repository creation, architecture/execution gates, external authorization and merge—not automatic office policy approval |
| Office authority | Owner–Practitioner decides the policy; Managing Co-operator applies and operationally verifies it where authorized |
| Purpose | Deliver one independently valuable Office Team policy revision and evidence for the comparison/convergence gates |
| ConvMem changes | None in this pass |

## Required inputs — stop if missing

The workflow is locked as **approved office policy or procedure change**. Before
creating code, obtain:

- Ryan's Office Team repository location/name and authorization to create it and
  execute this handoff;
- one real office service or operating-policy artifact plus the change request and
  previous text, represented by a sanitized fixture;
- the Owner–Practitioner who approves or rejects the exact revision;
- the Managing Co-operator who applies the approved revision and verifies the
  active artifact where authorized; and
- confirmation that the fixture contains no client, health or secret data.

Use this exact workflow unless a concrete artifact/authority blocker is found:

| Step | Locked result |
|---|---|
| Evidence | Contains or references the request and previous policy text. |
| Observation | Current text does not match the intended policy. |
| Action proposal | Exact replacement revision. |
| Human decision | Owner–Practitioner approves or rejects that revision. |
| Completion | Managing Co-operator applies the approved text to the office-owned artifact. |
| Verification | Active artifact matches the approved content and semantic hash. |

## Scope

Create the real Office Team repository and implement exactly six canonical
records in one cycle:

```text
evidence(request + previous text) -> observation -> action proposal
-> Owner–Practitioner decision -> Managing Co-operator completion -> verification
-> restart/recover -> derived-index replay
```

Assume Python for the first pass because the reference implementation and its
tested leaf mechanics are Python; return to Ryan if the selected office workflow
requires another runtime.

### Task 1 — Separate human identity from machine configuration

- Hand-write `PROJECT-PROFILE.md` with purpose, human roles, authorities, the
  locked first workflow, exclusions and assumptions.
- Create a separate `config.toml` with project ID, config/data/secrets roots,
  ledger/projection paths and runtime settings.
- Neither file is a universal schema; keep the minimum role cards local to Office
  Team.
- Give Office Team unique project, config, data, secrets and CLI identities.
- Resolve all paths from explicit office config; do not read `CONVMEM_*`,
  `~/.config/convmem`, `~/.local/share/convmem` or the ConvMem checkout.
- Lock/vend dependencies inside Office Team's reproducible install. No editable
  ConvMem install, symlink, `PYTHONPATH`, local checkout index or subprocess.

**Done when:** an isolated temp environment loads both files for their separate
purposes and initializes a fresh office data root with ConvMem inaccessible.

### Task 2 — Office-local durable records

- Define only the fields the selected workflow needs for evidence, observation,
  action proposal, human decision, completion and verification.
- Copy/adapt the canonical JSON + SHA-256 mechanics and durable append behavior;
  record their ConvMem source commit and local changes.
- Choose deterministic evidence identity from the real source's business key and
  test duplicate delivery.
- Treat the request and previous policy as evidence-record content/reference, not
  a seventh record.
- Use one writer. Reject or serialize concurrent writes with an office-local lock.
- Write one complete canonical JSON record per line with flush/`fsync` before any
  derived write; validate every line on startup and fail closed on an invalid or
  truncated tail—never silently skip corruption.
- Test duplicate delivery, a simulated crash tail, explicit tail repair/recovery
  and a successful restart after repair.
- Accept office actors/policy from the office application. Do not copy
  `VALID_SIGNERS`, engineering domains, `site`, agent-model requirements or
  ConvMem proposal states by default.

**Done when:** one fixture produces exactly six canonical records in the locked
order and a fresh process reads identical semantic IDs, hashes and links; the
corrupt-tail test fails closed and the explicit recovery test passes.

### Task 3 — Replaceable derived projection

- Build the smallest derived index the valuable workflow needs. Use a thin
  office-owned Chroma adapter only if the workflow benefits from semantic search;
  identity/relationship lookup alone is acceptable when sufficient.
- Keep collection names, model choice and metadata mapping office-owned.
- Implement replay from the canonical ledger into a fresh empty projection.
- Track projection progress independently from canonical durability so unapplied
  records are identifiable and retryable.
- Make projection apply/replay idempotent by stable record identity; simulate a
  projection failure after durable append and prove retry succeeds.

**Done when:** deleting only the disposable derived index and replaying the ledger
recreates equivalent projected IDs, relationships and required retrieval output.

### Task 4 — Human decision, completion and verification

- Pause for the Owner–Practitioner's exact approve/reject decision; tests may use
  an explicit fixture decision, never a hidden Ryan/signer default.
- Record Managing Co-operator completion separately from the decision.
- Verify that the active policy artifact matches the approved content and semantic
  hash, then append a durable pass/fail record linked to the completion/result.
- Do not generalize these record kinds or lifecycle states during this pass.

**Done when:** the business result and independent verification are visible after
restart and projection replay.

### Task 5 — Independence v0 and comparison evidence

- Add `tests/independence/test_first_workflow_without_convmem.py` following
  [EXTRACTION-PROBE.md](EXTRACTION-PROBE.md#independence-v0--mandatory-for-the-first-implementation).
- Run with isolated HOME/XDG/PATH/PYTHONPATH, no ConvMem editable install or
  resolved import/command, the ConvMem checkout unavailable, and a fresh office
  database.
- Assert every config/runtime/data path remains below the temporary Office Team
  root and no ConvMem config or engineering database path is opened.
- In the PR/handoff, classify every copied or newly written mechanism as
  `[reused-as-is]`, `[adapted]`, `[office-specific]`,
  `[new-and-maybe-general]` or `[shared-change]` and compare it with
  [NEUTRAL-CORE-CANDIDATES.md](NEUTRAL-CORE-CANDIDATES.md).

**Done when:** workflow, crash recovery, restart, replay and Independence v0 pass,
and the comparison routes each candidate to direct qualification, bounded
convergence proof, another workflow or project ownership without extracting code.

## Required acceptance checks

- [ ] The approved policy artifact is updated.
- [ ] `PROJECT-PROFILE.md`, `config.toml` and role cards load from Office Team only
      and retain separate human/machine responsibilities.
- [ ] Office ledger and derived database initialize under a fresh temp data root.
- [ ] Exactly six records—evidence, observation, action proposal, human decision,
      completion and verification—form the expected relationship chain.
- [ ] The request and previous policy live in/reference the evidence record; no
      seventh source record exists.
- [ ] Duplicate source delivery preserves canonical evidence identity.
- [ ] Concurrent writers are rejected/serialized; invalid/truncated tails fail
      closed; corruption is never skipped; explicit crash-tail recovery passes.
- [ ] Projection failure preserves the canonical record, exposes retry progress
      and replays idempotently.
- [ ] A new process recovers IDs, hashes, payloads and links.
- [ ] A deleted derived index rebuilds solely from the ledger.
- [ ] The complete workflow passes with ConvMem source, config, database,
      environment, CLI and processes unavailable.
- [ ] No file or data is read from or written to ConvMem Engineering.
- [ ] No Neutral repository/package/schema/framework is created.
- [ ] No ConvMem Engineering code is changed.
- [ ] The handoff reports candidate routes without claiming convergence or
      extraction approval.

## Out of scope

- Neutral Core repository or package extraction;
- changes to ConvMem Engineering;
- generic Project Profile, role-contract or workflow schemas;
- scheduling, Gmail, client/health records, background agents, UI, marketing
  automation, website automation or client intake;
- ConvMem CLI, MCP, watch, ask/query orchestration, backup or deployment transfer;
- shared ranking weights, source-trust policy or a general completion lifecycle;
- a second office workflow;
- Independence v1 OS-level mount denial, comprehensive subprocess interception
  and filesystem auditing; these remain required hardening after the functional
  probe unless already inexpensive and portable.

## Stop and return to Ryan

- Ryan's repository/execution authorization, real policy artifact or either office
  authority is missing.
- The real value cannot be delivered without an out-of-scope product capability.
- A proposed dependency resolves through ConvMem or an unpinned local artifact.
- The office ledger cannot be made canonical before projection.
- Passing requires a ConvMem `[shared-change]`; report the exact blocker and the
  “would ConvMem need this without Office Team?” evidence instead of changing it.
- The selected workflow exposes sensitive client data that cannot be represented
  by a safe fixture.

## Handoff after implementation

Report the policy outcome, exact six-record chain, test commands/results, all
storage locations, dependency provenance, largest remaining Independence v0 risk,
and the four-route candidate comparison. Then stop for Ryan's Gate 3 review. Any
ConvMem-local convergence work requires a new, candidate-specific approval and
handoff. Do not create Neutral or refactor ConvMem in this pass.

**TL;DR:** After Ryan authorizes the repository and the office authorities identify
the real policy artifact, Cursor should implement exactly six fail-closed,
ledger-first records with restart/replay and Independence v0, report the four-route
comparison, and stop before any ConvMem convergence work or Neutral extraction.
