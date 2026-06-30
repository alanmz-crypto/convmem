# Handoff: Global convmem protocol plan — for Claude Cloud review

**Date:** 2026-06-25  
**From:** Kiro (reviewer lane) + Ryan  
**To:** Claude Cloud (Opus or Sonnet)  
**Purpose:** Judge the global rollout plan and merged gap analysis; recommend implementation order and flag anything unsound.

---

## What is convmem?

A local-first knowledge corpus on Ryan's miniPC. It indexes AI chat transcripts (Cursor, Continue, Kiro, ChatGPT, Crush) into ChromaDB, embeds them with Ollama (nomic-embed-text), and exposes search/ask/related via CLI and MCP. 1434 knowledge units, 329 summaries.

Agents use it to recall past decisions, check open security findings, and avoid repeating work. The system works — golden eval 10/10, doctor exit 0, test suite 126/126.

---

## The problem being solved

The convmem session-start protocol (`doctor → brief → unresolved → search before guessing`) only reaches agents when they happen to open a project with an AGENTS.md that tells them about it. Open Cursor in `~/WordPress/willowyhollow-practice/` — blank slate. Spin up Codex on a random repo — blank slate. ChatGPT webUI — no access at all.

**Goal:** instructions follow the human, not the directory. Every AI surface Ryan uses should know about convmem at session start, regardless of working directory.

---

## The proposed solution

Single canonical source-of-truth (`config/agent-protocol.md`) in the convmem repo. A generator script produces per-surface slices. A deploy script pushes them to user-level configs:

- **Cursor:** `~/.cursor/rules/convmem.mdc` with `alwaysApply: true`
- **MCP:** expanded `instructions=` in `mcp_server.py` (covers Cursor, Continue, Kiro, Crush simultaneously)
- **Codex:** `~/.codex/AGENTS.md` synced from template
- **Kiro:** `~/.kiro/steering/convmem.md` synced
- **ChatGPT:** paste-only custom instructions

Three capability tiers:
- **Tier A (shell):** `doctor → brief → unresolved`
- **Tier B (MCP-only):** `brief() → check unresolved_count → search_fast/ask`
- **Tier C (paste-only):** ask human for `brief --stdout-only` output

---

## What has been critiqued already

Two independent analyses (Continue/DeepSeek + Codex) reviewed the plan. Their merged findings are in `MERGED-GAP-ANALYSIS-2026-06-25.md` (included in this archive). They agree on:

- Architecture is correct (SSoT → generate → deploy)
- 9 gaps, 2 blockers
- MCP `instructions=` expansion is highest ROI
- `.mdc` format is required for Cursor global-always (current `.md` is inert)
- Protocol order must be canonicalized (`doctor → brief → unresolved`)

---

## What Claude Cloud should judge

1. **Is the architecture sound?** SSoT → generated surfaces → deploy script → recovery doc. Is there a simpler approach that achieves the same coverage?

2. **Are the capability tiers correct?** Shell / MCP-only / paste-only. Is this the right split? Are there agents that don't fit?

3. **Priority order.** The merged analysis says: fix blockers (order conflict + .mdc format) → MCP expansion → rest. Is this right, or should MCP expansion come first since it covers 4 surfaces at once?

4. **Maintenance burden.** One canonical file + generator + deploy script. Is this over-engineered for a single-user system? Would "just hand-write 5 files and keep them in sync manually" be more pragmatic?

5. **The generator approach.** Is a shell script that reads markdown and emits per-surface slices the right tool? Or would a simpler approach (e.g., symlinks, includes, or just copying the same content with minor tweaks) be more robust?

6. **Gap completeness.** Are there gaps the two analyses missed? Failure modes not covered by the alien-workspace matrix?

7. **Codex sandbox problem.** Codex can't reach localhost (Ollama). The plan says "retry with login shell." Is there a better architectural fix, or is this the right pragmatic workaround?

8. **Risk of over-prompting.** If every surface loads a full protocol, do agents waste context on instructions they don't need? Should the MCP slice be minimal and the Cursor rule comprehensive, or vice versa?

---

## Files in this archive

```
handoff-claude-cloud-2026-06-25/
├── HANDOFF.md                              (this file)
├── GLOBAL-CONVMEM-PROTOCOL-PLANNER.md      (the plan under review)
├── MERGED-GAP-ANALYSIS-2026-06-25.md       (Continue + Codex critiques merged)
├── GLOBAL-PLANNER-GAP-ANALYSIS.md          (Continue/DeepSeek analysis)
├── CODEX-2026-06-25-global-convmem-protocol-insights.md  (Codex analysis)
├── CODEX-2026-06-25-global-planner-critique-summary.md   (Codex summary)
├── AGENTS.md                               (current repo AGENTS.md)
├── ROADMAP-DRAFT.md                        (current project state)
├── mcp_server.py                           (current MCP server — see instructions= stub)
├── convmem.py                              (CLI entry point — for reference)
├── cursor-rules-convmem.md                 (current inert Cursor rule)
└── brief-output.txt                        (live brief output for context)
```

---

## Constraints

- Single user (Ryan), single machine (miniPC), ~6 AI tools
- Corpus is local-only (no cloud sync)
- MCP server runs via stdio (Cursor/Continue/Kiro/Crush all connect)
- Codex sandboxes block localhost by default
- ChatGPT has no shell or MCP — paste only
- Recovery must work from scratch (machine rebuild scenario)
- No auto-writes to corpus without human approval

---

## Expected output from Claude Cloud

1. Verdict: ship as planned / modify / rethink
2. Recommended implementation order (with reasoning)
3. Any gaps or risks not caught by the two prior analyses
4. Opinion on generator vs manual sync for a single-user system
5. Specific wording suggestions for the MCP `instructions=` expansion if you have them
