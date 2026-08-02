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

The declared dimensions, seed, and serializer revision must be reviewable
inputs to the run. Resolve this without expanding the ten-field C6 artifact:
the future run must produce a private, payload-free companion input manifest
containing those inputs, canonicalize and hash that manifest separately using
the same canonical-JSON rules (sorted keys, compact separators, UTF-8,
`ensure_ascii=False`, `allow_nan=False`) and SHA-256 algorithm as the ten-field
artifact, and
bind its hash to the evidence review packet. The companion is not a live
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
HOLD. This remains future design guidance, not authorization to create either
artifact.

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
hash verification.

## Review, rollback, and authorization gates

Independent review must verify the exact source revision (performed by a
reviewer who did not author or operate the generator run), negative controls,
field allowlist, canonical artifact hash, companion-manifest hash and binding,
declared bounds plus their workload justification, deterministic replay, and
representativeness limits. Any failure means no artifact may feed C6. A
passing generator design or implementation does not authorize merge, C6, or
Shadow activation. Rollback is simply to discard the unapproved generator and
artifact; no live state may need repair.

## Verdict

**C6 EVENT-SIZE EVIDENCE HOLD — the generator design is bounded, but no
approved implementation or independently reviewed fresh artifact exists.**
