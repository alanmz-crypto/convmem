# [Arc Codex #286] Rollback can erase valid processed state

**For Kiro; author: Codex investigative lane, 2026-10-20 UTC.** Read-only investigation requested by Ryan. Status: **READY FOR REVIEW; no implementation or live repair performed**. The accompanying [Cursor fix brief](ASTRA-2026-10-20-issue-286-rollback-fix-brief.md) is a proposed implementation scope, not an Execute grant.

Main examined: `686d50e8e671b773cacc44c14e70aa3cbd822d2e`. Worktree: `/home/lauer/.cache/astra-rollback-gap-wt`; branch: `docs/2026-10-20-issue-286-rollback-empty-before-image`. No PR. Claude's Oct 17 collateral packet is the incident lead: `git show b347272:docs/inter-model/CLAUDE-2026-10-20-issue-286-oct17-collateral-packet.md` (branch `docs/2026-10-20-issue-286-oct17-collateral`). Its preserved evidence is `/home/lauer/.cache/convmem-evidence-oct17/`.

## 1. Findings and confidence

1. **Confirmed code defect, present in both the authoring runtime and main:** `_snapshot_before_images()` reads `_processed()`, which prefers a caller-supplied dictionary over disk. The CLI loads that dictionary **before** acquiring the incremental source lock. A waiting contender can therefore capture an empty or older processed state even after its predecessor has published a valid entry. The source lock does not refresh the dictionary.
2. **Confirmed incident damage:** the original transaction `7d95f2728d57406f91dd428fbf35d9d4` bound an internally inconsistent rollback: a complete checkpoint and matching 1-summary/10-unit projection, but `processed_preimage = {}`. The Oct 17 re-drive restored that authority and erased the valid processed entry. The same entry exists in all five preserved Oct 13–17 processed snapshots and is absent in the Oct 18 and Oct 20 copies and live.
3. **Strongly supported mechanism, not an observed process trace:** stale caller state explains the empty capture. The archived journal does not contain the caller's dictionary, PID, load time, or a per-write processed audit. It cannot conclusively distinguish stale input from a deletion between the fresh eligibility check and capture. Do not promote the inferred scheduling sequence to witnessed history.
4. **A second confirmed defect:** `_restore_processed()` performs unlocked `load → filter → update → save`. It can erase an unrelated entry committed after its load, resurrect an unrelated entry concurrently removed, erase an exclusion, or replace a later same-source generation. An atomic rename does not make this read/modify/write safe.
5. **One additional inconsistency:** live source state `914be526…` also has a valid checkpoint/projection/export but no processed entry. Its retained evidence does **not** establish a rollback cause. Its missing tail is 927,034 bytes. Do not repair it as part of R-975 by inference.
6. **A repair is exact and small:** add back R-975's one archived metadata entry, after checking its checkpoint, projection, source prefix, exclusions and current key ownership under a separately granted writer-free window. No reindex, bootstrap or provider call is needed to repair the metadata. Letting the watcher run afterwards can incur a rebuild; that is a separate decision.

## 2. Where capture happens, and which runtime wrote it

### Current main (`686d50e`)

The path is:

- `ingest.py:1732`: `_index_impl()` loads `processed.json` once before dispatch; it refreshes only after a file returns (`1789`).
- `ingest.py:1420`: `_index_one_file()` passes that dictionary into `maybe_route_incremental()`.
- `incremental_jsonl.py:554`: constructor stores it as `processed_override`.
- `incremental_jsonl.py:913–915`: `_processed()` returns the override whenever it is **not None**, including `{}`. Only `None` reloads disk.
- `incremental_jsonl.py:3371`: route acquires `SourceAdvisoryLock` after construction. The dictionary can already be stale before this acquisition, or become stale while waiting.
- `incremental_jsonl.py:2461`: `_commit_generation()` captures before-images after transforms, under `source_flock` and C1 `index_write_flock`, immediately before writing the rollback authority and the APPLYING journal.
- `incremental_jsonl.py:1755–1760`: capture uses `_processed()` and selects **every mapping whose value has `path == self.path_key`**, retaining its original key. There is no `processed[path_key]` or `processed[file_hash]` lookup here.
- `incremental_jsonl.py:1866–1877`: restore reloads disk, removes every exact-path entry, overlays the captured mapping, and calls `save_processed()` **without** `mutate_processed()` or `_processed_lock()`.
- `incremental_jsonl.py:2010–2037`: Chroma and export restore happen before processed restore. A guard placed only in `_restore_processed()` is too late to prevent a known bad journal from partially restoring other surfaces.

The lineage eligibility check uses a **different read**: `_projection_checkpoint_mismatch()` at `1260–1279` reloads disk and looks for the checkpoint lineage. A run can pass this fresh check and subsequently journal stale override state. Current `validate_rollback()` (`412–435`) checks version, required fields, source and collection-list types, but not processed/checkpoint consistency or processed-entry ownership.

### Authoring runtime (`8a7cdab`), not the Oct 17 re-drive runtime

The runtime worktree's read-only reflog shows promotion to `8a7cdab16420893fe26a2648d1d03f2b84d8589d` before the transaction. Its coordinator is byte-identical to the earlier admission implementation at `5550def` (`git diff 5550def 8a7cdab -- incremental_jsonl.py` is empty).

Independent identity check: an archive of `8a7cdab`, evaluated only through the pure authority-manifest hash code and an AST-extracted fingerprint function, yields implementation identity `4f4ed47bf42ce208e94649d1b7dcd2385eec95b9`. With the historical settings (60/10 chunking; confidence 0.6; 768 dimensions; DeepSeek v4 flash summary/distill; nomic embedding; Codex rollout adapter v1), it reproduces the full archived fingerprint:

`d53ed4fe102a16b72a2e948be6b833f76da1b257c6e8e8c4f8f90a6d51872536`.

Relevant historical coordinator locations:

- constructor override: `511`; `_processed()`: `728–731`;
- fresh disk lineage check: `1068–1087`;
- before-image selection: `1453–1486`;
- unlocked restore: `1566–1577`;
- capture in commit under `source_flock`: `2005–2020`;
- checkpoint then followers, with processed publication after `source_flock`: `2073–2078`;
- incremental source lock acquired before running/recovering, but after caller dictionary creation: `2330–2335`.

The Oct 17 re-drive used the later coordinator from `d0f987b`/`3e705e4`, as Claude's packet establishes. That later runtime rejected the old prepared fingerprint and took rollback. It did not create the empty original before-image.

## 3. What the incident evidence proves

State ID: `975fc327a8be70506775d31cb273ca7ae78c57898c210f1324f62da33dbbb3da`.

Source: `/home/lauer/.codex/sessions/2026/10/12/rollout-2026-10-12T20-20-37-01a132d8-e2f6-7580-88d7-8b2cd89ef0af.jsonl`.

The preserved Oct 17 rollback SHA-256 is `38e5dd344b4ecb74b02e6dc6dbcce03d5b2b2990ec9983dff046574a9379e349`; the transaction binds exactly that hash. The rollback's embedded checkpoint bytes hash to `acddb732b7c12c4c8a81ecc18eb3fb007b1f251670221f7c90fa923cacdcdd3b`, also the live checkpoint hash. Its projection hash recomputed from the rollback's rows equals the checkpoint lineage `82756622f9001bf73c4dd1dc38daa22ad0083fa560df9915d2d3e19dcb96614b`. The processed preimage alone is empty.

Preserved file mtimes (UTC): checkpoint `2026-10-13T01:27:15.316728`; rollback `01:29:33.284488`; APPLYING journal `01:29:33.288291`. These are file times, not transaction event telemetry. The transaction's selected prefix is `1e6083061607952e2d282d9539bc9e860167140871c1fac1a09c0d1e28074a46` at 1,259,938 bytes. The prior checkpoint represents `02b3dafe…` at 1,113,106 bytes.

**Correction to the collateral packet's causal wording:** an empty `processed_preimage` does not establish that the on-disk entry first appeared *after* capture. Capture can read an earlier in-memory dictionary. The fresh lineage guard in this same runtime normally requires the prior entry to be present before transforms begin. The snapshots establish presence by the first backup, not the exact publication instant.

A sufficient interleaving, reproduced at method level:

1. Contender B reads processed state with no source entry, before acquiring the incremental source lock.
2. A commits the first checkpoint and publishes its processed entry; A releases the incremental lock.
3. B acquires it. B reads A's checkpoint, and its fresh on-disk lineage guard passes.
4. B prepares the append, then captures rows/checkpoint from A but processed state from B's old dictionary.
5. B fails after APPLYING. Days later, rollback filters out A's valid entry and overlays `{}`.

No simultaneous Chroma writes or hash-key bug is required. Another process or an older caller snapshot is enough. The locks added after the original runtime do not fix this because the load still precedes source-lock acquisition.

Other hypotheses:

- **Hash key versus path key:** not the incident cause. Capture searches values by path. The valid hash-keyed entry is selected when supplied through a fresh dictionary.
- **Legacy entry under a different hash:** still selected if `value.path` matches exactly. A legacy reindex lacking lineage is normally caught by the fresh lineage check. A differently spelled `path` (relative path, symlink spelling, `..`) can be missed; capture does not canonicalize stored path values, whereas some ingest exclusion/prune helpers do. No such alias is needed or observed for R-975.
- **Supersede/purge:** incremental force/supersede is refused. Separate legacy/purge writers can change state; no retained evidence attributes R-975's original empty capture to them. A stale nonempty override can also resurrect a generation already removed by one of those operations.
- **Missing file:** with no override, `load_processed()` returns `{}` when the file is absent. Corrupt JSON raises; it is not silently converted to empty. A genuine first ingest with no prior checkpoint/rows may correctly have an empty before-image.

## 4. Recurrence and wider rollback effects

**The defect can recur on main. It is conditional, not every rollback.** A fresh capture without an override, no intervening edits and valid authority can be correct. A stale nonempty override is as dangerous as an empty one.

Current v2 routing refuses old pending v1 transactions before replay (`_roll_forward`, `2672+`). That blocks a direct repeat of this particular v1 replay under today's admitted Codex v2 runtime. It does **not** protect new v2 transactions: capture and restore are shared and unchanged. Kiro exact-path, bootstrap and hermetic routes use the same helpers.

Beyond the confirmed source-entry deletion:

- **Processed state:** later same-source hashes and exclusions are removed; old same-source entries can be resurrected. A preimage key currently owned by another source is overwritten by `dict.update()`. Unlocked whole-file replacement can lose an unrelated concurrent insertion/update or resurrect an unrelated concurrent deletion. These risks are outside the non-source Chroma digest check.
- **Chroma rows:** `_restore_before_images()` deletes every current source row absent from the old manifest, then upserts old rows. It does not first prove that each changed same-source row was written by this transaction. A later legacy reindex can be replaced; a purge can be undone. The non-source digest is taken immediately before rollback, so it does not prove that intervening same-source work belongs to the failed transaction. C1 serializes participating collection writes during restore; it does not establish historical ownership.
- **Export:** rollback removes current source-owned lines and inserts old source lines. Main preserves foreign lines under the export lock, but a later valid same-source export can be replaced; an old exported line can be resurrected. Unexpected source lines are diagnosed after replacement, not treated as a pre-write conflict.
- **Checkpoint/prepared files:** old checkpoint bytes are restored and prepared files absent from the preimage are deleted. Unrecognized later same-source state could be lost if introduced outside the incremental source lock or while an old journal survives. Do not confuse the journal's SHA integrity with its authority over later writers.
- **Dedupe:** current rollback filters by transaction ID rather than blindly restoring the global captured dedupe files. That is a narrower ownership rule, but `_restore_dedupe_files()` still rewrites a whole file; callers must share serialization. Its rewrite also normalizes malformed-line endings and drops blank lines. This investigation does not assert observed dedupe loss.

`_restore_replay_before_images()` on main holds C1 but not the separate `source_flock`; the outer incremental advisory lock is a different lock. Purge marks an exclusion under `source_flock` **before** acquiring C1. Soft exclusion (`exclude_cli.run_exclude_soft`) uses only the processed mutator. Therefore neither the incremental source lock nor C1 substitutes for the processed sidecar lock or a current-state conflict check.

## 5. Read-only census and limits

The [metadata census](ASTRA-2026-10-20-issue-286-rollback-census.json) records each state ID, checkpoint/transaction hashes, source-prefix checks and archive comparisons. The retained census began at `2026-10-20T08:31:17Z`:

- **91 live state directories:** 87 checkpoints, of which **85 match** the current processed key and lineage; **2 have no processed entry** (`975fc327…`, `914be526…`). Four dirs have no checkpoint: the three previously identified moved/lost dirs (`248e25cb…`, `98d65c7f…`, `e55a6f61…`) and the existing Kiro failed-bootstrap dir (`13c4c30c…`). No-checkpoint rows are not classified as rollback corruption.
- **Two retained live transactions:** the known APPLYING wedge `0d508630…`/`46313d43…` has no live rollback authority; Kiro's `13c4c30c…` transaction is `transform_failed`. Neither is a newly discovered empty before-image. The known wedge's archived rollback is consistent.
- **Five retained rollback records, all in the Oct 17 evidence root:** four match their embedded checkpoint key/lineage (`0d508630…`, `0f4d56e0…`, `1677cfce…`, `614602b2…`); **only R-975 is empty/inconsistent**. All five row-projection fingerprints match their embedded checkpoints. All four available adjacent APPLYING journals bind their rollback hashes; the separately restored wedge rollback has no adjacent archived journal in that restore set.
- **33 archived checkpoint files + 11 transaction files + 5 rollback files:** all 49 hashes checked against the eight corresponding SHA256SUMS manifests; zero mismatches. Archive copies were not edited.
- **Seven processed snapshots:** R-975 is present identically in the five Oct 13–17 copies, absent in Oct 18 and Oct 20 copies. R-914 is absent in all seven; earlier snapshots predate its source, so those absences are not evidence of loss.

Census scope: recursive rollback-name discovery throughout `/home/lauer/.local/share/convmem/` and the supplied `/home/lauer/.cache/convmem-evidence-oct17/`, plus every immediate live incremental state directory. No other `convmem-evidence*` directory was present under `.cache`. No remote/offline restic repository was scanned or restored. Deleted journals cannot be counted. This is **not** a claim that only one defective authority has ever existed.

The watcher remained active; this was not an atomic production snapshot. An earlier scan saw 90 dirs; a new source appeared during the work. The retained scan's processed file was byte-identical before/after that scan. Transaction files can appear/disappear between scans; the census records retained files at observation time, not every transient authority. No source messages or provider outputs are in the report or census.

### R-914: additional finding, cause open

Full ID: `914be5268ea5693c9e854e344f4b0d44f7c2b42c9c3105573611503e649b4818`.
Source basename: `rollout-2026-10-15T02-15-37-01a13e6a-a125-7f23-917d-53874737cda9.jsonl`.
Checkpoint key `30ada1f00350b03ccd41329ebada28ee9e9b8c4fe4ff426fae367e95d86139c9`; lineage `ebb99fe4696829e249813252385c940920c20d3831c46ee06e1d00c7e7b0ad4a`.
The source prefix and inode match. A read-only SQLite projection check found the expected 1 summary + 6 units, matching fingerprint, and all 6 export units. Its retry state says `rebuild_required:projection_checkpoint_mismatch` (mtime Oct 18 00:27:51Z). There is no retained journal here to attribute its missing entry to rollback, as opposed to failed follower publication or a later edit. The fix brief requests a separate evidence decision, not an automatic repair.

## 6. Smallest correct correction

A one-line reload fixes the demonstrated capture error but is **not** a complete correction for already-recorded bad authority or lost concurrent writes. The smallest safe change has three parts:

1. Take rollback processed state from a fresh, briefly sidecar-locked disk read; never from the pre-index override. Check that a prior incremental checkpoint's processed key and lineage are represented and consistent with captured source rows. Refuse before APPLYING if not. Allow a genuinely empty initial generation and checkpointless bootstrap according to their existing rules.
2. Validate the same relationship on recovery **before any restore writes**. An old journal with a prior incremental checkpoint but `{}` must refuse with preserved journal/snapshot; never synthesize its authority or silently delete the current entry. Also validate processed mapping shape, canonical source ownership and key collisions.
3. Restore processed state through the existing locked merge path (`mutate_processed`), with a source-slice comparison/ownership check inside that critical section. Leave unrelated keys as reloaded. Accept unchanged before-state; accept a changed state only if it is positively proven to be this transaction's published state. Unknown later state or an exclusion is a conflict, not permission to overwrite. Preserve authority on conflict. Preflight this before other writes, and repeat the check at the final processed merge to catch races.

Use `source_flock → C1` for recovery, matching commit/purge order; never add source acquisition inside C1. Do **not** hold the processed lock over model calls, Chroma work or export IO. A concurrent processed-only writer after preflight can still require a late refusal; retain recovery authority and report partial recovery rather than cleaning up or claiming atomic success. Full cross-surface linearizability needs a shared writer fence and is not delivered by the narrow patch.

For same-source projection/export changes not attributable to the transaction, choose **refusal with retained authority**, not an unconditional rewind. If corrupt prepared data makes attribution impossible, preserve evidence and require explicit recovery. This trades automatic recovery availability for avoiding deletion of another writer's work. Do not silently broaden this fix into migration, quarantine release or source reactivation.

## 7. R-975 exact repair specification — NOT EXECUTED

Authoritative donor: `/home/lauer/.cache/convmem-evidence-oct17/restic-495c2d65-store/home/lauer/.local/share/convmem/processed.json`, whole-file SHA-256 `56478757372bc6ff02cae6aafa4753ed115389aa0b6cab3f340c1d3bd16e9b7d`.

Only this mapping is to be restored:

```json
{
  "02b3dafec98565f033afd8876240e28e398ba9506ba54e05a6a6f995fc7eb20a": {
    "path": "/home/lauer/.codex/sessions/2026/10/12/rollout-2026-10-12T20-20-37-01a132d8-e2f6-7580-88d7-8b2cd89ef0af.jsonl",
    "chunks": 1,
    "units": 10,
    "incremental_jsonl_lineage": "82756622f9001bf73c4dd1dc38daa22ad0083fa560df9915d2d3e19dcb96614b"
  }
}
```

Never use the current whole-file source hash or the failed transaction's `1e608306…` key. They would claim progress beyond the committed 1,113,106-byte prefix.

For a later Kiro-reviewed/Ryan-granted repair:

1. Establish the separately approved no-writer window (E2 fence or approved E3); make a copy-first backup of processed state and preserve the target checkpoint/retry metadata. No restart/release is implied.
2. Revalidate donor hash; exact checkpoint hash `acddb732…dcdd3b`; no transaction/rollback; source device/inode and SHA-256 over exactly 1,113,106 bytes; checkpoint key/lineage; both collection manifests and projection hash; all 10 export units. Abort on any change. Current evidence: source is 3,974,891 bytes, so 2,861,785 bytes remain beyond that checkpoint.
3. Under `processed.json.lock`, reload current state. Abort if any canonical-path alias, exclusion, different same-source entry or foreign owner of the donor key exists. If the exact donor entry is already present, report an idempotent no-op. Otherwise insert exactly this one key. Preserve every unrelated key/value. Atomic write/fsync through the reviewed helper; never replace the whole file with the donor backup.
4. Re-read and verify the exact one-key delta; compare canonical hashes of all unrelated entries; checkpoint, export, collections and source must remain unchanged. Keep the writer-free window while deciding whether to resume indexing.
5. Reversal before any later indexing is allowed only if this exact inserted entry is unchanged: remove just that key under the lock, preserving unrelated entries. After a later generation publishes, do not remove its entry or restore an old whole processed file.

The payload and one-key delta were checked in memory against current metadata; no live write or executable live-repair script was run. The current v1 checkpoint and old transform fingerprint still imply a later full rebuild under today's v2/Luna route. The collateral packet estimates two chunk transforms; this investigation did not call a provider or re-plan source content. Ryan's spend/restart choice remains separate.

## 8. Verification and review request

The investigation extracted the actual `_processed`, `_snapshot_before_images`, `_restore_processed` and validator ASTs from each code revision and executed them against synthetic in-memory stores; no production imports or provider functions were used. **18/18 observations** reproduced across `8a7cdab` and `686d50e`: stale empty capture; deletion of a valid entry; correct hash-key selection control; stale nonempty capture; alias miss; exclusion deletion; foreign concurrent insertion loss; foreign-key collision overwrite; acceptance of an inconsistent rollback by validation. These are bounded method proofs, not a substitute for the coordinator/locking tests in the Cursor brief.

Read-only projection verification used SQLite `mode=ro`, `PRAGMA query_only=1`, and the preserved `projcheck.py` tool. It printed only IDs/counts/hashes/booleans. For R-975: exact manifests, projection hash and all 10 export rows match; row seq IDs 186198–186208 agree with the previously reported Oct 17 rewrite. R-914 likewise matches its projection and export. No Chroma client, live mutation, provider call, quarantine clear, configuration change, service operation, or restic operation was performed. Git and report/scratch writes are confined to the requested worktree. Track A is left to the automatic watcher rather than an explicit ingest under this no-live-writes grant.

Kiro should decide whether the three-part fail-closed correction and conservative legacy-journal policy are acceptable, then review the separate R-975 repair gates. Cursor implementation requires Ryan's Execute authorization. R-914 remains an evidence follow-up.

I finished: [Arc Codex #286] read-only investigation, census and repair specification.
Next step: Review the correction and repair policy; authorize implementation separately.
Next lane: Kiro, then Ryan, then Cursor if granted.
See my work: this report; the linked Cursor brief carries implementation acceptance criteria.

**TL;DR:** [Arc Codex #286] Stale caller state can become rollback authority in both the authoring runtime and main; unlocked restoration adds further loss risks. R-975 has a proven inconsistent before-image and exact one-entry repair. The census found one more missing processed entry (R-914), without proof of a rollback cause. No production state was changed.

<!-- src: ../../incremental_jsonl.py, ../../ingest.py, ../../purge_locks.py, ../../source_purge.py, ../../exclude_cli.py — main 686d50e capture, locking and rollback paths -->
<!-- src: /home/lauer/.cache/claude-ckpt-wt/docs/inter-model/CLAUDE-2026-10-20-issue-286-oct17-collateral-packet.md, /home/lauer/.cache/convmem-evidence-oct17/ — incident lead and preserved evidence -->
<!-- src: /home/lauer/.cache/astra-rollback-gap-wt/.tmp/rollback-gap/ — pure runtime identity and in-memory proof scratch -->
<!-- ref: ./ASTRA-2026-10-20-issue-286-rollback-fix-brief.md, ./ASTRA-2026-10-20-issue-286-rollback-census.json, ../plans/STATUS-codex-jsonl-production-integration.md — next review and current arc state -->
