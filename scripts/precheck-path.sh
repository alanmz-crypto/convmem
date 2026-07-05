#!/usr/bin/env bash
# Advisory: warn if PATH appears in failed/partial attempts. Always exits 0.
#
# Reads ~/.local/share/convmem/attempts.jsonl by default.
# Override: ATTEMPTS_FILE=/path/to/attempts.jsonl
#
# Run: bash scripts/precheck-path.sh cross_project_digest.py

set -euo pipefail

ATTEMPTS="${ATTEMPTS_FILE:-$HOME/.local/share/convmem/attempts.jsonl}"

if [ $# -eq 0 ]; then
  echo "Usage: precheck-path.sh <file-path>" >&2
  exit 0
fi

TARGET="$1"
if [ ! -f "$ATTEMPTS" ]; then
  exit 0
fi

python3 - "$ATTEMPTS" "$TARGET" <<'PY'
import json
import sys

path, target = sys.argv[1], sys.argv[2]
for line in open(path, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    try:
        row = json.loads(line)
    except json.JSONDecodeError:
        continue
    if row.get("outcome") not in ("failed", "partial"):
        continue
    if row.get("path") != target:
        continue
    obs = row.get("obs_id", "?")
    summary = row.get("summary", "")
    print(f"WARN: {target} had prior failed attempts")
    print(f"  obs: {obs} — {summary}")
PY

exit 0
