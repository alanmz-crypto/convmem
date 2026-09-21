# Grok actualization brief — OpenClaw bounded ConvMem reader

**Status:** READY FOR RYAN'S BOUNDED T0–T5 EXECUTE DECISION. This brief does
not authorize implementation. The separately required maintenance watch-
coverage gate is BLOCKED on a reviewed repository-knowledge indexing design
and has no Execute grant.

**Arc:** none (ad-hoc integration)

**Purpose:** Convert the Kiro-approved planning revision into an ordered build
brief for Cursor using Grok 4.5 High. This document resolves implementation
sequence and checkpoint detail only. It does not amend the architecture,
execution scope, interfaces, acceptance criteria, or gate ownership.

## 1. Exact authority packet

Bind the implementation to all of these exact values:

```text
REVIEWED_PLAN_SHA=cd9d2698b7423f907b552bc9118a0af523018ca9
REVIEWED_PARENT_SHA=2aa66a8753db3be6adce7cb17533eae96aee609d
PLAN_BRANCH=plan/2026-09-20-openclaw-convmem-final-readiness
CODE_BASELINE_SHA=7809f20dc53d9dd19f765c3ec3214a3df54ca5bf
REVIEWED_BUNDLE_SHA256=2d0b0810947e4caedff5c77c0c89a5e02fd72bad293bad98127a4aff5050c9c2
REVIEWED_ASTRA_REPORT_SHA256=b923847c95ed48351ad20dc4f829c1d4c09a98ffc1ad361872abeafdda1d2941
KIRO_DECISION=PASS
BUILD=PASS
TEST=NOT_YET_RUN
LIVE_DATA=BLOCKED
PROMOTION=BLOCKED
EXECUTE_AUTHORIZED=NO
WATCH_COVERAGE=BLOCKED
WATCH_EXECUTE_AUTHORIZED=NO
```

The authoritative inputs are the following two files at
`REVIEWED_PLAN_SHA`:

```text
docs/plans/ARCHITECTURE-openclaw-convmem-integration.md
docs/plans/EXECUTION-openclaw-convmem-integration.md
```

Read both completely before editing. The architecture defines meaning. The
execution plan defines build ownership, allowed paths, sequence, commands, and
evidence. If this brief appears to disagree with either plan, stop and apply
the plans. Do not reconcile a disagreement by choosing new behavior.

Kiro independently confirmed that the two plans in the review bundle are
byte-identical to Git at `REVIEWED_PLAN_SHA`, that all 101 non-plan bundle
files are byte-identical to `CODE_BASELINE_SHA`, and that the parent-to-tip
change touches only those plans. Kiro's PASS establishes design and scope
readiness only. Ryan must issue a separate grant that names this exact plan
SHA and the bounded T0–T5 scope before any implementation begins.

The watch-coverage requirement in §10 was added after Kiro's exact-tip review.
It does not amend Kiro's PASS or enter T0–T5 by implication. Its inventory,
exclusions, and acceptance conditions are binding maintenance requirements;
the missing repository-knowledge adapter/indexing route requires a separate
Codex/Kiro design and Ryan grant before implementation or live configuration.

## 2. Role and decision boundary

Cursor is the sole implementation writer. Grok implements the already-frozen
contract and may decide ordinary coding details such as private helper names,
function decomposition, local variable names, and test fixture organization
inside the owned paths, provided those choices do not alter observable
behavior or component membership.

Grok must stop and return the issue to Codex/Kiro if implementation would
require any change to:

- authority, identity, provenance, qualification, state, or publication
  semantics;
- a schema, field, enum, hash input, canonicalization rule, or component set;
- an interface, CLI verb, MCP method, error code, response shape, queue bound,
  protocol deadline, or file owner;
- scope, audience, selector, row authorization, or completeness behavior;
- authentication, containment, runtime distribution, process ownership,
  manager emptiness, freshness, release, retirement, or peer policy;
- rollback, recovery, failure handling, or acceptance criteria;
- the allowed-file list, dependency inventory, capture issuer, resolver,
  runtime mount, suite selection, deselection list, or gate assignment.

Fix ordinary conformance defects inside the frozen contract. Report a
contract contradiction as a BUILD BLOCKER with the exact failed criterion and
smallest required planning correction. A missing Gate D, Gate W, Gate E, or
Gate D-V artifact is not permission to invent it during T0–T5.

## 3. Frozen outcome

Build exactly the synthetic T0–T5 fixture capability:

1. Synthetic authority, grounding, canonical state, and immutable file
   publication.
2. A direct read-only file CLI.
3. An MCP server with exactly `search`, `unresolved`, and `related`.
4. Uninstalled connector library logic with the three fixed aliases
   `convmem_search`, `convmem_unresolved`, and `convmem_related`.
5. Controller and supervisor protocol cores exercised only through the fixed
   `FixturePlatform` and test-owned connector `spawn` port.
6. A disposable, closed runner that executes the exact three bounded suites
   and returns the required independent evidence.

The fixture is a protocol implementation. It is not an installed OpenClaw
runtime, a production distribution, a host-containment qualification, an
authentication solution, or a production write path.

Production controller `start`, supervisor entrypoints, and ordinary plugin
registration must refuse `runtime_not_qualified`; command-line refusal exits
78 before OS operations. No CLI flag, environment variable, plugin setting,
manifest field, source record, or production loader may select a fake.

## 4. Frozen invariants

Preserve every invariant in the reviewed architecture, including all exact
algorithms, fields, conditional requirements, bounds, and test cases in
Architecture §§4, 6–9, 11–15 and Execution §§2–10. The following is the
implementation checklist, not a substitute for those sections.

### 4.1 Authority and surface

- ConvMem files and CLI retain governance and durable-memory ownership.
- OpenClaw is a bounded disposable reader/orchestrator with no governance
  authority.
- The audience is one immutable operator-owned binding. Caller text, paths,
  ordinary metadata, model output, CWD, MCP Roots, and public IDs cannot widen
  it.
- The strict profile is exactly `openclaw-strict`. Unset/`full` and `shell`
  retain existing behavior. Every other non-empty profile fails closed.
- The MCP inventory is exactly three tools and zero resources/templates.
  There is no `ask`, global index, `search_fast`, brief, folder state, stats,
  prompt, sampling, completion, or dynamic dispatch.
- There is no native OpenClaw memory, capture, automatic indexing, ACP,
  subagent, channel, remote inference, ambient credential, or consequential
  external effect.
- Retrieved evidence has zero instruction authority.

### 4.2 Identity, grounding, and state

- Preserve existing legacy IDs, provenance envelope bytes, and envelope UUIDs.
- Strict assertion identity and the existing envelope UUID remain distinct.
- Qualification is grounded in exact bytes and authenticated capture receipts
  and is frozen at original admission. Late witnesses or receipts cannot
  upgrade it.
- Capture issuer inventories remain separate from source-producer inputs.
- Revocation and supersession remain permanent after admission.
- Full-bound canonical verification state is computed once, independent of
  retrieval filters. Same-check forks, selected-out conflicts, terminal
  precedence, ineligible inconclusive contribution, support union, and the
  exact unresolved predicate follow the architecture.
- A query narrows display only. It never runs a local or alternate state
  reducer.

### 4.3 Authority, publication, rollback, and recovery

- Enrollment creates genesis explicitly. Every later mutation requires the
  full `--expected-publication SHA256` comparison.
- Cumulative authority conserves identities, parents, dispositions, source
  cutoff, and original provenance context.
- Fence precedes intent/source commitment. Durable authority may advance to
  unavailable before serving publication.
- Publication serves the exact current authority head and semantic contract,
  or nothing. Compare complete publication hashes, never generation names.
- A rejected candidate cannot rewrite history. Projection failure cannot undo
  an admitted terminal action.
- Rebuild, rollback, and recovery retain the current authority head, contract,
  and persisted expiry. Rollback changes serving only and never restores an
  old authority head or renews lifetime.
- Missing or ambiguous history, corrupt admitted witnesses, uncertain
  rename/fsync state, nonempty or unknown containment, and lost latest-history
  proof fail closed to unavailable/quarantined.
- Fixture deletion is teardown, not recovery of an enrolled lineage.
- Recovery cannot issue an implicit add. An uncommitted admission requires an
  explicit operator retry; already-proven admission may repair only its exact
  bookkeeping and derivative.

### 4.4 Qualification and runtime separation

- Private cold qualification runs in a fresh operator-controlled process
  before publication and activation.
- The runtime opens only the exact committed public projection and manifests.
  It cannot read private grounding, citation, source, issuer, governance, or
  control files.
- Public row hashes alone do not prove derivation. A qualification flag never
  self-authenticates.
- The fake has no authentication or provider-selection operation and cannot
  prove installed OpenClaw compatibility.
- Supervisor exit, stop acknowledgement, or cleanup callback cannot attest an
  empty manager domain. Detached descendants and outstanding model work stay
  present until independent manager events remove them.
- Only an exact-invocation, current-boot, independently observed
  `terminal=true, populated=false` result permits retirement and slot reuse.
  Stale, partial, unknown, nonterminal, or nonempty observations quarantine.
- Same-boot freshness anchors persist. A new boot requires clock review.
- Release/revoke linearization cannot wait for a blocked consumer, and an
  uncertain delivery is never retried or rerun.

### 4.5 Legacy and production separation

- Existing production writers, backups, recovery safeguards, legacy IDs,
  envelopes, site normalization, and protected modules remain unchanged.
- Approval, explicit `convmem add --file ABS`, durable admission, and
  derivative projection remain separate operations.
- No automatic legacy migration, inferred consent, Chroma-as-absence proof,
  fixture-to-production promotion, or claim that current production APIs
  already meet Gate W is allowed.
- Selected legacy tests establish only preserved legacy behavior. They do not
  grant strict components access to legacy writers/config or prove Gate W.

## 5. Exact edit boundary

Gate B/C may add or change only these eight Python implementation modules:

```text
bound_read_scope.py
strict_grounding.py
strict_evidence_state.py
strict_projection_publisher.py
strict_projection.py
openclaw_strict_server.py
openclaw_activation_controller.py
openclaw_activation_supervisor.py
```

The only allowed existing-source change is reject-only behavior in
`mcp_server.py`: unknown profiles fail closed, and strict mode refuses with an
instruction to use the dedicated entrypoint. `requirements.txt` may change
only to pin reviewed `idna==3.18`.

Gate B schema paths are exactly:

```text
schemas/convmem-bound-read-scope-v2.schema.json
schemas/convmem-project-binding-registry-v3.schema.json
schemas/convmem-bound-authority-record-v3.schema.json
schemas/convmem-authority-disposition-v1.schema.json
schemas/convmem-strict-provenance-context-v2.schema.json
schemas/convmem-strict-grounding-v1.schema.json
schemas/convmem-capture-receipt-v1.schema.json
schemas/convmem-strict-fixture-bundle-v2.schema.json
schemas/convmem-strict-citation-map-v1.schema.json
schemas/convmem-bound-authority-manifest-v3.schema.json
schemas/convmem-bound-projection-row-v2.schema.json
schemas/convmem-strict-graph-v1.schema.json
schemas/convmem-bound-projection-manifest-v3.schema.json
schemas/convmem-strict-generation-layout-v2.schema.json
schemas/convmem-strict-publication-v2.schema.json
schemas/convmem-strict-enrollment-v1.schema.json
schemas/convmem-strict-slot-v1.schema.json
schemas/convmem-strict-source-cutoff-v1.schema.json
schemas/convmem-strict-semantic-contract-v1.schema.json
schemas/convmem-strict-state-v2.schema.json
schemas/convmem-clock-review-v1.schema.json
schemas/convmem-raw-evidence-v3.schema.json
schemas/convmem-error-v1.schema.json
schemas/convmem-strict-config-v2.schema.json
```

Gate C schema paths are exactly:

```text
schemas/convmem-openclaw-connector-launch-v2.schema.json
schemas/convmem-openclaw-activation-v2.schema.json
schemas/convmem-activation-control-v1.schema.json
schemas/convmem-activation-retirement-v1.schema.json
schemas/convmem-activation-launch-policy-v1.schema.json
schemas/convmem-activation-manager-policy-v1.schema.json
schemas/convmem-controller-socket-policy-v1.schema.json
```

Gate W schemas and `governed_admission.py` are specified for a later packet and
are outside this edit.

The remaining allowed paths are exactly:

```text
integrations/openclaw-convmem-reader/package.json
integrations/openclaw-convmem-reader/openclaw.plugin.json
integrations/openclaw-convmem-reader/index.js
integrations/openclaw-convmem-reader/test/connector.test.mjs
tests/fixtures/openclaw_strict/**
tests/test_bound_read_scope.py
tests/test_strict_grounding.py
tests/test_strict_evidence_state.py
tests/test_strict_projection_publisher.py
tests/test_strict_projection.py
tests/test_strict_projection_recovery.py
tests/test_mcp_openclaw_strict.py
tests/test_strict_snapshot_revocation.py
tests/test_openclaw_lifecycle_config.py
tests/test_openclaw_connector_contract.py
tests/test_openclaw_activation_controller.py
tests/test_openclaw_activation_supervisor.py
tests/test_openclaw_strict_packet_contract.py
```

Protected during T0–T5 are `canonical_json.py`, `provenance.py`,
`provenance_binding.py`, `domains.py`, every legacy ID/ledger/query/unresolved/
related/Chroma/store/ingest/observe/monitor/proposal/recovery module,
`convmem.py`, adapters, live data/config/credentials, and unrelated plans.
Pure functions from the four named canonical/provenance/domain helpers may be
imported without changing their bytes.

Before every commit, compare the baseline-to-tip filename set with this exact
allowlist. Any unlisted change stops implementation.

## 6. Closed schemas and hashes

Unknown, missing, or duplicate keys; noncanonical order; wrong types; and
omitted required nulls fail. JSON Schema encodes structural constraints;
validators enforce graph, history, receipt, file, and OS invariants. A schema
default never upgrades an older version.

Implement the exact schema fields, nested closed definitions, hash inputs,
enums, conditional requirements, and bounds from Architecture §§4, 6, 8, and
11. Do not infer or improve them. The fixture manifest is test-only
`convmem.strict-fixture-manifest.v1` with exactly:

```text
schema, artifact_kind, plan_sha, code_baseline_sha, source_tree_sha256,
test_runtime_tree_sha256, components, artifacts, manifest_payload_sha256
```

`artifact_kind` is `protocol_fixture`. Its hash excludes only its own hash
field. The source inventory excludes that manifest and generated outputs. It
is not a production schema, semantic-contract input, or runtime distribution.

The duplicate-free `CORE` set is exactly:

```text
canonical_json.py
provenance.py
provenance_binding.py
domains.py
bound_read_scope.py
strict_grounding.py
strict_evidence_state.py
strict_projection.py
requirements.txt
```

`SCHEMAS_BC` is exactly the 24 Gate B plus 7 Gate C schema paths above. It
contains no Gate W or fixture-manifest schema.

Hash canonical sorted arrays of `{path,mode,sha256}` using repo-relative POSIX
paths and actual four-octal-digit modes. Reject missing, duplicate, extra, and
symlink entries. The five exact component sets are:

- `builder`: `CORE ∪ SCHEMAS_BC ∪ {strict_projection_publisher.py}`.
- `strict_server`: `CORE ∪ SCHEMAS_BC ∪ {openclaw_strict_server.py}`.
- `supervisor`: `CORE ∪ SCHEMAS_BC ∪ {openclaw_activation_supervisor.py}`.
- `controller`: `CORE ∪ SCHEMAS_BC ∪`
  `{openclaw_activation_controller.py, openclaw_activation_supervisor.py}`.
- `plugin`: exactly the connector's `package.json`, `openclaw.plugin.json`,
  and `index.js`.

Reader/server modules cannot import publisher/controller/supervisor. The
controller may reuse supervisor protocol parsing. Tests, fake adapters,
runtime/model bytes, and legacy `mcp_server.py` are outside component hashes.
Separate fixture/source/test-runtime inventories bind those inputs. Missing
local-import membership is a stop for Codex/Kiro; do not extend a set.

### 6.1 Closed interfaces to copy verbatim

The registry v3 top level is exactly `schema, revision, bindings`. Its one
binding has exactly `id, public_ref, project, domain_root, site_mode, site,
non_expanding_roots, source_registrations, lineage_id, capture_issuers,
verification_producers`. A source registration has exactly `id, source_class,
source_identity, identity_match, authorization_domain, site,
event_id_resolver`; `identity_match` is `exact`, and the only initial resolver
is `fixture_scan_event_v1`.

Strict config is exactly:

```text
schema: convmem.strict-config.v2
projection_root: ABS
max_projection_rows: 10000
max_projection_bytes: 67108864
telemetry: false
```

Every other key fails. This parser is independent of the legacy config
loader.

The MCP method signatures are exactly:

```text
search(query, top_k=5, project?, site?, domain?, cross_domain?)
unresolved(limit=20, project?, site?, domain?, cross_domain?)
related(ledger_id, project?, site?, domain?, cross_domain?)
```

Raw key presence distinguishes omission from explicit null. Connector aliases
map statically and one-to-one. Success is `convmem.raw-evidence.v3`; errors are
the exact seven-code `convmem.error.v1` contract.

The direct read-only CLI is exactly:

```text
python -B -s strict_projection.py read --method search|unresolved|related --scope ABS --registry ABS --strict-config ABS --request-file ABS --expected-publication SHA256
```

The fixture mutation CLI is exactly:

```text
python -B -s strict_projection_publisher.py enroll-fixture --enrollment ABS --semantic-contract ABS --strict-config ABS
python -B -s strict_projection_publisher.py build-fixture --bundle ABS --scope ABS --registry ABS --strict-config ABS --expected-publication SHA256
python -B -s strict_projection_publisher.py rebuild-fixture --scope ABS --registry ABS --strict-config ABS --expected-publication SHA256
python -B -s strict_projection_publisher.py rollback-fixture --scope ABS --registry ABS --strict-config ABS --expected-publication SHA256 --target-generation gen2_SHA256
python -B -s strict_projection_publisher.py recover-fixture --scope ABS --registry ABS --strict-config ABS --expected-publication SHA256
```

The connector-launch v2 manifest has exactly:

```text
schema, python_executable, python_executable_sha256, strict_server_path,
strict_server_tree_sha256, working_directory, scope_file, registry_file,
strict_config_file, scope_sha256, registry_sha256, strict_config_sha256,
service_home, path_value, lang, lc_all, temp_directory,
setpriv_executable, setpriv_sha256, seccomp_filter_file,
seccomp_filter_sha256, runtime_distribution_sha256, launch_policy_sha256,
manager_policy_sha256, launch_payload_sha256
```

Its production launch tuple is exactly `[SETPRIV, "--no-new-privs",
"--seccomp-filter", FILTER, PYTHON, "-B", "-s", STRICT_SERVER]`, without a
shell. T4 validates the same data through injected transport and never executes
that tuple. The child environment is constructed from empty with exactly
`CONVMEM_MCP_PROFILE=openclaw-strict`,
`CONVMEM_BOUND_READ_SCOPE_FILE`,
`CONVMEM_PROJECT_BINDING_REGISTRY_FILE`,
`CONVMEM_STRICT_CONFIG_FILE`, `HOME`, `PATH`, `LANG`, `LC_ALL`, and `TMPDIR`
from the manifest. No ambient environment copy or
loader/proxy/provider/token variable is accepted.

The fixed fixture platform port consists only of:

- `sample_clock()` returning `{boot_id, wall_time, boottime_before_ns,
  boottime_after_ns}`;
- `peer(connection_id)` returning `{uid, gid}` from the harness connection
  table;
- `access(role, path, operation)`, where operation is one of `read`, `create`,
  `replace`, or `lock`;
- `spawn(role, argv, env, cwd, fd_roles)`, where role is one of `supervisor`,
  `gateway`, `agent`, `strict_server`, or `model_worker`;
- `next_event(handle)` returning the closed `{kind, bytes_b64, exit_code}`
  shape with kind `ready`, `stdout`, `stderr`, `exit`, or `hang`;
- `manager_start(slot_id, activation_id)`,
  `manager_stop(invocation_id)`, and `manager_observe(invocation_id)`, whose
  observation is exactly `{manager_boot_id, unit_invocation_id,
  containment_id, terminal, populated}`.

The model-worker argv is exactly `["/fixture/bin/model-worker"]`. Agent
success bytes are exactly
`{"fixture":"protocol-only","text":"synthetic answer"}` with exit 0. Fixed
ports `49152`/`49153` and `openai-completions`/`fixture-model` may appear only
as inert schema-validation data. They must never be connected to or used to
select a provider.

The exact virtual access meanings in Architecture §6.5.8 remain binding:
publisher/qualifier/operator may access synthetic private authority and
governance inputs; controller may read them for qualification and write
control/slot/receipt paths; supervisor may read pinned public files and use
inherited lease/control roles; runtime may read only public
manifest/projection plus scope/registry/strict-config and may write only its
disposable state/temp paths. Public files are read-only to every runtime role.

## 7. Step-by-step implementation

Perform the following stages in order. Keep each checkpoint coherent, commit
it, and push it immediately. Do not start the next stage while its predecessor
has a contract failure. These checkpoints refine T0–T5 without changing them.

### Step 0 — Bind the workspace before editing

1. Obtain Ryan's Execute grant naming `REVIEWED_PLAN_SHA` and T0–T5. If it is
   absent or cites another SHA/scope, stop.
2. Create an isolated implementation worktree and branch from
   `CODE_BASELINE_SHA`. Do not silently substitute current `main` or rebase the
   implementation target.
3. Install the repository-local Git configuration required by `AGENTS.md`.
4. Record the clean base commit, branch, upstream, and complete tracked-file
   inventory.
5. Verify that the only source authority for the build is the exact two-plan
   packet named above.
6. Predeclare the exact allowed-file checker and protected-byte comparison.
7. Do not run OpenClaw, touch live ConvMem data, or configure/provision host
   runtime resources.

**Exit:** exact grant present; clean isolated branch at the exact baseline;
zero implementation changes; allowed/protected inventories recorded.

### Step 1 — T0a: make refusal and runner preflight exist first

1. Add the test-only fixture-manifest schema and the closed runner entrypoint
   `tests/fixtures/openclaw_strict/run_isolated.py`.
2. Implement its exact CLI only:

   ```text
   --source-commit HEX40 --plan-sha HEX40 --runtime-root ABS --suite all
   ```

   Reject unknown/missing arguments, dirty or untracked inputs, arbitrary
   commands, arbitrary mounts, caller selectors, and a plan SHA other than the
   reviewed grant.
3. Make production controller start, supervisor entrypoints, and ordinary
   plugin registration refuse `runtime_not_qualified` before any OS action.
4. Inventory the supplied runtime prefix before importing implementation code.
   Bind interpreter, stdlib, packages, Node, ELF loaders, shared libraries,
   locales, and loaded data in the one canonical
   `test_runtime_tree_sha256`, including `sysroot/usr/`.
5. Freeze the mount plan: read-only `/src`, `/runtime`, inventoried
   `sysroot/usr` at `/usr`, and only `/bin -> usr/bin`, `/lib -> usr/lib`, and
   `/lib64 -> usr/lib64` as sandbox aliases. No host `/usr`, loader cache,
   `LD_LIBRARY_PATH`, `PYTHONHOME`, added mount, or fallback.
6. Freeze the bubblewrap boundary: nonprivileged user/PID/IPC/net/UTS
   namespaces, no capabilities, new session, parent-death exit, private
   proc/dev, no host root/home/run/sockets, private 256 MiB `/tmp`, and one
   new mode-0700 `/fixture` root.
7. Use the exact mandatory flags from Architecture §6.5.8 / Execution §5.1,
   including `--disable-userns`, `--assert-userns-disabled`,
   `--cap-drop ALL`, `--new-session`, and `--die-with-parent`. Never use
   `--as-pid-1` or a permissive fallback.
8. Build the child environment from empty with exactly `HOME`, `TMPDIR`, the
   three XDG paths, `PATH=/runtime/bin:/usr/bin`, `LANG=C.UTF-8`,
   `LC_ALL=C.UTF-8`, `PYTHONDONTWRITEBYTECODE=1`, and
   `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` as specified by Execution §5.1. Close
   every inherited FD except stdio.
9. Implement pre-import checks for namespace identity, absent external routes,
   outside-root synthetic canaries, read-only mount writes, inherited sentinel
   env/config/credentials, unexpected FDs, runtime version/resolution, and
   every loaded regular file's membership.
10. Add failing outer-boundary-safe mutants for an exposed synthetic canary,
    host-`/usr` bind, missing/changed dependency, added unlisted file, wrong
    namespace/env/FD observation, arbitrary suite selection, and production
    fake selection.

**Exit:** preflight rejects every bypass before strict imports; no host
fallback exists; production selection refuses; the runner still has no
integration behavior to certify.

### Step 2 — T0b: close schemas, vectors, artifacts, and independent oracles

1. Add the exact Gate B/C schemas and validate filename-to-schema-literal
   agreement.
2. Add deterministic `protocol_fixture` specimens and known-answer vectors for
   every digest, ID, record, cumulative multi-head lineage, enrollment,
   publication, grounding, receipt, and control variant.
3. Require two independent parsers to agree on canonical bytes and digests.
   Reject malformed, reordered, duplicate, unknown, wrong-type, and omitted
   required-null inputs.
4. Preserve exact legacy envelope bytes. Do not rewrite equivalent provenance.
5. Implement the exact five component inventories and test-owned reference
   walkers. The reference owns literal expected sets and computes canonical
   bytes/hashes without asking production code.
6. Mutate disposable copies only. Every included file/mode mutation and every
   protected helper/schema mutation must affect or invalidate the proper
   result. An excluded test mutation changes the fixture manifest but not a
   component hash.
7. Require the omitted-`canonical_json.py` mutant to fail even when the wrong
   implementation inventory and recomputed wrong digest agree.

**Exit:** case 58's independent membership and hash oracles are executable;
the fixture cannot self-attest production packaging.

### Step 3 — T1: implement scope, identity, grounding, and canonical state

Implement in dependency order:

1. `bound_read_scope.py`: strict config/scope/registry parsing, IDNA2008/STD3
   site normalization, trusted project binding, source registration, omission
   policy, selector narrowing, row authorization, and neighborhood
   authorization.
2. `strict_grounding.py`: legacy verifier composition without modifying it,
   exact byte selectors, roots/edges/outputs/receipts, authenticated issuer
   handling, and original-admission qualification.
3. `strict_evidence_state.py`: occurrence/logical/assertion identities,
   event-retry collision handling, source rejection, canonical semantic/final
   hashes, dispositions, cumulative admission validation, eligibility, and the
   single complete-bound reducer.
4. Add independent reducer/qualifier references and negative mutants for scope
   ceiling removal, selected-out conflicts, same-check forks, late assurance
   upgrade, retained-history removal, terminal precedence, supersession, and
   the unresolved predicate.

**Exit:** T1 known answers and negative controls pass inside the closed runner;
no query-time reducer or mutable/global store exists.

### Step 4 — T2: implement conserved authority and publication

1. Implement explicit empty-root enrollment and genesis.
2. Implement cumulative authority sets/parents, source cutoff, operation
   idempotence, dispositions, and exact publication CAS.
3. Order mutations exactly: fence; persist intent/source operation; commit
   authority to its new head and unavailable serving state; independently
   qualify/build; atomically publish that exact head or remain unavailable.
4. Run independent fresh-process cold validation of state, rows, graph,
   grounding, citation, and qualification before public opening.
5. Implement serving-only rebuild, rollback, and recovery with current-head,
   current-contract, and persisted-expiry preservation.
6. Inject faults at every file write, fsync, rename, pointer, admission, and
   publication boundary, including ambiguous crash points and retries.
7. Prove no hash cycle, ABA publication success, old-head restoration, lost
   disposition/witness, implicit add, or lease renewal.

**Exit:** T2 crash/retry/rebuild/rollback/recovery matrices pass in two fresh
synthetic roots; ambiguity produces unavailable/quarantined state.

### Step 5 — T3: implement the read-only CLI and strict MCP surface

1. Implement the exact lexical kernel, integer scoring, tie rules, limits, and
   deterministic serialization from Architecture §6.5.5.
2. Implement selector-only display over canonical full-bound state.
3. Implement `related` as the exact bounded target neighborhood plus queried-
   head verification support. Deny the whole request when support is
   unauthorized, unavailable, or oversized.
4. Emit exact `convmem.raw-evidence.v3` success values and the seven-code
   `convmem.error.v1` contract, including qualification, basis, canonical
   state/hash, and honest completeness fields.
5. Add the exact direct file CLI verbs `enroll-fixture`, `build-fixture`,
   `rebuild-fixture`, `rollback-fixture`, and `recover-fixture`, plus the
   direct read command frozen in §6.1 above. Do not add
   `--expected-generation`, a generic metadata writer, environment override,
   or live-source mode.
6. Add `openclaw_strict_server.py` with only the three fixed methods. Ensure
   `resources/list` and `resources/templates/list` return empty collections and
   `resources/read` resolves no ConvMem URI.
7. Prove read-only opening causes no mtime, file, or cache change and imports no
   general config, model, Chroma, writer, publisher, controller, or supervisor.
8. Test omission versus explicit null by raw key presence and test exact
   selector/limit/depth metamorphic behavior.

**Exit:** exact three-tool/zero-resource inventory; deterministic v3 results;
private qualification and public runtime opening are separately proved and
cryptographically bound.

### Step 6 — T4: implement the uninstalled connector core

1. Implement only the connector library and test-owned injected `spawn`
   transport. Do not register with or launch OpenClaw.
2. Validate connector-launch v2, all runtime/policy/component digests, exact
   argv, empty-built environment, cwd, paths, modes, ownership assumptions,
   and launch payload hash.
3. Preserve the exact launch tuple from Architecture §4. A scripted filter
   load failure must stop before the logical Python child. Use no real
   `setpriv`, filter, gateway, agent, provider, or model.
4. Map the three fixed aliases one-to-one. Reject dynamic names and paths.
5. Forward raw evidence only inside untrusted tool-result blocks. Never
   execute content.
6. Exercise one active tool call plus eight pending, 10-second deadline,
   128-KiB frame, 64-KiB server response, cancellation, partial frames, no late
   success, and no retry after uncertain delivery.

**Exit:** connector framing and bounds pass with a fixed synthetic response;
no claim of inference, authentication, provider, OpenClaw, filter, or host
compatibility.

### Step 7 — T5: implement fake controller, manager, and supervisor cores

1. Implement stable-slot lifecycle, peer policy, lock order, launch-tuple
   validation, turn state, watchdogs, deadlines, release, revoke, retirement,
   and quarantine through the fixed `FixturePlatform` ports.
2. Use only the logical identities operator `1000/1000`, controller `0/0`,
   supervisor `0/0`, and runtime `1001/1001`. Do not create host users, groups,
   services, sockets, privileges, filters, or mounts.
3. Implement exactly one turn, no turn queue, and at most 256 accepted turn
   identities. Keep this separate from the connector tool queue.
4. Script clocks/boots, peer identity, access, process, and manager events.
   No ad hoc OS call may replace a port.
5. Keep manager membership independent of controller/supervisor state. Test
   supervisor death/hang, stop acknowledgement, cleanup callback, detached
   descendants, outstanding model work, partial independent removal, stale or
   unknown observation, and genuine final emptiness.
6. Test release/revoke linearization while a consumer is blocked, stable turn
   IDs, cancellation, deadline, partial-frame discard, crash, restart,
   same-boot freshness, and new-boot clock review.
7. Deny runtime access to all private qualification, issuer, governance, and
   control paths. Test production refusal even with an unwrapped specimen.

**Exit:** cases 33/35/45/46/48/53–55 and fake portions of 57 pass with
independent manager traces. No Gate D or Gate W claim is made.

### Step 8 — Run the one allowed acceptance entrypoint

Run only after T0–T5 are committed in a clean implementation tip and the exact
test-runtime prefix has been separately supplied:

```bash
python -I tests/fixtures/openclaw_strict/run_isolated.py --source-commit IMPLEMENTATION_SHA --plan-sha cd9d2698b7423f907b552bc9118a0af523018ca9 --runtime-root /tmp/convmem-openclaw-test-runtime --suite all
```

Inside the boundary, `--suite all` means exactly these three commands:

```bash
/runtime/bin/python -m pytest -q -p no:cacheprovider --basetemp=/fixture/pytest-strict tests/test_bound_read_scope.py tests/test_strict_grounding.py tests/test_strict_evidence_state.py tests/test_strict_projection_publisher.py tests/test_strict_projection.py tests/test_strict_projection_recovery.py tests/test_mcp_openclaw_strict.py tests/test_strict_snapshot_revocation.py tests/test_openclaw_lifecycle_config.py tests/test_openclaw_connector_contract.py tests/test_openclaw_activation_controller.py tests/test_openclaw_activation_supervisor.py tests/test_openclaw_strict_packet_contract.py
/runtime/bin/node --test integrations/openclaw-convmem-reader/test/connector.test.mjs
/runtime/bin/python -m pytest -q -p no:cacheprovider --basetemp=/fixture/pytest-legacy --deselect=tests/test_agent_run_ledger.py::test_v8_kiro_hook_adapter_fail_open --deselect=tests/test_agent_run_ledger.py::test_v6_git_facts_non_git_cwd --deselect=tests/test_agent_run_ledger.py::test_q7_hook_failure_writes_stderr --deselect=tests/test_agent_run_ledger.py::test_q4_hook_two_missing_id_starts_same_cwd tests/test_site_filter.py tests/test_milestone_c.py tests/test_agent_run_ledger.py tests/test_query_ledger_lookup.py tests/test_query_search_harden.py tests/test_ledger_related.py tests/test_unresolved_payload.py tests/test_file_generation_store.py tests/test_file_generation_validate.py tests/test_governed_recovery_and_writers.py tests/test_governed_writer_gate.py tests/test_shadow_writer_coverage_scan.py tests/test_provenance.py tests/test_provenance_continuity.py
```

The runner must validate the exact commands, selected node IDs, and four
deselections against a test-owned constant before collection. It must reject
full discovery, `-k`, `--ignore`, another deselection, a missing selected
safety node, a hook/Git/systemd launch, or a strict writer/config import.

Do not report a full-repository PASS or coverage for the four excluded nodes.
Report all four IDs and the absence of a full-repository run. Every other test
in the named legacy files remains selected. No selected strict safety test may
be skipped.

The pre-provisioned runtime must resolve exactly CPython 3.13.12, Unicode
15.1.0, Node 26.9.0, MCP 1.28.1, and idna 3.18, with remaining test
dependencies from the baseline `requirements.txt`.

Each suite has a 600-second wall deadline and 16,777,216-byte combined output
limit. Private `/tmp` is exactly 268,435,456 bytes. Record monotonic elapsed
time, combined output bytes, maximum sampled `/tmp` allocation, and sampling
interval. Timeout, output overflow, or ENOSPC fails. Do not raise a limit.

Wait for PID-namespace termination before disposal. If termination is
uncertain, retain the exact root for operator inspection. Deletion is not
recovery.

Run `git diff --check` outside the exported tree. Do not run the acceptance
commands directly on the host and call them acceptance.

### Step 9 — Reproduce and package evidence

1. Re-run the exact isolated entrypoint in two fresh roots from the clean
   implementation commit.
2. Compare every changed filename with the allowed list and every protected
   file's bytes and mode with `CODE_BASELINE_SHA`.
3. Return the full canonical source, fixture, test-runtime, and five component
   entry arrays and hashes.
4. Return actual interpreter, Unicode, Node, MCP, idna, module, loader, and
   pytest-plugin inventories.
5. Return selected node IDs, exact commands, results, skips, four exclusions,
   capacity measurements, subprocess trace, and proof no full discovery ran.
6. Return each independent reference and each failing negative control,
   including case 57 bypasses and case 58 wrong-inventory mutants.
7. Return crash/fsync/rename/retry, clock/boot, race, blocked-consumer,
   manager-membership, stale/unknown/nonempty retirement, and production-
   refusal outcomes.
8. Return read-only import/file/network/FD evidence and the exact three-tool,
   zero-resource inventory.
9. Label every observation `STATIC`, `FAKE`, `DISPOSABLE_KERNEL`, or `REAL`.
   Never present fake/static evidence as actual OpenClaw, authentication,
   provider, host containment, sealed distribution, live-data, or production
   proof.
10. Commit and push every coherent correction before handoff. Return branch,
    exact tip, upstream, and push state.

**Exit:** evidence is reproducible at one clean implementation SHA; BUILD
scope is unchanged; TEST may be reported PASS only for the assigned B/C
acceptance set.

## 8. Acceptance map

Architecture §13 cases 1–58 are normative. Report results by owner; never
compress them into an unsupported “58 passed” claim.

- Gate B: cases 1–27, 40–44, 49–52; strict-server part of 47;
  private/public qualification part of 55; preflight/artifact parts of 57–58;
  builder/server inventory parts of 58.
- Gate C fake: connector/lifecycle parts of 33, 35, 45, 46, 48, 53, 54;
  pre-activation qualification part of 55; fake lifecycle and production
  refusal parts of 57; remaining component inventory parts of 58.
- Gate D real, outside this build: repeat 1–4 and run 28–36, 38–39, 45–47,
  53–55 against the actual sealed runtime.
- Gate W, outside this build: case 56 plus 41–44, 49, 51–52 through separately
  reviewed governed CLI code and disposable synthetic stores.
- Gate E, outside this build: case 37 under a separate live-phase grant.

Every safety obligation needs an independent reference or negative control
whose removal of enforcement fails. Passing implementation-derived expected
values against implementation-derived actual values is not independent proof.

## 9. Deferred items and fixed routing

The following classifications are frozen. They do not authorize redesign:

- `B-FIXTURE` — SAFE TO DEFER INTO ISOLATED IMPLEMENTATION. Implement the
  fixed harness, ports, and fake cores; case 57 and the assigned lifecycle
  cases decide conformance. Need for a real runtime, selectable fake, or new
  containment/retirement semantics stops BUILD for Codex/Kiro.
- `B-DIGEST` — SAFE TO DEFER INTO ISOLATED IMPLEMENTATION. Implement the exact
  sets and case 58 oracles. Any guessed membership, unbound import, or fake
  production attestation stops BUILD.
- `I-IMPLEMENTATION` — SAFE TO DEFER INTO ISOLATED IMPLEMENTATION. Implement
  and repair the frozen modules/schemas/tests. Any needed semantic, schema,
  protected-writer, or acceptance change stops BUILD.
- Capacity — TEST work at fixed limits. A needed limit change returns to
  Codex/Kiro with measurements; it is never silently expanded.
- `C-RUNTIME` — LIVE-DATA/PROMOTION BLOCKER. A separate Gate D packet must
  qualify a real local-only authentication/provider route. The fake does not
  address it.
- `D-CONTAINMENT` — LIVE-DATA/PROMOTION BLOCKER. A separate Gate D packet must
  qualify real UID/peer/mount/FD/filter/network/manager enforcement.
- `D-DISTRIBUTION` — LIVE-DATA/PROMOTION BLOCKER. A separate Gate D packet must
  supply and qualify the sealed runtime/model/worker inventory.
- `W-PRODUCTION` — LIVE-DATA/PROMOTION BLOCKER. A separate exact-baseline Gate
  W packet owns governed admission and all enumerated writer/backup/restore
  callers.
- `U-VALUE` — NON-BLOCKING UNCERTAINTY. A later Gate D-V packet predeclares and
  runs the 32-run paired value experiment. T0–T5 uses only fixed lexical
  known-answer tests.

## 10. Maintenance watch-coverage gate

Future agents must be able to retrieve the knowledge needed to understand,
maintain, test, and safely modify the combined ConvMem + OpenClaw system
without a human remembering which repository areas to attach as context.
Meeting this requirement needs both path observation and eligible-content
indexing. Merely adding a directory to `[watch].extra_paths` is not coverage
when `adapters.detect.get_parser()` returns no parser for its files.

This is a separate maintenance gate, outside T0–T5. It does not authorize a
generic repository parser, live config change, watcher restart, bulk index,
production corpus mutation, or expansion of the strict OpenClaw runtime.
Codex/Kiro must approve the repository-knowledge ingestion design; Ryan must
grant its implementation and any live configuration change.

### 10.1 Current-state finding

At the baseline inspected for this brief:

- `convmem watch` recursively observes `[watch].paths` plus
  `[watch].extra_paths`, debounces eligible file events, and dispatches the
  ordinary `convmem index --file PATH` path in a subprocess.
- `is_watchable()` requires an existing parser, rejects configured exclusions,
  and hard-skips known live databases.
- Active Markdown under `docs/inter-model/` has the
  `inter_model_doc` section adapter and is indexable.
- Ordinary Markdown outside `docs/inter-model/`, Python, JavaScript, MJS,
  TOML, generic JSON/JSON Schema, shell, and arbitrary fixture formats have no
  repository-knowledge parser. Watching their folders today observes events
  but does not index their contents.
- The live config already observes the main checkout's `docs/inter-model/`.
  It does not make the remaining inventory below retrievable.

Therefore `WATCH_COVERAGE=BLOCKED`. Do not claim that watching the repository
root, `docs/`, or another broad parent closes the gate. That would still skip
most required content and would expose unrelated files to future parsers.

### 10.2 Required watch-scope inventory

The implementation packet must materialize this inventory as a reviewed,
machine-readable allowlist. Each entry records exact repo-relative path or
closed path set, content class, parser/adapter ID and version, expected
`source_type`, watch-versus-explicit-index mode, owner, required query needles,
and exclusion reason when applicable. Directory membership alone is not an
allowlist. A wildcard may be used only when the packet freezes its expanded
file inventory and rejects additions until review.

The required included classes are:

1. **ConvMem + OpenClaw architecture and plans.** Include exact content from
   `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md` and
   `docs/plans/EXECUTION-openclaw-convmem-integration.md` at
   `cd9d2698b7423f907b552bc9118a0af523018ca9`, this actualization brief, and
   any later reviewed STATUS/VERIFY/runbook document that expressly governs
   this integration. Superseded drafts and review copies are provenance
   references, not current instructions, and must be labeled historical or
   excluded.
2. **ConvMem implementation modules needed to operate or change the reader.**
   Include the exact eight T0–T5 modules, the four protected canonical/
   provenance/domain helpers, `requirements.txt`, reject-only `mcp_server.py`,
   and the exact component sets from §6. Include the maintenance boundary
   modules `convmem.py`, `config.py`, `watch.py`, `ingest.py`,
   `source_reconciler.py`, `adapters/detect.py`,
   `adapters/inter_model_doc.py`, `propose_decision.py`, `observe.py`, and the
   governed writer/provenance guards needed to prove non-bypass. Inclusion for
   retrieval never grants edit or runtime-import permission.
3. **Tests and fixtures.** Include `tests/fixtures/openclaw_strict/**`, the
   exact T0–T5 test files in §5, and maintenance controls
   `tests/test_watch.py`, `tests/test_watch_skip.py`,
   `tests/test_provenance.py`, `tests/test_provenance_continuity.py`,
   `tests/test_governed_recovery_and_writers.py`,
   `tests/test_governed_writer_gate.py`, and
   `tests/test_shadow_writer_coverage_scan.py`. Generated pytest output and
   disposable runtime roots are excluded.
4. **Schemas and interfaces.** Include the exact 24 Gate B and seven Gate C
   schemas from §5, the fixture-manifest schema, connector package/plugin
   manifests, and the closed CLI/MCP/platform-port definitions in §6.1. Gate W
   schemas enter only after their separate reviewed packet lands.
5. **OpenClaw integration implementation and documentation.** Include
   `integrations/openclaw-convmem-reader/package.json`,
   `openclaw.plugin.json`, `index.js`, `test/connector.test.mjs`, and safe
   operator documentation that explains the disabled registration state,
   runtime qualification boundary, and later activation procedure. Never
   index a live OpenClaw profile, auth store, workspace memory, transcript,
   or runtime state merely because it sits near the integration.
6. **Safe configuration knowledge.** Include `config.example.toml`,
   `config/agent-protocol.md`, and reviewed redacted examples that explain
   watch paths, strict profile selection, environment construction, and
   refusal behavior. Include only literal examples proven to contain no
   credential, host identity, private path, live grant, or deployment value.
   The operator's real `~/.config/convmem/config.toml` and any real OpenClaw
   configuration remain excluded.
7. **Execution, acceptance, and operational documentation.** Include this
   brief, `AGENTS.md`, `docs/MODEL-WORKFLOW.md`,
   `docs/CODEX-DEEPSEEK-VERIFY.md`, `docs/RECOVER.md`, `docs/MILESTONE-F.md`,
   `docs/plans/ARCHITECTURE-watch-incremental-index.md`,
   `docs/plans/INVARIANTS-watch-incremental-index.md`,
   `docs/plans/EXECUTION-watch-incremental-index.md`, and the applicable
   Git-hygiene/always-available-fallback plans. Include the architecture-
   maintenance references `docs/builder-reference/ousterhout-builder-digest.md`,
   `manning-builder-digest.md`, `zeller-builder-digest.md`, and
   `hard-parts-builder-digest.md`. Include the exact acceptance map, negative
   controls, rollback/recovery procedure, and evidence format used by the
   implementation tip.
8. **Maintenance and troubleshooting knowledge.** Include reviewed material
   explaining parser detection, watch path loading, file-event debounce,
   exclusion handling, source reconciliation, index-child containment,
   provenance validation, proposal/approval separation, common refusal
   reasons, and how to prove coverage drift. Active incident handoffs enter
   only when they concern this combined system and are explicitly marked with
   freshness/current-state metadata. Do not recursively admit all
   `docs/inter-model/` or all historical incident archives as OpenClaw system
   knowledge merely because the global watcher observes them for other uses.

Planned files enter the inventory only after they exist as reviewed tracked
bytes. Every required item must resolve to a clean Git commit or to a reviewed
immutable reference. Untracked drafts, `/tmp` reports, review bundles, and a
developer's current working copy cannot satisfy coverage.

The inventory audit begins from the complete tracked repository tree and must
classify every file under each named root as included, excluded, or unrelated,
with a reason. No unclassified file is silently accepted or silently counted
as covered. Changes to a required module's local import/dependency closure,
test ownership, schema inventory, or operational-document link set fail the
coverage check until the reviewed inventory is updated.

### 10.3 Mandatory exclusions

The allowlist and adapter must reject these classes before content parsing or
embedding:

- **Credentials and secrets:** `.env*`, tokens, cookies, API keys, auth stores,
  SSH/GPG material, password files, real provider settings, credential-bearing
  command output, and real ConvMem/OpenClaw user configuration.
- **Private authority data:** production authority roots, admitted source
  artifacts, private grounding/citation/issuer stores, governance intents,
  capture receipts, approval files, protected backup/recovery evidence, and
  any real strict lineage or publication state. Synthetic inert fixtures are
  allowed only through their reviewed fixture inventory and remain labeled
  synthetic.
- **Live databases and corpora:** Chroma directories, SQLite databases and
  WAL/SHM siblings, live transcript/session stores, corpus exports,
  `knowledge_units.jsonl`, `processed.json`, inventory state, live source
  trees, and mutable OpenClaw memory/workspaces.
- **Caches and transient state:** `.git`, worktree administrative state,
  `__pycache__`, `.pytest_cache`, coverage caches, virtual environments,
  `node_modules`, build/dist/temp directories, locks, sockets, PIDs, service
  state, and editor caches.
- **Generated artifacts that are not project knowledge:** review ZIPs,
  generated manifests and run outputs, compiled/minified bundles, copied
  runtime trees, test reports, screenshots, logs, coverage output, temporary
  canaries, and duplicate review/worktree copies. A generated artifact may be
  indexed only when a separate reviewed contract declares it canonical
  knowledge and defines its provenance and supersession behavior.
- **Unrelated repository material:** other arcs, client/site material, generic
  historical debates, unrelated tests/config, vendored dependencies, and
  repository files outside the frozen combined-system inventory.

Exclusions win over includes. Symlinks, traversal, path aliases, case tricks,
and a matching filename under an unapproved root fail. A newly added file in
an included directory is excluded until the machine-readable inventory is
reviewed or its closed expansion is regenerated and accepted.

### 10.4 Positive coverage verification

Run this verification only in a separately granted disposable ConvMem data
root with synthetic content and no live corpus/config. The eventual design
must supply an executable harness; prose or `is_watchable()==true` is not
evidence.

1. Freeze the reviewed inventory, adapter versions, clean source commit,
   isolated config, and empty derived index state.
2. For every included content class and parser, select at least one tracked,
   safe representative and one negative representative. For closed exact file
   sets, verify every path resolves and hashes to the committed bytes.
3. Prove the unique positive canary is absent from retrieval before its folder
   is added to the isolated watch set.
4. Add one previously unwatched relevant folder to the isolated
   `[watch].extra_paths`, restart the isolated watcher so configuration is
   reloaded, and create or modify a tracked eligible file containing a unique
   nonce plus an unambiguous maintenance statement.
5. Observe one debounced watch event, one normal `index --file` dispatch, a
   successful eligible-file parse, and the normal source-scoped durable ingest
   result. No direct adapter-to-store shortcut is allowed.
6. Query through normal ConvMem retrieval using the unique nonce and a natural
   maintenance question. Require the eligible content to be returned with the
   exact committed source path, content hash, adapter/source type, provenance
   envelope/commitment, and current text.
7. Modify the same eligible file in a new clean synthetic commit, wait for the
   watch path, and require current retrieval plus the normal source-scoped
   supersession/reconciliation behavior. The old text cannot remain an
   unlabeled current duplicate.
8. Repeat from a second fresh isolated data root and require the same inventory
   membership, parsed units, provenance identities, and retrieval needles.
9. Report watched roots, eligible and rejected files, hashes, event/dispatch
   counts, index result, retrieval evidence, derived-state mutations, timings,
   and any skips. A folder is covered only when this end-to-end proof passes.

At minimum, acceptance must demonstrate architecture/plan Markdown, Python
source, Python tests/fixture text, JSON Schema/interface definitions,
JavaScript/MJS connector code, safe TOML/Markdown configuration examples, and
operational Markdown. If one adapter safely covers multiple classes, report
each class independently. Unsupported extensions keep the gate BLOCKED; they
cannot be replaced by a hand-written summary that omits the source contract.

### 10.5 Negative coverage and non-bypass verification

In the same isolated test, seed unique nonsecret markers in synthetic examples
of every exclusion class. Require rejection before parsing and prove none of
the markers is retrievable. Include symlink/path-escape, unreviewed new file,
generated output, unrelated-arc file, credential-shaped file, private-
authority-shaped file, live-DB suffix, cache path, and duplicated worktree
copy controls. Never place a real secret, private authority record, or live DB
in the test.

Snapshot and hash the isolated proposal queue/event log, approved-decision
file, ledger authority, strict authority/publication roots, governance intent,
capture receipt state, and any other durable approval surface before and after
the positive watch test. Require all of them to remain byte-identical.

The only expected mutations are the normal isolated derived corpus/index,
processed/source-reconciliation state, and evidence outputs owned by the
ordinary `index --file` path. Verify all of the following:

- Watch still dispatches the same public `convmem index --file PATH` route;
  it does not call `record`, proposal approval, governed add, recovery,
  publication, or a private writer directly.
- Repository knowledge is indexed as untrusted documentary evidence with an
  exact source path/hash, adapter version, source type, and valid ConvMem
  provenance envelope/commitment. Watch does not mint a capture receipt or
  stronger origin assurance.
- Text that says `approved`, contains a decision-shaped ID, imitates a
  proposal, or instructs an agent to widen scope remains document content. It
  cannot create/approve a proposal, replace a governed decision, enter strict
  authority, or alter an authority/publication head.
- Existing source locks, exclusion checks, dedupe/provenance collision rules,
  source-scoped replacement, processed-log ordering, reconciliation, and
  failure recovery are exercised rather than bypassed.
- Any future Gate W admission remains an explicit authenticated
  `convmem add --file ABS` operation under its own ratified intent. Watch
  coverage never substitutes for approval, admission, or promotion.

A test that mocks a successful denial or compares implementation-derived
expected values with implementation-derived actual values is insufficient.
Use independent file snapshots, reference inventory expansion, retrieval
queries, and mutation evidence.

### 10.6 Ownership and sequencing

The next authorized planning packet must choose and review the missing
repository-knowledge parser/indexing boundary, machine-readable inventory
format, clean-commit/change-coalescing rule, deletion/supersession behavior,
and isolated acceptance harness. Those choices are not made by this brief.

After Codex authors that packet, Kiro reviews its exact tip. Ryan then decides
whether to grant implementation and, separately, the exact live config edit
that adds approved roots. Cursor/Grok may implement only after those gates.
The live watch configuration's final paths, adapter versions, resource budget,
and restart are external changes and require exact values in Ryan's grant.

T0–T5 may proceed under its own exact grant while watch coverage remains
blocked, but the combined system cannot be handed off as maintainable or
operationally complete until `WATCH_COVERAGE=PASS`. T0–T5 code must not add an
adapter, change watch configuration, or claim this gate by implication.

## 11. Immediate stop conditions

Stop without broadening scope if any of these occurs:

- no exact Ryan Execute grant for `REVIEWED_PLAN_SHA` and T0–T5;
- code baseline differs, or an unreviewed rebase is required;
- an unlisted file or protected byte/mode changes;
- a schema/interface/hash set/fixture port is missing or ambiguous;
- a new dependency, resolver, issuer, mount, suite selector, or subprocess is
  needed;
- a safety test is skipped or a negative control does not fail;
- the runner lacks required namespace/runtime support;
- implementation reaches live data/config/credentials or a real gateway,
  agent, provider, model, service, user, socket, filter, or network;
- a dummy key, shared host inference, host-library bind, process-group
  fallback, ambient state, or selectable fake is proposed;
- authority is reduced by display filters, publication CAS uses only a
  generation, provenance is upgraded late, recovery implies add, legacy
  consent is inferred, or old authority/expiry is restored;
- supervisor/controller state is used to manufacture manager emptiness;
- fake/static evidence is offered as actual containment, auth, distribution,
  live-data, or promotion evidence.
- watch-folder observation is presented as retrieval coverage without an
  eligible parser and end-to-end query result;
- a broad repository root, live config, secret/private authority path, live
  database/corpus, generated state, or unrelated material is added to watch;
- watched document text is allowed to create authority, approval, admission,
  capture, or promotion state;
- T0–T5 implementation attempts to design or implement the separately gated
  repository-knowledge adapter or live watch configuration.

On a test provisioning failure, preserve the contract and request the missing
pre-provisioned bytes/environment. On a coding defect, correct the code inside
scope. On a contract defect, stop for Codex/Kiro. Do not lower a control to
obtain a green result.

## 12. Required handoff

Return a handoff that a reviewer can verify without reconstructing the run:

```text
PLAN_SHA: cd9d2698b7423f907b552bc9118a0af523018ca9
CODE_BASELINE_SHA: 7809f20dc53d9dd19f765c3ec3214a3df54ca5bf
IMPLEMENTATION_BRANCH: <exact>
IMPLEMENTATION_SHA: <exact>
PUSH_STATE: <exact remote ref and status>
BUILD_SCOPE: T0-T5_ONLY
TEST: PASS | BLOCKED | NOT_YET_RUN
LIVE_DATA: BLOCKED
PROMOTION: BLOCKED
WATCH_COVERAGE: BLOCKED | PASS | NOT_YET_RUN
WATCH_INVENTORY_REVISION: <exact commit/hash or BLOCKED>
WATCH_CONFIG_CHANGE: NONE | <separately authorized exact change>
CHANGED_FILES: <complete allowed-list comparison>
STRICT_SUITE: <result, selected node ids, time, bytes, tmp peak>
CONNECTOR_SUITE: <result, selected node ids, time, bytes, tmp peak>
LEGACY_SUITE: <result, selected node ids, four exclusions, time, bytes, tmp peak>
FULL_REPOSITORY_SUITE: NOT_RUN
CASE_57: <preflight, containment, manager, refusal, bypass evidence>
CASE_58: <five arrays/hashes and mutation evidence>
REPRODUCTION: <two fresh roots and matching results>
DEFERRED_ITEMS: <observations routed without redesign>
WATCH_EVIDENCE: <isolated path-to-index-to-retrieval and non-bypass result>
BLOCKERS: <none, or exact failed frozen criterion>
```

Do not merge, activate, configure, provision, access live data, promote, or
claim complete-integration readiness. A successful T0–T5 result can change
only `TEST` for the bounded B/C fixture; `LIVE_DATA` and `PROMOTION` stay
blocked until their separately owned gates pass.

The handoff must state that watch coverage is blocked until its separately
reviewed design and executable isolated verification pass. Do not omit the
gate merely because T0–T5 tests pass.

Grok can begin implementation without making an architectural decision only
after Ryan issues the exact bounded Execute grant. Known deferred issues do
not authorize Grok to redesign the architecture.

**TL;DR:** [Arc none] Implement only the exact `cd9d2698` T0–T5 disposable
fixture after Ryan's matching Execute grant. Follow Steps 0–9 in order, edit
only the frozen allowlist, run only the closed three-suite runner, return the
independent case 57/58 and gate evidence, and stop for Codex/Kiro rather than
making any architectural choice. The combined system also requires the §10
watch inventory, isolated retrieval proof, and governance non-bypass proof;
that separate gate is currently BLOCKED. TEST is not yet run; LIVE-DATA and
PROMOTION remain blocked.
