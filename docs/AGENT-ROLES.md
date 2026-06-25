# Agent roles (static — do not duplicate in brief.md)

| Agent | Lane |
|-------|------|
| **Kiro** | Design review, milestone sign-off; session start: `convmem brief` → `ask` → `LATEST.md`; **finish facts via `convmem record --approve-last --signer kiro-review`**, not markdown sign-off |
| **Cursor** | Implementer on canonical dev machine; read `brief.md` + `docs/inter-model/` |
| **Sonnet** | MCP verification (static source + live Crush handshake) |
| **ChatGPT** | Orchestration/strategy; paste-only access to corpus |
| **Crush** | Runtime agent with MCP read tools |
| **DeepSeek** | Runtime synthesis only (`ask` / distill API) |
| **Codex** | Shell + `AGENTS.md` (`~/.codex/AGENTS.md` global + repo root); change-feed design lane (deferred); no MCP |
| **Continue** | MCP read (`brief`, `search_fast`, `ask`); rules in `~/.continue/config.yaml` |

**Session close (all models):** read `docs/inter-model/SESSION-CLOSE-RECORD.md`; output **`convmem record --relates-to … --summary … --rationale … --author …`** then **`convmem record --approve-last`**. Never `record` alone or fake flags (`session=`, `detail=`). Agent must search for `--relates-to`.

Cross-model messages: `docs/inter-model/<MODEL>-<date>-<topic>.md`
