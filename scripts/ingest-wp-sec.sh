#!/usr/bin/env bash
# Ingest wp-sec-agent scan results into convmem as observations.
#
# Usage:
#   ./scripts/ingest-wp-sec.sh staging2.willowyhollow.com
#   ./scripts/ingest-wp-sec.sh staging2.willowyhollow.com --run-scan
#
# Requires: convmem in PATH (source ~/.config/convmem/env.local)

set -euo pipefail

SITE="${1:?Usage: $0 <site> [--run-scan]}"
RUN_SCAN=0
if [[ "${2:-}" == "--run-scan" ]]; then
  RUN_SCAN=1
fi

CONVMEM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WP_SEC="${WP_SEC_ROOT:-$HOME/Projects/wp-sec-agent}"
RESULTS="$WP_SEC/clients/$SITE/results"
OUT="${TMPDIR:-/tmp}/observations-${SITE//./_}.jsonl"

if [[ "$RUN_SCAN" -eq 1 ]]; then
  echo "[+] Running wp-sec-agent scan for $SITE..."
  (cd "$WP_SEC" && ./run.sh "$SITE" lite)
fi

echo "[+] Exporting observations from $RESULTS"
python "$CONVMEM_ROOT/export_report_to_observations.py" \
  --site "$SITE" \
  --results-dir "$RESULTS" \
  -o "$OUT"

echo "[+] Ingesting into convmem"
convmem add --file "$OUT" --upsert

echo "[✓] Done. Query with:"
echo "    convmem ask \"What security issues exist on $SITE?\" --domain web_stack.security"
