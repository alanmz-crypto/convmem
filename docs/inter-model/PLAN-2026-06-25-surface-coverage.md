# Post-soak surface coverage plan

**Date:** 2026-06-25  
**Author:** DeepSeek R1 (Continue)  
**Status:** Draft for Cursor Planner review  
**Prerequisite:** Soak data in `docs/inter-model/SOAK-REPORT-2026-06-25.md` (6 sessions, 3 surfaces)

---

## Problem statement

The global convmem protocol ships a canonical source-of-truth (`config/agent-protocol.md`) and deploys per-surface slices. Soak data shows **surface coverage is uneven**:

| Surface | Protocol deployed | Protocol reached agent? | Failure mode |
|---------|------------------|------------------------|--------------|
| Cursor | `convmem.mdc` alwaysApply | ✅ Loaded, but order wrong | brief() before doctor |
| Codex | `~/.codex/AGENTS.md` | ✅ (no soak data yet, assumed working) | — |
| Kiro | `~/.kiro/steering/convmem.md` | ✅ (no soak data yet, assumed working) | — |
| Continue | MCP instructions= + config.yaml rules | ❌ **Not loaded** | Agent ignored convmem entirely — no MCP tools, no shell commands |
| Crush | Stale pre-protocol rules file | ❌ **Not loaded** | MCP initialized but never invoked; old rules only mention search/ask, not session-start |

MCP `instructions=` — the channel we called "highest ROI" — did not carry protocol to Continue or Crush. The `.mdc` file is what actually drives Cursor behavior. For non-Cursor surfaces, we need something else.

---

## Surface-by-surface plan

### 1. Cursor — qualify the `.mdc` ordering (soak data: n=2 Cursor alien sessions, order wrong in 1)

**Problem:** `convmem.mdc` concatenates Tier A (doctor) and Tier B (brief-first) as two numbered lists, both starting with "1." An agent scanning top-down may latch onto the wrong first step.

**Evidence:** Session #2 (willowyhollow-practice): MCP brief() called before doctor. Session #3 (convem repo): correct order, but user had pointed at handoff. Inconclusive.

**Plan:** Do not change `.mdc` structure yet. Wait for ≥3 Cursor-only alien sessions with different task framings. Alternative: add a section header between Tier A and B (`## If you have shell access` / `## If you have MCP only`) so the two lists are visually separated.

**Gate:** If session 7+ shows same order violation, apply headers. If not, ship as-is.

---

### 2. Crush — deploy a global-protocol slice (soak data: session #6, zero convmem)

**Problem:** `~/.config/crush/rules/convmem.md` is pre-protocol. It mentions search/ask but has no session-start protocol (no doctor, no brief, no unresolved). Crush MCP is initialized (`crush.log` shows MCP clients loaded) but never invoked for convmem.

**Evidence:** Session #6 (pavlomassage-practice via Crush + DeepSeek V4 Flash): tools were ls/view/bash/glob/write only. Zero MCP brief/search_fast/ask. `loaded_total:0` skills on turn summary.

**Fix is clear.** Crush has a rules file path; it just needs current content.

**Implementation:**

1. Generate `config/crush-rules-convmem.md` from canonical SSoT (Tier B — MCP-only, no shell)
2. Deploy to `~/.config/crush/rules/convmem.md` (existing path, confirmed in session #6)
3. Preserve any Crush-specific frontmatter if needed (verify current file first)

**Output file:** `config/crush-rules-convmem.example.md`

---

### 3. Continue — shorten rules block (soak data: session #5, zero convmem)

**Problem:** `~/.continue/config.yaml` has a `rules:` block that already mentions convmem — but the agent didn't follow it. Two possible causes:

1. **Rules block is too long/verbose** — MCP `instructions=` also carried the protocol and was also ignored. The entire model may skip non-code channels.
2. **DeepSeek V4 Flash in Continue** may have different instruction-following behavior than Cursor's models.

**Evidence:** Session #5 (pavlomassage-practice via Continue + DeepSeek V4 Flash): List/Bash/Read/docker/curl only. No mode selection exists in Continue (user confirmed). MCP tools were available but not used.

**Fix should be minimal.** Add a terse session-start stanza to the top of the rules block. Do not duplicate the full protocol — just the Tier A shell order:

```yaml
rules:
  - Before answering: run `convmem doctor` (must exit 0), then `convmem brief --stdout-only`, then `convmem unresolved --site <hostname>`.
  - <existing rules...>
```

**Important:** Continue `config.yaml` is protected from agent writes. Ryan must apply this change. The plan should make the exact text copy-pasteable.

---

### 4. ChatGPT — still manual paste, unchanged

No new data. Still `docs/chatgpt-pack/custom-instructions.txt`. Ryan pastes when convenient.

---

### 5. Soak continuation — collect more Cursor alien sessions

The Cursor order-violation hypothesis is not yet confirmed (n=1). Keep testing:

- Open a non-convmem directory in Cursor
- Ask a work-relevant question (not "what's the state?" — different framing)
- Observe: does doctor run first?
- Log in SOAK-REPORT.md

---

### 6. P2 gate — do not accelerate

Session #5 and #6 might look like P2 signal (agents bypass CLI), but the bypass is because the protocol never reached them, not because they need new MCP tools. Fix surface coverage first, then re-evaluate P2.

---

## Implementation order

| Priority | Surface | Action | Owner |
|----------|---------|--------|-------|
| 1 | **Crush** | Generate + deploy Tier B protocol slice | Agent (write + deploy) |
| 2 | **Continue** | Trim config.yaml rules to short session-start stanza | **Ryan** (file protected) |
| 3 | **Cursor** | Observe 2+ more alien sessions before structural changes | Agent (soak mode) |
| 4 | **ChatGPT** | Manual paste (unchanged, low urgency) | Ryan |

---

## Files to touch

| File | Action |
|------|--------|
| `scripts/generate-agent-protocol.sh` | Add Crush slice output |
| `config/crush-rules-convmem.example.md` | Generated (Tier B, MCP-only) |
| `~/.config/crush/rules/convmem.md` | Deploy generated slice |
| `~/.continue/config.yaml` | Add short session-start stanza (Ryan) |
| `docs/inter-model/SOAK-REPORT-2026-06-25.md` | Append future sessions |

---

## Verification

After Crush deploy + Continue yarn:
- Open `~/WordPress/pavlomassage-practice/` in Continue — agent should run `doctor` before repo survey
- Open any random dir in Crush — agent should call `brief()` first (MCP-only)
- Log results in SOAK-REPORT.md

---

## Open questions

- Does Crush use frontmatter in its rules files? Verify against current `~/.config/crush/rules/convmem.md` before overwriting.
- Does Continue use `jsonl` or `yaml` rules format? Current file is YAML; confirm before suggesting edit.
