#!/usr/bin/env bash
# Quit all Crush processes so the next start loads current hooks/MCP cleanly.
# Use when freezes stack up from many Crush TTYs (each spawns mcp_server.py).
set -euo pipefail

pids=($(pgrep crush 2>/dev/null || true))
if ((${#pids[@]} == 0)); then
  echo "No Crush processes running."
  exit 0
fi

echo "Stopping ${#pids[@]} Crush process(es): ${pids[*]}"
kill "${pids[@]}" 2>/dev/null || true
for _ in 1 2 3 4 5 6 7 8 9 10; do
  pgrep crush >/dev/null 2>&1 || break
  sleep 1
done
left=($(pgrep crush 2>/dev/null || true))
if ((${#left[@]} > 0)); then
  echo "Force-killing: ${left[*]}"
  kill -9 "${left[@]}" 2>/dev/null || true
fi

# Drop mcp_server children whose parent was Crush (not Cursor/Kiro).
python3 - <<'PY'
import os, signal, subprocess

for line in subprocess.check_output(["ps", "-eo", "pid,ppid,cmd"], text=True).splitlines()[1:]:
    parts = line.split(None, 2)
    if len(parts) < 3:
        continue
    pid, ppid, cmd = int(parts[0]), int(parts[1]), parts[2]
    if "Projects/convmem/mcp_server.py" not in cmd:
        continue
    try:
        pcmd = open(f"/proc/{ppid}/cmdline", "rb").read().replace(b"\0", b" ").decode()
    except FileNotFoundError:
        pcmd = ""
    if (not pcmd) or pcmd.strip() == "crush" or pcmd.strip().startswith("crush "):
        print(f"Stopping crush-owned mcp_server pid={pid}")
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
PY

echo "Done. Start one Crush in the project dir (prefer Qwen3.7-Max)."
echo "Cursor/Kiro MCP processes were left running."
