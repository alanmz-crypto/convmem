# Agent roles (static — do not duplicate in brief.md)

| Agent | Lane |
|-------|------|
| **Kiro** | Design review, milestone sign-off; session start: `convmem brief` → `ask` → `LATEST.md`; **finish facts via `convmem record --approve-last --signer kiro-review`**, not markdown sign-off |
| **Cursor** | Implementer on canonical dev machine; read `brief.md` + `docs/inter-model/` |
| **Sonnet** | MCP verification (static source + live Crush handshake) |
| **ChatGPT** | Orchestration/strategy; paste-only access to corpus |
| **Crush** | Runtime agent with MCP read tools |
| **DeepSeek** | Runtime synthesis only (`ask` / distill API) |

Cross-model messages: `docs/inter-model/<MODEL>-<date>-<topic>.md`
