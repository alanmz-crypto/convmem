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
  CRUSH_DIR="$(dirname "$CRUSH_CONFIG")"
  RULES_DIR="$CRUSH_DIR/rules"
  mkdir -p "$RULES_DIR"
  cp docs/builder-reference/ousterhout-builder-digest.md "$RULES_DIR/builder-reference-ousterhout.md"
  cp docs/builder-reference/manning-builder-digest.md "$RULES_DIR/builder-reference-manning.md"
  cp docs/builder-reference/zeller-builder-digest.md "$RULES_DIR/builder-reference-zeller.md"
  cp docs/builder-reference/hard-parts-builder-digest.md "$RULES_DIR/builder-reference-hard-parts.md"
  cp docs/builder-reference/ddia-builder-digest.md "$RULES_DIR/builder-reference-ddia.md"
  cp docs/builder-reference/arch-patterns-python-builder-digest.md "$RULES_DIR/builder-reference-arch-patterns-python.md"
  cp docs/builder-reference/evolutionary-architectures-builder-digest.md "$RULES_DIR/builder-reference-evolutionary-architectures.md"
  echo "  [deploy] $RULES_DIR/builder-reference-ousterhout.md"
  echo "  [deploy] $RULES_DIR/builder-reference-manning.md"
  echo "  [deploy] $RULES_DIR/builder-reference-zeller.md"
  echo "  [deploy] $RULES_DIR/builder-reference-hard-parts.md"
  echo "  [deploy] $RULES_DIR/builder-reference-ddia.md"
  echo "  [deploy] $RULES_DIR/builder-reference-arch-patterns-python.md"
  echo "  [deploy] $RULES_DIR/builder-reference-evolutionary-architectures.md"

  python3 - <<'PY' "$CRUSH_CONFIG"
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
rules_dir = config_path.parent / "rules"
digests = [
    str((rules_dir / f"builder-reference-{name}.md").expanduser())
    for name in ("ousterhout", "manning", "zeller", "hard-parts", "ddia", "arch-patterns-python", "evolutionary-architectures")
]
# Canonical global_context_paths order (single source of truth; this script is the
# last writer in a full deploy): CONVMEM-RITUAL -> other context -> builder digests -> CRUSH.md.
# The ritual MUST stay first so it loads before CRUSH.md ponytail; see docs/inter-model/CRUSH-VERIFY.md.
ritual = "~/.config/crush/CONVMEM-RITUAL.md"
crush_md = "~/.config/crush/CRUSH.md"

with open(config_path) as f:
    cfg = json.load(f)

opts = cfg.setdefault("options", {})
original = list(opts.get("global_context_paths") or [])

digest_set = set(digests)
# Ritual must always head the list (Codex 2026-07-07): presence-only skip left
# partially migrated configs without CONVMEM-RITUAL.md after builder-reference deploy.
head = [ritual]
tail = [crush_md] if crush_md in original else []
middle = [p for p in original if p not in digest_set and p != ritual and p != crush_md]
ordered = head + middle + digests + tail

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

