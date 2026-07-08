# Site-reference slices + Cursor surfaces — shipped 2026-07-06

**Lane:** convmem repo — Willowy Hollow cycle surface (parallel to `builder-reference` / `lab-reference`).

## Shipped

- `docs/site-reference/` — three slices (PHP parity, site address, backup-before-write) + `NOTES.md` + `README.md`
- Scripts: `verify-site-reference.sh`, `refresh-site-reference.sh`, `deploy-site-reference.sh`, `validate-site-reference-surfaces.sh`, `smoke-site-reference-surfaces.sh`
- Cycle wiring: `WILLOWYHOLLOW-SESSION-LOOP.md` step 4b, TLDR, WEBDEV-GUIDE, `MODEL-WORKFLOW.md`, `willowyhollow-practice/AGENTS.md`

## Surface fix (Cursor)

Initial deploy used user-level `~/.cursor/rules/site-reference.mdc` with `alwaysApply: false` and globs only — **does not load on workspace open**. Fixed by deploying workspace-local rules (`alwaysApply: true`) to:

- `~/WordPress/willowyhollow-practice/.cursor/rules/site-reference.mdc`
- `~/WordPress/willowyhollow/.cursor/rules/site-reference.mdc`
- `~/GitClones/willowyhollow-dev/.cursor/rules/site-reference.mdc`

User globs expanded to all three paths as fallback when editing from another workspace.

## Verify (2026-07-06)

```bash
bash scripts/smoke-site-reference-surfaces.sh   # PASS
bash scripts/verify-site-reference.sh          # PASS
```

- Workspace rules: `alwaysApply: true`, byte-match repo example — all three roots
- Glob simulation: practice, preview, willowyhollow-dev match; convmem negative does not
- Live gate probe on practice `:8081`: siteurl/home PASS; PHP 8.3 in container vs 8.5.8 host (parity slice correctly flags cross-env risk); latest production backup `gunzip -t` PASS
- Manual UI test (Ryan): first test **PASS** — rule visible in willowyhollow workspace

## Deploy habit

After slice edits:

```bash
cd ~/Projects/convmem
bash scripts/deploy-site-reference.sh
bash scripts/smoke-site-reference-surfaces.sh
```
