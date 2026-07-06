#!/usr/bin/env bash
# Index a session file into prod Chroma from any cwd (e.g. convmem-lab).
# Avoids "Refusing prod write from convmem-lab context" without remembering flags.
#
# Usage:
#   bash ~/Projects/convmem/scripts/convmem-index-prod.sh PATH [--force]
#   bash ~/Projects/convmem/scripts/convmem-index-prod.sh ~/.kiro/sessions/.../messages.jsonl --force
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: convmem-index-prod.sh FILE [extra convmem index args...]" >&2
  exit 1
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
CONVMEM_CONFIRM_PROD=1 exec convmem index --file "$@"
