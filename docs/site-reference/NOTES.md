# Site reference — application guide

Hand-curated companion to the generated [`README.md`](README.md) index.
Read this before promoting changes across Willowy Hollow environments or writing to production.

**Cycle docs:** [`WILLOWYHOLLOW-SESSION-LOOP.md`](../WILLOWYHOLLOW-SESSION-LOOP.md) · [`WILLOWYHOLLOW-TLDR.md`](../WILLOWYHOLLOW-TLDR.md)

## Read when

| Task | Slice |
|------|-------|
| Comparing test results across practice / preview / staging2 / prod | [php-version-parity.md](php-version-parity.md) |
| After sync scripts or before trusting browser tests | [site-address-consistency.md](site-address-consistency.md) |
| Any write to staging2 or production | [backup-before-write-gate.md](backup-before-write-gate.md) |
| Regenerating the slice index | `bash scripts/refresh-site-reference.sh` |

## Pre-promote gate sequence

Run in order before git push to `willowyhollow-dev` staging or any production touch:

1. **Address** — `siteurl` / `home` match the environment you're on ([site-address-consistency.md](site-address-consistency.md))
2. **PHP** — major.minor matches source test env and target ([php-version-parity.md](php-version-parity.md))
3. **Backup** — fresh, verified, covers DB+files if needed ([backup-before-write-gate.md](backup-before-write-gate.md))

Any gate failure is **blocking** — not a warning. Fix or explicitly document the test as unverified.

## Gate registry

| Gate | Property | Mechanism | fail-open / fail-closed |
|------|----------|-----------|-------------------------|
| PHP version parity | test validity across envs | manual `php -v` / `PHP_VERSION` | fail-closed before promote |
| Site address consistency | environment identity | `wp option get siteurl/home` | fail-closed before trust tests |
| Backup-before-write | rollback safety | fresh backup + `gunzip -t` | fail-closed before prod write |
| `verify-site-reference.sh` | slices + index consistent | repo-only checks | fail-closed |

## Verify

```bash
cd ~/Projects/convmem
bash scripts/verify-site-reference.sh
```

Exit 0 = PASS or WARN only. Exit 1 = any FAIL.

## Deploy surfaces

```bash
bash scripts/deploy-site-reference.sh
bash scripts/smoke-site-reference-surfaces.sh   # deploy + validate Cursor/Kiro wiring
```

Copies:
- **User** Cursor rule (`~/.cursor/rules/site-reference.mdc`) — glob fallback when editing willowy paths from another workspace
- **Workspace** Cursor rules (`alwaysApply: true`) in `willowyhollow-practice`, `willowyhollow` (preview), `willowyhollow-dev`
- Kiro steering pointer

Slices stay in-repo — not Crush standing context.
