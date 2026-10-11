# Sol Backup Authority Proposal — Issue #286 Kiro Bootstrap

**Arc:** Kiro bootstrap  
**Prepared:** 2026-10-11 by Sol  
**State:** corrected proposal only; `NO-GO` until Kiro and Copilot PASS the
same exact revision and Ryan authorizes that reviewed revision
**Scope:** one replacement local Restic snapshot and one exact offsite copy;
no bootstrap, provider transport, source operation, or watcher change

## Decision consequence

The first 2026-10-11 backup pair is internally valid but cannot protect a new
successor bootstrap proposal. The local snapshot
`f8d69dc1199636f66d6216f0325cf4218c566c829907dd205c244d00115c324b`
and its offsite copy
`a38bd4c7bfac4aa5c44634674138fa9c65f83cf37d7b3025c952b5368786f449`
share tree `84795d75a083f7a3898617e1c751a41f3863ddc2e32050d321568cbc89851084`,
timestamp `2026-10-11T00:18:59.640911-05:00`, path
`/home/lauer/.local/share/convmem`, and the required complete-data tags. The
offsite snapshot's `original` field equals the full local ID.

At `2026-10-11T00:36:40.664144791-05:00`, an older checkout appended two
mocked HTTP 402/503 test rows to live `synthesis_failures.jsonl`. PR #384's
isolation fix is on `main` as
`6a23aa93184460ed853996608bb28190c61f8d89`, but stale checkouts can still run
the older test code.

Ryan later authorized the exact reviewed runner at commit
`a9f2acf753994fec078d80b39b34d387dc652fd4`. It safely refused before backup
creation because the bound mutation inventory had become stale. A prior
handoff explicitly indexed this Codex session at `2026-10-11T12:25-05:00`;
that one-chunk reindex pruned 13 stale units and wrote 8 units, updating only
the global `processed.json` and `knowledge_units.jsonl` mutation-proof roles.
The failure result is
`/tmp/convmem-kiro-replacement-backup-result-20261011.json`, SHA-256
`6b57b6ec135360580f1b12720766d7099329943dd6ef9e4ae6efcb7a74676f99`.
It reports no local or offsite snapshot, successful timer restoration, an
inactive/disabled watcher, and an unmounted offsite device. That grant is
consumed and must never be reused.

The current predecessor mutation-inventory digest is now
`0ecb33ea8a62be7fd4d0faeee30929cefbca04d001b59be8459b2a1616a9b27b`.
The exact Kiro projection remains 2 summaries and 17 knowledge units; the
failure ledger, queues, checkpoint, rollback, and prepared cache also remain
unchanged from the prior authority.

Kiro and Copilot PASSed the current-inventory correction at exact commit
`4fd5ef37d8079891b5470b09770092ce286b4ea1`. Ryan's r2 grant then safely
refused before inventory measurement or backup creation because
`convmem-restic-external.service` was in systemd state `failed`. Journal and
unit evidence show that service had exited 17 minutes earlier with
`MainPID=0`; no process was active. The runner had incorrectly treated the
persistent `failed` state as non-quiescent. The r2 result is
`/tmp/convmem-kiro-replacement-backup-result-20261011-r2.json`, SHA-256
`537ed562edc45d97482d64104e288f9d7fe4cabecfe4d85abf2990639a817950`.
It reports no local or offsite snapshot and successful cleanup. The r2 grant
is consumed and must never be reused.

This revision accepts only systemd service states `inactive` or `failed` and
separately requires `MainPID=0`. Active, activating, reloading, deactivating,
or any nonzero PID still refuses. The observed state and PID for every
governed service are retained in the result.

Kiro PASSed the earlier proposal at exact commit
`4d7741a58c242bac0b0cdac91e093405c6a2feb9`. Copilot FAILed that same
revision because it did not bind a concrete governed command that creates a
new same-day tagged snapshot and hands the returned full ID directly to the
offsite copy. Sol-High accepted Copilot's finding. Sol-High also confirmed
that raw Restic is unnecessary: the existing governed
`backup_data_root(..., extra_tags=...)` and
`copy_snapshot_to_external(ctx, source.id)` APIs provide the required
boundary.

This correction binds those APIs in one reviewed runner. It authorizes
nothing by itself.

Copilot then FAILed exact commit
`60373685883a5780e588e96b1da56211f7d0feb4` on two execution-boundary gaps:
the process census did not recognize the real `convmem.py <command>` forms,
and the result path was not reserved until after the backup/copy work. This
revision corrects both gaps. It also revalidates a clean runtime tree before
import, pauses every installed ConvMem timer, checks device identity before
mount, and binds isolated Python execution.

Copilot FAILed the next exact revision,
`270705a1f9dd65054f1d3625be8c44d861d1c495`, solely because the bound
`/usr/bin/python3 -I` lacks `chromadb` and cannot import the reviewed runtime.
That audit confirmed the writer-census and early-reservation blockers were
closed. This revision binds the ConvMem environment's Python interpreter and
extends the census to the remaining known mutation commands and direct
reconciler form.

Copilot FAILed exact revision
`524bb15598d94ef2d2c0a6c88fee3010309c55b2` on one shell guard: `! findmnt`
is exempt from Bash `set -e`, so a mounted device did not stop the command
block before runner invocation. That audit confirmed the interpreter and all
prior corrections. This revision uses an explicit conditional exit and makes
the runner enforce its bound interpreter plus `-I -B` flags.

## Exact reviewed runner

| Item | Bound value |
|---|---|
| Repository attachment | `docs/inter-model/attachments/issue-286-kiro-replacement-backup-runner.py.txt` |
| Attachment SHA-256 | `8c87799a39e394e4495af2dfc2d4828e0282d669683ef7e3573553266e0e001b` |
| Materialized path | `/tmp/convmem-kiro-replacement-backup-runner-20261011-r3.py` |
| Result path | `/tmp/convmem-kiro-replacement-backup-result-20261011-r3.json` |
| Valid local date | `2026-10-11` in `America/Chicago` |

After Ryan grants the exact reviewed revision and attachment digest, the
named one-shot operation consists of these commands from that exact checkout:

```bash
set -e
if findmnt -rn -S /dev/sda1 -o TARGET; then
    exit 1
fi
cp docs/inter-model/attachments/issue-286-kiro-replacement-backup-runner.py.txt /tmp/convmem-kiro-replacement-backup-runner-20261011-r3.py
chmod 0700 /tmp/convmem-kiro-replacement-backup-runner-20261011-r3.py
printf '%s  %s\n' '8c87799a39e394e4495af2dfc2d4828e0282d669683ef7e3573553266e0e001b' '/tmp/convmem-kiro-replacement-backup-runner-20261011-r3.py' | sha256sum --check --strict -
/home/lauer/miniforge3/envs/convmem/bin/python3.11 -I -B /tmp/convmem-kiro-replacement-backup-runner-20261011-r3.py --execute
```

`set -e` makes a digest mismatch stop before the runner. The detached runtime
at `/tmp/convmem-kiro-bootstrap-e798bba` must already exist at exact commit
`e798bba284c96642fc31229e6375eadc26986493`; runtime materialization is not
part of this backup grant. The runner requires its worktree to be clean before
importing from it. It also requires the exact bound interpreter with isolated
mode and bytecode writes disabled. It refuses any existing result path,
including a dangling symlink. It has not been executed during packet
preparation.

## One-shot behavior

The runner performs this closed sequence:

1. Revalidate detached runtime revision and clean worktree before importing
   any runtime code, then revalidate them inside the operation. Require
   `e798bba284c96642fc31229e6375eadc26986493`, config digest
   `be9be9e963eade2a095d61fbda48a79db7e9fad4305d4af6e9c0ee68d7ce9413`,
   exact Kiro source digest
   `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741`,
   source state ID, and the local authority date.
2. Before any timer, mount, corpus, or backup mutation, reserve the result path
   with `O_EXCL`, reject symlinks, set mode `0600`, and fsync a `RESERVED`
   one-shot marker. Convert `SIGHUP`, `SIGINT`, `SIGQUIT`, `SIGTERM`,
   `SIGALRM`, `SIGUSR1`, and `SIGUSR2` into controlled failure so cleanup and
   final evidence run; signals during cleanup cannot interrupt restoration.
3. Require the watcher to be inactive, disabled, and have `MainPID=0`.
   Record and stop every installed ConvMem timer, then require each matching
   service to be quiescent: state `inactive` or `failed`, with `MainPID=0`.
   Record every observed service state/PID and restore only timers that were
   active beforehand.
4. Reject active stale failure tests, ConvMem pytest processes, known
   `convmem`/`convmem.py` mutation commands (including `ask`, agent-run,
   Shadow, and writer-census commands), the direct source-reconciler form,
   watcher processes, and Restic operations against either governed
   repository. Repeat the census inside the writer gate before the first
   inventory and before final inventory. A denied `/proc/<pid>/cwd` read does
   not suppress command-line classification.
5. Require `/dev/sda1` to be initially unmounted and require UUID
   `f1bd69b4-e567-4ef3-89ec-13faff0602e9` before mounting it at
   `/run/media/lauer/rxBUlauer-128Gfs`.
   Require the repository to be readable, writable, and have available space.
6. Rebuild `BackupContext` from the governed environment and require the exact
   data root and both repository locators. Before the first backup write,
   resolve the known valid old local/offsite pair by full ID and require its
   copy lineage.
7. Acquire the exclusive corpus writer gate. Compute the predecessor mutation
   inventory with `bootstrap_mutation_inventory`; bind its digest using
   `convmem-bootstrap-mutation-proof-v1`; require exact digest
   `0ecb33ea8a62be7fd4d0faeee30929cefbca04d001b59be8459b2a1616a9b27b`.
8. Capture complete-data evidence, then call the governed
   `backup_data_root` API exactly once with extra tag
   `kiro-successor-preflight`. Require exact path and the complete tag set.
9. Recompute the inventory while holding the writer gate. Any difference
   stops before offsite copy and preserves the local snapshot as evidence.
10. Pass the full ID returned by `backup_data_root` directly to the governed
   `copy_snapshot_to_external` API. There is no current/latest reselection.
11. Resolve the destination through exact `original == local ID` lineage and
    require equal tree, time, paths, and tags. Recompute the inventory again
    before releasing the writer gate.
12. Require the operation to remain on the bound local date. Unmount the
    offsite device, restore the timers to their exact prior active/enabled
    states, recheck the watcher state, and overwrite the reserved marker with
    one fsynced final result. Any failure leaves the reserved path in place so
    a second snapshot/copy invocation cannot start during the current boot.
    Once the runner starts, the external grant is consumed even if a later
    reboot clears `/tmp`; it must never be reused.

The attachment contains the complete invocation. Neither
`backup_workflows.py ensure` nor `backup_workflows.py copy-offsite` is used,
because those wrappers reselect a current snapshot. No raw Restic invocation
is introduced; all Restic I/O remains in `restic_snapshot.py`.

## Exact inputs and stop conditions

| Input | Required value |
|---|---|
| Mutable data root | `/home/lauer/.local/share/convmem` |
| Detached runtime | clean `/tmp/convmem-kiro-bootstrap-e798bba` at `e798bba284c96642fc31229e6375eadc26986493` |
| Current inventory digest | `0ecb33ea8a62be7fd4d0faeee30929cefbca04d001b59be8459b2a1616a9b27b` |
| Inventory evidence | `/tmp/convmem-kiro-current-mutation-inventory-20261011-r3.json` |
| Inventory evidence SHA-256 | `e3ec2f1c5badae2307e2ef3abedec259ea4fb0bf0171ef96a0ca0a7b287faeb0` |
| Inventory procedure | `bootstrap_mutation_inventory` + `convmem-bootstrap-mutation-proof-v1` at runtime `e798bba…` |
| Local Restic repository | `/home/lauer/.local/share/convmem-restic` |
| Offsite block device | `/dev/sda1`, UUID `f1bd69b4-e567-4ef3-89ec-13faff0602e9` |
| Offsite Restic repository | `/run/media/lauer/rxBUlauer-128Gfs/convmem-backups` |
| Required coverage path | `/home/lauer/.local/share/convmem` |
| Required tags | `convmem-data-v2`, `convmem-2026-10-11`, `kiro-successor-preflight` |
| Paused timers | reconcile, external/local/ensure Restic, cross-project digest, monitor, watcher restart, CG-2 soak check |
| Maximum writes | one `/tmp` marker/result; one complete-data evidence update; one local snapshot; one offsite copy; no prune/delete |

Any source, runtime, config, date, inventory, watcher, device, mountpoint,
repository, writer-census, lineage, cleanup, or timer-state mismatch produces
a nonzero result. An existing result path or symlink stops before any
operational mutation. An inventory difference after local creation stops
before the offsite copy. A final inventory difference invalidates the pair for
this arc. Created snapshots remain evidence and are never deleted to hide a
failed qualification.

## Explicit exclusions

This proposal does not authorize:

- cleaning, truncating, or editing `synthesis_failures.jsonl`;
- bootstrap grant materialization or reading an execution-grant file;
- preparing a successor bootstrap proposal, operation ID, or authority
  fingerprint as part of this operation;
- DeepSeek or any other provider transport;
- corpus bootstrap, recovery invocation, source ingestion, or source write;
- runtime/config promotion or watcher start, enablement, or restart;
- Restic prune, forget, repair, initialization, or password changes; or
- a second local snapshot or offsite copy.

The read-only Kiro source remains outside both backup sets. The runner hashes
it only to revalidate identity; it performs no source indexing operation. A
new successor proposal is a separate later act after the replacement pair is
validated and requires its own exact binding and review. The stale proposal
`c5fec18c2403c4038740050d414cdf2d309f399d56a0cb46eb5431139b779c81`
must never be reused.

## Required result

The bound result must report PASS plus the full local and offsite snapshot
IDs, shared tree, timestamp, paths, tags, offsite `original`, pre/post/final
inventory digests, backup-evidence digest, timer restoration, watcher state,
and unmounted offsite state. The result permits only preparation of a new
successor packet. It does not authorize bootstrap execution.

## TL;DR

The old pair is valid but stale. The first reviewed runner safely refused on
later session indexing; r2 then safely refused because an already-exited
systemd service retained state `failed`. Neither run created a snapshot, and
both grants are consumed. This revision requires every governed service to be
`inactive` or `failed` with `MainPID=0`, records that evidence, and binds a
fresh r3 marker. It remains `NO-GO` until same-revision Kiro/Copilot PASS and
Ryan's new exact grant.
