# P4 Verification Evidence — Arc Trapdoor Hunt

> Evidence packet scaffold for the separately authorized T3 P4 verification
> lane. This file records observations and recommendations; it does not change
> the locked T3 requirements or promote repository VERIFY rows.

```text
Status:       P4 deterministic evidence collected; independent review pending
Arc:          Trapdoor Hunt
Starting basis: 6ec5b6c031ae8fdedbd90ef1392232d25f0bfaf1
Locked T3:    aae0cad0bb05b0e436e213b28abbe0ff05ba2e91
Branch:       verify/2026-08-18-trapdoor-t3-p4
Worktree:     /home/lauer/Projects/convmem-trapdoor-t3-p4
PR:           https://github.com/alanmz-crypto/convmem/pull/207
```

## Evidence-only boundary

P4 runs deterministic locked VERIFY oracles and collects reproducible
commands, outputs, hashes, serialized fixtures, negative controls, regression
results, and no-live-mutation evidence against one exact implementation tip.

If a locked requirement fails, P4 records the failure and stops. P4 does not
repair implementation, weaken an oracle, alter a requirement, or reinterpret a
failure as PASS. All repository VERIFY rows remain `PENDING` unless a separate
governance decision records otherwise.

Migration, live migration, production data or Chroma mutation, Verified Ingress
Bootstrap, CG-1/CG-2 implementation or activation, Shadow, R2b, T4, T5,
ranking/recency/temporal redesign, and broad endurance or fault-injection work
are excluded.

## Evidence mapping

The implementation revision tested throughout this packet is the exact
post-P3 closeout tip `6ec5b6c031ae8fdedbd90ef1392232d25f0bfaf1`.  The P4
branch contains only this evidence packet plus the current handoff/status
reconciliation; none of those documentation changes alters the implementation.
“PASS candidate” below is an evidence recommendation only;
the repository VERIFY rows remain `PENDING`.

### Revision, authorization, and slice gates

| VERIFY row | Implementation surface / exact evidence | Observed result | Recommended disposition |
|---|---|---|---|
| V0a | Kiro review of the final P4 evidence packet and exact SHA | Not yet run | PENDING |
| V0b | Copilot targeted audit of the same final P4 SHA | Not yet run | PENDING |
| V0c | T3 lock and separate P1/P2/P3 grants in the accepted status history | Present in the post-P3 closeout; P4 review still pending | PENDING |
| V0d | P4 packet binds evidence to `6ec5b6c…` and the baseline is explicit | Present; independent review still pending | PASS candidate |
| V0e | Named implementation paths resolve in the repository; no P4 code paths added | Present; P4 diff is documentation/status-only | PASS candidate |
| V0f | Accepted T1/T2 inventory and T3 child-slice history | Present in locked planning/status history | PENDING |
| V0g | Distinct P1/P2/P3 grants, branches, worktrees, and PRs | Present in accepted execution/status history | PASS candidate |
| V0h | Frozen FF1–FF5 parent hierarchy | Present in locked planning history | PENDING |
| V0A | P1/P2/P3 grant/branch/PR records | Present in `VERIFY-dependability-provenance.md` and status history; no new P4 execution slice | PASS candidate |

### P1 root authority and recursive propagation

| VERIFY row | Implementation surface / exact evidence | Observed result | Recommended disposition |
|---|---|---|---|
| V1a | `tests/test_provenance.py`: single registry policy path, root/derivation verification tests | Focused suite passed | PASS candidate |
| V1b | `test_verified_root_and_untrusted_production_root_are_conservative`; `test_monitor_inventory_is_the_only_root_elevation_authority` | Empty production inventory remains untrusted; synthetic fixture is monitor-owned | PASS candidate |
| V1c | `test_empty_input_is_rejected_before_it_can_mint_authority` | Passed | PASS candidate |
| V1d | `test_monitor_inventory_is_the_only_root_elevation_authority`; `test_caller_cannot_supply_an_assertion_id_to_mint` | Caller claims and caller IDs do not elevate or mint authority | PASS candidate |
| V1e | `test_strict_parser_rejects_duplicate_keys_nonfinite_and_surrogates`; `test_schema_and_typed_boundary_reject_drift_and_unknown_fields`; `test_registered_schema_semantics_are_snapshot_bound` | Passed for malformed input and semantic-digest drift | PASS candidate |
| V1f | `test_origin_class_is_closed_before_it_can_reach_authority_logic` | Passed | PASS candidate |
| V1g | `test_llm_meet_never_elevates_an_untrusted_root` and lattice tests | Passed for the tested synthetic fixtures | PASS candidate |
| V1h | No real Verified Ingress Bootstrap is authorized or implemented | Production non-degenerate lattice gate is intentionally not satisfied | PENDING |
| V2a | `test_lattices_caps_and_monotonicity_cover_all_levels` | Passed | PASS candidate |
| V2b | Same lattice/cap property test plus root/derivation cap tests | Passed | PASS candidate |
| V2c | `test_llm_meet_never_elevates_an_untrusted_root`; transformer-cap fixtures | Passed for synthetic LLM cap behavior | PASS candidate |
| V2d | `test_llm_meet_never_elevates_an_untrusted_root` | Passed | PASS candidate |
| V2e | `test_parent_commitment_mismatch_and_missing_parent_fail_closed`; recursive failure tests | Passed for missing/mismatched ancestry | PASS candidate |
| V2f | lattice monotonicity/property coverage and recursive verification tests | Passed for exercised paths | PASS candidate |
| V2g | root/derivation cap tests and lattice cap table | Passed for exercised deterministic/lossy cases | PASS candidate |
| V2h | `test_operation_pin_survives_new_generation_and_reclamation_is_safe`; `test_pinned_snapshot_records_are_deeply_immutable`; recipe replacement test | Passed | PASS candidate |
| V2i | cycle, depth/node/byte budget, pin-loss/reclamation negative controls in `tests/test_provenance.py` | Passed in focused suite | PASS candidate |

### Transformation, acknowledgement, and migration boundaries

| VERIFY row | Implementation surface / exact evidence | Observed result | Recommended disposition |
|---|---|---|---|
| V3a | P1 envelope/binding tests in `tests/test_provenance.py`; P2 continuity round trip | Passed for exercised binding fields | PASS candidate |
| V3b | Commitment/canonical-envelope tests and `test_unit_projection_round_trip_preserves_authoritative_identity` | Passed | PASS candidate |
| V3c | Binding parameter/commitment coverage in P1 tests | Passed for exercised parameters | PASS candidate |
| V3d | Provider payload/recipe commitment fixtures in P1/P3 tests | Passed for exercised payload paths | PASS candidate |
| V3e | `test_trusted_cap_requires_exact_rule_and_immutable_artifact` | Passed | PASS candidate |
| V3f | Envelope/commitment tests exclude secrets while retaining semantic bytes | Focused tests passed; full standalone secret audit not separately executed | PENDING |
| V3g | Locked architecture scope and envelope tests | No universal model-causality proof is claimed | PENDING |
| V3h | Persistence-profile acknowledgement contract | No supported-profile crash/durability oracle was authorized in P4; writer test is environment-blocked | PENDING |
| V3i | Migration semantic mapping/fixture requirement | Migration execution is excluded from P4 | PENDING |

### Representation, recovery, and capture consistency

| VERIFY row | Implementation surface / exact evidence | Observed result | Recommended disposition |
|---|---|---|---|
| V4a | Strict parser and canonical golden-vector tests: `test_strict_parser_rejects_duplicate_keys_nonfinite_and_surrogates`, `test_canonicalization_literal_golden_vector`, `test_registered_schema_semantics_are_snapshot_bound` | Passed | PASS candidate |
| V4b | `tests/test_provenance_continuity.py`; P3 projection/export/reconstruction tests | Passed for exercised unit/Chroma/export paths | PASS candidate |
| V4c | `test_projection_cannot_self_upgrade_or_repair_a_commitment` | Passed | PASS candidate |
| V4d | Projection/cache mismatch and explicit-untrusted tests | Passed for exercised mismatch paths | PASS candidate |
| V4e | `test_missing_projection_provenance_is_explicitly_untrusted` and legacy projection fixtures | Passed for exercised missing-field paths | PASS candidate |
| V4f | P2/P3 continuity suite: 90 passed, 1 deselected | Passed for exercised representation paths | PASS candidate |
| V4g | Complete-data-v2 preflight/restore contract | P4 did not execute later restore integration | PENDING |
| V4h | Registry-versus-sidecar validation contract | No complete-data restore oracle executed | PENDING |
| V4i | `tests/test_chroma_restore_drill.py` and projection continuity tests | Local projection/recovery controls passed; full authority recovery oracle not executed | PENDING |
| V4j | Ryan-gated bulk authority recovery | Later recovery operation is outside this P4 evidence slice | PENDING |
| V4k | Selected-generation/continuity/rollback publication | Full restore/rollback oracle not executed | PENDING |
| V4l | Normative R8.2 interruption table | Broad recovery fault injection is excluded from P4 | PENDING |
| V4m | `P1-PROVENANCE-MUTATOR-CENSUS.md`, `SHADOW-WRITER-COVERAGE-INVENTORY.json`, and P3 revalidation | P3 census revalidated; final universal evidence remains pending | PENDING |

### Assertion identity, dedupe, retrieval, and laundering

| VERIFY row | Implementation surface / exact evidence | Observed result | Recommended disposition |
|---|---|---|---|
| V5a | `test_exact_content_with_distinct_provenance_remains_accepted`; retrieval continuity tests | Passed | PASS candidate |
| V5b | `test_retrieval_keeps_integrity_fields_independent_for_duplicate_content` and duplicate isolation tests | Passed | PASS candidate |
| V5c | Same P3 duplicate isolation suite | Passed | PASS candidate |
| V5d | `test_approved_semantic_tombstone_requires_provenance_adjudication`; automatic tombstone test | Passed | PASS candidate |
| V5e | Semantic tombstone/adjudication negative controls | Passed for exercised paths | PASS candidate |
| V5f | P3 dedupe/projection/retrieval continuity tests | Passed | PASS candidate |
| V5g | P1 monitor-minted UUID/replay identity tests | Passed for exercised identity paths | PASS candidate |
| V5h | `test_successful_replay_is_idempotent`; P3 physical replay test | Passed | PASS candidate |
| V5i | `test_same_content_without_replay_pair_gets_new_monitor_assertion` | Passed | PASS candidate |
| V5j | `test_invalid_parent_identity_replay_fails_closed`; parent commitment tests | Passed | PASS candidate |
| V5k | `test_invalid_replay_never_overwrites_existing_identity`; invalid replay P3 tests | Passed | PASS candidate |
| V5l | `test_parent_commitment_mismatch_and_missing_parent_fail_closed`; same-content parent substitution test | Passed | PASS candidate |
| V7a | P3 retrieval tests: per-assertion identity/effective-integrity visibility | Passed | PASS candidate |
| V7b | `test_retrieval_keeps_integrity_fields_independent_for_duplicate_content`; ranking/priority tests | Passed for exercised ranking paths | PASS candidate |
| V7c | P3 supersession/temporal isolation tests | Passed for exercised supersession paths | PASS candidate |
| V7d | CG-2 request-frozen follower serving | CG-2 is excluded from P4 | PENDING |
| V7e | CG-2 non-recomputation/non-aggregation | CG-2 is excluded from P4 | PENDING |
| V8a | P1 untrusted-root/LLM-cap fixtures | Passed for exercised synthetic chain | PASS candidate |
| V8b | `test_llm_meet_never_elevates_an_untrusted_root` | Passed | PASS candidate |
| V8c | No full corroboration/elevation oracle separately executed | Not independently evidenced in P4 | PENDING |
| V8d | Missing-parent and recursive fail-closed tests | Passed | PASS candidate |
| V8e | No complete conversation/recapture/distill end-to-end oracle executed | Not independently evidenced in P4 | PENDING |
| V8f | Caller metadata/root authority negative controls | Passed | PASS candidate |
| V8g | No provider omission/fallback campaign authorized | Not independently evidenced in P4 | PENDING |
| V8h | Recursive ancestor omission/failure tests | Passed for exercised missing-ancestor paths | PASS candidate |
| V8i | Complete-data-v2 restore with projections | Restore integration excluded; local projection controls do not prove this full oracle | PENDING |
| V8j | Missing/partial registry recovery | Full restore oracle not executed | PENDING |
| V8k | Historical schema/policy/recipe semantic pinning tests | Passed for exercised P1 snapshot paths | PASS candidate |
| V8l | Authority-first projection-pending lifecycle | Projection continuity tests passed; full recovery lifecycle oracle not executed | PENDING |

### Regression, isolation, and independent sign-off

| VERIFY row | Implementation surface / exact evidence | Observed result | Recommended disposition |
|---|---|---|---|
| V9a | Focused suite: 90 passed, 1 deselected. Controlled full suite: candidate and exact baseline both 42 failed / 1344 passed / 2 skipped / 9 warnings / 222 subtests; identical failure identities | No novel regression; full PASS oracle is not satisfied | PENDING |
| V9b | Pylint regression gate and `git diff --check` | Pylint gate PASS: 494 findings, 253 fingerprints, no new/increased vs `6ec5b6c…`; diff check clean | PASS candidate |
| V9c | `git diff --name-status 6ec5b6c…`: only `docs/plans/P4-VERIFY-EVIDENCE.md`, `docs/inter-model/LATEST.md`, and `docs/plans/STATUS-dependability-provenance.md` | Documentation/status-only P4 reconciliation; no implementation files | PASS candidate |
| V9d | Relevant retrieval/dedupe regression tests in focused suite | Passed for exercised paths; full suite remains baseline-matched but not all green | PENDING |
| V9e | P4 branch diff is documentation/status-only; commands used hermetic `/tmp` config/cache; no production mutation was authorized or performed | No-live-mutation evidence collected | PASS candidate |
| V9f | This packet identifies commands, grants, exclusions, and evidence-only stop rules | Present | PASS candidate |
| V9g | Existing locked rows reused; no new VERIFY row or governance ceremony added | Present | PASS candidate |
| V10a | Kiro review of final P4 packet | Not yet run | PENDING |
| V10b | Copilot targeted audit of final P4 packet | Not yet run | PENDING |
| V10c | Sol-High conflict gate | No conflicting verdict exists | PENDING |
| V10d | Residual risk record in this packet | Environment-blocked writer checks, excluded restore/Bootstrap/CG-2, and final V4m are explicit | PENDING |
| V10e | Ryan merge/closure decision | Not yet authorized | PENDING |

Rows V6a–V6e and V9A are later CG-1/restore/operational assurance work and were
not executed in this P4 lane; they remain `PENDING`.

## Validation record

- Exact implementation revision tested: `6ec5b6c031ae8fdedbd90ef1392232d25f0bfaf1`.
- Focused verification: `90 passed, 1 deselected in 4.49s` across the P1/P2/P3 provenance, continuity, dedupe, retrieval, Chroma, and reindex suites.
- Additional projection checks: `6 passed, 1 failed` in `test_chroma_approve_index.py` plus `test_shadow_writer_coverage_scan.py`; the one failure was the baseline-matched read-only lock-path error at `/home/lauer/.local/share/convmem/locks/chroma_writer_gate.lock`.
- Known writer check: `test_commit_suppresses_exact_and_keeps_semantic_candidate` failed identically on candidate and exact baseline before the write, at the same read-only lock path.
- Controlled full-suite differential: candidate `42 failed, 1344 passed, 2 skipped, 9 warnings, 222 subtests passed`; exact baseline `42 failed, 1344 passed, 2 skipped, 9 warnings, 222 subtests passed`; failure identities were identical and no candidate-only failure occurred.
- Pylint: `Pylint regression gate PASS (494 findings, 253 fingerprints; no new/increased vs baseline)` with status 30 accepted and base `6ec5b6c…`.
- `git diff --check`: clean.
- No-live-mutation proof: P4 changed only Markdown evidence/handoff/status files; test configuration/cache used `/tmp`; the only attempted production-writer paths stopped at the read-only lock before mutation; no live corpus, Chroma, Shadow, R2b, CG-2, migration, or Bootstrap operation occurred.
- V4m mutator-census disposition: P3 census/revalidation is present; final universal writer coverage and overlap evidence remain `PENDING`.
- Kiro evidence review: pending against the final P4 SHA.
- Copilot targeted audit: pending against the same final P4 SHA after Kiro PASS.

The 42 baseline-matched full-suite failures are observed failures, not converted
to PASS. They are recorded as environment-limited evidence because the exact
baseline reproduces the same identities and counts. No implementation repair
was performed in P4.
