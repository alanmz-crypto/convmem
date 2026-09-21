# Execution Plan — OpenClaw bounded ConvMem reader

**Status:** CANDIDATE FOR FINAL FRESH ASTRA REVIEW — **BUILD BLOCKED — ARCHITECTURE** for the
complete integration. No Execute grant.

**Date:** 2026-09-21

**Arc:** none (ad-hoc integration)

**Architecture:** [revised architecture](ARCHITECTURE-openclaw-convmem-integration.md), especially
§§6.5, 14, 17–18. This file replaces the fixture contract at planning commit
`9b106b908b944f8bd4c3f417b576dc13884f2503`; the two files must be reviewed together.

**Code baseline:** `7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`. This editorial revision changes plans
only. A later build names the exact reviewed planning revision and proves all non-plan source is
identical to this baseline, or obtains review of an explicit new baseline. No silent rebase of the
implementation target.

**Roles:** Cursor using Grok 4.5 High is the proposed implementation lane. Codex owns architectural
editing and independent verification. Fresh Astra audits this candidate; Kiro owns required binary
design/scope review; Ryan alone grants implementation, runtime/config changes, data admission and
promotion. OpenClaw is the eventual bounded runtime and has no governance authority.

## 1. Consequence and bounded deliverable

The core deliverable is a fixture-capable, read-only file evidence reader, three-tool MCP adapter
and uninstalled OpenClaw connector, with fake-manager/controller/supervisor tests. The full
candidate also specifies required production approval/admission corrections and real containment.
**Core fixture acceptance cannot establish complete integration readiness.** Architecture §18
records C-RUNTIME and D-CONTAINMENT/D-DISTRIBUTION; a working credential-free installed model route
has not been established, and the inspected path rejects it.

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

Runtime control is exactly Architecture §6.5.6: external controller start plus authenticated framed
`turn`, `cancel`, `status`, `revoke`. One turn, no turn queue, at most256 accepted turn identities,
complete-result release. Connector **tool** queue is separately one active plus eight pending
with10s deadline/128KiB frame and64KiB server response; do not confuse it with the turn protocol. No
retry/rerun after uncertain delivery.

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
- `openclaw_activation_controller.py`: operator authentication, stable slot, root-owned manager
  control, lock ordering, external retirement/quarantine and receipts.
- `openclaw_activation_supervisor.py`: unit MainPID, child role launches with dropped privileges,
  turn state, watchdog, deadlines and release/revoke linearization. It cannot attest its own empty
  cgroup.
- Connector `index.js`: fixed manifest validation, pre-exec setpriv/filter launch and bounded stdio
  forwarding only.
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

The setpriv binary/filter/runtime image are qualified deployment artifacts, not permission to modify
host packages. Fixture policies and test-only filter inputs live under the listed fixture tree. A
production filter distribution/manager image is blocked pending the exact qualification packet. No
unlisted code, dependency or host config is an implementation convenience.

Protected during B/C: `canonical_json.py`, `provenance.py`, `provenance_binding.py`, all legacy
IDs/ledger/query/unresolved/related/Chroma/store/ingest/observe/monitor/proposal/recovery modules,
`convmem.py`, adapters, live data/config/credentials and unrelated plans. Pure
canonical/provenance/domain functions may be imported without changing their accepted bytes. Direct
reader import closure excludes every writer/config path. The prospective Gate W exceptions are
explicit later scope, not contradictory permission to modify these files now.

`test_openclaw_strict_packet_contract.py` checks schema inventory, exact production-file allowlist,
verb/API map, ownership and test/gate mapping against the reviewed packet. Compare baseline-to-tip
filenames before handoff. Reject unmatched ownership, a stale v1 pointer/activation/raw-v2 envelope,
or a requirement silently moved to a later gate.

## 4. Implementation sequence after a separate grant

Each coherent checkpoint is committed and pushed immediately. Stop on failure; no actual
gateway/agent/model launch or live config write in these steps.

### T0 — closed bytes and fixture contracts

Create schemas and known-answer vectors for every digest/ID/record, cumulative multi-head lineage,
enrollment/publication, grounding and control variant. Two independent parsers must agree on
canonical bytes/digests; reject malformed, reordered, duplicate or unknown fields. Include exact
legacy-envelope byte preservation, not rewritten equivalent provenance. Synthetic issuer inventory
is separate from source-producer inputs.

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

Validate connector-launch v2, runtime/policy digests and exact argv/env/cwd. Fake setpriv/child
tests must show filter-load failure stops before Python; real filter proof is Gate D. No shell,
inherited secret, ambient FD, dynamic path/tool mapping or content execution. Preserve raw evidence
only in untrusted tool-result blocks. Exercise single-active/eight-pending bounds,10s
deadline,cancellation and no late success/retry.

### T5 — fake controller, manager and supervisor

Implement slot lifecycle, peer authentication, lock order, root-controller versus unit-supervisor
ownership, role UID drops, fixed child argv and complete framed turn protocol. Fake manager tests
include supervisor death/hang, detached descendant, outstanding model work and unverifiable
emptiness; only an independent empty-domain receipt permits slot reuse. Test release/revoke
linearization without waiting for a blocked consumer, stable turn IDs and partial-frame discard.
Persist same-boot freshness anchors; require new-boot clock review. Fake environment success is
labeled fake and cannot close D-CONTAINMENT/D-DISTRIBUTION/C-RUNTIME.

All actual unit/runtime/model packaging and installation is outside T0–T5. Do not run `openclaw
config validate` against live state, start a gateway or provision UIDs/units to make tests pass. A
later qualified temporary-config probe needs its exact grant; this file grants none.

## 5. Acceptance ownership and commands

Architecture §13 cases1–56 are normative:

- **B:** 1–27,40–44,49–52, strict-server portion47 and private/public qualification portion55.
- **C fake:** connector/lifecycle portions33,35,45,46,48,53,54 and pre-activation qualification portion55.
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
“all56 passed” from B/C.

After implementation, run the named tests using disposable roots and an environment without live
config/credentials/network:

```bash
python -m pytest -q   tests/test_bound_read_scope.py   tests/test_strict_grounding.py   tests/test_strict_evidence_state.py   tests/test_strict_projection_publisher.py   tests/test_strict_projection.py   tests/test_strict_projection_recovery.py   tests/test_mcp_openclaw_strict.py   tests/test_strict_snapshot_revocation.py   tests/test_openclaw_lifecycle_config.py   tests/test_openclaw_connector_contract.py   tests/test_openclaw_activation_controller.py   tests/test_openclaw_activation_supervisor.py   tests/test_openclaw_strict_packet_contract.py
node --test integrations/openclaw-convmem-reader/test/connector.test.mjs
```

Then run existing compatibility suites: `test_site_filter.py`, `test_milestone_c.py`,
`test_agent_run_ledger.py`, `test_query_ledger_lookup.py`, `test_query_search_harden.py`,
`test_ledger_related.py`, `test_unresolved_payload.py`, `test_file_generation_store.py`,
`test_file_generation_validate.py`, `test_governed_recovery_and_writers.py`,
`test_governed_writer_gate.py`, `test_shadow_writer_coverage_scan.py`, followed by the
repository-required full pytest suite in its isolated test environment and `git diff --check`. No
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
schema/interface ambiguity, authority/provenance weakening, missing qualified deployment input,
skipped safety test or failed negative control. Explicit stops include dummy provider key, shared
host inference, process-group fallback, inferred legacy consent, imported old session,
generation-only CAS, local/display state reduction, late provenance upgrade, implicit
approve/recover indexing and claim of actual containment based on a fake manager.

No task prompt, fixture, model output or this plan authorizes runtime start, service/user
provisioning, network/model cost, live data, deployment, capture, merge or production write. Runtime
incompatibility returns to architecture; Grok must not choose another provider/version/auth
strategy.

## 9. Returned evidence and independent review

Return exact branch/tip/push state; baseline-to-tip allowed-file comparison; schema/fixture/runtime
artifact digests; Python/Unicode/Node/idna/MCP versions; commands/results/skips; independent
references and failing negative controls; every crash/clock/race outcome; read-only
import/file/network evidence; exact three-tool/zero-resource inventory; unresolved blockers. Label
every fake/static/real observation separately. No claim of live readiness or value.

This edit's gathered evidence is Architecture §14: matching Stage1/reconstruction hashes,2 passing
baseline routing tests, static governed caller mapping, installed systemd/cgroup/setpriv capability
observations, and a negative isolated auth-resolver test tied to exact installed source hashes. None
tests the unimplemented integration.

Fresh Astra verifies Architecture §17 on **both edited files**. Kiro reviews the exact resulting
revision; Ryan decides any subsequent scope-specific grant. Reviewer passage does not itself
authorize execution.

## 10. Precise changes and remaining readiness

Changed from `9b106b9`: active-pointer v1→publication v2 with enrollment/authority continuity;
manifests v2→v3; registry v2→v3; record v2→v3; provenance context v1→v2 plus grounding; projection
row/state v1→v2; fixture bundle/layout v1→v2; raw evidence v2→v3; activation/connector v1→v2; new
controller/retirement/launch/clock contracts. Replaced generation-only CAS and cross-head rollback,
request-local reduction and byte-provenance overclaim, parent-death/process-group enforcement and
implied completion. Added explicit Gate W and legacy refusal; updated file/module ownership and
cases49–56 plus corrected18/37/44/46. Unchanged controls are listed in §1.

**A:** internal implementation/test organization consistent with these contracts. **B:** recall,
model quality, bounded performance/storage and product value. **C:** C-RUNTIME, the compatible
credential-free exact installed local inference path/runtime decision. **D:** D-CONTAINMENT and
D-DISTRIBUTION, concrete enforcement and runtime/model closure evidence. Gate W production
acceptance/migration grants remain required and cannot be claimed from B/C.

**BUILD BLOCKED — ARCHITECTURE. Can Grok 4.5 High implement the complete architecture without making
an architectural decision? No: C-RUNTIME remains.** The concrete synthetic core and fake lifecycle
are reviewable; that does not make the complete candidate ready. No execution authorization is
issued.

**TL;DR:** [Arc none] The execution contract now matches the edited authority, state, grounding,
lifecycle and explicit-add architecture. Fresh Astra must verify the pair; the complete build
remains blocked on the exact runtime/authentication decision and containment/distribution evidence.
