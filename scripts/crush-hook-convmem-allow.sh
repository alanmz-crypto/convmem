#!/usr/bin/env bash
# Crush PreToolUse hook — enforce full convmem ritual before repo survey; auto-approve read-only convmem.
# Installed to ~/.config/crush/hooks/convmem-allow.sh by deploy-agent-protocol.sh
set -euo pipefail

tool="${CRUSH_TOOL_NAME:-bash}"
cmd="${CRUSH_TOOL_INPUT_COMMAND:-}"
session="${CRUSH_SESSION_ID:-unknown}"
cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/convmem-crush-ritual"
base_session="${session%%\$\$*}"
progress_base="$cache_dir/progress-$session"
base_progress="$cache_dir/progress-$base_session"
ritual_msg="convmem ritual required before repo survey. Run: convmem doctor && convmem brief --stdout-only && convmem unresolved"
# Prefer shell: Crush MCP stdio has hung indefinitely on tools/call (server idle
# on stdin) — do not steer the model into mcp_convmem_* until that path is solid.
search_first_msg="The convmem corpus has the answers. Use bash: convmem \"query\" or convmem ask \"…\" before grep/glob/ls/view. Do not wait on mcp_convmem_*."

# Fallback: parse stdin JSON for bash when env not set
if [ "$tool" = "bash" ] && [ -z "$cmd" ] && [ ! -t 0 ]; then
  cmd="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("command",""))' 2>/dev/null || true)"
fi

mkdir -p "$cache_dir"

_progress_complete() {
  local base="$1"
  [ -f "${base}.doctor" ] && [ -f "${base}.brief" ] && [ -f "${base}.unresolved" ]
}

_ritual_complete() {
  _progress_complete "$progress_base" && return 0
  [ "$base_session" != "$session" ] && _progress_complete "$base_progress" && return 0
  return 1
}

_record_progress() {
  [ -z "$cmd" ] && return 0
  echo "$cmd" | grep -qE 'convmem[[:space:]]+doctor' && touch "${progress_base}.doctor" || true
  echo "$cmd" | grep -qE 'convmem[[:space:]]+brief' && touch "${progress_base}.brief" || true
  echo "$cmd" | grep -qE 'convmem[[:space:]]+unresolved' && touch "${progress_base}.unresolved" || true
}

_seen_search() {
  [ -f "${progress_base}.search_seen" ] && return 0
  # Mirror _ritual_complete: child sessions inherit parent search completion
  # (Codex 2026-07-07 asymmetric inheritance finding).
  [ "$base_session" != "$session" ] && [ -f "${base_progress}.search_seen" ] && return 0
  return 1
}

_record_search() {
  touch "${progress_base}.search_seen" || true
}

_deny() {
  echo "$1" >&2
  echo "{\"decision\":\"deny\",\"message\":\"$1\"}"
  exit 2
}

_survey_tool() {
  case "$tool" in
    ls|view|glob|grep|read|agent) return 0 ;;
  esac
  return 1
}

_allow_readonly_convmem_bash() {
  [ -n "$cmd" ] || return 1
  if echo "$cmd" | grep -qE '(^|[;&|]|&&|\|\|)[[:space:]]*convmem[[:space:]]+(record|add|index|verify)([[:space:]]|$)'; then
    return 1
  fi
  if echo "$cmd" | grep -qE '(^|[;&|]|&&|\|\|)[[:space:]]*convmem[[:space:]]+(doctor|brief|unresolved|search|ask|stats)([[:space:]]|$)'; then
    echo '{"decision":"allow"}'
    return 0
  fi
  if echo "$cmd" | grep -qE 'convmem[[:space:]]+(doctor|brief|unresolved|search|ask|stats)'; then
    if echo "$cmd" | grep -qE '(^|[|;&]|&&|\|\|)[[:space:]]*(head|tail|echo)[[:space:]]'; then
      echo '{"decision":"allow"}'
      return 0
    fi
  fi
  return 1
}

if [ "$tool" = "bash" ] && [ -n "$cmd" ]; then
  if _allow_readonly_convmem_bash; then
    _record_progress
    if echo "$cmd" | grep -qE 'convmem[[:space:]]+search|convmem[[:space:]]+ask'; then
      _record_search
    fi
    exit 0
  fi
fi

if ! _ritual_complete; then
  case "$tool" in
    mcp_convmem_*)
      _deny "Shell convmem ritual required before MCP. Run: convmem doctor && convmem brief --stdout-only && convmem unresolved"
      ;;
  esac
  if _survey_tool; then
    _deny "$ritual_msg"
  fi
  if [ "$tool" = "bash" ] && [ -n "$cmd" ]; then
    if echo "$cmd" | grep -qE 'convmem[[:space:]]+(doctor|brief|unresolved|search|ask|stats)([[:space:]]|$)'; then
      exit 0
    fi
    _deny "$ritual_msg"
  fi
fi

if [ "$tool" = "bash" ] && [ -n "$cmd" ]; then
  if _allow_readonly_convmem_bash; then
    exit 0
  fi
fi

# MCP search/ask: allow if present, but prefer shell (Crush MCP client can hang).
# Only mark search_seen for MCP after allow — shell path records search above.
case "$tool" in
  mcp_convmem_search_fast|mcp_convmem_search|mcp_convmem_ask)
    _record_search
    exit 0
    ;;
  mcp_convmem_*)
    # Non-search MCP after ritual: allow (stats/related) but do not count as search.
    exit 0
    ;;
esac

# Ritual complete but search not yet used: block survey tools
if _survey_tool && ! _seen_search; then
  _deny "$search_first_msg"
fi

exit 0
