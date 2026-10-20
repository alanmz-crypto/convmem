# [Arc Codex #286] Oct 13 wedge: recovery-authority search and per-source repair packet

**Author / recipient:** Claude (Opus 5.5) → Kiro, 2026-10-20 UTC (Oct 19 CDT).
**State:** `READY_FOR_KIRO_REVIEW`. **Live repair: `NO-GO`** until Kiro reviews and Ryan grants.
**Branch:** `docs/2026-10-20-issue-286-oct13-wedge-recovery` (from `origin/main` `686d50e`).
**Authority used:** Ryan's read-only investigation brief. No live writes. Quarantine not
cleared. No journal deleted or fabricated. No runner pointed at the transaction. No provider
call. No restic restore, in place or anywhere else: restic was used only through `snapshots`,
`ls` and `dump | sha256sum` / in-memory parse. Metadata and hashes only. No session text was
printed or written.

Follows Astra's Stage 1 packet §6 (`docs/inter-model/ASTRA-2026-10-20-issue-286-kiro-stage1-packet.md`
on `docs/2026-10-20-issue-286-kiro-stage1-packet`), which left the wedge gate FAIL/UNRESOLVED
because `rollback.json` and the transaction snapshot were missing.

## 1. Bottom line

1. **The original recovery authority still exists and is byte-exact.** `rollback.json`, SHA-256
   `33ab1c3b…1c56a`, matching the transaction's bound `rollback_authority_sha256`, is in four
   local daily restic snapshots (Oct 14–17) and in the offsite copy of Oct 17. The transaction
   snapshot `snapshots/46313d43…/rollout.jsonl` (SHA-256 `ba6f350a…`, equal to the
   transaction's `prefix_sha256`) is in the same snapshots. It can also be reproduced from the
   live source file's first 6,079,972 bytes: same inode, same hash.
2. **Authoring runtime: `8a7cdab`** ("Stop the watcher retrying inter-model docs the provenance
   guard rejected", #390), the `.worktrees/runtime-main` HEAD from Oct 12 06:54 to Oct 16 21:41
   CDT. A manual Track A self-index (`convmem index --file <this rollout>`) by the Codex session
   that wrote the rollout created the transaction on Oct 13 between 17:52:35 and 17:55:00 CDT.
3. **The shared store for this source already equals the rollback before-image.** Chroma
   summary and unit rows (ids, documents, metadata), export lines, the processed entry,
   checkpoint, prepared artifacts and dedupe ledgers all match the recovered `rollback.json`.
   The wedge is now **journal-only**: an APPLYING `transaction.json` whose authority files were
   deleted. Not verified: HNSW embedding vectors (would need Chroma opened) and non-source
   invariance (the Oct 13 digest is obsolete).
4. **The authority was lost on Oct 17, not Oct 13.** Between 00:23:09 and 00:24:22 CDT, some
   process ran what matches the `3e705e4` "rolled_back" path: it restored this source's
   before-images, then `_cleanup()` removed transaction, rollback and snapshot. At 00:24:44 a
   **byte-identical `transaction.json` reappeared**. No coordinator path at `3e705e4` writes
   that, and I could not attribute either write to any agent transcript, systemd unit or watcher
   spawn. That leaves an **unexplained writer into live incremental state**, a writer-fence
   finding for Stage 1.
5. **Smallest repair: route (a), and it reduces to completing a rollback that already took
   effect.** Recover the authority into scratch, prove there that the before-image restore is a
   no-op for this source, including vectors and non-source invariance, then dispose of the
   orphan journal under a Ryan grant. The real-data converter disposition (route b) is **not
   needed** for recovery. It returns only later, as the normal way to re-admit the
   pre-transaction v1 checkpoint to semantic-v2.

## 2. Target identity (live, read-only, 2026-10-20 ~04:00Z)

| Item | Value |
|------|-------|
| Source | `/home/lauer/.codex/sessions/2026/10/13/rollout-2026-10-13T17-07-28-01a1374e-6a94-71c1-8e8d-fc2c30c4ec9c.jsonl` |
| Source stat | 15,099,601 bytes, dev 66306 / inode 18892734, mtime 2026-10-13 18:37:53 CDT (stable since) |
| Source full SHA-256 | `3c2c827ff0450da74cbf22981f540a9b351cf80e1ccf190059f58161cbced76a` (= `retry_state.prefix_digest`) |
| Live prefix 0..6,079,972 | `ba6f350a458709125d0d19058c9284b19d08db64c9dff136c3da72177ed31e48` (= transaction `prefix_sha256`) |
| Live prefix 0..1,995,036 | `7f9105962e976974f93039a1970fb36c043287ba793ecb34ac32a1ae9a7f14e1` (= checkpoint prefix / processed key) |
| State dir | `~/.local/share/convmem/incremental-jsonl/0d50863041f0fcd95dc7497d140dd7dceca1babc631838f3ef6fd548db922137` |
| `transaction.json` | `a0530661c920c17ff22679a43cd94b80e10c97dd9f872a6da47fbf622d4fa7c4`, v1, APPLYING, mtime 2026-10-17 00:24:44 CDT |
| Bound rollback | `33ab1c3ba1f7462b326bdfc3e71b7768232f924e4c913f5a78579d4b1851c56a` (file **absent** live) |
| `snapshots/46313d43…` | **absent** live (dir `snapshots/` mtime 2026-10-17 00:24:22) |
| `checkpoint.json` | `bab59aa6d987690d92e3424a30ab46f306831b97ec9e70fd3bcf2ba11da5d705`, v1, 13 records, boundary 1,995,036, mtime Oct 17 00:23:09 |
| `prepared/8dc69540….json` (pending, 35 msgs) | `d8eeebe8033d5294066e36c8053fdd091bcdd02de3987262838d70486518942b`, mtime Oct 17 00:23:09 |
| `prepared/d945d74e….json` (pre, 13 msgs) | `366e30680ac4d21a8ebeffd5166c898ffd0bb77ed3074ad9d22649090320f7c0`, mtime Oct 17 00:23:09 |
| `retry_state.json` | `101fc9cee7650568aa29adf13179c68d47f90eed000852972eeea4921be6b90e`, `recovery_unproven`, attempts_on_prefix 3, mtime Oct 17 11:26:56 |

The transaction lacks `coordinator_implementation_revision` and the v2 recovery fields that
current `main` writes, which fits a pre-semantic-v2 author.

## 3. Retained evidence found

Local repo `~/.local/share/convmem-restic` (tag `convmem-data-v2`). Every file below was hashed
via `restic dump --quiet <snap> <path> | sha256sum`. Hashes are identical in all four snapshots.

| Snapshot (CDT) | id |
|----------------|----|
| 2026-10-14 00:17:46 | `ca2a6f04` |
| 2026-10-15 00:20:55 | `7da3e6bc` |
| 2026-10-16 00:17:42 | `a045ba6a` |
| 2026-10-17 00:17:28 | `495c2d65` (`495c2d65d5f5da8b17a01367364eca5f71ad8fc2968cb62d2842e434ef1f17a3`; taken 6 min before the Oct 17 loss) |
| offsite 2026-10-17 00:17:28 | `1d4a9ff5` in `$RESTIC_EXTERNAL_REPOSITORY`; `rollback.json` hash re-verified there |

| Path under state dir (as backed up) | Size | Backup mtime (CDT) | SHA-256 | Matches |
|---|---|---|---|---|
| `rollback.json` | 2,728,383 | Oct 13 17:55:00 | `33ab1c3b…1c56a` | bound `rollback_authority_sha256` ✔ |
| `snapshots/46313d437ae4446282a752270770c614/rollout.jsonl` | 6,079,972 | Oct 13 17:52:35 | `ba6f350a…1e48` | `prefix_sha256`, `complete_boundary`, live prefix ✔ |
| `transaction.json` | 776 | Oct 13 17:55:00 | `a0530661…a7c4` | live file, byte-identical ✔ |
| `checkpoint.json` | 32,386 | Oct 13 17:45:44 | `bab59aa6…5d705` | live file ✔ |
| `prepared/8dc69540….json` | 649,711 | Oct 13 17:53:24 | `d8eeebe8…942b` | live file ✔ |
| `prepared/d945d74e….json` | 535,472 | Oct 13 17:20:02 | `366e3068…f7c0` | live file ✔ |

The Oct 18 snapshot `e496b881` already shows the post-loss layout (no rollback, empty
`snapshots/`). No `restic forget`/`prune` timer or script exists (only the backup and offsite-copy
timers), so automation will not drop these snapshots. An explicit hold tag is still advisable
(§7, Ryan-gated). Searches of `~/.config/convmem/backups`, `~/.cache/*`, other incremental state
directories and agent transcripts found no other copy of the rollback hash. The only other hits
are this investigation's own transcripts and Astra's packet.

## 4. Timeline (CDT; UTC = CDT + 5 h)

| When | Event | Evidence |
|------|-------|----------|
| Oct 13 17:19:30 | State dir / `lock.flock` created (first index of the new rollout) | backup + live mtimes |
| Oct 13 17:45:44 | v1 checkpoint published, 13 records @ 1,995,036 | checkpoint mtime |
| Oct 13 17:52:35 | Snapshot of prefix @ 6,079,972 captured, tx `46313d43…` | backup |
| Oct 13 17:53:24 | Pending prepared artifact (35 msgs) written | backup |
| Oct 13 17:55:00 | `rollback.json` + APPLYING `transaction.json` written; apply begins | backup |
| Oct 13 18:16:26 | Manual retry `convmem index --file … > /tmp/enso-session-index-retry.txt` on runtime-main enters `_roll_forward` → `_commit_generation` (rollback authority present, hash check passes) and dies in `_verify_non_source_collections` → `chroma_store.non_source_inventory_digest` → Chroma `InternalError: Error executing plan: Internal error: Error finding id` | `/tmp/enso-session-index-retry.txt` (13,580 B, traceback only) |
| Oct 13 18:37:53 | Source file reaches its final size (Codex session ended) | source stat |
| Oct 14–17 00:17 | Daily restic snapshots capture the full intact authority | §3 |
| Oct 16 21:41 | runtime-main fast-forwards `8a7cdab` → `3e705e4` (#395) | runtime-main reflog |
| Oct 17 00:23:09 | `checkpoint.json` and both `prepared/*` rewritten, each byte-identical to before | mtimes + hashes |
| Oct 17 00:24:22 | Snapshot directory removed (`snapshots/` mtime) | live mtime |
| Oct 17 00:24:44 | `transaction.json` re-created with byte-identical APPLYING content `a0530661…` | live mtime + hash |
| Oct 17 01:09 / 01:12 | runtime-main → `bd37946`; watcher started (it was not running during the loss) | reflog, journal |
| Oct 17 11:26:56 | `retry_state.json` written: `recovery_unproven`, attempts_on_prefix 3 | live |

**Authoring runtime proof.** Every convmem frame in the Oct 13 traceback matches `8a7cdab`
line for line: `incremental_jsonl.py:2632` `coordinator.run()`, `:2349` `_roll_forward`,
`:2282` `_commit_generation`, `:2036` `_verify_non_source_collections(rollback…)`,
`:1490` digest, `chroma_store.py:766` `col.get`, `ingest.py:1394` `maybe_route_incremental`.
`~/.local/bin/convmem` execs `.worktrees/runtime-main/convmem.py`. The user journal shows no
watcher or `systemd-run` index of this source between Oct 13 and Oct 20, so the writer was the
manual command. Its approval prefix (`convmem index --file <this rollout> >
/tmp/enso-session-index-retry.txt 2>&1`) appears in later Codex session state. At 17:52–17:55
runtime-main was `8a7cdab` (reflog: no change between Oct 12 06:54 and Oct 16 21:41).
Residual uncertainty: whether that working tree was clean. The reflog shows no checkout and the
traceback lines match the committed blob.

**Oct 17 loss, best fit.** Under `3e705e4`, `_roll_forward` → (`IncrementalJsonlError`) →
`_restore_replay_before_images()` runs `_restore_before_images(preserve_recovery_authority=True)`.
That rewrites checkpoint and prepared from the rollback preimages (byte-identical, consistent
with 00:23:09). Then it verifies non-source against a fresh attempt digest, re-hashes the
authority, and calls `_cleanup()`. `_cleanup()` unlinks transaction, then rollback, then the
snapshot directory (consistent with 00:24:22). That path ends in a completed source-scoped
rollback. **What I cannot explain:** a byte-identical `transaction.json` re-created 22 s after
cleanup. `3e705e4` has exactly one `_restore_before_images` caller, and it preserves
transaction/rollback. The only other transaction writers (`bootstrap_supersession.py`,
`scripts/bootstrap-incremental-jsonl.py`) are Kiro-bootstrap-only. Who ran: no watcher (it
started 01:12:58), no `systemd-run` scope, no shell-history entry, and no `index`/restore command
in any Codex, Claude, Kiro, Copilot or Cursor transcript between 03:30Z and 05:26Z. The only
convmem activity in that window was Kiro session `sess_c5d99720…`: `convmem doctor` at 05:20:36Z
(read-only at `3e705e4`), `chroma_guard.py audit` at 05:23:15Z, and the audit-timer install with
two `daemon-reload`s at 05:23:22Z. None of those writes incremental state. **Treat this as an
unidentified writer, not a solved mystery.**

## 5. Live source state vs. recovered before-image

Method: `restic dump 495c2d65 …/rollback.json` streamed into an in-memory parser
(stdin, `python3 -I`). Live Chroma was read through `chroma.sqlite3?mode=ro` with
`PRAGMA query_only=1` (no Chroma client, no HNSW access). Live export/processed/state files were
read as plain files. Only hashes, ids, counts and booleans were output.

| Surface | Before-image (rollback v2, source match ✔) | Live | Result |
|---|---|---|---|
| `conversation_summaries` | 1 row `4bb0ba9f…` | 1 row; doc hash = pre (13-msg) prepared summary, ≠ pending (35-msg) | ids ✔ document ✔ metadata (11 keys) ✔ |
| `knowledge_units` | 14 rows | 14 rows | ids ✔ documents 14/14 ✔ metadata (21 keys) 14/14 ✔; pending-generation docs 0/10 live |
| Export (`knowledge_units.jsonl`) | 14 `payload_base64` lines | 14 lines | payloads byte-identical, same order ✔ (absolute line position moved 200231→200165 from foreign-line changes; not identity) |
| `processed.json` entry | key `7f910596…`, 14 units, lineage `9b463fb1…` | same | ✔ |
| `state_files.checkpoint` | `bab59aa6…` | live checkpoint | ✔ |
| `state_files.transaction` | PREPARING preimage (`98014dc5…` short) | APPLYING `a0530661…` | expected difference (journal, preserved by design) |
| `state_files.rollback` | `null` | absent | ✔ |
| `prepared_files` | `8dc69540…`→`d8eeebe8…`, `d945d74e…`→`366e3068…` | same | ✔ |
| Dedupe ledgers | `dedupe_queue.jsonl`, `ingest_duplicate_suppressions.jsonl` captured | 0 rows tagged with tx or source in either | ✔ (restore only strips tx-tagged rows) |
| Embedding vectors | 768-d per row in rollback | **not read** (HNSW) | **unverified** |
| Non-source digest | `fa54b340…` (short hash of the Oct 13 digest JSON) | changed by later indexing | **obsolete as an oracle** |

Conclusion: on every surface checkable without opening Chroma, this source sits exactly at the
rollback before-image, which is the v1 checkpoint state. No partial apply of the pending
generation is visible. The prepared artifact for that generation is retained and reusable
(zero paid calls if it were ever replayed).

## 6. Repair options (per source, smallest first)

### R1 (recommended): authority-backed rollback completion

1. **Scratch recovery (no live writes; can be granted separately from the live step).**
   `restic restore 495c2d65 --target <fresh 0700 scratch> --include` exactly the two paths
   (`rollback.json`, `snapshots/46313d437ae4446282a752270770c614/rollout.jsonl`), never
   in place. Verify `33ab1c3b…` / `ba6f350a…` and the snapshot's equality with the live source
   prefix. Cross-check one file against offsite `1d4a9ff5`.
2. **Scratch proof.** In an isolated data root (own `HOME`/config, network denied, no provider
   key): a Chroma copy from a fresh writer-fenced restic snapshot, plus copies of export,
   processed, dedupe and this one state directory with the recovered authority placed back
   byte-exact. Drive the v1 recovery once for this source with a v1-compatible runtime.
   `3e705e4` is the right choice because its rollback path uses a fresh non-source attempt
   digest. `8a7cdab` re-verifies against the obsolete Oct 13 digest, so it can only refuse or
   fail on today's store. Current `main` refuses v1 by design (`v1 transaction requires
   original runtime`). Acceptance:
   (i) outcome `rolled_back`;
   (ii) source rows, **including embedding vectors**, export payloads, processed, checkpoint
   and prepared byte/hash-equal before and after;
   (iii) non-source digest equal before and after;
   (iv) only this state dir's `transaction.json`, `rollback.json` and `snapshots/<tx>` removed;
   (v) zero HTTP attempts.
   If the runtime instead attempts `replay_forward` and commits the 35-message generation, stop
   and report. That is a different (forward) disposition that needs Kiro's ruling (§8 Q2).
3. **Live disposition (Ryan grant, writer window, source held throughout).** Archive
   (copy-first, 0700 dir, SHA manifest) the live `transaction.json`, `retry_state.json`,
   `checkpoint.json`, `prepared/*` and the recovered authority. Then take one of:
   - **R1-A (code-native):** place the two recovered files back byte-exact and run the
     `3e705e4` recovery once for this source only. It performs Chroma upserts of identical rows
     under `index_write_flock`. Real shared-store writes, on an engine with a heap-corruption
     history.
   - **R1-B (minimal-mutation):** since step 2 proved the restore is a no-op, close the orphan
     journal by moving `transaction.json` into the archive. Do not delete it, and leave Chroma,
     export and processed untouched. This is what the completed Oct 17 rollback would have
     left, minus the unexplained re-creation.

   Kiro decides whether R1-B counts as "deleting a journal". My view: archive-move after
   authority-backed no-op proof is a disposition, not fabrication. Afterwards, clear the retry
   hold only as part of the same grant. The source keeps its v1 checkpoint (13 records @
   1,995,036). The remaining ~13.1 MB of the source is unindexed either way.
4. **Re-admission (separate decision, paid).** The v1 checkpoint then needs the planned
   real-data v1→semantic-v2 converter or the current full-rebuild route (#402 extended it to
   old-format Codex checkpoints; shared `allow_full_rebuild=true`). That spends DeepSeek calls
   on the whole 15.1 MB file. It is out of this packet's scope and should be costed with the
   Arc Codex burn.

### R2: replay forward under the original runtime

Re-apply the pending 35-message generation from the retained prepared artifact (no provider
calls) and commit a v1 checkpoint @ 6,079,972. Not recommended. It needs the obsolete Oct 13
non-source digest to match at `8a7cdab` (it cannot), or a `3e705e4` replay that then still
needs conversion. It also mutates more shared state than R1 for no lasting benefit.

### R3: converter disposition (route b)

Only if step 1 fails (backup unreadable or hash mismatch). It is not needed today: the
authority is recoverable in two repositories.

## 7. What this means for Stage 1 (Astra §6 / Kiro's wedge gate)

- **Upgrade from "authority missing" to "authority recovered; live state equals
  before-image".** That removes the torn-shared-store premise for this source on every
  plain-file and SQLite-metadata surface. Vectors and non-source invariance still need the
  scratch proof.
- **New blocker for the writer-fence gate:** an unidentified process wrote into the live
  incremental state on Oct 17 00:23–00:24 with no systemd, watcher or transcript trace, and
  its last write recreated a journal. Stage 1's "no other writer" precondition needs this
  explained or structurally fenced (for example, owner-only lock plus audit event on every
  state-dir write).
- **Ryan-gated hygiene, not done here:** `restic tag --add hold-issue-286-wedge` on local
  `ca2a6f04` and `495c2d65` and offsite `1d4a9ff5`, so a future prune policy cannot drop the
  only copies. This is a repository metadata mutation; not performed.
- The second retained transaction (excluded Kiro source `sess_2628159e…`, tx `18d83bf3…`,
  `transform_failed`) is untouched and still needs its own disposition.

## 8. Questions for Kiro

1. Accept R1 (rollback completion) as the per-source disposition, given that live
   state = before-image?
2. If the `3e705e4` scratch run chooses `replay_forward` rather than rollback, should the packet
   stop (my default) or accept a forward commit?
3. R1-A vs R1-B for the live step: is archive-move of the orphan `transaction.json` after
   no-op proof acceptable, or must the authority be re-placed and the code path run live?
4. Is the unexplained 00:24:44 re-creation a hard Stage 1 blocker, or acceptable with a fence
   plus monitoring?
5. Acceptance list for the scratch proof: is §6 step 2 (i)–(v) sufficient, or do you also
   want a hermetic replay of the Oct 17 sequence to reproduce the re-creation?

## 9. Verification of this packet

- Every hash in §§2–3 was recomputed in this session. Restic hashes came from `restic dump`
  streams. No file was restored, and nothing under `~/.local/share/convmem` or the source was
  modified. Restic was run with `snapshots`, `ls -l --recursive` and `dump` only.
- Live Chroma was read solely via SQLite `mode=ro` + `query_only`. No Chroma client or HNSW
  segment was opened. No `convmem` index, watch, clear-quarantine, bootstrap or recovery
  command was run. `convmem doctor`/`brief`/`unresolved` and two ledger searches only.
- Transcript searches extracted timestamps and command lines from agent sessions to attribute
  writers. Nothing from the wedged rollout's own content was read beyond byte lengths and
  prefix hashes.
- Code facts are from `git show <rev>:<path>` for `8a7cdab`, `3e705e4` and `686d50e`. No checkout
  was switched.
- Not done: scratch restore, Chroma vector comparison, non-source digest, any repair.

I finished: [Arc Codex] read-only Oct 13 wedge recovery-authority search and repair packet.
Next step: Kiro reviews this packet (R1 disposition, live-step variant, unexplained writer).
Next lane: Kiro, then Ryan for the scratch-restore grant and, later, the live disposition grant.
See my work: `docs/inter-model/CLAUDE-2026-10-20-issue-286-oct13-wedge-recovery-packet.md` on
branch `docs/2026-10-20-issue-286-oct13-wedge-recovery`.

**TL;DR:** [Arc Codex] The Oct 13 wedge's rollback authority (`33ab1c3b…`) and snapshot
(`ba6f350a…`) survive byte-exact in local restic Oct 14–17 and offsite Oct 17. The transaction
was authored by runtime-main `8a7cdab` via a manual self-index. The live store for this source
already equals the rollback before-image, so the wedge is a journal-only orphan created when
something recreated `transaction.json` after a completed Oct 17 rollback. Recommended repair:
scratch-restore the authority, prove a no-op rollback with `3e705e4`, then close the journal
under a Ryan grant. The converter route is not needed for recovery.

<!-- src: ./ASTRA-2026-10-20-issue-286-kiro-stage1-packet.md (branch docs/2026-10-20-issue-286-kiro-stage1-packet) — wedge facts this packet resolves -->
<!-- src: ../../incremental_jsonl.py — roll-forward, before-image restore and cleanup paths (also at 8a7cdab, 3e705e4) -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc brief; not updated by this read-only packet -->
