# Architecture Plan — OpenClaw orchestration with a bounded ConvMem evidence surface

**Status:** ASTRA FINAL REVIEW ON COMMIT `7809f20` BLOCKED BUILD; STATE,
REPLAY, RECOVERY, LIFECYCLE, AND FRESHNESS CONTRACTS CORRECTED FOR RE-REVIEW —
no implementation, OpenClaw configuration, live-data use, production smoke, or
capture is authorized

**Date:** 2026-09-20

**Arc:** none (ad-hoc integration)

**Authority:** Codex architecture/planning lane. Astra's independent final
review of commit `7809f20dc53d9dd19f765c3ec3214a3df54ca5bf` found the
previous scope/isolation corrections materially useful but blocked build on an
unfinished authority/state model, replay identity, payload binding,
publication recovery, OpenClaw lifecycle shutdown, and snapshot/session
revocation. This revision resolves those architecture choices and is paired
with an execution-complete build plan. Kiro remains the required binary
design-review lane and Ryan remains the approval and execution authority.
Neither Astra nor Claude authorized implementation.

**Supersedes for review:** the untracked local draft whose SHA-256 was
`9846e4df1211359b30427fc4ceebe108616e1dd6de9cb773648ed6cf0ed67f09`.

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

The trusted computing base is limited to the reviewed ConvMem strict-scope
module, the ingest-owned project-binding registry, the fixed connector plugin,
the operator-owned scope file, and the installed OpenClaw binary/config
revision that passed the gate.

## 3. Authority and data ownership

1. ConvMem's append-only ledger remains the durable fact and evidence
   authority. The bound authority snapshot is an immutable, content-addressed
   read model derived from ledger records plus operator-owned disposition
   artifacts; it cannot introduce or approve a fact and is not a second
   authority.
2. Chroma remains a rebuildable serving projection, never the sole authority.
3. Git, GitHub, and project-native tools remain authoritative for live project
   state.
4. OpenClaw owns only workflow coordination and transient request state.
5. OpenClaw native memory is disabled in the isolated integration profile.
6. ConvMem durable writes remain Ryan-run CLI operations. No MCP or OpenClaw
   tool may expose `record`, `approve`, `add`, `index`, `verify`, or an
   equivalent write path.
7. Retrieved evidence has zero instruction authority. It cannot grant tool
   access, alter scope, authorize writes, or change completion state.

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
`openclaw --help`, and `openclaw config validate --help` plus their SHA-256
digests. Exact integration-config validation remains Gate D evidence because
Gate A does not authorize creating a live profile or config.

Phase 1 therefore uses a narrow OpenClaw plugin that is an MCP client for a
local ConvMem strict-profile subprocess. It contains no retrieval or scope
policy. It translates three fixed plugin tool calls to MCP stdio and returns
the server response unchanged inside an untrusted-evidence envelope.

The connector must spawn with a fixed executable, fixed argument vector, fixed
working directory, explicitly constructed environment, and no shell. The child
environment starts empty; it does not copy `process.env`. A closed launch
schema supplies fixed reviewed values for `CONVMEM_MCP_PROFILE`,
`CONVMEM_BOUND_READ_SCOPE_FILE`, `CONVMEM_PROJECT_BINDING_REGISTRY_FILE`,
`CONVMEM_STRICT_CONFIG_FILE`, fixed `HOME`, minimal `PATH`, and locale
variables. Every other variable is absent. The strict config is a new closed,
read-only schema containing only the bound projection root and read-only store
parameters; credential, provider, API-key, model, watch, ingest, and write keys
are rejected. The connector launches a dedicated strict entry point that
selects and validates `openclaw-strict` before importing general ConvMem config
or any module that performs home-directory credential lookup. It never uses the
legacy `CONVMEM_CONFIG` loader. Fixed `HOME` points to an empty service home
that contains no ConvMem or provider credentials.

Strict server startup hard-ignores and tests hostile values for legacy
`CONVMEM_READ_SCOPE_DOMAIN`, `CONVMEM_READ_SCOPE_FILE`, `CONVMEM_CONFIG`, and
credential variables. Query text, selectors, ledger IDs, channel messages, and
corpus content may never influence the executable path, arguments before the
MCP protocol boundary, environment keys or values, scope-file path,
project-binding-registry path, strict-config path, or working directory.

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
  Gate B must extend, not bypass, those boundaries.
- `chroma_store.py:300-325` and `file_generation_store.py:718-760` query shared
  serving indexes and have no immutable bound-scope projection contract.
- `chroma_store.py:219-232,418-435` provides additional summary/unit metadata
  write paths, while `provenance_binding.py:276-295` currently passes unknown
  keys through and `chroma_write_store.py` gates production writers without
  enforcing the reserved authorization prefix.
- Metadata also crosses `chroma_store.py:286,480,619`,
  `file_generation_store.py:165`, `mixed_mode_control.py:64`, and
  `eval_corpus/shadow_build.py:386`; the strict prefix guarantee requires an
  audited writer census, not a hand-picked method list.
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
  "authority_snapshot": "authority:convmem-coding:fixture-v1",
  "serving_projection": "scope:convmem-coding:v1",
  "max_snapshot_age_seconds": 86400
}
```

`project`, `allowed_project_bindings`, `domain`, `authority_snapshot`, and
`serving_projection` are mandatory and non-empty.
`max_snapshot_age_seconds` is a mandatory integer from 60 through 86400; it is
an operator policy, not a caller selector. Schema v2 requires
`allowed_project_bindings` to
contain exactly one binding. That binding must resolve in the service-owned
registry to the same canonical project, bound-domain root, and site policy
named by the scope; all reviewed source registrations for the audience live
inside it, so relations across sources remain same-binding. Zero or multiple
bindings prevent startup. `site_mode` is either `exact` or `not_applicable`. `site`
is mandatory and non-empty only in `exact` mode. No dimension has an implicit
unscoped state. The named serving projection is immutable and its signed or
content-digested manifest must exactly match the scope, registry revision,
included-row content digest, embedding model, and builder version before tool
registration; a mismatch prevents startup. The manifest separately records the
source authority checkpoint for freshness/audit, but that checkpoint is not part
of the projection's authorization identity.

The server opens the file without following symlinks and validates its resolved
location, owner, regular-file type, mode, schema, keys, and binding references
before registering tools. Missing, empty, malformed, unknown-key, writable,
symlinked, relative, stale-binding, or otherwise ambiguous scope files prevent
startup. The parsed scope is immutable for the process lifetime. The authority
snapshot and projection manifest must name each other and the exact scope
digest. A scope, registry, authority snapshot, projection generation,
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
   Each binding record also has a closed `non_expanding_roots` list for
   high-degree protocol anchors. The list may be empty. Every declared entry
   must be a valid stored ledger ID resolving unambiguously inside that
   deployment's binding; missing, duplicate, or cross-binding declared roots
   prevent startup. The production registry declares the installed fallback ID
   named in Section 8.3 only after binding materialization proves that it
   resolves. Hermetic and synthetic registries declare only roots that exist in
   their own fixture stores; they do not inherit the production root.
2. During trusted ingestion, after source parsing, ConvMem constructs exactly
   four reserved scalar keys because Chroma metadata is flat:
   `_convmem_auth.project_binding_id`, `_convmem_auth.site`,
   `_convmem_auth.domain`, and `_convmem_auth.source_registration_id`. Every
   adapter discards both the bare `_convmem_auth` key and every key beginning
   `_convmem_auth.` from its output, and the ingest trust boundary rejects the
   source/batch if it observes that an untrusted input attempted either form.
   Only after that check does trusted code construct the four-key set from the
   matched immutable binding and source-registration record. In particular,
   `_convmem_auth.domain` is the registration's operator-owned authorization
   domain; it is never copied from `unit["domain"]`, model/distiller output,
   keywords, document content, or an adapter. The existing model-derived
   `unit["domain"]` remains under its legacy `domain` key for full/shell
   compatibility, but is semantic context only; strict projection membership,
   selectors, graphs, and response envelopes never consult it.

   The enforcement rule is exhaustive rather than tied to selected method
   names: every production, control, evaluation, migration, restore, or
   file-generation path that passes `metadatas=` to a collection must route
   through one reserved-prefix verifier. At this revision the audited census
   includes every metadata-writing `ChromaStore` method (including
   `add_summary()`, `add_unit()`, `update_unit_metadata()`, `update_unit()`,
   `supersede_units_for_source()`, and restore delegation),
   `file_generation_store.py:165`, `mixed_mode_control.py:64`, and
   `eval_corpus/shadow_build.py:386`. Read-modify-write paths such as
   `supersede_units_for_source()` must re-verify the stored four-key set against
   the registry before preserving it; copying stored keys is not proof.

   `provenance_binding.projection_metadata()` and
   `provenance_binding.enforce_projection_metadata()` reject the bare key and
   every `_convmem_auth.*` caller key before trusted code constructs or verifies
   the exact four-key set from separately supplied authorization context. No
   adapter or caller mapping is merged afterward. `chroma_write_store.py`
   carries no metadata itself; its obligation is to vend only enforcing store
   APIs and never a raw collection handle. A static writer-census test fails on
   any new direct `.add`, `.upsert`, or `.update` metadata call until that path
   is routed through the verifier and added to the reviewed census. Existing
   provenance-only validation is insufficient.
3. The query authorizer accepts a row only when its service-owned binding ID is
   in `allowed_project_bindings`, the registry maps that ID to the bound
   canonical project, the source registration is allowed by that binding, the
   protected site/domain values exactly equal that registration's immutable
   values, and those values satisfy the effective scope.

The authority record and its Chroma projection carry the same four scalar keys,
with Chroma remaining a follower. The prefix schema is closed: all four keys
must be present, non-empty, scalar, well-typed, and mutually consistent, and no
unknown `_convmem_auth.*` key may exist. Any partial, duplicate, conflicting,
or additional prefixed set denies the row. Rebuild regenerates the projection
from the closed authority snapshot; it does not infer authorization from
filenames, ordinary exports, Chroma, or prose.
If the current ledger/storage path cannot reserve and protect the whole prefix,
Gate B stops: copying a claimed authorization key from a document or adapter is
not a substitute.

The service-owned site value is either a normalized hostname or the literal
`not_applicable`; ordinary blank values are invalid. Exact-site scope requires a
hostname and exact normalized equality. A `not_applicable` bound scope ignores
row-site selection but does not weaken project-binding or domain proof.

Trusted ingest rejects any row whose service-owned domain is not exact or a
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
Gate B may use hermetic fixtures whose binding is assigned through the trusted
ingest path. It may not mutate or backfill the live corpus. A live-corpus
project-binding materialization or rebuild is a separate Ryan-granted data
migration with its own completeness and rollback evidence.

Gate B also builds a physical serving projection for each reviewed bound-scope
manifest. Rebuild scans the closed authority snapshot, applies the full bound project,
binding, site, and service-owned domain authorizer, and writes only accepted
rows into a dedicated collection/index. Domain descendants are discovered by
applying `domain_matches(auth_domain, bound_domain)` to the protected ledger
field during rebuild; model-derived ordinary `domain` is ignored. The open
taxonomy is never pre-enumerated into an `$in` filter. Shared global ANN indexes
and post-query over-fetch are forbidden in strict mode. The strict process
opens only its named projection read-only and fails startup if the manifest or
collection contains a row outside the bound scope.
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
bindings, exact site, or bound domain subtree never enter search's ANN/keyword
corpus or unresolved/related's metadata graph, result count, ordering, response
shape, first-call cost, or process cache. Keyword fallback, vector retrieval,
reranking, graph indexing, and any future fallback operate only inside that
projection and still apply the final row authorizer before serialization.
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
search. Before embedding, the server splits query text only on whitespace and
applies only the grammar-and-length stage of the centralized strict
public-handle parser with `re.fullmatch()` to each token. It never tests whether
the token's public binding reference is known or allowed. Every syntactically
valid qualified handle therefore receives the same fixed, non-reflecting
`identifier_query_not_supported` response before embedding. Binding
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

The snapshot is a JSONL file plus a closed manifest. Each line has schema
`convmem.bound-authority-record.v1` and exactly these semantic fields:

- `project_binding_id`, `source_registration_id`, and the protected site/domain;
- `record_kind`: `observation`, `decision`, or `verification`;
- `logical_id`: the continuing finding or decision subject;
- `assertion_id`: one immutable occurrence of that subject;
- `source_event_id`: the registered source's stable occurrence identity;
- `payload_sha256`: SHA-256 of the canonical semantic payload;
- `title`, `document`, `observed_at`, `recorded_at`, and integer
  `confidence_bps` from 0 through 10000;
- optional contextual `relates_to_assertion_id`;
- optional typed `supersedes_assertion_id`;
- `origin_assurance`: `untrusted`, `claimed`, or `verified`;
- for decisions only, `decision_state`: `approved` or `rejected` and a
  non-empty `disposition_ref` naming an operator-owned approval disposition;
- for verifications only, `verification_result`: `pass`, `fail`, or
  `inconclusive` and a required `target_assertion_id`.

All IDs are lowercase ASCII. Times are RFC 3339 UTC with `Z` and whole-second
precision; `observed_at` must not exceed manifest `as_of`, and `recorded_at`
must be at or after `observed_at` and not exceed manifest `built_at`. A
violation fails the snapshot rather than being repaired. `title` is 1–512
Unicode code points, `document` is 1–65536
code points before response truncation, and confidence is an integer. These
bounds are schema rules, not implementation defaults.

Pending proposals never enter the authority snapshot. A decision enters only
when its disposition is present in the operator-owned approved/rejected queue
artifact and its digest equals `disposition_ref`; a permitted signer name is
not proof. A rejected decision may be returned as historical evidence but can
never supersede an approved decision or establish current direction.
Observations and verifications remain evidence claims even when their origin
assurance is `verified`; source authorization is disclosure authority, not a
truth certificate. Model-derived decisions remain ordinary untrusted evidence
unless the governed disposition artifact exists.

The canonical payload is UTF-8 canonical JSON with sorted keys, no insignificant
whitespace, no floats, NFC strings, and explicit `null` for absent optional
semantic fields. It includes every field above except `payload_sha256`, plus
the four protected authorization values. Unknown keys, duplicate JSON keys,
non-NFC strings, NaN/infinity, or non-canonical encodings fail materialization.
The projection carries the resulting state under a second protected, closed
flat prefix `_convmem_state.*`. The same prefix-wide strip, construction,
writer-census, and all-or-nothing rules used for `_convmem_auth.*` apply to
`_convmem_state.*`; caller input may construct neither prefix.

#### 6.5.1 Logical identity, immutable assertions, and replay

Strict v2 separates a continuing subject from an immutable assertion:

- `logical_id` is `find2_<64-lowercase-hex>` for a finding or
  `choice2_<64-lowercase-hex>` for a decision subject. The digest input is the
  canonical binding, registered source identity, normalized site, producer,
  and operator-defined finding/decision key. It does not identify a scan.
- `source_event_id` is `evt_<64-lowercase-hex>` derived by the registered
  adapter from a source-native occurrence locator, never from mutable payload
  text. The registry pins the resolver and test vectors. It is stable for an
  exact delivery retry and distinct for a genuinely later scan/event. A source
  without such an identity is ineligible for strict materialization.
- `assertion_id` is `<kind>2_<64-lowercase-hex>`, where kind is `obs`, `dec`, or
  `ver` and the digest covers binding ID, source-registration ID,
  `source_event_id`, `record_kind`, and `logical_id`. It deliberately excludes
  payload bytes so changed bytes under one source occurrence collide and deny
  rather than masquerading as a new event.

An exact retry is a no-op only when binding, source registration, source event,
assertion ID, payload digest, complete canonical payload, and relation fields
are byte-equivalent to the committed authority record. Reprocessing identical
input must recover and reuse the preserved source-event identity; minting a new
UUID or occurrence ID is not a retry. A later legitimate scan has a distinct
source event and assertion ID even when its visible text is unchanged. Reusing
one source event with changed content, reusing one assertion ID with another
payload, or presenting the same payload digest with different canonical bytes
is `source_event_conflict` and fails the whole snapshot. Nothing overwrites an
assertion. Live adoption of this schema remains a separately granted migration.

#### 6.5.2 Deterministic current-state reduction

`relates_to_assertion_id` is contextual lineage only; it never means
replacement. Supersession occurs only through `supersedes_assertion_id`. The
builder rejects a supersession edge that is ambiguous, cyclic, cross-binding,
cross-logical-ID, cross-kind, self-referential, or points to a missing
assertion. A decision supersession is effective only when both decisions are
approved. Rejected and pending decisions never hide an approved decision.

An assertion is active when no valid active assertion explicitly supersedes
it. Multiple active observations or approved decisions for one logical ID are
returned as `current_state: conflict`; the builder never picks the latest
timestamp. A verification applies only to its exact target assertion. Active
verification results reduce conservatively: no result is `unverified`; only
passes are `pass`; any fail without a pass is `fail`; pass plus fail is
`conflict`; and inconclusive without fail/pass is `inconclusive`. A fail or
conflict can never be masked by an inline observation field, a newer timestamp,
or a summary. Outcome, decision state, disposition, target, supersession,
confidence basis points, and relation changes are semantic payload changes and can never be
skipped as text-identical updates.

Strict `unresolved` includes active observations whose reduced state is
`unverified`, `fail`, `inconclusive`, or `conflict`. It excludes only an
explicitly superseded observation or one whose exact active assertion reduces
to `pass`. Search and related may return historical/superseded records, but
must label their state and never describe them as current. The reducer output
is materialized and independently recomputed during validation; disagreement
fails publication.

#### 6.5.3 Authority-first materialization and recovery

The authority snapshot is the sole input to strict publication. Chroma,
ordinary unit exports, global ledger maps, summaries, caches, and projection
rows are never recovery authority. Fixture construction and any later granted
materialization follow this order under one authority-writer lease:

1. validate source registrations and canonical records;
2. write the selected, validated immutable assertion view to a temporary
   authority generation without modifying its source ledger/dispositions;
3. fsync every authority file and its directory;
4. write and fsync a manifest containing the scope/registry digests, complete
   file hashes, record count, authority checkpoint, reducer version, and
   `as_of` time;
5. close the authority generation; no later mutation is permitted;
6. build the bound projection in a new generation from that closed snapshot;
7. validate every row, recompute payload/state digests and the reducer, and
   record collection, embedding, builder, dependency, and row-content digests;
8. fsync the projection and manifest, then publish with one compare-and-swap
   active-pointer update using the existing generation-publication primitive.

The builder pins one authority checkpoint. Assertions committed afterward are
absent until a later reviewed generation. A crash before pointer publication
leaves the previous generation active; an incomplete generation is never
opened. A crash after the atomic pointer update opens only the fully validated
new generation. Startup validates pointer lineage and both manifests before
tool registration. Rollback is a compare-and-swap pointer change to the
retained prior verified generation; it never edits or deletes authority
records. Projection-only rows are quarantined from consideration and are never
silently imported. Disk-full, torn-tail, duplicate delivery, concurrent
writer, stale builder, and stale-pointer cases must fail without changing the
active view.

#### 6.5.4 Freshness, activation, and revocation

The projection manifest contains an opaque `snapshot_id`, `authority_snapshot`,
`source_checkpoint_sha256`, `scope_sha256`, `registry_sha256`, `built_at`,
`as_of`, and `expires_at`. `expires_at` equals `as_of` plus the scope's reviewed
maximum age. Clock rollback, an already expired view, or a request beginning
after expiry returns `snapshot_stale` before retrieval. No automatic rebuild or
silent extension is allowed.

Every successful tool response carries `snapshot_id`, `as_of`, and
`expires_at`. One OpenClaw task session is pinned to one tuple of scope,
registry, authority, projection, and snapshot digests. Activation creates a
fresh, empty, generation-specific `OPENCLAW_STATE_DIR`; no prior session store,
compaction summary, cached tool result, or credential directory is copied.
When scope narrows, authority changes, a correction publishes, the view expires,
or rollback occurs, the gateway and connector stop and all sessions for that
activation become non-resumable. The next activation uses a new state directory
and session identity. Old session artifacts may be retained offline for audit
but are never mounted or resumed. Because a model cannot be made to forget
already disclosed text, continuing an old session after revocation is a hard
failure, not a refresh strategy.

## 7. Deep module boundary

Scope policy belongs in the new deep module `bound_read_scope.py`,
not in `mcp_server.py`.

The module owns:

- strict scope-file parsing and validation;
- project-binding registry validation;
- the omitted-selector sentinel;
- selector resolution;
- project membership proof;
- bound-projection manifest validation;
- row authorization;
- related-chain authorization;
- public non-revealing denial payloads;
- private structured audit reasons.

A second new deep module, `strict_evidence_state.py`, owns the closed authority
record schema, canonical payload, logical/source-event/assertion identifiers,
approval-disposition validation, supersession graph, conservative verification
reducer, and public state fields. A third module,
`bound_projection_builder.py`, is the only authority-snapshot-to-projection
path and owns generation manifests, checkpoint pinning, validation,
compare-and-swap publication, and rollback integration. These responsibilities
must not be reimplemented in handlers or adapters.

`mcp_server.py` owns only profile selection, fixed tool registration, argument
decoding, delegation, and serialization. Query, unresolved, and ledger modules
continue to own their domain behavior; they do not learn about OpenClaw.
`ledger_ids.py` preserves legacy v1 IDs and owns qualified public-handle syntax;
`strict_evidence_state.py` owns v2 logical/source-event/assertion generation
and validation. The strict-scope module owns
`normalize_authority_site()`, the pinned authority-host algorithm used by the
registry and v2 site normalization. The dedicated projection builder owns
authority-snapshot-to-bound-index materialization; `chroma_store.py` and
`file_generation_store.py` expose the
result read-only but do not decide scope. The strict-scope module owns
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
  "schema": "convmem.raw-evidence.v2",
  "instruction_authority": "none",
  "snapshot": {
    "snapshot_id": "...",
    "as_of": "2026-09-20T00:00:00Z",
    "expires_at": "2026-09-21T00:00:00Z"
  },
  "results": [
    {
      "title": "...",
      "document": "...",
      "ledger_id": "...",
      "citation_ref": "...",
      "record_kind": "observation",
      "logical_id": "find2_...",
      "current_state": "unverified",
      "decision_state": null,
      "verification_result": null,
      "target_ledger_id": null,
      "superseded": false,
      "origin_assurance": "claimed",
      "confidence_bps": 7000,
      "observed_at": "2026-09-20T00:00:00Z",
      "recorded_at": "2026-09-20T00:00:01Z",
      "disposition_ref": null,
      "domain": "...",
      "site": "..."
    }
  ]
}
```

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
only from `_convmem_auth.domain` and `_convmem_auth.site`; the legacy ordinary
`domain`/`site` metadata is never exposed as strict authorization context.

OpenClaw may summarize the returned data for its user, but no second model call
occurs inside ConvMem. Excluding `ask()` removes that additional synthesis and
prompt-injection surface; it does not pretend the orchestrating model performs
no synthesis.

### 8.2 `unresolved`

Inputs are an optional bounded `limit`, optional project/site/domain selectors,
and optional `cross_domain`. Omitted selectors inherit the bound scope. Domain
matching is hierarchical, not the current exact-string comparison. Strict
unresolved loads observations and children only from the named bound projection,
authorizes them independently, constructs an effective-selector-scoped graph,
and computes each observation's status from that graph.
An out-of-scope child is treated as absent and cannot cause an otherwise
in-scope observation to disappear. If the only pass verification is out of
scope, the safe result is to report the observation as unresolved. Results use
the same untrusted-evidence envelope.

### 8.3 `related`

Strict `related(ledger_id=...)` accepts only the binding-qualified public handle
returned by strict search or unresolved, never a bare stored ledger ID or raw
Chroma storage ID. `ledger_ids.py` remains the owner of legacy IDs and
public-handle parsing; `strict_evidence_state.py` owns v2 assertion IDs. Both
use the same centralized stored-ID validator. The strict
stored-ID validator uses
`re.fullmatch()` over this ASCII grammar plus a 160-code-point maximum, not
`match`, `search`, extraction, or an appended `$`:

```text
(?:dec_prop|obs2|dec2|ver2|obs|dec|ver)_[A-Za-z0-9_.-]+
```

The public-handle validator uses `re.fullmatch()` over
`cm1\.[a-f0-9]{32}\.(?:dec_prop|obs2|dec2|ver2|obs|dec|ver)_[A-Za-z0-9_.-]+`, enforces a
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

Every registry-v2 generator calls its centralized full-string validator before
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
authoritative. A registry-v2 generator that cannot produce a valid ID fails the
entire authority generation with the operator-visible reason
`ledger_id_mint_denied`; this read-only slice creates no mutable quarantine.
It must never substitute a UUID, truncate without a digest, or silently skip
the item. Existing legacy IDs that already satisfy the strict grammar may be
qualified only after the separately reviewed binding-materialization migration;
invalid legacy IDs fail closed until a separately reviewed ID migration exists.

`agent_run_ledger.py` already performs full-string validation at an integrity
boundary. Gate B replaces that local validator with the centralized helper and
must not weaken it. The regexes in `query.py` and `cross_project_digest.py` are
extraction helpers only; strict search disables the former, and the latter's
narrower shape is a known non-authoritative recall limitation. Strict input
validation rejects Unicode confusables, whitespace, slashes, colons, missing
suffixes, embedded IDs, trailing text, and values longer than the bound below.

Every registry-aware authority record validates its assertion ID and every
non-empty relation with the centralized helper before authority-generation
publication. Legacy writers remain unchanged and outside strict authority until
their own migration. Strict identity is `(project binding, assertion_id)`;
`logical_id` groups assertions but is never a lookup overwrite key.
`provenance_identity()` remains context and may be checked, but it is not the
payload-integrity or retry predicate. Exact retry, changed-payload conflict,
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
   verifications attached to decisions, and unknown kinds. This step does not
   run when that observation is also a registered non-expanding root.
4. If step 1 found a non-expanding root, include that root as lineage context
   but never enumerate its other children. Non-expanding-root status takes
   precedence over observation-anchor status: a node that is both is governed
   by this step, not step 3. The production registry's immutable
   `non_expanding_roots` list contains the installed protocol fallback
   `dec_prop_20260623_161428_c311` after materialization proves that it resolves;
   hermetic and synthetic deployments use only their own declared fixture
   roots. Request or corpus text cannot add a root.

Traversal uses a visited set and collects no more than 200 nodes. The complete
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
  "error": {
    "code": "scope_denied",
    "message": "The requested evidence chain is unavailable in this scope."
  }
}
```

Unknown IDs, malformed IDs, and out-of-scope IDs are deliberately
indistinguishable. The response contains no IDs, titles, counts, chain shape,
scope values, or reason detail. Private logs may record a reason enum and a
request correlation ID, but never corpus document text. Gate D must prove that
an operator can use that correlation ID to distinguish at least unknown,
malformed, wrong-binding, ambiguous-identity, and out-of-effective-scope
failures without exposing the private reason to OpenClaw. A binding/site/domain
registry mismatch is a startup failure, so ordinary writes from a different
exact site or domain authority cannot silently poison a live chain.

No partial normative neighborhood is returned. Authorization and deterministic
state reduction occur on its full protected graph before the strict v2
formatter.

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
    slots: { memory: "none" },
    allow: ["convmem-reader"],
    load: {
      paths: ["/operator/provisioned/convmem-reader"]
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
  acp: { enabled: false, dispatch: { enabled: false } }
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

Phase 1A uses synthetic corpus fixtures and a reviewed local inference endpoint.
The effective model route must be inspected from the running session, and
provider fallback must be disabled. If installed OpenClaw cannot keep inference
local without a remote fallback, the smoke stops. A transport-only MCP smoke
may still run without claiming the hostile-content gate passed.

Phase 1B under this plan also keeps model inference local. Sending real ConvMem
evidence to a hosted model is a distinct privacy, retention, cost, and authority
decision requiring a new architecture delta and an exact Ryan grant. Network
egress is denied by default; Phase 1B opens only the individually approved
external channel endpoints after its sender/perimeter tests pass. Neither the
connector nor the ConvMem child receives general network access.

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

Phase 1A and Phase 1B contain no background worker and no ACP delegation. Each
connector call is synchronous and has one request correlation ID.

The only terminal outcomes are `succeeded`, `denied`, `failed`, and
`interrupted`. `accepted` and `running` are non-terminal. A user-visible claim
of completion may be produced only after a complete MCP response has been
received and serialized. Process exit, timeout, broken stdio, gateway restart,
or cancellation before that point is `interrupted` or `failed`, never
`succeeded`.

No connector completion state is written to ConvMem, OpenClaw memory, or a new
durable ledger. Retrying after interruption creates a new request ID. This
defines false background completion out of existence for the initial phases.

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

The complete public error vocabulary is closed:
`invalid_request`, `identifier_query_not_supported`, `scope_denied`,
`snapshot_stale`, `response_too_large`, `temporarily_unavailable`, and
`internal_failure`. Every error contains only `schema`, `error.code`, a fixed
non-reflecting message, and `correlation_id`. Private reason enums may add
diagnostic specificity but never corpus text, request text, filesystem paths,
scope values, or credentials.

## 12. Phase gates

### Gate A — plan review

- Astra's final review of commit `7809f20` blocked build on seven incomplete
  contracts. This revision defines the bounded-reader deliverable, typed
  authority/state model, logical-versus-assertion identity, payload-bound
  replay, authority-first publication/recovery, lifecycle shutdown,
  freshness/revocation, and exact build packet.
- Kiro performs the charter-required binary review only after an independent
  recheck confirms that no category-3 or category-4 build decision remains.
- Ryan approves or rejects architecture and execution planning.

No code or OpenClaw configuration is authorized by Gate A.

### Gate B — strict ConvMem contract implementation

After a Ryan Execute grant, Cursor implements only:

- the deep bound-scope module;
- the strict evidence-state and bound-projection-builder modules;
- fail-closed profile parsing;
- the exact three-tool strict profile;
- empty resources and templates;
- the ingest-owned project-binding mechanism and hermetic bound fixtures;
- registry-owned source authorization domains separated from model-derived
  semantic domains;
- strict-only site normalization and versioned strict ID generation that leave
  legacy full/shell and monitor identity unchanged;
- immutable physical serving projections for each bound-scope manifest;
- versioned strict logical/source-event/assertion IDs that preserve legacy-v1,
  payload-bound exact replay, fresh-observation admission, binding-qualified
  public handles, and ambiguity-denying lookup;
- operator-owned fixture authority generations, deterministic state reduction,
  atomic generation publication, crash recovery, and rollback;
- strict search with no ledger-ID extraction/priority path and an authorized
  physical candidate universe;
- projection-only unresolved and bounded target-neighborhood related graphs;
- exhaustive metadata-writer census and reserved-prefix enforcement;
- focused hermetic tests.

No live-corpus binding migration, OpenClaw plugin, or OpenClaw configuration is
included in this gate.

### Gate C — connector implementation

After Gate B review passes, Cursor may implement the fixed local OpenClaw
connector plugin in the repository with hermetic fake-MCP tests. It may not
install or enable the plugin, create a live OpenClaw profile, or contact an
external channel.

### Gate D — Phase 1A isolated smoke

Requires a separate Ryan grant naming the profile and exact config path.

- local operator only;
- loopback/local stdio only;
- synthetic ConvMem corpus and reviewed local inference only;
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
- no ConvMem writes.
- a fresh snapshot-bound `OPENCLAW_STATE_DIR`, with memory flush and heartbeat
  independently disabled and no resumable prior session.

The first smoke uses an isolated synthetic ConvMem store whose project bindings
were assigned through the reviewed ingest path. It proves transport and denial
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

### Gate E — Phase 1B scoped normal operation

Requires fresh Kiro review and Ryan approval after all adversarial tests pass
and Gate D-V supplies a positive, independently graded result rather than a
retrieval-only success claim.
Every enabled channel/account/sender/group policy must be enumerated and
tested. Unknown senders, unapproved groups, and unbound channels must be unable
to invoke the integration. Each approved origin must map statically to this
profile's single audience policy; no inbound field may select or widen scope.

ACP, background workers, transcript capture, automatic indexing, and durable
OpenClaw memory remain disabled.

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

12. Authorize rows only when the trusted ingest path assigned a binding that is
    allowed by the immutable scope and resolves to the bound canonical project.
    Prove schema v2 rejects zero or multiple `allowed_project_bindings`.
13. Forge matching `project`, `domain`, `site`, the bare `_convmem_auth` key,
    each `_convmem_auth.*` key individually, the complete four-key set, an
    additional prefixed key, the bare `_convmem_state` key, every
    `_convmem_state.*` field individually and together, `project_binding_id`,
    `workspace_directory`, and
    `source_path` through corpus or adapter input. Also prompt the distiller to
    emit an allowed descendant domain from hostile source text. Prove every
    adapter, provenance projection helper, unit/summary add, metadata update,
    file-generation writer, and production writer boundary rejects the whole
    reserved prefixes; prove the protected domain remains the source
    registration's value while model output survives only as semantic context.
    Prove an unregistered or differently bound source cannot self-label into
    the projection. Only trusted code may construct an all-or-nothing set.
    Reject partial, unknown, stale, conflicting, cross-project, and
    row-domain-outside-binding assertions. Run the static writer census over
    the repository and prove every `metadatas=` add/upsert/update routes through
    enforcement; specifically exercise `supersede_units_for_source()`, mixed
    mode control-copy, shadow/eval build, file-generation, and restore paths.
    Prove `chroma_write_store.py` never vends a raw collection handle.
14. Prove legacy rows without a service-owned binding reduce recall rather than
    leak, and prove Gate B never backfills the live corpus.
15. Prove strict site filtering rejects source-path-only site inference.
16. Build a physical projection from an open domain taxonomy and prove search,
    unresolved, related, vector retrieval, keyword fallback, reranking, graph
    construction, and every future fallback read only that exact projection.
    Add or remove rows outside the immutable bound scope and prove its
    included-row content digest and each tool's query cost, process cache,
    response shape, count, and order do not change (the source-checkpoint audit
    field may advance). Include an unknown but registry-authorized descendant
    domain and prove it is included by rebuild without an enumerated `$in`
    list. Prove strict mode never calls `_fetch_scoped_units()`,
    `build_ledger_index()` over a global store, or any wider collection.
    Separately prove an explicit descendant selector may narrow results only
    inside the already authorized projection.

### Cross-surface oracle resistance

17. Put syntax-valid qualified handles containing an allowed, disallowed, and
    unknown public binding reference in otherwise identical
    whitespace-delimited search text. Prove the grammar/length stage gives all
    three the byte-identical fixed `identifier_query_not_supported` response
    before binding lookup or embedding and that neither ledger extraction nor
    priority injection runs.
    Prove malformed/punctuation-wrapped strings receive no lookup treatment,
    and `server_name`, `codec_config`, and `observer_pattern` are not rejected.
18. Under a caller-chosen descendant narrowing, give an included observation a
    verification elsewhere in the same authorized bound projection but outside
    the effective descendant. Prove strict unresolved computes from the
    effective-selector-scoped graph, returns the observation as unresolved, and
    is byte-equivalent to the same graph with that child absent.

### Project selectors and resources

19. Attempt another project through `brief`, `folder_state`,
    `memories://brief/{project}`, and `memory://brief/{project}`. Prove the
    surfaces are absent in strict mode.
20. Call `resources/read` directly with both aliases, another project, URI
    encoding, and malformed URIs; prove strict mode resolves none and reveals no
    project information.

### Ledger identity and related-chain authorization

21. Property-test every registry-v2 ID generator against the centralized
    `re.fullmatch` and length validator. Prove canonical length-prefixed digest
    inputs separate field boundaries and that `find2_`, `choice2_`, `evt_`,
    `obs2_`, `dec2_`, and `ver2_` are deterministic and kind-disjoint. Use full
    multi-label hosts, two hosts sharing the same first label, `www.*`,
    single-label hosts, ports, user info, paths, empty labels, trailing
    newlines, confusables, and maximum length. Pin UTS
    #46 non-transitional/IDNA2008 vectors for `straße`, `strasse`, fullwidth
    characters, underscores in any label position, and long legal hostnames.
    Prove generator failure aborts with
    `ledger_id_mint_denied` rather than a UUID fallback or partial generation.
    Separately prove legacy
    `site_short()`/`observation_id()`, `monitor.py`, and
    `tests/test_milestone_c.py` remain byte-compatible and that live writers
    cannot select v2 without the later migration grant.
22. On the registry-aware authority path, reject malformed IDs and relations,
    a reused source event/assertion with changed canonical payload, a changed
    source registration, and an ambiguous relation. Replay the exact preserved
    source event, assertion, payload, and registration and prove it is a no-op;
    then admit a distinct later source event under the same logical ID.
    Prove the existing `agent_run_ledger` integrity check is preserved through centralization and
    cross-binding stored-ID reuse yields distinct qualified public handles.
23. Using two separate single-binding profiles, build stored-ID reuse across
    bindings; separately build a collision within one binding, including two
    sites while `site_mode=not_applicable`. Prove strict lookup validates the
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
    raw-Chroma ID; prove byte-equivalent public denial shapes.
26. Put one out-of-effective-scope decision, verification, sibling,
    unknown-kind child, or metadata-incomplete node behind an in-scope target;
    prove the entire chain is denied without partial output. Prove registry
    startup rejects an exact-site binding spanning two sites or a binding whose
    domain root differs from the profile bound, and prove trusted ingest plus
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
37. For Phase 1B, test every configured channel, account, sender allowlist,
    group policy, mention rule, pairing policy, and Gateway exposure. Unknown or
    unapproved origins must fail before tool invocation.

### Capture negative controls

38. Prove no OpenClaw transcript path is watched or indexed.
39. Prove successful MCP retrieval does not create a capture authorization,
    quarantine claim, or background indexing route.
40. Exercise every request, graph, document, response, timeout, and wrong-type
    bound. Prove per-document truncation precedes the 64-KiB UTF-8 response cap,
    the response cap may reduce search/unresolved row count before
    `top_k`/`limit`, related denies rather than truncating a chain, and
    connector-side truncation cannot become partial success or change scope.
41. Mix pending, approved, rejected, superseded, and model-derived
    decision-shaped records with identical prose. Prove only operator-disposed
    records receive decision state, rejected records never suppress approved
    records, and every response preserves kind, state, assurance, confidence,
    time, disposition, and snapshot fields.
42. Reproduce outcome-only pass-to-fail updates, an inline pass with a failing
    child, pass/fail contradictions, late and out-of-order checks, and rejected
    replacement edges. Prove the conservative reducer returns fail or conflict
    and never skips a semantic change because visible text is unchanged.
43. Distinguish exact preserved-envelope retry, identical-source remint, a
    genuine later scan, and changed payload under one source event. Prove only
    the exact retry is a no-op; a later scan creates a new assertion under the
    same logical ID; remint/conflict fails; and payload bytes are recomputed and
    compared rather than inferred from `provenance_identity()`.
44. Inject failure before/after every authority append, file and directory
    fsync, manifest close, projection write, validation, and active-pointer
    compare-and-swap. Include torn tail, disk full, concurrent delivery, stale
    builder, and stale rollback. Prove restart selects exactly one complete
    generation and rebuild/rollback are authority-equivalent.
45. Drive the actual installed runtime across compaction thresholds, heartbeat
    intervals, restart, and malicious per-agent overrides. Prove effective
    memory flush and heartbeat remain disabled and that no unsolicited model
    turn occurs.
46. Expire, correct, narrow, and roll back a snapshot while attempting to reuse
    the old OpenClaw state/session directory. Prove every response exposes the
    pinned snapshot times, stale requests fail before retrieval, and old
    sessions cannot resume under the new activation.
47. Start the strict entry point with populated legacy home credentials,
    credential environment variables, and a general ConvMem config. Prove its
    empty fixed home and closed strict config prevent credential/provider
    loading before profile selection.
48. Exercise one active request plus eight queued requests, a ninth request,
    cancellation, timeout, oversized frame, malformed frame, and child exit.
    Prove FIFO bounds, fixed errors, no automatic retry, no late success, and no
    fallback to a wider profile.

## 14. Verification commands and evidence

The paired `EXECUTION-openclaw-convmem-integration.md` names the exact file
scope, sequence, commands, evidence, stop conditions, and rollback for the
fixture-only build. Its minimum evidence set includes:

- focused unit tests for selector resolution and membership proof;
- trusted-ingest tests proving corpus and adapter inputs cannot forge any
  `_convmem_auth.*` key or create a partial authorization set, and proving
  hostile distiller domain output cannot affect the registry-owned domain;
- a repository-wide metadata-writer census plus mutation tests for every
  production, control, eval, file-generation, supersede, and restore path;
- physical bound-projection tests proving rows outside the immutable profile
  scope cannot affect any strict tool's cost, cache, count, order, or shape;
- focused MCP inventory tests for tools, resources, and templates;
- focused bounded target-neighborhood tests, including depth-two relations and
  a greater-than-200-child non-expanding fallback hub;
- generator/validator property tests plus UTS #46/IDNA2008 vectors,
  payload-bound exact replay, fresh-observation versioning, binding-scoped
  collision, qualified-handle, ambiguous-relation, and write-rejection tests;
- typed authority/state, approval-disposition, conservative reducer, semantic
  equality, immutable-generation publication, crash/recovery, stale-view, and
  session-revocation tests;
- unchanged legacy compatibility tests for `tests/test_site_filter.py`,
  `tests/test_milestone_c.py`, and `monitor.py` ID lookup/write behavior;
- scoped unresolved-graph tests with out-of-scope child verifications;
- connector child-environment allowlist and remote-node refresh tests;
- installed-runtime memory-flush, heartbeat, state-directory, queue, deadline,
  cancellation, frame-limit, and credential-isolation tests;
- existing retrieval, brief, resource, and ledger regression tests, with
  `tests/test_query_ledger_lookup.py` and
  `tests/test_query_search_harden.py::QueryLimitTests::test_scoped_fetch_adapts_to_collection_size`
  parameterized by profile: their current priority-injection and adaptive
  over-fetch assertions remain required for `full`/`shell`, while
  `openclaw-strict` must prove both paths absent;
- ConvMem smoke checks from `docs/CODEX-DEEPSEEK-VERIFY.md` where relevant;
- `openclaw --version`, command inventory, config validation, plugin inventory,
  effective agent tool inventory, prompt/skill/hook inventory, model-provider
  route, network destinations, channel inventory, and security audit from the
  installed binary;
- production-path and network denial in hermetic tests;
- exact revision, config digest, scope-file digest, and test output in the
  review handoff.

Every portable review handoff includes immutable text captures and digests for
the installed `openclaw --version`, top-level `--help`, and
`config validate --help` probes. Gate D adds the exact isolated config-validation
result and effective runtime inventories; Gate A evidence never substitutes a
current web page for an installed-binary probe.

The Gate A review bundle also includes `chroma_store.py`,
`file_generation_store.py`, `provenance_binding.py`, the adapter output
boundary, `chroma_write_store.py`, `mixed_mode_control.py`,
`eval_corpus/shadow_build.py`, `monitor.py`, and the ingest/distill merge points
so candidate-store capabilities, domain ownership, writer coverage, identity
compatibility, and prefix stripping are reviewable rather than asserted.

No test may read or mutate the live ConvMem database, live OpenClaw state,
external channels, or production transcript paths without the later named Ryan
grant.

## 15. Stop conditions

Stop and return FAIL if any of the following occurs:

- an unknown profile falls back to a wider profile;
- an omitted selector becomes unscoped, empty, or erroneous solely because it
  was omitted;
- an explicit selector widens project, site, or domain;
- project membership depends on corpus prose or an untrusted substring;
- `_convmem_auth.domain` comes from model/distiller output, ordinary
  `unit["domain"]`, document content, or anything other than the matched
  operator-owned source registration;
- a protected row domain lies outside its binding root, or strict site identity
  uses a normalizer other than the one pinned authority-site function;
- strict authorization calls legacy `site_filter.normalize_site()`, or Gate B
  changes that legacy function's URL/path behavior;
- a corpus or adapter field can forge, preserve, or override any reserved
  authorization key, or a partial/additional `_convmem_auth.*` set authorizes;
- any metadata writer bypasses the reserved-prefix verifier, a read-modify-write
  preserves unverified authorization/state keys, or the writer census is incomplete;
- a caller can forge, partially supply, or preserve `_convmem_state.*`, or a
  response state is derived from prose, inline legacy fields, or timestamps;
- a row with missing proof is returned;
- `cross_domain=true` widens retrieval;
- a resource or unexpected tool appears;
- any strict surface reveals whether a valid qualified handle is unknown
  versus out of scope, or a row outside the immutable bound projection
  influences authorized response cost, count, order, or shape;
- unresolved or related reads a global ledger index, wider collection, or
  metadata cache rather than the named bound projection;
- strict search extracts or priority-injects a ledger ID from query text;
- strict search consults binding allowlists while screening syntactically valid
  handle tokens;
- unresolved status or inclusion changes because of an out-of-scope child;
- a registry-v2 ID generator can emit a value rejected by the canonical
  length/grammar validator, uses unpinned/IDNA2003 normalization, or falls back
  to a UUID;
- Gate B changes legacy-v1 monitor IDs, a live writer selects registry-v2
  without a migration grant, or one scheme can be mistaken for the other;
- a changed payload reuses a source event/assertion, an exact preserved retry
  is duplicated, a later legitimate scan cannot create a new assertion under
  its logical ID, last-write-wins is consulted, or identity resolution occurs
  before the qualified binding check;
- a pending/model-derived decision becomes approved, a signer string acts as
  approval proof, a rejected decision suppresses an approved decision, a
  relation is treated as supersession, or fail/conflict reduces to pass;
- projection state precedes durable authority, a partial generation becomes
  active, restart/rollback changes the authority reduction, or concurrent
  publication bypasses compare-and-swap;
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

## 17. Adversarial re-review questions

Astra's final review of commit `7809f20` blocked build. A fresh reviewer must
independently falsify the corrected architecture and paired execution plan and
answer with exact references:

1. Can any request-time input affect the bound scope or connector process
   launch before server authorization?
2. Can a legacy row, ledger child, fallback result, or resource escape project,
   site, or domain proof?
3. Is `domain_matches()` called in the correct direction at both selector and
   row-authorization stages?
4. Can omission, explicit blank, normalization, aliasing, or malformed values
   create a wider result?
5. Does project proof trust any attacker-controlled prose or ambiguous path?
   Is the protected domain sourced only from the immutable registration rather
   than the distiller's semantic label?
6. Can search, unresolved, or related act as an existence oracle, resolve a
   colliding or cross-binding identity, reject legitimate code substrings, or
   return a misleading partial chain?
7. Can OpenClaw `2026.3.2` still expose core tools despite the plugin allowlist?
8. Can native memory, automatic memory flush, skills, plugin prompts, or ACP
   child configuration reintroduce a second authority or injection route?
9. Can hostile evidence cross from tool-result data into an instruction
   channel?
10. Can a crash, timeout, cancellation, or restart become false completion?
11. Does any phase silently authorize external config, channels, capture,
    indexing, durable writes, or ACP?
12. Can an open-taxonomy domain escape or poison the physical bound projection,
    or can shared-index/global-graph density influence any tool's results,
    cache, or query cost?
13. Can exact replay, remint, later observation, or changed payload be
    conflated; can strict v2 IDs alter legacy monitor identity; can
    IDNA/library variation split or merge identities; or can any generator
    exceed its validator?
14. Can the bounded target-neighborhood traversal become unavailable because
    of the high-degree protocol fallback, miss required depth-two context, or
    cross a binding?
15. Does every metadata writer route through prefix enforcement, including
    supersede, mixed-mode, eval/shadow, generation, and restore paths?
16. Do site identity, response-size precedence, or child-session controls have
    more than one interpretation?
17. Is any acceptance test circular, unverifiable, internally contradictory,
    or dependent on current web documentation rather than bundled
    installed-binary evidence?
18. Can a pending, rejected, model-derived, or forged decision acquire approved
    state, or can a result lose kind, assurance, confidence, disposition,
    verification target, supersession, or time?
19. Can an outcome-only update be skipped, an inline pass mask a fail, a
    contextual relation act as supersession, or conflicting active assertions
    reduce to a reassuring state?
20. Are exact retry, identical-input remint, later observation, and changed
    payload distinct, payload-bound operations with no overwrite or lost event?
21. Can any crash/concurrency point publish projection state before durable
    authority or make restart/rollback select a different reduction?
22. Can memory flush, heartbeat, credential discovery, an old session/state
    directory, or an expired snapshot survive the effective runtime controls?
23. Does the execution plan leave Cursor/Grok any category-3 or category-4
    choice about schemas, authority, interfaces, recovery, containment,
    acceptance, or rollback?

The advisory reviewer returns `ADVISORY PASS`, `ADVISORY FAIL`, or `INCOMPLETE`.
After advisory PASS, Kiro independently returns the charter-required binary
design-review `PASS` or `FAIL` on the same revision. Only Ryan may authorize
implementation after a Kiro `PASS`.

## 18. Exit state

This document and its paired execution plan stop before implementation. They
are not an Execute grant. Astra's seven build blockers are resolved as explicit
contracts; incremental web-development value remains deliberately unproven and
is assigned to Gate D-V rather than asserted. The next step is independent
re-review, then Kiro's exact-revision binary design/scope review. Cursor/Grok
may implement only after both pass and Ryan issues an explicit Execute grant.

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
| Project binding | An opaque, service-owned membership assertion assigned only by trusted ingestion and resolved through an operator-owned registry; ordinary corpus metadata and paths cannot supply it. |
| Scope oracle | A response difference that lets a caller infer whether an otherwise inaccessible record exists. |
| Strict profile | The proposed `openclaw-strict` ConvMem MCP surface containing only `search`, `unresolved`, and `related`, with no resources. |
| Track A | ConvMem session-chat indexing used for handoff evidence; it is not a durable decision record. |
