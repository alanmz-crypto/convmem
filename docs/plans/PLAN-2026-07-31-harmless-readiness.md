# Harmless readiness plan: standing checks, C6, and retrieval gaps

**Status:** analysis and planning only. This document authorizes no config
change, census operation, Shadow operation, service control, Chroma mutation,
ledger write, or deployment action.

**Freeze boundary:** the deployed checkout `/home/lauer/Projects/convmem` is
held at `76126e07a97187f68d925dd8b431d2d03967084f` through 2026-08-07
00:00 UTC. This plan is authored in the isolated worktree branch
`docs/2026-07-30-c7-c6-standing-check-readiness`.

**Branch PR title:** `docs: freeze-safe analysis plans for C6 hold, standing
checks, and retrieval gaps`

## Current evidence snapshot

The 2026-07-31 read-only `convmem doctor` run reported:

- 12,427 active `knowledge_units` and 1,774 summaries.
- `recency-boost-retune`: due at `5714 * 2.0 = 11,428` units.
- `escalation-threshold-retune`: due at `5708 * 2.0 = 11,416` units.
- `synthesis_gate`: 2 failures in the last seven days, below its `>=3/week`
  investigation threshold.
- `index_gate`: 0 failures in the last seven days.

### Freshness recheck — 2026-07-31 08:42 UTC

A later read-only doctor run reports 12,452 active knowledge units and 1,779
summaries. Both trigger conditions therefore remain due (`5714 * 2.0 = 11,428`
and `5708 * 2.0 = 11,416`). Targeted corpus search located Ryan's approved
decision `dec_prop_20260705_182232_2d24` in
`/home/lauer/.local/share/convmem/decisions-approved.jsonl` (rechecked
2026-07-31; timestamp `2026-07-05T18:22:32Z`): recency boosting was
evaluated with no retrieval regression. This historical record supports the
plans, while escalation still lacks an attempt denominator; neither result
authorizes resetting a standing-check row.
- The standing-register warning is advisory; doctor remains exit-zero.

The two due rows are intentionally clustered corpus-size proxies. The source
of truth is `docs/standing-checks-register.json`; `doctor.py` evaluates a
corpus-size row as due only when the live count is strictly greater than
`baseline * multiple`. A `last_verified` edit does not reset either row. A
completed review must re-record a new baseline, and only then should a future
implementation change the register.

## Standing check A — recency weight / half-life

**Owner / timeline:** Design and evidence review delegated to Kiro / DeepSeek
assistance. Ryan approval required before any runtime config or register
change. Execution deferred until after the 2026-08-07 freeze.

### Decision question

Does the current `query.recency_weight` and half-life still improve retrieval
for fresh operational evidence without displacing durable architectural
evidence?

### Read-only evaluation design

1. Freeze a small held-out golden set covering architecture, debugging,
   retrieval, and cross-surface navigation. Keep the set separate from any
   queries used to select a candidate.
2. Run the current behavior and at least two candidate pairs of weight and
   half-life against the same corpus snapshot and candidate pool. Preserve
   only query identifiers, returned ledger IDs/source paths, ranks, scores,
   and aggregate metrics; do not alter the live config.
3. Compare P@5 and rank-sensitive NDCG, plus a regression list for queries
   where a durable decision is displaced by a newer but less authoritative
   chat artifact. Inspect `recency_boost` and rank movement rather than
   treating a larger score as correctness.
4. Use the existing retrieval tests as regression guards, especially
   `tests/test_query_recency.py` and `tests/test_evidence_rerank.py`. A
   candidate is not accepted from a single anecdotal query.

### Acceptance and reset rule

Accept a candidate only if it improves the held-out operational queries with
no unacceptable regression in durable-decision queries, and if the chosen
weight/half-life has a written rationale. Then, in a separately authorized
follow-up, change the runtime config, run the fixed evaluation again, and
record a new `collection_count` baseline. Until that happens, leave both the
config and register untouched; this plan does not close the standing check.

The key risk is that recency is a ranking signal, not a truth source. The
Manning builder guidance therefore requires a fixed evaluation set and warns
against tuning recency and chunking together.

## Standing check B — escalation thresholds

**Owner / timeline:** Design and evidence review delegated to Kiro / DeepSeek
assistance. Ryan approval required before any runtime config or register
change. Execution deferred until after the 2026-08-07 freeze.

Protocol draft: [escalation-threshold measurement design](PLAN-2026-07-31-ESCALATION-THRESHOLD-STANDING-CHECK.md).

### Decision question

Are the `>=3/week` synthesis and index failure thresholds still a useful
operational signal at current activity, or is the corpus-size trigger merely
masking a missing volume denominator?

### Read-only evaluation design

1. Re-run the two existing gate readers against their current seven-day
   windows and record counts, timestamps, and refusal/recovery outcomes in a
   private review note. Do not edit either failure log.
2. Compare those counts with corpus growth and with the operator impact of a
   threshold crossing: false-positive investigation cost, missed degradation,
   and whether partial synthesis or delayed indexing is visible to users.
3. Explicitly mark the denominator gap. `synthesis_failures.jsonl` and
   `index_failures.jsonl` record failures, not total attempts, so failure rate
   cannot be estimated from current evidence.
4. Do not claim a threshold retune from the current snapshot. If a future
   decision requires a rate, first propose a bounded attempt-counting design
   with privacy, overhead, and rollback checks; that would be a separate
   implementation decision.

### Acceptance and reset rule

The current evidence can support a qualitative review of whether `>=3/week`
still deserves investigation, but not a statistically grounded new number.
The corpus-size trigger remains a documented proxy until attempt logging
exists. If Ryan later approves a new threshold or a denominator mechanism,
the change must include tests, an updated rationale, and a fresh corpus-size
baseline. Do not bump `last_verified` merely to silence this warning.

## C6 readiness boundary

C6 remains **HOLD**. The C7 writer-census report, once valid and independently
reviewed, can supply only writer concurrency and conservative opens/day. It
does not supply event-size evidence, and C7 completion does not authorize C6.

### Candidate event-size sources

| Option | Privacy and freshness | Representativeness | Disposition |
|---|---|---|---|
| Structural estimator from public schema bounds | Can be payload-free and reproducible, but must prove the upper bound covers every encoder path and must not read production Chroma. | Produces bounds, not credible P50/P95 distributions unless declared dimensions model real workload. | Reject as the sole source until the bound and workload model are independently justified. |
| Hermetic synthetic generator using declared non-payload dimensions and the production encoder contract | Can produce fresh, hashable measurements without a live Shadow ledger if the generator is isolated and emits only lengths/counts/revisions. | Potentially representative, but only after showing dimensions cover the real event shape and the encoder revision is bound. | Preferred future path, but not yet approved or implemented; HOLD pending a bounded slice and independent review. |
| Existing historical or live Shadow artifacts | Historical data may be stale; live Shadow would violate the disabled-Shadow boundary and could expose payload-bearing material. | Unknown or disallowed. | Prohibited. |

The remaining unresolved constraint is therefore specific: there is no
approved, fresh, independently reviewable source for credible P50, P95, and
maximum event sizes that stays payload-free without creating live Shadow state
or reading production Chroma payloads.

### Proposed evidence contract for a later approved slice

The redacted evidence should contain exactly these semantic fields (plus no
payload or stable identifier):

```json
{
  "schema": "c6-event-size-evidence-v1",
  "p50_bytes": 0,
  "p95_bytes": 0,
  "max_bytes": 0,
  "sample_count": 0,
  "schema_revision": "",
  "encoder_revision": "",
  "measured_at_utc": "",
  "provenance": "hermetic-declared-dimensions",
  "sha256": ""
}
```

The hash should be SHA-256 over canonical JSON of the same object with
`sha256` omitted, using sorted keys, compact separators, UTF-8, and no
content-bearing fields. A future implementation must prove the negative
privacy property with tests that reject payload keys, stable IDs, production
Chroma roots, Shadow activation, network access, and live-ledger writes.

### Independent-review checklist

Before Ryan may request C6, an independent reviewer must verify every row
below against the exact artifact hashes. A passing row never implies C6
authorization; row 7 is unconditional.

| # | Check | Required evidence | Reviewer role | Stop condition |
|---|---|---|---|---|
| 1 | C7 identity | Report SHA-256, mode/owner, seven-day UTC interval, deployed revision, writer-gate protocol, Chroma-root identity, and gate identity. | Independent reviewer, not the census producer. | Any missing field or hash mismatch. |
| 2 | C7 privacy/plausibility | No payload-bearing fields or stable identifiers; concurrency and opens/day are plausible for the interval. | Independent evidence reviewer. | Payload/ID leakage or implausible aggregate metrics. |
| 3 | Event-size schema/hash and declared dimensions | Exact ten-field evidence contract; SHA-256 recomputed over canonical JSON with `sha256` omitted; private payload-free companion manifest binds declared dimensions, seed, serializer revision, and workload justification to the review packet. | Independent reviewer, not the generator author. | Extra/missing field, hash mismatch, canonicalization deviation, or unreviewed dimensions/seed/justification. |
| 4 | Freshness/binding | Fresh `measured_at_utc`; schema and encoder revisions bound to the intended deployed revision. | Independent reviewer. | Stale timestamp or revision mismatch. |
| 5 | Isolation/privacy | Negative tests and invocation evidence prove no live Shadow, production Chroma payload read, network, service control, config mutation, or ledger write. | Independent safety reviewer. | Any missing/failing negative control or prohibited access. |
| 6 | Fresh environment inputs | Fresh read-only unit count and a new private scratch directory on the intended-ledger mount. | Independent reviewer records timestamp and mount/path checks. | Missing/stale count or reused/unsafe scratch directory. |
| 7 | Separate authorization | Ryan names the C6 operation and cites the C7 and event-size artifact SHA-256 values after rows 1–6 pass. | Ryan only; no lane may infer or substitute. | No explicit named authorization, regardless of prior PASSes. |

## Bounded future implementation slice

If the HOLD is later resolved, the smallest safe implementation should be a
hermetic event-size generator plus focused tests. Allowed scope: a new
generator module, its unit tests, and a plan/verification document. Prohibited
scope: `shadow_*` activation paths, census artifacts, production Chroma
access, config files, services, backups, network, and live ledger writes.
Required tests include deterministic repeatability, canonical hash
verification, schema/encoder revision binding, upper-bound coverage, and
negative privacy/isolation controls. Merge remains disabled until independent
review confirms the evidence contract and boundary checks.

## Retrieval-gap triage (no ledger mutation)

The read-only search pass reproduced useful partial hits but not a single
complete current-state answer. Keep these findings in this plan/chat; do not
run `convmem add` or create observations while the deployed checkout is
frozen.

The bounded search order is documented in the
[retrieval-gap triage protocol](PLAN-2026-07-31-RETRIEVAL-GAP-TRIAGE.md).

| Open observation | Next bounded search/investigation | Current evidence | Status |
|---|---|---|---|
| `obs_67af0873f738` — current testing phase and CLI syntax | Search the Phase 3 Continue/Crush handoff and the canonical `add` syntax; verify the retrieved command includes required author/keyword fields. | Search surfaced the Phase 3 handoff and the known `--author`, repeated `--keyword` requirement, but not a single consolidated brief. | Searched-partial |
| `obs_a379f07d0878` — current testing phase not surfaced | Compare `LATEST.md`, the built-plans archive, and the newest inter-model handoff as a navigation test. | Search surfaced Phase 3 verify-only material; the brief also warned that `LATEST.md` is stale relative to newer handoffs. | Searched-partial |
| `obs_806985bc5697` — background synthesis pointer/gates | Preserve the canonical pointer to `BUILT-PLANS-2026-06-24-to-2026-06-29.md` and its Phase 0/1/2 gates; do not duplicate the plan. | Search confirmed Phase 1 shipped and Phase 2 remains gate-bound/deferred. | Searched-partial |
| `obs_885c236b34fd` — Willowy Hollow precedent | Use site-scoped retrieval in the separate WordPress repo when authorized; do not alter that repo here. | General search surfaced Method A deployment precedent, but not the complete current guide. | Searched-partial |
| `obs_e1520bf6e193` — Willowy Hollow webdev guide | Retrieve `docs/WILLOWYHOLLOW-WEBDEV-GUIDE.md` by exact path and compare it with the site-specific session loop. | Search identified the guide and its intended contents; no file was changed. | Searched-partial |
| Six staging2 header observations | Keep as external/site work, separate from this plan; only read-only monitor evidence is in scope here. | Current brief still reports missing CSP and Referrer-Policy; HSTS status also remains an open failed observation. | Pending/external |

## Safe next actions

1. Preserve the deployed checkout at the frozen revision and re-run only
   read-only `doctor`, `brief`, `unresolved`, and targeted corpus searches.
2. When the freeze ends and Ryan authorizes implementation, use the
   [execution-ready recency protocol](PLAN-2026-07-31-RECENCY-BOOST-RETUNE-EVALUATION.md)
   and run the recency
   golden-query evaluation first; do not tune recency and chunking together.
3. Treat escalation-threshold work as a measurement/denominator design
   problem before changing numbers.
4. Keep C6 at HOLD until the fresh event-size source and all independent
   review inputs exist.

**Verdict:** C6 EVENT-SIZE EVIDENCE HOLD — no approved fresh payload-free
source currently provides credible P50/P95/maximum evidence without live
Shadow state or production-payload access.
