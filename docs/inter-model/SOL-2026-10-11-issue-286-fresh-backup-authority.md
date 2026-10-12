# Sol Backup Authority Proposal — Issue #286 Kiro Bootstrap

**Arc:** Kiro bootstrap  
**Prepared:** 2026-10-12 by Sol
**State:** r8 proposal only; `NO-GO` until Kiro and Copilot PASS the same
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

This r8 authority proposal binds the current inventory and the most recent
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
is consumed and must never be retried.

The r5 drift is now diagnosed. Only the global `processed` and export roles
changed; the exact Kiro projection stayed at two conversation summaries and
17 knowledge units with identical entry digests. Twenty-one appended export
records came from the same unrelated active Claude `ButsabaJobScout`
transcript already present in r5. Between two r6 diagnostic captures, eight
more records were appended for a separate Codex rollout. The later capture,
made under the exclusive writer lease, is the r6 binding:
`d7208408827927f8c0ee2b24874eb4d3b69f6c469fdaa28bfbaf66b15a3a532b`.
The unrelated sessions remain a drift risk; the runner will refuse without a
snapshot if either is indexed again before execution.

Kiro and Copilot PASSed exact r6 revision `33f7a9e`. Ryan granted that
reviewed packet, and the runner started once. The privacy-safe writer census
refused before mount or backup on PID `1201589`, classified as the closed
`convmem_write_command` / `convmem.py` / `index` form, with cwd
`/home/lauer/.cache/convmem-stage1-5550def`. The process exited before the
post-run inspection. Result
`/tmp/convmem-kiro-replacement-backup-result-20261012-r6.json`, SHA-256
`7efd323bcef1f07efdf6ab095cc28cd926bdcfc9a925f48c1224b1f405f6f191`,
records null snapshot IDs, exact timer restoration, no cleanup errors,
inactive/disabled watcher state, and an unmounted offsite device. The r6 grant
is consumed and must never be retried.

Ryan then authorized another backup-only cycle. A bounded writer census found
no active writer. Sol captured inventory
`9b7599818c1eaad927c07f46e1b9de2a175abc7cd152eba441868842ddebca12`
under the exclusive writer lease and held a 30-second quiet window. A second
bounded census also found no writer, and the drift-sensitive `processed` and
export sizes and mtimes remained unchanged. The Kiro projection remains two
conversation summaries and 17 knowledge units with the same entry digests.

Kiro and Copilot PASSed exact r7 revision
`17460c218bb38ea89025d56866dd5de9f8c0521f`. Ryan granted that reviewed
packet, and the runner started once. It safely refused before mount or backup
because the live config digest was
`a0f88897f1c1b4b1da2f7027d4d1e0673e168cdb7c7d3ea6a40457bef39c3528`
instead of the bound `be9be9e9…9413`. Result
`/tmp/convmem-kiro-replacement-backup-result-20261012-r7.json`, SHA-256
`ea117edd8244170eddad11a8a26d85fcd25c2977bfb2a55de5993a5d85f9c092`,
records null snapshot IDs and an unmounted device. The runner's systemd
observations also returned user-bus connection errors; independent host
checks confirmed that the watcher remained inactive/disabled with
`MainPID=0` and that every governed timer retained its prior state. R7 is
consumed and must never be retried.

The config change is attributable and narrow. The exact old config remains at
`/home/lauer/.config/convmem/backups/config.toml.pre-codex-admission-2026-10-12`
with the former digest. The live config adds only the merged Codex rollout
admission block, enables incremental JSONL with an empty live-source list,
and retains embedding dimension `768`; all 29 prior leaf settings are
unchanged. R8 binds that live digest rather than reverting another lane's
configuration. Its runner validates every systemd observation against closed
state sets before any operational mutation, so unavailable user-bus state is
an explicit consuming refusal. Execution must provide host user-bus access;
launching it in the restricted workspace sandbox cannot succeed.

For r8, two more bounded writer censuses around a 30-second quiet window found
no writer. A new writer-lease capture is byte-identical to r7: inventory
`9b759981…bca12`, evidence SHA-256 `12d585f1…e189`, two Kiro conversation
summaries, and 17 Kiro knowledge units. The drift-sensitive file sizes and
mtimes remained unchanged.

## Exact proposed runner

| Item | Bound value |
|---|---|
| Repository attachment | `docs/inter-model/attachments/issue-286-kiro-replacement-backup-runner.py.txt` |
| Attachment SHA-256 | `b07df36e6030de4cb918d5bc50393284306d86af63c4f8ab8dded8421bb28eee` |
| Materialized path | `/tmp/convmem-kiro-replacement-backup-runner-20261012-r8.py` |
| Result path | `/tmp/convmem-kiro-replacement-backup-result-20261012-r8.json` |
| Valid local date | `2026-10-12` in `America/Chicago` |

After same-revision Kiro/Copilot PASS and Ryan's exact grant, the one-shot
operation would consist only of these commands from that exact checkout:

```bash
set -e
if findmnt -rn -S /dev/sda1 -o TARGET; then
    exit 1
fi
cp docs/inter-model/attachments/issue-286-kiro-replacement-backup-runner.py.txt /tmp/convmem-kiro-replacement-backup-runner-20261012-r8.py
chmod 0700 /tmp/convmem-kiro-replacement-backup-runner-20261012-r8.py
printf '%s  %s\n' 'b07df36e6030de4cb918d5bc50393284306d86af63c4f8ab8dded8421bb28eee' '/tmp/convmem-kiro-replacement-backup-runner-20261012-r8.py' | sha256sum --check --strict -
/home/lauer/miniforge3/envs/convmem/bin/python3.11 -I -B /tmp/convmem-kiro-replacement-backup-runner-20261012-r8.py --execute
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
3. Require every watcher and timer observation to match a closed set of valid
   systemd active/enabled states; unavailable user-bus state refuses before
   mutation. Require the watcher to be inactive, disabled, and `MainPID=0`.
   Record and stop every installed governed ConvMem timer. Require each
   corresponding service to be `inactive` or `failed` with `MainPID=0`;
   restore only timers that were active before the operation.
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
   `9b7599818c1eaad927c07f46e1b9de2a175abc7cd152eba441868842ddebca12`.
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
| Current inventory digest | `9b7599818c1eaad927c07f46e1b9de2a175abc7cd152eba441868842ddebca12` |
| Inventory evidence | `/tmp/convmem-kiro-current-mutation-inventory-20261012-r8.json` |
| Inventory evidence SHA-256 | `12d585f11becc06defedee562f5719ff30ff4738a9305d32d7411151f8a3e189` |
| Inventory procedure | `bootstrap_mutation_inventory` + `convmem-bootstrap-mutation-proof-v1` at runtime `e798bba…` |
| Exact source | `/home/lauer/.kiro/sessions/0fdb3f7faae1e6f9/sess_2628159e-d039-4646-a208-0a10a1b3e450/messages.jsonl` |
| Source SHA-256 | `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741` |
| Source state ID | `13c4c30c5c644a1771f0372e1b16fde35ab8cd283c26f594b96f800aad3976d2` |
| Config SHA-256 | `a0f88897f1c1b4b1da2f7027d4d1e0673e168cdb7c7d3ea6a40457bef39c3528` |
| Authority timezone/date | `America/Chicago`; `2026-10-12` |
| Backup profile | `complete-data-v2` |
| Restic executable | `/home/lauer/miniforge3/envs/convmem/bin/restic` |
| Restic executable SHA-256 | `20683e7746b70e99dd0538cc2740abd222dbb6b3a6851071be9880e3fe02694c` |
| Local Restic repository | `/home/lauer/.local/share/convmem-restic` |
| Offsite block device | `/dev/sda1`, UUID `f1bd69b4-e567-4ef3-89ec-13faff0602e9` |
| Offsite Restic repository | `/run/media/lauer/rxBUlauer-128Gfs/convmem-backups` |
| Required backup path | `/home/lauer/.local/share/convmem` |
| Required tags | `convmem-data-v2`, `convmem-2026-10-12`, `kiro-successor-preflight` |
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
be retried. The r5 backup-only grant at revision
`a3c5a9e40875999dfd2575ea8d4749025f37c277` is also consumed and must never
be retried. The r6 backup-only grant at revision
`33f7a9e15daa5f6e5eba515128bf7722f5822ea4` is also consumed and must never
be retried. The r7 backup-only grant at revision
`17460c218bb38ea89025d56866dd5de9f8c0521f` is also consumed and must never
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

The r4 through r7 backup grants are consumed. R7 safely refused before mount
or backup after detecting live config drift; it created no snapshot. R8 binds
the attributable current config and the unchanged writer-lease inventory, and
adds explicit refusal for unavailable systemd state. It remains `NO-GO`
pending same-revision Kiro/Copilot PASS and Ryan's separate exact execution
grant.
