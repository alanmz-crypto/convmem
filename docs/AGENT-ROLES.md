# Agent roles (static — do not duplicate in brief.md)

**Canonical protocol:** `config/agent-protocol.md` (three capability tiers: shell / MCP-only / paste).
Generated per-surface slices via `scripts/generate-agent-protocol.sh`.

| Agent | Lane | Capability tier |
|-------|------|-----------------|
| **Kiro** | Design review, milestone sign-off; session start: `convmem brief` → `ask` → `LATEST.md`; **finish facts via `convmem record --approve-last --signer kiro-review`**, not markdown sign-off | Tier A (shell + MCP via `~/.kiro/settings/mcp.json` + steering) |
| **Cursor** | Implementer on canonical dev machine; global `convmem.mdc` rule drives session start | Tier A (shell + MCP) |
| **Sonnet** | MCP verification (static source + live Crush handshake) | Tier A via Cursor |
| **ChatGPT** | Orchestration/strategy; paste-only access to corpus | Tier C (paste-only) |
| **Crush** | Runtime agent with shell + MCP read tools | Tier A (shell + MCP; soak #8 showed MCP-only rules ignored) |
| **DeepSeek** | Runtime synthesis only (`ask` / distill API) | Tier B (MCP-only) |
| **Codex** | Shell + `AGENTS.md` (`~/.codex/AGENTS.md` global + repo root); change-feed design lane (deferred); no MCP | Tier A (shell, but no MCP) — use CLI `convmem` commands |
| **Continue** | MCP read (`brief`, `search_fast`, `ask`); MCP `instructions=` carries expanded protocol | Tier A (shell + MCP) |

**Session close (all models):** read `docs/inter-model/SESSION-CLOSE-RECORD.md`; output **`convmem record --relates-to … --summary … --rationale … --author …`** then **`convmem record --approve-last`**. Never `record` alone or fake flags (`session=`, `detail=`). Agent must search for `--relates-to`.

Cross-model messages: `docs/inter-model/<MODEL>-<date>-<topic>.md`
