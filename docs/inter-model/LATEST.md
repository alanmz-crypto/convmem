# Latest cross-model handoff (single pointer — update at session end)

**Updated:** 2026-07-22 (CI-wait PR #81 merged; cleared stale handoff pointer)
**Live counts:** run `convmem brief` — do not trust stale numbers here.

## Active handoff

- **CI Wait Workflow MERGED (2026-07-22):** [#81](https://github.com/alanmz-crypto/convmem/pull/81) squash-merged to `main` as `c5f17b6`. Optional playbook for productive work while CI/review runs; docs-only six-file scope. Cursor mechanical PASS (V0–V7); Kiro independent sign-off PASS at `0baab46d` (pre update-from-main). VERIFY: [`../plans/VERIFY-ci-wait-workflow.md`](../plans/VERIFY-ci-wait-workflow.md). Architecture: [`../plans/ARCHITECTURE-ci-wait-workflow.md`](../plans/ARCHITECTURE-ci-wait-workflow.md). Playbook on main: [`../CI-WAIT-WORKFLOW.md`](../CI-WAIT-WORKFLOW.md).

- **P1.3 ops complete (2026-07-22):** Live `source_trust_weight = 1.0` in `~/.config/convmem/config.toml`. Crush `ksweep-routing` stopgap retired (rules → `rules-retired/`; deploy no longer redeploys it). Standing check `ksweep-sunset` closed. Smoke: steering still preferred for `ksweep-deploy`.

- **P1.3 source-trust LANDED (2026-07-22):** Merged [#78](https://github.com/alanmz-crypto/convmem/pull/78) (`af31c6e`) + [#77](https://github.com/alanmz-crypto/convmem/pull/77) (`99f8717`). Cursor mechanical PASS with residual; Kiro PASS. Smoke: `ksweep-deploy` steering at rank 1. Follow-ups done via ops complete above (#36 already closed). VERIFY: [`../plans/VERIFY-source-trust-ranking.md`](../plans/VERIFY-source-trust-ranking.md).

- **who-fixes-retrieval CLOSED (2026-07-22):** Debate board Rounds 1–4 coordination closed; round code already on `main`. Inherit/dismiss + cargo: [`CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md`](CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md). VERIFY: [`../plans/VERIFY-who-fixes-retrieval.md`](../plans/VERIFY-who-fixes-retrieval.md). Keep shipped tools (ask trace, diversification, retrieve_for_ask, nested inter-model); park corpus jobs (`semantic_dedupe`, evidence inject) as valued separate briefs — not P1.3 blockers.


- **P1.3 source-trust ranking (2026-07-21, superseded):** Historical Codex execution brief — superseded by **P1.3 source-trust LANDED** + **P1.3 ops complete** above. Keep packets only as provenance: [`../plans/EXECUTION-2026-07-21-source-trust-ranking.md`](../plans/EXECUTION-2026-07-21-source-trust-ranking.md), [`CURSOR-2026-07-21-p13-codex-packet.md`](CURSOR-2026-07-21-p13-codex-packet.md).

- **Context brief rule (2026-07-21):** Always-loaded companion to RESPONSE_TLDR — when citing PRs, SHAs, ledger ids, or paths, keep the id **and** give Who/What/When/Why/How so Ryan knows what the item is doing. Canonical slice `CONTEXT_BRIEF` in `config/agent-protocol.md`.

- **DeepSeek V4-Pro audit substitute (2026-07-21):** Canonical protocol + hermetic runner for Ryan-authorized Copilot-lane substitutes (not Crush, not `convmem ask`). [`../plans/ARCHITECTURE-deepseek-v4pro-audit-substitute.md`](../plans/ARCHITECTURE-deepseek-v4pro-audit-substitute.md); `scripts/deepseek_audit_substitute.py`. Merged PR #66 used an earlier ad-hoc PASS — do not treat superseded Cursor plan packets as provenance. **No live substitute audit authorized by this docs change.**

- **PR Steward Delivery role v0.1 (2026-07-21):** Nonblocking governance/protocol PR adding a lasting **PR Steward** Delivery role under Ryan HITL (default actor OpenAI Codex when assigned); v0.1 is the temporary training period. Canonical: [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md); roles: [`../AGENT-ROLES.md`](../AGENT-ROLES.md); successor: [`CODEX-2026-07-21-pr-steward-role.md`](CODEX-2026-07-21-pr-steward-role.md). Compact `TEAM_CHARTER` + fitness test + five regenerated TEAM_CHARTER surfaces. **Deploy not run** — merge ≠ live overlay authority. **PR #65 architecture is merged; R2b implementation remains separate and unauthorized.**

- **VERIFY every arc (2026-07-20):** Binding Planning OS rule — after Execute, every **arc** needs `docs/plans/VERIFY-<slug>.md` before close. Phase guide: [`../planning/VERIFY-PLANNING.md`](../planning/VERIFY-PLANNING.md); copy starter: [`../plans/VERIFY-TEMPLATE.md`](../plans/VERIFY-TEMPLATE.md). Kernel: [`../PLANNING-PROTOCOL.md`](../PLANNING-PROTOCOL.md). Example: [`../plans/VERIFY-r2a-config-generation.md`](../plans/VERIFY-r2a-config-generation.md).

- **R2b capture authorization (2026-07-20):** Option A is settled in the proposed [`../plans/ARCHITECTURE-r2b-capture-auth.md`](../plans/ARCHITECTURE-r2b-capture-auth.md): phase-scoped `authorization_phase: "r2b"`, content-bound trusted source snapshot, deterministic one-attempt capture, binder-only write capability, safe run/path containment, and an expanded last atomic completion marker. [`../plans/EXECUTION-2026-07-20-r2b-capture.md`](../plans/EXECUTION-2026-07-20-r2b-capture.md) and filled [`../plans/VERIFY-r2b-capture.md`](../plans/VERIFY-r2b-capture.md) carry the staged gates, V1g full prohibited list, and marker-authority V4c. The replacement docs PR **Supersedes #64**; do not merge #64. **No implementation or live R2b capture is authorized.**

- **HITL charter — Copilot lifecycle (#54, 2026-07-20):** **Merged and charter active** (`3ee9f28` on `main`). Same-SHA GitHub Copilot audit lane + Kiro PASSes recorded before merge. Canonical: [`TEAM-CHARTER-2026-07-06.md`](TEAM-CHARTER-2026-07-06.md); successor: [`CURSOR-2026-07-20-hitl-charter-copilot-lifecycle.md`](CURSOR-2026-07-20-hitl-charter-copilot-lifecycle.md); original handoff: [`CURSOR-2026-07-19-hitl-charter-delegation-sol-high.md`](CURSOR-2026-07-19-hitl-charter-delegation-sol-high.md). **Deploy qualification:** Cursor and Kiro live surfaces match tip examples; Copilot CLI / Codex `AGENTS.md` still has three trailing builder-digest lines (charter-safe drift — not a #54 blocker). Do not treat #54 as deploy-blocked or awaiting review.

- **Post-#54 backlog / R2a one-job (2026-07-20):** [#52](https://github.com/alanmz-crypto/convmem/pull/52) auth + [#59](https://github.com/alanmz-crypto/convmem/pull/59) Phase D docs merged; nomic/mxbai `shadow.toml` written; Kiro PASS. Binding verify (V0–V7, Restic absolute, per-arm STOP): [`../plans/VERIFY-r2a-config-generation.md`](../plans/VERIFY-r2a-config-generation.md). Handoff: [`CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md`](CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md). **Still not authorized:** further R2a without new grant; R2b+, Gate 2, promotion, cleanup. Gate 1 harness SHA remains `3b2790f50414f0445c35748e52f849c6276839f7`.


- **Response TL;DR (2026-07-19):** Canonical rule in `config/agent-protocol.md` (`RESPONSE_TLDR` slice) — every agent response ends with a scaled TL;DR. Regenerated into Cursor/Codex/Kiro/Crush/MCP/ChatGPT surfaces via `scripts/generate-agent-protocol.sh` (deploy with `scripts/deploy-agent-protocol.sh` when Ryan wants live surfaces updated).
- **Stage 3 bounded-autonomy accepted (2026-07-13):** Behaviorally verified and accepted by Ryan on 2026-07-13. Stage 2 soak 3/3 passed ([PR #13](https://github.com/alanmz-crypto/convmem/pull/13)–[PR #15](https://github.com/alanmz-crypto/convmem/pull/15)); doctor-first policy landed in [PR #16](https://github.com/alanmz-crypto/convmem/pull/16); the convmem-only default landed in [PR #17](https://github.com/alanmz-crypto/convmem/pull/17); prompt-level MCP brief deduplication shipped in [PR #18](https://github.com/alanmz-crypto/convmem/pull/18); [PR #19](https://github.com/alanmz-crypto/convmem/pull/19) added a cwd-gated shell profile; [PR #22](https://github.com/alanmz-crypto/convmem/pull/22) closed the doctor-first gate; [PR #24](https://github.com/alanmz-crypto/convmem/pull/24) shipped the human-readable pending-decision review (JSONL remains canonical). Ryan manually verified: `record --list` is readable; `record --approve-last` shows the full card; default-No cancellation leaves the draft unchanged. Cursor’s global MCP process still starts from `/home/lauer`, so that MCP caveat remains a separate open token-cut gap — do not claim PR #19 is mechanically verified for Cursor. WordPress, other repositories, architecture, security, and external configuration remain excluded. Plans: [`EXECUTION-token-efficient-bounded-autonomy.md`](../plans/EXECUTION-token-efficient-bounded-autonomy.md), [`ARCHITECTURE-token-efficient-bounded-autonomy.md`](../plans/ARCHITECTURE-token-efficient-bounded-autonomy.md).
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
