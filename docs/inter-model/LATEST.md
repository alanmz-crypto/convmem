# Latest cross-model handoff (single pointer — update at session end)

**Updated:** 2026-07-23 (#106 landed; squash-merge default follow-up)
**Live counts:** run `convmem brief` — do not trust stale numbers here.

## Active handoff

- **Crush freezes + Qwen/DeepSeek billing routing LANDED (2026-07-23):** Squash-merged [#106](https://github.com/alanmz-crypto/convmem/pull/106) to `main` as [`67b020f`](https://github.com/alanmz-crypto/convmem/commit/67b020fd7fd545cd583496f2bb6a1808bfc53f7b).  
  **Consequence:** Crush uses shell `convmem` (MCP disabled) to avoid tool hangs; Cursor-dry work goes to Crush **Qwen3.7-Max**, with **DeepSeek V4 Pro/Flash** as second cloud seat.  
  **Who:** Cursor + Crush soak; Ryan squash-merged.  
  **What/When/Why/How:** Handoff [`CURSOR-2026-07-23-crush-qwen-stability-handoff.md`](CURSOR-2026-07-23-crush-qwen-stability-handoff.md); paste [`../CRUSH-QWEN-BOOTSTRAP.md`](../CRUSH-QWEN-BOOTSTRAP.md) / [`../CRUSH-DEEPSEEK-BOOTSTRAP.md`](../CRUSH-DEEPSEEK-BOOTSTRAP.md); routing in [`../MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md).  
  **Follow-up ([#107](https://github.com/alanmz-crypto/convmem/pull/107)):** squash-merge default note (missed the #106 tip) + post-land soaks: Crush DeepSeek shell **PASS**; Crush MCP `tools/call` probe **FAIL** (50 s watchdog after PreToolUse allow) — keep `mcp.convmem.disabled=true`. Probe script: `scripts/probe-crush-mcp-tools-call.sh`.


- **Crush tool-output residual GATE ACCEPTED (2026-07-23):**  
  **Consequence:** Crush routine digs in the Task 2 soak sat ~**30k** prompt tokens instead of the old ~**100k** residual — cheaper if agents keep tool dumps thin; we did **not** start an MCP-clipping follow-on. Ryan accepted the close paperwork after [#103](https://github.com/alanmz-crypto/convmem/pull/103) / [#104](https://github.com/alanmz-crypto/convmem/pull/104).  
  **Who:** Cursor Execute + VERIFY; Crush/`deepseek-v4-flash` soak; Ryan GATE accepted.  
  **What:** Always-loaded `tool-output-hygiene` (ranged bash/view/grep; failures still show exit + last lines).  
  **When:** Execute [#102](https://github.com/alanmz-crypto/convmem/pull/102) → `main` [`482637b`](https://github.com/alanmz-crypto/convmem/commit/482637b7bf3bfe82eba6007ad8fdf09eeae4ce43); soak + VERIFY [#103](https://github.com/alanmz-crypto/convmem/pull/103) `e324d2f`; merge-reading guidance [#104](https://github.com/alanmz-crypto/convmem/pull/104) `ca1178b`.  
  **Why:** Stage 4 fixed standing ~6k; tool-history rebill was still the bill.  
  **How:** Live rule `~/.config/crush/rules/tool-output-hygiene.md`; three soaks mean ~30.5k vs ~98–107k; Task 3 SKIP.  
  **Caveat / TL;DR:** Short guided soaks — not equal-weight proof vs old mega-audits; Stage 4 stays CLOSED. Plans: [`../plans/ARCHITECTURE-residual-tool-output.md`](../plans/ARCHITECTURE-residual-tool-output.md), [`../plans/EXECUTION-2026-07-22-residual-tool-output.md`](../plans/EXECUTION-2026-07-22-residual-tool-output.md), [`../plans/VERIFY-residual-tool-output.md`](../plans/VERIFY-residual-tool-output.md).  
  **Known residual (no arc):** Crush UI can hang on “waiting for a tool response” (seen ×3 on 2026-07-23 soak). Reopen only if it keeps biting.

- **PR / VERIFY human layer + merge reading (2026-07-23):** [#103](https://github.com/alanmz-crypto/convmem/pull/103) + [#104](https://github.com/alanmz-crypto/convmem/pull/104) on `main`. Arc-close and Execute PRs lead with consequence → 5 Ws → TL;DR **and** a **Merge reading** link list (ARCHITECTURE / EXECUTION / VERIFY / LATEST); mechanical tables stay. Canonical: `AGENTS.md` PR summary guidance; template: [`../plans/VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md).

- **Copilot CLI Tier A surface LANDED + DEPLOYED (2026-07-22; key hygiene 2026-07-23):** Squash-merged [#97](https://github.com/alanmz-crypto/convmem/pull/97) to `main` as [`8b0f53f`](https://github.com/alanmz-crypto/convmem/commit/8b0f53f). Who/What: Cursor land of GitHub Copilot **CLI** session adapter + watch/doctor/open_source + always-on instructions (filename A: `config/copilot-instructions-convmem.example.md`) + key-omitted MCP example; not GitHub.com Copilot billing/PR settings. When: merge + `deploy-agent-protocol.sh` same day (always-on + optional `--agent convmem` synced; `mcp_copilot` PASS). **Follow-up:** live `~/.copilot/mcp-config.json` had retained a real `DEEPSEEK_API_KEY`; scrubbed and deploy now strips that key always (mcp_server loads `env.local`). Why: end COMBINE residue from cross-arc consolidation so plain `copilot` is ingestible and ritual-capable on `main`. How: Track A via `~/.copilot/session-state/<uuid>/events.jsonl`; docs [`../COPILOT-SESSION-ADAPTER.md`](../COPILOT-SESSION-ADAPTER.md). Parallel Kiro generate/deploy tip folded under filename A — do not revive `copilot-instructions.example.md`. **Does not authorize** expanding the scarce GitHub Copilot audit lane or GitHub-hosted spend.

- **BugBot PR-level external review gate LANDED (2026-07-22):** Squash-merged [#91](https://github.com/alanmz-crypto/convmem/pull/91) to `main` as [`db3e5e0`](https://github.com/alanmz-crypto/convmem/commit/db3e5e0aeff29b6666441200e3cbb5db7b30559e). SHA-bound BugBot evidence in Execute/Verify; tracked `.cursor/BUGBOT.md` review context only. Independent of Copilot audit lane and PR Steward — do not collapse “someone looked” into BugBot PASS. Org branch-protection / non-Cursor fallback reviewer remain optional follow-ons (not authorized by the merge).

- **MCP Roots brief boundary LANDED (2026-07-22):** Squash-merged [#87](https://github.com/alanmz-crypto/convmem/pull/87) to `main` as [`eb84472`](https://github.com/alanmz-crypto/convmem/commit/eb84472f7ae6fedd75f9ace4359c913b15ee9136). Cursor shell MCP may omit `brief` when Roots report a project workspace — closes the old “global MCP starts in `$HOME` so every chat re-briefs” product gap from Stage 3 / [#19](https://github.com/alanmz-crypto/convmem/pull/19). Residual panel/`stats` live proof and bridge “Connection closed” debug are optional, not a reopen of the land.

- **R2b capture: code on main; draft packet QUARANTINED (2026-07-22):** Implementation landed [#67](https://github.com/alanmz-crypto/convmem/pull/67) as [`c0f06f5`](https://github.com/alanmz-crypto/convmem/commit/c0f06f57ac1cf82df205fe0c5bd3d60422012b1b). **Live capture remains unauthorized.** Disk draft `~/.local/share/convmem/authorizations/r2b/2026-07-21-r2b-capture-01/` is **QUARANTINED / abandoned** (stale T4; no sidecar; do not ACCEPT AND GRANT from it). Resume only with a **new** T4 packet + Ryan ACCEPT AND GRANT. Plans: [`../plans/ARCHITECTURE-r2b-capture-auth.md`](../plans/ARCHITECTURE-r2b-capture-auth.md), [`../plans/EXECUTION-2026-07-20-r2b-capture.md`](../plans/EXECUTION-2026-07-20-r2b-capture.md), [`../plans/VERIFY-r2b-capture.md`](../plans/VERIFY-r2b-capture.md).

- **PR Steward prompt LANDED + DEPLOYED (2026-07-22):** Squash-merged [#92](https://github.com/alanmz-crypto/convmem/pull/92) to `main` as [`0e2b396`](https://github.com/alanmz-crypto/convmem/commit/0e2b396c6a04b32a373deb0480d84efd64f10209). Canonical TEAM_CHARTER Steward suggest-line + standing check `pr-steward-reminder` (Platform, manual, 30-day) + Platform charter `register_refs`. Kiro independent VERIFY V0–V4 PASS (pre-rebase tip `6145c1b`; land tip later rebased). Live overlays updated via `deploy-agent-protocol.sh` (Cursor/Codex/Kiro/Crush Steward line present; mcp-shell excluded). **Docs residual closed:** VERIFY V0b + EXECUTION blurb corrected `2`→`3` (pre-squash tip was product pair + VERIFY doc). Not a merge/deploy reopen.

- **Semantic dedupe / queue hygiene GATE ACCEPTED (2026-07-22):** VERIFY PASS at tip [`dba9795`](https://github.com/alanmz-crypto/convmem/commit/dba9795785b4dffdbb21f9cad82d93332b8b1554) ([#86](https://github.com/alanmz-crypto/convmem/pull/86)). Phase A shipped (ingest total-line `queue_max_depth` pause; live refine jobs omit `semantic_dedupe`; example config documents optional job). Phase C default band closed: exact-title @ similarity ≥0.999 drained (pending exact=0); banded applies with undo under `refine_undo/semantic_dedupe/`; no `--approve-dedupe all`. Cursor mechanical PASS + Kiro independent PASS; **Ryan GATE accepted**. Remaining ~1055 pending are lower bands (0.98/0.95/0.92) or non-exact 1.000 — **not authorized**. Phase D (snapshot steering) still deferred / separate GATE. Plans: [`../plans/ARCHITECTURE-semantic-dedupe-hygiene.md`](../plans/ARCHITECTURE-semantic-dedupe-hygiene.md), [`../plans/EXECUTION-2026-07-22-semantic-dedupe-hygiene.md`](../plans/EXECUTION-2026-07-22-semantic-dedupe-hygiene.md), [`../plans/VERIFY-semantic-dedupe-hygiene.md`](../plans/VERIFY-semantic-dedupe-hygiene.md). Handoff: [`CURSOR-2026-07-22-semantic-dedupe-hygiene.md`](CURSOR-2026-07-22-semantic-dedupe-hygiene.md).

- **P1.3 live soak CLOSED (2026-07-22):** Day-0 A/B + Crush + Cursor behavioral PASS; Day+1 A/B PASS. Steering preferred for `ksweep-deploy` / `#ksweep-deploy` with `source_trust_weight = 1.0` and Crush stopgap retired. Residual: Kiro session-snapshot steering copies crowd top-N (deferred to dedupe hygiene Phase D).

- **CI Wait Workflow MERGED (2026-07-22):** [#81](https://github.com/alanmz-crypto/convmem/pull/81) squash-merged to `main` as `c5f17b6`. Optional playbook for productive work while CI/review runs; docs-only six-file scope. Cursor mechanical PASS (V0–V7); Kiro independent sign-off PASS at `0baab46d` (pre update-from-main). VERIFY: [`../plans/VERIFY-ci-wait-workflow.md`](../plans/VERIFY-ci-wait-workflow.md). Architecture: [`../plans/ARCHITECTURE-ci-wait-workflow.md`](../plans/ARCHITECTURE-ci-wait-workflow.md). Playbook on main: [`../CI-WAIT-WORKFLOW.md`](../CI-WAIT-WORKFLOW.md).

- **P1.3 ops complete (2026-07-22):** Live `source_trust_weight = 1.0` in `~/.config/convmem/config.toml`. Crush `ksweep-routing` stopgap retired (rules → `rules-retired/`; deploy no longer redeploys it). Standing check `ksweep-sunset` closed. Smoke: steering still preferred for `ksweep-deploy`.

- **P1.3 source-trust LANDED (2026-07-22):** Merged [#78](https://github.com/alanmz-crypto/convmem/pull/78) (`af31c6e`) + [#77](https://github.com/alanmz-crypto/convmem/pull/77) (`99f8717`). Cursor mechanical PASS with residual; Kiro PASS. Smoke: `ksweep-deploy` steering at rank 1. Follow-ups done via ops complete above (#36 already closed). VERIFY: [`../plans/VERIFY-source-trust-ranking.md`](../plans/VERIFY-source-trust-ranking.md).

- **who-fixes-retrieval CLOSED (2026-07-22):** Debate board Rounds 1–4 coordination closed; round code already on `main`. Inherit/dismiss + cargo: [`CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md`](CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md). VERIFY: [`../plans/VERIFY-who-fixes-retrieval.md`](../plans/VERIFY-who-fixes-retrieval.md). Keep shipped tools (ask trace, diversification, retrieve_for_ask, nested inter-model); corpus job follow-up **closed for default band** — see Active handoff GATE ACCEPTED (lower bands not authorized).


- **P1.3 source-trust ranking (2026-07-21, superseded):** Historical Codex execution brief — superseded by **P1.3 source-trust LANDED** + **P1.3 ops complete** above. Keep packets only as provenance: [`../plans/EXECUTION-2026-07-21-source-trust-ranking.md`](../plans/EXECUTION-2026-07-21-source-trust-ranking.md), [`CURSOR-2026-07-21-p13-codex-packet.md`](CURSOR-2026-07-21-p13-codex-packet.md).

- **Context brief rule (2026-07-21):** Always-loaded companion to RESPONSE_TLDR — when citing PRs, SHAs, ledger ids, or paths, keep the id **and** give Who/What/When/Why/How so Ryan knows what the item is doing. Canonical slice `CONTEXT_BRIEF` in `config/agent-protocol.md`.

- **DeepSeek V4-Pro audit substitute (2026-07-21):** Canonical protocol + hermetic runner for Ryan-authorized Copilot-lane substitutes (not Crush, not `convmem ask`). [`../plans/ARCHITECTURE-deepseek-v4pro-audit-substitute.md`](../plans/ARCHITECTURE-deepseek-v4pro-audit-substitute.md); `scripts/deepseek_audit_substitute.py`. Merged PR #66 used an earlier ad-hoc PASS — do not treat superseded Cursor plan packets as provenance. **No live substitute audit authorized by this docs change.**

- **PR Steward Delivery role v0.1 (2026-07-21):** Nonblocking governance/protocol PR adding a lasting **PR Steward** Delivery role under Ryan HITL (default actor OpenAI Codex when assigned); v0.1 is the temporary training period. Canonical: [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md); roles: [`../AGENT-ROLES.md`](../AGENT-ROLES.md); successor: [`CODEX-2026-07-21-pr-steward-role.md`](CODEX-2026-07-21-pr-steward-role.md). Compact `TEAM_CHARTER` + fitness test + five regenerated TEAM_CHARTER surfaces. **Deploy not run** — merge ≠ live overlay authority. **PR #65 architecture is merged; R2b implementation remains separate and unauthorized.**

- **VERIFY every arc (2026-07-20):** Binding Planning OS rule — after Execute, every **arc** needs `docs/plans/VERIFY-<slug>.md` before close. Phase guide: [`../planning/VERIFY-PLANNING.md`](../planning/VERIFY-PLANNING.md); copy starter: [`../plans/VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md). Kernel: [`../PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md). Example: [`../plans/VERIFY-r2a-config-generation.md`](../plans/VERIFY-r2a-config-generation.md).

- **R2b capture authorization (2026-07-20, wording updated 2026-07-22):** Option A settled in [`../plans/ARCHITECTURE-r2b-capture-auth.md`](../plans/ARCHITECTURE-r2b-capture-auth.md); execution/VERIFY as linked from Active handoff **R2b capture** bullet. **Implementation is on `main` via [#67](https://github.com/alanmz-crypto/convmem/pull/67)** — do not re-assert “no implementation authorized.” **Live capture** and draft `2026-07-21-r2b-capture-01` remain unauthorized / quarantined (see Active handoff). Supersedes #64; do not merge #64.

- **HITL charter — Copilot lifecycle (#54, 2026-07-20):** **Merged and charter active** (`3ee9f28` on `main`). Same-SHA GitHub Copilot audit lane + Kiro PASSes recorded before merge. Canonical: [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md); successor: [`CURSOR-2026-07-20-hitl-charter-copilot-lifecycle.md`](CURSOR-2026-07-20-hitl-charter-copilot-lifecycle.md); original handoff: [`CURSOR-2026-07-19-hitl-charter-delegation-sol-high.md`](CURSOR-2026-07-19-hitl-charter-delegation-sol-high.md). **Deploy qualification:** Cursor and Kiro live surfaces match tip examples. **CLI session plumbing** later closed by [#97](https://github.com/alanmz-crypto/convmem/pull/97) (see Active handoff Copilot Tier A) — do not confuse #54 lifecycle/audit scarcity with CLI ingest wiring. Do not treat #54 as deploy-blocked or awaiting review.

- **Post-#54 backlog / R2a one-job (2026-07-20):** [#52](https://github.com/alanmz-crypto/convmem/pull/52) auth + [#59](https://github.com/alanmz-crypto/convmem/pull/59) Phase D docs merged; nomic/mxbai `shadow.toml` written; Kiro PASS. Binding verify (V0–V7, Restic absolute, per-arm STOP): [`../plans/VERIFY-r2a-config-generation.md`](../plans/VERIFY-r2a-config-generation.md). Handoff: [`CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md`](CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md). **Still not authorized:** further R2a without new grant; R2b+, Gate 2, promotion, cleanup. Gate 1 harness SHA remains `3b2790f50414f0445c35748e52f849c6276839f7`.


- **Response TL;DR (2026-07-19):** Canonical rule in `config/agent-protocol.md` (`RESPONSE_TLDR` slice) — every agent response ends with a scaled TL;DR. Regenerated into Cursor/Codex/Kiro/Crush/MCP/ChatGPT surfaces via `scripts/generate-agent-protocol.sh` (deploy with `scripts/deploy-agent-protocol.sh` when Ryan wants live surfaces updated).
- **Stage 3 bounded-autonomy accepted (2026-07-13):** Behaviorally verified and accepted by Ryan on 2026-07-13. Stage 2 soak 3/3 passed ([PR #13](https://github.com/alanmz-crypto/convmem/pull/13)–[PR #15](https://github.com/alanmz-crypto/convmem/pull/15)); doctor-first policy landed in [PR #16](https://github.com/alanmz-crypto/convmem/pull/16); the convmem-only default landed in [PR #17](https://github.com/alanmz-crypto/convmem/pull/17); prompt-level MCP brief deduplication shipped in [PR #18](https://github.com/alanmz-crypto/convmem/pull/18); [PR #19](https://github.com/alanmz-crypto/convmem/pull/19) added a cwd-gated shell profile; [PR #22](https://github.com/alanmz-crypto/convmem/pull/22) closed the doctor-first gate; [PR #24](https://github.com/alanmz-crypto/convmem/pull/24) shipped the human-readable pending-decision review (JSONL remains canonical). Ryan manually verified: `record --list` is readable; `record --approve-last` shows the full card; default-No cancellation leaves the draft unchanged. **MCP `$HOME` re-brief product gap:** closed later by Roots omit on [#87](https://github.com/alanmz-crypto/convmem/pull/87) (see Active handoff) — do not treat the Jul 13 “global MCP starts from `/home/lauer`” line as still-open product work. WordPress, other repositories, architecture, security, and external configuration remain excluded. Plans: [`EXECUTION-token-efficient-bounded-autonomy.md`](../plans/EXECUTION-token-efficient-bounded-autonomy.md), [`ARCHITECTURE-token-efficient-bounded-autonomy.md`](../plans/ARCHITECTURE-token-efficient-bounded-autonomy.md).
- **Always-Available GitHub Fallback (2026-07-12):** shipped; Kiro V6c signed (`Kiro reviewed: 2026-07-12`). V6a remains SKIP because GitHub branch protection requires Pro; do not claim `main` is protected. VERIFY: [`../plans/VERIFY-always-github-fallback.md`](../plans/VERIFY-always-github-fallback.md).
- **Bug sprint scored (2026-07-08):** 5/5 PASS. `tier_1_5_gate: UNLOCKED`. Bug 5 (provider fallback) fixed same day — `_resolve_fallback_model` + warn-once + `CONVMEM_FAIL_ON_FALLBACK=1`. Scored in [`BUG-SPRINT-SUCCESS-2026-07-06.md`](BUG-SPRINT-SUCCESS-2026-07-06.md). Convmem now clear for willowyhollow-practice bug work.
- **Orchestration approach (2026-07-06, merged):** Claude Cloud **Option B** — Tier 1 = **shared memory bus** (not orchestration); bug sprint proves value via [BUG-SPRINT-SUCCESS-2026-07-06.md](BUG-SPRINT-SUCCESS-2026-07-06.md); Tier 1.5 deferred until `tier_1_5_gate: UNLOCKED`; Tier 3 design in convmem-lab. Canonical: [ORCHESTRATION-APPROACH-2026-07-06.md](ORCHESTRATION-APPROACH-2026-07-06.md). Framing: [ORCHESTRATION-FRAMING.md](ORCHESTRATION-FRAMING.md). Prior handoff closed: [HANDOFF-CLAUDE-CLOUD-2026-07-06-orchestration-approach-review.md](HANDOFF-CLAUDE-CLOUD-2026-07-06-orchestration-approach-review.md).
- **HITL team charter (2026-07-06):** **shipped** — Claude Cloud review integrated; compact `TEAM_CHARTER` in [`config/agent-protocol.md`](../config/agent-protocol.md) (always-loaded via generate/deploy); full doc [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md). Key fix: **Crush lane ≠ DeepSeek API** — say Crush found it, not DeepSeek. Phrasebook + lane table on all Tier A surfaces. Prior handoff: [`HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md`](HANDOFF-CLAUDE-CLOUD-2026-07-06-hitl-orchestration-lab.md). Deploy: `bash scripts/deploy-agent-protocol.sh`.
- **Retrieval + synthesis hardening (2026-07-05):** **shipped** — P1c partial synthesis on timeout (`generate_stream`, `synthesis_interrupted`); Manning P1a recency on plain search; protocol anchor `c311` lookup fix; DDIA `ledger_unit_document()` at ingest + `scripts/repair-ledger-documents.sh`; inter-model doc adapter (`docs/inter-model/*.md` → section units, `scripts/index-inter-model-docs.sh` requires `CONVMEM_CONFIRM_PROD=1`); prod/lab **write guard** (`runtime_guard.py`, `write_lane` in doctor). Builder notes: [`suggested-application-of-builder-material.md`](../builder-reference/notes/suggested-application-of-builder-material.md). Streaming plan: [`PLAN-2026-06-29-streaming-synthesis.md`](PLAN-2026-06-29-streaming-synthesis.md) Phase 1 closed.
- **Ops closure (2026-07-05):** weekly digest timer **active** (`convmem-cross-project-digest.timer` Mon 09:00); `attempts.jsonl` real obs ids; `[watch].extra_paths` → `docs/inter-model`; doctor `ledger_documents` + `digest_timer` (v1). Install: `scripts/install-cross-project-digest-timer.sh`.
- **Synthesis + lab-reference (2026-07-05):** **shipped** — lab S1–S5 (`load_attempts`, recency, propose smoke), `lab-reference/` gates, prod port of `load_attempts` + `## Do not retry`, `MODEL-WORKFLOW.md`, `CODEX-DEEPSEEK-VERIFY.md`. Codex + DeepSeek verify PASS (shell + MCP). Cheat sheet: [`MODEL-WORKFLOW.md`](../MODEL-WORKFLOW.md). Verify: [`CODEX-DEEPSEEK-VERIFY.md`](../CODEX-DEEPSEEK-VERIFY.md). Status: [`SYNTHESIS-STATUS.md`](../../SYNTHESIS-STATUS.md). `--propose` prod trial still Ryan-gated.
- **Builder-reference plan (2026-07-01):** **execution shipped** — README tier A/B/archive, script thresholds reconciled, `Builder lens` on BUILT-PLANS + ROADMAP, DDIA changelog, arch-patterns expanded (1510w), DDIA tier-B on Cursor/Kiro/Codex (Crush unchanged). Plan: [`PLAN-2026-07-01-apply-builder-reference.md`](PLAN-2026-07-01-apply-builder-reference.md). Log: [`docs/logs/2026-07-01-builder-reference-plan-handoffs.md`](../logs/2026-07-01-builder-reference-plan-handoffs.md). ChatGPT literature lane still optional if recommendations return.
- **Repo organization (2026-06-30):** **shipped** (Option A — root `LATEST.md` renamed to [`SYNTHESIS-STATUS.md`](../../SYNTHESIS-STATUS.md)). Runbook + trail: [`docs/archive/inter-model/2026-06-30-org-planning/`](../archive/inter-model/2026-06-30-org-planning/). Log: [`docs/logs/2026-06-30-v4-execution.md`](../logs/2026-06-30-v4-execution.md).
- **Digest Phase 0 (2026-07-01):** **closed** (Run 6). Run 8 (2026-07-05): full digest + first `--propose` trial — auto-draft `dec_prop_20260705_152603_2c96` **rejected** (stale prod-gap line); pipeline validated; Ryan filing habit OK. Log: [`CROSS-PROJECT-DIGEST-PILOT.md`](CROSS-PROJECT-DIGEST-PILOT.md). Output: `~/.local/share/convmem/digests/2026-07-05.md`.
- **Background-synthesis status reconciliation (2026-07-14):** [`BUILT-PLANS-2026-06-24-to-2026-06-29.md`](BUILT-PLANS-2026-06-24-to-2026-06-29.md) now reflects Run 8, shipped P1c/inter-model indexing, and the active read-only weekly timer. Phase 2 remains held on agent-habit/value evidence and a recorded manual `link_queue.jsonl` review; timer-driven `--propose` remains Ryan-gated.
- **F1 semantic dedupe (2026-07-01):** **queue drained** — 10/10 pairs reviewed (`dec_prop_20260701_211650_5a62`); 9 Chroma tombstones applied via `convmem refine --approve-dedupe all`; 1 `rejected_keep_both`. CLI `--approve-dedupe` shipped in `refine.py`. Undo snapshots under `refine_undo/semantic_dedupe/`.
- **F1 backfill_domain acceptance (2026-07-01):** `convmem refine --once --job backfill_domain --limit 10` → **0 untagged** (corpus fully domain-tagged on visible units). MILESTONE-F manual gate **closed**.
- **Digest recency tighten (2026-07-02):** Run 7 — explicit recent-id ask injection + `## Recency check` in digest output. Log: [`CROSS-PROJECT-DIGEST-PILOT.md`](CROSS-PROJECT-DIGEST-PILOT.md) Run 7.

**Phase 1 gate:** **CLOSED.** Documents `13bf8547` PASS, linuxbrew `77a57494` PASS. Strict script + `--exclude Search` is the enforceable path for graded workspace_local smokes.

**Phase 2 gate — CLOSED (2026-06-29):** `f358d4f0` — `cn --auto` on Documents, PARTIAL ritual, v5 payload PASS (`inventory.total: 0`). **Qwen Continue verify lane complete.**

**Phase 2 (optional):** superseded — see Phase 2 section in [`CONTINUE-VERIFY.md`](CONTINUE-VERIFY.md).

**Archive:** [`HANDOFF-CLAUDE-CLOUD-2026-06-29-qwen-continue-verify.md`](HANDOFF-CLAUDE-CLOUD-2026-06-29-qwen-continue-verify.md). Tarball removed during residue cleanup.

## State

- **Global protocol:** **Closed.** All active surfaces **PASS** alien soak + post-permissions retest (Ryan). See `SOAK-REPORT-2026-06-25.md`.
- **Gap-fix (pre-P2):** Deploy permissions verify, Crush session-close slice, Continue trim template, verification matrix, grader alien check — **shipped**. Ryan manual: Continue trim + Codex/blank-dir soaks.
- **Deployed:** Cursor `.mdc`, Kiro steering + `permissions.yaml` (incl. `echo *`), Crush Tier A + `crush.json` permissions + bash hook, Continue MCP `instructions=`.
- **Post-permissions retest (Ryan):** **Cursor PASS ×2**, **Kiro PASS**, **Crush PASS**, **Continue qwen3-coder:30b PASS** — no convmem permission prompts.
- **ChatGPT Tier C:** out of scope (ignored).
- **Corpus:** see `convmem brief` — do not trust counts here; run `doctor` before ask/search.
- **P2 gate:** still **hold** (MCP `unresolved` tool optional next).
- **Tests:** run `convmem brief --with-tests` or pytest when needed.

## Architecture diagram

```
flowchart TD
  canonical["config/agent-protocol.md\n(canonical SSoT)"]
  mcp["mcp_server.py\nloads MCP slice"]
  cursor["~/.cursor/rules/convmem.mdc"]
  codex["~/.codex/AGENTS.md"]
  kiro["~/.kiro/steering/convmem.md"]
  crush["~/.config/crush/rules/convmem.md"]
  continue["~/.continue/config.yaml rules"]
  chatgpt["docs/chatgpt-pack/\ncustom-instructions.txt"]
  recover["docs/RECOVER.md +\ndeploy script"]

  canonical --> mcp
  canonical --> cursor
  canonical --> codex
  canonical --> kiro
  canonical --> crush
  canonical --> continue
  canonical --> chatgpt
  canonical --> recover
```

## Decision

- Inter-model markdown = archive; **ledger + brief** = truth.
- **Change feed** (Codex): deferred until payoff review **2026-07-07**.
- **Crush tier:** Tier A (shell + MCP) — soak #8 showed MCP-only rules ignored; redeployed with shell ritual.
- **P2 gate held:** Do not accelerate. Fix surface coverage first, then re-evaluate MCP tools.

## Record a fact (two commands)

```bash
convmem record -i                  # draft (interactive)
convmem record --approve-last      # finish — indexes automatically
```

Kiro: add `--signer kiro-review`. Legacy CLI name: `propose_decision`.

## Session close (all models)

Read `docs/inter-model/SESSION-CLOSE-RECORD.md`. Output:

```bash
convmem record --relates-to <id> --summary "..." --rationale "..." --author ...
convmem record --approve-last
```

Search for `--relates-to` (never topic slugs). Fallback root: `dec_prop_20260623_161428_c311`.

### Close chain (newest first)

| Layer | Ledger id |
|-------|-----------|
| **Lab synthesis S1–S5 + prod port + dual verify** | `dec_prop_20260705_151004_1e00` (after Ryan record) |
| **F1 dedupe queue review + tombstone apply** | `dec_prop_20260701_211650_5a62` (review); apply record → see session close below |
| **Builder-reference plan execution** | `dec_prop_20260701_182803_987b` |
| **Phase 2 deployment (Crush slice + soak report)** | `dec_prop_20260625_233830_b9af` |
| **Continue+Crush alien-workspace fail: zero convmem** | `dec_prop_20260625_225404_11cf` |
| **Continue alien-workspace fail: pavlomassage-practice** | `dec_prop_20260625_223006_528c` |
| **Soak: alien-workspace spot-check logged** | `dec_prop_20260625_220647_47d9` |
| **Global protocol post-deploy soak** | `dec_prop_20260625_203408_f9b3` |
| **Thai Massage image darkening fix** | `dec_prop_20260623_215943_5abe` |
| **Docker/Podman stack fix** | `dec_prop_20260624_025115_862b` |
| **Protocol root (fallback)** | `dec_prop_20260623_161428_c311` |

**Rule:** chain under the **newest relevant** id from `search_fast`, not a ledger you only cited during a test.

## Next

- **Builder-reference:** execution **shipped** (2026-07-01). Use digests per `docs/builder-reference/notes/suggested-application-of-builder-material.md` before architecture edits.
- **F1 refine:** semantic dedupe queue **drained** (0 pending; 9 tombstoned). `semantic_dedupe` **out of daemon jobs** until corpus growth warrants re-queueing — review via `dedupe_queue.jsonl` + `--approve-dedupe`. Live config: `dedupe_similarity=0.92`, `queue_max_depth=200` (no change needed).
- **Digest:** Phase 1 automation + recency self-check (Run 7). Run 8 `--propose` trial **closed** — `2c96` rejected; prose/record filing habit OK (Ryan). Weekly timer install = host ops; linker product **held** on agent-habit gate.
- **Default:** `convmem doctor` → `brief` → `unresolved` (shell) or MCP `brief()` + `unresolved()` (MCP-only); `search_fast` before guessing.
- **Ryan manual:** See [VERIFICATION-MATRIX.md](VERIFICATION-MATRIX.md) — Continue `rules:` trim, Codex alien soak, blank-dir checks.
- **Change feed:** hold until **2026-07-07**.
- **P2:** MCP `unresolved()` tool **shipped** (Run 5) — parity with shell `convmem unresolved`. Gate **still held** on agent-habit / Phase 2 linker (`obs_806985bc5697`); not blocked on unresolved tool anymore.

### Optional close (Ryan — search for newer `--relates-to` first)

```bash
convmem record \
  --relates-to dec_prop_20260625_233830_b9af \
  --summary "Global convmem protocol: all surfaces PASS + gap-fix deploy" \
  --rationale "Cursor/Kiro/Crush/Continue qwen verified; permissions echo*; deploy verify shipped; P2 deferred." \
  --author ryan
convmem record --approve-last
```
