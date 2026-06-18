#!/usr/bin/env bash
# Run F2b HTTP security monitor for staging2.
#
# Usage:
#   ./scripts/monitor-staging2.sh
#   ./scripts/monitor-staging2.sh --dry-run
#
# Requires: convmem in PATH (source ~/.config/convmem/env.local)

set -euo pipefail

SITE="${MONITOR_SITE:-staging2.willowyhollow.com}"
EXTRA_ARGS=("$@")

echo "[+] Monitor probes for $SITE"
convmem monitor --site "$SITE" "${EXTRA_ARGS[@]}"
