# Execution Plan — OpenClaw bounded ConvMem reader

**Status:** **BUILD PASS and TEST PASS for the frozen T0–T5 fixture contract at accepted
implementation `8010fb060c2edc29e1b09d7a30b1a1da2689d489`. M11 MERGE READINESS PAUSED FOR
CURRENT-MAIN RECONCILIATION. LIVE-DATA BLOCKED; PROMOTION BLOCKED.** This plan-only correction
does not authorize reconstruction, regression execution, merge or any runtime action; exact-tip
review and a new Ryan integration grant are required first.
BUILD is not complete-integration readiness and does not pass any of those later gates.

**Date:** 2026-09-23

**Arc:** ConvMem Switchboard

**Architecture:** [revised architecture](ARCHITECTURE-openclaw-convmem-integration.md), especially
§§6.5, 14, 17–18. The preceding runner and node-evidence correction history remains in §§10.3–4.
The current plan-only reconciliation starts from current `origin/main` at
`9193f5ec744f059d07a20612489b210527b5660a`; review the two parent files together.
The retained Astra report reviews the earlier `0f1216f` revision, not this correction:
`/tmp/astra-final-0f1216f7249c0066dafb6fc9ef2aafa9845a7264/STAGE-1-REVIEW.md`, SHA-256
`d3d330b6195263e86f0c648f446ca9b4dbbf648983ee2ec2ad9aeacc7cc2026a`.
It found B-FIXTURE and B-DIGEST, corrected by `2aa66a8`. Section 10.3 records the later runner
closure/suite repairs; §10.4 records the completed M8 evidence correction. This edit addresses
only M11 current-main reconstruction in §10.5; the fixture, manager and five component sets remain
frozen.

**Baselines:** Original accepted code baseline
`7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`; accepted bounded implementation
`8010fb060c2edc29e1b09d7a30b1a1da2689d489`; proposed M11 integration baseline
`9193f5ec744f059d07a20612489b210527b5660a`. This revision changes plans only. A new grant must
name the reviewed parent and overlay, all three revisions above, the new branch, rebound runtime
and durable evidence root. No silent rebase or merge of the historical implementation target.

**Roles:** Cursor using Grok 4.5 High remains the sole implementation lane and is paused. Codex owns
architectural editing, branch/worktree creation, runtime provisioning and independent verification.
Kiro owns required binary design/scope review; Ryan alone grants resumed implementation, merge,
runtime/config changes, data admission and promotion.
OpenClaw is the eventual bounded runtime and has no governance authority.

## 1. Consequence and bounded deliverable

The entire authorized-to-request build scope is the T0–T5 synthetic, read-only file evidence
reader, three-tool MCP adapter, uninstalled connector and controller/supervisor protocol cores,
using Architecture §6.5.8's fixed injected ports. It is not a real OpenClaw runtime build.
Actual manager/privilege/mount/socket/filter adapters, production packaging, authentication,
provider/model selection, deployment, Gate W writers, live data, migration, capture, channels and
promotion are non-goals. No production entrypoint can select the fake. Controller `start`,
supervisor entrypoints and ordinary plugin registration refuse `runtime_not_qualified` until a
separately reviewed Gate D adapter packet; command-line refusal exits 78 before OS operations.

The bounded implementation remains architecture-complete. M11 reconstruction may begin only after
exact-tip review and a new Ryan grant naming every §10.5 input. Known deferred issues do not
authorize Grok to redesign the architecture.

Those statements concern architectural readiness, not an Execute grant. C-RUNTIME remains a
real, later-runtime blocker: the inspected credential-free authentication path rejects the
configuration. The fake has no authentication operation and cannot prove OpenClaw compatibility.

Preserve all frozen invariants: file/CLI governance, immutable single audience, exactly `search`,
`unresolved`, `related`, no resources/ask/global store, no remote inference, no ambient credentials,
no native memory/capture/automatic indexing/ACP/subagents/channels, permanent admitted
revocation/supersession, honest provenance, explicit approved-file ingestion and unchanged legacy
IDs/envelopes. No control is weakened to complete a fixture or get BUILD READY.

Gate B/C is synthetic only; Gate D actual runtime, Gate W production write boundary, Gate E live
local use and Gate D-V value experiments require their own later grants. Gate W's semantics are in
the architecture, but the initial allowed-file list below does not authorize editing legacy writers.
Existing production APIs cannot be advertised as already compliant.

## 2. Closed schema inventory

Unknown/missing/duplicate keys, noncanonical order, wrong types and omitted required nulls fail.
Architecture §§4, 6, 8 and 11 define exact fields, conditional requirements, enums, hashes and
bounds. JSON Schema must encode what it can; validators enforce graph/history/receipt/file/OS
invariants. No schema default upgrades a previous version.

Gate B schema files:

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

Gate C schema files:

```text
schemas/convmem-openclaw-connector-launch-v2.schema.json
schemas/convmem-openclaw-activation-v2.schema.json
schemas/convmem-activation-control-v1.schema.json
schemas/convmem-activation-retirement-v1.schema.json
schemas/convmem-activation-launch-policy-v1.schema.json
schemas/convmem-activation-manager-policy-v1.schema.json
schemas/convmem-controller-socket-policy-v1.schema.json
```

Gate W schema files (specified here, **not** in the initial Gate B/C edit allowance):

```text
schemas/convmem-approved-admission-v1.schema.json
schemas/convmem-admission-intent-v1.schema.json
schemas/convmem-admission-review-v1.schema.json
schemas/convmem-admission-ratification-v1.schema.json
schemas/convmem-admission-event-v1.schema.json
```

Nested fixture-scan, capture selectors, source records, provenance qualification, grounding entries,
freshness anchor, control variants and buffered-release result are closed definitions in the owning
schemas, not extensible dictionaries. The `convmem.buffered-release.v1` value is the activation's
protocol version; the committed payload is the exact control-result shape, not an extra tool.
Owner/citation reference/ID hash-input objects are fixed algorithm inputs, not additional mutable
files. The lineage's semantic artifact binds exactly the Gate B/C schema inventory, never Gate W
deployment values; Gate W must version that artifact if adding a new semantic interpretation. JSON
Schema filenames and schema literals must agree.

The additional test-only `tests/fixtures/openclaw_strict/fixture-manifest.schema.json` describes
`convmem.strict-fixture-manifest.v1` in Architecture §6.5.8. It is not a Gate B/C production schema,
not a semantic-contract input and not a runtime distribution format. Its exact fields are `schema,
artifact_kind, plan_sha, code_baseline_sha, source_tree_sha256, test_runtime_tree_sha256, components,
artifacts, manifest_payload_sha256`; `artifact_kind` is always `protocol_fixture`. The hash excludes
only its own hash field. Source inventory excludes this manifest and generated outputs to avoid a
hash cycle. No test-only artifact can satisfy a production launch or qualification check.

Registry v3 top-level fields are exactly `schema, revision, bindings`. It retains one binding with
exact fields `id, public_ref, project, domain_root, site_mode, site, non_expanding_roots,
source_registrations, lineage_id, capture_issuers, verification_producers`. A source registration
retains `id, source_class, source_identity, identity_match, authorization_domain, site,
event_id_resolver`; match is exactly `exact`. The only initial resolver is `fixture_scan_event_v1`.
Every authority domain comes from that immutable registration. Mixed-audience sources, substring
matching, caller-provided registration, production resolvers and new capture issuers are not
implementation choices.

Strict config remains exactly `schema:convmem.strict-config.v2, projection_root:ABS,
max_projection_rows:10000, max_projection_bytes:67108864, telemetry:false`; every other key fails.
It is independent of the legacy config loader.

## 3. Interfaces and ownership

Unchanged MCP signatures (raw key-presence distinguishes omission from explicit null):

- `search(query, top_k=5, project?, site?, domain?, cross_domain?)`;
- `unresolved(limit=20, project?, site?, domain?, cross_domain?)`;
- `related(ledger_id, project?, site?, domain?, cross_domain?)`.

Connector aliases are exactly `convmem_search`, `convmem_unresolved`, `convmem_related`, statically
mapped one-to-one. No resources, templates, prompts, sampling, completion or dynamic dispatch.
Success is `convmem.raw-evidence.v3`; errors retain the exact seven-code `convmem.error.v1`
contract. Output carries canonical state/hash, qualification/check eligibility and honest
selection/display completeness.

Fixture CLI is exactly Architecture §6.5.4: `enroll-fixture`, `build-fixture`, `rebuild-fixture`,
`rollback-fixture`, `recover-fixture`. After explicit empty-root enrollment every mutation requires
`--expected-publication SHA256`. No `--expected-generation`, absent-pointer bootstrap after
enrollment, authority rollback, generic metadata writer, environment override or live source. The
same read algorithms are accessible through the direct read-only file CLI specified there, without
OpenClaw/MCP.

The eventual runtime control is exactly Architecture §6.5.6: external controller start plus authenticated framed
`turn`, `cancel`, `status`, `revoke`. One turn, no turn queue, at most256 accepted turn identities,
complete-result release. Connector **tool** queue is separately one active plus eight pending
with10s deadline/128KiB frame and64KiB server response; do not confuse it with the turn protocol. No
retry/rerun after uncertain delivery.
T5 implements that protocol as a library with §6.5.8's fixed `FixturePlatform`; actual OS adapters
are outside this build. Logical peers exercise authentication rules but prove no real host identity.

Owners:

- `bound_read_scope.py`: immutable scope/registry/config parsing, strict site normalization,
  omission/selector policy and final row/neighborhood authorization.
- `strict_grounding.py`: unchanged legacy verifier composition, byte selectors, exact
  root/edge/output/receipt checks and qualification at original admission. It fetches no external
  source and grants no governance.
- `strict_evidence_state.py`: occurrence/logical/assertion identity, source rejection, canonical
  semantic/final hashes, dispositions, cumulative admission validation, check eligibility and the
  single complete-bound state reducer.
- `strict_projection_publisher.py`: fixture enrollment, authority/serving files, fences, exact
  publication CAS, fresh-process qualification orchestration, serving-only
  rebuild/rollback/recovery. It never imports a legacy writer or approves a record.
- `strict_projection.py`: private cold qualification outside the runtime plus separate public-only
  immutable opening, state/search/graph reads and direct read CLI; no publisher imports, mutable store,
  model or network.
- `openclaw_strict_server.py`: closed startup, three method registrations, argument decoding,
  delegation and serialization. `mcp_server.py` changes only to reject unknown profiles and refuse
  strict mode with the dedicated-entrypoint instruction.
- `openclaw_activation_controller.py`: peer-policy, stable-slot, manager-port, lock-order,
  external retirement/quarantine and receipt core. Production `start` refuses during B/C.
- `openclaw_activation_supervisor.py`: launch-tuple validation, turn state, watchdog, deadlines and
  release/revoke core. It cannot attest its own empty domain. Production entrypoint refuses during
  B/C; real MainPID/privilege/signal enforcement awaits Gate D.
- Connector `index.js`: fixed manifest validation, launch-tuple validation and bounded stdio
  forwarding through an injected test transport. Real registration/launch is disabled during B/C.
- Gate W's `governed_admission.py`: protected review/ratification, explicit add, durable admission
  and consent-preserving recovery; never imported by any reader or OpenClaw adapter.

Gate B/C may change only the eight new Python modules listed above (excluding Gate W's engine),
reject-only `mcp_server.py`, the Gate B/C schema lists, the existing `requirements.txt` solely to
pin reviewed `idna==3.18`, and these paths:

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

Test harness ownership is Cursor/Grok in `tests/fixtures/openclaw_strict/`: `run_isolated.py`, fake
ports, closed fixture-manifest schema, deterministic scenarios and inert specimens. It implements
the selected contract; it cannot select another isolation mechanism. Cases57–58 are owned by
`tests/test_openclaw_strict_packet_contract.py` with lifecycle/controller/supervisor/connector tests
owning their existing behavioral portions. Codex owns any necessary contract correction.

The setpriv binary/filter/runtime image remain later qualified deployment artifacts, not permission
to modify host packages. B/C uses only marked inert specimens, never a working filter or model. A
production filter distribution/manager image needs a separate qualification packet. No unlisted
code, dependency, auth route or host config is an implementation convenience.

Protected during B/C: `canonical_json.py`, `provenance.py`, `provenance_binding.py`, `domains.py`, all legacy
IDs/ledger/query/unresolved/related/Chroma/store/ingest/observe/monitor/proposal/recovery modules,
`convmem.py`, adapters, live data/config/credentials and unrelated plans. Pure
canonical/provenance/domain functions may be imported without changing their accepted bytes. Direct
reader import closure excludes every writer/config path. The prospective Gate W exceptions are
explicit later scope, not contradictory permission to modify these files now.

`test_openclaw_strict_packet_contract.py` checks schema inventory, exact production-file allowlist,
verb/API map, ownership and test/gate mapping against the reviewed packet. Compare baseline-to-tip
filenames before handoff. Reject unmatched ownership, a stale v1 pointer/activation/raw-v2 envelope,
or a requirement silently moved to a later gate.

### 3.1 Exact hash membership is not edit permission

Architecture §6.5.9 is normative. Duplicate-free `CORE` is exactly `canonical_json.py`,
`provenance.py`, `provenance_binding.py`, `domains.py`, `bound_read_scope.py`, `strict_grounding.py`,
`strict_evidence_state.py`, `strict_projection.py`, `requirements.txt`. `SCHEMAS_BC` is exactly the
24 B and 7 C filenames above; no W or fixture-manifest schema. Hash canonical sorted arrays of
`{path,mode,sha256}` with repo-relative POSIX paths and actual four-octal-digit modes; reject missing,
duplicate, extra or symlink entries.

- `builder_tree_sha256` / `builder`: CORE ∪ SCHEMAS_BC ∪ `{strict_projection_publisher.py}`.
- `strict_server_tree_sha256` / `strict_server`: CORE ∪ SCHEMAS_BC ∪ `{openclaw_strict_server.py}`.
- `supervisor_tree_sha256` / `supervisor`: CORE ∪ SCHEMAS_BC ∪ `{openclaw_activation_supervisor.py}`.
- `controller_tree_sha256` / `controller`: CORE ∪ SCHEMAS_BC ∪
  `{openclaw_activation_controller.py, openclaw_activation_supervisor.py}`.
- `plugin_tree_sha256` / `plugin`: exactly
  `integrations/openclaw-convmem-reader/{package.json,openclaw.plugin.json,index.js}`.

Protected helpers remain unmodified. Reader/server cannot import publisher/controller/supervisor;
controller may reuse supervisor protocol parsing. No automatic dependency discovery expands these
sets. Tests, fake adapters, runtime/model bytes and legacy `mcp_server.py` are excluded. Separate
fixture/source/test-runtime inventories bind fixture inputs; the eventual full Gate D image binds
its real dependency closure. An included-file mutation must affect every consumer's digest; an
excluded test mutation affects fixture, not component, hashes. Missing local import membership
stops implementation for Codex, not an improvised inventory extension.

## 4. Implementation sequence after a separate grant

Each coherent checkpoint is committed and pushed immediately. Stop on failure; no actual
gateway/agent/model launch or live config write in these steps.

### T0 — closed bytes and fixture contracts

First implement the §5.1 isolated harness and its pre-import negative controls; do not import or
run the integration until preflight passes. Create the test-only manifest and deterministic
`protocol_fixture` specimens from Architecture §6.5.8. The fake supplies no OpenClaw/provider/auth
configuration to any real executable. Production launch/registration refusal is tested first.

Create schemas and known-answer vectors for every digest/ID/record, cumulative multi-head lineage,
enrollment/publication, grounding and control variant. Two independent parsers must agree on
canonical bytes/digests; reject malformed, reordered, duplicate or unknown fields. Include exact
legacy-envelope byte preservation, not rewritten equivalent provenance. Synthetic issuer inventory
is separate from source-producer inputs. Implement the five exact §3.1 component inventories and
independent case58 walkers; mutate every included file/mode and all protected helper/schema inputs.
No fixture helper can silently become part of the runtime or an attestation to real packaging.

### T1 — identity, qualification and state

Implement trusted scope assignment, event-based retry collision, exact dispositions and two distinct
identities (strict assertion and existing envelope UUID). Add grounding/receipt authentication and
freeze each assertion's qualification at original admission. Implement full-bound reduction once,
including same-check forks, ineligible inconclusive contribution, terminal precedence, permanent
supersession and exact unresolved predicate. A query never invokes a separate state reducer.

### T2 — conserved authority and publication

Implement enrolled genesis, cumulative sets/parents, source cutoff, operation idempotence, fence
before intent/source commitment, authority advancement to unavailable, then separate serving
publication. Compare full publication hashes, not generation names. Independent cold validation
rebuilds state/rows/graph. Rollback accepts only the current head/current contract; no lifetime
renewal. Fault inject every file/fsync/rename and recovery boundary. A rejected candidate cannot
rewrite history; an admitted terminal action cannot be undone by projection failure.

### T3 — read-only CLI and MCP

Implement deterministic lexical scoring/ties and complete-bound state with selector-only display.
Related includes defined context plus queried-head verification support; whole deny on
unavailable/oversized support. Emit v3 qualification/basis/state and completeness fields. Open the
exact qualified file projection read-only; prove no mtime/file/cache change and no general
config/model/Chroma imports. Register only three MCP tools and empty resource/template surfaces.

Full private authority/state/provenance reconstruction runs in a fresh operator-controlled process
before publication and before activation. The unprivileged runtime opens only the exact committed
public projection/manifests under the controller's pinned publication; it cannot read private grounding,
citation, source or issuer/governance files. Test both boundaries and their binding explicitly; hashing
public rows alone is not proof of their derivation, and a forged qualification flag is never accepted.

### T4 — connector

Validate connector-launch v2, runtime/policy digests and exact argv/env/cwd. Invoke the connector
library with the fixed injected `spawn` transport; do not register it with OpenClaw. A scripted
filter-load failure must stop before the logical Python child; no real setpriv/filter is used and
actual enforcement proof is Gate D. No shell,
inherited secret, ambient FD, dynamic path/tool mapping or content execution. Preserve raw evidence
only in untrusted tool-result blocks. Exercise single-active/eight-pending bounds,10s
deadline,cancellation and no late success/retry. A fixed synthetic response tests framing only,
not inference, provider behavior or OpenClaw compatibility.

### T5 — fake controller, manager and supervisor

Implement slot lifecycle, peer policy, lock order, controller versus supervisor ownership,
logical role/argv checks and complete framed turn protocol through `FixturePlatform`. Fixed logical
UID/GIDs are operator1000/1000, controller0/0, supervisor0/0 and runtime1001/1001; no host accounts
or privilege changes. Script clock/boot, peer identity, access, process events and manager events
using Architecture §6.5.8's exact port, not ad hoc OS calls. Fake manager tests
include supervisor death/hang, detached descendant, outstanding model work and unverifiable
emptiness; only an independent empty-domain receipt permits slot reuse. Test release/revoke
linearization without waiting for a blocked consumer, stable turn IDs and partial-frame discard.
Manager membership survives supervisor/controller failure and is cleared only by scheduled manager
events, not a supervisor assertion or stop acknowledgement. Reject stale boot/invocation receipts,
unknown population and wrong peers. Persist same-boot freshness anchors; require new-boot clock
review. Deny runtime access to private qualification/issuer/governance/control paths. Test production
refusal even with an unwrapped specimen. Fake success cannot close D-CONTAINMENT/D-DISTRIBUTION/
C-RUNTIME or Gate W.

All actual unit/runtime/model packaging and installation is outside T0–T5. Do not run `openclaw
config validate` against live state, start a gateway or provision UIDs/units to make tests pass. A
later qualified temporary-config probe needs its exact grant; this file grants none.

## 5. Acceptance ownership and commands

Architecture §13 cases1–58 are normative:

- **B:** 1–27,40–44,49–52, strict-server portion47, private/public qualification portion55,
  preflight/artifact portions57–58 and builder/server inventory portions58.
- **C fake:** connector/lifecycle portions33,35,45,46,48,53,54, pre-activation qualification portion55,
  fake-lifecycle/production-refusal portions57 and remaining component-inventory portions58.
- **D real:** repeat1–4;28–36,38–39,45–47,53–55 on the actual sealed runtime. Case33/35 repetition
  proves the real launch boundary; fake success does not close it.
- **W:**56 plus authority/publication cases41–44/49/51–52 exercised through real governed CLI code
  with disposable synthetic stores, never production data by default.
- **E:**37 proves channels remain absent and the local operator boundary persists under the
  separately granted live phase.

Test every safety obligation with an independent reference or negative control whose deliberately
removed enforcement fails. Include selector/limit/depth metamorphic tests, full verification table,
grounding substitutions, original-admission qualification, stale full CAS,
fence/admission/projection crashes, legacy refusal and clock/release/retirement races. Never report
“all58 passed” from B/C. For case57, removing empty-domain verification, retaining stale receipts,
granting runtime private access, using ambient state or bypassing preflight must fail independent
controls. Case58's omitted-`canonical_json.py` mutant must fail even with a recomputed matching wrong
digest; test-file edits must leave component hashes unchanged while changing the fixture manifest.

### 5.1 Fixed disposable runner

The test-only entrypoint is `tests/fixtures/openclaw_strict/run_isolated.py`. Its closed CLI is
`--source-commit HEX40 --plan-sha HEX40 --runtime-root ABS --suite all`; unknown/missing arguments
fail. `source-commit` is the clean implementation commit under test, not the plan parent; `plan-sha`
is the reviewed corrective plan commit. The runner reads only the named commit's tracked export,
checks the baseline-to-source edit allowlist, and excludes `.git`, untracked files and generated
outputs. No credentials or live ConvMem/OpenClaw paths are inputs. Outside the sandbox the runner
may only inspect that commit, inventory the supplied test runtime, create fresh synthetic roots,
launch the fixed bubblewrap command and collect bounded test evidence. It has no arbitrary-command
or arbitrary-mount argument.

Architecture §6.5.8 freezes the containment: nonprivileged bubblewrap, separate user/PID/IPC/net/UTS
namespaces, no capabilities, new session, parent-death exit, private proc/dev, no host root/home/run
or sockets, read-only `/src`, `/runtime`, the supplied prefix's `sysroot/usr` at `/usr` with
`/bin`/`/lib`/`/lib64` aliases, and exactly one
new mode0700 `/tmp/convmem-openclaw-fixture.XXXXXX` mounted read-write at `/fixture`. Private `/tmp`
is a 256 MiB tmpfs. Use mandatory `--unshare-user --unshare-pid --unshare-ipc --unshare-net
--unshare-uts --disable-userns --assert-userns-disabled --cap-drop ALL --new-session
--die-with-parent`; no permissive fallback or `--as-pid-1`. Missing namespaces/bubblewrap/runtime
bytes stop TEST before imports; do not install packages, provision host resources or run unconfined.

Pre-provisioned runtime versions are CPython3.13.12 / Unicode15.1.0 / Node26.9.0 / MCP1.28.1 /
idna3.18; remaining test dependencies follow baseline `requirements.txt`. Inventory every regular
file/mode/hash in the supplied prefix; reject symlinks, user config, credentials, model/OpenClaw
packages and unlisted files. Freeze that inventory for the run; no downloads or substitutions.
It is not a production image or an architectural choice about runtime distribution.

The supplied prefix is the complete test dependency closure: interpreter/stdlib, Python packages,
Node, ELF loaders/shared libraries and any locale/data files they load. Its `sysroot/usr` contains
only those inventoried support files, never host `/usr`, host executables or a package-manager
tree. `test_runtime_tree_sha256` hashes the canonical sorted `{path,mode,sha256}` array for every
regular file relative to this prefix, including `sysroot/usr/`; there is no second unbound library
input. The runner creates only the fixed sandbox aliases `/bin -> usr/bin`, `/lib -> usr/lib`,
`/lib64 -> usr/lib64`; these are not symlinks admitted into the supplied prefix. Provisioned files
must resolve at `/runtime` and these fixed aliases under the empty environment below, without
`LD_LIBRARY_PATH`, `PYTHONHOME`, host loader caches or additional mounts. Missing closure is a
TEST provisioning failure: supply the specified files in the same prefix and rerun preflight;
never discover/bind host libraries as a repair. Preflight records actual interpreter/version,
module and loader resolutions, checks that every loaded regular file is inventoried at its
mapped path, and rejects a missing/changed/unlisted dependency before implementation imports.
The prefix's independently computed inventory/hash is frozen before launch and checked again
afterward. It is fixture evidence only, not Gate D sealing.

Set only `HOME=/fixture/home`, `TMPDIR=/fixture/tmp`, `XDG_CONFIG_HOME=/fixture/config`,
`XDG_CACHE_HOME=/fixture/cache`, `XDG_DATA_HOME=/fixture/data`, `PATH=/runtime/bin:/usr/bin`,
`LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `PYTHONDONTWRITEBYTECODE=1`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, from an empty environment. Create those empty directories;
close inherited FDs except stdio. Tests run from `/src`, write only under `/fixture` or private
`/tmp`, disable pytest's cache provider and explicitly load only baseline-required test plugins.
Record the exact plugin inventory; autoload is forbidden. Per-suite wall deadline is 600 seconds
and captured stdout/stderr combined limit is 16 MiB; overflow/timeout fails, never silently raises
the budget. Simulated protocol deadlines use the scripted clock, not these driver limits.
These are unmeasured limits, not demonstrated capacity. TEST records monotonic elapsed time,
combined output bytes and maximum sampled `/tmp` allocated bytes (with sampling interval), verifies the tmpfs size
is 268435456 bytes, and fails on deadline/output overflow or ENOSPC. The `/tmp` limit does not
describe `/fixture` storage. Thresholds remain 600 seconds, 16777216 output bytes and the fixed
256 MiB tmpfs; no harness limit changes protocol deadlines, authority or freshness. Cursor/Grok
repairs inefficient test/runner code within scope; a necessary limit change returns to Codex/Kiro
with the measurement, not an automatic BUILD downgrade or silent budget expansion.

Preflight checks namespace identity and absent external routes, inability to resolve/read/write
outside-root synthetic canaries, absent inherited sentinel credential/config variables, and no
unexpected inherited FD. It never reads real secrets or starts a host network listener. Negative
controls deliberately expose only synthetic canaries or substitute an incorrect namespace/env/FD
observation; the independent preflight must reject before importing implementation. Inner controls
may not disable the outer disposable boundary. Strict imports guard OS/network/exec actions and
writer/config imports; T4/T5 launch only virtual roles. Direct Python CLI/MCP subprocess tests use
only the allowlisted fresh-process entrypoints in the sandbox. Wait for PID-namespace termination
before disposal; timeout retains the exact root for operator inspection. Deletion is not recovery.

Case57 must observe actual kernel denials for outside-root canary opens/writes and read-only
mount writes, not merely a fake `access()` denial. A separate synthetic-only inner exposure of
a canary must make the independent preflight fail while the outer boundary stays intact. Fake
role permissions, peers and manager membership remain modeled contracts with independent oracles;
these tests do not require Gate D UID/systemd enforcement. Copy input files to fresh disposable
`/fixture` subtrees before any case58 mutation; never mutate `/src`, `/runtime`, `/usr` or the
protected checkout. The reference walker owns its literal inventory and computes canonical bytes
and expected hashes itself, never asking the implementation for its expected set or digest.

After implementation invoke the fixed runner (substitute only the reviewed plan and implementation
commit IDs and the location of the already provisioned test-runtime prefix):

```bash
python -I tests/fixtures/openclaw_strict/run_isolated.py --source-commit IMPLEMENTATION_SHA --plan-sha REVIEWED_PLAN_SHA --runtime-root /tmp/convmem-openclaw-test-runtime --suite all
```

Inside that boundary the driver runs these exact strict/connector suites with the inventoried
Python/Node, not host interpreters; these commands alone outside the runner are not acceptance:

```bash
/runtime/bin/python -m pytest -q -p no:cacheprovider --basetemp=/fixture/pytest-strict -o junit_family=xunit1 --junitxml=/fixture/evidence/pytest-strict-junit.xml tests/test_bound_read_scope.py tests/test_strict_grounding.py tests/test_strict_evidence_state.py tests/test_strict_projection_publisher.py tests/test_strict_projection.py tests/test_strict_projection_recovery.py tests/test_mcp_openclaw_strict.py tests/test_strict_snapshot_revocation.py tests/test_openclaw_lifecycle_config.py tests/test_openclaw_connector_contract.py tests/test_openclaw_activation_controller.py tests/test_openclaw_activation_supervisor.py tests/test_openclaw_strict_packet_contract.py
/runtime/bin/node --test integrations/openclaw-convmem-reader/test/connector.test.mjs
```

In the same boundary, separately run this bounded legacy compatibility suite:

```bash
/runtime/bin/python -m pytest -q -p no:cacheprovider --basetemp=/fixture/pytest-legacy -o junit_family=xunit1 --junitxml=/fixture/evidence/pytest-legacy-junit.xml --deselect=tests/test_agent_run_ledger.py::test_v8_kiro_hook_adapter_fail_open --deselect=tests/test_agent_run_ledger.py::test_v6_git_facts_non_git_cwd --deselect=tests/test_agent_run_ledger.py::test_q7_hook_failure_writes_stderr --deselect=tests/test_agent_run_ledger.py::test_q4_hook_two_missing_id_starts_same_cwd tests/test_site_filter.py tests/test_milestone_c.py tests/test_agent_run_ledger.py tests/test_query_ledger_lookup.py tests/test_query_search_harden.py tests/test_ledger_related.py tests/test_unresolved_payload.py tests/test_file_generation_store.py tests/test_file_generation_validate.py tests/test_governed_recovery_and_writers.py tests/test_governed_writer_gate.py tests/test_shadow_writer_coverage_scan.py tests/test_provenance.py tests/test_provenance_continuity.py
```

`junitxml` is pytest 9.1.1's built-in reporter already present and loaded in the frozen runtime;
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` remains unchanged. `-o junit_family=xunit1` freezes the emitted
`file`, `classname` and `name` attributes needed for lossless node reconstruction. These output-only
arguments add no dependency/plugin/process/environment input, do not change selection, and create
only the two named disposable files. The sole accepted terminal-output difference is pytest's own
built-in generated-report notice. The Node command is byte-for-byte unchanged.

`--suite all` means exactly the three commands above: strict Python, connector Node and bounded
legacy Python. It never means unqualified repository-wide pytest discovery. The frozen code
baseline's full suite executes Git/shell/systemd probes; the four explicitly deselected ledger
tests execute a Kiro hook or Git. Those calls contradict this runner's closed process inventory.
They are outside this fixture's acceptance set, not passed, newly skipped strict tests, or replaced
with mocked successful executions. Report those four node IDs and the absence of a full-repository
run. Existing repository-wide checks remain separate work; no all-repository PASS is claimed.
All other tests in the named legacy files remain selected; provenance byte/UUID and continuity
tests are explicitly retained above. No protected test or source is edited to fit the runner.

The runner validates these exact selectors/deselections against a test-owned constant before
collection; no caller-supplied `-k`, `--ignore`, extra deselection or arbitrary command is accepted.
Legacy compatibility runs in a separate fresh pytest process with the same physical boundary and
no subprocess allowance. Its unchanged tests may import legacy config/writer code against their
disposable synthetic stores, as they already do at the baseline; they prove only legacy behavior.
That does not grant strict components a writer/config import or production write authority. Strict
import guards remain mandatory in the strict suite and every strict entrypoint. No new selected
safety test may be skipped; compare collected node IDs with the frozen selection and report them.
Packet-contract negative controls must reject a full-discovery command, a missing selected safety
node, an extra deselection, a hook/Git spawn and a strict reader importing a legacy writer. Fix the
runner/test selection implementation, never silently execute on the host or broaden its inventory.

After the unchanged Python processes exit, parse the two raw reports with the standard library and
write canonical `/fixture/evidence/pytest-node-outcomes.json` with exact top-level fields
`schema, full_repository_discovery, suites`. `schema` is
`convmem.pytest-node-outcomes.v1`; `full_repository_discovery` is false; `suites` is the ordered
strict-then-legacy array. Each suite has exact fields `suite, junit_path, selector_files,
deselections, counts, node_outcomes`. `counts` has `collected, passed, failed, error, skipped`;
`node_outcomes` is sorted by node ID and contains exact `{nodeid,outcome}` objects, where outcome is
one of `passed, failed, error, skipped`.

For every xunit1 `<testcase>`, require exact nonempty `file`, `classname` and `name` attributes.
`file` must equal one exact selector. Its dotted `.py`-stripped form must equal `classname` or be
its unique prefix; any remaining dotted classname components are class/collector segments between
the file and test name. Reconstruct `file::segment...::name`, require a unique round trip to the
same three attributes, and reject any `#xNN`/`#xNNNN` lossy escape marker. Require exactly one
`testsuites` root containing exactly one direct `testsuite`; reject DTD/entity declarations,
malformed or additional/nested suite elements, unexpected testcase children, duplicate node IDs,
nodes outside selectors, a selected file with no testcase, or any deselected node. A
testcase with no outcome child is `passed`; exactly one `failure`, `error` or `skipped` child maps
to that outcome; multiple/unknown children reject. Counts must equal both the testcase-derived
counts and the JUnit suite attributes. `failed` or `error`, a nonzero process status, or disagreement
with the fixed behavioral counts fails TEST. The strict and legacy canonical arrays must each be
identical across the two fresh-root M8 runs. AST inventories are diagnostic only and may never
populate `pytest-node-outcomes.json` or be labeled collected evidence.

The pre-correction behavioral baseline is fixed as 238 strict passes; 29 Node passes; and 115
legacy passes, one legacy skip and four deselections. The correction must preserve those results.
No selected test logic, file inventory or outcome may change. Updating the existing exact
semantic-parent SHA assertion to the newly reviewed parent is the sole mechanical selected-test
file edit allowed; it may not alter test behavior.

Run `git diff --check` against the implementation branch outside the exported tree. No
new strict-test skips; report existing production-dependent skips. B/C leaves existing
approval/recovery tests unchanged because Gate W is separate; their baseline pass does not prove the
corrected approval invariant.

## 6. Gate W production correction contract

A separately reviewed execution packet must instantiate Architecture §6.5.7 and §14.3 against an
exact current baseline. It may not reinterpret the selected explicit route or upgrade legacy
consent. That packet identifies changes to `convmem.py`, `propose_decision.py`, `observe.py`,
`conflict_events.py`, writer-prefix guards, index/watch exclusions, restore/backup
manifests/validators and wrapper/help guidance, plus new governed engine/schema tests. It preserves
all existing production write/backup authorization and other arcs' ownership. No such code is edited
in this architectural pass or B/C scope.

Mandatory behaviors: ratification persists exact intent without ingestion; explicit `convmem add
--file ABS` alone authenticates and admits; source/intent commit is preceded by retirement and
durable serving fence; durable admission precedes derivative projection; recovery repairs
bookkeeping/derivatives without issuing an add or accepting Chroma absence as authority. The new
event stream has strict byte-bound deduplication; old events remain readable and unchanged.
Pending/partial/complete/rejected/superseded legacy proposals never automatically become new-format
admissions. Old incomplete recovery returns `legacy_review_required`; generic governed adds require
new authenticated artifacts. Unknown history fails closed.

The source census now exists; §14.3 names the caller families and baseline inventory evidence. A
fresh baseline must re-run that census and test all create/upsert, approval/recover/rebase,
watch/index/repair, restore and raw-writer branches. Existing live in-flight data need not be read
to invent a transition: this contract deliberately refuses automatic migration. Any future
historical migration/source resolver/controlled capture recorder requires its own architecture and
data grant.

## 7. Failure, recovery and rollback

Implementation-code rollback is a reviewed revert on its branch; live configuration/data are
untouched by B/C. Test fixture teardown may dispose of a fixture root, but must never present that
as recovering the same enrolled lineage.

Runtime/serving recovery follows the architecture: retire first, independently prove the old domain
empty, preserve durable pending intent/admission and latest cutoff, then qualify only the current
authority. Missing pointers/history, corrupt admitted witnesses, ambiguous rename/fsync, unknown
ledger state or nonempty containment mean unavailable/quarantined, not old-snapshot fallback. No
process restarts a lease or resumes an old session. Rebuild/rollback retains the exact head,
contract and persisted expiry. A revoked/superseded predecessor never becomes current.

After ADMISSION_PREPARED but before proven admission, `recover` can inspect/report/reconcile
bookkeeping; completing an uncommitted admission requires the operator's explicit add retry. If
authority already committed but completion bookkeeping did not, recovery may record that exact
proven admission and repair its derivative without minting a new operation. This distinction
prevents “recovery” from becoming an implicit add command.

Whole-authority disaster restoration requires independent latest-history evidence under
owner-controlled recovery. Self-hashes and retained snapshots alone cannot prove absence of later
lost revocations. No local automatic reset or anti-rollback claim.

## 8. Automatic stops

Stop for any architecture §15 failure, unlisted change, new dependency/resolver/capture issuer,
schema/interface ambiguity, authority/provenance weakening, missing specified fixture input,
skipped safety test or failed negative control. Explicit stops include dummy provider key, shared
host inference, process-group fallback, inferred legacy consent, imported old session,
generation-only CAS, local/display state reduction, late provenance upgrade, implicit
approve/recover indexing and claim of actual containment based on a fake manager. A runtime call,
ambient access, production-selectable fake, supervisor-authored empty proof, unknown component
membership or unbound imported dependency stops B/C. Fix a coding defect against this contract;
any required change to its authority/interface/security/recovery/acceptance meaning returns to
Codex/Kiro as BUILD BLOCKER. Missing later Gate D artifacts do not block this fixture implementation.

No task prompt, fixture, model output or this plan authorizes runtime start, service/user
provisioning, network/model cost, live data, deployment, capture, merge or production write. Runtime
incompatibility stays at Gate D; Grok must not choose another provider/version/auth strategy or
make the fixture depend on it. Missing test-runtime tools or namespace support blocks TEST until
the specified environment is separately supplied; it never authorizes a weaker runner.

## 9. Returned evidence and independent review

Return exact branch/tip/push state; baseline-to-tip allowed-file comparison; schema/fixture/runtime
artifact digests and the full canonical entry arrays; Python/Unicode/Node/idna/MCP versions;
fixture-manifest/source/test-runtime inventories and reproduction in two fresh roots;
commands/results/skips; independent
references and failing negative controls; every crash/clock/race outcome; read-only
import/file/network evidence; exact three-tool/zero-resource inventory; unresolved blockers. Label
every fake/static/real observation separately. Return pre-import canary/namespace/env/FD checks,
the allowlisted subprocess trace, independent fake-manager event/membership trace, stale/unknown/
nonempty retirement refusals, production-launch refusals, and clean PID-namespace termination or
the retained failed root. Case57 bypass mutants and case58 omitted-helper/excluded-test mutations
must have explicit expected failure evidence. No claim of live readiness, real auth compatibility,
real host containment, production sealing or value.

Retained preceding-edit evidence is Architecture §§14.1–4: matching Stage1/reconstruction hashes,2 passing
baseline routing tests, static governed caller mapping, installed systemd/cgroup/setpriv capability
observations, and a negative isolated auth-resolver test tied to exact installed source hashes. None
tests the unimplemented integration.

This correction's documentary evidence is Architecture §14.5: exact parent/report identity, paired
inventory/classification/contract checks, unchanged baseline code and `git diff --check`. The
review bundle includes the checker/output and exact committed diff. It does not relabel these
checks as TEST PASS.
For this correction return the complete inventoried `sysroot/usr` mapping, the exact three-suite
selection with four named exclusions, both raw JUnit reports, the canonical exact node/outcome
report, unchanged protected baseline bytes, and the capacity measurements when TEST is later run.
Prove both fresh runs have identical node/outcome arrays and preserve the fixed behavioral counts.
The retained Astra report reviews `0f1216f`; the preceding runner correction's parent was
`2aa66a8`. Neither report history nor document checks certify this M8 correction or execution.

A focused fresh Astra check of the runner corrections, preserved fixture/hash contracts and their
regression matrix precedes Kiro's exact-tip binary review. Do not reopen passed semantics or demand future
production evidence merely to perfect the packet. Ryan decides any subsequent scope-specific grant;
reviewer passage does not itself authorize execution.

## 10. Precise changes and remaining readiness

The preceding runner edit's parent was `2aa66a8753db3be6adce7cb17533eae96aee609d`.
Architecture §18.4 and §10.3 here record those two contradictions and fixed remedies;
Architecture §18.5 is that correction's regression matrix. The current M8 correction begins at
`492ba7b656d065ce1eaf31a4032d6eaf0bf6dbb3` and is recorded in Architecture §18.6 and §10.4 here.
Authority, state, grounding, receipts, lifecycle/freshness, explicit-add, private
qualification, manager ownership and exact component sets remain intact. Architecture §§18.1–3
retain the preceding `0f1216f` to `2aa66a8` correction for reference. No production-schema version,
implementation allowance or legacy identifier/envelope changes in this edit.

### 10.1 Remaining issues and correction paths

Architecture §18.2's full records are normative here, including evidence, owners, locations,
negative controls, observable failures, safety rationale, rollback and contamination stops.
The following execution mapping uses the same exact classifications; no item grants redesign.

- **B-FIXTURE — SAFE TO DEFER INTO ISOLATED IMPLEMENTATION.** Original missing specification is
  corrected by Architecture §6.5.8 and execution §§3–5. Cursor/Grok implements the fixed harness,
  injected ports and component cores in the allowlisted files; correction is conformance, before
  B/C TEST. Acceptance: case57 plus33/35/46/48/53–55, including independent manager membership,
  stale/nonempty/unknown refusal, blocked release/revoke, private-path/ambient denial, disposable
  preflight and production refusal. Negative bypasses must fail, not become alternative backends.
  Observable failures are host/ambient access, wrong-peer/receipt acceptance or unintended launch.
  Deferral is safe because neither real provider nor privileged runtime is needed and suite entry
  is physically isolated. Recovery preserves head/expiry, quarantines uncertainty and distinguishes
  teardown from lineage recovery. Architectural contamination is forbidden: needing real runtime,
  selectable fake or changed retirement/containment semantics stops BUILD for Codex/Kiro.
  Grok architectural decision: **no**.
- **B-DIGEST — SAFE TO DEFER INTO ISOLATED IMPLEMENTATION.** Evidence/correction: exact §3.1 and
  Architecture §6.5.9 sets now restore the oracle; Cursor/Grok implements them in component owners
  and packet-contract tests at T0/B/C TEST. Acceptance: case58 independent arrays/hashes, every
  included file/mode mutation, schema-subset rejection, excluded-test invariance and an
  omitted-canonical-helper negative mutant that must fail. Observable failure is unbound import,
  unequal vectors or invisible included-byte drift. Deferral is safe because only computed output
  hashes, not membership decisions, remain. Recovery refuses qualification without policy/authority
  fallback. New/guessed membership or fake production attestation can contaminate the architecture
  and stops BUILD; Codex owns a necessary contract correction. Grok decision: **no**.
- **I-IMPLEMENTATION — SAFE TO DEFER INTO ISOLATED IMPLEMENTATION.** Evidence: fixed core
  Architecture §§6–8, T1–T3 and named test owners. Cursor/Grok implements/reproduces/repairs within
  the eight modules, schemas and tests before B/C TEST. Exact acceptance is §5's assigned cases;
  independent reducer/qualifier references and mutants removing scope ceiling, retained history,
  original-admission freezing, full CAS or current-head-only rollback must fail. Observable failure:
  wrong bytes/state/assurance, stale publication or forbidden import. Deferral is safe: synthetic
  implementation/testing is the deliverable and no durable semantics remain to choose. Recovery:
  revert code by reviewed branch revert; preserve admitted fixture history and remain unavailable
  on ambiguity.
  Any needed schema, invariant, resolver, protected-writer or acceptance change can contaminate
  architecture and stops BUILD for Codex/Kiro. Grok decision: **no**.
- **C-RUNTIME — LIVE-DATA/PROMOTION BLOCKER.** Evidence: Architecture §14.2's no-key failure.
  Codex/Kiro own the separate Gate D runtime/auth packet and §§9.1/14.2; Ryan grants actions.
  Correction: prove an exact compatible local-only route or separately review one. Acceptance:
  real cases28/34/55, one local turn without key/dummy key/auth-store/env fallback/shared host
  inference/egress; introducing each forbidden route must fail qualification. Observable failure
  remains resolver rejection or wider access. Recovery refuses activation or retires/quarantines;
  no fallback. Importing this decision into T0–T5 or claiming fake compatibility contaminates scope
  and stops BUILD. Grok T0–T5 decision: **no**.
- **D-CONTAINMENT — LIVE-DATA/PROMOTION BLOCKER.** Evidence: no real qualification under
  Architecture §§6.5.6/14.4. Ryan-granted provisioning/qualification lane and Codex/Kiro's separate
  Gate D policy packet own correction. Acceptance: real cases46/53/55 and UID/peer/mount/FD/filter/
  network/death/hang/detached-work controls; removing each enforcement in the granted disposable
  environment must fail. Observable failure is ambient access, egress or unknown/nonempty domain.
  Recovery quarantines without receipt/replacement/publication until independently empty.
  Real mechanism choices during B/C or fake proof asserted as host proof contaminate scope and stop
  BUILD. Grok T0–T5 decision: **no**.
- **D-DISTRIBUTION — LIVE-DATA/PROMOTION BLOCKER.** Evidence: missing real sealed runtime/model
  and inventory in Architecture §§6.5.6/14.4. The separately granted packaging lane with Codex/Kiro
  owns exact artifacts in the Gate D packet. Acceptance: real cases28–34/45/47/55, full closure
  and inventory; mutate imports under an unchanged launcher, poison CWD/HOME, or add FD/tool/endpoint
  and require failure. Observable failure is digest/import/inventory drift or fallback. Recovery
  refuses/retire-quarantines drift, preserves authority/freshness, never substitutes host packages.
  A fixture dependency on production image/model selection or fabricated sealing contaminates
  architecture and stops BUILD. Grok T0–T5 decision: **no**.
- **W-PRODUCTION — LIVE-DATA/PROMOTION BLOCKER.** Evidence: Architecture §§6.5.7/14.3 and §6 here
  remain outside B/C. Codex/Kiro own the exact-baseline Gate W packet; Cursor after Ryan's grant
  corrects the governed engine and enumerated CLI/writer/backup/restore callers. Acceptance:
  case56 plus41–44/49/51–52 using disposable governed CLI; bypass approval/add/backup/restoration
  fences and require failure. Observable failure is implicit ingest/forged consent/Chroma-absence
  authority/lost revocation/automatic migration. Recovery fences and reconciles protected history;
  uncommitted admission needs explicit add retry. Editing protected writers or claiming production
  consent from fixture PASS contaminates scope and stops BUILD. Grok T0–T5 decision: **no**.
- **U-VALUE — NON-BLOCKING UNCERTAINTY.** Evidence: lexical §6.5.5 and unrun D-V; not a BUILD
  dependency. Ryan/evaluation owner predeclare thresholds/stops in the later D-V packet, then
  measure the 32-run paired comparison against the off arm. Fixed lexical known-answer tests are
  the fixture acceptance; null/harmful value blocks promotion claims. Observable failure is poor
  usefulness or exceeded fixed bounds. Recovery keeps the prototype disposable/unpromoted.
  Adding global search/inference/authority/fallback for quality contaminates scope and stops BUILD.
  Grok T0–T5 decision: **no**; later value thresholds are not fixture architecture choices.

### 10.2 Independent gate decisions

These are the current decisions. The earlier M8 pause is retained in §§10.3–4 only as repair
history and cannot be mistaken for current state.

- **BUILD PASS / BOUNDED TEST PASS:** the frozen T0–T5 fixture implementation is accepted at
  `8010fb060c2edc29e1b09d7a30b1a1da2689d489`. That verdict is bound to the original baseline,
  parent, overlay, runtime and evidence; it is not current-main merge readiness.
- **LIVE-DATA BLOCKED:** actual Gate D authentication/containment/distribution and applicable Gate W
  production enrollment, plus an explicit data/config grant, are still required.
- **PROMOTION BLOCKED:** LIVE-DATA and the later applicable Gate E/D-V/production authorization
  requirements must be independently satisfied. No channel/gateway/consequential-data effect now.

**WHAT DID THIS EDIT BREAK THAT WAS PREVIOUSLY SOUND?** No documentary regression found in the
attempted attacks in Architecture §18.5. The earlier missing-node-evidence issue was repaired and
accepted at `8010fb0`; M11 requires fresh evidence rather than inheriting that PASS. The matrix covers
authority rollback, canonical state/forks, grounding/receipts/original admission, retirement/
freshness/release, explicit writes, private qualification, physical fixture/credential isolation,
legacy bytes, recovery, Gate W separation and hash membership. The prior full-repository test
claim and four hook/Git nodes are explicitly outside this runner's result because they contradict
its process restrictions. No previously passing coverage is asserted or removed; no strict safety
case is removed, and selected legacy behavior remains mandatory.

### 10.3 Final runner repair records and implementation obligations

Architecture §18.4's complete labeled records for **B-RUNNER-CLOSURE** and **B-RUNNER-SUITES**
are normative in this plan. Both are **RESOLVED in specification**, not executed conformance.
The changed execution sections are §5.1's mount/inventory and command contracts, §9's evidence,
and this section; Architecture §§6.5.8/13 case57/14.5/18.4–5 carry the matching contracts/checks.

- **B-RUNNER-CLOSURE:** The old hash omitted the libraries mounted separately at `/usr`.
  §5.1 now mounts only inventoried `sysroot/usr` from the supplied prefix, binding loader/stdlib/
  dependency/data bytes in `test_runtime_tree_sha256`. Case57 must reject a host-library bind and
  missing/changed/unlisted copied dependency before strict-import entry. Independently recompute
  the inventory/hash; changing only the implementation's claimed digest cannot pass. Missing
  provisioned bytes remain TEST work for the provisioning owner, followed by Cursor/Grok's
  preflight rerun. No extra mounts or inherited loader settings; no component-inventory changes.
- **B-RUNNER-SUITES:** The old full pytest command and four hook/Git nodes required forbidden
  processes. §5.1 now fixes exactly three suites and four explicit legacy exclusions, rejects
  any additional selector change, and separates baseline legacy imports from strict imports.
  Case57 must fail full discovery, extra deselection, a missing selected safety node, hook/Git
  spawning or a strict writer import. Report the coverage limitation rather than call it PASS.
  Cursor/Grok implements only the frozen runner/test guards in the existing allowance; neither
  a host-tool expansion nor editing protected tests is a correction path.

For both repairs, fail closed before entry or retain failed evidence until namespace termination;
uncertain teardown retains the root. Rollback never changes the authority head or expiry, and
deletion is not recovery. Contract changes return to Codex/Kiro; conformance defects return to
Cursor/Grok. Case58 must mutate disposable copies and use reference-owned expected inventory and
hashes. Case57 must separately script supervisor death, stop acknowledgement and cleanup callback
while detached descendants/outstanding model work remain; partial independent removal still
refuses retirement, and only genuine exact-invocation terminal/empty observation permits it.
Physical denial tests observe kernel results inside the disposable boundary, not Gate D host proof.
Capacity remains unmeasured TEST work at the unchanged thresholds; fake success never proves real
authentication, provider compatibility, sealed production distribution, live data or promotion.

### 10.4 M8 node-inventory correction obligations

Architecture §18.6 records the authorized correction and observed blocker. This obligation was
completed and accepted at `8010fb060c2edc29e1b09d7a30b1a1da2689d489`; it is retained to define
the unchanged M11 evidence contract. Its implementation allowance was limited to the fixture runner/evidence helpers
needed to add the two §5.1 JUnit arguments, parse/validate their reports, emit the fixed canonical
node/outcome artifact, update generated-output exclusions if required by the exact walker, and
mechanically repin the semantic-parent constant and its existing assertion. The selected test
files, selector arrays, four deselections, Node command, dependency/runtime/plugin inventories,
environment, mounts, permissions, negative controls and all production modules remain unchanged.

Codex must inspect the complete diff before execution. Any new test or test-logic edit, new process,
`--collect-only`, conftest or environment injection, plugin/dependency, selector/deselection change,
report outside `/fixture/evidence`, AST-derived collected claim, changed behavioral count/outcome,
or weakened failure rule receives `PAUSE` or `REQUIRE TEST`. The first corrected reproduction does
not inherit the old run's status; M8 requires two fresh-root runs at one clean pushed commit and
the exact raw/canonical evidence in §5.1/§9. TEST PASS may be issued only after both are inspected.

The bounded implementation remains architecture-complete. M11 does not reopen this correction;
it only repins the exact reviewed parent/baseline literals and then re-runs the unchanged contract
under §10.5. Known deferred issues do not authorize Grok to redesign the architecture.

### 10.5 M11 current-main reconstruction and merge-readiness obligations

Architecture §18.7 is controlling. The accepted bounded implementation remains
`8010fb060c2edc29e1b09d7a30b1a1da2689d489` over original baseline
`7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`; current-main integration targets exactly
`9193f5ec744f059d07a20612489b210527b5660a`. Acceptance of the former does not transfer to the
latter. No action below is authorized until this parent and the paired overlay receive exact-tip
Kiro PASS and Ryan issues a new grant naming the revisions, branch, runtime path and evidence root.

Execution order is frozen:

1. Codex creates and pushes the granted implementation branch and separate worktree from the exact
   reviewed milestone-overlay tip named in Ryan's grant, without switching the live ConvMem
   checkout. Before Grok starts, Codex proves that tip descends from product baseline
   `9193f5ec744f059d07a20612489b210527b5660a`, changes exactly the four authorized plan/status
   documents, and leaves every non-plan byte identical to that baseline.
2. Grok cherry-picks exactly the 45 non-merge commits in
   `2f05a8540b9155346f313d7b2eea6300fec29350^..8010fb060c2edc29e1b09d7a30b1a1da2689d489`
   in their existing order. It neither merges the old branch nor selects, drops, squashes, edits or
   resolves a commit. Any conflict or unexpected path stops at `PAUSE` before a commit is made.
3. Grok commits one separately held reconciliation that changes only the two frozen SHA values and
   assertions plus the nine exact parent/overlay comment/docstring files named in Architecture
   §18.7. The parent SHA is the reviewed parent commit in Ryan's grant; the code baseline is
   `9193f5ec744f059d07a20612489b210527b5660a`. Observable behavior and selected test bytes remain
   unchanged. Grok pushes with an explicit refspec and stops.
4. Codex compares complete trees and path sets before testing. The four reviewed plan/status blobs
   must remain exact. Every other path changed on current main relative to the original baseline
   must remain byte-identical to current main unless it is in the accepted product delta or exact
   pin/comment allowance. The replayed product delta must equal the accepted old-baseline delta
   except for that allowance. Missing, extra or modified paths are `PAUSE`.
5. Codex, under the exact Ryan grant, provisions the complete frozen runtime at the newly bound
   parent/baseline path and confirms tree hash
   `sha256:74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`, full
   file/mode/hash inventory, resolved dependency paths, version checks, mutation check, and absence
   of symlinks, unlisted bytes or host fallback. Grok performs none of this work.
6. At one clean pushed source commit, the unchanged isolated runner executes twice from fresh roots
   using `--plan-sha` equal to the new semantic parent and the newly bound runtime. Both runs must
   reproduce the accepted M8 counts, exact nodes/outcomes, component/source inventories, negative
   controls and mutation guarantees. Codex copies staging evidence to the new Ryan-designated
   durable root and verifies every byte/hash mapping.
7. Codex runs the seven M11 legacy MCP files and the unchanged Pylint regression gate in the
   reviewed disposable environment. Host-runtime results are not acceptance evidence. It retains
   commands, environment/runtime identity, exact collection/outcomes and raw logs.
8. Kiro reviews the exact integrated tip and evidence. Ryan alone decides whether to open/merge a
   PR and whether any later gate begins. A merge-readiness PASS grants no runtime activation or
   live use.

The seven regression files remain exactly: `tests/test_ask_trace.py`,
`tests/test_mcp_after_tier_a.py`, `tests/test_mcp_crush_stdio_sequence.py`,
`tests/test_mcp_rerank_scores.py`, `tests/test_mcp_roots_probe.py`,
`tests/test_mcp_shell_profile.py`, and `tests/test_mcp_site.py`. The Pylint gate remains the
unchanged `.github/workflows/pylint.yml` contract. Any required test edit, dependency change,
selector change, production configuration, or new environment mechanism is `PAUSE`, not a repair
Grok may invent.

The new durable evidence root is selected by Ryan after the final overlay SHA exists and uses
`runs/<integration-source-commit>/<run-label>/`. Historical M8 evidence and runtime inventory are
retained as comparison evidence only. Real OpenClaw remains outside this phase; before Gate D,
its installed distribution must be deliberately updated or pinned and freshly probed/reviewed.

**TL;DR:** [Arc ConvMem Switchboard] M0–M8 passed at `8010fb0`; M11 now requires a fresh branch
from `9193f5e`, exact 45-commit replay, pin-only reconciliation, a rebound frozen runtime, two M8
runs, seven legacy MCP regressions and Pylint before merge readiness. No implementation, real
OpenClaw action, merge, live data or promotion is authorized by this plan edit.
