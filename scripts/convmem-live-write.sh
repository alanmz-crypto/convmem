#!/usr/bin/env bash
# External fail-closed gate for live Chroma writes — does NOT modify convmem CLI.
#
# Use instead of bare convmem for operations that upsert the live corpus:
#   scripts/convmem-live-write.sh record --approve-last
#   scripts/convmem-live-write.sh add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
#
# Runs restic-ensure-chroma-snapshot.sh first; on any failure exits 1 without calling convmem.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -lt 1 ]]; then
  echo "usage: $(basename "$0") <convmem-args…>" >&2
  echo "example: $(basename "$0") record --approve-last" >&2
  exit 1
fi

"$SCRIPT_DIR/restic-ensure-chroma-snapshot.sh" || {
  echo "convmem-live-write: BLOCKED — Restic gate failed (fail-closed; no live write)" >&2
  exit 1
}

if ! command -v convmem >/dev/null 2>&1; then
  CONVMEM_PY="${CONVMEM_ROOT:-$SCRIPT_DIR/..}/convmem.py"
  if [[ -f "$CONVMEM_PY" ]]; then
    exec "${CONVMEM_PYTHON:-python3}" "$CONVMEM_PY" "$@"
  fi
  echo "convmem-live-write: ERROR: convmem not on PATH" >&2
  exit 1
fi

exec convmem "$@"
