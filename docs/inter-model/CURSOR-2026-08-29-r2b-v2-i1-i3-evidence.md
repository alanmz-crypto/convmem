# R2b v2 I1–I3 corrective evidence

**Arc:** R2b Capture Authorization
**Granted base:** `c6e8b2b0293edf8b0faf29e9e393e69eca6ca494`
**Prior failed tip:** `d50f041e4eec6e5ad5e80041a71763bb0ae7b7b3`
**Status:** Corrective implementation evidence — NOT operational VERIFY

## Exact-tip inventory binding

`docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` is generated evidence, not hand-edited.
After the corrective commit lands, regenerate at the candidate tip:

```bash
python -c "from eval_corpus.r2b_v2.coverage.inventory import write_v2_inventory_file; write_v2_inventory_file()"
```

`code_revision` in the inventory is `current_code_revision()` (= `git rev-parse HEAD` at generation time).
The inventory digest incorporates `source_scan_unlisted_sites` from `scan_repo_for_unlisted_chroma_ctor()`.

## Corrective scope (P0/P1)

| Finding | Correction |
|---|---|
| P0 live LOCK_EX verification | Subprocess flock probe; verify fails after `LOCK_UN` |
| P0 fabricated coverage | `DiagnosticCoverageResult` vs `TrustedCoverageProof` separation |
| Cross-slice binding | `source_authority_from_lease_and_coverage` cross-checks all digests/identities |
| Same-run reacquisition | `trusted.py` one-shot consumption registry |
| Capability forgery/fork | Process-local tokens + `register_at_fork` invalidation |
| Canonical gate binding | `gate_policy.py` production vs `test_gate_policy()` |
| Trusted implementation revision | Derived from `current_code_revision()`, not caller param |
| Strict contract version | Only exact `int` 2 accepted |
| State reconstruction | `reconstruct_state_machine` sets `_resumed=True`; no live transitions |
| Transition/evidence coupling | `transition_to_q_held` / `transition_to_coverage_proven` |
| Static inventory grounding | Source scan feeds inventory digest and coverage proof |
| skip_runtime authority | Cannot mint `TrustedCoverageProof` when runtime skipped |
| Concrete timeout default | `timeout_ms` required parameter (no silent 30000) |

## Mechanical gates

- Focused pytest: `tests/test_r2b_v2_*.py`
- Pylint regression (R2b files): PASS, 0 new/increased findings
- `git diff --check`: PASS
- `convmem doctor`: PASS

**Note:** Static scan tests require a clean checkout without `.worktrees/` contamination.
