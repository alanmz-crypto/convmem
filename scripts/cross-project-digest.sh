#!/usr/bin/env bash
# Read-only cross-project coordination digest → ~/.local/share/convmem/digests/
set -euo pipefail

ROOT="${CONVMEM_ROOT:-$HOME/Projects/convmem}"
PY="${CONVMEM_PY:-$HOME/miniforge3/envs/convmem/bin/python}"

usage() {
  cat <<EOF
Usage: $0 [--skip-ask] [--propose] [--site HOST]

  --skip-ask   Brief + queues only (no LLM synthesis)
  --propose    Queue one synthesis draft in pending_decisions.jsonl (Phase 2)
  --site HOST  Include client-site unresolved (default: coordination lane only)

Requires: convmem doctor exit 0, DEEPSEEK_API_KEY for ask (unless --skip-ask).

Weekly timer: systemd/convmem-cross-project-digest.timer.example
Pilot log: docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md
EOF
}

ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-ask) ARGS+=(--skip-ask); shift ;;
    --propose) ARGS+=(--propose); shift ;;
    --site) ARGS+=(--site "$2"); shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

convmem doctor >/dev/null
exec "$PY" "$ROOT/cross_project_digest.py" "${ARGS[@]}"
