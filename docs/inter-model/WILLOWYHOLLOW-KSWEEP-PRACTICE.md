<!-- Synced for convmem index. Edit source in practice .kiro/steering/ksweep-practice.md, re-run index. -->

**Edit source:** `/home/lauer/WordPress/willowyhollow-practice/.kiro/steering/ksweep-practice.md`

# ksweep — willowyhollow-practice (all-round)

You are running an interactive sweep of the willowyhollow-practice stack.
Execute each check below in order, report results live, and summarize at the end.

---

## 1. Stack health

- Run `source scripts/stack.sh && stack_ps` — confirm both `willowyhollow-practice-db-1` and `willowyhollow-practice-wordpress-1` are running and healthy.
- Run `source scripts/stack.sh && wait_db` — confirm MariaDB accepts connections.
- Confirm http://localhost:8081 responds (curl -sI http://localhost:8081 | head -5).

## 2. WordPress core integrity

- `source scripts/stack.sh && stack_wp core verify-checksums` — report any modified core files.
- `stack_wp option get siteurl` and `stack_wp option get home` — both must be `http://localhost:8081`.

## 3. Backup check (critical)

- List backup files: `ls -lhtr ~/WordPress/willowyhollow/backups/ | tail -10`
- Report the newest staging2, preview, **practice**, production, and **uploads** backups — note age in days.
- Flag if any backup type is older than 7 days or missing entirely.
- **Explicitly check for a `practice-*.sql.gz` file** — this surface's own DB backup. If missing or stale, flag it:
  ```
  ls -lht ~/WordPress/willowyhollow/backups/practice-* 2>/dev/null | head -3
  ```
- Verify the most recent staging2 backup is non-empty: `gunzip -t <file>` (integrity check).
- Verify the most recent practice backup is non-empty: `gunzip -t <newest-practice-*.sql.gz>`
- Verify the most recent uploads backup: `tar -tzf <newest-uploads-*.tar.gz> >/dev/null`
- Check whether systemd timer `willowyhollow-backup.timer` is active: `systemctl --user status willowyhollow-backup.timer 2>/dev/null || echo "timer not found"`.
- **Backup key health** — `backup-all.sh` requires this key (dies immediately without it):
  ```
  ls -la ~/.ssh/willowyhollow-backup || echo "MISSING — timer will fail (P8 fault)"
  ```

## 4. Git status

- `git status --short` in the practice repo — report uncommitted changes.
- `git log --oneline -5` — show recent commits for context.
- Flag tracked files that have diverged from HEAD (dirty working tree).

## 5. Theme / functions.php sync check

- Compare the repo copy with the live container copy:
  ```
  diff <(cat wp-content/themes/astra-child/functions.php) \
       <(docker exec willowyhollow-practice-wordpress-1 cat /var/www/html/wp-content/themes/astra-child/functions.php)
  ```
- If they differ, report the delta and flag as a sync issue.

## 6. Production-readiness pre-flight

These checks validate whether practice is safe to push to staging2/production.

### 6a. URL leak scan
- Dump the DB to stdout and grep for localhost references that would break on staging2:
  ```
  docker exec willowyhollow-practice-db-1 mysqldump -u root -prootpassword \
    --single-transaction --no-tablespaces dbaknngopz5yse 2>/dev/null \
    | grep -oiP 'https?://localhost:\d+' | sort -u
  ```
- Only `http://localhost:8081` is acceptable. Flag any `:8080` or other ports.

### 6b. Plugin / theme state
- `stack_wp plugin list --format=table` — flag any deactivated plugins that should be active, or any "update available" notices.
- `stack_wp theme list --format=table` — confirm `astra-child` is active.

### 6c. WPCode snippet health
- `stack_wp eval 'if (function_exists("wpcode")) { wpcode()->cache->cache_all_loaded_snippets(); echo "OK\n"; } else { echo "WPCode not active\n"; }'`
- Report status.

### 6d. Page structure validation
- `stack_wp post list --post_type=page --fields=ID,post_title,post_status --format=table` — verify key pages exist and are published:
  - Home (1253), About (298), Services (299), Contact (301)
  - Thai Massage (1248), Therapeutic Bodywork (1178), Relaxation Massage (1251)

### 6e. Image attachments
- Confirm the three service hero images are attached:
  ```
  stack_wp post list --post_type=attachment --fields=ID,post_title --format=table | grep -E '1031|1032|1033'
  ```

### 6f. SSH reachability (staging2)
- `ssh -o BatchMode=yes -o ConnectTimeout=5 staging2-willowyhollow "echo ok"` — report if staging2 is reachable for deploy.

## 7. Security quick-check

- `stack_wp user list --fields=ID,user_login,roles --format=table` — flag unexpected admin accounts.
- Check for debug mode: `stack_wp eval 'echo WP_DEBUG ? "DEBUG ON" : "debug off";'`

## 8. Disk usage

- `du -sh ~/WordPress/willowyhollow-practice/public_html/` — report total size.
- `du -sh ~/WordPress/willowyhollow/backups/` — report backup directory size.
- `docker system df --format 'table {{.Type}}\t{{.Size}}\t{{.Reclaimable}}'` — report Docker disk usage.

---

## Summary

After all checks complete, produce a summary table:

| Check | Status | Notes |
|-------|--------|-------|
| Stack health | pass/fail | ... |
| Core integrity | pass/fail | ... |
| Backups | pass/warn/fail | age + integrity |
| Git clean | pass/warn | dirty files |
| functions.php sync | pass/fail | ... |
| URL leaks | pass/fail | leaked URLs |
| Plugins/theme | pass/warn | ... |
| WPCode cache | pass/fail | ... |
| Pages exist | pass/fail | missing pages |
| Images attached | pass/fail | ... |
| SSH staging2 | pass/fail | ... |
| Security | pass/warn | ... |
| Disk | info | sizes |

End with a one-line verdict: **READY TO PUSH** or **NOT READY — fix items above first**.
