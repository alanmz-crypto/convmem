#!/usr/bin/env bash
# deploy-builder-reference.sh — deploy builder-reference digests to agent surfaces

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/..")"

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
  if [ ! -f "$path" ]; then
    echo "ERROR: missing required builder-reference file: $path" >&2
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

CODEX_DIR=""
for candidate in "$HOME/.codex" "$HOME/.config/codex"; do
  if [ -d "$candidate" ]; then
    CODEX_DIR="$candidate"
    break
  fi
done

CRUSH_CONFIG=""
for candidate in "$HOME/.config/crush/crush.json" "$HOME/.crush/crush.json"; do
  if [ -f "$candidate" ]; then
    CRUSH_CONFIG="$candidate"
    break
  fi
done

echo "=== Deploying builder-reference surfaces ==="

if [ -n "$CURSOR_RULES" ]; then
  cp config/cursor-rules-builder-reference.mdc.example "$CURSOR_RULES/builder-reference.mdc"
  echo "  [deploy] $CURSOR_RULES/builder-reference.mdc"
else
  echo "  [skip]   Cursor rules directory not found"
fi

if [ -n "$KIRO_DIR" ]; then
  cp config/kiro-steering-builder-reference.example.md "$KIRO_DIR/builder-reference.md"
  echo "  [deploy] $KIRO_DIR/builder-reference.md"
else
  echo "  [skip]   Kiro steering directory not found"
fi

if [ -n "$CODEX_DIR" ]; then
  codex_result="$(python3 - <<'PY' "$CODEX_DIR/AGENTS.md"
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8") if path.is_file() else ""
digests = [
    ("ousterhout-builder-digest.md", "module boundaries and protocol surfaces"),
    ("manning-builder-digest.md", "ranking, chunking, retrieval, and evaluation"),
    ("zeller-builder-digest.md", "reproduction, triage, and verification"),
    ("hard-parts-builder-digest.md", "trade-offs, data ownership, split decisions"),
    ("ddia-builder-digest.md", "ledger leader, Chroma follower, watch stream"),
    ("arch-patterns-python-builder-digest.md", "repository, UoW, F1 refine queue"),
    ("evolutionary-architectures-builder-digest.md", "fitness functions, thresholds, ownership"),
]
if "docs/builder-reference/" not in text:
    block = "\n## Builder reference\n\nBefore convmem architecture edits, read the relevant digest in\n`docs/builder-reference/`:\n\n"
    block += "\n".join(f"- `{name}` for {desc}" for name, desc in digests)
    block += "\n"
    path.write_text(text.rstrip() + block, encoding="utf-8")
    print("append")
else:
    changed = False
    for name, desc in digests:
        if name not in text:
            text = text.rstrip() + f"\n- `{name}` for {desc}\n"
            changed = True
    if changed:
        path.write_text(text, encoding="utf-8")
        print("patch")
    else:
        print("skip")
PY
)"
  echo "  [deploy] $CODEX_DIR/AGENTS.md ($codex_result)"
else
  echo "  [skip]   Codex config directory not found"
fi

if [ -n "$CRUSH_CONFIG" ]; then
  # Stage 4 approach A: digests are on-demand under builder-reference/, not standing
  # context. rules/ keeps ritual/protocol/ksweep only; thin pointer lives in rules/.
  CRUSH_DIR="$(dirname "$CRUSH_CONFIG")"
  RULES_DIR="$CRUSH_DIR/rules"
  DIGEST_DIR="$CRUSH_DIR/builder-reference"
  mkdir -p "$RULES_DIR" "$DIGEST_DIR"

  digest_names=(ousterhout manning zeller hard-parts ddia arch-patterns-python evolutionary-architectures)
  for name in "${digest_names[@]}"; do
    src="docs/builder-reference/${name}-builder-digest.md"
    # Prefer legacy rules/ filename if present (migration); else repo digest.
    legacy="$RULES_DIR/builder-reference-${name}.md"
    dst="$DIGEST_DIR/builder-reference-${name}.md"
    if [ -f "$legacy" ]; then
      mv -f "$legacy" "$dst"
    else
      cp "$src" "$dst"
    fi
    echo "  [deploy] $dst"
  done

  # Drop any leftover digest copies under rules/ (double-load prevention).
  rm -f "$RULES_DIR"/builder-reference-ousterhout.md \
    "$RULES_DIR"/builder-reference-manning.md \
    "$RULES_DIR"/builder-reference-zeller.md \
    "$RULES_DIR"/builder-reference-hard-parts.md \
    "$RULES_DIR"/builder-reference-ddia.md \
    "$RULES_DIR"/builder-reference-arch-patterns-python.md \
    "$RULES_DIR"/builder-reference-evolutionary-architectures.md

  cp config/crush-rules-builder-reference-pointer.example.md \
    "$RULES_DIR/builder-reference-pointer.md"
  echo "  [deploy] $RULES_DIR/builder-reference-pointer.md"

  python3 - <<'PY' "$CRUSH_CONFIG"
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
# Canonical standing context (Stage 4 approach A): ritual -> rules/ -> CRUSH.md.
# Digests are NOT listed; they live in ~/.config/crush/builder-reference/ on demand.
# See docs/plans/EXECUTION-stage4-context-compression.md Task 1.
ritual = "~/.config/crush/CONVMEM-RITUAL.md"
rules_dir = "~/.config/crush/rules/"
crush_md = "~/.config/crush/CRUSH.md"
ordered = [ritual, rules_dir, crush_md]

with open(config_path) as f:
    cfg = json.load(f)

opts = cfg.setdefault("options", {})
original = list(opts.get("global_context_paths") or [])

if ordered != original:
    opts["global_context_paths"] = ordered
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    print("deploy")
else:
    print("skip")
PY
else
  echo "  [skip]   Crush config not found"
fi

echo ""
echo "Builder-reference deployment complete."

if [ -x scripts/verify-builder-reference.sh ]; then
  echo ""
  bash scripts/verify-builder-reference.sh || true
fi

