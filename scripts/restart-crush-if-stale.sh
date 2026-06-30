#!/usr/bin/env bash
# Quit Crush when convmem hook on disk is newer than the running process (hooks load at start).
set -euo pipefail

HOOK="${HOME}/.config/crush/hooks/convmem-allow.sh"
[ -f "$HOOK" ] || { echo "No hook at $HOOK — run deploy-agent-protocol.sh first"; exit 1; }

pid="$(pgrep -xo crush 2>/dev/null || true)"
if [ -z "$pid" ]; then
  echo "Crush not running — start Crush to load hooks."
  exit 0
fi

hook_mtime="$(stat -c %Y "$HOOK")"
crush_start="$(stat -c %Y "/proc/$pid")"
if [ "$hook_mtime" -le "$crush_start" ]; then
  echo "Crush PID $pid has current hooks (started after last hook update)."
  exit 0
fi

echo "Stale Crush: PID $pid started $(ps -p "$pid" -o lstart=) before hook $(stat -c %y "$HOOK")"
echo "Sending SIGTERM to Crush PID $pid ..."
kill "$pid" 2>/dev/null || true
for _ in 1 2 3 4 5; do
  pgrep -xo crush >/dev/null 2>&1 || break
  sleep 1
done
if pid="$(pgrep -xo crush 2>/dev/null || true)" && [ -n "$pid" ]; then
  echo "Still running — SIGKILL PID $pid"
  kill -9 "$pid" 2>/dev/null || true
fi
echo "Done. Start Crush again — deny hook will load on startup."
