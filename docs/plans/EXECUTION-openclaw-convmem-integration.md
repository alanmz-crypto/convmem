# Execution Plan — OpenClaw bounded ConvMem reader

**Status:** **BUILD PASS and TEST PASS for the frozen T0–T5 fixture contract at accepted
implementation `8010fb060c2edc29e1b09d7a30b1a1da2689d489`. BOUNDED M11 EVIDENCE PASS AT
`cd60cf19dca6706e4175e9f82c9ba55e41bca10b`; CURRENT-MAIN RECONSTRUCTION PRESERVED AT
`30bc134d74d7eeb4cef4d6371a5e96c926f0f2ca`; THREE-TIP CANDIDATE PRESERVED AT
`d276cb4ab0a0613b965e772d49d378e761df337e`; ADVANCED-MAIN CANDIDATE PRESERVED AT
`776a4ca3d4215490fb26b882dca2df9a41e0e03a`; INNER-ROLE RECONCILIATION AND THREE-TIP
DIFFERENTIAL PASS PRESERVED AT `65bbfd6f47515accfefa110b667afe1613f0dbed`; PYLINT PAUSED ON
THREE CANDIDATE-INTRODUCED `R0801` PAIRS.
LIVE-DATA BLOCKED; PROMOTION BLOCKED.** The final authority-packet correction, repository-wide differential,
unchanged Pylint gate, two M8 runs, seven MCP regressions and durable verification pass at
`cd60cf19`, with Kiro exact-tip PASS. That source is bound to baseline `9193f5ec…`. The first
current-main reconstruction and its applicability correction are preserved through `d276cb4`.
Before the first three-tip suite ran, current main advanced from `a92a74e` to
`5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`; the mandatory preflight paused without creating a
slot or evidence-run directory. This plan-only correction freezes a second deterministic
reconstruction. That source was completed at `776a4ca3`; three complete pytest runs and 166
isolated reruns then paused on pytest's unstable rendering of one unchanged inner-role assertion
for exactly 22 packet-contract nodes. Section 10.15 froze the closed semantic-signature
reconciliation. Its reviewed execution reached `65bbfd6f` and established the complete three-tip
differential, after which the unchanged Pylint gate paused on three candidate-introduced `R0801`
pairs. Section 10.16 freezes an exact two-test-file structural correction and fresh evidence
sequence; it authorizes no product/test edit, suite, PR, merge or runtime action. Exact-tip review
and a new Ryan resume grant are required first.
BUILD is not complete-integration readiness and does not pass any of those later gates.

**Date:** 2026-09-26

**Arc:** ConvMem Switchboard

**Architecture:** [revised architecture](ARCHITECTURE-openclaw-convmem-integration.md), especially
§§6.5, 14, 17–18. The preceding runner and node-evidence correction history remains in §§10.3–4.
Section 10.5 retains the completed reconstruction sequence; §10.6 records the completed
control-plane correction; §10.7 freezes the Pylint remediation and preserved-tip resume sequence;
§10.8 freezes the historical full-pytest differential and identity reconciliation; §10.9 records the
completed earlier M8 authority-packet rebind; §10.10 records the completed one-literal
bundle-schema correction; §10.11 records the completed final authority-packet correction and
evidence sequence; §10.12 freezes the current-main reconstruction and fresh merge evidence.
Section 10.13 records the resulting PAUSE and freezes the three-tip applicability correction.
Section 10.14 records that correction's fail-closed preflight and completed advanced-main
reconstruction. Section 10.15 records its governed evidence PAUSE and freezes the closed inner-role
signature rule. Section 10.16 records the resulting differential PASS and Pylint PAUSE and freezes
the exact post-reconstruction correction.
Review the two parent files together.
The retained Astra report reviews the earlier `0f1216f` revision, not this correction:
`/tmp/astra-final-0f1216f7249c0066dafb6fc9ef2aafa9845a7264/STAGE-1-REVIEW.md`, SHA-256
`d3d330b6195263e86f0c648f446ca9b4dbbf648983ee2ec2ad9aeacc7cc2026a`.
It found B-FIXTURE and B-DIGEST, corrected by `2aa66a8`. Section 10.3 records the later runner
closure/suite repairs; §10.4 records the completed M8 evidence correction. This edit addresses
only the observed current-main drift after the bounded M11 evidence PASS; the fixture schema,
test logic, manager and five component sets remain frozen.

**Baselines:** Original accepted code baseline
`7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`; accepted bounded implementation
`8010fb060c2edc29e1b09d7a30b1a1da2689d489`; historical M11 integration baseline
`9193f5ec744f059d07a20612489b210527b5660a`; prior current-main baseline
`a92a74eb326b3eaa59087b707de10153c7cc0c63`; exact advanced current-main baseline
`5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`; preserved integration tip
`a11b7a2a793c68e4e6e83c2680b077389a817c5c`; reconciliation base overlay
`581de2abf430786a36f2612f97c623a19b61353f`; preserved lint-remediation input tip
and pytest differential base `9c6421a6891fd8a861a51f4fed410f541b53148c`; currently preserved
corrected candidate `3f8ef8312e3f3c98915320bd1b988bac5d8d96a9`; first paused differential
candidate `853ef98ede44f2d171e5354b065e11f83558e010`; bundle-schema-paused candidate
`d7b15926ab7e4e41b8a80edba5edbe4bfed4c165`; completed post-bundle candidate
`851edbe49b820bd4081809022b10f67c30fef47a`; final reviewed M11 evidence candidate
`cd60cf19dca6706e4175e9f82c9ba55e41bca10b`; preserved first reconstruction PAUSE tip
`30bc134d74d7eeb4cef4d6371a5e96c926f0f2ca`; preserved three-tip preflight input
`d276cb4ab0a0613b965e772d49d378e761df337e`; advanced reconstruction and signature PAUSE tip
`776a4ca3d4215490fb26b882dca2df9a41e0e03a`; and preserved differential-PASS/Pylint-PAUSE tip
`65bbfd6f47515accfefa110b667afe1613f0dbed`. This revision changes plans only. A new grant must
name the new reviewed parent and overlay, advanced `N`, `R`, preserved `65bbfd6f`, the exact
reviewed plan range, four-literal authority rebind, two-file Pylint correction, rebound runtime and durable evidence root. No
rebase, merge, history rewrite or reuse of an earlier plan range.

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

The bounded implementation remains architecture-complete. M11 may resume only after exact-tip
review and a new Ryan grant naming every §10.15 input. Known deferred issues do not authorize
Grok to redesign the architecture, choose a weaker lint disposition or reinterpret a retained
repository failure as PASS.

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

### 10.6 M11 reviewed-plan allowlist correction obligations

Architecture §18.8 is controlling. The preserved implementation branch is clean and pushed at
`a11b7a2a793c68e4e6e83c2680b077389a817c5c`. Its first M8 attempt ended before source export,
integration import, runtime launch or tests because the outer edit-allowlist check reported the
four reviewed architecture/execution/milestone/STATUS paths. That retained failure must remain
labeled `PAUSE`; it is not a partial or failed test run and may not be retried under an earlier
grant.

The plan reconciliation itself has exactly two ordered commits after
`581de2abf430786a36f2612f97c623a19b61353f`: the architecture/execution/STATUS commit is the new
semantic parent; the milestone-overlay commit is the Kiro-reviewed overlay. After Kiro PASS, a new
Ryan resume grant must name both exact commits, the preserved integration tip, the unchanged
integration baseline and implementation branch, and new parent-bound runtime/evidence paths.
Execution then proceeds only in this order:

1. Codex verifies the preserved branch/worktree is clean, pushed and exactly at
   `a11b7a2a793c68e4e6e83c2680b077389a817c5c`; any other tip or dirty path is `PAUSE`.
2. Grok cherry-picks the exact two reviewed plan commits in order onto that branch, without merge,
   squash, edit, branch recreation, history rewrite or conflict resolution, pushes with an explicit
   refspec and stops. A conflict or third commit is `PAUSE`.
3. Codex proves the resulting delta from the preserved tip is exactly the four named documents,
   and each resulting `source_commit:path` regular blob and mode equals
   `REVIEWED_OVERLAY_SHA:path`. Every non-plan byte must equal the preserved tip. Only a written
   commit-specific `CONTINUE` opens the correction checkpoint.
4. Grok makes one correction commit limited to the twelve paths in Architecture §18.8. It adds the
   separate exact four-path control-plane set and reviewed-overlay constant; repins the semantic
   parent and packet assertion; implements exact Git tree-entry/blob validation and `P = D - C`
   before applying the unchanged product allowlist; adds only the frozen packet-contract coverage;
   and updates the nine existing parent/overlay comments or docstrings. It pushes and stops.
5. Codex proves `EDIT_ALLOWLIST_EXACT`, `EDIT_ALLOWLIST_PREFIXES`, `SCHEMA_ALLOWLIST`,
   `path_allowed()`, Gate-W denial, selected files, selectors, four deselections, dependencies,
   schemas, permissions, runtime hash, behavioral counts and T0–T5 semantics unchanged. It repeats
   the exact four-blob/mode proof at the corrected source commit.
6. Before any runner invocation, Codex independently proves the unchanged source exporter includes
   all four documents in the exported tree and full source inventory and that none is added to a
   generated-output or hash-exclusion set. Missing or excluded input is `PAUSE`.
7. Only if a new Ryan grant expressly authorizes the retry may Codex rebind the frozen runtime,
   execute M8 twice from fresh roots, copy durable evidence, and run the seven legacy MCP files and
   Pylint under §10.5. This plan edit itself stops before this step.

The runner-side algorithm is exact. Compute the complete sorted tracked path delta `D` from
`CODE_BASELINE_SHA..source_commit`. Require the exact four-path set `C` from Architecture §18.8 to
be present. Resolve `M11_REVIEWED_OVERLAY_SHA` as a commit and require, for each path in `C`, equal
`100644 blob <object-id>` entries at the source commit and reviewed overlay. Reject missing,
unavailable, non-blob, symlink/other-mode, extra-classified or mismatched entries. Apply the existing
product allowlist and Gate-W second layer only to `P = D - C`. Return `P` to the existing
`allowlist_changed_paths` report. A fifth document path remains in `P` and fails normally. There is
no wildcard, prefix exception, worktree fallback or test-authored expected content.

Packet-contract coverage must independently exercise exact success and every rejection class above,
including a fifth documentation path, while preserving the existing `mcp_server.py` positive and
Gate-W negative cases. Source-export coverage must prove the four reviewed inputs remain inventoried
and hashed. No runner CLI, process list, test selector, deselection, dependency, fixture schema,
permission, product interface or runtime behavior changes. The only new outer Git reads are the
closed tree-entry/blob checks needed before source export; Git is already an inventoried runner
dependency.

Any requested edit outside the twelve implementation paths, any product allowlist literal change,
any attempt to suppress the documents from source export/hash, or any M8 execution before the new
grant is `PAUSE`. This correction does not authorize real OpenClaw, Gate D/W/D-V/E/F, watch
activation, live data, merge, deployment or promotion.

### 10.7 M11 Pylint regression-remediation obligations

Architecture §18.9 is controlling. The §18.8 correction and its follow-up node/leakage repairs are
clean and pushed at `9c6421a6891fd8a861a51f4fed410f541b53148c`. Both fresh M8 runs and the seven
legacy MCP regressions passed there. The unchanged current-main Pylint gate did not: it reported
the following exact non-`R0801` occurrence deltas, all derived from report SHA-256
`2b724b4ff79405ffb286452be6c17ebef7de4eaeabd6522985c4baaee605848b` against base
`9193f5ec744f059d07a20612489b210527b5660a`.

| Path | New occurrences | Exact message-ID counts |
|---|---:|---|
| `bound_read_scope.py` | 6 | `C0325:2`, `R0902:2`, `R0912:1`, `R0914:1` |
| `mcp_server.py` | 1 | `C0302:1` |
| `openclaw_activation_controller.py` | 66 | `C0103:1`, `C0123:3`, `C0302:1`, `C0325:3`, `E1102:4`, `E1111:8`, `E1136:29`, `R0902:3`, `R0912:3`, `R0914:1`, `R0916:1`, `R1731:1`, `W0613:1`, `W0621:2`, `W0718:5` |
| `openclaw_activation_supervisor.py` | 13 | `C0123:1`, `E1111:3`, `E1136:4`, `R0902:2`, `R0911:1`, `R0917:1`, `W0613:1` |
| `openclaw_strict_server.py` | 3 | `C0103:1`, `W0706:1`, `W0718:1` |
| `strict_evidence_state.py` | 19 | `C0302:1`, `C0325:5`, `R0902:1`, `R0912:3`, `R0914:3`, `R0915:3`, `R0916:1`, `R1714:2` |
| `strict_grounding.py` | 24 | `C0302:1`, `C0325:1`, `R0912:4`, `R0913:2`, `R0914:3`, `R0915:1`, `W0212:9`, `W0612:1`, `W0718:2` |
| `strict_projection.py` | 27 | `C0302:1`, `C0325:1`, `R0902:2`, `R0912:3`, `R0913:2`, `R0914:6`, `R0915:2`, `W0108:1`, `W0212:7`, `W0611:1`, `W0707:1` |
| `strict_projection_publisher.py` | 15 | `C0302:1`, `R0912:1`, `R0913:4`, `R0914:1`, `R0915:1`, `W0108:1`, `W0611:3`, `W0613:2`, `W0706:1` |
| `tests/fixtures/openclaw_strict/adversarial_matrix.py` | 6 | `C0301:5`, `E0401:1` |
| `tests/fixtures/openclaw_strict/allowlist.py` | 1 | `E0401:1` |
| `tests/fixtures/openclaw_strict/audit_evidence.py` | 8 | `C0302:1`, `E0401:5`, `R0913:1`, `R0914:1` |
| `tests/fixtures/openclaw_strict/canonical_oracle.py` | 1 | `W0706:1` |
| `tests/fixtures/openclaw_strict/canonical_oracle_b.py` | 1 | `W0706:1` |
| `tests/fixtures/openclaw_strict/component_inventory.py` | 3 | `E0401:1`, `R1721:1`, `W0707:1` |
| `tests/fixtures/openclaw_strict/containment.py` | 1 | `E0401:1` |
| `tests/fixtures/openclaw_strict/digest_oracle.py` | 3 | `C0103:2`, `C0325:1` |
| `tests/fixtures/openclaw_strict/digest_oracle_b.py` | 4 | `C0103:2`, `C0123:1`, `C0325:1` |
| `tests/fixtures/openclaw_strict/fixture_manifest.py` | 12 | `E0401:4`, `W0611:8` |
| `tests/fixtures/openclaw_strict/fixture_platform.py` | 5 | `R0902:4`, `R0904:1` |
| `tests/fixtures/openclaw_strict/inventory.py` | 1 | `E0401:1` |
| `tests/fixtures/openclaw_strict/lifecycle_scripts.py` | 3 | `E0401:1`, `W0212:2` |
| `tests/fixtures/openclaw_strict/limits.py` | 2 | `E0401:1`, `R0902:1` |
| `tests/fixtures/openclaw_strict/preflight.py` | 3 | `E0401:1`, `R0914:1`, `W0611:1` |
| `tests/fixtures/openclaw_strict/protocol_fixture/schema_contract.py` | 9 | `E0401:4`, `R0912:1`, `R0914:1`, `R0915:1`, `W0612:2` |
| `tests/fixtures/openclaw_strict/run_isolated.py` | 27 | `C0411:4`, `C0413:10`, `E0401:11`, `E0611:1`, `R0914:1` |
| `tests/fixtures/openclaw_strict/suites.py` | 1 | `E0401:1` |
| `tests/test_bound_read_scope.py` | 3 | `W0404:1`, `W0611:1`, `W0621:1` |
| `tests/test_mcp_openclaw_strict.py` | 10 | `C0209:1`, `R1702:1`, `W0212:3`, `W0612:1`, `W0613:3`, `W0718:1` |
| `tests/test_openclaw_activation_controller.py` | 48 | `C0302:1`, `C0413:2`, `E0401:3`, `W0212:20`, `W0611:2`, `W0612:20` |
| `tests/test_openclaw_activation_supervisor.py` | 23 | `C0413:2`, `E0401:2`, `E1101:3`, `E1123:1`, `W0212:14`, `W0612:1` |
| `tests/test_openclaw_strict_packet_contract.py` | 62 | `C0302:1`, `C0304:1`, `C0413:3`, `E0401:47`, `R0914:1`, `W0212:2`, `W0404:4`, `W0611:1`, `W0621:2` |
| `tests/test_strict_evidence_state.py` | 4 | `C1803:1`, `W0611:2`, `W0612:1` |
| `tests/test_strict_grounding.py` | 13 | `C0302:1`, `W0612:8`, `W0613:4` |
| `tests/test_strict_projection.py` | 81 | `C0301:1`, `C0302:1`, `C0325:1`, `C1803:1`, `E1101:5`, `R0913:1`, `R0914:4`, `R1714:1`, `W0212:33`, `W0404:9`, `W0612:10`, `W0613:3`, `W0621:9`, `W0632:1`, `W0718:1` |
| `tests/test_strict_projection_publisher.py` | 19 | `C0302:1`, `C1803:1`, `R0914:2`, `W0404:2`, `W0611:1`, `W0612:6`, `W0613:1`, `W0621:1`, `W0632:2`, `W0718:2` |
| `tests/test_strict_projection_recovery.py` | 1 | `C0301:1` |
| `tests/test_strict_snapshot_revocation.py` | 3 | `W0611:3` |

The 167 new aggregate `R0801` occurrences are governed separately by Architecture §18.9. The six
additional, `R0801`-only paths are exactly
`tests/fixtures/openclaw_strict/case58_oracle.py`,
`tests/fixtures/openclaw_strict/constants.py`,
`tests/fixtures/openclaw_strict/protocol_fixture/pinned_vectors.py`,
`tests/fixtures/openclaw_strict/protocol_fixture/schema_field_sets.py`,
`tests/fixtures/openclaw_strict/protocol_fixture/schema_instances.py`, and
`tests/fixtures/openclaw_strict/protocol_fixture/specimens.py`. Together with the 38 table rows,
they are the closed 44-path edit set; the observed report and table are an input inventory, not a
license to edit any other file named inside an `R0801` message.

No implementation action is authorized until the new semantic parent and paired milestone overlay
receive exact-tip Kiro PASS and Ryan issues a grant naming both commits, preserved source tip
`9c6421a6891fd8a861a51f4fed410f541b53148c`, branch, exact 44 paths, integration baseline, new
parent-bound runtime prefix and durable evidence root. After that grant, execution order is fixed:

1. Codex proves the implementation branch/worktree is clean, pushed and exactly at `9c6421a`; the
   Pylint failure, two M8 passes and seven MCP passes remain retained evidence, not inherited final
   acceptance.
2. Grok cherry-picks every commit in the reviewed linear first-parent range after
   `c5513d50b656f9cc9e6423ea819438f975d16ee5` through the final milestone-overlay commit named in
   Ryan's grant, oldest to newest, without a merge, gap, reorder, squash, edit, conflict resolution,
   branch recreation or history rewrite, then pushes and stops. Codex proves the range changes only
   the four reviewed documents and that each final blob/mode equals the reviewed overlay. A
   commit-specific `CONTINUE` is mandatory.
3. **L1 production checkpoint.** Grok changes only the nine top-level production paths in the
   §18.9 set, preserving every public interface, serialized byte contract, exception/refusal effect
   and injected-port behavior. It may extract only private in-file helpers. It pushes and stops.
   Codex inspects the complete diff, dependencies, signatures, schemas, permissions and a targeted
   Pylint report for those nine paths before issuing `CONTINUE`, `CORRECT`, `PAUSE` or
   `REQUIRE TEST`.
4. **L2 fixture/test checkpoint.** Grok changes only the remaining 35 exact paths. It repins the
   reviewed parent/overlay only in the already frozen constants/assertions/comments, preserves
   every node ID and expected outcome, applies Architecture §18.9's suppression hierarchy, pushes
   and stops. Codex inspects the full diff and an explicit suppression inventory. Any unlisted
   path, changed selector/node/outcome, broad disable or shared production/oracle helper is
   `PAUSE`.
5. **L3 gate-correction checkpoint.** Codex runs the full unchanged Pylint command and regression
   gate in a fresh disposable clone using the exact workflow versions. If it fails only on a
   still-increased fingerprint inside the 44-path set, Codex issues `CORRECT` naming the exact
   fingerprint and Grok may correct only that finding before pushing and stopping again. A
   baseline/config/gate failure, 45th path or required contract change is `PAUSE`; no finding is
   waived to finish the milestone.
6. Once the unchanged gate passes at one clean pushed commit, Codex proves the three protected
   Pylint blobs match their §18.9 IDs, `git diff --check` is clean, no dependency/config/permission/
   schema/selector change occurred, all 44 paths and only those paths differ beyond the reviewed
   plans, and all suppressions satisfy §18.9.
7. At that same exact commit and without source edits between runs, Codex executes §10.8's complete
   repository pytest differential against `9c6421a`, then the unchanged isolated M8 runner twice
   from fresh roots, then the seven exact legacy MCP files. The M8 node/outcome counts and
   identities must equal the accepted `9c6421a` evidence. A candidate-only or changed pytest
   failure is `PAUSE` or, only when the cause is demonstrably inside the frozen 44 paths and the
   correction preserves every contract, `CORRECT`; missing evidence is `REQUIRE TEST`.
8. Codex inventories the final source/component hashes and runtime pre/post tree, copies all raw
   Pylint/pytest/M8/MCP output and suppression evidence to the Ryan-designated durable root, and
   verifies the staging-to-durable byte/hash mapping. Kiro then reviews the exact integrated tip
   and evidence. Ryan alone decides PR/merge.

The exact Pylint commands remain those in `.github/workflows/pylint.yml`: install current
`requirements.txt` plus `pylint==4.0.6 pytest==9.1.1`; run
`pylint $(git ls-files "*.py") --output-format=json`; and invoke
`scripts/pylint_regression_gate.py ci` with base ref
`9193f5ec744f059d07a20612489b210527b5660a`. The base, report command, fingerprint algorithm,
workflow file, committed baseline, gate script, dependency set and file discovery are not editable.
The final gate must exit zero; targeted or preserved-tip comparisons are diagnostic only.

Forbidden changes include `pylintrc`/pyproject/setup configuration, ignore patterns, per-file
exclusions, thresholds, plugin changes, generated baselines, `--exit-zero`, path filtering,
`disable=all`, `skip-file`, category-wide or unexplained suppressions, new dependencies/modules,
public signature changes, schema/interface changes, selector/deselection/node changes, authority or
permission changes, and edits to `atomic_files.py`, `canonical_json.py`,
`tests/test_writer_census.py` or any other current-main path merely paired by `R0801`.

This correction changes no T0–T5 meaning and authorizes no merge, real OpenClaw operation or update,
Gate D/W/D-V/E/F, watch activation, live data, deployment or promotion.

### 10.8 M11 full-pytest differential obligations

Architecture §18.10 controls. The comparison baseline is exactly
`9c6421a6891fd8a861a51f4fed410f541b53148c`; the currently preserved candidate is
`3f8ef8312e3f3c98915320bd1b988bac5d8d96a9`; the first paused differential candidate is
`853ef98ede44f2d171e5354b065e11f83558e010`. Neither identity is inferred from a worktree. Before
execution Codex resolves every identity as a commit, proves the baseline is an ancestor of the
candidate, proves the candidate and its explicit upstream are identical and clean, and records
their source trees. A later candidate is allowed only if Ryan's resume grant names it, every
non-plan byte equals `853ef98`, and the remaining delta is only the newly Kiro-reviewed planning
range; any other source change is `PAUSE`. Codex also verifies the prior durable PAUSE ledger
SHA-256 `3c2a50d1a61578fa235524bc26493a2b1458ba60d729b039c0a66d27ddce0c1e` before using it as the
reconciliation input.

Codex, not Grok, owns the comparison. It performs the following held sequence after exact-tip Kiro
PASS and a new Ryan grant:

1. Inventory one separately reviewed CI-compatible environment: executable and library paths,
   Python/pytest versions, installed distributions, locale, timezone, environment-variable
   allowlist, resource limits and tree hash. Predeclare one disposable execution slot with fixed
   absolute `source/`, `state/`, `pytest-tmp/` and `report/junit.xml` path strings. Before every
   complete run or rerun, preserve the preceding evidence, remove only those prevalidated slot
   children, recreate them empty with identical modes, prove empty trees/no symlinks, export the
   exact Git tree into the same `source/` path and verify its tracked blob/mode inventory. HOME,
   all XDG roots, `CONVMEM_CONFIG`, `TMPDIR`, cwd, argv and every allowlisted environment byte must
   be identical at process start. Any unrepresented filesystem metadata must be fixed identically
   or proved equal. No live corpus, credential, user config, OpenClaw process, host fallback,
   retained state or shared mutable cache is permitted.
2. At each tip, from a fresh process, run the unchanged complete selector `python -m pytest -q`
   with only built-in output reporters appended:
   `--junitxml=<fixed-slot-report-path> -o junit_family=xunit1`. Capture exact argv,
   environment, stdout, stderr, status, duration and JUnit bytes. No marker, path, node, keyword,
   deselection, retry plugin or exit-code override is allowed.
3. Parse both JUnit files exactly as Architecture §18.10 specifies. Emit canonical sorted records,
   their SHA-256 values, equal/missing/added node sets, outcome deltas and failure-signature deltas.
   Do not derive expected values from the candidate or normalize any byte beyond the three closed
   substitutions in §18.10. Keep all raw 40-hex and 64-hex semantic values. For the five exact R2b
   nodes only, emit the separate structured identity record and both raw signatures; no mismatch
   is cleared at this step.
4. For every node with an outcome or signature mismatch, run that exact node independently at both
   tips in fresh processes through the reset fixed-path slot, again with xunit1 evidence. A
   mismatch clears only under §18.10's closed non-failing, confirmed-improvement,
   identical-retained-failure or exact-five-node R2b identity-rotation dispositions. For an R2b
   disposition, emit the complete authority-content manifest at each tip, prove equal member sets,
   verify every member against Git bytes, prove every changed member lies inside the reviewed
   44-path remediation, independently recompute the prefixed canonical-manifest digest, and prove
   §18.10's exact 118-member path-set hash and sole `mcp_server.py` content transition before
   matching the frozen committed/baseline/candidate identities. Retain the original
   complete-run mismatch and both diagnostic reruns. Any candidate regression, changed member set,
   unexpected identity/framing, other changed signature, unclassified or non-reproducing result is
   `PAUSE`, not a waiver.
5. Emit a final signed-off evidence ledger containing the verdict token, both source commits and
   trees, reset/environment inventory hashes, complete-run record hashes, every mismatch
   disposition, both authority manifests and every identical or identity-rotation retained
   failure. The only passing token for this step is
   `PYTEST_DIFFERENTIAL_PASS`. The ledger must state `FULL_PYTEST_PASS=false` whenever either
   complete run retains a failure or error.
6. Without source edits, run the two exact isolated M8 executions and seven legacy MCP files. Their
   existing commands, selectors, four deselections, expected counts, dependencies and evidence
   contracts remain unchanged. The differential verdict cannot compensate for any failure there or
   for a nonzero Pylint gate.
7. Copy the raw and canonical evidence to the Ryan-designated durable root, verify every
   volatile-to-durable byte/hash mapping, and stop for Kiro exact-tip conformance review. Ryan alone
   decides merge readiness.

Identical and closed identity-rotation retained baseline/candidate failures remain explicitly
recorded repository debt. They
must never be described as fixed, accepted, expected success, full-pytest PASS or proof that the
complete repository is healthy. This differential rule is scoped only to whether the exact M11
correction introduced a pytest regression. It changes no test, selector, CI workflow, committed
baseline, dependency, permission, runtime behavior or T0–T5 semantic contract.

This plan edit authorizes none of the sequence above. Gate D/W/D-V/E/F, real OpenClaw, watch
activation, live data, merge, deployment and promotion remain separately blocked.

### 10.9 M11 final M8 authority-packet reconciliation obligations

The governed §10.8 sequence is complete at clean pushed candidate
`7f2a2e22c74cf9fd87c00982d1ea0ce18fc978af`. Its differential verdict is
`PYTEST_DIFFERENTIAL_PASS=true` and `FULL_PYTEST_PASS=false`; both complete runs contain the same
2,912 nodes and outcomes, and all 238 retained failures/errors have a closed disposition. The
unchanged current-main Pylint gate also passes. Final M8 run 1 then stopped before fixture creation
with status 2 because the runner embedded preceding parent `b810fcd7` instead of authorized parent
`9c5c2bf7`. The runner never reached the runtime. The PAUSE classification is durable and hashes to
`e217e5607640b5f1985ad57256f7911fc8b409364ecc25c5f98e22c25082105c`; its unchanged runtime
revalidation retained tree SHA-256
`74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`.

After Kiro PASS and a new Ryan grant, execute only this held sequence:

1. Prove the implementation branch is clean, pushed and exactly at `7f2a2e2`. Apply every commit
   in the complete reviewed linear plan range after
   `b1b2341a4f98701f5784631f866c5405174c7414` through the final overlay named in the grant, oldest
   to newest. Do not merge, rebase, squash, edit, skip, reorder, resolve a conflict, create an empty
   commit or recreate the branch. Push and stop.
2. Codex verifies that the four final planning-document blobs and modes equal the reviewed overlay,
   every non-plan byte equals `7f2a2e2`, the prior PAUSE artifact/hash exists, and the runtime
   inventory is unchanged. Only a commit-specific `CONTINUE` may release the source correction.
3. Change only four 40-hex literals in exactly two files:
   - in `tests/fixtures/openclaw_strict/constants.py`, set `SEMANTIC_PARENT_SHA` to the grant-named
     semantic parent and `M11_REVIEWED_OVERLAY_SHA` to the grant-named final overlay;
   - in `tests/test_openclaw_strict_packet_contract.py`, set only the corresponding two expected
     literals in `test_plan_and_baseline_constants_frozen` to those same values.
   Do not change formatting, names, logic or any other byte. Commit, push and stop.
4. Codex independently proves the correction diff has exactly those two paths and four literal
   substitutions; the four reviewed document blobs remain exact; all other non-plan bytes equal
   `7f2a2e2`; `CODE_BASELINE_SHA`, `M11_CONTROL_PLANE_INPUTS`, runtime hash, allowlists, selectors,
   four deselections, dependencies, permissions, node IDs and outcomes are unchanged. Any extra
   byte or path is `PAUSE`.
5. Rebind, but do not alter, the same qualified runtime under the grant-named parent path. Recreate
   the same fixed disposable execution slot and durable evidence destination. Independently verify
   the complete runtime inventory and tree hash before execution.
6. Because the source tree changed, repeat §10.8's complete
   `9c6421a6891fd8a861a51f4fed410f541b53148c`-versus-final-candidate differential in the identical
   environment and fixed paths, including every symmetric mismatch rerun and the exact five-node
   R2b proof. Historical `7f2a2e2` evidence is retained but does not substitute for this run.
7. If and only if `PYTEST_DIFFERENTIAL_PASS` is re-established, rerun the unchanged current-main
   Pylint gate. Then run M8 twice from separate fresh roots with `--plan-sha` equal to the new
   semantic parent and the unchanged selectors/counts, followed by the same seven legacy MCP
   regression files. No OpenClaw process may run.
8. Preserve raw output, JUnit, canonical comparison, mismatch reruns, R2b proof, Pylint result,
   both M8 runs, MCP outputs, source/component/runtime inventories and staging-to-durable hash
   mappings. Stop for Kiro exact-tip conformance review. Ryan alone decides merge readiness.

The prior M8 refusal stays `PAUSE`; it is never rewritten as a failed test or passing run. A new
differential mismatch, changed R2b manifest, Pylint regression, M8 node/count/outcome deviation,
MCP failure, runtime mutation, required source edit or evidence asymmetry is `PAUSE`. This section
changes no schema, algorithm, tool surface, authority, permission, dependency, selector or T0–T5
behavior. It authorizes no implementation or evidence execution by itself.

### 10.10 M11 bundle-schema literal correction obligations

The governed §10.9 sequence produced clean pushed candidate
`d7b15926ab7e4e41b8a80edba5edbe4bfed4c165`. Its fresh differential again has equal 2,912-node
sets/outcomes, closes all 238 retained failure/error nodes and establishes
`PYTEST_DIFFERENTIAL_PASS=true` while honestly retaining `FULL_PYTEST_PASS=false`. The unchanged
current-main Pylint regression gate also passes with 458 findings and no new/increased fingerprint.
Final M8 run 1 then completed the strict, Node and legacy command groups with status 2: 210 strict
passes, 28 strict failures, 29 Node passes, 115 legacy passes, one skip and four deselections. All
28 failures are the same `bundle_schema` refusal caused by the one invented production literal
`convmem.strict-fixture-work.bundle.v2`; the canonical schema, fixtures and tests use
`convmem.strict-fixture-bundle.v2`. The durable PAUSE classification hashes to
`c25ece6380d0b1cf4989a010419307dfdc29c2ecc31b9c4dd47faaee23b89148`, and the runtime remained
unchanged at tree SHA-256 `74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`.

After Kiro PASS and a new Ryan grant, execute only this held sequence:

1. Prove the implementation branch is clean, pushed and exactly at `d7b1592`. Apply every commit
   in the complete reviewed linear plan range after
   `57285608b2ee9ec5950201968bc533b8830a6ea8` through the final overlay named in the grant,
   oldest to newest. Do not merge, rebase, squash, edit, skip, reorder, resolve a conflict, create
   an empty commit or recreate the branch. Push and stop.
2. Codex verifies that the four final planning-document blobs and modes equal the reviewed overlay,
   every non-plan byte equals `d7b1592`, the PAUSE classification/evidence exists, and the runtime
   inventory is unchanged. It also proves the old invented literal occurs exactly once in the
   candidate, at the permitted publisher check, and nowhere in schemas or tests. Only a commit-
   specific `CONTINUE` may release the source correction.
3. In exactly `strict_projection_publisher.py`, replace only
   `convmem.strict-fixture-work.bundle.v2` with `convmem.strict-fixture-bundle.v2`. Do not change
   formatting, control flow, errors, tests or any other byte. Commit, push and stop.
4. Codex independently proves the correction diff is exactly one path and one literal
   substitution; the four reviewed document blobs remain exact; every other non-plan byte equals
   `d7b1592`; and all schemas, test files, allowlists, selectors, four deselections, dependencies,
   permissions, node IDs and outcomes are unchanged. Any extra byte or path is `PAUSE`.
5. Rebind, but do not alter, the same qualified runtime under the grant-named parent path. Recreate
   the fixed disposable execution slot and durable evidence destination. Independently verify the
   complete runtime inventory and tree hash before execution.
6. Because the source tree changed, repeat §10.8's complete
   `9c6421a6891fd8a861a51f4fed410f541b53148c`-versus-final-candidate differential in the identical
   environment and fixed paths, including every symmetric mismatch rerun and the exact five-node
   R2b proof. Historical `d7b1592` evidence remains retained but does not substitute for this run.
7. If and only if `PYTEST_DIFFERENTIAL_PASS` is re-established, rerun the unchanged current-main
   Pylint gate. Then run M8 twice from separate fresh roots with `--plan-sha` equal to the new
   semantic parent and unchanged selectors/counts, followed by the same seven legacy MCP
   regression files. The existing tests are the regression harness; no test edit is authorized.
   No OpenClaw process may run.
8. Preserve raw output, JUnit, canonical comparison, mismatch reruns, R2b proof, Pylint result,
   both M8 runs, MCP outputs, source/component/runtime inventories and staging-to-durable hash
   mappings. Stop for Kiro exact-tip conformance review. Ryan alone decides merge readiness.

The failed M8 run stays `PAUSE`; it is never rewritten as a passing run. A new differential
mismatch, changed R2b manifest, Pylint regression, M8 node/count/outcome deviation, MCP failure,
runtime mutation, test change, second source edit or evidence asymmetry is `PAUSE`. This section
changes no schema, algorithm, tool surface, authority, permission, dependency, selector or T0–T5
behavior. It authorizes no implementation or evidence execution by itself.

### 10.11 M11 post-bundle authority-packet correction obligations

The governed §10.10 sequence produced clean pushed candidate
`851edbe49b820bd4081809022b10f67c30fef47a`. Its only source edit after plan application is the
authorized one-literal publisher correction. Its fresh differential again has equal 2,912-node
sets/outcomes, closes all 238 retained failure/error nodes and establishes
`PYTEST_DIFFERENTIAL_PASS=true` while retaining `FULL_PYTEST_PASS=false`. The unchanged
current-main Pylint regression gate passes with 458 findings and no new/increased fingerprint.
Final M8 run 1 then exited 2 during argument validation with
`plan_sha_mismatch: expected 48c9ce01bf557ff95fd82b84c3b0ab2e7e9f18cb`: the reviewed command
supplied parent `b46a16a3cdc928e98fba83cd64b17439d1734695`, while the fixture authority packet still
contains preceding parent `48c9ce01…` and overlay `57285608…`. No source export, fixture,
integration import or runtime use occurred. The runtime inventory remained unchanged at tree
SHA-256 `74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`; the durable PAUSE
classification hashes to `3fbfab4bac23c30325961d21a974ec4ed03229759c1b974686d323c061982c77`.

After Kiro PASS and a new Ryan grant, execute only this held sequence:

1. Prove the implementation branch is clean, pushed and exactly at `851edbe4`. Apply every commit
   in the complete reviewed linear plan range after
   `6b1b90b4865dc0b92e0ead470136eeebc3bd8447` through the final overlay named in the grant,
   oldest to newest. Do not merge, rebase, squash, edit, skip, reorder, resolve a conflict, create
   an empty commit or recreate the branch. Push and stop.
2. Codex verifies that the four final planning-document blobs and modes equal the reviewed overlay,
   every non-plan byte equals `851edbe4`, the PAUSE evidence/classification exists, and the runtime
   inventory is unchanged. It also proves the corrected publisher literal remains exact. Only a
   commit-specific `CONTINUE` may release the authority-packet correction.
3. Change exactly four 40-hex literals across exactly two files:
   - in `tests/fixtures/openclaw_strict/constants.py`, set only `SEMANTIC_PARENT_SHA` and
     `M11_REVIEWED_OVERLAY_SHA` to the grant-named semantic parent and final overlay; and
   - in `tests/test_openclaw_strict_packet_contract.py`, set only the corresponding two expected
     literals in `test_plan_and_baseline_constants_frozen` to those same values.
   Commit, push and stop. No other test logic, source byte or path may change.
4. Codex independently proves the correction diff is exactly those two paths and four literal
   substitutions; declarations equal assertions; the four reviewed document blobs remain exact;
   every other non-plan byte equals `851edbe4`; and the publisher correction, schemas, allowlists,
   selectors, four deselections, dependencies, permissions, node IDs and outcomes are unchanged.
   Any extra byte or path is `PAUSE`.
5. Rebind, but do not alter, the same qualified runtime under the grant-named parent path. Recreate
   the fixed disposable execution slot and durable evidence destination. Independently verify the
   complete runtime inventory and tree hash before execution.
6. Because the source tree changed, repeat §10.8's complete
   `9c6421a6891fd8a861a51f4fed410f541b53148c`-versus-final-candidate differential in the identical
   environment and fixed paths, including every symmetric mismatch rerun and the exact five-node
   R2b proof. Historical `851edbe4` evidence remains retained but does not substitute for this run.
7. If and only if `PYTEST_DIFFERENTIAL_PASS` is re-established, rerun the unchanged current-main
   Pylint gate. Then run M8 twice from separate fresh roots with `--plan-sha` equal to the new
   semantic parent and unchanged selectors/counts, followed by the same seven legacy MCP
   regression files. No OpenClaw process may run.
8. Preserve raw output, JUnit, canonical comparison, mismatch reruns, R2b proof, Pylint result,
   both M8 runs, MCP outputs, source/component/runtime inventories and staging-to-durable hash
   mappings. Stop for Kiro exact-tip conformance review. Ryan alone decides merge readiness.

The pre-fixture M8 refusal stays `PAUSE`; it is never rewritten as a failed test or passing run. A
new differential mismatch, changed R2b manifest, Pylint regression, M8 node/count/outcome
deviation, MCP failure, runtime mutation, fifth literal, third path, required source edit or
evidence asymmetry is `PAUSE`. This section changes no schema, algorithm, tool surface, authority,
permission, dependency, selector or T0–T5 behavior. It authorizes no implementation or evidence
execution by itself.

### 10.12 M11 current-main reconstruction obligations

Architecture §18.14 controls. The final reviewed M11 evidence candidate is
`cd60cf19dca6706e4175e9f82c9ba55e41bca10b` (`R`), historical integration baseline is
`9193f5ec744f059d07a20612489b210527b5660a` (`B`), and exact current main is
`a92a74eb326b3eaa59087b707de10153c7cc0c63` (`N`). No action below is authorized until Kiro PASS
and a new Ryan grant name the exact semantic parent, final overlay, three held-commit boundaries,
new branch, runtime/evidence paths and all frozen identities.

Execute only this held sequence:

1. Fetch origin. Require `origin/main == N`, `origin/feat/2026-09-23-openclaw-convmem-m11-integration == R`,
   both source trees readable, and the old branch clean and preserved. If main moved or either ref
   differs, `PAUSE`. Codex creates and pushes the grant-named new branch from exact `N` in a
   dedicated worktree; it never switches the live checkout.
2. Independently recompute Architecture §18.14's path algebra from Git trees. Require `M` = 40
   paths/hash `596a484c…`, `D` = 124 paths/hash `af1b9fd8…`, `P` = 120 paths/hash `60903bc1…`,
   `M ∩ D` = only the Switchboard STATUS path, `M ∩ P` empty and no deletion in `P`.
3. Grok sets exactly the 120 `P` paths to `R`'s blobs and modes, commits, pushes with an explicit
   refspec and stops. Codex proves the 120-path digest, exact blob/mode equality and that every
   other path still equals `N`. Only a commit-specific `CONTINUE` releases step 4.
4. Grok sets exactly the four §18.8 control-plane paths to the final reviewed overlay's blobs and
   mode `100644`, commits, pushes and stops. Codex proves four-blob equality and that every other
   byte equals the prior checkpoint. Only a new commit-specific `CONTINUE` releases step 5.
5. Grok changes exactly six 40-hex literals across exactly two paths: the values and matching
   frozen assertions for `CODE_BASELINE_SHA=N`, the grant-named `SEMANTIC_PARENT_SHA`, and the
   grant-named `M11_REVIEWED_OVERLAY_SHA`. It commits, pushes and stops. No formatting, logic,
   name, test selection or other byte may change.
6. Codex proves the final composition: outside `P ∪ C` equals `N`; `P` except the two identity
   files equals `R`; those two files differ from `R` only by six substitutions; and `C` equals the
   reviewed overlay. It also proves no deletion, extra path, symlink or mode drift. Any mismatch is
   `PAUSE`, not a correction opportunity.
7. Rebind without altering the qualified runtime at the grant-named parent/current-main path;
   verify all 30,421 inventoried files, modes and hashes, zero symlinks/unlisted/writable entries,
   resolved dependency paths and tree SHA-256
   `74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`. Recreate the exact fixed
   slot and durable evidence root. Grok performs no runtime/evidence operation.
8. Codex runs complete `python -m pytest -q` at `N` and the final candidate sequentially in the
   identical fixed slot with only the built-in xunit1 reporter. Apply Architecture §18.14's
   current-main node-set and outcome rules, symmetric reruns and exact five-node R2b disposition.
   The 119-member path-set hash is `cd13b301…`; main identity is `644552c…`, reconstructed identity
   `3a74d3d…`, and only `mcp_server.py` changes from `f9ac448c…` to `7fcbdcb4…`. Any additional
   identity/member/signature exception is `PAUSE`.
9. Only after `CURRENT_MAIN_DIFFERENTIAL_PASS`, run the unchanged full-tree Pylint regression gate.
   Then run M8 twice from fresh roots with `--plan-sha` equal to the new semantic parent and
   `CODE_BASELINE_SHA=N`, followed by the same seven legacy MCP files. Require 238 strict passes,
   29 Node passes, 115 legacy passes, one skip and four deselections in each M8 run; preserve exact
   node/outcome and cross-run identity. No OpenClaw process may run.
10. Verify raw output, JUnit, canonical records, mismatch reruns, R2b manifests, Pylint output,
    both M8 runs, MCP outputs, source/component/runtime inventories and staging-to-durable hashes.
    Kiro reviews the exact final tip and evidence. Before PR creation and before Ryan's merge
    decision, fetch again and require `origin/main == N`; otherwise `PAUSE`.

The new branch is a deterministic source-tree composition, not a replay, rebase or merge of the
105-commit branch. A fourth implementation commit, conflict resolution, force-push, product
rewrite, omitted path, test/CI/baseline/config/runtime-content edit or required source correction is
`PAUSE`. A squash PR is eligible only when its predicted tree over exact `N` equals the reviewed
candidate tree. Agents do not merge; Ryan alone decides PR creation and merge. This plan edit
authorizes none of the execution above.

### 10.13 M11 current-main three-tip differential obligations

Architecture §18.15 controls. Exact current main is
`a92a74eb326b3eaa59087b707de10153c7cc0c63` (`N`), the preserved reviewed Switchboard candidate is
`cd60cf19dca6706e4175e9f82c9ba55e41bca10b` (`R`), and the completed §10.12 reconstruction PAUSE
tip is `30bc134d74d7eeb4cef4d6371a5e96c926f0f2ca` (`H0`). The sealed PAUSE ledger has SHA-256
`3bd89ebf3dd016d5fc709215862ae491688cb878c3477fbd9f21f3619b2d256e`; the canonical comparison
has SHA-256 `03873a4d4e368e5b5fd3de86140e3fd9b74525c3e83b966275d556fd9728693b`.
The current-main branch is preserved, clean and pushed. No action below is authorized until Kiro
PASS and a new Ryan grant name the exact semantic parent, final overlay, complete reviewed linear
plan range, `N`, `R`, `H0`, fixed slot, runtime/evidence paths, four-literal correction and all
evidence authority.

Execute only this held sequence:

1. Fetch origin. Require `origin/main == N`, the preserved reviewed branch equals `R`, the current-
   main branch equals `H0`, all three worktrees/trees are readable and clean, and the PAUSE evidence
   hashes exactly as above. Any moved ref, dirty source, missing evidence or mismatched hash is
   `PAUSE`.
2. Re-prove §18.14's `M/D/C/P` algebra and `H0` tree composition. Require all four planning blobs
   at `H0` to equal the plan-base overlay named by the new grant. Grok then applies every commit in
   the complete reviewed linear range from that base through the final reviewed overlay, oldest to
   newest, without merge, squash, edit, empty commit, conflict resolution or history rewrite. Grok
   pushes and stops.
3. Codex proves the four planning-document blobs and mode `100644` equal the final reviewed overlay
   and every non-plan byte equals `H0`. Only a commit-specific `CONTINUE` releases step 4.
4. Grok changes exactly four 40-hex values across exactly two paths: the declarations for
   `SEMANTIC_PARENT_SHA` and `M11_REVIEWED_OVERLAY_SHA` in
   `tests/fixtures/openclaw_strict/constants.py`, and their two matching frozen assertions in
   `tests/test_openclaw_strict_packet_contract.py`. `CODE_BASELINE_SHA` remains `N`. No formatting,
   logic, selector, expectation or other byte changes. Grok commits, pushes and stops.
5. Codex proves the exact two-path/four-substitution diff, declaration/assertion equality, unchanged
   test logic, unchanged publisher correction, exact final plan blobs, and equality of every other
   non-plan byte to `H0`. The resulting exact pushed tip is final candidate `F`. Any fifth
   substitution, third path or other difference is `PAUSE`.
6. Rebind without altering the qualified runtime at the new grant's parent/current-main path.
   Re-prove all 30,421 files, modes and hashes, zero symlinks/unlisted/writable entries, resolved
   dependencies and tree SHA-256
   `74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`. Recreate the grant-named
   fixed slot and durable evidence root. Grok performs no runtime or evidence operation.
7. Codex runs complete `python -m pytest -q` sequentially at `N`, `R` and `F` in the same fixed
   slot, resetting it to a verified empty state before each run. The CI-compatible environment,
   argv, built-in xunit1 reporter, dependency closure, resource limits and allowlisted environment
   are identical. Preserve raw output, exact status, complete JUnit and canonical records for all
   three runs.
8. Apply Architecture §18.15's partition. `nodes(N)` must be a subset of `nodes(F)`, and common
   `N`/`F` nodes retain §18.14 outcome/signature/rerun rules and the exact five-node R2b proof. Let
   `S = nodes(F) - nodes(N)`: require exactly 238 identities; identity SHA-256 `fe50be2f…`;
   identity/outcome SHA-256 `2c03a11c…`; 160 passed identities SHA-256 `b98f02f3…`; 78 failed
   identities SHA-256 `e3fdc26e…`; every `S` identity present in `R`; equal `R`/`F` outcomes; and
   equal normalized signatures for retained failures after symmetric fresh-process reruns. An
   `F`-only identity absent from both baselines, any unresolved mismatch, incomplete collection,
   generic normalization or sixth R2b node is `PAUSE`. `R`-only identities are enumerated but do
   not override current-main ownership.
9. Only after `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`, run the unchanged full-tree Pylint
   regression gate, then two fresh-root M8 runs and the same seven legacy MCP files. Require the
   existing exact M8 node/outcome counts, four deselections, source/component/runtime identities
   and cross-run equality. `FULL_PYTEST_PASS` remains false while any retained failure exists.
10. Verify all raw/JUnit/canonical records, symmetric reruns, R2b proofs, Pylint/M8/MCP outputs,
    source/component/runtime inventories and staging-to-durable mappings. Kiro reviews the exact
    final tip and evidence. Before PR creation and before Ryan's merge decision, fetch again and
    require `origin/main == N`; otherwise `PAUSE`.

The existing §18.10 normalizations are the complete allowlist; this correction adds no new
normalization or exception. It changes no product/test behavior, CI/baseline, dependency,
permission, selector, runtime content, T0–T5 semantic or later-gate boundary. This section
authorizes planning only: no plan application, four-literal edit, suite, PR, merge, deployment or
real OpenClaw action may begin without exact-tip Kiro PASS and a new Ryan grant.

### 10.14 M11 advanced-current-main reconstruction obligations

Architecture §18.16 controls. Prior baseline `N0` is
`a92a74eb326b3eaa59087b707de10153c7cc0c63`; exact advanced current main `N1` is
`5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`; preserved reviewed candidate `R` is
`cd60cf19dca6706e4175e9f82c9ba55e41bca10b`; and the completed three-tip preflight input `F0` is
`d276cb4ab0a0613b965e772d49d378e761df337e`. The §10.13 preflight observed `origin/main=N1`
before creating its fixed slot, run root or any suite process and therefore stopped. No historical
PASS or unexecuted grant transfers to `N1`.

Execute only this held sequence after exact-tip Kiro PASS and a new Ryan grant:

1. Fetch origin. Require `origin/main == N1`, the preserved reviewed branch equals `R`, the first
   reconstruction branch equals `F0`, all named trees are readable and the two preserved branches
   are clean/pushed. Require the §10.13 evidence run and fixed slot to remain absent. Any moved ref,
   dirty source or unexpected run artifact is `PAUSE`.
2. Independently recompute Architecture §18.16's algebra. Require advance `A` = 11 paths/hash
   `0566d14e…`; prior-candidate `Q` = 124 paths/hash `af1b9fd8…`; `A ∩ Q` empty;
   `paths(B..N1)` = 45 paths/hash `670241f7…`; reviewed `D` = 124 paths/hash `af1b9fd8…`;
   product `P` = 120 paths/hash `60903bc1…`; the only `paths(B..N1) ∩ D` member the Switchboard
   STATUS; `paths(B..N1) ∩ P` empty; and no deletion in `A` or `P`.
3. Codex creates and pushes the grant-named new branch from exact `N1` in a dedicated worktree.
   Grok sets exactly the 120 `P` paths to `R`'s blobs and modes, commits, pushes with an explicit
   refspec and stops. Codex proves exact blob/mode equality and that every other path still equals
   `N1`. Only a commit-specific `CONTINUE` releases step 4.
4. Grok sets exactly the four §18.8 control-plane paths to the final reviewed overlay's blobs and
   mode `100644`, commits, pushes and stops. Codex proves four-blob equality and that every other
   byte equals the prior checkpoint. Only a new commit-specific `CONTINUE` releases step 5.
5. Grok changes exactly six 40-hex literals across exactly two paths: declarations and frozen
   assertions for `CODE_BASELINE_SHA=N1`, the grant-named `SEMANTIC_PARENT_SHA`, and the grant-
   named `M11_REVIEWED_OVERLAY_SHA`. It commits, pushes and stops. No formatting, logic, selector,
   expectation or other byte may change.
6. Codex proves final composition: outside `P ∪ C` equals `N1`; `P` except the two identity files
   equals `R`; those two files differ from `R` only by six substitutions; and `C` equals the final
   overlay. Prove the 120-member R2b path-set hash `fb062070…`, `N1` identity `b716152f…`, final
   resolved identity `e060dce4…`, and `mcp_server.py` as the sole changed member (`f9ac448c…` to
   `7fcbdcb4…`). Any other path/member/identity difference is `PAUSE`.
7. Rebind without altering the qualified runtime at the grant-named parent/`N1` path. Verify all
   30,421 inventoried files, modes and hashes, zero symlinks/unlisted/writable entries, resolved
   dependencies and tree SHA-256 `74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`.
   Require the new fixed slot and durable evidence root absent before creation. Grok performs no
   runtime or evidence operation.
8. Codex runs complete `python -m pytest -q` sequentially at `N1`, `R` and final candidate `F` in
   the same reset slot with identical environment, argv, built-in xunit1 reporter, dependencies
   and resource limits. Apply §18.15's exact 238-node partition, closed §18.10 normalization,
   symmetric mismatch reruns and the exact five-node advanced R2b proof. Collection difference,
   changed 238-node digest/outcome partition, path/reset asymmetry, unresolved signature, sixth R2b
   node or node absent from both baselines is `PAUSE`.
9. Only after `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`, run the unchanged full-tree Pylint
   regression gate, two fresh-root M8 runs and the same seven legacy MCP files. Require existing
   M8 counts, four deselections, source/component/runtime identities and cross-run equality.
   `FULL_PYTEST_PASS` remains false while any retained failure exists.
10. Verify raw output, JUnit, canonical records, all reruns, R2b proof, Pylint, both M8 runs, MCP,
    inventories and durable hashes. Kiro reviews the exact final tip/evidence. Before PR creation
    and before Ryan's merge decision, fetch and require `origin/main == N1`; otherwise `PAUSE`.

This is a new source-tree reconstruction from `N1`, not a plan replay, rebase, merge, cherry-pick
or continuation of `F0`. A fourth implementation commit, conflict resolution, product rewrite,
omitted path, test/CI/baseline/config/runtime-content edit or required source correction is
`PAUSE`. A squash PR is eligible only when its predicted tree over exact `N1` equals the reviewed
candidate tree. Agents do not merge; Ryan alone decides PR creation and merge. This plan edit
authorizes none of the execution above.

### 10.15 M11 inner-role signature reconciliation obligations

Architecture §18.17 controls. The advanced reconstruction is preserved, clean and pushed at
`776a4ca3d4215490fb26b882dca2df9a41e0e03a` (`H1`). Its complete same-slot `N1`/`R`/`H1`
runs, exact 238-node partition, closed five-node R2b proof and 166 isolated reruns completed.
The finalizer then issued `PAUSE` because exactly 22 packet-contract failures retained the same
inner-role assertion while pytest rendered their `os.environ` tails differently. The sealed PAUSE
ledger SHA-256 is `a6a2d95b6f294ad3893ea39fa8c739b15a7ea172d2067757492c49abf49399a6`;
the exact 22-node sorted-NUL identity-set SHA-256 is
`9fa64e04c15b96cbb935cb5b40d4e47a9cdd5869099d728a5213174c7244cbf6`. No positive
differential token exists, and no downstream gate ran.

Execute only this held sequence after exact-tip Kiro PASS and a new Ryan grant:

1. Require the implementation branch clean, pushed and exactly `H1`; require `origin/main` still
   equal `N1`; require `R` unchanged; verify the PAUSE ledger, diagnostic, PAUSE-manifest,
   rerun-plan and preliminary-comparison hashes from Architecture §18.17; and revalidate the
   unchanged runtime inventory. Any moved ref, missing byte or mutation is `PAUSE`.
2. Grok applies every commit in the complete reviewed linear plan range named by Ryan, oldest to
   newest, onto `H1`, with no conflict resolution, empty commit, edit, squash, merge, rebase or
   non-plan change. Grok pushes and stops. Codex proves that exactly the four planning-document
   blobs and modes equal the final overlay and every non-plan byte equals `H1`.
3. Only after a commit-specific `CONTINUE`, Grok changes exactly four 40-hex values across exactly
   two files: `SEMANTIC_PARENT_SHA` and `M11_REVIEWED_OVERLAY_SHA` in
   `tests/fixtures/openclaw_strict/constants.py`, plus their two frozen assertions in
   `tests/test_openclaw_strict_packet_contract.py`. `CODE_BASELINE_SHA` remains `N1`. Grok
   commits, pushes and stops. Codex proves the exact two-path/four-substitution diff and no fifth
   substitution or other byte.
4. Codex rebinds but does not alter the qualified runtime, creates the grant-named evidence root,
   resets the fixed slot, and freshly runs complete pytest at `N1`, `R` and final candidate `F`
   with identical argv, environment, dependencies, reporter, paths and resource limits. Prior raw
   output remains historical/diagnostic and supplies no PASS.
5. Apply §§18.10, 18.15 and 18.16 unchanged. Run every symmetric mismatch rerun. For only the
   exact §18.17 22-node set, parse each `R` complete, `F` complete, `R` rerun and `F` rerun record
   independently. Require outcome `failure`, empty type, exactly four message lines, both exact
   core lines, the exact two tail prefix/suffix pairs and byte-identical duplicated inner
   `environ(...)` payload within each record. Map only eligible records to the closed semantic
   signature; retain and hash every raw message and JUnit record unchanged.
6. A 23rd node, changed set hash, missing one of four records, nonfailure outcome, nonempty type,
   different line count/core/tail, unequal duplicated payload, generic environment/path/hash/text
   normalization, sixth R2b exception or any unresolved mismatch is `PAUSE`. The §18.10
   normalization allowlist remains exactly source root, pytest temporary root and exact tip SHA.
7. Only after every other three-tip condition and the closed 22-node proof establish
   `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`, run the unchanged full-tree Pylint regression gate,
   two fresh-root M8 runs and seven legacy MCP files. Retained failures remain explicit and keep
   `FULL_PYTEST_PASS=false`.
8. Verify and durably copy all raw output, JUnit, canonical records, semantic-projection records,
   set hashes, reruns, R2b proofs, Pylint/M8/MCP outputs, source/component/runtime inventories and
   staging mappings. Kiro reviews the exact final source and evidence. Fetch and require
   `origin/main == N1` before PR creation and again before Ryan's merge decision.

This rule is a closed semantic parser for one exact failure family, not an expansion of
normalization and not a failure waiver. Grok does not choose its node set, line grammar, signature,
plan range, identity values, runtime, evidence paths or verdict. This section authorizes planning
only: no plan application, identity edit, source/test/CI/runtime/configuration correction, suite,
PR, merge, deployment or real OpenClaw action may begin without Kiro PASS and a new Ryan grant.
Gate D/W/D-V/E/F, watch activation, live data and promotion remain blocked.

### 10.16 M11 post-reconstruction Pylint correction obligations

Architecture §18.18 controls. The §18.17 correction and complete fresh three-tip evidence are
preserved at `65bbfd6f47515accfefa110b667afe1613f0dbed`. The differential passed; the unchanged Pylint
gate then failed on exactly three candidate-introduced `R0801` pairs. The triage ledger SHA-256 is
`53eb6004562c89854189961f5b8303de09d43d436ebd7070ed5676a581f48757`, and the exact introduced-
pair file SHA-256 is `ab41f0096d024331fd06ce9d49eed0f0800e73f65668766bd806a2e2e3a70671`.
Current main independently passes the same protected gate with 455 findings and 69 `R0801`
messages; the candidate fails with 458 and 72. M8 and MCP remain unstarted.

Execute only this held sequence after exact-tip Kiro PASS and a new Ryan grant:

1. Require the implementation branch clean, pushed and exactly `65bbfd6f`; require `origin/main`
   still equal `5c6a4a8`; require `R=cd60cf19` unchanged; verify the original PAUSE ledger, triage
   ledger, introduced-pair file, CI-environment revalidation and their manifests; and revalidate
   the unchanged runtime inventory. Any moved ref, missing byte or mutation is `PAUSE`.
2. Grok applies every commit in the complete reviewed linear plan range beginning after
   `95011db461d51dcd3960a375757418401c5e505b`, oldest to newest, onto `65bbfd6f`, with no conflict
   resolution, empty commit, edit, squash, merge, rebase or non-plan change. Grok pushes and stops.
   Codex proves that exactly the four planning-document blobs/modes equal the reviewed overlay and
   every non-plan byte equals `65bbfd6f`.
3. Only after a commit-specific `CONTINUE`, Grok changes exactly four 40-hex values across exactly
   two files: `SEMANTIC_PARENT_SHA` and `M11_REVIEWED_OVERLAY_SHA` in
   `tests/fixtures/openclaw_strict/constants.py`, plus their two frozen assertions in
   `tests/test_openclaw_strict_packet_contract.py`. `CODE_BASELINE_SHA` remains `5c6a4a8`. Grok
   commits, pushes and stops. Codex proves the exact two-path/four-substitution diff.
4. Only after a second commit-specific `CONTINUE`, Grok makes exactly the three mechanical
   transformations in Architecture §18.18: the explicit seven-name Gate-C tuple in
   `tests/test_openclaw_strict_packet_contract.py`, and direct named constructor arguments plus a
   direct ordered dictionary literal in `tests/test_strict_evidence_state.py`. Grok changes no
   other byte, commits, pushes and stops.
5. Codex proves that the correction commit changes exactly those two paths and only those three
   constructions; that `strict_projection.py`, `tests/test_bound_read_scope.py` and
   `tests/test_strict_projection.py` still equal `65bbfd6f`; and that no suppression, helper,
   import, dependency, expected value, branch, node ID or executable behavior changed. A third
   path, production edit or fourth transformation is `PAUSE`.
6. Codex rebinds but does not alter the qualified runtime and freshly runs complete pytest at
   `N1=5c6a4a8`, `R=cd60cf19` and final candidate `F` in one reset slot with identical environment,
   argv, paths, reporter and resource limits. Apply §§18.10 and 18.15–18.17 unchanged, including
   every symmetric rerun, the exact 238-node partition, five-node R2b proof and 22-node semantic-
   signature proof. Prior output is diagnostic only.
7. Only a fresh `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` releases the unchanged full-tree Pylint
   command. Require exactly 455 findings, 69 `R0801` messages, absence of the three §18.18 module
   pairs, no new pair or other new/increased fingerprint, and gate status zero. Raw Pylint status
   remains evidence and must contain no fatal/usage bit; it is not laundered into the gate verdict.
8. Only that exact gate PASS releases two fresh-root M8 runs and seven legacy MCP regression files.
   Preserve all raw/JUnit/canonical records, hashes, reruns, Pylint/M8/MCP output, inventories and
   staging-to-durable mappings. Kiro reviews the exact final source and evidence. Fetch and require
   `origin/main == 5c6a4a8` before PR creation and again before Ryan's merge decision.

The two test-local rewrites remove static token duplication without sharing authority or oracle
logic and without a suppression. They do not reopen §18.9's 44-path boundary or create a new lint
policy. Grok does not choose the pair set, target files, transformations, counts, identity values,
runtime, evidence paths or verdict. This section authorizes planning only: no plan application,
identity edit, product/test/CI/runtime/configuration correction, suite, PR, merge, deployment or
real OpenClaw action may begin without Kiro PASS and a new Ryan grant. Gate D/W/D-V/E/F, watch
activation, live data and promotion remain blocked.

**TL;DR:** [Arc ConvMem Switchboard] The exact-current-main reconstruction is preserved at
`30bc134d`, the reviewed three-tip candidate is preserved at `d276cb4`, and the advanced-main
reconstruction is preserved at `776a4ca3`. The reviewed inner-role correction and fresh three-tip
differential passed at `65bbfd6f`; Pylint triage then proved three candidate-introduced duplicate-
code pairs. Section 10.16 freezes exactly two test-local structural rewrites before the complete
fresh evidence sequence. No implementation, test, PR, merge, real OpenClaw action, live data or
promotion is authorized by this plan edit.
