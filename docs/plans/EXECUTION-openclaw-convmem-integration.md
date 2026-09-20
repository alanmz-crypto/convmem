# Execution Plan — OpenClaw bounded ConvMem reader

**Status:** REVIEW REQUIRED — this is an implementation-complete contract, not
an Execute grant

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

The build is complete when hermetic fixtures demonstrate the architecture's
48 adversarial cases, legacy profiles remain compatible, and the connector can
be tested against a fake/fixture MCP child without installing or enabling an
OpenClaw profile. Gate D runtime smoke, Gate D-V value trials, live data, and
promotion each require later grants.

## 2. Frozen schemas and interfaces

Implementation adds these closed JSON Schemas; unknown keys fail:

- `schemas/convmem-bound-read-scope-v2.schema.json`
- `schemas/convmem-project-binding-registry-v2.schema.json`
- `schemas/convmem-bound-authority-record-v1.schema.json`
- `schemas/convmem-bound-authority-manifest-v1.schema.json`
- `schemas/convmem-bound-projection-manifest-v1.schema.json`
- `schemas/convmem-raw-evidence-v2.schema.json`
- `schemas/convmem-strict-config-v1.schema.json`

The architecture Sections 6.1, 6.2, 6.5, 8.1, and 11 are normative. The JSON
Schemas must encode those fields and bounds without adding defaults.

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
  "schema": "convmem.strict-config.v1",
  "projection_root": "/absolute/reviewed/read-only/path",
  "sqlite_timeout_seconds": 5,
  "telemetry": false
}
```

It rejects credentials, providers, inference endpoints, watch paths, write
paths, capture, and ordinary ConvMem config keys. The strict entry point never
imports the legacy config loader.

Public MCP methods and bounds are exactly:

- `convmem_search(query, top_k=5, project?, site?, domain?, cross_domain?)`;
- `convmem_unresolved(limit=20, project?, site?, domain?, cross_domain?)`;
- `convmem_related(ledger_id, project?, site?, domain?, cross_domain?)`.

No additional method, resource, template, prompt, completion, root, logging,
or sampling surface is registered. Success uses
`convmem.raw-evidence.v2`. Errors use only the seven codes and fixed payload
shape in Architecture Section 11.

## 3. File ownership and allowed changes

Cursor may add or modify only:

```text
bound_read_scope.py
strict_evidence_state.py
bound_projection_builder.py
openclaw_strict_server.py
ledger_ids.py
provenance_binding.py
chroma_store.py
chroma_readonly.py
chroma_write_store.py
file_generation_store.py
file_generation_contract.py
file_generation_pointer.py
serving_index_repository.py
query.py
unresolved.py
related.py
ledger.py
mcp_server.py
mixed_mode_control.py
eval_corpus/shadow_build.py
requirements.txt
schemas/convmem-bound-read-scope-v2.schema.json
schemas/convmem-project-binding-registry-v2.schema.json
schemas/convmem-bound-authority-record-v1.schema.json
schemas/convmem-bound-authority-manifest-v1.schema.json
schemas/convmem-bound-projection-manifest-v1.schema.json
schemas/convmem-raw-evidence-v2.schema.json
schemas/convmem-strict-config-v1.schema.json
integrations/openclaw-convmem-reader/package.json
integrations/openclaw-convmem-reader/openclaw.plugin.json
integrations/openclaw-convmem-reader/index.js
integrations/openclaw-convmem-reader/test/connector.test.mjs
tests/fixtures/openclaw_strict/**
tests/test_bound_read_scope.py
tests/test_strict_evidence_state.py
tests/test_bound_projection_builder.py
tests/test_strict_projection_recovery.py
tests/test_mcp_openclaw_strict.py
tests/test_strict_writer_census.py
tests/test_strict_snapshot_revocation.py
tests/test_openclaw_lifecycle_config.py
tests/test_openclaw_connector_contract.py
```

Adding another production file, dependency, writer, adapter resolver, tool,
schema field, or OpenClaw surface is an automatic stop requiring Codex/Kiro
review. The only permitted dependency change is the observed and reviewed
`idna==3.18` pin in `requirements.txt`; a different version returns to review.
Test helper files may be added only under
`tests/fixtures/openclaw_strict/` or one of the named test modules.

Protected from modification: `observe.py`, `evidence.py`, `ingest.py`,
`distill.py`, `monitor.py`, `propose_decision.py`, all live configs and user
state, corpus/export/ledger data, existing transcript adapters, unrelated plan
or handoff files, and all WordPress/external systems. Their known legacy state
semantics are not silently repaired in this slice; strict mode must not import
or rely on them for current-state reduction.

## 4. Implementation sequence

Each step is one reviewable commit and is pushed immediately. Cursor stops
after a failing gate; it does not continue to make later failures harder to
localize.

### T0 — schemas and fixtures

Add the seven schemas and fixture sets for two bindings, exact/not-applicable
sites, descendant domains, approvals/rejections, observation revisions,
contradictory verifications, high-degree roots, malformed records, and two
complete authority generations. Schema tests must fail on every unknown,
missing, duplicate, wrong-type, noncanonical, or out-of-bound field.

### T1 — authority and state deep module

Implement canonical JSON, payload digest verification, `find2_`/`choice2_`,
`evt_`, and v2 assertion IDs; approval disposition validation; exact retry;
source-event conflict; typed relations; explicit supersession; and the
conservative reducer. Preserve every legacy ID function byte-for-byte. Do not
call `observe.py` or `evidence.py` from strict code.

### T2 — bound scope and projection generations

Implement scope/registry/strict-config validation, selector inheritance,
authority-prefix and state-prefix enforcement, authority generation validation,
deterministic projection construction, recomputation checks, immutable
manifests, compare-and-swap publication, rollback, and read-only opening. Reuse
the existing generation pointer only through a strict wrapper that preserves
its invariants; do not fork its CAS semantics.

Fault injection is mandatory at every Architecture Section 6.5.3 boundary.
The active pointer may name only a complete validated generation. Global Chroma
and ledger caches are never opened by strict code.

### T3 — strict MCP entry point

Implement `openclaw_strict_server.py` as the only strict executable. It validates
the profile and closed environment before importing general server modules,
opens one immutable projection, registers exactly three tools, and returns the
closed v2 envelopes/errors. `mcp_server.py` may share pure registration helpers,
but unknown profiles must fail and strict startup must not load general config
or credentials.

Search has no exact-ID extraction or global fallback. Unresolved and related
use only the projection reducer/graph. All rows receive final authorization.
Resources and templates enumerate empty.

### T4 — reserved-prefix writer enforcement

Extend the one verifier and static writer census to both
`_convmem_auth.*` and `_convmem_state.*`. Cover direct, update,
read-modify-write, copy, restore, mixed-mode, file-generation, and shadow/eval
metadata paths. Production legacy writers may preserve already validated
prefixes only after registry/state revalidation; they may never create them
from caller metadata. `chroma_write_store.py` vends enforcing stores only.

Run all legacy compatibility tests before proceeding. A behavior change in
full/shell, monitor IDs, legacy site handling, or existing recovery is a stop.

### T5 — uninstalled connector

Implement a dependency-minimal JavaScript plugin with exactly three optional
tools. It launches the fixed strict Python entry point without a shell, from an
empty environment allowlist, and forwards bounded JSON-RPC frames unchanged as
tool-result text. It serializes one request, queues eight, rejects the ninth,
uses a ten-second deadline, propagates cancellation, never retries, and kills
the child on protocol/startup/snapshot failure.

The plugin manifest contains no skills, hooks, prompts, services, channels, or
commands. Tests use a fake child and fixture server only. Do not copy, install,
or register the plugin under any OpenClaw state directory.

### T6 — installed-version policy artifact, not activation

Add a fixture config and pure validation test that pins OpenClaw `2026.3.2`,
`heartbeat.every: "0m"`, `compaction.memoryFlush.enabled: false`, memory/ACP/
hooks/skills off, and the existing tool denies. Validate malicious per-agent
overrides, activation-manifest mismatch, old state-directory reuse, and
credential-home contamination. This step may read installed docs/package and
run `openclaw config validate` against a temporary config only if Ryan's Execute
grant explicitly includes that command. It may not start the gateway.

## 5. Required commands

Run from the implementation worktree with disposable temp roots:

```bash
python -m pytest -q \
  tests/test_bound_read_scope.py \
  tests/test_strict_evidence_state.py \
  tests/test_bound_projection_builder.py \
  tests/test_strict_projection_recovery.py \
  tests/test_mcp_openclaw_strict.py \
  tests/test_strict_writer_census.py \
  tests/test_strict_snapshot_revocation.py \
  tests/test_openclaw_lifecycle_config.py \
  tests/test_openclaw_connector_contract.py

node --test integrations/openclaw-convmem-reader/test/connector.test.mjs

python -m pytest -q \
  tests/test_site_filter.py \
  tests/test_milestone_c.py \
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

All commands must use fixture paths and an environment with live ConvMem,
OpenClaw, credential, network, and production paths absent. Any skip in a new
strict test is failure. Existing production-data-dependent skips are reported,
not converted into passes.

## 6. Acceptance matrix

The architecture's numbered tests 1–48 are mandatory. The following mapping is
load-bearing:

- 1–18: scope, omission, normalization, project/domain/site authority,
  resources, candidate isolation, hostile semantic metadata;
- 19–27: unresolved/related, qualified handles, bounded neighborhoods,
  exact-one-binding and non-expanding roots;
- 28–40: OpenClaw surface, hostile evidence, interruption, channel/capture
  negative controls, limits;
- 41–43: approval/state reduction, false-pass prevention, payload-bound replay,
  and fresh assertions;
- 44: authority-first crash/concurrency/rebuild/rollback equivalence;
- 45–47: flush/heartbeat, snapshot/session revocation, and credential isolation;
- 48: queue/deadline/frame/cancellation/child-failure behavior.

Every safety test has a negative control that removes its enforcement and must
then fail. Passing tool enumeration, connection, or retrieval never substitutes
for semantic or recovery assertions.

## 7. Rollback and recovery

Gate B/C rollback is `git revert` of the implementation commits or disposal of
the implementation worktree plus deletion of temporary fixtures. Because live
configuration/data are forbidden, no production rollback should be necessary.

Fixture projection rollback uses the tested compare-and-swap pointer to the
immediately prior retained generation, followed by fresh-process validation.
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
- any OpenClaw gateway start, plugin installation, model call, network access,
  channel, or external side effect;
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
- exact Python, Node, Chroma, MCP, `idna`, and OpenClaw versions;
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

Category 1 — implementation detail: private helper names inside the three new
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
