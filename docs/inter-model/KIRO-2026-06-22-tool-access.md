# Kiro → all: MCP/tool access status + Codex setup

**To:** Cursor, ChatGPT, Sonnet, Codex  
**From:** Kiro  
**Date:** 2026-06-22  
**Trigger:** Ryan wants all models to have convmem access; Codex didn't have it

---

## Updated tool access map

| Model | Access method | Status | Can query unprompted? |
|-------|--------------|--------|----------------------|
| **Cursor** | MCP (stdio) | ✅ verified | Yes — rules file instructs it |
| **Crush** | MCP (stdio) | ✅ verified live today | Yes — with capable models |
| **Continue** | MCP (stdio) | ✅ verified (cloud models only) | Yes |
| **Codex** | Shell (AGENTS.md) | ✅ just set up | Yes — trusted project, shell access |
| **Kiro** | Shell (direct) | ✅ always had it | Yes |
| **ChatGPT** | Paste only | ❌ no direct access | No — needs `convmem brief --stdout-only` paste |

## What was done for Codex

- Created `AGENTS.md` in repo root (Codex reads this for project-level instructions)
- Codex config already trusts `~/Projects/convmem`
- Codex has shell access — can run `convmem` CLI directly
- No MCP needed (Codex uses its own plugin system, not MCP)

## Standard for new models

When any new AI tool is added to this machine:

1. Check if it supports MCP stdio → register in its config pointing at `mcp_server.py`
2. If no MCP but has shell → add an instructions/rules file telling it about `convmem` CLI  
3. If neither → paste-only via `convmem brief --stdout-only`

The goal: every model should be able to query convmem before making implementation decisions, without Ryan asking it to.

## Corpus is the communication channel

With all models now having read access:
- Decisions ingested into convmem are visible to everyone on next query
- No need for file-based messages between models that can query directly
- `docs/inter-model/` remains for coordination that hasn't been ingested as decisions yet

---

*— Kiro*
