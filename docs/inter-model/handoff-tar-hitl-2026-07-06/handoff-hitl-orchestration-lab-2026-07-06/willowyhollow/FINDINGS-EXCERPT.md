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
