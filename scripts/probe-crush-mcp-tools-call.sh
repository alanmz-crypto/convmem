#!/usr/bin/env bash
# Timed Crush ConvMem MCP tools/call probe.
#
# Reproduces the hang class: PreToolUse allow → no tool_result (Crush client
# never completes tools/call while mcp_server sits on stdin).
#
# Always restores from backups taken at start:
#   - crush.json (including prior mcp.convmem.disabled / timeout)
#   - hooks/convmem-allow.sh
# Does not force MCP off after PASS (preserves live enabled state).
#
# Usage:
#   bash scripts/probe-crush-mcp-tools-call.sh
#   DEADLINE=60 bash scripts/probe-crush-mcp-tools-call.sh
#
# Exit: 0 = real tools/call returned under deadline; 1 = FAIL/watchdog;
#       2 = setup error.
set -u
DEADLINE="${DEADLINE:-50}"
REPO="${CONVMEM_REPO:-$HOME/Projects/convmem}"
CFG="${XDG_CONFIG_HOME:-$HOME/.config}/crush/crush.json"
HOOK="${XDG_CONFIG_HOME:-$HOME/.config}/crush/hooks/convmem-allow.sh"
BAK_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/crush/backups"
OUT="${PROBE_OUT:-/tmp/crush-mcp-tools-call-probe.out}"
TS="$(date +%Y%m%d-%H%M%S)"
HOOK_BAK="$BAK_DIR/convmem-allow.sh.mcp-probe-$TS"
CFG_BAK="$BAK_DIR/crush.json.mcp-probe-$TS"
MODEL="${PROBE_MODEL:-alibaba-singapore/qwen3.7-max}"

if [[ ! -f "$CFG" || ! -f "$HOOK" ]]; then
  echo "FAIL: missing Crush config or hook" >&2
  exit 2
fi
mkdir -p "$BAK_DIR"
cp -a "$CFG" "$CFG_BAK"
cp -a "$HOOK" "$HOOK_BAK"
: >"$OUT"

restore() {
  cp -a "$HOOK_BAK" "$HOOK" 2>/dev/null || true
  cp -a "$CFG_BAK" "$CFG" 2>/dev/null || true
  python3 - <<PY
import json
from pathlib import Path
cfg = json.loads(Path("$CFG").read_text())
m = cfg.get("mcp", {}).get("convmem", {})
print(
    "restored: hook + crush.json "
    f"(mcp.convmem.disabled={m.get('disabled')!r} timeout={m.get('timeout')!r})"
)
PY
}
trap restore EXIT

# Allow mcp_convmem_* so the probe measures Crush tools/call, not ritual deny.
python3 - <<'PY'
from pathlib import Path
hook = Path.home() / ".config/crush/hooks/convmem-allow.sh"
text = hook.read_text()
body = text.split("\n", 1)[1] if text.startswith("#!") else text
preamble = """#!/usr/bin/env bash
# TEMP MCP PROBE — allow mcp_convmem_* (restored on exit).
tool="${CRUSH_TOOL_NAME:-}"
case "$tool" in
  mcp_convmem_*)
    echo '{"decision":"allow"}'
    exit 0
    ;;
esac
"""
hook.write_text(preamble + body)
print("hook: temporary mcp_convmem_* allow")
PY

python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / ".config/crush/crush.json"
cfg = json.loads(p.read_text())
cfg.setdefault("mcp", {}).setdefault("convmem", {})["disabled"] = False
cfg["mcp"]["convmem"]["timeout"] = 45
p.write_text(json.dumps(cfg, indent=2) + "\n")
print("mcp: enabled for probe (timeout=45)")
PY

start=$(date +%s)
crush run --cwd "$REPO" --model "$MODEL" --verbose \
  'Call mcp_convmem_stats exactly once (MCP tool, not bash). When the tool returns real corpus stats, reply MCP_CALL_OK and stop.' \
  >>"$OUT" 2>&1 &
pid=$!
echo "pid=$pid deadline=${DEADLINE}s out=$OUT"

killed=0
while kill -0 "$pid" 2>/dev/null; do
  now=$(date +%s)
  elapsed=$((now - start))
  if rg -q 'MCP_CALL_OK' "$OUT" 2>/dev/null; then
    sleep 2
    break
  fi
  if ((elapsed >= DEADLINE)); then
    echo "WATCHDOG: killing after ${elapsed}s" | tee -a "$OUT"
    kill "$pid" 2>/dev/null || true
    sleep 1
    kill -9 "$pid" 2>/dev/null || true
    pkill -P "$pid" 2>/dev/null || true
    echo WATCHDOG_KILLED >>"$OUT"
    killed=1
    break
  fi
  sleep 1
done
wait "$pid" 2>/dev/null || true
end=$(date +%s)
elapsed=$((end - start))

allow=$(rg -c 'PreToolUse tool=mcp_convmem_stats hooks=1 decision=allow' "$OUT" || true)
deny=$(rg -c 'decision=deny|blocked by hook' "$OUT" || true)
ok=$(rg -c 'MCP_CALL_OK' "$OUT" || true)
wd=$(rg -c 'WATCHDOG_KILLED' "$OUT" || true)

db_ok=$(sqlite3 "$REPO/.crush/crush.db" "
SELECT COUNT(*) FROM messages
WHERE created_at > strftime('%s','now','-5 minutes')
  AND parts LIKE '%mcp_convmem_stats%'
  AND parts LIKE '%tool_result%'
  AND parts NOT LIKE '%blocked by hook%'
  AND length(parts) > 200;
" 2>/dev/null || echo 0)

echo "elapsed=${elapsed}s allow=${allow:-0} deny=${deny:-0} ok=${ok:-0} wd=${wd:-0} db_ok=${db_ok:-0}"
rg -n 'mcp_convmem|PreToolUse|WATCHDOG|MCP_CALL_OK|blocked|decision=' "$OUT" | head -30 || true

if ((killed == 0)) && [[ "${allow:-0}" -ge 1 ]] && [[ "${db_ok:-0}" -ge 1 ]] && [[ "${deny:-0}" -eq 0 ]]; then
  echo "PASS: Crush tools/call returned under ${DEADLINE}s (prior mcp.disabled restored)"
  exit 0
fi
echo "FAIL: Crush MCP tools/call did not complete cleanly (prior mcp.disabled restored)"
exit 1
