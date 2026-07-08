#!/usr/bin/env bash
# generate-site-reference.sh — build a tiny index for docs/site-reference
#
# Canonical slices live in docs/site-reference/*.md.
# Hand-curated application guide: docs/site-reference/NOTES.md (never overwritten).
# This script keeps a generated README alongside them.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir/.."

out_dir="docs/site-reference"
mkdir -p "$out_dir"

shopt -s nullglob

{
  echo "# Willowy Hollow site-reference slices"
  echo ""
  echo "Curated decision slices for client-site promotion gates and environment safety."
  echo "Application guide: [NOTES.md](NOTES.md) (pre-promote sequence, gate registry)."
  echo ""
  echo "## Current slices"
  echo ""
  for slice in "$out_dir"/*.md; do
    name=$(basename "$slice")
    [ "$name" = "README.md" ] && continue
    [ "$name" = "NOTES.md" ] && continue
    echo "- [${name}](${name})"
  done
  echo ""
  echo "## Notes"
  echo ""
  echo "- Keep topic slices short; see \`bash scripts/verify-site-reference.sh\` (word cap 800)."
  echo "- Session loop: [\`WILLOWYHOLLOW-SESSION-LOOP.md\`](../WILLOWYHOLLOW-SESSION-LOOP.md) step 4b (pre-promote gates)."
  echo "- Regenerate this index: \`bash scripts/refresh-site-reference.sh\`"
} > "$out_dir/README.md"

echo "  -> $out_dir/README.md"
