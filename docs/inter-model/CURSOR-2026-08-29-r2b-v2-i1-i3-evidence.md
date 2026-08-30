# R2b v2 I1–I3 authority-boundary corrective III evidence (current-main integration)

**Arc:** R2b Capture Authorization
**Integration base:** `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d` (`origin/main` at publication)
**Failed Corrective II review tip (preserved):** `d30173d5defd7879d70348080f72c6fda5a7056a`
**Status:** Corrective III candidate — NOT operational VERIFY

## Two-SHA model

| Role | SHA |
|---|---|
| `implementation_tip` | `6379073235fc3ad5e84faa867d44eed5628f99c5` |
| `evidence_tip` | *(this commit)* |
| `integration_base` | `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d` |

Inventory digest: `f27f782e849de61c0907f0b30fe97911f86148744d9d5a6a8213fb28740ae50d`

## Corrective III summary

- **Sealed registry stores:** backing dicts reject ordinary caller mutation; module-level registry exports blocked
- **Lifecycle-gated minting:** census, lease acquisition, and source composition windows required for trusted inserts
- **Custodian binding:** object-identity verification; substitution via registry overwrite forbidden
- **Cascade invalidation:** lease/coverage invalidation revokes dependent source authority
- **Issuance revalidation:** final lease+custodian re-check under composition window closes TOCTOU
- **Canonical gate binding:** caller-supplied production gate policy and revision substitution refused
- **Full SHA binding:** authority-bearing paths require 40-char git SHA; abbreviated tips fail closed
- **Per-sink scanner governance:** mutation sinks listed at file:line; new sinks in known routes fail inventory

## Test evidence

- R2b v2 focused suite: **120 passed**, 1 skipped
- Corrective III adversarial regressions: **16 tests** in `test_r2b_v2_authority_boundary_iii.py`
- PR #247 relocation-scope regressions: **included in run — pass**

## Authority boundaries (unchanged)

I4–I8: NONE | Production gate: NOT ACQUIRED | Live authority: NONE | 900s: NOT RATIFIED

## Claim offered for independent review

> Corrective III removes ordinary caller-controlled manufacture, substitution, replay, survival, and independent attestation of trusted R2b I1–I3 authority, while preserving a functional legitimate canonical authority lifecycle and detecting ungoverned current-main mutation sinks individually.
