#!/usr/bin/env bash
# Willowy Hollow full handoff: session chats (A) + findings/audit logs (B).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PRACTICE="${WILLOWYHOLLOW_PRACTICE:-$HOME/WordPress/willowyhollow-practice}"

echo "=== Track A: session chats ==="

CRUSH_DB="$PRACTICE/.crush/crush.db"
if [[ -f "$CRUSH_DB" ]]; then
  echo "Indexing Crush: $CRUSH_DB"
  convmem index --file "$CRUSH_DB" --supersede
else
  echo "Skip Crush (missing): $CRUSH_DB" >&2
fi

# Latest Kiro messages.jsonl under ~/.kiro/sessions (prefer practice cwd in session_meta if present)
KIRO_JSONL=""
if [[ -d "$HOME/.kiro/sessions" ]]; then
  KIRO_JSONL="$(find "$HOME/.kiro/sessions" -path '*/sess_*/messages.jsonl' -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2- || true)"
fi
if [[ -n "$KIRO_JSONL" && -f "$KIRO_JSONL" ]]; then
  echo "Indexing Kiro: $KIRO_JSONL"
  convmem index --file "$KIRO_JSONL"
else
  echo "Skip Kiro (no messages.jsonl found)" >&2
fi

# Latest Codex rollout for practice cwd (fallback: newest rollout anywhere)
CODEX_ROLLOUT=""
if [[ -d "$HOME/.codex/sessions" ]]; then
  while IFS= read -r line; do
    path="${line#* }"
    if grep -q "\"cwd\":\"$PRACTICE\"" "$path" 2>/dev/null || grep -q "\"cwd\": \"$PRACTICE\"" "$path" 2>/dev/null; then
      CODEX_ROLLOUT="$path"
      break
    fi
  done < <(find "$HOME/.codex/sessions" -name 'rollout-*.jsonl' -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn)
  if [[ -z "$CODEX_ROLLOUT" ]]; then
    CODEX_ROLLOUT="$(find "$HOME/.codex/sessions" -name 'rollout-*.jsonl' -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2- || true)"
  fi
fi
if [[ -n "$CODEX_ROLLOUT" && -f "$CODEX_ROLLOUT" ]]; then
  echo "Indexing Codex rollout: $CODEX_ROLLOUT"
  convmem index --file "$CODEX_ROLLOUT"
else
  echo "Skip Codex rollout (none found)" >&2
fi

echo ""
echo "=== Track B: log artifacts ==="
bash "$REPO/scripts/sync-willowyhollow-findings-index.sh"
bash "$REPO/scripts/sync-willowyhollow-audit-index.sh"

echo ""
echo "Handoff complete. Try: convmem \"finding 21 cron\" or convmem ask \"What did Crush find vs Codex audit?\""
