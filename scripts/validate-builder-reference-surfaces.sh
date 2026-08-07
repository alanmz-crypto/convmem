#!/usr/bin/env bash
# validate-builder-reference-surfaces.sh — live config/CLI checks per agent surface
#
# Complements verify-builder-reference.sh (filesystem + sha256).
# Word counts: PASS >= 1500 (ship gate, matches verify-builder-reference.sh);
# WARN 1500-2499 (aspirational depth); PASS >= 2500 (ideal band).
# Does not prove agents cite digests in UI — see README soak table.
#
# Run: bash scripts/validate-builder-reference-surfaces.sh

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

HOME="${HOME:-/home/lauer}"
FAIL=0
WARN=0
LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

note() { printf "%s\n" "$1" | tee -a "$LOG"; }
pass() { note "  PASS  $1"; }
warn() { note "  WARN  $1"; WARN=$((WARN + 1)); }
fail() { note "  FAIL  $1"; FAIL=$((FAIL + 1)); }

note "=== Builder-reference surface validation ==="
note "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
note ""

# --- Cursor ---
note "Cursor:"
CURSOR_MDC=""
for candidate in "$HOME/.cursor/rules/builder-reference.mdc" \
  "$HOME/.config/Cursor/rules/builder-reference.mdc"; do
  if [ -f "$candidate" ]; then
    CURSOR_MDC="$candidate"
    break
  fi
done

if [ -z "$CURSOR_MDC" ]; then
  fail "builder-reference.mdc not deployed"
else
  pass "deployed at $CURSOR_MDC"
  if rg -q 'alwaysApply:\s*false' "$CURSOR_MDC" 2>/dev/null; then
    pass "alwaysApply: false (scoped, not global noise)"
  else
    warn "alwaysApply not false — may load on every workspace"
  fi
  if rg -q 'globs:.*Projects/convmem' "$CURSOR_MDC" 2>/dev/null; then
    pass "globs target convmem repo"
  else
    warn "globs may not match ~/Projects/convmem"
  fi
  for digest in ousterhout manning zeller hard-parts ddia arch-patterns-python evolutionary-architectures; do
    if rg -q "${digest}-builder-digest" "$CURSOR_MDC" 2>/dev/null; then
      pass "lists ${digest}-builder-digest.md"
    else
      fail "missing ${digest} in mdc"
    fi
  done
  if diff -q config/cursor-rules-builder-reference.mdc.example "$CURSOR_MDC" >/dev/null 2>&1; then
    pass "matches repo example (byte-identical)"
  else
    warn "differs from config/cursor-rules-builder-reference.mdc.example"
  fi
fi

# --- Kiro ---
note ""
note "Kiro:"
KIRO_STEERING=""
for candidate in "$HOME/.kiro/steering/builder-reference.md" \
  "$HOME/.config/kiro/steering/builder-reference.md"; do
  if [ -f "$candidate" ]; then
    KIRO_STEERING="$candidate"
    break
  fi
done

if [ -z "$KIRO_STEERING" ]; then
  fail "builder-reference steering not deployed"
else
  pass "deployed at $KIRO_STEERING"
  if rg -q 'inclusion:\s*manual' "$KIRO_STEERING" 2>/dev/null; then
    pass "inclusion: manual (opt-in steering)"
  else
    warn "inclusion not manual"
  fi
  if rg -q 'name:\s*builder-reference' "$KIRO_STEERING" 2>/dev/null; then
    pass "steering name builder-reference"
  else
    warn "steering name missing or different"
  fi
  if command -v kiro >/dev/null 2>&1; then
    pass "kiro CLI on PATH"
  else
    warn "kiro CLI not on PATH — UI-only validation"
  fi
fi

# --- Codex ---
note ""
note "Codex:"
CODEX_AGENTS=""
for candidate in "$HOME/.codex/AGENTS.md" "$HOME/.config/codex/AGENTS.md"; do
  if [ -f "$candidate" ]; then
    CODEX_AGENTS="$candidate"
    break
  fi
done

if [ -z "$CODEX_AGENTS" ]; then
  fail "AGENTS.md not found"
else
  pass "AGENTS.md at $CODEX_AGENTS"
  if rg -q "docs/builder-reference/" "$CODEX_AGENTS" 2>/dev/null; then
    pass "builder-reference pointer present"
  else
    fail "no docs/builder-reference/ pointer"
  fi
  for digest in ousterhout manning zeller hard-parts ddia arch-patterns-python evolutionary-architectures; do
    if rg -q "${digest}-builder-digest" "$CODEX_AGENTS" 2>/dev/null; then
      pass "lists ${digest}-builder-digest.md"
    else
      warn "${digest} not named in AGENTS.md"
    fi
  done
  if command -v codex >/dev/null 2>&1; then
    pass "codex CLI on PATH ($(codex --version 2>/dev/null | head -1 || echo version unknown))"
  else
    warn "codex CLI not on PATH"
  fi
  if [ -f .codex/config.toml ] || [ -f "$HOME/.codex/config.toml" ]; then
    pass "codex config.toml present"
  else
    warn "no codex config.toml — sandbox may block convmem ask"
  fi
fi

# --- Crush ---
note ""
note "Crush:"
CRUSH_CONFIG=""
for candidate in "$HOME/.config/crush/crush.json" "$HOME/.crush/crush.json"; do
  if [ -f "$candidate" ]; then
    CRUSH_CONFIG="$candidate"
    break
  fi
done

if [ -z "$CRUSH_CONFIG" ]; then
  fail "crush.json not found"
else
  pass "crush.json at $CRUSH_CONFIG"
  python3 - <<'PY' "$CRUSH_CONFIG"
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
crush_dir = config_path.parent
digest_dir = crush_dir / "builder-reference"
rules_dir = crush_dir / "rules"
names = ("ousterhout", "manning", "zeller", "hard-parts", "ddia", "arch-patterns-python", "evolutionary-architectures")
with open(config_path) as f:
    cfg = json.load(f)
paths = list((cfg.get("options") or {}).get("global_context_paths") or [])
expected = [
    "~/.config/crush/CONVMEM-RITUAL.md",
    "~/.config/crush/rules/",
    "~/.config/crush/CRUSH.md",
]
if paths != expected:
    print(f"FAIL  global_context_paths want ritual/rules/CRUSH.md got {paths}")
else:
    print("PASS  standing context = ritual + rules/ + CRUSH.md")

for n in names:
    p = digest_dir / f"builder-reference-{n}.md"
    legacy = rules_dir / f"builder-reference-{n}.md"
    if legacy.is_file():
        print(f"FAIL  digest still in rules/: {legacy.name}")
    elif not p.is_file():
        print(f"FAIL  missing on-demand digest {p}")
    elif not p.read_text(encoding="utf-8").lstrip().startswith("#"):
        print(f"WARN  {p.name} does not start with markdown heading")
    else:
        print(f"PASS  {p.name} on-demand ({p.stat().st_size} bytes)")

pointer = rules_dir / "builder-reference-pointer.md"
if pointer.is_file():
    print(f"PASS  builder-reference-pointer.md present")
else:
    print(f"FAIL  missing {pointer}")

mcp = (cfg.get("mcp") or {}).get("convmem") or {}
timeout = mcp.get("timeout")
if timeout:
    print(f"PASS  mcp.convmem.timeout={timeout}s")
else:
    print("WARN  mcp.convmem.timeout not set")
PY
  if command -v crush >/dev/null 2>&1; then
    pass "crush CLI on PATH"
  else
    warn "crush CLI not on PATH"
  fi
fi

# --- Repo path resolution (all surfaces) ---
note ""
note "Repo digests (agent Read targets):"
for digest in docs/builder-reference/*-builder-digest.md; do
  if [ -f "$digest" ]; then
    words=$(wc -w <"$digest" | tr -d ' ')
    if [ "$words" -ge 2500 ]; then
      pass "$(basename "$digest") ($words words)"
    elif [ "$words" -ge 1500 ]; then
      warn "$(basename "$digest") ($words words — aspirational 2500+)"
    elif [ "$words" -ge 800 ]; then
      warn "$(basename "$digest") ($words words — below 1500 ship gate)"
    else
      fail "$(basename "$digest") ($words words — below 800 minimum)"
    fi
  fi
done

note ""
if [ "$FAIL" -gt 0 ]; then
  note "RESULT: FAIL ($FAIL failure(s), $WARN warning(s))"
  exit 1
fi
if [ "$WARN" -gt 0 ]; then
  note "RESULT: WARN ($WARN warning(s)) — config OK, digests or CLI gaps remain"
  exit 0
fi
note "RESULT: PASS"
exit 0
