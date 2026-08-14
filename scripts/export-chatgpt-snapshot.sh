#!/usr/bin/env bash
# Export local-only state that ChatGPT cannot see from GitHub.
# Run before a ChatGPT planning/review session and upload the output file.
#
# Captures: convmem runtime health, corpus stats, unresolved observations,
# git/worktree topology, uncommitted file inventories, and optionally the
# full source of uncommitted files in active worktrees.
#
# Usage:
#   bash scripts/export-chatgpt-snapshot.sh              # summary only
#   bash scripts/export-chatgpt-snapshot.sh --full       # include uncommitted source
#   bash scripts/export-chatgpt-snapshot.sh --full -o /tmp/snapshot.md
#
# Output: ~/Projects/convmem/chatgpt-snapshot-YYYY-MM-DD.md (default)
# No secrets, API keys, or corpus data are included.
set -euo pipefail
trap '' PIPE  # suppress SIGPIPE from head/tail truncation inside redirected block

export GIT_PAGER=cat

ROOT="${CONVMEM_ROOT:-$HOME/Projects/convmem}"
FULL=0
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) FULL=1; shift ;;
    -o|--output) OUTPUT="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,/^set -/{ /^#/s/^# \?//p }' "$0"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

DATE=$(date +%Y-%m-%d)
OUTPUT="${OUTPUT:-$ROOT/chatgpt-snapshot-${DATE}.md}"

{
  echo "# ConvMem Local State Snapshot"
  echo ""
  echo "Generated: $(date -Iseconds)"
  echo "Machine: $(hostname)"
  echo ""

  # --- Runtime health ---
  echo "## convmem doctor"
  echo ""
  echo '```'
  convmem doctor 2>&1 || true
  echo '```'
  echo ""

  # --- Brief ---
  echo "## convmem brief"
  echo ""
  echo '```'
  convmem brief --stdout-only 2>&1 || true
  echo '```'
  echo ""

  # --- Unresolved ---
  echo "## convmem unresolved"
  echo ""
  echo '```'
  convmem unresolved 2>&1 || true
  echo '```'
  echo ""

  # --- Main checkout git status ---
  echo "## Git status (main checkout)"
  echo ""
  echo '```'
  cd "$ROOT"
  git status --short --branch
  echo '```'
  echo ""

  # --- Active worktrees ---
  echo "## Worktrees"
  echo ""
  echo '```'
  git worktree list
  echo '```'
  echo ""

  # --- Per-worktree uncommitted inventory ---
  echo "## Uncommitted files per worktree"
  echo ""
  while IFS= read -r line; do
    wt_path=$(echo "$line" | awk '{print $1}')
    # Skip the main checkout (already shown above)
    [[ "$wt_path" == "$ROOT" ]] && continue
    # Only show worktrees with uncommitted changes
    status=$(cd "$wt_path" 2>/dev/null && git status --short 2>/dev/null || echo "")
    if [[ -n "$status" ]]; then
      branch=$(cd "$wt_path" && git branch --show-current 2>/dev/null || echo "(detached)")
      echo "### $wt_path"
      echo "Branch: \`$branch\`"
      echo ""
      echo '```'
      echo "$status"
      echo '```'
      echo ""

      # Optionally include full source of uncommitted files
      if [[ $FULL -eq 1 ]]; then
        # Tracked modifications
        tracked_diff=$(cd "$wt_path" && git diff 2>/dev/null || true)
        if [[ -n "$tracked_diff" ]]; then
          echo "#### Tracked changes (diff)"
          echo ""
          echo '```diff'
          echo "$tracked_diff"
          echo '```'
          echo ""
        fi

        # Untracked new files (source only, skip binaries/large)
        declare -A seen_dirs=()
        while IFS= read -r untracked; do
          [[ -z "$untracked" ]] && continue
          file="${untracked:3}"  # strip "?? " prefix
          file="${file%/}"      # strip trailing slash
          full_path="$wt_path/$file"
          if [[ -f "$full_path" ]]; then
            size=$(stat --format=%s "$full_path" 2>/dev/null || echo 0)
            # Detect language for syntax highlighting
            ext="${file##*.}"
            lang="text"
            case "$ext" in
              py) lang="python" ;;
              sh|bash) lang="bash" ;;
              md) lang="markdown" ;;
              json) lang="json" ;;
              toml) lang="toml" ;;
              yaml|yml) lang="yaml" ;;
            esac
            # Skip files > 100KB or binary
            if [[ $size -lt 102400 ]] && file "$full_path" | grep -q text; then
              echo "#### $file (untracked, ${size} bytes)"
              echo ""
              echo "\`\`\`$lang"
              cat "$full_path"
              echo '```'
              echo ""
            else
              echo "#### $file (untracked, ${size} bytes, skipped — too large or binary)"
              echo ""
            fi
          elif [[ -d "$full_path" ]]; then
            # Deduplicate directory listings
            [[ -n "${seen_dirs[$file]:-}" ]] && continue
            seen_dirs[$file]=1
            echo "#### $file/ (untracked directory)"
            echo '```'
            find "$full_path" -type f \( -name '*.py' -o -name '*.sh' -o -name '*.md' \) | sort | head -30 | while IFS= read -r f; do
              rel="${f#$full_path/}"
              echo "  $rel ($(wc -l < "$f") lines)"
            done
            echo '```'
            echo ""
          fi
        done <<< "$(cd "$wt_path" && git status --short | grep '^??' || true)"
        unset seen_dirs
      fi
    fi
  done < <(git worktree list | tail -n +1)

  # --- Recent branches with tracking info ---
  echo "## Branches (recent, with tracking)"
  echo ""
  echo '```'
  git --no-pager branch -vv --sort=-committerdate 2>/dev/null | head -30 || true
  echo '```'
  echo ""

  echo "---"
  echo ""
  echo "End of snapshot. No secrets or corpus data included."

} > "$OUTPUT"

echo "Snapshot written to: $OUTPUT ($(wc -c < "$OUTPUT" | tr -d ' ') bytes)"
echo ""
echo "Upload this file to ChatGPT at the start of a session."
