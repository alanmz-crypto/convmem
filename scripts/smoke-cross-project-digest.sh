#!/usr/bin/env bash
# Smoke: prod cross-project digest deterministic path (no LLM).
# Exit 0 = digest mechanics OK. Exit 1 = blocked.
#
# Run: bash scripts/smoke-cross-project-digest.sh

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
pass() { echo -e "${GREEN}PASS${NC} $*"; }
fail() { echo -e "${RED}FAIL${NC} $*"; exit 1; }

ROOT="${CONVMEM_ROOT:-$HOME/Projects/convmem}"
DATA="$HOME/.local/share/convmem"
PY="${CONVMEM_PY:-$HOME/miniforge3/envs/convmem/bin/python}"

echo "=== convmem cross-project digest smoke ==="

convmem doctor || fail "convmem doctor failed"
pass "doctor"

DIGEST_OUT="$DATA/digests/smoke-$(date +%Y%m%d-%H%M%S).md"
"$PY" "$ROOT/cross_project_digest.py" --skip-ask -o "$DIGEST_OUT" || fail "digest --skip-ask failed"
[ -s "$DIGEST_OUT" ] || fail "digest output empty"
case "$DIGEST_OUT" in
  "$DATA"/*) ;;
  *) fail "digest not under prod data dir" ;;
esac
pass "digest wrote $DIGEST_OUT"

grep -q "Corpus snapshot" "$DIGEST_OUT" || fail "missing Corpus snapshot"
grep -q "Recent approved decisions" "$DIGEST_OUT" || fail "missing Recent approved decisions"
grep -q "Open coordination observations" "$DIGEST_OUT" || fail "missing Open coordination observations"
pass "core headings present"

if [ -s "$DATA/link_queue.jsonl" ]; then
  grep -q "Link queue candidates" "$DIGEST_OUT" || fail "link_queue.jsonl non-empty but section missing"
  pass "link queue section"
else
  echo "SKIP link queue (empty or missing link_queue.jsonl)"
fi

if [ -f "$DATA/attempts.jsonl" ] && grep -qE '"outcome"\s*:\s*"(failed|partial)"' "$DATA/attempts.jsonl" 2>/dev/null; then
  grep -q "Do not retry" "$DIGEST_OUT" || fail "attempts.jsonl present but ## Do not retry missing"
  grep -qE "FAILED|PARTIAL" "$DIGEST_OUT" || fail "Do not retry missing outcome labels"
  pass "Do not retry (attempts.jsonl present)"
  ATTEMPTS_FILE="$DATA/attempts.jsonl" bash "$ROOT/scripts/precheck-path.sh" "cross_project_digest.py" | grep -q "WARN" \
    && pass "precheck-path warns on known path" \
    || echo "SKIP precheck warn (no matching path in attempts)"
else
  echo "SKIP Do not retry (no attempts.jsonl or no failed/partial rows)"
  echo "  Tip: cp config/attempts.jsonl.example ~/.local/share/convmem/attempts.jsonl and edit"
fi

bash "$ROOT/scripts/precheck-path.sh" "cross_project_digest.py" >/dev/null || fail "precheck-path must exit 0"
pass "precheck-path exits 0"

cd "$ROOT"
python -m pytest tests/test_cross_project_digest.py tests/test_precheck_path.py -q || fail "unit tests failed"
pass "unit tests"

echo ""
echo -e "${GREEN}=== smoke-cross-project-digest: PASS ===${NC}"
bash "$ROOT/scripts/emit-next-steps.sh" smoke-cross-project-digest
