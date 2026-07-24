# GitHub Copilot audit handoff — complete ConvMem data backups

**Audit lane:** GitHub Copilot audit lane — independent safety/isolation review; no implementation.
**Exact implementation artifact:** commit `492e6e7eacef6cfd64dfc5bb00b25296b5e29288`.
**Branch carrying this handoff:** `fix/2026-07-23-complete-data-backup`.
**Status:** awaiting independent `PASS` or `FAIL`; not merged; no live backup rollout performed.

## Context brief

- **Who:** Codex implemented the repository-side fix; GitHub Copilot audit lane owns this check; Ryan owns merge and any live Restic/offsite operation.
- **What:** Change the production backup unit from Chroma alone to the complete ConvMem-owned data root while preserving the existing gate, Restic repository, and Chroma-tool compatibility.
- **When:** Implemented and pushed 2026-07-23, after the Neutral/Office Team independence audit exposed that canonical decisions and ledgers were outside Restic coverage.
- **Why:** A machine-loss event could restore Chroma but permanently lose approved decisions, queues, imports, authorizations, and replay state stored beside it.
- **How:** Use a new coverage tag (`convmem-data-v1`), validate the snapshot source path, back up the data-root parent, retain `convmem-chroma` as a compatibility tag, and update offsite/doctor/integrity/restore consumers.

## Audit instruction

Audit the exact implementation commit above. Do not trust this handoff's claims or Codex's test report. Return a written, exact-SHA `PASS` or `FAIL` with file:line evidence.

This is a safety audit, not an implementation assignment. Do not edit code, create snapshots, copy to the removable repository, change timers, modify `~/.config/convmem/restic.env`, or touch `~/.local/share/convmem/`. Return findings to Ryan.

## Resolve the target independently

```bash
git fetch origin
git show --stat --oneline 492e6e7eacef6cfd64dfc5bb00b25296b5e29288
git diff 492e6e7eacef6cfd64dfc5bb00b25296b5e29288^ \
  492e6e7eacef6cfd64dfc5bb00b25296b5e29288
```

For execution, use a detached temporary worktree at that exact commit. Do not audit the mutable branch name as if it were the artifact.

## Required audit questions

### A. Backup-set completeness

Independently inventory ConvMem-owned persistent state from configuration and write paths. At minimum trace:

- Chroma and configured index sidecars;
- approved decisions and pending-decision/event ledgers;
- observations, evidence exports, queues, attempts, authorizations, imports, suppression records, and refine undo state;
- any module-level path that writes under or outside the configured data root.

Then answer:

1. Does backing up `CONVMEM_DATA_ROOT` (or the parent of legacy `CONVMEM_CHROMA_DIR`) actually include every durable state file needed for recovery?
2. Does any critical state still live outside that root?
3. Are the only exclusions—`worktrees/` and `restore-drill/runs/`—genuinely disposable? Flag any unique/unpushed state that makes either exclusion unsafe.
4. Does the fix include secrets accidentally, or correctly keep the password and repositories outside the snapshot target?

Do not accept a list copied from the implementation tests as the inventory proof.

### B. Migration and false-positive resistance

Verify that:

1. a same-day `convmem-chroma`-only snapshot cannot satisfy the new gate;
2. a same-day `convmem-data-v1` snapshot for the wrong source path cannot satisfy it;
3. an existing production `restic.env` without `CONVMEM_DATA_ROOT` safely derives the current data root without backing up the Restic repository itself;
4. `CONVMEM_DATA_ROOT=CONVMEM_CHROMA_DIR` fails closed;
5. local repository, password, and remote/backend repository forms are validated without rejecting valid configured backends;
6. the compatibility tag cannot cause the restore drill, integrity check, offsite copy, or doctor to select an old Chroma-only snapshot by mistake.

Pay particular attention to whether the offsite doctor verifies actual snapshot paths or only trusts the new tag, and whether `restic copy latest --tag convmem-data-v1` can select a wrongly tagged snapshot.

### C. Recoverability and consistency

Challenge the load-bearing recovery claim:

1. Do tests prove canonical bytes can be recovered, not merely that a snapshot row exists?
2. Does the Chroma restore drill still discover and verify Chroma when the snapshot root is now its parent?
3. Is there an operationally credible restore procedure for the complete data root, including ledgers and sidecars?
4. Can a Restic walk of the live data root capture an internally inconsistent combination while watch/refine/index processes are writing? If so, distinguish:
   - harmless derived-index skew that replay/reindex can repair;
   - canonical JSON/JSONL corruption or cross-file inconsistency that would block recovery.
5. Does the current code have enough locking, append semantics, or restore validation to justify `PASS`, or is a bounded consistency safeguard required?

Do not infer that Restic's successful exit makes application-level state coherent.

### D. Recovery-point objective and trigger coverage

The documents deliberately claim one complete restore point from the current local day, not per-write durability. Verify whether the implementation actually establishes that objective:

1. Which commands invoke the fail-closed gate, and which background/append paths do not?
2. Can durable state change for days without any path that creates a `convmem-data-v1` snapshot?
3. Does `convmem doctor --require-current` only report staleness, or create the missing snapshot?
4. Does the existing timer create local snapshots or merely copy an already-existing local snapshot offsite?
5. If the daily objective is not mechanically assured, is the documentation precise enough, or is a local scheduled snapshot/other bounded fix required before this closes the production exposure?

This is a central decision point. A broader backup target is not sufficient if no reliable trigger creates it.

### E. Offsite and secret recovery

Verify that:

- the external copy selects `convmem-data-v1` and the configured removable repository remains optional/nonblocking;
- offsite freshness cannot report `PASS` for only an old Chroma snapshot;
- `RESTIC_PASSWORD_BACKUP_FILE` remains outside both encrypted repositories and the backed-up data root;
- the password-copy guard handles both new and legacy environment layouts;
- no test or code path writes to the real removable repository during verification.

## Required hermetic verification

Run from the detached exact-commit worktree:

```bash
pytest -q \
  tests/test_restic_gate.py \
  tests/test_restic_integrity_check.py \
  tests/test_chroma_restore_drill.py \
  tests/test_doctor.py \
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

git diff --check 492e6e7eacef6cfd64dfc5bb00b25296b5e29288^ \
  492e6e7eacef6cfd64dfc5bb00b25296b5e29288
```

Use only temporary Restic repositories and temporary data roots. The repository-wide suite is optional corroboration, not a substitute for the safety questions above. Codex reported `776 passed, 99 subtests passed`; reproduce it only if useful.

## Negative controls that must be evidenced

The final audit must show evidence for all of these:

| Negative control | Required result |
| --- | --- |
| Current legacy Chroma-only snapshot | Gate rejects it |
| Current new-tag snapshot of another root | Gate rejects it as wrong path |
| Data root set to Chroma itself | Gate rejects it |
| Missing password | Wrapper blocks the protected write |
| Canonical decision in temporary data root | Recoverable with identical bytes |
| Worktree and restore-run scratch fixtures | Absent from snapshot contents |
| Complete snapshot copied to temporary offsite repo | New tag and expected source path present |

## Verdict format

```markdown
## GitHub Copilot audit verdict — complete ConvMem data backups

- Artifact: `492e6e7eacef6cfd64dfc5bb00b25296b5e29288`
- Verdict: `PASS` or `FAIL`
- Live production/offsite mutations performed: `none`
- Commands run: ...
- Negative controls: ...

### Blocking findings

- `file:line` — evidence, consequence, smallest safe correction

### Nonblocking findings

- `file:line` — evidence and why it does not block

### Recovery conclusion

State whether canonical data, Chroma, offsite copy, and password recovery are each adequately protected, and whether the claimed daily recovery-point objective is mechanically established.
```

`PASS` requires no unresolved data-loss or false-green path. Style, naming, or speculative framework improvements are nonblocking. If any load-bearing question is uncertain, return `FAIL` with the smallest test or change needed to resolve it; do not return `defer` as a passing substitute.

## Explicitly out of scope

- Running the live backup or offsite copy;
- changing the backup frequency or installing a timer unless the audit first identifies the current trigger as a blocker;
- the reranker singleton bug;
- Office Team or Neutral Core implementation;
- packaging, general storage abstraction, or ConvMem path cleanup beyond this backup boundary;
- merging, creating grants, recording a ledger decision, or editing the audited branch.

## TL;DR

Audit exact commit `492e6e7` in the GitHub Copilot safety lane. Prove the backup set is complete and recoverable, then challenge live-write consistency, daily trigger coverage, offsite false greens, and secret placement before issuing an exact-SHA `PASS` or `FAIL`; do not touch production data.
