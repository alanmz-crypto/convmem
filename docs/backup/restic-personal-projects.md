# Restic profile for thirteen personal project roots

**State:** implementation staged; no repository, snapshot, password, or timer is
created by this branch. Live activation needs a confirmed writer policy and the
exact external-change grant. This profile is independent of ConvMem's existing
Restic profile and does not alter its configuration, repositories, or timers.

## Scope and layout

The source manifest is the thirteen absolute paths in
`scripts/restic-personal-projects.py`: four directories under
`/home/lauer/Projects/SubProjects` and nine under `/home/lauer/.local/share`.
No exclusions are passed to Restic. Hidden files, Git metadata, `.crush` data,
SQLite databases, WAL/SHM files, dependencies, and preview artifacts are in
scope. Restic stores symlinks as links; it does not copy their targets.

`butsaba-google-backup` and `butsaba-drive-tools` appeared after the request.
They were reviewed on 2026-10-21 and belong to the separately managed Google
integration backup. They are explicitly outside this thirteen-root profile.
Any other new top-level `butsaba*` or `ryan*` directory in `.local/share`
blocks preflight until reviewed.

| Item | Path |
| --- | --- |
| Local repository | `/home/lauer/.local/share/restic-projects` |
| Removable repository | `/run/media/lauer/rxBUlauer-128Gfs/restic-projects` |
| Local password | `/home/lauer/.config/restic-projects/restic.password` |
| Offline password copy | `/run/media/lauer/BIT-Brg-larch-7t/restic-projects-secrets/restic.password` |
| Run report and lock | `/home/lauer/.local/state/restic-projects` |

The removable repository and offline password copy use different ext4 drives.
The wrapper verifies their filesystem UUIDs before writing. It pins
`/home/lauer/.local/bin/restic` version 0.19.0 at SHA-256
`20683e7746b70e99dd0538cc2740abd222dbb6b3a6851071be9880e3fe02694c`.
The password is never stored in either repository or source set.

## Consistency and verification

The source filesystem is ext4 on `/dev/nvme0n1p2`, without a filesystem
snapshot facility exposed for these paths. A live capture therefore needs
writer coordination. The staged wrapper has an explicit quiescence mode for
the email-ops timer/service, health index, workspace index, and job-list
watcher. It restores their prior active states immediately after local capture.
It checks open writable descriptors owned by the user and hashes all regular
files before and after capture. An unexpected write or failed restart rejects
the snapshot. This does not prove that a process without an open descriptor
cannot start writing during capture; live activation requires acceptance of
that residual race or an application-specific export design.

Preflight checks the thirteen canonical roots, adjacent-directory drift,
repository/password overlap, Restic pin, and symlink targets. Of 1,437 links
observed on 2026-10-21, seventeen point outside the manifest: sixteen
`/etc/hosts` escape-test fixtures and one stale Typora socket link under
`/tmp`. Those patterns are reviewed; new outside-target patterns block capture.

A successful backup requires a full local snapshot ID, exact snapshot root
list, successful offsite copy with `destination.original == source ID`, Restic
data-read checks on both repositories, and a scratch restore from the removable
drive using its offline password. The first backup does a full data read and
full restore; later runs read a 5% subset and restore one regular file from
each root. The full restore also runs SQLite integrity checks on recognizable
databases outside deliberately corrupt test fixtures. Reports distinguish
`TWO_COPY_VERIFIED`, `LOCAL_ONLY`, and `FAIL`; only the first is two-copy
coverage. Each run writes JSON to stdout and `last-run.json`.

## Activation order

1. Confirm that the source manifest remains thirteen paths and that the
   quiescence policy is acceptable. Review the two repository locations and
   offline password drive. Ryan chose 00:45, 06:45, 12:45, and 18:45 in the
   machine's local timezone on 2026-10-21.
2. Merge the implementation so its script path is stable. Run
   `python3 scripts/restic-personal-projects.py preflight` and inspect the JSON.
3. Grant the exact external changes: create the two repository paths, password
   and offline copy at the paths above, deploy the reviewed script to
   `/home/lauer/.local/libexec/restic-personal-projects.py`, then install the
   systemd units. Run `python3 scripts/restic-personal-projects.py init` once.
4. Run the first `backup --quiesce-known-writers --full-read` manually, confirm
   `TWO_COPY_VERIFIED`, and inspect its full restore and SQLite results. Check
   service states after the run.
5. Enable the timer only after that first run passes. A monthly `--full-read`
   run and a capacity review are required operating tasks. Do not enable
   `forget` or `prune` until actual high-churn growth on the 74 GiB free drive
   has been measured; the tentative policy is 14 daily, 8 weekly, 12 monthly.

The local repository remains usable when the removable drive is absent. A
local-only result is an alert, not a successful two-copy run. The `copy` command
accepts only a full 64-character local snapshot ID; it can retry an offsite
copy after a drive returns. It does not substitute for the first restore drill.

<!-- ref: ../../scripts/restic-personal-projects.py, ../../systemd/restic-personal-projects.service, ../../systemd/restic-personal-projects.timer — implementation and staged schedule -->
<!-- src: ../plans/ARCHITECTURE-complete-data-backup-correction-v2.md — existing ConvMem backup remains independent -->
