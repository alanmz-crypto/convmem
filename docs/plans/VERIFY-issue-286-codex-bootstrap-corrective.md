# [Arc Codex #286] Verification stub — existing Codex rollout bootstrap

**State:** T1 **COMPLETE** (V0–V2 at `ec11b10d31f6fc23e7cc859b47fe2e4e9f6a5eaa`). T2 **COMPLETE** (V3–V4 at `1dc1eff3dcfdae43e68624adc7f2749de1f377f1`; unconditional owner/source lock on all mutating authority APIs; no `CONVMEM_BOOTSTRAP_V2_ENFORCE_OWNER_LOCK`). V5–V8 **NOT RUN**. v2 live execution **closed**. `LIVE_READINESS=NO_GO`.
**Author:** Codex, 2026-10-18.
**Direction:** [architecture](ARCHITECTURE-issue-286-codex-bootstrap-corrective.md), Kiro PASS at `e0e91bd32f96bce1f8c109a84005ed547d8655ff`; Ryan approved direction in conversation.
**Tasks and contracts:** [execution plan](EXECUTION-issue-286-codex-bootstrap-corrective.md).
**Execution authority:** Ryan granted Cursor T1–T5 and hermetic verification after Kiro plan PASS at `9423900`; see the [Execute handoff](../inter-model/CODEX-2026-10-18-issue-286-codex-bootstrap-corrective-execute.md).
**Tested code SHA:** `1dc1eff3dcfdae43e68624adc7f2749de1f377f1` (T2 complete: owner lock + V3/V4 bwrap bundle). **Documentation evidence tip:** docs commit on branch. **PR:** none authorized.
**Template:** [VERIFY-TEMPLATE.md](VERIFY-TEMPLATE.md), adapted as an unfilled check list.

## Consequence and scope

Cursor's later authorized work must prove that one exact Codex rollout can be
adopted with bounded paid attempts and recoverable source-only changes while
compatible unrelated writers continue. These proofs do not authorize a live
run. A1 stays parked, and A2 remains stopped.

Scope is the execution plan's T1–T5 only. No production paths, provider calls,
watcher controls, quarantine release, deployment, PR, or global restore belongs
to this mechanical verification. V0–V4 rows below are filled from hermetic Execute evidence. V5–V6 **PASS** (hermetic bwrap at T3 tip). V7–V8 **NOT RUN** (T4–T5).

## Verification design

- **Independent oracle:** parent-owned authoritative-file/foreign-byte snapshots,
  expected format/path hashes, intercepted transport counts, and externally
  controlled process barriers. Receipts are compared to the oracle.
- **Failure injection:** kill before/after each fsync/atomic publication and
  coordinator transition; fail fsync/replace; force lock races and timeouts;
  interleave foreign writes between initial attempt and recovery.
- **Negative controls:** wrong Kiro state identity; third invocation; missing
  permit-before-send; missing legacy commit check; exit-91 deferral; stale
  processed restore; substituted rollback authority; foreign-line normalization.
- **Dual paths:** exact bootstrap/identical-grant recovery; direct index and
  watcher subprocess/parent; legacy and incremental; Chroma and sidecars;
  owner, disjoint writer, unscoped writer, and incompatible writer.

## V0 — Authority, baseline, isolation, and review inputs

**PASS (external bwrap boundary).** Prior evidence rows that relied on in-process `install_network_denial()` hooks (`5d5ec91`, `45b07d6`) are **withdrawn** — they do not satisfy execution plan §6.

| ID | Check | Result |
|----|-------|--------|
| V0a | Ryan Execute grant (T1–T5 + hermetic verification) | PASS — execute handoff on branch |
| V0b | Reviewed execution plan SHA | PASS — `942390001bca407c1c28e9972c443ee7612e1c1b` |
| V0c | T1 code baseline | PASS — includes `439b851` v2 grant/dry-run + later T1 contract/bwrap harness at `ec11b10d31f6fc23e7cc859b47fe2e4e9f6a5eaa` |
| V0d | External network enforcement | PASS — `bwrap --unshare-net`; parent loopback positive control; dual AF_INET probe artifacts written **inside** bwrap both `connect_failed` (`tests/test_issue_286_codex_bootstrap_hermetic_gate.py::test_external_network_namespace_denied`) |
| V0e | External filesystem enforcement | PASS — narrow production-path `ro-bind` masks + scratch bind; capability probe (`test_external_filesystem_masks_production_paths`) |
| V0f | Worker probe without Python network monkeypatch | PASS — `boundary-probe` uses real `socket.connect`; errno recorded (`test_worker_boundary_probe_without_python_network_hooks`) |
| V0g | Temporary HOME/config/data + synthesis log redirect | PASS — `sanitized_worker_env()` + worker sets `ingest._SYNTHESIS_FAIL_LOG` under isolation root before pytest |
| V0h | Host bwrap availability | PASS — `bwrap` + user-ns probe available on runner |

Execute fields (no PR-native review yet):

| Field | Value |
|-------|-------|
| `gate_applicability` | `pending` |
| `reason` | No PR authorized |
| `subject_tip_sha` | `ec11b10d31f6fc23e7cc859b47fe2e4e9f6a5eaa` |
| `bugbot_reviewed_sha` | `n/a` |
| `result` | `n/a` |
| `finding_disposition` | `none` |
| `authority_reference` | Ryan grant — CODEX-2026-10-18 execute handoff |

```bash
cd /home/lauer/.local/share/convmem/worktrees/fix-2026-10-18-issue-286-codex-bootstrap
git checkout 517d014a0be11c6d70c985aa35a8c3cbdac4fe71
python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py
# exit 0; 4 passed (requires host bwrap + user namespaces)
```

## V1 — Format, grant, and v1 compatibility (T1)

**PASS (scoped, tested at `ec11b10d31f6fc23e7cc859b47fe2e4e9f6a5eaa`).** Functional proofs executed inside the bwrap worker bundle (`test_t1_and_v1_regressions_in_bwrap`: **38 passed**, exit 0). Gate parent: `tests/test_issue_286_codex_bootstrap_hermetic_gate.py`.

| ID | T1 obligation | Test node(s) | Result |
|----|---------------|--------------|--------|
| V1a | v2 field set + operation/grant hash domains | `test_issue_286_codex_bootstrap_v2_t1.py::test_v2_hash_vectors_independent_oracle` | PASS |
| V1b | Kiro-default `source_state_id` negative control | `::test_v2_rejects_kiro_default_state_id` | PASS |
| V1c | v1 grant parse/hash unchanged | `::test_v1_grant_parse_unchanged` | PASS |
| V1d | v1 strict grant shape/hash | `test_incremental_jsonl_bootstrap_command.py` (3 tests in bundle) | PASS |
| V1e | Provider binding (paid transport) | `test_incremental_jsonl_bootstrap_safety.py::test_paid_transport_disables_automatic_redirects` | PASS |
| V1f | One-recovery invocation journal | `::test_invocation_journal_allows_exactly_one_recovery` | PASS |
| V1g | Predecessor-preserving supersession | `test_incremental_jsonl_bootstrap_supersession.py::test_admissible_supersession_archives_exact_bytes_and_preserves_evidence` | PASS |
| V1h | Admission check 2 (outside sessions root) | `test_issue_286_codex_bootstrap_v2_t1_contract.py::test_admission_predicate_rejects_outside_sessions_root` | PASS |
| V1i | Admission checks via preflight blocker | `::test_preflight_codex_admission_rejected_blocker` | PASS |
| V1j | Admission / identity check 5 (session meta) | `::test_preflight_session_identity_check_5` | PASS |
| V1k | Wrong-format source refused at validation | `::test_preflight_admission_rejected_outside_root` (expects `BootstrapGrantError`) | PASS |
| V1l | Complete-line / prefix binding | `::test_preflight_prefix_mismatch` | PASS |
| V1m | Chunk cap | `::test_preflight_chunk_cap_exceeded` | PASS |
| V1n | Device/inode ownership binding | `::test_validate_rejects_inode_mismatch` | PASS |
| V1o | `max_source_bytes` ceiling | `::test_validate_rejects_source_over_max_bytes` | PASS |
| V1p | Strict grant version/fields/types | `::test_validate_rejects_extra_field`, `::test_validate_rejects_wrong_grant_version`, `::test_validate_rejects_v2_supersession_document` | PASS |
| V1q | Checkpoint / transaction / retry / supersession artifacts | `::test_preflight_checkpoint_and_transaction_refused`, `::test_preflight_retry_state_refused`, `::test_preflight_supersession_evidence_refused` | PASS |
| V1r | Ready preflight for `bootstrap_required` fixture | `::test_preflight_ready_for_bootstrap_required` | PASS |

**Canonical synthetic v2 hash oracle** (independent worker `hash-oracle` at `517d014` gate; metadata digests only — no transcript content):

| Field | Value |
|-------|-------|
| `operation_id` | `72ed0df0e35939ad0e8f9446505821ff520d4b3d81267175f106eacae8ab209f` |
| `grant_fingerprint_v2` | `d4cc0d72de7c0817350f5ea8c437fa8ad553cb7ca4b7078a0589ebcbcd73d8e0` |
| `source_state_id` (format-bound) | `92a0cc170c15b58240963d3e7d9abc27e2432966246da9f230484665198520d9` |
| `kiro_default_state_id` (negative reference) | `141a770cbd3ee9a3f167ee5e839956e8f57788468c91034fc2c29110d26cf39c` |

**Remaining T1 deferrals (honest):**

| Item | Status |
|------|--------|
| Descriptor digest equality across grant, prepared cache, transaction, checkpoint, receipts | **Deferred T2/T4** — cross-artifact surfaces not built at T1 |
| Live coordinator construction / prepared-transaction integration | **Deferred T2/T4** — T1 proves pure state-id + `coordinator_state_dir` convergence only |

**V1 gate catalog (admission 1/3/4, alias, cross-format, strict types, symlink, state dir)** — `tests/test_issue_286_codex_bootstrap_v2_t1_gate.py` (13 tests in bwrap bundle): check 1 `::test_admission_check_1_rejects_wrong_detected_format`; check 3 `::test_admission_check_3_rejects_invalid_rollout_basename`; check 4 `::test_admission_check_4_rejects_before_admitted_after`; alias `::test_admission_rejects_duplicate_session_prefix_alias`; cross-format `::test_v2_validate_rejects_cross_format_kiro_source`; checkpoint history `::test_v2_preflight_rejects_invalid_checkpoint_history`; bool-as-int `::test_validate_rejects_bool_masquerading_as_int`, `::test_validate_rejects_grant_version_bool`; descriptor `::test_validate_rejects_descriptor_digest_mismatch`; symlink `::test_validate_rejects_symlink_source`; state convergence `::test_state_directory_matches_coordinator_derivation`. | **PASS** |

```bash
# At 517d014 — already executed; do not treat re-run as new evidence
# Parent: tests/test_issue_286_codex_bootstrap_hermetic_gate.py::test_t1_and_v1_regressions_in_bwrap
# Worker argv ends with: pytest -q <ISOLATED_PYTEST_TARGETS>
# Observed: 38 passed, exit 0
```

## V2 — Read-only preflight (T1)

**PASS (scoped, same `517d014` bwrap bundle).**

| ID | T1 obligation | Test node / oracle | Result |
|----|---------------|-------------------|--------|
| V2a | Dry-run creates no state/processed/chroma writes | `test_issue_286_codex_bootstrap_v2_t1.py::test_dry_run_no_writes` (mtime before/after on state, processed, chroma) | PASS |
| V2b | Dry-run packet `ready=True` on admitted synthetic fixture | same test (`assert packet["ready"] is True`) | PASS |
| V2c | Format-bound vs Kiro-default state IDs in packet | same test (`source_state_id` ≠ `kiro_default_state_id`) | PASS |
| V2d | Proposed chunk count only (no execution) | `test_preflight_ready_for_bootstrap_required` (`proposed_chunk_count` ≥ 1, `blockers` empty) | PASS |
| V2e | Provider/embedding HTTP attempts | `test_issue_286_codex_bootstrap_v2_t1_gate.py::test_dry_run_audit_ready_path_zero_calls_and_no_mutations` + refusal path (`CONVMEM_BOOTSTRAP_V2_DRY_RUN_AUDIT=1`; `llm._permit_provider_http_attempt` counter) | PASS |
| V2f | No coordinator / journal / surface mkdir in dry-run | Same gate audit tests; byte oracle via `bootstrap_codex_v2_dry_run_audit.snapshot_surface` (processed/chroma/export/locks/state); blocks coordinator/journal `__init__` and guarded `Path.mkdir` on mutation surfaces | PASS |

**Deferred:** cross-artifact immutability of descriptor digests on prepared/transaction surfaces — **T2/T4**.

```bash
# Dry-run immutability + audit: 38-test T1 bwrap bundle (ec11b10 evidence SHA)
# V4 permit-before-send: test_issue_286_codex_bootstrap_v2_t2_accounting.py at d446122
```


## V3 — Authority crash matrix (T2)

**PASS (exhaustive publication barriers; tested inside bwrap at T2 code SHA recorded in evidence log).** Parent gate: `tests/test_issue_286_codex_bootstrap_hermetic_gate.py::test_t2_authority_accounting_and_crash_matrix_in_bwrap` — **87 passed**, exit 0. Oracle: `tests/fixtures/issue_286_t2_parent_oracle.py` (`snapshot_tree`, `count_oracle_rows`, `load_authority` ordinal/reservation fields).

**Unconditional owner lock (production; no opt-in env):**

| ID | Obligation | Test node | Oracle |
|----|------------|-----------|--------|
| V3-own-neg | Mutating authority without owner context refused before durable change | `test_issue_286_codex_bootstrap_v2_t2_contract_evidence.py::test_owner_lock_required_without_context` | `OwnerLockRequired`; authority file absent |
| V3-own-pos | Verified owner + source lock allows claim | `::test_owner_lock_positive_allows_claim` | authority durable |
| V3-own-acct | Accounting lock does not substitute for owner claim | `::test_accounting_lock_separate_from_owner_claim` | refusal without owner |
| V3-c1-deny | No provider permit consume under C1/Chroma session | `::test_provider_permit_refused_under_c1_session` | `provider_permit_under_c1_session` |


| Publication site | Kind | Parent SIGKILL node | Parent action | Post-kill oracle |
|------------------|------|---------------------|---------------|------------------|
| initial_authority.before_tmp_write | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[initial_authority.before_tmp_write]` | SIGKILL at ack-barrier; killed=True | no durable authority |
| initial_authority.before_tmp_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[initial_authority.before_tmp_fsync]` | SIGKILL at ack-barrier; killed=True | no durable authority |
| initial_authority.before_replace | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[initial_authority.before_replace]` | SIGKILL at ack-barrier; killed=True | no durable authority |
| initial_authority.after_replace | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[initial_authority.after_replace]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| initial_authority.before_dir_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[initial_authority.before_dir_fsync]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| initial_authority.after_dir_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[initial_authority.after_dir_fsync]` | SIGKILL at ack-barrier; killed=True | load_authority durable; ordinal per site |
| recovery_authority.before_tmp_write | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[recovery_authority.before_tmp_write]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| recovery_authority.before_tmp_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[recovery_authority.before_tmp_fsync]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| recovery_authority.before_replace | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[recovery_authority.before_replace]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| recovery_authority.after_replace | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[recovery_authority.after_replace]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| recovery_authority.before_dir_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[recovery_authority.before_dir_fsync]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| recovery_authority.after_dir_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[recovery_authority.after_dir_fsync]` | SIGKILL at ack-barrier; killed=True | load_authority durable; ordinal per site |
| progress_authority.before_tmp_write | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[progress_authority.before_tmp_write]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| progress_authority.before_tmp_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[progress_authority.before_tmp_fsync]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| progress_authority.before_replace | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[progress_authority.before_replace]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| progress_authority.after_replace | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[progress_authority.after_replace]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| progress_authority.before_dir_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[progress_authority.before_dir_fsync]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| progress_authority.after_dir_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[progress_authority.after_dir_fsync]` | SIGKILL at ack-barrier; killed=True | load_authority durable; ordinal per site |
| terminal_receipt.before_tmp_write | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_receipt.before_tmp_write]` | SIGKILL at ack-barrier; killed=True | receipt/authority per stage; terminal test preserves active reservation |
| terminal_receipt.before_tmp_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_receipt.before_tmp_fsync]` | SIGKILL at ack-barrier; killed=True | receipt/authority per stage; terminal test preserves active reservation |
| terminal_receipt.before_replace | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_receipt.before_replace]` | SIGKILL at ack-barrier; killed=True | receipt/authority per stage; terminal test preserves active reservation |
| terminal_receipt.after_replace | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_receipt.after_replace]` | SIGKILL at ack-barrier; killed=True | receipt/authority per stage; terminal test preserves active reservation |
| terminal_receipt.before_dir_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_receipt.before_dir_fsync]` | SIGKILL at ack-barrier; killed=True | receipt/authority per stage; terminal test preserves active reservation |
| terminal_receipt.after_dir_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_receipt.after_dir_fsync]` | SIGKILL at ack-barrier; killed=True | receipt file durable; reservation_active may stay True if killed before terminal_authority |
| terminal_authority.before_tmp_write | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_authority.before_tmp_write]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| terminal_authority.before_tmp_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_authority.before_tmp_fsync]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| terminal_authority.before_replace | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_authority.before_replace]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| terminal_authority.after_replace | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_authority.after_replace]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| terminal_authority.before_dir_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_authority.before_dir_fsync]` | SIGKILL at ack-barrier; killed=True | authority bytes + snapshot_tree |
| terminal_authority.after_dir_fsync | atomic | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[terminal_authority.after_dir_fsync]` | SIGKILL at ack-barrier; killed=True | load_authority durable; ordinal per site |
| journal_mirror.before_append | append | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[journal_mirror.before_append]` | SIGKILL at ack-barrier; killed=True | mirror row count per durability stage |
| journal_mirror.before_file_fsync | append | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[journal_mirror.before_file_fsync]` | SIGKILL at ack-barrier; killed=True | mirror row count per durability stage |
| journal_mirror.before_dir_fsync | append | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[journal_mirror.before_dir_fsync]` | SIGKILL at ack-barrier; killed=True | mirror row count per durability stage |
| journal_mirror.after_dir_fsync | append | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[journal_mirror.after_dir_fsync]` | SIGKILL at ack-barrier; killed=True | invocations.jsonl row count==1 |
| v2_permit.before_append | append | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[v2_permit.before_append]` | SIGKILL at ack-barrier; killed=True | permit row count per stage |
| v2_permit.before_file_fsync | append | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[v2_permit.before_file_fsync]` | SIGKILL at ack-barrier; killed=True | permit row count per stage |
| v2_permit.before_dir_fsync | append | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[v2_permit.before_dir_fsync]` | SIGKILL at ack-barrier; killed=True | permit row count per stage |
| v2_permit.after_dir_fsync | append | `test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py::test_parent_sigkill_at_publication_stage[v2_permit.after_dir_fsync]` | SIGKILL at ack-barrier; killed=True | v2_provider_permits.jsonl row count==1 |

Additional V3 nodes (non-parametrized):

| ID | Obligation | Test node | Oracle |
|----|------------|-----------|--------|
| V3-auth | Initial/recovery/terminal/progress protocol | `tests/test_issue_286_codex_bootstrap_v2_t2_authority.py` (11 tests) | authority bytes + refusals |
| V3-crash | In-process `_exit(91)` hooks | `tests/test_issue_286_codex_bootstrap_v2_t2_crash_matrix.py` (4 tests) | ordinal + reservation |
| V3-inject | Injected fsync/replace failures | `test_injected_publication_failure_matrix[…]` (4 cases), `test_injected_replace_fail_leaves_no_durable_authority`, `test_injected_fsync_fail_before_authority_dir` | no durable / tmp ambiguity |
| V3-ambig | Temp/journal ambiguity | `test_ambiguous_authority_temp_blocks_initial`, `test_orphan_journal_blocks_initial` | blockers |
| V3-ord3 | Third invocation denied | `test_parent_kill_ordinal3_child_exits_nonzero` | ordinal stays 2 |
| V3-term | Receipt-before-terminal window | `test_terminal_receipt_before_release_parent_kill_preserves_active_reservation` | reservation_active True |
| V3-chroma | No Chroma on claim | `test_authority_claim_does_not_mutate_chroma` | chroma snapshot unchanged |

```bash
cd /home/lauer/.local/share/convmem/worktrees/fix-2026-10-18-issue-286-codex-bootstrap
python3 -m pytest -q tests/test_issue_286_codex_bootstrap_v2_t2_process_kill_matrix.py
python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py::test_t2_authority_accounting_and_crash_matrix_in_bwrap
# exit 0; 87 passed in bwrap worker
```

```bash
python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py
# exit 0; 5 passed (3 boundary + T1 bundle 38 + T2 bundle 87)
```

## V4 — Provider permits and caps (T2)

**PASS (same bwrap T2 bundle).** `lifetime_paid_cap == max_provider_http_attempts` (no `max_attempts * (1+recovery)` multiplier). Recovery adds per-ordinal bucket only; cumulative lifetime does not reset.

| ID | Obligation | Test node | Oracle |
|----|------------|-----------|--------|
| V4a | Permit-before-send | `test_issue_286_codex_bootstrap_v2_t2_accounting.py::test_permit_before_send_blocks_transport` | intercepted POST count==1 |
| V4b | Composed nested guards | `::test_composed_outer_and_operation_guards_both_execute`, `::test_operation_guard_refusal_blocks_inner` | call order + exhaustion |
| V4c | Outer denial before ledger | `::test_outer_refusal_blocks_before_operation_counter` | permit rows==0 |
| V4d | Per-ordinal bucket + lifetime cap | `::test_recovery_ordinal_uses_separate_permit_bucket`, `::test_cumulative_lifetime_across_recovery_without_reset` | permit rows + exhaustion |
| V4e | Lost response still consumes | `::test_lost_response_still_counts_without_usage` | exhausted after 1 |
| V4f | Restart preserves ledger | `::test_ledger_survives_process_restart` | cumulative==1 |
| V4g | Ollama embed cap-exempt | `::test_ollama_embed_cap_exempt_observed` | permitted==0 observed==2 |
| V4h | Corrupt permit journal | `::test_corrupt_permit_journal_refuses_consume` | BootstrapGrantError |
| V4i | Broken permit-order control | `::test_broken_permit_order_negative_control` | AssertionError |
| V4j | Provider binding (no fallback) | `test_issue_286_codex_bootstrap_v2_t2_contract_evidence.py::test_provider_binding_rejects_model_mismatch` | binding_mismatch |
| V4k | Prepared reuse (no second permit) | `::test_prepared_reuse_does_not_append_second_permit` | permit count stable |
| V4l | Lifetime cap equals grant max | `::test_lifetime_cap_equals_grant_max_not_multiplied` | cap==max_attempts |
| V4m | Recovery does not reset cumulative | `::test_recovery_does_not_reset_cumulative_paid_allowance` | exhausted after lifetime spent |
| V4n | v1 journal default lifetime parity | `::test_v1_journal_default_lifetime_matches_v2_ledger` | equal caps |
| V4o | No Chroma during permit append | `::test_no_chroma_mutation_during_permit_append` | chroma snapshot |
| V4p | Journal ahead / rolled-back revision | `::test_journal_ahead_of_authority_blocks_fresh_claim`, `::test_rolled_back_authority_revision_rejected` | corruption detectors |
| V4c1 | Permit refused under C1 session | `test_issue_286_codex_bootstrap_v2_t2_contract_evidence.py::test_provider_permit_refused_under_c1_session` | no permit row |
| V4q | v1 paid-cap regression (T1 bundle) | `test_incremental_jsonl_bootstrap_safety.py` in T1 bwrap at `ec11b10d31f6fc23e7cc859b47fe2e4e9f6a5eaa` | not re-run at T2-only worker |

```bash
# V4 accounting/contract nodes run inside the bwrap T2 worker bundle only.
```


**PASS (same `d446122772839f25cc30847b653cb9282b79004d` bwrap bundle).** Transport interception uses fake endpoints only; production outer budget remains `outer_budget_unverified` (§7).

| ID | Obligation | Test node | rc | Oracle |
|----|------------|-----------|-----|--------|
| V4a | Permit-before-send (intercepted POST count) | `test_issue_286_codex_bootstrap_v2_t2_accounting.py::test_permit_before_send_blocks_transport` | 0 | transports==1 |
| V4b | Composed outer+operation guards | `::test_composed_outer_and_operation_guards_both_execute` | 0 | both called |
| V4c | Outer denial before operation ledger | `::test_outer_refusal_blocks_before_operation_counter` | 0 | permits rows==0 |
| V4d | Recovery ordinal permit bucket + lifetime cumulative | `::test_recovery_ordinal_uses_separate_permit_bucket`, `::test_cumulative_lifetime_across_recovery_without_reset` | 0 | ledger file rows |
| V4e | Lost-response / retry consumes permit | `::test_lost_response_still_counts_without_usage` | 0 | exhausted after 1 |
| V4f | Process restart preserves permits | `::test_ledger_survives_process_restart` | 0 | cumulative==1 |
| V4g | Ollama embed cap-exempt observations | `::test_ollama_embed_cap_exempt_observed` | 0 | permitted==0, observed==2 |
| V4h | Operation guard refusal | `::test_operation_guard_refusal_blocks_inner` | 0 | exhausted |
| V4i | Corrupt permit journal | `::test_corrupt_permit_journal_refuses_consume` | 0 | BootstrapGrantError |
| V4j | Broken permit-order negative control | `::test_broken_permit_order_negative_control` | 0 | AssertionError expected |
| V4k | v1 paid-cap regression (bundle) | `test_incremental_jsonl_bootstrap_safety.py` nodes in T1 bwrap bundle at `ec11b10d31f6fc23e7cc859b47fe2e4e9f6a5eaa` | 0 | not re-run at `d446122772839f25cc30847b653cb9282b79004d` unless full parent file |

```bash
git checkout d446122772839f25cc30847b653cb9282b79004d
python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py::test_t2_authority_accounting_and_crash_matrix_in_bwrap
# includes all V4 rows above
```

## V5 — Complete writer mediation (T3)

**PASS (hermetic, external bwrap).** Subject SHA: fill at commit (`git rev-parse HEAD` on
`fix/2026-10-18-issue-286-codex-bootstrap`). v2 live execution remains **closed**; rows
mark **hermetic** vs **live NO_GO**.

**Gate command (parent oracle):** `python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py`
→ **exit 0**, **6 passed** (T1+T2+T3 bwrap bundles).

**T3 worker bundle (independent count):** bwrap worker pytest on
`tests/test_issue_286_codex_bootstrap_v2_t3_*.py` → **20 passed**, **exit 0**.

### §5 writer inventory (execution plan)

| Entrypoint / boundary | Source scope | Prep enforcement | Mutation guard / lock | Positive test | Negative test | Live compat |
|---|---|---|---|---|---|---|
| `claim_initial_authority` | v2 grant source state dir | exclusive prep lease try-only under owner lock | owner lock + authority lock | `test_initial_claim_under_prep_lease`, `test_race_legacy_prep_blocks_exclusive_claim` | `test_race_legacy_prep_before_bootstrap_claim_parent_oracle` (busy once) | NO_GO (execute closed) |
| Legacy provider prep → commit (`ingest._process_file_chunks`, `_commit_chunk_to_stores`, `_prune_completed_reindex`) | `jsonl_codex_rollout` path key | `legacy_shared_preparation_lease` through provider work | `recheck_reservation_before_commit` under source/C1 locks; `production_writer_boundary` | race matrix + ingest wiring | `test_race_reservation_before_stale_legacy_recheck`, subprocess `recheck_commit` child | hermetic PASS |
| `mutate_processed` / `commit_processed_index_entry` | `affected_sources` tuple | n/a (leaf) | processed lock + `enforce_writer_scope` | `test_disjoint_source_processed_while_reservation_active` | stale recheck without `acting_operation_id` | hermetic PASS |
| `IncrementalJsonlCoordinator._commit_generation` / `_publish_processed` | `bootstrap_operation_id` when set | owner prep at claim (exclusive) | `recheck` with `acting_operation_id`; source/C1 locks unchanged | owner processed commit via `acting_operation_id` | coordinator recheck path (stale legacy) | NO_GO until execute authorized |
| `production_writer_boundary` / `enforce_writer_scope` | per-call `affected_sources` or `maintenance_unscoped` | n/a | defers on active foreign reservation | `test_active_reservation_defers_ordinary_writer` | maintenance defer when reservations active (shared rule) | hermetic PASS |
| `chroma_write_store._IndexWriteGuardedChromaStore` | `inspect_chroma_mutation_scope` | n/a | scope → `enforce_writer_scope` before mutate | chroma guard unit coverage via T3 defer tests | unknown-scope → maintenance defer under reservation | hermetic PASS |
| `source_purge.execute` | purge targets | n/a | `production_writer_boundary` | shared deny rule (boundary) | defer under active reservation | hermetic PASS |
| `refine.write`, `propose_decision.write`, `conflict_events`, `incremental_jsonl_canary` | entrypoint-scoped / maintenance | n/a | shared `production_writer_boundary` | shared boundary defer tests | same | hermetic PASS (boundary only; business logic untouched) |
| Export / dedupe / compaction (`ingest.export`, `ingest_dedupe`, `_compact_units_export_after_index`) | source or maintenance | n/a | boundary + maintenance defer | ingest export boundary wiring | maintenance defer under reservation | hermetic PASS (partial; compaction defer via `maintenance_unscoped`) |
| Recovery / cutover callers | existing shared stores | n/a | refuse via shared boundary when reservation conflicts | boundary deny proof | not expanded (recovery arc policy unchanged) | NO_GO |

**Race / disjoint evidence (parent oracle):** `test_issue_286_codex_bootstrap_v2_t3_race_matrix.py`
(both orders, disjoint processed preservation). **State root:** `test_resolve_incremental_state_root_from_config_path`
uses redirected `config.toml` under bwrap (not isolation-only).

**Negative controls (must fail if broken):** exit 91 mapping control
(`test_broken_exit91_mapping_control_would_quarantine`); malformed deferral;
stale recheck (`test_race_reservation_before_stale_legacy_recheck`).

## V6 — Watcher/CLI deferral (T3)

**PASS (hermetic).** Same subject SHA as V5.

| Check | Evidence |
|---|---|
| Exit **93** disjoint from 0/1/91/timeout/native | `test_exit93_disjoint_from_timeout_and_native_parsing`, `test_exit_code_disjoint_from_91_and_native` |
| Child stderr marker → parent requeue, no breaker/refusal | `test_subprocess_exit93_requeues_without_breaker_side_effects`, `test_watch_coordination_deferral_requeues_without_refusal` |
| `_flush_path_subprocess` → `_record_ready_path_failure` chain | `test_flush_path_subprocess_exit93_maps_to_requeue` (mocked `Popen`, real handler) |
| `_process_ready_path` retains scheduler event on deferral | `test_process_ready_path_defer_does_not_forget_scheduler` |
| Ordinary `bootstrap_required` still exit **91** quarantine | `test_broken_exit91_mapping_control_would_quarantine` |
| Malformed / path mismatch deferral → failure | `test_malformed_deferral_is_failure_not_requeue`, `test_path_mismatch_refused` |

**Not run:** live watcher parent deployment compatibility (§7 gate).

## V7 — Prefix, commit, and recovery (T4)

**NOT RUN.** Selected-prefix-only chunks after append; replacement/truncation
refusal; real temporary Chroma both-collection crash points; original rollback
hash retained; checkpoint/follower/receipt recovery without new transforms;
source-only processed merge and byte-exact preservation of foreign export/dedupe
records, including malformed/blank lines and concurrent foreign updates.

## V8 — Integrated results and independent sign-off (T5)

**NOT RUN.** Record exact commands/exit codes/counts and evidence paths for V1–V7,
boundary-probe and negative-control failures, applicable static checks, v1
regressions, and full command-to-receipt/command-to-watcher integration.

Report separately: hermetic mechanical result, independent Kiro verdict at the
implementation subject SHA, pending PR-native review, and live readiness.
Applicable skipped proofs cannot yield mechanical PASS. Verifier performs no
corrections or cleanup. Review findings go through the established lane route.

## Ryan gates — not mechanical PASS rows

- Exact Cursor T1–T5 and hermetic verification authorization: **GRANTED; T1 COMPLETE (`ec11b10`); T2 COMPLETE (`1dc1eff`); T3 COMPLETE (V5–V6 hermetic at branch tip); T4–T5 NOT STARTED**.
- Kiro execution-plan review: **PASS at `942390001bca407c1c28e9972c443ee7612e1c1b`**, written verdict supplied by Ryan; precision notes incorporated in the Execute handoff.
- Later PR/review/merge and deployment authority: **PENDING**.
- Outer-budget enforcement, compatible writer rollout, health diagnosis and
  fresh baseline, verified backups/source disposition, refreshed numeric A1
  grants: **PENDING** under execution plan §7.
- A1 live execution: **PARKED / NOT AUTHORIZED**. A2: **STOPPED**.

## Evidence log (fill after Execute)

| Date | SHA role | Command | Exit | Result | Notes |
|------|----------|---------|------|--------|-------|
| 2026-10-18 | `ec11b10d31f6fc23e7cc859b47fe2e4e9f6a5eaa` | `python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py` | 0 | PASS | 4 tests; external bwrap net+fs |
| 2026-10-18 | `ec11b10d31f6fc23e7cc859b47fe2e4e9f6a5eaa` | bwrap worker pytest bundle | 0 | PASS | 38 passed (T1 contract + v1 regressions) |
| 2026-10-18 | `5d5ec91` / `45b07d6` | prior in-process hook gate | — | **invalid** | withdrawn — not external enforcement |
| 2026-10-18 | `439b851` | ad hoc pytest without bwrap | — | **not hermetic** | implementation only |
| 2026-10-18 | T3 tip | `python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py` | 0 | PASS | 6 parent tests; T3 worker 20 passed in bwrap |

**TL;DR:** [Arc Codex] T1 `ec11b10`; T2 `1dc1eff`; T3 **COMPLETE** (V5–V6 bwrap). T4–T5 NOT RUN.

<!-- src: ./VERIFY-TEMPLATE.md — evidence and review-gate structure -->
<!-- ref: ./EXECUTION-issue-286-codex-bootstrap-corrective.md, ./ARCHITECTURE-issue-286-codex-bootstrap-corrective.md — scoped contracts -->
