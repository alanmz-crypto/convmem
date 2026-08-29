# R2b v2 I1–I3 implementation evidence

**Arc:** R2b Capture Authorization  
**Granted base:** `c6e8b2b0293edf8b0faf29e9e393e69eca6ca494`  
**Status:** Implementation evidence only — NOT operational VERIFY

## V0 — scope / revision

| ID | Result | Evidence |
|---|---|---|
| V0d | PASS (implementation scope) | I1–I3 only; no live gate, packet, grant, or service control |
| V0e | PASS | No mutation of `2026-07-21-r2b-capture-01` or `2026-08-27-r2b-capture-02`; v1 validator unchanged |

## V1 — contract / state (I1)

| ID | Result | Evidence |
|---|---|---|
| V1a | PASS | `validate_r2b_v2_manifest_schema` requires `r2b_contract_version: 2` |
| V1b | PASS | Exact `service_policy` / `source_quiescence_policy` enforcement in `eval_corpus/r2b_v2/contract.py` |
| V1c | PASS | v2 validator delegates inherited v1 capture fields via `validate_r2b_manifest_schema` |
| V1d | PASS | `detect_contract_version` + `test_v1_manifest_not_upgraded` |
| V1e | PASS | `assert_no_ratified_duration_defaults`; concrete duration fields rejected on manifest |
| V1f | NOT RUN | Freshness at ACCEPT/bind/materialization is I4+ runtime |

## V2 — coverage (I3)

| ID | Result | Evidence |
|---|---|---|
| V2a | PASS | `build_static_route_inventory` binds `code_revision` + `inventory_digest` |
| V2b | PASS | Route table covers watch/F0, refine, monitor, manual, CG-2/D4, RA, export/processed/chroma |
| V2c | PASS | Per-route `gate_path` + `gate_protocol` in inventory |
| V2d | PASS | Exclusions require explicit route records; bypass injection test |
| V2e | PASS | `inspect_runtime_writers` binds PID/start/executable/entrypoint/revision/gate/surfaces |
| V2f | PASS | `CoverageProofResult.hold_classes` explicit empty-set report |
| V2g | PASS | HOLD on unattested/uninspectable/unknown signature (negative tests) |
| V2h | PASS | `test_gate_without_coverage_no_source_authority` |

## V3 — lease (I2)

| ID | Result | Evidence |
|---|---|---|
| V3a | NOT RUN | Preparation authority record is I4+ |
| V3b | NOT RUN | Full prohibited-operation runtime is I4+ |
| V3c | PASS | `R2bQuiescenceLease` binds run/grant/gate inode/protocol/PID/start/revision/digests/deadline |
| V3d | PASS | Authority digest, phase bounds, bound source paths on `_LeaseBindings` |
| V3e | PASS | Adversarial tests: forge, pickle, copy, bool, replay, extension, cross-run |
| V3f | PASS | Inode verify via `fstat`; lost ownership after release; alternate holder blocks acquire |

## V4–V8

NOT RUN except static prerequisites above. Missing operational evidence is NOT PASS.

## Mechanical gates (candidate tip)

- Focused pytest: `tests/test_r2b_v2_*.py` — PASS (32)
- Pylint regression (changed files): PASS, 0 new findings
- `git diff --check`: PASS
- `convmem doctor`: PASS (pre-existing warnings only)

**Note:** `test_shadow_writer_gate_c3` / `test_shadow_writer_coverage_scan` static scans fail locally when `.worktrees/` is present under the repo root; reproduced on clean `c6e8b2b` without R2b v2 changes.
