# ConvMem Local State Snapshot

Generated: 2026-08-10T11:23:37-05:00
Machine: archlinux

## convmem doctor

```
[PASS] config: /home/lauer/.config/convmem/config.toml readable
[PASS] write_lane: lane=prod workspace=prod config=config.toml write_guard=OK
[PASS] hooks_path: hooksPath=scripts/git-hooks (pre-push+pre-commit ok)
[PASS] wip_on_main: main: 0 WIP commits in last 50
[PASS] dirty_main: main clean (tracked)
[SKIP] unpushed_commits: skip on main
[PASS] deepseek_key: DEEPSEEK_API_KEY set
[PASS] ollama: http://localhost:11434 OK (33 models; e.g. ['laguna-xs-2.1:latest', 'ornith:9b'])
[PASS] chroma: 19701 knowledge units, 2451 summaries
[PASS] index_drift: Chroma 19701 active; JSONL 31488 historical ids (31554 lines; 19343 overlap, 98% active coverage; 12145 historical-only, 358 active-only)
[WARN] embed_collection_identity: WARN: legacy collection metadata lacks convmem:embed_model (configured='nomic-embed-text'; shadow stores must set metadata)
[PASS] shadow_ledger: disabled (no sink injection; Phase 0 default)
[PASS] restic_gate: complete-data-v2 snapshot covers today (id=5e9a7e1162ee2d2a3b904893736521526bae0ff348143f2d8b2799f8e4e8d836 tag=convmem-data-v2)
[PASS] restic_external: offsite copy covers today (source=5e9a7e1162ee2d2a3b904893736521526bae0ff348143f2d8b2799f8e4e8d836 destination=ed8d546f3737cb92940817ad2aa313967a64916ede525c9e2608fe28d44340fd)
[PASS] restic_password_backup: offline password copy present and matches (/run/media/lauer/BIT-Brg-larch-7t/convmem-secrets/restic.password)
[PASS] synthesis_gate: 0 ask failures, 512 ingest-degraded in 7d (provider drops; projection completeness unproven until reconciled)
[PASS] index_gate: 0 index failures in 7d
[PASS] standing_register: 13 open checks, 0 due (2 charter-standing)
[PASS] planning_guide_contract: contract v2: 5 guide(s) ok
[PASS] ledger_documents: 0 empty decision/verification docs (361 scanned)
[PASS] mcp_import: mcp_server tools importable
[PASS] mcp_cursor: ~/.cursor/mcp.json has convmem
[PASS] mcp_continue: Continue MCP wiring present
[PASS] mcp_copilot: ~/.copilot/mcp-config.json has convmem
[PASS] verify_continue: verify-continue.sh present (use --verify to run)

doctor: all checks passed
  (1 warning(s) — non-fatal)
  (1 skipped — expected for cross-lane workspace)

── Next steps ──
  • convmem tldr  # one-page cheat sheet
  • convmem brief --stdout-only
  • convmem unresolved  # add --site <host> for client work
  • convmem "your topic"  # search before ask
  • convmem doctor --v1  # watch RSS, digest timer, locks
```

## convmem brief

```
# CONVMEM BRIEF

Generated: 2026-08-10T16:23:45Z

## State
- Corpus: **19701** units, **2451** summaries
- Inventory: 1289 indexed, 0 pending, 0 deferred
- Tests: unknown (run: convmem brief --with-tests)
- rerank: False
- Services: watch=unknown refine=unknown monitor.timer=unknown
- Kiro live DB excluded: **no**
- MCP: cursor=registered crush=registered crush_live=2026-06-22T15:35:23Z
- MCP stdio: verified (Cursor dev machine 2026-06-22)
- LATEST.md: updated **1d ago** (2026-08-09) **(stale)**
- Recent inter-model: BUILT-PLANS-2026-06-24-to-2026-06-29.md, WILLOWYHOLLOW-BUG-TRIAGE-2026-07-06.md, FLASH-2026-08-08-post-rebuild-verify-handoff.md
- Unresolved observations: **4** (run `convmem unresolved`)
- **⚠ STALE HANDOFF:** `LATEST.md` is older than `BUILT-PLANS-2026-06-24-to-2026-06-29.md` (newest 35m ago) — read newest file or update LATEST
- brief @ `2026-08-10T16:23:45Z`

## Projects (indexed activity)
- **convmem** — 85 sources, 4782 units, last activity 13h ago
  - repo: `/home/lauer/Projects/convmem`
  - agents: `/home/lauer/Projects/convmem/AGENTS.md`
  - newest: `/home/lauer/Projects/convmem/.crush/crush.db`
  - try: `search_fast("convmem handoff next steps")`
- **local_share_convmem_worktrees_fix_2026_07_24_crush_bash_index_freeze** — 1 sources, 5 units, last activity 16d ago
  - newest: `/home/lauer/.cursor/projects/home-lauer-local-share-convmem-worktrees-fix-2026-07-24-crus…`
  - try: `search_fast("local_share_convmem_worktrees_fix_2026_07_24_crush_bash_index_freeze handoff next steps")`
- **worldmonitor** — 1 sources, 0 units, last activity 18d ago
  - repo: `/home/lauer/GitClones/worldmonitor`
  - agents: `/home/lauer/GitClones/worldmonitor/AGENTS.md`
  - newest: `/home/lauer/GitClones/worldmonitor/.crush/crush.db`
  - try: `search_fast("worldmonitor handoff next steps")`
- **willowyhollow-practice** — 101 sources, 1704 units, last activity 18d ago
  - repo: `/home/lauer/WordPress/willowyhollow-practice`
  - agents: `/home/lauer/WordPress/willowyhollow-practice/AGENTS.md`
  - newest: `/home/lauer/WordPress/willowyhollow-practice/.crush/crush.db`
  - try: `search_fast("willowyhollow-practice handoff next steps")`
- **local_share_convmem_worktrees_docs_2026_07_21_2026_07_21_deepseek_v4pro_audit_substitute** — 2 sources, 110 units, last activity 18d ago
  - newest: `/home/lauer/.cursor/projects/home-lauer-local-share-convmem-worktrees-docs-2026-07-21-202…`
  - try: `search_fast("local_share_convmem_worktrees_docs_2026_07_21_2026_07_21_deepseek_v4pro_audit_substitute handoff next steps")`
- **convmem-fix-ask-trace** — 1 sources, 31 units, last activity 19d ago
  - repo: `/home/lauer/Projects/convmem-fix-ask-trace`
  - agents: `/home/lauer/Projects/convmem-fix-ask-trace/AGENTS.md`
  - newest: `/home/lauer/.cursor/projects/home-lauer-Projects-convmem-fix-ask-trace/agent-transcripts/…`
  - try: `search_fast("convmem-fix-ask-trace handoff next steps")`
- **convmem-worktrees-pr52-r2a-closeout** — 7 sources, 120 units, last activity 19d ago
  - repo: `/home/lauer/Projects/convmem-worktrees-pr52-r2a-closeout`
  - newest: `/home/lauer/.cursor/projects/home-lauer-Projects-convmem-worktrees-pr52-r2a-closeout/agen…`
  - try: `search_fast("convmem-worktrees-pr52-r2a-closeout handoff next steps")`
- **willowyhollow-dev** — 8 sources, 100 units, last activity 19d ago
  - repo: `/home/lauer/GitClones/willowyhollow-dev`
  - agents: `/home/lauer/GitClones/willowyhollow-dev/AGENTS.md`
  - newest: `/home/lauer/.cursor/projects/home-lauer-GitClones-willowyhollow-dev/agent-transcripts/a3c…`
  - try: `search_fast("willowyhollow-dev handoff next steps")`

## Active P0
1. Update LATEST.md or read `BUILT-PLANS-2026-06-24-to-2026-06-29.md` before cross-model handoff

## Recent Decisions
- **dec_prop_20260808_150112_f49e**: Ryan Execution HITL: JudgeBench execution plan + Flash S1-S9 implementation aut…
  - Rationale: Architecture lock granted; Flash slice brief (EXECUTION-judgebench-flash-slices.md) scopes S1-S9 pr…
- **dec_prop_20260808_150053_5d61**: Ryan Architecture HITL lock: JudgeBench offline semantic calibration architectu…
  - Rationale: Both required AI reviewers (Kiro, ChatGPT) PASSed the ARCHITECTURE-judgebench.md tip; DeepSeek's tr…
- **dec_prop_20260707_184401_44e8**: convmem repo bug sprint closed; convmem index hangs on pending Crush DBs
  - Rationale: Bug sprint complete (Bugs 1-4 fixed, 5 analyzed, 6 verified correct). User attempted convmem index…
- **dec_prop_20260715_223237_c9d4**: Continue MCP verify: P0 retrieval fix sequence complete — Kiro snapshot filter,…
  - Rationale: P0a: adapters/inter_model_doc.py _EXCLUDE_PATH_TOKENS frozenset. P0b: 646  snapshot inter_model_doc…
- **dec_prop_20260722_013340_dc60**: P1.3 source-trust ranking plan approved and handed to Codex; execution + handof…
  - Rationale: Closes the ksweep-class ranking failure by preferring kiro_steering/ledger/inter-model over chat af…

## Recent Monitor
- staging2.willowyhollow.com: Referrer-Policy still absent on staging2.willowyhollow.com (monitor re-check of obs_staging2_monito… [fail]
- staging2.willowyhollow.com: Content-Security-Policy still absent on staging2.willowyhollow.com (monitor re-… [fail]
- staging2.willowyhollow.com: Referrer-Policy absent or failed on staging2.willowyhollow.com (convmem-monitor probe referrer-poli…

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
- `/home/lauer/Projects/convmem/docs/inter-model/`


── Next steps ──
  • Update docs/inter-model/LATEST.md or read the newest inter-model file
  • convmem unresolved  # 4 open
  • convmem "your question"  # or: convmem ask "…"
  • convmem record -i  # after a durable win (you: record --approve-last)
```

## convmem unresolved

```
4 unresolved observation(s):

LEDGER ID                                    SEVERITY  SITE                        DOMAIN              STATUS               LAST TOUCHED  TITLE                                                       
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
obs_staging2_monitor_csp-missing             medium    staging2.willowyhollow.com  web_stack.security  failed_check         2026-07-12    Content-Security-Policy absent or failed on staging2.willow…
obs_staging2_monitor_header-referrer-policy  medium    staging2.willowyhollow.com  web_stack.security  failed_check         2026-07-12    Referrer-Policy absent or failed on staging2.willowyhollow.…
ver_staging2_mon_csp                         medium    staging2.willowyhollow.com  web_stack.security  failed_verification  2026-07-12    Content-Security-Policy still absent on staging2.willowyhol…
ver_staging2_mon_referrer-policy             medium    staging2.willowyhollow.com  web_stack.security  failed_verification  2026-07-12    Referrer-Policy still absent on staging2.willowyhollow.com …

── Next steps ──
  • convmem ask "How do we fix these?" --site staging2.willowyhollow.com
  • convmem "staging2.willowyhollow.com CSP SiteGround"
```

## Git status (main checkout)

```
## main...origin/main
?? .kiro/settings/
?? chatgpt-snapshot-2026-08-10.md
?? complete-data-restore-reports/
?? docs/inter-model/C5-ACTIVATION-HANDOFF-2026-07-29.md
?? docs/inter-model/CODEX-2026-08-02-summarizer-switch-decision.md
?? docs/inter-model/CRUSH-2026-08-02-summarizer-bakeoff-chroma-assessment.md
?? docs/inter-model/CRUSH-2026-08-07-session-handoff-gpu-fix.md
?? docs/inter-model/CRUSH-2026-08-08-index-complete-judgebench-unblock.md
?? docs/inter-model/PYLINT-BRIEF-FOR-QWEN-2026-07-25.md
?? docs/plans/TEMPLATE-flash-slice-brief.md
?? piped
?? pylint-report.json
?? scripts/export-chatgpt-snapshot.sh
```

## Worktrees

```
/home/lauer/Projects/convmem                                                                             0be0a05 [main]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-14-background-synthesis-status-reconcile         3d55f51 [docs/2026-07-14-background-synthesis-status-reconcile]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-14-claude-exclude-purge-postmerge                8edd4fa [docs/2026-07-14-claude-exclude-purge-postmerge]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-14-exclude-purge-verification-status             ccc926e [docs/2026-07-14-exclude-purge-verification-status]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-15-2026-07-15-purge-correction-trail             d58e623 [docs/2026-07-15-purge-correction-trail]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-15-codex-top-two-retrieval-plans                 894cf3b [docs/2026-07-15-codex-top-two-retrieval-plans]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-15-consolidation-volatile-status                 243562e [docs/2026-07-15-consolidation-volatile-status]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-15-debate-insight-folder                         c29b449 [docs/2026-07-15-debate-insight-folder]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-19-2026-07-19-latest-stage4-task1                fb4c874 [docs/2026-07-19-2026-07-19-latest-stage4-task1]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-19-2026-07-19-synthesis-plan-pointer             61ac61c [docs/2026-07-19-2026-07-19-synthesis-plan-pointer]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-19-refresh-latest-md                             6284673 [docs/2026-07-19-refresh-latest-md]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-21-2026-07-21-context-brief-rule                 b1a6464 [docs/2026-07-21-2026-07-21-context-brief-rule]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-21-2026-07-21-deepseek-v4pro-audit-substitute    c1aa8ec [docs/2026-07-21-2026-07-21-deepseek-v4pro-audit-substitute]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-21-latest-handoff-refresh                        0af6ff6 [docs/2026-07-21-latest-handoff-refresh]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-21-pr-steward-role                               9be13c5 [docs/2026-07-21-pr-steward-role]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-22-land-who-fixes-debate-folder                  52b338b [docs/2026-07-22-land-who-fixes-debate-folder]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-22-latest-dedupe-hygiene-gate                    5100257 [docs/2026-07-22-latest-dedupe-hygiene-gate]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-22-latest-drop-pr36-leftover                     2c5684f [docs/2026-07-22-latest-drop-pr36-leftover]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-22-retrieval-reliability-v7-close                b939412 [docs/2026-07-22-retrieval-reliability-v7-close]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-22-retrieval-reliability-v7-recovered            3e3831c [docs/2026-07-22-retrieval-reliability-v7-recovered]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-30-c7-c6-standing-check-readiness                03a2297 [docs/2026-07-30-c7-c6-standing-check-readiness]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-30-proactive-pr-description                      5f8be83 [docs/2026-07-30-proactive-pr-description]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-30-shadow-phase0-c6-event-size-policy-decision   4eb5aa7 [docs/2026-07-30-shadow-phase0-c6-event-size-policy-decision]
/home/lauer/.local/share/convmem/worktrees/docs-2026-07-30-shadow-phase0-c7-operational-handoffs         5962306 [docs/2026-07-30-shadow-phase0-c7-operational-handoffs]
/home/lauer/.local/share/convmem/worktrees/docs-2026-08-09-2026-08-09-judgebench-status-awareness        fbbbd33 [docs/2026-08-09-2026-08-09-judgebench-status-awareness]
/home/lauer/.local/share/convmem/worktrees/docs-2026-08-09-complete-data-status-brief                    475fe43 [docs/2026-08-09-complete-data-status-brief]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-12-conflict-detection-arc-verify                 1faf3f8 [feat/2026-07-12-conflict-detection-claude-review]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-12-gate5-hashless-graduation                     f9a3927 [feat/2026-07-12-gate5-hashless-graduation]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-14-exclude-source-purge                          72aeec8 [feat/2026-07-14-exclude-source-purge]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-15-claude-branch-only-access                     fb43050 [feat/2026-07-15-claude-branch-only-access]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-15-doctor-purge-drift                            fb43050 [feat/2026-07-15-doctor-purge-drift]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-19-2026-07-19-collection-count-smoke             6ae655e [feat/2026-07-19-2026-07-19-collection-count-smoke]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-19-retrieval-reliability                         61bb552 [feat/2026-07-19-retrieval-reliability]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-22-ingest-dedupe-queue-pause                     643e8c3 [feat/2026-07-22-ingest-dedupe-queue-pause]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-29-planning-os-verification-methodology          7843d75 [feat/2026-07-29-planning-os-verification-methodology]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-29-shadow-phase0-c6-canary-evidence              3668100 [feat/2026-07-29-shadow-phase0-c6-canary-evidence]
/home/lauer/.local/share/convmem/worktrees/feat-2026-07-30-shadow-phase0-c7-writer-census                50504ef [feat/2026-07-30-shadow-phase0-c7-writer-census]
/home/lauer/.local/share/convmem/worktrees/feat-2026-08-07-synthesis-calibration-expansion               ab5e8ce [feat/2026-08-07-synthesis-calibration-expansion]
/home/lauer/.local/share/convmem/worktrees/feat-2026-08-09-2026-08-09-judgebench-g3-corpus               d87ff7e [feat/2026-08-09-2026-08-09-judgebench-g3-corpus]
/home/lauer/.local/share/convmem/worktrees/feat-2026-08-09-judgebench-calibration-prep                   200a2f4 [feat/2026-08-09-judgebench-calibration-prep]
/home/lauer/.local/share/convmem/worktrees/feat-2026-08-10-judgebench-live-driver                        f80fbcd [feat/2026-08-10-judgebench-live-driver]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-14-processed-json-exclude-race                    482f533 [fix/2026-07-14-processed-json-exclude-race]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-14-pylint-regression-gate                         f57a83f [fix/2026-07-14-pylint-regression-gate]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-15-2026-07-15-ask-trace-nested-inter-model        fb43050 [fix/2026-07-15-ask-trace-nested-inter-model]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-19-doctor-render-smoke                            6c2ce2b [fix/2026-07-19-doctor-render-smoke]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-19-index-history-diagnostic                       7e0a168 [fix/2026-07-19-index-history-diagnostic]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-21-2026-07-21-response-tldr-minimal               e4e74a5 [fix/2026-07-21-2026-07-21-response-tldr-minimal]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-22-2026-07-22-mcp-roots-boundary                  30a24b4 [fix/2026-07-22-mcp-roots-boundary]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-22-golden-eval-soak-arch                          f06dc03 [fix/2026-07-22-golden-eval-soak-arch]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-24-crush-bash-index-freeze                        a79b63a [fix/2026-07-24-crush-bash-index-freeze]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-27-complete-data-backup-correction-v2             a3b56c8 [fix/2026-07-27-complete-data-backup-correction-v2]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-28-shadow-phase0-c1-strict-validation             ed230c3 [fix/2026-07-28-shadow-phase0-c1-strict-validation]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-28-shadow-phase0-c2-secure-append                 f02f724 [fix/2026-07-28-shadow-phase0-c2-secure-append]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-29-shadow-phase0-c4-truth-reporting               c07a5ed [fix/2026-07-29-shadow-phase0-c4-truth-reporting]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-29-shadow-phase0-c5-activation-transaction        f96ffb8 [fix/2026-07-29-shadow-phase0-c5-activation-transaction]
/home/lauer/.local/share/convmem/worktrees/fix-2026-07-31-doctor-test-fixture                            722e87f [fix/2026-07-31-doctor-test-fixture]
/home/lauer/.local/share/convmem/worktrees/fix-2026-08-04-embedding-eval-gate1-hardening                 69d8303 [fix/2026-08-04-embedding-eval-gate1-hardening]
/home/lauer/.local/share/convmem/worktrees/fix-2026-08-06-ask-eval-trace                                 19fdce1 [fix/2026-08-06-ask-eval-trace]
/home/lauer/.local/share/convmem/worktrees/fix-2026-08-06-delegate-deepseek-empty-response               c86ddad [fix/2026-08-06-delegate-deepseek-empty-response]
/home/lauer/.local/share/convmem/worktrees/fix-2026-08-07-judge-bench-judge-upgrades                     657336d [fix/2026-08-07-judge-bench-judge-upgrades]
/home/lauer/.local/share/convmem/worktrees/fix-2026-08-09-deepseek-v4-flash-timeout                      810ef2a [fix/2026-08-09-deepseek-v4-flash-timeout]
/home/lauer/.local/share/convmem/worktrees/fix-2026-08-09-projection-parity-reconcile                    bc23ff9 [fix/2026-08-09-projection-parity-reconcile]
/home/lauer/.local/share/convmem/worktrees/fix-2026-08-09-safe-file-reindex                              04fa8eb [fix/2026-08-09-safe-file-reindex]
/home/lauer/.local/share/convmem/worktrees/plan-2026-07-12-chroma-restore-drill                          f8e8a8f [plan/2026-07-12-chroma-restore-drill]
/home/lauer/.local/share/convmem/worktrees/plan-2026-07-12-knowledge-unit-conflict-detection             9b5bee7 [plan/2026-07-12-knowledge-unit-conflict-detection]
/home/lauer/.local/share/convmem/worktrees/plan-2026-07-12-restic-integrity-preflight                    8d9983d (detached HEAD)
/home/lauer/.local/share/convmem/worktrees/plan-2026-07-12-token-efficient-autonomy                      6cc4ef6 [plan/2026-07-12-token-efficient-autonomy]
/home/lauer/.local/share/convmem/worktrees/plan-2026-07-14-exclude-source-purge                          1734167 [plan/2026-07-14-exclude-source-purge]
/home/lauer/.local/share/convmem/worktrees/plan-2026-07-27-2026-07-27-complete-data-backup-correction-v2 b285782 [plan/2026-07-27-complete-data-backup-correction-v2]
/home/lauer/.local/share/convmem/worktrees/plan-2026-07-28-shadow-phase0-activation-corrective           29eede1 [plan/2026-07-28-shadow-phase0-activation-corrective]
/home/lauer/.local/share/convmem/worktrees/plan-2026-08-06-synthesis-calibration-prep                    913ec84 (detached HEAD)
/home/lauer/.local/share/convmem/worktrees/plan-2026-08-07-2026-08-07-chroma-reconcile-revise            4b47d5c [plan/2026-08-07-2026-08-07-chroma-reconcile-revise]
/home/lauer/.local/share/convmem/worktrees/wip-2026-07-19-2026-07-19-post-demotion-smoke                 f0d6486 [wip/2026-07-19-2026-07-19-post-demotion-smoke]
/home/lauer/.local/share/convmem/worktrees/wip-2026-07-19-2026-07-19-small-refactor                      f2fc186 [wip/2026-07-19-2026-07-19-small-refactor]
/home/lauer/.local/share/convmem/worktrees/wip-2026-07-19-2026-07-19-telemetry-t6-smoke                  742e25a [wip/2026-07-19-2026-07-19-telemetry-t6-smoke]
/home/lauer/.local/share/convmem/worktrees/wip-2026-07-28-local-dev-tools                                83b8c11 [wip/2026-07-28-local-dev-tools]
/home/lauer/.local/share/convmem/worktrees/wip-2026-07-29-shadow-phase0-c6-operational-canary            0daf2cf [wip/2026-07-29-shadow-phase0-c6-operational-canary]
/home/lauer/Projects/convmem-docs-debate-close                                                           ab5e9cf [docs/2026-07-22-debate-who-fixes-closed]
/home/lauer/Projects/convmem-docs-debate-kiro-followup                                                   09e80f0 [docs/2026-07-15-cursor-after-kiro]
/home/lauer/Projects/convmem-docs-who-fixes-closed                                                       8ceb6ac [docs/2026-07-22-who-fixes-retrieval-closed-to-p13]
/home/lauer/Projects/convmem-fix-ask-trace                                                               950e830 (detached HEAD)
/home/lauer/Projects/convmem-worktrees/pr52-r2a-closeout                                                 e585a09 (detached HEAD)
/home/lauer/Projects/convmem-wt-crush-digest-demotion                                                    2c040f4 [feat/2026-07-19-crush-digest-demotion]
/home/lauer/Projects/convmem-wt-debate-insight                                                           c29b449 [wip/2026-07-15-codex-top-two-proxy]
/home/lauer/Projects/convmem-wt-fix-ask-evidence-budget                                                  56802f1 [fix/2026-07-15-ask-evidence-budget]
/home/lauer/Projects/convmem-wt-stage4-close                                                             35f75e6 [docs/2026-07-19-stage4-close]
/home/lauer/Projects/convmem-wt-stage4-context-compression                                               a8668ce [plan/2026-07-19-stage4-context-compression]
/home/lauer/Projects/convmem-wt-stance-stage4-residual                                                   6f80df9 [docs/2026-07-22-stance-stage4-residual]
/tmp/convmem-cg1                                                                                         0be0a05 [feat/2026-08-10-2026-08-10-cg1-committed-generation-substrate]
/tmp/convmem-complete-data-status-brief                                                                  459892d [docs/2026-08-09-complete-data-status-brief-followup]
/tmp/convmem-crush-exec-1786150330                                                                       ecefcd7 [wip/2026-08-07-crush-delegation-test]
/tmp/convmem-judge-hardening                                                                             f475cea [fix/2026-08-08-judge-injection-hardening]
/tmp/convmem-main-pylint                                                                                 1f4edf0 (detached HEAD)
```

## Uncommitted files per worktree

### /home/lauer/.local/share/convmem/worktrees/docs-2026-07-15-codex-top-two-retrieval-plans
Branch: `docs/2026-07-15-codex-top-two-retrieval-plans`

```
?? docs/inter-model/debate-2026-07-15-who-fixes-retrieval/CODEX-top-two-problems-and-plans.md
```

### /home/lauer/.local/share/convmem/worktrees/fix-2026-07-27-complete-data-backup-correction-v2
Branch: `fix/2026-07-27-complete-data-backup-correction-v2`

```
?? complete-data-restore-reports/
```

### /home/lauer/.local/share/convmem/worktrees/fix-2026-07-28-shadow-phase0-c1-strict-validation
Branch: `fix/2026-07-28-shadow-phase0-c1-strict-validation`

```
?? complete-data-restore-reports/
```

### /home/lauer/.local/share/convmem/worktrees/fix-2026-07-28-shadow-phase0-c2-secure-append
Branch: `fix/2026-07-28-shadow-phase0-c2-secure-append`

```
?? complete-data-restore-reports/
```

### /home/lauer/.local/share/convmem/worktrees/fix-2026-07-29-shadow-phase0-c4-truth-reporting
Branch: `fix/2026-07-29-shadow-phase0-c4-truth-reporting`

```
?? complete-data-restore-reports/
```

### /home/lauer/.local/share/convmem/worktrees/fix-2026-08-07-judge-bench-judge-upgrades
Branch: `fix/2026-08-07-judge-bench-judge-upgrades`

```
 M eval_judge.py
 M eval_methodology.py
 M scripts/eval-summaries.py
 M scripts/eval-synthesis.py
 M tests/test_doctor.py
 M tests/test_eval_methodology.py
 M tests/test_eval_synthesis.py
?? docs/inter-model/CRUSH-2026-08-07-judge-bench-analysis.md
```

### /home/lauer/.local/share/convmem/worktrees/plan-2026-07-28-shadow-phase0-activation-corrective
Branch: `plan/2026-07-28-shadow-phase0-activation-corrective`

```
 M docs/plans/EXECUTION-shadow-phase0-activation-corrective.md
```

### /home/lauer/.local/share/convmem/worktrees/wip-2026-07-28-local-dev-tools
Branch: `wip/2026-07-28-local-dev-tools`

```
?? .vscode/
```

### /tmp/convmem-cg1
Branch: `feat/2026-08-10-2026-08-10-cg1-committed-generation-substrate`

```
 M ingest_dedupe.py
?? file_generation_builder.py
?? file_generation_contract.py
?? file_generation_pointer.py
?? file_generation_store.py
?? file_generation_validate.py
?? tests/test_file_generation_builder.py
?? tests/test_file_generation_contract.py
?? tests/test_file_generation_dedupe.py
?? tests/test_file_generation_durability.py
?? tests/test_file_generation_faults.py
?? tests/test_file_generation_pointer.py
?? tests/test_file_generation_read_path_inventory.py
?? tests/test_file_generation_read_paths.py
?? tests/test_file_generation_store.py
?? tests/test_file_generation_validate.py
```

### /tmp/convmem-crush-exec-1786150330
Branch: `wip/2026-08-07-crush-delegation-test`

```
 M chroma_store.py
?? scripts/chroma_orphan_inventory.py
?? tests/test_chroma_flatten.py
```

## Branches (recent, with tracking)

```
+ feat/2026-08-10-judgebench-live-driver                        f80fbcd (/home/lauer/.local/share/convmem/worktrees/feat-2026-08-10-judgebench-live-driver) [origin/feat/2026-08-10-judgebench-live-driver] prove both DeepSeek candidates use the bounded driver
+ feat/2026-08-10-2026-08-10-cg1-committed-generation-substrate 0be0a05 (/tmp/convmem-cg1) [origin/feat/2026-08-10-2026-08-10-cg1-committed-generation-substrate: behind 1] Prepare fail-closed JudgeBench calibration runs (#171)
* main                                                          0be0a05 [origin/main] Prepare fail-closed JudgeBench calibration runs (#171)
+ feat/2026-08-09-judgebench-calibration-prep                   200a2f4 (/home/lauer/.local/share/convmem/worktrees/feat-2026-08-09-judgebench-calibration-prep) [origin/feat/2026-08-09-judgebench-calibration-prep] preserve calibration compatibility exports
+ feat/2026-08-09-2026-08-09-judgebench-g3-corpus               d87ff7e (/home/lauer/.local/share/convmem/worktrees/feat-2026-08-09-2026-08-09-judgebench-g3-corpus) [origin/feat/2026-08-09-2026-08-09-judgebench-g3-corpus] satisfy Pylint gate for JudgeBench delivery
+ fix/2026-08-09-projection-parity-reconcile                    bc23ff9 (/home/lauer/.local/share/convmem/worktrees/fix-2026-08-09-projection-parity-reconcile) [origin/fix/2026-08-09-projection-parity-reconcile] update the governed writer location
+ fix/2026-08-09-safe-file-reindex                              04fa8eb (/home/lauer/.local/share/convmem/worktrees/fix-2026-08-09-safe-file-reindex) [origin/fix/2026-08-09-safe-file-reindex] test: document intentional internal reindex coverage
+ fix/2026-08-09-deepseek-v4-flash-timeout                      810ef2a (/home/lauer/.local/share/convmem/worktrees/fix-2026-08-09-deepseek-v4-flash-timeout) [origin/fix/2026-08-09-deepseek-v4-flash-timeout] fix: give reasoning extraction measured timeout headroom
  docs/2026-08-09-pga-landscape-hygiene                         ecb4678 [origin/docs/2026-08-09-pga-landscape-hygiene] docs: add DeepSeek V4 Flash timeout fix to LATEST landscape
+ docs/2026-08-09-complete-data-status-brief-followup           459892d (/tmp/convmem-complete-data-status-brief) [origin/docs/2026-08-09-complete-data-status-brief-followup: behind 10] add complete-data backup arc status brief
  docs/2026-08-09-landscape-status-sync                         ce6d49e [origin/docs/2026-08-09-landscape-status-sync] update: sync active STATUS file registry across agent surfaces
+ docs/2026-08-09-2026-08-09-judgebench-status-awareness        fbbbd33 (/home/lauer/.local/share/convmem/worktrees/docs-2026-08-09-2026-08-09-judgebench-status-awareness) [origin/docs/2026-08-09-2026-08-09-judgebench-status-awareness] docs: refresh JudgeBench arc landscape
+ docs/2026-08-09-complete-data-status-brief                    475fe43 (/home/lauer/.local/share/convmem/worktrees/docs-2026-08-09-complete-data-status-brief) [origin/docs/2026-08-09-complete-data-status-brief] docs: land post-rebuild verify handoff and Chroma reconcile STATUS (#161)
  docs/2026-08-09-2026-08-09-judgebench-status-test-note        189fc48 [origin/docs/2026-08-09-2026-08-09-judgebench-status-test-note: behind 3] update: correct JudgeBench STATUS test coverage note
  docs/2026-08-08-2026-08-09-pga-creation-rule                  479f43c [origin/docs/2026-08-08-2026-08-09-pga-creation-rule] Update JudgeBench arc brief: retrieval corpus repaired, T7 unblocked
  docs/2026-08-08-2026-08-09-judgebench-status-reconcile        9fc4579 [origin/docs/2026-08-08-2026-08-09-judgebench-status-reconcile: gone] reconcile JudgeBench STATUS arc brief to current main
  docs/2026-08-08-2026-08-09-pga-status-register                3fb82e2 [origin/docs/2026-08-08-2026-08-09-pga-status-register] propagate project-goal-awareness section and active-arc list to all model surfaces
  docs/2026-08-08-2026-08-09-project-goal-awareness             902f407 [origin/docs/2026-08-08-2026-08-09-project-goal-awareness] add Flash follow-up brief for stalled-arc briefs (R2b, Shadow)
  fix/2026-08-09-judgebench-arch-lock-chroma-rebuild            2ba88a7 [origin/fix/2026-08-09-judgebench-arch-lock-chroma-rebuild] fix: clear pylint gate for JudgeBench T2-T5 branch
  plan/2026-08-07-2026-08-07-judge-bench-analysis               740865c [origin/plan/2026-08-07-2026-08-07-judge-bench-analysis] mark JudgeBench planning docs complete after PR #153 merge
+ fix/2026-08-08-judge-injection-hardening                      f475cea (/tmp/convmem-judge-hardening) [origin/fix/2026-08-08-judge-injection-hardening] harden LLM judge against injected instructions in graded excerpts
+ fix/2026-08-04-embedding-eval-gate1-hardening                 69d8303 (/home/lauer/.local/share/convmem/worktrees/fix-2026-08-04-embedding-eval-gate1-hardening) [origin/fix/2026-08-04-embedding-eval-gate1-hardening] preserve Kiro embedding hardening review
+ feat/2026-08-07-synthesis-calibration-expansion               ab5e8ce (/home/lauer/.local/share/convmem/worktrees/feat-2026-08-07-synthesis-calibration-expansion) [origin/feat/2026-08-07-synthesis-calibration-expansion] Merge remote-tracking branch 'origin/main' into feat/2026-08-07-synthesis-calibration-expansion
+ plan/2026-08-07-2026-08-07-chroma-reconcile-revise            4b47d5c (/home/lauer/.local/share/convmem/worktrees/plan-2026-08-07-2026-08-07-chroma-reconcile-revise) [origin/plan/2026-08-07-2026-08-07-chroma-reconcile-revise] complete T7-2 rebuild CLI verification for tier-L reconcile
  plan/2026-08-07-2026-08-07-chroma-orphan-vector-repair        ce33e82 [origin/plan/2026-08-07-2026-08-07-chroma-orphan-vector-repair] fix: clear pylint regressions on orphan inventory and tests
+ wip/2026-08-07-crush-delegation-test                          ecefcd7 (/tmp/convmem-crush-exec-1786150330) note Flash critique cross-checks against revised plan
+ fix/2026-08-07-judge-bench-judge-upgrades                     657336d (/home/lauer/.local/share/convmem/worktrees/fix-2026-08-07-judge-bench-judge-upgrades) [origin/fix/2026-08-07-judge-bench-judge-upgrades] Mitigate qwen3.5 summarizer GPU saturation that was silently dropping ingested chunks (#140)
+ fix/2026-08-06-ask-eval-trace                                 19fdce1 (/home/lauer/.local/share/convmem/worktrees/fix-2026-08-06-ask-eval-trace) [origin/fix/2026-08-06-ask-eval-trace] clear ask lint regression for eval trace
+ docs/2026-07-15-consolidation-volatile-status                 243562e (/home/lauer/.local/share/convmem/worktrees/docs-2026-07-15-consolidation-volatile-status) [origin/docs/2026-07-15-consolidation-volatile-status] Merge branch 'main' into docs/2026-07-15-consolidation-volatile-status
  docs/2026-08-03-copilot-codeoss-token-guard                   f244c6a [origin/docs/2026-08-03-copilot-codeoss-token-guard] fix: align Copilot guidance with Pylint gate
```

---

End of snapshot. No secrets or corpus data included.
