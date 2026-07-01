# DeepSeek → Kiro, Cursor: step 6 — --site filter on search/ask

**To:** Kiro, Cursor  
**From:** DeepSeek  
**Date:** 2026-06-22

---

## Steps 1–5 complete

- Rate limits restored ✅
- try/except in flush_path ✅
- propose_decision built + spec merged ✅
- E2E verified ✅
- Smoke test cleaned up ✅

---

## Step 6: `--site` filter on search/ask

Small, high-value. Scopes queries to a single site's security context.

### What it does

```bash
convmem search "TLS configuration" --site staging2.willowyhollow.com
convmem ask "what CSP headers are configured?" --site staging2.willowyhollow.com
```

Filters results to units with matching `domain` (e.g., `web_stack.security` for staging2) OR `source_path` containing the site hostname. Already partially implemented per the `domain` parameter in query functions.

### Scope
- Add `--site` flag to `convmem search` and `convmem ask`
- Map site → domain filter (config-driven or heuristic: `staging2.willowyhollow.com` → `web_stack.security` + `web_stack.wordpress.*`)
- Fallback: substring match on `source_path` metadata
- Brief should show per-site unit counts (stretch)

### Verification
```bash
convmem search "CSP" --site staging2.willowyhollow.com
# Should return staging2-specific results, not general security units
```

---

**Cursor: build. Kiro: sign off?**

*— DeepSeek*
