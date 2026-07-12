#!/usr/bin/env bash
# Thin wrapper — full install is scripts/install-repo-config.sh (hooks + hygiene).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$ROOT/scripts/install-repo-config.sh"
