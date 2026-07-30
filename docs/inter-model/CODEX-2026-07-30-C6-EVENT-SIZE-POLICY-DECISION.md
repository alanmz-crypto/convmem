# C6 event-size evidence — decision packet

**Owner:** Ryan  
**Author:** Codex planning lane  
**Status:** Decision required. Shadow remains disabled; C7, C6, and activation are not authorized by this document.

## Decision to make

C6 needs fresh P50, P95, and maximum encoded-event byte sizes plus a redacted
evidence hash. C7 supplies writer concurrency only; it cannot supply event
sizes. Under the present policy, production Chroma document, metadata,
embedding, and source-content reads are prohibited.

The completed investigation established that SQLite `LENGTH()` is not an
acceptable loophole: for text it returns Unicode code points rather than bytes
and reads the complete string internally. Schema-only bounds cannot supply
credible P50/P95 values. Therefore C6 is currently held.

## Option 1 — preserve strict payload isolation (recommended)

**Decision:** Retain the current prohibition on all production payload reads,
including SQL functions that inspect text internally.

**Result:**

- C7 may still be separately authorized and operated under its merged runbook.
- C6 remains held; no event-size implementation slice begins.
- Shadow remains disabled and activation remains forbidden.

**Why recommended:** It preserves the already-approved privacy boundary and
avoids recasting a canary prerequisite into a data-access exception. There is
no credible percentile source presently available inside this boundary.

## Option 2 — authorize a new aggregate-only measurement architecture

**Decision:** Narrowly permit a future, separately reviewed measurement design
to inspect production values in memory solely to compute byte-accurate aggregate
statistics.

**Required authorization text:**

```text
Authorize a read-only, aggregate-only production measurement planning slice for
C6 event-size evidence. It may inspect document/metadata values in memory only
to compute byte-accurate aggregate statistics. It may retain or emit no content,
identifiers, per-record lengths, embeddings, or source paths. Shadow remains
disabled; C7 arm, C6 execution, and activation are not authorized by this
decision.
```

**Result:** Codex may then author a bounded architecture/execution plan. No
Cursor implementation starts until that plan receives Kiro review and targeted
Copilot privacy/isolation audit. Any implementation must add an evidence-file
binding to C6; current C6 accepts only manual event-size values and an evidence
SHA, so this is not a trivial helper addition.

**Non-negotiable constraints for a later plan:**

- byte-accurate encoded-event sizes, including serialization and metadata
  overhead—not document character counts;
- output limited to aggregate statistics, provenance, timestamp, schema/code
  identity, and hash;
- private durable evidence; no raw values or payload-bearing diagnostics;
- no Chroma writes, no new Chroma schema, no Shadow ledger/artifacts, no
  service control, and no network access;
- independent negative privacy controls and exact-tip safety audit before
  merge;
- a successful measurement tool still does not authorize C6 or activation.

## Decision outcomes

| Ryan decision | Immediate next owner | What may happen | What remains blocked |
|---|---|---|---|
| Option 1 | Ryan for optional C7 operation | C7 preflight/arm under its runbook | C6, activation |
| Option 2 | Codex planning lane | architecture/execution plan only | implementation, C7 arm, C6, activation unless separately granted |
| No decision | None | no new C6 work | C6, activation |

## Current facts

- C7 writer census is merged and has a merged, review-cleared operational
  runbook.
- C6 event-size evidence is explicitly held; no valid evidence artifact exists.
- The C6 budgets remain approved but are unusable until an approved evidence
  source exists.
- The PR #135 review documentation did not authorize a payload-read exception.

## Verdict

```text
C6 EVENT-SIZE EVIDENCE HOLD — Ryan policy decision required
```

