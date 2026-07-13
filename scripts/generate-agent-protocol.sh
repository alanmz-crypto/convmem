#!/usr/bin/env bash
# generate-agent-protocol.sh — emit per-surface protocol slices from canonical SSoT
#
# Reads config/agent-protocol.md (section-delimited), writes:
#   config/agent-protocol-mcp.txt           — MCP instructions= content
#   config/cursor-rules-convmem.mdc.example  — Cursor global-always rule
#   config/codex-agents-convmem.example.md   — Codex global AGENTS.md
#   config/kiro-steering-convmem.example.md  — Kiro steering file
#   docs/chatgpt-pack/custom-instructions.txt — ChatGPT paste-only pack
#
# Run: bash scripts/generate-agent-protocol.sh
# Edit canonical -> regenerate. Do NOT hand-edit generated files.

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

SSoT="config/agent-protocol.md"
if [ ! -f "$SSoT" ]; then
  echo "ERROR: $SSoT not found. Run from repo root." >&2
  exit 1
fi

mkdir -p config docs/chatgpt-pack

# Helper: extract a section between <!-- SECTION --> markers
extract_section() {
  local marker="$1"
  sed -n "/<!-- ${marker}_START -->/,/<!-- ${marker}_END -->/p" "$SSoT" \
    | sed '1d;$d' \
    | sed 's/^[[:space:]]*//'
}

# --- MCP instructions ---
# Labeled paths: shell (Tier A) → post-shell MCP → MCP-only (Tier B brief-first)
{
  echo "## Path: shell (Tier A)"
  echo ""
  extract_section TIER_A
  echo ""
  echo "## Path: post-shell MCP (after Tier A)"
  echo ""
  extract_section MCP_AFTER_TIER_A
  echo ""
  echo "## Path: MCP-only (Tier B — no shell; brief-first)"
  echo ""
  extract_section TIER_B
  echo ""
  extract_section SESSION_CLOSE
} > config/agent-protocol-mcp.txt
# Append workflow routing for MCP-only agents
{
  echo ""
  echo "## Workflow routing (when unsure)"
  echo ""
  extract_section WORKFLOW_ROUTING
} >> config/agent-protocol-mcp.txt
{
  echo ""
  extract_section TEAM_CHARTER
} >> config/agent-protocol-mcp.txt
{
  echo ""
  echo "## Bounded autonomy"
  echo ""
  extract_section BOUNDED_AUTONOMY
} >> config/agent-protocol-mcp.txt
{
  echo ""
  echo "## Verify shipped work (DeepSeek / MCP agents)"
  echo ""
  echo "Read \`docs/CODEX-DEEPSEEK-VERIFY.md\` — use \`search_fast\` + \`ask\` for sections marked DeepSeek; ask Ryan to paste shell output for Codex-only steps."
} >> config/agent-protocol-mcp.txt
echo "  -> config/agent-protocol-mcp.txt"

# --- Cursor .mdc rule ---
# Shell+MCP: Tier A + MCP_AFTER_TIER_A (not full MCP-only Tier B)
cat > config/cursor-rules-convmem.mdc.example << 'FRONTMATTER'
---
description: convmem cross-session memory — session start/close protocol
alwaysApply: true
---

FRONTMATTER
{
  echo "# convmem — Local knowledge corpus protocol"
  echo ""
  echo "## If you have shell access (Tier A)"
  echo ""
  extract_section TIER_A
  echo ""
  echo "## After Tier A — MCP tools (do not repeat brief)"
  echo ""
  extract_section MCP_AFTER_TIER_A
  echo ""
  extract_section SESSION_CLOSE
  echo ""
  echo "## Handoff vs record"
  echo ""
  echo "- Handoff / **ingest your chat** → \`convmem index --file\` this chat's \`agent-transcripts/...jsonl\` (Track A). **No record block** unless Ryan asks."
  echo "- Do **not** create new markdown logs unless Ryan requested a file."
  echo ""
  extract_section TEAM_CHARTER
  echo ""
  echo "## Bounded autonomy"
  echo ""
  extract_section BOUNDED_AUTONOMY
  echo ""
  echo "## Workflow routing (when unsure)"
  echo ""
  extract_section WORKFLOW_ROUTING
} >> config/cursor-rules-convmem.mdc.example
echo "  -> config/cursor-rules-convmem.mdc.example"

# --- Codex AGENTS.md ---
# Tier A + model-specific notes (Codex sandbox retry)
{
  echo "# convmem — Local knowledge corpus"
  echo ""
  echo "You have access to a local knowledge corpus via convmem. Use it before repeating past work."
  echo ""
  extract_section TIER_A
  echo ""
  echo "## Builder reference"
  echo ""
  echo "Before convmem architecture edits, read the relevant digest in \`docs/builder-reference/\`."
  echo ""
  echo "- \`ousterhout-builder-digest.md\` for module boundaries and protocol surfaces"
  echo "- \`manning-builder-digest.md\` for ranking, chunking, retrieval, and evaluation"
  echo "- \`zeller-builder-digest.md\` for reproduction, triage, and verification"
  echo "- \`hard-parts-builder-digest.md\` for trade-offs, data ownership, and split decisions"
  echo ""
  echo "## Read-only guard"
  echo ""
  echo "Do not run \`convmem add\`, bulk \`convmem index\` (no \`--file\`), or \`convmem verify\` without user direction."
  echo "Allowed: \`convmem index --file <path> [--supersede]\` for session tracking (Tier A)."
  echo ""
  extract_section TEAM_CHARTER
  echo ""
  echo "## Bounded autonomy"
  echo ""
  extract_section BOUNDED_AUTONOMY
  echo ""
  echo "## Codex — no improvised logs"
  echo ""
  echo "- Do **not** create new \`logs/*.md\`, audit files, or handoff markdown unless Ryan explicitly asked for a file."
  echo "- Preserve work: \`convmem index --file\` on **this session's** \`~/.codex/sessions/**/rollout-*.jsonl\` (full chat — not \`history.jsonl\` prompts-only)."
  echo "- Handoff ≠ record — no \`convmem record\` unless Ryan says **record block** or **closing**."
  echo ""
  echo "## Workflow routing (when unsure)"
  echo ""
  extract_section WORKFLOW_ROUTING
  echo ""
  echo "Full cheat sheet: \`docs/MODEL-WORKFLOW.md\`"
  echo ""
  echo "## Verify shipped work (Codex / DeepSeek)"
  echo ""
  echo "Independent checklist: \`docs/CODEX-DEEPSEEK-VERIFY.md\` — pytest, smoke scripts, MCP spot-checks. Do not trust prior chat claims without running it."
} > config/codex-agents-convmem.example.md
echo "  -> config/codex-agents-convmem.example.md"

# --- Kiro steering file ---
# inclusion: always — session ritual must load every turn (auto skipped on "project state"; soak #13)
cat > config/kiro-steering-convmem.example.md << 'FRONTMATTER'
---
inclusion: always
name: convmem
description: Session-start convmem protocol. Always run before repo survey, stack_ps, docker, git, or wp-cli.
---

FRONTMATTER
{
  echo "# convmem — Local knowledge corpus"
  echo ""
  echo "You have **shell** (\`convmem\` CLI) and **MCP** (\`@convmem/brief\`, etc.) on this machine."
  echo ""
  echo "**Before answering anything** (including \`stack_ps\`, docker, git, wp-cli, or directory listing):"
  echo ""
  extract_section TIER_A
  echo ""
  echo "## After Tier A — MCP tools (do not repeat brief)"
  echo ""
  extract_section MCP_AFTER_TIER_A
  echo ""
  echo "## Session close"
  echo ""
  extract_section SESSION_CLOSE
  echo ""
  echo "## Kiro — handoff vs record (critical)"
  echo ""
  echo "- Verification, read-only review, bug audit, or Ryan says **ingest your chat** → run \`convmem index --file\` on **this session's** \`~/.kiro/sessions/.../messages.jsonl\`. **Stop. No record block.**"
  echo "- **Never volunteer** \`convmem record\` at task end — important work is already in chat ingest."
  echo "- \`convmem record\` **only** when Ryan says **record block**, **closing**, or **end session**."
  echo ""
  extract_section TEAM_CHARTER
  echo ""
  echo "## Bounded autonomy"
  echo ""
  extract_section BOUNDED_AUTONOMY
  echo ""
  echo "## Workflow routing (when unsure)"
  echo ""
  extract_section WORKFLOW_ROUTING
} >> config/kiro-steering-convmem.example.md
echo "  -> config/kiro-steering-convmem.example.md"

# --- ChatGPT paste-only pack ---
{
  echo "# convmem — Local knowledge corpus (paste-only instructions)"
  echo ""
  echo "You cannot run CLI commands. You can interpret pasted convmem output."
  echo ""
  extract_section TIER_C
  echo ""
  echo "## Strategy lane (ChatGPT / Claude Cloud)"
  echo ""
  echo "Orchestration and role-charter review only — paste-only, no code edits, no prod writes. Full charter: \`docs/inter-model/TEAM-CHARTER-2026-07-06.md\`"
} > docs/chatgpt-pack/custom-instructions.txt
echo "  -> docs/chatgpt-pack/custom-instructions.txt"

# --- README for ChatGPT pack ---
cat > docs/chatgpt-pack/README.md << 'EOF'
# ChatGPT paste-only pack

## Setup (one-time)
1. Open ChatGPT webUI → Settings → Personalization → Custom instructions
2. Copy the contents of `custom-instructions.txt` into the "What would you like ChatGPT to know?" field
3. Save

## Usage
- At session start: ask Ryan for `convmem brief --stdout-only`
- At session close: suggest `convmem record` blocks for Ryan to run

## Notes
- ChatGPT cannot run CLI commands — never pretend to call convmem
- Session-close record blocks use the format in `docs/inter-model/SESSION-CLOSE-RECORD.md`
EOF
echo "  -> docs/chatgpt-pack/README.md"

# --- Crush rules (Tier A — shell + MCP; soak #8: MCP-only ignored) ---
{
  echo "# convmem — Local knowledge corpus (shell + MCP)"
  echo ""
  echo "convmem is a local-first knowledge corpus on this machine. You have **bash** and MCP read access."
  echo ""
  echo "**MANDATORY before repo survey, docker, git, \`stack_ps\`, or answering project-state questions:**"
  echo ""
  extract_section TIER_A
  echo ""
  echo "## After Tier A — MCP tools (do not repeat brief)"
  echo ""
  extract_section MCP_AFTER_TIER_A
  echo ""
  echo "**DeepSeek V4 (Flash/Pro) in Crush:** often skips this ritual on alien \"project state\" queries — do **not** start with \`ls\`, git, or docker until convmem steps above complete."
  echo ""
  echo "## Session close"
  echo ""
  extract_section SESSION_CLOSE
  echo ""
  echo "## Crush — handoff vs record"
  echo ""
  echo "- You are **Crush lane**; never call yourself DeepSeek in handoff text (DeepSeek V4 is runtime weights only)."
  echo "- Handoff / **ingest your chat** → \`convmem index --file <project>/.crush/crush.db\` (Track A). **No record block** unless Ryan asks."
  echo "- Do **not** create new markdown logs unless Ryan requested a file."
  echo ""
  extract_section TEAM_CHARTER
  echo ""
  echo "## Bounded autonomy"
  echo ""
  extract_section BOUNDED_AUTONOMY
  echo ""
  echo "## Workflow routing (when unsure)"
  echo ""
  extract_section WORKFLOW_ROUTING
} > config/crush-rules-convmem.example.md
echo "  -> config/crush-rules-convmem.example.md"

echo ""
echo "All surfaces generated from $SSoT."
echo "Run scripts/deploy-agent-protocol.sh to deploy."
