# Safe Harbor — deployment preflight and rollout/rollback draft

**Unexecuted draft, overtaken by events — 2026-10-22.** The Safe Harbor runtime
(T1–T5, `c6f0724`) is already live: runtime-main reached it through ordinary
promotions for other arcs (`3e705e4` by October 17; `1a68675` with the watcher
restarted 2026-10-22 13:52 CDT), not through this procedure. Both live segments
already carry release evidence, and the legacy initializer is parked. Nothing in
this procedure is granted; start with [STATUS](STATUS-safe-harbor.md). The proposed
next step is a read-only post-deployment check against the "acceptance after a
permitted rollout" record in [RECOVER](../RECOVER.md#safe-harbor-incident-handling-and-rollout). [Recovery inputs](#recovery-inputs--decided-2026-10-22) were decided on
2026-10-22. No service, corpus, backup/restore or deployment action is authorized.

**Arc: Safe Harbor. DRAFT; NOT AN EXECUTION GRANT.** Codex prepared this procedure
under Ryan's bounded read-only preflight/drafting authorization on 2026-10-14
(America/Chicago). T1–T5 are accepted and merged. Deployment readiness is **OPEN**.
No production service change, corpus write, backup, restore, audit, repair or
release was run. The later authorized synthetic readiness evidence is recorded
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

The authorized preflight/draft and isolated readiness slice are complete. The
installed-interpreter and legacy mechanisms now have focused evidence; recovery
qualification, an operational initialization entrypoint and rollout approval remain
open. These are concrete remaining steps, not a request to redo T1–T5 reviews.

Kiro's bounded evidence and initializer-scope reviews are complete; the scope
PASS is pinned to `c46fbc6` (EXECUTION §22). Next: Ryan's isolated implementation
decision and recovery inputs
(acceptable lost-work interval, newest image completion/scope/location,
independent access and restore/check history). No recovery answer has been inferred. Later
implementation and evidence must address durable preservation, multiple segments
and refusal when the strict oracle cannot pass. Then finish operational review
and request an exact execution decision. No further reviewer, PR, live operation
or runtime fix is invoked by recording this recommendation. The static-only
startup exception retains the warning and grants none of the live steps above.

**Suggested documentation PR title:** Prepare Safe Harbor rollout against the current runtime

**Prepared body (not a PR-creation grant):** Codex records Ryan's T5 merge and the
read-only deployment preflight, then drafts the rollout/rollback sequence. It
identifies old MCP processes, shared-checkout backup routing, missing audit units,
legacy generations without release evidence. Follow-up synthetic checks give 83
installed-Python safety passes and five legacy-state passes, with explicit limits.
No runtime or live state changed. Read this procedure, STATUS and VERIFY before
granting review or later work. **TL;DR:** deployment remains gated on recovery
qualification and a reviewed, preserved legacy-state initialization procedure.

<!-- ref: STATUS-safe-harbor.md, EXECUTION-safe-harbor.md, ../RECOVER.md — current readiness and execution boundaries -->
<!-- src: VERIFY-safe-harbor.md, ../../chroma_write_guard.py, ../../backup_workflows.py, ../../systemd/convmem-chroma-audit.service.example — accepted evidence and rollout contracts -->
