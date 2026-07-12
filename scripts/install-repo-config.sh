#!/usr/bin/env bash
# Repo-local git hygiene + hooks for this convmem clone only.
# Never uses git config --global.
#
# Sets:
#   core.hooksPath          → scripts/git-hooks (pre-commit + pre-push block main)
#   pull.ff                 → only
#   rerere.enabled          → true
#   blame.ignoreRevsFile    → .git-blame-ignore-revs
#
# pull.ff=only means a plain `git pull` fails closed when histories have diverged
# (non-fast-forward) instead of creating a merge commit. Recovery:
#   Feature branch:  git fetch origin && git rebase origin/main
#   Clean main:      git fetch origin && git pull --ff-only
# If pull still fails, stop and inspect — do not force a merge pull.
#
# Local CONVMEM_SKIP_MAIN_HOOK=1 skips hooks only (not GitHub authz).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PRE_PUSH="$ROOT/scripts/git-hooks/pre-push"
PRE_COMMIT="$ROOT/scripts/git-hooks/pre-commit"
BLAME="$ROOT/.git-blame-ignore-revs"

for hook in "$PRE_PUSH" "$PRE_COMMIT"; do
  if [[ ! -f "$hook" ]]; then
    echo "missing $hook" >&2
    exit 1
  fi
  chmod +x "$hook"
done
if [[ ! -f "$BLAME" ]]; then
  echo "missing $BLAME (create header-only file before install)" >&2
  exit 1
fi

cd "$ROOT"

git config --local core.hooksPath scripts/git-hooks
git config --local pull.ff only
git config --local rerere.enabled true
git config --local blame.ignoreRevsFile .git-blame-ignore-revs

echo "core.hooksPath = $(git config --get core.hooksPath)"
echo "pull.ff = $(git config --get pull.ff)"
echo "rerere.enabled = $(git config --get rerere.enabled)"
echo "blame.ignoreRevsFile = $(git config --get blame.ignoreRevsFile)"
echo "Installed. Commits/pushes to main are rejected (CONVMEM_SKIP_MAIN_HOOK=1 = local hook skip only)."
