# Transition Options

> **Salvage note (2026-07-24):** Landed from a previously untracked working tree for
> workspace takeover. Draft Architecture [#115](https://github.com/alanmz-crypto/convmem/pull/115)
> (`ARCHITECTURE-shadow-ledger-phase0.md`) requires the corrections below before these
> files are treated as an approved baseline. **Does not authorize** shadow hooks,
> cutover, restore-order flip, or Neutral.

## Architecture #115 corrections (applied 2026-07-24)

- Replace any claim of **“zero production behavior change.”** Shadow Phase 0 is
  additive and Chroma remains authoritative, but instrumentation at mutation sinks
  is still a behavior change under an activation flag.
- **Coverage scope:** Shadow capture must cover **unit-mutating** `ChromaStore`
  paths enumerated by Architecture — not “every file touch in the repo.”
- **Delta vs historic rebuild:** Passing delta shadow↔Chroma compare does **not**
  prove historic corpus rebuild. Historic rebuild / migration remain later gates.

## Option A — Immediate cutover

All new observations use ledger-first after one release. Legacy data migrated in a single batch.

| Dimension | Assessment |
|-----------|------------|
| Implementation complexity | Medium — one code path to maintain |
| Rollback | Hard — requires restoring backup and reverting code |
| Risk of split authority | High during migration window |
| Duration | Single release cycle + migration batch |
| Data reconciliation | One-time bulk reconciliation |
| Reader changes | All readers must support canonical schema immediately |
| Test burden | Full test suite against new path |
| Operational observability | Binary: old or new |

**Verdict: Not recommended.** The 21,420 legacy records and 192 Chroma-only records make a clean cutover risky. Any migration bug means data loss.

## Option B — Parallel compatibility period

New observations use ledger-first. Readers support both legacy (Chroma-direct) and canonical (ledger-projected) records. Migration happens incrementally.

| Dimension | Assessment |
|-----------|------------|
| Implementation complexity | High — two read paths, dual-format support |
| Rollback | Easy — stop writing to ledger; readers still work |
| Risk of split authority | Medium — clear boundary between old and new |
| Duration | Weeks to months |
| Data reconciliation | Incremental; can pause and resume |
| Reader changes | Gradual; legacy path remains functional |
| Test burden | Both paths tested independently |
| Operational observability | Must track dual-state metrics |

**Verdict: Viable but expensive.** The dual-read path adds sustained complexity. Given that convmem is a single-developer project, maintaining two parallel systems is a significant ongoing cost.

## Option C — Shadow ledger (recommended)

Current Chroma-first behavior remains authoritative. A shadow ledger is written alongside every observation write. The shadow is compared against Chroma to validate reconstructability. Once the shadow has proven it can rebuild Chroma faithfully, cutover happens.

| Dimension | Assessment |
|-----------|------------|
| Implementation complexity | Low–medium — additive shadow path, but mutation-sink instrumentation is a real behavior change under an activation flag |
| Rollback | Easy — disable flag / stop shadow writes; Chroma path unchanged |
| Risk of split authority | None for authority — Chroma remains sole authority during shadow phase (shadow is non-authoritative) |
| Duration | Until shadow validates (days to weeks) |
| Data reconciliation | Continuous comparison during shadow phase |
| Reader changes | None during shadow phase |
| Test burden | Shadow writer + comparison tool |
| Operational observability | Shadow-vs-Chroma drift metric |

### Shadow mode implementation

1. After every successful Chroma write, append the canonical record to `shadow_ledger.jsonl`.
2. Periodically (or on demand), replay `shadow_ledger.jsonl` into a temporary Chroma instance.
3. Compare the temporary Chroma against production Chroma using content-hash equivalence.
4. Report drift: missing records, mismatched content, extra records.
5. Fix drift causes before proceeding.

### Shadow mode caveats

Shadow mode generates **misleading confidence** if:
- The shadow writer doesn't capture all write paths (e.g., repair, manual ingest, verify).
- The shadow uses a different normalization than the eventual canonical schema.
- The comparison ignores fields that matter for retrieval quality.

**Mitigation:** Enumerate ALL Chroma write paths in the codebase and verify each writes to the shadow. The audit identified these write paths:
- `observe.py:ingest_observation()` — primary observation/decision/verification ingest
- `observe.py:repair_empty_ledger_documents()` — decision document repair
- `verify.py:verify_unit()` — inline verification metadata update
- `chroma_store.py:supersede_units_for_source()` — tombstoning
- `chroma_store.py:update_unit_metadata()` — metadata-only updates
- `distill.py` → `ingest.py` — legacy knowledge extraction pipeline

### When to exit shadow mode

Exit when:
1. Shadow ledger captures 100% of new Chroma writes for N consecutive days.
2. Shadow replay produces equivalent Chroma state (content-hash match for all records).
3. All identified gaps (fsync, append-only, tail validation) are fixed.
4. Migration feasibility assessment is complete and approved.

## Recommendation

**Option C (Shadow ledger)**, followed by Option A (immediate cutover) once shadow validates.

Rationale:
- Chroma stays authoritative; shadow fails visible and must not block Chroma.
- Proves **delta** reconstructability before any cutover claim (not historic rebuild).
- Identifies gaps in **unit-mutating** write-path coverage.
- Lower cost than dual-read parallel period, still not “zero behavior change.”
- Natural graduation to a later cutover Architecture once delta gates pass.
