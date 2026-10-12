# Sol Backup Authority Proposal — Issue #286 Kiro Bootstrap

**Arc:** Kiro bootstrap  
**Prepared:** 2026-10-11 by Sol  
**State:** r4 proposal only; `NO-GO` until Kiro and Copilot PASS the same
exact pushed revision and Ryan grants that reviewed revision
**Scope:** one new local complete-data Restic snapshot and one exact offsite
copy; no bootstrap, provider transport, source operation, proposal generation,
or watcher change

## Decision consequence

Ryan's reviewed r3 bootstrap grant stopped before bootstrap, corpus mutation,
dimension probing, or provider transport. Another lane had indexed one Cursor
transcript after the r3 backup pair was created. That changed the predecessor
mutation inventory from
`0ecb33ea8a62be7fd4d0faeee30929cefbca04d001b59be8459b2a1616a9b27b` to
`85566aed12281c21867eef033016e5292e31f994157fa0559f18dc2363641e6a`.

The r3 bootstrap proposal remains sealed and unconsumed, but its backup and
inventory binding is stale. It must not be executed, edited, regenerated, or
reused. A new successor bootstrap proposal can be prepared only after this
separate backup-only operation returns a valid matching local/offsite pair.

This r4 authority proposal binds the current inventory and the most recent
valid pair as a readiness anchor:

- local snapshot
  `89aaf9ef40a1b07e95af09d0227382ce7333a4c897fd3f0da8c6382d62d63ecc`;
- offsite copy
  `995102108a10ad222f615e7cf130feb7c56ebceac19c5eeb0ebdd0562b31a4a8`;
- shared tree
  `de8888c7236881c81cfc16de67c51fe9f0168ce365f60079f0b6cb1280e524c6`.

The r4 inventory evidence was captured under ConvMem's exclusive writer lease
after the unrelated pytest run finished. It reports the same Kiro projection
as r3: two conversation summaries and 17 knowledge units. The additional
Cursor transcript accounts for the changed global `processed.json` and
`knowledge_units.jsonl` roles. This proposal authorizes nothing by itself.

## Exact proposed runner

| Item | Bound value |
|---|---|
| Repository attachment | `docs/inter-model/attachments/issue-286-kiro-replacement-backup-runner.py.txt` |
| Attachment SHA-256 | `e8cbf8827632c75f4fda58edf9d1d79f30a4002ed025668f84dcdc8580f6b6fe` |
| Materialized path | `/tmp/convmem-kiro-replacement-backup-runner-20261011-r4.py` |
| Result path | `/tmp/convmem-kiro-replacement-backup-result-20261011-r4.json` |
| Valid local date | `2026-10-11` in `America/Chicago` |

After same-revision Kiro/Copilot PASS and Ryan's exact grant, the one-shot
operation would consist only of these commands from that exact checkout:

```bash
set -e
if findmnt -rn -S /dev/sda1 -o TARGET; then
    exit 1
fi
cp docs/inter-model/attachments/issue-286-kiro-replacement-backup-runner.py.txt /tmp/convmem-kiro-replacement-backup-runner-20261011-r4.py
chmod 0700 /tmp/convmem-kiro-replacement-backup-runner-20261011-r4.py
printf '%s  %s\n' 'e8cbf8827632c75f4fda58edf9d1d79f30a4002ed025668f84dcdc8580f6b6fe' '/tmp/convmem-kiro-replacement-backup-runner-20261011-r4.py' | sha256sum --check --strict -
/home/lauer/miniforge3/envs/convmem/bin/python3.11 -I -B /tmp/convmem-kiro-replacement-backup-runner-20261011-r4.py --execute
```

The runner refuses an existing result path, including a dangling symlink. Its
detached runtime must already exist at
`/tmp/convmem-kiro-bootstrap-e798bba`, be clean, and resolve to exact commit
`e798bba284c96642fc31229e6375eadc26986493`. Runtime materialization is not
part of this proposed grant. The runner has not been executed during packet
preparation.

## One-shot behavior

The runner performs this closed sequence:

1. Revalidate the detached runtime, configuration, exact Kiro source, source
   state ID, local authority date, interpreter, and isolated `-I -B` flags.
2. Before any operational mutation, reserve the result path with `O_EXCL`,
   mode `0600`, and a fsynced `RESERVED` marker. Convert termination signals
   into controlled failure so cleanup and final evidence complete.
3. Require the watcher to be inactive, disabled, and `MainPID=0`. Record and
   stop every installed governed ConvMem timer. Require each corresponding
   service to be `inactive` or `failed` with `MainPID=0`; restore only timers
   that were active before the operation.
4. Reject active pytest/failure-test processes, ConvMem mutation commands,
   direct source reconciliation, watcher processes, and Restic operations
   against either governed repository. Repeat the census inside the writer
   gate before the initial and final inventory measurements.
5. Require `/dev/sda1` initially unmounted and UUID
   `f1bd69b4-e567-4ef3-89ec-13faff0602e9` before temporarily mounting it at
   `/run/media/lauer/rxBUlauer-128Gfs`. Require the offsite repository to be
   readable, writable, and have available space.
6. Rebuild the governed `BackupContext`; require the exact data root and both
   repository locators. Resolve the bound readiness-anchor pair by full IDs
   and require its exact copy lineage.
7. Acquire the exclusive corpus writer gate. Compute the mutation inventory
   with `bootstrap_mutation_inventory` and
   `convmem-bootstrap-mutation-proof-v1`; require
   `85566aed12281c21867eef033016e5292e31f994157fa0559f18dc2363641e6a`.
8. Capture complete-data evidence, then call governed `backup_data_root`
   exactly once with tag `kiro-successor-preflight`. Require the exact data
   path and complete tag set.
9. Recompute the inventory while holding the writer gate. Any difference
   stops before offsite copy and preserves the local snapshot as evidence.
10. Pass the full local ID returned by `backup_data_root` directly to
    governed `copy_snapshot_to_external`. There is no current/latest
    reselection.
11. Resolve the destination by exact `original == local ID` lineage; require
    equal tree, timestamp, paths, and tags. Recompute inventory before
    releasing the writer gate.
12. Require the bound local date, unmount the offsite device, restore timer
    state, recheck the watcher, and fsync the final result. Once the runner
    starts, the external grant is consumed even if it refuses or later reboots
    clear `/tmp`.

The attachment contains the complete proposed invocation. It uses the
governed backup APIs and introduces no raw Restic command. Created snapshots
remain evidence and are never deleted to hide a failed qualification.

## Exact inputs and stop conditions

| Input | Required value |
|---|---|
| Mutable data root | `/home/lauer/.local/share/convmem` |
| Detached runtime | clean `/tmp/convmem-kiro-bootstrap-e798bba` at `e798bba284c96642fc31229e6375eadc26986493` |
| Current inventory digest | `85566aed12281c21867eef033016e5292e31f994157fa0559f18dc2363641e6a` |
| Inventory evidence | `/tmp/convmem-kiro-current-mutation-inventory-20261011-r4.json` |
| Inventory evidence SHA-256 | `00b64821f258f1bfaece2696974a57d3a07630d45ea610f3eda3f1b848688b95` |
| Inventory procedure | `bootstrap_mutation_inventory` + `convmem-bootstrap-mutation-proof-v1` at runtime `e798bba…` |
| Exact source | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl` |
| Source SHA-256 | `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741` |
| Source state ID | `13c4c30c5c644a1771f0372e1b16fde35ab8cd283c26f594b96f800aad3976d2` |
| Config SHA-256 | `be9be9e963eade2a095d61fbda48a79db7e9fad4305d4af6e9c0ee68d7ce9413` |
| Local Restic repository | `/home/lauer/.local/share/convmem-restic` |
| Offsite block device | `/dev/sda1`, UUID `f1bd69b4-e567-4ef3-89ec-13faff0602e9` |
| Offsite Restic repository | `/run/media/lauer/rxBUlauer-128Gfs/convmem-backups` |
| Required backup path | `/home/lauer/.local/share/convmem` |
| Required tags | `convmem-data-v2`, `convmem-2026-10-11`, `kiro-successor-preflight` |
| Maximum writes | one `/tmp` marker/result; one complete-data evidence update; one local snapshot; one offsite copy; no prune/delete |

Any source, runtime, config, date, inventory, watcher, device, mountpoint,
repository, writer-census, lineage, cleanup, or timer-state mismatch produces
a nonzero result. An inventory difference after local creation stops before
the offsite copy. A final inventory difference invalidates the pair for this
arc.

## Explicit exclusions

This proposal does not authorize:

- bootstrap execution, recovery invocation, session indexing, or source
  writes;
- preparing, editing, or sealing a successor bootstrap proposal;
- reading or materializing a bootstrap execution grant;
- DeepSeek or any other provider transport;
- runtime/config promotion or watcher start, enablement, or restart;
- Restic prune, forget, repair, initialization, deletion, or password changes;
- cleaning or editing corpus mutation-proof roles; or
- a second local snapshot or offsite copy.

The read-only Kiro source remains outside both backup sets. The runner hashes
it only to revalidate identity. The prior backup-only grants at revisions
`a9f2acf753994fec078d80b39b34d387dc652fd4`,
`4fd5ef37d8079891b5470b09770092ce286b4ea1`, and
`bf50c6295b99e800b3438b1c4e6c3ead1936cf5b` are consumed and must never be
reused. The sealed r3 bootstrap proposal at revision
`9d249d0c36dcf791ebc95e2516f94c5844b2b845` is unconsumed but stale and must
never be executed or reused.

## Required result

The bound result must report PASS plus full local and offsite snapshot IDs,
shared tree, timestamp, paths, tags, offsite `original`, pre/post/final
inventory digests, backup-evidence digest, timer restoration, watcher state,
and unmounted offsite state. PASS permits only later preparation of a new
successor bootstrap packet. It does not authorize that preparation or any
bootstrap execution.

## TL;DR

The prior bootstrap authority stopped before bootstrap or paid calls and is
now stale because unrelated Cursor indexing changed the mutable corpus. This
r4 proposal binds the current inventory to one guarded local snapshot and one
exact offsite copy. It remains `NO-GO` pending same-revision Kiro/Copilot PASS
and Ryan's separate exact execution grant.
