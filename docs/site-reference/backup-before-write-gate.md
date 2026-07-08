# Site-reference slice — Backup-before-write gate

## Topic: Does a fresh, verified backup exist before this change touches production?

**Use for:** the single hardest gate before any write to a production WP site — database, files, or both.

**Source:** Standard operational practice — the backup-before-write rule is universal to any system, not specific to WordPress, but the DB+files split is a WP-specific consequence of its architecture.

### Decision procedure

- No production write proceeds without a backup taken *after* the last change that's about to be overwritten — an old backup is not a backup for this purpose, it's a rollback to a stale state.
- Backup must cover both database and files if the change touches either — a files-only or DB-only backup is incomplete for most plugin/theme changes.
- Verify the backup is restorable, not just that it completed. A backup file existing is not the same as a backup that restores cleanly.
- If no fresh, verified backup exists: this is a blocking condition, not a warning. The change does not proceed until one exists — no exception for "it's a small change."

### Willowy Hollow hooks

| Target | Gate |
|--------|------|
| Production (`willowyhollow.com`) | Fresh DB + files backup; `gunzip -t` on SQL dump |
| staging2 | Fresh staging backup before destructive sync |
| Practice | Lower risk — still backup before `sync-staging2-to-practice.sh` (destructive pull) |

```bash
ls -lhtr ~/WordPress/willowyhollow/backups/ | head -10
gunzip -t ~/WordPress/willowyhollow/backups/<latest>.sql.gz
```

See `ksweep-willowyhollow` steering §3 for routine backup health checks. This slice is the **blocking** rule before prod writes.
