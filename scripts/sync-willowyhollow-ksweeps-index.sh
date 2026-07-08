#!/usr/bin/env bash
# Copy Willowy Hollow ksweep steering files into inter-model and index with --supersede.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STEERING="${WILLOWYHOLLOW_STEERING:-$HOME/WordPress/willowyhollow-practice/.kiro/steering}"
DEST_DIR="$REPO/docs/inter-model"

KSWEEPS=(ksweep-practice.md ksweep-preview.md ksweep-deploy.md ksweep-all.md ksweep-tldr.md)

for file in "${KSWEEPS[@]}"; do
  SRC="$STEERING/$file"
  DEST="$DEST_DIR/WILLOWYHOLLOW-${file^^}"  # uppercase filename
  # Normalize: ksweep-practice.md → WILLOWYHOLLOW-KSWEEP-PRACTICE.md
  DEST="$DEST_DIR/WILLOWYHOLLOW-$(echo "$file" | tr '[:lower:]' '[:upper:]' | sed 's/\.MD$//'  ).md"

  if [[ ! -f "$SRC" ]]; then
    echo "Skip (missing): $SRC" >&2
    continue
  fi

  {
    echo "<!-- Synced for convmem index. Edit source in practice .kiro/steering/, re-run this script. -->"
    echo ""
    echo "**Edit source:** \`$SRC\`"
    echo "**Index:** \`bash scripts/sync-willowyhollow-ksweeps-index.sh\`"
    echo ""
    # Strip the YAML front-matter (inclusion: manual) before indexing
    sed '1{/^---$/d}' "$SRC" | sed '1,/^---$/d'
  } > "$DEST"

  echo "Copied → $DEST"
  convmem index --file "$DEST" --supersede
done

echo ""
echo "Ksweep index complete. Try: convmem \"ksweep backup key\" or convmem ask \"What does ksweep-deploy check?\""
