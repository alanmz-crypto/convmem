# [Arc Codex #286] Verification stub — existing Codex rollout bootstrap

**T3 hermetic evidence status (2026-10-18):** Prior PASS rows through `1723dd0` / `4a99eba` (**55** inner tests) are **WITHDRAWN — host isolation leak**. Isolation fix **committed+pushed** at tested code `0b68bad9c43f6c182d8efac0cf02b65170f01913`; guarded rerun4: **guard 15** + **inner T3 subset 54** PASS; **full T3 INCOMPLETE** (mandatory V6 production-route proof **NOT RUN**).

**State:** T1 **COMPLETE** (`ec11b10d`). T2 **COMPLETE** (`1dc1eff`). **T3 INCOMPLETE** (V5 subset green at `0b68bad9c43f6c182d8efac0cf02b65170f01913`; **V6 mandatory proof NOT RUN**). V7–V8 **NOT RUN** (T4–T5 parked). v2 live execution **closed**. `LIVE_READINESS=NO_GO`.
**Author:** Codex, 2026-10-18.
**Direction:** [architecture](ARCHITECTURE-issue-286-codex-bootstrap-corrective.md), Kiro PASS at `e0e91bd32f96bce1f8c109a84005ed547d8655ff`; Ryan approved direction in conversation.
**Tasks and contracts:** [execution plan](EXECUTION-issue-286-codex-bootstrap-corrective.md).
**Execution authority:** Ryan granted Cursor T1–T5 and hermetic verification after Kiro plan PASS at `9423900`; see the [Execute handoff](../inter-model/CODEX-2026-10-18-issue-286-codex-bootstrap-corrective-execute.md).
**Tested code SHA:** `0b68bad9c43f6c182d8efac0cf02b65170f01913` (isolation + guarded T3 subset rerun). **Documentation SHA:** `92f55610c5a60c43241b34b038ad51bf4e29fb51` (docs-only reconciliation; distinct from tested code above).
**Template:** [VERIFY-TEMPLATE.md](VERIFY-TEMPLATE.md), adapted as an unfilled check list.

## Consequence and scope

Cursor's later authorized work must prove that one exact Codex rollout can be
adopted with bounded paid attempts and recoverable source-only changes while
compatible unrelated writers continue. These proofs do not authorize a live
run. A1 stays parked, and A2 remains stopped.

Scope is the execution plan's T1–T5 only. No production paths, provider calls,
watcher controls, quarantine release, deployment, PR, or global restore belongs
to this mechanical verification. V0–V4 from earlier hermetic evidence. **V5 subset PASS** (54 inner tests at `0b68bad9c43f6c182d8efac0cf02b65170f01913`). **V6 production-route proof NOT RUN** (mandatory gap). V7–V8 **NOT RUN** (T4–T5 parked).

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

**PASS (subset, guarded rerun4).** Subject SHA: `0b68bad9c43f6c182d8efac0cf02b65170f01913`. v2 live execution remains **closed**; mechanical hermetic PASS is separate from live compatibility (**NO_GO**).

**Guard suite (outer bwrap, separate from inner worker):** `python3 scripts/issue_286_guarded_pytest_launcher.py -q tests/test_issue_286_host_isolation_guard.py` → **15 passed**.

**Inner T3 worker oracle (nested bwrap):** `python3 scripts/issue_286_guarded_pytest_launcher.py -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py::test_t3_writer_mediation_in_bwrap` → **54 passed**, 0 failed, 0 skipped (`ISOLATED_PYTEST_TARGETS_T3`; guard excluded).

**Not verified in rerun4:** full parent file `tests/test_issue_286_codex_bootstrap_hermetic_gate.py` (six parent tests including V0–V2 bundles).

### §5 writer inventory (execution plan)

| Entrypoint / boundary | Scope | Prep | Guard before first mutation | Positive test node | Negative test node | Live compat |
|---|---|---|---|---|---|---|
| `claim_initial_authority` | v2 grant source state dir | exclusive prep lease | owner lock + authority lock | `test_initial_claim_under_prep_lease` | `test_race_legacy_prep_before_bootstrap_claim_parent_oracle` | NO_GO |
| Legacy ingest commit (`_commit_chunk_to_stores`, `_prune_completed_reindex`) | `path_key` | `legacy_shared_preparation_lease` | `recheck_reservation_before_commit` + `production_writer_boundary` | `test_disjoint_source_chroma_and_processed_while_reservation_active`, `test_disjoint_export_append_and_compaction_after_owner_commit` | `test_stale_legacy_commit_chunk_to_stores_refused`, `test_race_reservation_before_stale_legacy_recheck` | NO_GO |
| `mutate_processed` / `commit_processed_index_entry` / exclusion undo | `affected_sources` | n/a | processed lock + `enforce_writer_scope` + recheck | `test_owner_bound_identity_allows_same_source_processed`, `test_disjoint_processed_merge_while_other_reserved` | `test_exclude_processed_on_reserved_source_defers`, `test_undo_exclude_on_reserved_source_defers`, `test_processed_preimage_restore_on_reserved_source_defers`, `test_raw_save_processed_refused_outside_mutate` | NO_GO |
| `IncrementalJsonlCoordinator` rollback processed (`_restore_processed`) | `path_key` | owner prep at claim | `mutate_processed` + recheck | `test_owner_bound_identity_allows_same_source_processed` | `test_processed_preimage_restore_on_reserved_source_defers` | NO_GO |
| `production_writer_boundary` / `enforce_writer_scope` | per-call scope | n/a | scope at boundary entry | `test_active_reservation_defers_ordinary_writer` | `test_chroma_no_source_mutation_defers_under_reservation` | hermetic PASS |
| Chroma dispatch (`production_chroma_write_session`, `_IndexWriteGuardedChromaStore`) | per-mutation `inspect_chroma_mutation_scope` | index write flock | `enforce_writer_scope` on each mutate | `test_chroma_scoped_disjoint_mutation_while_other_reserved`, `test_nested_chroma_sessions_reenter_safely` | `test_chroma_mutation_without_source_defers_under_reservation` | hermetic PASS |
| `inter_model_index` (`production_chroma_write_session`) | `affected_sources=(path_key,)` | source flock + index flock | session scope + per-mutation inspect | `test_chroma_scoped_disjoint_mutation_while_other_reserved` (entrypoint `inter_model_index`) | scoped defer on reserved path via chroma guard | NO_GO |
| `repository_knowledge_index` / `repository_knowledge_retire` | `affected_sources=(path_key,)` | source flock + index flock | session scope + per-mutation inspect | disjoint chroma/oracle tests (repo index shares chroma guard class) | `test_repository_knowledge_scoped_session_defers_on_reserved_path` | NO_GO |
| `refine.write` / `convmem.add` / `convmem.forget` / `convmem.verify` / `convmem.monitor` | chroma metadata `source_path` or maintenance | index write flock | chroma inspect → scoped or maintenance defer | `test_nested_chroma_sessions_reenter_safely` (`refine.write`) | `test_propose_decision_entrypoint_unscoped_chroma_defers`, `test_monitor_entrypoint_unscoped_chroma_defers`, `test_chroma_mutation_without_source_defers_under_reservation` (`convmem.add` class) | NO_GO |
| `propose_decision.write` / `conflict_events.governed` | data-root flock inside boundary | n/a | boundary + governed chroma writes | governed path shares chroma dispatch proofs | `test_propose_decision_entrypoint_unscoped_chroma_defers` | NO_GO |
| `incremental_jsonl_canary` / `incremental_jsonl.apply` | grant-listed lease | prep at claim | `production_writer_boundary` + coordinator locks | owner/coordinator tests | stale recheck / broken recheck control (`test_broken_recheck_control_allows_stale_chroma_write`) | NO_GO |
| `ingest.export` / `_compact_units_export_after_index` | maintenance unscoped | n/a | `production_writer_boundary(maintenance_unscoped=True)` | `test_disjoint_export_append_and_compaction_after_owner_commit` (`export_compaction_deferred` metadata, bytes preserved) | `test_export_compaction_defers_under_active_reservation` | hermetic PASS |
| `ingest_dedupe.persist` | `affected_sources` from batch / caller | index write flock inside | scoped or maintenance boundary | `test_persist_ingest_dedupe_disjoint_append_without_reservation` | `test_persist_ingest_dedupe_defers_under_reservation` | hermetic PASS |
| `clear_incremental_retry_states_for_source` / `clear_all_incremental_retry_states` | per-source / global | n/a | refuse while foreign reservation | coordinator success path clears under owner (oracles) | `test_clear_retry_state_for_source_defers_under_reservation`, `test_clear_all_retry_states_defers_when_reservation_active` | NO_GO |
| `source_purge.execute` | purge targets | source flock | mark_purge_exclusion before index_write_flock/Chroma | stage-2 purge util disjoint path | test_source_purge_defers_at_processed_exclusion_before_chroma | NO_GO |

| recovery/cutover: open_production_recovery_write_store (propose_decision) | governed paths | shared lease | production_writer_boundary + scoped chroma | propose_decision chroma proofs | test_propose_decision_entrypoint_unscoped_chroma_defers | NO_GO |
| IncrementalJsonlCoordinator._cleanup | tx/rollback/snapshot only | _transition | disjoint from bootstrap_v2_authority.json | test_incremental_cleanup_preserves_v2_authority_artifact | n/a | hermetic PASS |
| enforce_incremental_retry_gates / live retry admission | path_key | n/a | check before reserve | test_enforce_incremental_retry_gates_check_before_reserve | clear_* defer tests | NO_GO |
| migration_required refusal | stale checkpoint | coordinator locks | _unchanged_prereturn_refusal before migration (T4 executes migration) | incremental_jsonl migration_required path | authority file disjoint | NO_GO |
**Race / disjoint oracles:** `test_issue_286_codex_bootstrap_v2_t3_race_matrix.py`, `test_issue_286_codex_bootstrap_v2_t3_oracles.py`, `test_issue_286_codex_bootstrap_v2_t3_inventory.py`.

**Negative controls:** `test_broken_recheck_control_allows_stale_chroma_write`, `test_broken_exit91_mapping_control_would_quarantine`, malformed deferral tests in watch integration.

## V6 — Watcher/CLI deferral (T3)

**Deferral revision binding:** v2 authority revision increases by exactly one per `publish_authority_progress` and `publish_terminal_authority` (see `bootstrap_codex_v2_authority.py`); there is no one-step cap. Parent accepts child deferral when `operation_id` matches and `1 <= signal.authority_revision <= authority.revision`; future revisions refused.


**PASS (deferral subset only, hermetic).** Subject SHA: `0b68bad9c43f6c182d8efac0cf02b65170f01913`. Deferral/coordination nodes in the inner **54** bundle above.

| Check | Evidence test node |
|---|---|
| Exit **93** disjoint from 0/1/91/timeout/native | `test_exit93_disjoint_from_timeout_and_native_parsing`, `test_exit_code_disjoint_from_91_and_native` |
| Real CLI child → `_flush_path_subprocess` → parent requeue | `test_real_cli_child_coordination_deferral_exit93`, `test_flush_path_subprocess_real_child_then_parent_requeue` |
| `_process_ready_path` bounded backoff / no immediate relaunch | `test_process_ready_path_real_subprocess_defer_scheduler_backoff`, `test_process_ready_path_defer_does_not_forget_scheduler` |
| Valid deferral after terminal → requeue; future revision → forget | `test_real_child_deferral_after_multi_progress_terminal_still_requeues`, `test_terminal_accepts_deferral_revision_behind_multi_progress`, `test_real_child_deferral_after_terminal_authority_still_requeues`; `test_fabricated_deferral_revision_mismatch_after_terminal_refuses_requeue` |
| Pre-existing refusal quarantine skips spawn | `test_preexisting_refusal_quarantine_skips_real_spawn` |
| Ordinary unreserved `bootstrap_required` → exit **91** + breaker | `test_real_cli_bootstrap_required_exit91_unreserved_route` in `tests/test_issue_286_codex_bootstrap_v2_t3_v6_production_route_gap.py` — **NOT RUN** (excluded; mandatory V6 harness gap; **ROOT retained**) |
| Malformed / path / op / revision mismatch | `test_malformed_deferral_is_failure_not_requeue`, `test_path_mismatch_refused` |
| Exit 91 negative control (no false quarantine) | `test_broken_exit91_mapping_control_would_quarantine` |

**Not run:** live watcher deployment compatibility (§7 gate).

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

- Exact Cursor T1–T5 and hermetic verification authorization: **GRANTED; T1 COMPLETE (`ec11b10`); T2 COMPLETE (`1dc1eff`); T3 INCOMPLETE (V6 mandatory proof NOT RUN; V5 subset 54+guard 15 at `0b68bad9c43f6c182d8efac0cf02b65170f01913`); T4–T5 PARKED**.
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
| 2026-10-18 | T3 reconciliation tip (superseded) | `python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py` | 0 | PASS | 6 parent tests; T3 worker **31 passed** (superseded) in bwrap |

| 2026-10-18 | `0b68bad9c43f6c182d8efac0cf02b65170f01913` (tested code) | `python3 scripts/issue_286_guarded_pytest_launcher.py` guard 15 + `::test_t3_writer_mediation_in_bwrap` inner 54 | 0 | PASS (subset) | Guard outer; inner T3 subset only; V6 module NOT RUN |

**TL;DR:** [Arc Codex] T1 `ec11b10`; T2 `1dc1eff`; T3 **INCOMPLETE** (V6 mandatory NOT RUN; V5 subset+guard PASS at `0b68bad9c43f6c182d8efac0cf02b65170f01913`). T4–T5 parked.

<!-- src: ./VERIFY-TEMPLATE.md — evidence and review-gate structure -->
<!-- ref: ./EXECUTION-issue-286-codex-bootstrap-corrective.md, ./ARCHITECTURE-issue-286-codex-bootstrap-corrective.md — scoped contracts -->


## V6 production-route CLI proof gap

`test_real_cli_bootstrap_required_exit91_unreserved_route` is **skipped** (not PASS) until a
faithful harness exists. Production `maybe_route_incremental` selects the isolated path when
`CONVMEM_INCREMENTAL_ROOT` is set; exit-91 live-route refusal requires the production branch
(`ROOT` unset). Keeping `ROOT` for isolation safety cannot simultaneously prove production-route
exit-91 without weakening production security or falsifying assertions. This is a **proof gap**,
not isolation success and not a new grant.

## Final guarded evidence (rerun4, metadata-only)

**Tested code SHA (implementation):** `0b68bad9c43f6c182d8efac0cf02b65170f01913` on `fix/2026-10-18-issue-286-codex-bootstrap` (pushed; HEAD matches origin).

**Entry (mandatory):** `python3 scripts/issue_286_guarded_pytest_launcher.py` — outer `bwrap` (`--ro-bind / /`, `--unshare-net`, scratch bind) then single-process capture/isolation before pytest. Unguarded host `pytest` on issue #286 paths **fail closed** (`issue_286_unguarded_pytest`).

### What ran (final rerun4)

| Layer | Command / node | Result |
|-------|----------------|--------|
| **Guard (outer only)** | `…/issue_286_guarded_pytest_launcher.py -q tests/test_issue_286_host_isolation_guard.py` | **15 passed** |
| **T3 inner subset (nested bwrap worker)** | `…/issue_286_guarded_pytest_launcher.py -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py::test_t3_writer_mediation_in_bwrap` | **54 passed**, 0 failed, 0 skipped (`ISOLATED_PYTEST_TARGETS_T3`; guard file excluded) |
| **V6 production-route module** | `tests/test_issue_286_codex_bootstrap_v2_t3_v6_production_route_gap.py` | **NOT RUN** (excluded from inner targets; mandatory proof gap while `CONVMEM_INCREMENTAL_ROOT` retained) |
| **Full parent hermetic gate (6 tests)** | `tests/test_issue_286_codex_bootstrap_hermetic_gate.py` (entire file) | **NOT RUN** in rerun4 — only the targeted T3 worker oracle above |

**Withdrawn:** prior T3 worker **55 passed** at `1723dd0` / `4a99eba` (**host isolation leak**); do not cite.

### Production metadata snapshots (rerun4 window ~12.31s)

| Artifact | Path |
|----------|------|
| Before | `/tmp/issue-286-rerun4-before.json` (`captured_ns`: `1792360071527129462`) |
| After | `/tmp/issue-286-rerun4-after.json` (`captured_ns`: `1792360083834667963`) |
| Coordinator baseline (reference) | `/tmp/issue-286-isolation-correction-before.json` |
| Prior runs (preserved) | `/tmp/issue-286-run-before.json`, `/tmp/issue-286-run-after.json`, `/tmp/issue-286-rerun3-before.json`, `/tmp/issue-286-rerun3-after.json` |

**Scope:** metadata only (config/synthesis file hashes+mtime; Codex session **path** inventory with inode/dev/size/mtime). **No** transcript body reads; **no** content/prefix proof.

| Field | Before → after (rerun4) |
|-------|-------------------------|
| `config.mtime_ns` | `1792355640024833560` → **equal** |
| `config.sha256` | `b9e06f1e9e5dc2e80f1ec01e2cedc63b59d90965d9757a8c15e2958d6d684721` → **equal** |
| `config.size` | `5240` → **equal** |
| `synthesis_failures.mtime_ns` | `1792355284777120051` → **equal** |
| `synthesis_failures.sha256` | `2e3e68a08436a96f02ab40966014777fc1d67c4d00e96c91e1cf41b111b79039` → **equal** |
| `synthesis_failures.size` | `636205` → **equal** |
| Session **unique** paths | **831** → **831** (identical set) |
| `sessions_metadata_sha256` | `212ed285526e28751dfe631d54bb39efa4ffc1449544c481e4ab1f0e3218d713` → **equal** |
| Added / removed / changed paths | **0 / 0 / 0** |

**Earlier counter corrections (not rerun4 drift):**

- Duplicate directory rows in a pre-fix snapshot script produced **933** inventory rows vs **831** unique paths (**102** duplicate dir entries); not live session growth.
- Coordinator metadata-only review (separate window) found **three** existing rollout paths with same inode/dev and increasing size/mtime while host `codex` (pid 5852) held writable fds — **not** claimed as full-session byte identity; rerun4 showed **no** path add/remove and **no** metadata row changes across the guarded window.

### T3 arc status

- **V5 writer-mediation subset (54 inner tests):** PASS at `0b68bad9c43f6c182d8efac0cf02b65170f01913` under guarded launcher.
- **V6 production-route exit-91 proof:** **mandatory, unresolved** — module **NOT RUN**; requires harness design with **ROOT retained** (no `CONVMEM_INCREMENTAL_ROOT` stripping).
- **Full T3 task:** **INCOMPLETE** until V6 is satisfied.
- **T4–T5:** parked (not started).

