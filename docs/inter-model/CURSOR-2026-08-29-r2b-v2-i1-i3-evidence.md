# R2b v2 I1–I3 corrective evidence

**Arc:** R2b Capture Authorization
**Intervening main:** `3dd355a50c1498aadc94b143f6997d2e005016be` (PR #245 watch memcap)
**Prior granted base:** `c6e8b2b0293edf8b0faf29e9e393e69eca6ca494`
**Prior corrective tip (old-base):** `fce82a8b70264c327ddc8443d5f46b1ea495f50c`
**Status:** Clean-base recovery evidence — NOT operational VERIFY

## Exact-tip inventory binding (two-SHA model)

Per `VERIFY-r2b-v2-quiescence.md` V2a, the inventory binds the **implementation
tip** (code-bearing commit), not the later evidence-only commit.

| Role | SHA |
|---|---|
| `implementation_tip` | `e2af5001c4de0852e94769fc5692105353d5046c` |
| `evidence_tip` | `5cdc6be…` (inventory commit on clean-base branch) |

`docs/plans/R2B-V2-WRITER-COVERAGE-INVENTORY.json` is generated at
`implementation_tip` via detached worktree:

```bash
git worktree add /tmp/r2b-inv-bind e2af500
cd /tmp/r2b-inv-bind
python -c "from eval_corpus.r2b_v2.coverage.inventory import write_v2_inventory_file; write_v2_inventory_file()"
```

`code_revision` in the inventory equals `implementation_tip`. The evidence commit
changes only the inventory JSON — no implementation/config/coverage semantics.

## PR #245 watch/F0 compatibility

Audited `3dd355a`: `_scoped_index_cmd` wraps existing `convmem index --file`
argv in `systemd-run --user --scope` when available. Inner mutation child
unchanged. Static route `watch.py:watch_index_event` unchanged. Wrapper is not a
new writer route; runtime census classifies processes opening mutable surfaces,
not ancestor wrappers.

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
