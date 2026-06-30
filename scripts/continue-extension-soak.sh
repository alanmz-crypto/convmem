#!/usr/bin/env bash
# Continue IDE extension soak — wiring check + copy-paste prompts + optional grade.
# MCP works in Plan or Agent mode (not plain Chat).
# Models: daily qwen2.5-coder:14b; heavy qwen3-coder:30b (override: CONTINUE_MODEL=…).
set -euo pipefail

ROOT="${CONVMEM_ROOT:-$HOME/Projects/convmem}"
SESSION_DIR="${SESSION_DIR:-$HOME/.continue/sessions}"
CONTINUE_MODEL="${CONTINUE_MODEL:-qwen2.5-coder:14b}"
CONTINUE_MODEL_HEAVY="${CONTINUE_MODEL_HEAVY:-qwen3-coder:30b}"

usage() {
  cat <<EOF
Usage: $0 [prompts|grade|grade-latest|all]

  prompts       Print extension verify prompts (default)
  grade FILE    Grade a session JSON (named-tool + alien ritual)
  grade-latest  Grade newest session in ~/.continue/sessions/
  all           Run verify-continue.sh, print prompts, then grade-latest

Open Continue sidebar → **Plan or Agent** mode → ${CONTINUE_MODEL} (heavy: ${CONTINUE_MODEL_HEAVY}) → new chat.
(Continue panel: activity-bar icon or Ctrl+L — not Cursor Agent. Mode: bottom-left of input or Ctrl+.)

See: $ROOT/docs/inter-model/CONTINUE-VERIFY.md § Continue IDE extension
EOF
}

print_prompts() {
  cat <<EOF

=== Continue extension verify (Agent chat; model: ${CONTINUE_MODEL}; heavy: ${CONTINUE_MODEL_HEAVY}) ===

0. Alien ritual (matrix row #9) — open alien WP or blank dir, unprompted:
   What's the current state of this project?
   PASS: first tool is MCP brief or shell convmem doctor/brief.

1. Brief (named tool):
   Call MCP tool `brief` with `project="willowyhollow-dev"`. Reply with **only one sentence**
   that quotes `coordination.durable_writes` from the JSON. No other sections.

2. Search practice facts:
   Call MCP tool `search_fast` only (no Read, no Bash) for
   `practice-local willowyhollow-practice 8081`. Cite top `ledger_id`.

3. Ask:
   Call MCP tool `ask` only: "How do I reset the willowyhollow practice stack?"
   with `site=practice-local`. If `ask` is weak, say so — do **not** Read files under ~/WordPress.

4. History ingest marker:
   Continue verify marker: purple-elephant-8081
   (wait ~2 min, then: convmem search "purple-elephant-8081")

After prompts 1–3 in the same chat:
  ~/Projects/convmem/scripts/grade-continue-session.sh --at 'now'

EOF
}

cmd="${1:-prompts}"
case "$cmd" in
  prompts)
    bash "$ROOT/scripts/verify-continue.sh" || true
    print_prompts
    ;;
  grade)
    shift
    exec bash "$ROOT/scripts/grade-continue-session.sh" "$@"
    ;;
  grade-latest)
    latest="$(ls -t "$SESSION_DIR"/*.json 2>/dev/null | grep -v sessions.json | head -1 || true)"
    if [[ -z "$latest" ]]; then
      echo "No session files in $SESSION_DIR" >&2
      exit 1
    fi
    echo "Grading: $(basename "$latest")" >&2
    exec bash "$ROOT/scripts/grade-continue-session.sh" "$latest"
    ;;
  all)
    bash "$ROOT/scripts/verify-continue.sh"
    print_prompts
    echo "--- grade-latest (run named-tool prompts first for PASS) ---"
    bash "$ROOT/scripts/grade-continue-session.sh" "$(ls -t "$SESSION_DIR"/*.json | grep -v sessions.json | head -1)"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 1
    ;;
esac
