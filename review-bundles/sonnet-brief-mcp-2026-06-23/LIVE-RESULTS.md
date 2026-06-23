# Local verification (already run on Ryan's machine)

Cloud reviewers: **do not assume you can reproduce**. Challenge logically if results seem inconsistent with code.

## Tests

```
python -m unittest discover -s tests -q
→ Ran 112 tests in 1.390s — OK
```

## `gather_brief_payload(project="willowyhollow-dev")`

```json
{
  "slug": "willowyhollow-dev",
  "repo_path": "/home/lauer/GitClones/willowyhollow-dev",
  "agents_md": "/home/lauer/GitClones/willowyhollow-dev/AGENTS.md",
  "indexed_sources": 5,
  "knowledge_units": 53,
  "newest_source_at": "2026-06-01T16:09:44Z",
  "newest_source_age": "22d ago",
  "newest_source_path": "/home/lauer/.cursor/projects/home-lauer-GitClones-willowyhollow-dev/agent-transcripts/5999742f-1ad4-4f2e-948d-482577e853ae/5999742f-1ad4-4f2e-948d-482577e853ae.jsonl",
  "formats": ["aider_markdown", "jsonl_cursor", "sqlite_crush"],
  "recent_unit_titles": [
    "Verify origin remote URL",
    "Setup Template",
    "Understand the importance of .gitignore"
  ],
  "entry_search": "willowyhollow-dev handoff next steps"
}
```

`coordination.mcp_writes`: **false**

## Git context

- Repo: `github.com/alanmz-crypto/convmem`
- `main` synced through `391c07a`; brief MCP changes **not yet committed** (included in this bundle)

## Payoff tests (earlier session, same machine)

| Test | Result |
|------|--------|
| `ask` CSP `--site staging2` after supersession fix | Pass — cites `a66c`, not nginx `d1ba` |
| `ask` coordination protocol `--domain coding.tooling` | Pass — cites `c311` step list |
| Vague `ask` "where left off willowyhollow-dev" without project brief | Fail / thin |

## MCP status

- `brief` tool added to `mcp_server.py` — **requires MCP client restart** to appear
- Crush MCP live verify: not run (Ryan does not use Crush MCP regularly)
