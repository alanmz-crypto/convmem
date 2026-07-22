# Claude review package — Knowledge-Unit Conflict Detection

**Date:** 2026-07-12 (America/Chicago) / 2026-07-13 UTC merge window  
**Main tip (arc complete):** `d8496c2` — merge of PR #5 (after #3 conflict-detection + #4 Gate 5)  
**Ask:** External review before calling the arc closed. This package answers the six prior-review points, ships concrete verify evidence (not self-report), and lists architecture-vs-execution shape changes.

## Pointers (SSoT on main)

| Artifact | Path |
|----------|------|
| Architecture | [`ARCHITECTURE-knowledge-unit-conflict-detection.md`](ARCHITECTURE-knowledge-unit-conflict-detection.md) |
| Execution | [`EXECUTION-knowledge-unit-conflict-detection.md`](EXECUTION-knowledge-unit-conflict-detection.md) |
| VERIFY (end-of-arc) | [`VERIFY-knowledge-unit-conflict-detection.md`](VERIFY-knowledge-unit-conflict-detection.md) |
| PRs | [#3](https://github.com/alanmz-crypto/convmem/pull/3), [#4](https://github.com/alanmz-crypto/convmem/pull/4), [#5](https://github.com/alanmz-crypto/convmem/pull/5) |

**Core code:** `ledger_content_hash.py`, `conflict_events.py`, `hash_schema_gate.py`, `propose_decision.py`, `observe.py`, `chroma_store.py` (`add_unit` replace gate), `ledger.py` (`ledger_unit_metadata`), `convmem.py` (`--recover`, `--rebase`).

---

## Six prior-review points — addressed vs declined

| # | Point | Disposition | Where / how |
|---|-------|-------------|-------------|
| 1 | **Hash canonicalization** | **Addressed** | `ledger_content_hash.py`: NFC strings, `sort_keys=True`, compact separators, schema v1 field set in `SEMANTIC_FIELDS`. `proposal_id` / author / timestamps excluded from hash. Tests: `tests/test_ledger_content_hash.py` (per-field flip + NFC + operational fields do not flip). |
| 2 | **Deleted-target handling** | **Addressed** | `validate_governed_apply`: `live_hash is None` → `target_missing`; `live_tombstoned` (`is_superseded` metadata) → `target_tombstoned`. Approve path uses `live_decision_state`. Rebase refuses tombstoned/missing targets. Tests: `test_validate_tombstone_and_create_collision`, `test_tombstoned_target_blocked_on_approve`. |
| 3 | **`stale_base` resolution path** | **Addressed** | Fail-closed on approve (`stale_base`). Resolution = **Gate 9** `rebase_proposal` / `convmem record --rebase`: new `proposal_id`, old → `SUPERSEDED` with `superseded_by_proposal_id`; new carries `rebases_proposal_id` + fresh `base_content_hash`. Old base never mutated. Test: `test_rebase_yields_new_id_and_superseded_link`. |
| 4 | **Conflict-check timing** | **Addressed (with note)** | Checks at **propose** (sibling / create collision) and again under flock in `_approve_unlocked` **before** `APPROVAL_STARTED`. Uncertain Chroma leave `APPROVAL_STARTED`; recovery via `--recover` matrix (no blind retry). **Note:** sibling set is ledger-target based, not a separate “session ID conflict group” structure — `active_conflicts` exists on the reducer for annotations; approve uses live unresolved targets. |
| 5 | **Legacy PENDING graduation trigger** | **Addressed** | Gate 5 (`hash_schema_gate.py`): `hash_schema_deploy.json` recorded once; warn until earlier of zero hashless targeted unresolved **or** 14d after deploy; then block approve of hashless targeted. One-shot `hash_schema_migration_report.json`. Wired on propose/approve/legacy import. Tests: `tests/test_hash_schema_gate.py`. |
| 6 | **Metadata-allowlist rationale** | **Addressed in code; rationale restated** | Semantic hash allowlist = meaning fields only (`SEMANTIC_FIELDS`). Chroma emit allowlist in `ledger_unit_metadata` **includes** operational `proposal_id` + `content_hash` + `summary` so recovery can read markers without putting them in the semantic hash. Rationale: apply marker must survive normalize/upsert; hash must not change when marker is stamped. |

**Nothing in the six was deliberately declined.** Item 4’s “session ID / pending conflict groups” wording from the review maps to **proposal_id + unresolved target sets + `active_conflicts` annotations**, not a separate session-scoped grouping object — if Claude meant a different structure, that would be a follow-on design ask.

---

## Concrete verification evidence (named cases)

Host run 2026-07-12 (worktree @ `d8496c2`), pytest **-v**:

```text
test_governed_apply_rejects_sibling_stale_and_create_collision PASSED
test_validate_tombstone_and_create_collision PASSED
test_reject_sibling_then_other_proceeds PASSED
test_tombstoned_target_blocked_on_approve PASSED
test_rebase_yields_new_id_and_superseded_link PASSED
test_barrier_race_second_writer_sees_stale_base PASSED
test_each_semantic_field_changes_hash PASSED
test_operational_fields_do_not_change_hash_and_unicode_is_nfc PASSED
test_is_hashless_targeted_only_for_updates_missing_hashes PASSED
test_schema_deploy_recorded_once_and_migration_report PASSED
test_warn_then_block_after_14_days PASSED
test_zero_hashless_graduates_to_block_for_new_hashless PASSED
test_hashed_targeted_never_blocked PASSED
============================== 13 passed ==============================
```

### In-process `validate_governed_apply` (same tip)

```text
stale_base: stale_base
sibling: pending_sibling
new_fact_skip_CAS_ok (no target, absent): None
new_fact_create_exists: create_target_exists
new_fact_no_stale_check (create never returns stale_base): None
```

Interpretation for Claude’s three asks:

1. **Stale-base rejection** — returns `stale_base` when `live_hash != base_hash`; barrier test shows second flock holder sees `stale_base` after first “commits.”
2. **Genuine sibling collision** — propose second same `target_ledger_id` → `pending_sibling`; reject first → second propose succeeds (`test_reject_sibling_then_other_proceeds`).
3. **New facts skip CAS** — no `target_ledger_id` → create-if-absent: absent → allow (`None`); occupied → `create_target_exists`; **never** `stale_base` (no base-hash CAS on creates).

Broader slice also green on tip: 45 tests across conflict/Gate5/recovery/propose (see VERIFY).

---

## Architecture shape changes during execution (drift log)

| Topic | Architecture said | Execution reality |
|-------|-------------------|-------------------|
| Status banner | Still said “not code-executed yet” after merge | **Fixed in this review package PR** — status now points at executed/merged + VERIFY |
| Apply sequence | Event → approved JSONL → Chroma → APPROVED under flock | Shipped; nested flock deadlock fixed via `_approve_unlocked` / single outer lock |
| Recovery | Matrix §7 | Plus EXECUTION additions: JSONL keyed by `proposal_id`; `--recover` CLI |
| Hash boundary | Full semantic record | Shared module; metadata also stores `content_hash` for live compare |
| Gate 5 | Warn/block + schema-deploy timestamp | Files under data root: `hash_schema_deploy.json`, `hash_schema_migration_report.json` |
| Gate 9 | Rebase = new id + SUPERSEDED | `rebase_proposal` + `record --rebase` |
| Conflict groups | `active_conflicts` on reducer | Approve gating uses unresolved **target/create id sets**; CONFLICT_* events annotate without removing from unresolved |
| Doctor nag | Out of scope | Not wired (per EXECUTION out-of-scope) |
| Similarity collision | Deferred | Still deferred — natural next arc |

---

## Explicitly still out of scope (unchanged)

Distributed locks, force-approve, MCP writes, **similarity-based collision**, hybrid retrieval, CI eval, timing JSONL, provenance sidecars, Restic.

---

## Suggested next (Claude’s priority #1)

**Similarity-based collision detection** on top of this model (exact `target_ledger_id` MVP already shipped): same-domain / high embedding similarity / opposite claims → conflict group, without redesigning base hash / proposal lifecycle.

---

## Ask of Claude

1. Confirm the six points are satisfied or name residual gaps.  
2. Confirm the three evidence cases are sufficient for close, or name missing fixtures.  
3. Sign off end-of-arc VERIFY, or list blocking follow-ups before similarity work.

---

## Round-2 closure (Claude 2026-07-12 follow-up)

### Self-collision (point 4 terminology)

**Direct answer:** There is **no** same-author / same-session exception. Sibling checks are **target-based only**. If the same author revises a still-pending proposal against the same `target_ledger_id` via a second `propose`, it registers as `pending_sibling` against the prior unresolved draft.

**Intended refine path:** `convmem record --rebase <proposal_id>` (or `rebase_proposal`) — new `proposal_id`, old → `SUPERSEDED` with links — or reject then re-propose. Error text now points at `--rebase`.

**Named test:** `test_same_author_repropose_is_pending_sibling_no_author_exception`.

### `--recover` / APPROVAL_STARTED idempotence

**Named test added:** `test_recover_approval_started_idempotent_no_double_apply`

- Leave `APPROVAL_STARTED` + approved JSONL (no Chroma / no `APPROVED`)
- First `recover_approval` → `retry_chroma`, one ingest, lifecycle `APPROVED`
- Second `recover_approval` → `approve`, **ingest call_count unchanged**, no extra `APPROVED` event

(Existing N8/N9 cover single-shot matrix paths; this test specifically proves no double-apply.)

### SEMANTIC_FIELDS maintenance flag

Architecture hash section now notes: bump `HASH_SCHEMA_VERSION` in the same change when `SEMANTIC_FIELDS` / canonicalization changes; cross-version hash equality is undefined.

### Sign-off ask

Both hold items from Claude round-2 are closed in code + tests. PR #6 carries the review package + these closures — ready for full arc close on merge.
