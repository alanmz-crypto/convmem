# Global convmem protocol — gap analysis

**Source:** `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md`  
**Auditor:** Continue (DeepSeek v4 via convmem MCP)  
**Date:** 2026-06-25  
**Audience:** Cursor, Codex, Kiro, human — any model building or critiquing the global rollout

---

## Verdict: will it work?

**Yes — with 5 gaps to fill for full system-wide coverage.** The architecture is correct; the surface wiring is ~80% complete. The gaps are in the *content that flows through* each surface, not in the surface topology itself.

---

## Surface audit (current → target)

| Surface | Current state | Plan target | Works? | Gap |
|---------|--------------|-------------|--------|-----|
| **Cursor** | `~/.cursor/rules/convmem.md` (no `.mdc`, no `alwaysApply`) | `~/.cursor/rules/convmem.mdc` with `alwaysApply: true` | ✅ Yes — `.mdc`+frontmatter is the global-always mechanism | Deploy script must handle `.md`→`.mdc` migration |
| **MCP** | 5-line `instructions=` stub | Loads from `config/agent-protocol-mcp.txt` | ✅ **Highest ROI** — every MCP client sees it before first tool call | See gaps below |
| **Codex** | Already has `~/.codex/AGENTS.md` with ritual | Sync from template to prevent drift | ✅ Already working globally | Sandbox network override not in canonical protocol |
| **Kiro** | `~/.kiro/steering/convmem.md` exists | Sync from template | ✅ Works | Minor: verify Kiro's `inclusion: auto` frontmatter preserved |
| **Continue** | Convmem rules already in `config.yaml` | Trim to reference MCP instructions | ✅ MCP expansion covers it | Current rules already effective; trim is optional |
| **ChatGPT** | None | Paste-only pack | ✅ Low priority, structurally simple | None |

---

## 5 gaps for true inclusivity

### Gap 1: MCP instructions must carry the shell fallback path

The plan says MCP clients can't run `doctor`/`unresolved` — but agents with Bash access (Cursor, Continue, Codex) **can**. MCP instructions should say:

> "If shell is available, run `convmem doctor` (must exit 0) and `convmem unresolved` after `brief`. If shell is unavailable, use brief's `unresolved_count` field."

Without this, shell-capable agents in non-convmem repos will skip doctor entirely even though they could run it. Currently `mcp_server.py:21` has no mention of doctor at all.

**Impact:** Medium. An agent that reads only MCP instructions and has Bash will miss the pre-flight health check entirely — it will jump straight to `brief` without confirming Ollama/Chroma are healthy. In a cold-start or corrupted-env scenario, this means silent failures before any useful work begins.

**Fix:** Add ~3 lines to `instructions=` string. If loading from `config/agent-protocol-mcp.txt`, add a "Shell preamble (MCP clients with Bash)" section.

---

### Gap 2: `brief` MCP docstring needs a "call first" signal

The plan mentions this as an aside but not as a structural requirement. The current docstring starts with `"Session orientation: corpus state..."` — it should lead with:

> "**Call this first every session.** Session orientation..."

Agents read tool docstrings even when they ignore server instructions. This is a one-line change with outsized impact — it reaches every agent in every MCP client regardless of whether they parse the server-level `instructions=` field.

**Impact:** Low effort, high leverage. In debugging sessions where the server instructions are truncated or ignored, the tool docstring is the last line of defense.

**Fix:** Prepend to `brief()` docstring in `mcp_server.py`. Also consider adding to `search_fast()`: "For prior work, use this before guessing."

---

### Gap 3: Codex sandbox network override belongs in canonical protocol

Codex defaults to `network_access = false`. On random repos (no `.codex/config.toml`), `convmem ask` will fail even if the protocol is loaded. The canonical protocol should include:

> "Codex sessions: if `ask` fails with network error, run with login shell: `bash -lc 'convmem ask "..."`' or approve network once."

This is currently only in `~/.codex/AGENTS.md` — it should be in `config/agent-protocol.md` so it flows to all surfaces including Cursor (which can also use Codex as backend).

**Impact:** Medium-high. Without this, Codex agents in alien repos will fail on `ask` and potentially abandon convmem entirely after one sandbox error. The first-run experience determines whether agents *trust* convmem or route around it.

**Fix:** Add a "Model-specific notes" section to `config/agent-protocol.md` with the Codex sandbox override. Also add to the MCP slice: "If synthesis fails with network error, retry with login shell."

---

### Gap 4: Deploy script needs `.md` → `.mdc` migration for Cursor

The existing `~/.cursor/rules/convmem.md` (no `.mdc` extension) is **not** an `alwaysApply` rule — Cursor only processes `.mdc` files for global-always mode. The deploy script should:

1. Remove `convmem.md` (it's stale/ignored by Cursor's global-always mechanism)
2. Deploy `convmem.mdc` with `alwaysApply: true`

Without this, the old `.md` file might confuse or shadow the new rule. More importantly, the old file has zero effect — it's dead bytes in the rules directory.

**Impact:** High. This is the difference between "protocol deployed" and "protocol actually loaded." The `.md` file exists but Cursor doesn't apply it globally. Unless the deploy script handles this migration explicitly, the rollout will silently fail for Cursor.

**Fix:** `scripts/deploy-agent-protocol.sh` should check for `convmem.md`, warn if found, remove it, then write `convmem.mdc`.

---

### Gap 5: MCP `instructions=` needs `unresolved` mention even before P2 MCP tool

The plan defers MCP `unresolved` tool to P2, but the `brief` payload already includes `unresolved_count`. MCP instructions should note:

> "Check `unresolved_count` in the brief response. If >0 and working on a client site, include `convmem unresolved --site <hostname>` in your shell preamble."

Without this, agents have no signal that open observations exist — the `unresolved_count` value is in the JSON payload but agents need an instruction to *look at it*.

**Impact:** Medium. Agents will still get brief data; this gap is about active prompting vs passive data. Adding the instruction makes open-issue awareness *mandated* rather than *discoverable.*

**Fix:** Add to MCP instructions. When P2 MCP `unresolved` tool is built, remove the shell preamble and promote to a first-class tool.

---

## What's solid / correct

| Design decision | Why it's right |
|----------------|----------------|
| Single SSoT (`config/agent-protocol.md`) | No drift between surfaces. One file to audit, one file to update |
| MCP `instructions=` as highest-ROI channel | Covers Cursor, Continue, Kiro, Crush in one edit. Agents read this before any tool call |
| Deploy + recovery script | Clean-room restore after machine rebuild. RECOVER.md step 8 |
| `alwaysApply: true` Cursor rule for alien workspaces | This IS the mechanism. Without it, agents in `~/WordPress/*` never see convmem |
| MCP/shell lane separation | Correct distinction — MCP-only agents vs agents with Bash. Just needs the fallback note (Gap 1) |

---

## Bottom line

The architecture is right. Ship with the 5 gaps filled and agents will run `doctor → brief → unresolved` from any folder, on any repo, without prompting. The plan as written covers ~80% of surfaces — the gaps are in the **content that flows through** those surfaces, not the surface wiring itself.

### Severity ranking for implementation

1. **Gap 4** (`.md` → `.mdc` migration) — **blocker**: silent Cursor failure
2. **Gap 1** (MCP shell fallback) — **high**: agents skip doctor
3. **Gap 2** (`brief` docstring) — **low effort, high leverage**: one line
4. **Gap 3** (Codex sandbox in canonical) — **medium-high**: first-run trust
5. **Gap 5** (unresolved mention in MCP instructions) — **medium**: active vs passive prompting
