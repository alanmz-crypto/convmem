#!/usr/bin/env bash
# Fail-closed Restic gate for live writes — thin wrapper over backup_workflows.
#
# Stale threshold (pinned): correct-path snapshot for the configured data root
# must be from the **current local calendar day**.
#
# Flags:
#   --check-only       Toolchain + repo reachable; does not backup.
#   --require-current  Exit nonzero if no current correct-path snapshot.
#   --dry-run          Report actions only; no backup.
#
# Exit codes: 0 ok | nonzero fail-closed (preserves resolver/restic codes)
set -euo pipefail

CONVMEM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${CONVMEM_RESTIC_ENV:-$HOME/.config/convmem/restic.env}"

ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) ARGS+=(--check-only); shift ;;
    --require-current) ARGS+=(--require-current); shift ;;
    --dry-run) ARGS+=(--dry-run); shift ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *)
      echo "restic-gate: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

exec python3 "$CONVMEM_ROOT/backup_workflows.py" ensure --env-file "$ENV_FILE" "${ARGS[@]}"
