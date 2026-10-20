# [Arc Codex #286] Oct 13 wedge: scratch proof and Oct 17 writer attribution

**Author / recipient:** Claude (Opus 5.5) → Kiro, 2026-10-20 UTC (Oct 20 CDT).
**Grant used:** Ryan's SCRATCH-step grant from Kiro's review
`docs/inter-model/KIRO-2026-10-20-issue-286-oct13-wedge-recovery-review.md`
(branch `kiro/2026-10-20-issue-286-oct13-wedge-review`, `f3b2b45`) of my packet
`docs/inter-model/CLAUDE-2026-10-20-issue-286-oct13-wedge-recovery-packet.md` (`70adb23`).
**Branch:** `docs/2026-10-20-issue-286-oct13-wedge-scratch-proof` from `origin/main` `686d50e`.
**State:** `READY_FOR_KIRO_REVIEW`. Live disposition stays `NO-GO` until Kiro re-reviews and
Ryan grants.

**What I did not do:** I made no live writes. I did not clear quarantine, and I did not delete,
move or edit any journal. I made no provider calls and no restic repository writes (every
restic call used `--no-lock`). I did not print session text. The live wedged state dir is
byte- and mtime-identical at the start and end of this session (§5).

## 1. Bottom line

1. **(1) Restore is idempotent in scratch: PASS.** The pinned `3e705e4` runtime ran in a
   network-less, read-only-root sandbox against a restic copy of today's store with the
   recovered authority placed back byte-exact. It took the rollback path (`rolled_back`) and
   never reached `_commit_generation`. Every source surface was hash-equal before and after,
   including the float32 vector bytes; so were both non-source digests (vectors included).
   Only `transaction.json`, `rollback.json` and `snapshots/<tx>/` were removed.
2. **(2) Live already equals the Oct 13 before-image: PASS, vectors included**, with one
   precise qualification. The live HNSW segment stores **unit-normalized** vectors plus a
   separate norm (`length.bin`), because the collection space is cosine. The live stored
   (unit × norm) for all 15 source rows is **bit-identical** to what Chroma returns after the
   exact before-image bytes are written into it. It is **not** bit-identical to the JSON floats
   in `rollback.json`. Chroma's normalize/denormalize round trip moves 40–195 of 768 components
   by exactly 1 ulp. This is deterministic, and the restore reproduces it.
3. **The Oct 17 writer is attributed:** **Crush session `cc8fde6b-4bc3-48b8-9dea-eab4c1712617`**
   in `~/null`, model `deepseek-v4-flash`, running ad-hoc scripts against the live state on
   Oct 17 05:14–05:36Z. Its `/tmp/settle_apply.py` rewrote the live journal to `PREPARING` and
   drove `ingest.index()` on the source, which produced the completed rollback
   (05:21:31→05:24:22Z). Its `/tmp/settle_apply2.py` then re-wrote the saved APPLYING journal
   with `_atomic_json` (byte-identical) without the rollback authority, at 05:24:40→05:24:44Z.
   That re-write is what wedged the source. No in-tree code path is involved, which confirms
   Kiro's code reading.
4. **The same session touched more than this source (new finding, needs Ryan):**
   - three other incremental state dirs were *moved* to `/tmp`, which was cleared at the
     Oct 20 00:48 boot;
   - four other APPLYING journals were flipped to PREPARING and then re-driven through live
     `convmem.py index --file --now`;
   - the Codex watch quarantine was cleared;
   - one more Codex source was indexed live.

   See §4.3.

## 2. Scratch setup (A)

| Item | Value |
|------|-------|
| Authority restore | `restic --no-lock restore 495c2d65 --include rollback.json --include snapshots/46313d43…/rollout.jsonl` into a 0700 scratch dir |
| `rollback.json` | `33ab1c3ba1f7462b326bdfc3e71b7768232f924e4c913f5a78579d4b1851c56a`, 2,728,383 B (local restore, offsite `1d4a9ff5` dump, and bound `rollback_authority_sha256` all agree) |
| Snapshot `rollout.jsonl` | `ba6f350a458709125d0d19058c9284b19d08db64c9dff136c3da72177ed31e48`, 6,079,972 B (local, offsite, and live source prefix 0..6,079,972 all agree; source inode 18892734 unchanged) |
| Store copy | `restic --no-lock restore a3fb870a` (complete-data-v2, 2026-10-20 00:41 CDT) of the data root, minus corrupt backups, `experiments`, `worktrees`, `imports`, `backups`, `restore-drill` (12.5 GiB) |
| Wedged state dir in copy | byte-equal to live (all 6 files). `retry_state.json` was set aside so the retry gate would not refuse; it did not exist at the Oct 17 run either |
| Runtime | `git archive 3e705e4` (tree `f50f479af4d203233f05908e2bdfaf36e6d62ec5`), made read-only; `incremental_jsonl.py` sha256 `3330dbbb…339d`; interpreter = convmem env Python 3.11.15, chromadb 1.5.9 |
| Sandbox | `bwrap`: `/` read-only; `/home/lauer` = scratch HOME; source file ro-bound at its real path; `--unshare-net` (no route; 127.0.0.1:11434 refused, DNS fails); `--clearenv` (no `DEEPSEEK_API_KEY`, no `env.local`/`env.systemd`) |
| Entry | unmodified CLI `convmem.py index --file <source>` via `runpy`, with a tripwire on `_commit_generation` and `_write_transaction` that aborts *before* either runs (Kiro C-run2 hard stop). The tripwire did not fire |

## 3. Results

### 3.1 Proposition 1: restore is idempotent in scratch

Branch taken: `_roll_forward` → `_codex_roll_forward_refusal` returned `None` → the forward
`try` failed in prepared-artifact validation with `prepared_artifact_corrupt` (a `3e705e4`
`_validate_prepared_artifact` check on the `8a7cdab`-authored artifact; the specific check was
not isolated) → `_restore_replay_before_images` → `_cleanup`. CLI exit 91,
`live_route_refused:rolled_back:ba6f350a…`. Elapsed 2 min 46 s.

**Note for Kiro:** the rollback is reached only because `3e705e4` rejects the old prepared
artifact. If that artifact had validated, this runtime would have attempted a forward commit.
The tripwire was the guarantee here, and the code alone would not have been.

| Surface (hash-only, `measure.py`) | Before | After | |
|---|---|---|---|
| Summary row: ids, doc, metadata, f32 vector digest | `c3086834…` | same | ✔ |
| 14 unit rows: ids, docs, metadata, f32 vector digest | `e5932a66…` | same | ✔ |
| Non-source `conversation_summaries` (5,453 rows, vectors incl.) | `eb9e2a2f…` | same | ✔ |
| Non-source `knowledge_units` (111,327 rows, vectors incl.) | `1bbd7d5c…` | same | ✔ |
| Export: 14 source lines vs before-image payloads, in order | equal | equal | ✔ (file hash changes from in-place rewrite; foreign lines hash `ef8711d9…` unchanged) |
| `processed.json` source entry `7f910596…` | = preimage | = preimage | ✔ (file hash changes from rewrite) |
| `checkpoint.json`, both `prepared/*` | = preimage | same bytes | ✔ |
| Dedupe ledgers | 0 tagged rows | same file hashes | ✔ |
| Removed | — | `transaction.json`, `rollback.json`, `snapshots/46313d43…/` | ✔ only these |
| Added | — | `retry_state.json` (`prepared_artifact_corrupt`, attempt 1) | expected |

The restore really wrote: all 15 rows got new consecutive seq_ids (208245–208259,
`embeddings_queue` op UPSERT), and the logged vectors are **15/15 bit-exact to the
before-image**. Reading them back gives the same bits as before the write. That is the
deterministic normalization in §3.2.

mtime signature: in scratch, checkpoint and prepared were rewritten 95 s after start and
snapshots removed 71 s later. On Oct 17 the gap was 73 s (00:23:09 → 00:24:22 CDT).

### 3.2 Proposition 2: live equals the Oct 13 before-image

| Surface | Method | Result |
|---|---|---|
| Docs + metadata, 15 rows | live `chroma.sqlite3` `mode=ro`, `query_only` | 15/15 equal |
| Vectors, 15 rows | `cp -a` of the two live HNSW segment dirs (`cmp`-stable). Parse `data_level0.bin` + `length.bin` + `index_metadata.pickle` (no-globals unpickler); compare stored unit×norm to Chroma's `get()` of the scratch store after the exact before-image was written | **15/15 bit-identical**; norms match the before-image within 1e-5 |
| Stored representation | same | stored norm 1.0 (cosine HNSW); vs numpy-normalized before-image ≤ 6 ulp (arithmetic order) |
| `get()` vs raw JSON before-image | scratch `get()` | 3/14 units and 0/1 summary bit-exact, max \|Δ\| 2.4e-7, every diff exactly 1 ulp, cosine 1 ± 7e-8: normalization round-trip |
| Export source lines | live file, read-only | 14 lines, byte-equal in order |
| `processed.json` entry | live, read-only | equal to preimage |
| Dedupe ledgers | live | 0 rows tagged with source or tx |
| When live rows were last written | `chroma.sqlite3` from restic | Oct 17 00:17 (`495c2d65`): seq 182073–182087, global max 186143. Oct 18 (`e496b881`) and live now: **186144–186158**, the next 15 writes after the 00:17 backup, in restore order (summary first) |

Not claimed (Kiro G-b): live non-source state equals Oct 13. That is false by design, since
other sources were indexed afterwards, and it does not matter for this source.

## 4. Oct 17 writer attribution (B)

### 4.1 Attribution

Crush session `cc8fde6b-4bc3-48b8-9dea-eab4c1712617`, DB `~/null/.crush/crush.db`, model
`deepseek-v4-flash`, created 05:14:56Z. It had user turns at 05:14:56, 05:18:01 and 05:36:01Z,
and its last message was at 05:36:01Z. I did not read the user-turn text, so whether it was
authorized is Ryan's call. Shell interpreter: miniforge base Python 3.13 (its tracebacks name
`/home/lauer/miniforge3/lib/python3.13`). Code was `PYTHONPATH=~/Projects/convmem`, and the
main checkout was then on `fix/2026-10-16-issue-286-watcher-child-now` `d0f987b`. That checkout
was byte-identical to `3e705e4` for `incremental_jsonl.py`, `ingest.py`,
`incremental_retry_state.py`, `incremental_jsonl_production.py` and `config.py`. Traceback line
numbers (`incremental_jsonl.py:2976`, `:3031`; `ingest.py:1400`) match.

| Time (Z) | Crush tool call (command sha256 prefix) | Effect on live state |
|---|---|---|
| 05:19:17 | `convmem watch --clear-quarantine ~/.codex/sessions` | watch circuit-breaker hold cleared for all Codex rollouts |
| 05:20:10 | `python3 convmem.py index --file …/rollout-2026-10-13T21-08-50-01a1382b….jsonl --now` | live index of a different Codex source |
| 05:21:11–15 | writes and runs `/tmp/settle_stale.py` (`e514483c`) | read-only plan: 5 APPLYING → "apply", 3 PREPARING → "drop", 2 unclassified |
| 05:21:25–29 | writes and runs `/tmp/settle_apply.py` (`92ab2c13`) | **moves 3 "drop" state dirs to `/tmp/convmem-settled-<sid>`**; saves our tx to `/tmp/convmem-replay-0d5086…/transaction.changed.json` and copies `rollback.json` beside it; crashes (`IndexError`) |
| 05:21:31 → 05:24:22 | patches and re-runs `settle_apply.py` (`78b81432`) | `_atomic_json` writes **all 5** live journals as `PREPARING`; then `ingest.index()` with patched `load_processed`/`_files_from_inventory` drives the first target (our source) → **rollback** (00:23:09 rewrite, 00:24:22 cleanup CDT) → raises `live_route_refused:rolled_back` → script dies; `retry_state.json` attempt 1 `prepared_artifact_corrupt` |
| 05:24:22–38 | read-only inspection (state dirs, `/tmp` copies) | none |
| 05:24:40 → (no result recorded) | writes and runs `/tmp/settle_apply2.py` (`befae81c`) | for each "apply" dir: `_atomic_json(d/"transaction.json", <saved APPLYING tx>)`. **This is the 00:24:44 CDT byte-identical re-creation.** Rollback authority is not restored. Then `subprocess.run(["python3","convmem.py","index","--file",src,"--now"])` per source |

The re-creation is byte-identical because the saved copy was re-serialized with the same
`_atomic_json` the coordinator uses. Its mtime is the write time because the script wrote it
rather than copying it. The authority copy at `/tmp/convmem-replay-0d5086…/rollback.json` lived
in /tmp until the 2026-10-20 00:48 boot.

### 4.2 Corroborating and ruled-out evidence

- **Timing:** the Crush call issued 05:21:31Z returned 05:24:22Z. The pinned scratch run
  predicts start ≈ 05:21:34, rewrite 05:23:09 and cleanup 05:24:22.
- **Chroma:** the 15 source rows became the first 15 writes after the 00:17 backup (§3.2).
- **Retry state:** Oct 18/19 snapshots show `attempts_on_prefix 3, consecutive 2,
  recovery_unproven`. That is one `prepared_artifact_corrupt` (05:24:22Z) followed by
  `recovery_unproven` attempts: the `settle_apply2` subprocess and an unattributed 11:26:56 CDT
  write, outside the asked window.
- **`runtime-main/__pycache__/incremental_retry_state.cpython-313.pyc` born 00:23:38.746 CDT:**
  this is Kiro `sess_c5d99720` running `python -c "import incremental_retry_state as m;
  print(dir(m))"` (cwd runtime-main) at 05:23:38.762Z. It is read-only and not the writer.
  Kiro's other in-window calls were also read-only: doctor, `chroma_guard.py audit`, the audit
  timer install and `daemon-reload`.
- **Ruled out:**
  - The user/system journal shows only 2-min reconcile sweeps (`queued=1`, ~1 s each), the
    backup (finished 00:17:56), and Kiro's audit timer.
  - No watcher was running (it started 01:12).
  - The `restore-drill` dir was last used 2026-07-12.
  - No Python 3.13 unit exists (system Python is 3.14, and units use 3.11).
  - Codex sessions `01a1476a` (Oct 16 20:12), `01a147fb` (22:50) and `01a14842` (Oct 17 00:08)
    were all in ButsabaJobScout and made no convmem calls. Their wedged-path mentions are
    `world_state.permissions.approved_command_prefixes` snapshots.
  - The Claude WordPress session `b7972be6` made no convmem calls.
  - Claude `b0bed3dd` is the Oct 20 packet session.
  - No Cursor, Copilot, opencode, Gemini or OpenClaw files were written in the window.
  - Of 60+ Crush DBs, only `~/null` had in-window messages.
- **Gaps:** there is no auditd/fanotify trail. /tmp contents and the `settle_apply2` output
  were lost (reboot, and no recorded result). Shell histories give no coverage: the newest
  `~/.zsh_history` entry is from 2026-06-23, `~/.bash_history` has no timestamps, and neither
  mentions `settle_apply`, `convmem-replay` or `--clear-quarantine`. Agent shells do not write
  them anyway.

### 4.3 Collateral found (not in this brief's scope; for Ryan and Kiro)

| State dir | Crush action | Now (live, read-only) |
|---|---|---|
| `248e25cb…`, `98d65c7f…`, `e55a6f61…` (tx `8be6bd4c`, `f7d61185`, `04194a14`) | whole dir moved to `/tmp/convmem-settled-*` ("intact cached artifacts") | dirs re-created holding only `retry_state.json` (Oct 17 18:54). **Checkpoints and prepared caches lost**; last copies are restic `495c2d65` (Oct 17 00:17) and earlier. Paid transforms may need redoing (Arc Codex burn) |
| `0f4d56e0…`, `1677cfce…`, `614602b2…`, `975fc327…` (tx `8d471c42`, `d70a723d`, `e3c467cf`, `7d95f272`) | journal flipped APPLYING→PREPARING, then re-set to APPLYING and re-driven via `convmem.py index --file --now` from the main checkout | no journal; checkpoints committed Oct 17 00:34 to Oct 19 21:44. Outcome (roll forward or back) not verified here |
| `0d508630…` (this wedge) | see §4.1 | orphan APPLYING journal, no authority |

## 5. Verification of this report

- Live wedged state dir at session end has the same 6 files, sha256 and mtimes as at session
  start (`bab59aa6`, `e3b0c442`, `d8eeebe8`, `366e3068`, `101fc9ce`, `a0530661`).
- Every restic call used `--no-lock` (`snapshots`, `ls`, `dump`, `restore` into scratch only).
- Live Chroma was read through SQLite `mode=ro` + `query_only`, plus a `cp -a` of the two
  HNSW segment dirs, which was then parsed in scratch. No Chroma client was opened on live data.
- Transcripts: I extracted timestamps, record types and tool-call command strings that touch
  convmem. Crush tool-call inputs and outputs for 05:21–05:25Z were saved to a 0700 scratch dir
  for code reading only. I read no user or assistant prose.
- Local scratch evidence (not pushed): `measure_pre.json` `a787f3d3…`, `measure_post.json`
  `d15b3d95…`, `calls.json` `2fe1c263…`, tools `measure.py` `e13036bb…`, `run_pinned.py`
  `d7d93167…`, `bridge.py` `5b105ae7…`, `sandbox.sh` `005b0bd2…`. All live in the session
  scratchpad `…/c64238fd-e9a5-495b-92f1-dba1e8b90c6b/scratchpad/`.

## 6. Questions for Kiro

1. Does §3.2 (stored-representation equality, not JSON-float equality) satisfy guard R1-B-g
   for the live R1-B archive-move?
2. With the writer attributed to an ad-hoc agent script rather than an in-tree path, is the
   Stage 1 no-other-writer gate cleared under E1? Or is E2 (owner lock + per-write audit)
   still required, given that any lane with shell access can run `python3` against the live
   state dir?
3. Should the §4.3 collateral (three lost state dirs, four re-driven transactions) become its
   own investigation packet before any further Arc Codex live work?

I finished: [Arc Codex] the scratch proof (both propositions PASS) and the Oct 17 writer
attribution.
Next step: Kiro reviews this report (R1-B-g, the E1/E2 ruling, the §4.3 collateral). Ryan then
decides on the live R1-B grant and the collateral follow-up.
Next lane: Kiro, then Ryan.
See my work: `docs/inter-model/CLAUDE-2026-10-20-issue-286-oct13-wedge-scratch-proof-report.md`
on branch `docs/2026-10-20-issue-286-oct13-wedge-scratch-proof`.

**TL;DR:** [Arc Codex] The pinned `3e705e4` runtime proves the restore is idempotent in
scratch. Live already equals the Oct 13 before-image, vectors included, under Chroma's cosine
storage (bit-identical to a fresh write of the before-image; 1-ulp from the raw JSON floats).
The Oct 17 writer was Crush session `cc8fde6b` (`~/null`, deepseek-v4-flash). Its ad-hoc
`/tmp/settle_apply.py` triggered the rollback, and `/tmp/settle_apply2.py` re-wrote the
APPLYING journal without its authority. The same session also moved three other state dirs
into /tmp, which was later wiped at reboot.

<!-- src: ./CLAUDE-2026-10-20-issue-286-oct13-wedge-recovery-packet.md (branch docs/2026-10-20-issue-286-oct13-wedge-recovery, 70adb23) — packet this proof executes -->
<!-- src: ./KIRO-2026-10-20-issue-286-oct13-wedge-recovery-review.md (branch kiro/2026-10-20-issue-286-oct13-wedge-review, f3b2b45) — acceptance G-a/G-b, C-run1/C-run2, E1/E2 -->
<!-- src: ../../incremental_jsonl.py at 3e705e4 — _roll_forward, _restore_replay_before_images, _cleanup, _validate_prepared_artifact -->
<!-- src: ../../chroma_write_guard.py — HNSW header/data_level0 layout used to read stored vectors -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc brief; not updated by this report -->
