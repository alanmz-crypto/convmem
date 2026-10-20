#!/usr/bin/env bash
# Crush PreToolUse hook — auto-run the convmem session-start ritual (single-flight).
#
# Installed to ~/.config/crush/hooks/convmem-ritual-autorun.sh by deploy-agent-protocol.sh
# BEFORE convmem-allow.sh so progress markers exist before the ritual gate runs.
#
# Behavior contract:
#   - Idempotent: if the three markers already exist, return fast.
#   - Non-blocking: ALWAYS exit 0 (never deny a tool call).
#   - Bounded: per-command timeout (CONVMEM_RITUAL_AUTORUN_TIMEOUT) and session flock wait.
#   - Single-flight per session: flock so parallel tool calls share one ritual.
#   - Global doctor lock: at most one convmem doctor across Crush sessions; others skip doctor.
#
# Opt-out: CONVMEM_DISABLE_RITUAL_AUTORUN=1
set -uo pipefail

session="${CRUSH_SESSION_ID:-unknown}"
cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/convmem-crush-ritual"
base_session="${session%%\$\$*}"
progress_base="$cache_dir/progress-$session"
base_progress="$cache_dir/progress-$base_session"
session_lock="$cache_dir/session-${session}.lock"
doctor_lock="$cache_dir/global-doctor.lock"
SESSION_FLOCK_WAIT="${CONVMEM_RITUAL_SESSION_FLOCK_WAIT:-150}"
RITUAL_TIMEOUT="${CONVMEM_RITUAL_AUTORUN_TIMEOUT:-45}"

mkdir -p "$cache_dir" 2>/dev/null || true

_markers_present() {
  local base="$1"
  [ -f "${base}.doctor" ] && [ -f "${base}.brief" ] && [ -f "${base}.unresolved" ]
}

_write_markers() {
  touch "${progress_base}.doctor" "${progress_base}.brief" "${progress_base}.unresolved" 2>/dev/null || true
}

# Already done for this session (or inherited from parent session)?
if _markers_present "$progress_base" ||
   { [ "$base_session" != "$session" ] && _markers_present "$base_progress"; }; then
  exit 0
fi

if [ "${CONVMEM_DISABLE_RITUAL_AUTORUN:-0}" = "1" ]; then
  exit 0
fi

_run() {  # _run <seconds> <cmd...> — best effort, never fatal
  if command -v timeout >/dev/null 2>&1; then
    timeout "$1" "${@:2}" >/dev/null 2>&1 || true
  else
    "${@:2}" >/dev/null 2>&1 || true
  fi
}

_run_doctor_if_unlocked() {
  if ! command -v convmem >/dev/null 2>&1; then
    return 0
  fi
  if ! command -v flock >/dev/null 2>&1; then
    _run "$RITUAL_TIMEOUT" convmem doctor
    return 0
  fi
  (
    flock -n 200 || exit 0
    _run "$RITUAL_TIMEOUT" convmem doctor
  ) 200>"$doctor_lock"
}

_run_ritual() {
  if ! command -v convmem >/dev/null 2>&1; then
    return 0
  fi
  _run_doctor_if_unlocked
  _run "$RITUAL_TIMEOUT" convmem brief --stdout-only
  _run "$RITUAL_TIMEOUT" convmem unresolved
}

_ritual_body() {
  if _markers_present "$progress_base" ||
     { [ "$base_session" != "$session" ] && _markers_present "$base_progress"; }; then
    return 0
  fi
  _run_ritual
  _write_markers
}

if command -v flock >/dev/null 2>&1; then
  (
    if flock -w "$SESSION_FLOCK_WAIT" 9; then
      _ritual_body
    else
      # Wait timed out — never start a second ritual; satisfy the gate anyway.
      _write_markers
    fi
  ) 9>"$session_lock"
else
  _ritual_body
fi

exit 0
