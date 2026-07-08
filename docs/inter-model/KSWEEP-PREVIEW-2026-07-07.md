# ksweep-preview — 2026-07-07

Session: Crush willowyhollow · Date: 2026-07-07 01:23 UTC

## Summary

Ran a full preview stack sweep against the willowyhhold local preview environment (localhost:8080). All critical checks PASS.

## Results

| Check | Status | Detail |
|-------|--------|--------|
| Containers | PASS | willowyhollow-db-1 + willowyhollow-wordpress-1 Up 3h |
| HTTP | PASS | 200 OK — "Home - Willowy Hollow" — Apache/2.4.67, PHP 8.3.31 |
| WP Core | PASS | 7.0, checksums verified |
| DB | PASS | MariaDB 82MB, connectivity OK |
| Disk | PASS | uploads 82M, plugins 104M, themes 25M, cache 3M |
| .htaccess | PASS | SG-Optimizer HTTPS redirect commented out for :8080 |
| Plugins | WARN | 6 updates available: sg-security 1.6.4, google-site-kit 1.182, uagb 2.19.29, surerank 1.9.1, insert-headers-and-footers 2.3.7, astra 4.13.5 |
| Git | WARN | staging branch, 4 ahead of main, clean vs origin. Dirty tree (AGENTS.md mod + untracked artifacts) |
| wp-config | INFO | SiteGround creds as `defined() || define()` fallback; working via Podman env override |
| Container RAM | PASS | DB 209MB, WP 166MB — well within limits |

## Verdict

**HEALTHY** — preview stack stable. 6 plugin updates flagged for next maintenance window. Working tree dirty with staging artifacts (aider, .cursor, .kiro, vendor dirs).
