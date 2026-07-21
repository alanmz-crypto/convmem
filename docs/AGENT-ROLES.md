# Agent roles (static — do not duplicate in brief.md)

**Canonical protocol:** `config/agent-protocol.md` (three capability tiers: shell / MCP-only / paste).
Generated per-surface slices via `scripts/generate-agent-protocol.sh`.

| Agent | Lane | Capability tier | May create branch | Prefixes | May merge main |
|-------|------|-----------------|-------------------|----------|----------------|
| **Kiro** | Non-implementing, review-required design/sign-off lane. May edit an architecture, plan, or review document only when Ryan explicitly requests that documentation task; never implementation code, tests, scripts, configuration, generated surfaces, or runtime state. Uses `--signer kiro-review` only in a record block Ryan explicitly requests; never runs `--approve-last`. | Tier A (shell + MCP via `~/.kiro/settings/mcp.json` + steering) | Yes, for authorized docs | **plan, docs only** | No — sign-off |
| **Cursor** | Implementer on local workstation; global `convmem.mdc` rule drives session start | Tier A (shell + MCP) | Yes | feat, fix, docs, wip | No |
| **Sonnet** | MCP verification (static source + live Crush handshake) | Tier A via Cursor | — | — | No |
| **ChatGPT** | Orchestration/strategy; paste-only access to corpus | Tier C (paste-only) | No | — | No |
| **Crush** | Runtime agent with shell + MCP read tools | Tier A (shell + MCP; soak #8 showed MCP-only rules ignored) | Yes | fix, wip | No |
| **DeepSeek** | Runtime synthesis only (`ask` / distill API) | Tier B (MCP-only) | No | — | No |
| **GitHub Copilot audit lane** | Governing conditional technical-review lane; independent code/safety/isolation audit when warranted; targeted post-impl verification. GitHub Copilot in VS Code. No merge-to-main; no inferred deploy or live authorization. | Tier A (shell + MCP where available) | Yes | fix, feat, docs | No |
| **OpenAI Codex** | Separately installed product if retained; **not** the governing audit lane owner. Default actor for the **PR Steward** Delivery role when Ryan assigns that job (overlay does not enlarge Codex capabilities). Keeps its own factual paths: `~/.codex/AGENTS.md` global + repo root; `codex_rollout_jsonl` adapter; `CODEX-DEEPSEEK-VERIFY.md`; `bash -lc` sandbox network retry; generated filename `codex-agents-convmem.example.md`. Historical posts that say "Codex" for the audit lane refer to the pre-2026-07-19 role and are preserved as-is. | Tier A (shell, no MCP) — use CLI `convmem` commands | Yes | fix, feat, docs | No |
| **Continue** | MCP read (`brief`, `search_fast`, `ask`); MCP `instructions=` carries expanded protocol | Tier A (shell + MCP) | Yes (via shell) | feat, fix, docs, wip | No |

**Ryan** may create any prefix and is the only lane that merges to `main`. Branching rules: [`plans/branching-strategy.md`](plans/branching-strategy.md).

**DeepSeek vs Crush:** DeepSeek row = Tier B synthesis API behind `convmem ask` only — not a bug-hunter. Crush running DeepSeek V4 weights is still **Crush lane** (Tier A shell). Bug discovery owner = **Crush**, not DeepSeek. Full audit: [`docs/inter-model/TEAM-CHARTER-2026-07-06.md`](inter-model/TEAM-CHARTER-2026-07-06.md).

**Lane routing + Sol-High gate:** Large implementation → Cursor; bound-brief GitHub PR lifecycle → **PR Steward** Delivery role under Ryan HITL (default actor Codex when assigned); investigation/audit/safety → GitHub Copilot audit lane (conditional). Sol-High is a separate scarce adjudicator — it requires written PASS or FAIL from both the GitHub Copilot audit lane and Kiro on the same artifact and revision. `defer`, DeepSeek R1 model output, and the embedding worked example's Authorization R1 cannot satisfy the gate. Always-loaded in `TEAM_CHARTER` (`config/agent-protocol.md`). Full lifecycle: [`docs/inter-model/TEAM-CHARTER-2026-07-06.md`](inter-model/TEAM-CHARTER-2026-07-06.md).

**Session close (all models):** follow [`config/agent-protocol.md`](../config/agent-protocol.md) and [`SESSION-CLOSE-RECORD.md`](inter-model/SESSION-CLOSE-RECORD.md).

- **Handoff (default):** index session chat — `convmem index --file <session-path>` (Track A). **Handoff is not a record.**
- **Record block:** output a copy-paste `convmem record …` block **only** when Ryan says `record block`, `closing`, `end session`, or `record this`. Agents **never** run `convmem record --approve-last`.
- **`--approve-last`:** Ryan-gated only. Kiro uses `--signer kiro-review` when Ryan approves.

Cross-model messages: `docs/inter-model/<MODEL>-<date>-<topic>.md`

---

## Planning OS (lane terminology)

The Planning OS uses vocabulary distinct from this table:

| Term | Source | Meaning |
|------|--------|---------|
| **Lane** | This file | Agent surface + capability tier + must-not rules |
| **Function** | Phase guides under [`planning/`](planning/) | Workflow job (Planner, Reviewer, Implementer) |
| **Role** | [`role-charters.md`](role-charters.md) | Engineering-team ownership (seven cards) |
| **Delivery role** | HITL charter ([`TEAM-CHARTER-2026-07-06.md`](inter-model/TEAM-CHARTER-2026-07-06.md)) | Temporary workflow overlay under Ryan HITL; never changes Lane/capability/must-nots |

Kernel: [`PLANNING-PROTOCOL.md`](PLANNING-PROTOCOL.md). Do not add Planner/Reviewer
rows to the agent table above — those are **Functions**, not lanes.

---

## Delivery roles (workflow overlays)

A **Delivery role** is a temporary overlay for a Ryan-bound brief. It does **not** create a new agent product row, change the assignee's Lane, or enlarge capabilities.

### PR Steward (v0.1)

- **Owns:** delivery mechanics for an already-bounded Ryan brief (task branch, explicit-refspec push, PR open/update per mutation allowlist, tip CI report, handoff to Ryan).
- **Default actor (now):** OpenAI Codex — subject to reassignment; overlay ≠ model weights.
- **Must:** exact brief only; stop-and-flag on ambiguity; never commit on `main`; explicit refspec push; mutation allowlist only; mechanical/brief-contained findings only; Ryan keeps merge/grant/ledger.
- **Must not:** merge/force-push; grant live/eval/capture/promotion; ledger write; expand scope; act as Copilot audit; impersonate Kiro or Cursor large implementation; reroute large implementation away from Cursor; material architecture/scope/security/product/authorization judgment.
- **GitHub mutations:** open PR; update title/body; supersession/recommended-close links; push with explicit refspec; status comments. Close/reopen/retarget/supersede only when the brief names PR numbers. Unlisted actions (labels, reviewers, CI reruns, branch deletion, thread resolution, merge, etc.) require explicit Ryan authorization.
- **Maturity:** v0.1 spontaneous after the R2b architecture PR delivery (single data point). Expect refinement.

