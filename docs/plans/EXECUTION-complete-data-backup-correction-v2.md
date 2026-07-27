# Execution Plan — Complete-data backup correction v2

**Source:** Approved direction will be
[`ARCHITECTURE-complete-data-backup-correction-v2.md`](ARCHITECTURE-complete-data-backup-correction-v2.md)
**Authority:** Draft awaiting Ryan Architecture and Execution HITL; Cursor is
not authorized by this document alone
**Planning date:** 2026-07-27
**Implementation base:** `origin/main` at
`1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7`
**Historical failed artifacts (immutable):**

| Artifact | Verdict |
|---|---|
| PR #120 `492e6e7eacef6cfd64dfc5bb00b25296b5e29288` | Ryan `A-FAIL / FAIL` |
| Crush tip `b6284ad9ac42e0bb554cd2d44d512b01bad748f2` | **Codex FAIL** — do not edit |

**VERIFY companion:**
[`VERIFY-complete-data-backup-correction-v2.md`](VERIFY-complete-data-backup-correction-v2.md)

## Human consequence

This plan gives Cursor a decision-complete sequence for implementing the v2
correction from clean `origin/main` without rehabilitating `b6284ad…`, without
claiming complete protection before live grants, and without leaving legacy
fallback selection in any safety consumer.

| | |
|---|---|
| **Who** | Cursor implements after Ryan approval; Kiro reviews conformance; Codex independently replays doctor/fallback/root-path/restore/FD-leak reproductions; Copilot audits the exact SHA; Ryan owns merge and live rollout |
| **What** | BackupContext, v2 profile, fallback-free workflows, atomic publication, evidence-backed restore policy, hermetic proof |
| **When** | Only after Architecture and Execution HITL on this three-document package |
| **Why** | `b6284ad…` is Codex FAIL; correction must be structural, not layered |
| **How** | P0 plan package (this arc) then five serial implementation stages T1–T5 with hermetic gates |

## Preconditions and execution locks

1. Start a fresh implementation branch/worktree from the exact approved base.
   If `origin/main` differs from the Architecture base, stop for Codex plan
   reconciliation before changing code.
2. Do not use, edit, rebase, or cherry-pick `492e6e7…` or `b6284ad…`.
3. Confirm `restic version >= 0.19.0`. Use `RESTIC_TEST_BIN` for integration
   tests and behaviorally verify required features.
4. Run every Restic mutation against repositories below a newly created
   temporary test parent. Install a path firewall that aborts if any mutable
   test path escapes that parent.
5. No live local repository, external/removable repository, data root, env
   file, timer, or user-systemd state may be changed.
6. No implementation stage begins until Ryan grants both Architecture and
   Execution HITL.
7. Tests must not read live paths or configuration.

## Expected file set

### Required files

Core modules:

- `restic_snapshot.py` — new: `BackupContext`, profile, path safety, subprocess
  boundary, resolution, lineage, exit codes, capability checks.
- `backup_workflows.py` — new deep orchestration for ensure/copy/health/
  integrity/restore workflows.
- `atomic_files.py` — new: `atomic_write_text()`.
- `complete_data_restore.py` — new: closed `StateSpec` matrix, validators,
  evidence comparison, durable reporting.
- `restic_gate.py` — delegate to workflows/context; preserve compatibility API.
- `doctor.py` — profile-aware local/offsite health via workflow functions;
  `WARN_LEGACY_ONLY` until v2 live grants complete.
- `observe.py` — migrate JSONL publication to `atomic_write_text()`.

Commands / thin wrappers:

- `scripts/restic-ensure-chroma-snapshot.sh`
- `scripts/restic-copy-external.sh`
- `scripts/restic_integrity_check.py`
- `scripts/chroma_restore_drill.py`
- `scripts/complete_data_restore_preflight.py` — new CLI.
- `scripts/setup-restic-chroma.sh`
- `scripts/verify-restic-gate.sh`

Configuration and operations:

- `config/restic.env.example` — profile + explicit `CONVMEM_DATA_ROOT`.
- systemd local/external service and timer examples.
- `docs/RECOVER.md`
- `docs/SYSTEMD-DEPLOY.md`

Tests:

- `tests/test_restic_snapshot.py` — new.
- `tests/test_restic_offsite.py` — new (must not be missing).
- `tests/test_backup_workflows.py` — new consumer-wide S/W challenge.
- `tests/test_atomic_files.py` — new fault + FD-leak suite.
- `tests/test_complete_data_restore.py` — new matrix suite.
- `tests/test_restic_systemd.py` — new temporary unit names.
- Update: `tests/test_restic_gate.py`, `tests/test_restic_integrity_check.py`,
  `tests/test_chroma_restore_drill.py`, `tests/test_doctor.py`,
  `tests/test_upsert.py`, `tests/test_write_gate_effect.py`.

### Conditional after inspection

Change only if materially inaccurate backup/lane claims are discovered:

- `scripts/backup-restic-password.sh`
- `docs/ROADMAP.md` / `docs/inter-model/LATEST.md`
- charter/role mappings with inaccurate backup ownership claims

Do not perform general documentation normalization or unrelated cleanup.

## Stage P0 — Superseding plan package (this document set)

### Deliverables

1. Create `plan/2026-07-27-complete-data-backup-correction-v2` from current
   `origin/main` in a separate worktree.
2. Update Architecture, Execution, and VERIFY together.
3. Record `b6284ad…` as Codex FAIL; do not alter that branch.

### Gate

Plan package is pushed and awaiting Ryan Architecture + Execution HITL.
No code changes in P0.

## Stage T1 — Context and Restic boundary

### Deliverables

1. Implement `BackupContext`, `BackupProfile`, repository refs, path safety,
   and subprocess environment construction in `restic_snapshot.py`.
2. Enforce profile rules: missing/`legacy-chroma` vs `complete-data-v2`
   (explicit data root mandatory; no parent derivation).
3. Centralize every Restic subprocess call; preserve codes `10`–`12`; apply
   domain codes `20`–`32` only when Restic did not supply a reserved code.
4. Implement capability checks and v2 resolution (`convmem-data-v2`, never
   `--latest`).
5. Update `config/restic.env.example` for profile + explicit data root.

### Gate

Real hermetic Restic tests plus unsafe-root, overlap, empty-capability, and
codes `10`–`12`. Stop on any unresolved Restic/path semantic; do not invent a
fallback selector.

## Stage T2 — Workflow migration

### Deliverables

1. Implement `backup_workflows.py` with the six owned functions.
2. Migrate gate, offsite, doctor, integrity, Chroma drill, and restore
   preflight to those workflows.
3. Shell scripts become thin exec wrappers.
4. Delete all legacy fallback selection. Configured failure → WARN or FAIL,
   never PASS or SKIP.
5. Doctor reports `WARN_LEGACY_ONLY` under missing/`legacy-chroma` profile.

### Gate

Every consumer runs against the same older-correct/newer-wrong fixture and must
name the correct full ID. No consumer may select or report the newer wrong
snapshot.

## Stage T3 — Durable atomic publication

### Deliverables

1. Implement `atomic_files.py::atomic_write_text()`.
2. Migrate JSONL export and authoritative JSON report publication.
3. Markdown reports remain derived from durable JSON.

### Gate

Fault-inject: partial write, flush, temporary fsync, pre-replace, replace, and
parent-directory fsync failures. Add a repeated-write descriptor-count test
requiring zero growth.

## Stage T4 — Evidence and restore policy

### Deliverables

1. Implement pre-snapshot capture of `.convmem-backup-evidence.json` via
   atomic publication.
2. Implement closed `StateSpec` table, validators, lifecycle reducer,
   fingerprint/evidence comparison, and durable reporting.
3. Update `docs/RECOVER.md` with classifications, named repair sources, and
   separate live-replacement authorization.

### Gate

One test per matrix row plus duplicates, orphan events, invalid active Shadow,
corrupt authorization/import state, missing required collections, and scratch
leakage. Unknown state blocks. Validators never repair.

## Stage T5 — Integrated proof and operations

### Deliverables

1. Add missing `tests/test_restic_offsite.py`.
2. Update systemd examples/docs; verify with temporary `.service` / `.timer`
   names via `systemd-analyze verify`.
3. Run the complete hermetic flow:

```text
capture S → reject newer W → copy S → resolve D.original=S
→ integrity check S → restore S → validate evidence → retain reports
```

4. Produce Tier-1 writer census classification evidence.
5. ShellCheck with zero findings.
6. Confirm required suites collect successfully — no missing files or safety
   skips.

### Gate

All VERIFY mandatory proofs green at one immutable implementation SHA. Then
stop for Kiro, Codex independent replay, and Copilot Hybrid audit. No live
mutation.

## Mandatory proof checklist (maps to VERIFY)

- Captured argv showing no `--latest`.
- Exact codes `10`–`12`, `20`–`32`.
- All seven negative controls.
- Every consumer challenged with S/W.
- Real offsite shell/workflow test.
- All atomic fault points + FD-leak zero growth.
- Full restore matrix.
- Tier-1 writer census.
- Temporary HOME, XDG directories, cache, repositories, password, reports, and
  systemd paths.
- Path firewall abort on escape from temporary parent.
- ShellCheck zero findings.
- `systemd-analyze verify` using temporary unit names.
- Required suites collected successfully — no missing files or safety skips.
- Broad pytest success remains supplementary.

## Verification commands

```bash
pytest -q \
  tests/test_restic_snapshot.py \
  tests/test_restic_offsite.py \
  tests/test_backup_workflows.py \
  tests/test_atomic_files.py \
  tests/test_restic_gate.py \
  tests/test_restic_integrity_check.py \
  tests/test_chroma_restore_drill.py \
  tests/test_complete_data_restore.py \
  tests/test_restic_systemd.py \
  tests/test_doctor.py \
  tests/test_upsert.py \
  tests/test_write_gate_effect.py

bash -n \
  scripts/restic-ensure-chroma-snapshot.sh \
  scripts/restic-copy-external.sh \
  scripts/setup-restic-chroma.sh \
  scripts/verify-restic-gate.sh \
  scripts/backup-restic-password.sh

shellcheck \
  scripts/restic-ensure-chroma-snapshot.sh \
  scripts/restic-copy-external.sh \
  scripts/setup-restic-chroma.sh \
  scripts/verify-restic-gate.sh \
  scripts/backup-restic-password.sh

# Use temporary copied unit names under the hermetic parent:
systemd-analyze verify \
  "$TMP/systemd/convmem-restic-local.service" \
  "$TMP/systemd/convmem-restic-local.timer" \
  "$TMP/systemd/convmem-restic-external.service" \
  "$TMP/systemd/convmem-restic-external.timer"
```

## Review and rollout

At one immutable implementation SHA:

1. Kiro issues plan-conformance PASS or FAIL.
2. Codex independently replays the original doctor, fallback, root-path,
   restore-misclassification, and FD-leak reproductions.
3. Copilot audits the same SHA and issues `A-PASS`/`A-FAIL` plus overall
   `PASS`/`FAIL`.
4. Ryan decides merge.

After merge, separate grants remain required for:

1. Configuring `complete-data-v2`.
2. Creating the first live v2 snapshot.
3. Copying it offsite and validating lineage.
4. Installing/enabling timers.

Until all four finish, doctor must say `WARN_LEGACY_ONLY`, never
“complete-data protected.”

## Exact stop points

1. **Before T1:** Ryan approves Architecture and Execution.
2. **After T1:** stop on any unresolved Restic/path/context semantic.
3. **After T2:** stop if any consumer retains legacy fallback selection.
4. **After T3:** stop if any atomic fault or FD-leak gate fails.
5. **After T4:** stop on unknown state class or any attempted automatic repair.
6. **After T5:** stop for Kiro, Codex replay, and Copilot exact-SHA reviews.
7. **After reviews:** stop for Ryan merge and later live-rollout grants.

Cursor must not infer implementation, timer, repository, or production
authority from the existence of these plans.
