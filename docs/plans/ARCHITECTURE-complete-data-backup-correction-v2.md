# Architecture Direction — Complete-data backup correction v2

**Source:** Codex corrective architecture after independent verification of the
Crush audit-closure implementation
**Authority:** Awaiting Ryan HITL; this document does not authorize
implementation or live rollout
**Planning date:** 2026-07-27
**Implementation base:** `origin/main` at
`1ad99585060d62b2dfc22b50cdbbefdd20b0b8b7`
**Historical failed artifacts (immutable — never rehabilitate):**

| Artifact | Role | Verdict |
|---|---|---|
| PR #120 commit `492e6e7eacef6cfd64dfc5bb00b25296b5e29288` | First complete-data attempt | Ryan `A-FAIL / FAIL` |
| Branch tip `b6284ad9ac42e0bb554cd2d44d512b01bad748f2` on `fix/2026-07-27-complete-data-backup-audit-closure` | Crush audit-closure implementation | **Codex FAIL** |

**Consistency bar:** Hybrid, locked by Ryan on 2026-07-24
**Supersedes (planning only):** the audit-closure Architecture/Execution/VERIFY
package. Those documents remain historical; this package is the correction
path. Do not layer fixes onto `b6284ad…`.

## Human consequence

If Ryan approves this direction, Cursor can implement a correction that makes
omitted credentials and skipped path validation structurally impossible, keeps
merge honest until an explicit `complete-data-v2` profile is activated, removes
every legacy safety fallback that false-greens wrong snapshots, centralizes
durable atomic publication, and validates restores against capture evidence plus
a closed authority matrix.

| | |
|---|---|
| **Who** | Codex authors this package; Ryan owns approval; Cursor implements only after Architecture and Execution HITL; Kiro reviews conformance; Codex independently verifies reproductions; Copilot performs the Hybrid audit |
| **What** | Complete-data backup correction v2 |
| **When** | Fresh plan and implementation from `origin/main` at `1ad9958…` after Architecture and Execution approval |
| **Why** | Current boundaries permit missing credentials, unused safety checks, legacy false-greens, and incomplete restore validation; the Crush tip at `b6284ad…` is Codex FAIL and must remain immutable audit evidence |
| **How** | One deep `BackupContext`, explicit activation profile, fallback-free workflows, fixed restore policy, durable atomic writes, capture evidence, and hermetic consumer-wide proof |

## Problem statement

The failed Crush implementation at `b6284ad…` remains useful as audit evidence
but must not be patched in place. Independent verification found that the
current boundaries still permit:

- credentials or path validation omitted at individual call sites;
- safety workflows that catch resolver failure and fall back to legacy
  selection, producing PASS or SKIP instead of WARN or FAIL;
- doctor or protection claims that overstate coverage before an explicit
  complete-data profile and live v2 snapshot exist;
- incomplete restore validation without capture-time evidence to detect
  mid-capture skew;
- atomic publication logic duplicated or incomplete (missing parent-directory
  fsync fault coverage and FD-leak proof).

Layering fixes onto the reviewed branch would mix FAIL evidence with new work.
The correction therefore starts from clean `origin/main` on a fresh plan branch
and a separate implementation worktree.

## System boundary

### In scope

- Immutable `BackupContext` construction from env with no trust-caller bypass.
- Explicit `CONVMEM_BACKUP_PROFILE=legacy-chroma|complete-data-v2`.
- Centralized Restic boundary in `restic_snapshot.py`.
- Deep safety orchestration in `backup_workflows.py` with zero legacy fallback
  selection.
- Reusable `atomic_write_text()` for JSONL and authoritative JSON reports.
- Closed `StateSpec` restore matrix in `complete_data_restore.py`.
- Pre-snapshot capture evidence `.convmem-backup-evidence.json` inside the data
  root.
- Hermetic consumer-wide proof, systemd/docs updates, and exact-SHA review.
- Recording `b6284ad…` as Codex FAIL without altering that branch.

### Out of scope

- Editing, rebasing, cherry-picking, or rehabilitating `492e6e7…` or
  `b6284ad…`.
- Universal Tier-1 writer coordination or participation.
- Global quiescence, freeze/thaw, or a shared checkpoint protocol.
- Adding the Restic gate to every Chroma mutation.
- A general backup/storage-provider abstraction.
- Neutral Core, Office Team, or Shadow Ledger backup redesign.
- Shadow activation or promotion to restore authority.
- Live repository changes, snapshots, offsite copies, timer installation, or
  production replacement (each needs a later separate Ryan grant).

## Architectural choices

### One deep backup context

Replace loose repository, password_file, expected_data_root, and env arguments
with an immutable `BackupContext`.

```python
@dataclass(frozen=True)
class BackupContext:
    profile: BackupProfile
    local_repository: RepositoryRef
    external_repository: RepositoryRef | None
    password_file: Path
    data_root: Path
    chroma_dir: Path
    restic_bin: Path
    subprocess_env: Mapping[str, str]
```

`BackupContext.from_env_file()` must:

- Load credentials and cache configuration once.
- Normalize and validate every path.
- Reject `/`, home, data-root/Chroma equality, and repository/password overlap.
- Construct the exact subprocess environment.
- Refuse complete-data operation unless all required fields are present.
- Provide no “trust caller” bypass.

This is preferable to fixing each call site because omitted credentials and
skipped path validation become structurally impossible.

### Explicit activation profile

Add:

```text
CONVMEM_BACKUP_PROFILE=legacy-chroma|complete-data-v2
```

Behavior:

- Missing or `legacy-chroma`: doctor emits `WARN_LEGACY_ONLY`; it never claims
  complete protection.
- `complete-data-v2`: explicit `CONVMEM_DATA_ROOT` is mandatory; no parent
  derivation.
- Complete-data v2 snapshots require tag `convmem-data-v2`.
- `convmem-chroma` may remain an additional compatibility tag but cannot
  satisfy any v2 check.
- Existing `convmem-data-v1` snapshots remain historical and do not satisfy v2
  protection.

This lets code merge before Ryan authorizes a new live snapshot without making
doctor circular or dishonest.

## Invariants

1. Complete-data v2 protection claims require profile `complete-data-v2`, tag
   `convmem-data-v2`, and exactly one recorded snapshot path equal to the
   normalized data root from `BackupContext`.
2. `convmem-chroma` and `convmem-data-v1` never prove v2 protection.
3. Every Restic selection, check, copy, or restore for safety workflows goes
   through `restic_snapshot.py`. No consumer invokes Restic directly for those
   operations.
4. Snapshot discovery never calls `restic snapshots --latest`. The resolver
   lists tagged snapshots as JSON, filters exact paths in Python, and sorts only
   validated candidates by timestamp.
5. No safety workflow may catch resolver failure and fall back to legacy
   selection. A configured failure is explicit WARN or FAIL, never PASS or
   SKIP.
6. A Restic copy has two identities: local source `S` and external destination
   `D`. Protection requires `D.original == S`; it never requires `D == S`.
7. Restic exit codes `10`, `11`, and `12` are preserved. Domain codes `20`–`32`
   apply only when Restic did not supply a reserved code.
8. Capture evidence is evidence, not authority and not a repair source.
9. Restore validators never repair. Outcome precedence:
   `BLOCKED > REPAIRABLE > ADVISORY > VALID`. Unknown state blocks.
10. Markdown reports are derived from durable JSON and may be regenerated;
    JSONL export and authoritative JSON reports use `atomic_write_text()`.
11. Until Ryan finishes the four post-merge live grants, doctor must say
    `WARN_LEGACY_ONLY`, never “complete-data protected.”

## Module boundaries

### `restic_snapshot.py` — Restic boundary

Owns:

- Context/config loading (`BackupContext`).
- Restic version and behavioral capability checks.
- Every Restic subprocess call.
- Snapshot resolution and copy lineage.
- Exit-code translation.
- Path-layout validation.

No consumer invokes Restic directly for selection, check, copy, or restore.

### `backup_workflows.py` — safety workflows

New deep orchestration module owning:

- `ensure_current_snapshot()`
- `copy_current_snapshot_offsite()`
- `check_local_health()`
- `check_offsite_health()`
- `run_integrity_check()`
- `restore_validated_snapshot()`

Shell scripts become thin exec wrappers. Doctor calls the same health
functions. No legacy fallback selection.

### `atomic_files.py` — durable publication

One reusable primitive:

```python
atomic_write_text(path, text, *, preserve_mode=True)
```

It must:

- Create a unique sibling temporary file.
- Flush and fsync it.
- Preserve `stat.S_IMODE`.
- Publish with `os.replace`.
- Open and close the parent-directory descriptor in `try`/`finally`.
- fsync the directory.
- Remove only its own unpublished temporary file.
- Distinguish pre-publication failure from post-publication durability
  uncertainty.

Use it for JSONL export and authoritative JSON reports.

### `complete_data_restore.py` — fixed restore policy

Keep a closed `StateSpec` table rather than ad hoc if branches:

```python
StateSpec(
    path,
    authority,
    presence,
    validator,
    missing_outcome,
    repair_source,
)
```

Outcome precedence: `BLOCKED > REPAIRABLE > ADVISORY > VALID`.
Unknown state blocks. Validators never repair.

## Snapshot evidence contract

Before each v2 snapshot, atomically generate
`.convmem-backup-evidence.json` inside the data root. It records:

- Normalized original data root.
- Canonical file byte hashes.
- Approved-decision IDs and proposal linkage.
- Pending-event lifecycle fingerprint.
- Chroma collections, IDs, counts, and logical fingerprint.
- Derived export IDs/count/hash.
- Top-level inventory.
- Writer-census classification.
- Evidence schema version and capture time.

It is evidence, not authority or a repair source. Mid-capture skew becomes
detectable because restored state will disagree with the captured evidence.
This does not claim universal quiescence; it turns possible skew into a
visible restore classification.

## Restore validation rules

Required validators:

- **Chroma:** SQLite `quick_check`, required `knowledge_units` and
  `conversation_summaries`, IDs, counts, fingerprint, evidence comparison.
- **Approved decisions:** strict schema, unique `ledger_id`, proposal linkage,
  content and byte hashes.
- **Pending events:** required strict JSONL plus deterministic lifecycle
  reducer.
- **Pending projection:** compare with reducer output; drift is repairable;
  orphan/conflict/corruption blocks.
- **Derived export:** parse, compare IDs/count/hash with Chroma; Chroma is the
  named repair source only when deterministic.
- **Processed state:** distinguish ordinary rescan drift from ambiguous
  exclusion markers.
- **Queues and suppressions:** parse and validate referenced identities;
  unrecoverable intent blocks.
- **Imports:** validate inventory hashes and SQLite integrity.
- **Authorizations:** malformed or mismatched active grants block;
  historical/quarantined residue is advisory.
- **Shadow:** absent/disabled valid; inactive malformed advisory; active
  incomplete/mismatched/corrupt control blocks.
- **Scratch:** `worktrees/**` or `restore-drill/**` in snapshot contents
  returns `BLOCKED_SNAPSHOT_SCOPE_LEAK`.
- **Unknown top-level state:** `BLOCKED_UNCLASSIFIED_STATE`.

Reports must include complete snapshot identity, tree, original lineage, tags,
paths, Restic version, evidence comparisons, classifications, and steps.

## Failure semantics

| Exit | Meaning |
|---:|---|
| `0` | Valid selection or completed operation |
| `10`, `11`, `12` | Restic repository, lock, or password failures; preserve unchanged |
| `20` | Invalid or unsafe configuration/path layout |
| `21` | Restic unavailable, below 0.19.0, or missing required capability |
| `22` | Repository invocation or snapshot JSON failure |
| `23` | No required v2 tagged snapshot |
| `24` | Tagged snapshots exist but none matches the exact data root |
| `25` | Correct-path snapshot exists but is stale |
| `26` | Requested ID is absent, abbreviated, ambiguous, or invalid |
| `27` | Destination lineage is absent, ambiguous, or inconsistent |
| `28` | Snapshot, copy, check, or restore action failed outside reserved Restic codes |
| `29` | Durable report could not be written |
| `30` | Repairable derived drift; not replacement-ready |
| `31` | `BLOCKED` by canonical/control corruption |
| `32` | Restore isolation or validator-internal failure |

Domain codes `20`–`32` apply only when Restic did not supply a reserved code.

## Hybrid Five-part positioning

This correction targets Hybrid bar A. It does not imply Universal Tier-1
closure.

| Dimension | Expected new-SHA score | Basis |
|---|---|---|
| 1. Tier-1 writer census | `PASS` | Capture evidence and Execution inventory classify durable/derived mutators |
| 2. Universal snapshot participation | `NOT CLAIMED` | Universal writer gating remains out of scope |
| 3. Snapshot-safe persistence boundary | `NOT CLAIMED` | No global checkpoint/freeze protocol |
| 4. Adversarial concurrency tests | `NOT CLAIMED` | Evidence detects skew; it does not prove universal prohibited mixes |
| 5. Isolated restore invariants | `PASS` | Closed matrix + evidence comparison without the live root |

Open Five-part dimensions do not excuse an A-bar data-loss or false-green path.

## Options considered

| Option | Decision | Reason |
|---|---|---|
| Patch `b6284ad…` in place | Rejected | Would mix FAIL evidence with new work; branch stays immutable |
| Keep loose per-call credentials/paths | Rejected | Omitted validation remains possible at each site |
| Derive data root from Chroma parent under v2 | Rejected | Profile v2 requires explicit `CONVMEM_DATA_ROOT` |
| Allow legacy fallback after resolver failure | Rejected | Produces false PASS/SKIP |
| Treat evidence as repair authority | Rejected | Evidence detects skew; validators never repair from it |
| Claim complete protection after code merge | Rejected | Four live grants remain; doctor stays `WARN_LEGACY_ONLY` |
| Gate every writer / add global quiescence | Rejected | Outside Track 1 Hybrid A |

## Test strategy

- Hermetic Restic fixtures under a temporary parent with a path firewall.
- Unsafe-root, overlap, empty-capability, and codes `10`–`12` / `20`–`32`.
- Older-correct / newer-wrong fixture challenged through every consumer.
- Atomic fault points including parent-directory fsync and FD-leak zero growth.
- One restore-matrix test per row plus duplicates, orphans, invalid Shadow,
  corrupt auth/import, missing collections, and scratch leakage.
- Integrated flow:
  capture `S` → reject newer `W` → copy `S` → resolve `D.original=S` →
  integrity check `S` → restore `S` → validate evidence → retain reports.
- ShellCheck zero findings; systemd-analyze verify on temporary unit names.
- No live paths or configuration may be read during tests.

## Migration, rollout, and rollback boundaries

- Code may merge while profile remains `legacy-chroma` / unset.
- Until all four post-merge grants finish, doctor must emit
  `WARN_LEGACY_ONLY`, never “complete-data protected.”
- Post-merge grants (separate Ryan authorizations):
  1. Configuring `complete-data-v2`.
  2. Creating the first live v2 snapshot.
  3. Copying it offsite and validating lineage.
  4. Installing/enabling timers.
- Historical `convmem-data-v1` and Chroma-only snapshots remain readable but
  cannot establish v2 protection.
- Code rollback must not reintroduce legacy fallback selection as a current
  protection claim.

## Downstream handoff

Companion documents:

- [`EXECUTION-complete-data-backup-correction-v2.md`](EXECUTION-complete-data-backup-correction-v2.md)
- [`VERIFY-complete-data-backup-correction-v2.md`](VERIFY-complete-data-backup-correction-v2.md)

Ryan must approve this Architecture Direction and the Execution Plan before
Cursor receives implementation authority. Implementation must use a fresh
worktree from the approved base and must not alter `b6284ad…`.
