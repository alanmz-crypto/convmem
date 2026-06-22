# Cursor → all: step 6 shipped — --site filter

**To:** DeepSeek, Kiro, Ryan  
**From:** Cursor  
**Date:** 2026-06-22  

## Shipped

- `site_filter.py` — normalize + match on `metadata.site` / `source_path`
- `query_units(..., site=)` and `query_raw(..., site=)`
- `convmem search --site` and `convmem ask --site` (+ interactive banner)
- `tests/test_site_filter.py` (5 tests)

## Verify

```bash
convmem search "CSP" --site staging2.willowyhollow.com
```

— Cursor
