# Architecture Plan — OpenClaw orchestration with a bounded ConvMem evidence surface

**Status:** DRAFT FOR CLAUDE ADVERSARIAL REVIEW — advisory review only; no
implementation, OpenClaw configuration, production smoke, or capture is
authorized

**Date:** 2026-09-20

**Arc:** none (ad-hoc integration)

**Authority:** Codex architecture/planning lane. Kiro remains the required
design-review lane and Ryan remains the approval authority. Claude's requested
adversarial review may find blockers but cannot authorize execution.

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

Phase 1 therefore uses a narrow OpenClaw plugin that is an MCP client for a
local ConvMem strict-profile subprocess. It contains no retrieval or scope
policy. It translates three fixed plugin tool calls to MCP stdio and returns
the server response unchanged inside an untrusted-evidence envelope.

The connector must spawn with a fixed executable, fixed argument vector, fixed
working directory, sanitized environment, and no shell. Query text, selectors,
ledger IDs, channel messages, and corpus content may never influence the
executable path, arguments before the MCP protocol boundary, environment keys,
scope-file path, project-binding-registry path, or working directory.

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
- `ledger.py:28-104,278-330` has domain, site, and source fields but no reserved
  project binding or protected authorization namespace.
- `brief.py:255-273` uses title, document, site, and source-path substring
  heuristics for project matching.
- `mcp_server.py:898-939` renders a related chain without scope authorization
  and distinguishes a missing ID, while `ledger.py:415-430,456-497` accepts raw
  Chroma IDs and omits unknown-kind children from the rendered subsets.

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
  "site": null
}
```

`project`, `allowed_project_bindings`, and `domain` are mandatory and
non-empty. Each binding ID must resolve in the service-owned registry to the
same canonical project named by `project`. `site_mode` is either `exact` or
`not_applicable`. `site` is mandatory and non-empty only in `exact` mode. No
dimension has an implicit unscoped state.

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
   `project:convmem:v1`, to one canonical project and a set of reviewed ingest
   source-registration IDs. It receives the same regular-file, ownership,
   symlink, mode, closed-schema, startup, and restart checks as the scope file.
2. During trusted ingestion, after source parsing, ConvMem constructs a reserved
   `_convmem_auth` record containing `project_binding_id`, normalized `site`,
   normalized `domain`, and `source_registration_id`. The ingest API strips and
   rejects that namespace in adapter output and corpus input before constructing
   it from operator/CLI/watch configuration. It never copies authorization
   values out of document content.
3. The query authorizer accepts a row only when its service-owned binding ID is
   in `allowed_project_bindings`, the registry maps that ID to the bound
   canonical project, the source registration is allowed by that binding, and
   the service-owned site/domain labels satisfy the effective scope.

The ledger record and its Chroma projection carry the same `_convmem_auth`
record, with Chroma remaining a follower. Rebuild regenerates the projection
from ledger authority; it does not infer authorization from filenames or prose.
If the current ledger/storage path cannot reserve and protect this namespace,
Gate B stops: copying a claimed `_convmem_auth` or `project_binding_id` from a
document or adapter is not a substitute.

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
        explicit -> normalize
        allow only if domain_matches(requested, bound.domain)

    cross_domain true -> deny
    cross_domain false or omitted -> continue

    return effective selectors
```

For domain containment the call direction is normative:
`domain_matches(requested_domain, bound_domain)`. Exact and descendant domains
may narrow. Parent, sibling, empty, malformed, and `general`-as-widening
requests are denied.

Site comparison uses `normalize_site()` on the bound value and the requested
value, then exact equality. A strict result row must itself contain an explicit
service-owned `_convmem_auth.site` whose normalized hostname equals the
effective site. The legacy `source_path` inference in `unit_matches_site()` and
ordinary adapter-supplied `metadata.site` are not authority in strict mode.

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

Unknown or missing metadata denies the row. Search may return fewer than
`top_k`; it may not refill from unauthorized rows after a bound is reached.
Keyword fallback, exact-ledger priority injection, vector retrieval, reranking,
recent-result injection, and any future fallback must all pass the same final
authorizer.

## 7. Deep module boundary

Scope policy belongs in a new deep module, provisionally `bound_read_scope.py`,
not in `mcp_server.py`.

The module owns:

- strict scope-file parsing and validation;
- project-binding registry validation;
- the omitted-selector sentinel;
- selector resolution;
- project membership proof;
- row authorization;
- related-chain authorization;
- public non-revealing denial payloads;
- private structured audit reasons.

`mcp_server.py` owns only profile selection, fixed tool registration, argument
decoding, delegation, and serialization. Query, unresolved, and ledger modules
continue to own their domain behavior; they do not learn about OpenClaw.

There must be one policy path shared by all three strict tools. A handler-local
check is not acceptable.

## 8. Tool contracts

### 8.1 `search`

Inputs are `query`, bounded `top_k`, optional project/site/domain selectors,
and optional `cross_domain`. Explicit project exists to test narrowing rules;
it cannot select another project.

The tool returns only rows authorized by the effective scope. Each row is
wrapped as untrusted evidence with a stable citation and no executable fields:

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
as an input by any strict tool. `ledger_id` is present only for a row with a
valid external ledger ID.

OpenClaw may summarize the returned data for its user, but no second model call
occurs inside ConvMem. Excluding `ask()` removes that additional synthesis and
prompt-injection surface; it does not pretend the orchestrating model performs
no synthesis.

### 8.2 `unresolved`

Inputs are an optional bounded `limit`, optional project/site/domain selectors,
and optional `cross_domain`. Omitted selectors inherit the bound scope. Domain
matching is hierarchical, not the current exact-string comparison. Every
observation and every child consulted to determine status must be within scope
or the observation is omitted. Results use the same untrusted-evidence
envelope.

### 8.3 `related`

Strict `related` accepts only a syntactically valid external ledger ID, never a
raw Chroma UUID.

The traversal must collect before rendering:

- the target;
- the anchor observation;
- all direct children of the anchor, including unknown kinds;
- decisions;
- verifications;
- sibling decisions;
- every node whose metadata affected traversal or rendering.

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
request correlation ID, but never corpus document text.

No partial chain is returned. Authorization occurs on the full metadata graph
before the current lossy MCP formatter.

### 8.4 Request and response bounds

The strict profile rejects, rather than silently widens or coerces, inputs
outside these initial bounds:

- UTF-8 query text: 1–2,048 Unicode code points;
- `search.top_k`: integer 1–10;
- `unresolved.limit`: integer 1–50, default 20;
- ledger ID: valid external-ID grammar and at most 160 code points;
- related graph: at most 200 collected nodes before rendering;
- one evidence document: at most 4,096 code points with an explicit
  `truncated: true` marker;
- one serialized tool response: at most 64 KiB.

Oversized or wrong-typed requests fail before retrieval. A related graph that
exceeds its bound receives the same non-revealing public denial as other
unavailable chains. The connector has a fixed timeout and output cap at least
as strict as the server; timeout or truncation is a failure, never success.

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
  acp: { enabled: false }
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
skill eligibility change.

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

ACP remains disabled through Phase 1B. A future ACP phase requires a new plan
because ACP workers run on the host and may inherit harness-specific MCP,
plugin, skill, memory, and filesystem surfaces. The required initial ACP test
is therefore a negative control: attempts to spawn or route an ACP session must
fail closed and must not create a child session. If any child session appears,
inspect its complete plugin, native-memory, skill, prompt, and tool inventory
and return FAIL; its mere existence already fails this phase.

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

- Claude adversarially reviews this exact Git revision and returns written
  findings or an advisory PASS.
- Codex resolves material findings in the plan.
- Kiro performs the charter-required binary design review on the corrected
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
- no external channels;
- native memory disabled;
- ACP disabled;
- exact three-tool inventory;
- zero eligible skills, workspace instructions, and plugin prompts;
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
10. Request site variants differing only in supported normalization and prove
    equality; request another hostname, a port variant, trailing-dot variant,
    user-info form, and Unicode/IDNA ambiguity and prove no widening.
11. Request another project and a prefix/suffix/case-confusable project.

### Project and row proof

12. Authorize rows only when the trusted ingest path assigned a binding that is
    allowed by the immutable scope and resolves to the bound canonical project.
13. Forge matching `project`, `domain`, `site`, `_convmem_auth`,
    `project_binding_id`, `workspace_directory`, and `source_path` values
    through corpus or adapter input; prove none can create or override a
    service-owned authorization record. Reject unknown, stale, conflicting, and
    cross-project registry bindings.
14. Prove legacy rows without a service-owned binding reduce recall rather than
    leak, and prove Gate B never backfills the live corpus.
15. Prove strict site filtering rejects source-path-only site inference.
16. Prove every fallback and priority-injection path receives the same final
    row authorizer.

### Project selectors and resources

17. Attempt another project through `brief`, `folder_state`,
    `memories://brief/{project}`, and `memory://brief/{project}`. Prove the
    surfaces are absent in strict mode.
18. Call `resources/read` directly with both aliases, another project, URI
    encoding, and malformed URIs; prove strict mode resolves none and reveals no
    project information.

### Related-chain authorization

19. Retrieve a fully in-scope chain.
20. Request an out-of-scope, unknown, malformed, and raw-Chroma ID; prove
    byte-equivalent public denial shapes.
21. Put one out-of-scope decision, verification, sibling, unknown-kind child,
    or metadata-incomplete node behind an in-scope target; prove the entire
    chain is denied without partial output.
22. Prove authorization occurs before formatting and private audit output does
    not contain corpus text.

### OpenClaw isolation and hostile evidence

23. Validate the exact `2026.3.2` config and inspect effective tool, plugin,
    skill, hook, bootstrap, workspace, and prompt-source inventories in a new
    session.
24. Prove `memory-core`, `memory_search`, `memory_get`, automatic memory flush,
    filesystem, runtime, browser, session, messaging, cron, gateway, and node
    tools are absent.
25. Attempt ACP spawn through natural language, slash command, and tool call;
    prove no child session is created.
26. Retrieve hostile corpus content containing tool calls, role labels, scope
    overrides, memory instructions, and false-completion claims. Prove it stays
    inside the untrusted result envelope and causes no action.
27. Attempt command, argv, cwd, environment, and scope-file injection through
    every connector input.
28. Inspect the effective model/provider route, disable fallback, deny general
    egress, and prove synthetic evidence never reaches a remote model or
    unapproved endpoint.

### Interruption and perimeter

29. Kill the ConvMem child before response, during response, and after response
    receipt but before outer serialization; only the last fully serialized path
    may succeed.
30. Restart the OpenClaw gateway during a call and prove no persisted false
    completion or automatic replay.
31. For Phase 1B, test every configured channel, account, sender allowlist,
    group policy, mention rule, pairing policy, and Gateway exposure. Unknown or
    unapproved origins must fail before tool invocation.

### Capture negative controls

32. Prove no OpenClaw transcript path is watched or indexed.
33. Prove successful MCP retrieval does not create a capture authorization,
    quarantine claim, or background indexing route.
34. Exercise every request, graph, document, response, timeout, and wrong-type
    bound; prove rejection or marked truncation cannot become partial success or
    change scope.

## 14. Verification commands and evidence

The future execution plan must name exact commands, but the minimum evidence
set is already fixed:

- focused unit tests for selector resolution and membership proof;
- trusted-ingest tests proving corpus and adapter inputs cannot forge project
  bindings;
- focused MCP inventory tests for tools, resources, and templates;
- focused related-chain graph tests;
- existing retrieval, brief, resource, and ledger regression tests;
- ConvMem smoke checks from `docs/CODEX-DEEPSEEK-VERIFY.md` where relevant;
- `openclaw --version`, command inventory, config validation, plugin inventory,
  effective agent tool inventory, prompt/skill/hook inventory, model-provider
  route, network destinations, channel inventory, and security audit from the
  installed binary;
- production-path and network denial in hermetic tests;
- exact revision, config digest, scope-file digest, and test output in the
  review handoff.

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
- a corpus or adapter field can forge, preserve, or override a service-owned
  project binding;
- a row with missing proof is returned;
- `cross_domain=true` widens retrieval;
- a resource or unexpected tool appears;
- `related()` reveals any partial or existence information across scope;
- OpenClaw native memory or ACP is active;
- an eligible skill, workspace instruction, hook, or plugin prompt is injected;
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
enforced after retrieval by server code.

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

## 17. Review questions for Claude

Claude should try to falsify the plan, not restate it. A useful review answers
these questions with exact references:

1. Can any request-time input affect the bound scope or connector process
   launch before server authorization?
2. Can a legacy row, ledger child, fallback result, or resource escape project,
   site, or domain proof?
3. Is `domain_matches()` called in the correct direction at both selector and
   row-authorization stages?
4. Can omission, explicit blank, normalization, aliasing, or malformed values
   create a wider result?
5. Does project proof trust any attacker-controlled prose or ambiguous path?
6. Can `related()` act as an existence oracle or return a misleading partial
   chain?
7. Can OpenClaw `2026.3.2` still expose core tools despite the plugin allowlist?
8. Can native memory, automatic memory flush, skills, plugin prompts, or ACP
   child configuration reintroduce a second authority or injection route?
9. Can hostile evidence cross from tool-result data into an instruction
   channel?
10. Can a crash, timeout, cancellation, or restart become false completion?
11. Does any phase silently authorize external config, channels, capture,
    indexing, durable writes, or ACP?
12. Is any acceptance test circular, unverifiable, or dependent on current web
    documentation rather than the installed binary?

Claude should return one of:

- `ADVISORY PASS` — no material bypass found;
- `ADVISORY FAIL` — one or more material bypasses, each with an exploit path,
  affected section, and required correction;
- `INCOMPLETE` — evidence needed to evaluate a named proposition.

Only Kiro may issue the required design-review PASS/FAIL, and only Ryan may
authorize implementation.

## 18. Exit state

This document stops at architecture. It is not an Execute grant. After Claude
adversarial review, Codex incorporates justified findings and presents an exact
revision to Kiro. A separate execution plan and Cursor handoff are created only
after Kiro PASS and Ryan architecture approval.

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
