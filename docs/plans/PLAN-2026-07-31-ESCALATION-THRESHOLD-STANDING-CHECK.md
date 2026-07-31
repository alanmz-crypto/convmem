# Escalation-threshold standing check: measurement design

**Status:** plan-only, review-required. This document authorizes no config
change, register edit, failure-log mutation, Shadow operation, production
Chroma access, ledger write, or service action.

**Draft source:** Kiro design-review lane. The deployed checkout remains at
`76126e07a97187f68d925dd8b431d2d03967084f` through 2026-08-07 00:00 UTC.
Any implementation is deferred until after that freeze and requires Ryan's
explicit authorization; implementation belongs to Cursor after approval.

## Evidence boundary

### Read-only evidence recheck — 2026-07-31

Targeted corpus search recovered prior analysis that corpus growth can serve as
a weak proxy for gate-event volume when failure logs omit total attempts. The
search also recovered the current Kiro/DeepSeek standing-trigger explanation.
Neither source supplies a complete attempt denominator, so the measurement
design and HOLD verdict remain unchanged.

The `escalation-threshold-retune` row is due because its corpus-size trigger is
`baseline: 5708` with `multiple: 2.0`, while the read-only snapshot reports
12,427 active units. Doctor reports this as an advisory warning and remains
exit-zero.

The current seven-day snapshot reports:

| Gate | Recorded failures | Attempts | Honest interpretation |
|---|---:|---:|---|
| `synthesis_gate` | 2 | Unknown | Below the `>=3/week` investigation trip-wire; rate unknown. |
| `index_gate` | 0 | Unknown | No recorded failures; any failure triggers investigation; rate and log completeness unknown. |

The failure logs establish recorded failure counts only. They cannot establish
failure rates, threshold sensitivity, operational volume, or complete failure
capture without an attempt denominator. Two failures could be 2/3 or 2/2,000.
Therefore no statistically grounded threshold retune is supportable today.

Corpus size is a reasonable maintenance proxy because it is observable without
new instrumentation, but it is weak: batch sizes, ingest clustering, and
trigger frequency vary independently of corpus size. It should remain the
current proxy until attempt logging exists and is independently verified.

## Minimal future attempt-counting design

This is a design proposal only. It must be implemented separately, tested, and
reviewed before the register is retargeted.

A future implementation would use two new append-only files alongside the
existing failure logs:
`synthesis_attempts.jsonl` and `index_attempts.jsonl`. Each terminal gate
outcome would emit exactly this payload and no other fields:

```json
{
  "schema": "gate-attempt-v1",
  "gate": "synthesis_gate",
  "outcome": "success",
  "timestamp_utc": "2026-08-01T00:00:00Z"
}
```

`gate` is `synthesis_gate` or `index_gate`; `outcome` is `success`, `failed`,
or `partial`. A future writer would append one line after the gate reaches a
terminal outcome and would not include query text, embeddings, unit content, stable IDs,
user/session identifiers, payload metadata, network addresses, or
environment-specific paths.

The attempt writer must be additive and rollback-safe: if its file is absent,
existing gate behavior and doctor exit status remain unchanged. It must use the
same process boundary as the gate, perform one open/write/close append, avoid
network and subprocesses, and never rewrite the failure logs.

With verified attempt files, the rolling seven-day rate is:

```text
failed records in UTC window / all attempt records in the same UTC window
```

The probe may display count and rate together, but must degrade to count-only
when attempt files are absent. Required future tests include schema rejection of
payload-bearing fields, correct fixture rates, unchanged behavior with absent
attempt files, failure-log immutability, and exact schema-version handling.

## Interim qualitative gates

Until a denominator exists, use these as review practices only; they do not
authorize a retune or register reset.

1. **Q1 — Absolute count:** inspect the rolling seven-day window. Investigate
   at `synthesis_gate >=3` or any `index_gate` failure. A qualitative pass is
   synthesis 0–2 and index 0, explicitly labeled weak count-only evidence.
2. **Q2 — Threshold plausibility:** document whether ingest pattern, trigger
   frequency, or operator impact materially differs from the calibration period.
   If so, mark the current threshold provisional.
3. **Q3 — Log completeness:** compare failure-log timestamps with known
   operational events. If a known failure is absent, treat absence as
   untrustworthy and do not claim a clean window.

The review note must state the UTC window, both counts, and the completeness
finding. Keep it in chat or a private review note; do not create a ledger record
without Ryan's authorization.

## Acceptance and rejection

A future rate-based retune requires all of the following:

- independently reviewed attempt logging and passing negative tests;
- at least two complete rolling seven-day windows, with representative volume;
- an explicit rationale covering observed rates, detection latency, and
  false-positive investigation cost;
- independent review by someone who did not author the instrumentation; and
- Ryan's explicit approval of the threshold value and register operation.

Reject the retune if it relies only on current failure counts, has an incomplete
or non-conformant attempt log, spans an anomalous migration/outage/debug period
without disposition, or attempts to silence the warning by changing only
`last_verified`.

The two standing checks must remain separate: recency can use its held-out
retrieval evaluation; escalation requires denominator instrumentation first.

## Reset and review checklist

The current corpus-size trigger may be reset only after a completed review and
separate Ryan authorization. A valid register update changes `baseline` to the
current collection count and `last_verified` together, with a one-sentence
rationale; editing only `last_verified` is never a reset. A future probe-based
register trigger is a separate authorized change after the rate evidence exists.

Before any threshold or baseline change, an independent reviewer must verify:

| # | Check | Stop condition |
|---:|---|---|
| 1 | Denominator gap and evidence window are explicitly stated. | A rate is claimed without a complete attempt window. |
| 2 | Attempt files contain exactly the approved fields, if present. | Extra, missing, or payload-bearing field. |
| 3 | Negative tests pass on the exact implementation revision. | Any failure or missing test output. |
| 4 | The rate window is representative and UTC boundaries match. | Unexplained migration, outage, or boundary mismatch. |
| 5 | Q1–Q3 or the rate review note records counts and completeness. | Missing, undated, or mismatched review note. |
| 6 | Register diff changes only the authorized baseline/verification fields. | `last_verified`-only edit or unrelated row changes. |
| 7 | Ryan names the threshold and register operation after rows 1–6 pass. | No explicit authorization, regardless of prior PASSes. |

**Verdict: HOLD.** The standing check remains due. The safe path is to add and
verify attempt measurement after the freeze, collect two representative rate
windows, review the threshold, and obtain Ryan's named authorization before any
register or runtime change.
