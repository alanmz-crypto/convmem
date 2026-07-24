# Neutral ConvMem Core v0 target

```text
Planning Status

Phase:        Architecture Planning
Characters:   Architect, Systems Thinker, Risk Reviewer
Functions:    Planner
Lane:         Codex, requested by Ryan for this direction pass
Authority:    Awaiting HITL approval
```

| Field | Value |
|---|---|
| Status | Proposed direction; no Neutral repository or runtime exists |
| Source | Ryan's 2026-07-23 Neutral Core handoff and operational-independence requirement |
| Question | What is the smallest evidence-gated Neutral Core target? |
| Next gate | Ryan approves the direction and selects a valuable first office workflow before implementation |

## Human consequence

Neutral Core will not be a cleaned-up copy of ConvMem Engineering. It will exist
only after a real office workflow demonstrates a coherent set of mechanisms that
keep the same responsibility in both applications. Until then, temporary
duplication is the safer architecture.

```text
                          build-time comparison
ConvMem Engineering  <------------------------------>  Office Team v0
         |                                                       |
         |             only after extraction gate                |
         +---------->  Neutral ConvMem Core v0  <----------------+

Runtime before extraction: no arrow between the applications.
Runtime after extraction: each application points only to its own pinned copy of
Neutral; neither application points to the other or to Neutral's source checkout.
```

## Target definition

Neutral Core v0 is the smallest **standalone mechanism library** for which the
same behavior has been demonstrated in ConvMem Engineering and Office Team. A
single useful helper is not a sufficient reason to create a repository: the
qualified mechanisms must form a coherent, independently testable runtime slice.

The likely slice is listed below as a target, not as a finding that every item is
ready now.

### Candidate responsibilities

1. Validate and canonicalize the common portion of durable records.
2. Produce stable semantic identifiers and content hashes where both applications
   demonstrate the same identity rules.
3. Append canonical records durably before updating derived state.
4. Read and iterate the durable ledger after process restart.
5. Project records into a replaceable derived index and rebuild that index by
   replaying the ledger.
6. Preserve common provenance relationships between records.
7. Traverse the common evidence relationship chain.
8. Offer only the minimal retrieval behavior proven useful in both applications.

Observation, decision, completion, and verification are not automatically a
universal kind list. Each joins Neutral only if the office comparison proves the
same responsibility and invariant. In particular, ConvMem Engineering has no
canonical completion record today, so completion starts as office-owned.

### Public seams, not a premature API

The probe should test responsibilities at these boundaries without freezing
function names or a framework:

| Seam | Neutral may own after qualification | Applications continue to own |
|---|---|---|
| Record | Common validation, canonical projection, hash/ID mechanics | Domain payload, vocabulary, required fields, policy |
| Durable store | Append/read/iterate behavior and durability contract | Storage root, backup, retention, migration timing |
| Projection | Apply one canonical record and rebuild from ledger | Backend choice and app-specific metadata adapter |
| Relationships | Common provenance link representation and traversal | Which links are permitted or required by a workflow |
| Retrieval | Small backend-neutral query/result contract, if demonstrated | Models, weights, source trust, orchestration, presentation |
| Runtime setup | Explicit values passed by the caller | Config file, secrets, CLI identity, roles, deployment |

Neutral must not discover a repository root, inspect an application's working
directory, read application environment variables by name, or choose user-level
paths. Explicit constructor/function inputs are sufficient; a universal Project
Profile schema is not required.

## Dependency boundary

Neutral Core v0 may depend on:

- the Python standard library;
- its own versioned modules;
- a small, declared persistence dependency if the extraction evidence requires
  it; and
- caller-supplied storage and indexing adapters.

Neutral Core v0 must not import or invoke:

- ConvMem Engineering or Office Team modules;
- either application's CLI, MCP server, watch process, roles, prompts, or policy;
- either application's configuration or database;
- checkout-relative resources or a service running from either repository; or
- an editable install, symlink, `PYTHONPATH`, local `file://` index, or subprocess
  whose continued availability depends on an application checkout.

The dependency graph must remain acyclic:

```text
ConvMem Engineering adapter ──> pinned Neutral artifact
Office Team adapter         ──> pinned Neutral artifact

Neutral artifact            -X-> either application
ConvMem Engineering         -X-> Office Team
Office Team                 -X-> ConvMem Engineering
```

## Project-owned responsibilities

The following stay outside Neutral v0 even if both applications happen to use
similar words:

- project identity, configuration files, data and secrets roots;
- domain record payloads, roles, signer identities, approval policy and workflow;
- model selection, prompts, ranking weights and source-trust policy;
- CLI, MCP, watch, background services and agent coordination;
- deployment, backup, restore scheduling and operator runbooks;
- schema migration decisions for each application's existing data; and
- project initialization or a universal workflow/Profile/role language.

## Independence properties

Neutral itself must pass tests from a clean environment with both application
repositories inaccessible. Each application must separately pass with the other
application absent and with only its pinned Neutral artifact available.

For every runtime:

1. configuration and storage paths are supplied by that runtime;
2. durable records live under that application's storage root;
3. process-global caches, locks and registries are scoped by the complete project
   storage/backend identity or avoided;
4. a restart can recover the ledger and relationship chain;
5. deleting the derived index and replaying the ledger recreates equivalent
   derived records; and
6. backup and restore never require another application's database.

## Neutral extraction success criteria

A mechanism qualifies only when all answers are yes:

- Does it have the same responsibility and observable behavior in both apps?
- Were domain assumptions removed rather than renamed or hidden in configuration?
- Can its contract tests move with the mechanism unchanged?
- Can it run with both application repositories absent?
- Does sharing it remove meaningful duplication without importing policy?
- Can each app pin, deploy, back up and upgrade independently?
- Is migration from each app's local implementation explicit and reversible?

If the qualified mechanisms do not form a useful standalone slice, Neutral Core
v0 is deferred and both applications keep their local implementations.

## Explicit exclusions for v0

Neutral v0 does not include ConvMem's current `ask`, `query`, approval,
MCP, watch, CLI, doctor, brief, inventory, backup, deployment or agent-protocol
subsystems. It also does not include the office workflow, office roles, office
approval policy, a Project Profile standard, an initializer or a generic workflow
engine.

## Chosen direction

Build one independently deployable office workflow selected for business value,
compare its local mechanisms with ConvMem Engineering, and extract only the
coherent subset that clears every gate above. Do not create Neutral Core before
that comparison.

**TL;DR:** Neutral v0 is a small standalone mechanism library discovered from two
working applications; all identity, policy, workflow, operations and deployment
remain application-owned, and no Neutral repository is justified until a coherent
slice passes the cross-domain and operational-independence gates.
