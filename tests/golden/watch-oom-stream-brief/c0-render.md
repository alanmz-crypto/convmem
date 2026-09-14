# CONVMEM BRIEF

Generated: 2026-09-13T12:00:00Z

## State
- Corpus: **21** units, **2** summaries
- Inventory: 1 indexed, 0 pending, 0 deferred
- Tests: unknown (run: convmem brief --with-tests)
- rerank: False
- Services: watch=enabled/active refine=enabled/active monitor.timer=enabled/active
- Kiro live DB excluded: **no**
- MCP: cursor=registered crush=registered crush_live=verified
- MCP stdio: verified
- LATEST.md: updated **just now** (2026-09-13, Cursor)
- Recent inter-model: CURSOR-2026-09-13-watch-oom-stream-brief-metadata-execute-handoff.md
- Unresolved observations: **4** (run `convmem unresolved`)
- brief @ `2026-09-13T12:00:00Z`

## Projects (indexed activity)
- **convmem** — 1 sources, 21 units, last activity 1h ago
  - newest: `TMP/Projects/convmem/session.jsonl`
  - try: `search_fast("convmem handoff next steps")`

## Active P0
- (none)

## Recent Decisions
- **dec_prop_superseded**: Superseded newest decision
  - Rationale: tombstone still listed by current brief scan
- **dec_prop_second**: Second newest decision
  - Rationale: keep second
- **dec_prop_equal_a**: Equal-ts decision A
  - Rationale: tie-break A
- **dec_prop_equal_b**: Equal-ts decision B
  - Rationale: tie-break B
- **dec_prop_fifth**: Fifth decision
  - Rationale: keep fifth

## Recent Monitor
- staging.example: Newest monitor hit [pass]
- staging.example: Mid monitor hit [fail]
- staging.example: Third monitor hit [pass]

## Open Risks
- Watch OOM if live DBs indexed (Kiro sqlite, Cursor store.db) — both skipped in watch
- Watch RSS high (~3–4G) — little headroom under MemoryMax=4G
- Crush MCP live path still unverified until `mcp_crush_verified` flag set

## Before Working
- Protocol: `brief` → `convmem ask` → `LATEST.md` → `convmem record -i` → `convmem record --approve-last`
- Session close: `SESSION-CLOSE-RECORD.md` — `convmem record --relates-to … --summary … --rationale … --author …`; then `--approve-last`; never `record` alone or fake flags
- Agent roles: `docs/AGENT-ROLES.md`
- Use `convmem search` / MCP `search_fast` for targeted prior art
- Drafts are not searchable until `record --approve-last`

## Inter-Model Inbox
- `REPO/docs/inter-model/`
