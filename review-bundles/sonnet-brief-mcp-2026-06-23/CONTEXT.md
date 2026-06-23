# Context

## User goal

New agents (no prior chat on a project) should:

1. See that a repo **exists in the index** and where files live
2. Find **past conversations** and **dive into files** (`AGENTS.md`, newest transcript path)
3. **Not** rely on Ryan manually relaying context

## Prior honest assessment (Cursor)

| Works | Weak |
|-------|------|
| Targeted `ask` / `search` | Vague "where did I leave off?" |
| `--site` for staging2 | No project row in brief |
| Ledger decisions + supersession | Inter-model markdown not in Chroma |
| CLI `propose_decision` | MCP had no `brief` |

## Sonnet critique (incorporated)

1. **Corpus-only brief is insufficient** — must include per-project/repo breakdown or `willowyhollow-dev` cold pickup still fails.
2. **"Writes are CLI-only" is a feature** — do not erode for agent convenience.
3. **Verify live after build** — local agents run MCP; cloud reviewers reason from `LIVE-RESULTS.md` + code.

## What was built

### `brief.py`

- `resolve_project_from_path(path)` → `(slug, repo_path)` from Cursor project dirs and `GitClones|Projects|WordPress` paths
- `gather_project_activity()` — rollup: indexed source count, newest source path/mtime, knowledge unit count, recent titles, `AGENTS.md` if present, suggested `entry_search`
- `gather_brief_payload()` — JSON for MCP + `coordination` block (`mcp_writes: false`, protocol ledger id)
- CLI markdown brief: new `## Projects (indexed activity)` section

### `mcp_server.py`

- New tool: `brief(project: str = "", with_tests: bool = False)`
- Updated MCP instructions: start with brief; read-only boundary stated

### Tests

- `tests/test_brief_projects.py` — slug extraction + filter
- `tests/test_mcp_site.py` — brief calls payload helper
- Full suite: 112 tests (local, pre-commit)

## Base commit

`main` @ `391c07a` (LATEST handoff) + **uncommitted** changes in `diff/brief-mcp-uncommitted.patch`

## Known limitations (acknowledged)

- Project slug is **heuristic** (path parsing), not a first-class `project:` ledger tag
- `newest_source_age` reflects **indexed sources**, not git commit date
- Site monitor (`staging2.willowyhollow.com`) does not roll up under `willowyhollow-dev` slug
- Exact "left off" still needs **CLI `propose_decision`** handoff by Ryan
