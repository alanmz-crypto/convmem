#!/usr/bin/env bash
# Folder-state convmem soak — enforces MCP before List/Read/Bash/Search.
#
# cn --auto ignores --exclude (Continue docs). Use this script WITHOUT --auto for
# graded smokes on any cwd: ~/Documents, /home/linuxbrew, ~/WordPress/*, ~/Projects/*.
#
# Canonical entry: cn-convmem-smoke.sh (symlink-style wrapper).
#
# Usage:
#   cn-workspace-convmem.sh /home/linuxbrew
#   cn-workspace-convmem.sh ~/Documents "How is this folder cataloged?"
#   cn-workspace-convmem.sh ~/WordPress/scripts
#   cn-workspace-convmem.sh /home/linuxbrew -p   # headless (slow)
set -euo pipefail

ROOT="${CONVMEM_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
CONFIG="${CONTINUE_CONFIG:-$HOME/.continue/config.yaml}"
TIMEOUT_SECS="${CONVMEM_CONTINUE_TIMEOUT:-0}"
TRANSCRIPT="${CONVMEM_CONTINUE_TRANSCRIPT:-}"
CWD="${1:?usage: $0 <workspace-dir> [prompt]}"
shift || true

if [[ "${1:-}" == "-p" || "${1:-}" == "--print" ]]; then
  HEADLESS=1
  shift
else
  HEADLESS=0
fi

PROMPT="${1:-What is the current state of this folder?}"
[[ -d "$CWD" ]] || { echo "Not a directory: $CWD" >&2; exit 1; }

cd "$CWD"
echo "convmem smoke: cwd=$CWD" >&2
echo "prompt: $PROMPT" >&2
echo "(no --auto; List/Read/Bash/Search blocked except Bash(convmem*))" >&2

CN_ARGS=(
  --config "$CONFIG"
  --exclude List
  --exclude Read
  --exclude Bash
  --exclude Search
  --allow 'folder_state'
  --allow 'brief'
  --allow 'search_fast'
  --allow 'ask'
  --allow 'related'
  --allow 'stats'
  --allow 'Bash(convmem*)'
)

if (( HEADLESS )); then
  CN_ARGS+=(--print --prompt "$PROMPT")
else
  CN_ARGS+=(--prompt "$PROMPT")
fi

if [[ "$TIMEOUT_SECS" =~ ^[0-9]+$ ]] && (( TIMEOUT_SECS > 0 )); then
  if [[ -z "$TRANSCRIPT" ]]; then
    TRANSCRIPT="$(mktemp /tmp/convmem-continue.XXXXXX.log)"
  fi
  echo "transcript: $TRANSCRIPT" >&2
  cmd=(cn "${CN_ARGS[@]}" "$@")
  exec timeout --signal=INT --kill-after=10s "${TIMEOUT_SECS}s" \
    script -q -c "$(printf '%q ' "${cmd[@]}")" "$TRANSCRIPT"
fi

exec cn "${CN_ARGS[@]}" "$@"
