#!/usr/bin/env bash
# Re-embed decision/verification units with empty Chroma document fields.
set -euo pipefail

ROOT="${CONVMEM_ROOT:-$HOME/Projects/convmem}"
PY="${CONVMEM_PY:-$HOME/miniforge3/envs/convmem/bin/python}"

convmem doctor >/dev/null
exec "$PY" "$ROOT/scripts/repair-ledger-documents.py" "$@"
