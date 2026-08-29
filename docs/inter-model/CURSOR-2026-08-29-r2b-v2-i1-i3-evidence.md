# R2b v2 I1–I3 authority-boundary corrective II evidence (current-main integration)

**Arc:** R2b Capture Authorization
**Integration base:** `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d` (`origin/main` at publication)
**Prior CI-red publication:** PR #251 @ `c870133` / implementation `5d72f45`
**Status:** Current-main integration corrective — NOT operational VERIFY

## Two-SHA model

| Role | SHA |
|---|---|
| `implementation_tip` | `539a1cf` |
| `evidence_tip` | *(this commit)* |
| `integration_base` | `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d` |

Inventory digest: `86256ddae6d81d6de55b4ed2a05abe47746a549b4b57798de220fdbd91ef51be`

## Integration corrective

- Transplanted Corrective II (`5d72f45` semantics) onto `e930ae4` via cherry-pick + inventory integration
- Classified landed CG-2 `cg2_rehearsal.py` `FileGenerationStore` sites as `cg2_d4` / `gated`
- Zero-bypass scans: PASS (0 unlisted mutation sinks)
- Pylint regression gate vs `e930ae4`: PASS

## Authority-boundary design (unchanged)

- Source-authority mint internalized: `compose_and_mint_source_authority`
- No public `mint_source_authority_record` or `register_custodian`
- Custodian registration lifecycle-only via `_register_lease_custodian`
- Diagnostic provenance seal, one-shot tickets, coverage-to-lease binding, epoch invalidation

## Authority boundaries (unchanged)

I4–I8: NONE | Production gate: NOT ACQUIRED | Live authority: NONE | 900s: NOT RATIFIED
