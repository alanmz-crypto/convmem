#!/usr/bin/env bash
# Phase 2 — cn --auto policy smoke (daily mode, workspace_local).
#
# Gate: alien_ritual PARTIAL acceptable; check v5 answer quality (no global corpus bleed).
# Run from a REAL terminal (iTerm/Alacritty/foot/tmux) — not Cursor agent shell.
#
# Usage:
#   cn-phase2-auto-smoke.sh ~/Documents
#   cn-phase2-auto-smoke.sh /home/linuxbrew
set -euo pipefail

CWD="${1:?usage: $0 <workspace-dir>}"
PROMPT="${2:-What is the current state of this folder?}"
CONFIG="${CONTINUE_CONFIG:-$HOME/.continue/config.yaml}"

[[ -d "$CWD" ]] || { echo "Not a directory: $CWD" >&2; exit 1; }

echo "Phase 2 cn --auto smoke" >&2
echo "  cwd=$CWD" >&2
echo "  prompt=$PROMPT" >&2
echo "  model: set cliSelectedModel or /model → qwen3-coder:30b" >&2
echo "  gate: PARTIAL ritual OK; final answer must not cite global corpus as folder stats" >&2
echo >&2

cd "$CWD"
exec cn --auto --config "$CONFIG" --prompt "$PROMPT"
