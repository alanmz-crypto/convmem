#!/usr/bin/env bash
# Arc #286 — mandatory outer-bwrap pytest entry (do not invoke raw pytest).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/scripts/issue_286_guarded_pytest_launcher.py" "$@"
