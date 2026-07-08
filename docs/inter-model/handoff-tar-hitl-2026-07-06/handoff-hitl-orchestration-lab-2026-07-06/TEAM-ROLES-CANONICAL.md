# Canonical agent roles (from docs/AGENT-ROLES.md)

**Protocol SSoT:** `config/agent-protocol.md` (three tiers: shell / MCP-only / paste).

| Agent | Lane | Capability |
|-------|------|------------|
| **Kiro** | Design review, milestone sign-off; session start ritual; **facts via `convmem record --approve-last --signer kiro-review`** | Tier A (shell + MCP) |
| **Cursor** | Implementer on local workstation; global `convmem.mdc` | Tier A (shell + MCP) |
| **Sonnet** | MCP verification (static + live Crush handshake) | Tier A via Cursor |
| **ChatGPT** | Orchestration/strategy; paste-only corpus | Tier C |
| **Crush** | Runtime agent with shell + MCP read; **must run shell ritual** (MCP-only rules ignored in soak) | Tier A |
| **DeepSeek** | **Runtime synthesis only** (`convmem ask` / distill API) | Tier B (MCP-only) — **not a bug-hunter role** |
| **Codex** | Shell + `~/.codex/AGENTS.md`; verification / audit lane; **no MCP** | Tier A (CLI only) |
| **Continue** | MCP read; `instructions=` carries protocol | Tier A |

**Critical distinction:** Crush may **run** DeepSeek V4 as its model weights. That is still **Crush lane** (shell, repo survey, findings). The **DeepSeek row** is the **corpus synthesis API** behind `convmem ask`, not the Crush chat model.

**Session close (all):** `convmem record --relates-to <real id> …` then Ryan `record --approve-last`. Never per-handoff unless Ryan says **record block**.
