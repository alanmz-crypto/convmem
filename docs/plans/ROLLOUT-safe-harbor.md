# Safe Harbor — deployment preflight and rollout/rollback draft

**Current operational checkpoint — 2026-10-24.** The Safe Harbor runtime
(T1–T5, `c6f0724`) is already live: runtime-main reached it through ordinary
promotions for other arcs (`3e705e4` by October 17; `1a68675` with the watcher
restarted 2026-10-22 13:52 CDT), not through this procedure. Both live segments
already carry release evidence, and the legacy initializer is parked. The
original rollout procedure was not executed. A separately granted read-only
post-deployment check and three-service routing correction are now complete;
[section 7](#7-post-deployment-check-and-service-routing--2026-10-23) records
their exact effects and limits. [Recovery inputs](#recovery-inputs--decided-2026-10-22)
retain the October 22 decisions; confirmation of the newer image/test and physical
custody is pending. Start with [STATUS](STATUS-safe-harbor.md). No further live
action is granted by this document.

**Arc: Safe Harbor. Sections 1–5 are a historical draft, not an execution grant.** Codex prepared this procedure
under Ryan's bounded read-only preflight/drafting authorization on 2026-10-14
(America/Chicago). T1–T5 are accepted and merged. Deployment readiness is **OPEN**.
At that preflight, no production service change, corpus write, backup, restore,
audit, repair or release was run. The later authorized synthetic readiness evidence is recorded
below; it changes neither the deployed runtime nor this draft's execution status.

**October 17 qualification:** the observations and source/service comparisons
below are historical. A later bounded static inspection found runtime-main at
`3e705e4197829f53ebbbd8433b59b60b648309d2`; this procedure has not been rebound to
that runtime or its loaded processes. Ryan retained the Typora CPU-tripwire
warning and authorized static planning/review only. The warning remains visible;
no causal link to ConvMem or hardware cause was established. EXECUTION §22 is the
current initializer review subject, and all live transitions remain ungranted.

**Goal:** bring the accepted recovery/incident contracts into service without losing
the ability to recover or allowing old processes to undermine incident authority.
**Author:** Codex. **Next reviewers:** Kiro for the operational procedure; Ryan for
the recovery inputs, explicit service/process transitions and execution decision.
No reviewer was invoked by preparing this document.

## 1. Exact source and authority

- Candidate: `c6f07241ccf1a71d9d874fee963a37b04091b3ce`, Ryan's squash of PR #394
  at 2026-10-15 03:31:16 UTC. Its tree `57e09250fbd4a74caa2b308e99aefeed8335ac3d`
  equals accepted head `188184b28707eb87c042d579aa7bbcba043dd5d0` exactly.
- Kiro V6 PASS remains pinned to `1cb02fbd9cc15b36c7f3f094237da071ca2dcd18`.
  The successor changed only acceptance/routing docs. Ryan accepted that review
  plus Codex's documentation-delta check as the exact-head BugBot outage exception.
  [VERIFY](VERIFY-safe-harbor.md#t5-hosted-ci-owner-exception-and-squash-mapping)
  records hosted CI and the merge; BugBot reviewed no accepted SHA.
- Runtime checkout observed at `8a7cdab16420893fe26a2648d1d03f2b84d8589d`.
  Exactly four first-parent commits separate it from the candidate: Safe Harbor
  PRs #389, #391, #392 and #394. T1 is already in the deployed checkout.
  This is an on-disk identity, not proof of what each old process loaded.
- Existing architecture, July 7 gate exemptions, Backup v2 ownership and
  Recovery Authority T4/V4k limits remain unchanged. This procedure neither
  closes the Hybrid capture-consistency audit nor qualifies continuous Restic
  capture. Watch activation and other arcs' live canaries are excluded.
- Current bounded evidence slice (EXECUTION §20) is complete: installed-interpreter
  checks and synthetic legacy-state rehearsal only. Future command examples below
  remain review material, not commands to execute under that grant.

## 2. Observed preflight, with limits

Observations were taken 2026-10-15 approximately 04:26–04:53 UTC (October 14 local).
They must be refreshed at the maintenance boundary. Other agents/timers were
active; this is not a frozen cross-file snapshot.

### Code roots, processes and services

- `/home/lauer/Projects/convmem/.worktrees/runtime-main` was clean at `8a7cdab`.
  The installed CLI and inspected Codex/Cursor/Kiro/Claude MCP entries select
  this root and `/home/lauer/miniforge3/envs/convmem/bin/python`.
- Shared checkout `/home/lauer/Projects/convmem` was on the unrelated feature
  branch `fix/2026-10-12-issue-286-stage2-wedge-fixes`, at `7d46e6e`, with
  unrelated untracked files. It was not switched, cleaned or edited.
- The host process listing showed **29 MCP servers** using runtime-main. The
  oldest started October 11, before runtime-main moved on October 12 at 06:54 CDT.
  Loaded module identity is unknown; lazy imports make the disk SHA insufficient.
  All require replacement, not a claim that a fast-forward upgrades them.
- A concurrent `convmem.py index --file` process was observed (PID 1754207 at
  23:47 CDT). It belonged to another activity and was not stopped. Watch being
  stopped does not establish quiescence. PIDs are historical evidence, never a
  reusable kill list; enumerate command/start-time/owner again before acting.
- `convmem-watch.service`: inactive/dead, disabled, MainPID 0. Preserve this
  state. Its OOM drop-in exists; no change to it is proposed here.
- `convmem-reconcile.timer`, local/external Restic timers and cross-project
  digest timer were active/waiting. Their oneshot services were inactive between
  invocations. Reconcile runs about every two minutes from runtime-main.
- Restic local/external services invoke scripts in the **shared feature checkout**.
  Their configured PATH resolves `python3` to `/usr/bin/python3.14` (3.14.8), not
  the production conda interpreter. The weekly digest also uses the shared root.
- `convmem-chroma-audit.service` and `.timer` were not installed. `audit.json`
  was absent. Installing/enabling them is a future operational change, not part
  of this inspection. Audit writes guard telemetry/events and can quarantine;
  the example unit's historical “read-only” description is not its effect contract.

The first sandbox-local `/proc` scan saw only two namespace processes. Its empty
result is **excluded** as evidence of no host clients. A separately approved
read-only host `ps` listing supplied the counts above. Selected config fields
and package metadata were read without importing project code or Chroma. No
production CLI/MCP startup ritual or session indexing ran.

### Interpreter and native backend

Proposed choice is to **retain** the production interpreter, subject to isolated
qualification, rather than silently move all clients to a different environment:

- Production: conda Python 3.11.15, Chroma 1.5.9, hnswlib 0.8.0, NumPy 2.4.6.
- Prior local proof: base miniforge Python 3.13.12, Chroma 1.5.9, hnswlib 0.8.0,
  NumPy 2.4.4. Hosted proof: Python 3.12.15.
- Both installed Chroma Rust bindings have SHA-256
  `a9794735847c3a78c15931d869cee8368fddbb10048c3d098bc09a14130075ad`.
  The hnswlib binaries differ by Python ABI. Production binary SHA-256 is
  `e2338cb057f75eb0d84d856f1626d56d876703c47278772ee48e2c6c31d7073d`.
  Matching Rust bytes are useful identity evidence, not proof that the complete
  Python 3.11 environment passes the candidate. No tests/import probes ran during
  that preflight; the subsequent focused run is recorded in section 3 below.

### Targets and existing guard state

- Config: `/home/lauer/.config/convmem/config.toml`, observed SHA-256
  `a8c279aafa0050f98c34717e40383d7f609230a875759827714614922c50e23b`.
  Configured Chroma is `/home/lauer/.local/share/convmem/chroma`, export is
  `/home/lauer/.local/share/convmem/knowledge_units.jsonl`.
  The Chroma path was canonical already, not a symlink.
- Restic env specifies `complete-data-v2` and the complete root
  `/home/lauer/.local/share/convmem`; env-file SHA-256 was
  `40ca2e3c0f71c50bd193b5e9399b89e0916758da925e9d2e0a3ec18bec52c5f3`.
  This is configuration inspection, not an executed gate PASS. Resolve every
  affected path, including governed files and enabled shadow sinks, at execution.
- Guard root: `/home/lauer/.local/share/convmem/chroma.write-guard`.
  No `QUARANTINE.json` was present. This is not a health or semantic-integrity
  verdict. The guard has `native-write.lock`, events and two current generations.
- Segment `5cda8744-0eb5-4580-9ff2-c57e985abf68`: CURRENT
  `g1791846318855181664-3011058`, manifest created October 12 23:05:18 UTC.
- Segment `5e85bc5f-5bea-4129-9602-9afe15991cca`: CURRENT
  `g1792023447979504839-170599`, manifest created October 15 00:17:28 UTC.
- Both manifests contain only `segment`, `live_signature`, `created_at`, `pid`;
  neither has `release_evidence`. Both signatures matched live segment stat
  signatures during inspection. No SQLite query, HNSW load, content validation
  or vector census was performed.

**Material adoption issue:** candidate `ChromaWriteGuard.reconcile()` skips a
generation when its signature matches. It does not upgrade these manifests just
because the code was upgraded. `_refresh_snapshot()` captures release evidence
when it does refresh, but it is not an operator-facing migration command and
prunes unpinned old generations. A generic deploy-time `reconcile` is neither a
guaranteed evidence upgrade nor an inspection: it can restore damaged segments.
Do not invent evidence for an old generation or induce an ordinary write to
“initialize” the new format. A restore using a generation without evidence can
remain contained with no validated release available under the strict oracle.
The synthetic rehearsal now confirms that missing evidence refuses source binding
before replacement: the torn files remain and the incident cannot be released.

### Recovery resources

- Root filesystem UUID `93d30805-f5c4-43a6-a746-ef914d6e5f8d` is ext4, currently
  `/dev/nvme0n1p2`, about 279.5 GiB available. Device numbering differs from the
  earlier image discussion; use UUID and disk serial, never copied `/dev/nvmeN`
  names, to select an imaging/restore target.
- `/run/media/lauer/ext-ex4-1T-NVMe` is mounted ext4, UUID
  `cce6ae9a-b6ce-49da-8dd9-feb94b817777`, about 869.2 GiB available. The top-level
  listing was empty excluding `lost+found`. No allocation or write was made.
- External Restic repo path exists on mounted rxBU volume, UUID
  `f1bd69b4-e567-4ef3-89ec-13faff0602e9`, about 78 GiB available.
- The password-copy path now exists and is readable at
  `/run/media/lauer/BIT-Brg-larch-7t/convmem-secrets/restic.password` (mode 0600,
  45 bytes). The workstation password file is also 45 bytes. **Contents were
  not read or compared**; size equality is not key verification. Independent
  retrieval/use and physical custody remain open.
- Existing journal reports local snapshot
  `ca2a6f047a707820bc8209ca7a4bc6c2d145910f7af0eec875f69988535510a1`
  with tag `convmem-data-v2` at October 14 00:18 CDT, copied as
  `c288c04557cf60cc3483e4e12571c93431246dcef4e7b98f77096f705e8a8794`
  at 21:54 and 23:03 CDT, with `original == source`. Earlier external attempts
  failed while the repo path was unavailable. These are dated service reports;
  no Restic command, new check or restore was run. They do not qualify an artifact.
- No current Rescuezilla image was identified on the inspected mounted top-level
  locations. Newest image, completion, scope, custody, restore history and the
  acceptable lost-work interval await Ryan. Absence from this limited inspection
  does not mean an image does not exist elsewhere.

### Recovery inputs — decided 2026-10-22

Claude gathered facts read-only (file names, dates, sizes and small Clonezilla
metadata files; no image data, keys or Restic commands). Ryan delegated items 1–3
("You're given authority"); Claude adopted its stated recommendations. Item 4 is
Ryan's report.

- **Images found** (search depth 5 on mounted volumes):
  `/run/media/lauer/ext-ex4-1T-NVMe/2026-10-20-05-img` (Clonezilla Live 3.3.2,
  saved 2026-10-20 05:03–05:16 UTC, 311 GB) and
  `/run/media/lauer/rszl-larch-5t-fs/2026-10-11-06-img` (06:38–06:51 UTC, 254 GB).
  Both are `savedisk` images of the workstation disk: their `blkid.list` UUIDs
  `01A6-9C51` (vfat `/boot`) and `93d30805-f5c4-43a6-a746-ef914d6e5f8d` (ext4 `/`)
  match the current root disk, so `/home` and the ConvMem data are included. Both
  logs show "Finished saving" for both partitions; neither log records
  Clonezilla's restorability check.
- **Restic:** `convmem-restic-local` reported `snapshot OK` (tag
  `convmem-data-v2`) at 2026-10-22 00:21 CDT; `convmem-restic-external` finished
  every two hours through 21:04 CDT. These are journal reports, not a new check.
- **1. Lost-work interval:** one day for ConvMem data, delivered by the daily
  snapshot; "since the last disk image" for the rest of the system. A tighter
  interval is a backup-schedule change owned by Complete-data Backup v2.
- **2. Recovery point:** `2026-10-20-05-img`, keeping `2026-10-11-06-img` as the
  older fallback. Ryan plans a new image and test on 2026-10-23; once tested it
  becomes the recovery point, and an image made after the October 21–22 snapshot
  refreshes cannot reintroduce legacy snapshot generations.
- **3. Independent access (policy):** keep at least one image drive and a Restic
  password copy unplugged and stored away from the workstation. Observed
  2026-10-22: all six external drives were mounted, including both image drives,
  `rxBUlauer-128Gfs` (Restic copy) and `BIT-Brg-larch-7t` (password copy). The
  physical step is Ryan's; no agent unmounts drives or handles keys.
- **4. Restore history (Ryan):** "Clonezilla is restorable. Tested." The image
  was not named; "Image is becoming two weeks old" fits `2026-10-11-06-img`.
  "agents have restore from restic months ago." No restorability check is
  recorded for `2026-10-20-05-img` itself.

## 3. Readiness decisions before activation

### Completed isolated evidence; remaining operational gap

Codex used the installed production Python 3.11.15 and actual packages on
synthetic roots only. **83 existing safety cases passed**, including real backend,
strict release/stale-vector controls, alias admission and uncertain approval
publication/concurrency. **Five legacy cases passed**, including an actual
refresh/restore/release positive case and pending-work refusal. No skips or source
drift; runtime stays `c6f0724`. [VERIFY's readiness record](VERIFY-safe-harbor.md#isolated-rollout-readiness--installed-interpreter-and-legacy-state)
pins source, selection, logs, identities and limits. Kiro's bounded evidence
review PASS is pinned to `f45b051`, after same-session coverage completion. It is
not a full Python 3.11 suite, owner acceptance or deployment PASS.

The legacy rehearsal establishes the existing mechanism, not a live command:
the test archives old bytes outside the prune tree, then invokes the private
refresh under the native lock. A synced fixture becomes releasable; a fixture
with pending work still refuses `watermark_drift`, even after successful repair.
No queue flush or database mutation is performed by refresh. The ordinary scratch
archive copy is not a power-loss-qualified archival procedure. The public CLI has
no explicit unchanged-generation initializer. [EXECUTION §22](EXECUTION-safe-harbor.md#22-bounded-legacy-source-initialization--proposed-scope-not-a-grant)
now proposes the bounded entrypoint: whole-set eligibility, durable originals
before prune, new saves only, and honest partial/uncertain completion. This later
scope was not part of Kiro's `f45b051` review and is not implemented or granted.
No private production one-liner is provided. Multiple live segments and actual
pending work remain to be handled under that separately reviewed procedure.

### Decisions still open

1. **Recovery point:** Ryan supplies maximum lost work for maintenance and routine
   operation. Name the exact image/snapshot and independent key path. Obtain a
   separately scoped capture/qualification grant if required. Preserve the
   pre-incident image. The proposed extra drive has capacity, not proven protection.
2. **Interpreter:** Kiro has reviewed the focused Python 3.11 evidence and its
   limits. Ryan's operational choice/acceptance remains pending. No dependency
   upgrade, interpreter switch or full environment certification is implied.
3. **Legacy generations:** review the proposed EXECUTION §22 scope, then grant
   its bounded implementation/evidence separately if accepted.
   Preserve original guard/generation bytes and CURRENT references before any
   refresh can prune them; do not fabricate release evidence for the old saves.
   Prefer an explicitly authorized, validated new generation using existing guard
   mechanics. The existing public CLI lacks that explicit operation; a separately
   bounded procedure/tool decision is needed. If the actual store has pending
   work, creating a manifest alone cannot establish the oracle. No private-method production
   one-liner, forced queue flush, census-only release or generic reconcile fallback.
4. **Process/service manifest:** name the owners of MCP parents, manual indexing
   and all launch paths. Agree the maintenance window and prevent respawn before
   draining. Stopping readers matters because reads can write bookkeeping.
   Preserve watch as stopped/disabled. No blanket stop of unrelated applications.
5. **Reviewed procedure and grant:** Kiro reviews the resulting exact procedure;
   Ryan grants its named transitions. Unresolved entries above keep activation
   closed. Draft completeness is not operational readiness.

## 4. Proposed rollout sequence — future grant only

### A. Prepare while the old runtime remains in service

1. Pin this candidate and refresh the observations. Refuse if runtime-main is
   dirty, has moved from the recorded base, the candidate differs, or any actual
   target/profile/interpreter differs. Review only the new delta before proceeding.
2. Finish the isolated interpreter and legacy-state rehearsals and record their
   exact source/results. Name approved preservation paths, required free space
   and complete artifact/config/key recovery dependencies.
3. Qualify the recovery artifact for the accepted loss interval under its own
   bounded grant. A fresh offline Rescuezilla image is one option, retaining the
   older image. A reboot invalidates the process/unit census: inspect it again.
   A restore drill must use a separate approved target, never the only backup disk.
4. Prepare exact unit/drop-in changes for review. Proposed Restic services use
   the selected production interpreter and runtime-main directly:

   ```text
   /home/lauer/miniforge3/envs/convmem/bin/python3.11 /home/lauer/Projects/convmem/.worktrees/runtime-main/backup_workflows.py ensure --env-file /home/lauer/.config/convmem/restic.env
   /home/lauer/miniforge3/envs/convmem/bin/python3.11 /home/lauer/Projects/convmem/.worktrees/runtime-main/backup_workflows.py copy-offsite --env-file /home/lauer/.config/convmem/restic.env
   ```

   Preserve schedules, complete-data-v2 profile, repositories, tags and lineage.
   Do not install the old shared-checkout examples unchanged. A systemd drop-in
   replacing ExecStart must clear the old ExecStart first. Review the final unit
   text/environment and inherited settings; these example argv are not an install.
   Hold the digest timer until its shared-root entrypoint disposition is explicit.

### B. Establish and prove maintenance quiescence

1. Under the future grant, stop the named **timers first**, then drain their
   active services and unrelated-to-watch manual ConvMem writers. Record exactly
   which timer enablement/active states are to be restored. Do not interrupt a
   backup or writer mid-commit merely to meet a timetable; investigate a stuck job.
2. Coordinate all MCP/client parents: prevent new launches, close the selected
   clients, and verify their old child processes exited. Enumerate any remaining
   direct clients. Application flock/quarantine alone cannot establish this boundary.
3. Verify no new writer can enter during capture/adoption, not merely that one
   `ps` sample was empty. Recheck stopped services and all known launch sources.
   If access cannot be controlled, postpone the maintenance. Refresh guard state
   under this boundary; any new incident changes the plan and stops generic rollout.
4. Make the separately authorized preservation capture of complete relevant state:
   Chroma, guard generations/CURRENT/markers/events, governed intent/events/export,
   config and exact deployment/unit files. Record manifest identity and durable
   completion. This capture is evidence preservation and rollback support; it
   does not replace independent artifact qualification.

### C. Install the pinned source and adopt state deliberately

1. Ryan/authorized operator advances clean runtime-main **only** to `c6f0724`,
   after confirming the ancestor relationship. The reviewed command is:

   ```sh
   git -C /home/lauer/Projects/convmem/.worktrees/runtime-main merge --ff-only c6f07241ccf1a71d9d874fee963a37b04091b3ce
   ```

   This is a future local deployment command, not permission for agents to merge
   a PR, push main or execute it now. Do not use moving `origin/main` as the target.
2. Install only the reviewed unit/drop-in changes and reload the unit manager
   under that grant. Keep timers and clients held. Do not start watch.
3. Perform the specifically reviewed legacy-state initialization from section 3,
   with exact input manifest, pinned source/interpreter and abort conditions.
   This substep remains **UNRESOLVED**; the draft supplies no executable adoption
   command. A failure or unavailable evidence retains containment and the old bytes.
4. Run only the granted diagnostics. `status`, `validate` and `census` have
   narrower effects than `audit`; audit publishes authority/telemetry. Production
   doctor and MCP/search also have incidental paths and are not substitutes for
   approved read-only checks. Never use `reconcile` as a health probe.
5. After a clean permitted audit, enable the reviewed audit timer if explicitly
   granted. A failed or unavailable check stops this sequence. `skipped` is not a
   passing audit. Check evidence freshness separately from a zero exit code.

### D. Resume only named consumers and observe

1. Recreate selected MCP clients against the pinned root/interpreter. Check new
   process start identities and selected target configuration; do not reuse old
   imports. Any functional query or write is a separately named canary with its
   expected effects. No index/approve/recover command is an implicit smoke test.
2. Restore only the pre-approved reconcile/backup schedules after their new
   routing and gates pass. `ensure --check-only` is toolchain evidence and does
   not license a write. Freshness must use the actual evaluation time; midnight
   rollover/future-date refusal is not permission for fallback or skipped gates.
3. Keep watch stopped/disabled and preserve the existing OOM settings. Digest
   resumption requires its reviewed routing. Record the observation interval,
   events, expected no-incident result and exact release criterion before resuming.
4. If any automatic restore occurs, stop the initiating operation. Every restore
   requires a fresh owner disposition; no automatic release or retry is authorized.
   Close deployment only with observed code/process/guard identities and the
   authorized diagnostics. Do not label that disaster-recovery proof.

## 5. Rollback and stop conditions

**Default on an unexpected result: stop affected activity and preserve evidence.**
Stopping timers/clients itself needs the named future operational authority;
this drafting grant does not permit emergency service manipulation.

- **Before new code has touched durable state:** keep consumers held, compare
  state and deployment records with the completed pre-change preservation
  manifest. If the reviewed procedure proves no incompatible state was published,
  an expressly authorized operator may restore the old source/unit selection.
  Pin old source `8a7cdab`, old interpreter and exact old unit bytes. No blanket
  `git reset --hard`, shared-checkout switch or automatic restart.
- **After a new incident, generation, disposition, approval event or uncertain
  write/removal:** do not resume the old runtime against that store. The old guard
  is version 1; it lacks T3 preservation/pinning/release semantics. Its refusal of
  an unknown marker does not prove whole-store rollback compatibility. Keep
  current authority and originals; prefer a separately reviewed forward correction.
- **If data restoration is required:** use a new exact-artifact/target grant after
  independent qualification. Restore coherent affected state, not just HNSW or a
  convenient old marker. Preserve post-change evidence separately. Code rollback
  does not roll back completed Chroma/export/APPROVED effects; uncertain outcomes
  must be reconciled from authoritative records without truncation or blind replay.
- Stop for any unexpected schema/target/config/clock/backend identity, live writer
  during quiescence, preservation failure, missing recovery dependency, new
  incident or failed/unknown validation. No force clear, backup skip, invented
  release evidence or erased incident is an allowed escape.

## 6. Completion and next bounded work

The preflight, isolated readiness evidence, read-only post-deployment inspection
and three-service routing correction are complete. T1–T5 remain accepted and
merged. The runtime is already live; repeating the historical rollout is not the
next step. The initializer candidate remains parked, unreviewed and unaccepted.

Open items are (1) Ryan's newest completed image and actual test, plus physical
custody of an image drive and password copy; and (2) evidence from the next normal
scheduled runs using the corrected routes. Existing configuration checks do not
prove those jobs have executed successfully. Do not force a job, restore, release
or initializer to close either item. Scope any necessary follow-up separately.
No PR or merge is proposed for the parked implementation branch by this receipt.

## 7. Post-deployment check and service routing — 2026-10-23

**Who/authority:** Codex, after Ryan's read-only inspection grant and subsequent
explicit routing-correction grant ([EXECUTION §24](EXECUTION-safe-harbor.md#24-post-deployment-inspection-and-scheduled-service-routing--completed)).
All times below are America/Chicago unless marked UTC. Observations are a bounded
October 23 snapshot, not standing guarantees. No application runtime was changed.

### Read-only findings

- **Runtime/process identity:** clean deployed checkout
  `1a686753d8fd1b710883050e8a4f9c45b7ae1e26`, last fast-forward October 22
  13:52:31 CDT. The watcher (PID 1149, started October 23 13:14:52 CDT) and ten
  observed MCP servers used `runtime-main` with production conda Python; all
  started after that code update. The host process scan found no older client;
  it does not prove every loaded module's bytes or constitute a writer freeze.
- **Installed backend:** Python 3.11.15, Chroma 1.5.9, hnswlib 0.8.0, NumPy
  2.4.6. Native binding SHA-256
  `a9794735847c3a78c15931d869cee8368fddbb10048c3d098bc09a14130075ad`
  matched the saved release-evidence identity. Core guard/CLI/Restic gate,
  resolver/workflow and conflict-event files matched accepted `c6f0724`;
  store/write-store/doctor/proposal files have later changes from other merged
  PRs and were not independently re-reviewed in this operational check.
- **Guard authority:** configured target is canonical
  `/home/lauer/.local/share/convmem/chroma`; only the adjacent
  `chroma.write-guard` authority was found, with no `QUARANTINE.json`. No Chroma
  client, new audit or live SQLite query was used for this inspection.
- **Saved generations:** summaries segment
  `5cda8744-0eb5-4580-9ff2-c57e985abf68` points to
  `g1792612804689283045-3913359` (October 21; recorded metadata/vector watermark
  214400); knowledge segment `5e85bc5f-5bea-4129-9602-9afe15991cca` points to
  `g1792774494736299479-171509` (October 23; recorded watermark 218447).
  Both contain release evidence. All ten saved segment-file hashes matched
  their manifests; pointers/manifests and file metadata were stable during the
  read. This does not establish eligibility against current SQLite watermarks
  or semantic correctness, and no release was attempted.
- **Existing audit:** timer active/enabled; last record October 23 00:24:04 CDT,
  PASS for two segments, 118,739 HNSW vectors, zero lost/extra IDs. Seven recorded
  daily audits (October 17–23) passed. The read event log had no malformed line
  or recorded restore/quarantine/release. ID coverage does not exclude stale
  vectors or semantic corruption. No warning was cleared.
- **Routing defect:** local Restic, external copy and cross-project digest
  service commands still used the shared checkout. Backup PATH selected system
  Python 3.14. The wrappers and inspected static backup import closure matched
  runtime-main that day, but future feature-branch changes could change scheduled
  behavior. Dynamic imports were not exhaustively proven.
- **Existing backup journals:** local success October 23 00:19:59 CDT,
  source `bc3c8d1521417ceb099c4611c5c5e31a9c432f9f1f47d185edfed6b7ebd70d1f`.
  External destination
  `6c5b372b753d6bcc94d226560e9856800f23edd912eecf96306562ee8348201d`
  recorded that source as its original. External-copy attempts at 09:28,
  11:03 and 13:02 found the repository config unavailable; later attempts
  succeeded, most recently 23:04:06 CDT. The cause of that unavailability was
  not established. These are pre-correction journal observations; this lane ran
  no Restic command and did not qualify recovery.

### Installed routing correction

At **2026-10-23 23:26:43 CDT / 2026-10-24 04:26:43 UTC**, Codex installed
`90-safe-harbor-routing.conf` under each of these user-unit drop-in directories:

- `~/.config/systemd/user/convmem-restic-local.service.d/`:
  script `restic-ensure-chroma-snapshot.sh`;
  drop-in SHA-256 `12cd9571ce528999bdff62c50ce6a41a692b374b13530027643a99f7004f74e9`.
- `~/.config/systemd/user/convmem-restic-external.service.d/`:
  script `restic-copy-external.sh`;
  drop-in SHA-256 `48b08bbdb59ac3512a9b6ddb37076d7bf9b1840fd19e5cf3a9103c84d75565ab`.
- `~/.config/systemd/user/convmem-cross-project-digest.service.d/`:
  script `cross-project-digest.sh`;
  drop-in SHA-256 `40c5fb6bec1770e6570af4bdce19f801df2a7c7116e0a82ebc9dbd51bf614439`.

All three use this configuration, with `<script>` replaced as listed:

```ini
[Service]
WorkingDirectory=%h/Projects/convmem/.worktrees/runtime-main
Environment="PATH=%h/.local/bin:%h/miniforge3/envs/convmem/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=
ExecStart=%h/Projects/convmem/.worktrees/runtime-main/scripts/<script>
```

The digest additionally sets:

```ini
Environment="CONVMEM_ROOT=%h/Projects/convmem/.worktrees/runtime-main"
Environment="CONVMEM_PY=%h/miniforge3/envs/convmem/bin/python"
```

Original units and timer files were retained byte-for-byte. Restic still resolves
through the existing `~/.local/bin/restic`; profile `complete-data-v2`, local repo
`/home/lauer/.local/share/convmem-restic`, external repo
`/run/media/lauer/rxBUlauer-128Gfs/convmem-backups` and credential configuration
were unchanged. No secret values were read into this record. Digest's existing
environment file and fail-on-fallback setting remain in effect.

### Checks and limits

- Staged and installed `systemd-analyze --user verify --man=no` checks returned
  0 for all three units. The installer refused changed originals, an existing
  destination, active jobs, changed staged bytes or a changed deployed checkout.
  Installed files/directories were synced before the manager reload.
- After `systemctl --user daemon-reload`, effective working directories,
  commands, PATH and digest ROOT/PY matched the intended configuration;
  `NeedDaemonReload=no`. Python resolved to the production Python 3.11 path.
- Installed drop-in hashes matched staged hashes. Original service/timer hashes
  were unchanged. Services remained inactive/dead, with no main PID; timers
  remained active/enabled. No service was manually started or restarted.
- Calendar rules remain local `00:15`, external `01/2:00`, digest Monday `09:00`.
  Reload resampled randomized delays: observed next triggers were October 24
  00:17:50, October 24 01:00:58 and October 26 09:08:21 respectively. This does
  not imply that those runs occurred or passed.
- Existing jobs continue on their normal schedules. **No scheduled execution
  under the new routing was observed at this checkpoint.** Configuration
  validation is not a backup, copy or digest completion result. There was no
  corpus operation, audit invocation, backup/restore, initializer, repair or
  release initiated by this lane, and no application code change.

### Rollback of this correction only — not executed

If separately authorized, first inspect current drop-ins and active jobs. Refuse
to discard later edits; compare against the three recorded hashes. Remove only
the three `90-safe-harbor-routing.conf` files and reload the user manager, then
inspect effective configuration and timers again. Do not use `systemctl revert`,
which could remove unrelated overrides. No process start/restart is inherent in
this rollback. It would restore the prior shared-checkout routing, including its
known drift risk; it is not a data/runtime rollback or a recovery procedure.

### Recovery confirmation still pending

Ryan was asked which image is newest and completed, what test was actually
performed, and whether an image drive plus a Restic password copy are unplugged
and stored away from the workstation. No reply had arrived at this checkpoint.
The October 22 loss-window policy remains recorded above. The October 23 image
was planned, not confirmed; the general report “Clonezilla is restorable. Tested.”
does not identify the tested image. No drive action, secret read, image check,
backup or restore was performed to infer an answer.

### Read-only follow-up — October 23, 23:53–23:55 CDT

Ryan authorized: “go: Next step: Confirm recovery facts and inspect the next
scheduled results.” Codex ran the required doctor/brief/unresolved orientation
(doctor exit 0), then inspected timer/service properties, existing journals,
mount metadata and top-level image metadata on mounted external volumes. No
job start, configuration change, restore, image verification or initializer was
performed. Doctor's logical read path may perform incidental Chroma bookkeeping;
this is not a claim that every storage byte was unchanged.

- **No post-correction execution yet:** the three service journals have no entry
  since the 23:26:43 routing change. Timers retain the next triggers recorded
  above: October 24 00:17:50 and 01:00:58 for local/external, October 26 09:08:21
  for digest. All three remain active/enabled. Effective service commands still
  use runtime-main; `NeedDaemonReload=no`. `Result=success` with missing/older
  timestamps is not evidence of a new run. The last external success is still
  October 23 23:04:06, before the correction.
- **Existing availability checks pass:** doctor reported the same local source
  and external destination IDs recorded above, a matching configured password
  copy, no Chroma quarantine and the previous daily audit. CPU tripwire reported
  zero native faults this boot. Other nonfatal warnings remain; this follow-up
  did not clear or reclassify any warning.
- **Image visibility:** `/run/media/lauer/ext-ex4-1T-NVMe/` is not mounted and
  its mountpoint is absent. The previously recorded October 20 image is therefore
  unavailable to this inspection; absence does not prove unplugging or remote
  custody. A top-level scan of mounted external volumes found
  `/run/media/lauer/rszl-larch-5t-fs/2026-10-11-06-img`. Its small metadata files
  name a saved whole `nvme1n1` disk with boot/root partitions and a 254 GiB-class
  image. That metadata is not integrity or restore-test evidence; image payloads
  were not scanned or restored. No newer completed/tested image was established.
- **Password-copy custody:** the configured copy at
  `/run/media/lauer/BIT-Brg-larch-7t/convmem-secrets/restic.password` exists on a
  currently mounted volume. File contents were not printed or manually opened;
  doctor's existing check reported a match. This particular copy is not unplugged
  or physically separated. Another independently stored copy remains possible
  but unconfirmed.

Ryan's image-specific test and physical-custody questions are pending. The next
useful backup-result inspection is after October 24 01:05 CDT, subject to actual
job completion; digest evidence cannot be checked before its Monday run. Keep
this read-only follow-up scope: observe normal runs, report failures before any
correction, and do not force jobs to satisfy the checkpoint.

### Scheduled local backup and health refresh — October 24

Ryan asked Codex to perform the follow-up after 01:05 CDT and suggested a doctor
refresh. Codex remained in the session and observed the normal timers; no agent
automation, manual backup, service change or initializer was created/run.

- A doctor refresh after midnight exited 1 solely on local snapshot freshness:
  October 23 source `bc3c8d15…` no longer covered the current local day. External
  freshness was WARN; guard, audit and CPU checks passed. No bypass or repair
  was applied.
- The corrected local service started automatically at **00:17:51 CDT** and
  completed at **00:19:52**, `Result=success`, `ExecMainStatus=0`. Journal output
  identifies new `convmem-data-v2` source
  **`0295cf8e4922568d4b9633ee9fc8f2246939f3c116ff75f69919f38428cda26d`**.
- During that invocation, `/proc/864711/exe` resolved to
  `/home/lauer/miniforge3/envs/convmem/bin/python3.11`; cwd was
  `/home/lauer/Projects/convmem/.worktrees/runtime-main`; argv ran that checkout's
  `backup_workflows.py ensure --env-file /home/lauer/.config/convmem/restic.env`.
  The allowlisted PATH matched the installed override. This is observed running
  process identity, beyond unit configuration alone.
- The subsequent doctor refresh exited **0** and recognized the new local source.
  External status remained **WARN: no destination snapshot with original=0295cf8e4922**,
  before the scheduled 01:00:58 copy. Overall doctor success therefore does not
  close the external-copy check.
- Existing audit journals show the normal daily audit passed at **00:13:02**:
  two segments, 118,977 vectors, zero lost IDs. No new audit was invoked by this
  lane. This is ID/structural coverage, not semantic integrity or restore proof.

**Open at 00:23 CDT:** external scheduled completion/lineage, Monday's digest,
and Ryan's image-specific test/custody answers. Local routing/execution is now
demonstrated for this invocation. The snapshot has not been restored or otherwise
qualified as a recovery artifact by this check.

<!-- ref: STATUS-safe-harbor.md, EXECUTION-safe-harbor.md, ../RECOVER.md — current readiness and execution boundaries -->
<!-- src: VERIFY-safe-harbor.md, ../../chroma_write_guard.py, ../../backup_workflows.py, ../../systemd/convmem-chroma-audit.service.example — accepted evidence and rollout contracts -->
<!-- ref: /home/lauer/.config/systemd/user/convmem-restic-local.service.d/90-safe-harbor-routing.conf, /home/lauer/.config/systemd/user/convmem-restic-external.service.d/90-safe-harbor-routing.conf, /home/lauer/.config/systemd/user/convmem-cross-project-digest.service.d/90-safe-harbor-routing.conf — installed October 23 routing -->
