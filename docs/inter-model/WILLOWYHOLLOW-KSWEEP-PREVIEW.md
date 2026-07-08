<!-- Synced for convmem index. Edit source in practice .kiro/steering/ksweep-preview.md, re-run index. -->

**Edit source:** `/home/lauer/WordPress/willowyhollow-practice/.kiro/steering/ksweep-preview.md`

# ksweep — willowyhollow preview (:8080)

You are running an interactive sweep of the willowyhollow **preview** stack.
This is the validation surface — content here must match what practice or GitClones pushed,
and be ready for visual/functional sign-off before deploying to production.

Execute each check in order, report results live, and summarize at the end.

---

## 1. Stack health (Podman)

- `source ~/WordPress/willowyhollow/scripts/stack.sh && stack_ps` — confirm both `willowyhollow-db-1` and `willowyhollow-wordpress-1` are running.
- `source ~/WordPress/willowyhollow/scripts/stack.sh && wait_db` — confirm MariaDB accepts connections.
- `curl -sI http://localhost:8080 | head -5` — confirm HTTP 200.
- Check systemd unit: `systemctl --user status willowyhollow.service 2>/dev/null | head -5` (auto-start after reboot).

## 2. WordPress core integrity

- `source ~/WordPress/willowyhollow/scripts/stack.sh && stack_wp core verify-checksums` — report any modified/extra core files.
- `stack_wp option get siteurl` and `stack_wp option get home` — both must be `http://localhost:8080`.
- Confirm DB_HOST is `db`: `grep -E "DB_HOST" ~/WordPress/willowyhollow/public_html/wp-config-local.php`

## 3. GitClones - Preview file sync check

The preview `public_html/` should be an rsync mirror of `~/GitClones/willowyhollow-dev/`.
Check for drift:

```bash
# Theme functions.php (most critical file)
diff ~/GitClones/willowyhollow-dev/wp-content/themes/astra-child/functions.php \
     ~/WordPress/willowyhollow/public_html/wp-content/themes/astra-child/functions.php
```

- If they differ, report the delta and flag as a sync issue.
- Check when preview.sh was last run: `stat -c '%y' ~/WordPress/willowyhollow/public_html/wp-content/themes/astra-child/functions.php` vs `stat -c '%y' ~/GitClones/willowyhollow-dev/wp-content/themes/astra-child/functions.php`
- Check for stale files that should have been deleted by rsync:
  ```bash
  diff <(cd ~/GitClones/willowyhollow-dev && find wp-content/themes/astra-child -type f | sort) \
       <(cd ~/WordPress/willowyhollow/public_html && find wp-content/themes/astra-child -type f | sort)
  ```

## 4. Practice - Preview consistency

If practice (:8081) is also running, compare their theme engines:

```bash
# Only if practice is running
if docker ps --format '{{.Names}}' | grep -q willowyhollow-practice-wordpress-1; then
  diff <(docker exec willowyhollow-practice-wordpress-1 cat /var/www/html/wp-content/themes/astra-child/functions.php) \
       <(podman exec willowyhollow-wordpress-1 cat /var/www/html/wp-content/themes/astra-child/functions.php)
  echo "EXIT: $?"
else
  echo "Practice stack not running — skipping cross-check"
fi
```

- Report whether both stacks have identical theme code.

## 5. Backup check

- List backups: `ls -lhtr ~/WordPress/willowyhollow/backups/ | tail -10`
- Report newest staging2, preview, **practice**, production, and **uploads** backups — note age in days.
- Flag if any backup type is older than 7 days or missing entirely.
- Verify most recent preview backup integrity: `gunzip -t <newest-preview-*.sql.gz>`
- Verify most recent uploads backup integrity: `tar -tzf <newest-uploads-*.tar.gz> >/dev/null`
- Timer status: `systemctl --user status willowyhollow-backup.timer 2>/dev/null | head -5`
- Local backup script: check `~/WordPress/willowyhollow/scripts/backup.sh` exists and is executable.
- **Backup key health** — the timer's `backup-all.sh` requires this key (dies immediately without it):
  ```
  ls -la ~/.ssh/willowyhollow-backup || echo "MISSING — timer will fail (P8 fault)"
  ```

## 6. URL leak scan (DB)

```bash
podman exec willowyhollow-db-1 mysqldump -u root -prootpassword \
  --single-transaction --no-tablespaces dbaknngopz5yse 2>/dev/null \
  | grep -oiP 'https?://[a-z0-9._-]+(?::\d+)?' | sort -u
```

- Only `http://localhost:8080` is acceptable for the preview surface.
- Flag any `localhost:8081` (practice leaking in), `staging2.willowyhollow.com`, `willowyhollow.com`, or `https://localhost` references.

## 7. SG Optimizer / HTTPS redirect check

The `.htaccess` SiteGround HTTPS redirect must be commented out on preview (breaks local HTTP).

```bash
grep -A5 "HTTPS forced by SG-Optimizer" ~/WordPress/willowyhollow/public_html/.htaccess 2>/dev/null | head -10
```

- If any `RewriteRule` or `RewriteEngine On` lines are NOT commented, flag as broken.
- Also verify mu-plugin is present:
  ```bash
  ls -la ~/WordPress/willowyhollow/public_html/wp-content/mu-plugins/wh-local-dev.php 2>/dev/null
  ```
- Verify SG HTTPS rewrite is disabled in output:
  ```bash
  curl -s http://localhost:8080/ | grep -c 'https://localhost:8080'
  ```
  Expect 0.

## 8. Plugin / theme state

- `stack_wp plugin list --format=table` — flag deactivated plugins, update-available notices.
- `stack_wp theme list --format=table` — confirm `astra-child` is active.
- SG Optimizer combine check: `stack_wp option get siteground_optimizer_combine_css` — on preview this should be disabled (mu-plugin handles it), report state.

## 9. WPCode snippet health

```bash
stack_wp eval 'if (function_exists("wpcode")) { wpcode()->cache->cache_all_loaded_snippets(); echo "OK\n"; } else { echo "WPCode not active\n"; }'
```

## 10. Page structure validation

```bash
stack_wp post list --post_type=page --fields=ID,post_title,post_status --format=table
```

- Verify key pages exist and are published. IDs may differ from practice — just confirm the **titles** are present:
  - Home, About, Services, Contact
  - Thai Massage, Therapeutic Bodywork, Relaxation Massage

## 11. Visual / functional smoke tests

These are the checks from the Deploy Workflow validation step:

- `curl -s http://localhost:8080/ | grep -c 'view-transition-name'` — VT CSS is being injected.
- `curl -s http://localhost:8080/ | grep -c '::view-transition'` — dark baseline present.
- `curl -s http://localhost:8080/ | grep -c 'vt-image-'` — shared-element classes on cards.
- `curl -s http://localhost:8080/ | grep -c 'pageswap'` — JS nav types event handler present.
- Check for broken image references (404s):
  ```bash
  curl -s http://localhost:8080/ | grep -oP 'src="[^"]*"' | head -20
  ```
- `curl -s http://localhost:8080/services/ | grep -c 'vt-image-'` — VT classes on services page too.
- Check dark theme color is set:
  ```bash
  curl -s http://localhost:8080/ | grep -o 'background[^;]*#0F172A'
  ```

## 12. SG combined assets check (local dev overrides)

```bash
curl -s http://localhost:8080/ | grep -c 'siteground-optimizer-combined'
```

- Expect 0 on preview (mu-plugin disables it). If >0, SG is combining assets and may cause layout issues.

## 13. Google Fonts / typography

```bash
curl -s http://localhost:8080/ | grep -c 'fonts.googleapis.com'
```

- Expect >0 (Belleza + Work Sans should be loading).

## 14. Security quick-check

- `stack_wp user list --fields=ID,user_login,roles --format=table` — flag unexpected admin accounts.
- `stack_wp eval 'echo defined("WP_DEBUG") && WP_DEBUG ? "DEBUG ON" : "debug off";'`
- wp-login accessible: `curl -sI http://localhost:8080/wp-login.php | head -3` — should return 200, not 404 (SG Security login hiding must be disabled locally).

## 15. SSH reachability (production + staging2)

```bash
ssh -o BatchMode=yes -o ConnectTimeout=5 staging2-willowyhollow "echo staging2-ok" 2>&1
```

- Report if staging2 is reachable for push/deploy workflows.

## 16. Disk usage

- `du -sh ~/WordPress/willowyhollow/public_html/` — total preview size.
- `du -sh ~/WordPress/willowyhollow/backups/` — backup directory size.
- `podman system df 2>/dev/null | tail -5` — Podman disk usage.

## 17. Podman health / resource

- `podman stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}' 2>/dev/null` — container resource usage snapshot.
- Check for orphan/stopped containers: `podman ps -a --filter "name=willowyhollow-" --format 'table {{.Names}}\t{{.Status}}'`

---

## Summary

After all checks complete, produce a summary table:

| Check | Status | Notes |
|-------|--------|-------|
| Stack health | pass/fail | ... |
| Core integrity | pass/fail | ... |
| GitClones sync | pass/warn/fail | drift detected? |
| Practice consistency | pass/skip/warn | ... |
| Backups | pass/warn/fail | age + integrity |
| URL leaks | pass/fail | leaked URLs |
| .htaccess HTTPS | pass/fail | redirect disabled? |
| Plugins/theme | pass/warn | ... |
| WPCode cache | pass/fail | ... |
| Pages exist | pass/fail | missing pages |
| VT smoke tests | pass/warn/fail | injection present? |
| SG combined off | pass/fail | ... |
| Google Fonts | pass/warn | loading? |
| Security | pass/warn | ... |
| SSH staging2 | pass/fail | ... |
| Disk | info | sizes |
| Podman health | pass/warn | ... |

End with a one-line verdict:
- **PREVIEW VALIDATED — ready to deploy** (all critical checks pass)
- **PREVIEW NEEDS ATTENTION — fix items above before deploying**
