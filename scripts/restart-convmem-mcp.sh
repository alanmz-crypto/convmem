#!/usr/bin/env bash
# Kill stale convmem MCP stdio subprocesses so clients reconnect to current mcp_server.py.
# Run after updating mcp_server.py, then restart Crush/Kiro/Cursor/Continue MCP clients.
set -euo pipefail

PATTERN='/home/lauer/Projects/convmem/mcp_server.py'
mapfile -t pids < <(pgrep -f "$PATTERN" || true)

if ((${#pids[@]} == 0)); then
  echo "No convmem MCP processes running."
  exit 0
fi

echo "Killing ${#pids[@]} stale convmem MCP process(es): ${pids[*]}"
kill "${pids[@]}" 2>/dev/null || true
sleep 0.5
mapfile -t left < <(pgrep -f "$PATTERN" || true)
if ((${#left[@]} > 0)); then
  echo "Force-killing: ${left[*]}"
  kill -9 "${left[@]}" 2>/dev/null || true
fi

echo "Done. Restart long-lived MCP clients (Crush/Kiro/Cursor) so MCP respawns with current code."
echo ""
echo "Continue (continue-cli): no reload needed — each \`cn --auto\` session spawns a fresh MCP."
echo "  After killing stale processes, start a new cn session before smoke tests."
echo ""
echo "Continue IDE extension only (not used here): Developer → Reload Window before smoke tests"
echo "  if brief/stats show 'Not connected' after this script."
