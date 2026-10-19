# [Arc Codex #286] Kiro exact-revision implementation review — Kiro incremental indexing

**Reviewer:** Kiro, 2026-10-18. **Scope:** review-only; new branch from
`origin/main`; no PR; `.worktrees/runtime-main` and live config untouched.
**Target under review:** `fix/2026-10-18-issue-286-kiro-incremental` at
`c432408` (`c432408 fix: enforce durable Kiro paid-call budgets across retries`).
**Baseline:** `origin/main` `07117ed`.
**Binding:** my design-review conditions **C-KI1..C-KI6**
(`docs/inter-model/KIRO-2026-10-18-issue-286-kiro-incremental-review.md`).

## Verdict

- **Merge: PASS-with-conditions.** The implementation satisfies C-KI1, C-KI4,
  C-KI5, C-KI6 fully, and C-KI2/C-KI3 in mechanism and partial test coverage.
  Two conditions below (CX-A, CX-B) must be closed in the Execute PR; neither is
  a correctness defect, both are test-completeness gaps the design already named.
- **Stage 1 live spending: FAIL (not yet authorized).** This revision does not
  establish operational readiness and must not spend. `live_sources` is empty in
  the live config and there is no `kiro_session` table; the pending Codex
  `recovery_unproven` transaction `46313d43…` is still open per `doctor`. A
  separate exact packet with a no-other-writer window and a materialized cohort
  ledger is required before any paid run.

## Consequence for Ryan

Codex brought Kiro sessions onto the incremental v2 route exactly as the design
described, with no shortcuts. Admission is pure exact-source (a path must be in
`live_sources`); there is no time-derived selection anywhere, even disabled. New
paid Kiro work is fail-closed behind a durable, fsync'd cohort budget that counts
every provider HTTP attempt — including failed/retried ones — before dispatch,
and refuses if the budget is not fully configured. Nothing is enrolled or live.
The headline trade-off I confirmed at design time holds: every new Kiro session
must be manually enrolled before its first index or it falls to the legacy route.

## Verification I performed (independent, at `c432408`)

I checked out `c432408` in a throwaway worktree, read the implementation, and ran
the suites and the real CI pylint gate.

### Tests
- **Kiro #286 suites** (budget, routing, sidecar, watcher, codex-regression):
  **32 passed** in 4.5s — including the real `_deepseek_generate` retry probe,
  the two-process shared-cap test, and the SIGKILL-after-reserve test.
- **Incremental / canary / codex route / boundary** (40 files, the full #286 +
  incremental_jsonl + canary + codex-corrective scope):
  **285 passed** (part 1) + **227 passed** (part 2) = **512 passed**, 0 failures.
- The six host skips Claude reported are the Safe Harbor **T3/T4** modules, which
  abort collection without the launcher-isolation bootstrap (`require_t3_bootstrap`
  → `SystemExit(5)`); unrelated to this slice. This corroborates the
  "854 passed / 6 host skips" direction-level claim.

### CI pylint gate (independent)
- `pylint 4.0.6` / `astroid 4.0.4` (exact CI pin), full-repo report
  `pylint $(git ls-files "*.py")`, compared against committed
  `ci/pylint-baseline.json` via `scripts/pylint_regression_gate.py compare`.
- **Result: PASS** — 457 findings, 231 fingerprints, **no new/increased vs
  baseline**. (The STATUS doc text says 454; it was written at the `b131b0f`
  corrective-2 point before the last two commits. Fingerprint count 231 matches
  exactly and the gate is green — a documentation-count staleness, not a gate
  failure.)

## Focus areas (a)–(e)

### (a) Kiro identity change (raw bytes → semantic digest; v1 → v2) — PASS

- `adapters/kiro_session_jsonl.py` adds `semantic_session_meta_digest(session_id,
  workspace_directory)` over a canonical `{version, session_id,
  workspace_directory}` body, with the **raw-byte digest preserved** as evidence
  (`CompletePrefixView.session_meta_raw_digest`, carried through capture and
  commit snapshots in `incremental_jsonl.py`). This directly fixes the
  full-byte-hash `source_identity_changed` refusal I confirmed at design time,
  without the lazy "keep the raw digest" shortcut.
- `validated_kiro_session_identity` requires `id == sess_<uuid>` for live
  transcripts (`session_dir.name.startswith("sess_")` → mismatch raises); snapshot
  copies are allowed only when the id itself starts with `sess_`. **No snapshot
  directory-name fallback.** Malformed / mismatched / oversized metadata yields a
  `None` digest, and the coordinator refuses with `kiro_session_meta_missing`
  (both at capture and in `_live_route_refusal`) — **no provider call** on bad
  metadata.
- The contract bump `kiro-complete-prefix-v1 → v2` is applied consistently in
  `incremental_jsonl.ADAPTER_CONTRACT_VERSION` and `incremental_jsonl_formats._KIRO`.
- **Canary fixtures / T0 baseline refresh is deliberate and documented.**
  `tests/test_incremental_jsonl_canary_baseline.py` carries explicit per-file
  comment lines ("Kiro incremental v2 routing and policy guards", "fail-closed
  paid cohort accounting") for the refreshed `incremental_jsonl.py`, `ingest.py`,
  `watch.py` hashes and the new `watch_kiro_paths.py`. The canary helpers and
  `incremental_jsonl_canary_p2._descriptor_metadata_binding` now compute the
  `session.json` digest **semantically**, matching the coordinator — the fixtures
  are self-consistent with the new contract.
- **No live Kiro checkpoint is broken.** The live config has `live_sources = []`
  and no `[index.incremental_jsonl.kiro_session]` table; Kiro was never on the v2
  route (v2 was Codex-only at baseline). There is no existing live Kiro checkpoint
  for the v1→v2 bump to invalidate, and v1 checkpoints refuse `migration_required`
  rather than silently rebuilding.

### (b) C-KI4 / C-KI6 budget — PASS

`incremental_jsonl_cohort_budget.py` + the budget suite
(`tests/test_issue_286_kiro_incremental_budget.py`) prove every property:
- **Fail-closed without cohort fields.** `_consume_cohort_paid_attempt` raises
  `cohort_budget_required` if an admitted-Kiro deepseek call is attempted with no
  ledger; `_init_cohort_ledger` returns `None` unless all three cohort fields are
  present; `config._parse_kiro_session_policy_table` rejects partial cohort config
  (`kiro_cohort_incomplete`). The parametrized `test_missing_cohort_fields_*`
  (all 7 masks) asserts **no dispatch**.
- **fsync.** `_atomic_json` fsyncs the file, `os.replace`, then the parent dir;
  `test_atomic_reservation_fsyncs_file_before_replace_and_parent_after` pins the
  order `[file, replace, dir]` and `0o600` perms; `test_fsync_failure_prevents_dispatch`
  shows a durability failure blocks the HTTP call.
- **Lock order (budget lock inside source lock, released before HTTP, refused
  under Chroma write scope).** `test_real_run_holds_source_lock_and_unchanged_run_does_not_pay`
  + `_assert_dispatch_locks` prove the source flock is held and the budget flock
  is **free** during the POST, with chroma store depth 0.
  `test_write_scope_refuses_before_budget_lock_or_reservation` (index + chroma)
  proves `reject_provider_under_write_scope()` fires **before** the budget lock is
  acquired or any ledger file is written.
- **Two-process + SIGKILL.** `test_two_process_sources_share_cap_without_duplicate_reservations`
  (7 unique reservations, consumed=7, reserved=0) and
  `test_sigkill_after_reserve_still_counts_and_next_run_proceeds`
  (killed reservation leaves reserved=1 permanently → crash-conservative; next run
  still proceeds and the stale slot keeps counting against the cap).
- **CohortBudgetError subclasses ProviderAttemptBudgetExceeded — callers are
  correct.** The `ingest.py` summarize/distill retry loops check
  `isinstance(exc, ProviderAttemptBudgetExceeded): raise` as the **first** branch
  of their `except`, so a cohort refusal propagates out of the 3× retry loop
  immediately (no extra paid attempts) and is never mis-classified as a fatal HTTP
  status. `_build_frontier_with_accounting` catches `CohortBudgetError` specifically
  and re-raises as `IncrementalJsonlError`.
- **Operational note (not a defect):** a crashed reservation permanently consumes
  a cap slot (never reclaimed). This is intentionally conservative; an operation
  that accumulates crashes may need a fresh `cohort_operation_id`. Worth stating
  in the Stage 1 runbook.

### (c) hermetic_path_guard worktree exemption — PASS

`share_convmem_worktree_path` exempts only paths resolved under
`~/.local/share/convmem/worktrees` (returns `production_path_denied = False`),
after the `DEFAULT_BRIEF` check and with `is_relative_to` on resolved paths.
Narrowly scoped to the `worktrees` subdir; dev checkouts there are correctly not
treated as production corpus.

### (d) watcher re-reads settings on every file event — PASS (with a precise caveat)

`watch.queue_paths_from_fs_event(event, cfg=cfg)` now forwards every event through
`watch_kiro_paths.expand_selected_kiro_session_meta_paths`, which calls
`incremental_jsonl_settings(cfg)` **per event** (no stale cached settings object)
and maps a `session.json` event to the sibling `messages.jsonl` **only** when that
sibling is a `selected_kiro_path`. The sidecar is never indexed as a transcript
and watch roots are not broadened. **Caveat:** `cfg` is the dict captured once at
`run_watch` start; "re-reads settings" means it re-parses from that in-memory cfg
each event, **not** that it reloads the config file from disk. Picking up a newly
enrolled `live_source` requires a watcher restart — consistent with the design's
manual-enrollment + NO-GO deploy-window posture, so not a defect, but it should
not be read as live config hot-reload.

### (e) llm.py attempt-finished hook doesn't change non-Kiro calls — PASS

`_PROVIDER_ATTEMPT_FINISHED` defaults to `None`; `provider_http_accounting` is
entered only by `_build_frontier_with_accounting` (when `kiro_admitted_live`) and
the bootstrap script. `_finish_provider_http_attempt` fires inside `_post_deepseek`
on both success (after `raise_for_status`) and failure (except branch) — so it is
deepseek-only by construction and a no-op for every ordinary non-admitted call.

## Ruling against C-KI1..C-KI6

| Cond | Subject | Ruling | Evidence |
|---|---|---|---|
| **C-KI1** | No time-based/time-derived selection path | **PASS** | `grep` for `admitted_after`/`st_mtime`/`st_ctime`/`birth`/`createdAt`/`lastModifiedAt` across the Kiro admission, watch-path, budget, and adapter modules = **zero**. `kiro_admitted_live` is `production_boundary AND policy present AND format==jsonl_kiro_session AND path_key in live_sources`. `test_selected_kiro_requires_exact_live_source_not_time_admission` confirms a same-workspace, same-format sibling is **not** admitted. |
| **C-KI2** | Prove checkpoint-comparison refusal for unchanged prefix + changed effective sidecar field | **PASS-with-condition (CX-A)** | Mechanism correct: `_revalidate_live_prefix` uses `session_meta_digest_for_dir` (semantic) for the Kiro format and raises `source_identity_changed` on mismatch. Digest semantics proven at the adapter level (`test_..._sidecar.py`: title-only unchanged, workspace change differs). **Gap:** no single end-to-end coordinator test mutates `workspacePaths`/`id` between capture and revalidate on an unchanged JSONL prefix and asserts the coordinator refuses. The generic `source_identity_changed` continuity path is tested for Codex. |
| **C-KI3** | Kiro contract-version gates Kiro-only changes; Codex v2 cache keys/full-rebuild unchanged | **PASS-with-condition (CX-B)** | Axes are separated: `_active_resource_policy`, `_effective_allow_full_rebuild`, `_resource_policy_live` fork Codex vs Kiro cleanly; the descriptor is built from `format_spec.{format_id,adapter_contract_version}` so enrolling Kiro does **not** touch the Codex descriptor. **Gap:** `test_issue_286_kiro_incremental_codex_regression.py` only asserts a Codex descriptor *builds* with a digest — it does **not** pin the Codex digest to a pre-slice golden value, so it would not catch a shared-epoch bump that changed Codex keys. |
| **C-KI4** | Durable, crash-conservative pre-dispatch HTTP-attempt reservation before Stage 1; no soft counter | **PASS** | Reservation persisted (fsync file+dir) before the request returns; failed/crashed attempts count against the cap; config + runtime both refuse without the full cohort ledger. |
| **C-KI5** | Prefix change must not forgive terminal refusal / recovery-authority failure; woken ops keep journal | **PASS** | `watch_circuit_breaker.should_skip_refusal_quarantine` returns `True` (still quarantined) unconditionally for a terminal `rolled_back` refusal even when the prefix digest changes; only `wedged_incremental_transaction_*` is forgiven, and only on a differing digest. `test_kiro_prefix_change_does_not_clear_terminal_refusal_quarantine` pins this. |
| **C-KI6** | Cohort-ledger budget-lock ordering exactly; concurrent + crash tests | **PASS** | See (b). Budget lock inside source lock, released before HTTP, refused under Chroma write scope; two-process and SIGKILL tests present and green. |

## Conditions on the Execute PR (close before merge)

- **CX-A (closes C-KI2):** add one coordinator-level test that runs an admitted
  Kiro source to a committed checkpoint, mutates `workspacePaths` (or `id`) in the
  sibling `session.json` with the **JSONL prefix unchanged**, and asserts the next
  run refuses with `source_identity_changed` (not a silent zero-transform reuse).
  This is the exact case I flagged at design time as "the easiest to under-test"
  and the one that leaves reused historical rows carrying obsolete provenance if
  missed.
- **CX-B (closes C-KI3):** strengthen the Codex regression test to assert the
  Codex `jsonl_codex_rollout` descriptor **digest is byte-identical** to a pinned
  pre-slice value (golden), proving enrolling Kiro did not bump a shared epoch or
  change Codex v2 cache keys / full-rebuild behavior.

Neither condition requires code changes to the reviewed modules; both are
test-coverage additions the design already called for.

## What this review does NOT grant

- Not a Stage 1 live-spending grant. `live_sources` stays empty; the cohort ledger
  is not materialized; the no-other-writer window is not established.
- Does not clear or repair the pending Codex `recovery_unproven` transaction
  `46313d43…`; the implementation correctly leaves it with its owner.
- No Cursor rollout and no time-based admission are authorized by this slice.
- No savings percentage or payback date is accepted.

---

I finished: exact-revision implementation review of Kiro incremental indexing at `c432408`.
Next step:  Codex closes CX-A and CX-B (two test additions); then Ryan decides the Execute PR and, separately, a Stage 1 live-spend packet.
Next lane:  Codex (test additions), then Ryan (merge + Stage 1 authority).
See my work: `docs/inter-model/KIRO-2026-10-18-issue-286-kiro-incremental-exact-review.md`

<!-- src: ./KIRO-2026-10-18-issue-286-kiro-incremental-review.md — the binding design review (C-KI1..C-KI6) -->
<!-- src: fix/2026-10-18-issue-286-kiro-incremental @ c432408 — incremental_jsonl.py, incremental_jsonl_cohort_budget.py, incremental_jsonl_kiro_admission.py, adapters/kiro_session_jsonl.py, config.py, llm.py, ingest.py, watch.py, watch_kiro_paths.py, hermetic_path_guard.py and the issue_286 kiro tests, verified at this revision -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — Arc Codex routing status and future Execute evidence -->
