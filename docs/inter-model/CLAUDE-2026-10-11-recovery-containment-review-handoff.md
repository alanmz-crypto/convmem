# Review Handoff: recovery, detection, and containment (Opus ↔ Codex review packet)

**Date:** 2026-10-11
**Author:** Claude Opus 5.5 (adversarial review lane; four rounds with Codex)
**For:** Codex (architecture author) → Opus (one review + one delta) → Kiro (design sign-off) → Ryan → Cursor
**Authorization:** Ryan, 2026-10-11, in chat — asked that the review be placed on GitHub before a
Rescuezilla reboot, and agreed that Codex architects while Opus reviews. **This document authorizes no
implementation, deployment, arc, service change, or live write.**

> **Status update 2026-10-19 (Opus) — this packet is superseded; do not resume from it.**
> Codex authored **Arc Safe Harbor** from this packet. Opus review + delta PASS at `505a422` (85%),
> Kiro PASS and Ryan direction approval at `5ea16a6`, execution plan accepted at `dca13a5`, Cursor T1
> grant at `b4c0e73`. The live arc state is `docs/plans/STATUS-safe-harbor.md` on branch
> `plan/2026-10-11-safe-harbor`. Opus returns only if contracts beyond the E7 clause are added.
> The sections below are the 2026-10-11 record, kept unchanged.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `COMPLETE` — superseded by Arc Safe Harbor (see status update above); work placed on hold by Ryan 2026-10-19 |
| **Branch** | `docs/2026-10-11-recovery-containment-review-handoff` |
| **Push status** | pushed to origin |
| **PR** | not opened; not intended for merge (cite, then delete when convenient) |
| **Ryan GATE** (2026-10-11 list → 2026-10-19 state) | (1) fresh Rescuezilla image — **still unconfirmed** per Safe Harbor STATUS §3; (2) arc named **Safe Harbor**, review chain completed; (3) #341 detector — **observed deployed** 2026-10-19 (runtime checkout contains `5c6a4a8`; audit timer enabled and ran; watch active); (4)–(5) backup facts and loss window — **still open**, tracked in Safe Harbor STATUS §6 item 3 |
| **Track A ingest** | `~/.claude/projects/-home-lauer-Projects-convmem/67a19512-adab-4337-990a-de1649c128a4.jsonl` — **not indexed**. Safe Harbor STATUS §7 hard stops forbid indexing from that brief; run only on Ryan's explicit "ingest your chat" |
| **Resume chat** | `claude --resume 67a19512-adab-4337-990a-de1649c128a4` |

---

## Owner requirements (verbatim — the arc must serve these)

1. No verified recovery point, no risky change.
2. Unexpected result, stop and investigate.
3. Never repair production blindly.

Durability of code **and** governance over 6–18 months is priority #1; usability/speed is #2.

---

## What Codex should author

A **bounded** architecture under a Ryan-named arc (`ARCHITECTURE-<slug>.md` + `STATUS-<slug>.md` on a
`plan/` branch) that:

- Uses the **existing** recovery layers first: offline Rescuezilla images and daily Restic (local repo +
  USB copy). Defines when a fresh offline image is a prerequisite (proposal: before any corpus-affecting
  maintenance). Retains the pre-incident image (needs a destination — see Open questions).
- Treats the **#341 detector deploy** as a separate, already-reviewed decision.
- Adds **persistent containment** using the existing `QUARANTINE.json` mechanism for (a) an audit FAIL
  and (b) an automatic segment restore whose census stays unavailable.
- **Preserves torn segment evidence** before replacement, interruption-safely.
- Makes approval recovery distinguish **unavailable / absent / tombstoned**, and puts `record --recover`
  behind the Restic recovery-point check.
- Removes the **destructive permission-file fallback** and reviews wildcard grants.
- Converges the **backup units** on the deployed release and interpreter.

Deferred (do not design unless Ryan reopens): live-backup freeze, approved-identity registry, general
HOLD subsystem, global read-path `ChromaStore` constructor change, the 41-commit `runtime-main` catch-up.

---

## Revisions inspected

| Root | Path | Revision |
|------|------|----------|
| D (deployed) | `~/Projects/convmem/.worktrees/runtime-main` | `a92a74eb326b3eaa59087b707de10153c7cc0c63` (last fast-forward 2026-09-25) |
| R (detector candidate, PR #341) | merged on `main` | `5c6a4a8ad51c968a27afc1c8726fc78c4801cb6d` — exactly one commit beyond D |
| C (shared checkout) | `~/Projects/convmem` | `fb923d58…` on a feature branch that **predates** `chroma_write_guard.py` |
| `origin/main` at writing | — | `6a23aa93…` (41 commits beyond D) |

Recheck before relying on any of these.

---

## Observed evidence (2026-10-11, read-only)

| # | Observation | Evidence |
|---|---|---|
| O1 | A single MCP `search_fast` call commits a real SQLite write transaction: header change counter 162116→162117, mtime +56 ms; HNSW segment files untouched. Reproduced twice. `journal_mode=delete`. | header bytes 24–27 before/after; segment mtimes; D `serving_index_repository.py:244-245` admits the startup write |
| O2 | Restic backs up the **live** data root with no lock and no filesystem snapshot (ext4, plain partition `/dev/nvme1n1p2`). The write gate's snapshot runs *before* the write session opens. | D `restic_snapshot.py:916-961`; D `convmem.py:398-402` |
| O3 | The backup arc lists writer coordination / quiescence as still open. | D `docs/plans/STATUS-complete-data-backup-correction-v2.md:80` |
| O4 | Backup units (`convmem-restic-local`, `-ensure`, `-external`) run the **shared checkout** via a bare `python3` (system 3.14.7); launcher, watch, reconcile and MCP run `runtime-main` under conda 3.11.15. Backup import closure was identical across C and D at check time. | `~/.config/systemd/user/convmem-restic-local.service:21`, `convmem-restic-ensure.service:18` |
| O5 | 15 long-lived `mcp_server.py` processes (oldest 2026-10-09 16:00); coherent with D today because D has not moved since 2026-09-25. | `ps`; D reflog |
| O6 | Governed proposals: 22 total, 20 APPROVED, 2 REJECTED, **0 APPROVAL_STARTED**. Write-guard events since 2026-09-24: 2 `snapshot_created`, 1 `snapshot_adopted`, **0 restored, 0 quarantined**. | `pending_decision_events.jsonl` (reduced read-only); `chroma.write-guard/events.jsonl` |
| O7 | Census baseline at 00:33 CDT (deployed read-only tool): `knowledge_units` 109,865 rows / 109,693 HNSW IDs / 172 pending / **0 lost** / 0 extra; `conversation_summaries` 4,871 / 4,810 / 134 / 0 / 0. Both segments pass validation. Counter and mtime unchanged by the census. **Means only: 0 IDs without vectors.** Does not test stale vectors or semantic correctness. | D `scripts/chroma_guard.py validate` / `census` |
| O8 | #341 changes `chroma_write_guard.py` by +50/−0: `native_write`, `reconcile`, `_restore` unchanged. `audit()` never calls `reconcile()`. It classifies and publishes **after** releasing the lock. | `git diff --numstat a92a74e 5c6a4a8`; R `chroma_write_guard.py:796-828` |
| O9 | CPU tripwire inputs clean this boot: 0 kernel fault lines; the only coredump is a SIGABRT (`SI_TKILL`) from a `/tmp` test harness, outside `HARDWARE_SIGNALS`. | `coredumpctl`; R `cpu_tripwire.py:33,183-186` |
| O10 | Kiro `permissions.yaml` matches the template (9/9 shell patterns, 0 extra). `~/.kiro/settings/mcp.json` auto-approves `'*'` for convmem. All current MCP tools are logically read-only. | `~/.kiro/settings/mcp.json:13`; D `mcp_server.py:687-943` |
| O11 | Doctor at 00:33: `restic_gate` PASS (`f8d69dc…`), `restic_external` PASS (`a38bd4c…` on USB `rxBUlauer-128Gfs`). Password-copy volume `BIT-Brg-larch-7t` **not attached**. | `convmem doctor`; `lsblk` |
| O12 | Clonezilla-format image `2026-09-16-06-img` on USB `rszl-larch-5t-fs`: `savedisk` of all of `nvme1n1` (boot + root, ~250 GB), about 12 minutes (01:30→01:42). **Predates** the 2026-09-19/20 corruption. The drive has 160 GB free and **cannot hold a second image**. The Restic password file lives on `nvme1n1p2` (mtime 2026-06-30), so it is **inferred, not verified**, to be inside the image. | `ls`, `Info-saved-by-cmd.txt`, `parts`, `df`, `stat` (no secret read) |
| O13 | Hardware: i7-13700K with CPUs 4,5,8,9 offline; Intel RMA pending. The 2026-09-19/20 corruption passed SQLite `integrity_check` and was recovered from an **older, pre-corruption** snapshot. No Restic `forget`/`prune` exists (96 local snapshots). | `lscpu`; config `[hardware]`; ledger `obs_c1499a660d4f` |

---

## Agreed findings (Codex and Opus concur)

Level per `DECISION-REVIEW-GUARDRAILS.md`: local / interface / architectural.

| # | Finding | Code | Level | Direction |
|---|---|---|---|---|
| F1 | Approval recovery turns "could not read" into "absent": `live_decision_state` returns empty on five except/early paths; empty hash + approved row → `retry_chroma`; recovery re-upserts with `_governed_protocol`, which only bypasses the proposal-id check. On the fresh-process `--recover` path a **tombstoned** target is invisible (active-only ledger index) and is also treated as absent. `record --recover` never calls the Restic gate. **Current exposure: zero candidates (O6).** | D `propose_decision.py:105,160-178,220-222,279`; `observe.py:17`; `ledger.py:357,399-401`; `chroma_store.py:386-401`; `convmem.py:1319-1323` vs `:1376-1377` | local | Distinguish unavailable / absent / tombstoned (`include_superseded` for classification); unavailable or tombstoned → `review`; gate `--recover` on the recovery-point check |
| F2 | An automatic segment restore proceeds when the census is unavailable (quarantine only when `lost` is truthy). The restore **destroys the torn files** (overwrite + unlink; only five failure strings kept). The next write refreshes the restore point and **deletes the restore-source generation**. | D `chroma_write_guard.py:756,758,764-787,768,771`; `:658`; `:730` | local | Copy torn files to `chroma.write-guard/torn/<event>/` before the existing replace (interruption-safe); retry the census under the held lock (≈0.2 s); if still unavailable → existing `_quarantine`; release only on a post-restore census tied to that event, or Ryan's explicit bounded continuation |
| F3 | #341 detection is latest-observation: a FAIL can be replaced by `skipped`/`error`, which doctor reports as WARN; skipped audits exit 0. | R `doctor.py:699-748`; R `scripts/chroma_guard.py` audit exit map; R `chroma_write_guard.py:796-828` | local | Audit FAIL → existing quarantine, classified and published **inside** the lock, catching the raise so `audit.json` is still written |
| F4 | Restic captures are not consistent images (O1–O3). A method claim needs a lock-coverage argument plus a positive-control test; clean samples license claims only about those snapshots. The proposed "freeze" (guard flock + SQLite SHARED lock + segment-signature check) is plausible but **blocked as written**: `backup_data_root` applies the qualifying tag at creation, the gate selects by that tag, so a rejected capture stays eligible. | D `restic_snapshot.py:923-928`, `:774-776`; `backup_workflows.py:187` | interface | **Deferred** pending Ryan's loss window and fresh-image cadence. If ever built: two-phase qualification (provisional tag → promote after checks), and interruption must leave the candidate ineligible. Note `restic tag` likely rewrites snapshot IDs (~80%); test against the offsite lineage check |
| F5 | Permission deploy: superset skip retains removed permissions; matching reads only the **first** shell rule; the fallback rewrites the whole file, deleting unrelated user rules (including deny rules). Wildcards (`convmem/*`, `'*'`) silently grant any future MCP tool. | D `scripts/deploy-agent-protocol.sh:278,297-309` | local / interface | Delete the full-file fallback; reconcile owned entries exactly; replace wildcards with explicit tool names |
| F6 | Backup units run whatever branch the shared checkout holds, under a different interpreter (O4). | installed units (O4) | local (ops) | Point `ExecStart` at `runtime-main` and the conda interpreter; add "restart reconcile/MCP as needed; do not start watch" to the deploy checklist |

---

## Settled decisions (do not reopen without new evidence)

- **Roles:** Codex architects; Opus does one adversarial review plus one delta review; Kiro signs off
  (charter `TEAM-CHARTER-2026-07-06.md:119`); Ryan approves; Cursor implements.
- **#341 deploy is separate:** exact `5c6a4a8` via `git merge --ff-only` in `runtime-main` (one commit,
  **not** `origin/main`), audit units installed, **watch stays stopped**, previous revision and unit
  files kept for rollback. It provides detection, not containment. Re-run gate, external, census and
  tripwire checks immediately before.
- **"Verified"** is judged by an operation's actual effects. Corpus-affecting changes need a qualified
  recovery point; a fresh offline image is the practical prerequisite.
- **Deferred:** freeze, identity registry, general HOLD, global read-constructor change, 41-commit
  catch-up.
- **Confidence numbers** for priorities are judgment (about 65–75%), not incident rates.

---

## Acceptance claims (separate; each licensed only by its own evidence)

| Claim | Licensed by | Invalidated by |
|---|---|---|
| **1. Recovery materials independently accessible** | From a device other than this workstation: password retrieved from a non-workstation source (or from a mounted image file), `restic snapshots` on the USB repo opens; physical locations recorded | Password rotation, repo re-init, drive loss/relocation, age (re-check periodically) |
| **2. Snapshot or image X usable for scope S** | Restore to scratch (ideally another machine); full `restic check --read-data` for X (Restic case); SQLite `integrity_check`; segment validate; census 0 lost / 0 extra; golden-question probes (`tests/fixtures/golden_questions.jsonl`) return expected ledger ids; counts and ledger hashes match X's evidence file | X unreadable, scope change, or a later audit dating corruption onset before X |
| **3. Capture method yields consistent snapshots** | Lock-coverage argument **and** a positive control that shows the checks catch an induced inconsistency **and** clean protected trials. Samples alone never license this | Any new writer path, backup-code change, Chroma upgrade, filesystem change; one failure falsifies |
| **4. Detection operational** | Timer enabled; `audit.json` < 36 h and PASS; scratch fault drill (via `--chroma-dir`) shows FAIL → quarantine → doctor FAIL that survives a later skipped run | Timer disabled, stale audit, code change |

---

## Experiment corrections (scratch copies only; none run on production)

- **Read-path writes:** change counter **and** full-file hash **and** inotify/strace on write syscalls;
  run in both journal modes.
- **Approval recovery:** four separate cases — read raises; tombstoned target; hash differs from base
  and proposed; target absent — each with a cold and a warm ledger cache. Expected after the fix:
  `review`, `review`, `review`, `retry_chroma`.
- **Census after restore:** census raises once then succeeds (retry path); raises persistently
  (expect quarantine); torn files present under `torn/`; kill the process mid-restore and re-run.
- **Capture method:** positive control first (unprotected capture during induced writes must sometimes
  fail the checks — otherwise the checks are too insensitive to support claim 3); then the protected
  variant; report per snapshot; keep artifact and method conclusions separate. Include a fresh gate
  invocation after a deliberately rejected capture.
- **Stale-vector blind spot:** re-upsert an id with a new embedding between an HNSW copy and a SQLite
  copy; expect the census to PASS — the known false negative.

---

## What NOT to build

- No general HOLD subsystem; no approved-identity registry; no global `ChromaStore` constructor change.
- No live-backup freeze before Ryan sets a loss window and the tag-eligibility contract is designed.
- No watch start, no 41-commit `runtime-main` fast-forward, no live restore, no permission or service
  change without a separate Ryan grant.

---

## Open questions for Ryan

1. Arc codename, and its boundary with **Recovery Authority** (T4 not authorized) and the write-guard
   containment code.
2. Where newer Rescuezilla images live (is `BIT-Brg-larch-7t` the image/password drive?), whether an
   image has ever been restored, where the drives are physically kept, and where the pre-incident
   image should be retained (its current drive cannot hold a second image).
3. Acceptable loss window (decides whether the freeze is needed at all).
4. Authorize or decline the exact #341 deploy.

**Pending reminder (separate file, not this arc):** `tripwire-deploy.md` is eligible by its own
pre-check. Its procedure needs two corrections: fast-forward to `5c6a4a8` only, and do **not**
"restart convmem-watch" (watch is inactive; a restart would start ingestion).

*2026-10-19:* question 1 answered (Safe Harbor). Question 4 overtaken: the detector is observed
deployed and the reminder file is gone. Questions 2–3 remain open in Safe Harbor STATUS.

---

## Could not verify

- That the 2026-09-16 image actually contains a readable password file, or that any image or Restic
  snapshot restores cleanly.
- Physical custody of the USB drives; whether a password-manager copy exists.
- Whether Recovery Authority's restore classification tolerates cross-file skew outside `chroma/`.
- Whether any unguarded process ever persists HNSW in production (none seen during reads).
- Kiro's effective permission semantics (mode-dependent `autoApprove`; redirection parsing).
- Incident probabilities and costs.

---

## Related files

| What | Path |
|------|------|
| Decision/review guardrails used for the delta review | `docs/inter-model/DECISION-REVIEW-GUARDRAILS.md` |
| Team charter (lanes, Kiro sign-off) | `docs/inter-model/TEAM-CHARTER-2026-07-06.md` |
| Backup arc brief (quiescence open) | `docs/plans/STATUS-complete-data-backup-correction-v2.md` |
| Recovery Authority brief | `docs/plans/STATUS-recovery-authority.md` |
| Write guard (deployed) | `chroma_write_guard.py` |
| Detector candidate | commit `5c6a4a8` (PR #341) |
| Approval recovery | `propose_decision.py`, `convmem.py` (`record --recover`) |
| Backup path | `backup_workflows.py`, `restic_snapshot.py`, `restic_gate.py` |
| Permission deploy | `scripts/deploy-agent-protocol.sh` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on a pushed branch
- [x] `LATEST.md` bullet at top with link and resume state
- [x] `STATUS-*.md` Update Log line — done by Codex in `STATUS-safe-harbor.md` once the arc was named
- [x] Branch pushed

**Codex (picking up):** done — Safe Harbor architecture, STATUS and execution plan authored on
`plan/2026-10-11-safe-harbor`; Opus review cadence complete.

<!-- src: docs/plans/STATUS-safe-harbor.md (branch plan/2026-10-11-safe-harbor, tip b4c0e73) — 2026-10-19 status update -->
<!-- ref: docs/inter-model/LATEST.md — routing bullet updated with this status -->
