# [Arc Codex #286] Kiro review — Oct 17 collateral packet (restore, E3, 975fc327 defect)

**Reviewer:** Kiro (design review / sign-off lane; review-only, no implementation)
**Date:** 2026-10-20 UTC
**Arc:** Codex (issue #286)
**Artifact under review:**
`docs/inter-model/CLAUDE-2026-10-20-issue-286-oct17-collateral-packet.md`
at commit `b347272` on branch `docs/2026-10-20-issue-286-oct17-collateral`
(base `origin/main` `686d50e`).
**Prior ruling this executes:**
`docs/inter-model/KIRO-2026-10-20-issue-286-oct13-wedge-scratch-proof-review.md`
at `283968a` on branch `kiro/2026-10-20-issue-286-oct13-wedge-review` — ruling (c)
opened a dedicated collateral packet (restore three lost checkpoints from restic
`495c2d65`; verify the four re-driven transactions; state whether `cc8fde6b` touched
anything beyond the eight).
**This review:** own detached worktree at `/tmp/kiro-oct17-collateral-review`, branch
`kiro/2026-10-20-issue-286-oct17-collateral-review`, explicit-refspec push, no PR.
**Scope:** review-only. Authorizes **no** live restore, journal archive/move, quarantine
clear, re-bootstrap, provider call, config change, or runtime promotion. I did not touch
`.worktrees/runtime-main` or any live config. I read code via `git show`/worktree
checkout, read live state **read-only** (listed and hashed state dirs, parsed
`processed.json`, parsed `retry_state`/`checkpoint` JSON), and read the evidence tree
and restore script without executing them. I ran no `convmem` command that writes
incremental state.

---

## Consequence first (for Ryan)

Claude's packet answers my ruling (c) completely and, in doing so, changes the economics
I assumed and surfaces a real coordinator defect. Net effect:

- **Restore is safe but does not save money.** The three lost checkpoints are intact in
  restic `495c2d65` and match live exactly, so restoring them corrupts nothing. But they
  are old-format (v1, DeepSeek fingerprint `d53ed4fe`), and the current runtime `686d50e`
  runs transform contract v2 with `gpt-6-luna`. The fingerprints can never match, so the
  next watcher pass is a **full rebuild of ~4 Luna chunks total**, not an unchanged
  no-op. My prior ruling's premise — "restore recovers paid transform spend, re-bootstrap
  pays again" — **does not hold here**: restore and re-bootstrap cost the same ~4 chunks.
  What restore uniquely buys is re-attaching the record that describes the live rows and
  letting the watcher index the unindexed tails without a one-shot bootstrap grant.
- **So the restore disposition stands, but its justification is "operational tidiness +
  avoid a bootstrap grant," not "cost recovery."** It is still worth doing if Ryan wants
  those tails indexed; if he does not, parking the dirs costs nothing. The ~4-chunk spend
  is real and Ryan should accept it explicitly before any run.
- **All four re-driven transactions rolled back** — proven directly from the Crush job
  output (each `rolled_back:<hash>` equals that transaction's snapshot sha256). Three of
  the four sources are consistent today.
- **One source is genuinely broken, and the cause is a coordinator defect, not a Crush
  mistake.** `975fc327…` lost its `processed.json` entry because the rollback obeyed a
  stale authority that had captured an **empty** processed preimage. I independently
  confirmed the entry is gone from live `processed.json` and read the code path that
  deletes it. **This can recur on any source** — it is not specific to this incident.
- **The restore script is sound** — restore-only, journal-free, five hard preconditions,
  atomic install, hash-guarded rollback. I accept it for a single supervised E3 run.

**My verdict, by question:**

- **(a) Restore vs park: APPROVE restore, Ryan-gated on the ~4-chunk spend.** Keep
  "restore" as the disposition (checkpoint + prepared, no journal). Ryan is inclined to
  approve the spend; that is reasonable. If he declines, **park** — do not re-bootstrap as
  a substitute, since it costs the same and still needs a grant.
- **(b) Supervised E3 window for this one scripted restore + the R1-B wedge archive-move,
  before E2 exists: ACCEPTABLE, with conditions.** E3 is the interim my prior ruling
  already defined; this packet's restore script enforces the quiescence preconditions in
  code. I accept a **single** combined supervised window for both actions, under the gates
  below. E3 does **not** retire the E2 requirement.
- **(c) The 975fc327 empty-before-image rollback gap IS a coordinator defect that can
  recur on any rollback.** It needs a fix and a census. Scope below.
- **(d) The rest of the Crush blast radius is bounded.** The one extra dir (`02a4f7b2…`)
  and the global side effects (quarantine clear, restic scripts) are accounted for and
  benign. One residual item (the Codex watch quarantine clear) deserves a line.

**Bottom line:** I approve the restore disposition and the restore script, accept a single
supervised E3 window for the restore + R1-B archive-move, and rule the 975fc327 gap a
recurring coordinator defect requiring a fix + census as its own packet. Nothing here
grants anything; every live step still needs Ryan.

---

## What I independently verified (read-only, live + code)

I did not take the packet on authority alone. Every fact checkable without opening a
Chroma client on live data, I checked.

1. **The three lost dirs are exactly the post-Oct-17 bootstrap shell.** `248e25cb…`,
   `98d65c7f…`, `e55a6f61…` each contain exactly `{lock.flock (0 bytes), prepared/
   (empty), retry_state.json, snapshots/ (empty)}`, all mtime Oct 17 18:54,
   `error_code: bootstrap_required`, `transaction_id: ""`, pointing at the Oct 13/14
   Codex rollouts the packet names. This matches §3 and is exactly the precondition
   `restore-lost-checkpoints.sh precheck_live_dir` enforces (contents list + empty
   lock + pinned `retry_state.json` sha). The three retry-state hashes in the script
   are the ones I would compute from these files.
2. **The four re-driven dirs match §5.2.** `0f4d56e0…` v1 `040f5598` (later rebuild,
   no retry_state → consistent); `1677cfce…` v2 `07102f02` (consistent); `614602b2…`
   v1 `040f5598` (consistent); `975fc327…` v1 `d53ed4fe`, `retry_state =
   rebuild_required:projection_checkpoint_mismatch`, source = the Oct 12 20:20 rollout.
   None of the four carries a `transaction.json`/`snapshots/` entry (no orphan journal
   remains), consistent with "all four rolled back and cleaned up."
3. **The 975fc327 processed-entry loss is real.** I parsed live `processed.json` (2977
   entries) and indexed it by each value's `path`. The entry for the 975fc327 source
   (`…rollout-2026-10-12T20-20-37-01a132d8…`) is **MISSING**, while the extra dir's
   source (`02a4f7b2…` → `…rollout-2026-10-13T21-08-50-01a1382b…`) is **PRESENT** (key
   `0c1d0572…`). That is precisely the inconsistency the packet describes: a committed
   v1 checkpoint and Chroma rows on disk, but no `processed.json` entry, so the source
   now refuses `rebuild_required:projection_checkpoint_mismatch`.
4. **The deletion mechanism is in the coordinator, exactly as the packet claims.**
   `incremental_jsonl.py` at `686d50e`:
   - Authority capture (`~line 1756`) builds `processed_preimage` as *only the current
     entries whose `path == self.path_key`*. If no such entry exists at capture time,
     the preimage is `{}`.
   - Restore (`_restore_processed`, line 1866) does:
     `restored = {k:v for current if v.path != self.path_key}; restored.update(preimage);
     save_processed(restored)`. It **unconditionally drops every current entry for the
     path and re-adds only the preimage**. With an empty preimage, it deletes a valid
     live entry with no comparison, no "did this transaction write this entry" check,
     and no guard that the current entry differs from what was captured.
   This is version-independent — the path is identical for v1 and v2 checkpoints.
5. **The evidence cache and restore artifacts exist and are protected.**
   `~/.cache/convmem-evidence-oct17/` is mode 700; restored restic trees are read-only
   (`dr-x`/`r-x`); SHA256 manifests are present for every set; `RESTORE-MANIFEST.sha256`
   and `restore-lost-checkpoints.sh` are present and read-only. I read the script in full
   (did not execute it).

**What I did NOT independently reproduce:** the §4 sandbox runs on `686d50e` (require the
bwrap harness and a full data-root restic restore — exactly the sandboxed work the packet
performed and which I will not run live); the restic lineage/byte comparisons in §3; the
Crush transcript timestamps in §5.1/§5.3. I accept these on the packet's authority given
(i) internal consistency, (ii) exact agreement of every live surface I could check, and
(iii) specific, technically sound method descriptions. The one claim I most wanted to be
true and could not take on faith — the 975fc327 processed deletion — I confirmed directly
against live `processed.json` and against the code.

---

## (a) Restore vs park — APPROVE restore, Ryan-gated on the ~4-chunk spend

My prior ruling (c) said "prefer restore; re-bootstrap only on verified mismatch, because
restore recovers paid transform spend." The packet proves the cost premise wrong for these
three dirs, and I accept the correction:

- The three checkpoints are **v1** (`d53ed4fe`); runtime `686d50e` is **v2** contract +
  `gpt-6-luna`. The continuity check is `transform_fingerprint_changed` for all three, so
  with `allow_full_rebuild = true` the next watcher pass is a full rebuild (planned `[0]`,
  `[0,50]`, `[0]` = ~4 Luna chunks total); with it off, `migration_required`. The
  hermetic v1→v2 migrator (`incremental_checkpoint_migration.py`) exists but is
  `CONVMEM_INCREMENTAL_ROOT`-only and would correctly refuse to relabel DeepSeek-distilled
  artifacts as Luna output. So there is no path on `686d50e` where restore yields an
  unchanged result.
- **Therefore restore and re-bootstrap cost the same ~4 chunks.** Restore is still the
  better of the two because it (i) re-attaches the record describing which live rows
  belong to the incremental generation, (ii) returns that record to the daily restic set,
  and (iii) avoids needing a separate one-shot bootstrap grant. Those are real but modest
  benefits — "operational tidiness," not "cost recovery."

**Ruling:** keep **restore** as the disposition (checkpoint + prepared, no journal).
Gate it on **Ryan explicitly accepting the ~4-chunk Luna spend** on the next watcher pass.
If Ryan wants these three tails (4.6/1.2/1.1 MB) indexed, restore. If he does not, **park**
the dirs as `bootstrap_required` — that costs nothing until someone grants a bootstrap.
**Do not re-bootstrap as a substitute for restore** — it costs the same and also needs a
grant, so it is strictly worse. My earlier "re-bootstrap on verified mismatch" fallback is
moot here: the packet verified the restored artifacts load through the runtime's own
`validate_checkpoint` to planning, so there is no integrity mismatch to fall back from.

Ryan's inclination to approve the ~4-chunk spend is reasonable and I endorse it; the spend
is well under the cap of 10 and buys a clean, record-attached state.

---

## (b) A supervised E3 window for the single scripted restore + the R1-B wedge archive-move — ACCEPTABLE, with conditions

The packet asks whether one E3 quiescence window (watcher + reconcile timer stopped, no
agent writers) is acceptable for **this one scripted restore plus the R1-B wedge
archive-move**, before E2 exists. **Yes, as a single bounded supervised window**, under the
gates below. This is consistent with my prior ruling, which already named E3 (bounded
live-quiescence attestation) as the only defensible interim for a single supervised action
before the E2 fence is built.

Why E3 is sufficient here and why I will allow both actions in one window:

- Both actions are **additive and non-Chroma**. The restore only installs 19 checkpoint +
  prepared files, each gated on non-existence; it never touches Chroma, `processed.json`,
  the export, `retry_state.json`, or `lock.flock`. The R1-B archive-move only closes the
  orphan `transaction.json` by a copy-first SHA-manifested 0700 move, Chroma untouched,
  and R1-B-g (the vector guard) already PASSed at `283968a`. Neither action mutates a
  projection, so the blast radius of a concurrent writer during the window is bounded to
  the state-dir files the script already hash-guards.
- The restore script **enforces the quiescence preconditions in code**: it refuses unless
  each live dir is still exactly the captured bootstrap shell (contents + empty lock +
  pinned `retry_state.json` hash), the manifest is unchanged, the evidence matches the
  manifest, the backup dir does not exist, and no target file exists. A concurrent writer
  that perturbed any of these would trip a refusal rather than a silent clobber.

**E3 conditions for the combined window (all must hold, in this order):**

1. Kiro approval (this document) + Ryan grant for both actions.
2. Watcher and reconcile timer **stopped and disabled**, `MainPID=0`, `inactive`
   (`systemctl --user disable --now convmem-watch.service convmem-reconcile.timer`,
   verified), and `pgrep -af 'convmem(\.py)? (index|watch)'` prints nothing.
3. **No agent session holding a shell against the data root during the window** — this is
   the condition the Oct 17 incident violated, and it is the whole point of E3 given the
   confirmed standing capability of any shell-bearing lane to `python3` a live state dir.
   A human attestation of "no other agent writer active" is required because there is no
   lock to enforce it yet (that is E2).
4. `convmem doctor` shows `restic_gate` PASS for today (it does, as of this session).
5. For the restore specifically: Ryan has accepted the ~4-chunk spend (a).
6. The two actions run **sequentially in one window**, each immediately re-verified
   (the restore via its own `verify` mode; the R1-B move via its copy-first manifest),
   then the watcher/timer are re-enabled.

**Hard boundary:** E3 is a one-time supervised bound for **these two specific actions on
these specific state dirs**. It is **not** a general license to write live incremental
state, and it does **not** discharge E2. The durable fix — an owner-only advisory lock on
the source-state directory that every writer (coordinator, bootstrap, recovery, ad-hoc
tool) must hold, plus an append-only audit event on every mutation of
`transaction.json`/`rollback.json`/`snapshots/`, keyed on stable identity (source path, tx
id, pid/exe) per my carried-forward C2 — remains **MANDATORY before any routine live
incremental work** resumes. The 975fc327 defect (c) is additional evidence that unfenced,
unaudited mutation of this state is dangerous: here the mutating writer was the
coordinator's own rollback, and nothing recorded or guarded the deletion.

One narrow note: the restore script verifies the dir is the bootstrap shell but does not
itself check that the watcher is stopped — it trusts the E3 procedure (step 2) for that.
That division is acceptable because step 2 is an explicit gate, and the script's
`already exists` / `retry_state changed` refusals would catch a concurrent writer
indirectly. I do not require the script to add a watcher check.

---

## (c) The 975fc327 empty-before-image rollback gap — a recurring coordinator defect

**Ruling: yes, this is a coordinator defect, and it can recur on any rollback.** It is not
a Crush artifact. The Crush-driven re-drive only *triggered* a rollback; the deletion of a
valid `processed.json` entry was performed by the coordinator's own `_restore_processed`
obeying a stale rollback authority. I confirmed both the live symptom (entry gone) and the
code mechanism (unconditional overwrite from the preimage).

**Root cause.** The rollback authority captures `processed_preimage` as a filtered
snapshot of the current `processed.json` entries for the path *at authority-capture time*.
`_restore_processed` then deletes **all** current entries for the path and re-adds **only**
the preimage. There is no check that:

- the current entry differs from the captured preimage (i.e. was it changed since
  capture?), or
- the transaction being rolled back is the one that authored the current entry, or
- the preimage is non-empty before it is allowed to delete a non-empty current entry.

So any rollback whose authority captured an empty-or-stale processed preimage will silently
delete whatever valid entry is live at rollback time.

**Why this is a *latent* defect, not a one-off.** The arc's own invariant is that
`processed.json` is a **follower** of checkpoint commit ("processed.json cannot advance
before checkpoint authority"). That means there is a legitimate ordering — checkpoint
commits, authority for the *next* transaction is captured, and only then does the processed
follower write — in which the preimage is empty for a path that will shortly have a valid
entry. The packet's restic timeline for 975fc327 is exactly this: checkpoint written Oct 12
20:27:15; next authority captured 20:27:34–20:29:33 with no processed entry; entry appeared
afterward. The rollback then "restored" to an empty preimage and deleted the real entry.
This race is available to **any source**, not just 975fc327.

**Note the asymmetry in the same function's neighbors.** The Chroma restore path
reconciles against the *current* row ids (`extra_* = current - before`; delete extras,
keep/restore before-image rows). It does not blindly trust the preimage. `_restore_processed`
is the odd one out: it is a blind overwrite. That asymmetry is the tell — the fix should
bring processed-restore up to the same "reconcile against current, don't clobber unrelated
state" discipline the row restore already uses.

**Scope of the fix (design intent; Cursor implements under a separate grant after design
review — not this review's work):**

1. **Make processed-restore conservative.** `_restore_processed` must not delete a current
   entry for the path that the transaction did not demonstrably author. Minimum viable
   guard: if the current entry for the path differs from what the authority captured
   (empty preimage vs non-empty current, or a different digest), **refuse the silent
   delete** and raise a recovery error (e.g. `processed_preimage_stale`) so the rollback
   is caught rather than quietly corrupting state — mirroring the fail-closed posture the
   runtime already takes for `recovery_unproven` / `prepared_artifact_corrupt`. A stronger
   form reconciles like the Chroma path: only remove entries this transaction added, keep
   pre-existing ones.
2. **Capture-time correctness.** Consider whether the authority should capture the
   processed preimage at the same instant it snapshots Chroma/export, under the same lock,
   so the preimage cannot describe a different moment than the rows it is paired with.
   This is the C2 lesson applied to processed-state: key the authority to the state it
   will actually restore.
3. **Audit coupling.** When the E2 fence is built, a processed-entry deletion during
   rollback is exactly the kind of mutation that must emit an append-only audit event
   (path, tx id, before/after digest), so a future stale-authority deletion is visible
   even if the guard is bypassed.

**Scope of the census (read-only; can proceed now without an E2/E3 grant):** enumerate
every incremental source and flag any where a committed checkpoint + Chroma rows exist on
disk but the `processed.json` entry is **absent** (or whose lineage digest disagrees with
the live checkpoint). That is the signature of a stale-authority deletion. The census
should cover:

- all Codex rollout sources (the class 975fc327 belongs to), and
- all Kiro JSONL sources (the production-eligible class), since the defect is
  source-class-independent.

If the census finds only 975fc327, scope the remediation to the optional **R-975** entry
restore the packet describes (restore the single `processed.json` entry from the Oct 17
00:17 store, key `02b3dafe…`, lineage `82756622…` matching the live checkpoint, under
`processed.json.lock`, copy-first, watcher stopped). I accept R-975 as a **separate,
small, Ryan-gated packet** — Claude should write and rehearse it the same way as §7 if
Ryan wants 975fc327 made consistent. It re-enables a 2-chunk Luna rebuild of that source,
which Ryan must accept alongside the (a) spend.

If the census finds additional affected sources, the fix (step 1) becomes a prerequisite
before any further routine rollback can be trusted, and each affected source gets the same
entry-restore treatment under one supervised window.

**Priority:** the *fix* gates resuming routine live incremental work (alongside E2); the
*census* is read-only and should run first so we know the true blast radius before the fix
is scoped. R-975 (the single-source repair) is independent and small.

---

## (d) The rest of the Crush session's reach — bounded

My prior ruling (c)(3) asked for an explicit statement of whether `cc8fde6b` touched
anything beyond the eight enumerated dirs. The packet's §5.3 answers it, and I accept the
answer:

- **One extra state dir: `02a4f7b2…`** (Oct 13 21:08 rollout). A live
  `convmem.py index --file … --now` at 05:20:10Z returned
  `live_route_refused:prepared_artifact_corrupt` and discarded its PREPARING journal +
  snapshot. PREPARING never writes Chroma. I confirmed live: the dir has a v1 checkpoint
  (`d53ed4fe`), `frontier_violation` retry-state (a *later* run, Oct 17 22:25), and its
  `processed.json` entry is **present** (key `0c1d0572…`). So this source is consistent;
  the Crush touch left no projection damage. Verified, not argued.
- **Global side effects:**
  - `convmem watch --clear-quarantine ~/.codex/sessions` at 05:19:17Z. This cleared the
    Codex watch circuit breaker. It is benign for state integrity but worth one line: the
    live doctor still shows a `wedged_incremental_transaction` WARN for the Oct 13
    `rollout-…01a1374e…` source (tx `46313d43…`, `recovery_unproven`, `APPLYING`) — that
    is the original single-source wedge this arc has been chasing (R1-B), not a new item.
    The quarantine clear did not resolve it; it only cleared the breaker/retry hold. No
    action needed here beyond noting it is the R1-B subject, which the E3 archive-move
    addresses.
  - restic ensure-snapshot + offsite-copy scripts at 05:18:11Z / 05:18:26Z. Repository
    writes only, after `495c2d65` was taken. Benign.
- **Read-only touches:** two unclassified PREPARING journals (`878b7ee7`, `24d93c59`) were
  listed but not written by the settle scripts; both sources are consistent today
  (their later changes are ordinary watcher runs).

**Residual concern worth stating for Ryan (not a blocker):** the Oct 17 session's reach
was *nine* state dirs, the Codex watch quarantine, and the restic repos — all by an ad-hoc
Crush script with raw shell access and no owner lock or audit. That is the same standing,
unfenced capability my prior ruling flagged under (b)/E2. The collateral is now fully
enumerated and bounded, but the *mechanism* that produced it is still live for every
shell-bearing lane until E2 exists. Nothing in (d) changes my E2 ruling; it reinforces it.

---

## Carried forward (unchanged)

- **E2 remains MANDATORY** before routine live incremental work — owner-lock + per-write
  audit on `transaction.json`/`rollback.json`/`snapshots/` (and now, per (c), on
  `processed.json` deletions during rollback), keyed on stable identity (source path, tx
  id, pid/exe), not a content manifest a routine deploy perturbs (C2).
- **C1** (fail-closed contract-inventory hashing actual bytes) still applies to any
  eventual re-admission of a v1 checkpoint to semantic-v2. The §4 finding — that v1
  checkpoints can never match the v2 fingerprint and the migrator is hermetic-only — is
  consistent with C1 and means re-admission is a full rebuild, not a relabel.
- The **restic `hold-issue-286-wedge` tag** on `495c2d65` / offsite remains correctly
  Ryan-gated and more urgent than ever: `495c2d65` is the only remaining copy of the three
  lost checkpoints *and* the only copy of the 975fc327 processed entry needed for R-975.
  I endorse tagging it before any prune.
- The **second retained transaction** (Kiro `sess_2628…`, `transform_failed`) still needs
  its own disposition, separate from this collateral.

---

## Overall verdict

**(a) Restore: APPROVE, Ryan-gated on the ~4-chunk Luna spend.** The three lost
checkpoints match live exactly and restore is safe, but on `686d50e` (v2 contract, Luna)
restore triggers a ~4-chunk full rebuild rather than an unchanged no-op — so restore and
re-bootstrap cost the same, and restore wins only on tidiness + avoiding a bootstrap grant.
Keep restore; park if Ryan declines the spend; never re-bootstrap as a substitute.

**(b) Single supervised E3 window for the scripted restore + R1-B archive-move: ACCEPTABLE**
under the six E3 conditions above (watcher stopped/disabled/MainPID=0, no agent shell
writer, restic_gate PASS, spend accepted, both actions additive/non-Chroma, each
re-verified). E3 does not discharge E2.

**(c) The 975fc327 empty-before-image rollback IS a coordinator defect that can recur on
any rollback.** `_restore_processed` blindly overwrites the path's entries from a preimage
that may be empty/stale because processed is a commit follower. Fix: make processed-restore
conservative/fail-closed and capture the preimage under the same lock as the rows (Cursor,
separate grant, after design review). Census: read-only scan of all Codex and Kiro sources
for committed-checkpoint-but-missing-processed-entry; run it first. R-975 is a separate
small Ryan-gated single-entry repair.

**(d) The rest of the Crush blast radius is bounded** — one extra consistent dir
(`02a4f7b2…`), a Codex watch quarantine clear (benign; the still-WARNing wedge is the R1-B
subject), and restic repo writes. The *mechanism* (unfenced ad-hoc writer) reinforces E2.

**Net change vs my prior ruling:** restore's justification shifts from "cost recovery" to
"tidiness + grant avoidance" (and the spend is real); E3 is approved for a single combined
window; the collateral is fully bounded; and the four re-driven transactions are now proven
(all rolled back) rather than "unverified." A new, higher-severity workstream opens: the
processed-restore coordinator defect with a fix + census. Nothing here grants anything.

---

## Forward announcement

I finished: Kiro review of the Oct 17 collateral packet (`b347272`) — rulings on (a)
restore vs park, (b) a single supervised E3 window for the restore + R1-B archive-move,
(c) the 975fc327 processed-restore coordinator defect (fix + census scope), and (d) the
rest of the Crush blast radius.
Next step: Ryan decides (1) whether to accept the ~4-chunk Luna spend and grant the single
E3 restore + R1-B archive-move window; (2) to authorize the read-only processed-entry
census and, pending its result, a Cursor fix of `_restore_processed` (after design review)
plus the optional R-975 single-entry repair; (3) the `hold-issue-286-wedge` restic tag.
Next lane: Ryan (grants) → Cursor (processed-restore fix + E2 fence, under separate grants
and design review) / Claude (census + R-975 packet) → Kiro re-review before any live
disposition.
See my work:
`docs/inter-model/KIRO-2026-10-20-issue-286-oct17-collateral-review.md` on branch
`kiro/2026-10-20-issue-286-oct17-collateral-review`.

## TL;DR

- **(a) Restore APPROVED, Ryan-gated on the ~4-chunk Luna spend.** The 3 lost checkpoints
  match live exactly (I confirmed the dirs are the Oct 17 bootstrap shell), but they are
  v1 and `686d50e` is v2+Luna, so restore triggers a ~4-chunk full rebuild — restore and
  re-bootstrap cost the same. Keep restore (tidiness + avoids a bootstrap grant); park if
  Ryan declines; never re-bootstrap as a substitute.
- **(b) One supervised E3 window for the scripted restore + R1-B archive-move is
  ACCEPTABLE** (watcher stopped/disabled, no agent shell writer, restic_gate PASS, spend
  accepted; both actions additive/non-Chroma; script enforces quiescence preconditions in
  code). E3 does NOT discharge the mandatory E2 fence.
- **(c) The 975fc327 processed-entry loss IS a recurring coordinator defect, not a Crush
  mistake.** I confirmed the entry is gone from live `processed.json` and that
  `_restore_processed` blindly overwrites from an empty/stale preimage with no guard.
  Because processed is a commit follower, any rollback can hit this. Fix = make
  processed-restore conservative/fail-closed (Cursor, separate grant); census = read-only
  scan of all Codex + Kiro sources for committed-checkpoint-but-missing-processed-entry,
  run first; R-975 = separate small single-entry repair.
- **(d) Rest of the blast radius bounded** — `02a4f7b2…` consistent, quarantine clear
  benign (the still-WARNing wedge is the R1-B subject), restic writes benign. The unfenced
  ad-hoc-writer mechanism reinforces E2.
- **All four re-driven transactions proven rolled back.** Nothing in this review grants
  anything; restore, R1-B move, the fix, the census, R-975, and the hold-tag each remain
  separate Ryan-gated actions.

<!-- src: ./CLAUDE-2026-10-20-issue-286-oct17-collateral-packet.md (branch docs/2026-10-20-issue-286-oct17-collateral, b347272) — packet under review -->
<!-- src: ./KIRO-2026-10-20-issue-286-oct13-wedge-scratch-proof-review.md (branch kiro/2026-10-20-issue-286-oct13-wedge-review, 283968a) — prior ruling (c) this packet executes -->
<!-- src: ../../incremental_jsonl.py at 686d50e — _restore_processed (1866), processed_preimage capture (1756), _roll_forward restore path (2031) read read-only to confirm the defect -->
<!-- src: /home/lauer/.local/share/convmem/incremental-jsonl/{248e25cb,98d65c7f,e55a6f61,975fc327,02a4f7b2,0f4d56e0,1677cfce,614602b2}… and processed.json — live state read read-only to corroborate §3/§5 -->
<!-- src: /home/lauer/.cache/convmem-evidence-oct17/restore-lost-checkpoints.sh — restore script read (not executed) to rule on (b) -->
<!-- ref: ../plans/STATUS-codex-jsonl-production-integration.md — arc brief; not updated by this read-only review -->
