#!/usr/bin/env bash
# Phase 3 — CORE 8 system_runbook smoke (cn --auto, /etc or /boot).
#
# Gate: turn 1 brief()/folder_state with brief_mode=system_runbook; then search_fast;
#       answer cites runbook_hint / local files — not global corpus dump.
# Run from a REAL terminal — headless -p often stops after one tool round.
#
# Usage:
#   cn-phase3-system-runbook-smoke.sh /etc "What is the state of my pacman configuration?"
#   cn-phase3-system-runbook-smoke.sh /boot/loader/entries "What is the state of boot entries?"
set -euo pipefail

CWD="${1:?usage: $0 </etc|/boot/loader/entries> [prompt]}"
PROMPT="${2:-What is the state of this system path?}"
CONFIG="${CONTINUE_CONFIG:-$HOME/.continue/config.yaml}"

[[ -d "$CWD" ]] || { echo "Not a directory: $CWD" >&2; exit 1; }

echo "Phase 3 system_runbook smoke" >&2
echo "  cwd=$CWD" >&2
echo "  prompt=$PROMPT" >&2
echo "  model: set cliSelectedModel or /model → qwen3-coder:30b" >&2
echo "  gate: turn 1 folder_state/brief with brief_mode=system_runbook; then search_fast" >&2
echo >&2

cd "$CWD"
exec cn --auto --config "$CONFIG" --prompt "$PROMPT"
