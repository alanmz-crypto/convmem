#!/usr/bin/env bash
# Read-only cross-project coordination digest → ~/.local/share/convmem/digests/
set -euo pipefail

ROOT="${CONVMEM_ROOT:-$HOME/Projects/convmem}"
PY="${CONVMEM_PY:-$HOME/miniforge3/envs/convmem/bin/python}"

usage() {
  cat <<EOF
Usage: $0 [--skip-ask] [--propose] [--site HOST] [-o PATH]

  --skip-ask   Brief + queues + do-not-retry only (no LLM synthesis)
  --propose    Queue one synthesis draft in pending_decisions.jsonl (Phase 2)
  --site HOST  Include client-site unresolved (default: coordination lane only)
  -o, --output PATH  Write digest markdown to PATH (default: digests/YYYY-MM-DD.md)

Requires: convmem doctor exit 0, DEEPSEEK_API_KEY for ask (unless --skip-ask).

Inputs (append-only under ~/.local/share/convmem/):
  decisions-approved.jsonl  recent decisions header
  link_queue.jsonl          link candidates
  attempts.jsonl            optional — renders ## Do not retry (see docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md)

Recency: digest injects recent approved decision ids into the ask prompt and
renders a Recency check section (header ↔ citations overlap).

Precheck: bash scripts/precheck-path.sh <path>  (advisory, exit 0)
Smoke:    bash scripts/smoke-cross-project-digest.sh

Weekly timer: systemd/convmem-cross-project-digest.timer.example
Pilot log: docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md
Phase 0: closed (Run 6). --propose remains Ryan-gated.
EOF
}

ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-ask) ARGS+=(--skip-ask); shift ;;
    --propose) ARGS+=(--propose); shift ;;
    --site) ARGS+=(--site "$2"); shift 2 ;;
    -o|--output) ARGS+=(--output "$2"); shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
done

convmem doctor >/dev/null
exec "$PY" "$ROOT/cross_project_digest.py" "${ARGS[@]}"
