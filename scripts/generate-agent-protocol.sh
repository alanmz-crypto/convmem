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
# Tier B + shell preamble + Codex retry note + session close
{
  extract_section TIER_A
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
  echo "## Verify shipped work (DeepSeek / MCP agents)"
  echo ""
  echo "Read \`docs/CODEX-DEEPSEEK-VERIFY.md\` — use \`search_fast\` + \`ask\` for sections marked DeepSeek; ask Ryan to paste shell output for Codex-only steps."
} >> config/agent-protocol-mcp.txt
echo "  -> config/agent-protocol-mcp.txt"

# --- Cursor .mdc rule ---
# Cursor has both shell and MCP, so include Tier A + B + session close
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
  echo "## If you have MCP only — or after Tier A shell ritual (Tier B)"
  echo ""
  extract_section TIER_B
  echo ""
  extract_section SESSION_CLOSE
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
  echo "Do not run \`convmem add\`, \`convmem index\`, or \`convmem verify\` without user direction."
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
  echo "## MCP (after shell ritual, or use MCP first if no shell step yet)"
  echo ""
  extract_section TIER_B
  echo ""
  echo "## Session close"
  echo ""
  extract_section SESSION_CLOSE
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
  echo "## MCP (after shell ritual — not optional)"
  echo ""
  echo "After \`doctor\` + shell \`brief\` + \`unresolved\`: use \`brief(project=<slug>)\` — infer slug from cwd; \`search_fast()\`, \`ask()\`, \`related()\`, \`stats()\`. Read-only. Or \`resources/read\` on \`memories://brief\`."
  echo ""
  echo "**DeepSeek V4 (Flash/Pro) in Crush:** often skips this ritual on alien \"project state\" queries — do **not** start with \`ls\`, git, or docker until convmem steps above complete."
  echo ""
  echo "## Session close"
  echo ""
  extract_section SESSION_CLOSE
  echo ""
  echo "## Workflow routing (when unsure)"
  echo ""
  extract_section WORKFLOW_ROUTING
} > config/crush-rules-convmem.example.md
echo "  -> config/crush-rules-convmem.example.md"

echo ""
echo "All surfaces generated from $SSoT."
echo "Run scripts/deploy-agent-protocol.sh to deploy."
