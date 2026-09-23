# Architecture Direction — OpenClaw orchestration with ConvMem evidence

**Source:** revise upstream adversarial findings and Ryan’s request for a design
document for cross-agent review
**Authority:** Awaiting HITL review by Kiro and approval by Ryan
**Date:** 2026-09-20
**Arc:** ConvMem Switchboard
**Problem:** Add OpenClaw as the user-facing orchestrator without allowing
unscoped retrieval, prompt-injection escalation, external-channel compromise,
or unsafe transcript capture to weaken ConvMem’s authority and integrity.

## Planning Status

**Phase:** Architecture Planning
**Characters:** Architect, Systems Thinker, Risk Reviewer
**Functions:** Planner
**Lanes:** Codex authors; Kiro reviews; Ryan approves
**Authority:** Awaiting HITL

## System boundary

### In scope

- OpenClaw’s external perimeter: channels, sender authentication, Gateway
  exposure, and worker/tool permissions.
- A version-adapted, read-only OpenClaw-to-ConvMem connector.
- Server-enforced project, site, and domain read scope.
- Tool and resource enumeration, including ConvMem’s `memories://` and
  `memory://` brief resources.
- Output-side authorization for `related(ledger_id)` evidence traversal.
- Deferral of `ask()` until synthesized-result handling is verified.
- The future OpenClaw transcript capture boundary, including quarantine and
  ledger-first ingestion.

### Out of scope

- Replacing ConvMem’s append-only ledger or making OpenClaw native memory the
  source of truth.
- Giving OpenClaw a durable `record` or `approve` capability.
- Enabling continuous transcript capture before its independent safety gate.
- A ConvMem microservice, remote corpus, or second memory implementation.
- Building the four project-specific OpenClaw workspaces in this architecture
  phase.
- Choosing an OpenClaw upgrade without a separate authorization.

## Existing constraints and evidence

1. The ConvMem MCP surface is read-only. `mcp_server.py` documents durable
   writes as CLI-only and exposes the eight read-only tools through decorators
   in [`mcp_server.py`](../../mcp_server.py:686).
2. Full MCP mode also exposes four brief resources and aliases through
   `@mcp.resource`; the shell profile omits them in
   [`mcp_server.py`](../../mcp_server.py:726).
3. Retrieval scope is currently a default, not a ceiling. The current
   precedence is `cross_domain > explicit argument > session default >
   unscoped` in [`read_scope.py`](../../read_scope.py:63).
4. Site filtering is fail-open when the site argument is empty in
   [`site_filter.py`](../../site_filter.py:49).
5. Domain containment is hierarchical. `domain_matches(unit_domain,
   query_domain)` accepts an exact match or a child of the query domain in
   [`domains.py`](../../domains.py:62). For a scope ceiling, the containment
   check must therefore be called as
   `domain_matches(requested_domain, bound_domain)`.
6. Omitted arguments require their own branch. An empty domain passed to
   `domain_matches()` does not mean “inherit the bound scope”; it would fail
   the containment check for a non-empty bound domain. Omission must resolve
   directly to the bound value before containment logic runs.
7. `related(ledger_id)` accepts no scope parameter and traverses a target,
   observation, decisions, verifications, and siblings through
   [`ledger.py`](../../ledger.py:456) and [`mcp_server.py`](../../mcp_server.py:898).
   Authorization must therefore occur after traversal and before rendering.
8. `brief(project=...)`, `folder_state(project=...)`, and the project resource
   aliases share `_resolve_brief_project()`. Caller-selected project names are
   another scope selector and must not be treated as caller identity.
9. The installed OpenClaw binary is `2026.3.2`; it currently reports no
   `openclaw mcp` command, and no `~/.openclaw/openclaw.json` exists. Current
   OpenClaw documentation describes newer MCP surfaces, so capability discovery
   must precede configuration.
10. ConvMem currently has high-severity evidence of a poison-transcript/native
    Chroma upsert crash loop. Transcript capture is therefore a separate,
    blocking data-integrity phase, not ordinary wiring.
11. The ledger owns durable facts; Chroma is a rebuildable serving projection.
    OpenClaw capture must follow ledger → derived index ordering.

## Security and authority invariants

1. OpenClaw is the coordinator, not the durable-memory authority.
2. Git, GitHub, and project tools remain the authority for live project state.
3. ConvMem tool results—raw, cited, or synthesized—are inert evidence, never
   executable instructions.
4. Durable ConvMem writes remain Ryan-approved CLI operations.
5. A bound project/site/domain scope is a hard ceiling. Caller arguments may
   narrow it but never widen it.
6. An omitted selector under a bound scope inherits that scope and returns
   eligible results; it must not become unscoped, empty, or an error solely
   because the selector was omitted.
7. Site scope uses normalized hostname equality. Domain scope permits only
   descendants of the bound dotted domain; parents and siblings are rejected.
8. `cross_domain=true` is rejected under a bound scope.
9. Project selectors in `brief`, `folder_state`, and resource URIs cannot
   select a project outside the bound project.
10. The strict OpenClaw profile exposes no ConvMem resources. If a full profile
    is ever used, every resource must enforce the same scope contract.
11. `related()` is all-or-nothing under scope: if the target or any linked
    evidence node cannot be proven in scope, return a scope-denied result
    without revealing the out-of-scope chain.
12. OpenClaw’s reachable channels and senders are explicit and authenticated;
    unknown senders cannot invoke tools or workers.
13. OpenClaw plugin-tools/native-memory injection into ACP workers is explicitly
    disabled unless separately reviewed.
14. Capture failures quarantine the source with bounded retry; no native crash
    may trigger an infinite retry loop against shared Chroma state.

## Scope-resolution contract

The resolver must distinguish omitted selectors from explicit selectors. The
conceptual algorithm is:

```text
resolve(bound, requested):
    if bound.project exists:
        if requested.project is omitted: use bound.project
        else if requested.project != bound.project: deny

    if bound.site exists:
        if requested.site is omitted: use bound.site
        else if normalize_site(requested.site) != normalize_site(bound.site): deny

    if bound.domain exists:
        if requested.domain is omitted: use bound.domain
        else:
            requested = normalize_domain(requested.domain)
            if not domain_matches(requested, bound.domain): deny

    if requested.cross_domain is true: deny
    return the bound scope plus permitted narrower selectors
```

The production implementation should use an explicit omitted sentinel rather
than collapsing omission into `""`. Each denial must be observable in
structured metadata without disclosing the rejected resource’s existence.

For `related()` the resolver is different:

1. Resolve the supplied ledger ID internally.
2. Collect metadata for target, observation, decisions, verifications, and
   siblings before formatting the response.
3. Verify every node against the bound project/site/domain scope.
4. If any node is out of scope or lacks enough metadata to prove scope, return
   `scope_denied` without IDs, titles, or chain shape.
5. Only then render the chain. Do not authorize after the lossy MCP formatter
   has removed site/project metadata.

This is intentionally stricter than filtering individual children: a partial
chain can reveal relationships and can be mistaken for a complete evidence
chain.

## Options considered

| Option | Summary | Rejected because |
|---|---|---|
| A. Version-adapted read-only ConvMem surface, chosen | OpenClaw receives a strict, scoped ConvMem connector; use the installed transport capability, with MCP preferred where actually supported and a narrow local adapter only for the isolated smoke path. Workers retain direct read access where already wired. | — |
| B. OpenClaw-only memory broker | OpenClaw retrieves ConvMem and injects all context into workers. | Creates a context bottleneck, duplicates retrieval policy, and makes OpenClaw a second memory authority. |
| C. OpenClaw native memory primary | ConvMem periodically exports or summarizes OpenClaw memory. | Loses ledger authority, weakens provenance, and makes replay/completeness difficult to prove. |

## Chosen direction

Choose Option A. OpenClaw becomes the front door and workflow coordinator, while
ConvMem remains the shared, read-only evidence layer for agent retrieval and the
ledger-backed authority for durable facts. The connector is a strict profile,
not a prompt convention: project/site/domain scope is bound by the server
instance, tool arguments can only narrow, resources are absent by default, and
`related()` performs post-traversal authorization. `ask()` stays out of the
initial OpenClaw allowlist until synthesized-result handling is proven.

The transport is deliberately treated as an adapter detail. The installed
OpenClaw binary must be probed and pinned before configuration; current docs
cannot be assumed to describe `2026.3.2`.

## Phase gates

### Phase 0 — perimeter and capability lock

Required evidence:

- installed version and command/config capability probe;
- explicit OpenClaw channel, account, sender, and Gateway exposure inventory;
- explicit plugin-tools/native-memory bridge setting;
- bound project/site/domain contract selected for each OpenClaw session;
- strict ConvMem profile selected;
- resources confirmed absent, or separately authorized as scope-aware.

### Phase 1A — isolated read-only smoke

Allowed immediately after Phase 0 capability discovery:

- local operator-only session;
- no external channels;
- raw retrieval tools only;
- no `ask()`;
- no transcript capture;
- no durable ConvMem write path.

### Phase 1B — scoped normal operation

Requires passing the complete tool/resource/scope/related/perimeter review.

### Later phases

Generated protocol surface, worker routing, transcript capture, ingest
quarantine, and operational soak remain downstream phases. Transcript capture
cannot begin until it proves source identity, append/replay idempotence,
ledger-first ordering, bounded retry, quarantine, and hash-plus-chunk-offset
completeness.

## Adversarial review matrix

Kiro should review the exact implementation revision against these cases:

1. Enumerate both tools and resources. Prove no write/approve tool is exposed;
   prove strict OpenClaw mode exposes no resources.
2. Omit site/domain/project under a bound scope. Assert that the bound scope is
   inherited and returns eligible results—not an error, empty result, or
   unscoped result.
3. Request a valid descendant domain. Assert allowed narrowing.
4. Request a parent or sibling domain. Assert denial.
5. Request another normalized site, including protocol/case variations. Assert
   equality-only behavior after `normalize_site()`.
6. Set `cross_domain=true`. Assert denial under a bound session.
7. Request another project through `brief`, `folder_state`, and resource URIs.
   Assert denial without leaking the other project’s payload.
8. Pass a known in-scope ledger ID to `related()` and an out-of-scope ID to the
   same bound session. Assert complete in-scope output and non-revealing denial.
9. Verify that an out-of-scope child cannot be exposed through a related chain
   whose target is in scope.
10. Retrieve hostile content through raw search and, later, `ask()`. Assert the
    outer agent treats it as data rather than instructions.
11. Test every configured external channel and sender policy, including an
    unknown sender and an unapproved group context.
12. Inspect ACP child sessions for plugin-tools/native-memory injection.
13. Kill a worker mid-task and restart OpenClaw. Assert explicit incomplete
    state and no false completion.
14. Replay, truncate, and poison-test the future capture adapter. Assert
    idempotence, quarantine, bounded retry, and corpus preservation.

## Risks and reversibility

- **Over-restriction:** strict scope may deny legitimate cross-project work.
  This is reversible through a separately authorized unscoped/Ryan-only
  connector; fail-closed is preferable to silent leakage.
- **Transport mismatch:** the installed OpenClaw may require a local adapter or
  a separately authorized upgrade. Keep the ConvMem contract transport-neutral.
- **Resource drift:** a future OpenClaw or ConvMem profile may expose resources
  by default. Add `tools/list` and `resources/list` checks to the smoke gate.
- **Related-chain information loss:** all-or-nothing denial may reduce utility,
  but partial evidence chains are unsafe and difficult to interpret.
- **Capture complexity:** quarantine and replay state are new ingest
  mechanisms, not reuse of serving/recovery quarantine. Keep capture disabled
  until independently verified.

## Downstream handoff

- **Kiro:** perform read-only PASS/FAIL review against this document and the
  exact implementation revision; focus on scope precedence, omitted selectors,
  resources, project binding, and `related()` output authorization.
- **Ryan:** approve or reject the architecture direction. No execution or
  durable ConvMem write is authorized by this document.
- **Cursor:** after HITL approval, shape the approved direction into an
  execution plan and implementation slices. Do not implement from this
  architecture document alone.

**Stop state:** Awaiting HITL approval.
