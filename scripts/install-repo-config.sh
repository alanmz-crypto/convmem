#!/usr/bin/env bash
# Repo-local git hygiene + hooks for this convmem clone only.
# Never uses git config --global.
#
# Sets:
#   core.hooksPath          → scripts/git-hooks (WIP-on-main pre-push)
#   pull.ff                 → only
#   rerere.enabled          → true
#   blame.ignoreRevsFile    → .git-blame-ignore-revs
#
# pull.ff=only means a plain `git pull` fails closed when histories have diverged
# (non-fast-forward) instead of creating a merge commit. Recovery:
#   Feature branch:  git fetch origin && git rebase origin/main
#   Clean main:      git fetch origin && git pull --ff-only
# If pull still fails, stop and inspect — do not force a merge pull.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOK="$ROOT/scripts/git-hooks/pre-push"
BLAME="$ROOT/.git-blame-ignore-revs"

if [[ ! -f "$HOOK" ]]; then
  echo "missing $HOOK" >&2
  exit 1
fi
if [[ ! -f "$BLAME" ]]; then
  echo "missing $BLAME (create header-only file before install)" >&2
  exit 1
fi

chmod +x "$HOOK"
cd "$ROOT"

git config --local core.hooksPath scripts/git-hooks
git config --local pull.ff only
git config --local rerere.enabled true
git config --local blame.ignoreRevsFile .git-blame-ignore-revs

echo "core.hooksPath = $(git config --get core.hooksPath)"
echo "pull.ff = $(git config --get pull.ff)"
echo "rerere.enabled = $(git config --get rerere.enabled)"
echo "blame.ignoreRevsFile = $(git config --get blame.ignoreRevsFile)"
echo "Installed. WIP-pattern pushes to main will be rejected (CONVMEM_SKIP_WIP_HOOK=1 to bypass)."
