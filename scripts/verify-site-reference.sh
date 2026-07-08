#!/usr/bin/env bash
# verify-site-reference.sh — repo checks for docs/site-reference (no surface deploy)
#
# Run: bash scripts/verify-site-reference.sh
# Exit 0 = PASS or WARN only; exit 1 = any FAIL

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir/.."

FAIL=0
WARN=0
SITE_REF="docs/site-reference"
MAX_SLICE_WORDS=800
MIN_SLICE_WORDS=30

REQUIRED_SLICES=(
  php-version-parity.md
  site-address-consistency.md
  backup-before-write-gate.md
)

status_line() {
  local label="$1"
  local result="$2"
  local detail="${3:-}"
  printf "  %-40s %-4s %s\n" "$label" "$result" "$detail"
  case "$result" in
    FAIL) FAIL=$((FAIL + 1)) ;;
    WARN) WARN=$((WARN + 1)) ;;
  esac
}

word_count() {
  wc -w <"$1" | tr -d ' '
}

echo "=== Site-reference verification ==="
echo ""

echo "Hand docs:"
for path in "$SITE_REF/NOTES.md" "$SITE_REF/README.md"; do
  if [ -f "$path" ]; then
    status_line "$(basename "$path")" PASS
  else
    status_line "$(basename "$path")" FAIL "missing"
  fi
done

if [ -f "$SITE_REF/NOTES.md" ]; then
  for section in "## Pre-promote gate sequence" "## Gate registry"; do
    if grep -qF "$section" "$SITE_REF/NOTES.md"; then
      status_line "NOTES $section" PASS
    else
      status_line "NOTES $section" FAIL "missing section"
    fi
  done
fi

echo ""
echo "Required slices:"
for name in "${REQUIRED_SLICES[@]}"; do
  slice="$SITE_REF/$name"
  if [ ! -f "$slice" ]; then
    status_line "$name" FAIL "missing"
    continue
  fi
  words="$(word_count "$slice")"
  if [ "$words" -lt "$MIN_SLICE_WORDS" ]; then
    status_line "$name words" FAIL "$words (min $MIN_SLICE_WORDS)"
  elif [ "$words" -gt "$MAX_SLICE_WORDS" ]; then
    status_line "$name words" WARN "$words (cap $MAX_SLICE_WORDS)"
  else
    status_line "$name words" PASS "$words"
  fi
  if grep -qE '\*\*Use for:\*\*|^## Topic:' "$slice"; then
    status_line "$name header" PASS
  else
    status_line "$name header" FAIL "missing Use for / Topic"
  fi
done

echo ""
echo "Generated index:"

if [ ! -f "$SITE_REF/README.md" ]; then
  status_line "README.md" FAIL "missing"
else
  if grep -qF "NOTES.md" "$SITE_REF/README.md"; then
    status_line "README -> NOTES" PASS
  else
    status_line "README -> NOTES" WARN "no link to NOTES.md"
  fi
  for name in "${REQUIRED_SLICES[@]}"; do
    if grep -qF "[$name]" "$SITE_REF/README.md"; then
      status_line "README lists $name" PASS
    else
      status_line "README lists $name" FAIL "not in index"
    fi
  done
fi

echo ""
echo "Scripts:"
for script in \
  scripts/generate-site-reference.sh \
  scripts/refresh-site-reference.sh \
  scripts/verify-site-reference.sh \
  scripts/deploy-site-reference.sh \
  scripts/validate-site-reference-surfaces.sh \
  scripts/smoke-site-reference-surfaces.sh; do
  if [ -x "$script" ]; then
    status_line "$script" PASS
  elif [ -f "$script" ]; then
    status_line "$script" WARN "not executable"
  else
    status_line "$script" FAIL "missing"
  fi
done

echo ""
if [ "$FAIL" -gt 0 ]; then
  echo "verify-site-reference: FAIL ($FAIL failure(s), $WARN warning(s))"
  exit 1
fi
echo "verify-site-reference: PASS ($WARN warning(s))"
exit 0
