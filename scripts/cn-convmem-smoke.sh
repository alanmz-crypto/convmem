#!/usr/bin/env bash
# Folder-state convmem soak — enforces MCP before List/Read/Bash.
#
# cn --auto ignores --exclude, so model often runs `pwd && ls -la` first (FAIL).
# Use this script for graded smokes on ANY cwd (Documents, linuxbrew, WordPress/*, Projects/*).
#
# Usage:
#   cn-convmem-smoke.sh ~/Documents
#   cn-convmem-smoke.sh ~/WordPress/scripts "What is the current state of this folder?"
#   cn-convmem-smoke.sh /home/linuxbrew -p   # headless (slow; prefer interactive)
set -euo pipefail

exec "$(dirname "$0")/cn-workspace-convmem.sh" "$@"
