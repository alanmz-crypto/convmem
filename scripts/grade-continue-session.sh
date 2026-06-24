#!/usr/bin/env bash
# Grade a Continue session JSON for convmem verify compliance (tool use, not answer polish).
set -euo pipefail

SESSION_DIR="${SESSION_DIR:-$HOME/.continue/sessions}"

resolve_timestamp() {
  local ts="$1"
  local target_epoch
  target_epoch="$(date -d "$ts" +%s 2>/dev/null)" || {
    echo "Error: cannot parse timestamp '$ts'. Try formats like:" >&2
    echo "  2026-06-24" >&2
    echo "  2026-06-24_14-30" >&2
    echo "  2026-06-24T14:30:00" >&2
    exit 1
  }
  local best_file=""
  local best_diff=""
  local f
  for f in "$SESSION_DIR"/*.json; do
    [[ -f "$f" ]] || continue
    [[ "$(basename "$f")" == "sessions.json" ]] && continue
    local file_epoch
    file_epoch="$(stat -c %Y "$f")"
    local diff=$(( target_epoch - file_epoch ))
    [[ ${diff#-} -lt ${best_diff#-} ]] || [[ -z "$best_diff" ]] && { best_diff="${diff#-}"; best_file="$f"; }
  done
  if [[ -z "$best_file" ]]; then
    echo "Error: no session files found in $SESSION_DIR" >&2
    exit 1
  fi
  echo "$best_file"
}

SESSION=""
case "${1:-}" in
  --at)
    shift
    SESSION="$(resolve_timestamp "$1")"
    echo "Resolved $(date -d "$1" '+%F_%H-%M-%S') -> $(basename "$SESSION")" >&2
    ;;
  *)
    SESSION="${1:-}"
    ;;
esac

if [[ -z "$SESSION" || ! -f "$SESSION" ]]; then
  echo "Usage:" >&2
  echo "  $0 ~/.continue/sessions/<id>.json" >&2
  echo "  $0 --at '2026-06-24_14-30'" >&2
  echo "" >&2
  echo "Nearest sessions:" >&2
  ls -t "$SESSION_DIR"/*.json 2>/dev/null | grep -v sessions.json | head -3 >&2 || true
  exit 1
fi

CONVMEM_PY="${CONVMEM_PY:-$HOME/miniforge3/envs/convmem/bin/python}"

"$CONVMEM_PY" - "$SESSION" <<'PY'
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
history = data.get("history") or []

def tool_names(turn):
    msg = turn.get("message") or {}
    return [tc.get("function", {}).get("name") for tc in (msg.get("toolCalls") or [])]

def user_text(turn):
    return (turn.get("message") or {}).get("content") or ""

def assistant_text(turn):
    return (turn.get("message") or {}).get("content") or ""

def model_for_turn(turn):
    return ((turn.get("message") or {}).get("usage") or {}).get("model") or ""

checks = {
    "brief": {"want_tool": "brief", "forbid": ("Read", "Bash", "grep", "Grep")},
    "search_fast": {"want_tool": "search_fast", "forbid": ("Read", "Bash")},
    "ask": {"want_tool": "ask", "forbid": ("Read", "Bash")},
}

results = {k: {"called": False, "cheated": False, "model": None, "note": ""} for k in checks}

for i, turn in enumerate(history):
    if (turn.get("message") or {}).get("role") != "assistant":
        continue
    names = [n for n in tool_names(turn) if n]
    utext = ""
    for j in range(i - 1, -1, -1):
        if (history[j].get("message") or {}).get("role") == "user":
            utext = user_text(history[j]).lower()
            break
    model = model_for_turn(turn)
    for key, spec in checks.items():
        if spec["want_tool"] not in utext and key not in utext:
            continue
        if spec["want_tool"] in names:
            results[key]["called"] = True
            results[key]["model"] = model or results[key]["model"]
        if any(f in names for f in spec["forbid"]):
            results[key]["cheated"] = True
            results[key]["note"] = f"also used: {', '.join(names)}"

# Brief answer quality (last assistant reply after brief user prompt)
brief_ok = False
for i, turn in enumerate(history):
    ut = user_text(turn).lower()
    if "brief" not in ut or "durable_writes" not in ut:
        continue
    for j in range(i + 1, len(history)):
        if (history[j].get("message") or {}).get("role") != "assistant":
            continue
        body = assistant_text(history[j])
        if not body.strip():
            continue
        if "record --approve-last" in body.lower() or "record -i" in body.lower():
            brief_ok = True
        break

print(f"Session: {path.name}")
print(f"Title:   {data.get('title', '')}")
print()
fail = 0
for key, r in results.items():
    status = "SKIP"
    if r["called"] or r["cheated"]:
        if r["called"] and not r["cheated"]:
            status = "PASS (tool only)"
        elif r["called"] and r["cheated"]:
            status = "FAIL (tool + filesystem/bash fallback)"
            fail += 1
        else:
            status = "FAIL (no MCP tool)"
            fail += 1
        print(f"  {key:12} {status}  model={r['model'] or '?'}  {r['note']}")
    else:
        print(f"  {key:12} not run in this session")

print()
if brief_ok:
    print("  brief_answer PASS (mentions record workflow)")
else:
    print("  brief_answer FAIL (did not answer durable_writes in one focused reply)")
    fail += 1

print()
if fail:
    print(f"GRADE: FAIL ({fail} issue(s)) — correct answers via Read/Bash do not count.")
    sys.exit(1)
print("GRADE: PASS (MCP tool discipline)")
PY
