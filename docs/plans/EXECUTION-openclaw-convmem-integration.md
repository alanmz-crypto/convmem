# Execution Plan — OpenClaw bounded ConvMem reader

**Status:** REVIEW REQUIRED — revised after Astra blocked commit `2424857` on
C1–C6; this is an implementation-complete fixture contract, not an Execute
grant

**Date:** 2026-09-20

**Arc:** none (ad-hoc integration)

**Architecture:** `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md`

**Code baseline:** `7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`.
Only planning documents change after that baseline. Before execution, the
handoff must name the Kiro-reviewed planning commit and prove that non-plan
source is byte-identical to this baseline.

**Roles:** Cursor is the sole implementation writer, using Grok 4.5 High. Kiro
owns exact design/scope sign-off. Ryan alone grants Execute, fixture runtime,
live-data, and promotion authority. Codex independently verifies the submitted
implementation. OpenClaw/Crush is only the eventual runtime.

## 1. Consequence and deliverable

The deliverable is only a fixture-capable, read-only ConvMem evidence server
and an uninstalled OpenClaw connector for three tools: `search`, `unresolved`,
and `related`. It is not a task dispatcher, autonomous executor, transcript
capture system, live-corpus migration, native memory replacement, channel
deployment, or proof of product value.

The build is complete when Gate B/C's explicitly assigned adversarial cases
pass, legacy profiles remain compatible, the strict file reader is proven
read-only, and the connector/supervisor pass fake-child tests without installing
or enabling an OpenClaw profile. It must not claim all 48 cases: actual-runtime
cases remain Gate D and channel case 37 remains Gate E. Gate D runtime smoke,
Gate D-V value trials, live data, and promotion each require later grants.

## 2. Frozen schemas and interfaces

Implementation adds these closed JSON Schemas; unknown keys fail:

- `schemas/convmem-bound-read-scope-v2.schema.json`
- `schemas/convmem-project-binding-registry-v2.schema.json`
- `schemas/convmem-bound-authority-record-v2.schema.json`
- `schemas/convmem-authority-disposition-v1.schema.json`
- `schemas/convmem-strict-provenance-context-v1.schema.json`
- `schemas/convmem-strict-fixture-bundle-v1.schema.json`
- `schemas/convmem-strict-citation-map-v1.schema.json`
- `schemas/convmem-bound-authority-manifest-v2.schema.json`
- `schemas/convmem-bound-projection-row-v1.schema.json`
- `schemas/convmem-strict-graph-v1.schema.json`
- `schemas/convmem-bound-projection-manifest-v2.schema.json`
- `schemas/convmem-strict-generation-layout-v1.schema.json`
- `schemas/convmem-strict-active-pointer-v1.schema.json`
- `schemas/convmem-openclaw-connector-launch-v1.schema.json`
- `schemas/convmem-openclaw-activation-v1.schema.json`
- `schemas/convmem-raw-evidence-v2.schema.json`
- `schemas/convmem-strict-config-v2.schema.json`

Architecture Sections 6.1, 6.2, 6.5, 8.1, and 11 are normative. Schemas encode
every closed field set, conditional, bound, enum, and explicit-null rule
without defaults. Known-answer fixture bytes and SHA-256 values are checked by
two independent parsers: the implementation and a test-only reference parser.

The registry schema is fixed to one binding:

```json
{
  "schema": "convmem.project-binding-registry.v2",
  "revision": "sha256:<64 lowercase hex>",
  "bindings": [{
    "id": "project:fixture:v1",
    "public_ref": "32 lowercase hex",
    "project": "fixture",
    "domain_root": "coding",
    "site_mode": "not_applicable",
    "site": null,
    "non_expanding_roots": [],
    "source_registrations": [{
      "id": "source:fixture-scan:v1",
      "source_class": "fixture_scan",
      "source_identity": "fixture://scan-feed",
      "identity_match": "exact",
      "authorization_domain": "coding",
      "site": "not_applicable",
      "event_id_resolver": "fixture_scan_event_v1"
    }]
  }]
}
```

`identity_match` has only the literal value `exact` in v2. Glob, regex,
substring, basename, cwd, repo-name, and prose matching are forbidden. Trusted
launcher code resolves the registration before parsing content and passes it
out of band. A mixed-audience source is ineligible; it must be split before
registration. Each resolver is a named implementation with registry fixtures
proving retry stability and later-event distinction. Adding a resolver is an
architecture change, not an adapter convenience.

The strict config contains only:

```json
{
  "schema": "convmem.strict-config.v2",
  "projection_root": "/absolute/reviewed/read-only/path",
  "max_projection_rows": 10000,
  "max_projection_bytes": 67108864,
  "telemetry": false
}
```

It rejects credentials, providers, inference endpoints, watch paths, write
paths, capture, and ordinary ConvMem config keys. The strict entry point never
imports the legacy config loader.

Public MCP method names and bounds are exactly:

- `search(query, top_k=5, project?, site?, domain?, cross_domain?)`;
- `unresolved(limit=20, project?, site?, domain?, cross_domain?)`;
- `related(ledger_id, project?, site?, domain?, cross_domain?)`.

The OpenClaw plugin aliases are exactly `convmem_search`,
`convmem_unresolved`, and `convmem_related`, mapped statically in that order to
the three MCP names. Alias strings are never forwarded as request data.

No additional method, resource, template, prompt, completion, root, logging,
or sampling surface is registered. Success uses
`convmem.raw-evidence.v2`. Errors use only the seven codes and fixed payload
shape in Architecture Section 11.

## 3. File ownership and allowed changes

Cursor may add or modify only:

```text
bound_read_scope.py
strict_evidence_state.py
strict_projection_publisher.py
strict_projection.py
openclaw_strict_server.py
openclaw_activation_supervisor.py
mcp_server.py
requirements.txt
schemas/convmem-bound-read-scope-v2.schema.json
schemas/convmem-project-binding-registry-v2.schema.json
schemas/convmem-bound-authority-record-v2.schema.json
schemas/convmem-authority-disposition-v1.schema.json
schemas/convmem-strict-provenance-context-v1.schema.json
schemas/convmem-strict-fixture-bundle-v1.schema.json
schemas/convmem-strict-citation-map-v1.schema.json
schemas/convmem-bound-authority-manifest-v2.schema.json
schemas/convmem-bound-projection-row-v1.schema.json
schemas/convmem-strict-graph-v1.schema.json
schemas/convmem-bound-projection-manifest-v2.schema.json
schemas/convmem-strict-generation-layout-v1.schema.json
schemas/convmem-strict-active-pointer-v1.schema.json
schemas/convmem-openclaw-connector-launch-v1.schema.json
schemas/convmem-openclaw-activation-v1.schema.json
schemas/convmem-raw-evidence-v2.schema.json
schemas/convmem-strict-config-v2.schema.json
integrations/openclaw-convmem-reader/package.json
integrations/openclaw-convmem-reader/openclaw.plugin.json
integrations/openclaw-convmem-reader/index.js
integrations/openclaw-convmem-reader/test/connector.test.mjs
tests/fixtures/openclaw_strict/**
tests/test_bound_read_scope.py
tests/test_strict_evidence_state.py
tests/test_strict_projection_publisher.py
tests/test_strict_projection.py
tests/test_strict_projection_recovery.py
tests/test_mcp_openclaw_strict.py
tests/test_strict_snapshot_revocation.py
tests/test_openclaw_lifecycle_config.py
tests/test_openclaw_connector_contract.py
tests/test_openclaw_activation_supervisor.py
tests/test_openclaw_strict_packet_contract.py
```

Adding another production file, dependency, writer, adapter resolver, tool,
schema field, or OpenClaw surface is an automatic stop requiring Codex/Kiro
review. The only permitted dependency change is the observed and reviewed
`idna==3.18` pin in `requirements.txt`; a different version returns to review.
Test helper files may be added only under
`tests/fixtures/openclaw_strict/` or one of the named test modules.

Protected from modification: `canonical_json.py`, `provenance.py`,
`provenance_binding.py`, `ledger_ids.py`, `agent_run_ledger.py`, `query.py`,
`unresolved.py`, `related.py`, `ledger.py`, every Chroma/file-generation/store
module, `observe.py`, `evidence.py`, `ingest.py`, `distill.py`, `monitor.py`,
`propose_decision.py`, all live configs/user state, corpus/export/ledger data,
existing transcript adapters, unrelated plans/handoffs, and every external
system. The new modules may import the pure canonical/provenance validators but
must not mutate them or import any protected ingest/query/store path. Their
known legacy semantics are not silently repaired in this slice.

### 3.1 Requirement-to-owner consistency lock

This matrix is normative. A requirement may not move to another file, schema,
or gate as an implementation convenience.

| Contract | Production owner | Frozen artifact/interface | Executable evidence | Gate |
|---|---|---|---|---|
| Scope ceiling and selector omission | `bound_read_scope.py` | bound-scope v2, registry v2 | `test_bound_read_scope.py`, cases 5–16 | B |
| Approval, provenance, replay, and state | `strict_evidence_state.py` | authority-record v2, disposition v1, provenance-context v1, citation-map v1 | `test_strict_evidence_state.py`, cases 21–26 and 41–43 | B |
| Fixture publication and rollback | `strict_projection_publisher.py` | fixture-bundle v1, authority/projection manifests v2, layout/pointer v1 | publisher/recovery tests, cases 44 and publication portions of 41–43 | B |
| Read-only graph and lexical retrieval | `strict_projection.py` | projection-row/graph v1 and sealed reader | projection tests, cases 16, 18, 24, 40 | B |
| MCP names and zero extra surfaces | `openclaw_strict_server.py`; reject-only change in `mcp_server.py` | MCP `search`/`unresolved`/`related`, raw-evidence v2 | `test_mcp_openclaw_strict.py`, cases 1–4, 17, 19–20, 27, 47 server portion | B |
| Plugin aliases and bounded stdio | connector `index.js` | connector-launch v1; `convmem_search`/`convmem_unresolved`/`convmem_related` | connector tests, cases 33 and 48 | C |
| Activation, buffered release, revocation | `openclaw_activation_supervisor.py` | activation v1, strict-config v2, and pinned policy fixture | supervisor/lifecycle tests, fake portions 35 and 45–46 | C |
| Installed runtime behavior | no Gate-B/C production owner | exact reviewed Gate-D config and activation | cases 1–4, 28–36, 38–39, actual portions 45–47 | D |
| External sender/channel perimeter | later plan only | later channel policy | case 37 | E |

`tests/test_openclaw_strict_packet_contract.py` statically checks the schema
inventory, MCP-to-plugin name map, exact allowed production-file set, and that
every numbered case has the gate owner above. The handoff additionally compares
`git diff --name-only <code-baseline>..HEAD` with the allowed list. A new file,
unnamed test owner, duplicate gate owner, or unassigned case stops the build;
one case may exercise multiple modules inside its single assigned gate.

## 4. Implementation sequence

Each step is one reviewable commit and is pushed immediately. Cursor stops
after a failing gate; it does not continue to make later failures harder to
localize.

### T0 — schemas and fixtures

Add the seventeen schemas and fixture sets for two separate single-binding
profiles, exact/not-applicable sites, descendant domains,
approvals/rejections, observation revisions,
revocation/withdrawal, forks/joins, contradictory verifications, high-degree
roots, malformed records, absent-pointer bootstrap, and three complete
authority snapshots with derived projection generations. Include frozen
canonical-byte and digest vectors for
records, dispositions, manifests, pointers, provenance, IDs, and fixture event
resolution. Schema tests fail on every unknown, missing, duplicate, wrong-type,
noncanonical, cross-boundary, or out-of-bound field.

### T1 — authority and state deep module

Implement canonical semantic/final payload digests, exact disposition binding,
existing-provenance authority inventory, recursive verification, strict-output
payload binding/mapping, private citation-map
construction, the length-prefixed
`find2_`/`choice2_`/`check2_`/`evt_`/assertion IDs,
`fixture_scan_event_v1`, exact retry/source-event conflict, typed relations,
monotonic multi-target supersession, basis-bound joins,
revocation/withdrawal, and the complete verification truth table. Preserve all
legacy ID/ledger functions byte-for-byte. Do not call legacy state reducers.

### T2 — bound scope and projection generations

Implement scope/registry/strict-config validation and selector inheritance in
the scope module. Implement fixture-bundle/source rejection, authority snapshot
validation, deterministic projection construction, exact immutable manifests,
absent-pointer first publication, and forward/rollback compare-and-swap only in
`strict_projection_publisher.py`. Implement recomputation, fresh-process
qualification, deterministic lexical/graph reads, and sealed read-only opening
only in `strict_projection.py`. The reader must not import the publisher.
Implement the strict pointer specified in Architecture 6.5.4; do not adapt the
path/Chroma-specific generic generation pointer.

Fault injection is mandatory at every Architecture Section 6.5.4 boundary.
The active pointer may name only a complete qualified generation. No legacy
ingest/query/store, Chroma, model, network, or writable-cache path is imported.

### T3 — strict MCP entry point

Implement `openclaw_strict_server.py` as the only strict executable. It validates
the profile and closed environment without importing general server modules,
opens one immutable projection, registers exactly three tools, and returns the
closed v2 envelopes/errors. `mcp_server.py` changes only so unknown profiles
fail and `openclaw-strict` refuses with a fixed instruction to use the dedicated
entry point; no registration helper is shared.

Search has no exact-ID extraction or global fallback. Unresolved and related
use only the projection reducer/graph. All rows receive final authorization.
Resources and templates enumerate empty.

### T4 — uninstalled connector

Implement a dependency-minimal JavaScript plugin with exactly three optional
tools. It validates the connector-launch v1 manifest and launches its exact
fixed strict Python argv without a shell from the closed eight-key environment;
it never copies ambient process state. It forwards bounded JSON-RPC frames
unchanged as tool-result text. It serializes one request, queues eight, rejects the ninth,
uses a ten-second deadline, propagates cancellation, never retries, and kills
the child on protocol/startup/snapshot failure.

The plugin manifest contains no skills, hooks, prompts, services, channels, or
commands. Tests use a fake child and fixture server only. Do not copy, install,
or register the plugin under any OpenClaw state directory.

### T5 — activation supervisor and installed-version policy artifact

Add a fixture config and pure validation test that pins OpenClaw `2026.3.2`,
`heartbeat.every: "0m"`, `compaction.memoryFlush.enabled: false`, memory/ACP/
hooks/skills off, and the existing tool denies. Validate malicious per-agent
overrides, activation-manifest mismatch, old state-directory reuse, and
credential-home contamination. Implement the supervisor, locks, `0600` control
socket, wall/monotonic lease, process-group/parent-death behavior, buffered
delivery, revocation receipt, and state-dir sealing against fake executables.
This step may read installed docs/package and run `openclaw config validate`
against a temporary config only if Ryan's Execute grant explicitly includes
that command. It may not start the actual gateway or agent.

Run all legacy compatibility tests after T5. A behavior change in full/shell,
monitor IDs, agent-run-ledger validation, legacy site handling, or existing
recovery is a stop.

## 5. Required commands

Run from the implementation worktree with disposable temp roots:

```bash
python -m pytest -q \
  tests/test_bound_read_scope.py \
  tests/test_strict_evidence_state.py \
  tests/test_strict_projection_publisher.py \
  tests/test_strict_projection.py \
  tests/test_strict_projection_recovery.py \
  tests/test_mcp_openclaw_strict.py \
  tests/test_strict_snapshot_revocation.py \
  tests/test_openclaw_lifecycle_config.py \
  tests/test_openclaw_connector_contract.py \
  tests/test_openclaw_activation_supervisor.py \
  tests/test_openclaw_strict_packet_contract.py

node --test integrations/openclaw-convmem-reader/test/connector.test.mjs

python -m pytest -q \
  tests/test_site_filter.py \
  tests/test_milestone_c.py \
  tests/test_agent_run_ledger.py \
  tests/test_query_ledger_lookup.py \
  tests/test_query_search_harden.py \
  tests/test_ledger_related.py \
  tests/test_unresolved_payload.py \
  tests/test_file_generation_store.py \
  tests/test_file_generation_validate.py \
  tests/test_governed_recovery_and_writers.py \
  tests/test_governed_writer_gate.py \
  tests/test_shadow_writer_coverage_scan.py

python -m pytest -q
git diff --check
```

All commands use fixture paths and an environment with live ConvMem, OpenClaw,
credential, network, and production paths absent. Mount the qualified fixture
projection read-only for the server suite and prove no mtime/file inventory
change. Any skip in a new strict test is failure. Existing
production-data-dependent skips are reported, not converted into passes.

## 6. Acceptance matrix

The architecture's numbered tests 1–48 are mandatory across their assigned
gates. The build handoff reports only Gate B/C results. The mapping is
load-bearing:

- 1–18: scope, omission, normalization, project/domain/site authority,
  resources, candidate isolation, hostile semantic metadata;
- 19–27: unresolved/related, qualified handles, bounded neighborhoods,
  exact-one-binding and non-expanding roots;
- 28–36 and 38–39: actual installed OpenClaw surface, hostile evidence,
  isolation, interruption, and capture controls at Gate D only;
- 37: external channel perimeter at Gate E only;
- 40: bounds and no-partial-output behavior at Gate B;
- 41–43: exact approval/provenance, monotonic chains/forks/joins and full truth
  table, payload-bound replay, and fresh assertions at Gate B;
- 44: exact first/forward/rollback publication and crash recovery at Gate B;
- 45–46: fake supervisor/lifecycle contracts at Gate C and mandatory installed
  runtime repetition at Gate D;
- 47: strict-server credential isolation at Gate B and installed-process
  repetition at Gate D;
- 48: queue/deadline/frame/cancellation/child-failure behavior at Gate C.

Cases 1–27 and 40–44 plus the server portion of 47 are Gate B acceptance.
Fake-process portions of 33, 35, 45, 46, and 48 are Gate C acceptance. Gate D
repeats 1–4 and owns 28–36, 38–39, and the actual-runtime portions of 45–47.
Gate E owns 37. A mock or fake success is labeled as such and can never close a
later runtime case.

Every safety test has a negative control that removes its enforcement and must
then fail. Passing tool enumeration, connection, or retrieval never substitutes
for semantic or recovery assertions.

## 7. Rollback and recovery

Gate B/C rollback is `git revert` of the implementation commits or disposal of
the implementation worktree plus deletion of temporary fixtures. Because live
configuration/data are forbidden, no production rollback should be necessary.

Fixture projection rollback uses the strict compare-and-swap pointer to an
unexpired retained generation after fresh-process validation.
Never edit an active generation in place. If tests detect a projection row
without authority, an authority row without deterministic reducer output, or
pointer ambiguity, discard the entire fixture root and rebuild from its frozen
authority input.

Any future live materialization requires a separate plan naming backup,
completeness proof, activation/rollback pointers, session invalidation, and the
exact corpus snapshot. This execution plan grants none of it.

## 8. Automatic stops and Ryan decisions

Stop immediately for:

- any Architecture Section 15 condition;
- need to edit a protected or unlisted file;
- need for a new dependency other than the exact reviewed `idna` pin;
- ambiguity in approval, state, source-event identity, supersession, payload,
  publication, recovery, error, or session semantics;
- any attempted access to live corpus/config/session/credential paths;
- any actual installed OpenClaw gateway/agent start, plugin installation, model
  call, network access, channel, or external side effect (fake executables are
  required for Gate C);
- legacy regression, nondeterministic fixture output, skipped strict test, or
  negative control that still passes;
- implementation scope expanding into watch/capture, task dispatch, execution,
  website changes, or product evaluation.

Ryan must decide any cost-bearing model run, installed-profile/config action,
live-data snapshot/materialization, external channel, or promotion. Kiro must
review any schema/interface/authority change. Cursor must not resolve those by
implementation preference.

## 9. Evidence returned by Cursor

The handoff must include:

- branch and `git log origin/main..HEAD --oneline`;
- explicit push status and commit SHAs;
- file list and confirmation that every changed file is allowed;
- packet-consistency test output and the baseline-to-tip changed-file check;
- exact Python, Unicode-data, Node, MCP, `idna`, and OpenClaw versions;
- schema/config/plugin/projection artifact SHA-256 values;
- commands, exit codes, test counts, skips, and negative-control results;
- fault-injection matrix and active-generation checks;
- effective three-tool/zero-resource fixture inventory;
- proof that live paths, credentials, network, gateway, and external systems
  were absent;
- largest residual risk and every category-2 uncertainty;
- no claim of live readiness or product value.

Codex then independently reconstructs the implementation and runs the same
tests plus mutation/negative controls. Kiro checks conformance to the exact
approved architecture. Ryan alone decides whether any later smoke is granted.

## 10. Remaining issue classification

Category 1 — implementation detail: private helper names inside the six new
Python modules, test helper organization inside the named test files, and
internal data classes that serialize exactly to the frozen schemas.

Category 2 — non-blocking for this disposable build: real binding coverage,
mixed-source eligibility in production, retrieval quality, performance on a
real corpus, local-model adequacy, website outcome effect, and net owner effort.
These cannot change the fixture architecture and remain explicit blockers to
live use or promotion.

Category 3 — architecture decision still required: **none after this packet is
approved**.

Category 4 — safety/integrity blocker for fixture implementation: **none after
this packet is approved**. Live data and promotion remain category 4 because
they are explicit non-goals requiring later plans and grants.

**Grok can begin implementation without making an architectural decision, but
only after Kiro signs this exact architecture/build packet and Ryan issues an
explicit Execute grant.** This sentence is a readiness contract, not an
authorization.
