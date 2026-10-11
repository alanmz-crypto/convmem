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
mocked HTTP 402/503 test rows to live `synthesis_failures.jsonl`. The current
predecessor mutation-inventory digest is therefore
`104acbef1f22f85c27380c0cda703dba051d4e0c8182f3608c64392d2e634b73`.
All other measured surfaces remain stable, including the exact Kiro
projection of 2 summaries and 17 knowledge units. PR #384's isolation fix is
on `main` as `6a23aa93184460ed853996608bb28190c61f8d89`, but stale checkouts can still
run the older test code.

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

## Exact reviewed runner

| Item | Bound value |
|---|---|
| Repository attachment | `docs/inter-model/attachments/issue-286-kiro-replacement-backup-runner.py.txt` |
| Attachment SHA-256 | `2618e24302d547a311cc1459ef24ab4bdb0b853d6ba2febdbfcccd14be1821f8` |
| Materialized path | `/tmp/convmem-kiro-replacement-backup-runner-20261011.py` |
| Result path | `/tmp/convmem-kiro-replacement-backup-result-20261011.json` |
| Valid local date | `2026-10-11` in `America/Chicago` |

After Ryan grants the exact reviewed revision and attachment digest, the
named one-shot operation consists of these commands from that exact checkout:

```bash
cp docs/inter-model/attachments/issue-286-kiro-replacement-backup-runner.py.txt /tmp/convmem-kiro-replacement-backup-runner-20261011.py
chmod 0700 /tmp/convmem-kiro-replacement-backup-runner-20261011.py
sha256sum /tmp/convmem-kiro-replacement-backup-runner-20261011.py
python /tmp/convmem-kiro-replacement-backup-runner-20261011.py --execute
```

The operator must stop unless `sha256sum` returns the bound attachment digest.
The runner refuses to overwrite an existing result file. It has not been
executed during packet preparation.

## One-shot behavior

The runner performs this closed sequence:

1. Revalidate detached runtime revision
   `e798bba284c96642fc31229e6375eadc26986493`, config digest
   `be9be9e963eade2a095d61fbda48a79db7e9fad4305d4af6e9c0ee68d7ce9413`,
   exact Kiro source digest
   `dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741`,
   source state ID, and the local authority date.
2. Require the watcher to be inactive, disabled, and have `MainPID=0`.
   Record and stop only the four named ConvMem maintenance timers; require
   their corresponding services to be inactive.
3. Reject active stale failure tests, ConvMem pytest processes, known corpus
   writers, watcher processes, and Restic operations against either governed
   repository.
4. Require `/dev/sda1` to be initially unmounted, mount it, and require UUID
   `f1bd69b4-e567-4ef3-89ec-13faff0602e9` at
   `/run/media/lauer/rxBUlauer-128Gfs`.
5. Rebuild `BackupContext` from the governed environment and require the exact
   data root and both repository locators. Before the first write, resolve the
   known valid old local/offsite pair by full ID and require its copy lineage.
6. Acquire the exclusive corpus writer gate. Compute the predecessor mutation
   inventory with `bootstrap_mutation_inventory`; bind its digest using
   `convmem-bootstrap-mutation-proof-v1`; require exact digest
   `104acbef1f22f85c27380c0cda703dba051d4e0c8182f3608c64392d2e634b73`.
7. Capture complete-data evidence, then call the governed
   `backup_data_root` API exactly once with extra tag
   `kiro-successor-preflight`. Require exact path and the complete tag set.
8. Recompute the inventory while holding the writer gate. Any difference
   stops before offsite copy and preserves the local snapshot as evidence.
9. Pass the full ID returned by `backup_data_root` directly to the governed
   `copy_snapshot_to_external` API. There is no current/latest reselection.
10. Resolve the destination through exact `original == local ID` lineage and
    require equal tree, time, paths, and tags. Recompute the inventory again
    before releasing the writer gate.
11. Require the operation to remain on the bound local date. Unmount the
    offsite device, restore the timers to their exact prior active/enabled
    states, recheck the watcher state, and write one mode-`0600` result.

The attachment contains the complete invocation. Neither
`backup_workflows.py ensure` nor `backup_workflows.py copy-offsite` is used,
because those wrappers reselect a current snapshot. No raw Restic invocation
is introduced; all Restic I/O remains in `restic_snapshot.py`.

## Exact inputs and stop conditions

| Input | Required value |
|---|---|
| Mutable data root | `/home/lauer/.local/share/convmem` |
| Current inventory digest | `104acbef1f22f85c27380c0cda703dba051d4e0c8182f3608c64392d2e634b73` |
| Inventory evidence | `/tmp/convmem-kiro-current-mutation-inventory-20261010.json` |
| Inventory evidence SHA-256 | `558fbaf70da5c04a3e62d9800857f045ac9b55c508fe75b4438673c3d406d5b4` |
| Inventory procedure | `bootstrap_mutation_inventory` + `convmem-bootstrap-mutation-proof-v1` at runtime `e798bba…` |
| Local Restic repository | `/home/lauer/.local/share/convmem-restic` |
| Offsite block device | `/dev/sda1`, UUID `f1bd69b4-e567-4ef3-89ec-13faff0602e9` |
| Offsite Restic repository | `/run/media/lauer/rxBUlauer-128Gfs/convmem-backups` |
| Required coverage path | `/home/lauer/.local/share/convmem` |
| Required tags | `convmem-data-v2`, `convmem-2026-10-11`, `kiro-successor-preflight` |
| Maximum writes | one local snapshot; one offsite copy; no prune/delete |

Any source, runtime, config, date, inventory, watcher, device, mountpoint,
repository, writer-census, lineage, cleanup, or timer-state mismatch produces
a nonzero result. An inventory difference after local creation stops before
the offsite copy. A final inventory difference invalidates the pair for this
arc. Created snapshots remain evidence and are never deleted to hide a failed
qualification.

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

The old pair is valid but stale relative to the live mutation inventory. This
corrected proposal binds one governed, date-limited runner that creates one
tagged local snapshot, passes its returned full ID directly into one offsite
copy, proves the inventory remained stable, and restores all paused services.
It remains `NO-GO` until same-revision Kiro/Copilot PASS and Ryan's exact
grant.
