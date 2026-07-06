#!/usr/bin/env bash
# Print contextual next-step hints (disable: CONVMEM_NO_NEXT_STEPS=1).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${CONVMEM_PYTHON:-$HOME/miniforge3/envs/convmem/bin/python}"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi
exec "$PY" "$ROOT/next_steps.py" "$@"
