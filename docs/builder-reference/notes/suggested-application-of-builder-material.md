# Suggested Application of Builder Material

This is a practical note, not part of the canon itself. The point is to turn
the builder-reference digests into a repeatable way of working on `convmem`.

## Use the canon as a pre-edit filter

Before changing code, pick the digest that matches the shape of the work:

- [Ousterhout](../ousterhout-builder-digest.md) for CLI surfaces, `brief`,
  `mcp_server.py`, protocol generation, and any helper that risks becoming a
  shallow wrapper.
- [Manning](../manning-builder-digest.md) for retrieval ranking, recency,
  reranking, chunking, and evaluation.
- [Zeller](../zeller-builder-digest.md) for failures, reproduction, triage, and
  verification.
- [Hard Parts](../hard-parts-builder-digest.md) for ownership, coupling, and
  split-vs-merge trade-offs.
- [DDIA](../ddia-builder-digest.md) for ledger truth, derived index state,
  stream processing, and single-writer reasoning.
- [Architecture Patterns with Python](../arch-patterns-python-builder-digest.md)
  for ingest adapters, repositories, Unit of Work, and aggregate boundaries.
- [Building Evolutionary Architectures](../evolutionary-architectures-builder-digest.md)
  for fitness-function design, threshold reconciliation, adding or modifying
  automated checks (`verify-builder-reference.sh`, `validate-builder-reference-surfaces.sh`,
  `convmem doctor`).

Archived digests in `../archive/` are useful background, but they should not
drive first-pass decisions unless the current change is specifically about
knowledge-capture workflow or craftsmanship notes.

## Suggested application pattern

1. Read the matching digest first.
2. State the change in one sentence without naming implementation details.
3. Ask whether the change deepens a module, improves retrieval quality,
   reduces coupling, or makes a failure easier to reproduce.
4. Make the smallest change that satisfies that goal.
5. Verify with the repo's existing fitness checks.
6. Record the decision so the next session does not rediscover it.

## Common change classes

| Change shape | Primary digest | Verify with |
| --- | --- | --- |
| CLI, protocol, or surface cleanup | Ousterhout | `scripts/verify-builder-reference.sh`, `scripts/validate-builder-reference-surfaces.sh` |
| Retrieval, ranking, or recency tuning | Manning | fixed golden queries, `convmem search`, `convmem ask` |
| Failure triage or behavior drift | Zeller | `convmem doctor`, smallest repro, replay the failure |
| Ledger vs Chroma ownership | DDIA | ingest/rebuild path, review single-writer assumptions |
| Split-vs-merge or coupling questions | Hard Parts | trade-off table, data-ownership statement |
| Ingest adapter or aggregate design | Architecture Patterns with Python | module boundary review, ledger write path, Unit of Work shape |
| Adding or modifying automated checks / thresholds | Building Evolutionary Architectures | state what the check protects, confirm single ownership, verify no threshold drift |

## What this should prevent

- Adding a new surface when a deeper module would do.
- Fixing retrieval problems by expanding prompts instead of ranking.
- Declaring a bug fixed without replaying the original failure.
- Blurring ledger truth with derived search state.
- Proposing architectural splits without an explicit trade-off table.

## My bias for this repo

If a change touches more than one builder digest, prefer the one that removes
the most user-visible complexity:

- Choose Ousterhout when the problem is surface depth.
- Choose Manning when the problem is evidence selection.
- Choose Zeller when the problem is uncertainty.
- Choose DDIA when the problem is data ownership or replay.
- Choose Hard Parts when the problem is whether the system should split at all.
- Choose Building Evolutionary Architectures when the problem is two checks
  disagreeing, a threshold with no stated rationale, or a new gate that needs
  a clear owner.

When in doubt, keep the change closest to the layer that can remove the
complexity instead of documenting it in a higher layer.

## Good defaults

- Keep `convmem.py` thin.
- Keep retrieval and generation separate.
- Keep the ledger authoritative.
- Keep derived indexes rebuildable.
- Prefer one verified path over multiple almost-equivalent ones.

## Editing past work

When revisiting earlier docs or notes:

- Update the canonical index if the new material changes how people should
  navigate the canon.
- Keep archive material archived unless it is now a daily-use digest.
- Do not copy digest content into notes; point at the digest instead.
- Add verification hooks where the note recommends action, not just advice.
- Prefer a narrow note that helps action over a broad note that restates the
  books.

## Applied decisions (ADR record)

These are decisions derived from the digests and applied to the codebase.
They serve as the explicit architecture decision record (ADR) that each
digest recommends.

### Single-writer consensus avoidance (DDIA § Ch.9)
**Applied 2026-07-01.** Convmem avoids distributed consensus by design, not
by algorithm: a single machine, single process, single JSONL file. There is
no leader election, no split-brain risk, no clock skew between writers. The
cross-surface workflow (propose → review → approve) involves multiple agents
but only one ledger writer (Ryan's CLI). This eliminates the entire class of
failure modes that Raft/Paxos/Zab exist to solve. The decision pipeline
(propose_decision → Kiro sign-off → record --approve-last) is an Epic
Saga(sao) mediated by human gates — not a distributed consensus protocol.

**When to revisit:** if convmem ever supports multi-machine ledger writes.
Until then, single-writer is correct and sufficient.

### Unit of Work compensating action (Architecture Patterns with Python § UoW)
**Applied 2026-07-01.** The `record --approve-last` flow is not fully atomic:
the ledger write (step 3) and Chroma index (step 4) are separate operations.
If Chroma indexing fails, the approval already succeeded in the durable
ledger (DDIA: ledger is authoritative). Per Arch Patterns Python, the
compensating action is:

1. Log the failure to `index_failures.jsonl` telemetry
2. Show a warning (not error exit — the durable write succeeded)
3. Provide explicit recovery: `convmem add --file <approved.jsonl> --upsert`
4. Doctor gate at >=3 failures/week triggers investigation

This is not a full Unit of Work transaction boundary; it's a documented
compensating action with observable telemetry. Full UoW (atomic ledger +
Chroma commit) would require a write-ahead log or two-phase commit — not
warranted at current scale.

### Recency on plain search (Manning IR — P1a)
**Applied 2026-07-05.** `query_units()` applies `apply_recency_rerank()` when
`query.recency_weight` > 0 — same decay formula as `ask --evidence`, without
ledger graph walk (keeps `search_fast` fast).

| Path | Recency | Evidence graph |
|------|---------|----------------|
| `convmem search` / MCP `search_fast` | `recency_boost` | No |
| `convmem ask --evidence` / MCP `ask` | `recency_boost` | Yes |
| `convmem ask` (default CLI) | No | No |

**Verify:** `python scripts/eval-retrieval.py` (golden queries); inspect
`rank_score` / `recency_boost` in MCP `search_fast` JSON.

**When to revisit:** forced recent-decision injection for state questions (see
Manning digest § Proposed fix pattern) if mild decay alone misses coordination
queries.

### Protocol fallback anchor lookup (Manning IR — stable ledger id)
**Applied 2026-07-05.** Golden anchor query failed because `dec_prop_20260623_161428_c311`
was indexed with an empty Chroma `document` field. `query_units()` now:

1. Detects **explicit ledger ids** in the query → `find_unit_by_ledger_id` (JSONL
   enrichment when document empty).
2. Detects **protocol anchor queries** (`fallback`+`root`, or `protocol`+`root`+`relat*`)
   → injects `PROTOCOL_FALLBACK_LEDGER_ID` from `decisions-approved.jsonl`.

Hits prepend semantic results (`ledger_lookup: true`). Golden eval anchor row **PASS**.

**When to revisit:** backfill empty decision documents at ingest so lookup injection
is rare.

### Decision document at ingest (DDIA derived index)
**Applied 2026-07-05.** `ledger_unit_document()` is the single source for embed text
(summary + keywords + rationale). `ingest_observation()` uses it; upsert skips only
when the stored document is non-empty **and** matches expected text.

**Repair:** `bash scripts/repair-ledger-documents.sh` re-embeds decision/verification
units with empty Chroma documents from `decisions-approved.jsonl` (dry-run supported).

**When to revisit:** index `summary` into metadata field for keyword fallback without
JSONL round-trip.

### Partial synthesis on timeout (Ousterhout Ch.10 + Zeller observability)
**Applied 2026-07-05 (P1c Phase 1).** `ask()` uses `generate_stream()` with a
45s wall-clock timer. Three degraded states are now explicit to callers:

| State | Field | Telemetry | Caller action |
|-------|-------|-----------|---------------|
| Full synthesis | *(none)* | — | Trust answer |
| Partial (timeout mid-stream) | `synthesis_interrupted: true` | not logged as failure | Use partial answer; note `[Synthesis interrupted]` trailer |
| Total failure (empty buffer) | `synthesis_failed: true` | `synthesis_failures.jsonl` | Use citations only; doctor gate counts these |

This is Ousterhout **promote-and-reuse**: streaming + partial fallback is the
standard path, not a one-off mask. Manning separation holds — retrieval runs
before synthesis; partial text does not fix bad ranking.

**Fitness function:** `convmem doctor` `_check_synthesis_gate` counts only
empty-buffer failures (>=3/week → investigate). Partial interrupts are visible
via `synthesis_interrupted` but do not trigger the gate.

**When to revisit:** Phase 2 `ask_stream` after Cursor/Crush pre-flight confirms
progressive MCP rendering.

### Fitness-function ownership (Building Evolutionary Architectures)
**Applied 2026-07-01.** Each measurable property has exactly one
authoritative fitness function:

| Property | Owner | File |
|----------|-------|------|
| Digest completeness (ship gate) | `verify-builder-reference.sh` | word count >= 1500 |
| Digest depth (aspirational) | `validate-builder-reference-surfaces.sh` | word count >= 2500 |
| Surface wiring (deploy integrity) | `verify-builder-reference.sh` | sha256 + file presence |
| Per-surface config depth | `validate-builder-reference-surfaces.sh` | globs, alwaysApply, timeout |
| Infra health | `convmem doctor` | Ollama, Chroma, config, watch RSS |
| Index drift | `convmem doctor` _check_index_drift | Chroma vs JSONL count |
| Synthesis failures (empty buffer) | `convmem doctor` _check_synthesis_gate | >=3/week → investigate ask pipeline |
| Partial synthesis (timeout mid-stream) | `ask()` / MCP `ask` | `synthesis_interrupted: true`; not gate-counted |
| Index failures (delayed-index) | `convmem doctor` _check_index_gate | >=3/week triggers investigation |
| Cross-project digest (deterministic) | `scripts/smoke-cross-project-digest.sh` | headings + pytest; optional Do not retry when attempts.jsonl present |
| Path precheck (advisory) | `scripts/precheck-path.sh` | fail-open WARN; reads attempts.jsonl |
| Empty ledger document repair | `scripts/repair-ledger-documents.sh` | decision/verification units with empty Chroma document |
| Retrieval quality | golden queries (manual) | P@k on fixed query set; `scripts/eval-retrieval.py` |
| Search recency | `query.recency_weight` + `apply_recency_rerank` | MCP `search_fast` exposes `rank_score`, `recency_boost` |
| Protocol anchor lookup | `query_units` + `ledger_recent.approved_decision_hit` | `fallback`+`root` or explicit ledger id in query |

No two fitness functions measure the same property without a declared
relationship. The previous threshold mismatch (two scripts disagreeing on
word-count gates) is resolved: `verify-builder-reference.sh` owns the ship
gate (>= 1500); `validate-builder-reference-surfaces.sh` owns the
aspirational depth band (>= 2500).
