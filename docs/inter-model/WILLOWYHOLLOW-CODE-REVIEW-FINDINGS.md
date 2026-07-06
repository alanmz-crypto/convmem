<!-- Synced for convmem index. Edit source in practice repo, re-run this script. -->

**Edit source:** `/home/lauer/WordPress/willowyhollow-practice/logs/2026-07-05-code-review-findings.md`
**Index:** `bash scripts/sync-willowyhollow-findings-index.sh`

# 2026-07-05 — Code review: functions.php / wpcode-view-transitions.css / wpcode-view-transitions.js

Reviewed by Crush. Source: `wp-content/themes/astra-child/functions.php`, `wpcode-view-transitions.css`, `wpcode-view-transitions.js`. Based on commit `f19a7f7`.

---

## Findings

### 1. `wpcode-view-transitions.css` contains PHP code (extension mismatch)

**Symptom:** The file is named `.css` but its first 28 lines contain `add_filter`, `add_action`, and a `function` definition — raw PHP. If referenced as a standalone stylesheet or opened in a CSS editor, the PHP code appears as invalid CSS and the snippet breaks.

**Root cause:** The file was written to be evaluated by WPCode as a PHP snippet, but the `.css` extension signals the wrong content type. Future maintainers may serve it as CSS, pipe it through a CSS minifier, or fail to recognize it needs PHP evaluation.

**Fix:** Rename to `.php` (e.g. `wpcode-view-transitions-snippet.php`) or split into a standalone `.css` for the CSS rules and a separate `.php` for the `wp_head` injection wrappers. If WPCode requires the `.css` extension for CSS-type snippets, strip the PHP wrapper lines and keep only the CSS — the PHP filter/action calls are already covered by `functions.php`.

### 2. `back` navigation animation direction is inverted

**Symptom:** When navigating via history-back, the incoming page drops downward from above (`translateY(-14px)` → `translateY(0)`), which reads visually as "new page arriving from above" — opposite of the expected "returning" direction.

**Root cause:** The `::view-transition-new(root)` keyframe `vt-root-sink-in` starts at `translateY(-14px)` (above viewport) and ends at `translateY(0)`. The name says "sink" but the motion is a drop.

**Fix:** Change the `from` value to `translateY(14px)` so the page rises from below — consistent with returning to content lower in the stack:

```diff
 @keyframes vt-root-sink-in {
-  from { opacity: 0; transform: translateY(-14px); }
+  from { opacity: 0; transform: translateY(14px); }
   to   { opacity: 1; transform: translateY(0); }
 }
```

Applied in both `functions.php` (the `<style>` block) and `wpcode-view-transitions.css` (the `<?css` or PHP snippet).

### 3. Line-art inversion targets all images, not just line-art

**Symptom:** Any `<img>` added to the About (`page-id-298`), Services (`page-id-299`), or Contact (`page-id-301`) pages inside `.entry-content` will be inverted and screened — rendering photographs, icons, or logos unreadable.

**Root cause:** The selector `body.page-id-XXX .entry-content img` catches every image descendant, not just the `continuousLineMassage` line-art SVGs.

**Fix:** Scope the inversion to the specific line-art images — either by adding a common class (e.g. `.line-art-image`) or by targeting the specific UAGB figure blocks that contain line-art:

```diff
-body.page-id-298 .entry-content img,
-body.page-id-299 .entry-content img,
-body.page-id-301 .entry-content img {
+body.page-id-298 .entry-content .wp-block-uagb-image.line-art img,
+body.page-id-299 .entry-content .wp-block-uagb-image.line-art img,
+body.page-id-301 .entry-content .wp-block-uagb-image.line-art img {
   filter: invert(1);
   mix-blend-mode: screen;
 }
```

This requires adding a `line-art` class to each line-art block in the WordPress editor.

### 4. Services page `!important` image overrides are too broad

**Symptom:** All UAGB images on the Services page are forced to `width: 100% !important; height: 100% !important; object-fit: contain`. This prevents responsive image techniques (srcset, `sizes`, `picture` element) from controlling dimensions, and relies on hardcoded block-specific `aspect-ratio` values (lines 173–177) that must be manually kept in sync with image changes.

**Root cause:** The `!important` overrides on `img` were added to fix white space showing through the invert filter when UAGB's hardcoded width/height attributes don't match the actual image proportions. The fix was applied too broadly.

**Fix:** Remove the `!important` declarations on width/height and rely on the aspect-ratio overrides and `object-fit: contain` on the specific blocks that need it, or apply the override only to the figures with known aspect-ratio mismatches.

### 5. Page IDs are hardcoded for one environment

**Symptom:** All page-specific selectors (`body.page-id-298`, `body.page-id-299`, `body.page-id-301`, `body.page-id-1253`, plus all service-specific block IDs) are tied to environment-specific IDs that differ between practice (:8081), staging2, and production.

**Root cause:** Page IDs are auto-assigned by WordPress per database. The practice DB was restored from a staging2 backup at a different point in time, so the IDs diverged.

**Fix:** Replace page-ID selectors with page-slug-based selectors:

```diff
-body.page-id-298 .entry-content img
+body.page-slug-about .entry-content img
```

Or apply `.vt-` classes directly to the page body via the WordPress body_class filter. Block IDs (`.uagb-block-*`) remain a separate concern (see finding 6).

### 6. Dual selector paths create silent `view-transition-name` collision risk

**Symptom:** If a UAGB block is re-saved and its block ID changes, or if a `.vt-*` class is on the wrong ancestor element, two different elements can receive the same `view-transition-name`. The spec disables the transition for that name **silently** — no console warning, no visual error, just a broken morph.

**Root cause:** The VT system uses fallback block-ID selectors alongside `.vt-*` classes for backward compatibility. If the two paths diverge, they may target different DOM elements.

**Fix:** Remove the block-ID fallback selectors once the `.vt-*` classes are verified on all source and destination elements. The `.vt-*` convention was explicitly created to get off brittle block IDs (per AGENTS.md gotcha #7). This migration should be completed.

### 7. Blob `z-index` stacking lacks isolation

**Symptom:** Any positioned child element inside a blob container that has `z-index` set may render behind the blob pseudo-element.

**Root cause:** Blobs use `z-index: 0`, content wrappers use `z-index: 1`, but there is no stacking context isolation. A child with `z-index: auto` in normal flow is fine, but an explicitly positioned child with `z-index` could slip below.

**Fix:** Add `isolation: isolate` to the blob container (`.uagb-block-e9f89e50`, etc.) to create a fresh stacking context, ensuring the blob and its content are contained:

```diff
 .uagb-block-e9f89e50 {
   position: relative;
   overflow: hidden;
+  isolation: isolate;
 }
```

## Verification

Each fix should be verified on localhost:8081 by navigating the affected pages and checking:
1. Image inversion is narrow in scope (findings 3, 4) — add a non-line-art image temporarily to confirm it's untouched.
2. VT morphs work for all three services (finding 6) — navigate home → service page and back.
3. Back navigation rises from below (finding 2) — use browser back button.
4. CSS file loads without PHP parsing errors if served standalone (finding 1).
5. Page-specific selectors match on staging2 after deploy (finding 5).

## Related

- Commit `f19a7f7` — Haikei white blobs, Read More micro-interactions, VT refinements
- AGENTS.md gotcha #6 (page IDs differ per environment)
- AGENTS.md gotcha #7 (UAGB block IDs change on re-save)

---

## Additional Findings (second pass — install scripts and CSP)

### 8. `install-vt-card.php` would overwrite functions.php with stale block IDs

**Symptom:** Re-running `install-vt-card.php` would replace `functions.php` with an old version using different UAGB block IDs for Therapeutic Bodywork (`uagb-block-724` / `uagb-block-2b5b97c7`) instead of the currently deployed IDs (`uagb-block-d384ebff` / `uagb-block-9b4422a3`). The VT morph for Therapeutic Bodywork would silently break.

**Root cause:** The install script embeds a static snapshot of functions.php (lines 19–160) that has not been updated to reflect the current block IDs. Since the functions.php written by `install-vt-card.php` is the **earliest** version of the VT code, and later install scripts (`install-vt-nav.php`, `install-therapy-bodywork-page.php`) changed the block IDs, the install script is now out of sync.

**Fix:** Remove the embedded `functions.php` snapshot from `install-vt-card.php` and make it a `require_once` of the current file, or add a guard that skips the write if `functions.php` already contains the current block IDs.

### 9. `install-service-cards-html.php` has two broken links

**Symptom:** The services grid HTML ships three links, two of which point to non-existent pages:

```
<a href="/thai-massage">       → OK (exists, missing trailing slash)
<a href="/deep-tissue">        → BROKEN — no such page exists
<a href="/relaxation">         → BROKEN — should be /relaxation-massage/
```

**Root cause:** The HTML was written before the current VT-based service pages existed. "Deep Tissue" was renamed to "Therapeutic Bodywork" and the relaxation slug changed from `/relaxation` to `/relaxation-massage/`.

**Fix:** 
- Rename "Deep Tissue" to "Therapeutic Bodywork" with link `/therapeutic-bodywork/`
- Fix relaxation link to `/relaxation-massage/`

### 10. `install-service-cards-html.php` lacks `ABSPATH` guard

**Symptom:** Unlike `install-vt-nav.php` and `install-therapy-bodywork-page.php` which guard with `if ( ! defined( 'ABSPATH' ) ) { exit(...); }`, this script has no guard and could accidentally be loaded from a web request.

**Root cause:** Omission during creation.

**Fix:** Add `if ( ! defined( 'ABSPATH' ) ) { exit( "Run via wp eval-file\\n" ); }` at the top of the file, matching the convention of the other install scripts.

### 11. Thai Massage flip card has an empty back face

**Symptom:** The flip card on the Thai Massage card wraps in a 3D flip, but the back face is an empty `<div class="flip-card-back">`. Clicking the card triggers a 0.6s 3D flip animation that reveals nothing — a blank navy box where Thai content was.

**Root cause:** `install-flip-card.php` line 116: `'    <div class="flip-card-back">' . "\n" . '    </div>' . "\n"` — the back face has no content.

**Fix:** Either remove the flip-card wrapper entirely (if the 3D flip was a temporary experiment), or add content to the back face (e.g., a "Book Now" CTA, service summary, or testimonial).

### 12. Conflicting link re-pointing between install scripts

**Symptom:** `install-vt-card.php` rewires the Therapeutic Bodywork "Read More" link from its dedicated page back to `/services/` (line 202). `install-vt-nav.php` rewires it to `/therapeutic-bodywork/` (line 136). Depending on which script runs last, the link destination changes — and a concurrent morph may target the wrong page.

**Root cause:** `install-vt-card.php` was written before dedicated service pages existed, so it reverted the link to the generic `/services/` page. `install-vt-nav.php` later created dedicated pages and pointed links there. The scripts are not aware of each other.

**Fix:** Update `install-vt-card.php` to point to `/therapeutic-bodywork/` instead of `/services/`, matching the destination set by `install-vt-nav.php`. Or remove the re-pointing logic from `install-vt-card.php` entirely (it's an obsolete step).

### 13. Service pages have conflicting double-animation on Chromium

**Symptom:** On Chromium browsers where View Transitions are supported, navigating to a service page triggers TWO animations: the VT root crossfade (functions.php, 0.4s) AND the CSS `body { animation: page-reveal ... }` fallback (embedded in the page content, 0.35s). Both animate opacity on the new page, potentially causing a flicker or extended fade.

**Root cause:** The page-reveal fallback animations in `install-vt-nav.php` (lines 69–77), `install-therapy-bodywork-page.php` (lines 35–41), and `install-thai-vt-card.php` (lines 136–147) are intended as graceful degradation for non-Chromium browsers (iOS/Safari), but they have no `@supports` or `prefers-reduced-motion` guard. They apply unconditionally to all browsers.

**Fix:** Wrap the fallback animation in a `@supports not (view-transition-name: none)` query, or use a feature detect to only apply it when View Transitions are unsupported:

```css
@supports not (view-transition-name: none) {
  body { animation: page-reveal 0.35s ease both; }
}
```

Or detect via the Navigation API and only set the animation when VT is absent (JS-only approach).

### 14. (CRITICAL) Every install script hardcodes home page ID 296 — modifies zombie page instead of live home

**Symptom:** All five install scripts (`install-vt-card.php`, `install-thai-vt-card.php`, `install-relax-vt-card.php`, `install-flip-card.php`, `install-vt-nav.php`) hardcode `$home_id = 296` or `const HOME_ID = 296`. The published front page is ID 1253. Page 296 is `Home-obs` — a private obsolete page. Re-running any of these scripts modifies the zombie page, not the live home. VT inline CSS and link re-pointing silently go to the wrong page. Re-running `install-flip-card.php` wraps the wrong page's Thai block in a flip card.

**Root cause:** The page IDs shifted when the DB was restored from a newer backup. The scripts were written when 296 was the correct home page ID and never updated.

**Evidence:**
```
$ wp option get page_on_front → 1253
$ wp post get 296 --field=post_title → "Home-obs"
$ wp post get 1253 --field=post_title → "Home"
```

**Fix:** Replace all hardcoded `296` references with a dynamic lookup:
```php
$home_id = (int) get_option( 'page_on_front' );
if ( ! $home_id ) { fwrite( STDERR, "No front page set.\n" ); exit( 1 ); }
```

Only `scripts/fix-home-buttons.php` already does this correctly (line 10).

### 15. Missing semicolon in flip-card CSS breaks `z-index` on back face

**Symptom:** The flip-card inline style injected into the real Home page (1253) renders the back face behind the front due to a missing semicolon. Clicking the Thai card triggers the 0.6s 3D flip animation but nothing appears to change — the empty back face is hidden behind the front.

**Root cause:** `install-flip-card.php` generates this CSS inside the page content (confirmed live in the real Home page raw content):
```css
.flip-card-back {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  transform: rotateY(180deg);
  z-index: 1
  border-radius: 24px;
  background: #0F172A;
  box-shadow: 0 8px 30px rgba(0,0,0,.08);
}
```
Missing `;` after `z-index: 1`. The browser parses `z-index: 1 border-radius: 24px` — an invalid value — and discards the declaration entirely. Without `z-index`, the back face stacks behind the front face regardless of `backface-visibility: hidden` on the front. The flip animates but the back is never visible.

**Fix:** Add the missing semicolon:
```diff
   z-index: 1
+  ;
   border-radius: 24px;
```
Applied in both `install-flip-card.php` (the source) and as a one-off content fix on page ID 1253 via WP-CLI.

### 16. Duplicate Privacy Policy pages with conflicting slugs

**Symptom:** Two Privacy Policy pages exist: ID 561 (published, slug `privacy-policy-2`) and ID 3 (private, slug `privacy-policy`). The published one has the ugly auto-renamed slug, and a visitor hitting `/privacy-policy/` gets a 404 (that page is private).

**Root cause:** A new Privacy Policy was created when the old one's slug was already taken, rather than updating the original.

**Fix:** Decide which version is correct (ID 561 or ID 3), delete the other, and publish the keeper at the clean slug `/privacy-policy/`:
```bash
# Example: delete private duplicate, republish correct one at clean slug
stack_wp post delete 3 --force
# or slug-swap via wp db query if 561 has the correct content
```

### 17. `restore-from-backup.sh` defaults to month-old backup

**Symptom:** Running `scripts/restore-from-backup.sh` without arguments silently restores data from May 31 — over a month out of date. The stack comes up with old content, old page IDs, and no recent VT work.

**Root cause:** The default backup path (line 7) is hardcoded:
```bash
BACKUP="${1:-$HOME/WordPress/willowyhollow/backups/willowyhollow-live-2026-05-31.sql.gz}"
```

**Fix:** Dynamically find the most recent backup, or require an explicit argument so the user can't accidentally restore stale data:
```diff
-# Default to a specific dated backup (stale)
-BACKUP="${1:-$HOME/WordPress/willowyhollow/backups/willowyhollow-live-2026-05-31.sql.gz}"
+# Require explicit argument (no default)
+BACKUP="${1:?Usage: $0 <path-to-dump.sql.gz>}"
+
+# Or use the most recent backup in the directory
+# BACKUP="${1:-$(ls -t $HOME/WordPress/willowyhollow/backups/*.sql.gz 2>/dev/null | head -1)}"
```

### 18. `push-practice-to-staging2.sh` overwrites files before backing them up

**Symptom:** The push script syncs practice files to staging2 (step 2) before creating the staging2 DB backup (step 4). If rsync is interrupted or the script crashes between steps 2 and 4, staging2's files are partially overwritten with no backup to fall back to.

**Root cause:** Step order in `push-practice-to-staging2.sh`:
1. Fix permissions
2. **rsync files → staging2** (destructive)
3. Export practice DB
4. **Backup staging2 DB** (too late — files already overwritten)
5. Import practice DB to staging2

**Fix:** Reorder so staging2 is backed up before any destructive write:
```diff
 # Current order (wrong):
-[1] Fix permissions
-[2] Sync files practice → staging2 (DESTRUCTIVE)
-[3] Export practice DB
-[4] Backup staging2 DB (too late)
-[5] Import practice DB
+[1] Backup staging2 DB (before any writes)
+[2] Backup staging2 files (rsync to temp dir)
+[3] Fix permissions
+[4] Sync files practice → staging2
+[5] Export practice DB
+[6] Import practice DB
```

Also add a pre-sync file backup (`rsync -a --dry-run ...` or tar archive) for staging2's `wp-content/uploads/` and theme files so file overwrites are reversible.

### 19. WP_DEBUG is OFF on practice environment

**Symptom:** PHP warnings, notices, and deprecation errors are silently suppressed on the development environment (:8081). Runtime errors in the VT engine, plugin conflicts, or PHP 8.x incompatibilities produce no visible output and no debug log.

**Root cause:** `wp-config.php` line 90 defines `WP_DEBUG` as `false`. The `wp-config-local.php` override file (which Docker uses) does not re-enable it.

**Fix:** Enable WP_DEBUG on the practice environment in `wp-config-local.php`:
```php
define( 'WP_DEBUG', true );
define( 'WP_DEBUG_LOG', true );
define( 'WP_DEBUG_DISPLAY', false );
```

### 20. Orphan cron hooks from uninstalled plugins

**Symptom:** Four cron events reference plugins that no longer exist:
- `updraftplus_clean_temporary_files` — UpdraftPlus not installed
- `prli_ipn_clean`, `prli_ipn_remote_fetch`, `prettylink_check_license_status_event` — Pretty Link not installed

**Root cause:** Plugins were removed without clearing their scheduled events.

**Fix:** Remove orphan cron hooks:
```bash
stack_wp cron event delete updraftplus_clean_temporary_files
stack_wp cron event delete prli_ipn_clean
stack_wp cron event delete prli_ipn_remote_fetch
stack_wp cron event delete prettylink_check_license_status_event
```

Also delete any leftover option rows (`wp_options` WHERE `option_name` LIKE `%updraft%` or `%prli%`).

### 21. WordPress cron has stopped firing (~10 days stalled)

**Symptom:** All scheduled cron events show `next_run` dates from June 26-27, 2026 — none have fired in ~10 days. Site health checks, version/plugin/theme update checks, sitemap regeneration, scheduled post deletions, and cache optimization are all stalled.

**Root cause:** WordPress cron relies on site visits to trigger `wp-cron.php`. On the practice environment (:8081), either no traffic reaches the site (idle development machine), or a PHP error in `wp-cron.php` is silently failing (hidden by WP_DEBUG being OFF — see bug 19).

**Fix:**
1. Enable WP_DEBUG first (bug 19) to surface any cron errors.
2. Add a systemd timer or host-side cron job to ping `wp-cron.php`:
```bash
# /etc/cron.d/willowyhollow-practice
*/15 * * * * lauer curl -s http://localhost:8081/wp-cron.php?doing_wp_cron=1 >/dev/null 2>&1
```
3. Or set `ALTERNATE_WP_CRON` in `wp-config-local.php`.

### 22. `headers-security-advanced-hsts-wp` installed but inactive

**Symptom:** The plugin responsible for HSTS headers is installed but deactivated. The unresolved staging2 monitor observation about missing HSTS (`obs_staging2_monitor_header-hsts`) may share the same root cause on staging2 — or it may be a separate server-level config issue on SiteGround.

**Root cause:** The plugin was deactivated at some point, stopping HSTS header delivery. The inactive plugin lingering on practice also creates confusion about which mechanism handles HSTS (SG Security vs this plugin).

**Fix:** Either remove the orphaned plugin entirely, or reactivate and configure it:
```bash
stack_wp plugin activate headers-security-advanced-hsts-wp
```
If HSTS is instead handled by SG Security on staging2, uninstall this plugin from practice to avoid misattribution on the next staging2 sync.

### 23. Three "Learn More" buttons have empty `aria-label` overriding visible text

**Symptom:** All three home page service card buttons render as:
```html
<a class="uagb-buttons-repeater wp-block-button__link" aria-label="" href="/thai-massage/"
   rel="follow noopener" target="_self" role="button">
  <div class="uagb-button__link">Learn More</div>
</a>
```
The `aria-label=""` is empty, which **overrides** the visible "Learn More" text for screen readers. Assistive technology announces nothing — the button is effectively invisible to blind users.

**Root cause:** UAGB (Ultimate Addons for Gutenberg) sets `aria-label=""` as the default when no custom aria-label is configured in the button block settings. The empty value takes precedence over the visible child text.

**Fix:** Either set a meaningful `aria-label="Learn more about Thai Massage"` on each button in the WordPress editor, or remove the `aria-label` attribute entirely so screen readers fall back to the visible text. A WPCode snippet or `functions.php` filter can strip empty aria-labels:
```php
add_filter( 'render_block', function( $content ) {
  return str_replace( 'aria-label=""', '', $content );
}, 10, 1 );
```

### 24. Heading hierarchy skips H1→H3 on services page

**Symptom:** The Services page heading order goes: `<h1>Explore Our Therapeutic Massage Services</h1>` → `<h3>Thai Massage</h3>`. The `h2` level is skipped between the page title and the service card headings. This violates WCAG heading hierarchy best practices (headings should not skip levels).

**Root cause:** The three service cards use `<h3>` tags while the section heading within the page content uses `<h2>`. There is no `<h2>` wrapper between the page `<h1>` and the card `<h3>`s.

**Fix:** Change the service card headings from `<h3>` to `<h2>` in the page editor, or add a section `<h2>` between the main heading and the cards:
```html
<h2>Our Services</h2>
<!-- then h3 cards below h2 -->
```

### 25. Duplicate H1 on Therapeutic Bodywork page

**Symptom:** The rendered Therapeutic Bodywork page has two `<h1>Therapeutic Bodywork</h1>` tags — one from the Astra theme's page title output and one from the page content's hero heading. This is an accessibility/SEO violation (duplicate H1 was previously noted for the Thai page in AGENTS.md gotcha #8 but also applies here).

**Root cause:** Astra theme outputs `the_title()` as an `<h1>` via the theme template. The page content also contains an `<h1>` block. This affects all single-service pages.

**Fix:** Change the in-content heading to `<h2>` or `headingTag":"h2"` in the UAGB advanced heading block. The theme's H1 serves as the canonical page title.

### 26. Google Fonts URL has malformed weight parameter

**Symptom:** The rendered page loads fonts with:
```html
<link rel='stylesheet' id='astra-google-fonts-css'
  href='https://fonts.googleapis.com/css?family=Work+Sans:400%2C%2C600|Belleza:400%2C&#038;display=swap&#038;ver=4.13.4'
  media='all' />
```
The `Work+Sans:400%2C%2C600` decodes to `Work+Sans:400,,600` — a double comma indicating an empty weight value between 400 and 600. Google Fonts may ignore the malformed entry or fail to serve the 600 weight.

**Root cause:** The Astra theme's font loader generates the URL with an empty weight entry. The `%2C` encodes commas but produces `400,,600` instead of `400,600`.

**Fix:** In WordPress Customizer → Typography → check Work Sans font weights. Ensure only 400 and 600 are selected (no blank entry). If the issue persists, a filter can clean the URL:
```php
add_filter( 'style_loader_src', function( $src ) {
  return str_replace( '%2C%2C', '%2C', $src );
} );
```

### 27. Auto-generated AI filenames used as image alt text

**Symptom:** Several images use their AI-generated filenames as alt text:
- `alt="comfyui 01302 "` (Relaxation card on home page)
- `alt="comfyui 01114"` (services page)
- `alt="comfyui 01018 stretchscale"` (Thai card on home page)

These are not meaningful descriptions. A screen reader announces "comfyui 01302" instead of describing the image content.

**Root cause:** Images were uploaded with their ComfyUI-generated filenames. When UAGB generates the `<img>` tag, it falls back to the filename (stripped of extension) as the alt attribute when no manual alt text is entered.

**Fix:** Set meaningful alt text on each image in the WordPress media library. Each ComfyUI-generated image should have a human-readable description (e.g. "Relaxation massage session in a calm studio setting").

### 28. Internal site URL causes redirect loop on Docker network

**Symptom:** Requests made from inside the WordPress container (wp_remote_get, wp-cron internal pings, REST API self-calls) all fail or redirect because `siteurl` is `http://localhost:8081/` but the container serves on port 80. Internal requests to `http://wordpress/` redirect to `http://localhost:8081/` which is unreachable from inside the container. This breaks:
- **WordPress cron** — DISABLE_WP_CRON may be needed (but not set), and cron never fires because no external traffic hits the dev machine
- **REST API self-calls** — any plugin making internal API requests will fail
- **wp_remote_get() to itself** — Site Health checks that ping the site will time out
- **Services page redirect** — `/services/` redirects to `http://wordpress:8081/services/` instead of serving directly

**Root cause:** The database stores `siteurl` and `home` as `http://localhost:8081/` (matching the external port), but the Docker container serves WordPress on port 80 internally.

**Fix:** Either (a) configure the Docker WordPress container to also serve on port 8081 internally, or (b) add a filter in `wp-config-local.php` that overrides siteurl for internal requests, or (c) accept the limitation and ensure wp-cron is triggered via an external cron job.

### 29. Protocol-relative URLs for third-party services

**Symptom:** Several resources use protocol-relative URLs (`//cal.com`, `//google-analytics.com`, `//www.googletagmanager.com`) instead of explicit `https://`. These can break when the page is served over HTTPS with strict CSP headers, and some CDNs/browsers interpret them relative to the current protocol (which may be `http:` in development).

**Root cause:** Various plugins and site settings that used protocol-relative URLs, possibly from SG Optimizer or the theme's URL builder. The `//` prefix means "use the same protocol as the current page."

**Fix:** Replace with explicit `https://` URLs where possible. For Google services (Analytics, Tag Manager) and Cal.com, these must be HTTPS:
```html
<!-- Instead of: -->
src="//www.googletagmanager.com"
<!-- Use: -->
src="https://www.googletagmanager.com"
```

### 30. Duplicate viewport meta tag

**Symptom:** The rendered HTML contains two viewport meta tags:
```html
<meta name="viewport" content="width=device-width, initial-scale=1">
```
(twice). While browsers handle duplicates gracefully, the duplicate wastes bytes and indicates a plugin/theme conflict.

**Root cause:** Both the Astra theme and a plugin (likely UAGB or SG Optimizer) inject a viewport meta tag.

**Fix:** Identify the source of the duplicate and remove it via a `wp_head` action at priority 0 or 99:
```php
remove_action( 'wp_head', 'the_source_plugin_viewport_function' );
```

### 31. `robots.txt` disallows all crawlers (blocking indexing if synced to staging2)

**Symptom:** `robots.txt` returns:
```
User-agent: *
Disallow: /
```
No sitemap URL is listed. All search engine crawlers are blocked from indexing the entire site. If this `robots.txt` is part of the database content and gets pushed to staging2 via `push-practice-to-staging2.sh`, staging2 would also have `Disallow: /`, preventing Google from indexing it.

**Root cause:** The `robots.txt` is generated by a plugin or WordPress setting (SG Security or SureRank). On localhost practice this is harmless, but the robots.txt content is DB-stored and travels with sync scripts.

**Fix:** Add a sitemap URL and remove the blanket disallow:
```
Sitemap: https://staging2.willowyhollow.com/sitemap.xml

User-agent: *
Allow: /
```
Since robots.txt on practice should still block crawlers, make the fix conditional per environment (e.g. via a filter that checks `siteurl`).

### 32. PHP upload limits too low (2MB) for site images

**Symptom:** `upload_max_filesize = 2M` and `post_max_size = 8M`. The site uses high-resolution ComfyUI-generated images (500px+, WebP format, typically 200-500KB each). Media uploads larger than 2MB will fail silently.

**Root cause:** Default PHP configuration in the Docker `wordpress:latest` image. These values are not overridden in `php.ini` or `wp-config.php`.

**Fix:** Override in `wp-config-local.php` or a custom `php.ini`:
```php
@ini_set( 'upload_max_filesize', '64M' );
@ini_set( 'post_max_size', '64M' );
@ini_set( 'memory_limit', '256M' );
```

### 33. XML-RPC enabled (attack surface)

**Symptom:** `xmlrpc.php` returns HTTP 200. XML-RPC is a known WordPress attack vector for brute force login attempts and pingback DDoS amplification.

**Root cause:** XML-RPC is enabled by default in WordPress. The `wordpress:latest` Docker image does not disable it.

**Fix:** Disable XML-RPC in a mu-plugin or via the SG Security plugin settings:
```php
add_filter( 'xmlrpc_enabled', '__return_false' );
```

### 34. `readme.html` exposed (WordPress version disclosure)

**Symptom:** `http://localhost:8081/readme.html` is accessible and reveals the exact WordPress version installed. Attackers use this to target known vulnerabilities for that specific version.

**Root cause:** The `wordpress:latest` Docker image includes `readme.html` in the web root.

**Fix:** Remove or restrict access:
```bash
rm public_html/readme.html
```

### 35. REST API user enumeration via `/wp/v2/users/`

**Symptom:** `GET /wp-json/wp/v2/users/` returns user ID 1 with display name, avatar, and author URL. This exposes the username (`rsteitz`), enabling brute force targeting.

**Root cause:** The WordPress REST API exposes users by default for any unauthenticated request.

**Fix:** Restrict the users endpoint to authenticated requests only:
```php
add_filter( 'rest_endpoints', function( $endpoints ) {
  if ( isset( $endpoints['/wp/v2/users'] ) ) {
    $endpoints['/wp/v2/users']['permission_callback'] = function() {
      return current_user_can( 'list_users' );
    };
  }
  return $endpoints;
} );
```

### 36. Unused dark SVG blob files in uploads

**Symptom:** Four SVG files (`blob-3.svg`, `blob-5.svg`, `blob-7.svg`, `blob-9.svg`) exist in `/wp-content/uploads/` with dark fills (`#243348`, `#3E5C86`, `#9CBACF`, `#4F6B82`). The CSS in `functions.php` only references the `blob-white-*.svg` variants. The dark blobs are never used on any page.

**Root cause:** The SVG blobs were generated in both dark and white variants. The dark blobs were kept when the design switched to white-only blobs on the navy background.

**Fix:** Remove the four unused dark blob files:
```bash
rm public_html/wp-content/uploads/blob-3.svg
rm public_html/wp-content/uploads/blob-5.svg
rm public_html/wp-content/uploads/blob-7.svg
rm public_html/wp-content/uploads/blob-9.svg
```

### 37. `dns-prefetch` hint for `//localhost` (wasted DNS)

**Symptom:** The page includes `<link rel='dns-prefetch' href='//localhost' />`. Prefetching localhost is meaningless — the DNS resolution for `localhost` is instant and never a bottleneck.

**Root cause:** SG Optimizer auto-generates dns-prefetch hints based on the site URL (`http://localhost:8081/`) and incorrectly includes localhost.

**Fix:** Remove the localhost dns-prefetch. SG Optimizer settings can exclude specific domains, or a filter can strip it:
```php
add_filter( 'sg_cachepress_dns_prefetch', function( $urls ) {
  return array_filter( $urls, fn( $url ) => ! str_contains( $url, 'localhost' ) );
} );
```

### 38. 12 JavaScript files loaded on home page (excessive)

**Symptom:** The home page loads 12 JavaScript files (10 external + 2 inline scripts), including 7 from UAGB alone: countUp.min.js, imagesloaded.min.js, slick.min.js, spectra-block-positioning.min.js, spectra-counter.min.js, testimonial.min.js, uagb-button-child.min.js — plus a page-specific UAGB script. Many of these (counter, testimonial slider, slick carousel) are not used on the home page.

**Root cause:** UAGB enqueues all its block JS assets globally on every page, regardless of whether those blocks are present.

**Fix:** Enable conditional script loading in UAGB settings (Settings → UAGB → Assets → "Load assets on specific pages"). Or switch to a lighter block/theme approach.

### 39. `jQuery Migrate` loaded (deprecated API usage)

**Symptom:** `jquery-migrate.min.js` is loaded alongside jQuery. This indicates at least one plugin or theme component still uses deprecated jQuery APIs. jQuery Migrate is a compatibility shim and should not be present in production.

**Root cause:** Either Astra theme, UAGB, or another plugin references deprecated jQuery methods.

**Fix:** Remove jQuery Migrate via filter after confirming compatibility:
```php
add_action( 'wp_default_scripts', function( $scripts ) {
  if ( ! is_admin() && isset( $scripts->registered['jquery'] ) ) {
    $scripts->registered['jquery']->deps = array_diff(
      $scripts->registered['jquery']->deps, ['jquery-migrate']
    );
  }
} );
```

### 40. `noindex, nofollow` on all pages (blocks all search indexing)

**Symptom:** Every page includes `<meta name="robots" content="noindex, nofollow">`. This prevents ALL search engines from indexing ANY page on the site — even on staging2 where indexing may be desired for testing.

**Root cause:** The SureRank plugin (or SG Security) sets `noindex, nofollow` globally. On practice this is desired, but the setting is DB-stored and will propagate to staging2 and production via sync scripts.

**Fix:** Make robots meta conditional per environment, or set it to `index, follow` for staging2 and production. In SureRank or SG Security settings, configure different rules per environment.

### 41. Schema.org JSON-LD has incorrect founder name

**Symptom:** The structured data markup contains:
```json
"founder":[{"@type":"Person","name":"alan"}]
```
The founder name is "alan" instead of the business owner's actual name (Sa Rai). This incorrect data could appear in Google Knowledge Panels.

**Root cause:** The SureRank SEO plugin pulls the founder name from the WordPress user profile, which has the display name "alan" (the admin user).

**Fix:** Update the user profile display name to "Sa Rai" in WordPress admin → Users, or configure SureRank's schema settings to use the correct business owner name.

### 42. Email address exposed in plain text (spam vulnerability)

**Symptom:** The footer contains `mailto:alanz@willowyhollow.com` as a plain, unencoded HTML link. Email harvesters can easily scrape this address for spam lists.

**Root cause:** The email address is hardcoded in a footer widget's raw HTML block with no obfuscation.

**Fix:** Obfuscate the email using HTML entities, JavaScript encoding, or a shortcode:
```html
<!-- Instead of: -->
<a href="mailto:alanz@willowyhollow.com">alanz@willowyhollow.com</a>
<!-- Use: -->
<a href="mailto:&#097;&#108;&#097;&#110;&#122;&#064;&#119;&#105;&#108;&#108;&#111;&#119;&#121;&#104;&#111;&#108;&#108;&#111;&#119;&#046;&#099;&#111;&#109;">
  alanz@willowyhollow.com
</a>
```

### 43. Images missing alt attributes entirely

**Symptom:** Two `<img>` tags on the home page have no `alt` attribute at all (not even empty). This fails WCAG accessibility guidelines — screen readers will announce the image filename or nothing.

**Root cause:** The images were inserted without alt text in the page content or through a widget that doesn't enforce alt attributes.

**Fix:** Add descriptive alt text to each image in the WordPress editor or via the media library.

### 44. Hardcoded copyright year in footer

**Symptom:** The footer displays `Copyright © 2026 Willowy Hollow` with a hardcoded year. In 2027, this will appear outdated.

**Root cause:** The footer text is a static string in the WordPress Customizer footer copyright section rather than using a dynamic `echo date('Y')`.

**Fix:** Replace with a dynamic year in a child theme template or mu-plugin:
```php
add_filter( 'astra_footer_copyright', function( $text ) {
  return str_replace( date( 'Y' ), '', $text ) . date( 'Y' );
} );
```

### 45. Database has 1,081 tables from 7 abandoned WordPress installations

**Symptom:** The single database contains 1,081 tables, but only ~10% belong to the active installation (`ldt_` prefix). The other 6 WordPress installations — `stag02stag04WH`, `staging03`, `tmp502ff4`, `wp1737ed`, `wp7f1f5b`, `wpcf8a57` — are from old staging copies, plugin tests, and abandoned setups. Key orphaned plugin tables include:

| Plugin | Tables per install | Orphaned total |
|--------|-------------------|----------------|
| Amelia (appointments) | 57 | ~342 |
| Latepoint (bookings) | 39 | ~234 |
| Wordfence (security) | ~18 | ~108 |
| Fluent Forms | 7 | ~42 |
| Pretty Link | 3 | ~18 |
| Action Scheduler | ~4 | ~24 |
| WPvivid Backup | ~3 | ~18 |

**Root cause:** The database was imported from staging2 or production, which accumulated tables from years of plugin testing, site migrations, and staging clones. The sync scripts (`pull-staging2-to-practice.sh`, `restore-from-backup.sh`) copy the entire database including all orphaned tables.

**Fix:** Drop all tables with non-active prefixes after backing up:
```bash
# List all non-active prefixes:
stack_wp db query "SELECT DISTINCT SUBSTRING_INDEX(table_name, '_', 1) as prefix FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name NOT LIKE 'ldt_%'"

# Drop each orphan prefix group (careful — backup first!)
# For prefix groups: stag02stag04WH_, staging03_, tmp502ff4_, wp1737ed_, wp7f1f5b_, wpcf8a57_
```

### 46. Orphaned plugin tables from uninstalled plugins

**Symptom:** Even within the active `ldt_` prefix, tables exist for plugins that are no longer installed:
- `ldt_amelia_*` (57 tables) — Amelia booking plugin not installed
- `ldt_latepoint_*` (39 tables) — Latepoint booking plugin not installed
- `ldt_fluentform_*` (7 tables) — Fluent Forms not installed
- `ldt_prli_*` (3 tables) — Pretty Link not installed
- `ldt_wf*` (18+ tables) — Wordfence not installed
- `ldt_wpvivid_*` (3 tables) — WPvivid Backup not installed

**Root cause:** Plugins were deactivated and deleted from `wp-content/plugins/` but their database tables were never cleaned up during uninstallation.

**Fix:** Drop each orphaned table group. Most plugins provide a cleanup option during deactivation, but since they're already removed, manual cleanup is needed:
```bash
# Back up database first, then drop each group
stack_wp db query "DROP TABLE IF EXISTS ldt_amelia_*"  # (one by one)
stack_wp db query "DROP TABLE IF EXISTS ldt_latepoint_*"
stack_wp db query "DROP TABLE IF EXISTS ldt_fluentform_*"
stack_wp db query "DROP TABLE IF EXISTS ldt_prli_*"
stack_wp db query "DROP TABLE IF EXISTS ldt_wf*"
stack_wp db query "DROP TABLE IF EXISTS ldt_wpvivid_*"
```

### 47. 20MB+ of orphaned Astra/UAGB template cache

**Symptom:** The uploads directory contains 16MB of `ast-block-templates-json/` and 5.7MB of `astra-sites/` — cached block template data from the Astra theme and UAGB starter libraries. These files accumulate over time and are never pruned.

**Root cause:** The Astra theme and UAGB plugin cache template library JSON responses in the uploads directory. The cache accumulates with each template preview but is never automatically cleaned.

**Fix:** Clear the cache directories:
```bash
rm -rf public_html/wp-content/uploads/ast-block-templates-json/
rm -rf public_html/wp-content/uploads/astra-sites/
```

### 48. Stale SG Optimizer assets directory (combining disabled)

**Symptom:** The `siteground-optimizer-assets/` directory has 56 files (2.4MB) of cached/minified CSS and JS. However, SG Optimizer combining is explicitly disabled on practice by the sync scripts (lines 86-88 in `sync-preview-to-practice.sh`). The cached assets are stale and never regenerated.

**Root cause:** SG Optimizer's CSS/JS combination was disabled locally (because combined files don't exist on disk), but previously generated assets were never cleaned up.

**Fix:** Remove the stale combined assets:
```bash
rm -rf public_html/wp-content/uploads/siteground-optimizer-assets/
```

### 49. WPCode VT CSS/JS snippet files in repo are disconnected from the running system

**Symptom:** `wpcode-view-transitions.css` and `wpcode-view-transitions.js` exist in the repo root but are NOT registered as WPCode snippets in the database. The live system injects VT CSS/JS via `functions.php`. The WPCode database only has "Cal" and "MobileButtonsFirst" published. The `.css` and `.js` files in the repo are stale artifacts that no longer match the live system.

**Root cause:** The VT code was migrated from WPCode snippets to `functions.php` injection, but the WPCode snippet files were kept in the repo without updating their content or removing them.

**Fix:** Either (a) delete the stale `.css`/`.js` files from the repo, or (b) resync them to match `functions.php` and register them as active WPCode snippets. Delete the git-tracked copies:
```bash
rm wpcode-view-transitions.css wpcode-view-transitions.js
```

### 50. Install scripts accessible in web root (7 of 8 lack ABSPATH guard)

**Symptom:** 5+ install scripts (`install-*.php`) and `functions-vt.php` are present in `/var/www/html/` (the web root). 7 of 8 install scripts lack the `ABSPATH` guard that prevents direct HTTP execution. While most scripts require WordPress functions and will error gracefully, `install-flip-card.php` performs direct file writes and DB operations without any guard.

**Root cause:** The `docker-compose.yml` mounts `./public_html` to `/var/www/html`. The install scripts are in the repo root (`install-*.php`) and also land in the web root via the sync/rsync process.

**Fix:** Remove install scripts from the web root after use:
```bash
rm public_html/install-*.php public_html/functions-vt.php
```
Add them to the rsync exclude list in all sync scripts to prevent re-copying.

### 51. Google Site Kit and HSTS plugin are inactive (27MB of dead code)

**Symptom:** `google-site-kit` (24MB) and `headers-security-advanced-hsts-wp` (2.9MB) are installed but inactive. Together they waste 27MB of disk space and extend Docker image build times.

**Root cause:** Plugins installed during early site development, deactivated when not needed, never uninstalled.

**Fix:** Uninstall unused plugins:
```bash
stack_wp plugin uninstall google-site-kit
stack_wp plugin uninstall headers-security-advanced-hsts-wp
```

### 52. Service pages use inconsistent templates

**Symptom:** The three service pages each use different layouts:
- **Thai Massage** (`?page_id=1248`): Simple WordPress cover block (`wp-block-cover`) with inline view-transition-name styles
- **Therapeutic Bodywork** (`?page_id=1178`): Complex UAGB container grid layout (`wp-block-uagb-container`) with VT class names
- **Relaxation Massage** (`?page_id=1251`): Cover block layout (similar to Thai)

The Thai and Relaxation pages use the old install script layout, while Therapeutic Bodywork has the newer full-page design.

**Root cause:** Service pages were created by different install scripts at different times (`install-thai-vt-card.php`, `install-therapy-bodywork-page.php`, `install-relax-vt-card.php`), each with different template designs.

**Fix:** Unify all three service pages to use the same layout template (Therapeutic Bodywork's UAGB grid layout is the most complete).

### 54. Site logo alt text is auto-generated filename

**Symptom:** The site logo renders as:
```html
<img class="custom-logo" alt="comfyui 01114" ...>
```
The alt text is the AI image filename, not the business name "Willowy Hollow".

**Root cause:** The logo was uploaded from a ComfyUI-generated image without setting a human-readable alt text in the media library or Customizer.

**Fix:** Update the logo alt text in WordPress Customizer → Site Identity → Logo Alt Text.

### 55. On-page Cal.com booking embed may not function on practice

**Symptom:** The Cal.com embed script loads from `https://app.cal.com/embed/embed.js`, but the site URL is `http://localhost:8081/`. Cal.com's iframe embed typically includes a webhook callback URL pointing back to the site. If Cal.com sends booking confirmation callbacks to `http://localhost:8081/`, they will fail because this URL is not reachable from the internet.

**Root cause:** The site URL is hardcoded in the database and passed to Cal.com as the redirect/callback URL.

**Fix:** This is an accepted limitation of the practice environment. Ensure the `search-replace` in sync scripts correctly updates the site URL when pushing to staging2/production so Cal.com receives valid callback URLs.

### 56. Thai Massage page uses inline VT naming, not class-based convention

**Symptom:** The Thai Massage page still uses inline `style="view-transition-name: thai-image"` on the `<img>` tag (from the original `install-thai-vt-card.php` approach). The Therapeutic Bodywork page uses the newer `.vt-image-therapy` class convention. Two different VT naming patterns coexist.

**Root cause:** The Thai page was created with the older inline-style approach and was never migrated to the class-based `.vt-*` convention.

**Fix:** Replace the inline style with the `.vt-image-thai` and `.vt-title-thai` class names, matching the conventions used by Therapeutic Bodywork:
```diff
-<img class="wp-block-cover__image-background wp-image-1033" ... style="view-transition-name: thai-image" />
+<img class="wp-block-cover__image-background wp-image-1033 vt-image-thai" ... />
```

### 53. Amelia plugin settings persist with staging2 URLs (no Amelia installed)

**Symptom:** The `amelia_settings` option in `wp_options` contains serialized data with hardcoded `staging2.willowyhollow.com` URLs. The Amelia booking plugin is not installed, but its settings option remains in the database. The serialized data cannot be fixed with simple `search-replace` because serialized PHP strings encode their own length — changing URL lengths would corrupt the data.

**Root cause:** Amelia was installed and configured on staging2, then deactivated and deleted. The `amelia_settings` option was never cleaned up.

**Fix:** Delete the orphaned option:
```bash
stack_wp option delete amelia_settings
```

### 54. Gravatar enabled (privacy + performance cost)

**Symptom:** `show_avatars` is enabled with `mystery` as the default avatar type. Every page load makes external requests to `gravatar.com` to load mystery-man placeholder images for the admin user. With 1 user and no commenters, this wastes bandwidth and exposes visitor IPs to Gravatar's servers.

**Root cause:** Default WordPress settings were not adjusted for privacy.

**Fix:** Disable avatars in Settings → Discussion, or set to blank:
```bash
stack_wp option update show_avatars 0
```

### 55. Two SureForms forms exist, but only one is embedded

**Symptom:** Two published SureForms forms exist ("Massage Booking Form" ID 624, "Simple Contact Form" ID 513), but the Contact page does embed `[sureforms id='513']`. The booking form `624` was not found embedded anywhere in the current practice content.

**Root cause:** One form was placed on the Contact page; the booking form was created but not assigned to a page.

**Fix:** Either embed the booking form on the Booking page, or delete the unused form:
```bash
stack_wp post delete 624
```

### 56. Comments and pingbacks open by default (spam vector)

**Symptom:** `default_comment_status` and `default_ping_status` are both "open". Any new page or post created will have comments and pingbacks/trackbacks enabled by default. For a massage therapy site with no blog commenting, this invites spam.

**Root cause:** Default WordPress settings were not adjusted after installation.

**Fix:** Disable comments and pingbacks globally:
```bash
stack_wp option update default_comment_status closed
stack_wp option update default_ping_status closed
```

### 57. `blog_public` set to 0 (double-blocks search indexing)

**Symptom:** `blog_public` is 0 ("Discourage search engines from indexing this site"). Combined with the `noindex, nofollow` meta tag from SureRank (bug 40), search engine indexing is double-blocked. If this value is stored in the database and synced to staging2, it would prevent Google from indexing even if the robots.txt allows it.

**Root cause:** The setting was enabled during development and never reverted for staging2/production.

**Fix:** Make `blog_public` conditional per environment. On staging2/production it must be 1:
```bash
# For staging2/production:
stack_wp option update blog_public 1
```
Or override in `wp-config-local.php` per environment.

### 58. Site tagline calls it a "spa" — conflicts with "massage therapy" branding

**Symptom:** The site tagline reads "A spa and therapy for your wellbeing." The meta description and page content describe "massage therapy," "therapeutic bodywork," and "Thai massage." The word "spa" appears in the tagline and schema markup but nowhere in the actual page content or service descriptions.

**Root cause:** The tagline was set during initial site setup and never updated to match the refined brand voice (the business is a massage therapy practice, not a spa).

**Fix:** Update the tagline to accurately describe the business:
```bash
stack_wp option update blogdescription "Therapeutic massage for your wellbeing"
```

### 59. Phantom `php.ini` in web root (dead file, false security, exposed)

**Symptom:** `public_html/php.ini` exists with `disable_functions = shell_exec,system,passthru` but is NOT loaded by PHP — the Docker container reads from `/usr/local/etc/php/` and shows `disable_functions => no value`. The file is accessible via HTTP at `http://localhost:8081/php.ini` (200 OK). It provides a false sense of security (shell_exec is actually enabled) while exposing a configuration file to anyone who requests it.

**Root cause:** The php.ini was placed in the web root during initial setup, but the Docker WordPress image does not read php.ini from the web root. Apache/PHP-FPM in the container uses its own ini files.

**Fix:** Remove the dead file and apply the intended restrictions in the correct location:
```bash
# Remove dead file from web root
rm public_html/php.ini

# If shell_exec/sysytem/passthru should be disabled, use a Docker-specific ini:
# Create public_html/conf.d/disable-shell.ini and mount it
```

### 60. Stale wpcli container not cleaned up (5 days)

**Symptom:** The `willowyhollow-practice-wpcli-1` container has been in `Exited (1)` state since June 30 — 5 days without cleanup. Each `stack_wp` invocation creates a new container via `dc run --rm`, but the `--rm` flag failed to remove it (possibly due to the non-zero exit code).

**Root cause:** When `stack_wp` commands fail (exit code 1), Docker's `--rm` auto-cleanup may not trigger. The `dc run --rm --no-deps wpcli wp ...` pattern doesn't guarantee cleanup on failure.

**Fix:** Add periodic cleanup or a manual prune:
```bash
docker rm willowyhollow-practice-wpcli-1
# Or add to stack.sh for automatic cleanup:
# dc run --rm ... || docker rm -f $(dc ps -q wpcli 2>/dev/null) || true
```

### 61. No Docker memory limits on containers

**Symptom:** Both WordPress and MariaDB containers have no memory limits (`Memory: 0` in Docker inspect). The container can consume all available host memory. PHP's internal `memory_limit` of 128M constrains individual PHP processes, but Apache workers and MariaDB can grow unbounded.

**Root cause:** `docker-compose.yml` does not set `mem_limit` or `deploy.resources.limits.memory` on any service.

**Fix:** Add memory limits to docker-compose.yml:
```yaml
services:
  wordpress:
    ...
    mem_limit: 512m
  db:
    ...
    mem_limit: 512m
```

### 62. Contact page H1 references "Thai Solitude" — wrong business name

**Symptom:** The Contact page renders `<h1>Get in Touch with Thai Solitude Today</h1>`. The business is named **Willowy Hollow**, not "Thai Solitude." This name appears nowhere else on the site — not in the tagline, navigation, meta description, or service pages. The content also contains references to both "Thai Solitude" and "Willowy Hollow" inconsistently.

**Root cause:** The Contact page content was copied from a template or earlier branding iteration and never updated.

**Fix:** Edit the Contact page content to replace "Thai Solitude" with "Willowy Hollow":
```bash
stack_wp post update 301 --post_content="$(stack_wp post get 301 --field=post_content | sed 's/Thai Solitude/Willowy Hollow/g')"
```

### 63. 404 page causes connection failure — not a 404

**Symptom:** Requesting a non-existent URL from a browser returns HTTP 000 (connection failure). WordPress redirects to `http://wordpress:8081/...` which doesn't resolve on the host machine. Instead of a proper "Page Not Found" template with 404 status, the user sees a browser error page.

**Root cause:** The site URL is `http://localhost:8081/`. When WordPress generates a 404 redirect, it uses the internal Docker hostname (`wordpress:8081`) which is unreachable from the host.

**Fix:** Add a custom 404 handler to the child theme:
```php
add_action( 'template_redirect', function() {
  if ( is_404() ) {
    status_header( 404 );
    nocache_headers();
    include( get_404_template() );
    exit;
  }
} );
```

### 64. Empty search results has no title or "no results" message

**Symptom:** Searching for a non-existent term returns a page with no `<title>` tag and no visible "No results found" message. The page appears blank.

**Root cause:** The Astra theme's search template may not handle the empty results state, or the page fails to render when no posts match.

**Fix:** Add a filter that supplies the missing title:
```php
add_filter( 'astra_thead_title', function( $title ) {
  if ( is_search() && ! have_posts() ) {
    return 'No results found';
  }
  return $title;
} );
```

### 65. Cal.com embed script injected twice (header AND footer) via IHAF

**Symptom:** The Cal.com booking script and floating button initialization are injected into every page TWICE — once via `ihaf_insert_header` and once via `ihaf_insert_footer`, both containing identical 1092-byte Cal.com embed code. This means:
- The Cal.com JS library loads and initializes twice
- The floating booking button may render duplicate elements
- Possible JavaScript race conditions on initialization
- Double bandwidth for the Cal embed payload

**Root cause:** The Cal.com embed was added to the "Insert Headers and Footers" plugin in both the header and footer sections, likely unintentionally. The same snippet is also loaded via a WPCode snippet (#705), making it potentially THREE injections total.

**Fix:** Remove the duplicate from `ihaf_insert_footer` (or `ihaf_insert_header`) and verify only one instance loads:
```bash
stack_wp option update ihaf_insert_header ""
# OR
stack_wp option update ihaf_insert_footer ""
```

### 66. UAGB loads all assets globally (block conditions disabled)

**Symptom:** `uag_enable_block_condition` is "disabled", meaning UAGB loads ALL its CSS/JS assets on EVERY page regardless of whether the blocks are used. This was noted in bug 38 (12 JS files on home page). The setting to load assets conditionally per-page is available but not enabled.

**Root cause:** The UAGB performance setting was never enabled, or was disabled to avoid perceived issues with conditional loading.

**Fix:** Enable block-level conditional asset loading:
```bash
stack_wp option update uag_enable_block_condition enabled
```

### 67. Google Fonts loaded from CDN (privacy concern, self-hosting disabled)

**Symptom:** `uag_load_gfonts_locally` is "disabled", so Google Fonts (Work Sans, Belleza) are loaded directly from `fonts.googleapis.com` and `fonts.gstatic.com` on every page load. This sends visitor IP addresses to Google's servers, which may violate GDPR requirements.

**Root cause:** The UAGB option to self-host Google Fonts was not enabled.

**Fix:** Enable local Google Fonts hosting:
```bash
stack_wp option update uag_load_gfonts_locally enabled
```

### 71. RSS feed broken (cannot connect to self)

**Symptom:** The RSS feed at `/feed/` returns a cURL error 7 because the WordPress feed reader tries to fetch `http://localhost:8081/feed/` — port 8081 is not accessible inside the Docker container. Any RSS reader, feed caching plugin, or external service that subscribes to the feed will fail.

**Root cause:** The site URL is `http://localhost:8081/` (external port) but the container serves on port 80 internally. The `fetch_feed()` call uses the site URL, which doesn't resolve from inside the container.

**Fix:** Disable RSS feeds if not used, or add a filter that overrides the feed URL for internal requests:
```php
add_filter( 'option_siteurl', function( $url ) {
  if ( defined( 'WP_CLI' ) && WP_CLI ) {
    return 'http://wordpress';
  }
  return $url;
} );
```

### 72. `wp-config-local.php` missing WP_DEBUG definitions

**Symptom:** Despite being the development environment override file, `wp-config-local.php` does not enable `WP_DEBUG`, `WP_DEBUG_LOG`, or `WP_DEBUG_DISPLAY`. The file only sets DB credentials, URLs, cache, and filesystem method.

**Root cause:** The debug constants were never added to the override file when it was created by the sync/restore scripts.

**Fix:** Add debug configuration to all three wp-config-local writers in the sync scripts (`sync-preview-to-practice.sh`, `pull-staging2-to-practice.sh`, `push-practice-to-staging2.sh`, `sync-practice-to-preview.sh`, `restore-from-backup.sh`):
```php
define( 'WP_DEBUG', true );
define( 'WP_DEBUG_LOG', true );
define( 'WP_DEBUG_DISPLAY', false );
```

### 73. All three nav locations point to the same menu

**Symptom:** `nav_menu_locations` shows `{"primary":4,"mobile_menu":4,"footer_menu":4}` — the Primary Menu (Home, Services, About, Contact) is used for main nav, mobile menu, AND footer. No separate footer links (Privacy Policy, Booking) and no mobile-specific simplification.

**Root cause:** Same default menu assigned to all three theme locations during setup.

**Fix:** Create dedicated menus for each location:
```bash
stack_wp menu create "Footer Menu"
stack_wp menu item add <footer-menu-id> --title="Privacy Policy" --link="/privacy-policy/"
stack_wp menu item add <footer-menu-id> --title="Booking" --link="/booking/"
```

### 74. 30% of media library is AI-generated images with poor alt text

**Symptom:** 49 of 161 attachments (30%) have ComfyUI-generated filenames (`ComfyUI_01018_.webp`). 24 of those have empty or filename-derived alt text. SureRank's `auto_set_image_alt: 1` auto-generates alt text from filenames, spreading meaningless text like `alt="comfyui 01302 "` across the site.

**Root cause:** Images were bulk-uploaded from AI generation without human-readable alt text. Auto-alt propagates the poor names.

**Fix:** Prioritize fixing the 12-15 images used on live pages, then delete unused ComfyUI test images. Disable auto-alt:
```bash
stack_wp option update surerank_settings --format=json '"{\"auto_set_image_alt\":0}"'
```

### 75. Duplicate block navigation menus (IDs 4 and 533)

**Symptom:** Two `wp_navigation` posts exist (IDs 4 and 533), both published, both containing `<!-- wp:page-list /-->`. One (ID 533) is unassigned to any theme location — a leftover duplicate.

**Root cause:** A block navigation menu was duplicated during site setup or block editor experimentation.

**Fix:** Delete the duplicate:
```bash
stack_wp post delete 533 --force
```

### 76. `WP_ENVIRONMENT_TYPE` mis-set to "staging" on practice

**Symptom:** `wp-config.php` defines `WP_ENVIRONMENT_TYPE` as `'staging'` (added by SiteGround staging system). On the local Docker practice environment, this should be `'local'`. The `'staging'` value may cause: suppressed admin emails, staging-specific plugin behavior, and WordPress core features treating the environment as a staging site.

**Root cause:** The `wp-config.php` setting was inherited from the SiteGround staging system and never overridden for the Docker practice environment. The `wp-config-local.php` override file doesn't redefine it.

**Fix:** Override in `wp-config-local.php`:
```php
define( 'WP_ENVIRONMENT_TYPE', 'local' );
```

### 77. Really Simple Security leftovers in wp-config.php

**Symptom:** The `wp-config.php` contains leftover constants and comments from the Really Simple Security (RSSSL) plugin:
```php
//Begin Really Simple Security session cookie settings
//END Really Simple Security cookie settings
//Begin Really Simple Security key
//END Really Simple Security key
define('RSSSL_KEY', '...');
```
The RSSSL plugin is not in the active plugins list, but its configuration artifacts remain.

**Root cause:** The plugin was deactivated and deleted without cleaning up its wp-config additions.

**Fix:** Remove the RSSSL blocks from `wp-config.php`:
```bash
sed -i '/Begin Really Simple Security/,/END Really Simple Security/d' public_html/wp-config.php
sed -i "/^define('RSSSL_KEY'/d" public_html/wp-config.php
```

### 78. Sitemap, RSS feed, and login all return 302 redirect

**Symptom:** All of the following return HTTP 302 instead of their expected status codes:
- `/wp-sitemap.xml` → 302 (should be 200 with XML)
- `/feed/` → 302 (should be 200 with RSS XML)
- `/wp-login.php` → 302 (should be 200 with login form)
- Non-existent pages → 301 (should be 404)

All redirect to `http://wordpress:8081/...` which doesn't resolve on the host machine.

**Root cause:** The site URL (`http://localhost:8081/`) doesn't match the internal Docker network URL (`http://wordpress/`). WordPress's canonical redirect fires on every request, redirecting to the canonical URL which includes port 8081 — a port that only exists on the host side, not inside the Docker network.

**Fix:** Override site URL for internal requests in `wp-config-local.php`:
```php
if ( ! defined( 'WP_HOME' ) ) {
  define( 'WP_HOME', 'http://localhost:8081' );
  define( 'WP_SITEURL', 'http://localhost:8081' );
}
// Override for internal container requests
if ( isset( $_SERVER['HTTP_HOST'] ) && $_SERVER['HTTP_HOST'] === 'wordpress' ) {
  define( 'WP_HOME', 'http://wordpress' );
  define( 'WP_SITEURL', 'http://wordpress' );
}
```

### 79. CSP WPCode snippet not installed (no Content-Security-Policy header)

**Symptom:** The `purple-practice-csp-8081` WPCode snippet was written (`scripts/install-practice-csp-wp.php`, `scripts/purple-practice-csp-8081.php`) but never installed in the database. No `Content-Security-Policy` header is sent on any response. The configured CSP from the script files is not active.

**Root cause:** The install script was written but either never run, or the snippet was deleted. The `.php` files exist in the repo but the database has no corresponding WPCode post.

**Fix:** Install the CSP snippet or remove the dead script files:
```bash
source scripts/stack.sh && stack_wp eval-file scripts/install-practice-csp-wp.php
```
Or if CSP isn't needed on practice, delete the unused script files.

### 80. Missing `X-Frame-Options` header (clickjacking vulnerability)

**Symptom:** The response headers do not include `X-Frame-Options: SAMEORIGIN` or `frame-ancestors` CSP directive. The site pages can be embedded in iframes on any third-party domain, enabling clickjacking attacks.

**Root cause:** Neither the WPCode CSP snippet nor the SG Security plugin are configured to set clickjacking protection headers. The Apache server doesn't have `mod_headers` loaded (bug 38), so `.htaccess`-based headers wouldn't work.

**Fix:** Add via PHP in a mu-plugin or WPCode snippet:
```php
add_action( 'send_headers', function() {
  header( 'X-Frame-Options: SAMEORIGIN' );
} );
```

### 81. Referrer-Policy header missing (information leak)

**Symptom:** No `Referrer-Policy` header is sent. Browsers send the full URL as the `Referer` header when navigating from the site to external links (e.g., clicking the Google Maps link or Cal.com booking). This exposes the full page URL (including query parameters) to third-party sites.

**Root cause:** Unresolved staging2 monitor observation — same issue exists on practice.

**Fix:** Add via PHP:
```php
add_action( 'send_headers', function() {
  header( 'Referrer-Policy: strict-origin-when-cross-origin' );
} );
```

### 82. `WP_CACHE` conflict between wp-config.php (true) and wp-config-local.php (false)

**Symptom:** `wp-config.php` defines `WP_CACHE` as `true` (via SG Optimizer patching), but `wp-config-local.php` overrides it to `false`. Page caching is effectively off on practice, but anyone reading `wp-config.php` would see `true` and assume caching is active. If `wp-config-local.php` is ever removed or renamed, caching would silently turn on, potentially serving stale pages during VT development.

**Root cause:** The sync scripts patch `wp-config.php` to wrap DB/CACHE definitions with `defined() || define()` (line 15), but SG Optimizer originally set it to `true`. The local override correctly sets it to `false`, but the wp-config.php value is misleading.

**Fix:** Sync the values. Either set `WP_CACHE` to `false` in wp-config.php too, or add a comment explaining the override:
```php
// Set true by SG Optimizer; overridden to false by wp-config-local.php on practice
defined('WP_CACHE') || define( 'WP_CACHE', false );
```

### 83. Mixed collations across database tables

**Symptom:** MariaDB tables use three different collations:
- `utf8mb4_unicode_520_ci` — most tables (Amelia, Latepoint, core WordPress)
- `utf8mb3_general_ci` — Wordfence security tables
- `utf8mb4_unicode_ci` — some tables

The `DB_COLLATE` in wp-config is empty, so WordPress uses its default (`utf8mb4_unicode_ci`). Mixed collations can cause index usage issues and unexpected query results when joining tables with different collations.

**Root cause:** Different plugins create tables with different collations. Wordfence uses `utf8mb3` (3-byte UTF-8, no emoji support), while other plugins use `utf8mb4`. The `utf8mb4_unicode_520_ci` vs `utf8mb4_unicode_ci` difference is minor (sort order).

**Fix:** Set a consistent collation and convert mixed tables:
```sql
ALTER TABLE ldt_wffilemods CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_520_ci;
```
(Only relevant if Wordfence is ever reinstalled — otherwise drop the orphaned tables.)

### 84. Failed MariaDB connections from wpcli container flood error logs

**Symptom:** The MariaDB error log shows 8+ `Aborted connection` warnings per day from `172.19.0.4` (the ephemeral wpcli container). Each `stack_wp` command spawns a new container that attempts SSL connections, fails, and aborts without authentication. This fills the error log with noise and wastes connection resources.

**Root cause:** The `wordpress:cli` Docker image defaults to SSL connections for MySQL. MariaDB 10.6 has `have_ssl: DISABLED`, so the SSL handshake fails. The connection aborts before completing authentication.

**Fix:** Add `--skip-ssl` to the wpcli connection in `stack.sh` or configure MariaDB to accept SSL:
```bash
# In stack.sh stack_wp function:
dc run --rm --no-deps wpcli wp "$@" --allow-root --skip-ssl
```

**Symptom:** Four published blog posts contain placeholder content from the original WordPress installation:
- `/hello-world/` — default "Hello world!" post
- `/post-1/` — "Crafting Captivating Headlines: Your awesome post title goes here"
- `/post-2/` — "The Art of Drawing Readers In: Your attractive post title goes here"
- `/post-3/` — "Mastering the First Impression: Your intriguing post title goes here"

The Blog page (ID 300) is private, but the posts are published. If discovered via direct URL, they show nonsense content and waste SEO authority.

**Root cause:** The default WordPress sample content was never deleted when the site launched.

**Fix:** Delete the dummy posts:
```bash
stack_wp post delete $(stack_wp post list --post_type=post --format=ids --post__in=1,2,3,4)
```

### 69. 12 expired transients accumulating in database (cron not firing)

**Symptom:** 12 expired transient entries remain in `wp_options` because the `delete_expired_transients` cron hook hasn't run — WordPress cron has been stalled for ~10 days (bug 21). Transients accumulate in the options table, adding bloat and potentially causing stale data to be served if the transient timeout key is deleted but the data key remains.

**Root cause:** WordPress cron not firing. Without the scheduled cleanup, expired transients are never purged.

**Fix:** Trigger cron manually to clean expired transients, or run the cleanup directly:
```bash
stack_wp transient delete --all --expired
```
Also fix the underlying cron issue (bug 21).

### 70. Google Maps block on Contact page adds external dependency

**Symptom:** The Contact page includes a `uagb/google-map` block, which loads the Google Maps JavaScript API from Google's CDN. This adds another external third-party request on top of Google Fonts (Google), Cal.com, and Gravatar — 4+ external services on a single page load.

**Root cause:** The Google Maps embed block was added to the Contact page to show the business location, but it requires the Google Maps API which is a heavy external dependency.

**Fix:** Replace the interactive Google Maps block with a static map image or a simple linked address:
```html
<a href="https://www.google.com/maps?q=1002+W+Leland+Ave+Chicago+IL+60640" target="_blank">
  View on Google Maps →
</a>
```
