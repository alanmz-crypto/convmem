#!/usr/bin/env bash
# validate-site-reference-surfaces.sh — live config checks for Willowy Hollow Cursor surfaces
#
# Complements verify-site-reference.sh (repo slices). Proves workspace-local rules
# exist so Cursor loads site-reference when root is a willowyhollow repo.
#
# Run: bash scripts/validate-site-reference-surfaces.sh

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

HOME="${HOME:-/home/lauer}"
FAIL=0
WARN=0

note() { printf "%s\n" "$1"; }
pass() { note "  PASS  $1"; }
warn() { note "  WARN  $1"; WARN=$((WARN + 1)); }
fail() { note "  FAIL  $1"; FAIL=$((FAIL + 1)); }

note "=== Site-reference surface validation ==="
note "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
note ""

# --- User-level Cursor rule (cross-workspace globs) ---
note "Cursor (user rules):"
CURSOR_MDC=""
for candidate in "$HOME/.cursor/rules/site-reference.mdc" \
  "$HOME/.config/Cursor/rules/site-reference.mdc"; do
  if [ -f "$candidate" ]; then
    CURSOR_MDC="$candidate"
    break
  fi
done

if [ -z "$CURSOR_MDC" ]; then
  fail "site-reference.mdc not deployed to user rules"
else
  pass "deployed at $CURSOR_MDC"
  if rg -q 'alwaysApply:\s*false' "$CURSOR_MDC" 2>/dev/null; then
    pass "alwaysApply: false (glob-scoped fallback)"
  else
    warn "user rule alwaysApply not false"
  fi
  for token in willowyhollow-practice 'WordPress/willowyhollow/**' willowyhollow-dev; do
    if rg -q "$token" "$CURSOR_MDC" 2>/dev/null; then
      pass "globs mention $token"
    else
      fail "globs missing $token"
    fi
  done
  for slice in site-address-consistency php-version-parity backup-before-write-gate; do
    if rg -q "$slice" "$CURSOR_MDC" 2>/dev/null; then
      pass "lists $slice"
    else
      fail "missing $slice in user mdc"
    fi
  done
fi

# --- Workspace-local rules (primary — alwaysApply in willowyhollow roots) ---
note ""
note "Cursor (willowyhollow workspace roots):"
WILLOWY_WORKSPACES=(
  "$HOME/WordPress/willowyhollow-practice"
  "$HOME/WordPress/willowyhollow"
  "$HOME/GitClones/willowyhollow-dev"
)
EXAMPLE_WS="config/cursor-rules-site-reference-workspace.mdc.example"

for ws in "${WILLOWY_WORKSPACES[@]}"; do
  rule="$ws/.cursor/rules/site-reference.mdc"
  if [ ! -d "$ws" ]; then
    warn "workspace missing: $ws"
    continue
  fi
  if [ ! -f "$rule" ]; then
    fail "no $rule — run deploy-site-reference.sh"
    continue
  fi
  pass "$(basename "$ws")/.cursor/rules/site-reference.mdc"
  if rg -q 'alwaysApply:\s*true' "$rule" 2>/dev/null; then
    pass "$(basename "$ws") alwaysApply: true"
  else
    fail "$(basename "$ws") alwaysApply not true"
  fi
  if diff -q "$EXAMPLE_WS" "$rule" >/dev/null 2>&1; then
    pass "$(basename "$ws") matches repo example"
  else
    warn "$(basename "$ws") differs from workspace example"
  fi
done

# --- Glob path simulation (absolute paths Cursor uses) ---
note ""
note "Glob match simulation (absolute paths):"
python3 - <<'PY'
import fnmatch
import sys

home = __import__("os").environ.get("HOME", "/home/lauer")
patterns_raw = ""
mdc = f"{home}/.cursor/rules/site-reference.mdc"
try:
    for line in open(mdc, encoding="utf-8"):
        if line.startswith("globs:"):
            patterns_raw = line.split(":", 1)[1].strip().strip('"')
            break
except FileNotFoundError:
    print("FAIL  user site-reference.mdc missing for glob test")
    sys.exit(0)

patterns = [p.strip() for p in patterns_raw.split(",") if p.strip()]
samples = [
    ("practice AGENTS.md", f"{home}/WordPress/willowyhollow-practice/AGENTS.md"),
    ("preview theme", f"{home}/WordPress/willowyhollow/wp-content/themes/astra-child/functions.php"),
    ("willowyhollow-dev staging", f"{home}/GitClones/willowyhollow-dev/wp-content/themes/astra-child/functions.php"),
    ("convmem (negative)", f"{home}/Projects/convmem/mcp_server.py"),
]
fail = 0
for label, path in samples:
    matched = any(fnmatch.fnmatch(path, pat) for pat in patterns)
    expect = label != "convmem (negative)"
    if matched == expect:
        print(f"PASS  {label}: matched={matched}")
    else:
        print(f"FAIL  {label}: matched={matched} (expected {expect})")
        fail += 1
if fail:
    sys.exit(1)
PY
if [ $? -eq 0 ]; then
  pass "glob simulation complete"
else
  fail "glob simulation mismatches"
fi

# --- Practice AGENTS.md pointer ---
note ""
note "Practice AGENTS.md:"
AGENTS="$HOME/WordPress/willowyhollow-practice/AGENTS.md"
if [ -f "$AGENTS" ]; then
  if rg -q 'site-reference/NOTES' "$AGENTS" 2>/dev/null; then
    pass "AGENTS.md links site-reference/NOTES.md"
  else
    fail "AGENTS.md missing site-reference pointer"
  fi
else
  warn "practice AGENTS.md not found"
fi

# --- Kiro ---
note ""
note "Kiro:"
KIRO_STEERING=""
for candidate in "$HOME/.kiro/steering/site-reference.md" \
  "$HOME/.config/kiro/steering/site-reference.md"; do
  if [ -f "$candidate" ]; then
    KIRO_STEERING="$candidate"
    break
  fi
done
if [ -z "$KIRO_STEERING" ]; then
  warn "site-reference steering not deployed"
else
  pass "deployed at $KIRO_STEERING"
  if rg -q 'name:\s*site-reference' "$KIRO_STEERING" 2>/dev/null; then
    pass "steering name site-reference"
  else
    warn "steering name missing"
  fi
fi

note ""
if [ "$FAIL" -gt 0 ]; then
  note "RESULT: FAIL ($FAIL failure(s), $WARN warning(s))"
  exit 1
fi
if [ "$WARN" -gt 0 ]; then
  note "RESULT: WARN ($WARN warning(s))"
  exit 0
fi
note "RESULT: PASS"
exit 0
