# T3 Residual Closure Evidence — Arc Trapdoor Hunt

> Evidence-only packet for the separately authorized residual T3 closure lane.
> This packet does not repair implementation, alter locked requirements, or
> promote repository VERIFY rows.

```text
Status:       Evidence collection complete; T3 closure not ready
Arc:          Trapdoor Hunt
Starting basis: 8d9b7f00b171e1f9a1d2d2e57f9e674ab9d9a17e
Locked T3:    aae0cad0bb05b0e436e213b28abbe0ff05ba2e91
Branch:       verify/2026-08-19-trapdoor-t3-residual
Worktree:     /tmp/convmem-trapdoor-t3-residual.7QpIm2
PR:           #209 — https://github.com/alanmz-crypto/convmem/pull/209
Implementation under test: P1/P2/P3 merged tip 6ec5b6c031ae8fdedbd90ef1392232d25f0bfaf1
```

## Evidence-only boundary

This lane may add deterministic fixtures, tests, serialized evidence, and
controlled regression commands for exactly V3f, V3h, V4m, V8c, V8e, V8g, V9a,
and V9d. It must not repair implementation, weaken an oracle, change the
locked T3 requirements, or promote repository VERIFY rows from `PENDING`.

Migration, Verified Ingress Bootstrap, CG-1/CG-2, complete-data recovery,
Shadow, R2b, T4, T5, and broad fault-injection/endurance work are excluded.
If an oracle exposes an implementation defect, this lane records the failure
and stops for a separate Ryan correction grant.

## Authorized residual rows

| VERIFY row | Required evidence | Observed result | Disposition |
|---|---|---|---|
| V3f | `tests/test_t3_residual_closure.py::test_v3f_serialized_envelope_contains_hashes_but_no_secret_material` | Serialized envelope contains semantic hashes and no fixture secret/API-key material; parser and commitment round-trip passed | PASS candidate; repository row remains PENDING |
| V3h | `tests/test_atomic_files.py`, `tests/test_file_generation_durability.py`, `tests/test_writer_census.py`, `tests/test_governed_writer_gate.py`, `tests/test_governed_recovery_and_writers.py` | Hermetic writable-profile atomic publication, writer-lease ordering, and durable close controls: 24 passed | PASS candidate for exercised profile; power-loss/T5 work not claimed; repository row remains PENDING |
| V4m | `tests/test_t3_residual_closure.py::test_v4m_finalized_p1_p3_census_is_explicitly_revalidated_but_not_promoted`; census and writer inventory | P1/P2/P3 mutator inventory and no-bypass routing are inspectable, but universal final writer coverage and representative overlap proof are absent; census explicitly remains V4m PENDING | PENDING — T3 closure blocker |
| V8c | `tests/test_t3_residual_closure.py::test_v8c_same_root_does_not_create_corroboration_or_elevation` | Two distinct model derivations preserve one root lineage, distinct assertion IDs, and `untrusted` effective integrity | PASS candidate; repository row remains PENDING |
| V8e | `tests/test_t3_residual_closure.py::test_v8e_untrusted_retrieval_conversation_recapture_distill_chain` | Retrieval → reconstructed conversation → recapture → distill stages all remain `untrusted` and independently identified | PASS candidate; repository row remains PENDING |
| V8g | `tests/test_t3_residual_closure.py::test_v8g_provider_fallback_is_explicit_and_cannot_elevate` | Missing provider key resolves to explicit fallback; fail-on-fallback raises; fallback-derived ingest remains `untrusted` | PASS candidate; repository row remains PENDING |
| V9a | Controlled `pytest -q` under identical temporary HOME/config at baseline and candidate | Baseline: 6 failed / 1369 passed / 5 skipped / 3 warnings / 230 subtests; candidate: 6 failed / 1374 passed / 5 skipped / 3 warnings / 230 subtests; all six failure identities identical and no candidate-only failure | PENDING — clean full-suite oracle not satisfied; environment-matched limitation recorded |
| V9d | P1/P2/P3 continuity, Chroma, dedupe, retrieval, writer, and residual focused suites | 86 passed; no focused retrieval/dedupe regression; full-suite result remains baseline-matched but non-green | PENDING — exact closure oracle not satisfied |

All repository VERIFY rows remain formally `PENDING` throughout this lane.

## Validation record

- Residual controls: `pytest -q tests/test_t3_residual_closure.py` — 5 passed.
- Focused continuity/durability set: 86 passed in 8.00s; atomic/writer set: 24
  passed in 1.84s.
- Pylint regression gate: PASS, 491 findings and 253 fingerprints, with no
  new/increased findings versus `ci/pylint-baseline.json`; raw Pylint status 30
  was accepted by the repository gate. Pylint's cache warning was limited to
  the read-only `/home/lauer/.cache/pylint` path.
- `git diff --check`: clean.
- Controlled full-suite command, run independently at baseline and candidate:
  `HOME=/tmp/convmem-trapdoor-residual-home
  CONVMEM_CONFIG=/tmp/convmem-trapdoor-t3-residual.7QpIm2/config.example.toml
  pytest -q`.
- The six baseline-matched failure identities were the three restic/backup
  restore tests, the temporary-path substring decoy test, the golden eval, and
  the integrated restic restore test. No candidate-only failure occurred.
- No live corpus, Chroma, migration, Bootstrap, CG-1/CG-2, Shadow, R2b, T4,
  T5, or broad fault-injection operation was performed.

The evidence packet does not claim T3 closure. V4m, V9a, and V9d remain
unresolved closure blockers; the other five authorized rows have PASS
candidate evidence only. Repository VERIFY rows remain PENDING.

## Stop and handoff rule

Any implementation defect, architecture conflict, missing authority boundary,
or need to weaken an oracle stops this lane. The failure must be reported to
Ryan for a separately authorized correction; no repair is performed here.
