# [Arc Codex #286] Oct 17 collateral packet: three lost state dirs, four re-driven transactions

**Author / recipient:** Claude (Opus 5.5) → Kiro, then Ryan. 2026-10-20 UTC.
**Asked by:** Kiro's ruling (c) in `docs/inter-model/KIRO-2026-10-20-issue-286-oct13-wedge-scratch-proof-review.md`
(branch `kiro/2026-10-20-issue-286-oct13-wedge-review`, `283968a`).
**Source facts:** §4.3 of `docs/inter-model/CLAUDE-2026-10-20-issue-286-oct13-wedge-scratch-proof-report.md`
(branch `docs/2026-10-20-issue-286-oct13-wedge-scratch-proof`, `17530e5`).
**Branch:** `docs/2026-10-20-issue-286-oct17-collateral` from `origin/main` `686d50e`. No PR.
**State:** `READY_FOR_KIRO_REVIEW`. Every live step below stays `NO-GO` until Kiro approves, Ryan grants, and
the E2 fence or a Kiro-approved E3 quiescence window exists.

**What I did not do:** I made no live writes. I made no provider calls; every sandbox run had no network route
and recorded 0 connection attempts. Every restic call used `--no-lock` and restored into new directories. I
did not tag, forget or prune any snapshot. I did not print session text. All 11 live state dirs I read are
byte-identical at the end of the session to the copies taken at 07:44Z and 07:48Z (§6).

## 1. Consequence first (for Ryan)

- **The three lost checkpoints are intact and still match live exactly.** The restic copies agree with the
  live source files, the live Chroma rows, `processed.json` and the export, byte for byte. No write has touched
  those sources' rows since the Oct 17 00:17 backup. Restoring them is safe.
- **But restoring them does not save the money Kiro expected it to save.** All three are old-format (v1)
  checkpoints with a DeepSeek-era transform fingerprint. The current runtime (`686d50e`) runs every admitted
  Codex rollout on transform contract v2, and since the Oct 19 config change it uses `gpt-6-luna` for distill.
  The fingerprints can never match, so the next run after a restore is a **full rebuild**, not "unchanged" or
  a bounded append. In the sandbox that came to 4 chunk transforms in total (1 + 2 + 1). The step-2 acceptance
  as written therefore **fails**, and §4 shows why for every config variant.
- **All four re-driven transactions rolled back, and the proof is direct.** The Crush job output records
  `live_route_refused:rolled_back:<hash>` for each one, and each hash equals that transaction's snapshot
  sha256. Three of the four sources are consistent today.
- **One source is not consistent: `975fc327…`.** The Crush-driven rollback deleted its `processed.json` entry,
  because that transaction's rollback authority recorded an empty processed preimage. The source has been
  refused since Oct 17 18:37 CDT with `rebuild_required:projection_checkpoint_mismatch`. This looks like a
  real gap in how the coordinator captures its rollback authority (§5.2).
- **The Crush session touched one more state dir than the eight enumerated** (`02a4f7b2…`, by a live CLI
  index). It also cleared the Codex watch quarantine and ran the restic snapshot and offsite-copy scripts.
  `02a4f7b2…` is consistent today (§5.3).

## 2. Step 0: evidence preserved

All evidence is in `~/.cache/convmem-evidence-oct17/` (mode 700; restored trees made read-only), 29 GiB in
total. It is not inside the restic backup set, so it is a single local copy.

| Set | Contents | Manifest (sha256 prefix) |
|---|---|---|
| `restic-495c2d65/` | 3 lost dirs (full, incl. their PREPARING journals and snapshots), the wedge's `rollback.json` + `snapshots/46313d43…/rollout.jsonl`, and the 4 re-driven dirs as of Oct 17 00:17 | `SHA256SUMS.restic-495c2d65` `11b8e95d…` (68 files) |
| `restic-495c2d65-store/` | `processed.json`, `knowledge_units.jsonl`, `chroma.sqlite3` at Oct 17 00:17 | `22e47151…` |
| `restic-{e496b881,18cb57f1,a3fb870a}/` | the 7 collateral dirs on Oct 18, 19 and 20 | `987667bb…`, `987667bb…`, `7dfc522c…` |
| `restic-{495c2d65,e496b881}-extra/` | `02a4f7b2…`, `4f87df8f…`, `d1a36b72…` | `57a60391…`, `5729c981…` |
| `restic-e496b881-store/`, `restic-*-processed/` | Oct 18 `chroma.sqlite3` + `processed.json`; `processed.json` for Oct 13–16 | `7d2bbbdc…`, `5d0848fe…` |
| `live-state-20261020T0744Z/`, `live-state-extra-…0748Z/` | `cp -a` of the 11 live dirs (8 + 3) | `1599f09a…`, `c390da3c…` |
| `livecopy/` | live `chroma.sqlite3` (SQLite backup API from a `mode=ro` connection), `processed.json`, export, copied 07:38–07:39Z | in-report checks only |
| `sandbox/` | harness tools and every run record | `SHA256SUMS.sandbox` `df968051…` |
| `RESTORE-MANIFEST.sha256`, `restore-lost-checkpoints.sh` | the 19 files to restore, and the rehearsed restore script (§7) | `3d6d87ab…`, `d0556bd7…` |

Key hashes match the earlier proof: wedge `rollback.json` `33ab1c3b…`, wedge snapshot `ba6f350a…`.

## 3. Step 1: each lost dir against live

Method: the restored checkpoint (Oct 17 00:17) against (a) the live source file (prefix sha256 up to the
checkpoint boundary, plus device/inode); (b) a consistent copy of live Chroma (source rows in both collections,
ids against the checkpoint manifest, and the coordinator's projection fingerprint recomputed from documents
and metadata); (c) the live `processed.json` entry (its key against the checkpoint prefix, and
`incremental_jsonl_lineage` against `processed_lineage_digest`); (d) export lines for the checkpoint's unit
ids. I then repeated the whole check against the Oct 17 00:17 store and diffed the two reports.

| State dir | Source (Codex rollout) | Checkpoint | Prefix / inode vs live | Chroma ids, projection fp | `processed` entry | Export | Live grew past checkpoint |
|---|---|---|---|---|---|---|---|
| `248e25cb…` | `2026-10-14T01-56-33-01a13932…` | v1 `d53ed4fe`, 7 records, 1 summary + 9 units | match / match | equal, `a4e7b602` = checkpoint | key = prefix, lineage match | 9/9 | 4,653,703 B (now 38 records, 1 chunk) |
| `98d65c7f…` | `2026-10-13T15-33-20-01a136f8…` | v1 `d53ed4fe`, 62 records, 2 + 20 | match / match | equal, `0a2d0f7c` = checkpoint | key = prefix, lineage match | 20/20 | 1,207,849 B (now 75 records, 2 chunks) |
| `e55a6f61…` | `2026-10-14T01-58-25-01a13934…` | v1 `d53ed4fe`, 40 records, 1 + 10 | match / match | equal, `158bd209` = checkpoint | key = prefix, lineage match | 10/10 | 1,073,410 B (now 50 records, 1 chunk) |

- **Writes since 00:17 Oct 17:** none to Chroma, `processed.json` or the export for these sources. The check
  report against the 00:17 store is identical to the one against live. The `processed` entries are
  byte-equal, and every source row's `seq_id` (181484–183384) is below the 00:17 maximum of 186135. Each
  source file's mtime is Oct 14–15. The only writes are to the state dirs themselves:
  1. The Crush move to `/tmp` at 05:21:25Z.
  2. The dirs' re-creation at Oct 17 18:54:26–37 CDT with a refusal-only `retry_state.json`
     (`bootstrap_required`). No watcher, reconcile, `attempts.jsonl`, `agent_runs.jsonl` or Crush record
     names that 18:54 caller. **It is unattributed, but it is not a projection write.**
- **Internal integrity:** the sandbox runs (§4) loaded each restored checkpoint through the runtime's own
  `validate_checkpoint` (raw-line coverage digest included) and reached planning. An invalid checkpoint would
  have refused with `invalid_state`.
- **The PREPARING journals in the backup are not restorable.** Each still matches the live source (snapshot =
  live prefix; `prior_checkpoint_digest` = checkpoint). Under `686d50e`, though, a v1 journal raises
  `recovery_unproven: v1 transaction requires original runtime` and wedges the source (sandbox run
  `restoredtx-live-248e25cb`).
- **Decision per dir under Kiro's rule:** no mismatch, so **restore checkpoint + prepared cache, no journal,
  no re-bootstrap**, for all three. §4 changes the cost case behind that rule, not the integrity case.

## 4. Step 2: sandbox runs on runtime `686d50e`

**Setup.** `restic --no-lock restore a3fb870a` (today, 00:41 CDT) of the data root, without the corrupt
backups, `experiments`, `worktrees`, `imports`, `backups` and `restore-drill` (12.5 GiB). The runtime was
`git archive 686d50e` (tree `b1552077…`), made read-only. The sandbox was `bwrap` with `/` read-only,
`/home/lauer` = scratch HOME, the source files bind-mounted read-only, `--unshare-net` and `--clearenv`.
The harness (`run_sbx.py` `4979b723…`) runs the unmodified CLI `convmem.py index --file <src> --now` and adds
four things:

- every `socket.connect` is stubbed to fail and recorded;
- `build_chunk_artifact` (the paid transform) records its chunk and returns `None`;
- a hard stop sits before `_commit_generation` / `_apply_prepared`;
- decision probes record each run's choices.

The sandbox store's `chroma.sqlite3`, `processed.json` and export hashes were identical before and after all
runs.

| Variant (state / config) | 248e25cb | 98d65c7f | e55a6f61 |
|---|---|---|---|
| **As-is** (today's live dirs) / live config | `bootstrap_required`, 0 calls | same | same |
| **Restored** (checkpoint + prepared) / live config (Luna, `allow_full_rebuild = true`) | `transform_fingerprint_changed` → full rebuild, planned `[0]` → stub → `transform_failed` | planned `[0, 50]` | planned `[0]` |
| Restored / live config but `allow_full_rebuild = false` | `migration_required`, 0 calls | same | same |
| Restored / pre-Luna config (`distill = deepseek-v4-flash`) | full rebuild, fingerprint `07102f02`, planned `[0]` | `[0, 50]` | `[0]` |
| Restored + old PREPARING journal / live | `recovery_unproven` (wedge), 0 calls | not run | not run |
| Restored + today's `retry_state.json` kept / live | same as restored: full rebuild planned, no retry block | not run | not run |
| Restored by the §7 script / live | full rebuild planned `[0]` | `[0, 50]` | `[0]` |

Every run made 0 connection attempts, and the hard stop never fired.

**Why it can never be "unchanged" or a bounded append here:**

1. For an admitted Codex rollout the coordinator uses transform contract v2, so its fingerprint is the v2
   descriptor digest: `347376f1` with today's models, or `07102f02` with the pre-Oct-19 models. A v1
   checkpoint carries the legacy fingerprint `d53ed4fe`, so continuity is always
   `transform_fingerprint_changed`. With `allow_full_rebuild = true` that means a full rebuild; with it off,
   `migration_required`.
2. The v1→v2 converter (`incremental_checkpoint_migration.py`, PR #399) exists but is hermetic-only
   (`CONVMEM_INCREMENTAL_ROOT`). It also checks the legacy preimage against the *current* models, so it would
   refuse to relabel DeepSeek-distilled artifacts as Luna output. It should refuse: the units really were
   made by a different model.
3. Even in the best case, with a migrated checkpoint and matching models, the saving is small. Two sources
   now fit in one chunk whose input has changed, so chunk 0 re-transforms anyway; the third (98d65c7f) would
   save only chunk 0.

**What restoring actually buys:** it re-attaches the record that describes the live rows (which 1 + 9,
2 + 20 and 1 + 10 rows belong to the incremental generation). It puts that record back into the daily restic
set, and it lets the watcher index the unindexed tails (4.6, 1.2 and 1.1 MB) without a one-shot bootstrap
grant. **It also turns on spend.** The next time the watcher indexes each source, it runs a Luna full rebuild
of 4 chunks in total, well under the cap of 10, so no further gate stops it. Leaving the dirs as they are
(`bootstrap_required`) costs nothing until someone grants a bootstrap, and that bootstrap would pay for the
same 4 chunks.

## 5. Step 3: the four re-driven transactions and the rest of the blast radius

### 5.1 Outcome: all four rolled back

| State dir / tx | Outcome | Evidence |
|---|---|---|
| `0f4d56e0…` / `8d471c42` | **rolled back** | Crush job `05D` output: `replay 8d471c42 exit 91 | live_route_refused:rolled_back:af65fe9c…` (= this tx's snapshot sha256) |
| `1677cfce…` / `d70a723d` | **rolled back** | `…rolled_back:db097ed1…` (= snapshot sha256) |
| `614602b2…` / `e3c467cf` | **rolled back** | `…rolled_back:2fcb1dc3…` (= snapshot sha256) |
| `975fc327…` / `7d95f272` | **rolled back** | `…rolled_back:1e608306…` (= snapshot sha256); checkpoint `acddb732` byte-identical before and after |

Two other observations agree with this:

- **Why each re-drive rolled back.** Every journal's prepared artifact carries `d53ed4fe`. The Crush-era code
  (`d0f987b`, identical to `3e705e4` for the coordinator) expects `684776c5`, which I recomputed from that
  runtime's own implementation revision `a4682133…` and the pre-Luna models. Validation therefore failed with
  `prepared_artifact_corrupt`, and the coordinator took the rollback branch, as the Oct 13 wedge proof showed.
- **File signatures.** The prepared before-images were rewritten byte-identical at 00:26:20, 00:29:09,
  00:31:59 and 00:34:47 CDT, and each journal, `rollback.json` and snapshot was removed.

The earlier report's "outcome not verified" came from reading only the 05:21–05:25Z extract; job `05D` was
collected at 05:34:44Z.

### 5.2 Consistency today (read-only)

| State dir | Checkpoint today | Source prefix / inode | Chroma ids, projection fp | `processed` entry | Export | Verdict |
|---|---|---|---|---|---|---|
| `0f4d56e0…` | v1 `040f5598`, committed Oct 17 20:24 CDT by a later watcher full rebuild | match, not grown | equal / match | lineage match | 7/7 | **consistent** |
| `1677cfce…` | v2 `07102f02`, Oct 19 21:44 CDT (later rebuilds Oct 17 21:30 and Oct 19) | match, not grown | equal / match | lineage match | 19/19 | **consistent** |
| `614602b2…` | v1 `040f5598`, Oct 17 21:51 CDT | match, not grown | equal / match | lineage match | 17/17 | **consistent** |
| `975fc327…` | v1 `d53ed4fe`, the pre-image (rewritten at 00:34:47 CDT) | match; grown 2,861,785 B | equal / match (rows re-written at 00:34 CDT, `seq` 186198–186208) | **missing** | 10/10 | **inconsistent** |

**Why `975fc327…` lost its `processed` entry.** The transaction's rollback authority has
`processed_preimage = {}`. `_restore_processed` replaces every entry for the path with the preimage, so the
rollback deleted the entry. That entry (key `02b3dafe…` = checkpoint prefix, lineage `82756622…` = checkpoint)
was present in every snapshot from Oct 13 00:19 to Oct 17 00:17. Timeline from restic metadata:

1. The checkpoint was written at Oct 12 20:27:15 CDT.
2. The next transaction captured its authority between 20:27:34 (snapshot) and 20:29:33 (`rollback.json`),
   with no entry for the path.
3. The entry appeared afterwards.

So the authority's processed preimage did not describe the state it would later "restore". That is a
coordinator question for Kiro, not a Crush defect: the rollback only obeyed its authority. Today the source
refuses with `rebuild_required:projection_checkpoint_mismatch` (retry state Oct 17 18:37 CDT), and its last
2.86 MB is unindexed.

The later full rebuilds on the other three (Oct 17 20:20–21:51 and Oct 19 21:41 CDT, with new prepared files
at those times) were ordinary watcher runs after the Crush session ended at 05:36Z. They are Arc Codex
spend, but not collateral.

### 5.3 Did `cc8fde6b` touch anything beyond the eight? (Kiro (c)(3))

I enumerated every tool call in the session (05:14:56–05:34:44Z), reading commands and results only.

- **One more state dir: `02a4f7b2…`** (`rollout-2026-10-13T21-08-50-01a1382b…`). At 05:20:10Z the session
  ran a live `convmem.py index --file … --now`, which returned `live_route_refused:prepared_artifact_corrupt`.
  That run discarded this source's PREPARING journal `468d9671` and its snapshot. PREPARING never writes
  Chroma, and the checkpoint and all 10 prepared files are byte-identical at 00:17, on Oct 18 and live.
  Today the source is consistent: prefix and inode match, ids and projection fingerprint are equal, and the
  `processed` lineage matches. It is refused for `frontier_violation` (Oct 17 22:25 CDT, a later run), and
  the source has grown 580,609 B.
- **Global effects:**
  - `convmem watch --clear-quarantine ~/.codex/sessions` at 05:19:17Z.
  - The restic ensure-snapshot and offsite-copy scripts at 05:18:11Z and 05:18:26Z. These are repository
    writes only, after `495c2d65` was taken.
- **Read only:** the two "unclassified" PREPARING journals, `878b7ee7` (`4f87df8f…`) and `24d93c59`
  (`d1a36b72…`). The settle scripts listed them and never wrote them. Their later changes come from watcher
  runs at 11:27, 19:28 and 22:37 CDT, and both sources are consistent today.
- **Total written by the session:** 9 state dirs (3 moved, 5 journals flipped and re-driven, and 1 journal
  dropped by the CLI index), the watch quarantine, and the restic repositories.

## 6. Verification of this report

- At 07:56Z the 11 live state dirs were byte-identical to the 07:44Z / 07:48Z evidence copies
  (`LIVE_DIRS_UNCHANGED`, `EXTRA_DIRS_UNCHANGED`). That covers the 3 lost dirs, the 4 re-driven dirs, the
  wedge `0d508630…` and the 3 extras.
- Live Chroma was read only through SQLite `mode=ro` (a backup-API copy); no Chroma client touched live data.
- The sandbox store hashes were unchanged across all 18 runs. No run attempted a connection, and no hard stop
  fired.
- In the Crush DB I read tool-call commands and results only, with no user or assistant prose.
- One slip: a broad `journalctl` read printed an unrelated line containing an account email to my terminal.
  It is not in this report or in the evidence.

## 7. Step 4: live restore packet (for Kiro)

**Gates before anything runs:**

1. Kiro approves this packet.
2. Ryan grants it.
3. The E2 owner-lock + per-write audit fence exists, **or** Kiro approves an E3 window: the watcher stopped
   and disabled with `MainPID=0`, the state-dir contents unchanged since capture (the script checks this),
   and no agent session holding a shell against the data root.
4. `convmem doctor` shows `restic_gate` PASS for today.
5. **Ryan accepts the spend in §4:** about 4 Luna chunk transforms on the next watcher pass after the restore.
   If not, defer the restore. Do not re-bootstrap instead: that costs the same and also needs a grant.

**What gets restored (all three dirs, one window).** The 19 files in `RESTORE-MANIFEST.sha256`
(`3d6d87ab…`), taken from `restic-495c2d65/`:

| Dir | Files → target `~/.local/share/convmem/incremental-jsonl/<sid>/` |
|---|---|
| `248e25cb…` | `checkpoint.json` `8c8c4bf8…`; `prepared/3dd68c35….json` `850a7794…`, `prepared/665f17b5….json` `0226228d…` |
| `98d65c7f…` | `checkpoint.json` `b57bd6b0…`; 10 prepared: `0dd27d39` `0deda6a8…`, `2117aaab` `41932faa…`, `33c2d247` `20e0f28b…`, `459bd640` `2acd84f6…`, `47be5374` `aae614df…`, `6a12a325` `e1cb0eff…`, `a61b4e8c` `cb27e09f…`, `b9c8bda7` `555d936a…`, `d6366e72` `d6ccfca1…`, `e9f716b1` `e59189a5…` |
| `e55a6f61…` | `checkpoint.json` `df187dd4…`; 4 prepared: `3a136f20` `b5890b0e…`, `99a64283` `7e6c046b…`, `cef6ffb1` `8e4a53c2…`, `dc097ef6` `54b517a2…` |

**Not restored:** `transaction.json` and `snapshots/` (they would wedge the source). **Not changed:**
`lock.flock`, `retry_state.json` (it does not block; §4), Chroma, `processed.json` and the export.

**Procedure** (the operator is Claude CLI or Cursor under the grant; one commit window; the watcher stays
stopped for the whole window):

```bash
systemctl --user disable --now convmem-watch.service convmem-reconcile.timer
systemctl --user show convmem-watch.service -p MainPID -p ActiveState   # MainPID=0, inactive
pgrep -af 'convmem(\.py)? (index|watch)' && echo STOP                   # must print nothing
convmem doctor | grep -E 'restic_gate|wedged_incremental'               # restic_gate PASS today
B=~/.cache/convmem-evidence-oct17/pre-restore-$(date -u +%Y%m%dT%H%M%SZ)
~/.cache/convmem-evidence-oct17/restore-lost-checkpoints.sh restore ~/.local/share/convmem "$B"
#   -> "VERIFY OK: 19 files match manifest; no journals"; refuses on any precondition miss
systemctl --user enable --now convmem-watch.service convmem-reconcile.timer
```

The script (`d0556bd7…`) refuses unless five checks pass:

- the manifest hash is unchanged;
- all 19 evidence files match the manifest;
- each live dir is still exactly `{lock.flock (empty), prepared/ (empty), retry_state.json (sha as captured), snapshots/ (empty)}`;
- the backup dir does not already exist;
- no target file already exists.

It backs up the three live dirs to `$B` with a manifest, then installs each file with a temp-file +
`sync -f` + `mv -T` swap. It only adds files.

**Rollback** (before the watcher has rebuilt anything):

```bash
systemctl --user disable --now convmem-watch.service convmem-reconcile.timer
~/.cache/convmem-evidence-oct17/restore-lost-checkpoints.sh rollback ~/.local/share/convmem "$B"
#   removes only the 19 files, and only if each still has its manifest hash; then diffs the dirs against $B
systemctl --user enable --now convmem-watch.service convmem-reconcile.timer
```

Once the watcher has committed a rebuild, a file rollback no longer applies. The rebuild's own transaction and
checkpoint own the state then, and the script refuses (`changed after restore`).

**Rehearsal (sandbox store, same script):**

- restore → `VERIFY OK`;
- a second restore → refused;
- rollback → `ROLLBACK OK`, with all three dirs `diff -r`-equal to the pre-restore state;
- restore again → each source's run plans the full rebuild from §4.

The first rehearsal also caught a bug, now fixed: the backup manifest listed its own temp file.

**After the restore, expect:** no doctor change until the watcher next indexes these sources. Then a full
rebuild (`full_rebuild_fallback`, planned `[0]`, `[0, 50]`, `[0]`) commits v2 checkpoints under `347376f1`.

**Optional R-975 (separate grant, not rehearsed):** make `975fc327…` consistent by restoring its single
`processed.json` entry from the Oct 17 00:17 store (key `02b3dafe…`; lineage `82756622…` equals the live
checkpoint). Do it with the watcher stopped, under `processed.json.lock`, after a copy-first backup. It also
re-enables a 2-chunk Luna full rebuild of that source. If Kiro wants it, I will write and rehearse it the same
way as §7.

## 8. Questions for Kiro

1. §4 shows that restoring cannot avoid a full rebuild on `686d50e`: v1 checkpoint, v2 contract, Luna
   models. Do you keep "restore" as the disposition, gated on Ryan accepting the 4-chunk spend, and otherwise
   park the dirs as they are? My recommendation: restore when Ryan wants these tails indexed; never
   re-bootstrap.
2. `975fc327…`: should a rollback refuse, or at least flag, when the current `processed` entry for the path
   differs from `processed_preimage` and was not written by the transaction? As it stands, a stale authority
   silently deletes a valid entry. Do you want R-975 as a separate packet?
3. Is the §7 script and procedure acceptable for a live run under E3, or only after E2?
4. Is anything else left in `cc8fde6b`'s blast radius (§5.3) that you want verified?

I finished: [Arc Codex] the Oct 17 collateral packet: evidence preserved, the three lost checkpoints proven
intact, the sandbox showing that a restore means a full rebuild on `686d50e`, all four re-drives proven rolled
back, `975fc327…` found inconsistent, and a rehearsed live restore script.
Next step: Kiro reviews (§8). Ryan then decides the spend gate and the grant; live execution also waits for
E2 or an approved E3 window.
Next lane: Kiro, then Ryan.
See my work: `docs/inter-model/CLAUDE-2026-10-20-issue-286-oct17-collateral-packet.md` on branch
`docs/2026-10-20-issue-286-oct17-collateral`.

**TL;DR:** [Arc Codex] The three lost checkpoints in restic `495c2d65` match live exactly, so restore is
safe, but on runtime `686d50e` it triggers a full rebuild of about 4 Luna chunks rather than an unchanged
result; the step-2 acceptance fails for that reason. All four re-driven transactions rolled back (direct proof
in the Crush job output). Three of those sources are consistent; `975fc327…` lost its `processed` entry to a
stale rollback authority. The live restore packet and script are ready and rehearsed, gated on Kiro, Ryan's
spend decision, and E2 or E3.

<!-- src: ./KIRO-2026-10-20-issue-286-oct13-wedge-scratch-proof-review.md (branch kiro/2026-10-20-issue-286-oct13-wedge-review, 283968a) — ruling (c) this packet executes -->
<!-- src: ./CLAUDE-2026-10-20-issue-286-oct13-wedge-scratch-proof-report.md (branch docs/2026-10-20-issue-286-oct13-wedge-scratch-proof, 17530e5) — §4.3 collateral facts -->
<!-- src: ../../incremental_jsonl.py at 686d50e — run, _continuity_reason, _unchanged_prereturn_refusal, _roll_forward, _restore_processed -->
<!-- src: ../../incremental_checkpoint_migration.py at 686d50e — hermetic-only v1->v2 converter, legacy preimage check -->
<!-- src: /home/lauer/.cache/convmem-evidence-oct17/ — all evidence, manifests, sandbox records, restore script -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc brief; not updated by this report -->
