# C6 hermetic event-size generator — design draft

**Draft source:** Kiro design-review lane, preserved by Codex for review.
**Status:** Plan-only; C6 remains HOLD and merge-disabled.
**Branch PR title:** docs: freeze-safe analysis plans for C6 hold, standing checks, and retrieval gaps

This document defines the smallest future design that could close the fresh
event-size evidence gap. It authorizes no implementation, C6 run, Shadow
activation, census operation, or production-data access.

## Objective and boundary

Produce fresh P50, P95, and maximum serialized event sizes from a hermetic
synthetic generator whose inputs are declared structural dimensions, not
production payloads. The resulting artifact may contain only the ten fields
in the readiness plan’s evidence contract. C7 remains a separate input for
writer concurrency and opens/day; neither gate implies the other.
A valid C7 census report does not satisfy or substitute for the C6 event-size
evidence contract; the two evidence artifacts are structurally distinct, and
neither authorizes the other gate.

The generator must run from an isolated scratch context after the deployed
freeze, with no network, live configuration, production Chroma read, census
read, Shadow ledger, service control, or ledger write. The deployed checkout
remains frozen at `76126e07a97187f68d925dd8b431d2d03967084f` until
2026-08-07 00:00 UTC.

## Declared dimensions

The design may use only public/schema-declared values:

- fixed event keys, JSON types, schema revision, and encoder serialization
  rules;
- fixed-width synthetic UUID/hash/timestamp placeholders;
- enumerated operation and route lengths;
- declared maximum metadata shape and declared document-length bounds;
- a fixed RNG seed and sample count.

No bound may be inferred by reading production Chroma documents, metadata,
stable IDs, configuration, census artifacts, or a live ledger. Synthetic
placeholders must never be copied from production identifiers.

### Boundary inputs required before a future run

The companion input manifest must instantiate these boundary anchors with
concrete numeric values or enumerated members before any future generator run.
They are review fixtures, not authorization to create an artifact:

| Dimension | Minimum | Near maximum | Maximum |
| --- | --- | --- | --- |
| `sample_count` | `1` | `N_max - 1` | `N_max` |
| document length bound | `0` bytes | `L_max - 1` bytes | `L_max` bytes |
| metadata shape | `{}` | one shape below the declared bound | declared maximum shape |
| operation/route length | shortest declared member | one below declared maximum where length-bounded | longest declared member |
| fixed-width placeholders | minimum legal width | one below declared width maximum | declared width maximum |

The manifest must also include the selected nominal case and any malformed or
excluded case needed to prove fail-closed validation (for example, zero or
negative `sample_count`, an invalid timestamp, and an out-of-bound dimension).
The reviewer must confirm that every symbolic bound (`N_max`, `L_max`, and
other declared maxima) is replaced by a concrete value in the manifest and
that the resulting cases remain payload-free.

## Proposed interface and pseudocode

The future module should expose a pure function, with all inputs explicit:

```text
generate_event_size_evidence(
    schema_revision,
    encoder_revision,
    declared_dimensions,
    sample_count,
    rng_seed,
    measured_at_utc,
) -> redacted_evidence
```

The function validates non-empty revisions, positive sample count, bounded
declared dimensions, and a valid UTC timestamp. It then:

1. seeds a deterministic local RNG;
2. creates synthetic event shapes using only declared placeholders;
3. serializes each shape with the bound encoder/canonical JSON rules;
4. measures UTF-8 byte lengths, sorts them, and computes percentiles using
   the existing ceiling-rank method: `max(0, ceil(p/100*n)-1)`;
5. emits only the ten-field redacted evidence object; and
6. computes `sha256` over canonical JSON after omitting the `sha256` field.

The generator must not import or call live Shadow, Chroma, writer-census,
activation, or runtime-configuration paths. Encoder revision binding must be
an explicit reviewed input; it must not silently resolve to `unknown`.

## Evidence and reproducibility contract

The artifact contains exactly:

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

Canonicalization is UTF-8 `json.dumps` with sorted keys, compact separators,
`ensure_ascii=False`, and `allow_nan=False`; hash the object after removing
`sha256`. No additional field, payload, stable identifier, production path,
activation ID, or session nonce is allowed in the artifact.

Field constraints: `p50_bytes`, `p95_bytes`, and `max_bytes` must be
non-negative integers; `sample_count` must be a positive integer (non-finite,
null, or fractional values force C6 at HOLD); `measured_at_utc` must be a
non-empty ISO-8601 UTC string;
`sha256` must be exactly 64 lowercase hex characters; `schema`, `provenance`,
`schema_revision`, and `encoder_revision` must be non-empty strings. Any extra
field, missing required field, or type violation forces C6 at HOLD.

The declared dimensions, seed, and serializer revision must be reviewable
inputs to the run. Resolve this without expanding the ten-field C6 artifact:
the future run must produce a private, payload-free companion input manifest
containing those inputs, canonicalize and hash that manifest separately using
the complete companion-manifest object with no field removal (the companion
manifest contains no self-referential hash field), using the same canonical-JSON
rules (sorted keys, compact separators, UTF-8,
`ensure_ascii=False`, `allow_nan=False`) and SHA-256 algorithm as the ten-field
artifact, and
bind its hash to the evidence review packet. The packet must include a
`companion_manifest_sha256` field containing exactly 64 lowercase hex
characters, computed by the same canonical-JSON rules as the artifact hash;
reviewers must independently recompute it from the companion manifest to
confirm the binding. The companion is not a live
ledger artifact and must never contain payloads, stable identifiers, or
production paths. If the companion manifest or its binding is absent, the
result remains HOLD. This is a design contract only; implementation is not
authorized by this draft.

The companion and the reviewer-only evidence packet must exist only in an
ephemeral private scratch directory on an isolated non-production filesystem.
Neither may be written under the deployed checkout, any live data root,
intended-ledger mount, census or Shadow path, or repository tree. For this
design, the evidence review packet is the reviewer-only bundle containing the
ten-field artifact, the canonical companion-manifest hash, and the companion
manifest itself; it must carry no production path, scratch-directory path,
session nonce, activation ID, or stable identifier.
The packet's absence, path-boundary failure, or hash mismatch keeps C6 at
HOLD. The packet must also include a `source_revision` field recording the
exact git SHA of the generator source reviewed and a `reviewer_verdict` field
recording the independent reviewer's PASS or FAIL; absence of either field is
a HOLD condition. The packet must also include a `reviewer_independence` field
containing a non-empty string attesting that the reviewer neither authored nor
operated the generator run, without stable identifiers; absence or an empty
value forces C6 at HOLD. These are packet fields, not additions to the
ten-field artifact. Packet-only fields (`companion_manifest_sha256`,
`source_revision`, `reviewer_verdict`, `reviewer_independence`, and
`disposition`) are never present in the JSON object from which the artifact
`sha256` is computed; their hash scope is the review-packet binding, not the
artifact canonical form. Unknown fields in the review-packet envelope beyond
the five named packet-only fields and the ten-field artifact are prohibited and
force C6 at HOLD. This remains future design guidance, not authorization
to create either artifact.

## Companion manifest schema

The companion manifest must contain exactly these required fields:

- `schema_revision`, `encoder_revision`: non-empty strings;
- `source_revision`: the exact 40-character lowercase hexadecimal git SHA of
  the reviewed generator source;
- `rng_seed`: a non-negative integer;
- `sample_count`: a positive integer;
- `declared_dimensions`: a non-empty object whose bounds are concrete numeric
  values or enumerated members and contain no payloads or stable identifiers;
- `workload_justifications`: a non-empty object keyed by declared structural
  bound, with each value containing non-empty data-source-or-reasoning,
  conservative-direction, and safety-rationale strings. It must contain one
  entry for each boundary-input row named in the table: `sample_count`,
  `document_length_bound`, `metadata_shape`, `operation_route_length`, and
  `fixed_width_placeholders`; absence of any named row is a HOLD condition;
  each justification entry should name the concrete bound value it covers
  (matching the corresponding `declared_dimensions` key) so reviewers can
  validate the pairing without cross-referencing a second object;
- `boundary_exclusion_cases`: a non-empty list naming at least zero/negative
  `sample_count`, invalid UTC timestamp, out-of-bound dimension, unknown field,
  non-finite/null/fractional numeric value, payload or stable-identifier value,
  prohibited path (including any scratch-directory absolute or relative path
  leaked into the artifact or companion manifest fields), and missing required
  field, each with an expected HOLD result; absence or incomplete
  enumeration of any named case is a HOLD condition; and
- `measured_at_utc`: a non-empty ISO-8601 UTC string; it must be an explicit,
  reviewer-supplied input fixed before the run begins, not read from ambient
  wall-clock state at runtime, and must be identical across replay runs for
  `sha256` comparison to be valid. Any run where `measured_at_utc` differs
  between independent replay invocations forces C6 at HOLD.

Unknown fields are prohibited and force C6 at HOLD. A missing required field,
empty value, type violation, non-concrete bound, or privacy-boundary violation
also forces C6 at HOLD.

## Freshness and expiry

Evidence is valid only for the exact `schema_revision` and
`encoder_revision` declared in the artifact. Any change to either revision,
any discrepancy between the companion-manifest hash and the bound hash, or
any inability to independently reproduce the artifact's SHA-256 immediately
invalidates prior evidence and requires a new generator run and independent
review. Stale or unverifiable evidence holds C6 at HOLD and must not be
silently reused.

## Required negative controls

Before review, tests must fail closed if the generator:

- reads any production Chroma document, metadata, root, census report, live
  configuration, or ledger;
- imports or calls Shadow activation, sink, ledger, canary, writer-gate, or
  writer-census runtime paths;
- makes a network/DNS/socket call or controls a service;
- emits payload keys, stable IDs, production paths, activation IDs, or nonces;
- writes outside a declared private scratch directory;
- emits JSONL or any output file with a `.jsonl` extension, or produces an
  artifact with more than the ten allowlisted fields; or
- produces a non-deterministic result for identical declared inputs and seed.

A non-deterministic result means a `sha256` differing across two independent
runs with identical declared inputs, seed, `schema_revision`,
`encoder_revision`, `source_revision`, and `measured_at_utc`. Any such replay
disagreement is a
HOLD condition and must be explicitly documented in the `reviewer_verdict`
field before C6 evidence can be accepted.

Before the run begins, the isolated scratch directory must be confirmed not
to reside under any live data root, census path, Shadow path, ledger root, or
repository tree. This path-boundary check is a mandatory, independently
verifiable gate in the review packet; its absence is a HOLD condition.

Tests must also recompute the canonical hash independently and verify
`p50_bytes <= p95_bytes <= max_bytes` with positive integer values.

## Representativeness limits

The generator measures serialized byte-size behavior for declared synthetic
dimensions, not production payload distributions. A low document-length or
metadata bound can understate P95/max; a worst-case structural bound can
overstate typical sizes. The independent reviewer must accept the declared
limits as a conservative basis, or the design remains HOLD. Sample count does
not turn a declared distribution into empirical production evidence.
The companion input manifest must include a written workload justification for
each declared structural bound, explaining why the bound conservatively covers
the real workload distribution; its absence is a HOLD condition independent of
hash verification. A workload justification is adequate only if it states the
data source or reasoning, the conservative direction (over- or under-estimate),
and why that direction is safe; a justification that omits any of these three
elements is treated as absent and holds C6 at HOLD.

## Review, rollback, and authorization gates

Independent review must verify the exact source revision (performed by a
reviewer who did not author or operate the generator run), negative controls,
field allowlist, canonical artifact hash, companion-manifest hash and binding,
declared bounds plus their workload justification, deterministic replay, and
representativeness limits. Deterministic replay means at least two independent
runs with identical declared inputs, seed, `schema_revision`,
`encoder_revision`, `source_revision`, and `measured_at_utc` producing
byte-identical `sha256`; fewer than two runs is a HOLD condition. Any failure
means no artifact may feed C6. A
`reviewer_verdict` field value of `FAIL` is itself a HOLD condition independent
of field presence; the absence of the field and a `FAIL` value are treated
identically.

passing generator design or implementation does not authorize merge, C6, or
Shadow activation. A `reviewer_verdict` of `PASS` confirms technical
correctness only; it does not constitute or imply Ryan's merge authorization.
Rollback is simply to discard the unapproved generator and
artifact; no live state may need repair. A `reviewer_verdict` of `FAIL`
requires the review packet to include a `disposition` field confirming the
scratch artifact and companion manifest were deleted from the ephemeral
directory; absence of this field after a `FAIL` verdict is itself a HOLD
condition. `disposition` must be a string whose only allowed value is
`artifacts-deleted-from-ephemeral`; any other value, an empty string, or a
non-string type forces C6 at HOLD. When `reviewer_verdict` is `PASS`, the
`disposition` field must be absent. Presence of `disposition` when
`reviewer_verdict` is `PASS`, or a `reviewer_verdict` value that is missing,
empty, non-string, or not exactly `PASS` or `FAIL`, forces C6 at HOLD.

## Verdict

**C6 EVENT-SIZE EVIDENCE HOLD — the generator design is bounded, but no
approved implementation or independently reviewed fresh artifact exists.**
