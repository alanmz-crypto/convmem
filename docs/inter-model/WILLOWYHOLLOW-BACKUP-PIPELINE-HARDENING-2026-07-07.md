<!-- Synced for convmem index. Edit source in practice repo, re-run index. -->

**Edit source:** `/home/lauer/WordPress/willowyhollow-practice/logs/2026-07-07-backup-pipeline-hardening.md`

# Willowy Hollow backup pipeline hardening — 2026-07-07

Session: Cursor · willowyhollow cycle surface · Author: cursor-session

## Summary

Fixed and hardened the willowyhollow automated backup cycle after ksweep/convmem flagged stale uploads, intermittent SSH failures at 03:00, and silent partial-success exits. Full fault-matrix regression harness added (P0–P9).

## Root causes (confirmed)

| Issue | Cause |
|-------|--------|
| Staging2/production skipped nightly Jul 2–5 | Passphrase SSH key required ssh-agent; socket absent at 03:00 |
| Uploads stale since Jun 25 | `backup-all.sh` DB-only; `wh-backup` manual |
| Timer reported SUCCESS on partial fail | `backup-all.sh` always exited 0 |
| Practice missing from timer | Never added to `backup-all.sh` |
| `set -e` + `pipefail` aborts | Standalone pipes (mysqldump, ssh, tar, `REMOTE_HOME=$()`) killed script before soft-fail |

## Fixes shipped

### Infrastructure

- **`~/.ssh/willowyhollow-backup`** — dedicated ed25519 key (no passphrase), pubkey in SiteGround `authorized_keys`
- **`~/.config/systemd/user/willowyhollow-backup.service`** — `SSH_AUTH_SOCK=` cleared; runs `backup-all.sh` directly
- Timer unchanged: daily 03:00, `Persistent=true`, 300s jitter

### `willowyhollow-practice/scripts/backup-all.sh`

- Surfaces: **staging2, preview (:8080), practice (:8081), production, uploads**
- **`ssh_backup()`** — uses backup key, no agent
- **`safe_sql_gzip_dump()`** — `PIPESTATUS`-safe SQL dumps
- **`verify_sql_gz()`** — `gunzip -t` + ≥10KB decompressed SQL
- **Uploads** — preview `public_html/wp-content/uploads` tar.gz; `tar_ec` soft-fail
- **Practice** — optional skip when `:8081` down; `WH_BACKUP_REQUIRE_PRACTICE=true` to block
- **Retention** — `staging2 preview practice production uploads local-db` (keep 10)
- **SSH `REMOTE_HOME`** — `set +e` / `rh_ec` so resolve failure doesn't abort script

### `willowyhollow/scripts/backup.sh` (`wh-backup`)

- Uploads source aligned to preview `public_html` (was GitClones)
- Pipe-safe mysqldump + decompressed SQL verify
- `tar_ec` guard on uploads archive

### Ksweep steering

- `ksweep-practice.md`, `ksweep-preview.md`, `ksweep-deploy.md`, `ksweep-all.md` — uploads freshness + integrity checks

### Regression harness

- **`scripts/backup-fault-matrix.sh`** — P0–P9 permutation tests (~5 min)
- Log: `~/.cursor/debug-d2f9a2.log` (NDJSON, optional)

## Fault matrix results (final run 2026-07-06 22:44 CDT)

| Case | Fault | Exit | Expected |
|------|-------|------|----------|
| P0 | Healthy | 0 | all 5 backed |
| P1 | Practice down | 0 | 4 backed, practice skipped |
| P2 | Preview DB down | 1 | 4 backed, preview failed |
| P3 | Staging2 SSH bad | 1 | 4 backed, staging2 failed |
| P4 | Production SSH bad | 1 | 4 backed, production failed |
| P5 | Both SSH bad | 1 | 3 local backed |
| P6 | Uploads path missing | 1 | 4 DBs backed |
| P7 | REQUIRE_PRACTICE + down | 1 | 4 backed, practice failed |
| P8 | Missing backup key | 1 | die immediately |
| P9 | Read-only BACKUP_DIR | 1 | all soft-fail, full summary |

`orphan_tiny_gz=0` on every case.

## Verification commands

```bash
# Full permutation audit
~/WordPress/willowyhollow-practice/scripts/backup-fault-matrix.sh

# Spoof unattended timer
SSH_AUTH_SOCK= systemctl --user start willowyhollow-backup.service
journalctl --user -u willowyhollow-backup.service -n 20 --no-pager

# Manual local backup
~/WordPress/willowyhollow/scripts/backup.sh
```

## Open / not in scope

- Off-site copies (DB + uploads on same NVMe) — production has SiteGround backups
- Legacy one-off files in `backups/` (`willowyhollow-live-*`, etc.) — manual cleanup
- `restore-from-backup.sh` still outdated (Docker migration) — separate task

## Related ledger

- `dec_prop_20260701_084820_a87f` — daily automated backup timer (supersedes SSH-agent discovery)
- `WILLOWYHOLLOW-BACKUP-INVESTIGATION-2026-07-07.md` — initial ksweep investigation

## Files touched

| Path | Change |
|------|--------|
| `willowyhollow-practice/scripts/backup-all.sh` | Hardened multi-surface backup |
| `willowyhollow-practice/scripts/backup-fault-matrix.sh` | New regression harness |
| `willowyhollow/scripts/backup.sh` | Aligned with timer |
| `~/.ssh/willowyhollow-backup` | New automation key |
| `~/.ssh/config` | Backup host aliases |
| `~/.config/systemd/user/willowyhollow-backup.service` | No agent, 600s timeout |
| `willowyhollow-practice/logs/2026-07-07-backup-investigation.md` | Updated findings |
| `willowyhollow-practice/.kiro/steering/ksweep-*.md` | Backup check updates |
