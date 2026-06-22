# CONVMEM BRIEF

Generated: 2026-06-22T19:19:27Z

## State
- Corpus: **1089** units, **274** summaries
- Inventory: 127 indexed, 0 pending, 0 deferred
- Tests: unknown (run: convmem brief --with-tests)
- rerank: False
- Services: watch=enabled/active refine=enabled/active monitor.timer=enabled/active
- Kiro live DB excluded: **yes**
- MCP: cursor=registered crush=registered crush_live=2026-06-22T15:35:23Z
- MCP stdio: verified (Cursor dev machine 2026-06-22)

## Active P0
- (none — maintain watch journal for 24h)

## Recent Decisions
- **dec_convmem_workspace_standard**: Workspace standard is convention-only — documented in WORKSPACE-STANDARD.md, no…
  - Rationale: Without documentation, next new project repeats live-DB watch disasters (OOM, duplication, lock con…
- **dec_convmem_single_writer_chroma**: One machine owns the Chroma index; no sync between hosts
  - Rationale: Concurrent writes from two hosts corrupt the HNSW index silently. rsync between dev and miniPC was…
- **dec_convmem_no_auto_merge**: Queue semantic duplicate candidates for Kiro review; never auto-merge in v1
  - Rationale: Auto-merge is irreversible. False positives (units that look similar but represent different contex…
- **dec_convmem_rationale_in_document**: Append rationale to Chroma document text so LLM sees it in ask context
  - Rationale: Metadata-only storage is invisible to the retrieval and generation path. The ask prompt builds cont…
- **dec_convmem_monitor_never_supersede_kiro**: Monitor skips write if any existing verification has author_model or verifier_m…
  - Rationale: Automated low-confidence (0.4) checks must never overwrite a human-signed finding. Monitor pass is…

## Recent Monitor
- staging2.willowyhollow.com: TLS redirect re-check on staging2.willowyhollow.com: pass (monitor → obs_stagin… [pass]
- staging2.willowyhollow.com: Referrer-Policy still absent on staging2.willowyhollow.com (monitor re-check of… [fail]
- staging2.willowyhollow.com: X-Content-Type-Options present on staging2.willowyhollow.com (monitor re-check… [pass]

## Open Risks
- Watch OOM if live DBs indexed (Kiro sqlite, Cursor store.db) — both skipped in watch
- Re-enable watch only after 24h clean journal with per-chunk ingest + MemorySwapMax=0
- Crush MCP live path still unverified until `mcp_crush_verified` flag set
- Handoff doc sprawl — prefer brief + `docs/inter-model/`

## Before Working
- Read newest files in `docs/inter-model/`
- Agent roles: `docs/AGENT-ROLES.md`
- Use `convmem search` / MCP `search_fast` for targeted prior art
- Treat proposals as pending until human/Kiro approval

## Inter-Model Inbox
- `/home/lauer/Projects/convmem/docs/inter-model/`

