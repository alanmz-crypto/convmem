#!/usr/bin/env bash
# deploy-site-reference.sh — deploy site-reference pointers to agent surfaces

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

required=(
  "docs/site-reference/README.md"
  "docs/site-reference/NOTES.md"
  "docs/site-reference/php-version-parity.md"
  "docs/site-reference/site-address-consistency.md"
  "docs/site-reference/backup-before-write-gate.md"
  "config/cursor-rules-site-reference.mdc.example"
  "config/cursor-rules-site-reference-workspace.mdc.example"
)

for path in "${required[@]}"; do
  if [ ! -f "$path" ]; then
    echo "ERROR: missing required site-reference file: $path" >&2
    exit 1
  fi
done

HOME="${HOME:-/home/lauer}"

CURSOR_RULES=""
for candidate in "$HOME/.cursor/rules" "$HOME/.config/Cursor/rules" "$HOME/.config/cursor/rules"; do
  if [ -d "$candidate" ]; then
    CURSOR_RULES="$candidate"
    break
  fi
done

KIRO_DIR=""
for candidate in "$HOME/.kiro/steering" "$HOME/.config/kiro/steering"; do
  if [ -d "$candidate" ]; then
    KIRO_DIR="$candidate"
    break
  fi
done

WILLOWY_WORKSPACES=(
  "$HOME/WordPress/willowyhollow-practice"
  "$HOME/WordPress/willowyhollow"
  "$HOME/GitClones/willowyhollow-dev"
)

echo "=== Deploying site-reference surfaces ==="

if [ -n "$CURSOR_RULES" ]; then
  cp config/cursor-rules-site-reference.mdc.example "$CURSOR_RULES/site-reference.mdc"
  echo "  [deploy] $CURSOR_RULES/site-reference.mdc (user globs)"
else
  echo "  [skip]   Cursor user rules directory not found"
fi

for ws in "${WILLOWY_WORKSPACES[@]}"; do
  if [ -d "$ws" ]; then
    mkdir -p "$ws/.cursor/rules"
    cp config/cursor-rules-site-reference-workspace.mdc.example "$ws/.cursor/rules/site-reference.mdc"
    echo "  [deploy] $ws/.cursor/rules/site-reference.mdc (alwaysApply)"
  else
    echo "  [skip]   workspace not found: $ws"
  fi
done

if [ -n "$KIRO_DIR" ]; then
  cp config/kiro-steering-site-reference.example.md "$KIRO_DIR/site-reference.md"
  echo "  [deploy] $KIRO_DIR/site-reference.md"
else
  echo "  [skip]   Kiro steering directory not found"
fi

echo ""
echo "Site-reference deployment complete."

if [ -x scripts/verify-site-reference.sh ]; then
  echo ""
  bash scripts/verify-site-reference.sh || true
fi

if [ -x scripts/validate-site-reference-surfaces.sh ]; then
  echo ""
  bash scripts/validate-site-reference-surfaces.sh || true
fi
