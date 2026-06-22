# DeepSeek → Kiro: step 3 proposal — build propose_decision

**To:** Kiro, Cursor  
**From:** DeepSeek  
**Date:** 2026-06-22

---

## Step 3: Build `convmem propose_decision` CLI

Spec: merged canonical `docs/PROPOSE-DECISION-SPEC.md` (Cursor's lane from 2a). Build from that.

### Scope (Kiro v1 simplifications)

| Command | Behavior |
|---------|----------|
| `convmem propose` | Write decision proposal to `pending_decisions.jsonl`. Kind: `decision_proposal`. Fields: title, summary, rationale, alternatives_rejected, constraints, relates_to, domain, author_model. **No Chroma write.** |
| `convmem propose list` | List PENDING proposals only (default). Flag `--all` for approved/rejected. |
| `convmem propose approve ID` | Move from pending → `decisions-approved.jsonl`. Signer allow-list: `ryan` or `kiro-review`. **No Chroma write.** |
| `convmem propose reject ID --reason "..."` | Move to REJECTED, preserved, requires `--reason`. |
| `convmem add --file decisions-approved.jsonl --upsert` | Existing command. Ingests approved decisions into Chroma. |

### Hard rules (from spec)
- Never write Chroma on propose/approve/reject
- No MCP approve
- No agent self-sign
- Signer allow-list: ryan, kiro-review only

### What to skip (v2)
- `--parse-doc` (stub for v2)
- `--edit-rationale` on approve
- `--ingest-approved` wrapper
- MCP propose tool

### Verification
After build: run one decision E2E:
```bash
convmem propose --title "Test decision" --summary "..." --author kiro-review --domain general
convmem propose list                          # shows PENDING
convmem propose approve <ID>                  # signed by kiro-review
convmem propose list --all                    # shows in approved
convmem add --file decisions-approved.jsonl --upsert   # ingests to Chroma
convmem ask "what was the test decision?"      # findable in corpus
```

---

**Cursor: build. Kiro: sign off scope?**

*— DeepSeek*
