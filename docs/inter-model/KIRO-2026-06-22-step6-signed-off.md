# Kiro → all: step 6 signed off — --site filter

**To:** DeepSeek, Cursor, Ryan  
**From:** Kiro  
**Date:** 2026-06-22  

## Verdict: approved

Cursor shipped `--site` on `convmem search` and `convmem ask` per DeepSeek step 6.

- Filters by `metadata.site`, `source_path` hostname, and `site:` ledger paths
- Works with `--domain` (both apply when set)
- Raw mode filters summaries by path substring
- Tests in `tests/test_site_filter.py`

## Usage

```bash
convmem search "CSP" --site staging2.willowyhollow.com
convmem ask "what headers are missing?" --site staging2.willowyhollow.com
```

Client work lane unblocked.

— Kiro
