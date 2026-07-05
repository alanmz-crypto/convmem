# Ford/Richards et al. — builder digest (convmem)

**Source:** *Software Architecture: The Hard Parts* · Part I (trade-offs, coupling, data)
pp. 20–95; Chapters 9, 11, 12 (data ownership, distributed workflows, transactional
sagas) pp. 249–364

**Read when:** considering service splits, data ownership between ledger and
Chroma, ingest/watch boundaries, MCP vs CLI surfaces, the propose_decision →
Kiro sign-off → record --approve-last flow, or any "should we microservice this?"
question for convmem.

## Principles

- There is no "best" architecture — only **least-worst trade-offs** among
  competing characteristics (simplicity, reliability, operability, evolvability).
- **Architecture is the hard-to-change stuff** — structure, data ownership,
  integration patterns. Design and implementation details should move faster.
- **Trade-off analysis beats silver bullets** — novel problems need explicit
  pros/cons, not pattern names copied from blog posts.
- **Data outlives services** — who owns the truth, who holds derivatives, and
  how rebuild works matter more than which container runs the embedder.
- **Coupling is a spectrum** — integration style (sync API vs event log vs shared
  DB) determines how painful change becomes.
- **Granularity decisions are reversible only at cost** — splitting too early
  creates distributed ops tax; merging later is also expensive.
- **Fitness functions** — encode architectural constraints as automated checks
  (doctor, verify scripts, golden queries) so drift is visible early.
- **Sagas are the pattern for multi-step, multi-service workflows with approval
  gates.** A saga spans multiple services, each with its own transaction boundary,
  linked by orchestration or choreography. Compensating actions unwind partial
  progress when a step fails.
- **Three coupling forces define every saga:** communication (sync/async),
  consistency (atomic/eventual), coordination (orchestrated/choreographed). The
  combination determines the pattern's complexity, scalability, and error-handling
  profile.
- **Orchestration centralizes workflow state** in a mediator that manages
  branching, error handling, and compensating actions. **Choreography distributes
  workflow state** across participants — more scalable but harder to reason about
  when errors cross service boundaries.
- **Compensating transactions are not free.** They can fail, leave data
  inconsistent, and create side effects when other services have already acted on
  the now-reversed data. Saga state machines (tracking explicit states like START
  → NO_SURVEY → CLOSED) are often a better alternative than attempting atomic
  rollback.
- **The best saga is the weakest one that still meets requirements.** Favor
  eventual consistency over atomic when possible; favor orchestration when error
  handling complexity is high. The Anthology Saga(aec) pattern (async, eventual,
  choreographed) is the least coupled; the Epic Saga(sao) (sync, atomic,
  orchestrated) is the most traditional but hardest to operate.

## What this means for convmem (local monolith)

convmem is intentionally a **single-machine system**: CLI, MCP, watch daemon,
Chroma, JSONL ledger. The Hard Parts book targets distributed systems — apply
it as **trade-off discipline**, not as a mandate to split services.

| Question | convmem answer today | Revisit trigger |
|----------|---------------------|-----------------|
| Source of truth | JSONL ledger + approved decisions | Never Chroma alone |
| Derived index | Chroma embeddings | Rebuild via `convmem index` |
| Surfaces | CLI + MCP adapters | New surface = adapter, not service |
| Background work | watch + refine daemons | Split only if RSS/lock pain chronic |
| Cross-project view | digest script, brief | Not a separate query service |
| Decision pipeline | propose_decision → Kiro sign-off → record --approve-last | Saga isolation, compensating action gaps |

**Do not** propose microservices for convmem without a written trade-off table
and a failing fitness function the monolith cannot meet.

## Data ownership pattern

**Ledger owns facts.** Decisions, observations, verifications live in append-only
JSONL under `~/.local/share/convmem/`. **Chroma owns search geometry** — units
and chunks are derived and rebuildable.

Trade-offs:

- **Pros of derived Chroma:** fast semantic search; safe to re-embed after model
  change; `rm processed.json && convmem index` is a known rebuild path.
- **Cons:** drift if index lags ledger; agents must not treat vector hits as
  authoritative over recent approved decisions (see Manning digest recency gap).
- **Coupling point:** ingest adapters write both ledger export and Chroma —
  keep ingest→ledger→Chroma one-directional.

If you add a feature that writes only to Chroma, you have violated data
ownership — fix before merge.

## Coupling between subsystems

| Edge | Coupling type | Keep loose how |
|------|---------------|----------------|
| ingest → Chroma | Batch/event-ish | Adapters don't import `ask` |
| query → Chroma | Sync read | Via `ChromaStore` only |
| MCP → core | RPC-style calls | Thin handlers in `mcp_server.py` |
| brief → inbox markdown | File mtime | Staleness alarm, not hard dependency |
| agent protocol → surfaces | Generated copies | SSoT in `agent-protocol.md` |

**Integrator vs disintegrator test** (book framing): forces that pull toward
monolith — shared ledger, single operator, local Ollama, one corpus. Forces
that pull toward split — none required yet at Ryan's machine scale.

## Surface architecture (not service architecture)

Cursor, Kiro, Codex, Crush are **delivery adapters** for the same protocol and
builder digests — analogous to multiple API gateways on one backend.

Trade-off: Crush `global_context_paths` loads full digests (context cost) vs
Cursor `globs` scoping (may miss if cwd wrong). Least-worst: both — Crush needs
global load for DeepSeek ritual skips; Cursor scopes to repo.

Do not create per-surface business logic forks. If Crush needs different text,
fix deploy script output, not `ask.py`.

## When splitting would be on the table

Read this section before proposing process boundaries.

**Candidate splits (future only):**

1. **Ingest worker** — if watch + index blocks interactive CLI routinely.
2. **Embed/rerank sidecar** — if GPU rerank isolation needed for latency SLOs.
3. **Remote MCP** — if corpus moves off laptop (unlikely for convmem mission).

Each split needs:

- Independent deploy cycle justification
- Network failure mode analysis
- Data ownership diagram (who writes ledger)
- Fitness function the monolith failed

Until then, use **module boundaries** (Ousterhout) inside one repo.

## Trade-off worksheet (use in PRs)

```text
Decision:
Options considered (≥2):
Characteristics compared (simplicity, reliability, operability, evolvability):
Chosen least-worst:
Accepted downsides:
Fitness check added or updated:
```

Example — "Should `ask` always inject recent decisions?"

- **Option A:** Prompt-only recency instructions — simple, unreliable.
- **Option B:** Forced context blocks from JSONL — more code, reliable for
  coordination questions.
- **Option C:** Separate "state" MCP tool — new surface area, clearer contract.
- Least-worst for convmem today: **B** inside `ask.py` (see Manning digest).

## Choreography vs orchestration (local scale)

Distributed orchestration (central controller) vs choreography (peers react) maps
loosely to:

- **Orchestrated:** `convmem.py` Typer dispatches commands sequentially.
- **Choreographed:** watch daemon debounces file changes and indexes without CLI.

Do not add a central "orchestrator service" for ingest — the watch script plus
ledger log is sufficient choreography at current scale.

## Saga patterns reference

The book defines eight saga patterns based on three coupling forces
(communication × consistency × coordination). Letters in parentheses denote the
combination: (s|a)ync, (a|e)ventual, (o|c)hestrated.

| Pattern | Comms | Consistency | Coordination | Best for |
|---------|-------|-------------|--------------|---------|
| Epic(sao) | sync | atomic | orchestrated | Traditional distributed tx; compensating updates |
| Phone Tag(sac) | sync | atomic | choreographed | When orchestrator would be bottleneck |
| Fairy Tale(seo) | sync | eventual | orchestrated | Most practical — mediator + loose consistency |
| Time Travel(sec) | sync | eventual | choreographed | High throughput, simple error paths |
| Fantasy Fiction(aao) | async | atomic | orchestrated | Avoid — async + atomic is very difficult |
| Horror Story(aac) | async | atomic | choreographed | **Avoid at all costs** |
| Parallel(aeo) | async | eventual | orchestrated | Good perf with mediator + loose coupling |
| Anthology(aec) | async | eventual | choreographed | Least coupled; max scale, hardest to coordinate |

**convmem default mode:** Fairy Tale(seo) — sync communication (CLI/MCP calls),
eventual consistency (index lags ledger), orchestrated by convmem.py Typer or
MCP handler. The decision pipeline is closer to Epic(sao) because the approval
gate demands stronger consistency.

## Saga state machines vs compensating transactions

Rather than rolling back a distributed transaction with compensating updates
(which can fail and leave side effects), the book recommends **saga state
machines** — explicit state models with named transitions (START → TICKET_ASSIGNED
→ EXPERT_DISPATCHED → NO_SURVEY → CLOSED).

convmem's ledger already models this: obs_* and dec_prop_* have status fields,
relates_to edges form a DAG, and `--approve-last` moves a decision from proposed
to approved. The ledger is already a saga state machine — the missing part is
formalizing the transition model and adding compensating actions for failed
steps.

Example from Ch12 — Sysops Squad ticket workflow states: START → TICKET_ASSIGNED
→ ROUTED → IN_PROGRESS → COMPLETED → CLOSED (or NO_SURVEY). Each state has
associated transition logic and error handlers. The same pattern applies to a
decision's lifecycle: PROPOSED → KIRO_REVIEW → APPROVED (or REJECTED).

## Convmem decision pipeline as a saga

The propose_decision → Kiro sign-off → convmem record --approve-last flow is a
**distributed saga** spanning multiple agent surfaces (Crush proposes, Kiro
reviews, CLI approves). No single service holds a transaction boundary across
all three steps.

**Current pattern:** Epic Saga(sao) — the decision must be proposed, reviewed,
and approved as an atomic unit before it enters the searchable ledger. If any
step fails (review rejects, CLI never approves), the pipeline must compensate:

1. **Propose** — Crush (or any agent) writes a JSONL entry with `dec_prop_*` id
2. **Review** — Kiro signs off (or rejects) via `--signer kiro-review`
3. **Approve** — `convmem record --approve-last` moves the decision from pending
   to indexed

**Failure modes the book helps analyze:**

| Step fails | Current behavior | Saga gap |
|------------|-----------------|----------|
| Propose crashes mid-write | Partial JSONL line | No compensating action to clean partial writes |
| Kiro rejects | Decision stays unapproved | No automated notification back to proposer |
| Approve never runs | Decision stays in pending queue, not searchable | Timeout/nag mechanism absent |
| Approve succeeds but index fails | Decision in ledger but not searchable | No retry or reconciliation |
| Compensating update fails (e.g., removing approved decision) | Side effects: agents may cite an approved decision that the compensator is trying to unwind | No isolation context — side effect hazard described on pp. 378-380 |

**Least-worst today:** Accept the gaps — the pipeline is human-mediated at each
gate, so failure rates are low. When automating (agent-driven approval chain),
add:
- A saga state machine for decision lifecycle (PROPOSED → APPROVED → INDEXED)
- Compensating actions: `record --reject-last` to undo a proposed-but-unapproved
  decision (analogous to the book's compensating transaction)
- A timeout/nag fitness function (`doctor`) that flags decisions stuck in
  PROPOSED beyond a threshold

**Which pattern to target:** Fairy Tale(seo) — orchestrated (convmem.py controls
the flow), eventual consistency (short window between approve and index is
acceptable), sync communication (CLI calls are synchronous). Not Epic(sao)
because full atomicity across surfaces is not required — a short lag between
approve and index does not break the user contract.

## Modularity and transactional boundaries

Book emphasis: **transactional boundaries** align with business capabilities.
convmem capabilities:

- **Capture** — adapters, ingest
- **Record** — ledger writes, `convmem record`
- **Retrieve** — query, ask, search
- **Orient** — brief, doctor, unresolved
- **Coordinate** — digest, inter-model handoff (markdown, not runtime)

Avoid transactions that span capture+retrieve in one user command unless the
user contract requires it (`record --approve-last` indexing is the exception —
documented pipeline).

## convmem Hooks

- [`config.example.toml`](../../config.example.toml) — each section is a
  trade-off surface (query vs index vs watch vs refine).
- [`doctor.py`](../../doctor.py) — fitness function for infra; extend for
  ledger/Chroma count drift (future).
- [`scripts/verify-builder-reference.sh`](../../scripts/verify-builder-reference.sh)
  — fitness for agent wiring deploy.
- [`cross_project_digest.py`](../../cross_project_digest.py) — read-only
  synthesis; never auto-indexed (explicit trade-off: human review before corpus).
- **P2 held items** (MCP `unresolved` tool) — weigh thin MCP tool vs shell-only;
  least-worst: ship read-only JSON payload shared with CLI.
- **Decision pipeline saga** — the propose_decision → Kiro → record
  --approve-last flow is a saga. Use the book's vocabulary (orchestration vs
  choreography, compensating actions, saga state machines) when designing
  automated approval gates or cross-surface workflows.

## Distributed myths to reject for this repo

- "Microservices will simplify convmem" — false at current scale; ops cost dominates.
- "Chroma is the database of record" — false; rebuild path assumes otherwise.
- "Each agent surface needs its own retrieval logic" — false; shared `query.py`.
- "Split MCP server for isolation" — premature; fix timeouts and synthesis bounds first.

## Scenario: ingest daemon split proposal

**Trigger:** watch RSS > doctor threshold consistently.

**Analysis:**

| Factor | Monolith + daemon | Separate ingest service |
|--------|-------------------|-------------------------|
| Simplicity | One config, one doctor | Two deploys, two failure modes |
| Reliability | Shared locks in one codebase | Distributed lock needed |
| Operability | Ryan one-machine | systemd + network health |
| Evolvability | Module extract first | Service contract freeze |

**Least-worst now:** extract ingest modules inside repo; keep one process until
doctor proves chronic failure.

## Scenario: multi-machine corpus

If corpus must follow laptop → desktop:

- **Data moves:** ledger JSONL + chroma dir (Tier 1 backup per RECOVER.md).
- **Do not** split by "search on cloud, write on laptop" without sync protocol.
- Trade-off: git for source, rsync for corpus, or single canonical machine.

Book's data-over-services principle: define sync and ownership before any remote
MCP host.

## Anti-patterns for Agents

- Do not recommend microservices to sound architectural.
- Do not treat pattern names (CQRS, event sourcing) as requirements without a
  failing local constraint.
- Do not split ingest/query because files are large — split by **change rate and
  failure isolation**, not line count.
- Do not create duplicate sources of truth for decisions (markdown handoff vs
  ledger — handoff is pointer, ledger is truth).
- Do not skip documenting accepted downsides in PR or `convmem record` rationale.
- Do not conflate **surface adapters** (Cursor/Crush rules) with **runtime
  services** — deploy scripts are not microservices.
- Do not implement an Epic Saga(sao) (sync + atomic + orchestrated) for the
  decision pipeline unless you need instant consistency between proposal and
  searchability — Fairy Tale(seo) is almost always sufficient.
- Do not add compensating actions without modeling their own failure modes —
  a compensating update that fails is a new bug, not a rollback (Ch12, pp. 378-380).
- Do not treat propose_decision as a fire-and-forget event. It is a saga step
  with an expected subsequent action (approve or reject). Without tracking the
  saga state, decisions orphaned in PROPOSED become ledger debt.

## How agents should use this digest

- Before "split X into a service," fill the trade-off worksheet.
- Before changing data flow between ledger and Chroma, state ownership explicitly.
- Pair with **Ousterhout** for module depth inside the monolith.
- Pair with **Manning** when split motivation is "search is slow" — tuning may
  beat distribution.
- Pair with **Zeller** when trade-off experiment fails — reproduce before next
  architectural pivot.
- When designing cross-surface workflows (propose → review → approve), reach
  for this digest's saga patterns before inventing a new coordination mechanism.

## Fitness functions already in the repo

The book recommends encoding constraints as checks convmem already has or is
building:

| Fitness function | What it guards |
|------------------|----------------|
| `convmem doctor` | Ollama, Chroma, config, watch RSS |
| `verify-builder-reference.sh` | Agent digest deploy integrity |
| `validate-builder-reference-surfaces.sh` | Per-surface config depth |
| `pytest` / `test_evidence_rerank.py` | Ranking policy regressions |
| Golden-query set (Manning digest) | Retrieval quality |
| Digest pilot false-link count | Synthesis must cite fresh ledger ids |

When proposing architecture change, name which fitness function will detect a
regression — or add one before merging.
