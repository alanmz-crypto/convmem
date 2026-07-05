#!/usr/bin/env bash
# Index docs/inter-model/*.md into prod Chroma (section units, no LLM distill).
# Requires explicit prod intent — does not run on accident from lab cwd.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ "${CONVMEM_CONFIRM_PROD:-}" != "1" ]]; then
  echo "Refusing bulk prod index: export CONVMEM_CONFIRM_PROD=1 first." >&2
  echo "  Data: ~/.local/share/convmem (Tier 1, backed up)" >&2
  echo "  Lab work: use ~/Projects/convmem-lab/scripts/convmem-lab.sh instead." >&2
  exit 2
fi

shopt -s nullglob
files=("$ROOT"/docs/inter-model/*.md)
if ((${#files[@]} == 0)); then
  echo "No docs/inter-model/*.md files found under $ROOT"
  exit 1
fi
for f in "${files[@]}"; do
  echo "==> $f"
  convmem index --file "$f" --force
done
echo "Done. ${#files[@]} inter-model doc(s) indexed (prod)."
