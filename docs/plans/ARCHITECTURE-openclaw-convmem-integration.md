# Architecture Plan — OpenClaw orchestration with a bounded ConvMem evidence surface

**Status:** THIRD CLAUDE `ADVISORY FAIL` ON COMMIT `d6edbde`; CORRECTIONS
APPLIED FOR RE-REVIEW; KIRO REVIEW BLOCKED UNTIL ADVISORY RECHECK — no
implementation, OpenClaw configuration, production smoke, or capture is
authorized

**Date:** 2026-09-20

**Arc:** none (ad-hoc integration)

**Authority:** Codex architecture/planning lane. Claude's local advisory
re-review of commit `d6edbde33bf4c6f152beec68928b7528a73d60c9` returned
`ADVISORY FAIL` with one high, six medium, and four lower-severity findings
after confirming thirteen earlier findings closed. This revision incorporates
all eleven corrections. Kiro remains the required design-review lane and Ryan
remains the approval authority. Claude cannot authorize execution.

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
`CONVMEM_BOUND_READ_SCOPE_FILE`, `CONVMEM_PROJECT_BINDING_REGISTRY_FILE`, a
reviewed `CONVMEM_CONFIG`, fixed `HOME`, minimal `PATH`, and locale variables.
Every other variable is absent. Strict server startup hard-ignores and tests
hostile values for legacy `CONVMEM_READ_SCOPE_DOMAIN` and
`CONVMEM_READ_SCOPE_FILE`. Query text, selectors, ledger IDs, channel messages,
and corpus content may never influence the executable path, arguments before
the MCP protocol boundary, environment keys or values, scope-file path,
project-binding-registry path, config path, or working directory.

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
  normalization required for one strict site identity.
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
  can mint IDs outside the proposed ASCII grammar.
- `provenance_binding.py:210-226,260-295` already distinguishes replayed
  assertion identity from a different assertion and owns projection metadata;
  Gate B must extend, not bypass, those boundaries.
- `chroma_store.py:300-325` and `file_generation_store.py:718-760` query shared
  serving indexes and have no immutable bound-scope projection contract.
- `chroma_store.py:219-232,418-435` provides additional summary/unit metadata
  write paths, while `provenance_binding.py:276-295` currently passes unknown
  keys through and `chroma_write_store.py` gates production writers without
  enforcing the reserved authorization prefix.
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
- `related` — raw scoped all-or-nothing evidence traversal.

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
  "schema": "convmem.bound-read-scope.v1",
  "project": "convmem",
  "allowed_project_bindings": ["project:convmem:v1"],
  "domain": "coding",
  "site_mode": "not_applicable",
  "site": null,
  "serving_projection": "scope:convmem-coding:v1"
}
```

`project`, `allowed_project_bindings`, `domain`, and `serving_projection` are
mandatory and non-empty. Each binding ID must resolve in the service-owned
registry to the same canonical project, bound-domain root, and site policy
named by the scope. `site_mode` is either `exact` or `not_applicable`. `site`
is mandatory and non-empty only in `exact` mode. No dimension has an implicit
unscoped state. The named serving projection is immutable and its signed or
content-digested manifest must exactly match the scope, registry revision,
included-row content digest, embedding model, and builder version before tool
registration; a mismatch prevents startup. The manifest separately records the
source ledger checkpoint for freshness/audit, but that checkpoint is not part
of the projection's authorization identity.

The server opens the file without following symlinks and validates its resolved
location, owner, regular-file type, mode, schema, keys, and binding references
before registering tools. Missing, empty, malformed, unknown-key, writable,
symlinked, relative, stale-binding, or otherwise ambiguous scope files prevent
startup. The parsed scope is immutable for the process lifetime. A scope change
requires a new reviewed file and a server restart.

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
   `unit["domain"]` may survive only as ordinary `semantic_domain` context and
   is discarded for authorization and projection membership.

   `provenance_binding.projection_metadata()`,
   `provenance_binding.enforce_projection_metadata()`,
   `ChromaStore.add_unit()`, `ChromaStore.add_summary()`,
   `ChromaStore.update_unit_metadata()`, every file-generation writer, and the
   `chroma_write_store.py` authorized-writer boundary are named ingress points.
   Each accepts authorization context separately from caller metadata, rejects
   the bare key and every `_convmem_auth.*` key in caller input, and then
   constructs or verifies the exact trusted four-key set against the immutable
   registry. No adapter or caller mapping is merged afterward. Existing
   provenance-only validation is insufficient.
3. The query authorizer accepts a row only when its service-owned binding ID is
   in `allowed_project_bindings`, the registry maps that ID to the bound
   canonical project, the source registration is allowed by that binding, the
   protected site/domain values exactly equal that registration's immutable
   values, and those values satisfy the effective scope.

The ledger record and its Chroma projection carry the same four scalar keys,
with Chroma remaining a follower. The prefix schema is closed: all four keys
must be present, non-empty, scalar, well-typed, and mutually consistent, and no
unknown `_convmem_auth.*` key may exist. Any partial, duplicate, conflicting,
or additional prefixed set denies the row. Rebuild regenerates the projection
from ledger authority; it does not infer authorization from filenames or prose.
If the current ledger/storage path cannot reserve and protect the whole prefix,
Gate B stops: copying a claimed authorization key from a document or adapter is
not a substitute.

The service-owned site value is either a normalized hostname or the literal
`not_applicable`; ordinary blank values are invalid. Exact-site scope requires a
hostname and exact normalized equality. A `not_applicable` bound scope ignores
row-site selection but does not weaken project-binding or domain proof.

Trusted ingest rejects any row whose service-owned domain is not exact or a
descendant of its binding's declared domain root. The projection builder
repeats this check from ledger authority and fails the whole build on a
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
manifest. Rebuild scans ledger authority, applies the full bound project,
binding, site, and service-owned domain authorizer, and writes only accepted
rows into a dedicated collection/index. Domain descendants are discovered by
applying `domain_matches(auth_domain, bound_domain)` to the protected ledger
field during rebuild; model-derived `semantic_domain` is ignored. The open
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

`normalize_site()` becomes the single authority-site normalizer shared by the
registry, scope loader, ingest path, ID generator, selector resolver, and row
authorizer. It accepts a bare DNS hostname only, removes one terminal DNS dot,
and applies the pinned UTS #46 non-transitional/IDNA2008/STD3 algorithm from
Section 8.3 to produce a lowercase A-label. Schemes, ports, user info, paths,
empty labels, and underscores anywhere are rejected. Site comparison applies
this same function to the bound and requested values, then exact equality. A
strict result row must itself contain the canonical service-owned
`_convmem_auth.site` value. The current naive implementation and legacy
`source_path` inference in `unit_matches_site()` are not authority in strict
mode; ordinary adapter-supplied `metadata.site` is context only.

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
- required provenance fields are present and well-typed.

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

## 7. Deep module boundary

Scope policy belongs in a new deep module, provisionally `bound_read_scope.py`,
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

`mcp_server.py` owns only profile selection, fixed tool registration, argument
decoding, delegation, and serialization. Query, unresolved, and ledger modules
continue to own their domain behavior; they do not learn about OpenClaw.
`ledger_ids.py` owns stored-ID generation, qualified public-handle generation,
and the syntax/length validators. `normalize_site()` owns the one pinned
authority-host normalization algorithm used by both scope and ID modules. A
dedicated projection builder owns ledger-to-bound-index
materialization; `chroma_store.py` and `file_generation_store.py` expose the
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
  "schema": "convmem.raw-evidence.v1",
  "instruction_authority": "none",
  "results": [
    {
      "title": "...",
      "document": "...",
      "ledger_id": "...",
      "citation_ref": "...",
      "domain": "...",
      "site": "..."
    }
  ]
}
```

The connector must return this as tool-result data. It must not concatenate the
document into a system, developer, skill, tool-description, or user message.
Absolute paths, environment values, workspace locations, registry contents,
and private authorization reasons are excluded from the public envelope. A
`citation_ref` is an opaque, non-executable trace reference and is not accepted
as an input by any strict tool. In a strict response, `ledger_id` is not the raw
stored ID: it is the qualified public handle
`cm1.<public-binding-ref>.<external-id>`. The registry assigns each binding a
random, non-secret, immutable 128-bit lowercase-hex public reference. The
strict handle therefore names one identity across profiles without exposing a
project name or accepting a request-time scope selector. A row without a valid
stored external ID and binding reference has no public handle and cannot be
passed to `related()`.

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
Chroma storage ID. `ledger_ids.py` becomes the single owner of stored-ID and
public-handle generation and validation. The stored-ID validator uses
`re.fullmatch()` over this ASCII grammar plus a 160-code-point maximum, not
`match`, `search`, extraction, or an appended `$`:

```text
(?:dec_prop|obs|dec|ver)_[A-Za-z0-9_.-]+
```

The public-handle validator uses `re.fullmatch()` over
`cm1\.[a-f0-9]{32}\.(?:dec_prop|obs|dec|ver)_[A-Za-z0-9_.-]+`, enforces a
200-code-point maximum, and then validates the captured stored ID separately.
This is the syntax/length stage used by search. Only `related()` continues to
the authorization stage, where the public binding reference must equal an
allowed registry binding before any identity lookup. A handle copied from
another binding or profile therefore receives the generic denial even when the
same raw stored ID exists locally.

All ID generators call the stored-ID validator before returning. Site-derived
IDs use a normalization function pinned to UTS #46 non-transitional processing
with IDNA2008 semantics and STD3 rules; Python's standard-library IDNA2003 codec
is forbidden. Gate B pins the exact third-party `idna` package version and
records it in the reviewed dependency/artifact digest set. Ports, user info,
paths, empty labels, underscores anywhere, and invalid IDNA are rejected before
minting. Tests pin sharp-s, fullwidth, and underscore vectors so every writer
uses one representation.

The normalized A-label hostname is preserved in full when it is at most 80
characters. Longer legal hostnames use the deterministic segment
`h-<sha256(normalized-a-label)>` with the complete 64 lowercase hex digits.
Producer segments are normalized to `[a-z0-9-]{1,16}` and finding keys remain
bounded to 48 characters, keeping generated observation IDs within the same
160-character validator. No authorization decision parses site identity back
out of this segment; the protected site metadata remains authoritative. A
generator that cannot produce a valid bounded ID routes the source item to a
named `ledger_id_mint_denied` ingest quarantine with an operator-visible reason.
It must never substitute a UUID, truncate without a digest, or silently skip
the item. Invalid legacy IDs fail closed in strict mode until a separately
reviewed migration exists.

`agent_run_ledger.py` already performs full-string validation at an integrity
boundary. Gate B replaces that local validator with the centralized helper and
must not weaken it. The regexes in `query.py` and `cross_project_digest.py` are
extraction helpers only; strict search disables the former, and the latter's
narrower shape is a known non-authoritative recall limitation. Strict input
validation rejects Unicode confusables, whitespace, slashes, colons, missing
suffixes, embedded IDs, trailing text, and values longer than the bound below.

Every ledger write validates `id` and every non-empty `relates_to` with the
centralized helper before append. Identity is the pair `(project binding,
stored external ID)`. Re-ingest of that identity is accepted as an idempotent
re-assertion only when `provenance_identity()` returns the same assertion-ID and
commitment pair and the trusted source-registration ID is unchanged. A missing
provenance identity, changed commitment/assertion, changed source registration,
or second row under the same identity is a collision and is rejected before
append/projection rather than overwritten. A relation must resolve
unambiguously inside the same binding or the write fails. Cross-binding reuse
of a stored external ID is allowed because the strict public handle carries the
binding reference.

Strict lookup never consults the current global last-write-wins map or metadata
outside the named bound projection. It first validates the public handle and
resolves its public binding reference against the allowed registry entries,
then builds a binding-scoped multimap from the
captured stored external ID to all matching rows. Zero matches returns the
generic denial; more than one match is an integrity failure with the same
public denial; exactly one becomes the candidate target. Traversal and every
`relates_to` edge stay inside that same project-binding graph, so a row in
another binding with the same stored ID is a different identity, not a child
or overwrite. Registry startup guarantees that the binding's project, domain
root, and exact-site policy equal the bound profile, and trusted ingest forbids
a row domain outside that root. Only after the full same-binding connected
component is collected does the authorizer check target and every traversed
node against the effective site and domain scope. A node excluded only by a
caller-chosen descendant narrowing is already inside the caller's immutable
authority and may cause a whole-chain denial without revealing unauthorized
evidence. Duplicate child identities, ambiguous anchors, malformed metadata,
or any node that fails those checks deny the whole chain.

Traversal is a cycle-safe, bounded transitive closure over the relation graph
inside the named projection. Starting at the target, it follows parent
`relates_to` edges and reverse child edges recursively, across every record kind,
until the whole connected component is collected. This includes the anchor,
direct and indirect decisions, verifications attached to decisions, siblings,
unknown kinds, and every node whose metadata affected traversal or rendering.
Repeated identities or a cycle are traversed once using a visited set; an
ambiguous edge, unresolved parent, or closure beyond 200 nodes receives the
generic denial. A one-level `by_relates_to[anchor]` walk is not compliant.

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

No partial chain is returned. Authorization occurs on the full metadata graph
before the current lossy MCP formatter.

### 8.4 Request and response bounds

The strict profile rejects, rather than silently widens or coerces, inputs
outside these initial bounds:

- UTF-8 query text: 1–2,048 Unicode code points;
- `search.top_k`: integer 1–10;
- `unresolved.limit`: integer 1–50, default 20;
- stored ledger ID: centralized grammar and at most 160 code points;
- strict public ledger handle: qualified grammar and at most 200 code points;
- related graph: at most 200 collected nodes before rendering;
- one evidence document: at most 4,096 code points with an explicit
  `truncated: true` marker;
- one serialized tool response: at most 64 KiB.

Oversized or wrong-typed requests fail before retrieval. A related graph that
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
      skipBootstrap: true
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

## 12. Phase gates

### Gate A — plan review

- Claude returned a third `ADVISORY FAIL` on commit `d6edbde`; its one high,
  six medium, and four lower-severity findings are corrected in this revision
  and require advisory recheck.
- Kiro review remains blocked until that recheck finds no material unresolved
  bypass, then Kiro performs the charter-required binary review on the same
  exact revision.
- Ryan approves or rejects architecture and execution planning.

No code or OpenClaw configuration is authorized by Gate A.

### Gate B — strict ConvMem contract implementation

After a Ryan Execute grant, Cursor implements only:

- the deep bound-scope module;
- fail-closed profile parsing;
- the exact three-tool strict profile;
- empty resources and templates;
- the ingest-owned project-binding mechanism and hermetic bound fixtures;
- registry-owned source authorization domains separated from model-derived
  semantic domains;
- immutable physical serving projections for each bound-scope manifest;
- centralized ID generation/write validation, provenance-aware idempotent
  re-ingest, binding-qualified public handles, and ambiguity-denying lookup;
- strict search with no ledger-ID extraction/priority path and an authorized
  physical candidate universe;
- projection-only unresolved and bounded transitive related graphs;
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

The first smoke uses an isolated synthetic ConvMem store whose project bindings
were assigned through the reviewed ingest path. It proves transport and denial
behavior, not live-corpus readiness, channel safety, or capture safety. A smoke
against the live corpus remains blocked until Ryan separately authorizes and
reviews project-binding materialization or rebuild evidence.

### Gate E — Phase 1B scoped normal operation

Requires fresh Kiro review and Ryan approval after all adversarial tests pass.
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
    user-info, path, underscore, and invalid-IDNA form and prove denial.
11. Request another project and a prefix/suffix/case-confusable project.

### Project and row proof

12. Authorize rows only when the trusted ingest path assigned a binding that is
    allowed by the immutable scope and resolves to the bound canonical project.
13. Forge matching `project`, `domain`, `site`, the bare `_convmem_auth` key,
    each `_convmem_auth.*` key individually, the complete four-key set, an
    additional prefixed key, `project_binding_id`, `workspace_directory`, and
    `source_path` through corpus or adapter input. Also prompt the distiller to
    emit an allowed descendant domain from hostile source text. Prove every
    adapter, provenance projection helper, unit/summary add, metadata update,
    file-generation writer, and production writer boundary rejects the whole
    reserved prefix; prove the protected domain remains the source
    registration's value while model output survives only as semantic context.
    Prove an unregistered or differently bound source cannot self-label into
    the projection. Only trusted code may construct an all-or-nothing set.
    Reject partial, unknown, stale, conflicting, cross-project, and
    row-domain-outside-binding assertions.
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

21. Property-test every ID generator against the centralized `re.fullmatch`
    and length validator using full multi-label hosts, two hosts sharing the
    same first label, `www.*`, single-label hosts, ports, user info, paths,
    empty labels, trailing newlines, confusables, and maximum length. Pin UTS
    #46 non-transitional/IDNA2008 vectors for `straße`, `strasse`, fullwidth
    characters, underscores in any label position, and long legal hostnames. Prove the
    digest-bounded host segment is deterministic and generator failure enters
    `ledger_id_mint_denied` rather than a UUID fallback.
22. At ledger write time, reject malformed `id` and `relates_to`, a conflicting
    assertion under the same binding/ID, a changed source registration, and an
    ambiguous relation. Re-ingest the exact same provenance identity and source
    registration and prove it is idempotent. Prove the existing
    `agent_run_ledger` integrity check is preserved through centralization and
    cross-binding stored-ID reuse yields distinct qualified public handles.
23. Build collisions across two bindings and within one binding, including two
    sites while `site_mode=not_applicable`. Prove strict lookup validates the
    public binding reference before identity resolution, resolves one
    authorized row, and gives the generic denial for more than one authorized
    match—never last-write-wins. Paste a valid qualified handle from binding A
    into a binding-B profile and prove generic denial even when B contains the
    same stored external ID.
24. Retrieve a fully in-scope, unambiguous transitive chain, including a
    verification attached to a decision at depth two. Prove cycle handling is
    finite and a component exceeding 200 nodes receives generic denial.
25. Request an out-of-scope, unknown, malformed, embedded, trailing-text, and
    raw-Chroma ID; prove byte-equivalent public denial shapes.
26. Put one out-of-effective-scope decision, verification, sibling,
    unknown-kind child, or metadata-incomplete node behind an in-scope target;
    prove the entire chain is denied without partial output. Prove registry
    startup rejects an exact-site binding spanning two sites or a binding whose
    domain root differs from the profile bound, and prove trusted ingest plus
    rebuild reject a row whose protected domain lies outside its binding root.
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

## 14. Verification commands and evidence

The future execution plan must name exact commands, but the minimum evidence
set is already fixed:

- focused unit tests for selector resolution and membership proof;
- trusted-ingest tests proving corpus and adapter inputs cannot forge any
  `_convmem_auth.*` key or create a partial authorization set, and proving
  hostile distiller domain output cannot affect the registry-owned domain;
- physical bound-projection tests proving rows outside the immutable profile
  scope cannot affect any strict tool's cost, cache, count, order, or shape;
- focused MCP inventory tests for tools, resources, and templates;
- focused cycle-safe transitive related-chain graph tests;
- generator/validator property tests plus UTS #46/IDNA2008 vectors,
  provenance-aware re-ingest, binding-scoped collision, qualified-handle,
  ambiguous-relation, and write-rejection tests;
- scoped unresolved-graph tests with out-of-scope child verifications;
- connector child-environment allowlist and remote-node refresh tests;
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
boundary, `chroma_write_store.py`, and the ingest/distill merge points so
candidate-store capabilities, domain ownership, and prefix stripping are
reviewable rather than asserted.

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
- a corpus or adapter field can forge, preserve, or override any reserved
  authorization key, or a partial/additional `_convmem_auth.*` set authorizes;
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
- an ID generator can emit a value rejected by the canonical length/grammar
  validator, uses unpinned/IDNA2003 normalization, or falls back to a UUID;
- a conflicting assertion under one binding/ID is accepted, an identical
  provenance re-assertion is rejected, last-write-wins is consulted, or
  identity resolution occurs before the qualified binding check;
- an exact-site binding spans sites, a binding domain differs from the profile
  bound, or a cross-profile qualified handle resolves locally;
- strict ledger-ID authorization uses an extraction regex or anything other
  than the centralized full-string validator;
- related returns a one-level or otherwise partial relation component;
- OpenClaw native memory, ACP dispatch, ACP execution, or a subagent child is
  active;
- an eligible skill, workspace instruction, hook, or plugin prompt is injected;
- a remote node pairs/connects or changes the eligible-skill snapshot;
- the connector child inherits ambient environment variables or consults a
  legacy read-scope variable;
- a same-ID plugin resolves outside the approved path or has the wrong digest;
- inference or connector traffic reaches an unapproved network destination;
- hostile corpus content reaches an instruction channel or triggers an action;
- interruption can be reported as success;
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

Claude returned a third `ADVISORY FAIL` on commit `d6edbde`. A fresh advisory
reviewer must independently try to falsify this corrected exact revision and
answer with exact references before Kiro review resumes:

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
13. Can deterministic re-ingest be mistaken for a collision, can IDNA/library
    variation split or merge identities, or can any generator exceed its own
    validator?
14. Do site identity, transitive traversal, response-size precedence, or child
    session controls have more than one interpretation?
15. Is any acceptance test circular, unverifiable, internally contradictory,
    or dependent on current web documentation rather than bundled
    installed-binary evidence?

The advisory reviewer returns `ADVISORY PASS`, `ADVISORY FAIL`, or `INCOMPLETE`.
After advisory PASS, Kiro independently returns the charter-required binary
design-review `PASS` or `FAIL` on the same revision. Only Ryan may authorize
implementation after a Kiro `PASS`.

## 18. Exit state

This document stops at architecture. It is not an Execute grant. The findings
from the third advisory FAIL on commit `d6edbde` are incorporated, but Kiro
remains blocked until the corrected exact revision receives advisory re-review.
A separate execution plan and Cursor handoff are created only after advisory
PASS, Kiro PASS, and Ryan architecture approval.

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
