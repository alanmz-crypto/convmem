#!/usr/bin/env bash
# Smoke: prod/lab write boundary — cross-lane index must refuse without CONVMEM_CONFIRM_PROD.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
pass() { echo -e "${GREEN}PASS${NC} $*"; }
fail() { echo -e "${RED}FAIL${NC} $*"; exit 1; }

python3 -m pytest "$ROOT/tests/test_runtime_guard.py" -q || fail "runtime_guard unit tests"

lab_dir="$(mktemp -d)"
trap 'rm -rf "$lab_dir"' EXIT
mkdir -p "$lab_dir/convmem-lab"
out="$(cd "$lab_dir/convmem-lab" && CONVMEM_CONFIRM_PROD= python3 "$ROOT/convmem.py" index --file /etc/hosts 2>&1 || true)"
echo "$out" | grep -q "Refusing prod write" || fail "expected cross-lane block from lab cwd"
pass "cross-lane prod index blocked without CONVMEM_CONFIRM_PROD"

out_ok="$(cd "$lab_dir/convmem-lab" && CONVMEM_CONFIRM_PROD=1 python3 "$ROOT/convmem.py" index --file /etc/hosts 2>&1 || true)"
echo "$out_ok" | grep -q "Refusing prod write" && fail "CONVMEM_CONFIRM_PROD=1 should not block on cross-lane"
pass "CONVMEM_CONFIRM_PROD=1 bypasses cross-lane guard"

echo ""
echo -e "${GREEN}=== smoke-write-guard: PASS ===${NC}"
