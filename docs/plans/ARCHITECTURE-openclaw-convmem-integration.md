# Architecture Plan — OpenClaw orchestration with a bounded ConvMem evidence surface

**Current status (2026-09-27): PROVENANCE PACKET TECHNICAL PASS;
PROVENANCE/LICENSING PAUSE; COMPONENT/OWNERSHIP WORK-ITEM DESIGN REVIEW PENDING;
EXTERNAL PUBLICATION BLOCKED.** The bounded implementation and durable
M11 evidence remain preserved at
`94f29ebabee31112cccb223fd1445cb782aac6eb`, but pull request `#342` cannot merge.
Its required GitHub `pytest (3.12)` context failed with 83 failures, and a focused
Claude ultrareview found two independent safety defects: an invalid MCP profile can
terminate all of `convmem doctor` during import, and a fenced publication can be
misclassified as an exact retry without independently proved input identity. Section
18.22 is the held PR correction; §18.23 freezes its rejected qualified-runtime delivery
packet; and §18.24's replacement delivery-set plan received exact-tip Kiro PASS at
`3402e62a8479011814bfa76ce9e1c3269dc34350`. Sections 18.25–18.28 freeze the
canonical schema-v3 packet and independent disposition; §18.29 defines the lossless
pre-acquisition and clean-replacement contract; and §18.30 defines the closed,
planning-only component/ownership work-item contract. The first archive passed local byte/
mode/extraction validation, but public redistribution remains fail-closed on incomplete
component provenance, licensing evidence and embedded host paths. Everything
below through §18.21 is retained as historical design and evidence provenance. This
edit authorizes planning only.

**Status:** **BUILD PASS and TEST PASS for the frozen T0–T5 fixture contract at accepted
implementation `8010fb060c2edc29e1b09d7a30b1a1da2689d489`. BOUNDED M11 EVIDENCE PASS AT
`cd60cf19dca6706e4175e9f82c9ba55e41bca10b`; CURRENT-MAIN RECONSTRUCTION PRESERVED AT
`30bc134d74d7eeb4cef4d6371a5e96c926f0f2ca`; THREE-TIP CANDIDATE PRESERVED AT
`d276cb4ab0a0613b965e772d49d378e761df337e`; ADVANCED-MAIN CANDIDATE PRESERVED AT
`776a4ca3d4215490fb26b882dca2df9a41e0e03a`; INNER-ROLE RECONCILIATION AND THREE-TIP
DIFFERENTIAL PASS PRESERVED AT `65bbfd6f47515accfefa110b667afe1613f0dbed`; PYLINT PAUSED ON
THREE CANDIDATE-INTRODUCED `R0801` PAIRS; FIRST PYLINT CORRECTION PRESERVED AT
`c71d37a42de0937aff57a2af47770a89902f132a`; SUCCESSOR CORRECTION AND FRESH THREE-TIP
DIFFERENTIAL PASS PRESERVED AT `caec5c6868f600e897b29a39f555365e5f818ac1`; EXACT PYLINT
ACCEPTANCE PASSED AT `9da6dd98d276b250470de4e53ac786f7547d92d5`; FINAL M8 RUN 1
PAUSED BECAUSE THE CURRENT-MAIN SELECTED LEGACY FILE ADDED TWO PASSING SAFETY NODES WHILE THE
FROZEN EXPECTATION REMAINED 116 COLLECTED / 115 PASSED.
LIVE-DATA: BLOCKED. PROMOTION: BLOCKED.** The final authority-packet correction, repository-wide differential,
unchanged Pylint gate, two fresh M8 runs, seven legacy MCP regressions, durable evidence and Kiro
exact-tip conformance review passed at `cd60cf19`. That result is bound to integration baseline
`9193f5ec744f059d07a20612489b210527b5660a`. Before a PR existed, `origin/main` advanced by twelve
commits to `a92a74eb326b3eaa59087b707de10153c7cc0c63`; Git now reports a real conflict in the governed
Switchboard STATUS document, and the full tracked source identity no longer matches the tested
tree. Sections 18.9–18.13 remain the historical evidence contract. Section 18.14 freezes the
completed first current-main reconstruction and its first exact-main differential. Section 18.15
records that differential's governed PAUSE and the reviewed three-tip correction completed through
`d276cb4`. Before any authorized suite started, `origin/main` advanced again to
`5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`; §18.16 freezes the completed second deterministic
reconstruction from that exact base. Its first three complete pytest runs and 166 isolated reruns
paused because pytest rendered the same `CONVMEM_OPENCLAW_INNER_ROLE` assertion through unstable
`os.environ` representations for exactly 22 packet-contract nodes. Section 18.17 froze the closed
semantic projection. The reviewed correction was then applied and freshly proved the three-tip
differential at `65bbfd6f`, but the unchanged Pylint gate paused on three new `R0801` pairs.
Section 18.18 freezes the exact two-test-file structural correction and complete fresh evidence
sequence. That correction was applied at `c71d37a`; its fresh three-tip differential passed, but
the exact reviewed Pylint acceptance paused at 456 findings / 71 `R0801` messages even though the
protected regression gate exited zero. Section 18.19 preserves that governed PAUSE and freezes a
one-test-file/two-transformation correction plus the then-observed 454/69 acceptance target. That
correction and a fresh three-tip differential passed at `caec5c6`; the unchanged Pylint gate then
exited zero with exact `R0801` pair equality but 458 total findings because `R0401` rose from the
unfrozen 25-record observation to 29. Section 18.20 preserves that PAUSE and freezes a paired
`N1`/final-candidate Pylint semantic-identity rule under `PYTHONHASHSEED=0`. That reviewed rule,
fresh three-tip differential and paired Pylint evidence passed at `9da6dd98`. Final M8 run 1 then
stopped on exact legacy-count drift: two current-main safety tests were selected and passed, with
no removed or changed node, while the inherited fixture still required the historical 116/115
count. Section 18.21 preserves the PAUSE and freezes the exact 118/117 successor expectation and
one-path/two-integer correction. It authorizes no implementation, test, PR or merge.
Actual OpenClaw runtime qualification remains blocked by C-RUNTIME, D-CONTAINMENT and
D-DISTRIBUTION; production admission additionally requires Gate W. BUILD does not pass those gates.
This planning edit authorizes no implementation, runtime start, configuration change or live use.

**Date:** 2026-09-27

**Arc:** ConvMem Switchboard

**Authority:** Codex architectural editing lane. The M8 node-evidence history remains in
§§18.4–6. Ryan accepted bounded M0–M8 and separately authorized each held M11 correction through
the final authority-packet rebind. Candidate `cd60cf19` then satisfied the complete bounded
merge-readiness evidence sequence and received Kiro exact-tip PASS. Ryan delegated the merge
decision to Codex; Codex issued `PAUSE` after fetching current main and reproducing the governed
STATUS conflict. Ryan authorized the exact reconstruction and evidence sequence. The reconstruction
was completed, clean and pushed at `30bc134d`; its complete pytest comparison then issued a second
governed `PAUSE` because §18.14 treated all 238 Switchboard nodes absent from current main as newly
required passes even though the preserved reviewed candidate already records their outcomes. Ryan
authorized that plan-only applicability correction, Kiro passed it, and the held plan and identity
commits were completed at `d276cb4`. Its test preflight stopped before creating a slot or running a
suite when `origin/main` advanced to `5c6a4a8`. Ryan authorized this plan-only current-main advance.
The advanced reconstruction was then completed, clean and pushed at `776a4ca3`; complete `N1`,
`R` and final-candidate runs and all 166 isolated reruns completed before the signature-family
PAUSE. Ryan authorized the plan correction, Kiro passed it, and the fresh corrected evidence at
`65bbfd6f` established `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`. The unchanged Pylint gate then
paused on three candidate-introduced duplicate-code pairs. Ryan authorized that correction; its
fresh differential passed at `c71d37a`, but exact Pylint acceptance paused on two remaining excess
pairs. Ryan then authorized only the resulting plan correction. That correction was implemented at
`caec5c6`; its fresh three-tip differential passed, while exact Pylint acceptance paused at
458/69/29 `R0401` despite protected-gate zero and exact pair equality. Ryan authorized four
disposable determinism probes and this plan-only correction; the paired probes reproduced the same
semantic records at `N1` and `caec5c6`. The reviewed correction was then applied at `9da6dd98`;
fresh three-tip and paired Pylint acceptance passed, and M8 run 1 issued the governed legacy-count
PAUSE recorded in §18.21. Ryan authorized only this plan correction. Sections 6.5.8–9 remain the
frozen fixture and hash contracts. Section 18.9 defines the exact
lint-remediation boundary; §18.10 defines the candidate-versus-pre-remediation pytest and identity
rules; §18.11 records the completed earlier M8 packet rebind; §18.12 records the completed
one-literal production correction; §18.13 records the completed final authority-packet rebind and
evidence sequence; §18.14 records the completed current-main reconstruction; §18.15 records the
three-tip differential correction and preflight PAUSE; §18.16 records the completed current-main
advance; §18.17 freezes the exact inner-role semantic-signature rule; §18.18 freezes the exact
post-reconstruction Pylint correction; §18.19 freezes the correction to its observed acceptance
drift; §18.20 records deterministic paired Pylint authority; §18.21 freezes the exact final-M8
legacy-count drift correction; §18.22 freezes the held PR correction; §18.23 records
the rejected first runtime packet; §18.24 defines the Kiro-passed replacement delivery
set; and §18.25 defines the schema-only provenance-lock packet.
Kiro owns the required
exact-tip design review; Ryan owns any later implementation, test, PR, merge or promotion grant.
No complete-integration readiness is claimed.

**Review inputs:** Final Astra report
`/tmp/astra-final-0f1216f7249c0066dafb6fc9ef2aafa9845a7264/STAGE-1-REVIEW.md`, SHA-256
`d3d330b6195263e86f0c648f446ca9b4dbbf648983ee2ec2ad9aeacc7cc2026a`, explicitly states
`REVIEWED_PLAN_SHA: 0f1216f7249c0066dafb6fc9ef2aafa9845a7264`.
Earlier Stage 1 report SHA-256
`fc402286dbb720f3752613e3fe982c4542b168eda9609416b1dd4c51eff5c979`; reconstruction report SHA-256
`73ebe0f606551eb9ece035722d5af05468c9168b6b279abbcd444ec35b03b827`. The original code evidence
baseline remains `7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`; the historical M11 integration baseline is
`9193f5ec744f059d07a20612489b210527b5660a`, the prior current-main baseline is
`a92a74eb326b3eaa59087b707de10153c7cc0c63`, and the exact newly observed current-main baseline is
`5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`. No implementation changes are made here. This
reconciliation supersedes only stale merge sequencing, not the frozen invariants below.

**Frozen invariants:** ConvMem files/CLI retain governance and durable-memory ownership; OpenClaw is
only a bounded, disposable reader/orchestrator. Exactly three read-only tools, one immutable
audience, no resources/ask/global index, no native memory/capture/automatic
indexing/ACP/subagents/channels, no remote inference or ambient credentials. Preserve legacy IDs,
provenance envelope bytes/UUIDs, existing production writer/backup safeguards, exact approval,
permanent revocation/supersession, and explicit Ryan-run approved-file ingestion. No
fixture-to-production promotion or silent legacy migration.

**Contract precedence:** this architecture defines meaning; the paired execution plan defines build
ownership and phase scope. A disagreement stops implementation. Old schemas are rejected, not
adapted with defaults. Fixture construction is neither production approval nor evidence that the
installed adapter can run.

**Frozen implementation scope:** exactly execution T0–T5: synthetic authority/grounding/state and
file publication, a read-only file CLI and three-tool MCP reader, uninstalled connector logic, and
controller/supervisor state machines exercised through §6.5.8's test-only adapters. Actual OS
manager/privilege/runtime adapters, installed OpenClaw, model inference, production packaging,
credential selection, Gate W code, live sources, migration, capture, channels and promotion are
non-goals. Production launch entrypoints fail closed in this slice. A fake tests protocol behavior
only; it proves neither OpenClaw compatibility nor host containment.

The bounded implementation remains architecture-complete. M11 may resume only after exact-tip
Kiro review and a new Ryan grant naming the revised semantic parent, milestone overlay, exact
current-main baseline, preserved reviewed candidate, preserved `9da6dd98` M8-count PAUSE input,
frozen runtime, durable evidence destination, exact reviewed plan range, four-literal identity
rebind, one-path/two-integer legacy-count correction and final three-tip/Pylint/M8/MCP authority.
Known deferred issues do
not authorize Grok to redesign the architecture or reinterpret any test result. These are
BUILD-readiness statements, not an Execute grant.

## 1. Consequence for Ryan

This plan lets OpenClaw retrieve ConvMem evidence without making OpenClaw a
second memory authority and without trusting caller-supplied project, site, or
domain selectors. The initial integration is deliberately small:

- one isolated OpenClaw profile;
- one fixed local connector;
- three raw, read-only ConvMem tools;
- no ConvMem resources;
- no `ask()`;
- no OpenClaw native memory;
- no ACP workers;
- no external channels in the first smoke;
- no transcript capture or background indexing.

Every boundary is server-enforced. Prompt instructions are defense in depth,
not the authorization mechanism. Normal operation remains blocked until the
strict scope contract, tool inventory, OpenClaw perimeter, and interruption
behavior all pass adversarial review on an exact revision.

## 2. Problem and threat model

OpenClaw is allowed to coordinate work. It is not allowed to become the owner
of durable facts, widen ConvMem retrieval, treat corpus text as instructions,
or expose unrelated project/site evidence through another MCP surface.

The design assumes all of the following can be hostile or mistaken:

1. Tool arguments supplied by the model.
2. Corpus documents, titles, summaries, source paths, and ledger text.
3. Ledger IDs supplied by a caller.
4. OpenClaw messages from unknown senders or group contexts.
5. OpenClaw plugins or core tools accidentally left enabled.
6. OpenClaw native memory and automatic memory flush.
7. ACP child sessions, which run on the host rather than inside the OpenClaw
   sandbox in installed OpenClaw `2026.3.2`.
8. Missing, legacy, malformed, or ambiguous ConvMem metadata.
9. Process interruption between request acceptance and response delivery.
10. Documentation for an OpenClaw version other than the installed binary.

The trusted computing base is limited to the reviewed ConvMem strict-scope and
state modules, the operator-owned project-binding registry and dispositions,
the immutable strict file projection, the fixed connector, the operator-owned controller and
main-process supervisor, immutable launch/enrollment files, the sealed runtime/dependency/model
distribution, and the Linux kernel/systemd manager enforcing its boundary. The model, plugin data,
corpus producers and their runtime UID cannot modify governance, capture issuer inventories,
publication, or controller state. A distribution hash establishes bytes, not trust in arbitrary
code.

## 3. Authority and data ownership

1. For this strict lineage, ConvMem's operator-governed source files and append-only
   admission/disposition history are durable authority. This is a target contract for newly enrolled
   data, not a claim that the current legacy observation corpus is reconstructible from its mutable
   JSONL export. Legacy Chroma authority and Recovery Authority safeguards remain unchanged until
   separately reviewed migration. The bound authority snapshot is an immutable, content-addressed
   read model derived from ledger records plus operator-owned disposition
   artifacts; it cannot introduce or approve a fact and is not a second
   authority.
2. Legacy Chroma retains its existing record-specific authority/recovery role; this plan does not
   assert a completed corpus-wide ledger-first migration. The
   strict profile does not open Chroma: it serves a separate immutable,
   content-addressed file projection derived from the authority snapshot.
3. Git, GitHub, and project-native tools remain authoritative for live project
   state.
4. OpenClaw owns only workflow coordination and transient request state.
5. OpenClaw native memory is disabled in the isolated integration profile.
6. ConvMem durable writes remain Ryan-run CLI operations. No MCP or OpenClaw
   tool may expose `record`, `approve`, `add`, `index`, `verify`, or an
   equivalent write path.
7. Retrieved evidence has zero instruction authority. It cannot grant tool
   access, alter scope, authorize writes, or change completion state.

The dependency chain is one architecture: operator ratification fences the stable slot; explicit add
commits a forward-only source operation; cumulative authority conserves identity and original
provenance context; the full-bound reducer fixes canonical state; serving publication may expose
that exact head or nothing; the activation lease pins that publication until external retirement.
Retrieval narrows display only, rollback changes serving only, and OpenClaw cannot act upstream of
either boundary. Thus a failed projection cannot undo revocation, a hidden check cannot create pass,
and approval cannot upgrade provenance.

```mermaid
flowchart LR
    O[Ryan / file CLI] --> I[Ratified intent]
    I -->|explicit add| S[Durable admitted source]
    S --> H[Cumulative authority head]
    H --> V[Complete-bound state and qualification]
    V --> P[Immutable file projection]
    P --> R[Read-only CLI / MCP]
    R --> A[Disposable OpenClaw adapter]
    C[External controller / systemd] -->|retire and fence before writes| I
    C -->|pin lease / authorize complete release| A
    H --> U[Publication: exact head, serving or unavailable]
    U --> R
```

## 4. Installed capability lock

The current executable is `/home/lauer/.local/share/pnpm/openclaw`, version
`2026.3.2`. Its top-level command inventory has no `openclaw mcp` command. Its
bundled documentation establishes three security-relevant facts:

- `memory-core` is the default memory plugin; the supported disable switch is
  `plugins.slots.memory = "none"`;
- a tool allowlist containing only plugin-tool names does not remove core
  tools; a restrictive base profile is also required;
- ACP sessions run on the host and do not support `sandbox: "require"`.

These claims are grounded in the installed package, not current web docs:

- `docs/concepts/memory.md:14-15` names `memory-core` and its disable key;
- `docs/plugins/agent-tools.md:88-92` documents the plugin-only allowlist core
  tool gotcha;
- `docs/tools/acp-agents.md:123-134` documents host execution and the missing
  sandbox guarantee;
- `docs/tools/skills.md:15-45,219-227,241-266` documents managed, workspace,
  plugin, and watched skill sources plus the limited scope of `allowBundled`;
- `docs/automation/hooks.md:42-85,420-475` documents bundled, managed, and
  workspace hooks plus the internal-hook disable surface.

Read-only capability probes on 2026-09-20 independently returned version
`2026.3.2`, a top-level command inventory with no `mcp` command, and a
`config validate` command that validates without starting the gateway. The next
portable review bundle must include the literal stdout of `openclaw --version`,
`openclaw --help`, `openclaw gateway --help`, `openclaw agent --help`, and
`openclaw config validate --help` plus their SHA-256 digests. Exact
integration-config validation remains Gate D evidence because
Gate A does not authorize creating a live profile or config.

Phase 1 therefore uses a narrow OpenClaw plugin that is an MCP client for a
local ConvMem strict-profile subprocess. It contains no retrieval or scope
policy. It translates three fixed plugin tool calls to MCP stdio and returns
the server response unchanged inside an untrusted-evidence envelope.

The eventual installed connector receives only an immutable operator-owned manifest path.
T4 tests the same manifest/argv/environment validation via §6.5.8's injected transport; it does not
execute setpriv, load a real filter or import OpenClaw. This distinction never weakens Gate D.
`convmem.openclaw-connector-launch.v2` contains exactly:

```text
schema, python_executable, python_executable_sha256, strict_server_path,
strict_server_tree_sha256, working_directory, scope_file, registry_file,
strict_config_file, scope_sha256, registry_sha256, strict_config_sha256,
service_home, path_value, lang, lc_all, temp_directory,
setpriv_executable, setpriv_sha256, seccomp_filter_file, seccomp_filter_sha256,
runtime_distribution_sha256, launch_policy_sha256, manager_policy_sha256,
launch_payload_sha256
```

Every path is absolute inside the sealed runtime; inputs are regular read-only files owned by the
operator/root, never symlinks or model writable. The manifest self-hash excludes only itself.
Connector launch is exactly `[SETPRIV, "--no-new-privs", "--seccomp-filter", FILTER, PYTHON, "-B",
"-s", STRICT_SERVER]`, no shell. All executable, dependency, filter and config bytes are pinned by
the runtime image and manifest. Its cwd is fixed, empty and read-only; its dedicated HOME has no
credentials. It closes every inherited descriptor except stdin/stdout/stderr transport. Seccomp
failure is fatal before Python imports.

Construct the child environment from empty, with exactly `CONVMEM_MCP_PROFILE=openclaw-strict`,
`CONVMEM_BOUND_READ_SCOPE_FILE`, `CONVMEM_PROJECT_BINDING_REGISTRY_FILE`,
`CONVMEM_STRICT_CONFIG_FILE`, `HOME`, `PATH`, `LANG`, `LC_ALL`, `TMPDIR` from the manifest. The
launch policy's strict-server map must be byte-equivalent. No `process.env` copy, Node/Python loader
override, proxy/provider variable or token is inherited. Startup selects strict mode before any
general ConvMem loader import and rejects any non-allowlisted key; hostile legacy
scope/config/credential variables therefore cannot affect behavior. The closed
`convmem.strict-config.v2` has only `schema, projection_root, max_projection_rows:10000,
max_projection_bytes:67108864, telemetry:false`; no legacy credential/provider/watch/ingest/write
settings are accepted.

Tool arguments, query text, corpus data, channel messages and public IDs cannot change these fields,
argv, role UID, policy or file paths. The dedicated entry point and read-only reader never import
the publisher, controller, governed engine or general config. This adapter is replaceable: direct
file/CLI qualification and the three retrieval algorithms do not require OpenClaw.

An OpenClaw upgrade, discovery of a native MCP surface, or connector transport
change invalidates this lock and requires a new capability probe plus design
review. The integration must never silently change transport.

### 4.1 Current ConvMem gaps on this review revision

The plan is intentionally not a description of already-enforced behavior:

- `mcp_server.py:74-78` recognizes only `shell`; every other value, including a
  misspelled strict profile, becomes `full`.
- `mcp_server.py:686-763` registers project-selectable brief tools and four
  resource aliases in the full profile.
- `mcp_server.py:766-815` collapses omitted domain/site selectors into `None`
  and has no project ceiling or final row authorization.
- `mcp_server.py:877-895` exposes unresolved data without a project selector or
  bound-scope resolver.
- `read_scope.py:63-90` explicitly implements `cross_domain > explicit >
  session default > unscoped`, the reverse of this plan's ceiling.
- `domains.py:62-72` already provides the correct hierarchical primitive, but
  callers must preserve the direction `domain_matches(requested, bound)` for
  selector narrowing and `domain_matches(row, effective)` for row filtering.
- `site_filter.py:15-46` normalizes simple host strings but also authorizes by
  ordinary metadata and `source_path`; neither is strict-mode authority.
- `site_filter.py:15-26` does not perform the pinned UTS #46/IDNA2008/STD3
  normalization required for one strict site identity; it remains legacy-only
  rather than being redefined in Gate B.
- `distill.py:178` derives `unit["domain"]` from model output over untrusted
  source text, and `ingest.py:974` writes that ordinary semantic label into
  metadata. It must never become `_convmem_auth.domain`.
- `ledger.py:28-104,278-330` has domain, site, and source fields but no reserved
  project binding or protected authorization namespace.
- `brief.py:255-273` uses title, document, site, and source-path substring
  heuristics for project matching.
- `query.py:205-206,298-346,507-519,569-574` extracts ledger IDs from free-text
  search, resolves them outside bound scope, and injects priority hits after
  ordinary candidate filtering.
- `query.py:266-295` retrieves from the shared global vector index, filters in
  Python, and adaptively over-fetches according to out-of-scope density; it
  cannot provide the strict profile's bound candidate universe.
- `ledger.py:176-181,348-382,415-497` accepts caller-supplied IDs without the
  proposed grammar and resolves a global last-write-wins map before scope.
- `ledger_ids.py:20-48` truncates site identity to the first hostname label and
  can mint IDs outside the proposed ASCII grammar; that v1 API remains stable
  for legacy writers while strict ingestion receives a separate v2 API.
- `monitor.py:17,103,295,343,373-410` is a live writer and consumer of the
  legacy `site_short()`/`observation_id()` identity scheme;
  `tests/test_milestone_c.py:14-27` pins that behavior. Gate B may not silently
  change it.
- `provenance_binding.py:210-226,260-295` already distinguishes replayed
  assertion identity from a different assertion and owns projection metadata;
  Gate B preserves its envelope/commitment semantics but does not treat that
  identity pair as payload equality.
- `chroma_store.py:300-325` and `file_generation_store.py:718-760` query shared
  serving indexes and have no immutable bound-scope projection contract.
- `chroma_store.py:219-232,418-435` provides additional summary/unit metadata
  write paths, while `provenance_binding.py:276-295` currently passes unknown
  keys through and `chroma_write_store.py` gates production writers without
  enforcing the reserved authorization prefix.
- Metadata also crosses `chroma_store.py:286,480,619`,
  `file_generation_store.py:165`, `mixed_mode_control.py:64`, and
  `eval_corpus/shadow_build.py:386`. Those paths remain a live-migration
  blocker, but the fixture strict projection bypasses and does not modify them.
- `unresolved.py:21-56` computes status from the global child graph before its
  current site/domain filtering.
- `mcp_server.py:898-939` renders a related chain without scope authorization
  and distinguishes a missing ID, while `ledger.py:415-430,456-497` accepts raw
  Chroma IDs, scans a global index, traverses only one level below the anchor,
  and omits unknown-kind children from the rendered subsets.

Those are blockers to execution, not permission to fix code during plan review.

## 5. Strict ConvMem server profile

Add one exact profile name: `openclaw-strict`.

Profile parsing becomes fail-closed:

- unset or `full` retains the existing full profile;
- `shell` retains the existing shell profile;
- `openclaw-strict` activates this contract;
- every other non-empty value terminates server startup with an invalid-profile
  error rather than falling back to `full`.

The complete strict inventory is:

- `search` — raw scoped retrieval;
- `unresolved` — raw scoped unresolved observations;
- `related` — raw scoped, all-or-nothing bounded target-neighborhood traversal.

Those are the exact MCP `tools/list` names. The OpenClaw plugin exposes the
user-facing aliases `convmem_search`, `convmem_unresolved`, and
`convmem_related`; each alias maps one-to-one to the correspondingly named MCP
method and no name is accepted dynamically.

The strict profile exposes no other tools. In particular, `ask`, `search_fast`,
`brief`, `folder_state`, and `stats` are absent. Both `resources/list` and
`resources/templates/list` return empty collections. `resources/read` cannot
resolve any ConvMem URI.

The strict profile does not inherit the existing brief-first, cwd, or MCP Roots
behavior. Cwd and client Roots are context hints in other profiles; they are
not authorization inputs here.

## 6. Operator-owned bound scope

### 6.1 Scope document

The strict server requires `CONVMEM_BOUND_READ_SCOPE_FILE` at startup. The file
is a regular, non-symlink file outside the dedicated OpenClaw workspace. Its
parent is not writable by untrusted OS users, and the file has no group, other,
or owner write bit while the service runs. The model cannot reach it because
the profile exposes no filesystem or runtime tool. It uses this closed schema:

```json
{
  "schema": "convmem.bound-read-scope.v2",
  "project": "convmem",
  "allowed_project_bindings": ["project:convmem:v1"],
  "domain": "coding",
  "site_mode": "not_applicable",
  "site": null,
  "authority_snapshot": "authority:convmem-coding:v1",
  "serving_projection": "projection:convmem-coding:v1",
  "max_snapshot_age_seconds": 86400
}
```

`project`, `allowed_project_bindings`, `domain`, `authority_snapshot`, and
`serving_projection` are mandatory and non-empty.
`authority_snapshot` and `serving_projection` are stable, operator-chosen
namespace identifiers, not content digests and never caller selectors. The
scope digest binds them into `owner_digest`; the publication record selects a serving generation
within an independently enrolled stable `lineage_id`. The slot and lineage identities do not change
with `owner_digest`. An absent pointer or changed scope cannot create a new lineage or reset
history. Exact `snapshot_id` and
manifest digests are pinned by the activation manifest, avoiding any
self-referential hash between scope, owner, snapshot, and generation. Changing
either namespace requires a new scope file; publishing within a namespace
requires revoking the old activation before the pointer changes.
`max_snapshot_age_seconds` is a mandatory integer from 60 through 86400; it is
an operator policy, not a caller selector. Schema v2 requires
`allowed_project_bindings` to
contain exactly one binding. That binding must resolve in the service-owned
registry to the same canonical project, bound-domain root, and site policy
named by the scope; all reviewed source registrations for the audience live
inside it, so relations across sources remain same-binding. Zero or multiple
bindings prevent startup. `site_mode` is either `exact` or `not_applicable`. `site`
is mandatory and non-empty only in `exact` mode. No dimension has an implicit
unscoped state. The named serving projection is immutable and its
content-digested manifest must exactly match the scope, registry revision,
authority manifest, included-row and graph digests, lexical search-kernel
version, tokenizer Unicode version, and builder version before tool
registration; a mismatch prevents startup.

The server opens the file without following symlinks and validates its resolved
location, owner, regular-file type, mode, schema, keys, and binding references
before registering tools. Missing, empty, malformed, unknown-key, writable,
symlinked, relative, stale-binding, or otherwise ambiguous scope files prevent
startup. The parsed scope is immutable for the process lifetime. The projection
manifest must name the exact authority-manifest digest; the projection manifest must name the
authority manifest's snapshot, lineage, owner and scope digest. Only the projection manifest names a
generation; the authority manifest cannot depend on its derivative. A scope, registry,
active authority snapshot, projection generation,
freshness, or revocation change requires a new reviewed activation and a fresh
OpenClaw state directory; an earlier OpenClaw session is never resumed.

The existing `CONVMEM_READ_SCOPE_DOMAIN` and mutable `read_scope.json` remain
session defaults for legacy profiles. They are never authority inputs for
`openclaw-strict`.

### 6.2 Project membership proof

Corpus metadata is attacker-controlled input, so a row cannot authorize itself
by claiming a project, workspace, or source path. Project membership is instead
an ingest-owned assertion with three parts:

1. A second operator-owned, immutable file named by
   `CONVMEM_PROJECT_BINDING_REGISTRY_FILE` maps an opaque binding ID, such as
   `project:convmem:v1`, to one canonical project, one domain root, one site
   policy, a non-secret random public binding reference, and a set of reviewed
   ingest source registrations. Each source registration contains a fixed
   source identity, source class, authorization domain, and (for exact-site
   bindings) the same normalized site as its binding. Its authorization domain
   must be exact or a descendant of the binding's domain root. The registry
   receives the same regular-file, ownership, symlink, mode, closed-schema,
   startup, and restart checks as the
   scope file. Public binding references must be unique across the registry; a
   duplicate prevents startup. A binding with `site_mode: exact` names exactly
   one normalized site, and every source registration in it is fixed to that
   same site; one binding may never span exact sites. A `not_applicable`
   binding cannot be used by an exact-site scope. Every allowed binding must
   have a domain root exactly equal to the scope's bound domain, not merely an
   ancestor.
   The registry's top-level `revision` is `sha256:` plus the lowercase SHA-256
   over the canonical top-level object with only `revision` removed. Binding,
   source-registration, and root arrays must already be sorted by `id`/stored
   ID; duplicate IDs or noncanonical input order fail rather than being
   silently reordered before hashing.
   Each binding record also has a closed `non_expanding_roots` list for
   high-degree protocol anchors. The list may be empty. Every declared entry
   must be a valid stored ledger ID resolving unambiguously inside that
   deployment's binding; missing, duplicate, or cross-binding declared roots
   prevent startup. The production registry declares the installed fallback ID
   named in Section 8.3 only after binding materialization proves that it
   resolves. Hermetic and synthetic registries declare only roots that exist in
   their own fixture stores; they do not inherit the production root.
2. Gate B has one fixture-only materialization boundary owned by
   `strict_evidence_state.py`. The launcher resolves an exact source
   registration before parsing and supplies it out of band. The strict fixture
   parser rejects the complete batch if source object keys contain a bare
   `_convmem_auth`/`_convmem_state` key, any key beginning either prefix, or any
   field named like an authority/disposition digest. It never imports a legacy
   adapter or `ingest.py`. Only after rejection does trusted code construct
   `project_binding_id`, `source_registration_id`, `authority_site`, and
   `authority_domain` from the immutable registry record. In particular,
   authority domain never comes from a source `domain`, model/distiller output,
   keywords, document text, or filename. Ordinary semantic domain may remain
   inside untrusted document content but is never a selector, graph, or response
   authority value.

   The resulting strict records and file projection are written only by the
   fixture-only `strict_projection_publisher.py`; no generic metadata mapping
   is accepted and no raw
   writer handle is exposed. Legacy Chroma writers, adapters, ingest, restore,
   mixed-mode, eval, and file-generation paths are outside Gate B and remain
   byte-unchanged. They cannot create a strict generation or a module-sealed
   `QualifiedStrictGeneration`. Any future production resolver or Chroma-backed
   strict projection requires a separate writer-census/prefix-enforcement
   architecture and Ryan-granted migration; this fixture build does not claim
   that legacy writers protect strict prefixes.
3. The query authorizer accepts a row only when its service-owned binding ID is
   in `allowed_project_bindings`, the registry maps that ID to the bound
   canonical project, the source registration is allowed by that binding, the
   protected site/domain values exactly equal that registration's immutable
   values, and those values satisfy the effective scope.

The authority record and strict projection row carry the same four protected
values under their closed schemas. All must be present, non-empty, well-typed,
and registry-consistent. A partial, duplicate, conflicting, or additional
authority field denies the complete generation. Rebuild regenerates the
projection from authority; it never infers membership from filenames, ordinary
exports, Chroma, or prose.

The service-owned site value is either a normalized hostname or the literal
`not_applicable`; ordinary blank values are invalid. Exact-site scope requires a
hostname and exact normalized equality. A `not_applicable` bound scope ignores
row-site selection but does not weaken project-binding or domain proof.

Trusted strict materialization rejects any row whose service-owned domain is not exact or a
descendant of its binding's declared domain root. The projection builder
repeats this check from the authority snapshot and fails the whole build on a
mismatch; it never silently drops or repairs the row. Because every allowed
binding's root equals the profile bound, no row inside a valid binding can lie
outside that profile's immutable domain subtree.

Titles, summaries, documents, ordinary `project`, `domain`, `site`,
`workspace_directory`, `source_path`, model names, repo basenames, cwd, and MCP
Roots are context only. They are never direct authorization proof, even if they
exactly match the operator's configuration. Missing, unknown, conflicting,
stale, or caller-supplied authorization claims deny the row.

Existing rows have no service-owned binding and therefore deny in strict mode.
Gate B may use hermetic fixtures whose binding is assigned through the strict
fixture materializer. It may not mutate or backfill the live corpus. A live-corpus
project-binding materialization or rebuild is a separate Ryan-granted data
migration with its own completeness and rollback evidence.

Gate B also builds a physical serving projection for each reviewed bound-scope
manifest. Rebuild scans the closed authority snapshot, applies the full bound project,
binding, site, and service-owned domain authorizer, and writes only accepted
rows into the dedicated canonical file projection. Domain descendants are discovered by
applying `domain_matches(auth_domain, bound_domain)` to the protected ledger
field during rebuild; model-derived ordinary `domain` is ignored. The open
taxonomy is never pre-enumerated. Shared/global indexes, Chroma, ANN,
embedding, and post-query over-fetch are forbidden in strict mode. The process
opens only its named projection read-only and fails startup if the manifest or
file contains a row outside the bound scope.
The projection remains immutable for that process lifetime. New ledger data is
visible only after an operator-run rebuild, manifest review, and server restart;
Phase 1 contains no background refresh or index mutation.

### 6.3 Selector resolution

The API layer must preserve omission with a private sentinel. It must not
collapse omitted values into `""` or `None` before policy resolution. The MCP
adapter must inspect raw argument-key presence before framework default/type
coercion. Explicit `null`, blank, and whitespace-only selectors are invalid;
only an absent key inherits the bound value.

```text
resolve(bound, requested):
    reject explicit blank/whitespace project, site, or domain

    project:
        omitted -> bound.project
        explicit exact canonical equality -> bound.project
        otherwise -> deny

    site:
        bound exact + omitted -> bound.site
        bound exact + normalized exact equality -> bound.site
        bound exact + anything else -> deny
        bound not_applicable + omitted -> not_applicable
        bound not_applicable + any explicit site -> deny

    domain:
        omitted -> bound.domain
        explicit -> strict canonical parse
        allow only if domain_matches(requested, bound.domain)

    cross_domain true -> deny
    cross_domain false or omitted -> continue

    return effective selectors
```

For domain containment the call direction is normative:
`domain_matches(requested_domain, bound_domain)`. Exact and descendant domains
may narrow. The strict parser accepts only canonical lowercase ASCII dotted
segments matching `[a-z0-9_]+(?:\.[a-z0-9_]+)*`; it does not use the legacy
`normalize_domain()` slash/space/general coercions. Parent, sibling, empty,
malformed, and `general`-as-widening requests are denied.

A new `normalize_authority_site()` function is the single strict authority-site
normalizer shared by the registry, scope loader, registry-aware ingest path,
strict ID generator, selector resolver, and row authorizer. It accepts a bare
DNS hostname only, removes one terminal DNS dot, and applies the pinned UTS #46
non-transitional/IDNA2008/STD3 algorithm from Section 8.3 to produce a lowercase
A-label. Schemes, ports, user info, paths, empty labels, and underscores
anywhere are rejected. Strict site comparison applies this function to the
bound and requested values, then exact equality. A strict result row must
itself contain the canonical service-owned `_convmem_auth.site` value.

The existing `site_filter.normalize_site()` remains byte-compatible for
full/shell callers and their URL/path inputs and is never authority in strict
mode. Its `source_path` inference in `unit_matches_site()` and ordinary
adapter-supplied `metadata.site` remain legacy context only.

Any selector-policy failure returns the same public `scope_denied` shape used
by `related()`. Private diagnostics distinguish the reason without copying
request text or corpus content. Search and unresolved do not return a partial
result after a selector denial.

### 6.4 Row authorization

Every candidate row must independently pass all active dimensions after
retrieval and before serialization:

- project membership is proven;
- the service-owned site label is exact when `site_mode=exact`;
- the service-owned row domain exists and is inside the effective requested
  domain subtree;
- every required protected authority/state field is present, well-typed, and
  payload-digest consistent.

Unknown or missing metadata denies the row. All three strict tools open only
the physical bound-scope projection described in Section 6.2 as their sole
candidate and graph universe. Rows outside the profile's project, allowed
bindings, exact site, or bound domain subtree never enter search's lexical
candidate set or unresolved/related's graph, result count, ordering, response shape,
first-call cost, or process cache. The single deterministic lexical path and
graph traversal operate only inside that projection and still apply the final
row authorizer before serialization. There is no fallback.
Strict mode never calls the current shared index, `_fetch_scoped_units()`
adaptive over-fetch, `build_ledger_index()` over a global store, or
`units_metadata()` on a wider collection. Failure to open or validate the exact
projection prevents startup.

An explicit descendant-domain selector is a caller-chosen narrowing inside the
already authorized bound projection. Its post-retrieval filtering may reduce
or reorder results relative to the broader bound view, but cannot reveal data
the caller lacks authority to retrieve because omitting the selector exposes
that entire bound view. The security invariant and constant public envelope
apply to rows outside the immutable bound scope, not to caller-authorized rows
excluded by a voluntary narrowing. Search may return fewer than `top_k`; it
does not refill from a shared or wider index.

Exact-ledger extraction and priority injection are disabled entirely in strict
search. Before lexical tokenization or scoring, the server splits query text only on whitespace and
applies only the grammar-and-length stage of the centralized strict
public-handle parser with `re.fullmatch()` to each token. It never tests whether
the token's public binding reference is known or allowed. Every syntactically
valid qualified handle therefore receives the same fixed, non-reflecting
`identifier_query_not_supported` response before tokenization or scoring. Binding
authorization is a separate stage used only by `related()`. Substrings such as
`server_name`, `codec_config`, and `observer_pattern` are ordinary search text
and must not be rejected. Punctuation-wrapped or malformed strings are not
looked up or priority-injected; they remain ordinary text against the already
authorized projection. `related()` is the only strict handle-lookup surface.

### 6.5 Authority, assertion, state, and publication contract

Scope authorization answers who may see a row; it does not make the row true,
approved, current, or verified. Strict mode therefore admits rows only from an
immutable operator-reviewed authority snapshot. It never treats an existing
Chroma row, model summary, ordinary export row, source-registration label,
signer string, or `status=accepted` field as authority by itself.

The snapshot is an immutable directory containing canonical authority records,
governance dispositions, a private citation map, and a closed manifest. Pending
proposal files are never inputs. The live ledger/export and Chroma are not
silently converted; Gate B uses only hermetic fixtures. The Gate-B fixture file
is a synthetic stand-in for ledger-plus-disposition
input and has no durable-memory authority outside its test. A later live
materializer must read an immutable ledger/disposition snapshot and preserve
its provenance under a separately reviewed migration; it may not promote this
fixture parser into a second production write path.

Each record has schema `convmem.bound-authority-record.v3`. Every optional
field is present as JSON `null` or an empty array, so omission cannot change
meaning. Its exact fields are:

```text
schema, project_binding_id, source_registration_id, authority_site,
authority_domain, record_kind, logical_id, assertion_id, source_event_id,
producer, logical_key, semantic_sha256, payload_sha256, title, document,
observed_at, recorded_at, confidence_bps, relates_to_assertion_id,
target_assertion_id,
verification_result, supersedes_assertion_ids, decision_disposition_ref,
supersession_disposition_ref, provenance_envelope, provenance_commitment,
origin_assurance, provenance_qualification, check_eligibility
```

`record_kind` is `observation`, `decision`, or `verification`.
`supersedes_assertion_ids` is a sorted, duplicate-free array of zero through 32
assertion IDs. A verification has a required `target_assertion_id`; other kinds
set it to `null`. A verification also has `verification_result` equal to exactly
`pass`, `fail`, or `inconclusive`; other kinds set it to `null`. A decision has
a required `decision_disposition_ref`; other kinds set it to `null`.
`supersession_disposition_ref` is required exactly when the supersession array
is non-empty. Contextual `relates_to_assertion_id` never changes state. All IDs
are lowercase ASCII. Times are RFC 3339 UTC with `Z` and whole-second precision;
`observed_at <= recorded_at <= manifest.built_at` and `observed_at <=
manifest.as_of`. `title` is 1–512 Unicode code points, `document` is 1–65536,
and `confidence_bps` is an integer from 0 through 10000.
`producer` matches `[a-z0-9][a-z0-9._-]{0,15}`. `logical_key` is 1–256 NFC
code points and is stable for one source-native subject/check across scans; it
is not generated from title/document text. Observation, decision, and
verification records require `find2_`, `choice2_`, and `check2_` logical-ID
prefixes respectively; a kind/prefix mismatch fails the snapshot.

Canonical JSON uses the repository's `canonical_json_bytes()` profile plus
strict duplicate-key rejection: UTF-8, sorted object keys, `,`/`:` separators,
no insignificant whitespace, no surrogates, and explicit `null`. Every new
strict string is NFC and every new strict field forbids floats. The nested
`provenance_envelope` instead remains byte-equivalent to its existing v1
acceptance domain, including any finite float or non-NFC string that domain
validly contains; it is never normalized or rewritten. The semantic digest is SHA-256 over a closed
object containing every record field except `semantic_sha256`, `payload_sha256`,
`decision_disposition_ref`, `supersession_disposition_ref`,
and the full `provenance_envelope`; it includes
`provenance_commitment`. Thus approval binds the exact identity, text,
confidence, times, target, relation, and supersession targets without a digest
cycle. `payload_sha256` is SHA-256 over the final record with only
`payload_sha256` removed, so it additionally binds both disposition references
and the complete provenance envelope. A parser must re-encode and compare the
bytes; a matching hash over noncanonical input is not accepted.

#### 6.5.1 Closed dispositions and provenance continuity

Governance artifacts use schema `convmem.authority-disposition.v1`. The exact
fields are:

```text
schema, action, project_binding_id, subject_assertion_id,
subject_semantic_sha256, target_assertion_ids, basis_snapshot_id,
expected_head_assertion_ids, replaces_disposition_ref, review_actor,
review_role, review_outcome, reviewed_at, ratifier_actor, ratifier_role,
ratified_at, rationale_sha256
```

The content address is `disp_` plus SHA-256 of the canonical disposition bytes;
the object contains no self-reference. That recomputed address is its logical
ID inside `dispositions.jsonl`, and a record reference must equal it.
`review_role` is exactly
`kiro-design-reviewer`; `ratifier_role` is exactly
`ryan-authority-owner`; `review_outcome` is `pass` or `fail`. These fields are
not cryptographic identity: the trust root is the reviewed, non-writable,
operator-owned disposition directory populated only through the authorized
file/CLI approval path. A signer string copied from corpus content never
qualifies.

`action` is one of `decision_approved`, `decision_rejected`,
`decision_revoked`, `evidence_withdrawn`, or `supersession_authorized`.
The action matrix is exact:

- approval/rejection names a decision, requires `pass`/`fail` respectively,
  and sets `target_assertion_ids` and `expected_head_assertion_ids` empty and
  `basis_snapshot_id` and `replaces_disposition_ref` to `null`;
- revocation names that same decision and semantic digest, requires `pass`,
  sets both arrays empty and `basis_snapshot_id` to the immediate admitted
  parent snapshot, and names the exact prior approval in `replaces_disposition_ref`;
- withdrawal names an observation or verification and its semantic digest,
  requires `pass`, sets both arrays empty,
  `basis_snapshot_id` to the immediate admitted parent snapshot, and
  `replaces_disposition_ref` to `null`;
- supersession names the replacement assertion as subject, requires `pass`,
  binds its exact semantic digest, sorted target set, immutable immediate
  admitted parent `basis_snapshot_id`, and exact active head set in that basis, and sets
  `replaces_disposition_ref` to `null`.

New dispositions are validated against the immediate admitted parent; retained dispositions are
replayed against their original admission parent, never against the current head. Any competing,
cross-binding, wrong-kind, wrong-logical-ID, stale new basis, or partially matched disposition fails
the candidate. A new terminal action targets a parent record, never an addition in the same batch. A
join and any other head-changing operation on the same logical identity in one batch are rejected. A
revoked or withdrawn record remains historical; no artifact is rewritten or
deleted.

The disposition set is itself closed and reduced deterministically. Each
decision record names exactly one matching approval or rejection disposition;
the same disposition cannot approve two records. At most one later revocation
may replace that approval. At most one withdrawal may target an observation or
verification. Each non-empty supersession array names exactly one matching
supersession disposition, and every disposition in the manifest must be
consumed by exactly one allowed state transition. Duplicate actions,
unreferenced dispositions, two dispositions for the same transition, a
revocation of a rejection, or incompatible approval/rejection/revocation
chains fail the snapshot. A disposition never changes bytes in its subject;
it only contributes to the reducer for the snapshot that contains it.

Every authority record carries a byte-for-byte valid existing
`convmem/provenance-envelope-v1` plus its recomputed
`provenance_commitment`. The authority snapshot also contains closed
`convmem.strict-provenance-context.v2` with exact top-level fields `schema`,
`schema_semantics`, `policies`, `recipes`, `verified_channels`,
`registered_assertions`, `grounding_sha256`, and `context_payload_sha256`. `schema_semantics`
entries contain exactly
`schema_version`, `binding_version`, `semantic_bytes_b64`, and
`semantic_sha256`; policy entries contain exactly `policy_version`,
`semantic_bytes_b64`, `semantic_sha256`, and `rules`. Each rule contains
exactly `transformer_class`, `transformer_identity`, `transformer_version`,
`recipe_id`, `cap`, `preservation_contract`, and `artifact_sha256`, with the
last two explicitly `null` when absent. Recipe entries contain exactly `recipe_id`,
`recipe_bytes_b64`, and `recipe_sha256`; verified-channel entries contain
exactly `origin_class`, `channel_class`, `channel_locator`, and
`channel_evidence_sha256`. Registered-assertion entries contain exactly
`assertion_id`, `provenance_commitment`, and `envelope`; the envelope must
recompute to that commitment and its internal assertion ID must match the
entry. Arrays are duplicate-free and already sorted respectively by
`(schema_version,binding_version)`, `policy_version`, `recipe_id`,
`(origin_class,channel_class,channel_locator,channel_evidence_sha256)`, and
`assertion_id`; each policy's rules are sorted by
`(transformer_class,transformer_identity,transformer_version,recipe_id)`.
Base64 is canonical padded RFC 4648,
and every embedded digest is recomputed. The context payload hash excludes only
itself. The existing recursive verifier validates commitments, declared policies, channels and
ancestry. It does **not** establish source bytes, consumed view bytes or actual execution. Strict
qualification composes that result with the grounding contract below; no direct `trusted ->
verified` mapping is permitted.

The source record supplies only a provenance assertion UUID. Trusted code must
resolve it in `registered_assertions`, recursively verify that exact immutable
inventory entry, and copy its envelope/commitment into the authority record;
an envelope or assurance claim inside source content is rejected. The
publisher computes `strict_source_payload_sha256` over the canonical source
record with only `provenance_assertion_id` removed and requires the resolved
envelope's `selection_parameters.output_sha256` to equal it. Missing or unequal
binding fails the complete snapshot; matching provenance identity alone is
never payload proof. The
envelope's existing UUID identity remains unchanged and is not replaced by the
strict record's v2 `assertion_id`. The containing record is the explicit
mapping between those identities. Across the entire enrolled lineage, one existing
provenance assertion/commitment pair may map to only one strict assertion
except for a byte-identical retry; reusing it for different semantic bytes or
multiple apparently independent assertions fails the snapshot.

The builder does not mint replacement provenance. Its private
`citation-map.json` uses closed schema `convmem.strict-citation-map.v1` and
contains exactly `schema`, `citations`, and `citation_map_payload_sha256`.
`citations` is sorted by `citation_ref`; each entry contains exactly
`citation_ref`, `assertion_id`, `provenance_assertion_id`,
`provenance_commitment`, `root_bindings`, and `input_bindings`, with the last
two copied byte-equivalently from the validated envelope. The map payload hash
excludes only itself. It is hashed by the authority manifest, excluded from
the serving projection, and excluded from public tool data and runtime model mounts; the trusted
cold qualifier and operator audit path may read it. Public
`citation_ref` is `cite1_` plus SHA-256 of the canonical object with exact
fields `schema: convmem.strict-citation-ref.v1`, `project_binding_id`,
`assertion_id`, and `provenance_commitment`; it is never accepted as authority
or a tool input.

##### Byte grounding and capture contract

Keep `provenance.py` and its accepted envelope bytes/UUIDs unchanged. The strict qualifier composes
its narrower result with new immutable evidence. A legacy verifier result is never by itself mapped
to stronger byte/capture assurance.

Add `convmem.strict-grounding.v1` with exact fields `schema, blobs, roots, edges, outputs, receipts,
grounding_payload_sha256`. Blob entries are `sha256, length, bytes_b64`; arrays are canonical and
duplicate-free. Embedded bytes are never executable. Blob hashing covers decoded bytes; padded
base64 is canonical. The total decoded blob budget is 32 MiB and is also included in the existing
128-MiB authority budget; encoded overhead must fit that total. Exceeding a budget rejects the
candidate, never causes incomplete verification to pass.

Root bindings contain exactly `provenance_assertion_id, provenance_commitment,
source_registration_id, source_event_id, source_identity, record_locator, raw_blob_sha256,
view_blob_sha256, selector, receipt_ref`. Edge bindings contain exactly
`child_provenance_assertion_id, child_provenance_commitment, parent_provenance_assertion_id,
parent_provenance_commitment, parent_output_blob_sha256, view_blob_sha256, selector, receipt_ref`.
Output bindings contain exactly `provenance_assertion_id, provenance_commitment,
output_blob_sha256`.

The only selectors are closed objects `{kind:"identity"}` and `{kind:"byte_range", start, end}` with
integer half-open byte offsets `0 <= start <= end <= input_length`. Views intended as text must be
valid UTF-8. There are no runtime-loaded recipes, URLs, arbitrary file paths, JSON programs or
model-provided selectors. The input is the root's exact captured raw blob, or the exact output blob
bound to the named parent commitment. Recompute the view and compare it with the envelope's
root/input-view hash and binding identities. Check every claimed edge, not merely those reached by a
convenient displayed path.

Every included grounding blob and ancestor must be authorized for the same immutable audience;
private witness storage is not permission to import another project's bytes. An unavailable or
foreign ancestor stays absent and prevents stronger assurance. The qualifier never fetches it from a
global corpus to complete the chain.

A capture receipt contains exactly `schema, capture_id, capture_class, capture_issuer_id,
source_registration_id, source_event_id, provenance_assertion_id, provenance_commitment,
input_bindings_sha256, transformer_artifact_sha256, recipe_sha256, submitted_views_sha256,
returned_output_sha256, captured_at, receipt_payload_sha256`. There is exactly one invocation
receipt per provenance assertion. `input_bindings_sha256` hashes the complete ordered array of that
assertion's root/parent-input bindings, each tagged `{kind, binding}` with `receipt_ref` removed;
root entries precede edge entries and each group uses the grounding sort order below. Every binding
of that assertion references this same receipt. `submitted_views_sha256` hashes the corresponding
ordered array of view blob hashes (repeated uses retained). The recorder attests that whole ordered
input set and one returned output in one invocation. Receipts from separate calls cannot be
assembled into a stronger multi-input execution claim. These hashes avoid a receipt/commitment
cycle. `receipt_ref` is the receipt's content address. Each receipt is imported only from a
protected issuer inventory pinned in the registration; a row's receipt-shaped object is not
authenticated. The issuer inventory binds exact receipt bytes, not just an actor name.

For deterministic fixture evidence, the trusted fixture harness constructs raw bytes, performs the
declared selection/transformation, retains the exact input/output and issues
`capture_class=synthetic_fixture`. It does not attest a real website, production capture or
historical model run. Production can use `controlled_capture` only after an independent recorder is
qualified to own the invocation boundary and immutable receipt publication. Source producer/model
processes cannot write that inventory. No production recorder is assumed to exist in the supplied
code.

Qualification returns a closed tuple:

`commitments: valid|incomplete; byte_grounding: complete|missing; capture:
synthetic_fixture|controlled_capture|unattested; transformer_cap: trusted|agent|untrusted`.

Supplied mismatched bytes, wrong identities/locators/events, receipt reuse for a different binding,
changed retained receipts or commitments, or impossible selectors fail the complete candidate.
Missing witnesses/receipts or incomplete ancestry produce a weaker tuple, not a stronger claim. A
mismatched claimed hash cannot be treated as merely missing. Runtime disappearance/corruption of
previously admitted files fails cold qualification rather than retrospectively downgrading history.

`origin_assurance=verified` is allowed only with valid commitments, complete byte grounding, an
accepted capture class, complete ancestry and a trusted transformer cap. Public `provenance_basis`
explicitly says `synthetic_fixture` or `controlled_capture`; it never says historical execution was
independently proven. With complete recorded lineage but an agent cap, assurance is at most
`claimed`; missing grounding/capture is `untrusted`. Add the qualification tuple to public results
so the single legacy-style label cannot conceal its basis.

Actual consumption is stated narrowly: a controlled receipt attests bytes supplied and outputs
returned at the recorder's boundary. It does not prove that a model attended to all supplied
content. For an unrecorded past call, consumption is **not established**, even if deterministic
replay succeeds. Old envelopes are not rewritten; a later correction needs a new assertion/receipt
and forward admission. Approval never upgrades capture evidence, and repeated derivation never
creates independent support.

Qualification is frozen at the assertion's original admission context, found from the lineage's
added-ID arrays. Cold replay uses that original context. Appending a formerly missing parent or
witness cannot silently upgrade an old assertion. An explicit new assertion is required. Synthetic
and controlled-capture ancestry may not be mixed into a production-qualified chain. Sidecar receipt
addresses are not inserted into old envelopes; this avoids both reminting and a receipt/commitment
hash cycle.

The registry uses closed `convmem.project-binding-registry.v3` with top-level `schema, revision,
bindings`; its existing revision hash excludes only revision. The single registry-v3 binding adds
exactly `lineage_id`, `capture_issuers` and `verification_producers` to §6.2's binding fields.
`lineage_id` is 32 lowercase hex. Capture issuers are sorted by `issuer_id`; each closed entry is
`{issuer_id, capture_class, enrollment_sha256, receipt_root, source_registration_ids}`. Issuer IDs
match `[a-z0-9][a-z0-9._-]{0,63}`; class is `synthetic_fixture` or `controlled_capture`;
receipt_root is a protected absolute operator path, never mounted into OpenClaw. Source IDs are
sorted unique registered IDs. Enrollment binds the issuer and permission boundary; actual receipt
bytes are committed at admission. Runtime/model/source UIDs cannot enroll an issuer or write its
inventory. Gate B accepts fixture issuers only. A receipt is authentic only if its exact
content-addressed bytes are already in that issuer's protected inventory; importing a receipt-shaped
object cannot create authenticity.

`verification_producers` is a sorted unique array of closed entries `{source_registration_id,
producer, transformer_identity, transformer_version, transformer_artifact_sha256, recipe_sha256,
capture_class}`. It binds an exact non-LLM check implementation and capture class. Missing match
yields `inconclusive_only`; it never removes the check. Match plus full trusted qualification yields
`qualified`; non-verifications use `not_applicable`.

Grounding arrays sort by blob hash; root `(provenance_assertion_id, source_registration_id,
source_event_id, record_locator)`; edge `(child_provenance_assertion_id,
parent_provenance_assertion_id, view_blob_sha256)`; output provenance assertion ID; receipt capture
ID, respectively. Duplicate keys fail. Receipt schema is `convmem.capture-receipt.v1`; `capture_id`
is 32 lowercase hex and `receipt_ref` is `capture_` plus its payload hash. Every envelope root/input
must match one grounding binding for complete grounding, and every supplied binding must match an
envelope edge. No orphan, duplicate or unused witness claims are accepted. A blob may be referenced
by multiple exact bindings; it is stored once. Receipt IDs cannot be reused across different bytes
or assertion invocations; multiple bindings of the one attested invocation must share its receipt.
All referenced receipt output hashes must agree with that assertion's unique output binding and the
envelope's output commitment. An absent required binding is missing evidence; an included but
dangling/mismatched binding is invalid input.

Qualification fields are deterministic, included in record semantic/payload hashes, and frozen at
original admission. `provenance_basis` is derived from capture class (`synthetic_fixture`,
`controlled_capture`, or `unattested`) and is public; complete ancestry must have a homogeneous
accepted class. `claimed` requires valid complete lineage/grounding/capture with an agent cap; all
other non-verified combinations are `untrusted`. No receipt proves model attention, factual truth or
measurement freshness.

#### 6.5.2 Logical identity, immutable assertions, and replay

Strict v2 separates a continuing subject from an immutable assertion. Digest
inputs use one binary encoding, not delimiter-concatenated text:

```text
LP(value) = uint32_be(len(UTF8(NFC(value)))) || UTF8(NFC(value))
H(tag, fields...) = SHA256(ASCII(tag) || 0x00 || LP(field1) || ...)
```

Each input must satisfy its field grammar before hashing; a byte length above
`2^32-1` is invalid. The field orders below are normative.

- `logical_id` is `find2_`, `choice2_`, or `check2_` plus
  `H("convmem-logical-id-v2", project_binding_id, source_identity,
  authority_site, producer, logical_key, subject_kind,
  target_assertion_id_or_empty)`. `subject_kind` is `finding`, `decision`, or
  `verification`; the prefix follows that kind. The logical key is
  source-registration-defined and does not identify a scan. A verification
  includes its exact target assertion ID as the final digest field; other kinds
  use the empty string. Thus independent check keys remain independent while a
  revision of one check can supersede only its own prior head.
- `source_event_id` is `evt_<64-lowercase-hex>` derived by the registered
  adapter from a source-native occurrence locator, never from mutable payload
  text. The registry pins the resolver and test vectors. It is stable for an
  exact delivery retry and distinct for a genuinely later scan/event. A source
  without such an identity is ineligible for strict materialization.
- `assertion_id` is `<kind>2_<64-lowercase-hex>`, where kind is `obs`, `dec`, or
  `ver`, followed by `H("convmem-assertion-id-v2", project_binding_id,
  source_registration_id, source_event_id, record_kind, logical_id)`. It
  deliberately excludes payload bytes so changed bytes under one occurrence
  collide and deny rather than masquerading as a new event.

The only Gate-B resolver is `fixture_scan_event_v1`. Its registered source
object has the closed fields `schema`, `event_key`, `captured_at`, and
`records`; `schema` is `convmem.fixture-scan.v1`, `event_key` is 1–256 NFC code
points and matches `[A-Za-z0-9][A-Za-z0-9._:-]*`, and `records` may contain
many typed source records. Every record in one scan shares
`evt_ + H("convmem-fixture-scan-event-v1", source_registration_id,
source_identity, event_key)`; assertion uniqueness still includes each
record's logical ID. The scan's validated `captured_at` becomes each record's
`recorded_at`; source records cannot supply another recorded time. The collision key is the exact five-tuple
`(project_binding_id, source_registration_id, source_event_id, record_kind,
logical_id)`. No UUID, timestamp fallback, record index, or payload-derived
event key is permitted. Adding a production resolver is a later architecture
decision.

An exact retry is a no-op only when the collision key, assertion ID, semantic
digest, payload digest, complete canonical record bytes, dispositions, and
relation fields are byte-equivalent. Reprocessing identical input must recover
the registered event key; reminting an occurrence is not a retry. A later scan
has a distinct event and assertion even when visible text is unchanged. A
reminted event for one registered event key, changed content under one
collision key, same digest with different canonical bytes, or duplicate
assertion with different provenance is `source_event_conflict` and fails the
generation. Nothing overwrites an assertion. Live adoption remains a
separately granted migration.

#### 6.5.3 Deterministic current-state reduction

`relates_to_assertion_id` is context only. `target_assertion_id` is used only by
verification. State replacement uses only the disposition-backed
`supersedes_assertion_ids`. A valid supersession is permanent within and after
the snapshot in which it first appears: a target is historical when *any*
valid admitted successor supersedes it, regardless of whether that successor
is later superseded, withdrawn, or revoked. This monotonic rule prevents
`A <- B <- C` from resurrecting A; only C is a head. Cycles, self-edges,
missing targets, cross-binding/logical-ID/kind edges, and rejected-decision
successors fail the generation.

A successor may join multiple heads only when its supersession disposition's
`basis_snapshot_id` names the immediate admitted parent snapshot and its
`expected_head_assertion_ids` and target array exactly equal the complete
active head set for that logical ID in that basis. Publication compare-and-swap
then prevents two joins from both claiming the same basis. A stale or partial
join fails; concurrent independently admitted heads remain `conflict`. The
builder never chooses by timestamp. Rejected decisions are historical.
`decision_revoked` and `evidence_withdrawn` remove the subject from the active
head set but do not undo its already-authorized supersession edges; restoring
old meaning requires a new explicit assertion and disposition, never
resurrection.

The public state vocabulary is closed:

- observation `authority_state`: `current`, `conflict`, `superseded`, or
  `withdrawn`;
- decision `authority_state`: `approved`, `rejected`, `revoked`,
  `superseded`, or `conflict`;
- verification `authority_state`: `current`, `conflict`, `superseded`, or
  `withdrawn`;
- every row `verification_state`: `not_applicable`, `unverified`, `pass`,
  `fail`, `inconclusive`, or `conflict`.

Reducer precedence is exact. First apply a valid withdrawal, rejection, or
revocation to its subject. Next mark every target of any valid admitted
supersession `superseded` unless the earlier terminal state is
withdrawn/rejected/revoked. From the remaining eligible heads, one observation
or verification head is `current` and two or more heads of the same logical ID
are all `conflict`; one approved decision head is `approved` and two or more
approved heads are all `conflict`. Zero eligible heads is allowed and means the
logical subject has no current direction; no predecessor is reactivated.

Verification targets may name an observation or an approved decision in the same binding, never
another verification. Historical-target checks remain context and cannot verify a successor.
Contextual `relates_to` edges never change state.

For observation/decision `a`, collect every live `current` or `conflict` verification head targeting
the **exact assertion ID** of `a` in the complete admitted bound history. A check against a
predecessor does not verify a successor. `relates_to` never substitutes for `target_assertion_id`.

First, if any contributing verification logical identity has competing live heads, the target's
canonical verification state is `conflict`, even when those heads report the same result. Otherwise
assign each head an effective result:

- A registered check producer with fully qualified evidence and an accepted deterministic/capture
  contract contributes its recorded `pass`, `fail`, or `inconclusive`.
- Any live check lacking that eligibility contributes `inconclusive`; it is never silently omitted.
  A claimed or LLM-derived pass cannot close an observation. A weak fail likewise cannot disappear
  and expose a sole pass.

Apply the original conservative truth table to effective results: empty→unverified; pass only→pass;
fail only or fail+inconclusive→fail; inconclusive only or pass+inconclusive→inconclusive; any
pass+fail→conflict. Verification rows themselves retain their immutable reported result and use
`verification_state=not_applicable`.

Check eligibility is fixed by the registry's closed `verification_producers` inventory: exact
`source_registration_id, producer, transformer_identity, transformer_version,
transformer_artifact_sha256, recipe_sha256, capture_class`, sorted by that tuple. Entries are
supplied by the operator, never by corpus text. `capture_class` is `synthetic_fixture` for fixtures;
production requires a separately established protected recorder identity. No matching inventory
entry means ineligible, not an error in ordinary document retrieval. No LLM transformer is eligible
to close a check in this version.

This adds a necessary F2/F3 contract: uncertain evidence stays visible without receiving closure
power. It does not prove that a qualified measurement is correct or that every possible test was
run. Public responses name the basis `recorded_qualified_checks`; “pass” means the complete live
qualified recorded set has passed under the above rules, not “the website is correct.” Approval,
authority currency, provenance, measurement freshness and deployment completion remain separate.

Unresolved's predicate is precisely:

`record_kind == observation AND (authority_state == conflict OR (authority_state == current AND
verification_state != pass))`.

Order by conflict before current, then descending `observed_at`, then ascending `assertion_id`,
before applying the requested limit and byte bound. There is no positive “all resolved” conclusion
inferred from a limited empty query over a selected subtree.

The state map is computed over the **complete immutable authorized bound authority**, before
selectors, ranking, top-k, truncation or related depth. Every tool copies it. The immutable source
record never accepts current-state fields. Operator-side cold qualification independently recomputes
the state map;
any mismatch fails qualification. Appending cross-audience witnesses is forbidden, so complete-bound
reduction does not mean global reduction.

#### 6.5.4 Cumulative authority and derivative publication

The publisher owns admission qualification and derivative publication; it is not an approver. Gate
B's input is synthetic. Production intent and source admission use §6.5.7's governed engine, not
this fixture parser. Chroma, exports, cached rows and model output never supply missing authority.

**Stable enrollment.** One operator-created lineage owns exactly one audience and at most one
runtime slot. `lineage_id`, `slot_id`, `operation_id` and activation IDs are independent random
128-bit lowercase hex identities. `owner_digest` remains SHA-256 of canonical
`{schema:"convmem.strict-owner.v1", scope_sha256, registry_sha256, project_binding_id}`. It is a
configuration identity, not a lock name or enrollment identity. Changing scope, registry, producer
policy, binding or enrollment is unsupported in this version: retire/fence and require a separately
reviewed continuity-preserving migration. Starting a new owner root cannot evade old revocations.

Enrollment uses closed `convmem.strict-enrollment.v1` with exactly `schema, lineage_id, slot_id,
mode, owner_digest, operator_uid, controller_uid, supervisor_uid, runtime_uid, scope_sha256,
registry_sha256, semantic_contract_sha256, initial_source_cutoff_sha256, enrollment_payload_sha256`.
Mode is `fixture` or `production`; Gate B's enrollment command accepts only `fixture`. Controller
and supervisor identities are trusted; runtime UID differs from all three and cannot signal, ptrace,
read private process state of, or write their sockets/files. Exact UID/mount/IPC enforcement is part
of the manager-policy qualification. Production enrollment cannot be inferred from an empty
directory. No flag promotes fixtures.

A new authority head H[n+1] preserves every admitted record, disposition, source-event mapping,
provenance envelope, policy/recipe/channel inventory key, receipt and evidence blob byte-for-byte
from H[n]. Only a closed append delta is legal. Qualify every parent link from genesis; validate old
dispositions and qualification at their original admission context; validate new transitions against
H[n]. Added-ID lists equal exact recomputed set differences. Independent additions may create
conflict. Joining heads must target the complete parent head set, and no same-batch action may also
change that logical identity. A later withdrawn/revoked successor does not erase its supersession
edges. Restoring meaning requires a newly admitted assertion and governance.

The fixture bundle is closed `convmem.strict-fixture-bundle.v2`, with exactly `schema, lineage_id,
operation_id, expected_parent_manifest_sha256, batches, dispositions, provenance_context, grounding,
built_at, as_of, expires_at, fixture_payload_sha256`. Batches are cumulative, sorted by
`(source_registration_id, source.event_key)`, and contain exactly `source_registration_id, source`.
`source` is §6.5.2's fixture-scan object. Its source records contain exactly `record_kind, producer,
logical_key, title, document, observed_at, confidence_bps, relates_to_assertion_id,
target_assertion_id, verification_result, provenance_assertion_id`. Explicit kind-inapplicable nulls
are required. Other authority/ID/state/digest fields are rejected before trusted construction.
Supersession targets come from exact validated dispositions, not text. Each scan's records are
sorted by `(record_kind, producer, logical_key, target_assertion_id-or-empty)`; duplicate tuples
reject.

A bundle must add assertions, dispositions, or reviewed source-cutoff evidence. Merely rebuilding
cannot advance `as_of`. Retained events cannot change captured time. `built_at` is at least every
captured/recorded time; `observed_at <= as_of <= built_at`; `expires_at = as_of +
scope.max_snapshot_age_seconds`. A newer source cutoff must be backed by a new captured scan/event
or ratified transition, even if no new substantive text. No changing a timestamp to refresh old
measurements. Public `observed_at` remains independent of cutoff freshness.

Operation idempotence compares the exact bundle/artifact payload digest. Same operation ID/same
bytes returns the historic outcome **and the current head** without changing publication. Different
bytes under the same ID reject. Same source occurrence/different record bytes rejects across all
heads. Retrying an old successful operation cannot republish its head.

**Closed file layout and schemas.** JSON uses §6.5's canonical profile, duplicate-key rejection and
explicit nulls. Every listed object is closed, has its literal schema value, and self-hashes by
excluding only its named payload-hash field. Hashes are lowercase SHA-256. Canonical JSONL has one
object plus LF per line; records sort by assertion ID, dispositions by computed `disp_` address. All
arrays described as sets must arrive sorted and unique; parsers do not repair them.

```text
<root>/layout.json
<root>/control/enrollment.json
<root>/control/semantic-contract.json
<root>/control/slot.json
<root>/control/clock/<receipt-hash>.json
<root>/authority/<snapshot_id>/input.json
<root>/authority/<snapshot_id>/source-cutoff.json
<root>/authority/<snapshot_id>/records.jsonl
<root>/authority/<snapshot_id>/dispositions.jsonl
<root>/authority/<snapshot_id>/citation-map.json
<root>/authority/<snapshot_id>/provenance-context.json
<root>/authority/<snapshot_id>/grounding.json
<root>/authority/<snapshot_id>/manifest.json
<root>/projection/<generation_id>/rows.jsonl
<root>/projection/<generation_id>/graph.json
<root>/projection/<generation_id>/manifest.json
<root>/active/<lineage_id>.json
<root>/active/history/<publication-payload-sha256>.json
<root>/locks/<lineage_id>.lock
<root>/locks/<slot_id>.transition.lock
```

`convmem.strict-generation-layout.v2` has exactly `schema, authority_dir, projection_dir,
active_dir, locks_dir, control_dir, layout_payload_sha256`; directory values are exactly
`authority`, `projection`, `active`, `locks`, `control`. Slot state lives outside runtime-writable
mounts. Its closed `convmem.strict-slot.v1` record is `schema, slot_id, lineage_id, activation_id,
activation_manifest_sha256, unit_invocation_id, state, retirement_ref, slot_payload_sha256`;
nullable activation/invocation fields are null only when never launched/retired; state is `empty`,
`starting`, `active`, `retiring`, or `quarantined`. It records containment bookkeeping, never fact
approval. Missing/corrupt slot state on an enrolled slot requires reconciliation, not a new launch.

`convmem.strict-source-cutoff.v1` has exactly `schema, lineage_id, mode, operations,
cutoff_payload_sha256`. Operations are admission-ordered closed `{operation_id, input_sha256,
source_prefix_sha256}` objects. A fixture's source prefix hashes its cumulative canonical `batches`;
production hashes the canonical object `{schema:"convmem.admitted-source-prefix.v1", lineage_id,
previous_source_prefix_sha256, operation_id, artifact_sha256, ratification_ref}`. The previous
prefix is null only at first admission. Every referenced artifact/ratification is retained in
protected source storage; the prefix chain is independently replayed. It excludes the later ADMITTED
receipt and authority manifest, avoiding a cycle. The source step is written only by the explicit
add operation under its durable ADMISSION_PREPARED consent, not by a rebuild. Each operation ID
occurs once. `input.json` is the exact fixture bundle or approved admission artifact and its hash is
committed in the manifest. Cutoff history is cumulative; no wall-clock-only cutoff. The empty
genesis cutoff is explicit and hashed.

`convmem.bound-authority-manifest.v3` exact fields:

```text
schema, lineage_id, authority_seq, owner_digest, snapshot_id,
parent_snapshot_id, parent_manifest_sha256, scope_sha256, registry_sha256,
input_sha256, source_cutoff_sha256, operation_id,
authority_records_sha256, record_count, dispositions_sha256, disposition_count,
citation_map_sha256, provenance_context_sha256, grounding_sha256,
added_assertion_ids, added_disposition_ids, added_provenance_ids,
added_grounding_refs, semantic_contract_sha256, reducer_version,
canonicalization_version, builder_version, builder_tree_sha256,
built_at, as_of, expires_at, manifest_payload_sha256
```

Sequence starts at 1 with null parent fields; otherwise it is parent+1 with exact parent ID/hash.
`snapshot_id = snap2_` plus SHA-256 of this canonical manifest excluding only `snapshot_id` and
`manifest_payload_sha256`; then compute the payload hash. Added provenance IDs are envelope UUIDs.
Added grounding refs are sorted hashes of the canonical newly admitted blob/root/edge/output/receipt
entries (schema fixes the entry type in a tagged `{kind, entry}` hash). Grounding and context
inventories are retained even when an assertion is withdrawn.

`convmem.bound-projection-manifest.v3` exact fields:

```text
schema, lineage_id, authority_seq, owner_digest, generation_id,
previous_generation_id, snapshot_id, authority_manifest_sha256,
scope_sha256, registry_sha256, semantic_contract_sha256,
rows_sha256, row_count, graph_sha256, graph_node_count,
search_kernel, search_kernel_version, tokenizer_unicode_version,
builder_version, builder_tree_sha256, built_at, as_of, expires_at,
manifest_payload_sha256
```

`generation_id = gen2_` plus SHA-256 of the canonical projection manifest excluding only
`generation_id` and `manifest_payload_sha256`. `previous_generation_id` is audit context only; null
on the first generation, otherwise the generation serving when the build began (or null if none). It
never selects authority. Projection times `as_of/expires_at` copy authority exactly; generation
`built_at` may be later. A manifest contains no self-referential downstream identity.

`semantic_contract_sha256` hashes the canonical closed `convmem.strict-semantic-contract.v1` object
`schema, reducer_version, grounding_version, canonicalization_version, identity_version,
search_kernel, search_kernel_version, tokenizer_unicode_version, schema_digests,
contract_payload_sha256` excluding its payload hash. `schema_digests` is sorted closed `{path,
sha256}` for the execution plan's complete strict schema inventory. The semantic artifact excludes
deployment-specific enrollment/launch values. Its schema list is exactly the Gate B/C inventory in
the paired execution plan. Hash the schema bytes, not their future deployment instances.
Governance/capture files remain outside the sealed code image, so image→policy→activation digests
are acyclic. `builder_tree_sha256` uses §6.5.9's exact component inventory and §6.5.6's tree recipe,
including unchanged imported dependencies. Neither tests nor mutable outputs enter it. The edit
allowlist is not the hash inventory. Deployment permits only exact reviewed builder/runtime digests. Changing contract
semantics requires review, never an old-generation rollback.

`convmem.bound-projection-row.v2` exact fields:

```text
schema, project_binding_id, public_binding_ref, source_registration_id,
authority_site, authority_domain, record_kind, logical_id, assertion_id,
public_ledger_id, citation_ref, title, document, observed_at, recorded_at,
confidence_bps, relates_to_assertion_id, target_assertion_id,
verification_result, supersedes_assertion_ids, decision_disposition_ref,
supersession_disposition_ref, origin_assurance, provenance_qualification,
check_eligibility, authority_state, verification_state,
state_disposition_refs, payload_sha256, state_sha256
```

`payload_sha256` is the linked authority record's hash. `state_sha256` hashes closed
`convmem.strict-state.v2` with exact fields `schema, lineage_id, authority_seq,
authority_manifest_sha256, semantic_contract_sha256, assertion_id, authority_state,
verification_state, subject_head_assertion_ids, verification_inputs, state_disposition_refs`.
Subject heads and disposition refs are sorted unique; each verification input is closed
`{assertion_id, logical_id, authority_state, reported_result, effective_result, check_eligibility}`
sorted by assertion ID. All live check heads are present, including ineligible/conflicting ones.
Verification rows have an empty verification-input array and `not_applicable` verification state.
State hashes do not enter authority identity, avoiding a cycle.

`convmem.strict-graph.v1` remains exactly `schema, nodes, edges, graph_payload_sha256`; sorted
unique nodes are assertion IDs and sorted unique edges are `{kind, from_assertion_id,
to_assertion_id}` with kind `relates_to`, `targets` or `supersedes`. Every edge resolves inside the
bound history. No private paths or source locators enter rows/graph.

Limits: 1–10,000 records, 0–30,000 dispositions, one citation per record, 350,000 graph edges, 64
MiB provenance context, 32 MiB decoded grounding blobs, 128 MiB all authority files combined, 10,000
rows/64 MiB projection, 512 MiB total retained lineage root. Locators are at most 4,096 code points.
Encoding overhead counts toward file/root limits. No truncation, spill, history pruning or witness
garbage collection; quota failure means unavailable/rejected, never resurrection. Reserve fence/slot
bookkeeping space before starting a write; if even the fence cannot become durable, retire and deny
further activation pending recovery, and do not claim the operation committed.

**Publication record.** Replace the old active pointer with closed `convmem.strict-publication.v2`:

```text
schema, lineage_id, owner_digest, epoch, authority_seq, authority_snapshot_id,
authority_manifest_sha256, authority_source_cutoff_sha256,
serving_generation_id, projection_manifest_sha256, semantic_contract_sha256,
pending_operation_id, mode, previous_publication_sha256, freshness_anchor,
published_at, publication_payload_sha256
```

Mode is `serving`, `unavailable` or `fenced`. Serving/projection IDs are both non-null only for
serving. Pending operation is non-null only when fenced. Authority identity remains present when
unavailable/fenced; only enrolled empty genesis has sequence 0 and null authority ID/hash/anchor,
with a hashed empty cutoff and never serving mode. Every mutation increments epoch, including
fences, rebuilds and rollback; predecessor hash is null only at epoch1. CAS compares the **entire
publication payload hash**, not a generation/sequence. A→B→A serving cannot defeat CAS.
`freshness_anchor` is §6.5.6's persisted closed object.

The direct read-only CLI is `python -B -s strict_projection.py read --method
search|unresolved|related --scope ABS --registry ABS --strict-config ABS --request-file ABS
--expected-publication SHA256`. The canonical request object uses exactly the same method argument
keys and bounds as MCP. It acquires the already-created lineage lock shared through a read-only
descriptor, qualifies the exact serving publication and persisted anchor, and buffers one v3
response. It enforces a 10-second BOOTTIME request bound and rechecks time/publication before
committing stdout; no creates, credentials, model, MCP
or OpenClaw are needed. It does not create an activation or write a lease/clock anchor.
Missing/expired anchor means no read. Preexisting lease/lock handles for the runtime are opened by
the trusted controller, not created by the read-only child.

The exact fixture CLI is:

```text
python -B -s strict_projection_publisher.py enroll-fixture --enrollment ABS --semantic-contract ABS --strict-config ABS
python -B -s strict_projection_publisher.py build-fixture --bundle ABS --scope ABS --registry ABS --strict-config ABS --expected-publication SHA256
python -B -s strict_projection_publisher.py rebuild-fixture --scope ABS --registry ABS --strict-config ABS --expected-publication SHA256
python -B -s strict_projection_publisher.py rollback-fixture --scope ABS --registry ABS --strict-config ABS --expected-publication SHA256 --target-generation gen2_SHA256
python -B -s strict_projection_publisher.py recover-fixture --scope ABS --registry ABS --strict-config ABS --expected-publication SHA256
```

Enrollment requires an empty fixture root, creates epoch1 unavailable/seq0 plus the stable
slot/locks, and fails on any prior enrollment or retained history. `build-fixture` uses the bundle's
operation ID, not a CLI-generated fallback; rebuild/rollback/recovery never admit new source.
Missing/corrupt publication after enrollment is an operator recovery error; it does not accept
`none` as a CAS bypass. Recovery of a completely lost current pointer requires separate operator
reconciliation, not this routine CLI. All paths pass operator-file checks; no stdin records, ambient
config or live-source input.

Under slot-transition then lineage-exclusive locks (production additionally uses §6.5.6's
writer/governance locks):

1. Validate new input and its parent without changing admitted history; retire the old activation
   and independently prove its domain empty before writing.
2. Persist a new fenced publication naming this operation. Fsync the file and directory before
   committing source/intent. The fence is durable even if later work fails.
3. Write immutable input/cutoff/authority files, fsync each and directory, compute manifest;
   independently qualify cumulative authority in a fresh interpreter.
4. Publish the new authority head with mode unavailable and null serving. For production the durable
   source append precedes this step; a crash leaves the fence for exact reconciliation. Authority
   admission cannot depend on successful projection.
5. Build rows/graph in a new generation from that exact head; fsync files/manifests/directories;
   independently recompute all bytes/state in a fresh process.
6. Recheck exact current publication under the exclusive lock; publish serving for the **same**
   head, retaining its freshness anchor. Atomic rename plus directory fsync is the publication
   durability boundary.

Retained content-addressed publication files are audit history, not alternative selectors.
Write/fsync the immutable history entry before replacing the current record. Qualification verifies
history continuity and the enrolled source cutoff, plus any pending protected governance intent. A
stale serving record cannot override an unsettled ratification. Orphans written before a commit do
not create approval/admission. After durable admission, projection failure leaves the new head
unavailable. A retry reports or finishes that exact operation without changing historical meaning.

`rollback-fixture` selects only a retained generation of the **exact current authority manifest**,
unchanged enrollment/scope/registry/semantic contract, currently allowed builder/launch policy,
successful cold qualification and unexpired anchor. It retires first and creates a new epoch. It
never selects old authority, old semantic policy or a new lease. If no eligible generation exists,
rebuild current authority or remain unavailable.

Crash before rename leaves the previous publication, which may already be fenced/unavailable. Rename
without successful directory fsync is ambiguous: retire/fence the slot, cold-reconcile exact
history/source and fsync before serving. Torn authority, changed retained bytes, unknown source
cutoff, missing current pointer, stale CAS or conflicting operation IDs deny serving; no automatic
rollback or lineage reset. Recovery may clear an abandoned unratified fence only after proving no
durable intent/admission; it then requalifies the same head with unchanged expiry. A fixture root
may be discarded only as a test teardown, never as a recovery that preserves its enrollment
identity.

After private cold qualification, the public-opening boundary below returns a module-sealed
`QualifiedStrictGeneration`. Reader inputs are that
capability, never raw caller paths. It opens `O_RDONLY|O_NOFOLLOW`, checks ownership/type/mode, pins
validated inodes and rechecks manifest/state. It performs no
create/journal/cache/temp/model/network/Chroma operation. Host operator is trusted against arbitrary
offline rollback. Whole-authority backup restoration cannot prove that a later lost history never
existed; activation requires independent latest-history evidence under the existing owner-controlled
recovery process. A local self-hash is not an anti-rollback oracle.

##### Private qualification versus runtime read opening

Full independent cold qualification runs in the operator/publisher process and again in a fresh
operator-controlled process immediately before each activation. It reads private authority,
provenance, grounding and citation files, recomputes state/rows/graph, and returns the exact qualified
manifest/row/graph digests to the controller. The slot transition and lineage locks keep that result
bound to the publication being activated. Qualification failure prevents start.

The runtime mount includes only the public authority manifest, public projection files, exact serving
publication, unchanged scope/registry/config bytes and precreated read-lock files. Private issuer-store paths
have no mount in that namespace; config bytes are never rewritten after hashing. It never includes
private citation maps, source inputs, receipts'
issuer directories, raw grounding blobs or governance files. Registry strings naming private audit
paths are not resolvable there and are never exposed in tool data. Public evidence/config files are operator/root-owned, runtime-readable and non-writable (files0444, directories0555), while private source/witness/governance trees stay outside the mount. The strict child need not have the operator's UID or private read permissions. The controller and direct operator file CLI perform private
qualification outside the runtime namespace; the model/plugin cannot invoke that path.

`strict_projection.py` owns two explicit boundaries: `qualify_authority_generation` performs the full
private reconstruction; `open_published_generation` validates the protected public publication,
manifest linkage, row/graph hashes, closed row schemas, authorization and freshness before constructing
the module-sealed read capability. The latter does not pretend to reverify absent source bytes. It
accepts only the configured operator-owned immutable files matching the controller's pinned digests,
never an MCP-supplied path, mapping or claimed qualification flag. The existing protected projection
manifest is the publisher's exact commitment to qualified rows; no new approval service or independent
source of truth is introduced. Reader startup validates projection bytes; publisher/pre-activation
qualification validates their derivation. Direct file CLI use performs both boundaries under the same
shared lineage lock. Tests must distinguish these two proof obligations and deny swapped public files,
wrong owner/mode, omitted private qualification or changed publication before launch.

#### 6.5.5 Deterministic strict search and read-only projection

Gate B deliberately implements lexical search only. It promises no semantic or
paraphrase recall. Strict mode never imports `query.py`, an embedder, reranker,
Ollama, Chroma, a model cache, or general ConvMem config. The projection is
bounded to 10,000 rows and 64 MiB of canonical row bytes; exceeding either
limit fails the build rather than degrading or spilling.

The tokenizer applies NFC, Unicode `casefold()`, then emits maximal runs whose
code points have Unicode general category beginning `L` or `N`, plus internal
underscore. Other code points are separators; empty tokens disappear. The
manifest pins `unicodedata.unidata_version`. Query input is at most 2,048 code
points and 64 distinct tokens after stable first-occurrence deduplication.
`normalized_query`, `normalized_title`, and `normalized_document` are the
single-ASCII-space joins of the tokenizer's full token sequence before token
deduplication. Per-token terms use the stable first-occurrence distinct query
tokens. Occurrences are counted at every code-point start position, including
overlaps, before the cap is applied. A row is a candidate only if one query
token appears in its normalized title or document. Its integer score is:

```text
16 if normalized query is a title substring
 4 if normalized query is a document substring
+ 8 * min(3, title occurrences) for each distinct query token
+ 1 * min(3, document occurrences) for each distinct query token
```

The leading sort key is zero exactly for `authority_state` in `current`,
`approved`, or `conflict`, and one for every historical state. Rows sort by
that key, then descending integer score, descending `observed_at`, and ascending
`assertion_id`. No clock, confidence, vector distance, model output, random
order, or fallback changes ranking. `top_k` truncation occurs after final
authorization. An empty-token query is `invalid_request`. All tools share one
`StrictProjectionReader` over the qualified generation; it exposes only
`search_rows`, `unresolved_rows`, and `related_neighborhood`, never a raw file
handle or wider store.

#### 6.5.6 Lifecycle, containment and freshness

The state, protocol, authority and clock rules below apply to both fixture simulation and later
runtime qualification. The concrete systemd/root/mount/filter/model execution described here is
Gate D, not a T0–T5 implementation obligation. Section 6.5.8 fixes exactly how fixtures exercise
these rules without real privileged operations. Fake evidence never qualifies the actual platform.

An operator-side controller owns the stable slot and interacts with the OS manager. It is outside
the managed activation's failure domain. The inner supervisor is the unit's main process and owns
turn execution, deadlines and release. The controller can retire the unit after the supervisor has
died; the dead supervisor is never asked to certify its own cleanup.

Activation states are `NEW → QUALIFYING → ACTIVE_IDLE ↔ TURN_RUNNING → REVOKING → SEALED`. The only
back-and-forth transition is idle/running within the same valid activation. NEW/QUALIFYING may fail
directly into REVOKING; SEALED requires external retirement proof, never a supervisor
self-certification. Any terminal error, cancellation, lease loss, manifest drift, pointer change,
disconnect during a turn or unexpected child exit enters REVOKING. SEALED has no outgoing
transition. Failure to establish cleanup leaves the slot `QUARANTINED`, which is an operator-control
condition, never an ACTIVE state. No activation or publication follows until cleanup is
independently established.

The external local control protocol uses one length-prefixed UTF-8 canonical JSON object per
request, a four-byte unsigned big-endian length, maximum 128 KiB request frame and 2 MiB response
frame, duplicate-key rejection, no trailing frames and no implicit defaults. It is carried over an
operator-only Unix socket with filesystem access checks and peer-credential validation against the
enrolled operator UID. The endpoint belongs to the outer controller, not the model process. The
controller authenticates the enrolled operator UID; a private inherited supervisor-control
descriptor carries forwarded operations. Runtime children inherit neither that descriptor nor the
external control socket. Runtime UID differs from operator, controller and supervisor UIDs;
filesystem mode alone is insufficient. Request IDs correlate operations; they confer no authority.

Common request fields are `schema, op, request_id, slot_id, activation_id`. `schema` is
`convmem.activation-control.v1`; IDs are 128-bit lowercase hex. The four closed variants add:

- `turn`: `turn_id, text, expected_publication_sha256`;
- `cancel`: `turn_id`;
- `status`: no extra fields;
- `revoke`: `reason`, one of `operator`, `publish`, `scope_change`, `expiry`, `clock_anomaly`,
  `integrity_failure`, `disconnect`, `shutdown`.

Text uses the existing 16,384-code-point/64-KiB UTF-8 bounds and rejects NUL and surrogates. One
turn may run per activation, with no queue. A second turn returns `busy`. Control frames have a
10-second receive/send timeout and at most 8 concurrent authenticated control connections; exceeding
either closes that connection with no partial success. Status/busy/invalid responses are not stored
as turn identities. At most 256 accepted turns are retained for request deduplication; reaching that
cap seals the activation rather than evicting retry identity. Same turn ID/same text returns its
existing state, never reruns it. Same ID/different bytes rejects. Canceling a live turn seals the
activation because a gateway may retain context or continue work after its CLI client exits.
Canceling an already committed turn reports `already_committed` and cannot retract its answer.

Responses have `schema, request_id, slot_id, activation_id, outcome, payload`; every variant's
payload is closed. Outcomes are `status`, `running`, `committed`, `busy`, `cancelled`, `revoking`,
`sealed`, `already_committed`, `request_conflict`, `unavailable`, `invalid_request`. `status`
returns only state, current turn ID or null, pinned publication digest, lease deadline and a fixed
terminal reason or null. It never returns prompts, credentials, raw environment or private paths.

The inner supervisor buffers at most 1 MiB combined agent stdout/stderr. A committed result contains
`turn_id, publication_sha256, committed_wall_time, committed_boottime_ns, output_sha256,
model_output, evidence_basis`. Output hash covers the exact canonical UTF-8 model-output object;
parse with duplicate-key/surrogate/non-finite-number rejection, no executable evaluation. The input
is one complete JSON object followed only by whitespace, and agent exit must be zero.
Integer/finite-float values inside this opaque untrusted object use the existing canonical JSON
number encoding; strict envelope/control fields remain integer-only. `model_output` is the parsed
complete bounded JSON result treated as **untrusted data**, never executable markup or a
task-completion certificate. `evidence_basis` is exactly `model_output_unverified`. Tool-call
evidence is collected independently by the trusted connector/strict server; fields inside model
stdout cannot attest that retrieval ran or that a deployment passed. The operator client renders
only a complete validated response frame. A partial frame, disconnect, timeout or malformed child
output yields no successful answer.

Release commits and revoke acceptance serialize through one supervisor control mutex. The release
operation revalidates lease, pinned publication and activation identity while holding it, then
commits the complete result to the authenticated response path. A revoke that wins first prevents
commitment. A committed answer can be observed later because of transport backpressure; it remains
an answer authorized at its commitment time, never authorization to continue work. This explicitly
replaces the impossible promise of retroactively recalling already authorized bytes. Uncommitted
buffers are discarded, and result retransmission requires a still-valid activation/lease; a new
session cannot fetch an old session's answer.

The control front end does not hold this mutex while waiting for the output consumer. It services
revoke/cancel through separate control connections. Once release is committed, transport bookkeeping
cannot keep a model turn alive or delay unit retirement. On crash, uncertain delivery is reported
through the closed `unavailable` outcome; there is no automatic re-execution and no claim of
exactly-once human observation.

##### Containment and launch boundary

The selected platform is **Linux with an externally owned systemd system service and cgroup v2**. It
is not a user-shell process group or an ad hoc watchdog. A static reviewed unit policy uses the
supervisor as MainPID, `Type=notify`, `NotifyAccess=main`, `ExitType=main`, `Restart=no`,
`KillMode=control-group`, `SendSIGKILL=yes`, `TimeoutStopSec=2s`, `WatchdogSec=1s`,
`RuntimeMaxSec=24h`, `Delegate=no`, `LimitCORE=0`, a read-only root image and private network. No
runtime child receives the notify socket or permission to control the manager. The supervisor alone
owns the watchdog; a separate heartbeat thread may not keep a hung event loop alive. An
authenticated main-process watchdog detects a hung supervisor. Killing the supervisor terminates the
unit; the manager then retires its entire containment domain. Systemd documents group-wide stop
semantics and main-process service lifetime; the kernel exposes descendant-wide kill and
populated-state evidence. These documented mechanisms are capability evidence, not proof that this
target is configured correctly. [systemd kill
contract](https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.kill.xml), [service
lifetime contract](https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.service.xml),
[kernel cgroup v2 contract](https://docs.kernel.org/admin-guide/cgroup-v2.html)

Select a read-only root image/distribution with explicit read-only
public-manifest/projection/config/runtime mounts
and private activation-local writable mounts. No host home, project checkout, user service bus,
container socket, cgroup control handle, cloud credential directory or arbitrary host filesystem is
mounted. Runtime credentials cannot control the manager, publisher or operator socket. The reviewed
launcher closes unrelated inherited descriptors. The control socket/lease descriptors are explicitly
enumerated exceptions, not an ambient inheritance rule.

Use one private network namespace with no external interface or route. The gateway/client and a
dedicated credential-free local inference worker use pinned loopback endpoints **inside that
namespace**. The inference worker is in the same retirement domain and uses prepackaged read-only
model artifacts; no model pulling is allowed. A shared host inference endpoint is not used by this
candidate. The strict ConvMem child is launched through the sealed `setpriv --no-new-privs
--seccomp-filter FILE` executable before Python imports. The pinned BPF program rejects `socket` and
`socketpair` (including alternate ABI forms), network io_uring paths and privilege/namespace
changes; stdin/stdout are its only transport. Unexpected ABI kills the child. All unrelated
inherited descriptors are closed before exec. Filter-load failure aborts; Python-level network mocks
are not enforcement. The connector's only network-capable host is the already contained OpenClaw
process; the connector code may use only its fixed stdio transport.

This is more packaging work than an empty HOME, but it closes several paths with one existing OS
boundary: ambient config, unintended persistence, arbitrary host-loopback access and orphan
inference. It introduces no new durable-memory authority. A full general container platform,
orchestration cluster or internet proxy is unnecessary. If the exact OpenClaw/local-model
combination cannot operate here, activation is unsupported; Grok may not relax the boundary or
replace the provider without architecture review. [systemd execution isolation
contract](https://raw.githubusercontent.com/systemd/systemd/main/man/systemd.exec.xml)

The controller's retirement receipt is `convmem.activation-retirement.v1`, with exact fields
`schema, slot_id, activation_id, activation_manifest_sha256, pinned_publication_sha256,
manager_boot_id, unit_invocation_id, containment_id, terminal_reason, observed_empty_boottime_ns,
receipt_payload_sha256`. The protected controller issues it only after the manager reports the unit
terminal and the cgroup hierarchy empty. A stale receipt for a previous invocation or activation
fails. The inner supervisor's terminal note is diagnostic; only the controller can mark externally
confirmed SEALED after empty-domain proof.

SIGKILL is a termination request, not a claim that every uninterruptible process has vanished by a
wall-clock deadline. If emptiness cannot be established, the slot stays quarantined,
authority/serving mutation cannot race old readers, and the operator gets no successful retirement
receipt. A manager/OS outage is an explicit TCB failure: do not promise magical cleanup if the
kernel and manager both fail. On recovery, independently retire the old domain before reenabling
anything.

##### Locks, clock and publication ordering

One stable slot transition lock serializes launch, retirement, governance fencing and publication
preparation. The controller runs as root outside the service; the unit supervisor also runs as root
in the sealed image and drops supplementary groups, UID/GID and every capability before exec of any
runtime child. Its trusted launch code performs only the fixed role launches. Runtime UID is an
enrolled dedicated non-root account distinct from the operator. Runtime /proc visibility, ptrace and
signals must not reach the privileged supervisor/controller. This is an explicit privileged TCB, not
a claim of same-UID isolation. During ACTIVE, the supervisor holds the lineage's shared serving
lock. This lock is not the transition lock. The supervisor can process revoke and exit without
acquiring a lock held by the controller waiting for its exit.

The lock order for participating production operations is **slot transition → existing universal
production-writer boundary → existing governed-ledger lock → lineage publication exclusive lock**.
The controller retires the activation before requesting the exclusive lineage lock; the supervisor
holds no production/governed lock. A publisher never waits for retirement while holding a lock
needed by retirement. Fixture-only operations omit the production/governed layers but preserve
slot→lineage order. No implementation may introduce a reverse path; Gate W must prove this order
against §14.3’s census and all restore entry points before acceptance. This initial version enrolls
at most one runtime slot for a lineage, so there is no unspecified multi-slot lock order.

Launch holds the transition lock, verifies no pending governance and no old populated unit,
qualifies the exact publication, obtains the serving lease, starts the manager-owned unit and waits
for the exact activation's READY response. Only then does it release the transition lock. A failure
anywhere retires the incomplete activation. An operator controller crash leaves manager state and
slot evidence for recovery; it does not entitle the next caller to start a second unit.

Lease creation captures both wall time and `CLOCK_BOOTTIME`, with deadline
`min(persisted_snapshot_deadline_boottime_ns, boottime_now_ns + 1000000000 * min(expires_at -
wall_now, max_lifetime))`. Nonpositive remaining lifetime denies. Use integer nanoseconds, not float
rounding. Test both bounds at turn start, at least every 100 ms during work and at release. A
wall-time decrease or disagreement indicating a backwards step seals rather than extending
authority; false-positive retirement under clock adjustment is an accepted availability cost.
BOOTTIME includes suspended time, unlike MONOTONIC. A suspend/resume therefore cannot extend the
lease. After reboot every activation is dead and non-resumable. [Linux clock
semantics](https://man7.org/linux/man-pages/man3/clock_gettime.3.html)

Process restart must not reset snapshot age. At first qualification on a boot, persist
`freshness_anchor={boot_id, authority_snapshot_id, sampled_wall_time, sampled_boottime_ns,
snapshot_deadline_boottime_ns, clock_review_ref}`. The snapshot deadline is sampled BOOTTIME plus
the nonnegative remaining absolute snapshot lifetime. All activations/generations of that authority
snapshot on that boot reuse that deadline or a smaller one; the per-activation lifetime is an
additional bound. Rollback copies the current anchor, not the target generation's launch time. Clock
samples and release commitment are taken under the control mutex with no intervening awaited work;
the final valid clock sample is the release decision's linearization point.

For clock-anomaly detection, compare wall samples for an observed decrease and maintain the maximum
lower bound on the wall-minus-BOOTTIME offset using paired BOOTTIME-before/wall/BOOTTIME-after
samples. A new offset interval entirely below the retained lower bound seals. No claim is made to
detect every sub-sample correction; none can extend the persisted BOOTTIME deadline. On a new boot,
an old anchor is invalid. The initial contract requires an operator clock-review receipt binding the
new boot and the still-fixed `expires_at` before making a new anchor; it may only establish the
remaining absolute lifetime, never renew the source cutoff. Without trustworthy current time, no
activation. This is a deliberately manual, file-backed reboot boundary, not an invented secure clock
or silent lease refresh.

`as_of` denotes the admitted source cutoff, not the time a builder happened to run. Rebuilding or
rollback cannot extend `expires_at`. A new source cutoff requires new reviewed capture/admission
evidence; merely changing `built_at` or resubmitting identical bytes does not refresh measurements.
Even an unexpired snapshot can contain old measurements, so each result retains its `observed_at`;
snapshot freshness is not a claim that the underlying world was rechecked.

##### Activation inputs, outputs and configuration

Extend the activation manifest to bind `slot_id, lineage_id, publication_sha256,
runtime_distribution_sha256, model_artifacts_sha256, launch_policy_sha256, manager_policy_sha256,
control_protocol_version, release_protocol_version`, alongside the
scope/registry/config/plugin/server/supervisor identities and time bounds listed in the exact
manifest below. The launch policy is a closed hashed artifact specifying exact executable arrays,
empty working directories, environment maps by child role, read-only mounts, writable mounts with
size ceilings, endpoint tuples and descriptor inheritance. Runtime root-image bytes bind the actual
Node/Python/OpenClaw/imported-dependency closure, not just package/version names. Kernel, system
manager and required device-driver versions are named TCB assumptions and separately recorded; the
entire host is not hashed.

The launch-policy top-level field set is `schema, runtime_distribution_sha256,
model_artifacts_sha256, processes, read_only_mounts, writable_mounts, endpoints, operator_uid,
controller_uid, supervisor_uid, runtime_uid, manager_policy_sha256, policy_payload_sha256`.
`processes` has exactly the role keys `supervisor, gateway, agent, strict_server, model_worker`;
each value contains `executable, argv_template, cwd, environment, inherited_fd_roles,
network_policy`. All substitutions are typed activation values, except the single already-bounded
TURN_TEXT sentinel; no shell expansion is allowed. `network_policy` is `activation_loopback` or
`none`, with strict_server fixed to `none`. Mount entries are closed `source_role, destination,
mode, max_bytes` objects; max_bytes is null for immutable mounts and a positive reviewed integer for
writable mounts. Only declared runtime/public_evidence/config/model/control/state source roles are
allowed, never a supplied arbitrary host path. Endpoints contain exactly `gateway_port, model_port,
model_api, model_id`; ports are distinct reviewed high ports, addresses are the literal namespace
loopback, model_api is the bundled `openai-completions` adapter, and model_id is one packaged
identifier. A target-specific model worker command is an input artifact requiring evidence, not
permission to choose another provider.

Both gateway and agent run from the fixed read-only empty cwd. HOME, workspace, state, agent-model
config, caches, temp, logs and session roots are fresh activation-local mounts. Disable
shell-environment import; reject inline environment additions. Every documented `.env` discovery
point is absent inside the sealed root. OpenClaw config includes the exact gateway port, a single
local provider/model route, mandatory replace-not-merge provider catalog behavior, no fallback, no
secret lookup, and no inherited `models.json`. Host log/journal sockets are absent; captured stderr
stays bounded/private. Default shared `/tmp/openclaw` resolves only inside the private activation
filesystem, and an explicit private log path is still configured.

Keep the original disabling of native memory, automatic memory flush, heartbeat, ACP, subagents,
skills, hooks, discovery, channels, runtime/filesystem/browser/write tools and automatic transcript
capture. Verify effective inventory in the actual child session; configuration syntax alone does not
establish the boundary. The precise pinned build must also demonstrate that no implicit provider
credential or broader tool profile is required. Read-only inspection in §14.2 found that the
currently selected local route fails this requirement; this is a later-runtime architecture
blocker, not a T0–T5 task for Grok to bypass. Empty-secret placeholders may not be invented to hide that
incompatibility.

Runtime writable state is transient. On retirement it is made inaccessible for resumption;
subsequent controlled cleanup may remove it. The normal durable diagnostic receipt contains
IDs/digests/reasons only, with no prompts, corpus text, token or model answer. An optional retained
audit artifact containing content would require an explicit separate retention decision; it is not a
new default sink. Crash dumps are disabled. Evidence-rich fake tests use synthetic inputs only.

##### Closed activation/control artifacts

`convmem.openclaw-activation.v2` has exactly:

```text
schema, activation_id, slot_id, lineage_id, owner_digest, publication_sha256,
scope_sha256, registry_sha256, strict_config_sha256,
authority_manifest_sha256, projection_manifest_sha256, snapshot_id,
as_of, expires_at, openclaw_version, openclaw_config_sha256,
plugin_tree_sha256, connector_launch_sha256, strict_server_tree_sha256,
supervisor_tree_sha256, controller_tree_sha256, runtime_distribution_sha256,
model_artifacts_sha256, launch_policy_sha256, manager_policy_sha256,
control_protocol_version, release_protocol_version, state_dir,
gateway_port, gateway_argv_sha256, agent_argv_sha256, created_at,
max_monotonic_lifetime_seconds, manifest_payload_sha256
```

Protocol versions are `convmem.activation-control.v1` and `convmem.buffered-release.v1`. Maximum
lifetime is an integer 1–86400, bounded again by the persisted snapshot deadline. State directory
must be nonexistent under the enrolled activation parent; no reuse. Launch uses
`openclaw_activation_controller.py start --activation-manifest ABS --launch-policy ABS
--manager-policy ABS --openclaw-config ABS`; the controller alone starts the system unit. The unit
invokes `openclaw_activation_supervisor.py --activation-manifest ABS` with its private
control/lease/notify descriptors. Controller control operations use the authenticated framed Unix
socket. No OpenClaw/MCP tool can call them.

Tree hashes use canonical sorted closed `{path, mode, sha256}` entries: relative POSIX paths,
four-octal-digit mode, regular files only, no symlinks/unlisted loads. Runtime-distribution SHA-256
binds the complete immutable image containing actual Node, Python, OpenClaw, MCP/idna dependencies,
dynamic loader/libraries, plugin, setpriv and BPF bytes. Model-artifact digest uses the same tree
recipe for exact packaged model files. Host pnpm symlinks and a launcher hash are not a
distribution. No linker/import fallback to the host. Exact TCB kernel/manager versions and necessary
device policy are separately recorded; CPU-only is the initial profile, with no GPU/device-driver
delegation.

The manager policy is closed `convmem.activation-manager-policy.v1`: `schema, unit_bytes_b64,
unit_sha256, controller_socket_policy_sha256, runtime_distribution_sha256, operator_uid,
controller_uid, supervisor_uid, runtime_uid, kernel_release, systemd_version,
capability_evidence_sha256, policy_payload_sha256`. Decoded canonical unit bytes must implement
every setting and isolation property above. UIDs and paths are concrete reviewed evidence inputs,
never defaults. The controller socket policy is closed `convmem.controller-socket-policy.v1`:
`schema, socket_path, socket_mode, owner_uid, permitted_peer_uid, max_request_bytes,
max_response_bytes, policy_payload_sha256`; mode is `0600`, path outside runtime mounts, peer UID
equals operator UID, limits 131072/2097152. UID/GID provisioning and manager authorization are not
granted by this plan.

The launch-policy schema is `convmem.activation-launch-policy.v1` with the field set above.
`processes` entries additionally require `uid, gid, seccomp_filter_sha256` (null except the
mandatory strict-server filter). Environments are exact sorted key/value objects for each role; no
wildcard copying. Gateway/agent keys are only `OPENCLAW_GATEWAY_TOKEN, OPENCLAW_STATE_DIR,
OPENCLAW_CONFIG_PATH, HOME, PATH, LANG, LC_ALL, TMPDIR, XDG_CACHE_HOME`. Supervisor's separate map
adds only manager-supplied notify/watchdog values and fixed private descriptor roles. Model worker
receives only its packaged command's explicit local state/cache/thread settings, no provider
credentials. Strict-server map is exactly §4 (including `TMPDIR`); the connector clears all parent
variables. Every path resolves inside the sealed namespace. Directory ceilings total at most 1 GiB
writable state per activation; hitting any ceiling retires. Mount modes are `ro` or `rw`;
public-authority-manifest/projection/config/runtime/model mounts are ro, state/temp rw; no other
source role. Gateway and model
ports are distinct fixed 49152–65535 integers on namespace loopback.

Gateway/agent/model-worker stdout and stderr, not just the final agent frame, are supervised bounded
private sinks; no host journal/syslog socket or inherited terminal is attached. A per-activation 1
MiB cumulative gateway/model diagnostic-output budget and 1 MiB per-turn agent budget apply;
overflow retires instead of spilling. Normal retirement retains only content-free receipts;
transient session/log files are never resumed. Optional retained content requires a separate
retention decision.

Fixed gateway argv is `[NODE, OPENCLAW_ENTRY, "gateway", "run", "--bind", "loopback", "--port",
PORT, "--auth", "token", "--tailscale", "off", "--ws-log", "compact"]`; agent argv is `[NODE,
OPENCLAW_ENTRY, "agent", "--json", "--session-id", ACTIVATION_ID, "--timeout", "120", "--message",
TURN_TEXT]`. Node/entry are sealed absolute paths, not the host pnpm shell wrapper. The agent argv
hash uses literal `TURN_TEXT`; only that field accepts bounded operator text. Both run from the same
fixed empty read-only cwd. The gateway token is random 256-bit activation-local data supplied to
gateway/agent only, never persisted or sent to the strict child/model. The model worker's exact
executable/argv/model digest remain a required compatibility artifact; no guessed provider/worker is
implied by this document.

For activation control, `status` outcome payload is exactly `{state, turn_id, publication_sha256,
lease_deadline_boottime_ns, terminal_reason}`; `running` is `{turn_id}`; `busy` is
`{active_turn_id}`; `cancelled` is `{turn_id}`; `revoking` is `{reason}`; `sealed` is `{reason,
retirement_ref}`; `already_committed` is `{turn_id, output_sha256}`; `request_conflict` is
`{turn_id}`; `unavailable` and `invalid_request` are `{reason}` with a fixed reason enum drawn from
revoke reasons plus `not_active`, `stale_publication`, `bad_frame`, `bad_arguments`, `capacity`. No
free-form errors. `committed` has the exact result fields defined above. Status is read-only;
cancel/revoke are terminal control operations, not changes to evidence authority. Repeated request
ID for an accepted turn with changed canonical request bytes is invalid; turn ID deduplication also
covers a new request ID retry. Results are retransmitted only while that activation's lease remains
valid. After supervisor crash, uncertainty is unavailable; neither controller nor new activation
reruns an uncertain turn.

`convmem.clock-review.v1` has `schema, lineage_id, authority_snapshot_id, boot_id, expires_at,
reviewed_wall_time, reviewer_uid, review_payload_sha256`. It is owner-produced, protected, and
content-addressed; a copied reviewer UID is not authorization. New-boot qualification must
authenticate it in the protected operator inventory. An old same-boot anchor may only shrink.
`freshness_anchor` fields and sampling rule above also apply to CLI readers; reader process restart
never renews age.

#### 6.5.7 Explicit approval, admission and recovery

The selected contract keeps the user's literal route. Approval/rejection are governance operations.
**Approval does not invoke indexing.** `record --approve-last` persists ratified intent and reports
the exact artifact for a later `convmem add --file ABS`. Existing `--no-index` may remain a
compatibility no-op with clear output; no flag on the approval command enables automatic indexing.
`record --recover` can reconcile intent bookkeeping but cannot ingest. This is a necessary behavior
change to the combined default, not a claim that the existing stable CLI already implements the new
invariant.

The approved artifact is closed `convmem.approved-admission.v1` with `schema, operation_id,
proposal_id, lineage_id, expected_authority_manifest_sha256, source_registration_id, records,
dispositions, grounding_refs, intent_sha256, review_ref, ratification_ref, artifact_payload_sha256`.
Each reference names exact bytes in the operator-owned governance/capture inventory. The artifact is
a transport of already ratified intent, never independent approval authority. Records and
dispositions are the exact canonical new delta (not a rewrite of parent contents); record kind/IDs
and dispositions use §6.5's schemas. `grounding_refs` is a sorted unique array of `{kind, sha256}`
references, with kind `provenance_context` or `grounding`, naming exactly one new cumulative object
of each kind in protected immutable storage. Those bytes are authenticated and merged only by the
qualifier; the artifact cannot cause arbitrary filesystem/URL lookup. Proposal IDs preserve the
existing proposal-ID grammar; no implicit identifier migration. Expected parent is null only for
explicitly enrolled genesis.

Approval hashing is deliberately two-level to avoid both reference cycles and a demand that review
predict a future ratification timestamp. `intent_sha256` hashes the canonical closed object
`schema:"convmem.admission-intent.v1", operation_id, proposal_id, lineage_id,
expected_authority_manifest_sha256, source_registration_id, record_semantics, transition_semantics,
grounding_refs`. `record_semantics` is the assertion-ID-sorted array of exact `{assertion_id,
semantic_sha256}` objects, with semantic hashes recomputed under §6.5’s exclusions for disposition
references. `transition_semantics` contains each disposition's exact `action, project_binding_id,
subject_assertion_id, subject_semantic_sha256, target_assertion_ids, basis_snapshot_id,
expected_head_assertion_ids, replaces_disposition_ref, rationale_sha256`, canonically sorted by
action/subject/targets. These bind the entire proposed meaning and capture commitments without
binding future review/ratification metadata.

The review binds that intent digest; ratification binds the same digest and exact review reference.
Final disposition actor/role/outcome/time fields must equal the protected review/ratification
receipts, and the final source-record disposition references must equal the recomputed final
dispositions. The full artifact payload hash excludes only itself and binds all final bytes and both
references. The engine reconstructs these relationships; it does not trust a supplied
`intent_sha256`. Copied signer/status fields, plausible proposal IDs, an in-memory boolean or
`_governed_protocol` cannot authenticate approval. A review or ratification receipt is not hashed
recursively through the finalized artifact it authorizes.

The governed engine implements:

`PROPOSED → RATIFIED_AWAITING_ADD → ADMISSION_PREPARED → ADMITTED_UNPROJECTED → PROJECTED`.

`REJECTED` and `CANCELLED_BEFORE_ADMISSION` are terminal alternatives with exact owner-authored
events. They cannot undo ADMITTED. Revocation after admission is a separate forward authority
operation. At most one unsettled ratified operation exists per lineage; more drafts may exist, but
another ratification waits. This removes ambiguous competing recovery order without moving authority
into a queue daemon.

Before a ratification affecting an enrolled strict lineage becomes durable, the controller retires
its activation and persists a serving fence naming the operation. The ratified payload is then
durably recorded. A crash before ratification is distinguished from a committed intent by the
protected governance record, never by Chroma. Recovery may abandon an unratified preparation or
expose a missing artifact for reconstruction from the exact ratified bytes; it cannot infer approval
from a half-written queue row. A committed intent keeps the fence until explicit add or an
owner-authored pre-admission cancellation.

`add --file` validates exact approval, expected prior authority, full content and identity, source
registration and capture qualification under the existing writer discipline. It records the
operation's durable preparation, admits the immutable source/transition exactly once, advances the
authoritative source cutoff, and publishes an unavailable head before attempting projection.
Projection completion is derivative bookkeeping. A failure after admission leaves
ADMITTED_UNPROJECTED; retry rebuilds from admitted authority and never re-ratifies or duplicates the
decision. A crash after publication but before completion bookkeeping is reconciled by exact
operation/head/hash equality.

The protected admitted-source prefix is the admission commit boundary for production; qualified
authority publication and ADMITTED event may follow it. A crash after that commit must reconcile
forward from the durable exact operation, never restore old serving. A crash at ADMISSION_PREPARED
with no proven source-prefix commit requires explicit add retry; `recover` may report/repair
bookkeeping but cannot complete that uncommitted admission. A crash after admission may be
reconciled without repeating admission, even if the ADMITTED event was not appended. An
authenticated committed source operation cannot be cancelled; a stale queue marker cannot reopen it.

No recovery routine may treat a Chroma read exception as “no previous decision.” Chroma can be
inspected to repair serving, but expected-state validation uses the protected durable
admission/approval history. Unknown history is an error. Ordinary ungoverned observations remain
distinct from governed decision admission; generic add cannot convert a decision-shaped input into
approved strict authority. Existing legacy writers cannot set strict authority metadata or produce a
qualified strict generation.

This architecture requires a narrowly scoped follow-on change to the protected CLI,
proposal/recovery and governed-write boundary. The paired execution plan assigns this correction to
Gate W; Gate B/C preserve the legacy files byte-for-byte. Gate W is an explicit required production
boundary, not a claimed property of a fixture build. The baseline census and required compatibility
routing in §14.3 enumerate approval, recovery, watch/index, repair and raw-writer families. Gate W
must recheck that census on its exact implementation baseline; preserve existing outer
safety/backup/recovery guarantees; and show all governed routes resolve through the same engine. New
schema bytes cannot repair unknown historical consent. **No automatic legacy migration is
selected.** Existing ambiguous history stays in the legacy surface until an explicit reviewed
migration or fresh ratification establishes the needed binding; neither is delegated to Grok as an
implementation convenience.

Protected governance receipts use `convmem.admission-review.v1` (`schema, intent_sha256,
reviewer_actor, reviewer_role, outcome, reviewed_at, receipt_payload_sha256`) and
`convmem.admission-ratification.v1` (`schema, operation_id, intent_sha256, review_ref,
ratifier_actor, ratifier_role, ratified_at, receipt_payload_sha256`). Their refs are
`review_`/`ratify_` plus recomputed payload hash. Role/outcome enums equal §6.5.1.
Operator-controlled publication into the governance inventory authenticates them; artifact-supplied
names do not. A rejection is durably recorded but never admitted as approved.

The new admission event stream is a versioned extension beside the legacy events, not a
reinterpretation of old `APPROVED`: closed `convmem.admission-event.v1` has `schema, event_id,
sequence, previous_event_sha256, event_type, operation_id, proposal_id, lineage_id, intent_sha256,
artifact_sha256, authority_manifest_sha256, recorded_at, event_payload_sha256`. Event type is
exactly `PROPOSED`, `RATIFIED_AWAITING_ADD`, `ADMISSION_PREPARED`, `ADMITTED_UNPROJECTED`,
`PROJECTED`, `REJECTED`, or `CANCELLED_BEFORE_ADMISSION`; inapplicable hashes are explicit null.
Sequence is per lineage, starts1, exact+1, parent-hashed; duplicate event ID/same bytes is
idempotent, changed bytes reject. Unknown/truncated tail blocks admission/recovery. The semantic
state transition is validated independently from append order. An admission receipt is this stream's
exact ADMITTED_UNPROJECTED event referring to qualified authority, never a Chroma marker. Durable
intent and admitted source remain owner-governed files; projection bookkeeping cannot redefine them.

Legacy transition rule: `PROPOSED`, `APPROVAL_STARTED`, `APPROVED`, `REJECTED`, `SUPERSEDED` remain
readable in their existing schema, never automatically mapped to the new states. No legacy proposal
enters an enrolled lineage or receives new closure authority by inference. New-format fresh
ratification must explicitly bind any legacy material as new assertions with preserved old
references; no overwrite/renumber/reinterpretation of history. Old incomplete approvals are reported
`legacy_review_required`; recovery does not ingest them. Existing completed legacy approvals remain
historical evidence under the legacy authority map, not new admission receipts. After Gate W
cutover, approval commands persist intent only for all governed writes, and any legacy approved-file
add without the new authenticated artifact fails with a migration-required diagnostic. Ordinary
ungoverned observation ingestion remains outside strict admission.

All new-format artifacts, governance roots, capture inventories and strict authority roots are
excluded from generic index/watch/repair/discovery ingestion. No model-distilled copy qualifies.
Generic add may ingest ordinary legacy observations but rejects governed decisions/strict metadata
unless dispatched to the authenticated engine; both create and upsert are checked. A private Python
flag is not a transferable capability. Existing backup and recovery authorization remain outer
gates; a recovery path cannot become an alternate add command. Startup after a restore must
reconcile latest history before clearing the slot fence. The migration of any live corpus remains
unsupported in this candidate, rather than a decision for the implementer.

#### 6.5.8 Frozen T0–T5 fixture execution boundary

This section resolves B-FIXTURE. It selects a **nonprivileged protocol simulation**, not an
alternative OpenClaw provider or a miniature production deployment. B/C implement the existing
parsers, pure control/state machines and connector transport logic. Real systemd/privilege/model
execution adapters are outside B/C. In this slice the production controller `start` and supervisor
entrypoints exit 78 with fixed stderr `runtime_not_qualified` before any OS operation; ordinary
OpenClaw plugin registration refuses with that same reason. Direct strict file/MCP entrypoints
remain testable inside the disposable harness. Gate D needs a separately reviewed adapter/packaging
packet to enable actual launches; it cannot reinterpret the protocols frozen here.

**Injection boundary.** Tests directly construct the controller/supervisor core with test-owned
`FixturePlatform` and construct connector transport with a test-owned `spawn` function. These are
library dependencies supplied by the test caller, never serialized settings. No CLI flag,
environment variable, plugin setting, manifest field, imported source record or production loader
can select a fake. Fixture adapters live only under `tests/fixtures/openclaw_strict/`; production
modules do not import that tree. Core code cannot directly call OS manager, socket, signal, UID,
mount, exec or clock functions: all such actions pass through the following fixed port. Internal
helper names are free; port meanings and serialized values are not.

- `sample_clock()` returns `{boot_id, wall_time, boottime_before_ns, boottime_after_ns}` with
  §6.5.6's types and sampling semantics. The harness alone advances wall/BOOTTIME, independently,
  including backwards wall steps, suspend and new boot; no real waiting is needed for these tests.
- `peer(connection_id)` returns `{uid,gid}` from the harness's connection table, never request JSON.
  Logical UID/GID pairs are fixed: operator `1000/1000`, controller `0/0`, supervisor `0/0`, runtime
  `1001/1001`. They are simulation identities; no host account or real setuid is requested.
- `access(role,path,operation)` checks the fixed virtual table below before fixture file access.
  Operations are only `read`, `create`, `replace`, `lock`; paths must resolve within the fresh root,
  reject symlinks/traversal and never come from evidence text. Denial causes the normal caller's
  failure path, not an automatic alternative path.
- `spawn(role,argv,env,cwd,fd_roles)` validates the exact §4/§6.5.6 launch tuple as **data**, logs it
  in the synthetic test trace and returns a monotonically allocated 32-hex handle. The five roles
  are `supervisor`, `gateway`, `agent`, `strict_server`, `model_worker`. None is a real process in
  T4/T5. The model-worker argv is exactly `["/fixture/bin/model-worker"]`; it is an inert role
  name, not a selected inference executable. All other paths use the fixed `/fixture` namespace;
  the prescribed gateway/agent/strict-server argv structures are unchanged.
- `next_event(handle)` yields a closed `{kind, bytes_b64, exit_code}` object. Kinds are `ready`,
  `stdout`, `stderr`, `exit`, `hang`; bytes are canonical base64 only for stdout/stderr, exit_code
  is an integer only for exit, and other values are explicit null. `ready` is allowed once, exit
  is terminal, and hang emits nothing until a harness event. No event text is evaluated. Agent
  success bytes are exactly `{"fixture":"protocol-only","text":"synthetic answer"}` with
  exit 0; malformed/partial/oversized output and nonzero exits are explicit negative scenarios.
- `manager_start(slot_id,activation_id)` allocates a new invocation/containment identity from the
  same deterministic counter and registers all logical descendants and outstanding model work.
  `manager_stop(invocation_id)` requests retirement; its acknowledgement never asserts emptiness.
  `manager_observe(invocation_id)` returns exactly `{manager_boot_id, unit_invocation_id,
  containment_id, terminal, populated}`. `terminal` is boolean; populated is true, false or null
  (unknown). Only exact-invocation `terminal=true,populated=false` permits the external controller
  to issue §6.5.6's retirement receipt. A stale boot/invocation, null, or remaining descendant/work
  item quarantines. The fake manager owns a separate membership set; only harness-scheduled manager
  events remove members. Supervisor exit/self-report cannot clear it. Simulated detached children
  remain members. Controller crash preserves this set and the on-disk slot for reconciliation.

Fixture control transport is a pair of bounded in-memory byte queues exercising the exact length
framing, partial frames, eight connections, timeouts and separate revoke path. `fd_roles` are opaque
test capabilities: operator↔controller, controller↔supervisor, supervisor notify/lease, or strict
stdin/stdout/stderr. Runtime roles never receive control/notify/lease capabilities. Socket creation,
network endpoints, real signals and privilege drops are forbidden. Fixed ports 49152/49153 and
`openai-completions`/`fixture-model` may occur only as schema-validation data; nothing connects to
them. The fake neither requests nor accepts provider keys, tokens, profiles or fallback. A modeled
gateway-token value is a constant synthetic marker in an expected environment map, not a credential
and never used to authenticate anything. Fake success cannot change C-RUNTIME's status.

The virtual access table is exact: publisher/qualifier/operator may access synthetic private
authority, grounding, citation, issuer and governance paths; controller may read those paths for
qualification and write control/slot/receipt paths; supervisor may read pinned public files and
use its inherited lease/control roles; runtime may read only public manifest/projection and
scope/registry/strict-config, plus write its disposable state/temp paths. Public files are read-only
for every runtime role. Production-mode enrollment, foreign roots, private-path access by a runtime
role, or a runtime-supplied claimed qualification flag fails. This is a test of the access contract,
not proof of real UID/mount separation. Gate D repeats it with real enforcement.

**Physical test containment.** The whole test suite runs under a nonprivileged Linux bubblewrap
harness before importing the implementation: fresh user/PID/IPC/network/UTS namespaces, empty root,
capabilities dropped, new session, parent-death termination and private proc/dev. Bind only an
export of the exact tracked source at `/src` read-only, an explicitly inventoried test-runtime
prefix at `/runtime` read-only, that prefix's `sysroot/usr` subtree at `/usr` read-only (with
`/bin`, `/lib`, `/lib64` aliases into it), and one newly created mode0700 `/tmp/convmem-openclaw-fixture.XXXXXX`
root at `/fixture`. No host root/home, `/run`, service bus, Docker socket, live checkout `.git`,
ConvMem/OpenClaw state or host temp tree is mounted. Private `/tmp` is a 256 MiB tmpfs.
Use mandatory `--unshare-user --unshare-pid --unshare-ipc --unshare-net --unshare-uts`,
`--disable-userns --assert-userns-disabled --cap-drop ALL --new-session --die-with-parent`;
no `--*-try`, `--share-net` or `--not-a-security-boundary` fallback. Retain bubblewrap's PID1
reaper; do not use `--as-pid-1`. Sandbox setup failure stops TEST before imports.

The test-runtime prefix contains only the pre-provisioned interpreter/dependency files, no user
configuration, credentials, model artifacts or OpenClaw package. Freeze CPython 3.13.12, Unicode
15.1.0, Node 26.9.0, MCP 1.28.1 and idna 3.18; other compatibility-test dependencies follow the
baseline `requirements.txt`. The runtime manifest enumerates every regular file/mode/hash, rejects
symlinks and unlisted files, and is returned with evidence. These are test tools, not a production
image. Missing tools/dependencies block TEST provisioning, not the specified BUILD; no install,
download or version substitution occurs inside the harness. Supplying the specified bytes does
not let Grok choose a production distribution.

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

Environment starts empty: `HOME=/fixture/home`, `TMPDIR=/fixture/tmp`,
`XDG_CONFIG_HOME=/fixture/config`, `XDG_CACHE_HOME=/fixture/cache`, `XDG_DATA_HOME=/fixture/data`,
`PATH=/runtime/bin:/usr/bin`, `LANG=C.UTF-8`, `LC_ALL=C.UTF-8`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`; no other inherited variables.
Create these empty directories before tests. Close inherited FDs except bounded stdio. The driver
allows only the exact execution §5.1 pytest/Node suites and fresh Python invocations of the named publisher,
reader and strict-server entrypoints; it has no general command runner. T4/T5 spawn remains virtual.
Run from read-only `/src`, disable pytest's cache provider, and place its explicit base-temp roots
under `/fixture`. Explicitly load only baseline-required test plugins and record their inventory;
never enable plugin autoload. The two frozen Python commands additionally activate pytest's
already-loaded built-in JUnit reporter and write only
`/fixture/evidence/pytest-strict-junit.xml` and
`/fixture/evidence/pytest-legacy-junit.xml`. This adds no plugin, dependency, environment input,
process, selector, deselection, test, permission or runtime capability. The Node command is
unchanged. Per-suite wall deadline is 600 seconds; captured stdout/stderr has a
combined 16 MiB limit. Exceeding either fails without budget expansion. Execution §5.1 fixes the
test-only runner's closed CLI, pre-import setup operations and exact inner commands.
These are unmeasured limits, not demonstrated capacity. TEST records monotonic elapsed time,
combined output bytes and maximum sampled `/tmp` allocated bytes (with sampling interval), verifies the tmpfs size
is 268435456 bytes, and fails on deadline/output overflow or ENOSPC. The `/tmp` limit does not
describe `/fixture` storage. Thresholds remain 600 seconds, 16777216 output bytes and the fixed
256 MiB tmpfs; no harness limit changes protocol deadlines, authority or freshness. Cursor/Grok
repairs inefficient test/runner code within scope; a necessary limit change returns to Codex/Kiro
with the measurement, not an automatic BUILD downgrade or silent budget expansion.
No real OpenClaw/systemd/model executable or credential/auth request is ever allowed. Network
denial is independently checked before suite entry; network calls in B/C are additionally forbidden
by the test port/import guards. Failure cannot fall back to running on the host.

Preflight uses only synthetic canaries outside the bound root: prove they are unresolvable inside,
outside-root writes fail, the network namespace differs from the host with no external routes,
inherited sentinel credential/config variables are absent, and no unexpected FD survives. No host
listener is started. Do not fingerprint/read real credential files. Negative harness controls use
separate synthetic roots or deliberately incorrect namespace/env/FD observations and must fail
before implementation imports. They never disable the outer disposable boundary or mount live
paths. Missing containment, an ambient open/exec/network
attempt, forbidden import, or an unexpected surviving real test child fails the suite. The driver
waits for the sandbox PID namespace to terminate before test teardown; a timeout retains the root
and returns failure for operator cleanup. It never calls deletion “lineage recovery.”

**Closed suite selection.** Execution §5.1's `--suite all` is exactly strict Python, connector
Node and bounded legacy Python, not repository-wide pytest discovery. Its legacy command keeps
the named compatibility files and explicitly adds `tests/test_provenance.py` and
`tests/test_provenance_continuity.py`. Exactly four nodes in `tests/test_agent_run_ledger.py` are
outside this fixture selection: `test_v8_kiro_hook_adapter_fail_open`,
`test_v6_git_facts_non_git_cwd`, `test_q7_hook_failure_writes_stderr`, and
`test_q4_hook_two_missing_id_starts_same_cwd`. They require real hook/Git subprocesses forbidden
by this runner. The baseline's full suite also requires Git/shell/systemd probes. Report these
exclusions and no full-repository result; do not call them passed, replace them with mocked
success, alter protected tests, or broaden the process/mount inventory. Existing repository-wide
checks remain separate work. Every other node in the named legacy files remains selected.
The runner verifies the exact §5.1 selectors/deselections against test-owned constants before
collection, rejects extra deselections/full discovery, and reports the collected node IDs.
No new selected safety-test skip is accepted. Legacy compatibility uses a separate fresh pytest
process, the same physical containment and no subprocess allowance. Only that process may import
unchanged legacy config/writers for its synthetic stores; strict components retain their original
import restrictions. This preserves legacy behavior without granting strict readers write access.

Exact live Python node/outcome evidence comes only from the two built-in JUnit reports, never from
AST enumeration, a test-side session dump, `--collect-only`, another pytest process, `conftest.py`,
`PYTEST_PLUGINS`, `PYTEST_ADDOPTS` or a new plugin. After both existing Python processes finish, the
outer runner parses the xunit1 reports as data and reconstructs each node ID losslessly from
pytest's `file`, `classname` and `name` attributes against the exact selected-file map. It rejects missing or
multiple file-prefix matches, duplicate reconstructed node IDs, lossy `#xNN`/`#xNNNN` escape
markers, malformed XML, unexpected testcase children, a node outside the exact selected files, or
any of the four deselected nodes appearing. Outcome is exactly `passed`, `failed`, `error` or
`skipped`, derived from the testcase's zero-or-one outcome child; failures/errors, conflicting
children, report/process-count disagreement or a nonzero Python suite status fail TEST. Each
selected file must contribute at least one testcase. The canonical sorted node/outcome arrays from
both fresh-root runs must be identical. Static AST inventories may remain diagnostic only and must
not be labeled or accepted as collected-node evidence.

Case57 must observe actual kernel denials for outside-root canary opens/writes and read-only
mount writes, not merely a fake `access()` denial. A separate synthetic-only inner exposure of
a canary must make the independent preflight fail while the outer boundary stays intact. Fake
role permissions, peers and manager membership remain modeled contracts with independent oracles;
these tests do not require Gate D UID/systemd enforcement. Copy input files to fresh disposable
`/fixture` subtrees before any case58 mutation; never mutate `/src`, `/runtime`, `/usr` or the
protected checkout. The reference walker owns its literal inventory and computes canonical bytes
and expected hashes itself, never asking the implementation for its expected set or digest.

**Reproducible fixture artifacts.** T0 adds the closed test-only schema
`tests/fixtures/openclaw_strict/fixture-manifest.schema.json` and canonical `fixture-manifest.json`:
`schema:"convmem.strict-fixture-manifest.v1", artifact_kind:"protocol_fixture", plan_sha,
code_baseline_sha, source_tree_sha256, test_runtime_tree_sha256, components, artifacts,
manifest_payload_sha256`. Components is the exact sorted five `{name,sha256}` entries from §6.5.9.
Artifacts is a sorted array of `{path,mode,sha256}` covering every test helper, scenario, schema and
synthetic specimen under the fixture tree, excluding only the manifest itself and generated run
outputs. No missing/duplicate/unlisted input, symlink or path escape is accepted. Hash excludes only
manifest_payload_sha256. `source_tree_sha256` hashes the exact tracked source export with the
fixture manifest and generated run outputs excluded, preventing a self-reference; the exported
input inventory is returned alongside the manifest. Generation uses canonical JSON, fixed clock/event/identity scenario data
and exact source bytes; it never discovers a runtime/model/provider from the host.
The two raw JUnit reports and the derived canonical node/outcome report are generated only under
disposable `/fixture/evidence`; they are returned evidence, never fixture/source/component hash
inputs or authority artifacts.

Launch/activation/filter/image/model specimens are wrapped as closed
`{artifact_kind:"protocol_fixture", role, payload}` test data. Role is one of `activation`,
`launch`, `manager`, `socket`, `connector`, `filter`, `runtime_image`, `model`; payload is either
the relevant closed production-schema instance or, for filter/image/model, the canonical inert
object `{schema:"convmem.inert-fixture.v1", role}`. Cross-digests hash the referenced specimen's
canonical bytes. They are not executable filters/images/models. The harness alone unwraps specimen
payloads for pure validator tests, validating the same fixed field sets without claiming a real
deployment. Production entrypoints reject the wrapper and remain disabled even if a specimen is
unwrapped. No fixture manifest participates in the lineage's production semantic-contract hash or
supplies authority. No fixture-to-production promotion exists.

Rollback tests use real synthetic authority files plus the fake retirement port, retaining the
current authority head and original freshness anchor. Failed manager emptiness prevents serving
mutation/replacement exactly as at Gate D. All existing cases remain; §13 cases57–58 add exact
fixture-boundary and digest controls. Cursor/Grok repairs deviations in the owning allowed module
or test helper before TEST PASS. Any necessary change to the selected semantics returns to
architecture; a missing future production artifact does not reopen this bounded contract.

#### 6.5.9 Exact component hash inventories

This section resolves B-DIGEST. Each hash is SHA-256 of §6.5.6's sorted canonical array
`{path,mode,sha256}` over the **exact set below**, with repository-relative POSIX paths. Missing,
duplicate, symlinked or additional component entries reject. Modes are actual four-octal-digit
artifact modes; bytes and modes are verified again when loading the corresponding artifact.

Define `CORE` as exactly these nine files (an import allowance, not an edit allowance):

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

Define `SCHEMAS_BC` as exactly the 24 Gate B plus 7 Gate C filenames in execution §2, never the
5 Gate W files, fixture-manifest schema or a filesystem glob. Exact component sets are:

| Digest field / fixture component name | Exact membership |
|---|---|
| `builder_tree_sha256` / `builder` | CORE ∪ SCHEMAS_BC ∪ `{strict_projection_publisher.py}` |
| `strict_server_tree_sha256` / `strict_server` | CORE ∪ SCHEMAS_BC ∪ `{openclaw_strict_server.py}` |
| `supervisor_tree_sha256` / `supervisor` | CORE ∪ SCHEMAS_BC ∪ `{openclaw_activation_supervisor.py}` |
| `controller_tree_sha256` / `controller` | CORE ∪ SCHEMAS_BC ∪ `{openclaw_activation_controller.py, openclaw_activation_supervisor.py}` |
| `plugin_tree_sha256` / `plugin` | `integrations/openclaw-convmem-reader/{package.json,openclaw.plugin.json,index.js}` only |

Set union is duplicate-free; braces expand only the explicitly named paths. Inclusion binds a file
even when a component uses only part of it; it does not grant private-file access or permission to
invoke another owner's behavior. Controller may reuse supervisor protocol parsing; the reader and
server never import publisher/controller/supervisor. Runtime component sets exclude the publisher.
Test adapters, test files, generated fixture outputs, governance, model bytes, caches and legacy
`mcp_server.py` are absent from these component hashes. The fixture manifest separately binds tests
and test runtime; Gate D's full image digest separately binds actual third-party/stdlib/loader
bytes. A package-name/version list alone is never a sealed-runtime attestation.

Only CORE/entrypoint imports and pinned dependencies are allowed; missing or extra local imported
files are a closure-test failure, not automatic transitive discovery. New local dependencies
require a reviewed inventory update. T0's independent implementation and reference walkers must
agree on exact sorted entries, canonical bytes and all five hashes. Mutating any included file or
mode must change every consuming component hash or reject validation; changing a test/output file
must not change component hashes. A mutant omitting `canonical_json.py` must fail case58 even if
both a mislabeled manifest and its incorrect digest agree. This restores an exact oracle, rather
than leaving an implementer to select a hash boundary.

## 7. Deep module boundary

Scope policy belongs in the new deep module `bound_read_scope.py`,
not in `mcp_server.py`.

The module owns:

- strict scope-file parsing and validation;
- project-binding registry validation;
- the omitted-selector sentinel;
- selector resolution;
- project membership proof;
- bound-projection manifest validation (public opening; private derivation is qualified separately);
- row authorization;
- related-chain authorization;
- public non-revealing denial payloads;
- private structured audit reasons.

A second new deep module, `strict_evidence_state.py`, owns the closed authority
record schema, canonical payload, logical/source-event/assertion identifiers,
approval-disposition validation, supersession graph, conservative verification
reducer, and public state fields. A third module,
`strict_projection_publisher.py`, is the fixture-only
authority-snapshot-to-projection path and owns exact manifests, immutable file
layout, compare-and-swap publication, and rollback. A fourth module,
`strict_projection.py`, owns cold validation, deterministic lexical search,
and the sealed read-only reader through the two §6.5.4 boundaries; it exports no publication or
generic write API. A fifth module, `openclaw_activation_supervisor.py`, owns
turn state, deadlines and buffered release inside the unit. A sixth module,
`openclaw_activation_controller.py`, owns slot enrollment, manager control, authenticated local
control, retirement attestation and lock ordering outside the unit. `strict_grounding.py` composes
unchanged legacy provenance verification with exact byte/receipt qualification. Gate W alone adds
`governed_admission.py` for authenticated intent/admission/recovery; it is never imported by the
reader. These responsibilities must not be reimplemented in
handlers, adapters, or the plugin.

The dedicated `openclaw_strict_server.py` owns only closed startup, the exact
three MCP method names, argument decoding, delegation, and serialization.
`mcp_server.py` changes only to reject `openclaw-strict` and unknown profiles;
it never serves the strict tools. Legacy query, unresolved, ledger, Chroma,
and file-generation modules are not imported by the strict executable.
`ledger_ids.py` and `agent_run_ledger.py` remain byte-compatible legacy APIs;
`strict_evidence_state.py` exclusively owns v2 IDs and qualified public-handle
syntax. The strict-scope module owns
`normalize_authority_site()`, the pinned authority-host algorithm used by the
registry and v2 site normalization. The dedicated projection builder owns
authority-snapshot-to-bound-file materialization; the separate reader owns
qualified access. The
strict-scope module owns
binding-scoped identity resolution and hands ledger traversal an already
authorized, unambiguous graph rather than a global index.

There must be one policy path shared by all three strict tools. A handler-local
check is not acceptable.

## 8. Tool contracts

### 8.1 `search`

Inputs are `query`, bounded `top_k`, optional project/site/domain selectors,
and optional `cross_domain`. Explicit project exists to test narrowing rules;
it cannot select another project.

The tool returns only rows authorized by the effective scope. Each row is
wrapped as untrusted evidence with a binding-qualified stable citation and no
executable fields:

```json
{
  "schema": "convmem.raw-evidence.v3",
  "instruction_authority": "none",
  "snapshot": {
    "snapshot_id": "...",
    "lineage_id": "...",
    "authority_seq": 1,
    "authority_manifest_sha256": "...",
    "semantic_contract_sha256": "...",
    "state_basis": "complete_bound_authority",
    "verification_basis": "recorded_qualified_checks",
    "as_of": "2026-09-20T00:00:00Z",
    "expires_at": "2026-09-21T00:00:00Z"
  },
  "selection_complete": true,
  "display_basis": "ranked_selection",
  "results": [
    {
      "title": "...",
      "document": "...",
      "ledger_id": "...",
      "citation_ref": "...",
      "record_kind": "observation",
      "logical_id": "find2_...",
      "authority_state": "current",
      "verification_state": "unverified",
      "verification_result": null,
      "target_ledger_id": null,
      "supersedes_ledger_ids": [],
      "origin_assurance": "untrusted",
      "provenance_qualification": {
        "commitments": "valid",
        "byte_grounding": "missing",
        "capture": "unattested",
        "transformer_cap": "agent"
      },
      "provenance_basis": "unattested",
      "check_eligibility": "not_applicable",
      "state_sha256": "...",
      "confidence_bps": 7000,
      "observed_at": "2026-09-20T00:00:00Z",
      "recorded_at": "2026-09-20T00:00:01Z",
      "decision_disposition_ref": null,
      "supersession_disposition_ref": null,
      "state_disposition_refs": [],
      "truncated": false,
      "domain": "...",
      "site": "..."
    }
  ]
}
```

The top-level success object contains exactly `schema`,
`instruction_authority`, `snapshot`, `selection_complete`, `display_basis`, and `results`;
`snapshot` contains exactly the fields shown. `selection_complete` is false whenever an otherwise
qualifying authorized row is omitted by top-k, limit or response bytes. `display_basis` is
`ranked_selection` for search/unresolved, `bounded_context` for related. Related's true completeness
means only its defined neighborhood; no response claims complete history or all possible real-world
checks. Each result contains exactly the
fields shown above. `truncated` is always present and is true only when the
document was cut at the Section 8.4 per-document bound. `target_ledger_id` and
every `supersedes_ledger_ids` element are qualified public handles derived from
same-binding assertion IDs. Kind-inapplicable values are explicit `null` or an
empty array.

The connector must return this as tool-result data. It must not concatenate the
document into a system, developer, skill, tool-description, or user message.
Absolute paths, environment values, workspace locations, registry contents,
source checkpoints, and private authorization reasons are excluded from the
public envelope. Every state field is emitted from the protected authority
snapshot/reducer, never from summary prose or ordinary metadata. Kind-specific
non-applicable fields are JSON `null`; omission is not allowed, so consumers do
not guess whether state was lost. A
`citation_ref` is an opaque, non-executable trace reference and is not accepted
as an input by any strict tool. In a strict response, `ledger_id` is not the raw
stored ID: it is the qualified public handle
`cm1.<public-binding-ref>.<external-id>`. The registry assigns each binding a
random, non-secret, immutable 128-bit lowercase-hex public reference. The
strict handle therefore names one identity across profiles without exposing a
project name or accepting a request-time scope selector. A row without a valid
stored external ID and binding reference has no public handle and cannot be
passed to `related()`. The envelope's `domain` and `site` fields are rendered
only from `authority_domain` and `authority_site`; legacy ordinary
`domain`/`site` metadata is never exposed as strict authorization context.

OpenClaw may summarize the returned data for its user, but no second model call
occurs inside ConvMem. Excluding `ask()` removes that additional synthesis and
prompt-injection surface; it does not pretend the orchestrating model performs
no synthesis.

### 8.2 `unresolved`

Inputs are an optional bounded `limit`, optional project/site/domain selectors,
and optional `cross_domain`. Omitted selectors inherit the bound scope. Domain
matching is hierarchical, not the current exact-string comparison. Strict unresolved reads the
canonical complete-bound state map (§6.5.3), applies its exact predicate and ordering, then applies
effective selectors, limit and byte cap. An excluded-by-selector verification still contributes to
canonical state because it belongs to the same already authorized bound history. Search and related
report exactly the same state/hash for the same assertion at the same authority head. Rows outside
the immutable audience never enter that graph. Empty or limited selections never establish that the
entire project is resolved. Results use the v3 envelope and completeness metadata.

### 8.3 `related`

Strict `related(ledger_id=...)` accepts only the binding-qualified public handle
returned by strict search or unresolved, never a bare stored ledger ID or raw
storage ID. `ledger_ids.py` remains the owner of legacy IDs;
`strict_evidence_state.py` exclusively owns v2 assertion IDs, strict
public-handle parsing, and the strict stored-ID validator. The strict
stored-ID validator uses
`re.fullmatch()` over this ASCII grammar plus a 160-code-point maximum, not
`match`, `search`, extraction, or an appended `$`:

```text
(?:(?:obs2|dec2|ver2)_[a-f0-9]{64}|(?:dec_prop|obs|dec|ver)_[A-Za-z0-9_.-]+)
```

The public-handle validator uses `re.fullmatch()` over
`cm1\.[a-f0-9]{32}\.(?:(?:obs2|dec2|ver2)_[a-f0-9]{64}|(?:dec_prop|obs|dec|ver)_[A-Za-z0-9_.-]+)`, enforces a
200-code-point maximum, and then validates the captured stored ID separately.
This is the syntax/length stage used by search. Only `related()` continues to
the authorization stage, where the public binding reference must equal an
allowed registry binding before any identity lookup. A handle copied from
another binding or profile therefore receives the generic denial even when the
same raw stored ID exists locally.

The existing `site_short()` and `observation_id()` functions are legacy-v1
identity APIs. Gate B leaves their output byte-for-byte unchanged for
`monitor.py`, full/shell behavior, existing ledger references, and
`tests/test_milestone_c.py`; those writers do not become registry-authorized
merely because the validator is centralized. A new `finding_id_v2()` generator
creates the continuing `find2_` logical ID, and `assertion_id_v2()` creates
immutable `obs2_`, `dec2_`, or `ver2_` assertion IDs exactly as Section 6.5
defines. Each v2 assertion ID is a kind prefix plus 64 lowercase hex digits and
is lexically disjoint from legacy-v1 IDs. Strict kind parsing maps the three v2
prefixes to their record kinds.
Switching any live writer, including the monitor, to v2 requires
a separate Ryan-granted ledger-ID migration with continuity, collision, and
rollback evidence.

Every strict-v2 ID generator calls its centralized full-string validator before
returning. Logical-ID digest inputs use `normalize_authority_site()` with pinned UTS
#46 non-transitional processing, IDNA2008 semantics, and STD3 rules; Python's
standard-library IDNA2003 codec is forbidden. Gate B pins the exact third-party
`idna` package version and records it in the reviewed dependency/artifact
digest set. Ports, user info, paths, empty labels, underscores anywhere, and
invalid IDNA are rejected before minting. Tests pin sharp-s, fullwidth, and
underscore vectors for the v2 path while retaining legacy-v1 vectors unchanged.

The logical key, source event, and assertion digest inputs are length-prefixed
canonical UTF-8 fields; concatenated free text is forbidden. No authorization
decision parses site identity back out of an ID; protected metadata remains
authoritative. A strict-v2 ID generator that cannot produce a valid ID fails the
entire authority snapshot with the operator-visible reason
`ledger_id_mint_denied`; this read-only slice creates no mutable quarantine.
It must never substitute a UUID, truncate without a digest, or silently skip
the item. Existing legacy IDs that already satisfy the strict grammar may be
qualified only after the separately reviewed binding-materialization migration;
invalid legacy IDs fail closed until a separately reviewed ID migration exists.

`agent_run_ledger.py` already performs full-string validation at an integrity
boundary and remains byte-unchanged. Its legacy validator is not a strict
authorization API. The regexes in `query.py` and `cross_project_digest.py` are
extraction helpers only; strict search disables the former, and the latter's
narrower shape is a known non-authoritative recall limitation. Strict input
validation rejects Unicode confusables, whitespace, slashes, colons, missing
suffixes, embedded IDs, trailing text, and values longer than the bound below.

Every strict authority record validates its assertion ID and every non-empty
relation with `strict_evidence_state.py` before authority-generation
publication. Legacy writers remain unchanged and outside strict authority until
their own migration. Strict identity is `(project binding, assertion_id)`;
`logical_id` groups assertions but is never a lookup overwrite key.
`provenance_identity()` is not the payload-integrity or retry predicate. Exact
retry, changed-payload conflict,
fresh-observation admission, and relation resolution follow Section 6.5. A
relation must resolve unambiguously inside the same binding or materialization
fails. Cross-binding assertion-ID reuse is allowed because the public handle
carries the binding reference.

Strict lookup never consults the current global last-write-wins map or metadata
outside the named bound projection. It first validates the public handle and
resolves its public binding reference against the scope's single allowed
registry entry, then builds a binding-scoped multimap from the captured stored
external ID to all matching rows. Zero matches returns the
generic denial; more than one match is an integrity failure with the same
public denial; exactly one becomes the candidate target. Traversal and every
`relates_to` edge stay inside that same project-binding graph, so a row in
another binding with the same stored ID is a different identity, not a child
or overwrite. Registry startup guarantees that the binding's project, domain
root, and exact-site policy equal the bound profile, and trusted ingest forbids
a row domain outside that root. Only after the complete normative target
neighborhood below is collected does the authorizer check every collected node
against the effective site and domain scope. A node excluded only by a
caller-chosen descendant narrowing is already inside the caller's immutable
authority and may cause a whole-neighborhood denial without revealing
unauthorized evidence. Duplicate identities, ambiguous edges, malformed
metadata, or any node that fails those checks deny the whole neighborhood.

The normative neighborhood is directional and bounded; it is not the record's
whole undirected connected component:

1. Follow the target's unique parent `relates_to` path for at most eight hops,
   stopping at the first observation or at a registry-declared non-expanding
   root. A cycle, ambiguous parent, missing required parent, or ninth hop denies.
2. Collect the target's descendant subtree to depth two, across every record
   kind. This includes a verification attached to a target decision.
3. If step 1 found an observation anchor, collect that observation's descendant
   subtree to depth two, including sibling decisions, direct verifications,
   verifications attached to decisions, and any malformed/unknown kind causes denial. This step does not
   run when that observation is also a registered non-expanding root.
4. If step 1 found a non-expanding root, include that root as lineage context
   but never enumerate its other children. Non-expanding-root status takes
   precedence over observation-anchor status: a node that is both is governed
   by this step, not step 3. The production registry's immutable
   `non_expanding_roots` list contains the installed protocol fallback
   `dec_prop_20260623_161428_c311` after materialization proves that it resolves;
   hermetic and synthetic deployments use only their own declared fixture
   roots. Request or corpus text cannot add a root.

5. Add every live competing head of the explicitly queried target's logical identity. For each
   observation/decision in that queried head set, add all its live `targets` verification heads,
   including conflicting and ineligible heads. These support additions do not recursively expand
   `relates_to` context. A non-expanding root cannot suppress this support for an explicitly queried
   target. Other context rows carry canonical state without promising a complete explanation of each
   of their checks.

Traversal uses a visited set and collects no more than 200 nodes across the entire union. The complete
neighborhood either passes authorization and renders or receives the generic
denial; it is never silently truncated. Because sibling expansion occurs only
under an observation anchor, the protocol fallback may have arbitrarily many
unrelated children without making a target's neighborhood unavailable. A
one-level-only implementation remains noncompliant because target descendants
and observation descendants must reach depth two.

Every collected node must pass the bound project/site/domain policy. If any
node is outside scope, has missing proof, has malformed metadata, or cannot be
resolved, the public response is the same generic denial:

```json
{
  "schema": "convmem.error.v1",
  "error": {
    "code": "scope_denied",
    "message": "The requested evidence chain is unavailable in this scope."
  },
  "correlation_id": "00000000000000000000000000000000"
}
```

The example correlation ID is illustrative; each real response uses §11’s fresh random ID. Denial
equivalence compares the fixed schema/code/message after removing this independent ID, never its
random bytes.

Unknown IDs, malformed IDs, and out-of-scope IDs are deliberately
indistinguishable. The response contains no IDs, titles, counts, chain shape,
scope values, or reason detail. Private logs may record a reason enum and a
request correlation ID, but never corpus document text. Gate D must prove that
an operator can use that correlation ID to distinguish at least unknown,
malformed, wrong-binding, ambiguous-identity, and out-of-effective-scope
failures without exposing the private reason to OpenClaw. A binding/site/domain
registry mismatch is a startup failure, so ordinary writes from a different
exact site or domain authority cannot silently poison a live chain.

No partial normative neighborhood is returned. Authorization of the union precedes the v3 formatter;
canonical state was already reduced over complete bound authority and is never recomputed from this
union. A hidden support node cannot turn conflict into pass. The operator's private file/CLI audit
can inspect the complete history and qualification witnesses.

### 8.4 Request and response bounds

The strict profile rejects, rather than silently widens or coerces, inputs
outside these initial bounds:

- UTF-8 query text: 1–2,048 Unicode code points;
- `search.top_k`: integer 1–10;
- `unresolved.limit`: integer 1–50, default 20;
- stored ledger ID: centralized grammar and at most 160 code points;
- strict public ledger handle: qualified grammar and at most 200 code points;
- related normative neighborhood: at most 200 collected nodes before rendering;
- one evidence document: at most 4,096 code points with an explicit
  `truncated: true` marker;
- one serialized tool response: at most 64 KiB.

Oversized or wrong-typed requests fail before retrieval. A required related neighborhood that
exceeds its bound receives the same non-revealing public denial as other
unavailable chains. Response construction applies per-document truncation
first. For search and unresolved, it serializes authorized rows in rank order
and stops before the 64-KiB UTF-8 byte cap. The byte cap therefore overrides
`top_k`/`limit` and may return fewer authorized rows; that reduction depends
only on in-scope content. Related never truncates a chain: if the complete
authorized component does not fit, it returns the same generic denial. A single
search/unresolved row that cannot fit after document truncation is an explicit
response-too-large failure. The connector
has a fixed timeout and output cap at least as strict as the server; transport
timeout or connector-side truncation is a failure, never success.

## 9. OpenClaw isolation profile

The integration uses a dedicated OpenClaw named profile and state directory.
It does not modify the default OpenClaw profile.

One profile maps to exactly one immutable ConvMem bound scope and one approved
audience policy. Request text, channel identity, sender identity, and group
identity cannot choose another scope file or profile. A second project, site,
or trust zone requires a separate profile/process and a new review.

Normative settings for Phase 1A and Phase 1B are:

```json5
{
  env: { shellEnv: { enabled: false } },
  logging: { file: "/activation/tmp/openclaw.log" },
  agents: {
    defaults: {
      workspace: "/operator/provisioned/empty-openclaw-convmem-workspace",
      skipBootstrap: true,
      heartbeat: { every: "0m" },
      compaction: {
        memoryFlush: { enabled: false }
      }
    }
  },
  skills: {
    allowBundled: [],
    load: { extraDirs: [], watch: false }
  },
  plugins: {
    enabled: true,
    slots: { memory: "none" },
    allow: ["convmem-reader"],
    deny: [],
    load: {
      paths: ["/operator/provisioned/convmem-reader"]
    },
    entries: {
      "convmem-reader": {
        enabled: true,
        config: {
          launchManifest: "/operator/provisioned/connector-launch.json"
        }
      }
    }
  },
  hooks: {
    enabled: false,
    internal: { enabled: false }
  },
  tools: {
    profile: "minimal",
    allow: ["convmem_search", "convmem_unresolved", "convmem_related"],
    deny: [
      "session_status",
      "group:openclaw",
      "group:runtime",
      "group:fs",
      "group:sessions",
      "group:memory",
      "group:web",
      "group:ui",
      "group:automation",
      "group:messaging",
      "group:nodes"
    ]
  },
  acp: { enabled: false, dispatch: { enabled: false } },
  discovery: {
    mdns: { mode: "off" },
    wideArea: { enabled: false }
  },
  gateway: {
    mode: "local",
    bind: "loopback",
    auth: {
      mode: "token",
      allowTailscale: false,
      rateLimit: {
        maxAttempts: 10,
        windowMs: 60000,
        lockoutMs: 300000,
        exemptLoopback: false
      }
    },
    tailscale: { mode: "off", resetOnExit: false },
    controlUi: { enabled: false }
  }
}
```

The final config must be validated against the installed `2026.3.2` schema.
If any key is rejected, renamed, ignored, or normalized to a wider value, stop
rather than substituting a guessed setting. The placeholder workspace path
and connector path above must each become one exact operator-approved absolute
path before activation.

Disabling `plugins.slots.memory` is not accepted as disabling automatic memory
behavior. `agents.defaults.compaction.memoryFlush.enabled` is independently
false, and `agents.defaults.heartbeat.every` is exactly `"0m"`. The effective
config must show both values after normalization and must contain no per-agent
override that re-enables either route. Compaction-threshold, long-transcript,
timer, restart, and per-agent-override probes must produce zero silent flush or
heartbeat agent turns. Tool absence alone is not proof because both mechanisms
can schedule model turns before tool invocation.

Each activation supplies a new absolute `OPENCLAW_STATE_DIR` whose basename
includes the projection `snapshot_id`. It contains only the reviewed config and
fresh session structures, never credentials or a copied session database.
`OPENCLAW_CONFIG_PATH` is fixed inside that directory. A profile/state directory
whose embedded activation manifest does not match the current scope, registry,
authority, projection, plugin, and OpenClaw digests fails before the gateway
starts. Session reset, archive, or compaction files from an earlier activation
are never accepted as input.

The dedicated workspace starts empty and is not a project checkout. It contains
no bootstrap files, `skills/`, `.openclaw/extensions/`, memory files, hooks, or
instructions. Both HTTP/automation hooks and internal lifecycle hooks are
disabled. The connector plugin declares tools only and ships no skill, hook, or
prompt content. `allowBundled: []` filters only bundled skills, so it is not
sufficient by itself: the dedicated profile's managed/local skill and hook
directories must also be empty, no extra skill or hook directory may be
configured, and the actual new-session prompt/eligible-skill/hook inventory
must prove that zero loaded. The watcher is disabled to prevent a mid-session
filesystem-triggered skill refresh.

The installed version has a second mid-session refresh trigger when a newly
eligible remote node appears. The isolated profile starts with no paired or
connected nodes and accepts no node pairing. Gate D records an empty node
inventory before and after the hostile-content test. If any node connects or
the eligible-skill snapshot changes, the session stops and fails; disabling
the watcher alone is not accepted as proof.

The dedicated profile's managed extension directory is also empty. The single
connector is loaded only from the approved absolute path, and activation pins
and records the reviewed artifact digest. Plugin discovery, resolved path,
manifest, tool declarations, bundled content, and digest are inspected from the
running profile; a same-ID plugin from another path is a gate failure.

The tool, plugin, skill, workspace-bootstrap, hook, and prompt-source inventories
must be inspected from the actual child agent session, not inferred from the
config file. Exactly the three ConvMem plugin tools may reach the model and no
skill or workspace instruction may be injected. OpenClaw `memory_search`,
`memory_get`, `exec`, filesystem, browser, sessions, messaging, cron, gateway,
node, and ACP tools must be absent.

`group:openclaw` denies all built-in tools, including present or future tools
outside the nine named groups. The named group denies remain readable defense
in depth, but neither list is accepted as proof: the exact effective runtime
inventory is the authority and must still contain only the three plugin tools.

ACP remains disabled through Phase 1B. A future ACP phase requires a new plan
because ACP workers run on the host and may inherit harness-specific MCP,
plugin, skill, memory, and filesystem surfaces. The required initial ACP test
is therefore a negative control: attempts to spawn or route an ACP session must
fail closed and must not create a child session. If any child session appears,
inspect its complete plugin, native-memory, skill, prompt, and tool inventory
and return FAIL; its mere existence already fails this phase.

The installed default `sessions_spawn` runtime is `subagent`, not ACP, and is a
separate child-session route. `group:sessions`, `group:openclaw`, and the
effective runtime inventory must make `sessions_spawn` absent. Natural-language
and slash-command attempts to launch either a subagent or ACP child must fail
without producing a session. Disabling `acp.enabled` or
`acp.dispatch.enabled` is not accepted as proof that subagents are absent.

### 9.1 Model-provider and network boundary

The selected profile has no external channels and no host-network inference in Phase 1A or Phase 1B.
Use one private network namespace with loopback only and no external interfaces/routes, containing
gateway, client and a dedicated CPU local model worker in the same systemd retirement domain. No
host Ollama socket, shared host model daemon, proxy, model download, fallback, or cloud endpoint is
reachable. The strict child additionally has §4's pre-import socket denial. Connector transport
remains stdio.

The exact config must select one packaged model, `models.mode: "replace"`, the bundled
`openai-completions` adapter, no fallback and no inherited models/auth files. It must work without a
provider credential or dummy placeholder; the gateway's private activation token is a separate local
transport credential. **This combination is not qualified on OpenClaw 2026.3.2:** §14.2 establishes
a concrete authentication-path conflict. Do not fill in a fake key, loosen the environment, switch
provider/runtime, or introduce an auth proxy during implementation. A reviewed compatible route or
explicit architecture decision is required. Config schema acceptance alone would not close this
blocker.

The configuration example above specifies disabling controls, not a launchable final config. All
paths are replaced by exact namespace paths and the complete closed launch-policy bytes before
qualification. No per-agent/env override may widen it. Private
CWD/HOME/TMPDIR/workspace/cache/session/log directories and immutable imports close documented
`.env` and discovery routes; a fresh state directory alone is insufficient. Actual child inventories
and negative egress/write tests remain required.

Phase 1B stays local operator only. Channels, hosted inference and remote workers require another
reviewed architecture with privacy, retention, sender and delivery semantics; this candidate does
not open endpoints later as a config convenience.

## 10. Prompt-injection boundary

Corpus content is adversarial data. The following are mandatory:

1. Tool descriptions state that result content has no instruction authority.
2. The connector preserves the `instruction_authority: "none"` marker.
3. Corpus content is returned only in tool-result content blocks.
4. The connector never evaluates Markdown links, shell fragments, JSON tool
   requests, XML tool syntax, or embedded role labels from the corpus.
5. The OpenClaw agent has no write/runtime/browser/session tools that hostile
   evidence could invoke in Phase 1A or Phase 1B.
6. A hostile-evidence fixture instructing the model to widen scope, call a
   hidden tool, modify memory, disclose another project, or claim completion
   must produce no such action.

This does not claim prompt injection is solved generally. It makes the initial
failure consequence small by removing consequential tools and durable memory.

## 11. Synchronous completion contract

Phase 1A and Phase 1B contain no autonomous background task or ACP delegation. The contained model
worker serves only supervised local inference and owns no durable memory or independent task queue.
Each
connector call is synchronous and has one request correlation ID.

The only terminal outcomes are `succeeded`, `denied`, `failed`, and
`interrupted`. `accepted` and `running` are non-terminal. A connector call may report successful
transport only after a complete valid MCP response is received and serialized. A model answer may be
released only through §6.5.6's complete-result commit. Neither transport success nor arbitrary model
JSON proves that a tool ran, a fact is true or a deployment completed; model results are
`model_output_unverified`. Process exit, timeout, broken stdio, gateway restart,
or cancellation before that point is `interrupted` or `failed`, never
`succeeded`.

No connector completion state is written to ConvMem, OpenClaw memory, or a new
durable ledger. Retrying after interruption creates a new request ID. This prevents the adapter from
attesting background completion; arbitrary model assertions remain untrusted and cannot create a
completion receipt.

The connector uses one long-lived strict child per activation, permits one
in-flight request, and queues at most eight additional requests FIFO. A ninth
request receives `temporarily_unavailable` without reaching retrieval. Each
request has a ten-second end-to-end deadline and a 128-KiB MCP frame limit; the
server response remains capped at 64 KiB. Cancellation propagates to the active
MCP request and discards any late response. The connector never automatically
retries a timed-out, cancelled, malformed, oversized, or transport-failed call.
Startup failure, child exit, protocol desynchronization, or a snapshot-expiry
response terminates the activation and requires a fresh child; it never falls
back to another ConvMem profile.

The complete public MCP error vocabulary is closed (activation-control outcomes are the separate
§6.5.6 protocol):
`invalid_request`, `identifier_query_not_supported`, `scope_denied`,
`snapshot_stale`, `response_too_large`, `temporarily_unavailable`, and
`internal_failure`. The schema literal is `convmem.error.v1`; its top level
contains exactly `schema`, `error`, and `correlation_id`, and `error` contains
exactly `code` and `message`. Messages are respectively: `The request is
invalid.`, `Ledger handles are not supported in search.`, `The requested
evidence chain is unavailable in this scope.`, `The evidence snapshot is
unavailable.`, `The evidence response exceeds the allowed size.`, `The
evidence service is temporarily unavailable.`, and `The evidence service
failed.` `correlation_id` is a fresh 32-character lowercase hexadecimal
128-bit random value generated before argument validation and has no semantic
content. Private reason enums may add
diagnostic specificity but never corpus text, request text, filesystem paths,
scope values, or credentials.

## 12. Phase gates

### Gate A — plan review

BUILD asks whether the frozen T0–T5 implementation requires any architectural choice: this packet
answers PASS after the B-FIXTURE/B-DIGEST corrections. Bounded TEST passed at accepted historical
tip `8010fb060c2edc29e1b09d7a30b1a1da2689d489`; that result does not certify the proposed M11
current-main integration, whose replay/pin state is preserved at `a11b7a2` but whose fresh evidence
has not run. LIVE-DATA and PROMOTION are
BLOCKED. These gates are independent; BUILD/fixture TEST PASS is neither runtime qualification nor
an Execute or merge grant. Kiro reviews the exact reconciled plan; Ryan separately decides M11.
A substantive correction receives a focused fresh adversarial check of the changed contracts, not
a reopened general design search.

### Gate B — strict ConvMem contract implementation

After a Ryan Execute grant, Cursor implements only:

- the deep bound-scope module;
- the strict evidence-state and strict-projection modules;
- the fixture-only strict projection publisher CLI;
- fail-closed profile parsing;
- the exact three-tool strict profile;
- empty resources and templates;
- the registry-owned project-binding mechanism and hermetic fixture
  materializer;
- registry-owned source authorization domains separated from model-derived
  semantic domains;
- strict-only site normalization and versioned strict ID generation that leave
  legacy full/shell and monitor identity unchanged;
- immutable canonical file projections for each bound-scope manifest;
- versioned strict logical/source-event/assertion IDs that preserve legacy-v1,
  payload-bound exact replay, fresh-observation admission, binding-qualified
  public handles, and ambiguity-denying lookup;
- operator-enrolled cumulative fixture authority/disposition history, original-admission
  qualification, byte grounding, complete-bound state reduction, fenced atomic publication, crash
  recovery, and serving-only rollback;
- deterministic lexical strict search with no ledger-ID extraction, embedding,
  reranking, model, Chroma, or fallback path;
- one canonical state map shared by all tools and bounded related display with explicit verification support;
- focused hermetic tests.

No live-corpus binding migration, OpenClaw plugin, or OpenClaw configuration is
included in this gate.

### Gate C — connector implementation

After Gate B review passes, Cursor may implement the fixed local OpenClaw
connector plugin, external controller and in-unit supervisor in the repository with hermetic
fake-manager, fake-MCP, fake-gateway, fake-model-worker and fake-agent tests. No mock can qualify
actual containment, credentials or tool inventory. It may not
install or enable the plugin, create a live OpenClaw profile, or contact an
external channel.

The implementations are §6.5.8's pure cores and validators with test-only injected ports. Production
launch adapters are not implemented/enabled in this slice. Case57 must prove that distinction and
case58 must prove the exact component inventories. No OpenClaw authentication path is selected by
the fake agent/model roles.

### Gate D — Phase 1A isolated smoke

Requires closure of §18's runtime architecture/qualification blockers, Kiro conformance PASS on the
Gate B/C implementation, exact reviewed runtime/model image and manager/launch policy bytes, and a
separate Ryan grant naming the unit/profile/config. Installed package inspection is not launch
authorization.

- local operator only;
- loopback/local stdio only;
- synthetic strict fixture projection and reviewed local inference only;
- exact reviewed scope file;
- exact reviewed project-binding registry and child-environment allowlist;
- no external channels;
- native memory disabled;
- ACP disabled;
- exact three-tool inventory;
- zero eligible skills, workspace instructions, and plugin prompts;
- zero paired or connected remote nodes before and after the session;
- no resources;
- no transcript capture;
- no ConvMem writes;
- a fresh snapshot-bound `OPENCLAW_STATE_DIR`, with memory flush and heartbeat
  independently disabled and no resumable prior session.
- the operator-only controller and reviewed supervisor as the only user-facing local entrypoint;
  OpenClaw `--deliver`, direct gateway UI, channels, and streaming output stay
  disabled.

The first smoke uses an isolated synthetic strict file projection whose project
bindings were assigned through the reviewed fixture materializer. It proves
transport and denial
behavior, not live-corpus readiness, channel safety, or capture safety. A smoke
against the live corpus remains blocked until Ryan separately authorizes and
reviews project-binding materialization or rebuild evidence.

### Gate D-V — incremental-value experiment

After the isolated smoke passes, a separately cost-authorized experiment uses
the same frozen OpenClaw runtime with ConvMem off versus on. Ordinary files,
GitHub snapshot, handoff, prompts, tools, permissions, model/version/tier,
cache/session state, tasks, and budgets are identical; successor agents receive
no predecessor transcript. The predeclared screen is eight representative web
tasks, two fresh repetitions, and two arms (32 runs) in the ecological fixture
condition, preceded by a smaller isolation leakage check. Blind grading covers
current-state accuracy, decision consistency, useful patch/content quality,
rework, time/tokens/tool calls, accessibility, performance, security,
SEO/schema, and website substance. Owner minutes include briefing plus ConvMem
curation, registration, rebuild, session hygiene, and recovery.

The experiment must predeclare minimum practical effects, stopping rules,
failure handling, and the treatment of safety failures before results exist.
Recall or API success alone cannot pass. A null or harmful result blocks claims
of incremental value and blocks Phase 1B promotion, but does not retroactively
invalidate a safe disposable reader prototype. This plan does not authorize the
model runs or claim that value has been demonstrated.

### Gate W — governed production write boundary (separate slice)

Required before any production lineage enrollment. Implement §6.5.7's one governed engine, literal
separate approval/add route, explicit legacy refusal, prefix protection and recovery ordering. Apply
§14.3's caller mapping; preserve all existing production writer/backup/recovery safeguards. Gate B/C
do not modify those legacy files. Gate W's exact baseline, allowlist and acceptance plan need a
separate reviewed packet and Ryan grant; no production source resolver, old-consent migration,
capture recorder or live data is granted here. The semantic contract is fixed here; an execution
packet must instantiate it rather than make these choices anew.

### Gate E — Phase 1B scoped normal operation

Requires Gate W, qualified source/capture/enrollment artifacts, separately reviewed live-data
completeness and latest-history recovery evidence, fresh Kiro review and Ryan approval after all
assigned adversarial tests, plus a positive independently graded Gate D-V result. It remains local
operator only under the same containment and release rules. ACP, background workers, transcript
capture, automatic indexing and OpenClaw memory remain disabled. External sender/channel support is
outside this candidate and requires a new delivery/perimeter design.

### Gate F — later capabilities

ACP worker routing, synthesized `ask()`, background work, and transcript
capture are separate architecture phases. None is an incremental config toggle
under this plan.

Transcript capture requires a new ingest-owned quarantine primitive,
ledger-first ordering, append/replay idempotence, bounded retry, poison-source
isolation, and hash-plus-offset completeness. Serving or recovery quarantine is
not sufficient.

## 13. Required adversarial test matrix

The implementation is FAIL if any test leaks data, widens authority, exposes an
unexpected surface, or reports false completion.

Phase ownership is normative. Gate B owns cases 1–27, 40–44, 49–52 and the strict-server portion of case 47.
Gate B also owns case55's private/public qualification boundary; Gate C owns its fake pre-activation repetition. Gate C owns fake-process portions of 33, 35, 45, 46, 48 and 53–54; Gate W owns 56. Every case
may have multiple explicitly named layers, not an ambiguous single gate. Those fake tests do not
satisfy runtime acceptance.
Gate D repeats cases 1–4 against the installed child and owns cases 28–36,
38–39, 45–47 and 53–55 against the actual isolated runtime. Gate E alone owns case 37.
Gate B/C also own their respective preflight/fixture and component-inventory portions of cases57–58.
No Gate B/C handoff may claim all 58 passed; it reports only its assigned
cases, and every later case remains a blocking future gate.

### Profile and enumeration

1. Enumerate `tools/list`, `resources/list`, and resource templates from the
   strict MCP server and from the actual OpenClaw child agent session.
2. Assert exactly `search`, `unresolved`, and `related` on MCP and exactly their
   three connector aliases in OpenClaw.
3. Assert `ask`, `search_fast`, `brief`, `folder_state`, `stats`, all resources,
   and all write-capable tools are absent.
4. Set an unknown `CONVMEM_MCP_PROFILE` and prove startup fails rather than
   loading `full`.

### Selector resolution

5. Omit project/site/domain and prove inheritance returns eligible results.
6. Pass explicit `null`, blank, and whitespace selectors and prove denial while
   the same calls with absent keys inherit scope and return eligible fixtures.
7. Request the bound domain and an allowed descendant domain.
8. Request a parent, sibling, malformed, and `general` widening domain.
9. Set `cross_domain=true` on both selector-bearing tools and prove denial.
10. Request case, Unicode/A-label, and terminal-dot variants of one valid site
    and prove canonical equality. Request another hostname, a port, scheme,
    user-info, path, underscore, and invalid-IDNA form and prove denial. Prove
    legacy `site_filter.normalize_site()` and its URL/path regression tests are
    unchanged and never invoked by strict authorization.
11. Request another project and a prefix/suffix/case-confusable project.

### Project and row proof

12. Authorize rows only when the strict fixture materializer assigned a binding that is
    allowed by the immutable scope and resolves to the bound canonical project.
    Prove schema v2 rejects zero or multiple `allowed_project_bindings`.
13. Forge matching `project`, `domain`, `site`, bare or prefixed
    `_convmem_auth`/`_convmem_state`, authority/disposition digests,
    `project_binding_id`, `workspace_directory`, and `source_path` inside every
    fixture-source location. Prove the strict parser rejects the complete batch
    before trusted construction. Also put an allowed descendant domain in
    hostile source text and prove authority domain stays the registration's
    value. Prove unregistered/differently bound sources cannot self-label into
    the projection and partial, unknown, stale, conflicting, cross-project, or
    row-domain-outside-binding authority fails. Prove no legacy ingest,
    adapter, Chroma, restore, mixed-mode, eval, or file-generation module is
    imported or written by Gate B.
14. Prove legacy rows without a service-owned binding reduce recall rather than
    leak, and prove Gate B never backfills the live corpus.
15. Prove strict site filtering rejects source-path-only site inference.
16. Build a physical projection from an open domain taxonomy and prove search,
    unresolved, related, deterministic lexical ranking, and graph construction
    read only that exact projection, with no fallback.
    Add or remove rows outside the immutable bound scope and prove its
    included-row content digest and each tool's query cost, process cache,
    response shape, count, and order do not change. Include an unknown but registry-authorized descendant
    domain and prove it is included by rebuild without an enumerated `$in`
    list. Prove strict mode never imports/calls `_fetch_scoped_units()`, an
    embedder, reranker, Chroma, `build_ledger_index()`, or any wider store. Pin
    tokenizer and integer-ranking known-answer vectors and prove the projection
    opens on a read-only mount without creating any file. Prove the server and
    reader import graphs exclude `strict_projection_publisher.py`.
    Separately prove an explicit descendant selector may narrow results only
    inside the already authorized projection.

### Cross-surface oracle resistance

17. Put syntax-valid qualified handles containing an allowed, disallowed, and
    unknown public binding reference in otherwise identical
    whitespace-delimited search text. Prove the grammar/length stage gives all
    three the identical fixed `identifier_query_not_supported` code/message (with a fresh
    independent correlation ID)
    before binding lookup, tokenization, or scoring and that neither ledger extraction nor
    priority injection runs.
    Prove malformed/punctuation-wrapped strings receive no lookup treatment,
    and `server_name`, `codec_config`, and `observer_pattern` are not rejected.
18. Keep the same complete authorized authority head; move a pass or fail check outside an
    observation's selected descendant domain, lexical top-k, limit and displayed related depth.
    Across search/unresolved/related, prove the observation retains the same canonical state/hash:
    pass+fail remains conflict, pass+inconclusive remains inconclusive, and an ineligible live check
    contributes inconclusive. A related response requiring excluded support denies as a whole.
    Out-of-immutable-audience rows remain absent and cannot affect state. The former test that
    deleted the narrowed-out check is explicitly replaced.

### Project selectors and resources

19. Attempt another project through `brief`, `folder_state`,
    `memories://brief/{project}`, and `memory://brief/{project}`. Prove the
    surfaces are absent in strict mode.
20. Call `resources/read` directly with both aliases, another project, URI
    encoding, and malformed URIs; prove strict mode resolves none and reveals no
    project information.

### Ledger identity and related-chain authorization

21. Property-test every strict-v2 ID generator against the centralized
    `re.fullmatch` and length validator. Prove canonical length-prefixed digest
    inputs separate field boundaries and that `find2_`, `choice2_`, `check2_`,
    `evt_`, `obs2_`, `dec2_`, and `ver2_` are deterministic and kind-disjoint. Use full
    multi-label hosts, two hosts sharing the same first label, `www.*`,
    single-label hosts, ports, user info, paths, empty labels, trailing
    newlines, confusables, and maximum length. Pin UTS
    #46 non-transitional/IDNA2008 vectors for `straße`, `strasse`, fullwidth
    characters, underscores in any label position, and long legal hostnames.
    Prove generator failure aborts with
    `ledger_id_mint_denied` rather than a UUID fallback or partial generation.
    Separately prove legacy
    `site_short()`/`observation_id()`, `monitor.py`, `agent_run_ledger.py`, and
    `tests/test_milestone_c.py` remain byte-compatible and that live writers
    cannot select v2 without the later migration grant.
22. On the registry-aware authority path, reject malformed IDs and relations,
    a reused source event/assertion with changed canonical payload, a changed
    source registration, and an ambiguous relation. Replay the exact preserved
    source event, assertion, payload, and registration and prove it is a no-op;
    then admit a distinct later source event under the same logical ID.
    Prove the existing `agent_run_ledger` integrity check remains unchanged and
    cross-binding stored-ID reuse yields distinct qualified public handles.
23. Using two separate single-binding profiles, build stored-ID reuse across
    bindings. Within one `site_mode=not_applicable` binding, use two source
    registrations representing different sites and prove their source
    identities keep valid IDs distinct; then force a duplicate assertion ID
    with different bytes and prove the snapshot fails. Prove strict lookup validates the
    public binding reference before identity resolution, resolves one
    authorized row, and gives the generic denial for more than one authorized
    match—never last-write-wins. Paste a valid qualified handle from binding A
    into a binding-B profile and prove generic denial even when B contains the
    same stored external ID.
24. Retrieve a fully in-scope, unambiguous normative neighborhood, including a
    verification attached to a decision at depth two and sibling decisions
    beneath an observation anchor. Prove cycles, an ancestor path beyond eight
    hops, or a required neighborhood beyond 200 nodes receive generic denial.
    Add more than 200 unrelated children to the registered protocol fallback
    and prove a target below that non-expanding root still returns its useful
    lineage plus target descendants without enumerating the hub. Separately
    register a high-degree observation as a non-expanding root and prove its
    target still returns useful lineage and target descendants without running
    observation-anchor expansion. Prove an empty root list starts successfully
    in a fixture that contains no high-degree protocol anchor.
25. Request an out-of-scope, unknown, malformed, embedded, trailing-text, and
    raw storage ID; prove equivalent public denial shapes after removing the independent correlation ID.
26. Put one out-of-effective-scope decision, verification, sibling,
    unknown-kind child, or metadata-incomplete node behind an in-scope target;
    prove the entire chain is denied without partial output. Prove registry
    startup rejects an exact-site binding spanning two sites or a binding whose
    domain root differs from the profile bound, and prove strict materialization plus
    rebuild reject a row whose protected domain lies outside its binding root.
    Prove startup rejects a scope containing two otherwise valid bindings and
    a missing, ambiguous, or cross-binding non-expanding root.
27. Prove authorization occurs before formatting and private audit output does
    not contain corpus text. Using only a correlation ID, prove the operator can
    distinguish unknown, malformed, wrong-binding, ambiguous-identity, and
    out-of-effective-scope reasons while OpenClaw receives the same denial.

### OpenClaw isolation and hostile evidence

28. Validate the exact `2026.3.2` config and inspect effective tool, plugin,
    skill, hook, bootstrap, workspace, and prompt-source inventories in a new
    session.
29. Prove `memory-core`, `memory_search`, `memory_get`, automatic memory flush,
    filesystem, runtime, browser, session, messaging, cron, gateway, and node
    tools are absent. Prove the ungrouped built-in `image` tool is absent and
    `group:openclaw` does not suppress the three explicitly allowed plugin
    tools.
30. Record an empty paired/connected-node inventory, attempt a node connection,
    and re-inspect the eligible-skill snapshot. Any node or new skill fails the
    gate even though the skill watcher is disabled.
31. Attempt ACP and default-runtime `sessions_spawn`/subagent creation through
    natural language, slash commands, and tool calls; prove no child session is
    created and verify both `acp.enabled` and `acp.dispatch.enabled` are false.
32. Retrieve hostile corpus content containing tool calls, role labels, scope
    overrides, memory instructions, and false-completion claims. Prove it stays
    inside the untrusted result envelope and causes no action.
33. Attempt command, argv, cwd, environment, config-path, registry-path, and
    scope-file injection through every connector input. Start the parent with
    hostile legacy and unrelated variables; prove the child receives exactly
    the closed environment schema and strict mode ignores both legacy read-scope
    variables.
34. Inspect the effective model/provider route, disable fallback, deny general
    egress, and prove synthetic evidence never reaches a remote model or
    unapproved endpoint.

### Interruption and perimeter

35. Kill the ConvMem child before response, during response, and after response
    receipt but before outer serialization; only the last fully serialized path
    may succeed.
36. Restart the OpenClaw gateway during a call and prove no persisted false
    completion or automatic replay.
37. For Phase 1B prove all channels, remote senders, pairing and external Gateway exposure remain
    absent; only the authenticated local controller accepts turns. Channel enablement is not a Gate
    E option under this candidate.

### Capture negative controls

38. Prove no OpenClaw transcript path is watched or indexed.
39. Prove successful MCP retrieval does not create a capture authorization,
    quarantine claim, or background indexing route.
40. Exercise every request, graph, document, response, timeout, and wrong-type
    bound. Prove per-document truncation precedes the 64-KiB UTF-8 response cap,
    the response cap may reduce search/unresolved row count before
    `top_k`/`limit`, related denies rather than truncating a chain, and
    connector-side truncation cannot become partial success or change scope.
41. Mix pending, approved, rejected, revoked, superseded, and model-derived
    decision-shaped records with identical prose. Copy A's disposition onto B,
    change one byte/target/binding/event, forge actor strings, create competing
    dispositions, swap a registered provenance UUID between unequal payloads,
    change `selection_parameters.output_sha256`, and remove/change a provenance
    parent commitment. Prove only
    exact operator-owned dispositions bind, rejected/revoked records never
    establish current direction, assurance never rises on incomplete ancestry,
    and every response preserves kind, authority/verification state,
    assurance, confidence, time, disposition, and snapshot fields.
42. Reproduce 2-, 3-, 4-, and long supersession chains; forks; an approved
    multi-head join; stale/partial and concurrent joins; withdrawal/revocation;
    rejected replacement edges; out-of-order input; and every subset of
    pass/fail/inconclusive across independent `check2_` logical IDs, including
    pass+inconclusive, plus two competing revisions of one check. Prove superseded
    ancestors never resurrect, stale joins fail, concurrent heads conflict,
    the complete truth table holds, and visible-text equality never skips a
    semantic change. Compare an independently written reference reducer.
43. Distinguish exact preserved-envelope retry, identical-source remint, a
    genuine later scan, and changed payload under one source event. Prove only
    the exact retry is a no-op; a later scan creates a new assertion under the
    same logical ID; remint/conflict fails; and payload bytes are recomputed and
    compared rather than inferred from `provenance_identity()`.
44. Inject failure before/after every authority append, file and directory
    fsync, manifest close, projection write, cold validation, pointer rename,
    and pointer-directory fsync. Include absent-pointer first publication,
    forward CAS, torn tail, disk full, concurrent delivery, stale builder,
    ambiguous post-rename durability, and stale/expired rollback. Prove restart serves only an exact
    qualified current head or nothing. A committed revocation followed by projection failure must
    remain admitted/unavailable; an old unexpired head cannot serve. Rebuild/rollback may select
    only generations of the current authority and semantic contract. Test stale full-publication CAS
    after serving A→B→A.
45. Drive the actual installed runtime across compaction thresholds, heartbeat
    intervals, restart, and malicious per-agent overrides. Prove effective
    memory flush and heartbeat remain disabled and that no unsolicited model
    turn occurs.
46. Expire, correct, narrow, and roll back a snapshot during idle, queued,
    no-tool inference, and buffered response delivery. Kill the supervisor,
    move wall time backward/forward, suspend/resume, and attempt old
    state/session reuse. Exercise the turn-input and 1-MiB combined-output
    bounds. Race release commitment against revoke under the mutex; no new result may commit after
    lease loss or overflow. Already committed bytes may arrive later. Prove manager-owned domain
    retirement including detached grandchildren and the model worker, or quarantine on uncertain
    emptiness; a supervisor note is insufficient. Every successful result names its pinned basis and
    old sessions cannot resume.
47. Start the strict entry point with populated legacy home credentials,
    credential environment variables, and a general ConvMem config. Prove its
    empty fixed home and closed strict config prevent credential/provider
    loading before profile selection.
48. Exercise one active request plus eight queued requests, a ninth request,
    cancellation, timeout, oversized frame, malformed frame, and child exit.
    Prove FIFO bounds, fixed errors, no automatic retry, no late success, and no
    fallback to a wider profile.

49. Delete/change a retained assertion, disposition, policy key, source event, capture receipt or
    blob in a later head; reject. Replay original admissions against their own contexts, including
    an earlier supersession followed by withdrawal of its successor; no predecessor becomes current.
    New conflicting operation bytes reject; exact old retry returns its historic outcome with
    current head.
50. Permute selectors/top-k/limit/depth/document cap without changing authority; every returned
    assertion retains identical canonical state/hash. Same-check pass/pass forks remain conflict;
    conflicting observations remain unresolved even if each has pass checks. Verify completeness
    flags and no partial related support.
51. Swap raw/view/output bytes, locators, events, parents, selectors, receipts and issuer
    inventories; supplied contradiction rejects, missing evidence weakens. Deny cross-audience
    witnesses, receipt self-authentication and LLM closure. Later witnesses cannot upgrade old
    admission qualification. Preserve envelope UUIDs/bytes, including the valid legacy
    canonicalization domain; compare an independent reference qualifier.
52. Fail at fence, intent/source append, authority admission, projection, publication rename/fsync
    and recovery bookkeeping. Exercise empty enrolled genesis, lost pointer, torn tail, quota
    exhaustion, concurrent writer and stale operation. A valid preexisting authority remains
    history; serving never bypasses an unsettled terminal intent. Restoring the root without
    independent latest-history evidence stays unavailable.
53. Exercise turn/cancel/status/revoke, peer UID forgery, blocked consumer, repeated request/turn
    IDs, capacity exhaustion, partial frames, supervisor crash/hang, controller crash and stale
    retirement receipt. No lock inversion, automatic rerun or success from a half-frame. Supervisor
    cannot attest its own empty domain; unresolved containment prevents a replacement.
54. Restart against the same snapshot/boot, suspend/resume, step wall clock backwards, roll back a
    generation, rebuild without new capture, and reboot with/without a valid clock review. None
    renews source age. Retained BOOTTIME deadline never increases; release linearization uses the
    final valid sample without intervening awaited work.
55. Prove full private cold qualification precedes activation and exact committed public files are
    the only evidence files mounted into the runtime. Deny
    source/citation/grounding/issuer/governance file access by runtime UID; corrupt public
    manifests/rows or omit the private qualification and prove no start. On the sealed real runtime,
    poison caller cwd/.env/HOME/import paths/agent models, mutate a
    dependency without changing the launcher, inherit an unwanted FD, attempt all undeclared
    writes/network paths and invoke gateway/local model work while killing the supervisor. Exact
    effective tools/prompt/skills/hooks/model route must match policy. A dummy key or relaxed
    provider rule is failure, not successful compatibility.
56. At Gate W, exercise explicit approved-file admission with forged signer/status/IDs,
    pending/rejected/cancelled/old-format artifacts, stale expected parent, unknown prior state,
    duplicate add, admitted-unprojected retry and later revocation.
    Approval/recover/watch/index/repair do not ingest or authenticate themselves; all raw
    create/upsert paths reject strict authority fields. Existing legacy events remain bytes/IDs
    unchanged. Preserve production writer lock/backup gates and restore fencing; require no
    automatic migration of old approvals.
57. Execute §6.5.8's fixture contract. Preflight must fail before imports on missing namespace
    containment, an outside-root synthetic canary becoming readable/writable, ambient environment
    inheritance or an undeclared real process/network call. In T4/T5, assert every spawn/clock/peer/
    access/manager operation crosses the fixed fake port. A fake agent returns the fixed bounded
    object only; no credential or provider behavior is simulated. Exercise independent manager
    `populated=true`, `populated=null`, `terminal=false` and exact `terminal=true,populated=false`;
    only the last permits a matching retirement receipt. Keep detached descendants/model work after
    supervisor death/hang, restart the controller, inject stale boot/invocation/activation receipts,
    and race revoke against a blocked consumer. Assert no replacement/publication without empty
    proof. Deny runtime-role reads of private files, forged peer UID, production enrollment and
    direct/indirect fake selection from every production entrypoint. Negative mutants that remove
    the path/env guard, trust supervisor emptiness, accept a stale receipt or enable a production
    fake must fail. Test sandbox-negative controls against synthetic canaries only. Rollback must
    still retain the authority head/expiry, and teardown is not recovery.
    For the runner corrections, independently compare the actual mounts and runtime inventory:
    `/usr` must be the supplied `sysroot/usr`, with no host library bind. After freezing the
    inventory, remove/mutate one copied loader/library or add an unlisted file; preflight rejects
    before an implementation-import sentinel runs. Record real canary/read-only denial results;
    an inner synthetic canary exposure must be detected, not hidden by mocked denial results.
    Verify the exact three suite commands, the two exact built-in JUnit output arguments, the four
    declared legacy exclusions and every selected node/outcome. A full-discovery command, extra
    deselection, AST data labeled as collected evidence, hook/Git spawn or strict writer import
    fails. The pre-correction behavioral baseline remains 238 strict passes, 29 Node passes, and
    115 legacy passes plus one legacy skip and four deselections; any changed count/outcome is a
    regression, not evidence collection.
    Measure the existing capacity bounds; inject counter overflow/deadline and fill only private
    `/tmp` past its cap as negative controls. Failure never raises budgets or changes protocol time.
58. Build independently the five exact §6.5.9 component entry arrays and hashes plus the separate
    §6.5.8 fixture manifest. Mutate each included file's bytes/mode, including every unchanged
    CORE helper; all consuming hashes change or reject. Missing/extra/duplicate entries, substituted
    schema subsets, unlisted imports and a fake production image attestation reject. Change only
    test helpers/mutable output: production component hashes stay fixed, while fixture input
    changes alter the fixture manifest. Omit `canonical_json.py` in a mutant hashing walk and
    prove the independent inventory oracle rejects it. Regenerate from identical canonical inputs
    twice and require identical bytes/hashes. No host-image or provider discovery is permitted.

## 14. Verification commands and evidence

The paired `EXECUTION-openclaw-convmem-integration.md` names the exact file
scope, sequence, commands, evidence, stop conditions, and rollback for the
fixture-only build. Its minimum evidence set includes:

The list below spans the roadmap. Execution §5 assigns the B/C fixture subset; installed-runtime
probes and real inventory/enforcement are Gate D only, never prerequisites or authorized actions
for T0–T5. Frozen historical captures may support review but are not new runtime qualification.

- focused unit tests for selector resolution and membership proof;
- strict fixture-materializer tests proving source bytes cannot forge authority,
  state, disposition, or provenance fields and proving hostile semantic domain
  content cannot affect the registry-owned domain;
- import/write-denial tests proving Gate B never reaches legacy ingest,
  adapters, Chroma, restore, mixed-mode, eval, or file-generation paths;
- physical bound-projection tests proving rows outside the immutable profile
  scope cannot affect any strict tool's cost, cache, count, order, or shape;
- focused MCP inventory tests for tools, resources, and templates;
- focused bounded target-neighborhood tests, including depth-two relations and
  a greater-than-200-child non-expanding fallback hub;
- generator/validator property tests plus UTS #46/IDNA2008 vectors,
  payload-bound exact replay, fresh-observation versioning, binding-scoped
  collision, qualified-handle, ambiguous-relation, and write-rejection tests;
- typed authority/state, exact disposition substitution, provenance continuity,
  monotonic chain/fork/join, complete verification truth-table, semantic
  equality, strict first/forward/rollback publication, crash/recovery,
  stale-view, and supervisor-revocation tests;
- unchanged legacy compatibility tests for `tests/test_site_filter.py`,
  `tests/test_milestone_c.py`, and `monitor.py` ID lookup/write behavior;
- complete-bound state metamorphic tests with selected-out same-audience checks;
- connector child-environment allowlist and remote-node refresh tests;
- installed-runtime memory-flush, heartbeat, state-directory, queue, deadline,
  cancellation, frame-limit, and credential-isolation tests;
- existing retrieval, brief, resource, and ledger regression tests unchanged;
  strict tests separately prove the dedicated executable never imports the
  legacy priority-injection, over-fetch, Chroma, embedding, or rerank paths;
- ConvMem smoke checks from `docs/CODEX-DEEPSEEK-VERIFY.md` where relevant;
- `openclaw --version`, command inventory, config validation, plugin inventory,
  effective agent tool inventory, prompt/skill/hook inventory, model-provider
  route, network destinations, channel inventory, and security audit from the
  installed binary;
- production-path and network denial in hermetic tests;
- exact revision, config digest, scope-file digest, and test output in the
  review handoff.

Every portable review handoff includes immutable text captures and digests for
the installed `openclaw --version`, top-level `--help`, `gateway --help`,
`agent --help`, and `config validate --help` probes. Gate D adds the exact isolated config-validation
result and effective runtime inventories; Gate A evidence never substitutes a
current web page for an installed-binary probe.

The Gate A review bundle also includes `chroma_store.py`,
`file_generation_store.py`, `provenance_binding.py`, the adapter output
boundary, `chroma_write_store.py`, `mixed_mode_control.py`,
`eval_corpus/shadow_build.py`, `monitor.py`, and the ingest/distill merge points
so the decision to bypass legacy storage, domain ownership, identity
compatibility, and non-import claims are reviewable rather than asserted.

No test may read or mutate the live ConvMem database, live OpenClaw state,
external channels, or production transcript paths without the later named Ryan
grant.

### 14.1 Retained evidence gathered for planning revision `0f1216f`

The preceding edit's probes on 2026-09-21 inspected source and platform metadata against the exact code baseline.
They did not inspect live corpus content, live OpenClaw state or credential material, launch a
gateway/agent/model, mutate services, or run a production writer. Required session orientation/tracking
is separate from these probes. Stage 1's sealed bundle and 31 baseline tests remain baseline evidence
only. Both supplied report hashes were recomputed and matched the values at the top of this
document.

The existing writer inventory was checked mechanically with:

```text
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_shadow_writer_coverage_scan.py::test_inventory_documents_gated_routing tests/test_shadow_writer_coverage_scan.py::test_static_scan_matches_inventory_routing
```

Result: **2 passed in 0.10s**, exit0. This is a static repository routing check; it neither opens
Chroma nor proves future authentication semantics. The reviewed inventory is
`docs/plans/SHADOW-WRITER-COVERAGE-INVENTORY.json`, SHA-256
`1254d410c8dedd773530de7e1ba690714fccaac13f08c1adffc76194ccda827b`. Targeted `rg` inspection covered
approval/recovery/approved-file helpers, direct observation ingestion, decision files/events and
writer-boundary callers across tracked production Python and scripts; docs/tests were separately
treated as evidence, not callers.

Platform probes (`uname -srmo`, `/usr/lib/systemd/systemd --version`, `/usr/bin/systemctl
--version`, `node --version`, `python --version`, `setpriv --help`, cgroup/proc capability files)
returned Linux `7.2.6-arch2-1`, systemd `261.3-1-arch` with SECCOMP/BPF support, Node `v26.9.0`,
Python `3.13.12`, operator UID/GID1000. `/proc/self/cgroup` is unified cgroup v2; cgroup controllers
and network-namespace capacity are present. `setpriv` advertises pre-exec `--seccomp-filter`. The
shell name `systemd` was absent from PATH; absolute installed binaries succeeded. These establish
available mechanisms, not system-service privilege, valid unit/mount policy, actual filter
enforcement or a successful retirement. No new unit was installed or started.

The editorial consistency check also passed: 36 distinct named schema files have matching contract
literals, acceptance cases are exactly 1–56, Markdown fences balance, retired
pointer/envelope/state-contract text is absent, and baseline-to-worktree changes are confined to
these two plan files. `git diff --check` passed. These are document checks, not validation of
executable schemas or integration behavior.

### 14.2 Installed runtime compatibility result

Inspected installed OpenClaw root (a pnpm symlink closure, not a sealed image):

`/home/lauer/.local/share/pnpm/global/5/.pnpm/openclaw@2026.3.2_@napi-rs+canvas@0.1.96_@types+express@5.0.6_hono@4.11.9_node-llama-cpp@3.16.2/node_modules/openclaw`.

Exact byte identities:

- `package.json`: `4d2de1208138f9e8fd10a532c78defc2d942cc2c523adb2f90adff4209f1a5cb`.
- `openclaw.mjs`: `a5dd83191d4854dcb3f4d9b827a03917db020c458587427b3301553ea7b4c8ca`.
- `dist/auth-profiles-CNyDTsy4.js`: `5540085eeb079a811b1858874764506c57f8a421634ac25f60b8d415d3c831ee`.
- `dist/model-selection-Zb7eBzSY.js`: `2c99278b0426d032d59969b29eed78ea8bf91189c510835ed4a9645124009850`.
- `dist/model-selection-CjMYMtR0.js`: `1777c2eae39e52f2c15d5c36e1ef84524352080c468c782273a49b1f384a8573`.
- `dist/pi-embedded-DgYXShcG.js`: `f58ae685bb01c5327c082c6f1625e401cadd7c5b6a4b3d05f0c5a83c8f21fc37`.

`resolveApiKeyForProvider` at auth-profiles lines936–1003 checks explicit profile, auth store,
environment, then custom configured key; absent those it throws. `getApiKeyForModel` delegates to
it. The embedded run path at pi-embedded lines94213–94230 calls that resolver and rejects a missing
key except for AWS SDK authentication, which this local profile excludes. `authHeader:false` is a
request-header setting; it is not an exemption in this resolver/run branch. Compaction also uses the
resolver. The exact extracted function is byte-identical in both model-selection bundles; its
SHA-256 is `14c351c2e402bafe0cf1d71a19530767ecc28032fdcaef5f55e13ff9cb720b28`.

An isolated Node VM test evaluated **only that extracted function**, with an explicit empty
auth-store object and pure stubs returning no profiles/env/custom key. For provider names
`convmem-local`, `ollama`, `vllm`, all three returned `No API key found for provider ...`. Exit0
means the negative probe completed, not that a provider worked. It imported no OpenClaw modules,
performed no config lookup, made no network call and wrote no state. Reproduce by extracting from
the function declaration through the next `function resolveEnvApiKey` boundary, verifying the
function hash, and supplying the same empty auth dependencies. This proves the inspected branch's
incompatibility, not that no imaginable alternative runtime path exists.

**Consequence:** credential-free `openai-completions` under the inspected pinned run path cannot be
assumed implementable. A compatible exact route must be proven, or a separately reviewed
architecture decision must select a compatible runtime/authentication contract while retaining
local-only isolation and no ambient credentials. No dummy key, shared host service or hidden
fallback is an allowed repair. Neither a compatible sealed distribution nor exact
model-worker/config/inventory evidence exists yet.

### 14.3 Caller and legacy-transition mapping for Gate W

The missing baseline caller identification is resolved to these explicit routing requirements;
production behavior is not claimed fixed. This is repository-source coverage, not a census of
untracked operator scripts or current live in-flight proposals. Unsupported legacy admission is
refused, so missing historical consent does not become an automatic migration decision.

- `convmem.py` record/propose aliases (lines1298,1353,1521), `propose_decision.approve`,
  `_approve_unlocked`, `approve_and_ingest`: route all new ratification through the governed engine;
  approval emits the exact artifact and never indexes. Preserve interactive confirmation/write
  guard. `--no-index` is a documented compatibility no-op, not an optional control.
- `convmem.py:add` (lines393–410), `ingest_approved_file`, `ingest_approved_ledger`,
  `observe.ingest_observation[_file]`, observation/verification helpers: only explicit add may
  dispatch an authenticated approved-admission artifact. Remove transfer of authority via
  `proposal_id`/`_governed_protocol`; reject governed creates and upserts through generic paths. Old
  approved-file bulk ingestion becomes migration-required, never an implicit engine call.
- `recover_approval`, `recovery_action`, `live_decision_state`, `live_decision_snapshot`,
  `rebase_proposal`, `mark_approved`: use protected exact intent/admission state for new governed
  operations. Recovery can repair bookkeeping and already-admitted projections, not invent approval
  or perform an unissued add. A missing/failed Chroma read is unknown, never evidence of absent
  prior authority. A stale proposal requires fresh review/ratification.
- `conflict_events.py`: retain legacy reducer and identities; add a separate versioned admission
  event parser with byte-bound event deduplication. Preserve the existing universal
  production-writer boundary outside governed lock. New operation order is slot→production
  writer→governed ledger→lineage exclusive; do not call slot retirement while holding a
  reverse-order existing lock.
- `cross_project_digest.py` invokes proposal creation only, and `ledger_recent.py` reads approved
  intent only; neither receives admission authority. `scripts/convmem-live-write.sh` is a CLI
  wrapper, not approval. Change its examples with Gate W so they cannot promise legacy approved-file
  automatic ingestion.
- Ingest/index/watch families (`ingest.py`, `incremental_jsonl.py`, `inter_model_index.py`, watch
  dispatch), `refine.py`, monitor/evidence/forget/purge paths and generic Chroma mutation factories
  retain existing write gates but cannot emit reserved strict fields or ingest strict
  control/approval/capture roots. Mutable summaries are not authority. The inventoried 10
  production-session sites, 6 production-open sites and 15 allowlisted direct constructors must
  remain covered; the latter include read-only/disposable recovery/evaluation paths, not permission
  to write strict roots.
- `complete_data_restore.py` explicitly validates/restores `decisions-approved.jsonl` and
  `pending_decision_events.jsonl`; `recovery_authority.py`, file-generation/mixed-mode/shadow/eval
  routes can restore serving data but cannot mint enrollment, admission, or a fresh lease. Gate W
  must extend complete-data manifests/validators for the new protected admission files and retain
  existing backup authorization. Restored strict roots remain fenced until independent
  latest-history and empty-slot reconciliation; no source-of-truth flip for the existing legacy
  observation corpus.

Baseline source hashes: `convmem.py`
`0c278be127ac0f3f29815a283bf59b58d6520fbb5d390ae123733260d1897ad3`; `propose_decision.py`
`1bc098ad9275c8729269da90875eec83a65da7e3d37d288e091659f893b49dd1`; `observe.py`
`2d50037cdc9fddf919996f52f98109bfb8acf106b918855300a6b7d6bcc34599`; `conflict_events.py`
`0d41dbe4dca05e250ff2940698f5f1b36514365684198752a4258e393cc11a99`; `complete_data_restore.py`
`15dace7743f6cdaf067be4bc714749d6f6541fe7e042b0facd6b7c5c4e0c43f1`.

### 14.4 Evidence still required

Before qualifying the full adapter: exact root/model image and worker command/config, successful
credential-free run-path evidence, concrete manager/socket/mount/UID assignments, pre-exec filter
bytes, effective child inventory/output shape and independent cgroup-empty receipts across failure.
Static capability probes cannot replace these. Tests of the not-yet-built strict core are future
acceptance evidence, not a circular prerequisite to authoring its code. Gate W additionally requires
rechecking its complete caller/restore inventory and negative controls on its approved
implementation baseline; no live historical-consent scan is authorized or used as proof here.

### 14.5 Final corrective-edit documentary verification

The final Astra report explicitly reviewed `0f1216f7249c0066dafb6fc9ef2aafa9845a7264`; its recorded
plan-file hashes match that commit, and the report SHA-256 is pinned above. It is not an exact-tip
review of `2aa66a8` or this correction. The new diff starts at `2aa66a8` and is
limited to the two plans; all non-plan source remains identical to
`7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`. The document checker compares both schema inventories
(24 B, 7 C, 5 W), all original fenced contract bytes, cases1–56 unchanged plus57–58, CORE and all
five component sets, fixture fields, exact issue classes, containment constants, gate statements,
and Markdown/whitespace. It additionally compares the mirrored runtime closure, exact bounded
suite selection, repair records and unchanged manager/core semantics against `2aa66a8`.
Section18.5 records the focused regression review; §18.3 retains the preceding correction's matrix. The bundle carries
the checker, its output and parent-to-target diff so these assertions are reproducible.

At that corrective revision, no integration acceptance was claimed: one M8 reproduction was
behaviorally green but TEST remained PAUSED because its legacy collected-node evidence was
incomplete. Section 18.7 records the later accepted M8 result. Prior static routing/auth probes
were not rerun for this correction. No implementation, OpenClaw configuration, package install,
credential read or gateway/service start is part of this edit. The final exact-commit bundle must
bind the committed plan bytes, correctly labeled historical review, unchanged code evidence and historical probe
captures with a complete SHA-256 manifest; verify the archive before handoff.

## 15. Stop conditions

Stop and return FAIL if any of the following occurs:

- T0–T5 needs a real OS manager, credential, OpenClaw/model launch, production artifact, unlisted
  file/import, unspecified digest membership, or a fake selected through a production surface;
- fixture preflight cannot establish its disposable namespace boundary, a negative control passes,
  or the independent fake manager can be replaced by supervisor-self-certified cleanup;
- an unknown profile falls back to a wider profile;
- an omitted selector becomes unscoped, empty, or erroneous solely because it
  was omitted;
- an explicit selector widens project, site, or domain;
- project membership depends on corpus prose or an untrusted substring;
- authority domain comes from model/distiller output, ordinary semantic
  `domain`, document content, or anything other than the matched
  operator-owned source registration;
- a protected row domain lies outside its binding root, or strict site identity
  uses a normalizer other than the one pinned authority-site function;
- strict authorization calls legacy `site_filter.normalize_site()`, or Gate B
  changes that legacy function's URL/path behavior;
- source bytes can forge, preserve, or override authority, state, disposition,
  provenance, or manifest fields; or Gate B imports/writes any legacy ingest,
  adapter, Chroma, restore, mixed-mode, eval, or file-generation path;
- a response state is derived from prose, inline legacy fields, or timestamps;
- a row with missing proof is returned;
- `cross_domain=true` widens retrieval;
- a resource or unexpected tool appears;
- any strict surface reveals whether a valid qualified handle is unknown
  versus out of scope, or a row outside the immutable bound projection
  influences authorized response cost, count, order, or shape;
- any strict tool reads a global ledger index, wider store, Chroma, model,
  embedding, reranker, cache, or fallback rather than the named file projection;
- the strict server or read-only projection module imports the fixture
  publisher or exposes any publication/write entry point;
- strict search extracts or priority-injects a ledger ID from query text;
- strict search consults binding allowlists while screening syntactically valid
  handle tokens;
- canonical status changes under a voluntary selector, display limit or depth, or depends on any row
  outside the immutable audience;
- a strict-v2 ID generator can emit a value rejected by the canonical
  length/grammar validator, uses unpinned/IDNA2003 normalization, or falls back
  to a UUID;
- Gate B changes legacy-v1 monitor IDs, a live writer selects strict-v2 identity
  without a migration grant, or one scheme can be mistaken for the other;
- a changed payload reuses a source event/assertion, an exact preserved retry
  is duplicated, a later legitimate scan cannot create a new assertion under
  its logical ID, last-write-wins is consulted, or identity resolution occurs
  before the qualified binding check;
- a pending/model-derived decision becomes approved, a signer string or stolen
  disposition acts as proof, provenance ancestry is invented/upgraded, a
  rejected/revoked decision establishes current direction, contextual relation
  becomes supersession, a superseded ancestor resurrects, a partial/stale join
  resolves conflict, or the frozen verification truth table is violated;
- projection state precedes durable authority, a partial generation becomes
  active, first/forward/rollback publication violates its exact CAS contract,
  restart/rollback changes authority reduction, or concurrent publication
  bypasses compare-and-swap/cold qualification;
- an exact-site binding spans sites, a binding domain differs from the profile
  bound, schema v2 accepts other than one allowed binding, or a cross-profile
  qualified handle resolves locally;
- strict ledger-ID authorization uses an extraction regex or anything other
  than the centralized full-string validator;
- related returns a one-level or partial normative neighborhood, expands a
  registered non-expanding root's unrelated children, or denies a useful
  target solely because that root has more than 200 children;
- OpenClaw native memory, automatic memory flush, heartbeat, ACP dispatch, ACP
  execution, or a subagent child is active;
- an eligible skill, workspace instruction, hook, or plugin prompt is injected;
- a remote node pairs/connects or changes the eligible-skill snapshot;
- the connector child inherits ambient environment variables or consults a
  legacy read-scope variable;
- a same-ID plugin resolves outside the approved path or has the wrong digest;
- inference or connector traffic reaches an unapproved network destination;
- hostile corpus content reaches an instruction channel or triggers an action;
- interruption can be reported as success;
- a stale/expired snapshot returns evidence, a response omits snapshot times,
  or a prior activation's session/state directory can resume after correction,
  scope change, expiry, or rollback;
- a result commits after lease/pointer loss, retirement lacks an independent empty-domain receipt,
  runtime UID can impersonate the operator/supervisor, or any direct/streaming/`--deliver` output
  bypasses the controller;
- a strict process reads a home credential/general config, exceeds its one-plus-eight
  concurrency bound, retries automatically, or accepts an oversized frame;
- any external sender or channel bypasses the perimeter;
- transcript capture, indexing, or durable write becomes reachable;
- implementation requires scope beyond this plan.

A successful MCP connection, passing local smoke, or correct tool inventory is
necessary but never sufficient for Phase 1B or transcript capture.

## 16. Alternatives rejected

### OpenClaw native memory as authority

Rejected because it creates a second durable-memory system without ConvMem's
ledger provenance or recovery contract.

### Prompt-only scope instructions

Rejected because the caller and corpus are both untrusted. Scope must be
enforced by the physical bound projection and again before serialization by
server code.

### Reuse the mutable read-scope default as the ceiling

Rejected because it contains only domain, is designed as a convenience
default, and currently permits explicit override and `cross_domain` widening.

### Treat project-name text matches as authorization

Rejected because titles, summaries, paths, and ordinary metadata can be forged
by corpus or adapter input and are not service-owned identity assertions.

### Replace legacy site normalization or ledger IDs in Gate B

Rejected because full/shell URL handling and the live monitor's deterministic
IDs are existing production contracts. Strict authority uses a new normalizer
and versioned v2 generator; live identity changes require a separate migration.

### Traverse the whole related connected component

Rejected because the installed protocol fallback is intentionally a shared hub
for unrelated work and has unbounded fan-out. The bounded directional target
neighborhood preserves depth-two evidence and observation siblings without
expanding unrelated fallback children.

### Expose the current shell or full MCP profile

Rejected because shell exposes `ask` and global stats, while full additionally
exposes brief tools and resources.

### Enable ACP immediately

Rejected because installed ACP runs on the host and can inherit harness-level
tools and memory outside the initial integration's proof boundary.

### Add transcript capture during connector work

Rejected because capture has independent ingestion, quarantine, completeness,
and crash-loop failure modes.

## 17. Exact obligations for the final fresh Astra review

Audit the revised pair, not merely the sealed report. State PASS/FAIL/INCOMPLETE for each obligation
with exact section/schema references and a counterexample where it fails:

1. **Continuity and publication:** reconstruct genesis, new admission, fence, unavailable head,
   rebuild, rollback and retry from the exact field sets. Check no hash cycle, no authority
   rollback, no lost disposition/witness, full-publication CAS under ABA, and original-admission
   basis replay. Trace every crash point from fence to bookkeeping.
2. **State and retrieval:** independently apply the truth table, check-fork precedence and
   unresolved predicate. A selected-out conflict/ineligible check must never create pass. Confirm no
   global cross-audience influence, support-union denial and honest completeness metadata on all
   tools.
3. **Identity and provenance:** prove source occurrences cannot be reminted/reused, envelopes remain
   unchanged, grounding covers exact root/view/parent/output and protected receipt issuance, and no
   missing/late witness upgrades old assurance or LLM closure power. Confirm the separate meanings
   of approval, state, byte grounding, capture and factual truth.
4. **Ownership and concurrency:** validate slot/lineage independence from scope digests, UID
   separation, lock order, supervisor/controller distinction, manager-empty retirement and
   quarantine. Challenge forks, detached workers, controller/supervisor death, stale receipts,
   concurrent publish, blocked consumers and incomplete responses.
5. **Freshness and release:** test the specified release linearization against revoke, clock
   rollback, suspend, same-boot restart, rebuild/rollback and new-boot review. Reject promises to
   retract committed bytes or renew evidence by process restart.
6. **Fixture versus closed runtime:** re-attack §6.5.8's nonprivileged injected boundary, independent
   manager, pre-import physical isolation and production refusal. No actual authentication route or
   host mechanism may be selected by the fixture. Preserve §14.2's C-RUNTIME finding and the full
   Gate D dependency/CWD/env/FD/mount/network/inventory obligations; their missing real proof does
   not independently block this build. Dummy credentials and weaker fallbacks remain forbidden.
7. **Explicit writes and recovery:** trace every §14.3 caller family through the planned engine or
   refusal. Verify no implicit add, copied signer/marker, Chroma-absence authority, automatic legacy
   consent migration, restore bypass or lost backup/writer guard. Distinguish the fixture contract
   from unimplemented Gate W production compliance.
8. **Packet completeness:** compare all schema inventories, fields, CLI verbs, files, gate owners,
   tests and classifications between the pair, including §6.5.9's exact component sets and separate
   fixture manifest. Use only BUILD BLOCKER, SAFE TO DEFER INTO ISOLATED IMPLEMENTATION,
   LIVE-DATA/PROMOTION BLOCKER and NON-BLOCKING UNCERTAINTY. An unresolved decision needed by Grok,
   an unsafe fixture or an incomplete deferral safety case blocks BUILD; unbuilt fixed code and
   absent later production evidence do not. Cases57–58 are specification obligations, not executed
   proof. A proposed but unfrozen remedy cannot earn BUILD PASS.

For the corrective edit from `0f1216f`, focus the fresh advisory check on B-FIXTURE/B-DIGEST and
§18.3's interactions/regressions; do not restart general reconstruction of already passed semantics.
Kiro's exact-tip binary review follows. Ryan alone grants execution. This checklist authorizes no
runtime/config/data operation and missing future runtime proof is not a reason for another cycle.

## 18. Change log, resolution and readiness

Retained change history: the preceding edit from `9b106b9` to `0f1216f` made these corrections:

- **F1 resolved in specification (§§6.1, 6.5.3–6):** replace owner/generation-only pointers with
  stable enrollment, conserved parent-linked authority, exact added sets, durable fences, null
  serving and whole-publication CAS. Replace arbitrary unexpired-snapshot rollback with
  same-head/same-contract serving rollback; retain original expiry and operation history.
- **F2 resolved in specification (§§6.5.3, 8, tests18/42/50):** delete
  effective-selector/related-neighborhood state reduction. Introduce one canonical full-bound state,
  fork precedence even for pass/pass, weak-check inconclusive contribution, conflict-preserving
  unresolved predicate, verification-support union and completeness fields.
- **F3 resolved in specification (§6.5.1, tests41/51):** remove the false byte-verification claim
  about `provenance.py`. Keep envelopes unchanged; add grounding/receipts, explicit qualification
  dimensions, original-admission freezing and registered non-LLM closure eligibility. Missing
  history stays weak; contradictory evidence rejects.
- **F4 resolved in specification (§6.5.6, tests46/53/54):** replace process-group/self-receipt
  control with stable slot, external root controller/systemd ownership, separate runtime UID,
  complete turn protocol, serialized release/revoke, empty-domain receipt/quarantine and persisted
  BOOTTIME anchor. Already committed output is not retroactively recalled.
- **F5 corrected but runtime remains blocked (§§4, 9, 14.2):** replace launcher-only hashing and
  ambient host endpoint with full sealed imports/model image, private CWD/HOME/temp/network,
  dedicated contained worker and pre-import network filter. Read-only evidence now contradicts the
  assumed credential-free local auth path. No workaround is silently selected.
- **F6 resolved in specification; production acceptance pending (§6.5.7, §14.3, Gate W):** separate
  ratification, explicit `add --file`, durable admission and projection; authenticate the two-level
  intent/review/ratification chain; forbid implicit recovery ingestion and Chroma-derived prior
  authority. Add exact caller/legacy refusal mapping and preserve existing backup/restore/writer
  guards. Gate B/C protection of legacy files remains explicit; Gate W is required before production
  and is not covered by the fixture result.
- **Editorial closure refinements:** keep private authority qualification in the
  publisher/controller and mount only committed public projection files into the runtime; define
  empty enrolled genesis, non-circular production
  source-prefix hashing and the admission commit/recovery boundary; make capture receipts bind one
  whole multi-input invocation; specify direct file reads and preexisting read-only lock handles;
  separate root controller/supervisor from runtime UID and require pre-exec socket denial. These
  refine rather than assume the reconstruction remedies.
- **Paired contract revised:** version all changed schemas together; update file owners, publisher
  verbs, control protocol, return envelopes, gate mapping, 56 acceptance cases, recovery and
  readiness. Preserve lexical ranking, scope normalization, legacy IDs, three tools, no resources
  and all frozen runtime restrictions.

### 18.1 Preceding corrective edit from `0f1216f`

The sealed final Astra report reviewed that correction's parent `0f1216f`; its file hashes match
that correction's starting files. Classification preceded editing: B-FIXTURE and B-DIGEST were BUILD BLOCKER;
C-RUNTIME, D-CONTAINMENT, D-DISTRIBUTION and W-PRODUCTION were LIVE-DATA/PROMOTION BLOCKER;
I-IMPLEMENTATION was SAFE TO DEFER INTO ISOLATED IMPLEMENTATION; U-VALUE was NON-BLOCKING
UNCERTAINTY. Thus the no-edit path did not apply. This edit changes only the paired plans.

| Astra finding and candidate solution | Decision and evidence-based reason | Interaction / frozen contract |
|---|---|---|
| B-FIXTURE: name an executable nonprivileged fake boundary | Adopt, concretized in §6.5.8. Naming a fake did not choose its trust/OS/artifact behavior. Fixed injected ports, independent manager membership, disabled production launches and disposable test containment now do. | Keeps §§6.5.1–7 authority/state/provenance/recovery rules; fake artifacts bind separately through B-DIGEST. Codex owns semantics, Cursor/Grok implements; cases57 plus33/35/46/48/53–55 at B/C TEST. |
| B-DIGEST: restore exact component membership | Adopt in §6.5.9. An edit allowlist cannot define a dependency attestation. Exact CORE, SCHEMAS_BC and five component sets replace the ambiguous reference. | Binds unchanged helpers without authorizing edits, and excludes fixture/production model state. Cursor/Grok implements the fixed recipe; case58 at T0/TEST. |
| C-RUNTIME: resolve the actual credential-free route at the later runtime gate | Adopt gate assignment; reject an auth workaround in B/C. §14.2 proves the inspected branch incompatible, but T0–T5 invokes no provider. | §§9.1/14.2 unchanged; Gate D needs a reviewed compatible route. The protocol fake has no authentication result or fallback authority. |
| D-CONTAINMENT: qualify the real manager/UID/mount/socket/filter policy later | Adopt. §6.5.8 tests ownership and failures; only Gate D can prove OS enforcement. | Independent retirement/empty-domain rule remains mandatory in both layers. No process-group substitution or inferred real UID isolation. |
| D-DISTRIBUTION: qualify exact sealed runtime/model artifacts later | Adopt; §6.5.8's separately marked synthetic specimens resolve only fixture inputs. | No production image, model, argv or inventory is chosen. Five component hashes do not claim full image closure. |
| W-PRODUCTION: preserve separate governed-writer slice | Adopt. §§6.5.7/14.3 specify the route while B/C protects legacy writers. | No implicit approval/add/recovery/indexing, migration or Chroma authority; Gate W still required. |
| I-IMPLEMENTATION: build and falsify selected algorithms | Adopt deferral to TEST; unimplemented fixed algorithms are the deliverable. | No new schema/authority/state/rollback choices; named negative controls must fail. |
| U-VALUE: measure quality and cost later | Adopt. Fixed lexical behavior may be safe yet unhelpful; Gate D-V owns value claims. | No recall fix may add a model/global store/fallback to the frozen fixture. |

Precise changes: added §6.5.8's fixture interface/artifact/containment contract and §6.5.9's hash
inventories; bound T0/T4/T5 and production-entrypoint refusal to those definitions; added cases57–58;
separated BUILD/TEST/LIVE-DATA/PROMOTION and replaced the complete-integration BUILD label; added
the following owned deferral records and parent-to-target regression matrix. All existing record,
disposition, qualification, publication, state, tool/control and Gate W schemas remain unchanged.
The fixture-manifest schema is test-only and is not added to SCHEMAS_BC or the semantic artifact.

### 18.2 Remaining issues, correction paths and stops

The following records are normative in both plans. For all SAFE TO DEFER INTO ISOLATED
IMPLEMENTATION entries, the correction is code conforming to the already selected contract, not
redesign. A safety assertion failing is observable TEST failure. A missing/wrong implementation is
corrected in its assigned file; a required change to authority, provenance, schemas/interfaces,
security, containment, rollback/recovery or acceptance meaning instead stops BUILD and returns to
Codex/Kiro. No failed negative control may be waived. B/C uses synthetic data, never promotes a
fixture, and has no production writer or runtime activation. These constraints prevent a deferred
implementation defect from authorizing architectural change or consequential use.

- **B-FIXTURE — SAFE TO DEFER INTO ISOLATED IMPLEMENTATION.** Evidence: Astra's missing contract is
  now §6.5.8, with exact ports, roles, events, capabilities, artifact kind and fail-closed launcher.
  Gate: B/C TEST, before any suite acceptance. Owner/location: Cursor/Grok in controller/supervisor,
  connector and `tests/fixtures/openclaw_strict/`; named lifecycle/controller/supervisor/connector
  tests validate it. Correction path: implement those ports and the fixed harness; repair against
  this contract. Exact acceptance/negative control: case57 and assigned33/35/46/48/53–55; synthetic
  outside-root/ambient canaries deny, populated/unknown/stale manager state prevents retirement,
  production entrypoints refuse fixtures, and bypass mutants fail. Observable failure: host call,
  leaked canary, accepted stale/self-issued receipt, late result or unintended launch. Deferral is
  safe because no actual provider/privileged runtime is part of implementation and suite entry is
  physically isolated. Rollback/recovery: retain current head/expiry, quarantine nonempty domain;
  test teardown cannot recover an enrolled lineage. Contamination: prohibited; need for real
  runtime/credential access, a configurable fake bypass, or altered retirement meaning is the BUILD
  stop. Grok architectural decision: **no**.
- **B-DIGEST — SAFE TO DEFER INTO ISOLATED IMPLEMENTATION.** Evidence: §6.5.9 now enumerates all
  five sets and protected helpers separately from edit permissions. Gate: T0 and B/C TEST. Owner:
  Cursor/Grok in the existing component owners and `test_openclaw_strict_packet_contract.py`.
  Correction path: implement independent canonical walkers and exact-set validation. Exact
  acceptance/negative control: case58, including each included file/mode mutation, schema-subset
  substitution, excluded-test invariance and omitted-canonical-helper mutant. Observable failure:
  unequal known-answer digests, missing/extra import, or a mutation invisible to its component.
  Deferral is safe because membership is fixed now; future hash values are computed evidence.
  Rollback/recovery: a mismatched artifact cannot qualify/serve; no old authority or policy fallback.
  Contamination: prohibited; any new unbound dependency, guessed membership or fake production
  attestation stops BUILD. Grok architectural decision: **no**.
- **I-IMPLEMENTATION — SAFE TO DEFER INTO ISOLATED IMPLEMENTATION.** Evidence: fixed §§6–8,
  execution T0–T3 and the unimplemented acceptance matrix. Gate: B/C TEST. Owner/location:
  Cursor/Grok in the eight allowed modules, schemas and their named tests; Codex verifies, Kiro
  reviews conformance. Path: implement/reproduce/repair before acceptance. Exact acceptance:
  cases1–27/40–44/49–52, server47 and private55, plus C's assigned tests; independent reducer and
  qualifier references and mutants removing selector ceiling, cumulative history, original-admission
  freezing, full-publication CAS or current-head-only rollback must fail. Observable failure:
  byte/hash mismatch, selector-created pass, false assurance, stale publication or forbidden import.
  Safe deferral: tests of the selected implementation follow writing it; no unresolved semantics
  remain. Rollback/recovery: review/revert code, preserve admitted fixture history and stay
  unavailable on ambiguity. Contamination: prohibited; any need to change a schema/interface,
  invariant, resolver, protected writer or acceptance rule stops BUILD. Grok decision: **no**.
- **C-RUNTIME — LIVE-DATA/PROMOTION BLOCKER.** Evidence: §14.2 and Astra's matching-source check.
  Gate: D before actual runtime, then LIVE-DATA/PROMOTION. Owner/location: Codex/Kiro in §§9.1/14.2
  and the later Gate D packet; Ryan grants runtime actions. Path: prove a compatible exact route or
  separately review a runtime/auth contract while preserving local-only/no-ambient-credential rules.
  Acceptance: cases28/34/55 on exact real bytes, one local turn without provider key/dummy key,
  auth-store/env fallback, remote egress or shared host endpoint; each forbidden-route negative
  control fails qualification. Observable failure: no-key resolver error or wider route. Recovery:
  no activation, or retire/quarantine under §6.5.6; never fallback. Can contaminate architecture
  only if imported into fixture scope: dependency on or claimed proof of real auth stops BUILD.
  Grok decision in T0–T5: **no**; a later real-route decision belongs to Codex/Kiro/Ryan.
- **D-CONTAINMENT — LIVE-DATA/PROMOTION BLOCKER.** Evidence: §§6.5.6/14.4 lack actual host
  qualification. Gate: D, then LIVE-DATA/PROMOTION. Owner/location: Ryan-granted provisioning and
  qualification lane; Codex/Kiro review manager/socket/launch bytes. Path: instantiate the already
  selected systemd/cgroup boundary in a separate packet. Acceptance: actual cases46/53/55, UID/peer/
  mount/FD/filter/network denials and death/hang/detached-worker tests; remove each relevant control
  only in the granted disposable environment and require its negative test to fail. Observable
  failure: access/egress or surviving/unknown domain. Recovery: quarantine, no receipt/replacement
  or serving mutation until independently empty. Contamination: a real host mechanism chosen in
  B/C or fake proof asserted as OS enforcement stops BUILD. Grok T0–T5 decision: **no**.
- **D-DISTRIBUTION — LIVE-DATA/PROMOTION BLOCKER.** Evidence: §§6.5.6/14.4 have no sealed actual
  runtime/model/worker inventory. Gate: D, then LIVE-DATA/PROMOTION. Owner/location: separately
  granted packaging/qualification lane, Codex/Kiro's Gate D packet. Path: deliver exact immutable
  artifacts and effective child inventory without model/provider defaults. Acceptance: real
  cases28–34/45/47/55; mutate a dependency while retaining the launcher, poison CWD/HOME/imports,
  inherit an extra FD or add a tool/endpoint and require failure. Observable failure: digest/import/
  inventory drift or fallback. Recovery: refuse activation, retire a drifting runtime, retain
  authority/freshness; never substitute a host package. Contamination: a fixture relying on a
  chosen production image/model or fabricated sealing evidence stops BUILD. Grok decision: **no**.
- **W-PRODUCTION — LIVE-DATA/PROMOTION BLOCKER.** Evidence: §§6.5.7/14.3 and execution §6 remain
  specified but unimplemented outside B/C. Gate: W before production enrollment/LIVE-DATA and E.
  Owner: Codex/Kiro exact-baseline follow-on packet; Cursor after Ryan's grant. Path/location:
  governed engine plus enumerated CLI/writer/backup/restore callers, never B/C files by implication.
  Acceptance: case56 plus41–44/49/51–52 through disposable real governed CLI; bypass each approval,
  explicit-add, writer/backup or restoration fence and require negative-control failure. Observable
  failure: implicit ingest, forged consent, unknown Chroma state accepted as absent, lost revocation
  or automatic legacy migration. Recovery: fence and reconcile latest protected history; uncommitted
  admission needs explicit add retry. Contamination: importing/editing protected writers or claiming
  production consent from fixture PASS stops BUILD. Grok T0–T5 decision: **no**.
- **U-VALUE — NON-BLOCKING UNCERTAINTY.** Evidence: lexical-only §6.5.5 and unrun D-V. Gate:
  prototype assessment and D-V/E promotion claims, not BUILD. Owner/location: Ryan and the later
  evaluation owner in the predeclared Gate D-V packet. Path: predeclare thresholds/stops before the
  paired experiment, then measure quality, owner effort, rework and resource cost. Acceptance:
  lexical known-answer tests plus later 32-run comparison; an off arm is the control, null/harmful
  outcome fails value/promotion claims. Observable failure: safe retrieval is unhelpful or exceeds
  fixed bounds. Recovery: keep prototype disposable; do not promote. Architecture contamination is
  possible only through unauthorized scope changes: adding global search, inference, wider authority
  or fallback stops BUILD. Grok T0–T5 decision: **no**. No new value threshold is needed to implement
  the already bounded reader.

### 18.3 Preceding correction's regression matrix (`0f1216f` to `2aa66a8`)

Parent is `0f1216f7249c0066dafb6fc9ef2aafa9845a7264`; target is `2aa66a8`. These are
documentary counterexample checks and diff evidence, not claims that future executable tests ran.

| Previously sound property | Changed section | Adversarial regression attempted | Result/evidence |
|---|---|---|---|
| Authority-head continuity and rollback | §6.5.8 fixture binding; gates | Use fake cleanup to select an older unexpired authority | Denied: §§6.5.3–4 algorithms unchanged; fixture rollback explicitly retains head/expiry; cases44/49/52/57. |
| Canonical verification independent of filters | Scope/readiness only | Fake test drops selected-out fail to create pass | §6.5.3 and test18/50 unchanged; one full-bound state/hash remains normative. |
| Fork/conflict precedence | None in reducer | Same-check pass/pass fork or all-passed conflicting observation becomes current/pass | Full-bound fork precedence and unresolved predicate unchanged; case42/50. |
| Byte grounding/authenticated receipts | Fixture artifact boundary | Synthetic launch artifact authenticates capture or a receipt self-authenticates | §6.5.1 unchanged; fixture manifest cannot supply authority; case51/57. |
| Original-admission provenance | No semantic change | Append late witness and raise old assurance | Original context freezing unchanged; cases49/51. |
| Retirement/freshness/serialized release | §6.5.8 ports | Supervisor clears manager state, stale receipt reopens slot, restart renews age | Independent manager set plus unchanged §6.5.6 mutex/anchor; cases46/53/54/57. |
| Explicit approval/ingestion/admission/projection | Scope and gates | Fixture publisher becomes production add or recovery performs admission | §6.5.7/14.3 unchanged; production mode rejected; Gate W separate; cases52/56/57. |
| Private qualification | §6.5.8 access table | Runtime grants itself private access or supplies a qualification flag | §6.5.4's split unchanged; virtual runtime denies private paths; real proof remains Gate D; cases55/57. |
| Physical fixture isolation | §6.5.8 harness | Missing namespaces quietly runs host tests or outside-root canary leaks | Mandatory pre-import boundary, no host fallback, synthetic negative preflight; case57. No host deployment claim. |
| No ambient credentials | §6.5.8 ports/environment | Fake selects real auth, copies env or uses a dummy key | Fake has no auth operation; closed environment and production refusal; cases33/47/55/57. |
| Legacy identifiers/envelopes | §6.5.9 CORE inventory | Hash inclusion grants modification or normalization of protected helpers | Edit allowlist remains separate; legacy files/envelope bytes unchanged; cases21/43/51 and legacy suite. |
| Rollback/recovery | §6.5.8 teardown | Discard fixture root and claim continuity, or reset after uncertain retirement | Explicit teardown distinction and unchanged fail-closed history rules; cases44/52/57. |
| Fixture versus Gate W production | §12 / §18 gate labels | BUILD PASS becomes writer/live-data permission | Independent four-gate statuses; B/C protects all Gate W callers; future case56. |
| Component attestation | §6.5.9 | Protected helper changes without digest change; test bytes enter runtime hash | Exact sets restore the lost oracle; independent mutation/exclusion case58. |

**WHAT DID THIS EDIT BREAK THAT WAS PREVIOUSLY SOUND?** Nothing found in these documentary attacks.
The core schemas/state/provenance/publication and production recovery rules were retained; the
changed boundary removes ambiguous fixture execution and hash membership. Actual implementation
tests remain NOT YET RUN. A focused fresh Astra check is justified by these substantive fixture/
artifact choices, followed by Kiro exact-tip review; missing production evidence alone does not
justify another general planning cycle. No Execute, live-data or promotion authority is issued.

### 18.4 Final focused repair from `2aa66a8`

Decision: **EDIT REQUIRED**, only for the two concrete runner contradictions below. The exact
starting branch/commit, both Git/file/archive plan copies and all 139 bundle manifest entries were
verified against bundle SHA-256
`ebbc2d8cf3344cd6c82cb9793c0d137d8f72cf36dd1595ff2398d58467e03d92`. The retained Astra report is
evidence about `0f1216f` only. A coherent normative contract resolves a specification blocker;
reassuring assertions or promises of evidence do not. Executable conformance remains TEST work.

BLOCKER_ID: B-RUNNER-CLOSURE
FAILED_BUILD_CRITERION: Every executable fixture dependency has a fixed, nonambient input boundary.
WHY_CURRENT_CONTRACT_FAILS: At `2aa66a8`, §6.5.8 inventories only the `/runtime` prefix but also
mounts system libraries at `/usr`. Changing those library bytes need not change the fixture's
runtime hash. The promised closed runtime therefore admits an unbound host dependency.
MINIMUM_REPAIR: Mount only the supplied prefix's inventoried `sysroot/usr` at `/usr`; freeze loader,
stdlib, package and data resolution at the existing mount paths without environment/mount fallback.
FILES_AND_SECTIONS_CHANGED: This plan §§6.5.8, 13 case57, 14.5, 18.4–5; execution §§5.1, 9, 10.3.
FROZEN_FIXTURE_CONTRACT: All runtime regular files, including `sysroot/usr/`, enter the single
canonical sorted runtime inventory/hash; only the three fixed sandbox aliases are created.
No host `/usr`, new mount, inherited loader setting, systemd/OpenClaw/model or credential is admitted.
EXACT_ACCEPTANCE_TEST: Case57 preflight verifies mount source mapping, pinned versions, resolution
and every frozen file/mode/hash before strict imports; the independent reference recomputes the
runtime hash including support files. Return the inventory, resolution and post-run comparison.
NEGATIVE_CONTROL: In a disposable prefix copy after inventory freeze, remove or change one loader/
library, add an unlisted regular file, or propose a host-`/usr` bind. Each rejects before the strict
import sentinel; recalculating only the implementation's claimed hash cannot satisfy the reference.
ROLLBACK_OR_RECOVERY_BEHAVIOR: Refuse suite entry; on a running failure wait for namespace exit,
retain the root on uncertain teardown, and preserve synthetic authority head/expiry. No host fallback.
OWNER_AND_CORRECTION_PATH: Cursor/Grok implements preflight and case57 in the existing test-helper/
packet-test allowance. The provisioning owner supplies missing pinned bytes separately before TEST;
any proposed dependency/mount semantics change returns to Codex/Kiro.
REGRESSION_TEST: Case58 component sets stay identical; cases33/47/55/57 still deny ambient paths,
credentials and real launch. Runtime mutation affects the fixture hash, not production component sets.
NEW_STATUS: RESOLVED — normative contract; execution NOT YET RUN.

BLOCKER_ID: B-RUNNER-SUITES
FAILED_BUILD_CRITERION: Mandatory acceptance commands obey the runner's frozen process/import scope.
WHY_CURRENT_CONTRACT_FAILS: At `2aa66a8`, execution §5.1 requires unqualified full pytest and all
ledger tests while forbidding their required subprocesses. At unchanged baseline `7809f20`,
`tests/test_work_git.py` executes Git; `tests/test_restic_systemd.py` probes systemd-analyze; the
four ledger nodes now named in §6.5.8 execute `scripts/kiro-agent-run-hook.py` or Git. Applying
strict writer/config import guards to the mandatory legacy suite also rejects its intended imports.
MINIMUM_REPAIR: Freeze three bounded suites, explicitly exclude those four unrelated subprocess
nodes and full-repository discovery, retain all other named legacy nodes, and isolate legacy
compatibility imports in their own contained pytest process. Do not add host tools or modify tests.
FILES_AND_SECTIONS_CHANGED: This plan §§6.5.8, 13 case57, 14.5, 18.4–5; execution §§5.1, 9, 10.3.
FROZEN_FIXTURE_CONTRACT: Execution §5.1 supplies the exact command/node set. The driver compares it
with an independent test-owned constant before collection. Strict/connector safety coverage is
unchanged; legacy byte/UUID/continuity tests are explicit; no extra deselection or subprocess is allowed.
EXACT_ACCEPTANCE_TEST: Case57 compares command arrays and collected node IDs, all selected tests
pass with no new safety skip, and traces show only allowed strict subprocesses and none from the
legacy suite. Protected baseline files remain byte/mode identical. Report the four exclusions and
no full-repository result; do not claim coverage for unrun host-tool tests.
NEGATIVE_CONTROL: A full-discovery command, extra deselection, omitted selected safety test, real
hook/Git launch or strict reader importing a legacy writer must fail the independent packet guard.
ROLLBACK_OR_RECOVERY_BEHAVIOR: Fail TEST without widening process/mount access or fabricating skips;
retain failed evidence until namespace teardown is established. Fixture disposal is not recovery.
OWNER_AND_CORRECTION_PATH: Cursor/Grok implements the exact selection/guards in the existing runner
and packet-test allowance. Broader repository regression remains separately reported work; it is
not silently satisfied or turned into Gate D compatibility proof. Selection changes require Codex/Kiro.
REGRESSION_TEST: Every B/C case remains assigned; all selected legacy ID, provenance, writer and
recovery tests remain mandatory. Case57 rejects scope expansion and case58 keeps protected inputs bound.
NEW_STATUS: RESOLVED — normative contract; execution NOT YET RUN.

Other focused results: capacity is unmeasured, with unchanged limits now assigned measurement and
failure evidence in TEST. Manager membership remains independently owned: supervisor death, stop
acknowledgement and cleanup callbacks cannot remove detached descendants or outstanding model work;
only separately scheduled manager removals may produce an exact terminal/empty observation.
Case57 must test that sequence, partial independent removal, unknown/stale observations and genuine final emptiness.
Case58's expected inventory/hashes remain reference-owned; mutations are on disposable copies.
Real denial evidence concerns the disposable sandbox only. No real authentication, provider,
host UID/systemd deployment, production image or Gate W operation is introduced.

### 18.5 Final correction regression matrix (`2aa66a8` to this edit)

**WHAT DID THIS EDIT BREAK THAT WAS PREVIOUSLY SOUND?** No previously sound semantic contract is
changed. One coverage claim is deliberately narrowed: this closed runner cannot claim a full
repository regression run or the four excluded hook/Git cases. That requirement was incompatible
with its existing process restrictions, not demonstrated passing coverage. The following are
documentary comparisons and required future tests, never claims of executed conformance.

| Property | Documentary comparison / attack | Required TEST evidence |
|---|---|---|
| Authority-head continuity | §§6.5.3–4 unchanged; support-library or suite changes cannot restore an old head. | Cases44/49/52, old-head publication rejected. |
| Canonical verification | Full-bound reducer and canonical contracts unchanged; narrowing test selection grants no query-local reducer. | Cases18/42/50, hidden fail/fork still prevents pass. |
| Byte grounding | §6.5.1 unchanged; runtime inventory cannot authenticate source/output bytes. | Case51 substitutions rejected; protected provenance tests. |
| Receipts | Issuer inventories and original-admission context unchanged; no fixture self-attestation. | Cases49/51, forged/late receipt does not elevate assurance. |
| Retirement/freshness | §6.5.6 and fake manager port unchanged; death, stop ACK and cleanup leave membership populated. | Cases46/53/54/57: detached child/work persist; partial removal refuses; independent final terminal/empty event permits retirement; expiry never renews. |
| Explicit ingestion/admission/projection | §6.5.7 unchanged; legacy test imports stay in their separate synthetic process. | Cases52/57; future case56 remains Gate W, never claimed here. |
| Physical isolation | Namespace/capability/root/FD rules retained; host `/usr` input removed. | Case57 actual canary and read-only denials plus detected synthetic exposure; no mock-only PASS. |
| No ambient credentials | Empty environment and fake's no-auth port retained; no loader-variable fallback. | Cases33/47/55/57 and absent sentinel env/FD evidence. |
| Legacy behavior | All non-plan source remains baseline-identical; selected legacy tests plus explicit provenance/continuity tests stay required. | Exact selected nodes/results; four named exclusions and no whole-repository PASS. |
| Rollback | Current head, contract and freshness anchor unchanged. | Cases44/52/57, old authority or renewed expiry rejected. |
| Recovery | Unknown history/emptiness stays unavailable; disposal still is not lineage recovery. | Cases52/53/57, no reset or implicit add. |
| Hash contracts / safe mutations | Five component sets and schemas unchanged; full test dependency closure separately bound. | Case58 independent literal inventories; omit canonical helper/recompute wrong digest still fails; disposable-copy mutation leaves protected originals unchanged. |
| Fixture/live-data/promotion separation | Fake remains unselectable and unauthenticating; four gate statuses retained. | Case57 disabled launch/registration; no Gate D/W/E PASS from fixture success. |
| Capacity versus protocol | 600 seconds, 16 MiB output, 256 MiB private `/tmp` unchanged and unmeasured. | Record measurements and failing over-limit controls; protocol deadlines/authority/freshness unchanged. |

At the close of the preceding correction, BUILD remained PASS and TEST had not yet run. The current
state is superseded by §18.6: one behaviorally green M8 run exists, TEST is PAUSED without a PASS,
and LIVE-DATA/PROMOTION remain BLOCKED. The earlier reports do not certify this revision.

### 18.6 M8 exact node/outcome evidence correction

**Authorized correction.** On 2026-09-23 Ryan authorized only a plan correction allowing the two
frozen Python test commands to emit built-in pytest JUnit XML under disposable
`/fixture/evidence`, solely to obtain exact collected node IDs and outcomes. Selectors, the four
deselections, test behavior, dependencies, permissions, isolation and runtime semantics remain
unchanged. Gate D, real OpenClaw, merge, deployment and later gates remain unauthorized.

**Observed blocker.** M8 implementation tip
`8b8339e53565cad2f1a5fafda6212a7c800ffbdf` completed one behaviorally green isolated run: 238
strict passes, 29 Node passes, and 115 legacy passes plus one skip and four deselections. Its strict
suite supplied live pytest items, but its legacy report supplied only a named-file AST definition
inventory. Parameterization made that diagnostic smaller than the live legacy collection, so it
cannot satisfy §6.5.8's collected-node evidence requirement. No TEST PASS was issued.

**Minimum repair.** Execution §5.1 adds one built-in JUnit output argument to each existing Python
command and freezes both output paths. The runner derives canonical node/outcome arrays after the
unchanged processes finish, using the fail-closed reconstruction and validation rules in §6.5.8.
No new command, collection pass, plugin, environment mechanism or protected-test edit is allowed.
The only selected-test-file change permitted when implementation resumes is the mechanical update
of the existing semantic-parent SHA assertion required by the newly reviewed parent; it may not
change test logic, selection or outcome.

**Acceptance and regression boundary.** Both fresh-root runs must preserve the observed behavioral
counts, yield identical canonical Python node/outcome arrays, exclude the exact four legacy nodes,
and keep the Node command/result unchanged. Raw JUnit and derived evidence remain disposable,
hash-excluded test output. Missing, malformed, ambiguous, lossy, duplicate, inconsistent or
out-of-selection evidence fails M8. All authority, provenance, publication, recovery, component
hash, containment and later-gate invariants remain unchanged. At that correction point BUILD
remained PASS for bounded T0–T5 and TEST was PAUSED pending implementation and two accepted reruns;
§18.7 records their later completion.

### 18.7 M11 current-main integration boundary

**Accepted historical result.** The M8 correction was implemented and independently accepted at
`8010fb060c2edc29e1b09d7a30b1a1da2689d489`. Bounded Gate B/C TEST PASS applies only to that exact
implementation, its original code baseline
`7809f20dc53d9dd19f765c3ec3214a3df54ca5bf`, semantic parent
`34338133186010a26ed746bbfea4c9abb958e9ca`, reviewed overlay
`b16763ffefa90023800f05f78ab8a71e765f5022`, frozen runtime inventory, and accepted durable
evidence. It does not certify a rebased, merged, replayed or otherwise reconstructed tree.

**Observed integration condition.** Current `origin/main` is
`9193f5ec744f059d07a20612489b210527b5660a`. It and the accepted implementation diverge from
common ancestor `7607fbb4430619566974274ad7e0c6690c785278`. The accepted implementation's exact
45-commit range begins at `2f05a8540b9155346f313d7b2eea6300fec29350`, whose parent is the original
code baseline, and ends at `8010fb060c2edc29e1b09d7a30b1a1da2689d489`. The current-main product
paths and that implementation range have no path overlap. The planning documents do overlap and
carry different revisions, so a silent rebase, ordinary merge, or plan selection by Grok is
forbidden.

**Frozen reconstruction.** After this parent and its milestone overlay receive exact-tip Kiro
PASS and Ryan names a new integration grant, Codex creates the granted implementation branch and
worktree at the exact reviewed overlay tip named in that grant. Before Grok starts, Codex proves
that the overlay tip descends from `9193f5ec744f059d07a20612489b210527b5660a`, differs from it in
exactly the four authorized architecture, execution, milestone-overlay and STATUS documents, and
has byte-identical non-plan/product state. Grok then cherry-picks, in existing order and without
merge commits, exactly
`2f05a8540b9155346f313d7b2eea6300fec29350^..8010fb060c2edc29e1b09d7a30b1a1da2689d489`.
Any conflict, skipped commit, extra commit, path outside the accepted implementation range, or
change to a current-main-owned product byte is `PAUSE`; Grok does not resolve it. The four
planning/status documents from the reviewed reconciliation tip remain authoritative and are not
taken from the older current-main versions or historical implementation lineage.

**Exact pin-only reconciliation.** After the conflict-free replay, Grok makes one held correction
limited to:

- `tests/fixtures/openclaw_strict/constants.py`: set `CODE_BASELINE_SHA` to
  `9193f5ec744f059d07a20612489b210527b5660a` and `SEMANTIC_PARENT_SHA` to the exact reviewed
  semantic-parent commit named in Ryan's grant;
- `tests/test_openclaw_strict_packet_contract.py`: update only the two corresponding literal
  assertions; and
- the parent/overlay references in comments or docstrings in exactly
  `openclaw_strict_server.py`, `strict_projection.py`,
  `tests/fixtures/openclaw_strict/adversarial_matrix.py`,
  `tests/fixtures/openclaw_strict/audit_evidence.py`,
  `tests/fixtures/openclaw_strict/fixture_manifest.py`,
  `tests/fixtures/openclaw_strict/protocol_fixture/schema_field_sets.py`,
  `tests/test_mcp_openclaw_strict.py`, `tests/test_strict_projection.py`, and
  `tests/test_strict_projection_publisher.py` so they name the reviewed parent/overlay without
  altering executable behavior, test selection, expected outcomes, or component membership.

No schema, interface, dependency, permission, selector, deselection, test behavior, authority
rule, hash algorithm, component set or runtime behavior changes. The future overlay commit SHA is
not inserted into executable fixture state unless an already-frozen parent field requires it.

**Runtime and evidence rebinding.** The historical runtime tree is reusable only after Codex, as
the named provisioning operator, copies or reconstructs it at the newly Ryan-authorized exact
parent/baseline path and proves a complete file/mode/hash inventory, resolved dependency paths,
version checks, mutation check, no symlinks/unlisted bytes and the unchanged expected tree hash
`sha256:74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`. The historical
path is not acceptance input for the new baseline. Ryan must also name a new durable evidence root
bound to the reviewed overlay; M8 output is copied under
`runs/<integration-source-commit>/<run-label>/` with Codex-verified staging-to-durable hashes.
Grok may not provision, repair, download, substitute or select either location.

**New acceptance evidence.** At one clean pushed integration commit, Codex independently verifies
that the four reviewed plan/status blobs remain exact, all other current-main-owned paths remain
byte-identical unless they are in the accepted product delta or exact pin/comment allowance, the
replayed product delta matches the accepted `7809f20..8010fb0` delta except for those exact
allowances, and no product path is omitted or added. Then the unchanged isolated runner passes twice from fresh roots using
the newly reviewed parent SHA and baseline. The seven legacy MCP test files and the unchanged
Pylint regression gate run in the separately reviewed disposable environment. Every raw command,
node/outcome inventory, component/source hash, runtime inventory, mutation check and durable-copy
mapping is retained. Historical M8 evidence is comparison input, never substituted for these runs.

**Authority boundary.** This section changes integration sequencing and evidence binding only. It
does not change T0–T5 semantics or authorize implementation, merge, OpenClaw installation/update,
real OpenClaw execution, Gate D, Gate W, Gate D-V, Gate E, Gate F, watch activation, live data,
deployment or promotion. The installed OpenClaw version is irrelevant to this reconstruction;
before any separately granted Gate D testing, the runtime must be deliberately updated or pinned
and subjected to a fresh capability probe and review.

### 18.8 M11 reviewed-plan control-plane allowlist reconciliation

**Observed held checkpoint.** The reviewed overlay at
`581de2abf430786a36f2612f97c623a19b61353f` was applied as the base of
`feat/2026-09-23-openclaw-convmem-m11-integration`; the exact 45-commit replay and the §18.7
pin/comment reconciliation are clean and pushed at preserved tip
`a11b7a2a793c68e4e6e83c2680b077389a817c5c`. The first M8 attempt stopped in the outer runner,
before source export, integration import, runtime launch or any test, with `allowlist_violation`
for exactly these four paths:

1. `docs/plans/ARCHITECTURE-openclaw-convmem-integration.md`
2. `docs/plans/EXECUTION-openclaw-convmem-integration.md`
3. `docs/plans/EXECUTION-openclaw-convmem-milestone-plan.md`
4. `docs/plans/STATUS-openclaw-convmem-integration.md`

The failure is expected from the §18.7 tree shape: those reviewed control documents differ from
the current-main product baseline, while the original runner applies the product-edit allowlist to
the entire baseline-to-source path delta. No product test failed, and no real OpenClaw or live-data
action occurred. The retained paused evidence is comparison input only; it is not an M8 run.

**M11-only classification rule.** Let `D` be the complete sorted tracked path delta from
`CODE_BASELINE_SHA` to the exact source commit, and let `C` be the exact four-path set above. For
M11 only, `C` is a closed set of reviewed control-plane inputs, not product implementation edits.
The outer runner must, before runtime verification, source export, integration import or tests:

1. require all and only the four named control-plane paths to be classified through this rule;
2. resolve the exact Kiro-reviewed `REVIEWED_OVERLAY_SHA` named in Ryan's resume grant as a commit;
3. require each `source_commit:path` and `REVIEWED_OVERLAY_SHA:path` entry to exist as the same
   regular Git blob, with identical object ID and mode `100644`;
4. fail closed on a missing path, extra classified path, invalid/unavailable commit, non-blob,
   symlink or other mode, unreadable tree entry, or any object-ID/mode mismatch; and
5. define the product delta as exactly `P = D - C`, then apply the existing
   `EDIT_ALLOWLIST_EXACT`, `EDIT_ALLOWLIST_PREFIXES`, `SCHEMA_ALLOWLIST`, `path_allowed()` and
   Gate-W second-layer denial to `P` without adding, removing or widening any product allowance.

No path prefix, glob, directory-wide exception, current-worktree byte comparison, content copied
from a test expectation, or best-effort fallback is permitted. A fifth plan, status or documentation
path remains an ordinary product-delta path and therefore fails the unchanged product allowlist.
The outer runner's existing `allowlist_changed_paths` value reports `P`; independent M11 evidence
records `D`, `C`, the two commits, modes and blob IDs so the subtraction is auditable.

**Source export and hash boundary.** The classification above changes only which paths are checked
by the product-edit allowlist. All four reviewed documents remain tracked members of the exact
source commit, are exported by the unchanged `git archive` source-export path, appear in the full
source inventory, and contribute their exact bytes and modes to `source_tree_sha256`. They are not
added to `GENERATED_EVIDENCE_SOURCE_RELS`, a component exclusion, the fixture-output exclusions or
any other hash omission. The edit allowlist remains distinct from the source/component inventories.

**Exact bounded implementation correction.** After exact-tip Kiro PASS and a new Ryan resume grant,
the implementation correction may change only these twelve product/test paths:

- `tests/fixtures/openclaw_strict/allowlist.py`;
- `tests/fixtures/openclaw_strict/constants.py`;
- `tests/test_openclaw_strict_packet_contract.py`; and
- the nine parent/overlay comment or docstring paths already enumerated in §18.7:
  `openclaw_strict_server.py`, `strict_projection.py`,
  `tests/fixtures/openclaw_strict/adversarial_matrix.py`,
  `tests/fixtures/openclaw_strict/audit_evidence.py`,
  `tests/fixtures/openclaw_strict/fixture_manifest.py`,
  `tests/fixtures/openclaw_strict/protocol_fixture/schema_field_sets.py`,
  `tests/test_mcp_openclaw_strict.py`, `tests/test_strict_projection.py`, and
  `tests/test_strict_projection_publisher.py`.

`constants.py` adds a separate exact `M11_CONTROL_PLANE_INPUTS` set and
`M11_REVIEWED_OVERLAY_SHA`; it repins `SEMANTIC_PARENT_SHA` to the new reviewed semantic-parent
commit and leaves `CODE_BASELINE_SHA`, every product allowlist, schema list, selector, deselection,
runtime hash and behavioral count unchanged. `allowlist.py` implements the closed validation and
subtraction above without changing `path_allowed()`. The packet-contract tests must prove: exact
four-path success; missing, extra-classified, unavailable-commit, non-regular-entry and blob/mode
mismatch rejection; a fifth plan path reaching and failing the unchanged product allowlist; the
unchanged Gate-W denial; and the four documents remaining in source export/inventory/hash coverage.
The nine other paths may change only parent/overlay identifiers in comments or docstrings. No
executable product behavior or selected-test logic changes.

**Preserved-branch application order.** The reconciliation branch starts at
`581de2abf430786a36f2612f97c623a19b61353f` and contains exactly two plan commits: first this
architecture/execution/STATUS semantic-parent commit, then the milestone-overlay commit that pins
that parent. Kiro reviews the second commit as `REVIEWED_OVERLAY_SHA`. After a new Ryan resume grant
names both commits and the preserved tip, Codex first proves the implementation branch is clean,
pushed and exactly at `a11b7a2a793c68e4e6e83c2680b077389a817c5c`. Grok then cherry-picks those
two plan commits in order, without merge, squash, edit or conflict resolution, pushes and stops.
Codex proves the resulting four source blobs equal `REVIEWED_OVERLAY_SHA:path` exactly and every
other byte still equals the preserved tip. Only after a commit-specific `CONTINUE` may Grok make
one correction commit limited to the twelve paths above, push and stop again. Any conflict,
unexpected path, rewritten history, missing reviewed blob or stale branch tip is `PAUSE`.

**Acceptance and authority boundary.** Codex independently repeats the exact four-blob comparison
after the correction, proves the existing product allowlist literals and every frozen selector,
deselection, dependency, permission, schema, runtime rule and T0–T5 semantic contract unchanged,
and verifies the full source export/inventory contains the reviewed documents before any M8 retry.
The prior failed attempt is never relabeled. Only a later Ryan resume grant may authorize runtime
rebinding, two fresh-root M8 runs, legacy regressions or Pylint. This correction authorizes no
product/test edit, M8 retry, merge, deployment, real OpenClaw action, Gate D/W/D-V/E/F, watch
activation, live data or promotion.

### 18.9 M11 Pylint regression-remediation boundary

**Observed held checkpoint.** Kiro passed the §18.8 parent/overlay and Ryan authorized its exact
application. The two reviewed plan commits, twelve-path control-plane correction and subsequent
node-count/leakage repairs are clean and pushed on
`feat/2026-09-23-openclaw-convmem-m11-integration` at
`9c6421a6891fd8a861a51f4fed410f541b53148c`. At that exact source commit:

- two fresh-root M8 runs passed with 238 strict passes, 29 Node passes, 115 legacy passes, one
  legacy skip and four exact deselections;
- their canonical node/outcome artifact, fixture manifest and normalized audit output matched
  byte-for-byte, with SHA-256 values `f1d01f0c0da0987c42186e8417f2ad0c3fdef807c9ee9696fa3cc7ecf93d7fcc`,
  `7c5fff027e710853bc0285b22d5ca6c25fb73203e1862530a239bcb116840dfe` and
  `4e46b6883871cff7739b4ed6010723eaca127f4787c14947ab8f4e5185f2235f` respectively;
- the seven legacy MCP files passed with 54 tests and six subtests; and
- the separately provisioned CI-compatible Pylint environment used CPython 3.12.13,
  Pylint 4.0.6 and pytest 9.1.1, then ran the unchanged workflow command against base
  `9193f5ec744f059d07a20612489b210527b5660a`.

The actual current-main regression gate failed. Its report contains 1,159 live findings versus
506 baseline occurrences and reports 344 increased fingerprints totaling 699 new occurrences:
532 path-specific occurrences in 38 files plus 167 aggregate `R0801/duplicate-code` occurrences.
The exact report SHA-256 is
`2b724b4ff79405ffb286452be6c17ebef7de4eaeabd6522985c4baaee605848b`; raw gate output SHA-256 is
`05d9a230689ba1addff6e1c35848567f71a3015d665d7b18236d110ffb0bbda3`. Both are retained under the
Ryan-designated evidence root at
`runs/9c6421a6891fd8a861a51f4fed410f541b53148c/m11-pylint-failed-current-main-baseline/`, whose
verified payload-manifest SHA-256 is
`302c0f3503fd4370397f9bf63f7485ffa41198c910794902666fd9238832bd27`. A diagnostic comparison to
preserved tip `a11b7a2a793c68e4e6e83c2680b077389a817c5c` found only twelve additional occurrences, all in
`tests/test_openclaw_strict_packet_contract.py`; that comparison is diagnostic only and never
substitutes for the actual current-main gate.

**Decision and trade-off.** M11 will remove the new lint debt. It will not create a
component-specific debt baseline, raise or regenerate `ci/pylint-baseline.json`, weaken the
regression algorithm, exclude the Switchboard files, lower Pylint sensitivity, or substitute a
preserved-tip comparison for the repository's real merge gate. This costs a larger bounded
correction now but preserves one CI contract for the whole repository and prevents today's debt
from becoming permanent ambient state. The following baseline artifacts must remain byte-identical
to baseline `9193f5ec744f059d07a20612489b210527b5660a`:

- `.github/workflows/pylint.yml` Git blob `fefcd313e21ccd9c924703f0c3e6ecaf0ca02a0f`;
- `ci/pylint-baseline.json` Git blob `97284472f6e41f9d7087438dca1ad4c15359312a`; and
- `scripts/pylint_regression_gate.py` Git blob `c337eb349dddfb861d56e8132c3cc3a55bd888e6`.

**Exact correction surface.** The remediation may change only the following 44 product/test paths.
The set is the union of the 38 files with path-specific regressions and six fixture modules that
participate only in new aggregate `R0801` pairs. No paired current-main module is editable merely
because Pylint named it in a duplicate-code message.

```text
bound_read_scope.py
mcp_server.py
openclaw_activation_controller.py
openclaw_activation_supervisor.py
openclaw_strict_server.py
strict_evidence_state.py
strict_grounding.py
strict_projection.py
strict_projection_publisher.py
tests/fixtures/openclaw_strict/adversarial_matrix.py
tests/fixtures/openclaw_strict/allowlist.py
tests/fixtures/openclaw_strict/audit_evidence.py
tests/fixtures/openclaw_strict/canonical_oracle.py
tests/fixtures/openclaw_strict/canonical_oracle_b.py
tests/fixtures/openclaw_strict/case58_oracle.py
tests/fixtures/openclaw_strict/component_inventory.py
tests/fixtures/openclaw_strict/constants.py
tests/fixtures/openclaw_strict/containment.py
tests/fixtures/openclaw_strict/digest_oracle.py
tests/fixtures/openclaw_strict/digest_oracle_b.py
tests/fixtures/openclaw_strict/fixture_manifest.py
tests/fixtures/openclaw_strict/fixture_platform.py
tests/fixtures/openclaw_strict/inventory.py
tests/fixtures/openclaw_strict/lifecycle_scripts.py
tests/fixtures/openclaw_strict/limits.py
tests/fixtures/openclaw_strict/preflight.py
tests/fixtures/openclaw_strict/protocol_fixture/pinned_vectors.py
tests/fixtures/openclaw_strict/protocol_fixture/schema_contract.py
tests/fixtures/openclaw_strict/protocol_fixture/schema_field_sets.py
tests/fixtures/openclaw_strict/protocol_fixture/schema_instances.py
tests/fixtures/openclaw_strict/protocol_fixture/specimens.py
tests/fixtures/openclaw_strict/run_isolated.py
tests/fixtures/openclaw_strict/suites.py
tests/test_bound_read_scope.py
tests/test_mcp_openclaw_strict.py
tests/test_openclaw_activation_controller.py
tests/test_openclaw_activation_supervisor.py
tests/test_openclaw_strict_packet_contract.py
tests/test_strict_evidence_state.py
tests/test_strict_grounding.py
tests/test_strict_projection.py
tests/test_strict_projection_publisher.py
tests/test_strict_projection_recovery.py
tests/test_strict_snapshot_revocation.py
```

The new reviewed parent/overlay identifiers may be repinned only in the same fields and existing
comments/docstrings already authorized by §18.8. The exact 44-path set subsumes those paths; it does
not widen any runtime edit allowlist, schema list, test selector or product interface.

**Resolution hierarchy.** Grok applies these rules in order; it does not choose a weaker route:

1. Correct semantic/static defects and mechanical style findings without changing observable
   behavior, public interfaces, serialized bytes, schema fields, refusal effects, permissions,
   test selection or expected outcomes.
2. Remove unused/reimported names and improve annotations or private decomposition. Complexity
   findings are resolved through private helpers inside an already allowed module; no new module,
   dependency or cross-boundary helper is permitted.
3. A local Pylint suppression is allowed only for a demonstrated static-analysis false positive or
   an intentional white-box test access. It must name one exact message ID, cover the smallest
   statement or block Pylint supports, include an adjacent invariant rationale, and be listed in
   evidence. `disable=all`, `skip-file`, category-wide disables and file-wide suppressions are
   forbidden except for the two closed, exact-message cases below.
4. `C0302/too-many-lines` is inherently module-scoped. An exact-message module suppression is
   allowed only in the twelve files where the frozen report already contains that finding:
   `mcp_server.py`, `openclaw_activation_controller.py`, `strict_evidence_state.py`,
   `strict_grounding.py`, `strict_projection.py`, `strict_projection_publisher.py`,
   `tests/fixtures/openclaw_strict/audit_evidence.py`,
   `tests/test_openclaw_activation_controller.py`,
   `tests/test_openclaw_strict_packet_contract.py`, `tests/test_strict_grounding.py`,
   `tests/test_strict_projection.py`, and `tests/test_strict_projection_publisher.py`. The adjacent
   rationale must name the preserved module/component or collected-node boundary. No other message
   ID is covered by this exception, and no thirteenth file may use it.
5. `R0801/duplicate-code` is special: production modules and `tests/test_*.py` must remove the new
   duplicate structurally without sharing authority or oracle logic. Region-scoped suppression is
   allowed only in the exact reference-owned fixture modules
   `canonical_oracle.py`, `canonical_oracle_b.py`, `digest_oracle.py`, `digest_oracle_b.py`,
   `case58_oracle.py`, `component_inventory.py`, `fixture_manifest.py`, `pinned_vectors.py`,
   `schema_field_sets.py`, `schema_instances.py`, or `specimens.py`, and only where sharing code
   would destroy the fixture's independent-oracle or frozen-specimen role. If Pylint cannot scope
   `R0801` below a module, an exact-message module suppression in one of those eleven files is the
   only permitted file-level exception. No production helper may become the fixture's oracle.
6. The final full-tree report must contain no new or increased fingerprint relative to the exact
   current-main baseline. A merely lower total, a preserved-tip PASS, or a targeted-file PASS is
   insufficient.

**Identity and behavior boundary.** Source bytes and therefore component/source hashes may change
only as the deterministic result of the 44-path remediation. Hash algorithms, member sets,
canonicalization and inventory rules remain unchanged; final evidence binds the new exact hashes.
Collected test node IDs, the four deselections, counts/outcomes and the three-tool surface remain
identical to the accepted `9c6421a` evidence. Independent oracles must remain independent. No
redistillation, schema migration, permission change, new dependency, OpenClaw installation/update,
real runtime action, durable-memory write or live-data access is part of this correction.

**Acceptance and authority boundary.** After exact-tip Kiro PASS, a new Ryan grant must name this
parent, the final milestone overlay, source tip `9c6421a6891fd8a861a51f4fed410f541b53148c`, the exact
44 paths, implementation branch, current-main baseline, new parent-bound runtime prefix and durable
evidence root. The plan application is the complete linear first-parent range after
`c5513d50b656f9cc9e6423ea819438f975d16ee5` through the final milestone-overlay commit named in
Ryan's grant, oldest to newest. The range must contain no merge, gap, reordered commit, or commit
outside the four reviewed planning/STATUS documents. Grok applies that reviewed range in order and
stops. Only after Codex proves the four reviewed document blobs and issues a commit-specific
`CONTINUE` may Grok perform the bounded
remediation in the held checkpoints defined by Execution §10.7. Any 45th path, baseline/gate/config
change, broad suppression, behavior change or unsupported finding classification is `PAUSE`.

Final acceptance requires the unchanged current-main Pylint regression gate to pass on the exact
clean pushed tip, §18.10's repository-wide pytest differential verdict, two new fresh-root M8
passes, the seven legacy MCP regressions, exact source/component inventories and a Kiro exact-tip
conformance PASS. Ryan alone decides PR/merge. Gate D/W/D-V/E/F,
real OpenClaw, watch activation, live data, deployment and promotion remain independently blocked.

### 18.10 M11 full-pytest applicability and differential boundary

**Observed applicability failure.** The 44-path remediation and its bounded behavioral repairs are
clean and pushed at candidate
`3f8ef8312e3f3c98915320bd1b988bac5d8d96a9`. At that exact candidate, the unchanged current-main
Pylint gate passes with 461 findings and 240 fingerprints and no new/increased fingerprint. The
first complete pytest attempt reported 118 failures, 2,783 passes, four skips, seven errors and 262
subtests. Independent diagnostics showed at least three structural failures at both the candidate
and the preserved pre-remediation tip: the strict packet test requires the isolated runner role,
the CI Python provides Unicode 15.0 while the frozen strict projection requires Unicode 15.1, and
the R2b inventory binds a different source revision. Those failures are not caused by the lint
remediation, but they also are not a full-pytest PASS. The unconditional PASS claim is therefore
inapplicable and is replaced, not waived, by the rule below.

**Observed first differential pause.** Under the reviewed rule, Codex applied the plan-only range
to the preserved candidate and pushed exact candidate
`853ef98ede44f2d171e5354b065e11f83558e010`. Complete baseline and candidate runs each collected
the same 2,912 nodes and produced the same outcome totals: 2,763 passed, 64 skipped, 85 failed and
zero errors. The comparator nevertheless found 28 signature mismatches and correctly emitted
`PYTEST_DIFFERENTIAL_PASS=false`, `FULL_PYTEST_PASS=false` and `PAUSE`. Twenty-two strict-packet
signatures contained different `HOME`/XDG path bytes and pytest representation truncation; one
watch golden-oracle signature changed only because unequal source-root lengths moved the
representation truncation boundary; and five exact R2b nodes exposed a real authority-content
identity rotation across the frozen remediation. The durable PAUSE ledger is
`PAUSE-ledger.json`, SHA-256
`3c2a50d1a61578fa235524bc26493a2b1458ba60d729b039c0a66d27ddce0c1e`, under the candidate's
Ryan-designated `m11-full-pytest-differential-pause/` evidence directory. It is an input to this
correction, not a passing result. No symmetric mismatch rerun, Pylint rerun, M8 run or MCP
regression ran after the PAUSE.

**Frozen comparison identities and environment.** The baseline is exactly
`PYTEST_DIFFERENTIAL_BASE_SHA=9c6421a6891fd8a861a51f4fed410f541b53148c`. The candidate is the
exact clean pushed source commit named in the later Ryan resume grant. The remediation input is
`3f8ef8312e3f3c98915320bd1b988bac5d8d96a9`; the first paused differential candidate is
`853ef98ede44f2d171e5354b065e11f83558e010`. A later candidate is eligible only when its non-plan
bytes equal `853ef98` and its plan delta is the exact Kiro-reviewed range named by Ryan.

Codex runs both tips sequentially through one predeclared disposable execution slot in the same
separately reviewed CI-compatible environment. The absolute `source/`, `state/`, `pytest-tmp/`
and `report/junit.xml` path strings, working directory, argv and allowlisted environment bytes are
identical for the baseline and candidate and for both sides of every mismatch rerun. Before each
process Codex closes every prior process, durably preserves the preceding evidence, removes only
the prevalidated execution-slot children, recreates them empty with the same modes, and records an
independent empty-tree and no-symlink proof. It then exports the exact Git tree into the same
`source/` pathname, verifies every tracked path/blob/mode against `git ls-tree`, fixes or proves
equal every filesystem attribute not represented by Git, and creates byte-identical empty HOME,
XDG cache/config/data, `CONVMEM_CONFIG` and pytest-temp state at the same pathnames. Any retained
entry, shared mutable cache, path difference, source inventory mismatch against that tip's exact
Git tree, source difference outside the frozen baseline-to-candidate delta, unlisted environment
variable or reset asymmetry is `PAUSE`. Reusing path strings never means retaining contents.

The environment has one dependency/runtime inventory hash, Python and pytest versions, locale,
timezone, resource limits and command. No host fallback, live ConvMem data, credentials, user
configuration or OpenClaw process is allowed. The complete-suite command is the workflow's
unchanged `python -m pytest -q` plus only pytest's built-in output-only
`--junitxml=<the-fixed-slot-report-path> -o junit_family=xunit1` reporter arguments. They change
neither selection nor behavior. Every run uses a fresh process and a freshly reconstructed slot;
no source edit occurs between runs.

**Closed comparison record.** Codex constructs one canonical record per JUnit `testcase` using the
exact tuple `(file, classname, name)` as the node identity, the outcome vocabulary
`passed|skipped|failure|error`, and, for `failure` or `error`, the exact element `type` and
normalized `message` attributes as the failure signature. Normalization is limited to replacing
the fixed absolute disposable checkout root with `$SOURCE_ROOT`, the fixed pytest temporary-root
path with `$PYTEST_TMP`, and the exact baseline or candidate 40-hex Git object ID with
`$SOURCE_COMMIT`.
Nothing else is removed or rewritten: in particular, exception types, assertion text, error codes,
line numbers, expected/actual semantic values and 64-hex content hashes remain significant. An
absent/duplicate testcase, XML parse error, unknown outcome, collection interruption or reporter
disagreement with the raw terminal summary is `PAUSE`.

**Closed R2b authority-content identity disposition.** This is not another normalization. Raw
messages and every 40-hex token remain in the canonical evidence. The primary comparator still
reports the changed signatures. Only the following five exact node identities may enter the
secondary disposition; no prefix, file-wide rule, glob or sixth node is permitted:

1. `tests/test_r2b_v2_corrective_viii.py::R2bV2CorrectiveVIIIIdentityTests::test_committed_inventory_matches_authority_content_identity`
2. `tests/test_r2b_v2_corrective_viii.py::R2bV2CorrectiveVIIIRegressionGuard::test_inventory_artifact_exists_on_disk`
3. `tests/test_r2b_v2_implementation_revision.py::R2bV2ImplementationRevisionTests::test_committed_inventory_matches_resolved_implementation_identity`
4. `tests/test_r2b_v2_implementation_revision.py::R2bV2ImplementationRevisionTests::test_production_coverage_uses_committed_inventory_without_dual_mock`
5. `tests/test_r2b_v2_implementation_revision.py::R2bV2ImplementationRevisionTests::test_regenerated_inventory_matches_on_disk_artifact`

For this exact comparison the committed inventory identity is
`6ec645794d92a7d25eff94c97318256e851433f0`; the independently resolved baseline authority-content
identity is `cb0e66b7aa3c3685439c564e7f888c6d714742bf`; and the independently resolved candidate
identity is `0a8fe0b371744e9ad367f18979ef9367bb37fd34`. Codex must retain each raw assertion and parse it
into `(node identity, failure outcome, type, operand orientation, committed identity, resolved
identity)` using only the exact two-operand unittest equality-diff form observed here. The outcome,
type, framing, operand orientation and committed identity must match at both tips; the only allowed
difference is the resolved identity changing from the frozen baseline value to the frozen candidate
value.

The resolved values require independent content proof at each tip. Codex emits the complete
authority-content manifest, proves its governed-path member set is equal between tips, verifies
every member's bytes against the exact Git tree, proves every changed governed member is inside the
already-reviewed 44-path remediation and that every other governed member is byte-identical, then
independently recomputes
`sha256("r2b-v2-authority-content:v1:" + canonical_manifest)[:40]`. That standard-library digest
must equal both the fresh production resolver output and the exact token in every applicable raw
failure. The reviewed inputs freeze 118 governed members with ordered-path-set SHA-256
`7798b5d54cf3e1883c707ed73a80b7891e73f142933e71e05c89535314b2161b`. Exactly one governed
member changes: `mcp_server.py`, from content SHA-256
`1c94463de9f5035d4a19b2ad42939d9e8c70c59737f3a6fe6a6f9239e37fa2e1` to
`7fcbdcb4cdcfc635d2787cea10d031dcd9aed40f6678ab80fc772194aaf55123`; it is inside the frozen
44-path remediation. A plan document may not enter the authority manifest. A member-set change,
second changed governed member, different
committed identity, unexpected token, extra assertion text, different type/outcome/orientation,
generic 40-hex or 64-hex substitution, product-byte change after `853ef98`, or disagreement between
either oracle is `PAUSE`. Passing this disposition records five retained stale-inventory failures;
it does not make the inventory current or make any node pass.

**Fail-closed verdict.** The candidate earns exactly `PYTEST_DIFFERENTIAL_PASS`, never
`FULL_PYTEST_PASS`, only when all of the following hold:

1. The complete candidate and baseline node-identity sets are equal. No candidate node may be
   absent from the baseline, and no baseline node may disappear from the candidate.
2. A baseline `passed` or `skipped` node may not become candidate `failure` or `error`. No
   candidate-only failing/error node is permitted.
3. A node failing/erroring at both tips must have the same normalized failure signature, except
   that one of the five exact R2b nodes may remain a mismatch pending the closed secondary
   disposition above. A changed exception class, assertion/error message or failure/error phase is
   otherwise a mismatch.
4. Every outcome or signature mismatch from the complete runs is rerun independently at both tips,
   one node at a time in fresh processes using the same environment. The complete-run evidence is
   retained. The mismatch clears only as one of three closed dispositions: both reruns are
   non-failing (`passed` or `skipped`); the baseline rerun fails/errors while the candidate rerun is
   non-failing, recorded as a confirmed improvement; both reruns reproduce the same failure/error
   outcome and normalized signature, recorded as a retained failure; or one of the five exact R2b
   nodes reproduces and satisfies every closed identity proof above, recorded as a retained
   source-identity-rotation failure. A baseline
   non-failure becoming a candidate failure/error, a changed candidate failure signature, any
   other result, collection difference, non-reproduction or environmental asymmetry is `PAUSE`;
   a targeted rerun never substitutes for either complete run.
5. Every identical retained failure is listed by node identity and normalized signature, linked to
   both raw runs, and labeled repository debt outside this remediation's acceptance claim. It is
   never called a full-pytest PASS, never silently discarded and never used to waive the unchanged
   Pylint gate, either fresh M8 run or any of the seven MCP regressions.

The canonical base/candidate records, mismatch list, independent reruns, raw stdout/stderr/status,
JUnit XML, environment/reset inventories, authority manifests and independent identity proofs are
copied to the Ryan-designated durable evidence root with a verified volatile-to-durable mapping. A
passing differential verdict establishes only
that the bounded M11 correction added no repository-wide pytest regression relative to its exact
pre-remediation input. It does not certify the retained failures, change their ownership, authorize
a test/CI/baseline edit or weaken any existing gate.

**Authority boundary.** This correction changes plans only. Kiro must review the exact new parent
and milestone overlay. Ryan must then issue a new resume grant naming both, the baseline and
candidate identities, environment and evidence roots, the unchanged 44 paths, Pylint/M8/MCP
requirements and this differential authority. No previous grant authorizes another test run or
source edit. Gate D/W/D-V/E/F, real OpenClaw, watch activation, live data, merge, deployment and
promotion remain independently blocked.

### 18.11 M11 final M8 authority-packet identity reconciliation

**Observed held checkpoint.** Under Ryan's reviewed differential grant, the plan range was applied
to the preserved candidate and the clean pushed integration tip became
`7f2a2e22c74cf9fd87c00982d1ea0ce18fc978af`. Its four planning-document blobs equal reviewed
overlay `b1b2341a4f98701f5784631f866c5405174c7414`, and its non-plan bytes equal the preceding
candidate. The complete baseline/candidate comparison collected identical 2,912-node sets and
outcomes at both tips: 2,612 passed, 173 failed, 62 skipped and 65 errors. All 238 retained
failure/error nodes were closed as 233 identical repository-debt nodes plus the five §18.10 R2b
identity rotations. The resulting verdict is `PYTEST_DIFFERENTIAL_PASS=true` and
`FULL_PYTEST_PASS=false`; its canonical verdict SHA-256 is
`fd256daa5220882080c7f0c20f8d61bf74c124a1d893131c9044c2113ed6146d`. The unchanged
current-main Pylint gate also passes with 456 findings and no new or increased fingerprint; its
result SHA-256 is `ce5dffc895a5bd039b725fb76541ef232342508b4d67c5fa36ce915b98127559`.

The first final M8 execution then refused during argument validation with process status 2 and
`plan_sha_mismatch`. It created no fixture, imported no integration code and did not reach the
runtime. The runner correctly reported embedded parent
`b810fcd7ee545399a368afada2b0e7d9dd7821f6` while the authorized parent was
`9c5c2bf7d3c5b6d9f13d68329b6f7112c25cabe1`. The post-refusal runtime inventory remained
byte/mode-identical with tree SHA-256
`74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`. The durable PAUSE
classification SHA-256 is
`e217e5607640b5f1985ad57256f7911fc8b409364ecc25c5f98e22c25082105c`. M8 run 2 and the seven
legacy MCP regressions did not run.

**Cause and bounded correction.** The later reviewed planning revisions changed the exact
semantic-parent and control-plane overlay identities, while the accepted fixture deliberately
kept its previous authority packet. Only four executable test literals are stale: two declarations
and their two frozen assertions. After exact-tip Kiro PASS and a new Ryan grant, the implementation
correction may change only:

- `tests/fixtures/openclaw_strict/constants.py`: replace only the value of
  `SEMANTIC_PARENT_SHA` with the exact semantic-parent commit named in the grant and only the value
  of `M11_REVIEWED_OVERLAY_SHA` with the exact final overlay commit named in the grant; and
- `tests/test_openclaw_strict_packet_contract.py`: replace only the corresponding two expected
  40-hex literals in `test_plan_and_baseline_constants_frozen` with those same grant-named values.

No other byte in either file may change. No third product/test path may change. In particular,
`CODE_BASELINE_SHA`, `M11_CONTROL_PLANE_INPUTS`, `EXPECTED_TEST_RUNTIME_TREE_SHA256`, product and
schema allowlists, selectors, four deselections, dependencies, permissions, refusal behavior,
test logic, node IDs, outcomes and T0–T5 semantics remain unchanged. Source/component hashes may
change only as the deterministic consequence of these four literal replacements; their algorithms
and member sets remain unchanged. The correction binds the already-reviewed authority packet; it
does not grant new authority or alter the connector.

**Preserved-branch application order.** The plan branch starts at reviewed overlay
`b1b2341a4f98701f5784631f866c5405174c7414`. Kiro reviews the final milestone overlay and Ryan's
later grant names that exact overlay plus its semantic parent. Grok applies every commit in the
complete reviewed linear range after `b1b2341` through the grant-named final overlay, oldest to
newest, onto preserved clean pushed integration tip `7f2a2e22c74cf9fd87c00982d1ea0ce18fc978af`,
then pushes and stops. A merge, gap, reorder, squash, edit, conflict resolution, empty commit,
branch recreation, history rewrite or non-plan change is `PAUSE`. Codex must prove the four final
planning-document blobs equal the reviewed overlay and every non-plan byte equals `7f2a2e2`
before a commit-specific `CONTINUE` may authorize the four-literal correction. Grok then commits,
pushes and stops again; Codex proves the diff is exactly the two paths and four substitutions above.

**Fresh final-source evidence.** Evidence already produced at `7f2a2e2` remains valid historical
evidence for that exact source but is not silently transferred to a changed source tree. Codex
therefore repeats §18.10's complete baseline-versus-final-candidate differential in the identical
fixed slot and CI-compatible environment, including symmetric mismatch reruns and the closed
five-node R2b proof. It then reruns the unchanged current-main Pylint gate, executes M8 twice from
fresh roots using `--plan-sha` equal to the new semantic parent, runs the same seven legacy MCP
regression files, verifies the runtime remained unchanged and copies all evidence to the
grant-named durable root. Any new node/outcome/signature mismatch, authority-manifest drift,
Pylint regression, M8 count/identity deviation, MCP failure, runtime mutation or required source
change is `PAUSE`. The prior M8 refusal remains recorded and is never relabeled as a PASS.

**Authority boundary.** This section authorizes planning only. Kiro must PASS the exact parent and
overlay, and Ryan must issue a new resume grant naming them, `7f2a2e2`, the implementation branch,
baseline `9c6421a`, the fixed execution slot, runtime prefix, durable evidence root, PAUSE evidence
and its hash, exact two-file/four-literal correction, and complete final-evidence sequence. No
previous grant may be reused. Merge, deployment, real OpenClaw, Gate D/W/D-V/E/F, watch
activation, live data and promotion remain independently blocked.

### 18.12 M11 bundle-schema literal drift reconciliation

**Observed held checkpoint.** Kiro passed the §18.11 plan and Ryan granted its exact application,
two-file/four-literal authority-packet correction and Codex-owned evidence sequence. The resulting
clean pushed candidate is `d7b15926ab7e4e41b8a80edba5edbe4bfed4c165`; its four reviewed
planning-document blobs equal overlay `57285608b2ee9ec5950201968bc533b8830a6ea8`. The fresh
`9c6421a`-versus-candidate comparison again collected identical 2,912-node sets and outcomes at
both tips: 2,612 passed, 173 failed, 62 skipped and 65 errors. All 238 retained failure/error nodes
remain closed as 233 identical repository-debt nodes plus the five §18.10 R2b identity rotations.
The verdict remains `PYTEST_DIFFERENTIAL_PASS=true` and `FULL_PYTEST_PASS=false`; its canonical
verdict SHA-256 is `0e70c867e89d9b2bafb72e21749b2f3a6f460b28f4328162e9e29d3a8d79058a`.
The unchanged current-main Pylint regression gate also passes with 458 findings and no new or
increased fingerprint; its result SHA-256 is
`fae5e508e7db97c36e98d8a8b1d7652b1ff17c32c1a20cfa157ddb422afc9853`.

Final M8 run 1 then entered the unchanged isolated runner and completed all three frozen command
groups with process status 2: 210 strict tests passed and 28 strict tests failed, while all 29 Node
tests passed and the legacy group produced 115 passes, one skip and four deselections. Every strict
failure collapsed at the same production boundary to `StrictPublisherError("bundle_schema")`.
The canonical fixture schema, its JSON Schema, every fixture producer and the publisher's earlier
input classifier use `convmem.strict-fixture-bundle.v2`; only
`strict_projection_publisher.py`'s later validation check uses the invented
`convmem.strict-fixture-work.bundle.v2`. The durable PAUSE classification SHA-256 is
`c25ece6380d0b1cf4989a010419307dfdc29c2ecc31b9c4dd47faaee23b89148`; the independent
schema-drift proof SHA-256 is
`50a82638e4265c910dcdf7422d193bb6178ff29c51e175dd05fa1949cc4713d5`. Runtime post-run
revalidation remained byte/mode-identical at tree SHA-256
`74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`; its record hashes to
`d457b6150543310cec6a63dedb4699f21269a666af7ba17623bbf0bc321ed5e5`. M8 run 2 and the seven
legacy MCP regressions did not run.

**Cause and bounded correction.** This is a production validation typo, not a schema ambiguity or
test expectation problem. After exact-tip Kiro PASS and a new Ryan grant, the only product
correction permitted is this exact replacement in `strict_projection_publisher.py`:

```text
convmem.strict-fixture-work.bundle.v2
→ convmem.strict-fixture-bundle.v2
```

No other byte or path may change. No test edit is authorized: the existing M8 tests are the
regression harness and must turn green without adjustment. Schema files, fixture producers,
publisher control flow, exceptions, CLI behavior, selectors, four deselections, dependencies,
permissions, T0–T5 semantics, test node IDs and expected outcomes remain unchanged. Source and
component hashes may change only as the deterministic consequence of this literal replacement;
their algorithms and member sets remain unchanged.

**Preserved-branch application order.** This plan branch starts at reviewed overlay
`57285608b2ee9ec5950201968bc533b8830a6ea8`. Kiro reviews the final milestone overlay and Ryan's
later grant names that exact overlay plus its semantic parent. Grok applies every commit in the
complete reviewed linear range after `57285608` through the grant-named final overlay, oldest to
newest, onto preserved clean pushed candidate `d7b15926ab7e4e41b8a80edba5edbe4bfed4c165`, then
pushes and stops. A merge, gap, reorder, squash, edit, conflict resolution, empty commit, branch
recreation, history rewrite or non-plan change is `PAUSE`. Codex must prove the four final planning
document blobs equal the reviewed overlay and every non-plan byte equals `d7b1592` before a
commit-specific `CONTINUE` may authorize the literal correction. Grok then makes only the exact
replacement above, commits, pushes and stops; Codex proves the diff is one path and one literal.

**Fresh final-source evidence.** Evidence at `d7b1592` remains valid historical evidence for those
exact bytes but is not transferred to the corrected source tree. Codex therefore repeats §18.10's
complete `9c6421a`-versus-final-candidate differential in the identical fixed slot and
CI-compatible environment, including symmetric mismatch reruns and the closed five-node R2b
proof. It then reruns the unchanged current-main Pylint gate, executes M8 twice from separate
fresh roots using `--plan-sha` equal to the new semantic parent, runs the same seven legacy MCP
regression files, verifies the runtime remained unchanged and copies all evidence to the
grant-named durable root. Any new node/outcome/signature mismatch, authority-manifest drift,
Pylint regression, M8 count/identity deviation, MCP failure, runtime mutation or required source
change is `PAUSE`. The failed M8 run remains recorded and is never relabeled as a PASS.

**Authority boundary.** This section authorizes planning only. Kiro must PASS the exact parent and
overlay, and Ryan must issue a new resume grant naming them, `d7b1592`, the implementation branch,
baseline `9c6421a`, fixed execution slot, runtime prefix, durable evidence root, PAUSE evidence and
classification hash, exact one-file/one-literal correction, and complete final-evidence sequence.
No previous grant may be reused. Merge, deployment, real OpenClaw, Gate D/W/D-V/E/F, watch
activation, live data and promotion remain independently blocked.

### 18.13 M11 post-bundle authority-packet reconciliation

**Observed held checkpoint.** Kiro passed §18.12 and Ryan granted the complete six-commit reviewed
plan range, exact one-file/one-literal publisher correction and Codex-owned evidence sequence. The
resulting clean pushed candidate is `851edbe49b820bd4081809022b10f67c30fef47a`; its four planning
documents equal reviewed overlay `6b1b90b4865dc0b92e0ead470136eeebc3bd8447`, and its only source
delta after plan application is the authorized replacement of
`convmem.strict-fixture-work.bundle.v2` with `convmem.strict-fixture-bundle.v2` in
`strict_projection_publisher.py`. The fresh `9c6421a`-versus-candidate comparison again collected
identical 2,912-node sets and outcomes: 2,612 passed, 173 failed, 62 skipped and 65 errors. All 238
retained failure/error nodes remain closed as 233 identical repository-debt nodes plus the five
§18.10 R2b identity rotations. `PYTEST_DIFFERENTIAL_PASS=true`, `FULL_PYTEST_PASS=false`, and the
unchanged current-main Pylint gate passes with 458 findings and no new/increased fingerprint.

The first final M8 execution then refused during exact argument validation with process status 2:
`plan_sha_mismatch: expected 48c9ce01bf557ff95fd82b84c3b0ab2e7e9f18cb`. The reviewed command
correctly supplied §18.12 semantic parent `b46a16a3cdc928e98fba83cd64b17439d1734695`, but the
unchanged fixture authority packet still declared parent `48c9ce01…` and overlay `57285608…` from
the preceding §18.11 reconciliation. The refusal occurred before source export, fixture creation,
integration import or runtime use. Runtime inventories before and after are byte-identical at tree
SHA-256 `74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`. The durable PAUSE
classification SHA-256 is
`3fbfab4bac23c30325961d21a974ec4ed03229759c1b974686d323c061982c77`. M8 run 2 and the seven
legacy MCP regressions did not run.

**Cause and bounded correction.** Section 18.12 intentionally authorized no test change, so its
new semantic-parent and final-overlay identities could not be reflected in the fixture authority
packet. The publisher correction itself is complete and unchanged. After exact-tip Kiro PASS and
a new Ryan grant, the only subsequent correction permitted is exactly four 40-hex substitutions:

- in `tests/fixtures/openclaw_strict/constants.py`, replace only the value of
  `SEMANTIC_PARENT_SHA` with the exact semantic-parent commit named in the new grant and only the
  value of `M11_REVIEWED_OVERLAY_SHA` with the exact final-overlay commit named in that grant; and
- in `tests/test_openclaw_strict_packet_contract.py`, replace only the corresponding two expected
  literals in `test_plan_and_baseline_constants_frozen` with those same grant-named values.

No other byte or path may change. The already-corrected publisher literal must remain exactly
`convmem.strict-fixture-bundle.v2`. `CODE_BASELINE_SHA`, `M11_CONTROL_PLANE_INPUTS`, the runtime
hash, schema/product allowlists, selectors, four deselections, dependencies, permissions, refusal
behavior, test logic, node IDs, outcomes and T0–T5 semantics remain unchanged. Source/component
hashes may rotate only as the deterministic consequence of these four literal substitutions;
their algorithms and member sets remain unchanged.

**Preserved-branch application order.** This plan branch starts at reviewed overlay
`6b1b90b4865dc0b92e0ead470136eeebc3bd8447`. Kiro reviews the final milestone overlay and Ryan's
later grant names that exact overlay plus its semantic parent. Grok applies every commit in the
complete reviewed linear range after `6b1b90b4` through the grant-named final overlay, oldest to
newest, onto preserved clean pushed candidate `851edbe49b820bd4081809022b10f67c30fef47a`, then
pushes and stops. A merge, gap, reorder, squash, edit, conflict resolution, empty commit, branch
recreation, history rewrite or non-plan change is `PAUSE`. Codex proves the four final planning
document blobs equal the reviewed overlay and every non-plan byte equals `851edbe4` before a
commit-specific `CONTINUE` may authorize the four substitutions. Grok then commits, pushes and
stops again; Codex proves the diff is exactly the two paths and four substitutions above.

**Fresh final-source evidence.** Evidence at `851edbe4` remains valid historical evidence for
those exact bytes but is not transferred to the newly rebound source tree. Codex repeats §18.10's
complete `9c6421a`-versus-final-candidate differential in the identical fixed slot and
CI-compatible environment, including symmetric mismatch reruns and the closed five-node R2b
proof. It then reruns the unchanged current-main Pylint gate, executes M8 twice from separate
fresh roots using `--plan-sha` equal to the new semantic parent, runs the same seven legacy MCP
regression files, verifies the runtime remains unchanged and copies all evidence to the
grant-named durable root. Any new node/outcome/signature mismatch, authority-manifest drift,
Pylint regression, M8 count/identity deviation, MCP failure, runtime mutation or required source
change is `PAUSE`. The pre-fixture M8 refusal remains recorded and is never relabeled as a PASS.

**Authority boundary.** This section authorizes planning only. Kiro must PASS the exact new parent
and overlay, and Ryan must issue a new resume grant naming them, `851edbe4`, the implementation
branch, baseline `9c6421a`, fixed execution slot, runtime prefix, durable evidence root, PAUSE
evidence and classification hash, exact two-file/four-literal correction, and complete
final-evidence sequence. No previous grant may be reused. Merge, deployment, real OpenClaw,
Gate D/W/D-V/E/F, watch activation, live data and promotion remain independently blocked.

### 18.14 M11 current-main drift reconciliation

**Observed merge hold.** Candidate
`cd60cf19dca6706e4175e9f82c9ba55e41bca10b` is clean and pushed on
`feat/2026-09-23-openclaw-convmem-m11-integration`. Its final authority-packet correction,
repository-wide differential, unchanged Pylint gate, two fresh M8 runs, seven legacy MCP
regressions and durable-evidence verification passed, and Kiro returned exact-tip PASS. No PR or
merge followed. After a fresh fetch, `origin/main` was
`a92a74eb326b3eaa59087b707de10153c7cc0c63`, twelve commits beyond the evidence baseline
`9193f5ec744f059d07a20612489b210527b5660a`; the candidate is 105 commits ahead of current main.
The current-main range changes 40 tracked paths, including Chroma write-guard and watch safety
work. A three-way merge reproduces conflict markers in
`docs/plans/STATUS-openclaw-convmem-integration.md`. Resolving that conflict or merging the old
candidate directly would change a reviewed control-plane blob and the full tracked source hash.
The prior PASS remains valid historical evidence for `cd60cf19`; it is not merge authorization for
the new tree.

**Closed path algebra.** Let `B` be historical integration baseline `9193f5ec…`, `N` be exact
current main `a92a74e…`, `R` be reviewed candidate `cd60cf1…`, and `C` be the exact four paths in
§18.8. Let `M = paths(B..N)`, `D = paths(B..R)`, and `P = D - C`, with paths sorted as raw UTF-8
bytes and hashed as their NUL-terminated sequence. The independently observed identities are:

- `M`: 40 paths, SHA-256
  `596a484cbf550a63bf77ac559733455aceadef75aaa5d3d8a6fee417b6695e6b`;
- `D`: 124 paths, SHA-256
  `af1b9fd8a991fe689cf8819f03bb1e6417ff159c91677d70417f289cea53b314`;
- `P`: 120 paths, SHA-256
  `60903bc194bd6e471f6c7009df30ab0832cad7a5505e9fd14b2c64450d27c659`; and
- `M ∩ D` is exactly `docs/plans/STATUS-openclaw-convmem-integration.md`, while
  `M ∩ P` is empty. `P` contains no deletion.

These values are preconditions, not implementation-derived expectations. A different base, tip,
count, path digest, intersection or deletion is `PAUSE`; Grok does not update the plan to fit it.

**Deterministic reconstruction.** After Kiro PASS and a new Ryan grant, Codex creates a new branch
and dedicated worktree at exact `N`; the reviewed 105-commit branch is preserved and never rebased,
merged, force-pushed or rewritten. Grok then performs three held commits:

1. Set exactly the 120 `P` paths to the regular-file/blob modes and bytes at `R`, using the pinned
   Git trees as the source. No path outside `P` changes. Push and stop.
2. Set exactly the four `C` paths to the regular mode `100644` and blob bytes at the final
   Kiro-reviewed milestone overlay named by Ryan. Push and stop.
3. In only `tests/fixtures/openclaw_strict/constants.py` and
   `tests/test_openclaw_strict_packet_contract.py`, make exactly six 40-hex substitutions: bind
   `CODE_BASELINE_SHA` and its assertion to `N`, bind `SEMANTIC_PARENT_SHA` and its assertion to
   the new reviewed semantic parent, and bind `M11_REVIEWED_OVERLAY_SHA` and its assertion to the
   new reviewed overlay. Push and stop.

Codex issues a commit-specific `CONTINUE` after each held commit. It proves every path outside
`P ∪ C` equals `N`; every `P` path except the two identity files equals `R` by blob ID and mode;
the two identity files differ from `R` only by the six substitutions; and every `C` path equals the
reviewed overlay by blob ID and mode. No merge, cherry-pick, rebase, conflict resolution, path
deletion, product reimplementation or test-logic edit is permitted. This exact tree composition,
not commit-message similarity or worktree byte sampling, is the reconstruction contract.

**Current-main differential.** Historical §18.10 evidence is retained, but final merge-readiness
uses a fresh complete-pytest comparison between exact `N` and the reconstructed candidate in the
same fixed disposable slot, runtime, argv and allowlisted environment. The baseline node set must
be a subset of the candidate node set. A candidate-only node is permitted only when its source
path is a test path in exact `P`, and it must finish `passed` or `skipped`; a baseline-only node,
candidate-only failure/error, collection interruption, duplicate identity or unknown outcome is
`PAUSE`. Every common baseline `passed` or `skipped` node must remain non-failing. Every common
failure/error must retain its exact §18.10 normalized signature or clear through the same symmetric
fresh-process rerun rules. Retained failures remain explicit debt, and any retained failure keeps
`FULL_PYTEST_PASS=false`; the only positive token is `CURRENT_MAIN_DIFFERENTIAL_PASS`.

The sole closed signature exception remains the five exact R2b nodes enumerated in §18.10. At
`N`, the committed and independently resolved authority-content identity is
`644552c552d655810d6834ef00c54fd8e3512950`. In the deterministic reconstructed product tree it is
`3a74d3db553308e40c00c60ec16d9bd1489133c2`. Both manifests contain exactly 119 ordered members
with path-set SHA-256
`cd13b301320ebbfe15d13843160e8d93c5cdbf707fa357c3e56c226f87967cfb`; exactly one member changes:
`mcp_server.py`, from SHA-256
`f9ac448cf8ecbb9c8822f327a79a7af753685458ea1cd71e0dbed9c0fae85cb3` to
`7fcbdcb4cdcfc635d2787cea10d031dcd9aed40f6678ab80fc772194aaf55123`.
The candidate committed inventory remains `644552c…`; only those five nodes may retain the exact
committed-versus-resolved identity rotation after both standard-library manifest recomputation and
production-resolver agreement. Generic 40/64-hex normalization, a member-set change, a second
changed member, a sixth node or a different operand/outcome/type is `PAUSE`.

**Fresh acceptance and merge boundary.** After the differential passes, Codex runs the unchanged
full-tree Pylint gate with the protected workflow, baseline and gate-script blobs from §18.9; two
fresh-root M8 runs using the new semantic parent and `N` as `CODE_BASELINE_SHA`; and the same seven
legacy MCP regressions. M8 must preserve 238 strict passes, 29 Node passes, 115 legacy passes, one
skip, four deselections, exact node/outcome identity and all source/component/runtime invariants.
The runtime tree must remain
`sha256:74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`.
All evidence is copied to the grant-named durable root with verified hashes, then Kiro reviews the
exact integrated tip and evidence.

Immediately before PR creation and again before Ryan's merge decision, Codex fetches origin and
requires `origin/main == N`; any movement is `PAUSE`, not an inferred rebase. A squash merge is
eligible only if GitHub's predicted result tree is byte-for-byte the reviewed candidate tree over
exact base `N`; history preservation is not required. Agents do not merge. Ryan alone decides PR
creation and merge. Real OpenClaw, deployment, Gate D/W/D-V/E/F, watch activation, live data and
promotion remain independently blocked.

**Authority boundary.** This section authorizes planning only. It changes no product, test,
runtime, CI, baseline, configuration or evidence byte. Kiro must PASS the exact new semantic
parent and milestone overlay. A new Ryan grant must then name them, `B`, `N`, `R`, the new
implementation branch, fixed slot, parent/baseline-bound runtime and durable evidence roots, path
counts/digests, exact three-commit reconstruction, six substitutions and full evidence sequence.
No previous grant, Kiro verdict or `CONTINUE` may be reused.

### 18.15 M11 current-main differential applicability reconciliation

**Observed governed PAUSE.** Ryan authorized §18.14's deterministic reconstruction and evidence
sequence. The three held commits are clean, pushed and preserved on
`feat/2026-09-26-openclaw-convmem-m11-main-reconciliation` at
`30bc134d74d7eeb4cef4d6371a5e96c926f0f2ca` (`H0`). Independent Git-tree checks re-proved exact
`M/D/C/P` membership, the 120-path product transplant, four reviewed control-plane blobs, six
identity substitutions and unchanged `origin/main` at
`a92a74eb326b3eaa59087b707de10153c7cc0c63` (`N`). The qualified runtime remained byte-identical.
Complete pytest collection and execution then finished at both `N` and `H0`; this was not a crash,
partial collection or environment asymmetry.

The exact results were:

- `N`: 2,686 nodes — 2,469 passed, 62 skipped, 90 failed and 65 errored;
- preserved reviewed Switchboard candidate
  `cd60cf19dca6706e4175e9f82c9ba55e41bca10b` (`R`): 2,912 nodes — 2,612 passed,
  62 skipped, 173 failed and 65 errored; and
- `H0`: 2,924 nodes — 2,624 passed, 62 skipped, 173 failed and 65 errored.

Every `N` node exists in `H0`. Exactly 238 `H0` nodes are absent from `N`; all 238 already exist
in `R`, and their outcomes match `R` exactly: 160 passed and 78 failed, with no skip or error.
The five common `N`/`H0` outcome rotations are exactly the closed §18.10 R2b nodes. Across the
2,871 identities common to `R` and `H0`, there is no outcome mismatch. The historical `R` and
current `H0` runs used different fixed-slot path bytes, so their failure-signature strings are not
accepted as a cross-run oracle; the comparison must be repeated with all applicable tips in one
identical slot.

The sealed PAUSE evidence is under
`/home/lauer/.local/share/convmem-openclaw-evidence/33767acaf563c25e8fbd9984f08316f1ba4b1b27/a92a74eb326b3eaa59087b707de10153c7cc0c63/runs/30bc134d74d7eeb4cef4d6371a5e96c926f0f2ca/m11-current-main-pytest-differential/`.
Its canonical comparison has SHA-256
`03873a4d4e368e5b5fd3de86140e3fd9b74525c3e83b966275d556fd9728693b`; its PAUSE ledger has
SHA-256 `3bd89ebf3dd016d5fc709215862ae491688cb878c3477fbd9f21f3619b2d256e`.
`CURRENT_MAIN_DIFFERENTIAL_PASS=false` and `FULL_PYTEST_PASS=false`; Pylint, M8 and MCP evidence
correctly did not run.

**Why §18.14's candidate-only rule is inapplicable.** `N` predates the entire Switchboard test
surface. Requiring every node absent from `N` to pass or skip makes the ordinary full-repository
pytest environment, which intentionally lacks the isolated runner's Unicode 15.1 and inner-role
conditions, retroactively authoritative for 238 already-reviewed Switchboard nodes. That neither
detects a reconstruction regression nor preserves the earlier honest debt classification. It
instead guarantees a false PAUSE on 78 known outcomes. The correction does not exclude those
nodes, change their tests, supply their isolated-runner environment to full pytest or relabel a
failure. It adds the only source tree that can be their pre-reconstruction oracle: `R`.

**Closed node identity.** For a record with identity `(file, classname, name)`, encode each UTF-8
field followed by one NUL byte, sort records lexicographically by the three raw UTF-8 fields, and
hash the concatenation. Let `S = nodes(F) - nodes(N)`, where `F` is the final candidate after the
reviewed plan application and authority-packet rebind below. `S` must contain exactly 238 identities
and hash to `fe50be2f51456d85efdf80305af83a7d0fa224110cd4980a27da74ed46e291b8`.
Appending the UTF-8 outcome plus one NUL after each identity must hash to
`2c03a11c8c5d66b822b406e35deb6874be0dd4301fe78d51780da96977b4c607`.
The 160 passed identities hash to
`b98f02f3f6d8b1c14b9d0e90e4dbb0f8e67e12698842ab37b381f5f4b2c35ae1`; the 78 failed identities
hash to `e3fdc26e69739af0ff33282378d02d6d930416daa8b89fc6964825ecd6e08423`.
These are predeclared observations from sealed evidence, not values the implementation may update.

**Three-tip authority partition.** Fresh evidence uses `N`, `R` and `F`; no one tip is allowed to
silently govern a node it never contained.

1. `N` remains the sole oracle for every identity it contains. `nodes(N)` must be a subset of
   `nodes(F)`. Common-node outcomes, normalized signatures, symmetric fresh-process reruns and the
   exact five-node R2b disposition remain §18.14 rules without change.
2. `R` is an oracle only for `S`, the identities present in `F` but absent from `N`. Every member
   of `S` must exist in `R` and match `R`'s outcome. A failed/error member must also match `R`'s
   exact §18.10-normalized failure signature after a symmetric rerun at both `R` and `F`.
3. Any `F` identity absent from both `N` and `R` must pass or skip and is separately listed. Under
   the sealed node set above there are zero such identities; a nonzero count is `PAUSE`.
4. Identities present only in `R` are listed as historical removals but do not override `N`'s
   current-main source ownership and are not injected into `F`.
5. All retained failures/errors remain explicit debt. Any retained failure keeps
   `FULL_PYTEST_PASS=false`. The only positive token is
   `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`.

The existing §18.10 normalization is closed and unchanged: exact source root, exact pytest temp
root and the exact tip's Git object ID only. Generic path, 40/64-hex, message or representation
rewriting is forbidden. All three complete runs use the same CI-compatible dependency closure,
allowlisted environment, argv, built-in xunit1 reporter, resource limits and fixed disposable path,
with a verified empty reset between tips. `R` must be executed freshly in that same slot; its old
evidence is diagnostic only. Every mismatch is rerun in fresh processes at both applicable tips.
Collection difference, reset/path asymmetry, incomplete JUnit, duplicate identity, unknown outcome,
unresolved signature difference or a sixth R2b exception is `PAUSE`.

**Plan application and final-source identity.** `H0` remains the preserved PAUSE input. After
exact-tip Kiro PASS and a new Ryan grant, Grok applies every commit in the complete reviewed linear
plan range from this correction's grant-named base overlay through its final overlay, oldest to
newest, onto `H0`, then pushes and stops. Codex proves the four planning-document blobs and modes
equal the final overlay and every non-plan byte still equals `H0`. Only after a commit-specific
`CONTINUE`, Grok changes exactly four 40-hex values across exactly two files: the
`SEMANTIC_PARENT_SHA` and `M11_REVIEWED_OVERLAY_SHA` declarations in
`tests/fixtures/openclaw_strict/constants.py` and their two frozen assertions in
`tests/test_openclaw_strict_packet_contract.py`. `CODE_BASELINE_SHA` remains `N`. No other byte,
test logic, product path or runtime content changes. The resulting pushed commit is `F`.

Only after the exact tree and four substitutions are independently verified may Codex run the
fresh `N`/`R`/`F` sequence. If `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` is established, the
unchanged §18.9 Pylint gate, two fresh-root M8 runs, seven legacy MCP regressions, durable-evidence
verification and exact-tip Kiro conformance review remain mandatory. The prior M8 counts,
deselections, selectors, dependencies, permissions, runtime hash, T0–T5 semantics and later-gate
blocks do not change.

**Authority boundary.** This section authorizes planning only. It authorizes no plan application,
identity edit, source/test/runtime/CI/configuration correction, suite, PR, merge, deployment or
real OpenClaw action. Kiro must PASS the exact new semantic parent and overlay. A new Ryan grant
must name them, `N`, `R`, `H0`, the fixed slot, runtime prefix, durable evidence root, complete
reviewed plan range, exact four substitutions and complete three-tip/Pylint/M8/MCP sequence.
Gate D/W/D-V/E/F, watch activation, live data and promotion remain independently blocked.

### 18.16 M11 current-main advance after the three-tip preflight

**Observed fail-closed preflight.** Kiro passed the §18.15 parent/overlay and Ryan granted its
held sequence. The reviewed plan commits and four-literal rebind were applied, independently
verified, pushed and preserved at
`d276cb4ab0a0613b965e772d49d378e761df337e` (`F0`). The four planning blobs matched reviewed
overlay `05e0d79712fdb7c9d2e5640b8c4a744d3f84e56b`; every other byte matched the preserved
`30bc134d` input except the exact four authorized identity substitutions. The unchanged qualified
runtime rebind also passed with 30,421 regular files, zero symlinks or writable entries and tree
SHA-256 `74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`.

Before the first complete pytest process, fixed-slot creation or new evidence-run directory, the
mandatory upstream check found `origin/main` at
`5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d` (`N1`) rather than the grant-frozen
`a92a74eb326b3eaa59087b707de10153c7cc0c63` (`N0`). The movement is the landed CPU-crash and
silent-vector-loss safety change; it is not a Switchboard result. The preflight therefore issued
`PAUSE` exactly as designed. No pytest, Pylint, M8 or MCP process ran, and no three-tip evidence
slot or run root was created. `F0`, the reviewed evidence tip
`cd60cf19dca6706e4175e9f82c9ba55e41bca10b` (`R`) and all prior evidence remain immutable
historical inputs, not acceptance evidence for `N1`.

**Closed advance and reconstruction algebra.** Let historical integration baseline `B` remain
`9193f5ec744f059d07a20612489b210527b5660a`; let `C` remain the exact four §18.8 control-plane
paths; let `D = paths(B..R)` and `P = D - C`; let `A = paths(N0..N1)`; and let
`Q = paths(N0..F0)`. Paths are sorted as raw UTF-8 bytes and hashed as their NUL-terminated
sequence. Independent Git-tree calculation freezes:

- `A`: 11 paths, SHA-256
  `0566d14e2246970abe77a89736db01a95ae89cb88d2c9556f33c14b6bf7c484c`;
- `Q`: 124 paths, SHA-256
  `af1b9fd8a991fe689cf8819f03bb1e6417ff159c91677d70417f289cea53b314`;
- `paths(B..N1)`: 45 paths, SHA-256
  `670241f7690afc18cf8689c7406ac6d86d395bfc323acfc5f2f72a85a46c853e`;
- `D`: 124 paths, SHA-256
  `af1b9fd8a991fe689cf8819f03bb1e6417ff159c91677d70417f289cea53b314`;
- `P`: 120 paths, SHA-256
  `60903bc194bd6e471f6c7009df30ab0832cad7a5505e9fd14b2c64450d27c659`;
- `A ∩ Q` is empty; `paths(B..N1) ∩ D` is exactly
  `docs/plans/STATUS-openclaw-convmem-integration.md`; and
  `paths(B..N1) ∩ P` is empty. Neither `A` nor `P` contains a deletion.

The equal `D`/`Q` path-set hash states only that the same 124 relative paths differ in those two
ranges; it does not equate their bytes. Any moved source ref, different count/digest/intersection,
deletion, symlink or non-regular product member is `PAUSE`, not a value Grok may update.

**Second deterministic reconstruction.** After exact-tip Kiro PASS and a new Ryan grant, Codex
creates a new grant-named branch and dedicated worktree at exact `N1`. Neither `R`, `F0`, nor the
first reconstruction branch is rebased, merged, cherry-picked, force-pushed or used as the branch
base. Grok performs exactly three held commits:

1. Set exactly the 120 `P` paths to the regular-file/blob modes and bytes at `R`. Push and stop.
2. Set exactly the four `C` paths to mode `100644` and the exact bytes at the final Kiro-reviewed
   overlay named by Ryan. Push and stop.
3. In only `tests/fixtures/openclaw_strict/constants.py` and
   `tests/test_openclaw_strict_packet_contract.py`, make exactly six 40-hex substitutions: bind
   `CODE_BASELINE_SHA` and its assertion to `N1`, bind `SEMANTIC_PARENT_SHA` and its assertion to
   the new reviewed semantic parent, and bind `M11_REVIEWED_OVERLAY_SHA` and its assertion to the
   new reviewed overlay. Push and stop.

Codex issues a commit-specific `CONTINUE` after each held commit. Final composition requires every
path outside `P ∪ C` to equal `N1`; every `P` path except the two identity files to equal `R` by
Git blob ID and mode; those two files to differ from `R` only by the six substitutions; and all
four `C` paths to equal the reviewed overlay. No plan-range replay onto `F0`, merge, conflict
resolution, product reimplementation, test-logic change or fourth implementation commit is
permitted.

**Advanced R2b identity.** The authority-content manifest at `N1` contains exactly 120 ordered
members, path-set SHA-256
`fb062070b962265bfce6c2cc2b709eca4b2d5f7a8d1a516d5b3599bcb0361ec8`, and resolved identity
`b716152fbf725633a55371f6acf7ed5580a704bd`. The provisional reconstructed product has the same
120 members and path-set hash and resolved identity
`e060dce4eb3d51e0f4650ded8bd1aad4f2a34f4b`. Exactly one member changes:
`mcp_server.py`, from SHA-256
`f9ac448cf8ecbb9c8822f327a79a7af753685458ea1cd71e0dbed9c0fae85cb3` to
`7fcbdcb4cdcfc635d2787cea10d031dcd9aed40f6678ab80fc772194aaf55123`.
The final candidate inherits `N1`'s committed inventory identity; no inventory regeneration or
inventory edit is authorized. The exact five §18.10 R2b nodes remain the complete closed exception
set, now evaluated against these advanced identities. A 121st member, different path set, second
changed member, sixth node, different operand/outcome/type or generic identity normalization is
`PAUSE`.

**Fresh evidence and merge boundary.** Fresh complete pytest runs use `N1`, `R` and the newly
reconstructed final candidate `F` sequentially in one verified-empty fixed slot with identical
CI-compatible dependencies, argv, built-in xunit1 reporter, allowlisted environment and resource
limits. Section 18.15's authority partition and §18.10 normalization remain unchanged. In
particular, `S = nodes(F) - nodes(N1)` must still contain exactly 238 identities with identity
SHA-256 `fe50be2f…`, identity/outcome SHA-256 `2c03a11c…`, 160 passed identity SHA-256
`b98f02f3…` and 78 failed identity SHA-256 `e3fdc26e…`; every member must exist in freshly run
`R` and match outcome, and every retained failure must match the closed normalized signature after
symmetric fresh-process reruns. New-main nodes are governed only by `N1`. A node absent from both
`N1` and `R`, unresolved mismatch, collection difference, reset/path asymmetry, sixth R2b node or
new normalization is `PAUSE`. Retained failures remain explicit and keep
`FULL_PYTEST_PASS=false`; the only positive token remains
`CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`.

Only that PASS releases the unchanged §18.9 Pylint gate, two fresh M8 runs, seven legacy MCP
regressions, durable-evidence verification and exact-tip Kiro conformance review. The runtime tree,
M8 selectors/counts, four deselections, dependencies, permissions, T0–T5 semantics and later-gate
blocks remain unchanged. Immediately before PR creation and again before Ryan's merge decision,
Codex fetches and requires `origin/main == N1`; movement is another `PAUSE`. A squash merge is
eligible only when GitHub's predicted result tree over exact `N1` is byte-for-byte the reviewed
candidate tree. Agents do not merge; Ryan alone decides PR creation and merge.

**Authority boundary.** This section authorizes planning only. It changes no product, test,
runtime, CI, baseline, configuration or evidence byte. Kiro must PASS the exact new semantic
parent and milestone overlay. A new Ryan grant must name them, `B`, `N1`, `R`, `F0`, the new
implementation branch, fixed slot, parent/current-main-bound runtime and durable evidence roots,
path counts/digests, exact three-commit reconstruction, six substitutions and complete three-tip/
Pylint/M8/MCP sequence. No previous grant, Kiro verdict or `CONTINUE` may be reused. Gate
D/W/D-V/E/F, watch activation, live data, deployment and promotion remain independently blocked.

### 18.17 M11 inner-role failure-signature reconciliation

**Observed governed PAUSE.** The §18.16 reconstruction completed in three held commits and is
preserved, clean and pushed at `776a4ca3d4215490fb26b882dca2df9a41e0e03a` (`H1`). Complete
same-slot pytest runs then collected 2,702 nodes at advanced current main `N1`, 2,912 nodes at the
preserved reviewed candidate `R`, and 2,940 nodes at `H1`: respectively 2,485/62/90/65,
2,612/62/173/65 and 2,640/62/173/65 passed/skipped/failed/errored. The frozen 238-node
candidate-only partition remained exact: 160 passed and 78 failed with the identities, outcomes
and hashes already fixed by §§18.15–18.16. The exact five R2b mismatches also remained the closed
set. All 83 mismatch pairs were rerun symmetrically in 166 fresh processes.

The finalizer stopped with `rerun_complete_record_mismatch:7:preserved`. Exactly 22 nodes in
`tests/test_openclaw_strict_packet_contract.py` produced 44 raw complete-versus-rerun signature
mismatches because pytest's assertion introspection rendered `os.environ` with a different key
order or environment content. One of those nodes also differed between its preserved and final
isolated reruns because a random pytest temporary suffix appeared inside the rendered
`CONVMEM_CONFIG` value. The assertion meaning and result did not change. Codex sealed the PAUSE
ledger at:

```text
/home/lauer/.local/share/convmem-openclaw-evidence/538d37eb498e2d3bd497db33daa006520ad56d06/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/776a4ca3d4215490fb26b882dca2df9a41e0e03a/m11-three-tip-pytest-differential/comparison/PAUSE-ledger.json
```

Its SHA-256 is `a6a2d95b6f294ad3893ea39fa8c739b15a7ea172d2067757492c49abf49399a6`.
The diagnostic SHA-256 is
`115492f91adeaf71aa09afd81b66e863191d0e7306efdd2a51a1168633c0376d`; the PAUSE-manifest
SHA-256 is `78ac1cef55142892cdf75d2cad71a22a536519a4d27359fedba04881020e1c80`; the rerun-plan
SHA-256 is `15d082c9805943a11c4c6236c5f23e48bf64440aa8b60cda29b25c2ad55eddcd`; and the preliminary
comparison SHA-256 is `674f79845a763293128e5e2d95230c0ded1c296a42fa0365061e9f4a089f1f91`.
`CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS=false` and `FULL_PYTEST_PASS=false`; Pylint, M8 and
MCP did not run.

**Closed node set.** The only nodes eligible for the semantic projection below are exactly:

```text
tests/test_openclaw_strict_packet_contract.py::test_case57_fixture_legacy_identity_config_only
tests/test_openclaw_strict_packet_contract.py::test_case57_kernel_denial_readonly_mount_writes
tests/test_openclaw_strict_packet_contract.py::test_case57_outside_root_canary_kernel_denials
tests/test_openclaw_strict_packet_contract.py::test_case57_preflight_fds_proc_self_fd_f_getfd
tests/test_openclaw_strict_packet_contract.py::test_case57_preflight_sentinel_present_inside_runner
tests/test_openclaw_strict_packet_contract.py::test_case57_pytest_plugin_inventory
tests/test_openclaw_strict_packet_contract.py::test_case57_runtime_not_host_usr
tests/test_openclaw_strict_packet_contract.py::test_case57_tmp_allocated_bytes_uses_st_blocks
tests/test_openclaw_strict_packet_contract.py::test_case58_whole_case_not_passed_declared_future_reds
tests/test_openclaw_strict_packet_contract.py::test_m2_case58_literal_inventories_and_independent_walkers
tests/test_openclaw_strict_packet_contract.py::test_m2_case58_plugin_mutation_and_symlink_controls
tests/test_openclaw_strict_packet_contract.py::test_m2_dual_independent_canonical_parsers_and_vectors
tests/test_openclaw_strict_packet_contract.py::test_m2_future_production_modules_remain_absent
tests/test_openclaw_strict_packet_contract.py::test_m2_gate_b_and_c_schema_inventory_exact
tests/test_openclaw_strict_packet_contract.py::test_m2_idna2008_vectors_and_legacy_v1_retention
tests/test_openclaw_strict_packet_contract.py::test_m2_legacy_envelope_bytes_preserved
tests/test_openclaw_strict_packet_contract.py::test_m2_pinned_known_answer_vectors_dual_oracles
tests/test_openclaw_strict_packet_contract.py::test_m2_protocol_fixture_specimens_present
tests/test_openclaw_strict_packet_contract.py::test_m2_registry_schema_exact_binding_fields
tests/test_openclaw_strict_packet_contract.py::test_m2_schema_meta_and_31_positive_negative_instances
tests/test_openclaw_strict_packet_contract.py::test_m4_edit_allowlist_permits_mcp_server_protects_gate_w
tests/test_openclaw_strict_packet_contract.py::test_m8_selected_nodes_strict_live_inventory
```

The sorted-NUL identity-set SHA-256 is
`9fa64e04c15b96cbb935cb5b40d4e47a9cdd5869099d728a5213174c7244cbf6`. A missing member,
additional member or changed identity is `PAUSE`.

**Closed semantic signature.** For only a member of that exact set, a raw record is eligible only
when its outcome is `failure`, its type is empty, and its message is exactly four newline-separated
lines with all of these properties:

1. line 1 is exactly `AssertionError: assert None == 'inner'`;
2. line 2 is exactly ` +  where None = get('CONVMEM_OPENCLAW_INNER_ROLE')`;
3. line 3 begins exactly ` +    where get = environ(` and ends exactly `).get`;
4. line 4 begins exactly ` +      where environ(` and ends exactly `) = os.environ`; and
5. the bytes between the fixed line-3 prefix/suffix and the bytes between the fixed line-4
   prefix/suffix are identical within that record.

For an eligible record, the canonical semantic signature is the two exact core lines plus the two
fixed tail prefix/suffix pairs; the inner `environ(...)` representation is not part of that
semantic signature. The raw message, complete JUnit, canonical raw record and their hashes remain
stored unchanged. Nothing is deleted, rewritten or called passing. Each eligible node must have
all four failure records—`R` complete, final-candidate complete, `R` isolated rerun and
final-candidate isolated rerun—and all four must map independently to this one closed signature.

This is not a generic normalization. Section 18.10's normalization allowlist remains exactly the
source root, pytest temporary root and exact tip SHA. It gains no environment, ordering,
representation, path, suffix, hash or arbitrary-text substitution. A 23rd node; nonempty type;
different outcome; missing or extra line; changed core line; tail prefix/suffix mismatch; unequal
duplicated environment payload inside one record; absent one of the four records; new R2b node; or
any attempt to apply this rule outside the exact set is `PAUSE`. The exact five-node R2b rule is
independent and unchanged. Retained failures remain explicit debt and keep
`FULL_PYTEST_PASS=false`.

**Resume and evidence boundary.** After exact-tip Kiro PASS and a new Ryan grant, Grok applies the
complete reviewed linear plan range from this correction's grant-named base overlay through its
final overlay, oldest to newest, onto preserved `H1`, then pushes and stops. Codex proves the four
planning-document blobs and modes equal the reviewed overlay and every non-plan byte still equals
`H1`. Only after a commit-specific `CONTINUE`, Grok changes exactly four 40-hex values across
exactly two files: the `SEMANTIC_PARENT_SHA` and `M11_REVIEWED_OVERLAY_SHA` declarations in
`tests/fixtures/openclaw_strict/constants.py` and their two frozen assertions in
`tests/test_openclaw_strict_packet_contract.py`. `CODE_BASELINE_SHA` remains `N1`. No fifth
substitution, third path, formatting, test logic or other byte may change.

Codex then runs a fresh complete same-slot `N1`/`R`/final-candidate sequence and every symmetric
mismatch rerun; prior output is diagnostic only. Section 18.15's 238-node partition, §18.16's
advanced identities, §18.10's normalization allowlist, the five-node R2b proof and this 22-node
semantic-signature rule must all pass independently. This projection alone cannot produce a PASS:
every other differential gate still applies. Only a newly established
`CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` releases the unchanged §18.9 Pylint gate, two fresh M8
runs, seven legacy MCP regressions, durable-evidence verification and exact-tip Kiro conformance
review. Immediately before PR creation and Ryan's merge decision, `origin/main` must still equal
`N1`.

**Authority boundary.** This section authorizes planning only. It changes no product, test, CI,
baseline, runtime, configuration or evidence byte and waives no failure. A new Ryan grant must name
the semantic parent, final overlay, preserved `H1`, `N1`, `R`, complete reviewed plan range, exact
four substitutions, fixed slot, runtime prefix, durable evidence root, the closed 22-node set/hash
and complete three-tip/Pylint/M8/MCP sequence. Any conflict, extra change, signature mismatch,
runtime mutation or required correction is `PAUSE`. PR, merge, deployment, real OpenClaw, Gate
D/W/D-V/E/F, watch activation, live data and promotion remain independently blocked.

### 18.18 M11 post-reconstruction Pylint regression correction

**Observed governed PAUSE.** The reviewed §18.17 plan and four-literal authority rebind were
applied to the advanced-main candidate. Fresh same-slot runs at `N1`, `R` and final candidate
`65bbfd6f47515accfefa110b667afe1613f0dbed` collected 2,702, 2,912 and 2,940 nodes. The exact
238-node partition, five-node R2b proof, 22-node semantic-signature proof and all 166 symmetric
reruns passed, establishing `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` while retaining
`FULL_PYTEST_PASS=false`. The unchanged full-tree Pylint command then produced 458 findings,
including 72 `R0801/duplicate-code` messages. The protected regression gate compared that report
with baseline `9193f5ec744f059d07a20612489b210527b5660a`, reported one increased aggregate `R0801`
fingerprint (baseline 71, candidate 72), and exited 1. M8 and the seven legacy MCP regressions did
not start. The original PAUSE ledger is retained at:

```text
/home/lauer/.local/share/convmem-openclaw-evidence/9faac8ea87532bc73f74b788b38234de0c614a4e/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/65bbfd6f47515accfefa110b667afe1613f0dbed/PAUSE-ledger.json
```

Its SHA-256 is `28c3db4d0450c37d2a36079c1d960318161dcf8dc3c1cabf1f0082a21357f45b`.

Ryan authorized one read-only triage run at exact current main `N1` in the same fixed slot and
byte-revalidated CI environment. `N1` produced 455 findings and 69 `R0801` messages; its protected
gate passed with 240 fingerprints and no new/increased fingerprint. The candidate therefore adds
three `R0801` pairs relative to current main; the gate failure is not inherited. The CI
revalidation SHA-256 is
`47f8c6ab276e1ee6f2b1bd1a2ff7aa508a731af10bc976ddf55a0c249175ec54`. The sealed triage ledger
is retained at:

```text
/home/lauer/.local/share/convmem-openclaw-evidence/9faac8ea87532bc73f74b788b38234de0c614a4e/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/65bbfd6f47515accfefa110b667afe1613f0dbed/PYLINT-TRIAGE-ledger.json
```

Its SHA-256 is `53eb6004562c89854189961f5b8303de09d43d436ebd7070ed5676a581f48757`; the verified top-level
`pylint-triage-files.sha256` manifest SHA-256 is
`c9734c355b4d6d997ce4d163d6ba76893f13dd71049c132564c9353f57c6f3d3`.

**Closed three-pair boundary.** The candidate-only normalized pair list contains exactly these
three records, whose newline-terminated file has SHA-256
`ab41f0096d024331fd06ce9d49eed0f0800e73f65668766bd806a2e2e3a70671`:

```text
==strict_projection:[1125:1130]|==tests.test_openclaw_strict_packet_contract:[277:282]
==tests.test_bound_read_scope:[196:201]|==tests.test_strict_evidence_state:[402:407]
==tests.test_strict_evidence_state:[481:498]|==tests.test_strict_projection:[1044:1071]
```

Line spans identify the frozen `65bbfd6f` report only; they are not source selectors after a
correction shifts lines. The stable identities are the three ordered module pairs. A fourth pair,
different message ID, different module pair or correction outside the surface below is `PAUSE`.

**Exact two-file correction.** Section 18.9 continues to control and is not widened. Although all
five modules named by the report are members of its existing 44-path allowlist, only these two
test files may change:

```text
tests/test_openclaw_strict_packet_contract.py
tests/test_strict_evidence_state.py
```

The correction is mechanical and fully specified:

1. In `test_m2_gate_b_and_c_schema_inventory_exact`, replace only the Gate-C pipe-concatenated
   seven-name string plus `.split("|")` with an explicit seven-element tuple iterated by the
   existing list comprehension. Preserve every filename, order, prefixing call, assertion and
   expected value.
2. In `tests/test_strict_evidence_state.py::_binding`, replace only the six-field dictionary
   expansion holding `public_ref`, `project`, `domain_root`, `site_mode`, `site` and
   `non_expanding_roots` with the equivalent six direct named `ProjectBinding` arguments. Preserve
   every value and all remaining constructor arguments.
3. In `tests/test_strict_evidence_state.py::_source_record`, replace only the outer
   `dict((key, value), ...)` construction with a direct dictionary literal in the same key order,
   preserving every key and value exactly.

`strict_projection.py`, `tests/test_bound_read_scope.py` and `tests/test_strict_projection.py` are
reference sides and must remain byte-identical to `65bbfd6f`. The correction may add no helper,
import, dependency, suppression, comment directive, expected value or test branch. It may not
change node IDs, collection, selectors, outcomes, schema bytes, canonical bytes, production code,
authority/oracle ownership or any observable behavior. No `pylint: disable`, baseline growth,
workflow/gate/config edit, path exclusion or report laundering is allowed.

**Held application and evidence boundary.** After exact-tip Kiro PASS and a new Ryan grant, Grok
applies the complete reviewed linear plan range from `95011db461d51dcd3960a375757418401c5e505b`
through the grant-named final overlay onto preserved `65bbfd6f`, pushes and stops. Codex proves
exact four-document blob/mode equality and byte equality for every non-plan path. After a
commit-specific `CONTINUE`, Grok rebinds only the two parent/overlay declarations and their two
frozen assertions to the new semantic parent and overlay, pushes and stops. After a second
commit-specific `CONTINUE`, Grok performs only the three transformations above in exactly the two
files, pushes and stops. Codex verifies each commit independently; the authority rebind cannot be
hidden inside the Pylint correction.

Codex then repeats the complete fresh same-slot `N1`/`R`/final-candidate comparison, all required
symmetric reruns, the closed 238-node partition, five-node R2b proof and 22-node inner-role proof.
Only `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` releases the unchanged full-tree Pylint command.
The final Pylint report must contain exactly 455 findings and 69 `R0801` messages, none of the three
closed module pairs, no new pair, and no new/increased fingerprint; the unchanged gate must exit
zero. Codex then runs two fresh M8 reproductions and seven legacy MCP regressions, verifies the
runtime and durable-copy hashes, and obtains Kiro exact-tip conformance review. Any different
count, finding, pair, gate result, test outcome, source byte, runtime mutation or required further
correction is `PAUSE`.

**Authority boundary.** This section authorizes planning only. It changes no product, test, CI,
baseline, runtime, configuration or evidence byte. A new Ryan grant must name the new semantic
parent and final overlay, preserved `65bbfd6f`, `N1`, `R`, the complete reviewed plan range, exact
four-literal rebind, exact two-file transformations, fixed slot, runtime prefix, durable evidence
root and complete three-tip/Pylint/M8/MCP sequence. No earlier grant, Kiro verdict, test result or
`CONTINUE` may be reused. PR, merge, deployment, real OpenClaw, Gate D/W/D-V/E/F, watch
activation, live data and promotion remain independently blocked.

### 18.19 M11 Pylint acceptance-drift correction

**Observed governed PAUSE.** The reviewed §18.18 plan, four-literal authority rebind and exact
two-test-file/three-transformation correction were applied as separate held commits. Final source
`c71d37a42de0937aff57a2af47770a89902f132a` then passed the complete fresh same-slot `N1`/`R`/final
comparison: 2,702 / 2,912 / 2,940 collected nodes, the 238-node partition, five-node R2b proof,
22-node inner-role proof and all 166 symmetric reruns. `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`
therefore remains true for that exact source, while retained repository debt keeps
`FULL_PYTEST_PASS=false`.

The released unchanged full-tree Pylint command completed with raw status 30, empty stderr, 456
findings, 71 `R0801` messages and 240 fingerprints. The protected baseline gate exited zero with no
new/increased fingerprint, but the stronger reviewed §18.18 acceptance required 455/69 and exact
absence of every candidate-only pair. The exact pair comparison found two additions relative to
`N1` and no removal:

```text
tests.test_strict_evidence_state | tests.test_strict_projection
tests.test_strict_evidence_state | tests.test_strict_projection_publisher
```

The first is one of §18.18's original three pairs; the second is new. M8 and the seven MCP
regressions did not start. The sealed PAUSE packet is at:

```text
/home/lauer/.local/share/convmem-openclaw-evidence/3656104081a790676b02f1057bbc552631ce96d0/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/c71d37a42de0937aff57a2af47770a89902f132a/m11-pylint-final
```

Its `PAUSE-ledger.json` SHA-256 is
`fe268988c98e944b679446f3551987eaeccf9dce9a2b3b0963896069148a3e62`; its complete
`files.sha256` manifest SHA-256 is
`6f631cb97c8ae3531f70dc38a4fd5c865b3965ae207bac7b06ccd072cb15c01f`; the raw report SHA-256 is
`e114236db43b888184a3847631a1025031e31385c55664e2304d024618cd7a2b`; and the exact pair-comparison
SHA-256 is `a61465a3f448dcf98a6a583cc5d8f334e7831783443b2e6568044b72fa616301`.

**Cause and closed corrected surface.** The §18.18 Gate-C tuple rewrite succeeded and stays
byte-identical. The other two prescribed constructions were not sufficient:

1. six direct `ProjectBinding` keyword arguments recreated the static token sequence in
   `tests.test_strict_projection`; and
2. the single direct `_source_record` dictionary literal recreated the `title` through
   `target_assertion_id` sequence in `tests.test_strict_projection_publisher`.

Only `tests/test_strict_evidence_state.py` may change after this plan is applied and its separate
authority-packet rebind is verified. Exactly these two transformations are permitted:

1. In `_binding`, preserve the existing direct named arguments and values but reorder only the six
   governed arguments after `id=binding_id` to this exact order:
   `project`, `site`, `site_mode`, `domain_root`, `public_ref`, `non_expanding_roots`. Every
   remaining `ProjectBinding` argument stays byte-identical and in its current order.
2. In `_source_record`, replace the one direct return literal with the exact three-stage local
   construction: assign `source` to a dictionary containing, in order, `record_kind`, `producer`,
   `logical_key`, `title`, `document`, `observed_at`; call `source.update()` once with a dictionary
   containing, in order, `confidence_bps`, `relates_to_assertion_id`, `target_assertion_id`,
   `verification_result`, `provenance_assertion_id`; then `return source`. Preserve every value and
   the resulting eleven-key insertion order.

The correction adds no helper, import, branch, suppression, expected value, dependency or shared
oracle. It changes no node ID, selector, collected test, outcome, schema/canonical byte, production
surface or authority owner. `tests/test_openclaw_strict_packet_contract.py` may change only in the
separate four-literal parent/overlay rebind. `strict_projection.py`,
`strict_projection_publisher.py`, `tests/test_bound_read_scope.py`,
`tests/test_strict_projection.py`, `tests/test_strict_projection_publisher.py` and every other
non-plan path stay byte-identical to `c71d37a` except those four already-frozen authority literals.

**Falsifiable design check, not acceptance evidence.** Codex reproduced both excess pairs in an
untracked disposable export of `c71d37a`, applied only the two constructions above, and ran the
unchanged full-tree command in the byte-revalidated CI environment. The diagnostic report had 454
findings, 69 `R0801` messages and 240 fingerprints; the protected gate exited zero; and the complete
69-record normalized `R0801` pair multiset equaled `N1` with no addition or removal. The diagnostic
report SHA-256 is `db400a75f1a12f712a1f51e66e90a9ed631a87121ec0a21ff2ee9c28e055eb4f`, the pair-result SHA-256
is `cafe5c059255fc82d6c2b538c3505a2168312aef87788ff420002dd2537e104c`, and the gate-stdout SHA-256
is `a161f567da3656ef60ce3fe765abb4048ba0df2e5385a5d3171ee5e16fdd0f02`. These volatile probe
artifacts justify plan specificity only. They are not governed acceptance, do not release M8/MCP
and may not be cited as a PASS after source changes.

The corrected total is exactly 454, not current main's 455. Candidate source has one fewer
non-`R0801` cycle finding while retaining the same 240-fingerprint set allowed by the protected
gate; equality of total finding counts across different source trees is not an authority rule.
The exact requirements are therefore 454 total findings, 69 `R0801` messages, 240 fingerprints,
raw status with no fatal/usage bit, empty stderr, protected-gate exit zero, and byte-for-byte
equality of the normalized 69-pair multiset to `N1`. A different count, pair, fingerprint or gate
result is `PAUSE`; fewer findings are not silently accepted.

**Held application and evidence boundary.** After exact-tip Kiro PASS and a new Ryan grant, Grok
applies the complete reviewed linear plan range beginning after the §18.18 reviewed overlay onto
preserved `c71d37a`, pushes and stops. Codex proves exact four-document blob/mode equality and
byte equality for every non-plan path. After a commit-specific `CONTINUE`, Grok updates only the
same four parent/overlay SHA literals to the new semantic parent and overlay, pushes and stops.
After a second `CONTINUE`, Grok makes only the one-file/two-transformation correction above,
pushes and stops. Codex separately verifies each commit and the final composition.

Codex then repeats the complete fresh same-slot `N1`/`R`/final comparison and every required
symmetric rerun. Only a fresh `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` releases the unchanged
full-tree Pylint command and the exact 454/69/240 plus pair-multiset acceptance above. Only that
result releases two fresh M8 runs and seven MCP regressions, followed by durable-evidence
verification and Kiro exact-tip conformance review. Earlier differential or probe output supplies
no acceptance. Any conflict, extra byte/path, runtime mutation, evidence mismatch or required
additional correction is `PAUSE`.

**Authority boundary.** This section authorizes planning only. It changes no product, test, CI,
baseline, runtime, configuration or governed evidence byte. A new Ryan grant must name the new
semantic parent and final overlay, preserved `c71d37a`, `N1`, `R`, the complete reviewed plan
range, exact four-literal rebind, exact one-file/two-transformation correction, fixed slot, runtime
prefix, durable evidence root and complete three-tip/Pylint/M8/MCP sequence. No prior grant,
review, test or `CONTINUE` may be reused. PR, merge, deployment, real OpenClaw, Gate D/W/D-V/E/F,
watch activation, live data and promotion remain independently blocked.

### 18.20 M11 Pylint `R0401` deterministic acceptance

**Observed governed PAUSE.** The reviewed §18.19 plan, separate four-literal authority rebind and
exact one-test-file/two-transformation correction were applied as held commits. Final source
`caec5c6868f600e897b29a39f555365e5f818ac1` then passed a complete fresh same-slot
`N1=5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d` /
`R=cd60cf19dca6706e4175e9f82c9ba55e41bca10b` / final comparison: 2,702 / 2,912 /
2,940 collected nodes, the 238-node partition, five-node R2b proof, 22-node inner-role proof and
all 166 symmetric reruns. The sealed comparison established
`CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`; retained repository debt still keeps
`FULL_PYTEST_PASS=false`. Its final-summary SHA-256 is
`4b3999aef4490aedda3a365d052b5894da1a720e41a7f64c15284aa99dbf3a05`.

The released unchanged full-tree Pylint command completed with raw status 30, empty stderr, 458
findings, 69 `R0801` messages, 29 `R0401` messages and 240 fingerprints. The protected gate exited
zero, and the complete normalized 69-pair `R0801` multiset equaled `N1` with no addition, removal
or closed introduced pair. Exact §18.19 acceptance nevertheless required 454 total findings, so
Codex issued `PAUSE` before M8 or MCP. The sealed packet is at:

```text
/home/lauer/.local/share/convmem-openclaw-evidence/c92bc708d1fc23e8d37584890e876c151682a48d/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/caec5c6868f600e897b29a39f555365e5f818ac1/m11-pylint-final
```

Its `PAUSE-ledger.json` SHA-256 is
`b7fddc9534540a28116e62646e2989f80e6cd5f3d3efecc30a06649195f10860`; its complete
`files.sha256` manifest SHA-256 is
`9076aacd8185b88e73e1381fc1cb5706c1fd50b64609b8ce31a668438eb0d85d`; the raw report SHA-256 is
`044f723a77946bd3b6c593dcea10987d7956ab62a5a58789dc2b23215553eeaf`; the `R0801` equivalence
SHA-256 is `cafe5c059255fc82d6c2b538c3505a2168312aef87788ff420002dd2537e104c`; and the `R0401` drift
record SHA-256 is `a606e77bf639f13350107ceee6ac7131b5f867b4310b9d195f88c1b8a9d9abd1`.

**Closed diagnostic finding.** No import byte changed in §18.19's exact source correction. The
earlier unseeded disposable design probe observed 25 `R0401` messages and predicted 454 total;
the governed final run observed 29 `R0401` and 458 total, while both retained exactly 429
non-`R0401` findings. Therefore the 454-total rule accidentally made one unfrozen cycle-report
enumeration authoritative. Ryan authorized exactly four disposable, non-acceptance probes using
the same qualified environment, full tracked-Python inventory, command, fixed reset slot and
resource limits, adding only `PYTHONHASHSEED=0`: `N1` twice and exact final source twice.

All four probes produced 458 findings, 29 `R0401`, 69 `R0801`, 429 non-`R0401` and 240
fingerprints. Each tip was internally reproducible, and the two tips had identical message-ID
counts, canonical `R0401` records and canonical `R0801` pairs. Raw JSON report hashes differed
between repetitions because raw `R0801` message bodies and report ordering remained unstable;
raw byte equality is therefore evidence, never an authority condition. The diagnostic root is:

```text
/home/lauer/.local/share/convmem-openclaw-evidence/c92bc708d1fc23e8d37584890e876c151682a48d/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/caec5c6868f600e897b29a39f555365e5f818ac1/m11-pylint-r0401-determinism-probe
```

The final-summary SHA-256 is
`c68834661b2362a1e43a762460ab36a00077b91570fcb95767179d296ebef34b`; the canonical-authority
SHA-256 is `cbeb6e3d6253f17907ff25e109576a680d028333908f167ccf39e1589b71c8fe`; and the root-manifest
SHA-256 is `2cff8fe59f2e703e0183d175b33000b0b9d89e2651baf5dd0bf67bcff0d22eed`. These probes justify
plan specificity only. They are not acceptance evidence, do not relabel the governed PAUSE and do
not release M8 or MCP.

**Deterministic semantic authority.** After a fresh three-tip differential passes at the final
source, Codex must run the unchanged complete full-tree Pylint command first at `N1` and then at
the final candidate in the same reset slot, qualified runtime and environment, adding exactly
`PYTHONHASHSEED=0` to both executions. The Git-tracked Python inventory is derived independently
at each exact source tip. The protected workflow, baseline, gate, Pylint arguments, dependencies,
permissions and source bytes remain unchanged. Acceptance requires all of the following:

1. both tips report exactly 458 findings, 29 `R0401`, 69 `R0801`, 429 non-`R0401` and 240
   fingerprints; raw Pylint status has no fatal/usage bit, stderr is empty and the unchanged
   protected gate exits zero at both tips;
2. for each report, sort every `R0401` identity as the exact five-value sequence
   `[path,line,column,symbol,message]`; the complete 29-record lists must be identical between
   `N1` and final source, and their UTF-8 canonical JSON (`sort_keys=true`, separators `,` and `:`,
   one trailing newline) must have SHA-256
   `e0a2c3d9e41e204deff7fdc68265d2a4ed2952934b4eaea42a79fe22dfa09282`;
3. the complete message-ID count objects must be identical between tips and have the same
   canonical encoding with SHA-256
   `278ff3c7e0935c2b2426635a5c178f15ff0a0e3fb7943c16281fda111391c896`;
4. extract each `R0801` identity as the sorted two-module pair already frozen by §18.19; the
   complete 69-record pair multisets must be identical, contain no closed introduced pair, and
   their canonical list of `{count,left,right}` objects must have SHA-256
   `51d818973d3f9054ff35e1ba721adadb281fa0eac61a929fda7b02c5fee78556`; and
5. preserve both raw reports and their individual hashes, but never require raw report byte order
   or use sorting to rewrite raw evidence.

Any other seed, environment delta, count, canonical hash, pair, message-ID distribution, gate
result, stderr content, fatal/usage bit, missing raw report or required source/runtime correction
is `PAUSE`. A lower total is not silently accepted. This rule does not suppress, waive or
normalize a finding; it closes the previously unfrozen enumeration input and compares semantic
identities while retaining raw output.

**Held application and evidence boundary.** After exact-tip Kiro PASS and a new Ryan grant, Grok
applies the complete reviewed linear plan range beginning after the §18.19 reviewed overlay onto
preserved `caec5c6`, pushes and stops. Codex proves exact four-document blob/mode equality and
byte equality for every non-plan path. After a commit-specific `CONTINUE`, Grok changes only the
same four parent/overlay SHA literals to the new semantic parent and overlay, pushes and stops.
Codex proves the exact two-path/four-substitution diff. No further product, test, CI, baseline,
runtime-content or configuration correction is eligible.

Codex then runs a fresh same-slot `N1`/`R`/final comparison and every required symmetric rerun.
Only a fresh `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` releases the paired seeded Pylint evidence
above. Only exact Pylint semantic acceptance releases two fresh M8 runs and seven legacy MCP
regressions, followed by durable-evidence verification and Kiro exact-tip conformance review. Any
conflict, extra byte/path, runtime mutation, evidence mismatch or required correction is `PAUSE`.

**Authority boundary.** This section authorizes planning only. It changes no product, test, CI,
baseline, runtime content, configuration or governed acceptance evidence byte. A new Ryan grant
must name the new semantic parent and final overlay, preserved `caec5c6`, `N1`, `R`, the complete
reviewed plan range, exact four-literal rebind, fixed slot, runtime prefix, durable evidence root
and complete three-tip/paired-Pylint/M8/MCP sequence. No prior grant, review, test, diagnostic
probe or `CONTINUE` may be reused. PR, merge, deployment, real OpenClaw, Gate D/W/D-V/E/F, watch
activation, live data and promotion remain independently blocked.

### 18.21 M11 final-M8 legacy-count drift correction

**Observed governed PAUSE.** The reviewed §18.20 plan range and exact four-literal authority
rebind were applied as held commits. Final source
`9da6dd98d276b250470de4e53ac786f7547d92d5` then completed a fresh same-slot
`N1=5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d` /
`R=cd60cf19dca6706e4175e9f82c9ba55e41bca10b` / final comparison, all 166
symmetric reruns, the exact 238-node partition, five-node R2b proof and 22-node inner-role proof.
The final comparison SHA-256 is
`dee4a8746c307311984a8ee5aa19ffdd8f443ebf28a92566a915a57599769d11` and established
`CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS`; retained repository debt still keeps
`FULL_PYTEST_PASS=false`. Paired seeded Pylint then passed §18.20 exactly at both tips with
458 findings, 29 `R0401`, 69 `R0801`, 429 non-`R0401`, 240 fingerprints, protected-gate zero and
the three frozen semantic hashes. Its canonical authority SHA-256 is
`89c9bde4db8807cb979ca10e516ecac3437136571ff612678a9b7e8adad69b0a`.

Final M8 run 1 entered the unchanged isolated runner. Strict Python passed 238/238, Node passed
29/29, and legacy Python completed successfully with 118 collected, 117 passed, zero failed,
zero errored, one skipped and the same four deselections. The evidence parser correctly returned
status 2 because `EXPECTED_LEGACY_JUNIT_COUNTS` still required the historical 116 collected /
115 passed. Runtime inventories before and after were byte-identical. Run 2 and the seven MCP
regressions did not start. The durable PAUSE packet is:

```text
/home/lauer/.local/share/convmem-openclaw-evidence/45863c87f1ae70b89dd063da8f09f6cd16fdb3a3/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d/runs/9da6dd98d276b250470de4e53ac786f7547d92d5/m11-m8-run1-final
```

Its PAUSE-ledger SHA-256 is
`73005d7a3b65d5de6652696c92a6801789b0051a90b399755c8e4c3854ce8aa8`; its complete
evidence-manifest SHA-256 is
`51bf7fef728223106a1da8f7dfeb3de42bce8a7e15d2e3830c0919eeabe7152d`; and its exact
count-drift diagnostic SHA-256 is
`a025ada8c43533577ed8a204f16317865b0e2beb7edd80687aa28a1184f48264`.

**Closed diagnosis and authority.** The historical 116/115 count remains true for the accepted
M8 source and preserved `R`; it is not the node set of current main. Current-main commit
`ad524e1e5181b086918748161e489d608a329794` added two positive safety controls to the already
selected `tests/test_shadow_writer_coverage_scan.py`. That file is current-main-owned and has
identical Git blob `d1ed10f1f4a2d6b457e3e09f9af156f222efd4e8` at `N1` and final source. The exact additions are:

- `tests/test_shadow_writer_coverage_scan.py::test_scan_skip_ignores_review_bundle_snapshots` —
  `passed`; and
- `tests/test_shadow_writer_coverage_scan.py::test_scan_skip_ignores_worktree_snapshots_but_not_tracked_files`
  — `passed`.

Independent comparison against the last accepted legacy JUnit found exactly those two additions,
zero removals and zero outcome changes. Section 6.5.8 requires every node other than the four
named deselections in every selected legacy file to remain selected. Excluding either new node,
adding a deselection or narrowing the selector would therefore weaken the governing contract.
The successor final-source expectation is exactly 118 collected, 117 passed, zero failed, zero
errored, one skipped and four unchanged deselections. The two fresh M8 legacy arrays must each
equal the historical accepted array plus exactly the two additions above, with no removal or
outcome change, and must remain byte-for-byte equal to each other after canonicalization.

**Exact successor correction.** After exact-tip Kiro PASS and a new Ryan grant, Grok applies the
complete reviewed linear plan range beginning after the §18.20 reviewed overlay onto preserved
`9da6dd98`, pushes and stops. Codex proves exact four-document blob/mode equality and byte equality
for every non-plan path. After a commit-specific `CONTINUE`, Grok updates only the same four
parent/overlay SHA literals to the new semantic parent and reviewed overlay, pushes and stops.
After a second `CONTINUE`, Grok changes only
`tests/fixtures/openclaw_strict/constants.py`: within `EXPECTED_LEGACY_JUNIT_COUNTS`, replace
`"collected": 116` with `"collected": 118` and `"passed": 115` with `"passed": 117`.
No test function, selector, deselection, parser, failure rule, Node command, dependency,
permission, runtime byte or other source byte may change. Grok commits, pushes and stops; Codex
proves the exact one-path/two-integer diff before any evidence execution.

Codex then repeats the complete fresh same-slot `N1`/`R`/final comparison and every required
symmetric rerun. Only a fresh `CURRENT_MAIN_THREE_TIP_DIFFERENTIAL_PASS` releases paired seeded
Pylint under §18.20. Only exact Pylint semantic acceptance releases two fresh M8 runs under the
118/117 successor contract and the seven legacy MCP regressions, followed by durable-evidence
verification and Kiro exact-tip conformance review. Prior differential, Pylint and M8 output is
historical evidence only. Any conflict, extra byte/path, changed selector/deselection, missing or
different added node, runtime mutation, evidence mismatch or required additional correction is
`PAUSE`.

**Authority boundary.** This section authorizes planning only. It changes no product, test, CI,
baseline, runtime content, configuration or governed acceptance evidence byte. A new Ryan grant
must name the new semantic parent and final overlay, preserved `9da6dd98`, `N1`, `R`, the complete
reviewed plan range, exact four-literal rebind, exact one-path/two-integer correction, fixed slot,
runtime prefix, durable evidence root and complete three-tip/paired-Pylint/M8/MCP sequence. No
prior grant, review, test, diagnostic or `CONTINUE` may be reused. PR, merge, deployment, real
OpenClaw, Gate D/W/D-V/E/F, watch activation, live data and promotion remain independently
blocked.

### 18.22 M11 PR #342 safety, CI applicability and R2b convergence corrective

**Observed merge-blocking state.** Pull request `#342`, “Add the bounded read-only
OpenClaw connector to ConvMem,” compares exact base
`5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d` with exact head
`94f29ebabee31112cccb223fd1445cb782aac6eb`. CodeQL, secret scan and the unchanged
Pylint regression gate passed. The live ruleset-required `pytest (3.12)` job failed
with 83 failures: 22 packet-contract nodes require a fixture-only
`CONVMEM_OPENCLAW_INNER_ROLE`, 56 nodes depend on the qualified CPython 3.13.12 /
Unicode 15.1 runtime rather than GitHub CPython 3.12.14, and five nodes expose the
already-recorded R2b committed-versus-resolved authority-content identity difference.
The base commit passes the same workflow. This is a CI applicability failure, not
permission to skip or weaken any test.

A focused ultrareview of the effective four-file product delta also established two
independent blockers:

1. `mcp_server.py` correctly fails closed at import for an unknown or
   `openclaw-strict` profile, but `doctor.py::_check_mcp_import()` catches only
   `ImportError`. A stray invalid environment value can therefore abort the whole
   doctor process before later health checks run.
2. `strict_projection_publisher.py::_find_operation_outcome()` treats a historic
   fenced record with the same `pending_operation_id` as a retry without independently
   proving the canonical input digest. A crash between fence persistence and durable
   input persistence makes same-operation/different-content replay indistinguishable
   under that branch.

The duplicated reader/publisher hashing helpers are a maintainability observation,
not part of this correction. Moving them is forbidden here.

#### 18.22.1 Doctor containment contract

The MCP startup refusal remains import-time and fail-closed; this correction must not
move, weaken or special-case it in `mcp_server.py`. Instead, only `doctor.py` and
`tests/test_doctor.py` may change. `_check_mcp_import()` catches `SystemExit` from the
import and returns a failed `DoctorCheck("mcp_import", False, <fixed sanitized
message>)`. The overall doctor command continues every later check and exits through
its normal nonzero health-check result. It must not stringify the `SystemExit`
payload, raw profile value, environment, credentials or paths. Existing `ImportError`
handling remains; `BaseException`, `KeyboardInterrupt` and unrelated failures are not
caught.

Fresh-process regression tests cover `openclaw-strict`, one fixed unknown sentinel,
recognized `shell` and unset/full profiles, an injected sensitive `SystemExit`
payload, empty disclosure surfaces, and proof that checks scheduled after
`mcp_import` still execute. Tests bind the semantic failure and non-disclosure, not
parent-unspecified presentation bytes.

#### 18.22.2 Fenced publication and recovery contract

Only `strict_projection_publisher.py` and
`tests/test_strict_projection_publisher.py` may change for this defect. The existing
CAS and lock checks run first. While the current publication is fenced, every ordinary
publish/admission attempt refuses without writes, regardless of operation identifier
or input bytes. Recovery is a distinct explicit path:

- A crash after the fence but before durable authority input may clear the active
  fence only after proving there is no durable intent or admission. Recovery restores
  the predecessor authority under a new epoch with unchanged expiry, retains the
  fenced history, and permanently consumes every operation identifier present in that
  abandoned durable fence. Because the missing bytes cannot be proved, even apparent
  “same bytes” reuse is forbidden; a new operation identifier is required.
- A crash after durable input but before admission remains recovery-required and
  ambiguous. Recovery does not clear the fence, serve predecessor authority, admit
  the input, or manufacture `exact_retry`. Completing or abandoning that durable
  intent is a later reconciliation surface and is not added here.
- After durable admission but before projection, authority remains unavailable. A
  verified exact retry may report the historic admitted outcome/current head without
  mutation, and the existing rebuild path may project that admitted head.
- A historic exact retry requires the same operation identifier, an independently
  recomputed canonical input digest, and matching retained admitted-authority
  bindings. Same identifier with different bytes always rejects before writes.
- Missing, malformed, symlinked, inconsistent, multiply conflicting or uninspectable
  required evidence is an error, never “not found.” Recovery must never clear a fence
  and then rebuild the predecessor into service when durable intent exists.

No schema, publication layout, hash algorithm, operation-ID syntax, data model or
reader behavior changes. The crash matrix must prove write-free refusals and exact
post-state bytes for every boundary above.

#### 18.22.3 Required GitHub pytest partition

The live ruleset context remains exactly `pytest (3.12)` and its existing workflow
producer remains `.github/workflows/pylint.yml`; branch protection is not edited.
Pylint, its baseline and the Pylint job remain byte-for-byte unchanged. On the actual
GitHub pull-request merge commit, collect the complete pytest node universe `U`, then
partition it using the exact existing 13 `STRICT_PYTEST_FILES`:

- `Q` is every collected node whose file is one of those 13 exact paths. `Q` runs in
  the qualified closed runtime and containment adapter.
- `O` is every other collected repository node. `O` runs under the ordinary GitHub
  Python 3.12 environment.
- Evidence must prove `O ∩ Q = ∅` and `O ∪ Q = U`, with exact sorted node identities,
  outcomes and hashes. The current reference collection is `|U|=2940`, `|Q|=238`;
  successor ordinary counts must include newly added doctor and CI regression nodes
  rather than freezing those reference totals.

The qualified invocation also runs the unchanged 29-node connector suite and the
unchanged legacy selector with its four exact deselections. Those four legacy nodes
remain ordinary-coverage members in `O`; the qualified legacy repetition does not
remove them from the complete ordinary partition. The Node and legacy executions are
supplemental M8 regressions, not second memberships in `U` and not substitutes for an
`O` outcome. Broad skip/xfail/markers, wildcards,
failure-derived selectors, changing the four deselections, or a Python-version bump
alone are forbidden.

Add one bounded CI orchestration adapter, `scripts/run_switchboard_ci.py`, with its
contract in `tests/test_switchboard_ci_contract.py` and immutable runtime coordinates
in `ci/switchboard-runtime.json`. It must reuse—not copy or weaken—the existing M8
containment, runtime inventory, negative controls, source export, preflight, suite
commands, resource limits and result validation. It runs the exact checked-out
commit/tree, validates real JUnit/node/process output, and emits a separate
CI-regression receipt that can never be called M8 PASS, conformance PASS or runtime
qualification. It accepts ordinary repository deltas without importing the historical
M8 product allowlist as a general PR allowlist. The existing M8 runner remains
unchanged and still runs separately twice.

If the workflow uses dependent jobs, the required aggregate context runs under
`always()` and explicitly requires every dependency to conclude `success`; a skipped,
cancelled, missing or neutral dependency fails. Contract tests must make missing
branches/nodes, duplicates, fake PASS output, skipped dependencies, selector drift,
host `CONVMEM_OPENCLAW_INNER_ROLE`, stale evidence, any runtime byte drift, or a
missing containment flag fail closed. Evidence records PR head, PR base, GitHub merge
commit and merge-tree identity.

#### 18.22.4 Immutable runtime delivery is a separate external gate

The qualified local runtime is not yet a GitHub-accessible artifact. The proposed
delivery coordinate is repository `alanmz-crypto/convmem`, tag
`switchboard-fixture-runtime-74a12c725ac3bad4f`, asset
`switchboard-fixture-runtime.tar.gz`, whose extracted tree must equal
`sha256:74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`.
Those coordinates are a proposal, not authorization to publish.

Before any asset exists, a separate runtime-delivery packet and Kiro review must bind
the source runtime directory and full inventory, archive hash and deterministic
extraction rules, extracted tree hash, release coordinates, provenance/licensing,
hosted-runner/kernel compatibility, pinned `bwrap` provisioning recipe and hashes,
negative controls, and replacement policy. The archive contains no credentials,
configuration, live data, OpenClaw installation/model packages, symlinks, special
files or path escapes. Ryan must then authorize the exact external release operation.
CI never resolves `latest`, accepts a mutable replacement, repairs the runtime, uses
host dependencies as fallback, or substitutes another source. Missing or incompatible
bytes fail closed.

#### 18.22.5 R2b authority-content convergence

This planning correction crosses into Arc R2b Capture Authorization only for static
content attestation; it authorizes no lease, writer quiescence, capture, packet, live
mutation or I4–I8 action. At PR head `94f29eb`, the governed 120-member path set has
committed identity `b716152fbf725633a55371f6acf7ed5580a704bd` and independently
resolved identity `e060dce4eb3d51e0f4650ded8bd1aad4f2a34f4b`. `mcp_server.py` is
already the sole changed governed member; the doctor correction makes `doctor.py` the
second. The publisher is not a governed R2b member.

After every final governed edit, an independent lane regenerates only
`docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json`. The member count, exact path set,
seed, closure and routes remain unchanged; all members other than `mcp_server.py` and
`doctor.py` stay byte-identical to fixed main. The lane retains before/after canonical
manifests and change proof, recomputes
`SHA256("r2b-v2-authority-content:v1:" + canonical_manifest)[:40]`, and proves
convergence with the runtime resolver, inventory binding/digest and artifact. No R2b
algorithm, coordinate, writer gate, lease, capture or coverage expectation changes.

Because `STATUS-r2b-capture-auth.md` is part of this reviewed cross-arc correction, the
reviewed control-plane set becomes exactly five documents: the existing four
Switchboard planning documents plus that R2b STATUS document. The five source blobs
and modes must equal the reviewed overlay exactly and remain in source export,
inventory and `source_tree_sha256`. `constants.py`, `allowlist.py` and the packet
contract test may receive only the closed additions needed to name this fifth control
document and the exact corrective product/test/CI/R2b paths. An unlisted sixth
document, prefix/glob exception or product-allowlist widening fails closed. The
original `EDIT_ALLOWLIST_EXACT`, `EDIT_ALLOWLIST_PREFIXES` and `SCHEMA_ALLOWLIST`
remain unchanged. Instead, the packet freezes a separate M11-only exact corrective
set containing only: `doctor.py`, `tests/test_doctor.py`,
`strict_projection_publisher.py`, `tests/test_strict_projection_publisher.py`,
`.github/workflows/pylint.yml`, `tests/test_ci_contract.py`,
`scripts/run_switchboard_ci.py`, `tests/test_switchboard_ci_contract.py`,
`ci/switchboard-runtime.json`, and
`docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json`. That set is valid only for this
reviewed PR correction and is never a T0–T5 product allowance.

#### 18.22.6 Ordered correction and final evidence

The required order is: plan correction → Kiro exact-tip binary review → new Ryan
implementation grant → held doctor commit → held publisher/recovery commit → held CI
commit → independently held R2b inventory rotation → fresh evidence → Kiro exact-tip
integrated review → Ryan merge decision. Codex verifies and issues a commit-specific
`CONTINUE`, `CORRECT`, `PAUSE` or `REQUIRE TEST` after every pushed hold. Any conflict,
extra path/byte, runtime-distribution uncertainty, authority ambiguity or required
unplanned correction is `PAUSE`.

Final evidence includes doctor continuation/non-disclosure; the complete fenced-crash
matrix; complete `O`/`Q` union/intersection and actual GitHub merge-tree reconciliation;
CI mutation controls; all five R2b failures plus existing R2b revision/coverage/
authority-boundary/negative/shadow-writer tests; independent R2b convergence; the
unchanged Pylint gate; two fresh M8 runs at 238 strict, 29 Node, and 118 collected /
117 passed / one skipped / four deselected legacy outcomes; seven MCP regressions;
durable verification; required GitHub checks green; focused safety/isolation review;
and Kiro review of the exact integrated tip. Historical evidence is not replayed as a
new PASS.

**Authority boundary.** This section authorizes planning only. It does not authorize
the plan application, doctor/publisher/CI/test/inventory edits, runtime provisioning or
publication, evidence execution, PR update, merge, deployment, real OpenClaw, live
data, watch activation, promotion, or Gates D/W/D-V/E/F. PR `#342` is amended rather
than split only after the separately reviewed and granted correction completes.

### 18.23 Qualified-runtime delivery packet

Section 18.22.4 remains the authority boundary. Ryan authorized Codex to derive one
disposable local archive from the frozen runtime and to encode the result in the four
Switchboard plans. This section does not authorize an external release or make the
archive acceptance evidence.

#### 18.23.1 Exact source, coordinate and local artifact

The source is the read-only directory
`/home/lauer/.local/share/convmem-openclaw-runtimes/7dccb771b2f43288c52b7cb1dd18dedb18cb7e57/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d`.
Its canonical regular-file inventory is a sorted compact-JSON array of exact
`mode,path,sha256` objects. The inventory contains 30,421 regular files and hashes to
`sha256:74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`.
The tree has 2,840 directories including its root, zero symlinks, zero special files
and zero writable paths. Recomputing every content hash and mode before and after
archive construction matched that inventory.

The only proposed external coordinate remains:

```text
repository=alanmz-crypto/convmem
tag=switchboard-fixture-runtime-74a12c725ac3bad4f
asset=switchboard-fixture-runtime.tar.gz
archive_size=557628743
archive_sha256=6f9cfa93e3847793a42279e6ff79e07ed0b47c23d6ec7a368a4e8cb530ce594e
runtime_tree_sha256=74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b
complete_extracted_regular_file_tree_sha256=52d3f70a9eb64b5c5348abc8c487994acba7fe7de0b77c358175ff42cfd23d37
```

The disposable archive has 33,271 members: 30,429 regular files and 2,842
directories. `runtime/` contributes the exact frozen runtime. `delivery/` contains
one packet description and seven unmodified provisioning/rebind evidence files. All
delivery files are mode `0444`, both delivery directories are mode `0555`, and their
SHA-256 values are:

| Archive member | SHA-256 |
|---|---|
| `delivery/PACKET.md` | `24073ab433c503c1d5721984b97fe957ccada0ce634f8bdeae4e8ed1f9907a7d` |
| `delivery/provisioning/python-packages.json` | `8d95f92e57afa70111ad7304ce82cc7ed4fec4786643c66bf3e4a3dc0618c2f6` |
| `delivery/provisioning/loaded-resolution.json` | `dcf4e9e762dac5bd56aaac45d622391be11b1959ab557d6bed691a26849c3707` |
| `delivery/provisioning/runtime-checks.json` | `b0b51fb4d8dadb7e1c3d747728d01664c9d668a4963da5a0c2f8ec6dc25fc5e3` |
| `delivery/provisioning/runtime-inventory.json` | `74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b` |
| `delivery/provisioning/runtime-provisioning-summary.json` | `82fefc9caef737c1691ae0ce354e71946ac1363da005c3e4e6015a8b16d4ffea` |
| `delivery/provisioning/rebound-runtime-inventory.json` | `73750e4825dae93c1a77a8d7e63c9616fe83a00b080eff16c34073191e56b2b4` |
| `delivery/provisioning/runtime-rebind-summary.json` | `051b2e4541931acac3e02451191e227a40450efae3bd50827ed91aaca3ce7a79` |

#### 18.23.2 Deterministic construction and closed extraction

Construction is frozen to GNU tar 1.35 and GNU gzip 1.15 under `LC_ALL=C`. Tar reads
the source directly, sorts names, uses POSIX format, deletes `atime`/`ctime` PAX
fields, sets every header `mtime=0`, `uid=gid=0`, preserves modes, and transforms
only the source-root name to `runtime/`. It then adds the prebuilt `delivery/` tree.
Gzip uses `-n -9`. A tool/version, ordering, metadata, source-root, transform or
delivery-member change creates a different packet; it is never accepted as an
equivalent rebuild.

Before extraction, verify the exact archive hash and inspect every tar header. Each
normalized UTF-8 POSIX name must be uniquely and strictly below `runtime/` or
`delivery/`, with no absolute, empty, dot or dot-dot segment. Members must be only
regular files or directories with zero uid/gid/mtime and no setuid, setgid, sticky or
sparse metadata. Links, devices, FIFOs, sockets, duplicate names and path escapes
reject the archive.

Extraction occurs only into a newly created empty directory with Python 3.12+.
For each prevalidated member, call `tarfile.data_filter`; then restore only the
prevalidated archived mode with `filtered.replace(mode=member.mode)`. Do not restore
ownership/time, and never use `fully_trusted` or a permissive fallback. This closed
filter is required because the standard data filter intentionally adds owner-write
permission and would otherwise invalidate the read-only inventory. Before any test
import, recompute the embedded runtime inventory byte-for-byte, its tree hash, all
directory/file modes and all counts. The locally extracted archive produced the exact
runtime hash above, zero writable/link/special members, and complete regular-file tree
hash `52d3f70a…`.

#### 18.23.3 Contents, compatibility and bubblewrap

Path and content controls found zero OpenClaw packages, user-state paths, live ConvMem
data, external model/cache/checkpoint data or private-key markers. The two `.pem`
members are package-owned public CA bundles, not credentials. Installed dependency
code and package-owned test/license assets remain part of the inventoried runtime.

The target is a GitHub-hosted x86_64 `ubuntu-24.04` runner. The historical failing job
reported runner `2.337.0`, image `20260920.314.1` and kernel
`6.17.0-1022-azure`; this observation is not a future compatibility grant. Every run
must prove Linux/x86_64, unprivileged user namespaces, the mandatory bubblewrap flags,
read-only runtime/sysroot, private `/tmp`, cleared environment, capability drop and
network isolation before qualified test import. The local exact-shape probe passed
with bubblewrap 0.13.0 on Linux 7.2.6, but it is diagnostic only.

Hosted provisioning is pinned to Ubuntu Noble security package
`bubblewrap_0.9.0-1ubuntu0.3_amd64.deb` from
`https://security.ubuntu.com/ubuntu/pool/main/b/bubblewrap/`: size 50,436 bytes,
SHA-256 `2461f1beee9cb04c8942739fe1a2b37e7b7c2a3d518f0779dc75f9245baa3094`,
SHA-512
`16cad315aa5a302ee8573c8ccb7e6adcdf5bd10dd29adeed0f7f061f39f7b52159d4020b2db1b1dde88fa7f7a3f54522d83037266c956a346882e234247c790b`,
reported version `bubblewrap 0.9.0`. Download to a fresh path, verify size and both
hashes, then install that exact package. APT substitution, an unverified cache, another
version, setuid fallback, a `--*-try` flag, failed namespace probe or host dependency
resolution is `PAUSE`.

#### 18.23.4 Provenance, licensing and replacement disposition

The packet retains the 110-package Python name/version inventory, 248 loaded-path/hash
resolutions, 509-ELF checks, original provisioning summary, rebound summary and both
complete inventories. The runtime contains its CPython license and installed Python
package license/notice files. Those facts prove the frozen bytes; they do not complete
public redistribution provenance.

The historical evidence does not bind every Python wheel/conda artifact, Node 26.9.0
distribution artifact, system-library package/source coordinate, license expression,
notice or reciprocal-source obligation. Therefore the frozen result is:

```text
PUBLICATION_ELIGIBLE=false
LICENSING_DISPOSITION=PAUSE
```

Before any external release grant, an independent licensing review must bind every
shipped component to exact binary/source provenance, license and notice bytes, and any
required corresponding-source delivery. It may not mutate this archive. If closure
requires added or changed bytes, the archive hash, packet, Kiro review and Ryan grant
must all be replaced. This is a material publication blocker, not a nit or an implied
authorization for Codex, Cursor or CI to acquire substitute bytes.

The proposed tag and asset are single-assignment. Creation is allowed only while both
are absent and only with the exact reviewed hash. Never overwrite, delete/recreate,
retag, resolve `latest`, follow a substituted asset, repair bytes or fall back to host
dependencies. A different archive, tree, toolchain, license result or compatibility
requirement uses a new tree-derived tag and a new reviewed packet.

Negative controls cover the already frozen changed-byte
`ddb476d3ccb8a11d3c379cfb53925bbd8e81024f753678d7fcdecad479ae19fe`,
changed-mode `0318dbf5410aef57b9f03b2cc9a2f7a994caea673e7feffc90609971bae7be19`,
removed-entry `73586a3f3ea59c3899a24425cd648ed53506920ae236c211f9d04bf3dab02838`
and unlisted-entry `467a35f2b30e7e2056c871c307f0955ec856afd42a68697e86bf366536c6010f`
mutant tree hashes, plus link/special/path-escape/duplicate member, changed archive,
changed bubblewrap package, failed namespace, host-resolution and mutable-coordinate
controls. Every control fails before qualified test import.

**Authority boundary.** This packet authorizes no tag, release, asset upload,
implementation, runtime-content change, evidence run, PR update, merge, deployment,
real OpenClaw or later gate. Exact-tip Kiro PASS is required on this parent/overlay.
Because licensing is `PAUSE`, even Kiro PASS does not make the asset externally
publishable; licensing closure and a separate exact Ryan external-action grant remain
mandatory.

### 18.24 Replacement qualified-runtime delivery set after licensing PAUSE

Section 18.23 remains the immutable record of the first delivery archive. Kiro passed
that packet's byte/mode/extraction design, and two independent provenance/licensing
reviews confirmed its own fail-closed disposition. The archive at SHA-256
`6f9cfa93e3847793a42279e6ff79e07ed0b47c23d6ec7a368a4e8cb530ce594e` is therefore
**rejected for publication**, not repaired or retroactively cleared. It remains local
diagnostic evidence and may never be uploaded under the proposed §18.23 coordinate.

The reviews established the following concrete gaps without alleging that ConvMem or
the aggregate is governed by any one component's license:

- the 110 top-level Python distribution records are not a complete component
  inventory: twelve setuptools-vendored distributions, the embedded
  `lib/python3.13/ensurepip/_bundled/pip-25.3-py3-none-any.whl`, native dependencies
  and SBOM-described Rust/C/C++ components require independent ownership rows;
- the positive control found packaged license material for 106 of 110 top-level
  distribution directories, while Apache-2.0 FlatBuffers and Tokenizers shipped no
  `LICENSE`, `NOTICE` or declared `License-File` in their installed artifacts;
- the copied sysroot includes Readline, glibc, GCC runtime libraries and other system
  components while containing no component-bound license, notice or corresponding-
  source material;
- the frozen Node 26.9.0 executable is not bound to an authenticated binary artifact,
  patches or build recipe, and its SHA-256 differs from the official Linux x64 binary;
  CPython's conda-forge origin is substantially recoverable but its installed
  relocation must be proved; and the locally built hnswlib extension has no retained
  source-to-binary recipe.

These findings freeze the successor starting state:

```text
REJECTED_RUNTIME_ARCHIVE_SHA256=6f9cfa93e3847793a42279e6ff79e07ed0b47c23d6ec7a368a4e8cb530ce594e
REJECTED_RUNTIME_PUBLICATION_ELIGIBLE=false
REPLACEMENT_DELIVERY_SET_STATUS=PLAN_ONLY
REPLACEMENT_PROVENANCE_CLOSURE=UNRESOLVED
REPLACEMENT_LICENSING_DISPOSITION=PAUSE
REPLACEMENT_PUBLICATION_ELIGIBLE=false
```

#### 18.24.1 One delivery set, three immutable assets

The replacement is one logical delivery set with exactly three roles:

1. a deterministic qualified-runtime archive containing only the rebuilt runtime,
   its exact inventory, an embedded copy of the component lock and the exact
   license/notice corpus needed by recipients;
2. a deterministic compliance archive containing every source artifact, patch,
   recipe, build/install script and offer/instruction material required by the
   reviewed license dispositions, plus an identical component lock and notice
   corpus; and
3. a canonical `delivery-set.json` manifest that binds the two archives by exact names,
   sizes, SHA-256 values, extracted-tree hashes and schema version. The
   later reviewed packet binds the manifest's own size and SHA-256; the manifest never
   attempts a recursive self-hash.

The final names, tag, counts and hashes do not exist yet and may not be invented by an
implementer. A later plan-only packet must pin them after an authorized deterministic
build. The tag and all three assets are single-assignment. Qualified admission requires
all three roles at the same immutable release coordinate; a missing, redirected,
substituted, re-uploaded, differently hashed or differently versioned role rejects the
entire set before extraction or test import. A standalone runtime archive is never an
admissible substitute.

This split is the least-worst boundary: executable/runtime bytes remain narrow, while
source and compliance material can be inspected independently. The duplicated component
lock and notice corpus must be byte-identical across the two archives, eliminating
ambiguity rather than creating two authorities. `delivery-set.json` is the only
set-level index; package metadata and SBOMs are evidence inputs, not competing
manifests.

#### 18.24.2 Exhaustive component and transformation lock

Before any replacement build grant, a read-only provenance reconstruction must produce
one canonical component lock and one complete file-ownership map. Every runtime regular
file maps to exactly one component artifact or to one explicitly named generated output
whose inputs and deterministic transformation are recorded. Overlapping ownership,
unowned bytes, ambiguous host origin, a missing nested archive/component or a fallback
row is `PAUSE`.

Each component row freezes at least: stable component ID and package URL where
available; exact name/version/build; selected SPDX license expression; original binary
artifact name, authenticated origin, size and SHA-256; corresponding source artifact or
commit, origin and SHA-256; patch hashes; build recipe, toolchain and flags; installed
file-set hash; license/notice member hashes; required source-delivery disposition; and
the runtime/compliance delivery paths satisfying that disposition. An `OR` license
expression requires an explicit reviewed choice and supporting bytes. METADATA, RECORD,
an installed filename, current-host package ownership or an SBOM label alone never
proves artifact provenance.

Recursive closure includes top-level packages, setuptools vendor trees, ensurepip
archives, wheel/conda/native contents, every embedded SBOM component, copied shared
libraries/data, Node, CPython, locally compiled extensions and generated launchers.
Observed counts such as 110 top-level distributions, twelve setuptools-vendored
distributions and Tokenizers' 127 SBOM components are audit controls, not completeness
ceilings. The final proof is set equality between every shipped regular file and the
canonical ownership map, plus a separate exact inventory of directories, links and
special files.

#### 18.24.3 Rebuild and minimization boundary

The replacement runtime is constructed into a new empty root from the locked artifacts;
it is not a copy, repair or overlay of the rejected tree. No live rolling-host file,
ambient package cache, mutable index response, `latest`, dependency resolver choice or
network-fetched unpinned byte may enter the build. Locally compiled output requires a
fresh build from its pinned source, patches, container/toolchain digest, environment and
command record; otherwise that component remains unresolved.

Before the lock is frozen, the designer may propose removing components that the strict
test workload and transitive loader/import closure do not require. Removal is not an
in-place cleanup and is never inferred from one successful run. It changes the runtime
tree and requires a new complete qualification. The final runtime must still provide
the parent-required CPython, Unicode, Node, MCP, IDNA, baseline/test dependency and
loader/library behavior without host fallback. A component stays if necessity or
license-safe replacement is uncertain.

The replacement uses a new versioned schema, archive/tree identities and tree-derived
release tag. It may reuse the §18.23 closed extraction and containment mechanisms only
after proving they apply to the new member layout. No §18.23 count, hash, compatibility
PASS or mutation negative transfers to the replacement.

#### 18.24.4 License, notice and corresponding-source closure

The compliance archive must contain the exact reviewed license and notice corpus and
all corresponding-source material required for the shipped bytes. Reciprocal-license
rows must state whether the distributed file is a library, executable, linked work,
aggregate or covered source, identify the precise obligation relied upon, and bind the
source, patches, build/install scripts and recipient instructions that fulfill it.
Permissive rows must retain their exact copyright/license/NOTICE material. MPL rows
must bind covered files to the delivered source. No implementer, package manager or CI
job may make a legal classification by inference.

An independent provenance/licensing reviewer, separate from the builder, verifies every
row and returns `PASS` or `PAUSE`. The reviewer may require human counsel for aggregate,
linking, exception, offer-duration or jurisdiction questions; absence of that
disposition is `PAUSE`. Kiro verifies design/scope and evidence bindings but does not
substitute for licensing disposition. Exact runtime qualification does not substitute
for either review.

#### 18.24.5 Gated actualization sequence

The successor sequence is closed:

1. Kiro reviews this plan-only correction. No build follows from PASS.
2. Under a separate Ryan provenance grant, Codex may derive the read-only component
   lock, ownership map, proposed source-delivery matrix and build recipe. No runtime or
   external coordinate is created.
3. Kiro and the independent provenance/licensing reviewer inspect that exact lock. Any
   unresolved row remains `PAUSE`.
4. Under a separate Ryan build grant naming the reviewed lock and disposable roots,
   the authorized builder creates the replacement set once, without mutating the old
   archive or source runtime, then stops.
5. Codex independently verifies construction, inventories, recursive ownership,
   license/notice/source closure, extraction, containment, host independence and the
   complete qualified test suite. A new plan-only packet then pins every final
   coordinate, size and hash.
6. Kiro reviews the exact final packet; an independent licensing reviewer rechecks the
   actual bytes. Only simultaneous technical, provenance and licensing PASS can make a
   later publication grant eligible.
7. Ryan alone may authorize the exact single-assignment external tag and three assets.
   Publication still does not authorize CI admission, PR modification or merge.
8. A separately authorized CI run downloads all three roles, verifies the set manifest
   and every frozen hash, then performs hosted-runner containment preflight before any
   qualified test import.

Negative controls must cover at least: missing/extra/duplicate component or file;
unowned and multiply owned file; nested archive/SBOM omission; changed selected license;
missing notice/source/patch/recipe; changed source or binary artifact; host/cache/index
fallback; nonreproducible local build; manifest disagreement; missing/substituted asset;
changed member/mode/hash; path escape/link/special file; mutable coordinate; and a
runtime that passes tests while compliance closure fails. Every control rejects before
publication or qualified import.

**Authority boundary.** This section authorizes planning-document edits only. It does
not authorize provenance acquisition, downloads, runtime construction, archive or
compliance-byte creation, tag/release/asset creation, product/test/CI/configuration
changes, evidence execution, PR update, merge, deployment, real OpenClaw, live data,
watch activation, promotion or Gates D/W/D-V/E/F. The rejected archive remains
immutable and unpublished. Each later step requires its own exact reviewed packet and
Ryan grant.

### 18.25 Provenance-lock schema packet

Section 18.24 requires the provenance outputs, their schemas and their locations to be
reviewed before any provenance execution. This section freezes that contract. It does
not create the packet, inspect or fetch an artifact, or close any unresolved row.

The schema packet is bound to the reviewed replacement-plan overlay and the rejected
runtime tree, not to a mutable branch or current host:

```text
PROVENANCE_SCHEMA_VERSION=convmem.switchboard.provenance-lock.v1
PROVENANCE_SCHEMA_PLAN_BASE_OVERLAY_SHA=3402e62a8479011814bfa76ce9e1c3269dc34350
PROVENANCE_INPUT_RUNTIME_ROOT=/home/lauer/.local/share/convmem-openclaw-runtimes/7dccb771b2f43288c52b7cb1dd18dedb18cb7e57/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
PROVENANCE_INPUT_RUNTIME_TREE_SHA256=74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b
PROVENANCE_INPUT_RUNTIME_REGULAR_FILE_COUNT=30421
PROVENANCE_PACKET_FILE_ROLE_COUNT=13
PROVENANCE_STAGING_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v1
PROVENANCE_DURABLE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v1
PROVENANCE_DURABLE_PACKET_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v1/packet
PROVENANCE_DURABLE_REVIEW_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v1/review
PROVENANCE_PACKET_STATUS=SCHEMA_ONLY
PROVENANCE_EXECUTION_AUTHORIZED=false
```

None of these paths exists by authority of this plan. A later exact grant may permit
Codex to create only those roots. Staging is disposable and never evidence. The packet
is written first to a same-filesystem sibling of `PROVENANCE_DURABLE_PACKET_ROOT`
ending `.partial`, verified, atomically renamed, made read-only and thereafter
immutable. The reviewer later creates `PROVENANCE_DURABLE_REVIEW_ROOT` by the same
closed partial-to-final process without touching the packet root. An existing target,
cross-filesystem rename, symlink in any ancestor, writable final member or second
packet/review at the same coordinate is `PAUSE`.
`PROVENANCE_SCHEMA_VERSION` and its roots are single-assignment: any semantic field,
type, enum, nullability, identity, closure, authority or negative-control change must
advance the version and bind a new reviewed staging/durable coordinate. Editorial
changes that do not alter this contract still require exact-tip review but cannot
reinterpret an existing packet.

#### 18.25.1 Canonical encoding and identifiers

Every `.jsonl` is UTF-8 without BOM, one compact JSON object plus LF per record, with
records sorted by the declared primary key's UTF-8 bytes. Every `.json` is one compact
JSON value plus LF. Objects use lexicographically sorted keys, separators `,` and `:`,
`ensure_ascii=false`, no duplicate keys, no floats, no surrogate code points and no
Unicode normalization. Strings preserve the observed Unicode scalar sequence. Hashes
are lowercase 64-character SHA-256 hex; sizes/counts are nonnegative decimal integers;
modes are four-character octal strings. Arrays declared as sets are unique and sorted
by UTF-8 bytes. Unknown keys, omitted required keys, CRLF, noncanonical escapes,
unordered records or a second textual encoding reject the packet.

Field types are closed. Names, versions, IDs, hashes, URLs, paths, media types,
expressions, rationales and enum values are strings; `_sha256` strings use the hash
rule above. Fields ending `_ids`, `_paths` or `_sha256s` are arrays of strings.
Counts, sizes and `http_status` are integers (`http_status` is 100–599 when non-null).
`human_counsel_required`, `reciprocal_review_required` and `blocks` are booleans.
`argv` is an ordered string array; `environment` is an object from string keys to
string values. Timestamps are UTC RFC 3339 strings with whole seconds and trailing
`Z`. `redirect_chain` is an ordered URL array; every other scalar array is a set and
therefore sorted. `packet_files`, `license_texts`, `notice_texts` and
`copyright_texts` are arrays of the exact row objects specified below and sorted by
`path` or `delivery_path`; `reviewed_packet_file_sha256s` is an array of exact
`{path,sha256}` objects sorted by `path`; `review_scope` is a sorted string set; and
`reviewer` is exactly `{actor,lane,tool,tool_version}` with string values. No implicit
string-to-number/boolean coercion is allowed.

Required keys are always present, but reconstruction must represent unknowns without
inventing authority. `null` is allowed only for `objects.source_url` on an
`existing-runtime` object; observation `request_url` and `final_url` on a
`retained-local` `READ_RETAINED`; observation `source_path` on `https` or `vcs-https`;
observation `http_status` on a `vcs-https` `FETCH_OBJECT` or `retained-local`
`READ_RETAINED`; the nullable component identity fields `build`, `purl` and
`origin_namespace`; `source-artifacts.revision` for a release/source-package archive;
and `transformations.builder_image_digest` for a non-build copy/member/link operation.
In addition, `component-lock.selected_license_expression` and `source_delivery_id`,
`file-ownership.component_id`, `origin_kind`, `origin_id` and `origin_member_path`, and
artifact `authority_observation_id` may be `null` only when one matching `unresolved`
row names that exact subject and field. Build eligibility permits none of those
unresolved null cases.

Empty arrays are closed by field: `objects.authority_observation_ids` is empty only for
`existing-runtime`; an observation's `redirect_chain` is empty only when no redirect
occurred and `proof_object_ids` is empty only when `response_object_id` is itself the
complete authority proof; artifact `signature_object_ids` is empty only for
`not-published`, `not-applicable` or an exact unresolved signature row; transformation
`patch_object_ids` may be empty for an unpatched input; license `notice_texts`,
`copyright_texts` and `human_questions` may be empty when the reviewed license basis
does not require them; and source-delivery `patch_object_ids` may be empty for an
unpatched source. `review-disposition.open_unresolved_ids` is empty only when every
verdict is `PASS`. Every other required reference array is nonempty unless one matching
`unresolved` row names that exact subject and field; transformation inputs additionally
require at least one of `input_artifact_ids` or `input_object_ids`. Build eligibility
permits no unresolved empty case.

Runtime-relative paths use `/`, are nonempty UTF-8 strings and preserve exact bytes
under the runtime's proven UTF-8 path inventory. Absolute paths, backslashes, NUL,
empty/dot/dot-dot segments and normalized aliases reject. The sole exception is an
observation `source_path`, which is an exact absolute path under one future grant-named
read-only retained-source root and never enters a replacement artifact. URLs are
retained exactly as observed, including redirect order, but must contain no userinfo,
credential, secret or tracking token.

Content objects use `obj_sha256:<hex>`. Binary/source artifacts use respectively
`bin_sha256:<object-hex>` and `src_sha256:<object-hex>`. A component ID is
`cmp_sha256:<hex>`, where `<hex>` hashes the canonical JSON object containing exactly
`ecosystem,name,version,build,purl,origin_namespace`; nullable fields are present as
`null`. A transformation ID is `xform_sha256:<hex>` over its complete canonical row
with `transformation_id` omitted. Notice, source-delivery, observation and unresolved
IDs use the same prefix-plus-hash rule over their complete row with the ID omitted.
IDs are recomputed independently; caller-selected labels are descriptive only.

For each packet file, the manifest records raw-byte SHA-256, size, record count and
`primary_key_sha256`, computed over each sorted primary-key UTF-8 byte sequence followed
by one NUL. Empty JSONL has SHA-256 of empty bytes, zero records and the SHA-256 of empty
bytes as its primary-key hash. The manifest never self-hashes. A later overlay binds
the manifest's size and SHA-256; the independent review disposition separately binds
that manifest hash, avoiding circular identity.

#### 18.25.2 Closed packet files and schemas

`PROVENANCE_DURABLE_PACKET_ROOT` contains exactly an `objects/` content-addressed tree
and the first twelve regular mode-`0444` files below; directories are mode `0555`.
`PROVENANCE_DURABLE_REVIEW_ROOT` later contains only the thirteenth file,
`review-disposition.json`, at mode `0444`. No other member, link or special file is
allowed in either leaf root.

| File | Format and primary key | Required fields |
|---|---|---|
| `provenance-lock-manifest.json` | one object; no self-hash | `schema`, `plan_base_overlay_sha`, `input_runtime_tree_sha256`, `runtime_regular_file_count`, `packet_files`, `object_count`, `object_bytes`, `object_tree_sha256`, `unresolved_count`, `created_at_utc`; each `packet_files` row has exactly `path,size,sha256,record_count,primary_key_sha256` |
| `objects.jsonl` | JSONL; `object_id` | `schema`, `object_id`, `sha256`, `size`, `media_type`, `acquisition_kind`, `source_url`, `authority_observation_ids`, `observed_at_utc`, `relative_path`; `relative_path` is exactly `objects/sha256/<first-two-hex>/<64-hex>` |
| `authority-observations.jsonl` | JSONL; `observation_id` | `schema`, `observation_id`, `ecosystem`, `authority_class`, `transport`, `operation`, `request_url`, `final_url`, `source_path`, `redirect_chain`, `http_status`, `response_object_id`, `proof_kind`, `proof_object_ids`, `observed_at_utc` |
| `component-lock.jsonl` | JSONL; `component_id` | `schema`, `component_id`, identity tuple fields, `runtime_scope`, `selected_license_expression`, `binary_artifact_ids`, `source_artifact_ids`, `transformation_ids`, `license_notice_ids`, `source_delivery_id`, `evidence_object_ids` |
| `file-ownership.jsonl` | JSONL; `path` | `schema`, `path`, `mode`, `size`, `sha256`, `component_id`, `origin_kind`, `origin_id`, `origin_member_path`; `origin_kind` is only `binary-artifact`, `source-artifact` or `generated` |
| `nested-components.jsonl` | JSONL; tuple `container_component_id,nested_component_id,relationship` joined with NUL | `schema`, the primary-key fields, `evidence_object_id`, `evidence_path`; relationship is only `vendored`, `embedded`, `statically-linked`, `dynamically-linked` or `generated-from` |
| `binary-artifacts.jsonl` | JSONL; `binary_artifact_id` | `schema`, `binary_artifact_id`, `component_id`, `object_id`, `filename`, `artifact_type`, `authority_observation_id`, `signature_status`, `signature_object_ids`, `member_count`, `selected_member_set_sha256` |
| `source-artifacts.jsonl` | JSONL; `source_artifact_id` | `schema`, `source_artifact_id`, `component_id`, `object_id`, `filename`, `source_kind`, `revision`, `authority_observation_id`, `signature_status`, `signature_object_ids` |
| `transformations.jsonl` | JSONL; `transformation_id` | `schema`, `transformation_id`, `component_id`, `kind`, `input_artifact_ids`, `input_object_ids`, `patch_object_ids`, `toolchain_component_ids`, `builder_image_digest`, `argv`, `environment`, `working_directory`, `output_paths`, `output_set_sha256`; no shell string is accepted for `argv` |
| `license-notices.jsonl` | JSONL; `license_notice_id` | `schema`, `license_notice_id`, `component_id`, `selected_spdx_expression`, `selection_basis_object_ids`, `license_texts`, `notice_texts`, `copyright_texts`, `reciprocal_review_required`, `human_questions`; each delivered text row binds `object_id,source_member,delivery_path,sha256` |
| `source-delivery.jsonl` | JSONL; `source_delivery_id` | `schema`, `source_delivery_id`, `component_id`, `obligation_class`, `trigger`, `source_artifact_ids`, `patch_object_ids`, `recipe_transformation_ids`, `instruction_object_ids`, `delivery_paths`, `availability_owner`, `availability_period`, `review_status`, `review_rationale_object_id` |
| `unresolved.jsonl` | JSONL; `unresolved_id` | `schema`, `unresolved_id`, `subject_type`, `subject_id`, `field`, `reason_code`, `required_evidence`, `status`, `blocks`; `status` is always `OPEN`, `blocks` is always `true` |
| `review-disposition.json` | one object; separately created by the independent reviewer | `schema`, `manifest_sha256`, `reviewed_packet_file_sha256s`, `reviewer`, `review_scope`, `technical_verdict`, `provenance_verdict`, `licensing_verdict`, `human_counsel_required`, `open_unresolved_ids`, `reviewed_at_utc`; verdict values are only `PASS` or `PAUSE` |

`packet_files` covers the other eleven packet ledgers but not
`review-disposition.json`; the review disposition instead binds the immutable manifest
and every reviewed packet-file hash. `objects.jsonl` is the only object inventory:
every row has one matching regular object file, every object file has one row, and its
path, filename, size and hash must agree. `object_tree_sha256` hashes the canonical
sorted compact-JSON array of `relative_path,size,sha256` rows. No object is executed,
imported or installed during provenance work.

The exact enumerations are:

- component/observation `ecosystem`: `python`, `node`, `rust`, `system`,
  `toolchain`, `generated`, `other-reviewed`;
- `runtime_scope`: `runtime`, `runtime-vendored`, `build-only`, `source-only`;
- `acquisition_kind`: `existing-runtime`, `existing-cache`, `registry-metadata`,
  `authority-response`, `binary-artifact`, `source-artifact`, `license-text`,
  `notice-text`, `signature`, `build-recipe`, `review-rationale`;
- `authority_class`: `original-distributor`, `original-project`, `signed-index`,
  `signed-checksum`, `immutable-vcs`, `retained-package-record`,
  `retained-build-record`;
- observation `transport`: `https`, `vcs-https`, `retained-local`; observation
  `operation`: `GET`, `HEAD`, `FETCH_OBJECT`, `READ_RETAINED`; `GET` and `HEAD`
  require `https`, `FETCH_OBJECT` requires `vcs-https`, and `READ_RETAINED` requires
  `retained-local`;
- `proof_kind`: `original-release-metadata`, `artifact-checksum`,
  `detached-signature`, `signed-index`, `immutable-vcs-object`,
  `retained-package-record`, `retained-build-record`;
- `signature_status`: `verified`, `not-published`, `not-applicable`, `unresolved`;
- binary `artifact_type`: `python-wheel`, `conda-package`, `npm-package`,
  `system-package`, `node-binary`, `native-library`, `executable`, `archive`,
  `other-reviewed`;
- `source_kind`: `release-archive`, `vcs-commit`, `source-package`, `generated-source`;
- transformation `kind`: `install-copy`, `archive-member`,
  `conda-prefix-relocation`, `build`, `generated`, `statically-linked`,
  `dynamically-linked`;
- `obligation_class`: `permissive-notice`, `apache-notice`, `python-license`,
  `mpl-covered-source`, `lgpl-library`, `gpl-corresponding-source`,
  `gcc-runtime-exception`, `other-reviewed`, `none-reviewed`;
- `review_status`: `PASS`, `PAUSE`; and
- `reason_code`: `missing-origin`, `missing-binary`, `missing-source`,
  `missing-signature`, `missing-recipe`, `missing-owner`, `multiple-owners`,
  `missing-license`, `missing-notice`, `license-choice`, `source-obligation`,
  `human-disposition`, `hash-mismatch`, `unsupported-format`, `other-reviewed`.

Every enum expansion is a semantic change requiring a new reviewed schema version.

#### 18.25.3 Cross-file closure and eligibility

The packet is structurally valid when every byte is canonical, every present reference
resolves, all inventories/hashes agree and every missing authority value has one exact
`unresolved` row. Structural validity permits an honest `PAUSE` packet. Build
eligibility requires all of these independently recomputed equalities:

1. the exact rejected-runtime regular-file inventory equals `file-ownership.jsonl` by
   path, mode, size and SHA-256;
2. every file has one non-null owner and one existing non-null origin reference; every component,
   artifact, transformation, notice, delivery and evidence reference resolves exactly
   once with no orphan row;
3. every component reachable through a nested relation exists in `component-lock`, and
   every nested/bundled/SBOM-declared component is represented; observed counts such as
   110 top-level distributions, twelve setuptools-vendored distributions, the embedded
   ensurepip wheel and Tokenizers' 127 SBOM components are positive controls, not
   ceilings;
4. every binary/source artifact and authority response has one matching immutable
   object; every generated file is in one transformation's exact output set; and every
   transformation input, patch and toolchain reference resolves;
5. every runtime or runtime-vendored component has a non-null selected license expression, a
   license/notice row and one source-delivery row; every `OR` choice has evidence and
   every reciprocal row has the required source, patch, recipe, instruction and human
   disposition references;
6. `objects/` and `objects.jsonl` are equal sets, all packet hashes/counts agree, no
   credential/private data is present, and all paths/modes/types satisfy this section;
7. `unresolved.jsonl` may contain open rows during reconstruction, but build eligibility
   requires the canonical empty file, `unresolved_count=0`, and independent technical,
   provenance and licensing `PASS` in `review-disposition.json`.

A lower count, a successful runtime test, a package-manager claim, a copied license
directory or a reviewer statement without exact manifest/hash bindings cannot satisfy
closure.

#### 18.25.4 Source-authority and network boundary

Future provenance execution is read-only acquisition. The grant must name the exact
allowed HTTPS origins and operations before any request. Eligible evidence is limited
to an original package distributor or project, its authenticated release metadata,
signed checksum/index/package records, an immutable VCS commit/release, or a retained
exact package/build record whose bytes are also captured. Search results, mirrors not
named by the authoritative metadata, the current host package database by itself,
mutable branch heads, `latest`, unauthenticated HTTP, ambient caches and inferred URLs
are never authority.

`response_object_id` always resolves to the retained canonical response envelope: for
HTTP it contains status and selected identity-bearing headers plus any response body;
for immutable VCS acquisition it contains the exact remote, requested object ID,
resolved object ID and fetch transcript; for a retained-local read it contains the
grant-named root, exact source path, pre/post identity and mutation check. A `HEAD`, VCS
or retained-local observation therefore still has a response object even when no
artifact body exists. That envelope is evidence,
not a substitute for the separately hashed artifact/source object.

Every request and redirect is recorded in `authority-observations.jsonl`; a redirect to
an ungranted origin, credentialed URL, HTML interstitial in place of an artifact,
changed ETag/content bytes, signature/checksum disagreement or unavailable proof is
`PAUSE`. TLS alone establishes transport, not artifact identity. Downloaded bytes land
under staging `incoming/`, are hashed before parsing, move to their content-addressed
staging object path only after the expected identity matches, and are copied to durable
evidence only in the final atomic packet. Parsers may list or safely extract data into
disposable directories but may not execute setup hooks, imports, binaries, package
installers, shell fragments, build scripts or downloaded code.

The later execution grant may allow only HTTP `GET`/`HEAD`, immutable VCS object
fetches from its named origins and `READ_RETAINED` under exact named read-only roots.
It may not authenticate, upload, comment, publish,
create a repository/ref/release/asset, accept a license on Ryan's behalf or incur a
paid service. An origin discovered during execution but absent from the grant becomes
one `unresolved` row and stops acquisition for that component.

#### 18.25.5 Negative controls and supervision

Before a packet can be reviewed, independent mutants must prove rejection for:

- BOM/CRLF/noncanonical JSON, reordered/duplicate records or keys, unknown/missing key,
  invalid enum, changed mode/path/hash/count or manifest self-reference;
- one missing/extra object, ledger or runtime row; unowned, multiply owned or dangling
  component/artifact/transformation/notice/source reference;
- omitted setuptools/ensurepip/SBOM/native/sysroot member, nested-cycle or a positive-
  control count treated as a completeness ceiling;
- binary/source/signature/checksum/recipe/toolchain mismatch, current-host or ambient-
  cache substitution, retained-source root/path escape or mutation, ungranted
  redirect/origin, mutable ref or executed downloaded content;
- absent license/notice, unreviewed `OR` choice, missing reciprocal source/patch/build/
  instruction, self-authored legal conclusion or `PASS` with one unresolved row;
- staging cited as evidence, partial/cross-filesystem publication, existing destination,
  writable/symlink/special final member, manifest/disposition mismatch or review over a
  different packet hash.

Codex is the only authorized future provenance executor and packet collector. The
independent provenance/licensing reviewer creates only
`PROVENANCE_DURABLE_REVIEW_ROOT/review-disposition.json` after verifying the immutable
packet root; that reviewer does not repair evidence. Kiro reviews
design/scope and exact bindings, not legal sufficiency. Any correction creates a new
staging root and reviewed packet identity; no in-place durable repair is allowed.

**Authority boundary.** This section authorizes only the four planning-document edits.
It creates no evidence root and authorizes no provenance HTTP/VCS request, artifact
download, upstream VCS fetch, archive parsing, runtime inspection, provenance execution,
license acceptance, build, install, runtime/compliance/manifest creation, external
coordinate, product/test/CI/configuration change, PR update, evidence run, merge,
deployment, real OpenClaw, live data, watch activation, promotion or Gates
D/W/D-V/E/F. Kiro exact-tip PASS and a new Ryan provenance-execution grant naming the
exact roots, origins and operations remain mandatory.

### 18.26 Provenance-lock v2 CycloneDX revision projection

The first offline P0 execution of §18.25 stopped while projecting retained CycloneDX
evidence into `component-lock.jsonl`. The stopped schema-v1 staging tree is rejected
diagnostic evidence: it is never a packet, never authority, never repaired in place and
never copied into a successor packet. No schema-v1 durable packet or review root was
created.

The stop is bound to these exact facts:

```text
PROVENANCE_SCHEMA_V2_PLAN_BASE_OVERLAY_SHA=5f3978525c8685f59329ccae78d184d4a1822b4b
PROVENANCE_V1_FIRST_COLLECTOR_SHA256=e84cf1e633541b9a7343bbaf78457573cf041e7f59f0cc71d6c7be8d491de59e
PROVENANCE_V1_FIRST_INCORRECT_PROJECTION_SHA256=22da33da243b6fa7a7e75abe1e290fae22f2bf1d7ae87bb78ea4fd981b2e4bc4
PROVENANCE_V1_RETRY_COLLECTOR_SHA256=c9ef70f2a728cac680a1227b5bafc5533a3211f244e1abbf2f89906749eae028
PROVENANCE_V1_RUNTIME_CONTENT_PASS_COUNT=2
PROVENANCE_V1_RUNTIME_READ_BYTES=4537493452
PROVENANCE_V1_EVIDENCE_FILE_COUNT=780
PROVENANCE_V1_EVIDENCE_BYTES=600463206
PROVENANCE_V1_CYCLONEDX_DOCUMENT_COUNT=13
PROVENANCE_V1_CYCLONEDX_COMPONENT_COUNT=1371
PROVENANCE_V1_UNREPRESENTABLE_COMPONENT_COUNT=1
PROVENANCE_V1_SBOM_OBJECT_SHA256=d3c068f4be653f38b8f6fca1dd1a9d1b41dc712dc9c3daa01b0e0f84882324d6
PROVENANCE_V1_SBOM_COMPONENT_INDEX=0
PROVENANCE_V1_SBOM_NAME=base64
PROVENANCE_V1_SBOM_PURL=pkg:github/aklomp/base64@bf058e571ac5002b75b03fed38e33ed4e8d45eff
PROVENANCE_V1_SBOM_BOM_REF=pkg:github/aklomp/base64@bf058e571ac5002b75b03fed38e33ed4e8d45eff
PROVENANCE_V1_SBOM_VERSION_ASSUMPTION=null
```

The retry had already corrected `tree_inventory_hash()` so every inventory-row hash is
encoded as `sha256:<64-lowercase-hex>`, matching the governed runtime inventory. It then
proved the exact 30,421-file runtime tree before stopping at the sole missing component
version. That collector correction and the amended read ceiling do not authorize a
third schema-v1 pass. The consumed reads above remain part of the rejected v1 ledger.

Schema v2 keeps every §18.25 encoding, file-role, ownership, closure, source-authority
and review rule except the one closed component-version projection below. It binds new
single-assignment roots:

```text
PROVENANCE_SCHEMA_VERSION=convmem.switchboard.provenance-lock.v2
PROVENANCE_INPUT_RUNTIME_ROOT=/home/lauer/.local/share/convmem-openclaw-runtimes/7dccb771b2f43288c52b7cb1dd18dedb18cb7e57/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
PROVENANCE_INPUT_RUNTIME_TREE_SHA256=74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b
PROVENANCE_INPUT_RUNTIME_REGULAR_FILE_COUNT=30421
PROVENANCE_PACKET_FILE_ROLE_COUNT=13
PROVENANCE_STAGING_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v2
PROVENANCE_DURABLE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v2
PROVENANCE_DURABLE_PACKET_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v2/packet
PROVENANCE_DURABLE_REVIEW_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v2/review
PROVENANCE_PACKET_STATUS=PLAN_ONLY
PROVENANCE_EXECUTION_AUTHORIZED=false
```

#### 18.26.1 Closed version projection

For a CycloneDX component, an existing nonempty string `version` remains the exact
observed version string. It is not normalized. A JSON `null` version may be projected
only when all of these conditions hold simultaneously:

1. `name` is a nonempty string;
2. `bom-ref` and `purl` are both strings and are byte-for-byte identical; and
3. that shared string matches exactly
   `^pkg:github/[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*@([0-9a-f]{40})$`.

The projected component `version` is the captured 40-lowercase-hex group exactly. The
original `name`, then-assumed JSON-null `version` state, `purl`, `bom-ref`, component
index and complete SBOM object were intended to bind the projection; §18.27 later
proves the raw member is absent and supersedes that premise. The projected version is
an immutable source revision identifier for component identity; it is not a release
tag, license conclusion, artifact identity or authority to fetch/build anything.

There is no second derivation route. Empty or non-string names; an absent, empty or
non-string version; a non-null empty version; missing or unequal `bom-ref`/`purl`;
uppercase or non-40-hex revisions; qualifiers (`?`), subpaths (`#`), userinfo,
percent-encoding or any mutable/non-GitHub form remain `PAUSE`. The collector may not
case-fold, percent-decode, Unicode-normalize, URL/PURL-normalize, follow aliases, infer
a tag/version, consult the network or substitute package metadata. Any component not
representable by the original v1 rule or this one projection creates an exact open
`unresolved` row and blocks build eligibility.

#### 18.26.2 Freshness, negative controls and authority boundary

A future v2 execution must start from absent `schema-v2` staging/durable roots and
repeat the complete governed runtime inventory and bounded evidence selection. It may
use only a freshly frozen collector whose sole semantic difference from the corrected
v1 retry collector is §18.26.1. It may not read, copy, hard-link or cite any object,
ledger, manifest, counter or partial output from `schema-v1/packet.work`. The v1
collector identities, read counters and stop record remain evidence of the rejected
attempt, not inputs to v2 acceptance.

Negative controls must independently reject at least: null/empty/missing/non-string
`name`; missing/empty/non-string `purl` or `bom-ref`; unequal `purl` and `bom-ref`;
uppercase, short, long or nonhex revisions; tags or branch names; qualifiers, subpaths,
userinfo or percent-encoded aliases; any non-GitHub PURL; any normalization or network
lookup; reuse of a v1 object; a second projected component not satisfying the closed
grammar; and a packet that omits the raw SBOM-to-projection evidence binding.

**Authority boundary.** This section authorizes only planning-document edits. It does
not authorize a schema-v2 directory, packet retry, runtime/evidence read, collector
execution, network request, artifact parsing, retained-source inspection, packet or
review creation, product/test/CI/runtime/configuration change, build, publication, PR
update, merge, deployment, real OpenClaw, live data, watch activation, promotion or
Gates D/W/D-V/E/F. Kiro exact-tip PASS and a new Ryan P0 execution grant naming the
schema-v2 roots, collector identity, read ceilings and operations remain mandatory.

### 18.27 Provenance-lock v3 exact absent-version projection

The single granted schema-v2 P0 execution disproved one premise of §18.26 without
weakening its fail-closed boundary. The retained `base64` component does not encode
`"version": null`; its `version` member is absent. The frozen v2 collector therefore
exited at `missing SBOM component version` before writing any ledger, manifest, result,
durable packet or review disposition. That refusal is correct under schema v2. The
schema-v2 staging tree is rejected diagnostic evidence: it remains untouched, is never
a packet or authority, and no byte, object or conclusion may be copied, hard-linked,
resumed or accepted by a successor.

The stopped attempt is bound to these exact facts. Runtime-read counters are derived
from the frozen collector's completed first inventory pass plus its completed bounded
780-file evidence copy; the absence of `p0-result.json` is preserved rather than
papered over. The v2 delta is exactly `1,968,515,123 + 600,463,206 =
2,568,978,329` bytes, and the cumulative ledger is exactly `4,537,493,452 +
2,568,978,329 = 7,106,471,781` bytes:

```text
PROVENANCE_SCHEMA_V3_PLAN_BASE_OVERLAY_SHA=2956f70127544111d5d32e2f51a3e044fe878fb4
PROVENANCE_V2_COLLECTOR_SHA256=737aa48f1b6d99111e98ac0bd5b75445b1896ed937d5676e404b8630ad0c220f
PROVENANCE_V2_COLLECTOR_DIFF_SHA256=3065e94c18525191ebed2759001ec399b042131f8ad1214cccdc6a102dfb7c78
PROVENANCE_V2_COLLECTOR_RECEIPT_SHA256=c5d63d15468eb2270ebf9c1002aa7640b784159d33499c2737623f24a5047a1b
PROVENANCE_V2_EXIT_STATUS=1
PROVENANCE_V2_FAILURE=missing SBOM component version
PROVENANCE_V2_RUNTIME_CONTENT_PASS_COUNT=1
PROVENANCE_V2_RUNTIME_READ_BYTES=2568978329
PROVENANCE_CUMULATIVE_RUNTIME_CONTENT_PASS_COUNT=3
PROVENANCE_CUMULATIVE_RUNTIME_READ_BYTES=7106471781
PROVENANCE_V2_EVIDENCE_FILE_COUNT=780
PROVENANCE_V2_EVIDENCE_BYTES=600463206
PROVENANCE_V2_PARTIAL_OBJECT_COUNT=651
PROVENANCE_V2_PARTIAL_OBJECT_BYTES=600094627
PROVENANCE_V2_STAGING_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v2
PROVENANCE_V2_RESULT_PRESENT=false
PROVENANCE_V2_DURABLE_ROOT_PRESENT=false
PROVENANCE_V2_REVIEW_ROOT_PRESENT=false
PROVENANCE_V2_SBOM_OBJECT_SHA256=d3c068f4be653f38b8f6fca1dd1a9d1b41dc712dc9c3daa01b0e0f84882324d6
PROVENANCE_V2_SBOM_COMPONENT_PATH=components/0
PROVENANCE_V2_SBOM_COMPONENT_CANONICAL_SHA256=820f3546548cdbcda11395dbeeb274485b71582c0316bf0518d78fe7d209994b
PROVENANCE_V2_SBOM_COMPONENT_KEY_SET_SHA256=1516b75285ffd5cd81f18728ba54daa50a5991ea5e63c0b00a4d71bb26bda2ee
PROVENANCE_V2_SBOM_COMPONENT_KEYS=bom-ref,externalReferences,licenses,name,purl,type
PROVENANCE_V2_SBOM_VERSION_KEY_PRESENT=false
PROVENANCE_V2_SBOM_NAME=base64
PROVENANCE_V2_SBOM_PURL=pkg:github/aklomp/base64@bf058e571ac5002b75b03fed38e33ed4e8d45eff
PROVENANCE_V2_SBOM_BOM_REF=pkg:github/aklomp/base64@bf058e571ac5002b75b03fed38e33ed4e8d45eff
PROVENANCE_V2_PROJECTED_VERSION=bf058e571ac5002b75b03fed38e33ed4e8d45eff
```

Schema v3 keeps every §18.25 encoding, file-role, ownership, closure,
source-authority and review rule. It supersedes only §18.26.1's raw input-state
predicate and binds new, absent, single-assignment roots:

```text
PROVENANCE_SCHEMA_VERSION=convmem.switchboard.provenance-lock.v3
PROVENANCE_INPUT_RUNTIME_ROOT=/home/lauer/.local/share/convmem-openclaw-runtimes/7dccb771b2f43288c52b7cb1dd18dedb18cb7e57/5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d
PROVENANCE_INPUT_RUNTIME_TREE_SHA256=74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b
PROVENANCE_INPUT_RUNTIME_REGULAR_FILE_COUNT=30421
PROVENANCE_PACKET_FILE_ROLE_COUNT=13
PROVENANCE_STAGING_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3
PROVENANCE_DURABLE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3
PROVENANCE_DURABLE_PACKET_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet
PROVENANCE_DURABLE_REVIEW_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review
PROVENANCE_PACKET_STATUS=PLAN_ONLY
PROVENANCE_EXECUTION_AUTHORIZED=false
```

#### 18.27.1 Sole exact absent-member projection

An existing nonempty string `version` remains its exact observed string. Schema v3
admits exactly one absent-member projection, and only when all of these predicates hold
simultaneously:

1. the complete retained SBOM object is exactly
   `obj_sha256:d3c068f4be653f38b8f6fca1dd1a9d1b41dc712dc9c3daa01b0e0f84882324d6`;
2. the component path is exactly `components/0`;
3. the component's canonical compact sorted-key JSON SHA-256 is exactly
   `820f3546548cdbcda11395dbeeb274485b71582c0316bf0518d78fe7d209994b`, its
   sorted NUL-terminated key-set SHA-256 is exactly
   `1516b75285ffd5cd81f18728ba54daa50a5991ea5e63c0b00a4d71bb26bda2ee`,
   and its exact key set is `bom-ref,externalReferences,licenses,name,purl,type`;
4. `version` is absent as an object member, not present as null, empty or another type;
5. `name` is exactly `base64`, while `bom-ref` and `purl` are byte-identical and
   exactly
   `pkg:github/aklomp/base64@bf058e571ac5002b75b03fed38e33ed4e8d45eff`; and
6. that shared string independently matches §18.26's closed GitHub grammar and its
   captured group is exactly `bf058e571ac5002b75b03fed38e33ed4e8d45eff`.

The projected component version is that exact captured revision. The projection record
uses `raw_version_state="absent"`; it must not manufacture `raw_version=null` or a raw
`version` member. The complete raw SBOM object, component path, canonical component
hash, key-set hash, exact fields and projected value remain jointly bound evidence.
This rule is an exact-object exception, not a declaration that missing and null are
equivalent. An explicit JSON null, an absent `version` on any other component, or a
reconstructed component with the same visible identity but different object/component
hash remains `PAUSE`.

There is no second derivation route. Case folding, percent decoding, Unicode/URL/PURL
normalization, alias following, metadata substitution, tag/branch inference, network
lookup, qualifier/subpath removal or object reconstruction is forbidden. The projected
revision is component identity only; it grants no source authority, artifact identity,
license conclusion, acquisition, build or publication authority.

#### 18.27.2 Freshness, read ledger, controls and authority boundary

A future schema-v3 P0 must start from absent `schema-v3` staging and durable roots.
It may use only a freshly frozen collector whose sole semantic difference from the
frozen v2 collector is §18.27.1. The collector must begin with the cumulative consumed
ledger of three complete runtime-content passes and `7,106,471,781` runtime bytes. A
future grant may allow at most two additional complete runtime passes plus the same
bounded evidence selection (`4,537,493,452` additional bytes;
`11,643,965,233` cumulative bytes). It may not reset, reinterpret or omit the v1/v2
reads and may not read, copy, hard-link, cite or delete any v1/v2 partial object,
ledger, result or manifest.

Negative controls must independently reject at least: the same component with explicit
JSON null, empty/non-string `version`, a manufactured `version` member, any different
object/component/key-set hash or component path, another absent-version component,
missing/changed/non-string name/PURL/`bom-ref`, unequal identities, uppercase/short/
long/nonhex revision, tag/branch, qualifier, subpath, userinfo, percent alias,
non-GitHub PURL, normalization/lookup/second route, raw-binding omission, v1/v2 object
reuse, preexisting v3 output and a second projected component. The positive control is
exactly one projection with `raw_version_state="absent"`; zero or two projections is
`PAUSE`.

**Authority boundary.** This section authorizes only the four planning-document edits.
It does not authorize a schema-v3 directory, collector freeze or execution, runtime or
evidence read, deletion of rejected staging, network request, artifact parsing,
retained-source inspection, packet/review creation, product/test/CI/runtime/
configuration change, build, publication, PR update, merge, deployment, real OpenClaw,
live data, watch activation, promotion or Gates D/W/D-V/E/F. Kiro exact-tip PASS and a
new Ryan P0 grant naming the schema-v3 roots, collector identity, cumulative/additional
read ceilings and exact operations remain mandatory.

### 18.28 Schema-v3 offline P0 result and independent-review hold

The separately granted schema-v3 offline P0 execution completed exactly once. The
frozen collector exited zero after publishing one immutable packet leaf, but the packet
honestly reports `status="PAUSE"` and `build_eligible=false`. Structural completion is
not provenance closure. The durable packet is eligible only for exact-byte review; it
is not eligible for build, publication, CI admission or implementation use.

#### 18.28.1 Exact result and immutable packet identity

The following facts are frozen together and may not be recomputed into a replacement
identity, edited in place or combined with schema-v1/v2 staging:

```text
PROVENANCE_V3_COLLECTOR_SHA256=26352b39f3ff53bf8a41c579c4c9aec8a8f8734235fe99db0a8480fa9964adad
PROVENANCE_V3_COLLECTOR_SIZE=67575
PROVENANCE_V3_COLLECTOR_FREEZE_SHA256=c8f457b589b6554a33921965339a74db086806d9243bb5fa4565df39b5e74ada
PROVENANCE_V3_COLLECTOR_DIFF_SHA256=be6b82f89aaac51cc8ae1cbaace78d111dc0f00de92ee7a45009d57d182f59a5
PROVENANCE_V3_RESULT_SHA256=db755121a38ffa43587662337bf896196a944bdaaf0019e899c13bc0afb43045
PROVENANCE_V3_RESULT_SIZE=20155
PROVENANCE_V3_MANIFEST_SHA256=6791d33a82bd0f1e3fdbda072ae50aa296953b6a365194564090085541784fa4
PROVENANCE_V3_MANIFEST_SIZE=2957
PROVENANCE_V3_PACKET_TREE_SHA256=491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5
PROVENANCE_V3_PACKET_BYTES=654147403
PROVENANCE_V3_OBJECT_COUNT=651
PROVENANCE_V3_OBJECT_BYTES=600094627
PROVENANCE_V3_COMPONENT_COUNT=1221
PROVENANCE_V3_NESTED_COMPONENT_EDGE_COUNT=1384
PROVENANCE_V3_OWNED_FILE_COUNT=30402
PROVENANCE_V3_UNOWNED_OR_AMBIGUOUS_FILE_COUNT=19
PROVENANCE_V3_UNRESOLVED_COUNT=98608
PROVENANCE_V3_RUNTIME_CONTENT_PASS_COUNT=5
PROVENANCE_V3_RUNTIME_READ_BYTES=11643965233
PROVENANCE_V3_NEGATIVE_CONTROL_COUNT=65
PROVENANCE_V3_PACKET_STATUS=PAUSE
PROVENANCE_V3_BUILD_ELIGIBLE=false
PROVENANCE_V3_REVIEW_ROOT_PRESENT=false
```

`p0-result.json` is mode `0400` staging evidence outside the packet. The staging
`packet.work` and durable `packet` trees are mode-for-mode and byte-for-byte equal at
`PROVENANCE_V3_PACKET_TREE_SHA256`; every packet file is mode `0444`, every directory
is mode `0555`, and there is no symlink, special file or writable member. The manifest
is now bound by its exact size and SHA-256 as §18.25 required. Its self-exclusion remains
unchanged: the manifest does not hash itself, and the later independent disposition
must bind the manifest and each packet-file hash without entering or mutating the
packet leaf.

The execution consumed exactly the authorized two additional complete content passes
and bounded evidence selection: `7,106,471,781 + 4,537,493,452 = 11,643,965,233`
runtime bytes and five cumulative passes. It retained exactly one §18.27 projection,
the hash-bound `base64` component at `components/0` with
`raw_version_state="absent"`; all 65 closed negative controls passed. Network requests,
external bytes and retained-source reads were all zero. The unchanged ownership ledger
independently reconstructs runtime tree SHA-256
`74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b`.

#### 18.28.2 Exact unresolved classification

The packet contains exactly 98,608 blocking `OPEN` rows:

| Subject and field family | Reason | Count |
|---|---|---:|
| Every one of 30,421 runtime files: `origin_kind`, `origin_id`, `origin_member_path` | `missing-origin` | 91,263 |
| Every one of 1,221 components: `binary_artifact_ids` | `missing-binary` | 1,221 |
| Every one of 1,221 components: `source_artifact_ids` | `missing-source` | 1,221 |
| Every one of 1,221 components: `transformation_ids` | `missing-recipe` | 1,221 |
| Every one of 1,221 components: `selected_license_expression` | `license-choice` | 1,221 |
| Every one of 1,221 components: `license_notice_ids` | `missing-license` | 1,221 |
| Every one of 1,221 components: `source_delivery_id` | `source-obligation` | 1,221 |
| Eighteen runtime files: `component_id` | `multiple-owners` | 18 |
| One runtime file: `component_id` | `missing-owner` | 1 |

These rows are not failures to hide or a checklist that an implementer may clear by
inference. They prove that offline installed-byte inspection alone cannot establish
source authority, artifact lineage, build recipes or redistribution obligations. A
reviewer may confirm structural correctness while retaining provenance and licensing
`PAUSE`; no disposition may call this packet complete, build-eligible or publishable.

#### 18.28.3 Independent review and successor boundary

Kiro first reviews this exact result-binding plan for design/scope and verifies that it
names the immutable packet rather than blessing its contents. Only a later Ryan grant
may authorize an independent provenance/licensing reviewer, separate from the
collector, to inspect the exact durable packet and atomically create only
`PROVENANCE_DURABLE_REVIEW_ROOT/review-disposition.json`. The reviewer must recompute
the manifest and every packet-file hash, retain all open unresolved IDs, test the
§18.25/§18.27 negative controls independently, inspect the captured objects for
credential/private-data and licensing concerns, and return only the schema's exact
technical/provenance/licensing `PASS` or `PAUSE` values. The reviewer cannot edit,
repair, supplement or reinterpret the packet.

Because the unresolved ledger is nonempty, this packet cannot satisfy build
eligibility regardless of a structural technical finding. After the disposition, any
attempt to resolve provenance requires another plan-only packet that names exact HTTPS
or immutable-VCS origins, retained-local roots, methods, redirects, parsers, byte
ceilings, credentials prohibition and checkpoints component by component. Search
results, ambient caches, rolling-host ownership, guessed URLs and `latest` remain
non-authoritative. No acquisition permission is implied here.

#### 18.28.4 Authority boundary

This correction authorizes only four planning-document edits and exact-tip review. It
does not authorize creation of the review root or disposition, any network or retained-
source access, provenance acquisition, packet repair/replacement, another collector
execution, runtime read or mutation, build, install, test execution, tag/release/asset,
CI admission, product/test/CI/configuration/R2b change, PR `#342` update, merge,
deployment, real OpenClaw, live data, watch activation, promotion or Gates
D/W/D-V/E/F. Kiro PASS is not reviewer-write, acquisition, build, publication or
implementation authority.

### 18.29 Independent disposition and pre-acquisition replacement contract

Section 18.28 records the historical state before independent review: at that
checkpoint the review root was absent and reviewer creation was unauthorized. Kiro
passed that exact result binding, Ryan separately authorized Claude as the independent
provenance/licensing reviewer, and Codex independently verified the sole disposition
write. The immutable packet itself did not change. This successor freezes the review
result and defines only the closed planning contract required before any provenance
request or clean replacement build may be proposed.

#### 18.29.1 Frozen review result and continuing PAUSE

The following identities and verdicts are one indivisible current-state binding:

```text
P0_RESULT_BINDING_SEMANTIC_PARENT_SHA=9ecb10c3bb1b17b6190951037338f46d1f8e076b
P0_RESULT_BINDING_REVIEWED_OVERLAY_SHA=3b3550c85f8c0482353dac55998d7b6f0fcbbbb0
PROVENANCE_V3_PACKET_TREE_SHA256=491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5
PROVENANCE_V3_MANIFEST_SHA256=6791d33a82bd0f1e3fdbda072ae50aa296953b6a365194564090085541784fa4
PROVENANCE_V3_REVIEW_DISPOSITION_SHA256=45442e93958e7f0c4a2e4bf474d0b7430653fc0320ab1bad1b8222501b830669
PROVENANCE_V3_REVIEW_DISPOSITION_SIZE=8383806
PROVENANCE_V3_REVIEWED_AT_UTC=2026-09-27T21:34:24Z
PROVENANCE_V3_TECHNICAL_VERDICT=PASS
PROVENANCE_V3_PROVENANCE_VERDICT=PAUSE
PROVENANCE_V3_LICENSING_VERDICT=PAUSE
PROVENANCE_V3_HUMAN_COUNSEL_REQUIRED=true
PROVENANCE_V3_OPEN_UNRESOLVED_COUNT=98608
PROVENANCE_V3_BUILD_ELIGIBLE=false
PROVENANCE_V3_PUBLICATION_ELIGIBLE=false
```

The review directory is mode `0555` and contains only canonical mode-`0444`
`review-disposition.json`. Its 98,608 sorted unique `open_unresolved_ids` equal the
packet's complete ordered unresolved-ID set, and its twelve reviewed file bindings
equal the manifest plus every manifest-listed packet file. Technical `PASS` means the
packet is structurally exact; it is not runtime-relocation, provenance, licensing,
build, publication or CI-admission PASS. Provenance and licensing remain `PAUSE`, and
legal selections or reciprocal-source obligations remain human-counsel decisions.
The original packet, disposition and exhausted read ledger are immutable inputs; none
of their rows closes in place.

#### 18.29.2 Deterministic lossless planning coverage

The packet contains no authority observations, binary-artifact rows, source-artifact
rows, transformation rows, license-notice rows or source-delivery rows. This section
therefore cannot name 1,221 authoritative origins honestly. It defines the coverage
algorithm and information required to prepare later exact operation packets while
leaving unsupported authority fields unresolved.

The baseline sets are fixed by the packet manifest:

| Set | Count | Manifest primary-key SHA-256 |
|---|---:|---|
| Components | 1,221 | `b6b73ee112f898acf91c37ac0ad4e704ddd0fe131d3bcc5599c62d81bcf12146` |
| Runtime file paths | 30,421 | `432a960cd59db58b5c0345ff5179f71fb3aa7bb7a8780b3b5d2a072f390fb7aa` |
| Nested-component edges | 1,384 | `2c144bbd5a6d5e0a477a841847c5d9700de60c8a9488c546d09b13c138a3b580` |
| Open unresolved IDs | 98,608 | `2f207467c9e9308eda47a0dd762e361d687c7f6d614a46a810b8a43fc4554838` |

Planning sorts the exact component IDs by raw UTF-8 bytes and partitions consecutive
groups of 64: exactly twenty component batches, with five components in the final
batch. It independently sorts the exact unresolved IDs by raw UTF-8 bytes and creates
consecutive 2,048-ID verification pages: exactly 49 pages, with 304 IDs in the final
page. Pages prove coverage; they do not create authority or define operation budgets.
The observed ecosystem totals—1,031 Rust, 124 Python, 58 system, seven
`other-reviewed`, and one Node component—are cross-checks only, never authority
classes or completeness substitutes.

Each component unresolved row belongs to its exact component. Each file unresolved
row may be assigned through only the frozen non-null `file-ownership.jsonl`
`component_id`. The 18 multiply-owned files and one unowned file form one explicit
19-file ownership-dispute queue containing all four unresolved fields for each file;
planning never selects an owner to simplify batching. All 1,384 nested-component
edges remain dependencies. Reusing one upstream acquisition across components neither
merges component identities nor removes nested licensing or source-delivery duties.

Every future planning artifact must prove pairwise-disjoint primary assignments and
exact union equality to all four baseline sets and independently recompute the
manifest counts and primary-key hashes. An omission, duplicate, reassignment, new
subject, changed parent identity, altered nested edge or ownership guess is `PAUSE`.
Batching cannot multiply an operation packet's aggregate request, retry, content,
decoded or expanded-byte ceiling.

#### 18.29.3 Candidate records are not acquisition authority

Each component or ownership work item must state at least:

- `baseline_component_id`, exact covered unresolved IDs or an independently enumerable
  set plus count/hash, affected runtime paths and nested dependencies;
- exact evidence object IDs and member, JSON-pointer or byte-range citations;
- candidate origin, candidate state, remaining authority gap and required proof; and
- proposed operation, checkpoint and failure disposition.

The planning-only candidate states are `UNRESOLVED`, `CANDIDATE_ONLY` and
`READY_FOR_REVIEW`; they do not extend schema-v3 enums and never close a packet row.
A package name, PURL, familiar registry convention, installed metadata URL, SBOM URL,
search result, guessed path, ambient cache, current-host ownership or `latest` may
support a cited candidate but cannot establish artifact authority. Ryan may nominate
an exact candidate for later review, but nomination authorizes neither access nor a
provenance conclusion. If immutable source or binary identity is absent from currently
authorized evidence, the item stays unresolved. A metadata-resolution request is
itself acquisition; a newly discovered origin or redirect stops the operation and
requires a successor plan.

A later operation may reach `READY_FOR_REVIEW` only when it names an exact HTTPS URL,
immutable VCS remote and object, or exact authorized retained-local root and paths,
plus all of:

- allowed method and ordered permitted redirects;
- request, retry and wall-clock ceilings;
- compressed, decoded and expanded-byte ceilings plus archive member/depth limits;
- pinned parser/tool identity and data-only behavior with no acquired-byte execution;
- checksum, signature, VCS-object or equivalent identity verification;
- expected packet roles and fresh staging/durable coordinates;
- credential prohibition, responsible actor, checkpoints and fail-closed disposition.

No such origin or operation is granted by this correction. A complete cited planning
artifact, Kiro exact-tip review and a new Ryan operation-specific grant are required
before one network request, VCS fetch or retained-source read.

#### 18.29.4 Host-path evidence and clean-replacement rule

The independent reviewer found three packet-owned ELF objects containing rejected-host
paths. Codex reproduced the evidence without reading the original runtime:

| Runtime path | Packet object / component | Exact evidence |
|---|---|---|
| `lib/libtcl8.6.so` | `obj_sha256:a69a8d60eb3240f152a22f42f99e3bbd15ba60dc9d232615709406511d057d9b` / `cmp_sha256:01ade610ab72de8c23aa63afe15e12d6cdbd00aeb76d5c326e61557af9e43367` | eight `/home/lauer/miniforge3` occurrences at byte offsets 61547, 1564224, 1564488, 1564752, 1565024, 1565288, 1835457 and 1835936; ELF `DT_RPATH=/home/lauer/miniforge3/lib:/home/conda/feedstock_root/build_artifacts/tk_1769459871528/_build_env/lib` |
| `lib/libtk8.6.so` | `obj_sha256:3aef1cd676469b0e6d0402d3db3d74b9a64d25b3988adf069f8eae112a3dde0c` / `cmp_sha256:0aadfc99d8d94d11d49bbfb88d3752461e320a35f7f369bdf656baff3b795b7a` | one occurrence at byte offset 39637 and the same absolute ELF `DT_RPATH` |
| `lib/libtinfow.so.6` | `obj_sha256:60ecdf843974955b99a8b0e63d2167915ca046c88e01a7c0245a1fa3a380c8d8` / `cmp_sha256:bc9d05dedaedcfa6a8db1a50a1138dc51f269e74c45242e68b765d20ff489768` | `/home/lauer/miniforge3/share/terminfo` at byte offset 225640; ELF `DT_RPATH=$ORIGIN/.` |

These bytes disclose a local account path and prove ambient-host relocation. The Tcl
and Tk loader paths are also loader-search hazards. They do not prove that a host
escape occurred, and the packet's technical schema PASS must never be relabeled as
runtime-relocation PASS.

The only admissible remediation is a fresh replacement from independently locked
source, artifacts, configuration, patches, recipes and toolchains. The reviewed
recipe must prevent host/build-prefix embedding before construction. Copying the
rejected binaries, rolling-host substitution, post-build ELF or string rewriting,
`patchelf`, `chrpath`, binary prefix replacement, or any edit to the rejected runtime,
packet or disposition is forbidden. The existing `conda-prefix-relocation` enum is
not blanket repair authority. Removing Tcl, Tk or another component is a separate
reviewed minimization decision requiring complete loader/import/data closure; the
path finding alone grants no removal. Parent-governed CPython, Unicode, Node and
qualified-workload behavior remains unchanged.

Future qualification must scan the complete delivery set for host/build prefixes in
ELF loader paths, debug and printable strings, generated configuration, Tcl package or
data paths and terminfo lookup. It must inspect loader semantics and run with the
rejected host paths unavailable. Two builds from distinct disposable prefixes must
show that host-dependent paths do not influence distributable bytes. It must also
reject out-of-tree or traversing `$ORIGIN`, inherited loader/Tcl/terminfo fallback,
synthetic external libraries or data that make tests pass, omitted transitive
dependencies, and runtime PASS with failed provenance, privacy or compliance closure.
Any allowed absolute path requires one exact reviewed purpose and containment; there
is no blanket `/usr`, environment or “debug-only” exception.

#### 18.29.5 Closed sequence and authority boundary

The only admissible successor sequence is:

1. Kiro reviews this exact pre-acquisition planning contract.
2. A separately reviewed planning artifact supplies complete cited candidate coverage
   and preserves every unsupported item as unresolved.
3. A separate exact metadata/acquisition operation packet and Ryan grant name the
   precise origins, operations, ceilings, parsers, fresh roots and stop conditions.
4. Codex performs only that bounded collection; an independent reviewer and human
   counsel evaluate the resulting immutable bytes.
5. Only a fresh successor lock with zero unresolved rows and independent technical,
   provenance and licensing PASS may become build-eligible.
6. A separately reviewed recipe/build packet and Ryan grant may then authorize one
   clean construction, full host-path negative controls and qualification.
7. The actual three-role delivery set receives independent technical and licensing
   review before any separately authorized publication, CI admission or corrective
   implementation.

New evidence roles, closure rules or semantic schema fields require a new schema
version and fresh coordinates. Counsel questions cannot be discharged by model-
generated legal rationale. The rejected runtime, schema-v1/v2 staging, schema-v3
packet, disposition and PR `#342` remain immutable and unchanged.

**Authority boundary.** This correction authorizes only the four named planning-
document edits and exact-tip design review. It authorizes no network request,
retained-source inspection, acquisition, collector or evidence execution, packet/
disposition mutation, binary repair, runtime construction, publication, CI admission,
implementation, PR update, merge, live OpenClaw use or later gate. Planning PASS is
not execution authority.

### 18.30 Complete component and ownership work-item contract

Section 18.29 proves that the schema-v3 packet can be covered losslessly without
inventing an origin or owner. This successor freezes the one canonical planning model
that a later, separately granted offline authoring step must instantiate. It does not
read the packet, create a work-item bundle, resolve an ownership dispute, select a
license, or authorize an origin operation.

#### 18.30.1 Frozen inputs, proposed coordinates and status

The work-item design is bound to current main after the descriptive merge snapshot and
to the immutable packet/disposition pair:

```text
COMPONENT_OWNERSHIP_WORK_ITEM_PLAN_BASE_SHA=a986fce7e7c59ebbbe81a079a7e90c6bdaa816fb
PROVENANCE_V3_PACKET_TREE_SHA256=491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5
PROVENANCE_V3_REVIEW_DISPOSITION_SHA256=45442e93958e7f0c4a2e4bf474d0b7430653fc0320ab1bad1b8222501b830669
PROVENANCE_WORK_ITEM_SCHEMA=convmem.switchboard.provenance-work-items.v1
PROVENANCE_COMPONENT_WORK_ITEM_COUNT=1221
PROVENANCE_OWNERSHIP_DISPUTE_WORK_ITEM_COUNT=19
PROVENANCE_TOTAL_WORK_ITEM_COUNT=1240
PROVENANCE_COMPONENT_UNRESOLVED_COUNT=7326
PROVENANCE_OWNED_FILE_ORIGIN_UNRESOLVED_COUNT=91206
PROVENANCE_DISPUTED_FILE_UNRESOLVED_COUNT=76
PROVENANCE_WORK_ITEM_UNRESOLVED_COUNT=98608
PROVENANCE_WORK_ITEM_PACKET_FILE_COUNT=7
PROVENANCE_WORK_ITEM_NEGATIVE_CONTROL_COUNT=40
PROVENANCE_WORK_ITEM_PACKET_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHORING_AUTHORIZED=false
PROVENANCE_ACQUISITION_EXECUTION_AUTHORIZED=false
PROPOSED_WORK_ITEM_STAGING_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/a986fce7e7c59ebbbe81a079a7e90c6bdaa816fb/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v1
PROPOSED_WORK_ITEM_DURABLE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/a986fce7e7c59ebbbe81a079a7e90c6bdaa816fb/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v1
```

The proposed roots are single-assignment coordinates for a future grant; this plan
does not create them. If either root exists before that grant, authoring is `PAUSE`.
The schema-v3 packet and review roots remain immutable inputs and are never nested
under, copied into, hard-linked into, or modified by the work-item roots.

#### 18.30.2 One canonical work-item packet, not three authorities

A future offline authoring run may create exactly seven canonical files under one
immutable packet leaf:

| File | Primary key / purpose |
|---|---|
| `component-work-items.jsonl` | `work_item_id`; exactly 1,221 component records |
| `ownership-dispute-work-items.jsonl` | `work_item_id`; exactly 19 path records |
| `component-batches.jsonl` | `batch_id`; the exact twenty scheduling projections |
| `unresolved-pages.jsonl` | `page_id`; the exact 49 verification projections |
| `coverage.json` | one closed arithmetic and set-identity summary |
| `negative-controls.jsonl` | `control_id`; the closed fail-closed mutant corpus |
| `manifest.json` | hashes, sizes, modes, record counts and primary-key hashes for the preceding six files; never self-hashes |

All JSON uses the canonical §18.25 UTF-8/LF/sorted-key/no-float/no-duplicate-key
rules. JSONL records are sorted by raw UTF-8 primary-key bytes. Files are mode `0444`,
directories mode `0555`, and no symlink, special file, writable file, path escape,
hard link, credential or acquired byte is eligible. The staging leaf is written under
a same-filesystem partial name, verified, made read-only, and atomically renamed; the
durable leaf is a byte-and-mode-identical single assignment. A mode-`0400` authoring
result outside the packet binds the manifest and complete packet-tree identity.

Planning batches and verification pages are derived views only:

- `batch-00` through `batch-19` partition the 1,221 component work-item IDs in
  raw-component-ID order, 64 per batch except five in `batch-19`;
- `page-00` through `page-48` partition the 98,608 unresolved IDs in raw-ID order,
  2,048 per page except 304 in `page-48`; and
- the 19 ownership-dispute work items are ordered independently by raw path bytes.

A batch never owns a component, a page never owns an unresolved row, and neither view
may change work-item state, supply an origin, multiply a later operation budget, or
serve as a completeness substitute. `component-work-items.jsonl` and
`ownership-dispute-work-items.jsonl` are the sole primary-assignment surfaces;
`coverage.json` must prove their disjoint union and the two derived projections.

#### 18.30.3 Component work-item identity and exact assignments

Each component record is closed-schema and binds at least:

- the packet-tree identity, schema, `work_item_kind="component"`, exact
  `baseline_component_id`, and a content-addressed `work_item_id` derived from those
  identity fields only;
- the component primary-row citation and its canonical record hash; this v1 wording
  historically used `components.jsonl`, but §18.31 corrects the executable successor
  to the governed §18.25.2 role `component-lock.jsonl` with no alias or fallback;
- exactly the six component-level unresolved IDs for `binary_artifact_ids`,
  `source_artifact_ids`, `transformation_ids`, `selected_license_expression`,
  `license_notice_ids`, and `source_delivery_id`;
- every uniquely owned runtime path whose frozen non-null
  `file-ownership.jsonl.component_id` equals the component, plus exactly the three
  `missing-origin` unresolved IDs for each such path;
- every `nested-components.jsonl` edge for which the component is
  `container_component_id`, assigned exactly once by the edge's frozen
  `container_component_id,nested_component_id,relationship` primary key, and a
  derived inbound-reference list for edges where it is `nested_component_id` that
  never counts as primary edge coverage;
- all exact evidence-object/member/JSON-pointer or byte-range citations supporting
  any candidate, with each citation bound to its packet file, primary key, canonical
  record hash and evidence-object identity;
- zero or more cited candidate records, the remaining authority gaps, required
  proofs, proposed operation or explicit null, fail-closed checkpoint, and planning
  state; and
- the exact §18.29.4 host-path finding when the work item covers
  `lib/libtcl8.6.so`, `lib/libtk8.6.so`, or `lib/libtinfow.so.6`, with
  `clean_replacement_required=true` and no repair route.

The component arithmetic is exact: `1,221 * 6 = 7,326` component-level rows and
`30,402 * 3 = 91,206` uniquely owned-file origin rows. A uniquely owned path and all
three of its origin rows stay together in its component work item. Moving one field to
another component, splitting one path across items, or using a nested edge to merge two
component identities is `PAUSE`.

Work-item identity is exact. Let `subject_id` be the raw baseline component ID for a
component record and the raw runtime path for a dispute record. Canonically encode the
closed object
`{"packet_tree_sha256":PROVENANCE_V3_PACKET_TREE_SHA256,"schema":PROVENANCE_WORK_ITEM_SCHEMA,"subject_id":subject_id,"work_item_kind":kind}`
under §18.25 and set `work_item_id` to `work_item:sha256:` plus the lowercase SHA-256
of those bytes. No path, Unicode, case, URL or PURL normalization occurs. The manifest
separately hashes each complete record, so the stable subject identity is never
misrepresented as a full-record content hash.

#### 18.30.4 Ownership-dispute work items remain unowned

Each of the eighteen `multiple-owners` paths and the one `missing-owner` path has one
closed-schema dispute record. It binds the exact path, file row/evidence citations,
the three `missing-origin` unresolved IDs, the one owner unresolved ID, and every
packet-supported candidate component without selecting among them. Thus the queue
covers `19 * 4 = 76` unresolved IDs. Candidate-owner sets are evidence leads only;
an empty set remains honest for the unowned path, and a multi-member set remains
ambiguous for a multiply-owned path.

No disputed path or any of its four unresolved rows may appear in a component work
item until a later immutable acquisition proves one exact artifact-member ownership
and an independently reviewed successor lock records it. Filename similarity, package
layout, import behavior, current-host package ownership, nearest directory, SBOM
membership, common packaging practice or model judgment cannot choose an owner.

The complete unresolved arithmetic must remain:

```text
7,326 component rows
+ 91,206 uniquely owned-file origin rows
+ 76 disputed-file rows
= 98,608 open unresolved rows
```

Every unresolved ID appears in exactly one primary work item and exactly one
verification page. The work-item bundle never edits or closes the immutable packet's
row; it only binds a planning assignment back to that open row.

#### 18.30.5 Candidate citations and states do not create authority

The only planning states remain `UNRESOLVED`, `CANDIDATE_ONLY`, and
`READY_FOR_REVIEW`. They are local work-item schema values, not schema-v3 verdicts.
State is derived fail-closed:

- `UNRESOLVED`: no packet-cited candidate satisfies the record's minimum structural
  fields;
- `CANDIDATE_ONLY`: one or more packet-cited leads exist, but origin authority,
  immutable identity, operation details, or required proof remains incomplete; and
- `READY_FOR_REVIEW`: the record names a proposed exact HTTPS URL, immutable VCS
  remote/object, or exact retained-local root/path plus every §18.29.3 method,
  redirect, parser, identity, ceiling, checkpoint, output-role and credential-
  prohibition field. It is ready to review, not ready to access.

Candidate records are byte-preserving projections of already authorized packet
evidence. Each has a content-addressed candidate ID, exact citation set, candidate
kind/value bytes, stated gaps and no inferred normalization. Names, PURLs, installed
metadata, SBOM external references, familiar registries, search results, guessed
paths, ambient caches, current-host state, redirects and `latest` are never authority.
No network lookup, retained-source inspection, URL probing, DNS resolution, package-
manager query or metadata refresh may be used to improve a state under this plan.

License-choice, notice and source-delivery rows remain open even when packet metadata
contains a license string. Work items may preserve exact candidate expressions and
questions for counsel, but may not choose an `OR` branch, interpret an exception,
declare compatibility, or discharge reciprocal-source obligations. Human counsel is
still required.

Citation and candidate identities are also exact. A citation ID is `citation:sha256:`
plus the SHA-256 of the canonical closed object containing packet-tree SHA-256, packet
file role, raw primary-key value, canonical record SHA-256, evidence-object ID and raw
internal locator. A candidate ID is `candidate:sha256:` plus the SHA-256 of the
canonical closed object containing `candidate_kind`, the exact candidate value bytes
represented as a JSON string, and the sorted raw citation-ID array. Any different
byte, citation order after canonical sorting, locator or candidate kind produces a
different ID; aliases never converge by normalization.

#### 18.30.6 Successor operation packets and grouping boundary

After an independently reviewed work-item packet exists, a later plan may propose
operations only by exact `work_item_id` and unresolved-ID set. An operation may group
items only when they name byte-identical origin coordinates, methods, ordered
redirects, parser/tool identity, verification rule, output roles and stop conditions.
Grouping retains every per-item citation and obligation; it never merges components,
licenses or ownership decisions. Aggregate request, retry, time, compressed, decoded
and expanded-byte ceilings apply to the whole operation, not once per batch, page,
component or redirect.

Discovery of a new origin, redirect, mirror, VCS object, archive member, credential
need, executable parser path or larger ceiling stops the operation. A successor plan,
Kiro exact-tip review and Ryan's operation-specific grant are mandatory before any
HTTP request, VCS fetch or retained-source read. Acquired bytes remain evidence, not
build inputs, until a zero-unresolved successor lock and independent technical,
provenance and licensing PASS.

#### 18.30.7 Negative controls, review sequence and authority boundary

The future authoring verifier must run exactly forty single-mutant controls, each of
which must return `PAUSE` without a final packet:

| IDs | Mutations |
|---|---|
| `W001`–`W004` | packet-tree mismatch; disposition mismatch; preexisting staging root; preexisting durable root |
| `W005`–`W010` | missing role; extra role; manifest self-hash; noncanonical JSON; noncanonical JSONL order; wrong file type/mode or forbidden symlink/hard-link/path escape |
| `W011`–`W013` | wrong work-item ID; wrong citation/candidate ID; wrong count or primary-key hash |
| `W014`–`W017` | missing component item; duplicate component item; missing dispute item; duplicate dispute item |
| `W018`–`W024` | missing unresolved ID; duplicate unresolved ID; missing runtime path; duplicate runtime path; split uniquely owned path; disputed path in a component item; guessed dispute owner |
| `W025`–`W028` | missing nested edge; duplicate nested edge; non-container primary assignment; inbound reference counted as primary coverage |
| `W029`–`W031` | component-batch partition drift; unresolved-page partition drift; projection membership used to own/promote a record |
| `W032`–`W036` | candidate without exact citation; normalized/looked-up candidate; `READY_FOR_REVIEW` with a missing operation field; immutable packet row marked closed; owner or license choice asserted |
| `W037`–`W040` | host-path repair/removal route; per-batch/page/component ceiling multiplication; acquired/external byte in the packet; credential/private-data byte in the packet |

The unmutated baseline must return zero violations. A control that does not reject, a
41st semantic exception, a combined mutant that obscures which invariant fired, or an
authoring implementation that rewrites output after a failure is `PAUSE` and requires
a successor plan.

The only admissible next sequence is:

1. Kiro reviews this exact architecture/execution parent and milestone overlay.
2. Ryan may separately authorize one offline authoring run from the immutable packet
   and disposition into the exact absent roots, with a frozen author identity and
   bounded packet reads; no network or retained-source access is part of that grant.
3. An independent reviewer verifies all seven files, the packet/result identities,
   the `1,240`-item and `98,608`-ID unions, all 1,384 edge assignments, candidate
   citations and negative controls without repairing the bundle.
4. Only after that review may a successor origin-by-origin operation plan be authored.
5. Every actual acquisition, counsel disposition, successor lock, clean build,
   qualification, publication, CI admission and product correction remains a later
   separately reviewed and Ryan-granted stage.

**Authority boundary.** This section authorizes only edits to the four Switchboard
planning documents and exact-tip design review. It creates no work-item root, packet,
result, candidate record or evidence. It authorizes no packet/runtime read or
mutation, network request, retained-source inspection, metadata resolution,
acquisition, owner or license selection, binary repair, build, publication, CI
admission, implementation, PR `#342` update, merge, deployment, real OpenClaw, live
data, watch activation, promotion or Gate D/W/D-V/E/F action. Planning PASS is not
offline-authoring or operation authority.

### 18.31 Closed work-item schema-v2 correction

Section 18.30 remains the reviewed, uninstantiated v1 planning contract. The first
offline-author-freeze preflight stopped before any packet or disposition read because
v1 said records bound "at least" a set of fields and did not close the seven file
schemas, nested citation/candidate grammars, result identity, packet-tree algorithm or
negative-control receipts. No v1 root exists and no v1 byte may be created, repaired,
reused or reinterpreted. This successor changes only that work-item planning schema;
it does not change provenance schema v3, packet tree `491ae60b...`, its manifest,
review disposition or exhausted read ledger.

#### 18.31.1 Version, roots and canonical primitives

```text
PROVENANCE_WORK_ITEM_SCHEMA=convmem.switchboard.provenance-work-items.v2
PROVENANCE_WORK_ITEM_SCHEMA_PLAN_BASE_SHA=49130975a776864f9ba4bdf7347146fc07a2f95c
PROVENANCE_WORK_ITEM_PACKET_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_AUTHORIZED=false
PROVENANCE_WORK_ITEM_AUTHORING_AUTHORIZED=false
PROVENANCE_ACQUISITION_EXECUTION_AUTHORIZED=false
PROPOSED_WORK_ITEM_STAGING_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/49130975a776864f9ba4bdf7347146fc07a2f95c/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v2
PROPOSED_WORK_ITEM_DURABLE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/49130975a776864f9ba4bdf7347146fc07a2f95c/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v2
```

Both roots and their `.partial` siblings are single-assignment. Successful roots are
mode `0555` and contain exactly `packet/` mode `0555` plus external
`authoring-result.json` mode `0400`; `packet/` contains exactly the seven mode-`0444`
roles in §18.31.4. No review leaf exists at this phase. Pre-existence, a symlinked
ancestor, interruption, mismatch or unrepresentable field is `PAUSE`; preserve any
partial root and do not retry, patch, delete or publish a result.

Let `J(x)` be §18.25 canonical compact JSON encoded as UTF-8 with sorted keys and no
line feed; a JSON file is `J(x)||LF`, and each JSONL row is `J(x)||LF`. `H(b)` is the
lowercase SHA-256 of bytes `b`; a row hash is `H(J(row))`. A primary-key set hash is
`H(concat(UTF8(key)||NUL))` over unique raw-UTF-8 keys sorted bytewise; the empty set
hashes the empty byte string. All set-valued string arrays are unique and sorted by
raw UTF-8 bytes. Unknown or omitted keys, floats, duplicate keys, arbitrary extension
objects, free-form rationale, and `null` outside the cases explicitly named below are
rejected.

`work_item_id` is `work_item:sha256:` plus `H(J({"packet_tree_sha256":
PROVENANCE_V3_PACKET_TREE_SHA256,"schema":PROVENANCE_WORK_ITEM_SCHEMA,
"subject_id":subject_id,"work_item_kind":kind}))`; `subject_id` is the raw baseline
component ID or raw disputed runtime path. A citation ID is `citation:sha256:` plus
the hash of the canonical object containing `packet_tree_sha256`, `packet_file_role`,
raw `primary_key`, canonical `record_sha256`, `evidence_object_id` and `locator`. A
candidate ID is `candidate:sha256:` plus the hash of the canonical object containing
`candidate_kind`, exact `candidate_value` and the sorted unique `citation_ids`.
There is no case, path, Unicode, URL, PURL, percent or alias normalization.

The governed component role is exclusively `component-lock.jsonl`, as §18.25.2
defines. Section 18.30.3's `components.jsonl` spelling was an inconsistent planning
reference, not a rename or alias. No autodetection or fallback is permitted; absence
of `component-lock.jsonl` in a later separately authorized read is `PAUSE`.

#### 18.31.2 Closed supporting objects

A **citation** has exactly `citation_id`, `packet_tree_sha256`, `packet_file_role`,
`primary_key`, `record_sha256`, `evidence_object_id` (string or explicit `null`) and
`locator`. Admitted packet roles are only `component-lock.jsonl`,
`file-ownership.jsonl`, `nested-components.jsonl`, `unresolved.jsonl` and
`objects.jsonl`. Locator is exactly one of:

- `{"kind":"record-json-pointer","pointer":string}`;
- `{"kind":"object-json-pointer","pointer":string}`;
- `{"kind":"object-byte-range","offset":nonnegative-integer,"length":positive-integer}`; or
- `{"kind":"object-member-json-pointer","member_path":string,"pointer":string}`.

The initial author may emit only `record-json-pointer` and, for the three frozen
host-path findings, `object-byte-range`. A **gap** has exactly `unresolved_id`,
`citation_id`, `field`, `reason_code`, `required_evidence`, `status="OPEN"` and
`blocks=true`. A **candidate** has exactly `candidate_id`, `candidate_kind`,
`candidate_value`, `citation_ids`, `gap_unresolved_ids` and
`authority_status="CANDIDATE_ONLY"`. Initial candidate kinds are only
`component-name`, `component-version`, `component-build`, `component-purl`,
`component-origin-namespace` and `owner-component-id`; build/PURL candidates are
omitted when their source fields are null. There is no URL, registry, source or
license inference.

A candidate owner has exactly `component_id`, `candidate_id` and `citation_ids`.
Owner candidates are extracted only from exact `cmp_sha256:[0-9a-f]{64}` tokens,
with token boundaries, in that disputed path's own owner-unresolved
`required_evidence`; every token must resolve to the frozen component set. An owned
path has exactly `path`, `mode`, `size`, `sha256`, `owner_component_id`,
`file_citation_id` and `origin_gaps`; `origin_gaps` contains exactly the
`origin_kind`, `origin_id` and `origin_member_path` gaps for that path. A nested edge
has exactly `edge_key`, `container_component_id`, `nested_component_id`,
`relationship`, `evidence_object_id`, `evidence_path` and `citation_id`; `edge_key`
is the NUL-joined frozen primary key. A host finding has exactly `runtime_path`,
`evidence_object_id`, `needle`, sorted unique `offsets`,
`reported_dynamic_tag="DT_RPATH"`, `reported_dynamic_value`, `citation_ids`,
`finding_source="ARCHITECTURE_18_29_4"`, `clean_replacement_required=true` and
`remediation="CLEAN_REPLACEMENT_ONLY"`. Exactly the three §18.29.4 findings exist.

Initial `proposed_operation` is always explicit `null`. `READY_FOR_REVIEW` remains
reserved vocabulary but is rejected in this initial packet; state is `UNRESOLVED`
when `candidates` is empty and `CANDIDATE_ONLY` otherwise.

#### 18.31.2a Closed scalar, container and ordering map

Section 18.25.1's canonical scalar grammar is inherited without widening: hashes are
lowercase 64-hex strings, sizes/counts/ordinals/offsets/lengths are nonnegative JSON
integers (length is positive), modes are four-character octal strings, booleans are
JSON booleans, and paths/IDs/enum values are strings with no implicit coercion.
`schema` is always the exact v2 schema unless a different exact fixture/result schema
is named. `packet_tree_sha256`, `input_packet_tree_sha256` and
`disposition_sha256`/`input_disposition_sha256` are raw hashes, not prefixed IDs.
Work-item, citation, component, object and unresolved IDs must match their governed
prefix plus lowercase 64-hex grammar. Every copied scalar retains the exact source
JSON type and value; no stringify/parse conversion is permitted.

The nested container types and orderings are closed:

| Field | Exact JSON type and order |
|---|---|
| `component_gaps`, `origin_gaps` | arrays of gap objects, unique and sorted by `unresolved_id` |
| `owned_paths` | array of owned-path objects, unique and sorted by raw `path` |
| `primary_nested_edges` | array of nested-edge objects, unique and sorted by raw `edge_key` |
| `inbound_edge_keys`, `unresolved_ids`, `citation_ids`, `gap_unresolved_ids` | sorted unique string arrays |
| `citations` | array of citation objects, unique and sorted by `citation_id` |
| `candidates` | array of candidate objects, unique and sorted by `candidate_id` |
| `candidate_owners` | array of candidate-owner objects, unique and sorted by `component_id,candidate_id` joined with NUL |
| `host_path_findings` | array of host-finding objects, unique and sorted by raw `runtime_path` |
| `offsets` | sorted unique arrays of nonnegative integers |
| `component_ids`, `work_item_ids` | arrays of strings; sorted unique except the batch's two arrays are parallel in raw component-ID order |
| `files` | array of manifest descriptors sorted by raw `path` |
| `records` | array of manifest record descriptors sorted by raw `primary_key` |
| output tree rows | array of exact `{path,mode,size,sha256}` objects sorted by raw `path` |

Within those objects, every citation field is a string except
`evidence_object_id`, which is a governed object-ID string or explicit null, and
`locator`, which is exactly one locator object from §18.31.2. Every gap field is a
string except `blocks`, which is boolean. Every candidate field is a string except
its two sorted string arrays. Every candidate-owner field is a string except its
sorted citation-ID array. An owned path uses string `path`, `mode`, `sha256`,
`owner_component_id` and `file_citation_id`, integer `size`, and an origin-gap array.
A nested edge uses only strings. A host finding uses strings except its integer array
`offsets`, sorted citation-ID array and boolean `clean_replacement_required`.

A component row's scalar fields `schema`, `packet_tree_sha256`,
`disposition_sha256`, `work_item_id`, `work_item_kind`, `baseline_component_id`,
`component_citation_id`, `planning_state`, `checkpoint` and `failure_disposition`
are strings; `clean_replacement_required` is boolean; `proposed_operation` is JSON
null; its remaining fields have exactly the array types above. A dispute row has
string scalars `schema`, both hashes, both IDs, `work_item_kind`, `runtime_path`,
`mode`, `sha256`, `file_citation_id`, `ownership_reason`, `planning_state`,
`checkpoint` and `failure_disposition`; `size` is integer; `owner_gap` is one gap
object; `selected_owner_component_id` and `proposed_operation` are JSON null; all
remaining fields use the array types above.

A batch/page row uses string `schema`, ID and authority/hash fields, integer
`ordinal` and count, and the declared string arrays. Every coverage summary is one
object with integer `count` and hash-string `primary_key_sha256`; coverage top-level
counts are integers and its three eligibility/authority fields are booleans. A
negative-control row uses strings for schema/IDs/hashes/verdicts/rejection codes and
booleans for the two created flags and `passed`. A manifest descriptor uses string
`path`, `mode`, `sha256`, hash-string `primary_key_sha256`, integer `size` and
`record_count`, plus the ordered record-descriptor array; a record descriptor contains
only string `primary_key` and hash-string `record_sha256`.

The result uses strings for schemas/SHAs/roots/path/verdicts, integers for sizes,
counts/read passes/read bytes/access counters, and booleans for authorization and
eligibility. `argv` is an ordered string array. `author.path` is a string,
`author.sha256` a hash string and `author.size` an integer; its interpreter has string
`path`, hash strings `sha256`/`dependency_manifest_sha256`, integer `size` and exact
string `version`. No result field is nullable or optional.

#### 18.31.3 Exact primary records

Each of the 1,221 rows in `component-work-items.jsonl` has exactly these keys:

```text
schema, packet_tree_sha256, disposition_sha256, work_item_id,
work_item_kind, baseline_component_id, component_citation_id,
component_gaps, owned_paths, primary_nested_edges, inbound_edge_keys, citations,
candidates, unresolved_ids, planning_state, proposed_operation, checkpoint,
failure_disposition, host_path_findings, clean_replacement_required
```

`work_item_kind` is `component`; `checkpoint` is
`SEPARATE_ORIGIN_OPERATION_PLAN_REVIEW_AND_RYAN_GRANT`; `failure_disposition` is
`PAUSE`. Each row has exactly six component gaps, every uniquely owned path and its
three origin gaps, every primary edge whose frozen container is the component, and
only derived inbound edge keys. Arrays are raw-key sorted and unique. The three
affected component rows carry the exact host finding; all others carry an empty list.

Each of the 19 rows in `ownership-dispute-work-items.jsonl` has exactly:

```text
schema, packet_tree_sha256, disposition_sha256, work_item_id,
work_item_kind, runtime_path, mode, size, sha256, file_citation_id,
ownership_reason, owner_gap, origin_gaps, candidate_owners, citations,
candidates, unresolved_ids, selected_owner_component_id, planning_state,
proposed_operation, checkpoint, failure_disposition
```

`work_item_kind` is `ownership-dispute`; `ownership_reason` is `multiple-owners`
for exactly eighteen rows and `missing-owner` for one; `selected_owner_component_id`
and `proposed_operation` are explicit `null`; each row has one owner gap, exactly
three origin gaps and the same checkpoint/failure values as a component row. No
disputed path occurs in a component item.

#### 18.31.4 Seven files, projections and coverage

The other five roles are closed as follows:

- `component-batches.jsonl`: twenty rows with exactly `schema`, `batch_id`,
  `ordinal`, `component_ids`, `work_item_ids`, `component_count`,
  `component_primary_key_sha256`, `membership_sha256`, `authority="NONE"`.
  IDs are `batch-00` through `batch-19`; counts are 64 except final 5; component and
  work-item arrays are parallel and membership hash covers their canonical pair array.
- `unresolved-pages.jsonl`: 49 rows with exactly `schema`, `page_id`, `ordinal`,
  `unresolved_ids`, `work_item_ids`, `unresolved_count`,
  `unresolved_primary_key_sha256`, `authority="NONE"`. IDs are `page-00` through
  `page-48`; counts are 2,048 except final 304; work IDs are sorted unique.
- `coverage.json`: exactly `schema`, `packet_tree_sha256`, `disposition_sha256`,
  `component_items`, `dispute_items`, `all_items`, `components`, `runtime_paths`,
  `owned_paths`, `disputed_paths`, `component_gap_ids`, `owned_origin_gap_ids`,
  `disputed_gap_ids`, `unresolved_ids`, `primary_nested_edges`,
  `component_batches`, `unresolved_pages`, `open_unresolved_count`,
  `closed_unresolved_count`, `acquisition_authorized`, `build_eligible` and
  `publication_eligible`. Each summary is exactly `{count,primary_key_sha256}`.
  Counts are respectively 1,221; 19; 1,240; 1,221; 30,421; 30,402; 19; 7,326;
  91,206; 76; 98,608; 1,384; 20; 49. The component/path/edge/unresolved set hashes
  remain `b6b73ee112f898acf91c37ac0ad4e704ddd0fe131d3bcc5599c62d81bcf12146`,
  `432a960cd59db58b5c0345ff5179f71fb3aa7bb7a8780b3b5d2a072f390fb7aa`,
  `2c144bbd5a6d5e0a477a841847c5d9700de60c8a9488c546d09b13c138a3b580` and
  `2f207467c9e9308eda47a0dd762e361d687c7f6d614a46a810b8a43fc4554838`.
  Closed count is zero and all three booleans are false.
- `negative-controls.jsonl`: exactly forty rows with keys `schema`, `control_id`,
  `fixture_schema`, `fixture_sha256`, `mutation_id`, `mutation_sha256`,
  `expected_verdict`, `observed_verdict`, `expected_rejection_code`,
  `observed_rejection_code`, `final_packet_created`, `result_created`, `passed`.
  Fixture schema is `convmem.switchboard.work-item-synthetic-fixture.v1`; verdicts
  are `PAUSE`; rejection codes equal `W001` through `W040`; both created flags are
  false and `passed=true`. Receipts contain no clock, PID, temp path or randomness.
- `manifest.json`: exactly `schema`, `plan_base_sha`, `input_packet_tree_sha256`,
  `input_disposition_sha256`, `files`. `files` contains the preceding six roles in
  raw filename order. Each descriptor is exactly `path`, `mode="0444"`, `size`,
  `sha256`, `record_count`, `primary_key_sha256`, `records`; each record entry is
  exactly `primary_key`, `record_sha256`. Coverage uses synthetic key `coverage`.
  The manifest never lists itself, the result, receipts or directories.

For all seven files, form sorted rows `{path,mode:"0444",size,sha256}` and set
`output_packet_tree_sha256=H(J(rows))`. Payload `packet_tree_sha256` always means the
immutable input schema-v3 tree, avoiding recursion; the manifest contains no output
tree field.

#### 18.31.5 External result and controls

`authoring-result.json` has exactly:

```text
schema, work_item_schema, plan_base_sha, author,
author_freeze_receipt_sha256, self_test_receipt_sha256,
input_packet_tree_sha256, input_disposition_sha256, input_manifest_sha256,
input_packet_bytes_read, input_disposition_bytes_read,
input_packet_read_passes, input_disposition_read_passes,
staging_root, durable_root, packet_relative_path, packet_file_count, packet_bytes,
output_manifest_sha256, output_manifest_size, output_packet_tree_sha256,
coverage_sha256, negative_controls_sha256, control_count, controls_passed,
structural_verdict, provenance_verdict, licensing_verdict,
open_unresolved_count, network_requests, retained_source_reads, runtime_reads,
acquired_bytes, acquisition_authorized, build_eligible, publication_eligible
```

Its schema is `convmem.switchboard.work-item-authoring-result.v2`; packet path is
`packet`; file/control counts are 7/40; structural verdict is `PASS`, provenance and
licensing are `PAUSE`; open count is 98,608; all access counters other than the later
grant-bounded packet/disposition reads are zero; all eligibility/authorization flags
are false. `author` is exactly `{path,sha256,size,interpreter,argv}` and interpreter is
exactly `{path,sha256,size,version,dependency_manifest_sha256}`. The result does not
self-hash; its external hash and size are returned for later review.

Controls `W001`–`W040` retain §18.30.7 order but are now single, deterministic
mutations: input packet digest; disposition digest; staging preexistence; durable
preexistence; missing coverage; extra role; manifest self-list; noncanonical coverage;
swapped component rows; symlink; work-item ID; citation ID; manifest PK hash; missing
component; duplicate component; missing dispute; duplicate dispute; missing unresolved
assignment; duplicate unresolved assignment; missing owned path; duplicate path;
moved origin gap; disputed path in component item; selected owner; missing edge;
duplicate edge; edge moved from container; inbound-only edge counted primary; batch
exchange; page exchange; state added to projection; candidate without sole citation;
case-normalized candidate; ready state with null operation; row closed; license choice;
`PATCHELF` remediation; per-component multiplier; external/unbound locator; and a
credential-bearing sentinel URL. Except for the targeted semantic defect, dependent
transport hashes are recomputed. The expected and observed rejection code is the
control ID. The unmutated baseline yields zero violations; combined mutants, a 41st
exception, output rewriting or any final packet/result on rejection is `PAUSE`.

#### 18.31.6 Held freeze, authoring and review sequence

After Kiro exact-tip PASS, a new Ryan grant may authorize only a disposable synthetic
author freeze. It names the script/interpreter/dependency/fixture identities and runs
one zero-violation baseline plus exactly forty same-cardinality synthetic mutants:
1,221 components, 19 disputes, 30,421 paths, 98,608 unresolved IDs, 1,384 edges,
twenty batches and 49 pages. Synthetic IDs use a separate fixture domain, cannot
publish real roots and do not read real evidence. Freeze receipts bind the command and
self-test; execution stops before packet/disposition reads or root creation.

Only another Ryan grant may name the frozen author, exact input paths, bounded read
passes/bytes, absent v2 roots and one run. That run builds `S.partial`, validates it,
computes the packet tree and result, copies to and verifies `D.partial`, freezes modes,
then atomically renames both partial roots locally to `S` and `D`. Failure preserves
partials without retry or repair. A separately granted independent reviewer later
recomputes every identity, assignment and control without modifying either root.

**Authority boundary.** This section authorizes only the four Switchboard planning-
document edits and exact-tip review. It authorizes no freeze, packet/disposition read,
root creation, authoring, network or retained-source access, acquisition, owner or
license selection, runtime access, binary repair, build, publication, CI admission,
implementation, PR `#342` update, merge, deployment, real OpenClaw, live data, watch
activation, promotion or Gate D/W/D-V/E/F action.

### 18.32 Candidate-gap, locator and author-freeze closure

The Kiro-reviewed §18.31 schema v2 remains absent and uninstantiated. Its first
synthetic-author-freeze preflight stopped before creating a freeze root or reading any
immutable packet/disposition byte because two executable mappings remained implicit:
which gaps each candidate cites, and which JSON pointer denotes a complete primary
row. A synthetic-freeze grant also requires an exact coordinate and ceilings. This
successor closes only those surfaces, advances the work-item schema to v3 and fresh
coordinates, and preserves every other §18.31 rule. No v2 or v3 packet/root exists.

#### 18.32.1 Version, coordinates and authority state

```text
WORK_ITEM_CANDIDATE_GAP_PLAN_BASE_SHA=dea026ce561e480ba3436d3c1cbea9bbcae6a14b
PROVENANCE_WORK_ITEM_V2_SCHEMA=convmem.switchboard.provenance-work-items.v2
PROVENANCE_WORK_ITEM_V2_PACKET_STATUS=ABSENT
PROVENANCE_WORK_ITEM_SCHEMA=convmem.switchboard.provenance-work-items.v3
PROVENANCE_WORK_ITEM_PACKET_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_AUTHORIZED=false
PROVENANCE_WORK_ITEM_AUTHORING_AUTHORIZED=false
PROVENANCE_ACQUISITION_EXECUTION_AUTHORIZED=false
PROVENANCE_WORK_ITEM_NEGATIVE_CONTROL_COUNT=42
PROPOSED_WORK_ITEM_STAGING_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
PROPOSED_WORK_ITEM_DURABLE_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/v3
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/v3.partial
PROPOSED_WORK_ITEM_AUTHOR_INTERPRETER=/home/lauer/miniforge3/bin/python3
PROPOSED_WORK_ITEM_AUTHOR_INTERPRETER_VERSION=3.13.12
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_MAX_TOTAL_WRITTEN_BYTES=67108864
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_MAX_PROCESS_COUNT=1
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_REAL_INPUT_READ_BYTES=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_NETWORK_REQUESTS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_RUNTIME_READS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_RETAINED_SOURCE_READS=0
```

The v2 roots remain absent historical coordinates and cannot be created, deleted,
reused or reinterpreted. The three v3 final/partial coordinates are single-assignment;
pre-existence is `PAUSE`. The proposed interpreter path/version is a design binding;
the future freeze must independently bind its exact executable hash/size and loaded
standard-library dependency manifest. Third-party packages, subprocesses, shell
evaluation, network and real evidence are forbidden.

Every v3 work-item manifest/result `plan_base_sha` and the freeze manifest
`plan_base_sha` equal `WORK_ITEM_CANDIDATE_GAP_PLAN_BASE_SHA`; no v2 plan-base value
survives in a v3 output.

#### 18.32.2 Canonical row and field locators

All initial citations use only the two locator forms already admitted by §18.31:
`record-json-pointer` and the host finding's `object-byte-range`. JSON pointers use
RFC 6901 syntax without URI-fragment encoding. The empty string `""` is the sole
complete-record pointer. Because the admitted field names contain neither `~` nor `/`,
their field pointers are the literal slash plus field name; no alternative escaping,
dot notation, array index, normalized alias or parent pointer is accepted.

The mapping is exact:

| Output reference | Packet role and primary key | Locator | Evidence object |
|---|---|---|---|
| `component_citation_id` | `component-lock.jsonl`; component ID | `record-json-pointer`, `pointer=""` | null |
| `file_citation_id` | `file-ownership.jsonl`; raw runtime path | `record-json-pointer`, `pointer=""` | null |
| any component/file `gap.citation_id` | `unresolved.jsonl`; unresolved ID | `record-json-pointer`, `pointer=""` | null |
| primary nested edge `citation_id` | `nested-components.jsonl`; frozen NUL-joined edge key | `record-json-pointer`, `pointer=""` | the row's exact `evidence_object_id` |
| component identity candidate | `component-lock.jsonl`; component ID | exactly `/name`, `/version`, `/build`, `/purl` or `/origin_namespace` | null |
| owner-component candidate | `unresolved.jsonl`; the dispute's owner-gap unresolved ID | exactly `/required_evidence` | null |
| each host-path occurrence | `objects.jsonl`; exact object ID | `object-byte-range` with the frozen occurrence offset and UTF-8 byte length of `needle` | the same object ID |

Every citation's `record_sha256` hashes the complete canonical packet row with no
projection. `primary_key` is the raw governed primary key. The work-item `citations`
array is exactly the set union of citations referenced by its primary citation fields,
gaps, edges, candidates and host findings; it contains neither an unreferenced citation
nor a missing referenced citation. The host finding has exactly one citation per
§18.29.4 occurrence. Those byte ranges attest the embedded needle; the exact
`reported_dynamic_tag` and `reported_dynamic_value` remain plan-bound §18.29.4 facts,
and no unrecorded synthetic ELF-analysis citation is manufactured.

#### 18.32.3 Exact candidate emission and gap assignment

For a component work item, the author considers the five source fields in this exact
order only to define the closed set; output remains sorted by candidate ID:

| Source field | Candidate kind | Emission rule |
|---|---|---|
| `name` | `component-name` | exactly one candidate for the present string |
| `version` | `component-version` | exactly one candidate for the present string |
| `build` | `component-build` | one candidate iff the field is non-null |
| `purl` | `component-purl` | one candidate iff the field is non-null |
| `origin_namespace` | `component-origin-namespace` | one candidate iff the field is non-null |

The candidate value is the exact JSON string value, including an empty string if the
governed nullable field is non-null and empty; the author does not judge usefulness.
Each candidate has exactly the singleton field citation from §18.32.2 and
`gap_unresolved_ids` equal to the component work item's complete sorted
`unresolved_ids` array: its six component gaps plus every owned path's three origin
gaps. This deliberately records each identity value as a non-authoritative search lead
for the whole component obligation without claiming that it proves any gap.

For a dispute item, only `owner-component-id` candidates may exist. Each exact bounded
token from the owner gap's `required_evidence` creates one candidate whose value is the
token, whose citation set is the singleton `/required_evidence` citation, and whose
`gap_unresolved_ids` is the singleton owner-gap unresolved ID. `candidate_owners`
contains the corresponding `{component_id,candidate_id,citation_ids}` row. No owner
candidate is assigned to the three origin gaps; no component identity candidate is
copied into a dispute item. A missing-owner row with no exact token has empty
`candidate_owners` and `candidates` and state `UNRESOLVED`; otherwise a dispute item is
`CANDIDATE_ONLY`.

For both work-item kinds, every candidate gap ID must belong to the same item; the
union need not equal the item's unresolved set because an owner candidate intentionally
does not cover origin gaps. No candidate gap array may be empty. Candidate identity
still excludes `gap_unresolved_ids` as §18.31 specifies; the complete record hash and
manifest bind the assignment. A candidate never changes gap `OPEN`, never selects an
owner, and never supplies origin, license or operation authority.

#### 18.32.4 Two new closed controls

Controls `W001`–`W040` retain their exact §18.31 meanings. Schema v3 adds exactly two
single-mutant receipts:

- `W041`: recompute transport hashes after deleting one required gap ID from a
  component identity candidate, adding a foreign-item gap, or assigning an owner
  candidate to an origin gap; the validator must return rejection code `W041`.
- `W042`: recompute the citation ID and transport hashes after replacing one required
  root pointer with a field pointer, one required field pointer with `""`, or one
  host byte range with a record pointer; the validator must return `W042`.

The fixture selects one deterministic representative mutation for each control run;
alternatives above define the rejected family, not combined mutants. The unmutated
same-cardinality baseline returns zero violations, exactly 42 individual runs return
their matching code, and no rejected run creates a final packet or result. A 43rd
semantic exception, combined mutant or nondeterministic receipt is `PAUSE` and requires
another versioned plan.

Accordingly, schema v3 `negative-controls.jsonl` contains exactly 42 rows rather than
40, and every row's `fixture_schema` is
`convmem.switchboard.work-item-synthetic-fixture.v3`. Its keys, ordering,
deterministic-receipt rules and all other §18.31.4 semantics remain unchanged.

#### 18.32.5 Exact synthetic freeze packet and ceilings

A future two-SHA Ryan grant may create only the proposed freeze partial/final root. It
contains exactly six mode-`0444` regular files under a mode-`0555` final directory:

1. `work-item-author-v3.py` — standard-library-only author and validator;
2. `fixture-spec.json` — exact synthetic identity domain, seedless construction and
   the 1,221/19/30,421/98,608/1,384/20/49 cardinalities;
3. `dependency-manifest.json` — interpreter path/version/hash/size and every imported
   standard-library source path/hash/size;
4. `command-contract.json` — exact argv, environment allowlist, cwd, zero-access
   counters, ceilings and expected files;
5. `self-test-receipt.json` — baseline result and sorted `W001`–`W042` receipts with
   no time, PID, random value or temporary-path identity; and
6. `freeze-manifest.json` — path/mode/size/hash descriptors for the preceding five
   files only; it never self-hashes.

The five JSON objects are canonical and closed:

- `fixture-spec.json` has exactly `schema`, `fixture_id`, `work_item_schema`,
  `counts`, `construction`. Schema is
  `convmem.switchboard.work-item-synthetic-fixture.v3`; `construction` is
  `COUNTER_DERIVED_CONTENT_ADDRESSED_NO_RANDOMNESS`; `counts` has exactly integer
  `components=1221`, `disputes=19`, `runtime_paths=30421`, `owned_paths=30402`,
  `disputed_paths=19`, `unresolved_ids=98608`, `nested_edges=1384`, `batches=20`,
  `pages=49`, `controls=42`. `fixture_id` is `fixture:sha256:` plus the hash of the
  complete canonical object with `fixture_id` omitted.
- `dependency-manifest.json` has exactly `schema`, `interpreter`, `modules`.
  Interpreter is exactly `{path,version,size,sha256}`. Each module row is exactly
  `{name,kind,path,size,sha256}`, sorted uniquely by `name`; `kind` is `file`,
  `built-in` or `frozen`. File rows have canonical absolute path, nonnegative size and
  SHA-256; built-in/frozen rows have explicit null for path/size/hash. `modules` is the
  complete `sys.modules` closure at receipt generation, excluding only the running
  author as it is independently hashed by the receipt.
- `command-contract.json` has exactly `schema`, `interpreter_path`, `argv`, `cwd`,
  `environment`, `ceilings`, `expected_final_members`. `cwd` is the exact partial
  root. Environment is exactly `LANG=C.UTF-8`, `LC_ALL=C.UTF-8`,
  `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`; no inherited
  key is authoritative. Ceilings has exactly integer `max_process_count=1`,
  `max_total_written_bytes=67108864`, `real_input_read_bytes=0`,
  `network_requests=0`, `runtime_reads=0`, `retained_source_reads=0`,
  `subprocesses=0`. Expected members are the sorted six names above.
- `self-test-receipt.json` has exactly `schema`, `fixture_sha256`, `author_sha256`,
  `dependency_manifest_sha256`, `command_contract_sha256`, `baseline`, `controls`,
  `access_counters`. Baseline is exactly `{violations:[],verdict:"PASS",
  final_packet_created:false,result_created:false}`. Controls are exactly 42 rows
  sorted by control ID, each with the §18.31.5 fields and v3 fixture schema; access
  counters equal the seven command-contract ceiling names with observed zero except
  `max_process_count=1` and an observed nonnegative `total_written_bytes` no greater
  than the ceiling.
- `freeze-manifest.json` has exactly `schema`, `plan_base_sha`,
  `work_item_schema`, `fixture_id`, `files`; files are five exact
  `{path,mode:"0444",size,sha256}` rows in raw path order and exclude the manifest.

The command contract's exact argv is the proposed interpreter, absolute author path,
literal subcommand `synthetic-freeze`, then pairs `--fixture-spec`,
`--command-contract`, `--dependency-manifest`, `--receipt`, `--freeze-manifest` with
their absolute partial-root paths in that order. No optional argument or positional
tail is accepted. The six-file tree hash is the hash of the canonical sorted
`{path,mode,size,sha256}` array, including `freeze-manifest.json`.

An external returned result reports the six-file tree hash, manifest hash/size, total
persisted bytes and final modes; it is not stored beneath the freeze root. The fixture
is generated in memory from counters and content-addressed synthetic IDs, never copied
from real packet bytes. The single Python self-test process may read only its own
partial-root files plus the bound interpreter and imported standard library. Final
plus transient writes must not exceed 67,108,864 bytes. It performs zero packet,
disposition, runtime, retained-source or repository-content reads, zero network
requests and zero subprocesses. On success it removes no evidence, verifies the six
members, freezes modes and atomically renames `.partial` to the final root once. On
any mismatch it preserves the partial root, creates no final root and stops without
retry or repair.

After Kiro PASS, that future grant authorizes only this synthetic freeze. A later
separate run grant must name the resulting author/freeze identities, exact immutable
input paths, real read ceilings and fresh v3 output roots. Independent packet review
remains another separately granted stage.

**Authority boundary.** This section authorizes only four Switchboard planning-
document edits and exact-tip review. It authorizes no freeze-root creation, script
creation/execution, packet/disposition/repository/runtime read, work-item root,
network request, retained-source inspection, acquisition, owner/license selection,
binary repair, build, publication, CI admission, implementation, PR `#342` update,
merge, deployment, real OpenClaw, live data, watch activation, promotion or Gate
D/W/D-V/E/F action.

### 18.33 Synthetic-edge freeze retry correction

Kiro passed the exact §18.32/§10.30 parent and milestone overlay at
`21f5accd742f4e4e53760420e33d0ecfe4c62829`. Ryan then granted only the
schema-v3 six-file synthetic freeze. The single governed process stopped before
creating any JSON member or final root because the unmutated synthetic baseline
correctly returned `W026` instead of zero violations. The author constructed 1,384
edge rows by cycling a 1,221-component ring without changing the nested component
after the first cycle; ordinals 1,221 through 1,383 therefore duplicated ordinals 0
through 162. This is an author-fixture defect, not a weakening of `W026` and not a
defect in the reviewed real-packet 1,384-edge contract.

#### 18.33.1 Preserved failed attempt and fresh coordinates

```text
WORK_ITEM_SYNTHETIC_EDGE_RETRY_PLAN_BASE_SHA=21f5accd742f4e4e53760420e33d0ecfe4c62829
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_STATUS=PAUSE
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_RETRY_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_RETRY_AUTHORIZED=false
PRESERVED_FAILED_WORK_ITEM_AUTHOR_FREEZE_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/v3.partial
PRESERVED_FAILED_WORK_ITEM_AUTHOR_SHA256=44b59831e95c551d59c58be13ae64d88d19d7d4064d27299404b8eef697e490c
PRESERVED_FAILED_WORK_ITEM_AUTHOR_SIZE=37887
PRESERVED_FAILED_WORK_ITEM_AUTHOR_MODE=0644
PRESERVED_FAILED_WORK_ITEM_AUTHOR_PARTIAL_TREE_SHA256=00ae693740248bf2c323a12d0faad10663160decbcff00fb530233f191d00ce1
PRESERVED_FAILED_WORK_ITEM_AUTHOR_EXIT_STATUS=1
PRESERVED_FAILED_WORK_ITEM_AUTHOR_PARTIAL_MEMBER_COUNT=1
PRESERVED_FAILED_WORK_ITEM_AUTHOR_JSON_MEMBER_COUNT=0
PRESERVED_FAILED_WORK_ITEM_AUTHOR_FINAL_ROOT_EXISTS=false
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_RETRY_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/21f5accd742f4e4e53760420e33d0ecfe4c62829/v3
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_RETRY_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/21f5accd742f4e4e53760420e33d0ecfe4c62829/v3.partial
SYNTHETIC_EDGE_COUNT=1384
SYNTHETIC_EDGE_PRIMARY_KEY_SHA256=718184327681f68dbdee4f0920eaea71f0d9b5a989c453f1c3bf2ddc7e867051
```

The failed partial root contains exactly the one mode-`0644` author named
`work-item-author-v3.py`; its canonical one-row
`{path,mode,size,sha256}` tree hashes to the value above. No fixture, dependency
manifest, command contract, self-test receipt, freeze manifest or final root exists.
The exception was `RuntimeError: synthetic baseline did not return zero violations`
with exit status 1. Static inspection proves that the first rejection was `W026`.
The process reached no JSON write, packet/disposition/runtime/retained-source read,
network operation or subprocess. Because no receipt exists, the attempt is failure
evidence only and cannot be cited as a zero-access acceptance receipt.

The failed partial is immutable by authority despite its stopped writable modes: it
must not be deleted, chmodded, completed, renamed, copied into a successor, imported,
executed again, repaired or used as a source of acceptance. The old final root remains
absent and must remain absent. The retry final/partial roots above are new,
single-assignment and confirmed absent at planning time. Pre-existence at a later
grant is `PAUSE`. Work-item schema v3, its packet roots, the immutable provenance
packet/disposition, candidate-gap mappings, locators, counts, ceilings and controls
`W001`–`W042` remain unchanged.

#### 18.33.2 Exact collision-free synthetic edge construction

The retry changes only the edge construction and the `W026` representative. Let
`N=1221` and let `C[0]..C[N-1]` be the raw-UTF-8 sorted synthetic component IDs,
where the unsorted counter domain is exactly:

```text
CANDIDATE(i) = "cmp_sha256:" +
  H(UTF8("convmem.switchboard.work-item-synthetic-fixture.v3" || NUL ||
         "component" || NUL || eight-ASCII-decimal-digits(i)))
for i = 0..1220
```

Here `eight-ASCII-decimal-digits(i)` means the zero-padded eight-digit decimal
representation used by the stopped author; it is locale-independent and has no sign
or separator. For each edge ordinal `i=0..1383`, compute `q=floor(i/N)` and
`r=i mod N`, then emit exactly:

```text
container_component_id = C[r]
nested_component_id = C[(r + 1 + q) mod N]
relationship = "contains"
edge_key = container_component_id || NUL || nested_component_id || NUL || relationship
```

Thus `q` is zero for the first 1,221 rows and one for the final 163. Within a round,
the container fixes `r`; across rounds, the same container points to offsets `+1`
and `+2`, so no key can collide. The 1,384 unique keys, sorted by raw UTF-8 bytes and
hashed as `H(concat(UTF8(edge_key)||NUL))`, must equal
`SYNTHETIC_EDGE_PRIMARY_KEY_SHA256`. The retry author must independently prove count
1,384, set size 1,384 and this hash before running any mutant.

The `W026` retry mutant remains single and same-cardinality: replace edge ordinal
1,383 with an exact second copy of edge ordinal 0, retain 1,384 list members, recompute
transport hashes, and require the validator's sole rejection code to be `W026`.
`W025` and `W027`–`W042` retain their reviewed meanings. The unmutated baseline must
return exactly `[]`; any other code, extra code, exception, changed count/hash or
successful `W026` mutant is `PAUSE` before a JSON write.

#### 18.33.3 Held retry sequence and authority boundary

The retry retains the exact §18.32.5 interpreter, environment, argv order, six file
roles and closed JSON schemas, one-process ceiling, 67,108,864-byte total-write
ceiling and zero real-input/network/runtime/retained-source/subprocess ceilings. The
new author is written from the reviewed plan, never copied or patched from the failed
partial. Its command contract names only the fresh retry partial root, and all new
author, dependency, fixture, command, receipt, manifest and tree identities must be
derived anew.

The only admissible sequence is: Kiro exact-tip PASS on this correction; a new
two-SHA Ryan grant naming the fresh retry roots; one synthetic process; external
return of the six-file identities; and stop before real reads. Failure again preserves
the new partial root without repair or retry. Real packet authoring and independent
review remain separate later grants.

**Authority boundary.** This correction authorizes only the four Switchboard
planning-document edits and exact-tip review. It authorizes no mutation, chmod,
deletion or execution of the failed partial; no retry author/root creation or
execution; no packet/disposition/repository/runtime/retained-source read; no network,
acquisition, owner/license selection, binary repair, build, publication, CI
admission, implementation, PR `#342` update, merge, deployment, real OpenClaw, live
data, watch activation, promotion or Gate D/W/D-V/E/F action.

### 18.34 Successful freeze binding and real-author capability closure

Kiro passed the exact §18.33/§10.31 retry overlay at
`59ae444ea3f021c4807be82a0114c1a4d8558602`. Ryan then granted one retry at the
fresh §18.33 coordinate. That single process completed the collision-free synthetic
baseline and all `W001`–`W042` controls, froze exactly six files, renamed the partial
root once and stopped before any real packet, disposition, repository, runtime or
retained-source read. The prior one-file failed partial remains immutable.

The successful freeze is valid synthetic evidence, but it is not a real-packet
author. Its exact command contract admits only `synthetic-freeze`, and its exact
source accepts only that argv. It has no real input-path grammar, packet/disposition
reader, work-item output-root transaction or `author-packet` entry point. Therefore
the frozen v3 artifact cannot satisfy the later-run premise in §§18.31.6/18.32.5.
This is a capability boundary, not a failed semantic control: no synthetic PASS may
be reinterpreted as proof that an absent real I/O path works.

#### 18.34.1 Bound v3 freeze result and immutable stop

```text
WORK_ITEM_AUTHOR_RESULT_PLAN_BASE_OVERLAY_SHA=59ae444ea3f021c4807be82a0114c1a4d8558602
PROVENANCE_WORK_ITEM_SCHEMA=convmem.switchboard.provenance-work-items.v3
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_STATUS=PASS
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/21f5accd742f4e4e53760420e33d0ecfe4c62829/v3
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_TREE_SHA256=65f32f116472de8bce8b9c01dedf52d33c0f2dec6794bb8a2a00a460c403f826
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_MEMBER_COUNT=6
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_TOTAL_BYTES=80329
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_ROOT_MODE=0555
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_MEMBER_MODE=0444
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_FIXTURE_ID=fixture:sha256:a74c1322e073b91d1e704db6bf596bba4f983647a4f0873cc27e2c7252dcedb2
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_EDGE_KEY_SET_SHA256=718184327681f68dbdee4f0920eaea71f0d9b5a989c453f1c3bf2ddc7e867051
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_CONTROL_COUNT=42
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_CONTROLS_PASSED=42
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_REAL_AUTHOR_CAPABILITY=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_REAL_AUTHOR_ELIGIBLE=false
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_AUTHORIZED=false
PROVENANCE_WORK_ITEM_AUTHORING_AUTHORIZED=false
PROVENANCE_ACQUISITION_EXECUTION_AUTHORIZED=false
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial
```

The v3 final root is single-assignment and immutable. It contains exactly:

| File | Size | SHA-256 |
|---|---:|---|
| `work-item-author-v3.py` | 42,795 | `8c6dd7e2c1905980e9e431c96945f3c80d9f221e63680e9b8a58e1e34495f603` |
| `fixture-spec.json` | 476 | `d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f` |
| `dependency-manifest.json` | 8,471 | `6faff2fbede20477e4abeacfae62ff4156aa11ff732193f454740e5ed7bdb100` |
| `command-contract.json` | 1,708 | `dc2ec169bb79ff98d2b2e0fc6d25b12121b1094c68b7d22a2863e3891ccd7002` |
| `self-test-receipt.json` | 25,912 | `bd71db8ecaffd10ec7d2fa5e15c1fb4f91fad5a14d197ee2b0350f153ec7ae4f` |
| `freeze-manifest.json` | 967 | `8e9bee683e79c969bdc32c62f75a578f7f2a4e271bbd65fe85550441dfc07992` |

The interpreter remains `/home/lauer/miniforge3/bin/python3`, version `3.13.12`,
size `32,959,480`, SHA-256
`66c90902aba57b52abbe5e31e54fe65826c2046496f1656ef0f4e9d1ea26c8b0`,
with the 65-row standard-library dependency manifest bound above. The self-test
receipt records one zero-violation baseline, `42/42` individual controls, one process,
80,329 total written bytes and zero real-input, network, runtime, retained-source and
subprocess access. The required synthetic `W040` sentinel
`https://user:secret@example.invalid/` is test data, not a credential or an admitted
origin.

The v3 root may not be modified, chmodded, deleted, renamed, copied into a successor,
executed for real input or treated as an authoring grant. The new v4 roots and both
existing v3 work-item packet roots (including `.partial` siblings) were absent when
this plan was authored. Pre-existence at any later grant is `PAUSE`.

#### 18.34.2 Exact capability gap

The v3 `command-contract.json` contains one argv whose sole verb is
`synthetic-freeze`. The frozen source requires exact equality with that argv and
rejects every other command. It contains no admitted `author-packet` verb and no
contract for:

- the immutable schema-v3 packet root or independent disposition path;
- one-pass input member enumeration, hashing and canonical parsing;
- the v3 staging/durable packet roots or their `.partial` siblings;
- the seven-file packet plus external result transaction in §18.31; or
- the real-run read, write and access counters.

Consequently `PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V3_REAL_AUTHOR_ELIGIBLE=false` is
frozen. A wrapper, patched copy, dynamic import, shell pipeline, new subcommand,
environment switch or caller-side reader would be a new unreviewed author and is
forbidden. The v3 freeze remains positive evidence only for the shared deterministic
work-item builder/validator and the exact synthetic controls it actually ran.

#### 18.34.3 Successor v4 capability freeze

The successor changes no work-item schema, candidate/gap mapping, locator, ID,
ordering, coverage, `W001`–`W042` meaning or output-root coordinate. It freezes a new
standard-library-only `work-item-author-v4.py` at the fresh v4 coordinate. One source
must expose exactly two closed verbs:

1. `synthetic-freeze`, which retains the §18.33 collision-free fixture and runs the
   same zero-violation baseline plus `W001`–`W042`; and
2. `author-packet`, which owns the complete read, build, validation, two-root commit
   and result path in §18.34.4.

Both verbs must call the same `load -> derive -> validate -> serialize` core. The
synthetic path may substitute only a fixture-backed read adapter and disposable roots
under the v4 partial. It must exercise the real packet/disposition parsers, the exact
seven output serializers, both-root copy/verification logic and external-result
builder without reading real input. It removes every disposable synthetic input and
output before the six final freeze files are sealed. A test-only implementation that
bypasses a production function, a production verb that is present but unexecuted, or
two separately implemented derivation paths is `PAUSE`.

The v4 final root again contains exactly the six mode-`0444` roles
`work-item-author-v4.py`, `fixture-spec.json`, `dependency-manifest.json`,
`command-contract.json`, `self-test-receipt.json` and `freeze-manifest.json` under a
mode-`0555` root. The command contract contains both ordered argv contracts and the
closed environment:

```text
LANG=C.UTF-8
LC_ALL=C.UTF-8
PYTHONDONTWRITEBYTECODE=1
PYTHONHASHSEED=0
PYTHONNOUSERSITE=1
```

The v4 synthetic freeze retains one process, zero subprocesses, zero network and zero
real-input/runtime/retained-source reads, with one aggregate transient-plus-persisted
write ceiling of `67,108,864` bytes. It runs exactly 52 independent controls: the
unchanged `W001`–`W042` plus:

| Control | Exact rejected capability drift |
|---|---|
| `F001` | missing or renamed `author-packet` verb |
| `F002` | extra, missing, reordered or non-literal real argv member |
| `F003` | input packet root differs from the exact governed coordinate |
| `F004` | disposition path differs from the exact governed coordinate |
| `F005` | a second content pass or byte above either frozen input ceiling |
| `F006` | any output write before both inputs finish identity/schema validation |
| `F007` | synthetic and real verbs reach different derive/validate/serialize cores |
| `F008` | network, subprocess, repository, runtime or retained-source access |
| `F009` | staging/durable final or partial root pre-exists or has a symlinked ancestor |
| `F010` | output role/result/counter/mode/atomic-rename contract differs from §18.34.4 |

Each control is one deterministic mutation whose expected and observed rejection code
is its own ID; the clean baseline has zero violations. Combined controls, an `F011`,
nondeterministic receipt, missing executed production path, leftover disposable file
or post-failure output rewrite is `PAUSE`. A later exact Ryan grant is required before
the v4 partial may be created or the single synthetic process may run.

#### 18.34.4 Held one-pass real packet authoring contract

Only after v4 Kiro PASS, a separately granted successful v4 freeze and a result-binding
review may a still-later Ryan grant name one `author-packet` run. Its closed inputs are:

```text
INPUT_PACKET_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet
INPUT_PACKET_TREE_SHA256=491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5
INPUT_PACKET_TREE_MEMBER_COUNT=902
INPUT_PACKET_BYTES=654147403
INPUT_MANIFEST_SHA256=6791d33a82bd0f1e3fdbda072ae50aa296953b6a365194564090085541784fa4
INPUT_DISPOSITION_PATH=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json
INPUT_DISPOSITION_SHA256=45442e93958e7f0c4a2e4bf474d0b7430653fc0320ab1bad1b8222501b830669
INPUT_DISPOSITION_BYTES=8383806
MAX_INPUT_PACKET_CONTENT_PASSES=1
MAX_INPUT_DISPOSITION_CONTENT_PASSES=1
MAX_REAL_INPUT_READ_BYTES=662531209
MAX_PROCESS_COUNT=1
MAX_SUBPROCESS_COUNT=0
MAX_PEAK_RSS_BYTES=2147483648
MAX_SINGLE_OUTPUT_ROOT_BYTES=2147483648
MAX_TOTAL_WRITTEN_BYTES=4294967296
NETWORK_REQUESTS=0
RETAINED_SOURCE_READS=0
RUNTIME_READS=0
ACQUIRED_BYTES=0
```

The exact output roots remain the absent schema-v3 coordinates in §18.32.1. Directory
metadata enumeration does not consume a second content pass. Every regular input file
represented in the 902-member tree is opened for content at most once; its bytes feed
hashing and canonical parsing in the same stream. The disposition is opened once. The exact two
byte ceilings sum to `662,531,209`; early EOF, an extra byte/member, missing member,
symlink, special file, hard link, mode/hash/tree/manifest mismatch, second open for
content or parser replay is `PAUSE` before any output write.

After both inputs validate completely, retaining only bounded in-memory indexes in the
one process,
the author creates only the two exact absent `.partial` roots. It emits the seven
§18.31/§18.32 packet roles and external `authoring-result.json` to staging, validates
all 1,240 items, 98,608 unique open-ID assignments, 30,421 paths, 1,384 primary edges,
20 batches, 49 pages, 19 disputes, exact candidate/citation unions, `W001`–`W042`,
hashes and modes, then copies only those newly generated bytes to the durable partial.
It proves byte/mode/tree equality, freezes both roots, and atomically renames each once.
The aggregate write ceiling includes both copies, results and every transient regular
file; no per-component, per-page or retry multiplier exists.

Both final roots are mode `0555` and contain exactly mode-`0555` `packet/` plus mode-
`0400` `authoring-result.json`; packet files are mode `0444`. The result retains the
closed §18.31.5 schema, binds the future v4 author/freeze identities and reports the
exact input read counters above. It returns its own external size/SHA-256 and both root
tree identities; it never self-hashes. Any failure preserves partials, writes no final
root/result, and has no automatic retry, repair, deletion or resume route.

#### 18.34.5 Review sequence and authority boundary

The only valid sequence is:

1. Kiro exact-tip reviews this v3 result binding, capability diagnosis, v4 freeze and
   held real-read contract.
2. A new two-SHA Ryan grant may create and run only the fresh v4 synthetic freeze.
3. Codex binds the returned six identities in another plan-only overlay; Kiro reviews
   the exact frozen capability.
4. A separate Ryan grant may authorize one exact `author-packet` run with the inputs,
   roots, argv and ceilings above.
5. A separately granted independent reviewer recomputes every output identity and
   assignment without modifying packet, result or inputs.

This section authorizes only four Switchboard planning-document edits and exact-tip
review. It authorizes no v4 root/file creation, freeze execution, packet/disposition
content read, work-item root/result creation, network, retained-source or runtime
read, acquisition, ownership/license selection, binary repair, build, publication,
CI admission, product/test/config/R2b change, implementation, PR `#342` update, merge,
deployment, real OpenClaw, live data, watch activation, promotion or Gate
D/W/D-V/E/F action.

### 18.35 V4 synthetic write-budget preflight correction

Kiro passed the exact §18.34/§10.32 capability plan at
`42109775294bf9f20bacaac8f33abf00211fc082`. Ryan then granted only the fresh v4
synthetic capability freeze. Before creating either v4 root or running a governed
process, Astra's static preflight proved that the inherited 67,108,864-byte aggregate
write ceiling cannot contain the full-cardinality shared production transaction.
The preflight therefore stopped without consuming a root coordinate or execution
attempt. No v4 author, receipt, manifest or partial exists, and no real packet or
disposition byte was read.

#### 18.35.1 Exact failed-budget proof and preserved state

```text
WORK_ITEM_AUTHOR_WRITE_BUDGET_PLAN_BASE_OVERLAY_SHA=42109775294bf9f20bacaac8f33abf00211fc082
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_PREFLIGHT_STATUS=PAUSE
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_PREFLIGHT_ROOT_CREATED=false
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_PREFLIGHT_PROCESS_COUNT=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_PREFLIGHT_REAL_INPUT_READ_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_PREFLIGHT_NETWORK_REQUESTS=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_MIN_GAP_BYTES=262
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_MIN_CITATION_BYTES=468
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_OPEN_UNRESOLVED_COUNT=98608
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_ONE_COPY_LOWER_BOUND_BYTES=71983840
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_TWO_COPY_LOWER_BOUND_BYTES=143967680
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_MAX_TOTAL_WRITTEN_BYTES=67108864
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_AUTHORIZED=false
PROVENANCE_WORK_ITEM_AUTHORING_AUTHORIZED=false
```

Sections 18.31.2 and 18.32.2 require every one of the 98,608 open unresolved
assignments to appear as a gap object and to contribute its complete unresolved-row
citation to the owning item's exact citation union. Even an artificially shortened
canonical gap with empty field/reason/evidence strings is 262 bytes, and even a
canonical citation using a bare 64-character primary key is 468 bytes. Thus one
packet requires at least
`98,608 × (262 + 468) = 71,983,840` bytes for only those objects; the mandatory
staging and durable copies require at least 143,967,680 written bytes. The one-copy
minimum alone exceeds 67,108,864 by 4,874,976 bytes. The proof deliberately excludes
array punctuation, record wrappers, components, paths, edges, candidates, batches,
pages, manifests, results, fixtures, the author and freeze receipts, so it is a strict
lower bound rather than a size prediction.

The two byte counts are reproducible as `len(J(value))` over these exact artificial
lower-bound objects, where `Z64` is sixty-four ASCII zeroes. They intentionally omit
the required `unresolved_sha256:` prefixes, so no real object can be shorter:

```text
MIN_GAP={
  "blocks":true,
  "citation_id":"citation:sha256:" + Z64,
  "field":"",
  "reason_code":"",
  "required_evidence":"",
  "status":"OPEN",
  "unresolved_id":Z64
}  # 262 canonical bytes

MIN_CITATION={
  "citation_id":"citation:sha256:" + Z64,
  "evidence_object_id":null,
  "locator":{"kind":"record-json-pointer","pointer":""},
  "packet_file_role":"unresolved.jsonl",
  "packet_tree_sha256":Z64,
  "primary_key":Z64,
  "record_sha256":Z64
}  # 468 canonical bytes
```

The §18.34 v4 final/partial roots and all four schema-v3 work-item final/partial roots
remain absent and single-assignment. The successful v3 freeze and earlier failed
partial remain byte- and mode-immutable. This preflight did not run an author, create
a file, consume an input pass or authorize a retry under the impossible ceiling.

#### 18.35.2 Corrected bounded write contract

The successor changes only the v4 synthetic-freeze aggregate write budget and makes
its accounting executable. Every §18.34 schema, role, root, interpreter, environment,
shared `load -> derive -> validate -> serialize` path, full-cardinality fixture,
`W001`–`W042`, `F001`–`F010`, one-process limit, 2-GiB peak-RSS ceiling and zero
subprocess/network/real-input/repository/runtime/retained-source counters remains
unchanged.

```text
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_MAX_TOTAL_WRITTEN_BYTES=1073741824
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_MAX_PEAK_RSS_BYTES=2147483648
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_MAX_PROCESS_COUNT=1
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_SUBPROCESSES=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_REAL_INPUT_READ_BYTES=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_NETWORK_REQUESTS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RUNTIME_READS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETAINED_SOURCE_READS=0
```

The 1-GiB ceiling is a hard maximum, not a target, reservation or permission to pad.
It is greater than the proved two-copy lower bound while remaining one quarter of the
unchanged 4-GiB later real-run ceiling. The governed process must minimize writes and
must not preallocate, fill, compress, sparsify, hard-link, reflink or deduplicate a
payload to evade accounting.

Before the first disposable packet or result byte is written, the author builds the
complete canonical synthetic payloads in memory and computes an exact ordered write
ledger. The ledger counts, from v4 partial-root creation through final seal:

1. the new author and every persisted freeze member;
2. every materialized synthetic input or fixture byte;
3. every staging packet/result and every separately written durable-copy byte;
4. every temporary or rejected-control output byte actually written; and
5. every replacement write, which is otherwise forbidden.

Each ledger row is exactly `{ordinal,path,purpose,size,sha256}`; `ordinal` is the
zero-based file-creation order, paths are relative to the v4 partial, `purpose` is one
of `author`, `synthetic-input`, `staging-output`, `durable-output`, `freeze-member`,
or `temporary`, and rows retain raw write order. `size` is always the exact
nonnegative byte count. `sha256` is the exact 64-lowercase-hex digest except for
exactly the `self-test-receipt.json` and `freeze-manifest.json` events, where it is
JSON null. Those two nulls are mandatory: the receipt contains this ledger and the
manifest binds the receipt, so placing either final digest back into the ledger would
create a recursive or mutually recursive identity. The existing nonrecursive chain
still binds their actual bytes: `freeze-manifest.json` hashes the receipt, and the
external returned result hashes the manifest.

Every regular file is created exclusively, opened for write once, filled from one
already-canonical in-memory byte string, flushed and fsynced before the next row. The
pre-process setup may create only the new author as row zero; its observed size/hash
must equal the file the governed process validates before any other creation. Before
writing any category 3–5 byte, the author constructs every other payload, inserts the
two required null-digest rows, and resolves only their `size` fields by deterministic
fixed-point iteration: start both sizes at zero; rebuild the ledger, receipt and
non-self-hashing manifest in that order; replace the two sizes; and repeat until the
ordered size pair is unchanged. Repetition without equality or more than sixteen
iterations is `PAUSE`. One final rebuild must reproduce the same pair, receipt hash
and manifest bytes before any output write.
The forecast sum must be no greater than 1,073,741,824 before the first category 3–5
write. The observed byte counter sums the validated row-zero author size plus the
length of every governed regular-file write and must equal the forecast exactly after
disposable cleanup and before rename.
Directory metadata, mode changes, fsync and rename contribute zero bytes; an unknown
write, short write, second write to an exclusive role, forecast/observed mismatch or
one byte above the cap is `PAUSE`.

The v4 self-test receipt retains every §18.32.5 field and adds exactly one
`write_budget` object with exactly `ceiling_bytes`, `events`,
`forecast_total_written_bytes`, `ledger_sha256` and
`observed_total_written_bytes`. `events` is the complete row array above;
`ledger_sha256=H(J(events))`; both totals are nonnegative integers, are equal on PASS
and do not exceed `ceiling_bytes=1073741824`. The command contract's `ceilings` object
changes only `max_total_written_bytes` to 1,073,741,824 and adds exact
`max_peak_rss_bytes=2147483648`; every other key/value is unchanged. The complete
ledger remains inside the existing receipt role, so no seventh freeze role or
unreviewable sidecar exists. `F005` and `F010` cover any ceiling, ledger, special-row
nullability, fixed-point, output-role or transaction drift; no `F011`, combined mutant
or weakened control is introduced.

The later real `author-packet` contract remains exactly §18.34.4: one input pass each,
662,531,209 aggregate input bytes, 2-GiB peak RSS and per-output-root ceilings, and
4,294,967,296 aggregate written bytes. The synthetic correction neither multiplies
nor transfers its 1-GiB ceiling into that later run.

#### 18.35.3 Review sequence and authority boundary

The only admissible next sequence is Kiro exact-tip review of this correction, a new
Ryan two-SHA grant naming the still-absent v4 roots and corrected 1-GiB ceiling, one
synthetic process, external return of the six identities plus write-ledger hash and
counters, then another plan-only result binding and Kiro capability review. The prior
grant cannot be reused because its frozen budget was impossible, even though no root
or process was consumed.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no v4 root/file creation or execution, packet/disposition
content read, work-item root/result creation, network, subprocess, retained-source or
runtime read, acquisition, ownership/license selection, binary repair, build,
publication, CI admission, product/test/config/R2b change, implementation, PR `#342`
update, merge, deployment, real OpenClaw, live data, watch activation, promotion or
Gate D/W/D-V/E/F action.

### 18.36 V4 synthetic result-identity preflight correction

Kiro passed the exact §18.35/§10.33 write-budget overlay at
`7fe275239a47db58bc1dc30bfa3748cb2d685c78`. Ryan then granted only the corrected
v4 synthetic capability freeze. Before creating either root, writing an author or
running a governed process, Astra's static preflight found one remaining recursive
identity in the synthetic transaction. The preflight stopped without consuming the
single-assignment coordinate or execution attempt. No v4 file or root exists, and no
packet, disposition, repository, runtime or retained-source byte was read.

#### 18.36.1 Exact stopped state and cycle proof

```text
WORK_ITEM_AUTHOR_RESULT_IDENTITY_PLAN_BASE_OVERLAY_SHA=7fe275239a47db58bc1dc30bfa3748cb2d685c78
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_RESULT_IDENTITY_PREFLIGHT_STATUS=PAUSE
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_RESULT_IDENTITY_PREFLIGHT_ROOT_CREATED=false
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_RESULT_IDENTITY_PREFLIGHT_AUTHOR_CREATED=false
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_RESULT_IDENTITY_PREFLIGHT_PROCESS_COUNT=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_RESULT_IDENTITY_PREFLIGHT_REAL_INPUT_READ_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_RESULT_IDENTITY_PREFLIGHT_NETWORK_REQUESTS=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_AUTHORIZED=false
PROVENANCE_WORK_ITEM_AUTHORING_AUTHORIZED=false
```

Section 18.31.5 requires each synthetic `authoring-result.json` to contain
`author_freeze_receipt_sha256` and `self_test_receipt_sha256`. Section 18.34.3
requires the synthetic verb to exercise the unchanged production result builder, and
§18.35.2 requires non-null exact digests for both disposable result copies in the
ledger embedded by `self-test-receipt.json`. Let `R` be the final receipt bytes and
`A` either identical result copy. Under the reviewed contract, `A` contains `H(R)`
while `R` contains `H(A)`. The two reviewed null-digest events break only the
receipt/manifest cycle; the size fixed point never authorizes a cryptographic fixed
point. Inventing a placeholder, adding a third null digest, weakening the result
schema or bypassing the production builder is `PAUSE`.

#### 18.36.2 Closed synthetic predecessor-identity adapter

The successor changes only the identity pair supplied to the unchanged result builder
while `mode="synthetic-freeze"`. Define:

```text
SYNTHETIC_RESULT_IDENTITY_DOMAIN=convmem.switchboard.work-item-author-v4.synthetic-result-identity.v1
SYNTHETIC_RESULT_IDENTITY_PLAN_BASE_SHA=7fe275239a47db58bc1dc30bfa3748cb2d685c78
SYNTHETIC_AUTHOR_FREEZE_RECEIPT_IDENTITY_INPUT_BYTES=138
SYNTHETIC_AUTHOR_FREEZE_RECEIPT_SHA256=62dbd8500091eeeb91b4c4c8171ea50d999a6b5e8eca4b569db46a27ce18ebaf
SYNTHETIC_SELF_TEST_RECEIPT_IDENTITY_INPUT_BYTES=134
SYNTHETIC_SELF_TEST_RECEIPT_SHA256=37d2d4fdf1c0f7ca10dbcf85b4be621a710e19bee83e35529950f2676081160c
```

For field name `F`, the exact derivation is
`H(UTF8(SYNTHETIC_RESULT_IDENTITY_DOMAIN) || NUL || UTF8(F) || NUL ||
UTF8(SYNTHETIC_RESULT_IDENTITY_PLAN_BASE_SHA))`. `F` is exactly
`author_freeze_receipt_sha256` or `self_test_receipt_sha256`; there is no third field,
normalization, encoding variation, caller override or lookup. The two canonical input
byte strings are respectively 138 and 134 bytes and must reproduce the two hashes
above before any output write.

The shared production path contains one closed identity adapter with exactly two
modes:

1. `synthetic-freeze` accepts no identity input and returns exactly the two constants
   above to the unchanged §18.31.5 result builder. They are test-only predecessor
   identities, never claims about the receipt being constructed. Both staging and
   durable disposable results must be byte-identical and contain those values.
2. `author-packet` rejects both synthetic constants and requires the actual
   independently frozen v4 identities: `author_freeze_receipt_sha256` is the reviewed
   SHA-256 of `freeze-manifest.json`, and `self_test_receipt_sha256` is the reviewed
   SHA-256 of `self-test-receipt.json`. A later result-binding overlay must freeze both
   exact values before the real verb is eligible; this section does not supply or
   authorize them.

The adapter runs inside the same `load -> derive -> validate -> serialize` core. It is
not a second result builder, fixture serializer, argv field, environment switch or
output schema. The synthetic results retain ordinary non-null ledger hashes. Exactly
the receipt and freeze-manifest ledger rows remain null, and the existing at-most-
sixteen-iteration size fixed point remains unchanged. After the receipt and manifest
are built, the self-test must prove that neither synthetic constant equals either
actual v4 member digest. `F010` rejects the wrong mode, field, domain, base SHA,
constant, caller-supplied synthetic identity, synthetic value on the real path, actual
receipt value on the synthetic path or a changed result byte; no `F011`, extra control
or acceptance transfer is introduced.

#### 18.36.3 Preserved contract, sequence and authority boundary

Every §18.34/§18.35 root, role, cardinality, parser, serializer, control, ceiling,
write-ledger rule and later real-read contract remains unchanged. The only admissible
next sequence is Kiro exact-tip review, a new Ryan two-SHA grant naming the still-
absent v4 roots and this exact identity pair, one synthetic process, external return
of the six identities plus ledger/result counters, then plan-only result binding and
Kiro capability review. Neither prior grant is reusable.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no v4 root/file creation or execution, packet/disposition
content read, work-item root/result creation, network, subprocess, retained-source or
runtime read, acquisition, ownership/license selection, binary repair, build,
publication, CI admission, product/test/config/R2b change, implementation, PR `#342`
update, merge, deployment, real OpenClaw, live data, watch activation, promotion or
Gate D/W/D-V/E/F action.

### 18.37 V4 real-command argv preflight correction

Kiro passed the exact §18.36/§10.34 result-identity overlay at
`3107d6f57fc8835c5252fcd75fa3f87fea918aa3`. Ryan then granted only the corrected
v4 synthetic capability freeze. Before creating either root, writing the author or
running a governed process, Astra's static preflight found that §18.34.3 requires two
ordered argv contracts and `F002` rejects drift from the literal real vector, but no
reviewed section enumerates that vector. Choosing flags, order, implicit values or a
no-argument real command during author construction would therefore invent the
control oracle. The preflight stopped without consuming the coordinate or execution
attempt.

#### 18.37.1 Exact stopped state

```text
WORK_ITEM_AUTHOR_REAL_ARGV_PLAN_BASE_OVERLAY_SHA=3107d6f57fc8835c5252fcd75fa3f87fea918aa3
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_REAL_ARGV_PREFLIGHT_STATUS=PAUSE
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_REAL_ARGV_PREFLIGHT_ROOT_CREATED=false
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_REAL_ARGV_PREFLIGHT_AUTHOR_CREATED=false
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_REAL_ARGV_PREFLIGHT_PROCESS_COUNT=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_REAL_ARGV_PREFLIGHT_WRITTEN_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_REAL_ARGV_PREFLIGHT_REAL_INPUT_READ_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_REAL_ARGV_PREFLIGHT_NETWORK_REQUESTS=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_AUTHORIZED=false
PROVENANCE_WORK_ITEM_AUTHORING_AUTHORIZED=false
```

Both §18.34 v4 coordinates remain absent and single-assignment. No acceptance
receipt, member identity, ledger, control result or tree hash exists. Neither earlier
execution grant transfers to a successor.

#### 18.37.2 Closed two-command contract

The v4 `command-contract.json` object has exactly these nine keys:

```text
schema
interpreter_path
argv
cwd
environment
ceilings
expected_final_members
author_packet_argv
author_packet_cwd
```

`schema` is exactly
`convmem.switchboard.work-item-author-command-contract.v4`.
`interpreter_path`, `environment`, `ceilings` and `expected_final_members` retain
their §18.32.5/§18.35 meanings and values. Unknown, missing or additional keys are
`PAUSE`. The existing `argv` and `cwd` remain the synthetic contract: `cwd` is the
exact v4 partial root, and `argv` is this exact thirteen-member string array:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/work-item-author-v4.py",
  "synthetic-freeze",
  "--fixture-spec",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/fixture-spec.json",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/freeze-manifest.json"
]
```

`author_packet_cwd` is exactly the sealed v4 final root
`/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4`.
`author_packet_argv` is exactly this nineteen-member string array:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4/work-item-author-v4.py",
  "author-packet",
  "--input-packet-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet",
  "--input-disposition",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json",
  "--staging-root",
  "/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--durable-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4/freeze-manifest.json"
]
```

No optional argument, alias, reordered pair, implicit value, identity override,
environment-derived coordinate or positional tail is admitted. The two output
arguments name the governed final roots; only their literal `.partial` siblings are
derived by the already reviewed two-root transaction. The synthetic partial cwd
disappears on successful rename, so it cannot serve as the real cwd. `ceilings`
continues to describe the synthetic freeze; §18.34.4 remains the separate unchanged
real-run ceiling contract.

#### 18.37.3 Exact `F002` representative and authority boundary

The sole `F002` mutant exchanges complete zero-based argv slices `[3:5]` and `[5:7]`:
the `--input-packet-root` flag/value pair and the `--input-disposition` flag/value
pair. The mutant preserves all nineteen string values and array length, changes only
their pair order, and must return exactly `["F002"]` before content access or output
creation. No combined mutant, second `F002` representative, `F011` or exception is
admitted.

Every §18.34–§18.36 root, identity adapter, result schema, mapping, cardinality,
parser, serializer, `W001`–`W042`, `F001`–`F010`, ceiling, write-ledger rule and later
real-read contract remains unchanged. The only admissible next sequence is exact-tip
Kiro review, a new Ryan two-SHA grant naming the still-absent v4 roots and this closed
command contract, one synthetic process, external return of the six identities plus
ledger/result counters, then plan-only result binding and Kiro capability review.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no v4 root/file creation or execution, packet/disposition
content read, work-item root/result creation, network, subprocess, retained-source or
runtime read, acquisition, ownership/license selection, binary repair, build,
publication, CI admission, product/test/config/R2b change, implementation, PR `#342`
update, PR creation, merge, deployment, real OpenClaw, live data, watch activation,
promotion or Gate D/W/D-V/E/F action.

### 18.38 V4 input packet-tree identity preflight correction

Kiro passed the exact §18.37/§10.35 real-command overlay at
`be76abc544f02920336e7728f1b2a847fb02d40f`. Ryan then granted only the fresh v4
synthetic capability freeze. Before creating either v4 root, writing an author or
starting a process, Astra found that §18.34.4 binds the immutable input packet to
902 members, 654,147,403 regular-file bytes and tree SHA-256 `491ae60b...`, but the
reviewed plan never defines the canonical inventory that produces that tree hash.
The objects-only recipe in §18.25.2 and the seven-file output recipe in §18.31.4 are
different identities and cannot be substituted. Guessing a directory-row grammar
and validating a synthetic fixture produced by the same guess would be circular, so
the preflight stopped fail-closed without consuming either single-assignment root or
the execution attempt.

#### 18.38.1 Exact stopped state and derivation authority

```text
WORK_ITEM_AUTHOR_INPUT_TREE_RECIPE_PLAN_BASE_OVERLAY_SHA=be76abc544f02920336e7728f1b2a847fb02d40f
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_INPUT_TREE_PREFLIGHT_STATUS=PAUSE
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_INPUT_TREE_PREFLIGHT_ROOT_CREATED=false
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_INPUT_TREE_PREFLIGHT_AUTHOR_CREATED=false
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_INPUT_TREE_PREFLIGHT_PROCESS_COUNT=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_INPUT_TREE_PREFLIGHT_WRITTEN_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_INPUT_TREE_PREFLIGHT_REAL_INPUT_READ_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_INPUT_TREE_PREFLIGHT_PACKET_CONTENT_READ_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_INPUT_TREE_PREFLIGHT_DISPOSITION_CONTENT_READ_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_INPUT_TREE_PREFLIGHT_NETWORK_REQUESTS=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_AUTHORIZED=false
PROVENANCE_WORK_ITEM_AUTHORING_AUTHORIZED=false
```

Both §18.34 v4 coordinates remain absent and single-assignment. No author, receipt,
manifest, control result, member identity or freeze tree exists. The stopped grant is
not reusable.

Ryan separately authorized a bounded read-only derivation of the missing recipe. The
authority source is the already frozen schema-v3 collector, not the packet contents,
chat recollection or a newly invented fixture:

```text
AUTHORITATIVE_PACKET_TREE_COLLECTOR_PATH=/home/lauer/.cache/convmem-switchboard-provenance-collector-freeze/1cb8186e5e0938524414c530d5b842219f52412f/d03aa5538e0b82f1165a725394ef8df4bf805dbd/collect_p0.py
AUTHORITATIVE_PACKET_TREE_COLLECTOR_SHA256=26352b39f3ff53bf8a41c579c4c9aec8a8f8734235fe99db0a8480fa9964adad
AUTHORITATIVE_PACKET_TREE_COLLECTOR_SIZE=67575
AUTHORITATIVE_PACKET_TREE_COLLECTOR_MODE=0444
AUTHORITATIVE_PACKET_TREE_COLLECTOR_FREEZE_SHA256=c8f457b589b6554a33921965339a74db086806d9243bb5fa4565df39b5e74ada
AUTHORITATIVE_PACKET_TREE_RESULT_SHA256=db755121a38ffa43587662337bf896196a944bdaaf0019e899c13bc0afb43045
AUTHORITATIVE_PACKET_TREE_COLLECTOR_EXECUTED=false
AUTHORITATIVE_PACKET_TREE_PACKET_CONTENT_READ_BYTES=0
AUTHORITATIVE_PACKET_TREE_DISPOSITION_CONTENT_READ_BYTES=0
```

The collector hash, size and mode reproduce the §18.28.1 binding. Its immutable
`directory_fingerprint()` implementation and the already frozen P0 result bind the
recipe below to packet tree
`491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5`.
No collector, packet member, disposition member, runtime byte or retained source was
executed or modified during derivation.

#### 18.38.2 Exact 902-member input packet-tree recipe

Let `root` be the exact immutable `INPUT_PACKET_ROOT` from §18.34.4. Enumerate every
strict descendant of `root`; the root itself is not a row. Include every directory
and regular file, including `provenance-lock-manifest.json`. Use `lstat` semantics and
reject symlinks, hard-linked regular files, special files, path escapes, duplicate
relative paths or a member that changes type, mode, size or content during the one
governed pass. A relative path is the POSIX `/`-separated path from `root`, with no
leading or trailing slash, empty segment, `.`, `..`, backslash or NUL. Sort the rows
by the raw UTF-8 bytes of that relative-path string.

Each directory row has exactly three keys and no `size` or `sha256` member, including
no JSON-null placeholder:

```json
{"mode":"0555","path":"objects","type":"directory"}
```

Each regular-file row has exactly five keys:

```json
{"mode":"0444","path":"objects/sha256/00/<64-lowercase-hex>","sha256":"<64-lowercase-hex>","size":123,"type":"file"}
```

`path`, `mode`, `type` and `sha256` are JSON strings; `size` is a nonnegative JSON
integer. `type` is exactly `directory` or `file`. Mode is exactly
`f"{stat.S_IMODE(st_mode):04o}"`. The file digest is the unprefixed lowercase SHA-256
of all raw file bytes consumed by that file's sole content stream. A prefixed digest,
directory digest/size, unknown key, missing key, wrong scalar type, writable mode or
unlisted member is `PAUSE`.

Encode the complete sorted row array exactly as Python
`json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
allow_nan=False).encode("utf-8")`. There is no BOM, indentation, extra whitespace or
trailing LF. `packet_tree_sha256` is the unprefixed lowercase SHA-256 of those exact
array bytes. The packet root's required mode `0555` is verified separately and is not
a row. `packet_bytes` is the sum of regular-file sizes only.

The frozen identity therefore closes at exactly 663 regular-file rows—651 object
files plus the twelve packet files—and 239 directory rows, for 902 strict descendants.
The final regular-file-size sum is exactly 654,147,403 and the final tree digest is
exactly `491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5`.
Missing, extra or differently typed rows are `PAUSE`; count and byte equality never
substitute for tree-hash equality.

#### 18.38.3 Single-pass adoption and authority boundary

The future v4 source implements the recipe from this reviewed section; it does not
import, copy, patch or execute the frozen collector. During `author-packet`, each
regular input file remains opened for content at most once. Its retained relative
path, mode, size and streaming digest feed both canonical parsing and the tree rows.
Directory metadata enumeration does not consume a content pass. Reopening a regular
file to reproduce the tree, relying on `Path.is_file()` after `lstat`, following a
link, accepting a changed inode/link count, or hashing a second serialization is
`PAUSE` before output creation.

The synthetic baseline must exercise this exact production tree builder against its
in-memory packet adapter and compare against an independently precomputed fixture
identity. The baseline is nonzero on any root-inclusion, row-key, type, mode, digest-
prefix, ordering, JSON-encoding or final-LF drift. This closes an input identity
required by the existing production path; it adds no control ID and does not change
`W001`–`W042`, `F001`–`F010`, either argv, either cwd, the nine-key command contract,
the shared `load -> derive -> validate -> serialize` core, the six freeze roles, the
seven output roles, the two synthetic predecessor identities, the two ledger nulls,
fixed-point sizing, process/RSS/write/read ceilings or the later real-run transaction.
There is no `F011`.

The only admissible next sequence is exact-tip Kiro review, a new Ryan two-SHA grant
naming the still-absent v4 roots and this closed recipe, one synthetic process,
external return of the six identities plus ledger/result counters, then plan-only
result binding and Kiro capability review. Neither the stopped execution grant nor
the bounded derivation grant authorizes that process.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no v4 root/file creation or execution, packet/disposition
content read, work-item root/result creation, network, subprocess, retained-source or
runtime read, acquisition, ownership/license selection, binary repair, build,
publication, CI admission, product/test/config/R2b change, implementation, PR `#342`
update, PR creation, merge, deployment, real OpenClaw, live data, watch activation,
promotion or Gate D/W/D-V/E/F action.

### 18.39 V4 interpreter startup-isolation correction

Kiro passed the exact §18.38/§10.36 packet-tree recipe overlay at
`991f48866fcee52149211df3e70bac5d58acfb43`. Ryan then granted only the fresh v4
synthetic capability freeze. Before creating either v4 root, writing the author or
starting Python, Astra's final startup-dependency preflight proved that the literal
reviewed argv would execute a global site-package hook before the author could
install its audit boundary or validate the dependency manifest. The preflight stopped
without consuming either single-assignment root or the one-process allowance.

#### 18.39.1 Exact stopped state and startup proof

```text
WORK_ITEM_AUTHOR_STARTUP_ISOLATION_PLAN_BASE_OVERLAY_SHA=991f48866fcee52149211df3e70bac5d58acfb43
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STARTUP_PREFLIGHT_STATUS=PAUSE
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STARTUP_PREFLIGHT_ROOT_CREATED=false
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STARTUP_PREFLIGHT_AUTHOR_CREATED=false
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STARTUP_PREFLIGHT_PROCESS_COUNT=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STARTUP_PREFLIGHT_WRITTEN_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STARTUP_PREFLIGHT_REAL_INPUT_READ_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STARTUP_PREFLIGHT_PACKET_CONTENT_READ_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STARTUP_PREFLIGHT_DISPOSITION_CONTENT_READ_BYTES=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STARTUP_PREFLIGHT_NETWORK_REQUESTS=0
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_AUTHORIZED=false
PROVENANCE_WORK_ITEM_AUTHORING_AUTHORIZED=false
```

Both §18.34 v4 coordinates remain absent and single-assignment. No author, fixture,
receipt, manifest, control result, dependency closure or freeze identity exists. The
stopped grant is not reusable.

The interpreter binding itself remains exact: literal path
`/home/lauer/miniforge3/bin/python3`, version `3.13.12`, dereferenced executable size
`32,959,480` and SHA-256
`66c90902aba57b52abbe5e31e54fe65826c2046496f1656ef0f4e9d1ea26c8b0`.
The defect is the default startup path around that executable:

```text
STARTUP_HOOK_PATH=/home/lauer/miniforge3/lib/python3.13/site-packages/distutils-precedence.pth
STARTUP_HOOK_SHA256=2638ce9e2500e572a5e0de7faed6661eb569d1b696fcba07b0dd223da5f5d224
STARTUP_HOOK_SIZE=151
STARTUP_HOOK_MODE=0644
STARTUP_SITE_PATH=/home/lauer/miniforge3/lib/python3.13/site.py
STARTUP_SITE_SHA256=ea80b1f9fd676ec6d0c3ce8219d1ecfd103992e93e927c5d0a95a18443059f66
STARTUP_SITE_SIZE=25556
STARTUP_DISTUTILS_HACK_PATH=/home/lauer/miniforge3/lib/python3.13/site-packages/_distutils_hack/__init__.py
STARTUP_DISTUTILS_HACK_SHA256=df81e6bcba34ee3e3952f776551fb669143b9490fdd6c4caeb32609f97e985b4
STARTUP_DISTUTILS_HACK_SIZE=6755
STARTUP_HOOK_EXECUTED=false
```

The hook's exact line sets `enabled` when
`SETUPTOOLS_USE_DISTUTILS` is absent or equals `local`, then imports
`_distutils_hack` and calls `add_shim()`. The frozen five-key environment omits that
variable. The bound standard-library `site.py` calls global `addsitepackages()` and
executes import-prefixed `.pth` lines unless `sys.flags.no_site` is set.
`PYTHONNOUSERSITE=1` disables only the user site and does not suppress this global
hook. Therefore the old thirteen- and nineteen-member argv arrays would import a
third-party package before the author's first instruction, contradicting the
standard-library-only dependency closure. No Python process was started to prove a
condition already established from the bound startup bytes.

#### 18.39.2 Closed no-site command vectors

The successor changes only interpreter startup isolation. Insert literal `-S`
immediately after the interpreter in both §18.37.2 argv vectors. The command-contract
schema and exact nine-key set remain unchanged. The synthetic `argv` is now this exact
fourteen-member string array:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/work-item-author-v4.py",
  "synthetic-freeze",
  "--fixture-spec",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/fixture-spec.json",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4.partial/freeze-manifest.json"
]
```

The synthetic cwd remains the exact v4 partial root. The held
`author_packet_argv` is now this exact twenty-member string array:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4/work-item-author-v4.py",
  "author-packet",
  "--input-packet-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet",
  "--input-disposition",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json",
  "--staging-root",
  "/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--durable-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4/freeze-manifest.json"
]
```

The held real cwd remains the sealed v4 final root. No `-I`, `-s`, environment
override, `PYTHONPATH`, wrapper, module hiding or site-package mutation is admitted.
The exact five-key environment stays unchanged. The literal `-S` is an interpreter
option, not an author argument; the author path and verb therefore shift one argv
position without changing the author's own flag grammar.

#### 18.39.3 Startup invariant, `F002` shift and authority boundary

The governed source imports built-in `sys` first and requires
`sys.flags.no_site == 1` before importing any file-backed module or creating any
output. Its complete `sys.modules` dependency closure must omit `site` and
`_distutils_hack`, and every non-null module origin other than the independently
hashed author must resolve outside `site-packages` and `dist-packages`. A false
`no_site` flag, either forbidden module, a site-package origin, execution of any
`.pth` line or a dependency row outside the standard library is `PAUSE`. This is a
clean-baseline and dependency-closure invariant; it changes no JSON schema and adds
no control ID.

The sole `F002` representative retains the same semantic pair-order mutation. Because
`-S` shifts the author and verb by one position, it now exchanges complete zero-based
real-argv slices `[4:6]` and `[6:8]`. It preserves all twenty strings and array length,
changes only the packet-root/disposition pair order, and must still return exactly
`["F002"]` before content access or output creation. `F001` and `F003`–`F010` retain
their meanings; there is no second `F002`, `F011`, combined mutant or new exception.

Every §18.34–§18.38 root, source design, schema, parser, serializer, packet-tree
recipe, mapping, cardinality, identity adapter, six freeze roles, seven output roles,
`W001`–`W042`, `F001`–`F010`, write-ledger rule, exactly two null hashes, fixed-point
sizing, process/RSS/write/read ceiling and later real-run transaction remains
unchanged. The only admissible next sequence is Kiro exact-tip review, a fresh Ryan
two-SHA grant naming the still-absent v4 roots and these isolated argv vectors, one
synthetic process, external return of the six identities plus ledger/result counters,
then plan-only result binding and Kiro capability review. No prior grant is reusable.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no v4 root/file creation or execution, packet/disposition
content read, work-item root/result creation, network, subprocess, retained-source or
runtime read, acquisition, ownership/license selection, binary repair, build,
publication, CI admission, product/test/config/R2b change, implementation, PR `#342`
update, PR creation, merge, deployment, real OpenClaw, live data, watch activation,
promotion or Gate D/W/D-V/E/F action.

### 18.40 V4 row-zero durability freeze-retry correction

PR `#351` squash-merged the reviewed §§18.31–18.39 work-item author contract at
`a3b56abd3b5fa3fafe1b3f32de744bba3eb9772c`, and Kiro returned exact-main PASS.
PR `#352` then merged the descriptive current-state snapshot at
`0f84b4a983f9c1a367bc6e790d109c4342560653`. Ryan separately granted one fresh v4
synthetic freeze under the exact §18.39 no-site contract. The one process exited zero,
passed its clean baseline and all 52 controls, stayed inside its write/RSS ceilings and
sealed six files atomically. Post-run inspection nevertheless found that the external
setup which created ledger row zero did not explicitly prove a file `fsync` before the
process created ledger row one. The reviewed §18.35.2 transaction requires every
regular-file event, including the setup-created author, to be flushed and `fsync`ed
before the next row. Acceptance therefore remains `PAUSE` even though every payload
identity and process counter reproduced.

#### 18.40.1 Exact sealed PAUSE evidence

```text
WORK_ITEM_AUTHOR_ROW_ZERO_DURABILITY_PLAN_BASE_MAIN_SHA=0f84b4a983f9c1a367bc6e790d109c4342560653
WORK_ITEM_AUTHOR_ROW_ZERO_DURABILITY_REVIEWED_OVERLAY_SHA=fdf09017b1898a6ba4eabce127a3c34374feee22
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_STATUS=PAUSE
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_PROCESS_EXIT_STATUS=0
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/59ae444ea3f021c4807be82a0114c1a4d8558602/v4
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_PARTIAL_ROOT_PRESENT=false
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_TREE_SHA256=f6936649147140d2a9ee1da53284a2e8a1159e24a5f7aba3b2b2d62cec9c825f
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_MEMBER_COUNT=6
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_TOTAL_PERSISTED_BYTES=144330
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_ROOT_MODE=0555
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_MEMBER_MODE=0444
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_COUNT=52
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROLS_PASSED=52
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_BASELINE_VIOLATION_COUNT=0
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_WRITE_LEDGER_EVENT_COUNT=22
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_WRITE_LEDGER_NULL_DIGEST_COUNT=2
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_WRITE_LEDGER_SHA256=2c60f635797baaa5be654c6605e0ca1b369fc71396df560a92ad6ad2a74f3f33
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_FORECAST_WRITTEN_BYTES=333949322
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_OBSERVED_WRITTEN_BYTES=333949322
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_PEAK_RSS_BYTES=1804357632
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_FIXED_POINT_ITERATIONS=3
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_SYNTHETIC_RESULT_SIZE=4053
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_SYNTHETIC_RESULT_SHA256=b7a490a2700a45e69fd9871250ae918df3f749337e753a216df82ce221818dd3
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_SYNTHETIC_PACKET_TREE_SHA256=0625e41dced1b209c7c5c029d629f96a7776e74455c5aaa955fb254f405d6530
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_SYNTHETIC_INPUT_TREE_SHA256=96f62d3d37235655952c19da31e8c8a7365c04bee00d42911920d7173071a6ac
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_SYNTHETIC_INPUT_TREE_MEMBER_COUNT=902
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_DEPENDENCY_ROW_COUNT=76
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_ROW_ZERO_PRELAUNCH_FILE_FSYNC_PROVED=false
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_ROW_ZERO_PRELAUNCH_DIRECTORY_FSYNC_PROVED=false
REJECTED_WORK_ITEM_AUTHOR_FREEZE_V4_ACCEPTED=false
```

The sealed root contains exactly these single-link mode-`0444` regular files under a
mode-`0555` directory:

| File | Size | SHA-256 |
|---|---:|---|
| `work-item-author-v4.py` | 95,560 | `6b8027326657d1907d3b51af88bc60202cbe06f74f4b4026e5a6e7a52a736d2d` |
| `fixture-spec.json` | 476 | `d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f` |
| `dependency-manifest.json` | 10,921 | `b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63` |
| `command-contract.json` | 3,544 | `58e9c3254adfeea701334f892c2c78b646764840348e599bd90efbb0d93234ab` |
| `self-test-receipt.json` | 32,861 | `e0a15635de53a269213eb639d87a0e162fb4601e0ab0fb7465d503fa97182b33` |
| `freeze-manifest.json` | 968 | `fa54c86c25cbf17321268d0e99a339353e5745879660c72c74927d4079561a81` |

Read-only verification reproduced every member size/hash/mode, the 22-event ledger
with exactly two null digests, `52/52` controls, zero baseline violations and 76
dependency rows without `site`, `_distutils_hack`, `site-packages` or `dist-packages`
origins. Forecast and observed writes both equal 333,949,322 and remain below
1,073,741,824; peak RSS remains below 2,147,483,648. Process, subprocess, network,
real-input, repository, runtime, retained-source, acquisition and credential counters
are all zero. No real `author-packet` command ran.

The root is immutable rejected evidence. It may not be changed, chmodded, deleted,
renamed, copied, hard-linked, used as a source, accepted, repaired or reinterpreted.
Its successful controls prove only the bytes and behavior they actually observed;
they do not cure the missing row-zero durability transition.

#### 18.40.2 Exact durability gap

The external setup created `work-item-author-v4.py` once, checked its size and digest,
then launched the one reviewed process. The frozen author validates row-zero type,
link count, size and bytes. Its governed writer exclusively creates events 1–21 and
calls file `fsync` before advancing each event. Before the final rename it also calls
`fsync` on the partial directory. None of those later actions proves that row zero's
regular-file bytes were flushed before event 1: directory `fsync` persists directory
metadata and cannot substitute for file `fsync`; re-reading and hashing bytes cannot
establish the missing durability ordering. No after-the-fact `sync`, reopen, chmod,
receipt rewrite or review assertion can repair that historical sequence.

The accepted retry must therefore make the transition occur inside the sole governed
process before any event-1 directory or regular-file creation. This is a transaction-
ordering correction, not a new file role, schema inference or acceptance exception.

#### 18.40.3 Fresh retry coordinates and closed row-zero transition

```text
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_AUTHORIZED=false
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4.partial
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_MAX_PROCESS_COUNT=1
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_MAX_TOTAL_WRITTEN_BYTES=1073741824
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_MAX_PEAK_RSS_BYTES=2147483648
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_REAL_INPUT_READ_BYTES=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_NETWORK_REQUESTS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_RUNTIME_READS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_RETAINED_SOURCE_READS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_SUBPROCESSES=0
```

Both proposed roots were absent when this correction was authored and are new single-
assignment coordinates. Pre-existence at a future grant is `PAUSE`. The executor may
construct a new source only from the reviewed plan; it may not copy, patch, import or
execute the rejected v4 source. Before launch it may create only the partial directory
and row-zero author. Setup must use exclusive creation, complete one write, verify the
write count, set mode `0644`, call file `fsync`, close the descriptor, call `fsync` on
the partial directory, then re-open without following links and verify type, link
count, mode, size and SHA-256. Every operation must succeed before process creation.

The governed source must import built-in `sys` first, prove `sys.flags.no_site == 1`
and install the existing audit boundary. Before any event-1 directory or regular-file
creation, it must open its own row-zero path without following links, revalidate the
same type/link/mode/size/hash, call file `fsync` successfully, close it and call
`fsync` successfully on the partial directory. Only then may the existing writer
advance to ledger event 1. The external result adds exactly these nonnegative scalar
counters without changing a frozen file schema:

```text
row_zero_setup_file_fsync_count=1
row_zero_setup_directory_fsync_count=1
row_zero_governed_file_fsync_count=1
row_zero_governed_directory_fsync_count=1
row_zero_event_one_write_count_after_governed_fsync=1
```

Any missing, repeated, failed or reordered transition; any event-1 directory or file
creation before both governed `fsync` calls; any extra setup file; or any mismatch in
row-zero bytes/metadata is `PAUSE`. Failure preserves the new partial root without
repair, deletion, completion or retry. There is no in-place remedy and no acceptance
transfer from the rejected root.

The retry command contract retains exactly nine keys and the five-key environment.
It changes only the fresh literal root paths required by single assignment. The exact
synthetic argv is:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4.partial/work-item-author-v4.py",
  "synthetic-freeze",
  "--fixture-spec",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4.partial/fixture-spec.json",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4.partial/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4.partial/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4.partial/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4.partial/freeze-manifest.json"
]
```

The exact held real argv is:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4/work-item-author-v4.py",
  "author-packet",
  "--input-packet-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet",
  "--input-disposition",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json",
  "--staging-root",
  "/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--durable-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4/freeze-manifest.json"
]
```

The synthetic cwd is the new partial root and the held real cwd is the new final root.
The sole `F002` representative still swaps complete real-argv slices `[4:6]` and
`[6:8]`. It preserves all twenty values and length and must return exactly `F002`
before content access or output creation. No alias, implicit coordinate, caller choice,
environment override, second `F002`, `F011` or combined mutant is admitted.

#### 18.40.4 Frozen surrounding contract and authority boundary

Every §18.31–§18.39 schema, mapping, candidate/locator rule, parser, serializer,
identity adapter, packet-tree recipe, synthetic predecessor identity, cardinality,
six freeze roles, seven output roles, 22-event ledger shape, exactly two null digests,
fixed-point rule, `W001`–`W042`, `F001`–`F010`, one-process/2-GiB RSS/1-GiB synthetic
ceilings, zero-access boundary and held later real-run transaction remains unchanged.
The correction changes only the fresh literal root paths and closes the row-zero file/
directory `fsync` ordering before event 1. `F010` remains the transaction-drift code;
there is no new control ID or exception.

The only admissible next sequence is Kiro exact-tip review of this correction, a new
Ryan two-SHA grant naming the fresh roots and exact row-zero transition, one synthetic
process, external return of the six identities plus ledger/result/durability counters,
then plan-only result binding and Kiro capability review. The rejected root and every
prior grant are non-reusable.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no retry-root creation, source write, freeze execution,
packet/disposition/repository/runtime/retained-source read, work-item packet/result,
network, subprocess, acquisition, ownership/license selection, binary repair, build,
publication, CI admission, product/test/config/R2b change, implementation, PR `#342`
update, PR creation, merge, deployment, real OpenClaw, live data, watch activation,
promotion or Gate D/W/D-V/E/F action.

### 18.41 V4 coordinate-parent durability-audit correction

PR `#353` squash-merged the reviewed row-zero durability correction at
`073b19b1871203d50edb84ad845530441a4ba8d4`, Kiro returned exact-main PASS and PR
`#354` merged the descriptive snapshot at
`6de8845473e09742bcf5a44b2da22a285ed77570`. Ryan then issued one exact two-SHA
grant for the fresh `fdf09017…/v4.partial` and sibling final roots. External setup
exclusive-created the row-zero author, completed one write, file-`fsync`, close and
partial-directory `fsync`, and verified the exact bytes before launching the sole
no-site process. The process reached final publication after producing and sealing all
six freeze members, but exited one when its own audit hook rejected the required open
of the coordinate parent directory for the pre-rename durability `fsync`.

The failure is fail-closed. No final root exists, no external PASS result was emitted
and the consumed partial is immutable rejected evidence. The synthetic baseline,
controls and write ledger are useful diagnostic evidence only; they do not authorize
acceptance, repair or retry.

#### 18.41.1 Exact sealed PAUSE evidence

```text
WORK_ITEM_AUTHOR_COORDINATE_PARENT_AUDIT_PLAN_BASE_MAIN_SHA=6de8845473e09742bcf5a44b2da22a285ed77570
WORK_ITEM_AUTHOR_COORDINATE_PARENT_AUDIT_REVIEWED_OVERLAY_SHA=b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_STATUS=PAUSE
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_SETUP_STATUS=PASS
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_PROCESS_EXIT_STATUS=1
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_EXCEPTION=RuntimeError: forbidden open
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_FAILURE_STAGE=COORDINATE_PARENT_FSYNC_BEFORE_FINAL_RENAME
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_ROOT_PRESENT=false
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22/v4.partial
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_PARTIAL_ROOT_PRESENT=true
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_PARTIAL_TREE_SHA256=a9ceaa06945c17d588bb1ec66a17184c2f2df0612cc947a703cce61d70e0093d
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_MEMBER_COUNT=6
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_TOTAL_PERSISTED_BYTES=97757
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_ROOT_MODE=0555
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_MEMBER_MODE=0444
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_AUTHOR_SIZE=52513
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_AUTHOR_SHA256=26dcc5f1c5641597912f35f42c5f3dc5705fce0c8cd16d78a3186a68d53c8a57
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_ROW_ZERO_SETUP_FILE_FSYNC_COUNT=1
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_ROW_ZERO_SETUP_DIRECTORY_FSYNC_COUNT=1
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_CONTROL_COUNT=52
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_CONTROLS_PASSED=52
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_BASELINE_VIOLATION_COUNT=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_WRITE_LEDGER_EVENT_COUNT=22
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_WRITE_LEDGER_NULL_DIGEST_COUNT=2
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_WRITE_LEDGER_SHA256=993ddf3b65b54f18f6d432d962c88925c6b61c2902b22eceb7bf0eb09f8be271
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_FORECAST_WRITTEN_BYTES=356219589
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_OBSERVED_WRITTEN_BYTES=356219589
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_DEPENDENCY_ROW_COUNT=58
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_REAL_INPUT_READ_BYTES=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_NETWORK_REQUESTS=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_RUNTIME_READS=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_RETAINED_SOURCE_READS=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_SUBPROCESSES=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_EXTERNAL_RESULT_EMITTED=false
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_RETRY_ACCEPTED=false
```

The preserved partial contains exactly these single-link mode-`0444` regular files
under a mode-`0555` directory:

| File | Size | SHA-256 |
|---|---:|---|
| `work-item-author-v4.py` | 52,513 | `26dcc5f1c5641597912f35f42c5f3dc5705fce0c8cd16d78a3186a68d53c8a57` |
| `fixture-spec.json` | 476 | `d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f` |
| `dependency-manifest.json` | 7,513 | `67e6cedcb5aa364f28312864c02cbe03ab42b8a63c1bcbc3ee7b135fbb6b7b94` |
| `command-contract.json` | 3,544 | `7b2d7b7e5c671a1dbaa2a0a08f063184ae8211e479c9c58afaf0408504b9c2d3` |
| `self-test-receipt.json` | 32,735 | `218bca1d11a607f521c6bdc61eaf286581e86e8d9a3db67e66a54cbab01142b8` |
| `freeze-manifest.json` | 976 | `3b6ad9d3d989e1f512fc73ddbece0c2530784039e8ec3acc86ece6188e9514be` |

Read-only verification reproduced every member size, hash, mode and link count, the
canonical six-row partial-tree digest, the clean baseline, all `W001`–`W042` and
`F001`–`F010` receipts, and the 22-event ledger with exactly two null digests.
Forecast and observed writes both equal 356,219,589 and remain below the unchanged
1,073,741,824-byte ceiling. The receipt records zero real-input, network, runtime,
retained-source and subprocess access. Because the process failed before external
result emission, no peak-RSS or final-root identity is accepted or inferred.

The partial may not be changed, chmodded, deleted, renamed, copied, hard-linked,
imported, executed, used as source, accepted, repaired or reinterpreted. Its setup and
governed work consumed the grant and coordinate. There is no in-place remedy and no
acceptance transfer from either rejected v4 attempt.

#### 18.41.2 Exact failure and rejected broad fix

The frozen source's ordinary path predicate admits the partial root, final root,
packet/disposition inputs, output roots, interpreter directory and standard-library
directory. It does not admit the shared coordinate parent
`/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/fdf09017b1898a6ba4eabce127a3c34374feee22`.
Finalization calls `fsync_dir(os.path.dirname(PARTIAL))` before rename. That helper
uses `os.open`, which emits the audited `open` event; the audit hook therefore raised
`RuntimeError("forbidden open")` before rename. The sibling final remained absent and
the already sealed partial remained present.

Adding the coordinate parent to the ordinary prefix-based path roots is forbidden: it
would admit every descendant, including unreviewed siblings and files outside the
partial/final roots. Disabling the audit hook, accepting the sealed partial, omitting
either parent-directory `fsync`, moving the rename outside the governed process,
using a wrapper, inheriting a caller-opened directory descriptor or treating later
inspection as durability proof are also forbidden. The correction must keep ordinary
content-path authority byte-for-byte closed and add only an exact directory-handle
exception for the two publication barriers.

#### 18.41.3 Fresh coordinates and closed directory-only exception

```text
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_AUTHORIZED=false
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_COORDINATE_PARENT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288/v4.partial
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288/v4
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_MAX_PROCESS_COUNT=1
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_MAX_TOTAL_WRITTEN_BYTES=1073741824
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_MAX_PEAK_RSS_BYTES=2147483648
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_REAL_INPUT_READ_BYTES=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_NETWORK_REQUESTS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_RUNTIME_READS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_RETAINED_SOURCE_READS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_PARENT_FSYNC_RETRY_SUBPROCESSES=0
```

The coordinate parent and both children were absent when this correction was authored.
They are fresh single-assignment coordinates; pre-existence of any one at a future
grant is `PAUSE`. Setup retains the exact §18.40 row-zero transaction and may create
only the coordinate parent, partial directory and plan-derived author. The source must
be written fresh from the reviewed plan and may not copy, patch, import or execute a
rejected author.

The governed source defines one canonical `coordinate_parent` equal to both
`dirname(partial_root)` and `dirname(final_root)`. The ordinary prefix-based path
predicate remains unchanged and must continue to reject that parent as a general
content root. The audit hook may admit an `open` of the coordinate parent only when
all of these conditions hold:

1. the canonical path equals `coordinate_parent` exactly, never by prefix;
2. the flags are exactly `O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW` and the
   event carries no file-creation, write, truncate or content-read mode;
3. internal publication state is exactly `BEFORE_FINAL_RENAME` or
   `AFTER_FINAL_RENAME`;
4. each state admits exactly one open, one successful directory `fsync` and one close;
5. no directory enumeration, child lookup, path fallback, inherited descriptor or
   caller-selected coordinate is permitted.

After verifying the six final members and completing the existing partial-directory
flush and mode transition, the process enters `BEFORE_FINAL_RENAME`, performs the
first exact coordinate-parent open/`fsync`/close, and returns to a closed state. It
then performs the one atomic rename from the partial root to the sibling final root,
enters `AFTER_FINAL_RENAME`, performs the second exact coordinate-parent
open/`fsync`/close and returns to a closed state before emitting the external result.
The result adds exactly these scalar counters:

```text
coordinate_parent_pre_rename_open_count=1
coordinate_parent_pre_rename_fsync_count=1
coordinate_parent_post_rename_open_count=1
coordinate_parent_post_rename_fsync_count=1
```

Any missing, repeated, reordered or extra parent open/`fsync`; wrong flags; path or
state mismatch; content read; enumeration; alternate parent; rename before the first
barrier; result emission before the second barrier; or audit rejection is `PAUSE`.
Failure before rename preserves the partial; failure after rename preserves the final
coordinate as rejected evidence. Neither state may be repaired, renamed back,
deleted, completed or retried. `F010` remains the sole transaction-drift control and
must reject every such mutation before acceptance; there is no `F011` or exception.

The command contract retains exactly nine keys, the five-key environment, literal
`-S`, the fourteen-member synthetic argv and twenty-member held real argv. Only the
fresh freeze coordinate changes. The synthetic argv is:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288/v4.partial/work-item-author-v4.py",
  "synthetic-freeze",
  "--fixture-spec",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288/v4.partial/fixture-spec.json",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288/v4.partial/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288/v4.partial/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288/v4.partial/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288/v4.partial/freeze-manifest.json"
]
```

The held real argv retains the exact §18.40 order and values, changing only each
`fdf09017…/v4` freeze-member path and cwd to sibling final
`b7a8ade6…/v4`. The packet, disposition, staging and durable roots remain byte-for-
byte unchanged. The sole `F002` representative still swaps complete real-argv slices
`[4:6]` and `[6:8]`, preserves all twenty values and length, and must return exactly
`F002` before content access or output creation.

#### 18.41.4 Frozen surrounding contract and authority boundary

Every §18.31–§18.40 schema, mapping, candidate/locator rule, parser, serializer,
identity adapter, packet-tree recipe, cardinality, six freeze roles, seven output
roles, 22-event ledger with exactly two null digests, fixed-point rule,
`W001`–`W042`, `F001`–`F010`, row-zero durability transition, one-process/2-GiB
RSS/1-GiB synthetic ceilings, zero-access boundary and held later real-run contract
remains unchanged. This correction changes only the fresh freeze coordinate and the
exact directory-only audit transition required to persist the atomic rename. It adds
no file role, sidecar, wrapper, content read, control ID or acceptance exception.

The only admissible next sequence is Kiro exact-tip review of this correction, a new
Ryan two-SHA grant naming the fresh roots and exact parent-directory transition, one
synthetic process, external return of the six identities plus ledger/result/row-zero/
parent-durability counters, then plan-only result binding and Kiro capability review.
Both rejected v4 roots and every prior grant are non-reusable.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no retry coordinate/root/file creation, source write, freeze
execution, packet/disposition/repository/runtime/retained-source read, work-item
packet/result, network, subprocess, acquisition, ownership/license selection, binary
repair, build, publication, CI admission, product/test/config/R2b change,
implementation, PR `#342` update, PR creation, merge, deployment, real OpenClaw,
live data, watch activation, promotion or Gate D/W/D-V/E/F action.

### 18.42 V4 standard-library dependency-link freeze-retry correction

PR `#355` squash-merged the reviewed coordinate-parent correction at
`8e4bb2b704ea858301207c21b71427df4975b889`, Kiro returned exact-main PASS and PR
`#356` merged the descriptive snapshot at
`30052061942c4c016fcb305946444c0453046cb1`. Ryan then issued one exact two-SHA
grant for the fresh `b7a8ade6…/v4.partial` and sibling final roots. External setup
exclusive-created the coordinate parent and row-zero author, completed one write,
file-`fsync`, close and partial-directory `fsync`, and verified the exact bytes before
launching the sole no-site process. The process exited one before any JSON or
disposable output write because the dependency reader rejected one canonical
standard-library extension module whose regular-file inode has link count two.

The failure is fail-closed. No final root, receipt, manifest or external result exists.
The consumed partial contains only the fresh author and is immutable PAUSE evidence
by authority. It is not an author source, a capability freeze or acceptance evidence.

#### 18.42.1 Exact one-file PAUSE evidence

```text
WORK_ITEM_AUTHOR_STDLIB_LINK_PLAN_BASE_MAIN_SHA=30052061942c4c016fcb305946444c0453046cb1
WORK_ITEM_AUTHOR_STDLIB_LINK_REVIEWED_OVERLAY_SHA=816b713adac7f987efa282380b892ab03994fbed
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_STATUS=PAUSE
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_SETUP_STATUS=PASS
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_PROCESS_EXIT_STATUS=1
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_EXCEPTION=RuntimeError: not single-link regular file: /home/lauer/miniforge3/lib/python3.13/lib-dynload/_blake2.cpython-313-x86_64-linux-gnu.so
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_FAILURE_STAGE=DEPENDENCY_MANIFEST_COLLECTION
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_COORDINATE_PARENT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288/v4
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_ROOT_PRESENT=false
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/b7a8ade6a5acd80c09ab627ad2bb7ffcebe81288/v4.partial
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_PARTIAL_ROOT_PRESENT=true
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_PARTIAL_ROOT_MODE=0755
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_PARTIAL_MEMBER_COUNT=1
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_JSON_MEMBER_COUNT=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_PARTIAL_TREE_SHA256=99e4939d367cb9440e902c2cb29211508c2d5e17bb031de69e544af86e29c13f
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_AUTHOR_MODE=0644
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_AUTHOR_LINK_COUNT=1
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_AUTHOR_SIZE=70266
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_AUTHOR_SHA256=57ecd07bd142dc33569ed6a2f92309fc577f93c6daecd5f9876f8162a2e4eca3
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_ROW_ZERO_SETUP_FILE_FSYNC_COUNT=1
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_ROW_ZERO_SETUP_DIRECTORY_FSYNC_COUNT=1
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_REAL_INPUT_READ_BYTES=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_NETWORK_REQUESTS=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RUNTIME_READS=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETAINED_SOURCE_READS=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_SUBPROCESSES=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_EXTERNAL_RESULT_EMITTED=false
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_ACCEPTED=false
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_DEPENDENCY_PATH=/home/lauer/miniforge3/lib/python3.13/lib-dynload/_blake2.cpython-313-x86_64-linux-gnu.so
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_DEPENDENCY_MODE=0775
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_DEPENDENCY_LINK_COUNT=2
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_DEPENDENCY_SIZE=398208
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_DEPENDENCY_SHA256=73da16b0b8a13515b59fa651d63e675cf213f09dc1696d2b8f91889bd262367d
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_DEPENDENCY_DEVICE=66306
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_DEPENDENCY_INODE=18621870
```

The one-row partial tree uses the existing compact sorted-key UTF-8 JSON grammar over
`{path,mode,size,sha256}`; its canonical bytes are 138 bytes and hash to
`99e4939d…`. The stopped process wrote no JSON member and left no receipt, manifest or
final root. No packet, disposition, repository, runtime or retained-source byte was
read; no network request or subprocess occurred. These are stopped-run facts, not an
accepted result.

The coordinate parent, partial root, author and grant are consumed. They may not be
changed, chmodded, deleted, renamed, completed, copied, hard-linked, imported,
executed, used as source, accepted, repaired or reinterpreted. There is no in-place
remedy and no acceptance transfer from any earlier v4 attempt.

#### 18.42.2 Exact overconstraint and rejected broad fixes

The reviewed dependency-manifest contract records each imported module as exactly
`{name,kind,path,size,sha256}`. It binds the canonical absolute module origin under
the frozen standard-library root; it does not make inode link count part of module
identity. The fresh author nevertheless reused the single-link evidence predicate
when hashing that origin. The canonical `_blake2` origin is a regular file and stayed
at one bound path, size and digest, but its inode has `st_nlink=2`; the reused
predicate therefore raised before the dependency manifest could be serialized.

The correction must not remove no-follow opens, admit a symlink, search for or read an
alternate hard-link name, enumerate aliases, normalize a different origin, admit a
module outside the canonical standard-library root, admit `site-packages` or
`dist-packages`, add a dependency-manifest field, or relax any packet/output/freeze/
root/evidence single-link rule. A blanket `st_nlink >= 1` change in the common evidence
reader, a caller override, an allowlist of observed inodes, a copied dependency, a
wrapper, or accepting the stopped partial is forbidden.

#### 18.42.3 Fresh coordinates and deep dependency-reader boundary

```text
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_AUTHORIZED=false
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_COORDINATE_PARENT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/816b713adac7f987efa282380b892ab03994fbed
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/816b713adac7f987efa282380b892ab03994fbed/v4.partial
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/816b713adac7f987efa282380b892ab03994fbed/v4
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_MAX_PROCESS_COUNT=1
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_MAX_TOTAL_WRITTEN_BYTES=1073741824
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_MAX_PEAK_RSS_BYTES=2147483648
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_REAL_INPUT_READ_BYTES=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_NETWORK_REQUESTS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_RUNTIME_READS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_RETAINED_SOURCE_READS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_STDLIB_LINK_RETRY_SUBPROCESSES=0
```

The coordinate parent and both children were absent when this correction was authored.
They are fresh single-assignment coordinates; pre-existence of any one at a future
grant is `PAUSE`. Setup retains the exact §18.40 row-zero transaction and the sole
process retains the exact §18.41 coordinate-parent barriers. The author must be
written fresh from the reviewed plan and may not copy, patch, import or execute the
failed author.

One deep `read_stdlib_dependency` boundary owns the sole link-count distinction. For
each already-imported module it must:

1. obtain the module's canonical absolute `__file__` origin without searching for an
   alternate path, and prove it is a strict descendant of the exact bound
   `/home/lauer/miniforge3/lib/python3.13` standard-library root while rejecting every
   `site-packages` or `dist-packages` component;
2. open that exact origin once with `O_RDONLY | O_CLOEXEC | O_NOFOLLOW`, reject a
   symlink or non-regular file, and record the first descriptor `fstat` identity;
3. accept `st_nlink >= 1` only inside this boundary, never as an assertion that other
   names are known, approved or readable;
4. hash exactly one content stream, require its byte count to equal `st_size`, then
   require the second descriptor `fstat` to preserve device, inode, file type, mode,
   link count, size, mtime-ns and ctime-ns before close; and
5. emit only the existing `{name,kind,path,size,sha256}` row using the canonical origin
   path. Link count, device and inode are validation metadata and never serialized,
   promoted to identity or exposed as authority.

Every other governed file reader keeps `st_nlink == 1`, including interpreter,
startup-isolation support, fixture/command/dependency inputs after creation, freeze
members, receipts, manifests, packet/disposition members, object members, staging/
durable outputs and external results. No alias may be enumerated, opened, hashed,
compared, copied or cited. Any canonical-path drift, forbidden path component,
open/fstat mismatch, link-count change during the stream, short/extra read, digest
drift or second content pass is `PAUSE` before output acceptance.

The synthetic baseline and every control use this same production dependency reader.
`W001`–`W042` and `F001`–`F010` retain their exact meanings; `F010` remains the sole
transaction-drift control and there is no `F011`, 53rd control, new schema field or
acceptance exception.

#### 18.42.4 Frozen surrounding contract and authority boundary

Every §18.31–§18.41 schema, mapping, candidate/locator rule, parser, serializer,
identity adapter, packet-tree recipe, cardinality, six freeze roles, seven output
roles, 22-event ledger with exactly two null digests, fixed-point rule,
`W001`–`W042`, `F001`–`F010`, fourteen-/twenty-member no-site argv, `F002` slices
`[4:6]`/`[6:8]`, row-zero durability transition, coordinate-parent barriers,
one-process/2-GiB-RSS/1-GiB-write ceilings, zero-access boundary and held later
real-run contract remains unchanged. This correction changes only the internal
standard-library dependency file-reader rule from single-link to stable regular-file
`st_nlink >= 1` under the exact canonical-origin constraints above.

The only admissible next sequence is Kiro exact-tip review of this correction, a new
Ryan two-SHA grant naming the fresh roots and exact dependency-reader boundary, one
synthetic process, external return of the six identities plus ledger/result/row-zero/
parent-durability counters, then plan-only result binding and Kiro capability review.
All rejected v4 roots and every prior grant are non-reusable.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no retry coordinate/root/file creation, source write, freeze
execution, dependency, packet, disposition, repository, runtime or retained-source
read, work-item packet/result, network, subprocess, acquisition, ownership/license
selection, binary repair, build, publication, CI admission, product/test/config/R2b
change, implementation, PR `#342` update, PR creation, merge, deployment, real
OpenClaw, live data, watch activation, promotion or Gate D/W/D-V/E/F action.

### 18.43 V4 self-test receipt control-order freeze-retry correction

Kiro passed the exact §18.42/§10.40 standard-library dependency-link correction at
`946b469e27c7eb27c198898fa330c2475bde29fa`. Ryan then granted one exact two-SHA
retry at the fresh `816b713…` coordinate. External setup completed the reviewed
row-zero transaction and the sole no-site process accepted the canonical link-count-
two `_blake2` origin through the narrow §18.42 reader. The process ran the clean
baseline and all 52 individual controls, completed the 22-event transaction and both
coordinate-parent durability barriers, atomically renamed the partial root, emitted
an external `PASS` result and exited zero.

Acceptance is nevertheless `PAUSE`. The post-run read-only check proved that
`self-test-receipt.json.controls` was serialized as `W001` through `W042` followed by
`F001` through `F010`. Section 18.32.5 requires the receipt's control rows to be
sorted by raw control-ID bytes, and §§18.34–18.42 preserve that ordering while adding
the ten `F` controls. The required complete order is therefore `F001` through `F010`
followed by `W001` through `W042`. The author validated each mutation independently
but omitted this aggregate receipt-order invariant, so its zero-violation baseline,
52/52 count and external `PASS` do not establish acceptance.

#### 18.43.1 Exact sealed PAUSE evidence

```text
WORK_ITEM_AUTHOR_CONTROL_ORDER_PLAN_BASE_OVERLAY_SHA=946b469e27c7eb27c198898fa330c2475bde29fa
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_STATUS=PAUSE
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_PROCESS_EXIT_STATUS=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_PROCESS_REPORTED_STATUS=PASS
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_ACCEPTED=false
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_COORDINATE_PARENT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/816b713adac7f987efa282380b892ab03994fbed
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/816b713adac7f987efa282380b892ab03994fbed/v4.partial
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_PARTIAL_ROOT_PRESENT=false
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/816b713adac7f987efa282380b892ab03994fbed/v4
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_ROOT_PRESENT=true
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_ROOT_MODE=0555
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_MEMBER_COUNT=6
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_MEMBER_MODE=0444
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_TREE_SHA256=d399e3561740f9f9be5cd1eab0e69f7dd788b5c1398d3f38d9e37dd18af2c37e
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_TOTAL_BYTES=109452
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_AUTHOR_SHA256=799838f975300c4430c9342d61c44e7eb21bb380c122e2843f7539f9938819a1
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_AUTHOR_SIZE=62316
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_FIXTURE_SHA256=d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_FIXTURE_SIZE=476
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_DEPENDENCY_MANIFEST_SHA256=bdcf8f3bf7c95e7f47905f8360a7beb495fa46a74f15ea4e472bacc42fc63bca
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_DEPENDENCY_MANIFEST_SIZE=9365
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_COMMAND_CONTRACT_SHA256=8dc6ef51a7fad11a8d51c05b5ce43dad8197e1e70a97f12b2e7cdb027433be3e
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_COMMAND_CONTRACT_SIZE=3544
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_SELF_TEST_RECEIPT_SHA256=8d3ecbe08de5047a5eee473cf64958479a4062f4cd235b0544cfb8a39474cb9a
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_SELF_TEST_RECEIPT_SIZE=32775
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_FREEZE_MANIFEST_SHA256=19da463aa480a6ad2241763f30a2faa0a6cd5e6dcfe4cff1fb5fb1296b197f59
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_FREEZE_MANIFEST_SIZE=976
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_WRITE_LEDGER_SHA256=a5456f8247507f88c703052dd2bec7d2c0c988ad84f45bf7bbfa118744ed7b60
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_FORECAST_WRITTEN_BYTES=302475056
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_OBSERVED_WRITTEN_BYTES=302475056
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_PEAK_RSS_BYTES=2059636736
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_BASELINE_VIOLATION_COUNT=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_CONTROL_COUNT=52
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_CONTROLS_REPORTED_PASSED=52
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_ACTUAL_FIRST_ID=W001
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_ACTUAL_FAMILY_BOUNDARY=W042,F001
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_ACTUAL_LAST_ID=F010
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_EXPECTED_FIRST_ID=F001
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_EXPECTED_FAMILY_BOUNDARY=F010,W001
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_EXPECTED_LAST_ID=W042
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_REAL_INPUT_READ_BYTES=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_NETWORK_REQUESTS=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RUNTIME_READS=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETAINED_SOURCE_READS=0
FAILED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_SUBPROCESSES=0
```

The six member identities and modes independently match the sealed final root. The
receipt records exactly 22 ledger events, exactly two null digests for
`self-test-receipt.json` and `freeze-manifest.json`, equal forecast/observed writes,
one process, zero external access and peak RSS below 2 GiB. The dependency manifest
contains the canonical `_blake2` row with size `398208` and SHA-256 `73da16b0…`, so
the §18.42 correction worked as designed. Those facts remain useful failure evidence,
but none transfers acceptance across the receipt-order defect.

The coordinate parent, sealed final root, six members, source, external result claim
and grant are consumed and immutable by authority. They may not be changed, chmodded,
deleted, renamed, copied, hard-linked, imported, executed, used as a successor source,
accepted, repaired or reinterpreted. The absent `.partial` sibling may not be
recreated. There is no in-place remedy or acceptance transfer.

#### 18.43.2 Exact ordering gap and rejected broad fixes

Raw UTF-8 ordering of the admitted ASCII IDs is executable and unambiguous:

```text
EXPECTED_SELF_TEST_CONTROL_IDS =
  [F001, F002, ..., F010, W001, W002, ..., W042]
ACTUAL_REJECTED_CONTROL_IDS =
  [W001, W002, ..., W042, F001, F002, ..., F010]
```

The failure is not a control-semantic failure: every individual row reported its own
expected and observed code, and no 53rd control or `F011` appeared. It is a closed-
receipt aggregate-validation failure. Counting 52 rows, validating the first and last
within each family, preserving insertion order, sorting families separately, relying
on canonical JSON object-key sorting, or sorting only `negative-controls.jsonl` does
not satisfy the inherited receipt rule.

The correction must not relabel IDs, change a mutation, reorder the execution of a
control to manufacture receipt order, add a receipt field, add `F011`, add a sidecar,
accept either family order, sort by numeric suffix, or treat external `PASS` as
stronger than the sealed receipt. It must not weaken any identity, dependency-reader,
write-ledger, output, durability or access invariant.

#### 18.43.3 Fresh coordinates and closed receipt validator

```text
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_STATUS=ABSENT
PROVENANCE_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_AUTHORIZED=false
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_COORDINATE_PARENT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4.partial
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_MAX_PROCESS_COUNT=1
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_MAX_TOTAL_WRITTEN_BYTES=1073741824
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_MAX_PEAK_RSS_BYTES=2147483648
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_REAL_INPUT_READ_BYTES=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_NETWORK_REQUESTS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_RUNTIME_READS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_RETAINED_SOURCE_READS=0
PROPOSED_WORK_ITEM_AUTHOR_FREEZE_V4_CONTROL_ORDER_RETRY_SUBPROCESSES=0
```

The coordinate parent and both children were absent when this correction was authored.
They are fresh single-assignment coordinates; pre-existence of any one at a later
grant is `PAUSE`. Setup retains the exact §18.40 row-zero transaction, publication
retains §18.41 and dependencies retain the exact §18.42 deep reader. A new source must
be written from the reviewed plan and may not copy, patch, import, execute or derive
acceptance from the rejected source.

The one canonical self-test receipt builder owns a single ordered `control_rows`
array. Before the first disposable or persisted category-3-through-5 output byte, it
must:

1. construct the expected ID set as exactly `F001`–`F010` plus `W001`–`W042`;
2. sort that complete set once by raw UTF-8 bytes, producing exactly the 52-ID order
   above, with no family-specific concatenation or caller-provided order;
3. index the 52 independently executed receipts by `control_id`, reject a missing,
   extra or duplicate ID, and materialize rows only by iterating the expected list;
4. require every row's `control_id`, `mutation_id`, expected/observed rejection code,
   verdicts, created flags and `passed` value to match that same ID and its unchanged
   control contract;
5. canonicalize the complete receipt, parse the final fixed-point bytes back through
   the production receipt parser, and require the parsed control-ID array to equal the
   expected array byte-for-byte before any write; and
6. run the same aggregate receipt validator on the clean baseline and every control
   path. Any later reorder, family concatenation, unstable iteration or serializer
   drift is `F010`/`PAUSE` before output acceptance.

Control execution order is not authority and need not equal receipt order; only the
sealed receipt array is canonical. Schema-v3 `negative-controls.jsonl` remains the
unchanged W-only 42-row role sorted `W001` through `W042`. The receipt remains the
only 52-row surface and keeps its existing schema and keys. `F010` remains the sole
transaction/output-contract drift code; its meaning is not widened, and there is no
new control, schema field, file role, wrapper or acceptance exception.

#### 18.43.4 Frozen surrounding contract and authority boundary

Every §18.31–§18.42 schema, mapping, candidate/locator rule, parser, serializer,
identity adapter, packet-tree recipe, cardinality, six freeze roles, seven output
roles, 22-event ledger with exactly two null digests, fixed-point rule,
`W001`–`W042`, `F001`–`F010`, fourteen-/twenty-member no-site argv, `F002` slices
`[4:6]`/`[6:8]`, row-zero durability transition, coordinate-parent barriers,
canonical stdlib dependency reader, one-process/2-GiB-RSS/1-GiB-write ceilings,
zero-access boundary and held later real-run contract remains unchanged. This
correction closes only the already-required aggregate ordering validation for the
52-row self-test receipt.

The only admissible next sequence is Kiro exact-tip review of this correction, a new
Ryan two-SHA grant naming the fresh roots and exact receipt validator, one synthetic
process, external return of the six identities plus ledger/result/row-zero/parent-
durability counters, then plan-only result binding and Kiro capability review. Every
rejected v4 coordinate and every prior grant is non-reusable.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no retry coordinate/root/file creation, source write,
freeze execution, dependency, packet, disposition, repository, runtime or retained-
source read, work-item packet/result, network, subprocess, acquisition, ownership/
license selection, binary repair, build, publication, CI admission, product/test/
config/R2b change, implementation, PR `#342` update, PR creation, merge, deployment,
real OpenClaw, live data, watch activation, promotion or Gate D/W/D-V/E/F action.

### 18.44 V4 capability-freeze result binding

PR `#357` squash-merged the exact §18.43/§10.41 aggregate receipt-order correction
at `c5cb7c7871354b97157f392123a658a1adab4210`, Kiro returned exact-main PASS, and
PR `#358` merged the descriptive snapshot at
`2c22898b9974198fedfdf31459cb3efbcdfd08ea`. Ryan then issued one exact two-SHA
grant naming semantic parent `b279a5c9b1725157e663da610f7f66cb75773522`, reviewed
overlay `e649da29108ec17165ec9c5fd129f5e41a183ac4` and the fresh `946b469…`
coordinate. External setup completed the reviewed row-zero transaction exactly once,
and the sole no-site process completed the clean baseline, all 52 individual controls,
the 22-event ledger and both coordinate-parent durability barriers before atomically
sealing the final root. It reported `PASS`, exited zero and returned the complete
evidence packet without reading any real input.

The process result is technically `PASS`; capability acceptance remains false until
Kiro reviews this exact plan-only binding. Neither the process-reported status nor
this planning edit alone authorizes the held `author-packet` command.

#### 18.44.1 Exact sealed candidate evidence

```text
WORK_ITEM_AUTHOR_CAPABILITY_BINDING_SEMANTIC_PARENT_SHA=b279a5c9b1725157e663da610f7f66cb75773522
WORK_ITEM_AUTHOR_CAPABILITY_BINDING_REVIEWED_OVERLAY_SHA=e649da29108ec17165ec9c5fd129f5e41a183ac4
WORK_ITEM_AUTHOR_CAPABILITY_BINDING_AUTHORIZATION_BASE_SHA=2c22898b9974198fedfdf31459cb3efbcdfd08ea
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_PROCESS_EXIT_STATUS=0
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_PROCESS_REPORTED_STATUS=PASS
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_ACCEPTED=false
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_ACCEPTANCE_STATE=PENDING_EXACT_TIP_KIRO_REVIEW
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_COORDINATE_PARENT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_COORDINATE_PARENT_MODE=0700
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4.partial
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_PARTIAL_ROOT_PRESENT=false
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_ROOT_PRESENT=true
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_ROOT_MODE=0555
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_MEMBER_COUNT=6
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_MEMBER_MODE=0444
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_TREE_SHA256=291cf77798b652a41512902a5bc40a107afa661abf2edec53fa3f32e7158ff20
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_TOTAL_BYTES=196646
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_PROCESS_COUNT=1
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_SUBPROCESSES=0
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_BASELINE_COUNT=1
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_BASELINE_VIOLATION_COUNT=0
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_CONTROL_COUNT=52
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_CONTROLS_PASSED=52
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_ACTUAL_FIRST_ID=F001
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_ACTUAL_FAMILY_BOUNDARY=F010,W001
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_ACTUAL_LAST_ID=W042
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_EXPECTED_FIRST_ID=F001
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_EXPECTED_FAMILY_BOUNDARY=F010,W001
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_EXPECTED_LAST_ID=W042
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_WRITE_EVENT_COUNT=22
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_WRITE_LEDGER_SHA256=3732c403c8d46bb663d37421a6f616f282f95df7d56f87f9e59b4c086f01e440
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_FORECAST_WRITTEN_BYTES=323536730
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_OBSERVED_WRITTEN_BYTES=323536730
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_PEAK_RSS_BYTES=931274752
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_FIXED_POINT_ITERATIONS=3
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_SYNTHETIC_RESULT_SHA256=ec7a2e8c47cdb046cf1a05857c67f2af962c7a518ae7a1a3b6fa22496d9bad73
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_EXTERNAL_RESULT_SHA256=b471752f04a6b5a03089a679977dbe39651349efcc4390cf9e2722fb79ac2f45
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_EXTERNAL_RESULT_SIZE=32526
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_DEPENDENCY_COUNT=76
WORK_ITEM_AUTHOR_FREEZE_V4_CAPABILITY_STOP_STAGE=null
```

The exact final members are:

| Path | Size | Mode | SHA-256 |
|---|---:|---:|---|
| `command-contract.json` | 3,544 | `0444` | `c413185ef0a90d1e8785655abcdbece0ce94fba42fdaba89a79c6336deb2ba40` |
| `dependency-manifest.json` | 10,921 | `0444` | `b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63` |
| `fixture-spec.json` | 476 | `0444` | `d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f` |
| `freeze-manifest.json` | 969 | `0444` | `217e256fce5121f08a5687fba1b2ed4d11f0beeaaa7dd9fb6efe9a58c0ba2005` |
| `self-test-receipt.json` | 32,868 | `0444` | `3b01f77c48990d115e962d8798820110553962cc2145e2e177872a4ee4932092` |
| `work-item-author-v4.py` | 147,868 | `0444` | `fcfc60c21623093e75fef7d0cc88eba7481d16fe8a096b20cba3263124d1da07` |

Read-only verification reproduced every member size, mode, link count one and digest.
The final tree is exactly the canonical six-row inventory emitted by the reviewed
author. `freeze-manifest.json` remains nonrecursive: it hashes the other five members
and never itself. The 22-event receipt ledger likewise has null digests only for
`self-test-receipt.json` and `freeze-manifest.json`; its other twenty rows, including
both disposable result copies, have ordinary non-null digests. The external result is
not retained as a seventh member.

#### 18.44.2 Exact acceptance proof and limits

The sealed receipt independently establishes the previously missing invariant. Its
`controls` array has exactly 52 unique rows in this order:

```text
[F001, F002, ..., F010, W001, W002, ..., W042]
```

The first ID is `F001`, the sole family boundary is `F010,W001`, and the last ID is
`W042`; those values exactly equal the expected array. For each row, `control_id`,
`mutation_id`, expected and observed rejection code, expected and observed `PAUSE`
verdict, both created flags and `passed=true` bind to the unchanged control contract.
The clean baseline has zero violations and creates neither packet nor result. The
schema-v3 `negative-controls.jsonl` role remains the unchanged 42-row W-only surface;
execution order remains W-then-F and supplies no receipt authority.

Forecast and observed writes are both exactly `323,536,730`, below the unchanged
`1,073,741,824` cap. Peak RSS is `931,274,752`, below the unchanged
`2,147,483,648` cap. The canonical `_blake2` dependency remains the exact
398,208-byte file with SHA-256 `73da16b0…`; the 76-row dependency closure contains no
`site`, `_distutils_hack`, `site-packages` or `dist-packages` origin. The fixture still
contains 1,221 component items plus 19 ownership-dispute items, 98,608 unresolved IDs,
30,421 paths, 1,384 edges, twenty batches and 49 pages.

Every required durability counter is exactly one:

```text
row_zero_setup_file_fsync_count=1
row_zero_setup_directory_fsync_count=1
row_zero_governed_file_fsync_count=1
row_zero_governed_directory_fsync_count=1
row_zero_event_one_write_count_after_governed_fsync=1
coordinate_parent_pre_rename_open_count=1
coordinate_parent_pre_rename_fsync_count=1
coordinate_parent_post_rename_open_count=1
coordinate_parent_post_rename_fsync_count=1
```

Every prohibited access counter is zero:

```text
REAL_INPUT_READ_BYTES=0
NETWORK_REQUESTS=0
RUNTIME_READS=0
RETAINED_SOURCE_READS=0
REPOSITORY_READS=0
ACQUIRED_BYTES=0
CREDENTIAL_ACCESS=0
SUBPROCESSES=0
```

These facts close the synthetic qualification evidence only. `accepted=false` in the
external result deliberately prevents the process from accepting itself. Kiro must
review the exact committed binding and its unchanged inherited contract before this
candidate can become the accepted v4 author capability.

#### 18.44.3 Immutable candidate and held real operation

The coordinate parent, final root, six members, source, receipt, manifest, external
result claim and consumed grant are immutable. They may not be changed, chmodded,
deleted, renamed, copied, hard-linked, imported, executed again, repaired or
reinterpreted; the absent `.partial` sibling may not be recreated. A mismatch during
review is `PAUSE`, not authority to regenerate the candidate.

If and only if Kiro returns PASS on this exact two-commit result binding, the six-file
tree and member identities above become the sole accepted v4 author-capability
candidate for a later Ryan decision. That review still grants no real read or author
execution. The held real operation remains the exact twenty-member `author-packet`
argv and final-root cwd frozen in `command-contract.json`, with the actual reviewed
receipt and manifest hashes supplied through the existing two-mode identity adapter.
It may run only under a new two-SHA grant that names this result-binding parent and
overlay, the immutable input packet and disposition, fresh absent work-item staging
and durable roots, the exact one-pass read/write/RSS ceilings, and all stop conditions.

#### 18.44.4 Frozen surrounding contract and authority boundary

Every §18.31–§18.43 schema, mapping, role, parser, serializer, candidate/locator rule,
identity adapter, packet-tree recipe, cardinality, 22-event/two-null ledger rule,
fixed-point rule, `W001`–`W042`, `F001`–`F010`, `F010`-only drift control,
fourteen-/twenty-member no-site argv, `F002` slices `[4:6]`/`[6:8]`, row-zero and
coordinate-parent durability transition, canonical stdlib dependency reader,
one-process/2-GiB-RSS/1-GiB-write ceiling, zero-access boundary and held one-pass real
contract remains unchanged. No `F011`, schema field, file role, sidecar, wrapper,
reader, acceptance exception or second synthetic attempt is introduced.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no root/file/source creation, execution, packet/disposition/
repository/runtime/retained-source read, work-item packet/result, network, subprocess,
acquisition, ownership/license selection, binary repair, build, publication, CI
admission, product/test/config/R2b change, implementation, PR `#342` update, PR
creation, merge, deployment, real OpenClaw, live data, watch activation, promotion or
Gate D/W/D-V/E/F action. The consumed retry grant cannot be reused.

### 18.45 One-shot real work-item author grant boundary

PR `#359` squash-merged the exact §18.44/§10.42 capability binding at
`02bf65c2b4c4930da632d5a9c818f8e8047d05de`; Kiro returned exact-main PASS.
PR `#360` then squash-merged the descriptive current-state snapshot at
`ca0397c084b2616809307249212b7153d9d8ba39`. Candidate tree
`291cf77798b652a41512902a5bc40a107afa661abf2edec53fa3f32e7158ff20`
is therefore the sole accepted v4 author-capability candidate. The process result's
`accepted=false` remains the correct historical non-self-acceptance value and is not
a current rejection of the candidate.

This section closes the exact authority boundary for one possible later real
`author-packet` process. It does not grant that process. The already-frozen author,
command contract, input identities, output schemas, transaction, controls and
ceilings remain unchanged.

#### 18.45.1 Accepted author, immutable inputs and fresh output coordinates

```text
WORK_ITEM_REAL_AUTHOR_PLAN_AUTHORIZATION_BASE_MAIN_SHA=ca0397c084b2616809307249212b7153d9d8ba39
WORK_ITEM_REAL_AUTHOR_PLAN_SEMANTIC_PARENT_SHA=MILESTONE_OVERLAY_BINDING_REQUIRED
WORK_ITEM_REAL_AUTHOR_PLAN_REVIEWED_OVERLAY_SHA=EXTERNAL_EXACT_TIP_REQUIRED
WORK_ITEM_REAL_AUTHOR_OPERATION_STATUS=PLAN_ONLY
WORK_ITEM_REAL_AUTHOR_AUTHORIZED=false

WORK_ITEM_AUTHOR_CAPABILITY_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4
WORK_ITEM_AUTHOR_CAPABILITY_TREE_SHA256=291cf77798b652a41512902a5bc40a107afa661abf2edec53fa3f32e7158ff20
WORK_ITEM_AUTHOR_CAPABILITY_MEMBER_COUNT=6
WORK_ITEM_AUTHOR_CAPABILITY_MEMBER_MODE=0444
WORK_ITEM_AUTHOR_CAPABILITY_TOTAL_BYTES=196646
WORK_ITEM_AUTHOR_SOURCE_SHA256=fcfc60c21623093e75fef7d0cc88eba7481d16fe8a096b20cba3263124d1da07
WORK_ITEM_AUTHOR_COMMAND_CONTRACT_SHA256=c413185ef0a90d1e8785655abcdbece0ce94fba42fdaba89a79c6336deb2ba40
WORK_ITEM_AUTHOR_DEPENDENCY_MANIFEST_SHA256=b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63
WORK_ITEM_AUTHOR_FIXTURE_SPEC_SHA256=d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f
WORK_ITEM_AUTHOR_FREEZE_MANIFEST_SHA256=217e256fce5121f08a5687fba1b2ed4d11f0beeaaa7dd9fb6efe9a58c0ba2005
WORK_ITEM_AUTHOR_SELF_TEST_RECEIPT_SHA256=3b01f77c48990d115e962d8798820110553962cc2145e2e177872a4ee4932092

INPUT_PACKET_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet
INPUT_PACKET_TREE_SHA256=491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5
INPUT_PACKET_MANIFEST_SHA256=6791d33a82bd0f1e3fdbda072ae50aa296953b6a365194564090085541784fa4
INPUT_PACKET_MEMBER_COUNT=902
INPUT_PACKET_FILE_COUNT=663
INPUT_PACKET_DIRECTORY_COUNT=239
INPUT_PACKET_BYTES=654147403
INPUT_DISPOSITION=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json
INPUT_DISPOSITION_SHA256=45442e93958e7f0c4a2e4bf474d0b7430653fc0320ab1bad1b8222501b830669
INPUT_DISPOSITION_BYTES=8383806
TOTAL_REAL_INPUT_READ_BYTES=662531209

STAGING_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
STAGING_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
DURABLE_PARTIAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
DURABLE_FINAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
STAGING_PARTIAL_ROOT_STATUS=ABSENT
STAGING_FINAL_ROOT_STATUS=ABSENT
DURABLE_PARTIAL_ROOT_STATUS=ABSENT
DURABLE_FINAL_ROOT_STATUS=ABSENT
```

The accepted six-file root and both real inputs are immutable. A grant-time
preflight must reproduce the accepted root mode `0555`, the six member modes `0444`,
link counts one, sizes and SHA-256 values from §18.44.1 using metadata and read-only
hashing only. It must verify the packet root mode `0555`, the disposition's exact
regular-file identity and all four output-coordinate absences without opening packet
members or disposition content. Each output coordinate is single-assignment: any
pre-existence, identity mismatch or unexpected type/link/mode is `PAUSE`, with zero
processes and zero content bytes read. The preflight may not create a parent, partial,
final, author copy, wrapper, log or sidecar.

The milestone-only overlay binds the semantic parent after that commit exists. The
reviewed overlay is supplied externally as the exact Kiro review tip because a commit
cannot contain its own SHA. Any later grant must name both full SHAs; the symbolic
values above are not executable authority.

#### 18.45.2 Exact process grant

The sole admissible real command remains the literal twenty-member array already
sealed in `command-contract.json`:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4/work-item-author-v4.py",
  "author-packet",
  "--input-packet-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet",
  "--input-disposition",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json",
  "--staging-root",
  "/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--durable-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4/freeze-manifest.json"
]
```

The cwd is exactly the accepted v4 root. The complete environment is exactly
`LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONHASHSEED=0`, and `PYTHONNOUSERSITE=1`. Launch is direct `execve` semantics:
no shell, wrapper, inherited descriptor, extra argument, extra environment member,
path substitution, import, copy or source rewrite.

Ryan's later grant must name, in one decision, the exact plan semantic parent and
reviewed overlay, authorization-base main SHA, accepted author tree and all six
member identities, packet and disposition identities, four absent output
coordinates, exact argv/cwd/environment, one-process rule, content-read ceilings,
write/RSS ceilings, stop conditions and returned evidence. No earlier grant, PASS,
merge, candidate acceptance or `CONTINUE` supplies any part of that authority.

#### 18.45.3 One-pass transaction and ceilings

After successful preflight, exactly one no-site process may run. It independently
revalidates the accepted author and inputs under the frozen §18.31–§18.44 rules,
opens each of the 663 packet files and the disposition content at most once, and
reads exactly `662,531,209` governed input bytes. It creates neither partial root
until both inputs, the 902-row packet-tree identity and the complete disposition have
validated. It then exclusive-creates only the exact staging and durable `.partial`
roots and performs the unchanged seven-role/fixed-point/durability transaction.

Success requires exactly 1,221 component items, 19 ownership-dispute items, 98,608
unresolved IDs, 30,421 paths, 1,384 edges, twenty batches and 49 pages in each
seven-file packet; packet members are `0444`, `packet/` and both final roots are
`0555`, and `authoring-result.json` is `0400`. The unchanged result schema is
`convmem.switchboard.work-item-authoring-result.v2`; structural status is `PASS`,
provenance/licensing remains `PAUSE`, and every authorization/eligibility field
remains false. The real identity adapter supplies freeze-manifest SHA-256
`217e256f…` and self-test-receipt SHA-256 `3b01f77c…`; no synthetic predecessor is
admissible.

The hard ceilings are one process, zero subprocesses, peak RSS at most
`2,147,483,648`, at most `2,147,483,648` written bytes per output root and at most
`4,294,967,296` total written bytes. Network requests, runtime/repository/retained-
source reads, credentials, acquisitions and every non-input content read remain
zero. There is no retry, resume, repair, deletion, cleanup, partial acceptance or
second input pass. Failure preserves the exact coordinate state where execution
stopped and returns `PAUSE`.

#### 18.45.4 Returned evidence and acceptance boundary

The supervisor returns, outside both output roots, the exact process count, exit
status, reported status, input bytes by role, output bytes by root, peak RSS,
subprocess/network/forbidden-access counters, both partial/final presence states,
both final tree identities when present, and the external SHA-256 and byte size of
each `authoring-result.json`. The result does not self-hash. The returned evidence is
not a seventh packet role, sidecar or acceptance authority.

Even a zero exit and two byte-identical structurally passing packets cannot accept
their own provenance, licensing, acquisition, build or publication conclusions.
Success advances only to a plan-only exact-result binding and Kiro review. Any later
independent provenance/licensing review, acquisition, build, publication, CI
admission, implementation or real OpenClaw use requires a separately reviewed packet
and a separate Ryan grant.

#### 18.45.5 Sequence and authority boundary

The only admissible sequence is: Kiro exact-tip review of this two-commit plan;
Ryan's PR decision; squash merge and exact-main confirmation; a current-state
snapshot if required; one fresh Ryan two-SHA grant naming the still-absent roots and
the exact boundary above; one supervised process; plan-only result binding and Kiro
review; then a separately granted independent review. Kiro PASS, PR creation, merge
and descriptive snapshots do not collapse or imply the later grant.

Every §18.31–§18.44 schema, mapping, parser, serializer, identity adapter, seven
output roles, packet-tree recipe, cardinality, control, ledger, fixed-point rule,
durability barrier, command member, environment member and ceiling remains
unchanged. No new schema, role, control, `F011`, wrapper, reader, sidecar, exception
or acceptance transfer is introduced.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no input-content read, output parent/root/file creation,
author execution, retry, repair, network, subprocess, acquisition, ownership/license
selection, build, publication, CI admission, product/test/config/R2b change,
implementation, PR `#342` update, PR creation, merge, deployment, real OpenClaw,
live data, watch activation, promotion or Gate D/W/D-V/E/F action.

### 18.46 Real-author W001 unresolved-ID grammar correction

PR `#361` squash-merged the reviewed §18.45/§10.43 real-author boundary at
`8d1c01762d920a91667f96182fab04c4fc583e86`, and PR `#362` squash-merged its
reviewed current-state snapshot at
`ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c`. Ryan subsequently issued two exact
grants over semantic parent `31d4c919cfe77ae6d2fbbcb473a0fd8e0857515d` and
reviewed overlay `d7f82fbcd3afd3887d4b3764b173958d5094ee53`. Both grants
are consumed and non-reusable. This section preserves their evidence, closes the one
localized W001 grammar defect and defines a fresh synthetic capability-freeze route.
It does not authorize that freeze or another real-author process.

#### 18.46.1 Exact stopped state and localization

The first grant stopped during read-only output-lineage preflight because its
ancestor walker treated the expected first `ENOENT` as an error. It launched zero
processes, read zero packet/disposition content bytes, wrote zero bytes and created
or mutated no path. The successor grant changed only that preflight interpretation:
the first `ENOENT` on each exact output lineage proved the named descendants absent
and stopped traversal below the missing component.

Corrected preflight passed. Exactly one no-site process then launched and failed
closed with exit status `1`, stage `DEPENDENCY_CLOSURE`, and
`Refusal: W001: input ID prefix`. It read `54,052,776` real-input bytes, reached
peak RSS `2,059,636,736` below the `2,147,483,648` ceiling, launched no subprocess,
and made zero network, runtime, repository, retained-source, credential or
acquisition accesses. All four §18.45.1 output coordinates remain absent. No receipt,
result, write ledger, role file or work-item cardinality exists; setup row-zero
file/directory fsync counts are each one, while governed row-zero, event-one and
coordinate-parent barrier counts are zero.

The byte position localizes the refusal without reopening either input. The immutable
packet contains `654,147,403` bytes, of which its object payloads contain
`600,094,627`; their difference is exactly `54,052,776`. The process therefore read
every non-object packet member, reached the last raw-UTF-8-sorted role
`unresolved.jsonl`, and failed before opening any object payload or the disposition.

The earlier independent schema-v3 packet/disposition review recorded the immutable
packet's authoritative unresolved identifier grammar as
`unresolved_sha256:<64 lowercase hexadecimal characters>`. Its 98,608 identifiers
begin with
`unresolved_sha256:00026163d2a8b5be29c262045a87cd7bf8931cdfe0a1baa2936c1884a0754bb6`
and end with
`unresolved_sha256:fffee57633575222636d30ab1c65d051dae7eb6d7c4493dc4d95bcdd4c424581`;
the independently reviewed disposition carries the same ordered ID list. The
accepted author's real validator and synthetic fixture instead require and generate
`unresolved:sha256:<64 lowercase hexadecimal characters>`. Because both synthetic
producer and validator share that wrong literal, the clean baseline and all 52
controls could pass without exercising the real packet grammar.

#### 18.46.2 Sole correction and rejected broad fixes

The successor source has exactly one semantic correction: the authoritative
unresolved-ID form is
`unresolved_sha256:` followed by the lowercase SHA-256 of the unchanged canonical
unresolved-row body. The real-input validator, full-ID recomputation and synthetic
fixture generator must all use that same literal and the same shared production
validation path. Existing `W001` additionally substitutes the former
`unresolved:sha256:` spelling into an otherwise valid synthetic row and requires
that mutation to fail before any governed output write. This is an additional case
inside `W001`, not `W043`, `F011` or a 53rd control.

The immutable packet and disposition are correct and must not be rewritten. The
correction admits no alias, dual-prefix compatibility, punctuation normalization,
prefix translation, fallback parser, packet repair, pre-validation rewrite or
caller-selected grammar. Every non-unresolved identifier rule remains byte-for-byte
unchanged. If a future process rejects an input identifier, its external failure
context may expose only role, field and row ordinal; it must not echo the identifier
or any other input content.

The historical §18.35 lower-bound arithmetic is unchanged: replacing one punctuation
character with another does not change identifier length, object size or any read,
write or RSS ceiling.

#### 18.46.3 Fresh synthetic capability freeze

The accepted §18.44 candidate is immutable evidence of its reviewed source and is no
longer eligible for real input because that source contains the wrong unresolved-ID
literal. It must not be edited, copied, patched, rehashed into a successor, executed
again or treated as partially reusable authority. A corrected source can become a
candidate only through a new full synthetic capability freeze at fresh,
single-assignment coordinates:

```text
W001_CORRECTION_PLAN_AUTHORIZATION_BASE_MAIN_SHA=ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c
W001_CORRECTION_PLAN_SEMANTIC_PARENT_SHA=MILESTONE_OVERLAY_BINDING_REQUIRED
W001_CORRECTION_PLAN_REVIEWED_OVERLAY_SHA=EXTERNAL_EXACT_TIP_REQUIRED
W001_CORRECTION_OPERATION_STATUS=PLAN_ONLY
W001_CORRECTION_FREEZE_AUTHORIZED=false

REJECTED_REAL_AUTHOR_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/946b469e27c7eb27c198898fa330c2475bde29fa/v4
REJECTED_REAL_AUTHOR_TREE_SHA256=291cf77798b652a41512902a5bc40a107afa661abf2edec53fa3f32e7158ff20
CORRECTED_CAPABILITY_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c/v4.partial
CORRECTED_CAPABILITY_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c/v4
CORRECTED_CAPABILITY_PARTIAL_ROOT_STATUS=ABSENT
CORRECTED_CAPABILITY_FINAL_ROOT_STATUS=ABSENT
```

Any pre-existence at grant time is `PAUSE`; neither coordinate may be deleted,
repaired, completed or reused. A later grant may authorize only the existing
`synthetic-freeze` command under the unchanged `-S` interpreter, fourteen-member
argv, five-key environment, one-process/no-subprocess rule, row-zero and
pre-/post-rename durability transaction, 22-event/two-null ledger, one-GiB write and
two-GiB RSS ceilings, and zero external-access contract. It authorizes no real packet
or disposition read and no `author-packet` command.

The clean baseline and all 52 controls `F001`–`F010`, `W001`–`W042` must pass in the
required raw-ID order. The resulting source, command contract, dependency manifest,
fixture spec, freeze manifest, receipt and six-file tree receive new exact hashes;
none is inherited from tree `291cf777…`. A later plan-only result binding must record
those hashes, modes, sizes, control receipt, ledger, durability counters, resource
counters and `accepted=false`, followed by exact-tip Kiro review. No synthetic result
self-accepts.

#### 18.46.4 Frozen contract, sequence and authority boundary

Everything outside the literal correction and its `W001` negative case remains
unchanged: the six freeze roles, seven output roles, schemas, field mappings,
canonical serializers/parsers, 902-member packet-tree recipe, identity adapters,
14-/20-member argv, `F002` slices `[4:6]`/`[6:8]`, 52-control set, F-before-W receipt
order, 22-event/two-null ledger, fixed point, durability barriers, cardinalities,
read/write/RSS ceilings, and zero-access rules. `F010` remains the sole transaction-
drift control. No new schema, role, wrapper, sidecar, reader, exception, `W043`,
`F011` or acceptance transfer is introduced.

The only admissible sequence is: exact-tip Kiro review of this two-commit plan;
Ryan's PR decision; squash merge and exact-main confirmation; one new Ryan two-SHA
grant for only the fresh synthetic capability freeze; plan-only result binding and
Kiro review; then, if that corrected candidate is accepted, a separately planned,
reviewed and granted real-author operation using fresh output coordinates. Neither
consumed real-author grant, the old accepted candidate, this plan, a review PASS nor
a merge supplies any part of those later grants.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no packet/disposition content read, root/source/file
creation, capability freeze, author execution, real-author retry, network,
subprocess, acquisition, ownership/license selection, build, publication, CI
admission, product/test/config/R2b change, implementation, PR `#342` update, PR
creation, merge, deployment, real OpenClaw, live data, watch activation, promotion
or Gate D/W/D-V/E/F action.

### 18.47 Corrected capability-freeze result binding

PR `#363` squash-merged the exact §18.46/§10.44 unresolved-ID correction at
`0a250b197ce316f058e2df6d974aedc68d3db0e4`, byte-identical to reviewed overlay
`9241543c22b3d2f25e54cabd8ccb0203ed1feca5`, and Kiro returned exact-main PASS.
PR `#364` then squash-merged the descriptive current-state snapshot at
`4f6266e94c2add550ae15d456141536f9937dbf8`. Ryan separately issued one exact
two-SHA synthetic-freeze grant naming semantic parent
`a64fdcfe941743ef2b5f8d18829830a846d362a3`, reviewed overlay
`9241543c22b3d2f25e54cabd8ccb0203ed1feca5` and the fresh `ff5ce7b…`
coordinate. Setup wrote and durably bound the reviewed source once, and the sole
fourteen-member no-site process completed a clean baseline, all 52 controls, the
22-event ledger and both coordinate-parent durability barriers before atomically
sealing the final root. It reported `PASS`, exited zero and returned the complete
evidence packet without reading any real packet or disposition.

The process result is technically `PASS`; `accepted=false` remains controlling
until Kiro reviews this exact plan-only binding. Neither the process-reported status
nor this planning edit authorizes the held real `author-packet` command.

#### 18.47.1 Exact sealed candidate evidence

```text
W001_CORRECTION_BINDING_GRANT_SEMANTIC_PARENT_SHA=a64fdcfe941743ef2b5f8d18829830a846d362a3
W001_CORRECTION_BINDING_GRANT_REVIEWED_OVERLAY_SHA=9241543c22b3d2f25e54cabd8ccb0203ed1feca5
W001_CORRECTION_BINDING_AUTHORIZATION_BASE_MAIN_SHA=4f6266e94c2add550ae15d456141536f9937dbf8
W001_CORRECTION_BINDING_PLAN_MERGED_MAIN_SHA=0a250b197ce316f058e2df6d974aedc68d3db0e4
W001_CORRECTION_BINDING_PROCESS_EXIT_STATUS=0
W001_CORRECTION_BINDING_PROCESS_REPORTED_STATUS=PASS
W001_CORRECTION_BINDING_ACCEPTED=false
W001_CORRECTION_BINDING_ACCEPTANCE_STATE=PENDING_EXACT_TIP_KIRO_REVIEW
W001_CORRECTION_BINDING_COORDINATE_PARENT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c
W001_CORRECTION_BINDING_COORDINATE_PARENT_MODE=0700
W001_CORRECTION_BINDING_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c/v4.partial
W001_CORRECTION_BINDING_PARTIAL_ROOT_PRESENT=false
W001_CORRECTION_BINDING_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c/v4
W001_CORRECTION_BINDING_FINAL_ROOT_PRESENT=true
W001_CORRECTION_BINDING_FINAL_ROOT_MODE=0555
W001_CORRECTION_BINDING_MEMBER_COUNT=6
W001_CORRECTION_BINDING_MEMBER_MODE=0444
W001_CORRECTION_BINDING_TOTAL_BYTES=197259
W001_CORRECTION_BINDING_TREE_SHA256=939b8849d95eaf146efa528284d29d69f516c8aa400f432f1bed43009199a396
W001_CORRECTION_BINDING_SOURCE_SIZE=148481
W001_CORRECTION_BINDING_SOURCE_LINE_COUNT=2952
W001_CORRECTION_BINDING_SOURCE_SHA256=5550d1ecdc4a5375940166fe58232e2ba25d821e37478a6fe1608a771c5597b0
W001_CORRECTION_BINDING_RECEIPT_SHA256=920c0e0e74515b5b1304de59b2a32a00b55c949b11938f9b3ddd68b12213bce1
W001_CORRECTION_BINDING_FREEZE_MANIFEST_SHA256=8291129e3b47bb29dd39cfa7d2e8d60a62fcb8df8c6578d53e028ee7d7f48903
W001_CORRECTION_BINDING_WRITE_LEDGER_SHA256=959e64ba5782afbacb8eb94f0d7df297ee3351fe596ebc927c8c51b1a6932055
W001_CORRECTION_BINDING_COMMAND_CONTRACT_SHA256=e5291097982fdb8086bd7e7315e4a4cd577091c7ec6701d80486f0f7412a1206
W001_CORRECTION_BINDING_DEPENDENCY_MANIFEST_SHA256=b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63
W001_CORRECTION_BINDING_FIXTURE_SHA256=d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f
W001_CORRECTION_BINDING_SYNTHETIC_INPUT_TREE_SHA256=9551fa86cb9bf33f757bf584a16d5d930da5006ee0145beb2a675f136f38b4ab
W001_CORRECTION_BINDING_SYNTHETIC_DISPOSITION_SHA256=758764a25432300fb098d5480f9fcebd7a7648cf319b3d623c7eb294a4f80a82
W001_CORRECTION_BINDING_SYNTHETIC_PACKET_TREE_SHA256=2d1d95d6991fe9368d29746d0704267628884810a026a5d9a5814ab31e50b8a7
W001_CORRECTION_BINDING_SYNTHETIC_RESULT_SHA256=d9a17dd0daf5a601873addd0fb5d8c9226ecfda587a733de7f1bfa227d2253b2
W001_CORRECTION_BINDING_EXTERNAL_RESULT_SHA256=66bf06a25f02f102e876c7f2f396aed6c68c91b8a52f565834b401cd7cbbef36
W001_CORRECTION_BINDING_EXTERNAL_RESULT_SIZE=32527
W001_CORRECTION_BINDING_PROCESS_COUNT=1
W001_CORRECTION_BINDING_SUBPROCESSES=0
W001_CORRECTION_BINDING_BASELINE_COUNT=1
W001_CORRECTION_BINDING_BASELINE_VIOLATION_COUNT=0
W001_CORRECTION_BINDING_CONTROL_COUNT=52
W001_CORRECTION_BINDING_CONTROLS_PASSED=52
W001_CORRECTION_BINDING_ACTUAL_FIRST_ID=F001
W001_CORRECTION_BINDING_ACTUAL_FAMILY_BOUNDARY=F010,W001
W001_CORRECTION_BINDING_ACTUAL_LAST_ID=W042
W001_CORRECTION_BINDING_EXPECTED_FIRST_ID=F001
W001_CORRECTION_BINDING_EXPECTED_FAMILY_BOUNDARY=F010,W001
W001_CORRECTION_BINDING_EXPECTED_LAST_ID=W042
W001_CORRECTION_BINDING_WRITE_EVENT_COUNT=22
W001_CORRECTION_BINDING_FORECAST_WRITTEN_BYTES=323537343
W001_CORRECTION_BINDING_OBSERVED_WRITTEN_BYTES=323537343
W001_CORRECTION_BINDING_PEAK_RSS_BYTES=2059636736
W001_CORRECTION_BINDING_FIXED_POINT_ITERATIONS=3
W001_CORRECTION_BINDING_DEPENDENCY_COUNT=76
W001_CORRECTION_BINDING_STOP_STAGE=null
```

The exact final members are:

| Path | Size | Mode | SHA-256 |
|---|---:|---:|---|
| `command-contract.json` | 3,544 | `0444` | `e5291097982fdb8086bd7e7315e4a4cd577091c7ec6701d80486f0f7412a1206` |
| `dependency-manifest.json` | 10,921 | `0444` | `b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63` |
| `fixture-spec.json` | 476 | `0444` | `d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f` |
| `freeze-manifest.json` | 969 | `0444` | `8291129e3b47bb29dd39cfa7d2e8d60a62fcb8df8c6578d53e028ee7d7f48903` |
| `self-test-receipt.json` | 32,868 | `0444` | `920c0e0e74515b5b1304de59b2a32a00b55c949b11938f9b3ddd68b12213bce1` |
| `work-item-author-v4.py` | 148,481 | `0444` | `5550d1ecdc4a5375940166fe58232e2ba25d821e37478a6fe1608a771c5597b0` |

Read-only verification reproduced every member size, mode, single-link identity and
digest. `freeze-manifest.json` remains nonrecursive: it hashes the other five members
and never itself. The 22-event receipt ledger has null digests only for
`self-test-receipt.json` and `freeze-manifest.json`; its other twenty rows have
ordinary non-null digests. The external result is not a seventh member.

#### 18.47.2 Exact acceptance proof and limits

The clean baseline returned `PASS`, created neither packet nor result and had zero
violations. The sealed receipt contains exactly 52 unique passing rows in the required
raw-ID order `F001`–`F010`, then `W001`–`W042`; actual and expected first ID,
family boundary and last ID match exactly. The corrected shared production path uses
only `unresolved_sha256:`. Existing W001 retains its input-tree-hash mutation and
also rejects an otherwise-valid row using obsolete `unresolved:sha256:`. No alias,
normalization, dual-prefix path, `W043`, `F011` or 53rd control exists.

The fixture preserves 1,221 components, 19 disputes, twenty batches, 49 pages,
98,608 unresolved IDs, 30,402 owned paths, 30,421 runtime paths and 1,384 nested
edges. Synthetic packet and disposition reads were exactly `55,760,899` and
`8,383,504` bytes. Forecast and observed writes both equal `323,537,343`, below the
unchanged one-GiB ceiling. Peak RSS was `2,059,636,736`, below the unchanged
`2,147,483,648` ceiling.

Every required durability counter is exactly one:

```text
row_zero_setup_file_fsync_count=1
row_zero_setup_directory_fsync_count=1
row_zero_governed_file_fsync_count=1
row_zero_governed_directory_fsync_count=1
row_zero_event_one_write_count_after_governed_fsync=1
coordinate_parent_pre_rename_open_count=1
coordinate_parent_pre_rename_fsync_count=1
coordinate_parent_post_rename_open_count=1
coordinate_parent_post_rename_fsync_count=1
```

Every prohibited access counter is zero:

```text
REAL_INPUT_READ_BYTES=0
NETWORK_REQUESTS=0
RUNTIME_READS=0
RETAINED_SOURCE_READS=0
REPOSITORY_READS=0
ACQUIRED_BYTES=0
CREDENTIAL_ACCESS=0
SUBPROCESSES=0
```

These facts close only corrected synthetic qualification. `accepted=false` prevents
the process from accepting itself. Kiro must review the exact committed binding and
its inherited contract before the candidate can become accepted.

#### 18.47.3 Immutable candidate and held real operation

The coordinate parent, final root, six members, source, receipt, manifests, external
result claim and consumed grant are immutable. They may not be changed, chmodded,
deleted, renamed, copied, hard-linked, imported, executed again, repaired or
reinterpreted; the absent `.partial` sibling may not be recreated. A mismatch during
review is `PAUSE`, not authority to regenerate the candidate.

If and only if Kiro returns PASS on this exact two-commit result binding, tree
`939b8849d95eaf146efa528284d29d69f516c8aa400f432f1bed43009199a396`
becomes the sole accepted corrected v4 author-capability candidate for a later Ryan
decision. That review grants no real read or author execution. The held real operation
requires a new plan, exact-tip review, exact-main confirmation and separate Ryan
two-SHA grant naming the accepted candidate, immutable real packet/disposition and
fresh absent work-item output coordinates. No prior real-author or synthetic-freeze
grant is reusable.

#### 18.47.4 Frozen surrounding contract and authority boundary

Every §18.31–§18.46 schema, mapping, role, parser, serializer, candidate/locator
rule, identity adapter, packet-tree recipe, cardinality, 22-event/two-null ledger,
fixed-point rule, `W001`–`W042`, `F001`–`F010`, `F010`-only drift control,
fourteen-/twenty-member no-site argv, `F002` slices `[4:6]`/`[6:8]`, row-zero and
coordinate-parent durability transition, canonical stdlib dependency reader,
one-process/write/RSS ceilings, zero-access boundary and held one-pass real contract
remain unchanged. No new schema field, file role, sidecar, wrapper, reader,
acceptance exception or second synthetic attempt is introduced.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no root/file/source creation, execution, packet/disposition/
repository/runtime/retained-source read, work-item packet/result, retry, network,
subprocess, acquisition, ownership/license selection, binary repair, build,
publication, CI admission, product/test/config/R2b change, implementation, PR `#342`
update, PR creation, merge, deployment, real OpenClaw, live data, watch activation,
promotion or Gate D/W/D-V/E/F action. The consumed synthetic-freeze grant cannot be
reused.

### 18.48 Corrected one-shot real work-item author grant boundary

PR `#366` squash-merged the exact §18.47/§10.45 corrected capability binding at
`dd4dd39ce493e06462acdd21e9dd68466149f4b5`; Kiro returned exact-tip and
exact-main PASS. PR `#368` then squash-merged the acceptance snapshot at
`16dbd7926a8c14d71595440a5ac4ba78b99e26ed`, preserving the reviewed acceptance
blobs byte-for-byte. Candidate tree
`939b8849d95eaf146efa528284d29d69f516c8aa400f432f1bed43009199a396` is therefore
the sole accepted corrected-v4 author-capability candidate. The process result's
`accepted=false` remains the correct historical non-self-acceptance value. The nine
durability counters and peak RSS remain process-attested at 80% confidence; merge,
review and acceptance preserve that limitation and do not independently reproduce
those runtime facts.

This section closes the exact authority boundary for one possible later real
`author-packet` process using the corrected candidate. It does not grant that process.
The accepted author, input identities, output schemas, transaction, controls,
cardinalities and ceilings remain the same closed contract reviewed in
§§18.31–18.47, except that this operation uses fresh single-assignment output
coordinates bound to current main.

#### 18.48.1 Accepted author, immutable inputs and fresh output coordinates

```text
CORRECTED_REAL_AUTHOR_PLAN_AUTHORIZATION_BASE_MAIN_SHA=16dbd7926a8c14d71595440a5ac4ba78b99e26ed
CORRECTED_REAL_AUTHOR_PLAN_SEMANTIC_PARENT_SHA=MILESTONE_OVERLAY_BINDING_REQUIRED
CORRECTED_REAL_AUTHOR_PLAN_REVIEWED_OVERLAY_SHA=EXTERNAL_EXACT_TIP_REQUIRED
CORRECTED_REAL_AUTHOR_OPERATION_STATUS=PLAN_ONLY
CORRECTED_REAL_AUTHOR_AUTHORIZED=false

CORRECTED_AUTHOR_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c/v4
CORRECTED_AUTHOR_TREE_SHA256=939b8849d95eaf146efa528284d29d69f516c8aa400f432f1bed43009199a396
CORRECTED_AUTHOR_MEMBER_COUNT=6
CORRECTED_AUTHOR_MEMBER_MODE=0444
CORRECTED_AUTHOR_TOTAL_BYTES=197259
CORRECTED_AUTHOR_SOURCE_SIZE=148481
CORRECTED_AUTHOR_SOURCE_LINE_COUNT=2952
CORRECTED_AUTHOR_SOURCE_SHA256=5550d1ecdc4a5375940166fe58232e2ba25d821e37478a6fe1608a771c5597b0
CORRECTED_AUTHOR_COMMAND_CONTRACT_SHA256=e5291097982fdb8086bd7e7315e4a4cd577091c7ec6701d80486f0f7412a1206
CORRECTED_AUTHOR_DEPENDENCY_MANIFEST_SHA256=b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63
CORRECTED_AUTHOR_FIXTURE_SHA256=d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f
CORRECTED_AUTHOR_FREEZE_MANIFEST_SHA256=8291129e3b47bb29dd39cfa7d2e8d60a62fcb8df8c6578d53e028ee7d7f48903
CORRECTED_AUTHOR_SELF_TEST_RECEIPT_SHA256=920c0e0e74515b5b1304de59b2a32a00b55c949b11938f9b3ddd68b12213bce1
CORRECTED_AUTHOR_WRITE_LEDGER_SHA256=959e64ba5782afbacb8eb94f0d7df297ee3351fe596ebc927c8c51b1a6932055
CORRECTED_AUTHOR_DURABILITY_RSS_EVIDENCE=PROCESS_ATTESTED_80_PERCENT_CONFIDENCE

INPUT_PACKET_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet
INPUT_PACKET_TREE_SHA256=491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5
INPUT_PACKET_MANIFEST_SHA256=6791d33a82bd0f1e3fdbda072ae50aa296953b6a365194564090085541784fa4
INPUT_PACKET_MEMBER_COUNT=902
INPUT_PACKET_FILE_COUNT=663
INPUT_PACKET_DIRECTORY_COUNT=239
INPUT_PACKET_BYTES=654147403
INPUT_DISPOSITION=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json
INPUT_DISPOSITION_SHA256=45442e93958e7f0c4a2e4bf474d0b7430653fc0320ab1bad1b8222501b830669
INPUT_DISPOSITION_BYTES=8383806
TOTAL_REAL_INPUT_READ_BYTES=662531209

STAGING_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/16dbd7926a8c14d71595440a5ac4ba78b99e26ed/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
STAGING_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/16dbd7926a8c14d71595440a5ac4ba78b99e26ed/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
DURABLE_PARTIAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/16dbd7926a8c14d71595440a5ac4ba78b99e26ed/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
DURABLE_FINAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/16dbd7926a8c14d71595440a5ac4ba78b99e26ed/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
STAGING_PARTIAL_ROOT_STATUS=ABSENT
STAGING_FINAL_ROOT_STATUS=ABSENT
DURABLE_PARTIAL_ROOT_STATUS=ABSENT
DURABLE_FINAL_ROOT_STATUS=ABSENT
```

The accepted six-file root and both real inputs are immutable. A grant-time
preflight must reproduce the accepted root mode `0555`, coordinate-parent mode
`0700`, six single-link member modes `0444`, sizes and SHA-256 values from §18.47.1
using metadata and read-only hashing only. The process-attested durability and RSS
facts remain explicitly capped at 80% confidence after that inspection; a matching
hash does not lift the evidence ceiling. The preflight must verify the packet root
mode `0555`, the disposition's exact regular-file metadata and all four output-
coordinate absences without opening packet members or disposition content. Each
output coordinate is single-assignment. Any pre-existence, identity mismatch or
unexpected type, link count or mode is `PAUSE` with zero processes, zero content bytes
read and zero created paths. The preflight may not create a parent, partial, final,
author copy, wrapper, log or sidecar.

The milestone-only overlay binds the semantic parent after that commit exists. The
reviewed overlay is supplied externally as Kiro's exact-tip review target because a
commit cannot contain its own SHA. Any later grant must name both full plan SHAs;
symbolic values are not execution authority.

#### 18.48.2 Exact process grant

The sole admissible real command is the literal twenty-member array sealed by the
accepted corrected command contract:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c/v4/work-item-author-v4.py",
  "author-packet",
  "--input-packet-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet",
  "--input-disposition",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json",
  "--staging-root",
  "/home/lauer/.cache/convmem-switchboard-provenance-work-items/16dbd7926a8c14d71595440a5ac4ba78b99e26ed/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--durable-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/16dbd7926a8c14d71595440a5ac4ba78b99e26ed/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c/v4/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c/v4/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c/v4/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/ff5ce7b9cc30e4466045387e27e4d4f9fcdb482c/v4/freeze-manifest.json"
]
```

The cwd is exactly the accepted corrected root. The complete environment is exactly:

```text
LANG=C.UTF-8
LC_ALL=C.UTF-8
PYTHONDONTWRITEBYTECODE=1
PYTHONHASHSEED=0
PYTHONNOUSERSITE=1
```

The supervisor uses direct `execve` semantics with no shell, wrapper, extra argument,
extra environment member, inherited descriptor, author copy or alternate import
path. The accepted source must prove `sys.flags.no_site == 1` and the sealed
dependency manifest before opening real input. The command uses only corrected
`unresolved_sha256:<64 lowercase hex>` identifiers. Existing `W001` must reject the
obsolete `unresolved:sha256:` spelling; no alias, normalization or dual-prefix route
exists.

#### 18.48.3 One-pass transaction, ceilings and returned evidence

After grant-time preflight, the sole process independently revalidates the candidate
and both inputs. It opens each of the 663 packet files and the disposition at most
once, consumes exactly `662,531,209` governed input bytes and validates the complete
902-member packet-tree identity before output creation. It creates neither parent nor
root until both complete inputs validate, then exclusively creates the two partial
roots and follows the unchanged seven-role, fixed-point, file/directory-`fsync`,
coordinate-parent-`fsync` and atomic-publication transaction. Staging and durable
copies must be byte-identical.

Successful structural output remains exactly 1,221 component items plus 19 ownership-
dispute items, 1,240 primary items total, 98,608 unresolved IDs, 30,421 paths
(30,402 owned), 1,384 edges, twenty batches and 49 pages. Packet members are `0444`,
result files are `0400`, and packet/final directories are `0555`. The result schema
remains `convmem.switchboard.work-item-authoring-result.v2`. Structural success does
not change provenance, licensing, authorization or build eligibility: all remain
`PAUSE`/false until their separate reviews and grants.

The supervisor enforces exactly one process, zero subprocesses, peak RSS at most
`2,147,483,648`, writes at most `2,147,483,648` bytes per output root and at most
`4,294,967,296` total bytes. Network, runtime, repository, retained-source,
credential and acquisition access remain zero. Failure permits no retry, repair,
resume, deletion, cleanup or second input pass; it preserves the exact coordinate
state and returns `PAUSE`.

Returned evidence must include process/exit/reported status, baseline/control counts,
the exact F001–F010 then W001–W042 receipt order, input bytes by role, written bytes
by root, peak RSS, every durability and forbidden-access counter, coordinate states,
final tree identities if present, and external result hashes/sizes. The result does
not self-hash, and external evidence is neither an eighth packet role nor authority.
Any post-run statement about the prior capability's nine durability counters or peak
RSS must retain the explicit 80% process-attested confidence ceiling unless genuinely
independent evidence is separately reviewed; success of this operation cannot
retroactively lift that ceiling.

#### 18.48.4 Progression and authority boundary

Success advances only to a plan-only exact-result binding and Kiro review. An
independent reviewer must then prove the exact 1,240-item, 98,608-ID, 1,384-edge,
twenty-batch, 49-page and 19-dispute unions against the immutable inputs. That review
cannot select origins, owners or licenses, resolve a blocker, grant acquisition,
repair a host-path-bearing binary, authorize build/publication or accept its own
result. Every origin operation, acquisition, clean build, final packet, publication,
CI admission, implementation, deployment and real-OpenClaw action remains a later
separately planned, reviewed and Ryan-granted gate.

The only possible progression is exact-tip Kiro review of this two-commit plan,
Ryan's PR/merge decision, exact-main confirmation, one fresh two-SHA execution grant,
one supervised process, plan-only result binding and review, then a separately
granted independent work-item review. No prior real-author, retry or synthetic-freeze
grant is reusable.

Every §18.31–§18.47 schema, mapping, six freeze roles, seven output roles, parser,
serializer, identity adapter, packet-tree recipe, cardinality, 22-event/two-null
ledger, fixed-point rule, `W001`–`W042`, `F001`–`F010`, F-before-W order,
`F010`-only drift control, fourteen-/twenty-member no-site argv, `F002` slices,
durability transaction, canonical stdlib dependency reader, one-process ceilings and
zero-access boundary remain unchanged. This section creates no `W043`, `F011`, 53rd
control, schema field, file role, sidecar, wrapper, reader or acceptance exception.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no packet/disposition content read, root/file/source
creation, author execution, retry, acquisition, build, publication, implementation,
PR creation or update, merge, deployment, real OpenClaw, watch activation, live data,
promotion or Gate D/W/D-V/E/F action.

### 18.49 Output-coordinate binding correction after the F002 startup pause

PR `#369` squash-merged the reviewed §§18.48/10.46 plan at
`a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b`; Kiro returned exact-tip and
exact-main PASS. Ryan then issued the exact two-SHA grant naming semantic parent
`ce768a79eeddb36d3a150d09d850161a42338227`, reviewed overlay
`ac04fddadaa7a5ae741c49a2960c20e83151aff9`, accepted capability tree
`939b8849d95eaf146efa528284d29d69f516c8aa400f432f1bed43009199a396` and the
four `16dbd79…/491ae60b…/v3(.partial)` output coordinates. The grant is consumed.

The exact preflight passed. The sole direct process then exited `1` at `STARTUP`
with `status=PAUSE` and `Refusal: F002: literal argv`. It started no subprocess,
read zero packet/disposition content bytes, ran zero baseline or governed controls,
wrote zero governed bytes and created no output coordinate. All four grant-named
roots remain absent. The supervisor reported peak RSS `1,367,023,616` bytes and
zero network, runtime, repository, retained-source, credential and acquisition
access. Those facts preserve fail-closed behavior; they do not make the grant
reusable.

The mismatch is exact and narrow. The immutable accepted command contract pins
`author_packet_argv[9]` and `[11]` to final roots in the older `dea026ce…`
namespace, while §§18.48/10.46 and the grant substituted final roots in the
`16dbd79…` namespace. The accepted source compares the runtime argv literally to
that sealed vector before opening real input, so F002 correctly refused the
substitution. Output coordinates are therefore part of the capability itself, not
late-bound invocation parameters.

This section plans the only admissible correction: freeze a new synthetic
capability whose sealed twenty-member real argv already names one new output
namespace. It does not authorize that freeze or another real-author attempt.

#### 18.49.1 Immutable failure record and ineligible accepted candidate

```text
OUTPUT_COORDINATE_BINDING_PLAN_AUTHORIZATION_BASE_MAIN_SHA=a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b
OUTPUT_COORDINATE_BINDING_PLAN_SEMANTIC_PARENT_SHA=MILESTONE_OVERLAY_BINDING_REQUIRED
OUTPUT_COORDINATE_BINDING_PLAN_REVIEWED_OVERLAY_SHA=EXTERNAL_EXACT_TIP_REQUIRED
OUTPUT_COORDINATE_BINDING_OPERATION_STATUS=PLAN_ONLY_PENDING_EXACT_TIP_KIRO_REVIEW
OUTPUT_COORDINATE_BINDING_FREEZE_AUTHORIZED=false
OUTPUT_COORDINATE_BINDING_REAL_AUTHOR_AUTHORIZED=false

FAILED_REAL_AUTHOR_GRANT_SEMANTIC_PARENT_SHA=ce768a79eeddb36d3a150d09d850161a42338227
FAILED_REAL_AUTHOR_GRANT_REVIEWED_OVERLAY_SHA=ac04fddadaa7a5ae741c49a2960c20e83151aff9
FAILED_REAL_AUTHOR_PLAN_MERGED_MAIN_SHA=a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b
FAILED_REAL_AUTHOR_CAPABILITY_TREE_SHA256=939b8849d95eaf146efa528284d29d69f516c8aa400f432f1bed43009199a396
FAILED_REAL_AUTHOR_GRANT_STATUS=CONSUMED_F002_STARTUP_PAUSE
FAILED_REAL_AUTHOR_PROCESS_COUNT=1
FAILED_REAL_AUTHOR_SUBPROCESS_COUNT=0
FAILED_REAL_AUTHOR_EXIT_STATUS=1
FAILED_REAL_AUTHOR_STOP_STAGE=STARTUP
FAILED_REAL_AUTHOR_EXCEPTION=Refusal: F002: literal argv
FAILED_REAL_AUTHOR_BASELINE_COUNT=0
FAILED_REAL_AUTHOR_CONTROL_COUNT=0
FAILED_REAL_AUTHOR_REAL_INPUT_BYTES_READ=0
FAILED_REAL_AUTHOR_GOVERNED_BYTES_WRITTEN=0
FAILED_REAL_AUTHOR_PEAK_RSS_BYTES=1367023616
FAILED_REAL_AUTHOR_FORBIDDEN_ACCESS_COUNT=0

SEALED_STAGING_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
SEALED_DURABLE_FINAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/dea026ce561e480ba3436d3c1cbea9bbcae6a14b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
GRANTED_STAGING_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/16dbd7926a8c14d71595440a5ac4ba78b99e26ed/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
GRANTED_DURABLE_FINAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/16dbd7926a8c14d71595440a5ac4ba78b99e26ed/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
FAILED_REAL_AUTHOR_STAGING_PARTIAL_STATUS=ABSENT
FAILED_REAL_AUTHOR_STAGING_FINAL_STATUS=ABSENT
FAILED_REAL_AUTHOR_DURABLE_PARTIAL_STATUS=ABSENT
FAILED_REAL_AUTHOR_DURABLE_FINAL_STATUS=ABSENT

ACCEPTED_CORRECTED_V4_TREE_SHA256=939b8849d95eaf146efa528284d29d69f516c8aa400f432f1bed43009199a396
ACCEPTED_CORRECTED_V4_STATUS=IMMUTABLE_ACCEPTED_BUT_OUTPUT_COORDINATE_INELIGIBLE
ACCEPTED_CORRECTED_V4_DURABILITY_RSS_EVIDENCE=PROCESS_ATTESTED_80_PERCENT_CONFIDENCE
```

Tree `939b8849…` remains the sole historically accepted corrected-v4 candidate and
its `accepted=false` remains historical non-self-acceptance. It is not revoked,
rewritten or repaired. It is ineligible for a grant naming any output coordinate
other than its sealed argv, and this plan does not inspect or authorize the older
`dea026ce…` roots. Byte identity cannot turn an argv mismatch into authority or
raise the prior durability/RSS evidence above 80%.

#### 18.49.2 Fresh capability and future real-output coordinate set

The replacement freeze and the later real operation, if separately authorized,
must use these six presently absent single-assignment coordinates:

```text
FRESH_CAPABILITY_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4.partial
FRESH_CAPABILITY_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4
FRESH_CAPABILITY_PARTIAL_STATUS=ABSENT
FRESH_CAPABILITY_FINAL_STATUS=ABSENT

FRESH_REAL_STAGING_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
FRESH_REAL_STAGING_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
FRESH_REAL_DURABLE_PARTIAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
FRESH_REAL_DURABLE_FINAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
FRESH_REAL_STAGING_PARTIAL_STATUS=ABSENT
FRESH_REAL_STAGING_FINAL_STATUS=ABSENT
FRESH_REAL_DURABLE_PARTIAL_STATUS=ABSENT
FRESH_REAL_DURABLE_FINAL_STATUS=ABSENT
```

The successor freeze itself uses this exact fourteen-member synthetic vector and the
partial capability root as cwd:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4.partial/work-item-author-v4.py",
  "synthetic-freeze",
  "--fixture-spec",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4.partial/fixture-spec.json",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4.partial/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4.partial/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4.partial/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4.partial/freeze-manifest.json"
]
```

The successor must seal this exact twenty-member real vector:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4/work-item-author-v4.py",
  "author-packet",
  "--input-packet-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet",
  "--input-disposition",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json",
  "--staging-root",
  "/home/lauer/.cache/convmem-switchboard-provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--durable-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4/freeze-manifest.json"
]
```

Its synthetic cwd is exactly `FRESH_CAPABILITY_PARTIAL_ROOT`; its real cwd is exactly
`FRESH_CAPABILITY_FINAL_ROOT`. Its environment remains
exactly `LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONHASHSEED=0` and `PYTHONNOUSERSITE=1`, with no sixth key or inherited member.

The semantic correction changes only the source/fixture/command-contract path
constants needed to seal those exact roots and the identities mechanically derived
from those bytes. The new `author_packet_argv` remains exactly twenty members;
members `[9]` and `[11]` must equal `FRESH_REAL_STAGING_FINAL_ROOT` and
`FRESH_REAL_DURABLE_FINAL_ROOT` byte-for-byte. Its source, synthetic fixture and
validator must use that one shared literal vector. No runtime override, placeholder,
template expansion, environment substitution, alias, symlink, wrapper, rewrite or
normalization route is permitted.

All other source semantics remain frozen: corrected `unresolved_sha256:` grammar;
obsolete `unresolved:sha256:` rejection inside W001; `F001`–`F010` then
`W001`–`W042`; six capability roles; seven real-output roles; schemas;
serializers; packet-tree recipe; fixed-point identities; 22-event/two-null ledger;
durability barriers; one-process/zero-subprocess rule; five-key environment;
one-pass read, write and RSS ceilings; and zero forbidden access. F002 remains the
sole literal-argv control. This correction creates no alias, `W043`, `F011`, 53rd
control, schema field, role or alternate command path.

#### 18.49.3 Sequencing and proof obligations

The correction requires two separately reviewed and granted operations, never one
combined grant:

1. Kiro reviews this exact two-commit plan. Ryan may then decide whether to merge it;
   Kiro exact-main confirmation follows.
2. Ryan may issue one fresh two-SHA **synthetic capability-freeze** grant naming the
   reviewed plan SHAs and both absent `a94bc57…/v4(.partial)` roots. That grant may
   use only synthetic inputs and must not inspect packet/disposition content.
3. A result-binding plan records the new six-member tree, member hashes/sizes/modes,
   receipt, ledger, exact twenty-member argv and both `[9]`/`[11]` equalities. Kiro
   reviews that result; Ryan separately decides acceptance.
4. Only an accepted successor capability may enter a new real-author plan. That later
   plan must bind the four still-absent `a94bc57…/491ae60b…/v3(.partial)` roots and
   repeat exact-tip, merge, exact-main and fresh two-SHA Ryan-grant gates.

Before a synthetic-freeze grant is consumed, metadata-only preflight must prove all
six new coordinates absent and all immutable predecessors exact. Any pre-existence,
unexpected type, link, mode, identity or argv/root inequality is `PAUSE` with zero
processes and zero created paths. Any launched freeze process is one-shot: success,
failure or mismatch consumes the grant and coordinate; there is no retry, repair,
cleanup, deletion, resume or acceptance transfer.

Independent review must compare the sealed command-contract array, source constant,
fixture vector and planned roots directly, member by member. Checking only argv
length, source hash, tree digest or byte identity is insufficient. The review must
state the exact values at indices `[9]` and `[11]` and confirm that partial roots are
derived only by the unchanged transaction. This proof obligation is enforced under
existing F002; it is not a new runtime control.

#### 18.49.4 Authority boundary

This section authorizes only edits to the four Switchboard planning documents and
read-only exact-tip review. It authorizes no source write, capability root or file
creation, packet/disposition read, synthetic freeze, author execution, retry,
acquisition, implementation, PR creation or update, merge, deployment, real
OpenClaw, watch activation, live data, promotion or Gate D/W/D-V/E/F action.

The consumed §§18.48/10.46 grant cannot be reused. The absent `16dbd79…` roots do
not carry forward execution authority and are not selected by this correction. The
older sealed `dea026ce…` roots are neither inspected nor adopted. Only the future
two-step route in §18.49.3 can progress, each step under its own exact reviewed plan
and fresh Ryan grant.

### 18.50 Output-coordinate-corrected capability-freeze result binding

PR `#370` squash-merged the exact §§18.49/10.47 output-coordinate correction at
`956d74e8bab4a6c397a80a14a5709043b8b205ef`, byte-identical to reviewed overlay
`7b80c92b999282afe5edd614d4080bb4ebd8792e`, and Kiro returned exact-main PASS.
PR `#372` then squash-merged the reviewed current-state snapshot at
`bef5328123b279e38c9df075b070b9c352cdf1eb`. Ryan separately issued one exact
two-SHA synthetic-freeze grant naming semantic parent
`cfa8bb879af6efc785692eea3d64c6bdd2d83626`, reviewed overlay
`7b80c92b999282afe5edd614d4080bb4ebd8792e` and the fresh `a94bc57…`
capability coordinate. Metadata-only preflight proved all six selected capability
and future real-output coordinates absent and every immutable predecessor exact.

The sole fourteen-member no-site process completed a clean baseline, all 52 controls,
the 22-event ledger, row-zero durability and both coordinate-parent barriers before
atomically sealing the final capability root. It reported `PASS`, exited zero, read no
real packet or disposition content, used no forbidden external source and left all
four future real-author output coordinates absent. The one-shot grant is consumed.

The process result is technically `PASS`; `accepted=false` remains controlling. Kiro
must review this exact plan-only binding, after which Ryan separately decides whether
to accept the successor capability. Neither the process result, this edit nor Kiro
review authorizes the held real `author-packet` command.

#### 18.50.1 Exact sealed successor evidence

```text
OUTPUT_COORDINATE_CAPABILITY_BINDING_GRANT_SEMANTIC_PARENT_SHA=cfa8bb879af6efc785692eea3d64c6bdd2d83626
OUTPUT_COORDINATE_CAPABILITY_BINDING_GRANT_REVIEWED_OVERLAY_SHA=7b80c92b999282afe5edd614d4080bb4ebd8792e
OUTPUT_COORDINATE_CAPABILITY_BINDING_AUTHORIZATION_BASE_MAIN_SHA=bef5328123b279e38c9df075b070b9c352cdf1eb
OUTPUT_COORDINATE_CAPABILITY_BINDING_PLAN_MERGED_MAIN_SHA=956d74e8bab4a6c397a80a14a5709043b8b205ef
OUTPUT_COORDINATE_CAPABILITY_BINDING_PROCESS_EXIT_STATUS=0
OUTPUT_COORDINATE_CAPABILITY_BINDING_PROCESS_REPORTED_STATUS=PASS
OUTPUT_COORDINATE_CAPABILITY_BINDING_ACCEPTED=false
OUTPUT_COORDINATE_CAPABILITY_BINDING_ACCEPTANCE_STATE=PENDING_EXACT_TIP_KIRO_REVIEW_AND_RYAN_ACCEPTANCE
OUTPUT_COORDINATE_CAPABILITY_BINDING_COORDINATE_PARENT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b
OUTPUT_COORDINATE_CAPABILITY_BINDING_COORDINATE_PARENT_MODE=0700
OUTPUT_COORDINATE_CAPABILITY_BINDING_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4.partial
OUTPUT_COORDINATE_CAPABILITY_BINDING_PARTIAL_ROOT_PRESENT=false
OUTPUT_COORDINATE_CAPABILITY_BINDING_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4
OUTPUT_COORDINATE_CAPABILITY_BINDING_FINAL_ROOT_PRESENT=true
OUTPUT_COORDINATE_CAPABILITY_BINDING_FINAL_ROOT_MODE=0555
OUTPUT_COORDINATE_CAPABILITY_BINDING_MEMBER_COUNT=6
OUTPUT_COORDINATE_CAPABILITY_BINDING_MEMBER_MODE=0444
OUTPUT_COORDINATE_CAPABILITY_BINDING_TOTAL_BYTES=197259
OUTPUT_COORDINATE_CAPABILITY_BINDING_TREE_SHA256=e685ee056772c2c8831c4eb65ee23f5719c293bffd796501ff8e68029ccbc32f
OUTPUT_COORDINATE_CAPABILITY_BINDING_SOURCE_SIZE=148481
OUTPUT_COORDINATE_CAPABILITY_BINDING_SOURCE_LINE_COUNT=2952
OUTPUT_COORDINATE_CAPABILITY_BINDING_SOURCE_SHA256=e53b5d70cd6cf0a5c4cdd2cfbb782234ebab0353d15ee078a3ae55990df42c23
OUTPUT_COORDINATE_CAPABILITY_BINDING_RECEIPT_SHA256=f15b15f3b7d290a8d2ebfaf630921fab10c9d4779164f1ebea3b062f388868c4
OUTPUT_COORDINATE_CAPABILITY_BINDING_FREEZE_MANIFEST_SHA256=a75dd70a5eaa8420bc1c03cdf16a225a180672bb86604e3fa8db4c9973803ff9
OUTPUT_COORDINATE_CAPABILITY_BINDING_WRITE_LEDGER_SHA256=419a107bece7b8cd73e01b1ef9f72c2e428f9a13bd175004231f2bd33ffde28d
OUTPUT_COORDINATE_CAPABILITY_BINDING_COMMAND_CONTRACT_SHA256=168575b26ebcfdb7dc6aab19743e70ac5500c165bd3fac10c8ca5165ec305c5c
OUTPUT_COORDINATE_CAPABILITY_BINDING_DEPENDENCY_MANIFEST_SHA256=b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63
OUTPUT_COORDINATE_CAPABILITY_BINDING_FIXTURE_SHA256=d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f
OUTPUT_COORDINATE_CAPABILITY_BINDING_SYNTHETIC_INPUT_TREE_SHA256=9551fa86cb9bf33f757bf584a16d5d930da5006ee0145beb2a675f136f38b4ab
OUTPUT_COORDINATE_CAPABILITY_BINDING_SYNTHETIC_DISPOSITION_SHA256=758764a25432300fb098d5480f9fcebd7a7648cf319b3d623c7eb294a4f80a82
OUTPUT_COORDINATE_CAPABILITY_BINDING_SYNTHETIC_PACKET_TREE_SHA256=c1dc9a1012979c09cbc931d207af5dbf648031b76ff9be9abc5fcad5f431c00d
OUTPUT_COORDINATE_CAPABILITY_BINDING_SYNTHETIC_RESULT_SHA256=cc9a8a0323e18ce3d527f2799c6d312ea93922bc459a8d4a0a4028edf316cd6a
OUTPUT_COORDINATE_CAPABILITY_BINDING_EXTERNAL_RESULT_SHA256=e4abb793a6b19e9041accfb2d6b4ea079419383829e7a7a54fc2153746dba5a3
OUTPUT_COORDINATE_CAPABILITY_BINDING_EXTERNAL_RESULT_SIZE=32526
OUTPUT_COORDINATE_CAPABILITY_BINDING_PROCESS_COUNT=1
OUTPUT_COORDINATE_CAPABILITY_BINDING_SUBPROCESSES=0
OUTPUT_COORDINATE_CAPABILITY_BINDING_BASELINE_COUNT=1
OUTPUT_COORDINATE_CAPABILITY_BINDING_BASELINE_VIOLATION_COUNT=0
OUTPUT_COORDINATE_CAPABILITY_BINDING_CONTROL_COUNT=52
OUTPUT_COORDINATE_CAPABILITY_BINDING_CONTROLS_PASSED=52
OUTPUT_COORDINATE_CAPABILITY_BINDING_ACTUAL_FIRST_ID=F001
OUTPUT_COORDINATE_CAPABILITY_BINDING_ACTUAL_FAMILY_BOUNDARY=F010,W001
OUTPUT_COORDINATE_CAPABILITY_BINDING_ACTUAL_LAST_ID=W042
OUTPUT_COORDINATE_CAPABILITY_BINDING_EXPECTED_FIRST_ID=F001
OUTPUT_COORDINATE_CAPABILITY_BINDING_EXPECTED_FAMILY_BOUNDARY=F010,W001
OUTPUT_COORDINATE_CAPABILITY_BINDING_EXPECTED_LAST_ID=W042
OUTPUT_COORDINATE_CAPABILITY_BINDING_WRITE_EVENT_COUNT=22
OUTPUT_COORDINATE_CAPABILITY_BINDING_FORECAST_WRITTEN_BYTES=323537343
OUTPUT_COORDINATE_CAPABILITY_BINDING_OBSERVED_WRITTEN_BYTES=323537343
OUTPUT_COORDINATE_CAPABILITY_BINDING_PEAK_RSS_BYTES=1515155456
OUTPUT_COORDINATE_CAPABILITY_BINDING_FIXED_POINT_ITERATIONS=3
OUTPUT_COORDINATE_CAPABILITY_BINDING_DEPENDENCY_COUNT=76
OUTPUT_COORDINATE_CAPABILITY_BINDING_STOP_STAGE=null
OUTPUT_COORDINATE_CAPABILITY_BINDING_DURABILITY_RSS_EVIDENCE=PROCESS_ATTESTED_80_PERCENT_CONFIDENCE
```

The exact final members are:

| Path | Size | Mode | SHA-256 |
|---|---:|---:|---|
| `command-contract.json` | 3,544 | `0444` | `168575b26ebcfdb7dc6aab19743e70ac5500c165bd3fac10c8ca5165ec305c5c` |
| `dependency-manifest.json` | 10,921 | `0444` | `b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63` |
| `fixture-spec.json` | 476 | `0444` | `d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f` |
| `freeze-manifest.json` | 969 | `0444` | `a75dd70a5eaa8420bc1c03cdf16a225a180672bb86604e3fa8db4c9973803ff9` |
| `self-test-receipt.json` | 32,868 | `0444` | `f15b15f3b7d290a8d2ebfaf630921fab10c9d4779164f1ebea3b062f388868c4` |
| `work-item-author-v4.py` | 148,481 | `0444` | `e53b5d70cd6cf0a5c4cdd2cfbb782234ebab0353d15ee078a3ae55990df42c23` |

Read-only verification reproduced every member size, mode, single-link identity and
digest; the compact sorted-key canonical six-row inventory reproduces tree
`e685ee05…`. `freeze-manifest.json` remains nonrecursive: it hashes the other five
members and never itself. The 22-event receipt ledger has null digests only for
`self-test-receipt.json` and `freeze-manifest.json`; hashing its canonical event array
reproduces `419a107b…`. The external process result is not a seventh member.

#### 18.50.2 Exact qualification proof and evidence limit

The clean baseline returned `PASS`, created neither packet nor result and had zero
violations. The sealed receipt contains exactly 52 unique passing rows in required
raw-ID order `F001`–`F010`, then `W001`–`W042`; actual and expected first ID,
family boundary and last ID match. Corrected `unresolved_sha256:` remains the sole
production grammar, while obsolete `unresolved:sha256:` remains a W001 negative
case. No alias, normalization, dual-prefix path, `W043`, `F011` or 53rd control
exists.

The fixture preserves 1,221 components, 19 disputes, twenty batches, 49 pages,
98,608 unresolved IDs, 30,402 owned paths, 30,421 runtime paths and 1,384 nested
edges. Synthetic packet and disposition reads were exactly `55,760,899` and
`8,383,504` bytes. Forecast and observed writes both equal `323,537,343`, below the
unchanged one-GiB ceiling. Process-reported peak RSS was `1,515,155,456`, below the
unchanged `2,147,483,648` ceiling.

Every required durability counter is process-reported as exactly one:

```text
row_zero_setup_file_fsync_count=1
row_zero_setup_directory_fsync_count=1
row_zero_governed_file_fsync_count=1
row_zero_governed_directory_fsync_count=1
row_zero_event_one_write_count_after_governed_fsync=1
coordinate_parent_pre_rename_open_count=1
coordinate_parent_pre_rename_fsync_count=1
coordinate_parent_post_rename_open_count=1
coordinate_parent_post_rename_fsync_count=1
```

Every prohibited access counter is zero:

```text
REAL_INPUT_READ_BYTES=0
NETWORK_REQUESTS=0
RUNTIME_READS=0
RETAINED_SOURCE_READS=0
REPOSITORY_READS=0
ACQUIRED_BYTES=0
CREDENTIAL_ACCESS=0
SUBPROCESSES=0
```

The member identities, modes, sizes, tree, receipt control order, command vectors,
ledger digest and continued output-root absence are independently reproducible from
sealed bytes and metadata. The nine durability counters and peak RSS are not: they
remain process-attested at 80% confidence. Neither this binding, byte identity nor
Kiro review may raise that ceiling without genuinely independent evidence.

#### 18.50.3 Whole-vector proof, immutability and held acceptance

The sealed command contract contains exactly fourteen synthetic argv members and
twenty real argv members. The synthetic cwd is the now-absent `.partial` root; the
real cwd is the sealed final root. Real argv `[9]` equals the still-absent
`a94bc57…/491ae60b…/v3` staging final root and `[11]` equals the still-absent
durable final root byte-for-byte. The environment contains exactly the five frozen
keys and no inherited sixth key. Source, fixture and command contract share the whole
vector; F002 remains the sole literal-argv control.

The coordinate parent, final root, six members, source, receipt, manifests, external
result claim and consumed grant are immutable. They may not be changed, chmodded,
deleted, renamed, copied, hard-linked, imported, executed again, repaired or
reinterpreted; the absent `.partial` sibling may not be recreated. A review mismatch
is `PAUSE`, not authority to regenerate the candidate.

Tree `939b8849…` remains the historically accepted corrected-v4 candidate but is
output-coordinate-ineligible. Tree `e685ee05…` is the sole new successor candidate,
not yet accepted. If Kiro returns PASS on this exact two-commit binding, Ryan may
separately decide whether to accept it; Kiro PASS does not self-accept the process
result. Only a later explicit acceptance may make `e685ee05…` the sole accepted
output-coordinate-corrected capability.

Acceptance still grants no real read or author execution. A held real operation
requires a new plan, exact-tip review, merge, exact-main confirmation and separate
Ryan two-SHA grant naming the accepted successor, immutable packet/disposition and
the four still-absent `a94bc57…/491ae60b…/v3(.partial)` coordinates. No prior
real-author or synthetic-freeze grant is reusable.

#### 18.50.4 Frozen surrounding contract and authority boundary

Every §18.31–§18.49 schema, mapping, role, parser, serializer, candidate/locator
rule, identity adapter, packet-tree recipe, cardinality, 22-event/two-null ledger,
fixed-point rule, `W001`–`W042`, `F001`–`F010`, `F010`-only drift control,
fourteen-/twenty-member no-site argv, `F002` slices, row-zero and coordinate-parent
durability transition, canonical stdlib dependency reader, one-process/write/RSS
ceilings, zero-access boundary and held one-pass real contract remain unchanged. No
new schema field, file role, sidecar, wrapper, reader, acceptance exception or second
synthetic attempt is introduced.

This section authorizes only the four Switchboard planning-document edits and exact-
tip review. It authorizes no root/file/source creation, execution, packet/disposition/
repository/runtime/retained-source read, work-item packet/result, retry, network,
subprocess, acquisition, ownership/license selection, binary repair, build,
publication, CI admission, product/test/config/R2b change, implementation, PR `#342`
update, PR creation, merge, deployment, real OpenClaw, live data, watch activation,
promotion or Gate D/W/D-V/E/F action. The consumed synthetic-freeze grant cannot be
reused.

### 18.51 Output-coordinate-corrected one-shot real work-item author boundary

PR `#374` squash-merged the exact §§18.50/10.48 successor-capability binding at
`43b51214d775deb900d13bc8aedab93b14e41b90`, byte-identical to reviewed overlay
`7f9df36b55057cea27a93799b8193001f53c4905`; all six checks passed and Kiro
returned exact-tip and exact-main PASS. PR `#376` then squash-merged the reviewed
acceptance snapshot at `2c72c197f84e89e595723d5d425692b3428666e8`, byte-identical
to reviewed tip `8eb83dbb748408ec2eb64d689fa9f33ff3b5d4c0`; all six checks
passed and Kiro returned exact-main PASS. Ryan's external acceptance makes tree
`e685ee056772c2c8831c4eb65ee23f5719c293bffd796501ff8e68029ccbc32f`
the sole accepted output-coordinate-corrected v4 author-capability candidate.
Process-emitted `accepted=false` remains historical non-self-acceptance. The nine
durability counters and peak RSS remain process-attested at 80% confidence; neither
review, merge nor acceptance independently reproduced those runtime facts.

This section closes the exact boundary for one possible future real `author-packet`
process. It is plan-only and grants no process, read or root authority. Unlike the
consumed §§18.48/10.46 attempt, the accepted command contract itself seals the same
`a94bc57…/491ae60b…/v3` staging and durable finals named below. No caller-selected
root substitution is permitted.

#### 18.51.1 Accepted author, immutable inputs and single-assignment outputs

```text
OUTPUT_COORDINATE_REAL_AUTHOR_PLAN_AUTHORIZATION_BASE_MAIN_SHA=2c72c197f84e89e595723d5d425692b3428666e8
OUTPUT_COORDINATE_REAL_AUTHOR_PLAN_SEMANTIC_PARENT_SHA=MILESTONE_OVERLAY_BINDING_REQUIRED
OUTPUT_COORDINATE_REAL_AUTHOR_PLAN_REVIEWED_OVERLAY_SHA=EXTERNAL_EXACT_TIP_REQUIRED
OUTPUT_COORDINATE_REAL_AUTHOR_OPERATION_STATUS=PLAN_ONLY_PENDING_EXACT_TIP_KIRO_REVIEW
OUTPUT_COORDINATE_REAL_AUTHOR_AUTHORIZED=false

OUTPUT_COORDINATE_REAL_AUTHOR_CAPABILITY_ROOT=/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4
OUTPUT_COORDINATE_REAL_AUTHOR_CAPABILITY_COORDINATE_PARENT_MODE=0700
OUTPUT_COORDINATE_REAL_AUTHOR_CAPABILITY_ROOT_MODE=0555
OUTPUT_COORDINATE_REAL_AUTHOR_CAPABILITY_TREE_SHA256=e685ee056772c2c8831c4eb65ee23f5719c293bffd796501ff8e68029ccbc32f
OUTPUT_COORDINATE_REAL_AUTHOR_CAPABILITY_MEMBER_COUNT=6
OUTPUT_COORDINATE_REAL_AUTHOR_CAPABILITY_MEMBER_MODE=0444
OUTPUT_COORDINATE_REAL_AUTHOR_CAPABILITY_TOTAL_BYTES=197259
OUTPUT_COORDINATE_REAL_AUTHOR_SOURCE_SIZE=148481
OUTPUT_COORDINATE_REAL_AUTHOR_SOURCE_LINE_COUNT=2952
OUTPUT_COORDINATE_REAL_AUTHOR_SOURCE_SHA256=e53b5d70cd6cf0a5c4cdd2cfbb782234ebab0353d15ee078a3ae55990df42c23
OUTPUT_COORDINATE_REAL_AUTHOR_COMMAND_CONTRACT_SHA256=168575b26ebcfdb7dc6aab19743e70ac5500c165bd3fac10c8ca5165ec305c5c
OUTPUT_COORDINATE_REAL_AUTHOR_DEPENDENCY_MANIFEST_SHA256=b96ea9a50e60f8aad2cf8cf2861a81cb3c49bcd557d728bceb4f7a5ec17cad63
OUTPUT_COORDINATE_REAL_AUTHOR_FIXTURE_SHA256=d4e2a09b9ee93ee8c4c59ac6e622da946d58a2f3bd96c7e38e1c0a3b6418966f
OUTPUT_COORDINATE_REAL_AUTHOR_FREEZE_MANIFEST_SHA256=a75dd70a5eaa8420bc1c03cdf16a225a180672bb86604e3fa8db4c9973803ff9
OUTPUT_COORDINATE_REAL_AUTHOR_RECEIPT_SHA256=f15b15f3b7d290a8d2ebfaf630921fab10c9d4779164f1ebea3b062f388868c4
OUTPUT_COORDINATE_REAL_AUTHOR_WRITE_LEDGER_SHA256=419a107bece7b8cd73e01b1ef9f72c2e428f9a13bd175004231f2bd33ffde28d
OUTPUT_COORDINATE_REAL_AUTHOR_DURABILITY_RSS_EVIDENCE=PROCESS_ATTESTED_80_PERCENT_CONFIDENCE

OUTPUT_COORDINATE_REAL_AUTHOR_INPUT_PACKET_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet
OUTPUT_COORDINATE_REAL_AUTHOR_INPUT_PACKET_TREE_SHA256=491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5
OUTPUT_COORDINATE_REAL_AUTHOR_INPUT_PACKET_MANIFEST_SHA256=6791d33a82bd0f1e3fdbda072ae50aa296953b6a365194564090085541784fa4
OUTPUT_COORDINATE_REAL_AUTHOR_INPUT_PACKET_MEMBER_COUNT=902
OUTPUT_COORDINATE_REAL_AUTHOR_INPUT_PACKET_FILE_COUNT=663
OUTPUT_COORDINATE_REAL_AUTHOR_INPUT_PACKET_DIRECTORY_COUNT=239
OUTPUT_COORDINATE_REAL_AUTHOR_INPUT_PACKET_BYTES=654147403
OUTPUT_COORDINATE_REAL_AUTHOR_INPUT_DISPOSITION=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json
OUTPUT_COORDINATE_REAL_AUTHOR_INPUT_DISPOSITION_SHA256=45442e93958e7f0c4a2e4bf474d0b7430653fc0320ab1bad1b8222501b830669
OUTPUT_COORDINATE_REAL_AUTHOR_INPUT_DISPOSITION_BYTES=8383806
OUTPUT_COORDINATE_REAL_AUTHOR_TOTAL_INPUT_BYTES=662531209

OUTPUT_COORDINATE_REAL_AUTHOR_STAGING_PARTIAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
OUTPUT_COORDINATE_REAL_AUTHOR_STAGING_FINAL_ROOT=/home/lauer/.cache/convmem-switchboard-provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
OUTPUT_COORDINATE_REAL_AUTHOR_DURABLE_PARTIAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3.partial
OUTPUT_COORDINATE_REAL_AUTHOR_DURABLE_FINAL_ROOT=/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3
OUTPUT_COORDINATE_REAL_AUTHOR_STAGING_PARTIAL_STATUS=ABSENT
OUTPUT_COORDINATE_REAL_AUTHOR_STAGING_FINAL_STATUS=ABSENT
OUTPUT_COORDINATE_REAL_AUTHOR_DURABLE_PARTIAL_STATUS=ABSENT
OUTPUT_COORDINATE_REAL_AUTHOR_DURABLE_FINAL_STATUS=ABSENT
```

Grant-time preflight is metadata-only. It must reproduce the accepted coordinate-
parent mode `0700`, final-root mode `0555`, six single-link `0444` member identities,
sizes and tree; verify the packet root and disposition metadata; and `lstat` all four
outputs without opening packet members or disposition content. Any identity mismatch,
unexpected type/link/mode or pre-existing output returns `PAUSE` with zero processes,
zero content bytes read and zero created paths and consumes any later one-shot grant.
Preflight may create no parent, partial, final, author copy, wrapper, log or sidecar.

The milestone-only overlay binds the semantic parent after that commit exists. Kiro's
reviewed overlay remains externally supplied because a commit cannot contain its own
SHA. A future grant must name both full plan SHAs, the accepted capability tree and
all four exact absent coordinates; symbolic values are not execution authority.

#### 18.51.2 Exact direct-execve command

The only admissible command is this sealed twenty-member array:

```json
[
  "/home/lauer/miniforge3/bin/python3",
  "-S",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4/work-item-author-v4.py",
  "author-packet",
  "--input-packet-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/packet",
  "--input-disposition",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-lock/3402e62a8479011814bfa76ce9e1c3269dc34350/74a12c725ac3bad4fc09ef9bf9f15ce06d42c75484a6a62f4912426b2cba507b/schema-v3/review/review-disposition.json",
  "--staging-root",
  "/home/lauer/.cache/convmem-switchboard-provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--durable-root",
  "/home/lauer/.local/share/convmem-openclaw-evidence/provenance-work-items/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/491ae60bf98a831a1ee09c2ca207b1d9f24bb329ac6d5af79acce3379b5d93a5/v3",
  "--command-contract",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4/command-contract.json",
  "--dependency-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4/dependency-manifest.json",
  "--receipt",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4/self-test-receipt.json",
  "--freeze-manifest",
  "/home/lauer/.cache/convmem-switchboard-work-item-author-freeze/a94bc57ae7d01f3e5e449a8bd43e75ba7e597c8b/v4/freeze-manifest.json"
]
```

The cwd is exactly the accepted final root. The environment is exactly
`LANG=C.UTF-8`, `LC_ALL=C.UTF-8`, `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONHASHSEED=0` and `PYTHONNOUSERSITE=1`. Launch uses direct `execve` semantics:
no shell, wrapper, extra argument, sixth/inherited environment member, inherited file
descriptor, copied source or alternate import. Zero-based argv values `[9]` and `[11]`
must equal the staging and durable final roots above byte-for-byte. The accepted source
must prove `sys.flags.no_site == 1`, the sealed dependency manifest and literal argv
before opening real input.

#### 18.51.3 One pass, transaction, ceilings and evidence

The sole process independently revalidates the capability and both immutable inputs.
It opens each of the 663 packet files and the disposition at most once, consumes
exactly `662,531,209` governed bytes and validates the complete 902-member packet-tree
identity before output creation. Only then may it exclusively create both partials
and perform the unchanged seven-role fixed-point, file/directory-`fsync`, coordinate-
parent-`fsync` and atomic-publication transaction. Staging and durable copies must be
byte-identical.

Structural success remains exactly 1,221 component items plus 19 ownership-dispute
items, 1,240 primary items, 98,608 unresolved IDs, 30,421 paths (30,402 owned),
1,384 edges, twenty batches and 49 pages in
`convmem.switchboard.work-item-authoring-result.v2`. The sole production grammar is
`unresolved_sha256:` plus 64 lowercase hex characters; existing W001 rejects obsolete
`unresolved:sha256:`. No alias, normalization, `W043`, `F011`, 53rd control, schema
or role change exists. Structural PASS cannot resolve origin, ownership, provenance,
licensing or build eligibility.

The supervisor enforces one process, zero subprocesses, peak RSS at most
`2,147,483,648`, writes at most `2,147,483,648` bytes per output root and at most
`4,294,967,296` total. Network, runtime, repository, retained-source, credential and
acquisition access remain zero. Success, mismatch or failure consumes the one-shot
grant. There is no retry, repair, resume, cleanup, deletion or second input pass.

Returned evidence must include exit/reported status, baseline/control counts, exact
`F001`–`F010` then `W001`–`W042` order, bytes read/written by role/root, peak RSS,
all durability and forbidden-access counters, coordinate states, any final tree
identities and external-result hashes/sizes. The result does not self-hash or accept
itself. Evidence about this future process is separate from the accepted capability's
historical durability/RSS facts and cannot retroactively lift their 80% ceiling.

#### 18.51.4 Progression and authority boundary

The only progression is exact-tip Kiro review of this two-commit plan, Ryan's PR and
merge decision, exact-main confirmation, then a separate Ryan two-SHA decision on one
fresh execution grant. Success advances only to a plan-only result binding and an
independent review of the exact 1,240-item/98,608-ID/1,384-edge/twenty-batch/49-page/
19-dispute unions. It grants no origin, acquisition, repair, build, publication,
CI-admission, implementation, deployment or real-OpenClaw authority.

Every §18.31–§18.50 schema, mapping, role, parser, serializer, identity adapter,
packet-tree recipe, cardinality, 22-event/two-null ledger, fixed-point rule, control,
argv slice, durability barrier, canonical stdlib dependency reader, ceiling and zero-
access boundary remains unchanged. Tree `939b8849…` remains immutable and output-
coordinate-ineligible. No prior real-author or synthetic-freeze grant is reusable.

This section authorizes only edits to the four Switchboard planning documents and
read-only exact-tip review. It authorizes no packet/disposition content read, root or
file creation, author execution, retry, cleanup, deletion, acquisition, build,
publication, implementation, PR creation/update, merge, deployment, real OpenClaw,
live data, watch activation, promotion or Gate D/W/D-V/E/F action.

## Jargon TL;DR

| Term | Meaning |
|---|---|
| ACP | OpenClaw's Agent Client Protocol route for launching external coding harnesses; installed version `2026.3.2` runs these sessions on the host. |
| Bound scope | The immutable operator-owned project, site, and domain ceiling loaded by the strict ConvMem server at startup. |
| ConvMem resource | An MCP `resources/*` surface such as `memories://brief`, separate from MCP tools and absent in the strict profile. |
| Deep module | A narrow internal interface that owns the full scope-policy complexity so MCP handlers remain thin. |
| Evidence envelope | The stable JSON wrapper marking retrieved corpus content as data with no instruction authority. |
| Full profile | ConvMem's existing MCP profile that exposes brief tools and resources in addition to retrieval tools. |
| Native memory | OpenClaw's `memory-core` or another OpenClaw memory plugin, disabled in the isolated integration profile. |
| Activation supervisor | The trusted main process that pins one snapshot/session and commits bounded output; an external controller/system manager owns containment and retirement. |
| Authority disposition | An operator-owned, content-addressed approval, rejection, revocation, withdrawal, or supersession decision bound to exact assertion semantics. |
| Lexical kernel | The deterministic, version-pinned tokenization and integer-ranking algorithm used by strict search instead of embeddings or a shared vector index. |
| Monotonic supersession | Once a valid successor supersedes an assertion, that predecessor stays historical even if later successors are revoked or themselves superseded. |
| Project binding | An opaque, service-owned membership assertion assigned only by trusted ingestion and resolved through an operator-owned registry; ordinary corpus metadata and paths cannot supply it. |
| Scope oracle | A response difference that lets a caller infer whether an otherwise inaccessible record exists. |
| Pylint pair identity | The sorted two-module identity extracted from one raw `R0801` message; line spans are evidence, not selectors. |
| Component work item | The sole primary planning record for one frozen component, its six component gaps, uniquely owned files, origin gaps, nested-edge assignments and packet citations. |
| Ownership-dispute work item | The sole primary planning record for one unowned or multiply-owned path; it preserves all four gaps without choosing an owner. |
| Planning batch | One of twenty deterministic component scheduling views; it owns nothing and cannot multiply an operation budget. |
| Verification page | One of 49 deterministic unresolved-ID audit views; it proves coverage but cannot close or assign a row. |
| Candidate record | A byte-preserving, packet-cited lead whose planning state never establishes origin, ownership, licensing or access authority. |
| Closed command contract | A canonical command description with an exact schema, cwd and literal argv for each admitted verb; flag names, values and order cannot be chosen by the caller. |
| Startup isolation | Launching the bound interpreter with literal `-S`, then proving `sys.flags.no_site == 1` and a dependency closure free of global/user site-package startup code before any governed output. |
| Standard-library dependency reader | The sole internal boundary that hashes one canonical imported-module origin; it may tolerate a stable regular-file hard-link count without discovering or authorizing any alternate name. |
| Packet-tree identity | A SHA-256 over the exact canonical inventory of every strict descendant of an immutable packet root; directory rows and regular-file rows have different closed shapes, and the root mode is verified outside the hash. |
| Pylint semantic identity | The canonical message fields compared across raw Pylint reports; raw report order and bytes remain evidence but are not the verdict oracle. |
| Strict generation | A derivative of one exact cumulative authority head; atomic publication may instead select no serving generation. |
| Strict profile | The proposed `openclaw-strict` ConvMem MCP surface containing only `search`, `unresolved`, and `related`, with no resources. |
| Track A | ConvMem session-chat indexing used for handoff evidence; it is not a durable decision record. |
| Ordinary/qualified partition | The proof that every collected repository pytest node runs exactly once in its applicable ordinary (`O`) or qualified (`Q`) environment, with no gaps or overlap. |
| Fenced publication | A lineage state that deliberately makes authority unavailable while a publication operation is unresolved. |
| Authority-content identity | The content-derived R2b identifier computed from the canonical governed-member manifest; it attests bytes and does not authorize capture. |
| Qualified-runtime delivery packet | The exact archive, inventory, extraction, compatibility, provenance and replacement contract for making the frozen strict-test runtime available to CI; it is not runtime qualification of real OpenClaw. |
| Replacement delivery set | The inseparable runtime archive, compliance/corresponding-source archive and canonical manifest built from a complete reviewed component lock after the first archive failed publication provenance/licensing review. |
| Component lock | The canonical file-to-component, binary/source artifact, recipe, license/notice and source-delivery mapping; installed metadata or an SBOM alone is only an input. |
| Provenance-lock packet | The canonical immutable ledgers, content-addressed evidence objects, manifest and independent disposition that prove the component lock is complete before any replacement build. |
| CycloneDX revision projection | The schema-v3 exact-object rule that projects the immutable 40-lowercase-hex GitHub revision only for the one hash-bound `base64` component whose raw `version` member is absent; null or any other missing version stays `PAUSE`. |
| Source authority | An exact original distributor/project, signed index/checksum, immutable source revision or retained package/build record permitted by the grant; a search result, ambient cache or current-host inference is not authority. |
| Licensing disposition | The fail-closed public-redistribution result. `PAUSE` means byte integrity may pass while publication remains forbidden. |
| Pre-acquisition planning contract | The lossless component/obligation partition and exact operation requirements used to prepare later grant-ready acquisition packets; it authorizes no read or request. |
| Clean replacement | Fresh bytes built from independently locked inputs and recipes; never a repaired or prefix-rewritten rejected binary. |
| Capability freeze | An immutable author package whose self-test executes the same production path later used on real input; a synthetic-only command is not a real-author capability freeze. |
| Write ledger | The deterministic ordered accounting of every regular-file byte written by the v4 freeze; it proves the transaction stayed within its reviewed aggregate cap without allowing sparse, linked or compressed shortcuts. |
| Aggregate control-order validator | The single pre-write check that indexes all 52 self-test receipts by exact ID and emits them only in complete raw-UTF-8 order; family insertion order or a process-reported PASS cannot replace it. |
| Synthetic predecessor identity | A domain-separated test-only SHA-256 supplied to the unchanged result builder so a disposable synthetic result can exercise the real field without claiming or recursively hashing the receipt under construction. |
| Row-zero durability transition | The exact file-`fsync` then directory-`fsync` boundary that must complete for the externally created author before ledger event 1 may create any directory or file. |
| Coordinate-parent durability barrier | An exact no-follow directory-handle `fsync` on the single parent shared by the partial and final roots, once before and once after atomic rename; it grants no descendant content-read authority. |

**TL;DR:** [Arc ConvMem Switchboard] Bounded M0–M8 passed at `8010fb0`, and complete bounded M11
evidence plus Kiro conformance passed at preserved candidate `cd60cf19`. The advanced-main
reconstruction and inner-role correction established the fresh three-tip differential at
`65bbfd6f`; §18.18's first Pylint correction then reached `c71d37a` but paused exact acceptance at
456 findings / 71 `R0801`. Section 18.19's test-local correction and a fresh differential passed at
`caec5c6`, but exact Pylint acceptance paused because the old 454-total rule did not freeze
`R0401` enumeration. Section 18.20's paired seeded Pylint rule then passed at `9da6dd98`; final M8
run 1 paused because two passing current-main safety nodes raised the unchanged selected legacy
suite from 116/115 to 118/117. Section 18.21 preserves that PAUSE and freezes only the exact
one-path/two-integer successor correction, with selectors, deselections and test logic unchanged.
The first qualified-runtime archive later passed local byte validation and Kiro packet review but
failed independent publication provenance/licensing review. Section 18.24 keeps that archive
immutable and rejected, and defines a new three-role replacement delivery set whose component
lock, build, final packet and publication require separate reviews and Ryan grants. Exact-tip Kiro
PASSed that replacement plan at `3402e62a`. Section 18.25 now freezes the provenance-lock
packet's canonical schema, exact packet/review roots, source-authority boundary and negative
controls without creating evidence; exact-tip Kiro review of this schema is next and authorizes no
provenance execution. The first offline P0 attempt later stopped at one CycloneDX component believed
to have a null version. Section 18.26 preserved schema v1 and defined schema v2, but the single
granted v2 run proved the raw `version` member is absent and correctly stopped without a result or
durable packet. Section 18.27 preserves both rejected attempts and defines only a fresh-root
schema-v3 exact-object absent-member projection; it authorizes no collector freeze, retry or read.
Section 18.34 binds the successful six-file synthetic retry but records that its frozen
source has no real `author-packet` command. It therefore defines a fresh v4 capability
freeze and one-pass real-read contract without authorizing either execution.
Section 18.35 records the zero-root v4 budget preflight PAUSE, proves the inherited
64-MiB synthetic write cap impossible and replaces only that cap with a hard 1-GiB
maximum plus exact pre-write ledger accounting. The full-cardinality shared production
path, 52 controls, 2-GiB RSS limit and later real-run contract remain unchanged; the
next granted preflight then stopped before root/source/process on a receipt/result hash
cycle. Section 18.36 replaces only the synthetic result's two receipt-binding values
with exact domain-separated predecessor identities while preserving the unchanged
result builder and requiring actual reviewed v4 identities on the real path. Kiro
passed that correction, but the next granted preflight stopped before root/author/
process/read/write because `F002` lacked its literal real argv. Section 18.37 closes
the exact nine-key command contract, distinct synthetic/real cwd and argv values and
one order-only `F002` representative. Kiro passed the exact §18.38 packet-tree
successor at `991f488`, but the next granted preflight stopped before root, author,
process, read or write because global site initialization would import third-party
`_distutils_hack`. Section 18.39 adds only literal `-S` to both argv vectors, requires
`sys.flags.no_site == 1`, excludes site-package dependency origins and shifts the sole
`F002` slice indices mechanically. Every schema, environment key, control, root and
ceiling remains unchanged. The separately granted process then sealed the exact six-
file v4 root with a clean baseline and `52/52` controls, but acceptance correctly
remained `PAUSE`: setup did not prove row-zero file durability before ledger event 1.
Section 18.40 preserves that root as immutable rejected evidence and defines only a
fresh-root retry whose setup and governed process both complete file-then-directory
`fsync` before event 1. That retry proved row-zero durability and passed all controls,
but its audit hook rejected the coordinate-parent pre-rename directory open. Section
18.41 preserves sealed partial `a9ceaa06…`, keeps its sibling final absent and defines
only fresh `b7a8ade…` coordinates plus two exact phase-bound parent-directory
barriers without widening content-read authority. Section 18.42 then preserved the
one-file `99e4939d…` PAUSE and admitted stable link counts only inside the canonical
stdlib dependency reader. That correction passed Kiro at `946b469`; the granted
retry sealed final tree `d399e356…` and reported PASS, but acceptance paused because
receipt `8d3ecbe0…` concatenated W controls before F controls. Section 18.43 preserves
that final root as immutable rejected evidence and defines only fresh `946b469…`
coordinates plus exact complete raw-ID receipt validation before output. Kiro review
and a fresh Ryan two-SHA grant are mandatory.
Real OpenClaw, live data, PR, merge, deployment and promotion remain blocked.
