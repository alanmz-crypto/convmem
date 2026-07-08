# 2026-07-07 Root AGENTS.md created

Created `/home/lauer/WordPress/AGENTS.md` — the workspace root has no git repo, no `.gitignore`, and no agent onboarding guide. Agents had to discover each subdirectory's AGENTS.md individually; there was no cross-project map.

## What was done

- Surveyed all 6 subdirectories (`willowyhollow/`, `willowyhollow-practice/`, `pavlomassage/`, `pavlomassage-practice/`, `scripts/`, `thaisolude/`, `htdocs/`)
- Read existing AGENTS.md files from every site, docker-compose files, stack.sh scripts, and a representative sync script (`push-practice-to-staging2.sh`, `sync-practice-to-preview.sh`, `session-hint.sh`)
- Identified the two-container-engine architecture (Podman for preview, Docker for practice) with port conflicts
- Mapped all 4 active stacks + thaisolude (inactive)
- Documented the shared patterns: stack lifecycle, DB sync pipeline, wp-config-local.php, collation fix, WPCode cache rebuild
- Documented 10 cross-cutting gotchas
- Cross-referenced convmem session tracking commands and key reference docs
- Listed shell aliases and related Git repos

## Files touched

- `~/WordPress/AGENTS.md` — new file, 156 lines
