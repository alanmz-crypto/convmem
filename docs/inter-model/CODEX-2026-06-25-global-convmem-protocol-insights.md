# Global convmem protocol insights

Shared note for critique/build follow-up on whether the protocol can start from any folder and how to make it more inclusive.

## Verbatim note

Short version: yes, the architecture is sound, but the plan as written will only work reliably if you treat “system-wide” as “installed into each tool’s user-level config,” not as one repo file that magically covers every workspace.

What looks right
- The core idea in [GLOBAL-CONVMEM-PROTOCOL-PLANNER.md](/home/lauer/Projects/convmem/GLOBAL-CONVMEM-PROTOCOL-PLANNER.md) matches the corpus: per-project `AGENTS.md` does not scale globally; user-level config is the right lever.
- The current runtime surfaces already point in that direction:
  - Cursor global rules in `~/.cursor/rules/...`
  - Codex global instructions in `~/.codex/AGENTS.md`
  - MCP instructions in [mcp_server.py](/home/lauer/Projects/convmem/mcp_server.py)
  - Recovery/deployment documented in [docs/RECOVER.md](/home/lauer/Projects/convmem/docs/RECOVER.md)
- The corpus also confirms the “blank-slate across folders” problem and the preference for global rules over MCP-only instructions.

What will break if you ship it as-is
- The plan is not yet inclusive across actual client surfaces because it assumes too much uniformity:
  - Cursor and Codex have different real config paths and file formats.
  - ChatGPT cannot run shell commands, so it needs a separate paste-only protocol.
  - MCP clients may or may not have shell access, so “brief first, then doctor/unresolved” needs a no-shell fallback.
- There is already a path mismatch in the repo vs machine:
  - The planner references `~/.cursor/rules/convmem.mdc`
  - The real file on this machine is `~/.cursor/rules/convmem.md`
  - That kind of mismatch is exactly what makes “works from any folder” fail in practice.
- There is also a protocol-order conflict:
  - Repo [AGENTS.md](/home/lauer/Projects/convmem/AGENTS.md) says `doctor` first, then `brief`, then `unresolved`
  - The planner wants `brief` first in the global protocol
  - If you don’t reconcile that, agents will inherit contradictory startup rules depending on which surface they enter through.

How to make it more inclusive
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
5. Add a verification matrix for “alien workspace” cases:
   - blank repo
   - no repo
   - no shell
   - no MCP
   - different home directory / OS path layout

My judgment
- The plan will work for your own machine if you finish the deployment pieces.
- It will not be truly inclusive until it handles client capability differences and path detection instead of assuming a single global shape.
- The highest-value fix is to make the protocol generator-driven and client-aware, not just broader in scope.

If you want, I can turn this into a concrete patch list for the planner itself, including the exact wording changes I’d make to remove the path mismatches and add the capability tiers.
