#!/usr/bin/env bash
# smoke-site-reference-surfaces.sh — deploy + validate Willowy Hollow Cursor surfaces
#
# Run: bash scripts/smoke-site-reference-surfaces.sh
# Exit 0 = surfaces wired for willowyhollow workspace roots.

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

echo "=== smoke-site-reference-surfaces ==="
bash scripts/deploy-site-reference.sh
bash scripts/validate-site-reference-surfaces.sh
echo ""
echo "smoke-site-reference-surfaces: PASS"
