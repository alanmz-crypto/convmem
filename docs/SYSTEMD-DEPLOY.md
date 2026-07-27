# Systemd deployment for convmem backup timers

Two independent timer units manage complete-data Restic snapshots and
offsite copies. Example files live in `systemd/`; copy to
`~/.config/systemd/user/` to deploy.

## Local daily snapshot

Creates or verifies a current-day `convmem-data-v1` + `convmem-chroma`
snapshot of `CONVMEM_DATA_ROOT`.

```bash
cp systemd/convmem-restic-local.{service,timer}.example ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now convmem-restic-local.timer
systemctl --user list-timers convmem-restic-local.timer
```

**Schedule:** daily at 00:15 local, with up to 5 min jitter.
`Persistent=true` catches up one missed run after host resume.

## External offsite copy

Copies the current complete-data snapshot to the external USB repository
using explicit snapshot IDs with lineage verification (D.original == S).

```bash
cp systemd/convmem-restic-external.{service,timer}.example ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now convmem-restic-external.timer
```

**Schedule:** every 2 hours starting at 01:00 (01:00, 03:00, 05:00...).
The external service declares `After=convmem-restic-local.service` for
queuing convenience only; it does not pull in the local service or prove
its success. A stale local source exits 25, copies nothing, and is
visible in the failed state and journal.

## Monitoring

```bash
# See timer schedules
systemctl --user list-timers convmem-restic-*

# Check last run status
systemctl --user status convmem-restic-local.service
systemctl --user status convmem-restic-external.service

# Follow journal
journalctl --user -u convmem-restic-local -f
journalctl --user -u convmem-restic-external -f
```

## Pre-requisites

- `restic >= 0.19.0` on PATH
- `~/.config/convmem/restic.env` configured with `CONVMEM_DATA_ROOT`,
  `RESTIC_REPOSITORY`, `RESTIC_EXTERNAL_REPOSITORY`,
  `RESTIC_PASSWORD_FILE`
- `CONVMEM_DATA_ROOT` exists and contains the Chroma directory

Setup with `bash ~/Projects/convmem/scripts/setup-restic-chroma.sh`.

## Timer ordering and safety

The external timer's `After=` is an operational convenience that orders
queued jobs. It does **not** create a dependency or success guarantee:

- If the local timer hasn't run today, the external copy independently
  resolves the current local snapshot. A stale source exits 25.
- If either unit fails, systemd records the failure in the journal and
  `systemctl --user status` shows `failed`.
- `Persistent=true` on both timers ensures missed runs execute after
  resume, but no snapshot can be claimed for a calendar day when the
  host never runs.

Never rely on timer ordering for backup safety. The authoritative
protection claim comes from the resolver's path-bound selection and
explicit snapshot IDs, not from timer sequencing.
