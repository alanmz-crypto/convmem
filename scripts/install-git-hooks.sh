#!/usr/bin/env bash
# Point this clone's git hooks at scripts/git-hooks (WIP-on-main pre-push).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$ROOT/scripts/git-hooks/pre-push"
if [[ ! -f "$HOOK" ]]; then
  echo "missing $HOOK" >&2
  exit 1
fi
chmod +x "$HOOK"
cd "$ROOT"
git config core.hooksPath scripts/git-hooks
echo "core.hooksPath=$(git config --get core.hooksPath)"
echo "Installed. WIP-pattern pushes to main will be rejected (CONVMEM_SKIP_WIP_HOOK=1 to bypass)."
