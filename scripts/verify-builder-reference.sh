#!/usr/bin/env bash
# verify-builder-reference.sh — check repo digests and per-surface deploy state
#
# Word-count ship gate: PASS >= 1500 words per digest (WARN 800-1499; FAIL < 800).
# Aspirational depth band 2500+ is checked by validate-builder-reference-surfaces.sh only.
#
# Run: bash scripts/verify-builder-reference.sh
# Exit 0 = all PASS or WARN only; exit 1 = any FAIL

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

HOME="${HOME:-/home/lauer}"
FAIL=0
WARN=0

status_line() {
  local label="$1"
  local result="$2"
  local detail="${3:-}"
  printf "  %-10s %-4s %s\n" "$label" "$result" "$detail"
  case "$result" in
    FAIL) FAIL=$((FAIL + 1)) ;;
    WARN) WARN=$((WARN + 1)) ;;
  esac
}

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

word_count() {
  wc -w <"$1" | tr -d ' '
}

echo "=== Builder-reference verification ==="
echo ""

# --- Repo SSoT ---
echo "Repo SSoT:"
required=(
  "docs/builder-reference/README.md"
  "docs/builder-reference/SOURCES.md"
  "docs/builder-reference/ousterhout-builder-digest.md"
  "docs/builder-reference/manning-builder-digest.md"
  "docs/builder-reference/zeller-builder-digest.md"
  "docs/builder-reference/hard-parts-builder-digest.md"
  "docs/builder-reference/ddia-builder-digest.md"
  "docs/builder-reference/arch-patterns-python-builder-digest.md"
  "docs/builder-reference/evolutionary-architectures-builder-digest.md"
)

for path in "${required[@]}"; do
  if [ -f "$path" ]; then
    status_line "$path" PASS
  else
    status_line "$path" FAIL "missing"
  fi
done

for digest in docs/builder-reference/*-builder-digest.md; do
  [ -f "$digest" ] || continue
  words="$(word_count "$digest")"
  base="$(basename "$digest")"
  if [ "$words" -lt 800 ]; then
    status_line "$base words" FAIL "$words (minimum 800)"
  elif [ "$words" -lt 1500 ]; then
    status_line "$base words" WARN "$words (ship gate >= 1500)"
  else
    status_line "$base words" PASS "$words"
  fi
done

if [ -d staging/builder-reference ] && [ -n "$(ls -A staging/builder-reference 2>/dev/null)" ]; then
  status_line "staging/" PASS "extracts present"
else
  status_line "staging/" WARN "no local extracts (needed for re-distill)"
fi

echo ""
echo "Surfaces:"

# --- Cursor ---
CURSOR_MDC=""
for candidate in "$HOME/.cursor/rules/builder-reference.mdc" \
  "$HOME/.config/Cursor/rules/builder-reference.mdc" \
  "$HOME/.config/cursor/rules/builder-reference.mdc"; do
  if [ -f "$candidate" ]; then
    CURSOR_MDC="$candidate"
    break
  fi
done

if [ -n "$CURSOR_MDC" ]; then
  status_line "Cursor" PASS "$CURSOR_MDC"
else
  status_line "Cursor" FAIL "builder-reference.mdc not found"
fi

# --- Kiro ---
KIRO_STEERING=""
for candidate in "$HOME/.kiro/steering/builder-reference.md" \
  "$HOME/.config/kiro/steering/builder-reference.md"; do
  if [ -f "$candidate" ]; then
    KIRO_STEERING="$candidate"
    break
  fi
done

if [ -n "$KIRO_STEERING" ]; then
  status_line "Kiro" PASS "$KIRO_STEERING"
else
  status_line "Kiro" FAIL "builder-reference.md steering not found"
fi

# --- Codex ---
CODEX_AGENTS=""
for candidate in "$HOME/.codex/AGENTS.md" "$HOME/.config/codex/AGENTS.md"; do
  if [ -f "$candidate" ]; then
    CODEX_AGENTS="$candidate"
    break
  fi
done

if [ -n "$CODEX_AGENTS" ] && rg -q "docs/builder-reference/" "$CODEX_AGENTS" 2>/dev/null; then
  status_line "Codex" PASS "$CODEX_AGENTS"
else
  if [ -z "$CODEX_AGENTS" ]; then
    status_line "Codex" FAIL "AGENTS.md not found"
  else
    status_line "Codex" FAIL "AGENTS.md missing builder-reference pointer"
  fi
fi

# --- Crush ---
CRUSH_CONFIG=""
for candidate in "$HOME/.config/crush/crush.json" "$HOME/.crush/crush.json"; do
  if [ -f "$candidate" ]; then
    CRUSH_CONFIG="$candidate"
    break
  fi
done

CRUSH_RULES_DIR=""
if [ -n "$CRUSH_CONFIG" ]; then
  CRUSH_RULES_DIR="$(dirname "$CRUSH_CONFIG")/rules"
fi

crush_ok=1
crush_names=(ousterhout manning zeller hard-parts ddia arch-patterns-python evolutionary-architectures)
crush_paths=()
if [ -n "$CRUSH_RULES_DIR" ]; then
  for name in "${crush_names[@]}"; do
    f="$CRUSH_RULES_DIR/builder-reference-${name}.md"
    if [ ! -f "$f" ]; then
      crush_ok=0
      status_line "Crush $name" FAIL "missing $f"
    else
      crush_paths+=("$f")
      repo_digest="docs/builder-reference/${name}-builder-digest.md"
      if [ -f "$repo_digest" ]; then
        repo_hash="$(sha256_file "$repo_digest")"
        deploy_hash="$(sha256_file "$f")"
        if [ "$repo_hash" = "$deploy_hash" ]; then
          status_line "Crush $name" PASS "sha256 match"
        else
          status_line "Crush $name" WARN "stale deploy (re-run deploy-builder-reference.sh)"
          crush_ok=0
        fi
      fi
    fi
  done
else
  crush_ok=0
  status_line "Crush" FAIL "crush.json not found"
fi

if [ "$crush_ok" -eq 1 ] && [ -n "$CRUSH_CONFIG" ]; then
  missing_paths="$(python3 - <<'PY' "$CRUSH_CONFIG"
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
rules_dir = config_path.parent / "rules"
expected = [
    str((rules_dir / f"builder-reference-{name}.md").expanduser())
    for name in ("ousterhout", "manning", "zeller", "hard-parts", "ddia", "arch-patterns-python", "evolutionary-architectures")
]
with open(config_path) as f:
    cfg = json.load(f)
paths = list((cfg.get("options") or {}).get("global_context_paths") or [])
missing = [p for p in expected if p not in paths]
if missing:
    print("MISSING:" + "|".join(missing))
else:
    print("OK")
PY
)"
  if [ "$missing_paths" = "OK" ]; then
    status_line "Crush json" PASS "global_context_paths lists all four"
  else
    status_line "Crush json" FAIL "global_context_paths missing digest paths"
    crush_ok=0
  fi
fi

echo ""
if [ "$FAIL" -gt 0 ]; then
  echo "RESULT: FAIL ($FAIL failure(s), $WARN warning(s))"
  exit 1
fi
if [ "$WARN" -gt 0 ]; then
  echo "RESULT: WARN ($WARN warning(s))"
  exit 0
fi
echo "RESULT: PASS"
exit 0
