#!/usr/bin/env bash
# Verify Continue + convmem integration (CLI side). Run before/after Continue UI checks.
set -euo pipefail

CONVMEM_PY="${CONVMEM_PY:-$HOME/miniforge3/envs/convmem/bin/python}"
CONVMEM_ROOT="${CONVMEM_ROOT:-$HOME/Projects/convmem}"
CONTINUE_MCP="$HOME/.continue/mcpServers/convmem.json"

echo "=== Continue + convmem verify ==="
echo ""

fail=0
ok() { echo "  OK: $*"; }
bad() { echo "  FAIL: $*"; fail=1; }

# 1. MCP registration
CONTINUE_YAML="$HOME/.continue/config.yaml"
if [[ -f "$CONTINUE_MCP" ]]; then
  ok "MCP JSON exists: $CONTINUE_MCP"
  if grep -q 'mcp_server.py' "$CONTINUE_MCP"; then
    ok "JSON points at mcp_server.py"
  else
    bad "mcp_server.py not referenced in Continue MCP JSON"
  fi
else
  bad "missing $CONTINUE_MCP"
fi
if [[ -f "$CONTINUE_YAML" ]] && grep -q '^mcpServers:' "$CONTINUE_YAML"; then
  ok "config.yaml has mcpServers block (required for Agent mode UI)"
else
  bad "config.yaml missing mcpServers — add schema: v1 + mcpServers (see CONTINUE-VERIFY.md)"
fi
if [[ -f "$CONTINUE_YAML" ]] && grep -q '^schema: v1' "$CONTINUE_YAML"; then
  ok "config.yaml has schema: v1"
else
  bad "config.yaml missing schema: v1"
fi

# 2. MCP server tools (same process Continue uses)
echo ""
echo "--- MCP tools (stdio server imports) ---"
"$CONVMEM_PY" - <<PY || fail=1
import json, sys
sys.path.insert(0, "$CONVMEM_ROOT")
import mcp_server

for name in ("brief", "folder_state", "search_fast", "search", "ask", "related", "stats"):
    fn = getattr(mcp_server, name, None)
    if fn is None:
        print(f"  FAIL: missing tool {name}")
        sys.exit(1)
    print(f"  OK: tool {name}")

# Live corpus checks Continue agents rely on
sf = mcp_server.search_fast("practice-local willowyhollow-practice", site="practice-local")
if "willowyhollow-practice" not in sf and "8081" not in sf:
    print("  WARN: search_fast did not hit practice stack fact (index may be stale)")
else:
    print("  OK: search_fast finds practice-local stack fact")

br = json.loads(mcp_server.brief(project="willowyhollow-dev"))
if not br.get("coordination", {}).get("durable_writes"):
    print("  FAIL: brief missing coordination.durable_writes")
    sys.exit(1)
if "record" not in br["coordination"]["durable_writes"]:
    print("  WARN: brief durable_writes may not mention record workflow")
else:
    print("  OK: brief mentions record workflow")

# 2b. System runbook cwd (CORE 8 — /etc, /boot, not repo slugs)
import os
_prev = os.getcwd()
try:
    os.chdir("/etc")
    br_sys = json.loads(mcp_server.brief(""))
    if br_sys.get("brief_mode") != "system_runbook":
        print("  FAIL: brief from /etc missing brief_mode=system_runbook")
        sys.exit(1)
    if br_sys.get("focus_project"):
        print("  FAIL: brief from /etc should not set focus_project")
        sys.exit(1)
    if not (br_sys.get("runbook_hint") or {}).get("suggested_search_fast"):
        print("  FAIL: brief from /etc missing runbook_hint.suggested_search_fast")
        sys.exit(1)
    print("  OK: brief system_runbook from /etc cwd")
finally:
    os.chdir(_prev)
PY

# 3. Continue session indexing
echo ""
echo "--- Continue history in corpus ---"
_search_out=$(convmem search "Using MCP Search to query convmem" 2>&1 || true)
if echo "$_search_out" | grep -q 'continue/sessions'; then
  ok "Continue session JSON appears in convmem search"
elif echo "$_search_out" | grep -qi 'continue'; then
  ok "Continue content searchable (alternate match)"
else
  bad "Continue session not found in search (run: convmem index --file ~/.continue/sessions/<latest>.json)"
fi
unset _search_out

# 4. Watch observes Continue path
echo ""
echo "--- Watch path inventory ---"
if "$CONVMEM_PY" -c "
import sys
from pathlib import Path
sys.path.insert(0, '$CONVMEM_ROOT')
from inventory import SOURCES
roots = [str(Path(x).expanduser()) for x in SOURCES if not isinstance(x, Path) or x != Path.home()]
assert any('.continue/sessions' in r for r in roots)
print('  OK: ~/.continue/sessions in ingest inventory')
"; then
  :
else
  bad "Continue sessions path not in ingest inventory"
fi

echo ""
if [[ "$fail" -eq 0 ]]; then
  echo "CLI verify PASSED. Next: manual Continue UI checklist in docs/inter-model/CONTINUE-VERIFY.md"
else
  echo "CLI verify FAILED ($fail issue(s))"
  exit 1
fi
