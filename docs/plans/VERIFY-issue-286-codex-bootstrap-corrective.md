# [Arc Codex #286] Verification stub — existing Codex rollout bootstrap

**State:** T1 scoped mechanical **COMPLETE** (V0–V2 **PASS** under bwrap). V3–V8 **NOT RUN**. v2 live execution **closed**.
**Author:** Codex, 2026-10-18.
**Direction:** [architecture](ARCHITECTURE-issue-286-codex-bootstrap-corrective.md), Kiro PASS at `e0e91bd32f96bce1f8c109a84005ed547d8655ff`; Ryan approved direction in conversation.
**Tasks and contracts:** [execution plan](EXECUTION-issue-286-codex-bootstrap-corrective.md).
**Execution authority:** Ryan granted Cursor T1–T5 and hermetic verification after Kiro plan PASS at `9423900`; see the [Execute handoff](../inter-model/CODEX-2026-10-18-issue-286-codex-bootstrap-corrective-execute.md).
**Tested code SHA:** `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` (T1 implementation + contract + bwrap gate). **Documentation evidence tip:** `2654d71da5caf25413af2f728947083457913fc3`. **PR:** none authorized.
**Template:** [VERIFY-TEMPLATE.md](VERIFY-TEMPLATE.md), adapted as an unfilled check list.

## Consequence and scope

Cursor's later authorized work must prove that one exact Codex rollout can be
adopted with bounded paid attempts and recoverable source-only changes while
compatible unrelated writers continue. These proofs do not authorize a live
run. A1 stays parked, and A2 remains stopped.

Scope is the execution plan's T1–T5 only. No production paths, provider calls,
watcher controls, quarantine release, deployment, PR, or global restore belongs
to this mechanical verification. V0–V2 rows below are filled from hermetic Execute evidence. V3–V8 remain **NOT RUN** until dependent tasks land.

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
| V0c | T1 code baseline | PASS — includes `439b851` v2 grant/dry-run + later T1 contract/bwrap harness at `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` |
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
| `subject_tip_sha` | `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` |
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

**PASS (scoped, tested at `517d014a0be11c6d70c985aa35a8c3cbdac4fe71`).** Functional proofs executed inside the bwrap worker bundle (`test_t1_and_v1_regressions_in_bwrap`: **25 passed**, exit 0). Gate parent: `tests/test_issue_286_codex_bootstrap_hermetic_gate.py`.

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

**Not claimed tested at T1 (honest gaps):**

| Item | Status |
|------|--------|
| Per-check isolated proofs for admission checks 1, 3, 4 (format/basename/admitted-after) as separate named rows | **Partial** — covered indirectly via predicate/blocker tests; no dedicated per-check catalog beyond rows above |
| Rejected history / cross-format / alias grant corpora | **NOT RUN** — no dedicated negative corpus in bundle |
| Descriptor digest equality across grant, prepared cache, transaction, checkpoint, receipts | **Deferred T2/T4** — not built yet |
| State-directory convergence under live coordinator paths | **Deferred T2** |

```bash
# At 517d014 — already executed; do not treat re-run as new evidence
# Parent: tests/test_issue_286_codex_bootstrap_hermetic_gate.py::test_t1_and_v1_regressions_in_bwrap
# Worker argv ends with: pytest -q <ISOLATED_PYTEST_TARGETS>
# Observed: 25 passed, exit 0
```

## V2 — Read-only preflight (T1)

**PASS (scoped, same `517d014` bwrap bundle).**

| ID | T1 obligation | Test node / oracle | Result |
|----|---------------|-------------------|--------|
| V2a | Dry-run creates no state/processed/chroma writes | `test_issue_286_codex_bootstrap_v2_t1.py::test_dry_run_no_writes` (mtime before/after on state, processed, chroma) | PASS |
| V2b | Dry-run packet `ready=True` on admitted synthetic fixture | same test (`assert packet["ready"] is True`) | PASS |
| V2c | Format-bound vs Kiro-default state IDs in packet | same test (`source_state_id` ≠ `kiro_default_state_id`) | PASS |
| V2d | Proposed chunk count only (no execution) | `test_preflight_ready_for_bootstrap_required` (`proposed_chunk_count` ≥ 1, `blockers` empty) | PASS |
| V2e | Provider/embedding HTTP attempts | No transport intercept at T1; dry-run/preflight path uses validators + metadata reads only — **0 provider calls by construction** (not independently counted) | PASS (design-bound) |
| V2f | No lock-file / coordinator / journal construction in dry-run | Implied by V2a immutability oracle; no dedicated lock-path negative | **Partial** — mtime oracle only |

**Deferred:** cross-artifact immutability of descriptor digests on prepared/transaction surfaces — **T2/T4**.

```bash
# Dry-run immutability: included in 25-test bwrap bundle (test_dry_run_no_writes)
# Provider call count: not instrumented; reliance on read-only code path at T1 scope
```


## V3 — Authority crash matrix (T2)

**NOT RUN.** Concurrent claims; reservation with consumed initial invocation
but no mirror/transaction; identical-grant recovery; corrupted/rolled-back
authority; terminal receipt/release windows; ordinal 3 denied. Record every
durable boundary and both sides, with independent authority/count observations.

## V4 — Provider permits and caps (T2)

**NOT RUN.** Permit fsync before send; retry/lost-response accounting; preserved
cumulative cap; prepared reuse; provider-binding/no-fallback checks; Ollama
observation; nested outer/operation permit composition and either-gate denial.
Production guard composition is a separate operational gate, not inferred from
a fake outer-permit implementation.

## V5 — Complete writer mediation (T3)

**NOT RUN.** Fill the execution plan §5 inventory with exact entrypoints,
preparation and commit checks, scope/locks, tests and results. Prove same-source
races in both orders, disjoint progress, pending reservation after death,
unscoped maintenance refusal, protected retry/authority cleanup, bounded waits,
and no paid calls under C1. Missing coverage is FAIL.

## V6 — Watcher/CLI deferral (T3)

**NOT RUN.** Typed signal/exit mapping; deferred path requeue/backoff; unchanged
retry/quarantine state; no false success; malformed/mismatched signal refusal;
terminal-authority race; ordinary unreserved `bootstrap_required` still follows
the existing refusal path. Test actual subprocess and parent handling. Existing
quarantine remains intact.

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

- Exact Cursor T1–T5 and hermetic verification authorization: **GRANTED; T1 scoped mechanical COMPLETE; T2–T5 NOT STARTED**.
- Kiro execution-plan review: **PASS at `942390001bca407c1c28e9972c443ee7612e1c1b`**, written verdict supplied by Ryan; precision notes incorporated in the Execute handoff.
- Later PR/review/merge and deployment authority: **PENDING**.
- Outer-budget enforcement, compatible writer rollout, health diagnosis and
  fresh baseline, verified backups/source disposition, refreshed numeric A1
  grants: **PENDING** under execution plan §7.
- A1 live execution: **PARKED / NOT AUTHORIZED**. A2: **STOPPED**.

## Evidence log (fill after Execute)

| Date | SHA role | Command | Exit | Result | Notes |
|------|----------|---------|------|--------|-------|
| 2026-10-18 | `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` | `python3 -m pytest -q tests/test_issue_286_codex_bootstrap_hermetic_gate.py` | 0 | PASS | 4 tests; external bwrap net+fs |
| 2026-10-18 | `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` | bwrap worker pytest bundle | 0 | PASS | 25 passed (T1 contract + v1 regressions) |
| 2026-10-18 | `5d5ec91` / `45b07d6` | prior in-process hook gate | — | **invalid** | withdrawn — not external enforcement |
| 2026-10-18 | `439b851` | ad hoc pytest without bwrap | — | **not hermetic** | implementation only |

**TL;DR:** [Arc Codex] T1 V0–V2 PASS at tested code `517d014a0be11c6d70c985aa35a8c3cbdac4fe71` with bwrap boundary. V3–V8 NOT RUN. Documentation tip `2654d71da5caf25413af2f728947083457913fc3`.

<!-- src: ./VERIFY-TEMPLATE.md — evidence and review-gate structure -->
<!-- ref: ./EXECUTION-issue-286-codex-bootstrap-corrective.md, ./ARCHITECTURE-issue-286-codex-bootstrap-corrective.md — scoped contracts -->
