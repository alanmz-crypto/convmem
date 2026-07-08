# Agent roles (static — do not duplicate in brief.md)

**Canonical protocol:** `config/agent-protocol.md` (three capability tiers: shell / MCP-only / paste).
Generated per-surface slices via `scripts/generate-agent-protocol.sh`.

| Agent | Lane | Capability tier |
|-------|------|-----------------|
| **Kiro** | Design review, milestone sign-off; session start: `convmem brief` → `ask` → `LATEST.md`; **finish facts via `convmem record --approve-last --signer kiro-review`**, not markdown sign-off | Tier A (shell + MCP via `~/.kiro/settings/mcp.json` + steering) |
| **Cursor** | Implementer on local workstation; global `convmem.mdc` rule drives session start | Tier A (shell + MCP) |
| **Sonnet** | MCP verification (static source + live Crush handshake) | Tier A via Cursor |
| **ChatGPT** | Orchestration/strategy; paste-only access to corpus | Tier C (paste-only) |
| **Crush** | Runtime agent with shell + MCP read tools | Tier A (shell + MCP; soak #8 showed MCP-only rules ignored) |
| **DeepSeek** | Runtime synthesis only (`ask` / distill API) | Tier B (MCP-only) |

**DeepSeek vs Crush:** DeepSeek row = Tier B synthesis API behind `convmem ask` only — not a bug-hunter. Crush running DeepSeek V4 weights is still **Crush lane** (Tier A shell). Bug discovery owner = **Crush**, not DeepSeek. Full audit: [`docs/inter-model/TEAM-CHARTER-2026-07-06.md`](inter-model/TEAM-CHARTER-2026-07-06.md).

| **Codex** | Shell + `AGENTS.md` (`~/.codex/AGENTS.md` global + repo root); change-feed design lane (deferred); no MCP | Tier A (shell, but no MCP) — use CLI `convmem` commands |
| **Continue** | MCP read (`brief`, `search_fast`, `ask`); MCP `instructions=` carries expanded protocol | Tier A (shell + MCP) |

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

Kernel: [`PLANNING-PROTOCOL.md`](PLANNING-PROTOCOL.md). Do not add Planner/Reviewer
rows to the agent table above — those are **Functions**, not lanes.

