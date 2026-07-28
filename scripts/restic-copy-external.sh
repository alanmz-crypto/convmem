#!/usr/bin/env bash
# Copy the current correct-path snapshot to the external (offsite) repo.
# Thin wrapper over backup_workflows.copy_current_snapshot_offsite.
#
# Unconfigured external repo → exit 0 (SKIP_DISABLED).
# Configured failures preserve resolver/restic nonzero codes (no --latest).
set -euo pipefail

CONVMEM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${CONVMEM_RESTIC_ENV:-$HOME/.config/convmem/restic.env}"

exec python3 "$CONVMEM_ROOT/backup_workflows.py" copy-offsite --env-file "$ENV_FILE"
