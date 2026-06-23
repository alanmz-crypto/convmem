#!/bin/sh
# Install coordination claim lint into .git/hooks/pre-commit (convmem repo).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$ROOT/.git/hooks/pre-commit"
SRC="$ROOT/scripts/git-hooks/pre-commit-coord-lint"
MARKER="# convmem-coord-claim-lint"

if [ ! -d "$ROOT/.git" ]; then
  echo "Not a git repo: $ROOT" >&2
  exit 1
fi

if [ -f "$HOOK" ] && grep -q "$MARKER" "$HOOK" 2>/dev/null; then
  echo "Hook already installed."
  exit 0
fi

{
  echo "$MARKER"
  echo "exec \"$SRC\""
} >> "$HOOK"
chmod +x "$HOOK" "$SRC"
echo "Installed pre-commit coord lint → $HOOK"
