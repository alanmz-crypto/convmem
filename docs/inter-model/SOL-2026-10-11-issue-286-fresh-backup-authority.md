# Sol Backup Authority Proposal — Issue #286 Kiro Bootstrap

**Arc:** Kiro bootstrap  
**Prepared:** 2026-10-11 by Sol  
**State:** proposal only; `NO-GO` until Ryan authorizes the exact reviewed
revision  
**Scope:** one replacement local Restic snapshot and one exact offsite copy;
no bootstrap or provider work

## Decision consequence

Ryan authorized one fresh local/offsite backup pair. The repository's scheduled
backup had already created local snapshot
`f8d69dc1199636f66d6216f0325cf4218c566c829907dd205c244d00115c324b`,
and Sol copied it once to offsite snapshot
`a38bd4c7bfac4aa5c44634674138fa9c65f83cf37d7b3025c952b5368786f449`.
Independent exact-ID validation passed: both snapshots have tree
`84795d75a083f7a3898617e1c751a41f3863ddc2e32050d321568cbc89851084`,
timestamp `2026-10-11T00:18:59.640911-05:00`, path
`/home/lauer/.local/share/convmem`, and tags `convmem-data-v2` and
`convmem-2026-10-11`; the offsite `original` field equals the full local ID.

That pair cannot support a new bootstrap proposal. At
`2026-10-11T00:36:40.664144791-05:00`, after the snapshot, an older checkout
appended two more mocked HTTP 402/503 rows to live
`synthesis_failures.jsonl`. The current predecessor mutation-inventory digest
is now `104acbef1f22f85c27380c0cda703dba051d4e0c8182f3608c64392d2e634b73`.
All other measured surfaces remain stable, including the exact Kiro
projection of 2 summaries and 17 knowledge units. The isolation correction is
merged on `main` through PR #384 as
`6a23aa93184460ed853996608bb28190c61f8d89`, so the new rows are consistent
with a test running code from an older checkout, not failure of the merged
code.

This proposal authorizes nothing by itself. It prepares a bounded replacement
operation that Ryan may authorize by exact file revision and SHA-256.

## Named one-shot operation

The proposed operation may perform exactly these actions once:

1. Confirm the watcher is `inactive`, `disabled`, and has `MainPID=0`.
2. Record and pause only these four timers, restoring their exact prior states
   before exit:
   - `convmem-reconcile.timer`
   - `convmem-restic-external.timer`
   - `convmem-restic-local.timer`
   - `convmem-cross-project-digest.timer`
3. Confirm no active process is running
   `tests/test_index_loud_failures.py` or another known ConvMem corpus writer.
4. Acquire the exclusive writer gate at
   `/home/lauer/.local/share/convmem/locks/chroma_writer_gate.lock`.
5. Recompute the complete predecessor mutation inventory. Require digest
   `104acbef1f22f85c27380c0cda703dba051d4e0c8182f3608c64392d2e634b73`.
   Any mismatch stops the operation without regenerating this authority.
6. Create one new complete-data-v2 Restic snapshot of exactly
   `/home/lauer/.local/share/convmem` in the configured local repository
   `/home/lauer/.local/share/convmem-restic`, adding tag
   `kiro-successor-preflight` without pruning or deleting snapshots.
7. Recompute the mutation inventory while the writer gate remains held and
   require byte-for-byte equality with step 5. A mismatch invalidates the new
   snapshot for this arc and stops before offsite copy.
8. Mount only `/dev/sda1`, UUID
   `f1bd69b4-e567-4ef3-89ec-13faff0602e9`, label `rxBUlauer-128Gfs`, at its
   normal `/run/media/lauer/rxBUlauer-128Gfs` mountpoint.
9. Copy the exact new local snapshot once to
   `/run/media/lauer/rxBUlauer-128Gfs/convmem-backups` through the governed
   `backup_workflows.py copy-offsite` path.
10. Resolve both snapshots by full ID and require equal tree, timestamp, paths,
    and tags, plus offsite `original == local snapshot ID`. Use normal locking
    locally and `--no-lock` only for read-only validation of the offsite
    repository.
11. Write local evidence under `/tmp` with mode `0600`, unmount the designated
    drive, and restore all four timer states before exit.

## Exact inputs and stop conditions

| Input | Required value |
|---|---|
| Mutable data root | `/home/lauer/.local/share/convmem` |
| Current inventory digest | `104acbef1f22f85c27380c0cda703dba051d4e0c8182f3608c64392d2e634b73` |
| Inventory evidence SHA-256 | `558fbaf70da5c04a3e62d9800857f045ac9b55c508fe75b4438673c3d406d5b4` |
| Local Restic repository | `/home/lauer/.local/share/convmem-restic` |
| Offsite block device | `/dev/sda1`, UUID `f1bd69b4-e567-4ef3-89ec-13faff0602e9` |
| Offsite Restic repository | `/run/media/lauer/rxBUlauer-128Gfs/convmem-backups` |
| Required coverage path | `/home/lauer/.local/share/convmem` |
| Required tags | `convmem-data-v2`, `convmem-2026-10-11`, `kiro-successor-preflight` |
| Maximum writes | one local snapshot; one offsite copy; no prune/delete |

Stop before creating a snapshot if the inventory digest, watcher state, device
identity, repository configuration, or writer census differs. Stop before the
offsite copy if the pre/post local-snapshot inventories differ. Stop without
substitution if the mountpoint or repository differs. Preserve any created
snapshot as evidence; do not delete it to hide a failed qualification.

## Explicit exclusions

This proposal does not authorize:

- cleaning, truncating, or otherwise editing `synthesis_failures.jsonl`;
- reading or writing a bootstrap execution-grant file;
- generating a successor bootstrap proposal or operation ID;
- DeepSeek or other paid provider transport;
- corpus bootstrap, recovery invocation, or source mutation;
- runtime or config promotion;
- watcher start, enablement, or restart;
- Restic prune, forget, repository repair, or password-copy changes; or
- any source other than the already selected read-only Kiro transcript.

The Kiro source remains outside both backup sets. Ryan has previously accepted
that disposition because the bootstrap must never write the source. A later
successor packet must continue to bind the exact source path, prefix digest
`dfea479e48e0ec3d934f3d41aa350365c746e3beaaa692a790d2fe6c1a732741`,
boundary `225091`, dimension `768`, runtime `e798bba…`, config digest
`be9be9e…`, post-overlay transform fingerprint `d2ecd101…`, two-chunk limit,
and the carried two/six-additional/eight-lifetime DeepSeek attempt budget.

## Result required from an authorized run

Return the full local snapshot ID, full offsite snapshot ID, shared tree,
timestamp, paths, tags, offsite `original` value, pre/post inventory digests,
timer restoration state, watcher state, and evidence-file SHA-256. The result
only permits preparation of a new successor proposal and same-revision review;
it does not permit bootstrap execution.

## TL;DR

The first fresh pair is internally valid but predates two new mocked ledger
rows from an older checkout, so it is not exact rollback authority for the
current corpus. This proposal defines one replacement local snapshot and one
exact offsite copy with strict inventory, writer, lineage, and no-prune checks.
It remains `NO-GO` until Ryan authorizes its exact revision.
