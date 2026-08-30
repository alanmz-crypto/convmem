# R2b v2 I1–I3 authority-boundary corrective IV evidence

**Arc:** R2b Capture Authorization
**Integration base:** `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d`
**Failed Corrective III review tip (preserved):** `99014697b0b0e9a4c563ea0ca0d89135513a33b5`
**Status:** Corrective IV candidate — NOT operational VERIFY

## Two-SHA model

| Role | SHA |
|---|---|
| `implementation_tip` | `1b0dd44fe8797d12c8627512b36e079f677adcc0` |
| `evidence_tip` | *(this commit)* |
| `integration_base` | `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d` |

## Corrective IV summary

- **Possession capabilities:** `AuthorityMintCapability` tokens issued only from canonical
  lifecycle modules; single-use, chain-bound, non-constructible by callers
- **Mint windows removed:** `census_mint_window`, `lease_acquisition_window`, and
  `source_composition_window` no longer exist on the import surface
- **Closure-held registry:** trusted backing state held in closure; module globals
  `_REGISTRY` / `_TRUSTED_REGISTRY` unreachable
- **Continuous lock binding:** every trusted lookup re-verifies custodian kernel-lock
  possession; source authority fails closed after lock loss or custodian death
- **Trust class separation:** hermetic test fixtures vs production-capable authority
  distinguished in records; caller production gate policy still refused
- **Per-sink scanner governance:** unchanged from Corrective III — sink-specific evidence

## Test evidence

- R2b v2 focused suite: **104 passed**
- Corrective IV adversarial regressions: **17 tests** in `test_r2b_v2_authority_boundary_iv.py`
- PR #247 relocation-scope regressions: **19 passed**
- Scanner/inventory verification: **PASS**
- Pylint (changed modules): **10.00/10**

## Authority boundaries (unchanged)

I4–I8: NONE | Production gate: NOT ACQUIRED | Live authority: NONE | 900s: NOT RATIFIED

## Claim offered for independent review

> Corrective IV establishes a real possession-based authority boundary: ordinary Python
> callers cannot invoke trusted mint phases, mutate trusted backing state, manufacture an
> equivalent authority capability, substitute the custodian, preserve trust after
> kernel-lock loss, or conceal ungoverned mutation sinks, while the genuine canonical
> R2b I1–I3 lifecycle remains functional.
