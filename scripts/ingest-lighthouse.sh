#!/usr/bin/env bash
# Run Lighthouse CI and ingest failing audits into convmem.
#
# Usage:
#   ./scripts/ingest-lighthouse.sh staging2.willowyhollow.com
#   ./scripts/ingest-lighthouse.sh staging2.willowyhollow.com /path/to/lhci-dir
#
# Requires: lhci, convmem on PATH (source ~/.config/convmem/env.local)

set -euo pipefail

SITE="${1:?Usage: $0 <site> [lhci-project-dir]}"
LHCI_DIR="${2:-.}"
CONVMEM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${TMPDIR:-/tmp}/observations-lh-${SITE//./_}.jsonl"

echo "[+] Running Lighthouse CI in $LHCI_DIR"
(
  cd "$LHCI_DIR"
  lhci autorun
)

REPORT=""
for candidate in \
  "$LHCI_DIR/.lighthouseci/lhr-*.json" \
  "$LHCI_DIR/lighthouse-report.json" \
  "$LHCI_DIR/report.json"; do
  if compgen -G "$candidate" > /dev/null 2>&1; then
    REPORT=$(ls -t $candidate 2>/dev/null | head -1)
    break
  fi
done

if [[ -z "$REPORT" || ! -f "$REPORT" ]]; then
  echo "[!] Lighthouse JSON report not found under $LHCI_DIR"
  exit 1
fi

echo "[+] Exporting observations from $REPORT"
python "$CONVMEM_ROOT/export_lighthouse.py" \
  "$REPORT" \
  --site "$SITE" \
  -o "$OUT"

if [[ ! -s "$OUT" ]]; then
  echo "[~] No failing Lighthouse audits to ingest"
  exit 0
fi

if command -v convmem >/dev/null 2>&1; then
  echo "[+] Ingesting into convmem (--upsert)"
  convmem add --file "$OUT" --upsert
else
  echo "[~] convmem not on PATH — ingest manually:"
  echo "    convmem add --file $OUT --upsert"
fi

echo "[✓] Done. Example:"
echo "    convmem related obs_${SITE%%.*}_lh_csp-missing"
