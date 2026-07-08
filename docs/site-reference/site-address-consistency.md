# Site-reference slice — Site address consistency

## Topic: URL/address mismatch between environments (siteurl, home, serialized data)

**Use for:** verifying an environment's identity before trusting any test result or promoting a change.

**Source:** Standard WordPress migration practice — serialized data corruption from naive URL replacement is a well-known failure mode.

### Decision procedure

- Check `siteurl` and `home` in `wp_options` match the environment you're actually on — a common failure is a practice/staging copy still pointing at the production URL, or vice versa.
- URLs are not only in `wp_options` — theme/plugin settings, widget content, and post content can contain serialized arrays with hardcoded URLs. A naive find-replace on these will corrupt the data structure.
- Use a serialization-safe search-replace tool (e.g. WP-CLI `search-replace`), never a plain text find-replace, when migrating URLs between environments.
- If address mismatch is found: stop. Do not trust any test performed on that environment until corrected — it may be silently reading or writing against the wrong URL.

### Willowy Hollow hooks

| Environment | Expected `siteurl` / `home` |
|-------------|----------------------------|
| Practice | `http://localhost:8081` |
| Preview | `http://localhost:8080` |
| staging2 | `https://staging2.willowyhollow.com` |
| Production | `https://willowyhollow.com` |

```bash
# Practice
source scripts/stack.sh && stack_wp option get siteurl && stack_wp option get home
```

Sync scripts (`sync-staging2-to-practice.sh`, `sync-practice-to-preview.sh`) run URL rewrites — re-verify after any sync before trusting browser tests.
