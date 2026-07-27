# Execution Plan — Complete-data backup audit closure

**Source:** Approved direction will be
[`ARCHITECTURE-complete-data-backup-audit-closure.md`](ARCHITECTURE-complete-data-backup-audit-closure.md)
**Authority:** Draft awaiting Ryan Architecture and Execution HITL; Cursor is
not authorized by this document alone
**Planning date:** 2026-07-25
**Implementation base:** `origin/main` at
`1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7`
**Historical failed artifact:** PR #120 implementation commit
`492e6e7eacef6cfd64dfc5bb00b25296b5e29288` remains `A-FAIL / FAIL`
**VERIFY companion:**
[`VERIFY-complete-data-backup-audit-closure.md`](VERIFY-complete-data-backup-audit-closure.md)

## Human consequence

This plan gives Cursor a decision-complete sequence for implementing the
approved narrow correction without reviving the failed branch, expanding into
Universal Tier-1 coordination, or touching live backup state.

| | |
|---|---|
| **Who** | Cursor implements after Ryan approval; Kiro reviews conformance; Copilot audits the new exact SHA; Ryan owns merge and live rollout |
| **What** | Shared snapshot resolution, lineage-safe offsite copy, current-day trigger, isolated restore preflight, and atomic export rewrite |
| **When** | Only after Architecture and Execution HITL on this three-document package |
| **Why** | Every safety consumer must reject newer wrong-path snapshots and restoration must prove complete-data relationships |
| **How** | Five serial stages with hermetic Restic fixtures and explicit stop points |

## Preconditions and execution locks

1. Start a fresh implementation branch/worktree from the exact approved base.
   If `origin/main` differs from the Architecture base, stop for Codex plan
   reconciliation before changing code.
2. Do not use, edit, rebase, or cherry-pick the failed `492e6e7…` artifact.
3. Confirm `restic version >= 0.19.0`. The installed planning-host Restic 0.19.0
   is sufficient; no system installation or upgrade is part of this arc.
4. Use `RESTIC_TEST_BIN` for integration tests and behaviorally verify its
   required features.
5. Run every Restic mutation against repositories below a newly created
   temporary test parent.
6. No live local repository, external/removable repository, data root, env
   file, timer, or user-systemd state may be changed.
7. No implementation stage begins until Ryan grants both Architecture and
   Execution HITL.

## Expected file set

### Required files

Core modules:

- `restic_snapshot.py` — new authoritative resolver and CLI.
- `complete_data_restore.py` — new inventory, validator, classification, and
  durable-report library.
- `restic_gate.py` — delegate existing gate behavior to the resolver while
  preserving the compatibility API and exact exit codes.
- `doctor.py` — path-bound local/offsite reporting, version capability, and
  source/destination ID visibility.
- `observe.py` — crash-atomic `_upsert_jsonl_line()`.

Commands:

- `scripts/restic-ensure-chroma-snapshot.sh`
- `scripts/restic-copy-external.sh`
- `scripts/restic_integrity_check.py`
- `scripts/chroma_restore_drill.py`
- `scripts/complete_data_restore_preflight.py` — new CLI.
- `scripts/setup-restic-chroma.sh`
- `scripts/verify-restic-gate.sh`

Configuration and operations:

- `config/restic.env.example`
- `systemd/convmem-restic-local.service.example` — new.
- `systemd/convmem-restic-local.timer.example` — new.
- `systemd/convmem-restic-external.service.example`
- `systemd/convmem-restic-external.timer.example`
- `docs/RECOVER.md`
- `docs/SYSTEMD-DEPLOY.md`

Tests:

- `tests/test_restic_snapshot.py` — new.
- `tests/test_restic_offsite.py` — new.
- `tests/test_complete_data_restore.py` — new.
- `tests/test_restic_systemd.py` — new.
- `tests/test_restic_gate.py`
- `tests/test_restic_integrity_check.py`
- `tests/test_chroma_restore_drill.py`
- `tests/test_doctor.py`
- `tests/test_upsert.py`
- `tests/test_write_gate_effect.py`

### Conditional after inspection

Change these only if the implementation discovers a materially inaccurate
backup or lane claim:

- `scripts/backup-restic-password.sh` — only for a conflicting path-containment
  or version assumption.
- `docs/ROADMAP.md` and `docs/inter-model/LATEST.md` — only for a required
  active-status correction.
- `docs/inter-model/TEAM-CHARTER-2026-07-06.md` or generated role mappings —
  only if they contain an inaccurate backup ownership claim.

Do not perform general documentation normalization, generated role-surface
churn, or unrelated cleanup.

## Interfaces and exact behavior

### Resolver CLI

`restic_snapshot.py` exposes importable functions defined by the Architecture
and a CLI with these subcommands:

```text
python3 restic_snapshot.py resolve \
  --repository <repo> \
  --password-file <path> \
  --expected-data-root <path> \
  [--require-current-local-day] \
  [--snapshot-id <full-id>]

python3 restic_snapshot.py resolve-copy-destination \
  --repository <external-repo> \
  --password-file <path> \
  --source-json <validated-source-json>
```

Successful stdout is one JSON object matching `SnapshotRef`. Diagnostics go to
stderr. The resolver:

- invokes `snapshots --json --tag convmem-data-v1`;
- never invokes `snapshots --latest`;
- validates normalized paths before sorting;
- returns only a full 64-character ID;
- reads destination lineage from JSON field `original`;
- preserves Restic `10`, `11`, and `12`;
- uses Architecture domain codes `20`–`29`.

No CLI accepts an unsafe "trust this ID" bypass.

### Reports

Offsite copy, integrity, and restore reports use:

```text
${CONVMEM_BACKUP_REPORT_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/convmem/backup-audit}
```

Reports are written atomically as paired JSON/Markdown files. JSON is the
machine authority; Markdown is a rendered summary. Each report records:

- command kind and status;
- Restic version and repository role;
- expected normalized data root;
- source snapshot ID;
- destination snapshot ID and `original`, when applicable;
- tree, time, paths, and tags;
- exact invoked operation without password contents;
- validation steps, classifications, exit code, and timestamps.

Report-write failure returns `29`; an operation is not reported as protected
without its durable report.

## Stage T1 — Resolver, version, and path contract

### Deliverables

1. Implement `SnapshotRef`, environment loading, repository classification,
   path normalization, semantic version parsing, and capability checks in
   `restic_snapshot.py`.
2. Query every tagged snapshot as JSON; validate exact paths in Python; sort
   only correct-path candidates.
3. Validate requested full IDs through the same contract.
4. Implement destination lookup through `original == source.id` plus
   tree/time/path/tag equality.
5. Implement exit codes `20`–`27` and preserve Restic `10`–`12`.
6. Update `config/restic.env.example` and setup output for explicit
   `CONVMEM_DATA_ROOT`.

### Tests

In `tests/test_restic_snapshot.py`:

- explicit data-root normalization and legacy Chroma-parent derivation;
- rejection of `/`, home, data-root/chroma equality, local repo overlap,
  external repo overlap, and password containment;
- valid local, `local:`, and opaque remote repository forms;
- missing, malformed, short, and ambiguous IDs;
- no tag, wrong path, stale correct path, and current correct path;
- command-builder assertion that `--latest` is absent;
- actual Restic fixture with an older current-day correct-path
  `convmem-data-v1` snapshot and a newer current-day wrong-path snapshot;
- resolver selects the older correct snapshot despite the newer wrong snapshot;
- actual `restic check "<full-id>" --read-data-subset=100%`;
- actual copy creates a distinct destination object whose JSON `original`
  equals the source ID;
- missing/ambiguous/mismatched copy lineage returns `27`.

### Gate and stop

Run the focused resolver tests. Any uncertainty about Restic JSON or path
normalization stops T1 for Ryan/Codex; do not create a fallback selector.

## Stage T2 — Consumer migration and daily trigger

### Deliverables

1. Refactor `restic_gate.py` and
   `scripts/restic-ensure-chroma-snapshot.sh` to use the resolver.
2. Preserve `ensure_chroma_snapshot_for_live_write()` and both compatibility
   tags; preserve exact nonzero codes through protected write call sites.
3. Refactor offsite copy:
   - resolve current local source `S`;
   - on stale exit `25`, copy nothing and exit `25`;
   - copy explicit `S`;
   - resolve and verify destination `D`;
   - report both IDs and `D.original`.
4. Refactor `_check_restic_external()` to repeat local-current and destination
   lineage validation. Doctor retains aggregate status but includes the
   resolver code.
5. Change integrity to
   `restic check "<validated-id>" --read-data-subset=5%` or manual
   `--read-data`.
6. Refactor Chroma drill and restore selection to validate an explicit ID
   before use.
7. Add local user-systemd service/timer and update the external timer:

```ini
OnCalendar=*-*-* 00:15:00
Persistent=true
RandomizedDelaySec=300
```

```ini
OnCalendar=*-*-* 01/2:00:00
Persistent=true
RandomizedDelaySec=300
```

8. If the external service contains
   `After=convmem-restic-local.service`, document it as non-authoritative
   ordering only.
9. Document persistent catch-up: the local timer runs after resumed downtime;
   no recovery-point claim exists while the host never runs.

### Tests

- Gate creates/reuses only a current correct-path complete snapshot.
- Current legacy Chroma-only snapshots never satisfy the gate.
- Every affected consumer rejects the newer wrong-path fixture.
- Missing password blocks protected writes with exact code `12`.
- Offsite copy receives `S`, never `latest`, and verifies `D`.
- Repeated Restic copy succeeds only after the same valid `D` is resolved.
- Stale local `S` makes the offsite command exit `25`, copies nothing, and
  produces failure-visible output.
- Doctor cannot pass on an unrelated external snapshot.
- Integrity argv contains the explicit full ID and no tag/path selector.
- Restore/Chroma drill validate supplied IDs before Restic restore.
- `systemd-analyze calendar` parses both literal schedules.
- `systemd-analyze verify` accepts all four unit files.

### Gate and stop

Complete focused Python, shell syntax, ShellCheck, and systemd validation.
Do not install or start the units.

## Stage T3 — Isolated complete-data restore preflight

### Deliverables

1. Implement the fixed Architecture inventory in
   `complete_data_restore.py`.
2. Implement `scripts/complete_data_restore_preflight.py`:
   - validate requested/local/external snapshot ID;
   - create an isolated disposable run outside the live root;
   - restore with `--verify`;
   - execute every applicable inventory validator;
   - classify without repairing;
   - write reports outside the run;
   - return `0`, `30`, `31`, or `32`, or propagate selection/Restic codes.
3. Map configured durable paths to the restored root while validating their
   original recorded locations.
4. Treat unknown top-level durable state as
   `BLOCKED_UNCLASSIFIED_STATE`.
5. Implement bounded Shadow behavior:
   - absent/disabled is valid;
   - inactive residue is non-authoritative;
   - enabled requires existing Phase 0 activation/identity/root/health
     contracts;
   - compare manifest root with the original expected Chroma path;
   - never use Shadow as a repair source.
6. Update `docs/RECOVER.md` with:
   - exact ID resolution;
   - preflight classifications;
   - named derived repair sources;
   - rerun requirements;
   - separate Ryan live-replacement authorization;
   - authoritative-first replacement and rollback order.

### Tests

- Each matrix row has an exact path/config resolver, authority, validator,
  repair source, and failure classification.
- Canonical approved-decision bytes restore identically.
- Pending/conflict lifecycle valid, orphaned, and corrupt cases.
- Chroma required collections, IDs, counts, pinned hashes, and fingerprints.
- Derived export parse/identity/count drift.
- `processed.json` ordinary drift versus ambiguous exclusion state.
- Queue, suppression, import, authorization, hash-schema, and operational
  evidence classifications.
- Shadow disabled, inactive malformed, valid active, invalid manifest,
  root/identity mismatch, degraded health, and corrupt active state.
- Unknown top-level state blocks.
- Reports survive disposable-run deletion.
- `VALID_WITH_REPAIRABLE_DERIVED_DRIFT` never performs repair.
- `BLOCKED` never enables replacement.
- No live path is opened for write.

### Gate and stop

The preflight must pass its isolated fixtures before documentation may claim a
complete-data restore. Any new durable-state class stops for an Architecture
matrix revision rather than expanding ad hoc.

## Stage T4 — Crash-atomic JSONL replacement

### Deliverables

Within the existing export flock in `observe.py::_upsert_jsonl_line()`:

1. Create a same-directory temp file with exact prefix
   `.<destination>.convmem-upsert.` and suffix `.tmp`.
2. Preserve malformed lines, append-if-not-found behavior, UTF-8 bytes,
   newlines, and existing file mode.
3. Write all lines, flush, and `fsync` the temp descriptor.
4. `os.replace(temp, destination)`.
5. Open and `fsync` the parent directory.
6. Remove only the invocation-owned temp on caught pre-replace failure.
7. Add no glob cleanup or scavenger.

### Tests

Fault-inject:

- partial temp write;
- flush failure;
- temp-file `fsync` failure;
- interruption immediately before `os.replace`;
- parent-directory `fsync` failure after replacement.

Before replacement, the old file must remain byte-identical. After replacement,
readers may observe only the complete old or complete new file. The
post-replace directory-`fsync` failure returns nonzero while leaving a complete
visible file.

Also preserve existing malformed-line and append behavior tests.

### Gate and stop

Run `tests/test_upsert.py` and related write-effect tests. Do not add another
writer lock.

## Stage T5 — Integrated proof, documentation, and review

### Hermetic Restic setup

Create one temporary parent containing:

```text
home/
config/
cache/
correct-root/
wrong-root/
local-repo/
external-repo/
password
restore/
reports/
sentinels/
```

Override `HOME`, XDG variables, `CONVMEM_RESTIC_ENV`,
`CONVMEM_DATA_ROOT`, `CONVMEM_CHROMA_DIR`, all repositories, password, cache,
restore root, and report root. Abort unless every mutable local path is below
the temporary parent.

Create:

- a current legacy `convmem-chroma` snapshot;
- an older current-day correct-path `convmem-data-v1` snapshot;
- a newer current-day wrong-path `convmem-data-v1` snapshot;
- a separate stale correct-path fixture;
- a canonical approved decision with a recorded byte hash;
- complete Chroma/export/control fixtures;
- exact scratch directories that must be excluded.

### Required acceptance controls

1. Current legacy Chroma-only snapshot is rejected by the complete-data gate.
2. Current new-tag wrong-root snapshot is rejected.
3. `CONVMEM_DATA_ROOT=CONVMEM_CHROMA_DIR` fails closed.
4. Missing password blocks the protected write.
5. Canonical decision restores with identical bytes.
6. Worktree and restore-drill scratch fixtures are absent from snapshot
   contents.
7. Offsite copy retains tag/path/tree/time and proves
   `destination.original == source`; both IDs are recorded.

Extend control 2 across:

- offsite copy;
- offsite doctor;
- integrity check;
- restore selection;
- Chroma restore drill;
- complete-data restore preflight.

No broad suite result substitutes for these controls.

### Five-part evidence

- Produce the Tier-1 writer census and classify every mutator's output.
- Claim `PASS` only for the writer census and isolated restore invariants.
- Record universal participation, universal persistence boundary, and
  universal adversarial concurrency as `NOT CLAIMED`.
- Do not promote a focused crash/reconcile test into a universal claim.

### Reviews

1. Fill the companion VERIFY at one immutable implementation SHA.
2. Kiro performs independent implementation/plan-conformance review at that
   SHA.
3. GitHub Copilot performs the fresh Hybrid audit at the same SHA and reports:
   - `A-PASS` or `A-FAIL`;
   - all five dimensions;
   - overall `PASS` or `FAIL`;
   - confirmation of no live production/offsite mutation.
4. Only `A-PASS / PASS` is eligible for Ryan merge consideration.

## Verification commands

Focused suites:

```bash
pytest -q \
  tests/test_restic_snapshot.py \
  tests/test_restic_offsite.py \
  tests/test_restic_gate.py \
  tests/test_restic_integrity_check.py \
  tests/test_chroma_restore_drill.py \
  tests/test_complete_data_restore.py \
  tests/test_restic_systemd.py \
  tests/test_doctor.py \
  tests/test_upsert.py \
  tests/test_write_gate_effect.py
```

Shell:

```bash
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
```

Systemd:

```bash
systemd-analyze calendar '*-*-* 00:15:00'
systemd-analyze calendar '*-*-* 01/2:00:00'
systemd-analyze verify \
  systemd/convmem-restic-local.service.example \
  systemd/convmem-restic-local.timer.example \
  systemd/convmem-restic-external.service.example \
  systemd/convmem-restic-external.timer.example
```

Run broader suites only after the focused safety proof; report them as
supplementary.

## Rollout and rollback

- Merging code/examples does not install timers or mutate repositories.
- Setup/doctor may report that a target binary is unsupported, but do not
  install it automatically.
- Ryan separately authorizes timer installation and any live snapshot/offsite
  proof.
- Ryan separately authorizes production replacement after a durable `VALID`
  preflight report.
- Preserve the pre-cutover root for rollback; restore it if cutover validation
  fails.
- Rolling code back to tag-only selection reopens the audit defect and cannot
  support a current protection claim.

## Exact stop points

1. **Before T1:** Ryan approves Architecture and Execution.
2. **After T1:** stop on any unresolved Restic/path semantic.
3. **After T2:** stop before installing or starting timers.
4. **After T3:** stop on unknown state or any attempted automatic repair.
5. **After T5:** stop for Kiro and Copilot exact-SHA reviews.
6. **After reviews:** stop for Ryan merge and later live-rollout decisions.

Cursor must not infer implementation, timer, repository, or production
authority from the existence of these plans.

Active phase lane must stop here. Await HITL.
