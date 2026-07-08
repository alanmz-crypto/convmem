# ksweep-deploy: Backup Investigation

Date: 2026-07-07
Author: Crush (ksweep-deploy sweep)

## Summary

Investigated the willowyhollow backup architecture after the ksweep-deploy flagged
"No restic snapshots found." The restic alert was a false positive — restic covers
the convmem corpus only, not willowyhollow. Willowyhollow uses its own backup
pipeline based on sql dumps + tar.gz uploads, driven by a systemd timer.

## Backup Architecture

| Layer | Mechanism | Schedule | Location |
|-------|-----------|----------|----------|
| DB (preview, staging2, production) + uploads | `backup-all.sh` | Daily 3:00 AM via systemd timer | `~/WordPress/willowyhollow/backups/` |
| DB + uploads (preview local, manual) | `backup.sh` / `wh-backup` | Manual only (redundant with timer) | `~/WordPress/willowyhollow/backups/` |
| Code | `git push` | On demand | GitHub |
| Convmem corpus | `restic` | Pre-write gate | `~/.local/share/convmem-restic` |

### Systemd Timer

- Unit: `willowyhollow-backup.timer` / `willowyhollow-backup.service`
- Runs: `~/WordPress/willowyhollow-practice/scripts/backup-all.sh`
- Dumps: staging2 (SSH wp db export), preview (:8080 mysqldump), production (SSH wp db export), preview uploads (tar.gz)
- SSH: dedicated `~/.ssh/willowyhollow-backup` key (no passphrase; no ssh-agent at 03:00)
- Retention: keeps last 10 of each type

## Last Run (Jul 6 03:05 UTC) — Full Success

```
Backed up: staging2 preview production
```

- staging2: 3.6M
- preview: 3.5M
- production: 7.3M

All landed in `~/WordPress/willowyhollow/backups/`.

## Findings

### 1. Uploads not on timer — ✅ fixed 2026-07-06

`backup-all.sh` now includes preview uploads (`tar.gz`) on every timer run.
Manual `backup.sh` / `wh-backup` remains available but is redundant with the timer.

### 2. No off-site/restic for willowyhollow

Willowyhollow DB dumps and uploads sit on the same physical NVMe drive
(`/dev/nvme1n1p2`). Production is covered by SiteGround's own backups, but
staging2 and preview have no off-machine fallback.

The convmem restic repo (`~/.local/share/convmem-restic`) is entirely separate
and covers the convmem knowledge corpus only.

### 3. Staging2 SSH intermittent — ✅ fixed 2026-07-06

Jul 5 backup log: "staging2 SSH unreachable (key not loaded?)"
Jul 6 backup log: staging2 succeeded (3.6M dump)

**Root cause:** passphrase-protected `~/.ssh/willowyhollow` required ssh-agent at 03:00;
agent socket often absent overnight (Jul 2–5 failures).

**Fix:** dedicated `~/.ssh/willowyhollow-backup` key (no passphrase) in SiteGround
`authorized_keys`; `backup-all.sh` uses it directly — no agent discovery in systemd unit.

### 4. Convmem restic external repo unverified

`RESTIC_EXTERNAL_REPOSITORY` points at `/run/media/lauer/rxBUlauer-128Gfs/convmem-backups`
(removable USB drive). Not verified in this sweep — drive may not be mounted.

## Backup Inventory (local)

Recent dumps in `~/WordPress/willowyhollow/backups/`:
- **Preview DB:** daily Jun 30–Jul 6 (~3.5M each)
- **Staging2 DB:** Jul 6, Jul 5, Jul 1, Jun 30 — then gap to Jun 26
- **Production DB:** Jul 6, Jul 5, Jul 1, Jun 30 — ~7.3M each
- **Uploads:** last snapshot Jun 25 07:58 (40M tar.gz)
