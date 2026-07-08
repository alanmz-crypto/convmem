# 2026-07-06 — Bug triage: prioritized fix plan

Source: `logs/2026-07-05-code-review-findings.md` (84 findings), audited by Codex.
This plan organizes findings into tiers by impact and dependency. Practice only — not live.

---

## Tier 0 — Dead code & orphan data (15 min, zero risk)

Practice-only cleanup. Shrinks DB from ~1,081 tables to ~110, frees ~50MB disk.

| Finding | What |
|---------|------|
| #49 | Delete stale `wpcode-view-transitions.css`/`.js` from repo (disconnected from live system) |
| #36 | Remove 4 unused dark blob SVGs from uploads |
| #47 | Clear `ast-block-templates-json/` + `astra-sites/` cache (20MB) |
| #48 | Clear stale `siteground-optimizer-assets/` |
| #51 | Uninstall inactive Google Site Kit + HSTS plugin (27MB dead code) |
| #59 | Remove dead `php.ini` from web root (not loaded by PHP, exposed via HTTP) |
| #60 | `docker rm` stale wpcli container (5 days Exited) |
| #75 | Delete duplicate nav menu post ID 533 |
| #77 | Strip RSSSL leftovers from `wp-config.php` |
| #20 | Delete orphan cron hooks: updraftplus, prli, prettylink |
| #46 | Drop orphan plugin tables (~130: Amelia 57, Latepoint 39, Wordfence 18+, Fluent Forms 7, Pretty Link 3, WPvivid 3) |
| #53 | Delete `amelia_settings` option (serialized staging2 URLs) |

---

## Tier 1 — Install scripts (root cause of broken VT)

Every install script hardcodes home page ID 296 (zombie `Home-obs` page).
VT morphs and link re-pointing silently target wrong page. Must fix before any VT work.

| Finding | What |
|---------|------|
| **#14 CRITICAL** | Replace hardcoded `$home_id = 296` with `get_option('page_on_front')` in 5 scripts |
| #8 | Remove stale `functions.php` snapshot from `install-vt-card.php` (has old block IDs) |
| #9 | Fix broken links in `install-service-cards-html.php`: `/deep-tissue` → `/therapeutic-bodywork/`, `/relaxation` → `/relaxation-massage/` |
| #10 | Add `ABSPATH` guard to `install-service-cards-html.php` |
| #12 | Fix conflicting link re-pointing: `install-vt-card.php` reverts to `/services/` while `install-vt-nav.php` points to `/therapeutic-bodywork/` |
| #11 | Remove empty flip-card back face on Thai Massage card (or add content) |
| #15 | Add missing `;` after `z-index: 1` in flip-card CSS (back face stacks behind front) |

---

## Tier 2 — VT engine bugs (direct UX impact)

| Finding | What |
|---------|------|
| #2 | Fix back-nav animation direction: `translateY(-14px)` → `translateY(14px)` so page rises from below |
| #5 | Replace page-ID selectors (`body.page-id-298`) with page-slug selectors (`body.page-slug-about`) |
| #6 | Remove block-ID fallback selectors — use `.vt-*` classes only (prevents silent VT collisions) |
| #7 | Add `isolation: isolate` to blob containers to create stacking context |
| #3 | Scope line-art inversion to `.line-art` class only (not all images on About/Services/Contact) |
| #4 | Remove `!important` width/height overrides on services page images |
| #13 | Wrap page-reveal animation in `@supports not (view-transition-name: none)` to prevent double-fade on Chromium |

---

## Tier 3 — Practice environment (make dev correct)

| Finding | What |
|---------|------|
| #19 / #72 | Enable `WP_DEBUG` + `WP_DEBUG_LOG` in `wp-config-local.php` |
| #76 | Set `WP_ENVIRONMENT_TYPE` to `'local'` (currently `'staging'` from SiteGround) |
| #28 / #78 | Fix site URL redirect loop: internal container on port 80 vs host on 8081 |
| #21 | Set up host-side cron trigger for `wp-cron.php` (stalled ~10 days) |
| #61 | Add `mem_limit: 512m` to Docker services in `docker-compose.yml` |
| #84 | Add `--skip-ssl` to wpcli connection in `stack.sh` (MariaDB SSL not available) |

---

## Tier 4 — Content fixes (branding, accessibility, SEO)

| Finding | What |
|---------|------|
| #62 | "Thai Solitude" → "Willowy Hollow" in Contact page H1 |
| #58 | Tagline: "A spa and therapy" → "Therapeutic massage for your wellbeing" |
| #54 | Logo alt text: "comfyui 01114" → "Willowy Hollow" |
| #27 | Fix ComfyUI filenames as alt text on 12-15 images used on live pages |
| #43 | Add missing alt attributes on 2 images (WCAG fail) |
| #23 | Fix empty `aria-label=""` on 3 "Learn More" buttons (overrides visible text for screen readers) |
| #24 | Fix H1→H3 heading skip on services page (change H3 cards to H2) |
| #25 | Fix duplicate H1 on Therapeutic Bodywork page |
| #26 | Fix malformed Google Fonts URL: `400,,600` double comma |
| #41 | Fix schema.org JSON-LD founder name "alan" → "Sa Rai" |
| #42 | Obfuscate email address in footer (HTML entity encoding) |
| #44 | Fix hardcoded copyright year (use `date('Y')`) |
| #55 | Either embed unused SureForms booking form (ID 624) or delete it |
| #56 | Disable comments/pingbacks globally (`default_comment_status` → closed) |
| #30 | Fix duplicate viewport meta tag |
| #65 | Remove duplicate Cal.com embed injection (header AND footer AND WPCode snippet) |

---

## Tier 5 — Performance & optimization

| Finding | What |
|---------|------|
| #38 / #66 | Enable UAGB conditional asset loading (`uag_enable_block_condition`) |
| #39 | Remove jQuery Migrate (deprecated API shim) |
| #67 | Enable local Google Fonts hosting (`uag_load_gfonts_locally`) |
| #54 | Disable Gravatar (`show_avatars = 0`) |

---

## Tier 6 — Security headers (for staging2 sync)

| Finding | What |
|---------|------|
| #79 | Install or delete CSP WPCode snippet scripts |
| #80 | Add `X-Frame-Options: SAMEORIGIN` header |
| #81 | Add `Referrer-Policy: strict-origin-when-cross-origin` header |
| #29 | Fix protocol-relative URLs (`//cal.com` → `https://cal.com`) |
| #33 | Disable XML-RPC (brute force vector) |
| #34 | Remove `readme.html` from web root (version disclosure) |
| #35 | Restrict REST API user enumeration on `/wp/v2/users/` |
| #31 | Fix `robots.txt` Disallow (keep on practice, allow on staging2) |
| #40 | Make `noindex, nofollow` conditional per environment |
| #57 | Make `blog_public` conditional per environment (0 on practice, 1 on staging2) |

---

## Tier 7 — Sync script safety

| Finding | What |
|---------|------|
| #17 | Fix `restore-from-backup.sh` defaulting to May 31 backup — require explicit argument |
| #18 | Fix `push-practice-to-staging2.sh` backup order (backup staging2 BEFORE overwriting files) |
| #50 | Exclude install scripts from web root in rsync excludes |

---

## Tier 8 — Content consistency

| Finding | What |
|---------|------|
| #52 | Unify service page templates (all three currently use different layouts) |
| #56 | Migrate Thai Massage page from inline VT naming to `.vt-*` class convention |
| #82 | Fix `WP_CACHE` conflict: wp-config.php says true, wp-config-local.php says false |

---

## Tier 9 — Deferred / accepted limitations

| Finding | What |
|---------|------|
| #45 | Drop 6 abandoned WordPress installations from DB (stag02stag04WH, staging03, tmp502ff4, wp1737ed, wp7f1f5b, wpcf8a57) |
| #83 | Fix mixed database collations (utf8mb4 vs utf8mb3) — only if Wordfence reinstalled |
| #55 | Cal.com booking embed — accepted limitation (localhost not reachable from internet) |
| #63 | 404 page returns connection failure instead of 404 template |
| #64 | Empty search results has no `<title>` or "no results" message |
| #71 | RSS feed broken (container can't reach self on port 8081) |
| #22 | HSTS plugin inactive — staging2 concern, not practice |
| #73 | Nav menu locations — **audit says this finding is inaccurate** (`nav_menu_locations` is `false` in live DB) |
| #69 | Expired transients — **audit says count is 2, not 12** (log needs correction) |

---

## Audit corrections needed

Two findings had inaccurate claims vs live DB state:

- **#69**: Log says 12 expired transients accumulating. Live count: **2**.
- **#73**: Log says all three nav locations point to same menu. Live state: `nav_menu_locations` is **`false`**.

---

## Execution order

1. **Tier 0** → removes noise, frees resources
2. **Tier 1** → unblocks the VT system (fixes install scripts)
3. **Tier 2** → fixes VT behavior (CSS/JS bugs)
4. **Tiers 3–9** → independent polish, any order

Start with Tier 0.
