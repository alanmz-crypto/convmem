#!/usr/bin/env bash
# Copy Willowy Hollow Crush findings into inter-model and index with --supersede.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${WILLOWYHOLLOW_FINDINGS:-$HOME/WordPress/willowyhollow-practice/logs/2026-07-05-code-review-findings.md}"
DEST="$REPO/docs/inter-model/WILLOWYHOLLOW-CODE-REVIEW-FINDINGS.md"

if [[ ! -f "$SRC" ]]; then
  echo "Source findings missing: $SRC" >&2
  exit 1
fi

{
  echo "<!-- Synced for convmem index. Edit source in practice repo, re-run this script. -->"
  echo ""
  echo "**Edit source:** \`$SRC\`"
  echo "**Index:** \`bash scripts/sync-willowyhollow-findings-index.sh\`"
  echo ""
  cat "$SRC"
} > "$DEST"

echo "Copied → $DEST"
convmem index --file "$DEST" --supersede
