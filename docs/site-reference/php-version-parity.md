# Site-reference slice — PHP version parity

## Topic: PHP version mismatch between environments

**Use for:** deciding whether local/practice and production are safe to compare or promote between.

**Source:** Standard WordPress/PHP deployment practice — version drift is one of the most common causes of "works local, breaks prod."

### Decision procedure

- PHP version must match exactly (major.minor) between the environment a change was tested in and the one it ships to.
- A plugin/theme working locally on a newer PHP version can fail silently or fatally on an older prod version — deprecated functions, removed extensions, different default settings (e.g. error display).
- Check via `php -v` on both sides, or `phpinfo()` if shell access isn't available on prod.
- Mismatch found → do not treat local testing as validated for prod. Either match versions before testing, or explicitly flag the test as unverified for the target PHP version.

### Willowy Hollow hooks

| Environment | How to check |
|-------------|--------------|
| Practice `:8081` | `source scripts/stack.sh && stack_wp eval 'echo PHP_VERSION;'` |
| Preview `:8080` | `podman exec … php -v` (Podman stack) |
| staging2 / prod | SSH or hosting panel `php -v` |

Run before `sync-practice-to-preview.sh`, git push to `willowyhollow-dev` staging, or any prod write.
