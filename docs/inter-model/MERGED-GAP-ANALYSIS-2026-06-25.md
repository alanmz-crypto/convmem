# Merged gap analysis — global convmem protocol rollout

**Sources:**
- `GLOBAL-CONVMEM-PROTOCOL-PLANNER.md` — the plan under review
- `GLOBAL-PLANNER-GAP-ANALYSIS.md` — Continue (DeepSeek v4 via convmem MCP)
- `CODEX-2026-06-25-global-convmem-protocol-insights.md` — Codex assessment

**Date:** 2026-06-25  
**Audience:** Cursor, Codex, Kiro, human — any model building or critiquing the global rollout

---

## Verdict: will it work?

**Yes — with 9 gaps to fill for full system-wide coverage, 2 of which are blockers.** Both analyses independently agree: the architecture is correct (single SSoT → generate per-surface slices → deploy script). The surface wiring is ~80% complete. The gaps are in *content that flows through* each surface, not in surface topology.

---

## What Codex caught that Continue missed

**1. Protocol-order conflict (blocker)**

The planner says `brief` first. The existing `AGENTS.md` says `doctor` first. If both deploy globally, agents inherit contradictory startup sequences — and the one that wins depends on which surface they enter through.

```
AGENTS.md:   doctor → brief → unresolved
Planner:     brief → doctor → unresolved
```

This is a real bug. If Cursor loads `convmem.mdc` + reads `AGENTS.md` in a convmem repo, it gets two different orders. The canonical protocol must pick one and the deploy script must ensure all other surfaces point to it.

**2. Capability tiers**

Codex frames the startup protocol as a runtime decision tree, not a single instruction block:

```
if shell:         doctor → brief → unresolved
elif MCP:         brief → search_fast → ask
elif paste-only:  wait for brief text from user
```

Continue's analysis had the MCP/shell split but as a side note in Gap 1. Codex makes it the structural spine of the protocol. Each tier needs its own protocol slice generated from the same SSoT, and the deployer writes the right one to each surface.

**3. Path detection in deployer**

Continue's Gap 4 covers `.md`→`.mdc` specifically. Codex goes deeper: the deploy script itself should detect actual client paths rather than hardcoding `~/.cursor/rules/convmem.mdc`. If the user has a nonstandard home directory or Cursor installed differently, the deploy script should discover the real path.

**4. Alien workspace verification matrix**

Codex lists a systematic matrix Continue didn't: blank repo, no repo, no shell, no MCP, different home directory. Continue's surface audit is per-tool; Codex's is per-scenario. Both matter, but Codex's catches edge cases Continue's table doesn't (e.g., "agent spawned in `/tmp` with no git repo and no shell access").

---

## What Continue caught that Codex missed

| Finding | Codex covered? |
|---------|---------------|
| `.md` → `.mdc` Cursor format blocker (Gap 4) | Partial — mentions path mismatch but not the format consequence |
| `brief` docstring "call first" (Gap 2) | No |
| Codex sandbox network override (Gap 3) | No — Codex itself didn't flag its own sandbox problem |
| `unresolved` in MCP instructions (Gap 5) | No |
| Severity ranking with implementation order | No — Codex's is judgment-based, not ranked |

---

## Merged gap list (both analyses)

| # | Gap | Source | Severity |
|---|-----|--------|----------|
| 1 | **Protocol-order conflict**: AGENTS.md vs planner disagree on doctor↔brief order | Codex | **Blocker** |
| 2 | **`.mdc` format**: Cursor global-always requires `.mdc`, existing file is `.md` | Continue | **Blocker** |
| 3 | **Capability tiers**: protocol must fork by agent capability (shell / MCP-only / paste) | Codex | High |
| 4 | **MCP shell fallback**: instructions don't mention doctor/unresolved even though shell agents can run them | Continue | High |
| 5 | **`brief` docstring**: needs "call this first" preamble | Continue | High |
| 6 | **Codex sandbox**: network override not in canonical — ask fails in alien repos | Continue | Medium-high |
| 7 | **Path detection**: deploy script should discover real paths not hardcode them | Codex | Medium |
| 8 | **Alien workspace matrix**: blank repo, no repo, no shell, no MCP, nonstandard home | Codex | Medium |
| 9 | **`unresolved` in MCP proto**: agents need instruction to check `unresolved_count` | Continue | Medium |

---

## Consensus points (both analyses agree)

| Design decision | Why it's right |
|----------------|----------------|
| Single SSoT (`config/agent-protocol.md`) | No drift between surfaces. One file to audit, one file to update |
| MCP `instructions=` as highest-ROI channel | Covers Cursor, Continue, Kiro, Crush in one edit. Agents read this before any tool call |
| Deploy + recovery script | Clean-room restore after machine rebuild. RECOVER.md step 8 |
| `alwaysApply: true` Cursor rule for alien workspaces | This IS the mechanism. Without it, agents in `~/WordPress/*` never see convmem |
| Per-surface generation, not one-size-fits-all | MCP slice ≠ Cursor rule ≠ Codex AGENTS.md. Same SSoT, different outputs |
| MCP/shell lane separation | Correct distinction — MCP-only agents vs agents with Bash. Needs fallback note |

---

## Surface audit (current → target)

| Surface | Current state | Plan target | Works? | Gap |
|---------|--------------|-------------|--------|-----|
| **Cursor** | `~/.cursor/rules/convmem.md` (no `.mdc`, no `alwaysApply`) | `~/.cursor/rules/convmem.mdc` with `alwaysApply: true` | ✅ Yes — `.mdc`+frontmatter is the global-always mechanism | Deploy script must handle `.md`→`.mdc` migration |
| **MCP** | 5-line `instructions=` stub | Loads from `config/agent-protocol-mcp.txt` | ✅ **Highest ROI** — every MCP client sees it before first tool call | See merged gap list |
| **Codex** | Already has `~/.codex/AGENTS.md` with ritual | Sync from template to prevent drift | ✅ Already working globally | Sandbox network override not in canonical protocol |
| **Kiro** | `~/.kiro/steering/convmem.md` exists | Sync from template | ✅ Works | Minor: verify Kiro's `inclusion: auto` frontmatter preserved |
| **Continue** | Convmem rules already in `config.yaml` | Trim to reference MCP instructions | ✅ MCP expansion covers it | Current rules already effective; trim is optional |
| **ChatGPT** | None | Paste-only pack | ✅ Low priority, structurally simple | None |

---

## Detailed gaps (from Continue analysis)

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

## Detailed gaps (from Codex analysis)

### What looks right

- The core idea matches the corpus: per-project `AGENTS.md` does not scale globally; user-level config is the right lever.
- The current runtime surfaces already point in that direction:
  - Cursor global rules in `~/.cursor/rules/...`
  - Codex global instructions in `~/.codex/AGENTS.md`
  - MCP instructions in `mcp_server.py`
  - Recovery/deployment documented in `docs/RECOVER.md`
- The corpus also confirms the "blank-slate across folders" problem and the preference for global rules over MCP-only instructions.

### What will break if shipped as-is

- The plan is not yet inclusive across actual client surfaces because it assumes too much uniformity:
  - Cursor and Codex have different real config paths and file formats.
  - ChatGPT cannot run shell commands, so it needs a separate paste-only protocol.
  - MCP clients may or may not have shell access, so "brief first, then doctor/unresolved" needs a no-shell fallback.
- There is already a path mismatch in the repo vs machine:
  - The planner references `~/.cursor/rules/convmem.mdc`
  - The real file on this machine is `~/.cursor/rules/convmem.md`
  - That kind of mismatch is exactly what makes "works from any folder" fail in practice.
- There is also a protocol-order conflict:
  - Repo `AGENTS.md` says `doctor` first, then `brief`, then `unresolved`
  - The planner wants `brief` first in the global protocol
  - If you don't reconcile that, agents will inherit contradictory startup rules depending on which surface they enter through.

### How to make it more inclusive

1. Make one canonical protocol file in the repo and generate every surface from it.
2. Split the protocol into capability tiers:
   - shell-capable
   - MCP-only
   - paste-only / ChatGPT
3. Add a small installer/deployer that detects the actual client paths on the machine instead of hardcoding one path.
4. Make the startup rule tolerant:
   - if shell exists, run `doctor` and `brief`
   - if shell does not exist, use MCP `brief` and `search_fast`
   - if neither exists, fall back to pasted protocol text
5. Add a verification matrix for "alien workspace" cases:
   - blank repo
   - no repo
   - no shell
   - no MCP
   - different home directory / OS path layout

### Codex's judgment

- The plan will work for your own machine if you finish the deployment pieces.
- It will not be truly inclusive until it handles client capability differences and path detection instead of assuming a single global shape.
- The highest-value fix is to make the protocol generator-driven and client-aware, not just broader in scope.

---

## Bottom line

The architecture is right. Both analyses agree on the core pattern: single SSoT, per-surface generation, deploy script, MCP as highest-ROI channel. Ship with the 9 gaps filled and agents will run `doctor → brief → unresolved` from any folder, on any repo, without prompting.

### Implementation order (merged priority)

1. **Resolve protocol-order conflict** (blocker) — pick `doctor → brief → unresolved` or `brief → doctor → unresolved`, apply consistently across all surfaces
2. **Fix `.md` → `.mdc` Cursor format** (blocker) — deploy script migration + `alwaysApply: true`
3. **Add capability tiers** to canonical protocol (shell / MCP-only / paste)
4. **Add MCP shell fallback** to `instructions=`
5. **Add "call this first"** to `brief` docstring
6. **Add Codex sandbox override** to canonical protocol
7. **Add path detection** to deploy script
8. **Create alien workspace verification matrix**
9. **Add `unresolved_count` usage** to MCP instructions
