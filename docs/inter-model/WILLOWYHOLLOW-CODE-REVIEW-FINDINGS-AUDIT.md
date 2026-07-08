<!-- Synced for convmem index. Edit source in practice repo, re-run this script. -->

**Edit source:** `/home/lauer/WordPress/willowyhollow-practice/logs/2026-07-05-code-review-findings-audit.md`
**Index:** `bash scripts/sync-willowyhollow-audit-index.sh`

# Audit: `logs/2026-07-05-code-review-findings.md`

This is a verification audit of the Crush bug log against the live practice stack
(`willowyhollow-practice`, `:8081`) and the repo files in this workspace.

## Status

- The log has grown to 82 findings.
- Several tail entries are verified against live state.
- Two entries need correction because the observed state does not match the log text.
- A few newer tail entries were not independently rechecked in the last pass.

## Verified

- `53` Amelia settings persist with staging2 URLs. `amelia_settings` is still present.
- `54` Gravatar is enabled. `show_avatars=1` and `avatar_default=mystery`.
- `55` corrected SureForms entry is now accurate: the Contact page contains `[sureforms id='513']`, and `624` is not embedded.
- `56` Comments and pingbacks are open by default. `default_comment_status=open` and `default_ping_status=open`.
- `57` `blog_public` is `0`.
- `58` The tagline still says `A spa and therapy for your wellbeing.`
- `59` `public_html/php.ini` exists in the web root and is exposed, while PHP does not load it from that location.
- `62` The Contact page H1 still says `Get in Touch with Thai Solitude Today`.
- `65` Cal is injected twice via IHAF header/footer, and a published WPCode `Cal` snippet also exists.
- `66` `uag_enable_block_condition` is disabled.
- `67` `uag_load_gfonts_locally` is disabled.
- `68` Four sample blog posts are still published.
- `70` The Contact page still contains a `uagb/google-map` block.
- `71` RSS/feed behavior is still broken from the container side and does not return a normal feed response in the current practice setup.
- `72` `wp-config-local.php` still lacks `WP_DEBUG` definitions.
- `74` The media library still contains many ComfyUI images, and 24 attachments have empty or filename-derived alt text.
- `75` Two published `wp_navigation` posts exist, IDs `4` and `533`.
- `76` `WP_ENVIRONMENT_TYPE` is still `staging`.
- `77` RSSSL leftovers remain in `wp-config.php`.
- `82` `WP_CACHE` is inconsistent between `wp-config.php` and `wp-config-local.php`.

## Needs Correction

- `69` The log says 12 expired transients are accumulating, but the live count found in the practice DB was `2`, not `12`.
- `73` The log says all three nav locations point to the same menu, but `nav_menu_locations` is `false` in the live option state.

## Not Rechecked In The Last Pass

- `78` Sitemap, RSS feed, login, and 404 redirect/status behavior.
- `79` CSP WPCode snippet installation state.
- `80` Missing `X-Frame-Options` header.
- `81` Missing `Referrer-Policy` header.

## Notes

- The log file itself uses duplicated finding numbers in the tail, so line labels should be treated as a sequence of entries rather than a perfectly unique ID space.
- The SureForms correction was the main content fix needed; the rest of the log is mostly a mix of accurate findings and a few overstatements in the newest tail.
