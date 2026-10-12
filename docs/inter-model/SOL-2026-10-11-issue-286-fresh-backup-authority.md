# Sol Backup Authority Proposal — Issue #286 Kiro Bootstrap

**Arc:** Kiro bootstrap  
**Prepared:** 2026-10-11 by Sol  
**State:** r5 consumed; `NO-GO`. Kiro and Copilot PASSed exact reviewed
revision `a3c5a9e`, Ryan granted it, and the one-shot runner safely refused on
mutation-inventory drift before creating any snapshot
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

This r5 authority proposal binds the current inventory and the most recent
valid pair as a readiness anchor:

- local snapshot
  `89aaf9ef40a1b07e95af09d0227382ce7333a4c897fd3f0da8c6382d62d63ecc`;
- offsite copy
  `995102108a10ad222f615e7cf130feb7c56ebceac19c5eeb0ebdd0562b31a4a8`;
- shared tree
  `de8888c7236881c81cfc16de67c51fe9f0168ce365f60079f0b6cb1280e524c6`.

The r5 inventory evidence was captured under ConvMem's exclusive writer lease.
It reports the same Kiro projection as r3: two conversation summaries and 17
knowledge units. After r4, an unrelated Claude transcript from
`ButsabaJobScout` was indexed as processed key
`3d87d302cb37059d89ce1fe116281badde54b339874a561f14fe85de407dc26c`,
adding one chunk and 10 units to the global processed/export roles. The current
inventory is therefore `9321f51a…56a1`. This proposal authorizes nothing by
itself.

Kiro PASSed the first r4 revision at exact commit `a9c75f1d20bb1109a229fbbdcc4be19bfa5dc87a`.
Copilot FAILed that same revision because its effective Restic executable,
mounted repository filesystem, and `America/Chicago` date boundary were not
fully bound. Sol-High adjudicated the material conflict in Copilot's favor.
This correction pins the executable by path and digest, requires the
complete-data-v2 profile, proves the repository's backing device and UUID
after mount and immediately before copy, verifies mount identity before
cleanup, and fixes both authority checks and governed date-tag generation to
`America/Chicago`.

Kiro and Copilot then PASSed corrected r4 revision `5e9d3d4`. Ryan's exact r4
grant was consumed when the runner started. It safely refused before mount or
backup because writer census detected PID `1089804`; the process exited before
it could be inspected and left no journal or process-accounting record. Result
`/tmp/convmem-kiro-replacement-backup-result-20261011-r4.json`, SHA-256
`62fb8f9d08a301b0a68c10036671e70cdd38247998faa6af854b03f0dcf96546`,
records no snapshots, exact timer restoration, inactive/disabled watcher, and
an unmounted device.

The r5 correction preserves the same refusal classes while retaining bounded
process evidence before raising: classifier, closed launcher/subcommand or
marker, PID/PPID/start ticks/UID, cwd, resolved executable, argument count,
and SHA-256 of the raw command line. It does not store raw argument text.

Kiro PASSed the first r5 revision `09ae1c8`, while Copilot FAILed that same
revision because raw caller-controlled `argv[0]` appeared in both the bounded
evidence and error string, and a path-bearing launcher value remained in the
evidence. Sol-High adjudicated the material conflict in Copilot's favor. This
correction removes raw `argv[0]` from both channels and normalizes the launcher
to the closed values `convmem` or `convmem.py`; classifier behavior and every
refusal boundary remain unchanged.

Kiro and Copilot then PASSed exact corrected revision `a3c5a9e`. Ryan granted
that reviewed packet, and the runner started once. It safely refused after
mount and before backup creation because the live mutation inventory was
`781269daffebe6ae57b7a4bb70f90a93e8b0c1ef033013042f14f84df89e018c`
instead of the granted
`9321f51a0a25cbedaaa38c631b182f768b4ac4be66c8c15cd6246676e98156a1`.
Result `/tmp/convmem-kiro-replacement-backup-result-20261011-r5.json`, SHA-256
`79ef6d4a7d8abf2946865fcb645070f06a76327af09774b29de9170031429fc7`,
records null snapshot IDs, exact timer restoration, no cleanup errors,
inactive/disabled watcher state, and an unmounted offsite device. The r5 grant
is consumed and must never be retried. The inventory drift has not been
diagnosed, and no successor authority has been prepared.

## Exact proposed runner

| Item | Bound value |
|---|---|
| Repository attachment | `docs/inter-model/attachments/issue-286-kiro-replacement-backup-runner.py.txt` |
| Attachment SHA-256 | `521fead0af08499b42ca402cd73c7510284155de339d8744c266d8c5fe51cc96` |
| Materialized path | `/tmp/convmem-kiro-replacement-backup-runner-20261011-r5.py` |
| Result path | `/tmp/convmem-kiro-replacement-backup-result-20261011-r5.json` |
| Valid local date | `2026-10-11` in `America/Chicago` |

After same-revision Kiro/Copilot PASS and Ryan's exact grant, the one-shot
operation would consist only of these commands from that exact checkout:

```bash
set -e
if findmnt -rn -S /dev/sda1 -o TARGET; then
    exit 1
fi
cp docs/inter-model/attachments/issue-286-kiro-replacement-backup-runner.py.txt /tmp/convmem-kiro-replacement-backup-runner-20261011-r5.py
chmod 0700 /tmp/convmem-kiro-replacement-backup-runner-20261011-r5.py
printf '%s  %s\n' '521fead0af08499b42ca402cd73c7510284155de339d8744c266d8c5fe51cc96' '/tmp/convmem-kiro-replacement-backup-runner-20261011-r5.py' | sha256sum --check --strict -
/home/lauer/miniforge3/envs/convmem/bin/python3.11 -I -B /tmp/convmem-kiro-replacement-backup-runner-20261011-r5.py --execute
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
   state ID, `America/Chicago` authority date, interpreter, and isolated
   `-I -B` flags. Set the process timezone to `America/Chicago` before
   importing the governed backup runtime so its date-tag generation is bound.
2. Before any operational mutation, reserve the result path with `O_EXCL`,
   mode `0600`, and a fsynced `RESERVED` marker. Convert termination signals
   into controlled failure so cleanup and final evidence complete.
3. Require the watcher to be inactive, disabled, and `MainPID=0`. Record and
   stop every installed governed ConvMem timer. Require each corresponding
   service to be `inactive` or `failed` with `MainPID=0`; restore only timers
   that were active before the operation.
4. Reject active pytest/failure-test processes, ConvMem mutation commands,
   direct source reconciliation, watcher processes, and Restic operations
   against either governed repository. Before raising, retain bounded process
   identity and matched-classification evidence without free-form arguments.
   Repeat the census inside the writer gate before the initial and final
   inventory measurements.
5. Require `/dev/sda1` initially unmounted and UUID
   `f1bd69b4-e567-4ef3-89ec-13faff0602e9` before temporarily mounting it at
   `/run/media/lauer/rxBUlauer-128Gfs`. After mount, require the repository's
   effective source, target, UUID, real path, and filesystem device number to
   match that block device. Require it to be readable, writable, and have
   available space.
6. Rebuild the governed `BackupContext`; require complete-data-v2, the exact
   data root and both repository locators, and Restic executable
   `/home/lauer/miniforge3/envs/convmem/bin/restic` with SHA-256
   `20683e7746b70e99dd0538cc2740abd222dbb6b3a6851071be9880e3fe02694c`.
   Resolve the bound readiness-anchor pair by full IDs and require its exact
   copy lineage.
7. Acquire the exclusive corpus writer gate. Compute the mutation inventory
   with `bootstrap_mutation_inventory` and
   `convmem-bootstrap-mutation-proof-v1`; require
   `9321f51a0a25cbedaaa38c631b182f768b4ac4be66c8c15cd6246676e98156a1`.
8. Recheck the Chicago date before the evidence update and immediately before
   snapshot creation. Recheck the profile and executable, then call governed
   `backup_data_root` exactly once with tag `kiro-successor-preflight`.
   Require the exact data path and complete tag set.
9. Recompute the inventory while holding the writer gate. Any difference
   stops before offsite copy and preserves the local snapshot as evidence.
10. Immediately before copying, recheck the Chicago date, executable/profile,
    and mounted repository filesystem identity. Pass the full local ID
    returned by `backup_data_root` directly to governed
    `copy_snapshot_to_external`. There is no current/latest reselection.
11. Resolve the destination by exact `original == local ID` lineage; require
    equal tree, timestamp, paths, and tags. Recompute inventory before
    releasing the writer gate.
12. Require the bound Chicago date, verify device/UUID/target/repository
    identity before unmounting, restore timer state, recheck the watcher, and
    fsync the final result. Cleanup refuses to unmount an unverified device.
    Once the runner starts, the external grant is consumed even if it refuses
    or later reboots clear `/tmp`.

The attachment contains the complete proposed invocation. It uses the
governed backup APIs and introduces no raw Restic command. Created snapshots
remain evidence and are never deleted to hide a failed qualification.

## Exact inputs and stop conditions

| Input | Required value |
|---|---|
| Mutable data root | `/home/lauer/.local/share/convmem` |
| Detached runtime | clean `/tmp/convmem-kiro-bootstrap-e798bba` at `e798bba284c96642fc31229e6375eadc26986493` |
| Current inventory digest | `9321f51a0a25cbedaaa38c631b182f768b4ac4be66c8c15cd6246676e98156a1` |
| Inventory evidence | `/tmp/convmem-kiro-current-mutation-inventory-20261011-r5.json` |
| Inventory evidence SHA-256 | `c3ee53724a060d329c4e1a9139d2ae9956db0fa0a17469b677b6cc10b87f7d9c` |
| Inventory procedure | `bootstrap_mutation_inventory` + `convmem-bootstrap-mutation-proof-v1` at runtime `e798bba…` |
| Exact source | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl` |
| Source SHA-256 | `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741` |
| Source state ID | `13c4c30c5c644a1771f0372e1b16fde35ab8cd283c26f594b96f800aad3976d2` |
| Config SHA-256 | `be9be9e963eade2a095d61fbda48a79db7e9fad4305d4af6e9c0ee68d7ce9413` |
| Authority timezone/date | `America/Chicago`; `2026-10-11` |
| Backup profile | `complete-data-v2` |
| Restic executable | `/home/lauer/miniforge3/envs/convmem/bin/restic` |
| Restic executable SHA-256 | `20683e7746b70e99dd0538cc2740abd222dbb6b3a6851071be9880e3fe02694c` |
| Local Restic repository | `/home/lauer/.local/share/convmem-restic` |
| Offsite block device | `/dev/sda1`, UUID `f1bd69b4-e567-4ef3-89ec-13faff0602e9` |
| Offsite Restic repository | `/run/media/lauer/rxBUlauer-128Gfs/convmem-backups` |
| Required backup path | `/home/lauer/.local/share/convmem` |
| Required tags | `convmem-data-v2`, `convmem-2026-10-11`, `kiro-successor-preflight` |
| Maximum writes | one `/tmp` marker/result; one complete-data evidence update; one local snapshot; one offsite copy; no prune/delete |

Any source, runtime, config, Chicago date, profile, executable, inventory,
watcher, block device, mounted filesystem residence, mountpoint, repository,
writer-census, lineage, cleanup, or timer-state mismatch produces a nonzero
result. An inventory difference after local creation stops before the offsite
copy. A final inventory difference invalidates the pair for this arc.

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
reused. The r4 backup-only grant at revision
`5e9d3d4571161269a9a0b42f0394fa419635e13d` is also consumed and must never
be retried. The sealed r3 bootstrap proposal at revision
`9d249d0c36dcf791ebc95e2516f94c5844b2b845` is unconsumed but stale and must
never be executed or reused.

## Required result

The bound result must report PASS plus full local and offsite snapshot IDs,
shared tree, timestamp, paths, tags, offsite `original`, pre/post/final
inventory digests, backup-evidence digest, pinned profile/executable identity,
Chicago date/timezone, mounted filesystem identity before copy and unmount,
timer restoration, watcher state, and unmounted offsite state. PASS permits
only later preparation of a new successor bootstrap packet. It does not
authorize that preparation or any bootstrap execution.

## TL;DR

The r4 and r5 backup grants are consumed. R5 safely refused before backup
creation on mutation-inventory drift, restored all governed state, and created
no snapshot. Its drift remains undiagnosed; no successor authority or
bootstrap operation is authorized.
