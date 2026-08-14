#!/usr/bin/env bash
# Build a self-contained context bundle for Claude (no repo access).
#
# Unlike the ChatGPT export (which supplements GitHub browsing), this must
# include actual source code because Claude cannot fetch it independently.
#
# Tiers:
#   1. Orientation + machine state (same as ChatGPT)
#   2. Core source code (top-level .py modules — the actual system)
#   3. Architecture, STATUS, team docs
#   4. Recent handoffs (narrative)
#   5. Tests and scripts (inventory + selected full source)
#   6. Uncommitted work from active worktrees
#
# Usage:
#   bash scripts/export-claude-bundle.sh                    # standard bundle
#   bash scripts/export-claude-bundle.sh --slim             # skip tests/scripts source
#   bash scripts/export-claude-bundle.sh --slim --handoff docs/handoff.md
#   bash scripts/export-claude-bundle.sh -o /tmp/out.md     # custom output path
#
# Output: ~/Projects/convmem/claude-bundle-YYYY-MM-DD.md (default)
# No secrets, API keys, or corpus data are included.
set -euo pipefail
trap '' PIPE

export GIT_PAGER=cat

ROOT="${CONVMEM_ROOT:-$HOME/Projects/convmem}"
SLIM=0
OUTPUT=""
HANDOFF=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --slim) SLIM=1; shift ;;
    --handoff) HANDOFF="$2"; shift 2 ;;
    -o|--output) OUTPUT="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,/^set -/{ /^#/s/^# \?//p }' "$0"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

DATE=$(date +%Y-%m-%d)
OUTPUT="${OUTPUT:-$ROOT/claude-bundle-${DATE}.md}"

emit_file() {
  local filepath="$1"
  local label="${2:-$filepath}"
  local lang="${3:-text}"

  if [[ ! -f "$filepath" ]]; then
    echo "<!-- MISSING: $filepath -->"
    return
  fi

  local size
  size=$(stat --format=%s "$filepath" 2>/dev/null || echo 0)
  echo "### $label ($size bytes)"
  echo ""
  echo "\`\`\`$lang"
  cat "$filepath"
  echo '```'
  echo ""
}

emit_python() {
  emit_file "$1" "${2:-$1}" "python"
}

{
  echo "# ConvMem Complete Context Bundle for Claude"
  echo ""
  echo "Generated: $(date -Iseconds)"
  echo "Machine: $(hostname)"
  echo "Bundle type: $(if [[ $SLIM -eq 1 ]]; then echo 'slim (no test/script source)'; else echo 'standard'; fi)"
  echo ""
  echo "This file is self-contained. Claude has no access to the GitHub repo or"
  echo "the local machine. Everything Claude needs to understand and review this"
  echo "project is included below."
  echo ""
  echo "---"
  echo ""

  # ─── PART 1: Orientation ───
  echo "# PART 1: Project Orientation"
  echo ""

  if [[ -f /tmp/chatgpt-onboard/ORIENTATION-FOR-CHATGPT.md ]]; then
    # Reuse the orientation but note it's for Claude too
    sed 's/for ChatGPT/for Claude/g; s/ChatGPT/Claude/g' /tmp/chatgpt-onboard/ORIENTATION-FOR-CHATGPT.md
  else
    cat "$ROOT/README.md"
  fi
  echo ""
  echo ""

  # ─── PART 2: Machine State ───
  echo "---"
  echo ""
  echo "# PART 2: Local Machine State"
  echo ""
  echo '```'
  convmem doctor 2>&1 || true
  echo '```'
  echo ""
  echo '```'
  convmem brief --stdout-only 2>&1 || true
  echo '```'
  echo ""
  echo '```'
  convmem unresolved 2>&1 || true
  echo '```'
  echo ""

  echo "## Git status (main)"
  echo ""
  echo '```'
  cd "$ROOT"
  git status --short --branch
  echo '```'
  echo ""

  echo "## Worktrees with uncommitted changes"
  echo ""
  while IFS= read -r line; do
    wt_path=$(echo "$line" | awk '{print $1}')
    [[ "$wt_path" == "$ROOT" ]] && continue
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
    fi
  done < <(git worktree list)

  echo "## Recent branches"
  echo ""
  echo '```'
  git --no-pager branch -vv --sort=-committerdate 2>/dev/null | head -20 || true
  echo '```'
  echo ""
  echo ""

  # ─── PART 3: Core Source Code ───
  echo "---"
  echo ""
  echo "# PART 3: Core Source Code"
  echo ""
  echo "These are the production Python modules that make up convmem."
  echo ""

  cd "$ROOT"
  for f in $(find . -maxdepth 1 -name '*.py' | sort | sed 's|^\./||'); do
    emit_python "$f"
  done

  echo ""
  echo "## Adapters"
  echo ""
  for f in $(find adapters -name '*.py' | sort); do
    emit_python "$f"
  done

  echo ""

  # ─── PART 4: Tests & Scripts ───
  echo "---"
  echo ""
  echo "# PART 4: Tests and Scripts"
  echo ""

  if [[ $SLIM -eq 1 ]]; then
    echo "## Test inventory (--slim mode, source omitted)"
    echo ""
    echo '```'
    find tests -name '*.py' -exec wc -l {} + 2>/dev/null | sort -rn | head -40
    echo '```'
    echo ""
    echo "## Script inventory (--slim mode, source omitted)"
    echo ""
    echo '```'
    find scripts -name '*.py' -o -name '*.sh' | sort | while read -r f; do
      echo "  $f ($(wc -l < "$f") lines)"
    done
    echo '```'
    echo ""
  else
    echo "## Tests"
    echo ""
    for f in $(find tests -name '*.py' | sort); do
      emit_python "$f"
    done
    echo ""
    echo "## Scripts (Python)"
    echo ""
    for f in $(find scripts -name '*.py' | sort); do
      emit_python "$f"
    done
    echo ""
    echo "## Scripts (Shell)"
    echo ""
    for f in $(find scripts -name '*.sh' | sort); do
      emit_file "$f" "$f" "bash"
    done
    echo ""
  fi

  # ─── PART 5: Documentation ───
  echo "---"
  echo ""
  echo "# PART 5: Project Documentation"
  echo ""

  emit_file "AGENTS.md" "AGENTS.md" "markdown"
  emit_file "README.md" "README.md" "markdown"

  echo ""
  echo "## Team Charter"
  echo ""
  emit_file "docs/inter-model/TEAM-CHARTER-2026-07-06.md" "TEAM-CHARTER" "markdown"

  echo ""
  echo "## LATEST.md (handoff state)"
  echo ""
  emit_file "docs/inter-model/LATEST.md" "LATEST.md" "markdown"

  echo ""
  echo "## Active STATUS files"
  echo ""
  for f in docs/plans/STATUS-*.md; do
    emit_file "$f" "$(basename "$f")" "markdown"
  done

  echo ""
  echo "## Architecture locks (active arcs)"
  echo ""
  for f in \
    docs/plans/ARCHITECTURE-judgebench.md \
    docs/plans/ARCHITECTURE-shadow-ledger-phase0.md \
    docs/plans/ARCHITECTURE-r2b-capture-auth.md \
    docs/plans/ARCHITECTURE-complete-data-backup-correction-v2.md
  do
    [[ -f "$f" ]] && emit_file "$f" "$(basename "$f")" "markdown"
  done

  echo ""
  echo "## Recent handoffs (Aug 7-10)"
  echo ""
  for f in \
    docs/inter-model/CRUSH-2026-08-07-judge-bench-analysis.md \
    docs/inter-model/CODEX-2026-08-07-judge-bench-implementation-handoff.md \
    docs/inter-model/CRUSH-2026-08-08-index-complete-judgebench-unblock.md \
    docs/inter-model/DEEPSEEK-FLASH-2026-08-08-judgebench-delegate-handoff.md \
    docs/inter-model/FLASH-2026-08-08-post-rebuild-verify-handoff.md \
    docs/inter-model/KIRO-2026-08-09-arc-brief-flash-followup.md \
    docs/inter-model/CURSOR-2026-08-09-judgebench-T2-T5-complete.md \
    docs/inter-model/CURSOR-2026-08-09-judgebench-T2-T5-handoff.md
  do
    [[ -f "$f" ]] && emit_file "$f" "$(basename "$f")" "markdown"
  done

  echo ""

  # ─── PART 6: Uncommitted source from active worktrees ───
  echo "---"
  echo ""
  echo "# PART 6: Uncommitted Source (Active Worktrees)"
  echo ""
  echo "These files exist only on the local machine — not on GitHub."
  echo ""

  cd "$ROOT"
  while IFS= read -r line; do
    wt_path=$(echo "$line" | awk '{print $1}')
    [[ "$wt_path" == "$ROOT" ]] && continue
    status=$(cd "$wt_path" 2>/dev/null && git status --short 2>/dev/null || echo "")
    if [[ -n "$status" ]]; then
      branch=$(cd "$wt_path" && git branch --show-current 2>/dev/null || echo "(detached)")
      has_interesting=0
      # Check if there are .py or .md untracked files or tracked diffs
      if echo "$status" | grep -qE '^\?\? .*\.(py|md|sh|toml)$|^ M '; then
        has_interesting=1
      fi
      [[ $has_interesting -eq 0 ]] && continue

      echo "## Worktree: $wt_path"
      echo "Branch: \`$branch\`"
      echo ""

      # Tracked diffs
      tracked_diff=$(cd "$wt_path" && git diff -- '*.py' '*.md' '*.sh' '*.toml' 2>/dev/null || true)
      if [[ -n "$tracked_diff" ]]; then
        echo "### Tracked changes"
        echo ""
        echo '```diff'
        echo "$tracked_diff"
        echo '```'
        echo ""
      fi

      # Untracked source files
      while IFS= read -r untracked; do
        [[ -z "$untracked" ]] && continue
        file="${untracked:3}"
        file="${file%/}"
        full_path="$wt_path/$file"
        if [[ -f "$full_path" ]]; then
          ext="${file##*.}"
          case "$ext" in
            py|md|sh|toml|json|yaml|yml) ;;
            *) continue ;;
          esac
          size=$(stat --format=%s "$full_path" 2>/dev/null || echo 0)
          [[ $size -gt 102400 ]] && continue
          lang="text"
          case "$ext" in
            py) lang="python" ;;
            sh|bash) lang="bash" ;;
            md) lang="markdown" ;;
            json) lang="json" ;;
            toml) lang="toml" ;;
            yaml|yml) lang="yaml" ;;
          esac
          echo "### $file (untracked, $size bytes)"
          echo ""
          echo "\`\`\`$lang"
          cat "$full_path"
          echo '```'
          echo ""
        fi
      done <<< "$(cd "$wt_path" && git status --short | grep '^??' || true)"
      echo ""
    fi
  done < <(git worktree list)

  # ─── PART 7: Handoff (optional) ───
  if [[ -n "$HANDOFF" && -f "$HANDOFF" ]]; then
    echo ""
    echo "---"
    echo "---"
    echo ""
    echo ""
    echo "# PART 7: Active Work Handoff"
    echo ""
    echo "This section describes the primary work in progress."
    echo ""
    cat "$HANDOFF"
    echo ""
  fi

  echo ""
  echo "---"
  echo ""
  echo "End of Claude context bundle. $(date -Iseconds)"

} > "$OUTPUT"

echo "Bundle written to: $OUTPUT ($(wc -c < "$OUTPUT" | tr -d ' ') bytes, $(wc -l < "$OUTPUT" | tr -d ' ') lines)"
echo ""
echo "Upload this file to Claude as project knowledge."
