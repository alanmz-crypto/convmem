# Neutral Core candidate evidence

| Field | Value |
|---|---|
| Status | Current-tree assessment at 2026-07-23; classifications are extraction gates, not commitments |
| Source | ConvMem Engineering reference baseline `152db79` (`origin/main`, after Ryan merged application closeout PR `#105` on 2026-07-23) plus the same-day operational-independence audit |
| Question | Which current mechanisms are ready, which need more domain evidence, and which must stay project-owned? |
| Companion | [Neutral target](NEUTRAL-TARGET.md) and [office extraction probe](EXTRACTION-PROBE.md) |

## How to read the classifications

**Ready to transfer or extract** means a narrow behavior may be copied into the
office implementation now. It does **not** authorize a Neutral repository. Actual
extraction additionally requires identical behavior in both applications and a
coherent standalone slice.

**Needs one office implementation for comparison** is the ceiling for mechanisms
whose general shape is unknown. Conceptual importance does not raise the rating.
**Needs a second workflow for confirmation** means the first office workflow can
exercise the behavior but cannot establish that its shape is stable. **Must remain
project-owned** is a boundary decision, not a defect.

## Ready to transfer or extract

| Candidate | Current source and evidence | Present assumptions | Identical behavior possible? | Adaptation and missing evidence | Recommended disposition |
|---|---|---|---|---|---|
| Canonical JSON and SHA-256 mechanics | [`ledger_content_hash.py:17-42`](../../ledger_content_hash.py#L17-L42) is a standard-library leaf: NFC text normalization, sorted compact JSON and SHA-256. | Its v1 projection is an engineering record field list including `site`, `rationale`, `alternatives_rejected` and `constraints` at [`ledger_content_hash.py:9-14`](../../ledger_content_hash.py#L9-L14). | **Mechanics: yes. Projection: unproven.** | Copy the algorithm and tests; define the office projection locally. Missing: evidence that the two projections have a common stable subset and compatible schema-version rules. | Transfer the tiny primitive to Office Team as `[adapted]`; extract only after the record comparison. Do not share the current field tuple by assumption. |
| Durable append pattern | Approved decisions append JSONL, flush and `fsync` at [`propose_decision.py:72-77`](../../propose_decision.py#L72-L77); proposal events do the same at [`conflict_events.py:55-61`](../../conflict_events.py#L55-L61). | File names, payloads and lifecycle policy are engineering-specific. The code does not define a general ledger transaction. | **The durability behavior can remain identical.** | Reimplement the six-line pattern around an office-owned record and path. Missing: crash-boundary behavior for the complete office write/project sequence. | Transfer the behavior and contract test, not these modules. A standalone shared append helper is too small to justify Neutral by itself. |

## Needs one office implementation for comparison

| Candidate | Current source and evidence | Present assumptions | Identical behavior possible? | Adaptation and missing evidence | Recommended disposition |
|---|---|---|---|---|---|
| Canonical record envelope and kinds | [`ledger.py:18-25`](../../ledger.py#L18-L25) fixes observation/decision/verification and maps verification to an observation unit; dataclasses default to `web_stack.security` at [`ledger.py:28-104`](../../ledger.py#L28-L104). Normalization requires `author_model`, normalizes engineering domains and invents UUIDs at [`ledger.py:158-205`](../../ledger.py#L158-L205). | Agent authors, sites, security severity, current domain taxonomy, Chroma unit shape and engineering kind semantics. No completion record exists. | **Unknown.** A small common envelope is plausible; current structures cannot remain unchanged. | Office defines its own records first. Compare required identity, timestamp, actor, provenance and relationship fields after the workflow passes. | `[new-and-maybe-general]`; keep local in Office Team until comparison. Do not move the dataclasses wholesale. |
| Stable semantic identifiers | [`ledger_ids.py:1-47`](../../ledger_ids.py#L1-L47) encodes website hostnames, Lighthouse/WP security producers and `obs_<site>_<producer>_<key>`. Other records fall back to random IDs at [`ledger.py:177-181`](../../ledger.py#L177-L181). | WordPress/security producers and site identity; no demonstrated office business key or revision rule. | **The stability invariant may match; the identifier grammar will not.** | Office must choose IDs from its real source/request and test duplicate delivery plus restart. Missing: common namespace, collision and revision semantics. | `[adapted]`; copy normalization ideas only, then compare invariants after the office run. |
| Ledger-first writes and replay | Normal observation ingestion embeds and writes Chroma first at [`observe.py:83-137`](../../observe.py#L83-L137), then optionally appends a normalized *derived unit* to `units_export`. Approved decisions instead own a separate durable JSONL and recovery flow at [`propose_decision.py:221-276`](../../propose_decision.py#L221-L276). | Split sources of truth, Ollama embedding inside the write path, Chroma metadata shape, governed-decision exceptions and mutable export upserts. | **Unknown and currently not identical even inside ConvMem.** | Office implements a ledger-first journal with projection replay locally and tests crash/restart behavior. Missing: comparison of ordering, idempotency, failure recovery and update semantics. | `[new-and-maybe-general]`; classification is locked no higher than this category for the first comparison. No ConvMem refactor yet. |
| Derived indexing and Chroma adapter | `ChromaStore` accepts a path at [`chroma_store.py:96-104`](../../chroma_store.py#L96-L104), but owns ConvMem collection names and decision-governance checks at [`chroma_store.py:15-20`](../../chroma_store.py#L15-L20) and [`chroma_store.py:162-188`](../../chroma_store.py#L162-L188). Read-only access queries Chroma's internal SQLite schema at [`chroma_readonly.py:34-76`](../../chroma_readonly.py#L34-L76). | Chroma version/schema, collection names, superseded semantics and engineering decision policy. Module caches are path-keyed, not cross-path global, at [`chroma_store.py:18-41`](../../chroma_store.py#L18-L41). | **Storage mechanics may match; backend contract is unproven.** | Office may copy a thin path-injected Chroma adapter if useful, with office collection names and no approval policy. Missing: replay equivalence, version pin and whether both apps need Chroma at all. | `[adapted]`; treat Chroma as a replaceable projection, not Neutral's source of truth or required meaning. |
| Provenance relationship representation and traversal | `relates_to` is required for decisions/verifications at [`ledger.py:203-205`](../../ledger.py#L203-L205); traversal groups only observation anchors with decision/verification children at [`ledger.py:446-487`](../../ledger.py#L446-L487). | A shallow engineering chain, fixed kinds, one parent string, Chroma metadata scan and last-record-wins dedupe. | **Plausible, not demonstrated.** | Office records explicit links through the full request→completion→verification chain. Compare cardinality, link types and revision behavior. | `[new-and-maybe-general]`; keep an office-local graph view until both chains agree. |
| Human decision durability and recovery mechanics | Proposal lifecycle transitions are hard-coded at [`conflict_events.py:13-18`](../../conflict_events.py#L13-L18); deterministic reduction is at [`conflict_events.py:85-116`](../../conflict_events.py#L85-L116). Approval recovery reconciles JSONL and Chroma at [`propose_decision.py:221-276`](../../propose_decision.py#L221-L276). | Engineering proposal states, conflict rules, Chroma markers and separate approved/event logs. | **Reducer mechanics may match; lifecycle and policy will not.** | Office implements only the human decision needed by the chosen workflow, using office actors and policy. Missing: whether its crash states match ConvMem's approval states. | `[adapted]`; preserve office policy outside any future core. Compare only the durable transition mechanics. |
| Verification record and chain | `verify_unit` mutates target Chroma metadata before optionally creating a verification child at [`verify.py:11-74`](../../verify.py#L11-L74); defaults include `web_stack.security`. | Index-first mutation, verifier models, pass/fail vocabulary, optional ledger record and engineering domain defaults. | **Unknown.** The invariant “verification is durable evidence linked to a result” may match. | Office records verification in its ledger first and defines a real observable for the selected workflow. Missing: common result vocabulary, relationship target and supersession semantics. | `[new-and-maybe-general]`; compare after restart and replay, without copying `verify.py` as-is. |
| Project-owned storage injection | Chroma paths are injectable, and decision/event/lock paths derive from the configured Chroma parent at [`propose_decision.py:25-35`](../../propose_decision.py#L25-L35) and [`conflict_events.py:21-31`](../../conflict_events.py#L21-L31). | One Chroma-centered data-root convention; config is read from a ConvMem-named global default at import at [`config.py:7-9`](../../config.py#L7-L9). Secret lookup ignores that override at [`config.py:43-54`](../../config.py#L43-L54). | **The explicit-path invariant should match; the current config mechanism should not.** | Office owns config/data/secrets/CLI names and passes resolved paths into local mechanisms. Missing: evidence of the smallest common runtime input object, if any. | `[adapted]`; no universal Project Profile schema. A tiny explicit path seam may qualify after comparison. |

## Needs a second workflow for confirmation

| Candidate | Current source and evidence | Present assumptions | Why one office workflow is insufficient | Recommended disposition |
|---|---|---|---|---|
| Action proposal and completion primitives | ConvMem has a decision proposal lifecycle but no canonical completion kind; `LEDGER_KINDS` contains only three records at [`ledger.py:18`](../../ledger.py#L18). | “Proposal” means a governed engineering decision; completion is implicit in other operational state. | One office workflow can reveal what *that* workflow calls completion, but cannot prove a cross-domain completion responsibility or payload. | Keep both office records `[office-specific]` through v0. Reassess after another real workflow or an engineering implementation supplies a genuine counterpart. |
| Evidence ranking | Fixed boosts and penalties are encoded at [`evidence.py:17-27`](../../evidence.py#L17-L27); source trust explicitly prefers Kiro steering and `docs/inter-model` at [`evidence.py:116-134`](../../evidence.py#L116-L134). | Engineering unresolved/resolved semantics, agent sources, hand-tuned weights and decision preference. | A single small office fixture cannot validate ranking quality, source trust or useful ordering across different office questions. | Keep ranking application-owned. After a second office workflow, compare evaluation cases—not constants—for a possible minimal Neutral retrieval contract. |
| Minimal semantic retrieval | Current retrieval is entangled with query orchestration, models, reranking and engineering fallbacks; the reranker also caches one process-global model regardless of requested name at [`rerank.py:14-26`](../../rerank.py#L14-L26). | ConvMem corpus shape, Ollama/CrossEncoder choices, current ranking fusion and process lifetime. | The first workflow proves records are retrievable, not that a shared retrieval API or relevance policy is stable. | For the probe, implement only lookup by stable ID, relationship traversal and one minimal semantic query if business value requires it. Reassess after workflow two. |
| General update, supersession and conflict semantics | Current Chroma store and approval flow special-case `dec_` records at [`chroma_store.py:169-182`](../../chroma_store.py#L169-L182), while export upsert rewrites a matching JSONL line at [`observe.py:20-58`](../../observe.py#L20-L58). | Governed engineering decisions, last-write metadata caches and mutable derived export. | One happy-path office cycle does not expose concurrent edits, revisions, cancellation or competing human decisions. | Keep office update policy local; Neutral v0 may initially support append-only records plus replay only. |

## Must remain project-owned

| Candidate | Current source and evidence | Why it remains owned | Disposition |
|---|---|---|---|
| Signers, approval policy and governance | `VALID_SIGNERS = {"ryan", "kiro-review"}` at [`propose_decision.py:12-14`](../../propose_decision.py#L12-L14); approval and conflict lifecycle span the rest of that module. | Actors, authority and allowed transitions are domain policy, even if durable event mechanics later become shared. | ConvMem retains its policy; Office Team defines its own. `[office-specific]` adapters may call future neutral append/hash seams. |
| Application configuration, identity, secrets and write guard | [`config.py`](../../config.py), [`runtime_guard.py:8-84`](../../runtime_guard.py#L8-L84) and application defaults encode ConvMem prod/lab and ConvMem environment names. | Each app must own config/data/secrets/CLI identity. The binary prod/lab guard is evidence of a pattern, not a multi-project product. | Hand-write Office Team's local profile/config and isolation checks. Do not generalize an N-project registry now. |
| CLI, ask/query orchestration, MCP, watch, brief, doctor and inventory | Checkout/resource discovery appears in [`mcp_server.py:17-84`](../../mcp_server.py#L17-L84); watch invokes the checkout CLI at [`watch.py:151`](../../watch.py#L151); user-agent paths and ConvMem defaults are spread across these application modules. | These surfaces coordinate the engineering application and this user's installed tools; they are not memory-core mechanisms. | Leave in ConvMem Engineering. Write only the bounded Office Team surface its workflow needs. |
| Models, prompts, ranking/source-trust policy | Model calls occur inside ingestion at [`observe.py:112-129`](../../observe.py#L112-L129); engineering source trust is in [`evidence.py:116-134`](../../evidence.py#L116-L134). | Model/provider choice and relevance policy are operational/domain choices with separate costs and evaluations. | Applications own adapters and evaluation. Neutral may later accept caller-supplied embedding/search ports. |
| Roles, workflows, deployment, backup and initialization | Current scripts and protocol files resolve ConvMem checkout/config/data identities; there is no `pyproject.toml`, wheel or console-script artifact in the current tree. | These determine how an application is operated and who may act. Sharing them would turn Neutral or ConvMem into an upstream runtime. | Keep entirely application-owned. Do not create a Neutral initializer, role DSL, workflow framework or backup convention. |

## Hidden dependencies that affect the path

- The independence audit's static scan found 56 explicit ConvMem/user-home path
  references across 17 non-test Python files and another 20 matches across 15
  shell scripts. These are reference counts, not unique path values, but they
  show that the application shell is not a near-ready product extract.
- `CONVMEM_CONFIG` is captured in `CONFIG_PATH` during import, so changing the
  environment after import does not change the default config
  ([`config.py:7-9`](../../config.py#L7-L9), [`config.py:57`](../../config.py#L57)).
- Secret resolution still reads `~/.config/convmem` after a config override
  ([`config.py:43-54`](../../config.py#L43-L54)); doctor also hard-codes the
  ConvMem Restic env path.
- The prod/lab write guard classifies only ConvMem and ConvMem Lab and permits an
  `other` path without a project identity check
  ([`runtime_guard.py:18-32`](../../runtime_guard.py#L18-L32)).
- Chroma and ledger caches are keyed by the configured path, so distinct project
  paths do not collide; this does not make unkeyed process globals safe. The
  reranker is one unkeyed model singleton
  ([`rerank.py:14-26`](../../rerank.py#L14-L26)).
- No package artifact exists today. Any current “install ConvMem” story is a
  checkout invocation, so packaging is future work rather than `[reused-as-is]`.

## Smallest response rule

Route a discovered blocker by evidence, not by its apparent architectural
importance:

1. **Small ConvMem decoupling (`[shared-change]`):** propose it in ConvMem only if
   the current engineering application has the same concrete defect without
   Office Team—for example, a hard-coded failure-log path bypassing its own
   configured data root. The change must be narrow and independently useful to
   ConvMem; this planning pass does not make it.
2. **Office-local wrapper or rewrite:** use this when ConvMem behavior carries
   engineering policy or Office Team needs a different responsibility. This is
   the default for the first workflow.
3. **Speculative abstraction:** defer it when the shared shape is only inferred,
   when it needs domain switches, or when only one workflow demonstrates it.

The threshold question for a proposed ConvMem change is: **would ConvMem
Engineering accept this exact change if Office Team did not exist?** A yes makes
the proposal eligible for its own review; it does not make the result Neutral.

## Assumptions not yet verifiable

- The real first office workflow, business owner, approval actor and verification
  observable have not been selected.
- No Office Team repository or independent runtime was present during this audit.
- It is unknown whether Office Team needs Chroma, the same embedding model or
  semantic retrieval in its first valuable workflow.
- Chroma's internal SQLite schema is not a stable application-neutral contract.
- The common record envelope, ID grammar, completion meaning and migration policy
  cannot be known until Office Team produces durable records.

**TL;DR:** Only the narrow hash and durable-append mechanics are safe to copy now;
all load-bearing record, identity, ledger/replay, projection, provenance and
verification seams require the office comparison, while ranking, completion and
general conflict behavior need more than one workflow and all app operations and
policy remain project-owned.
