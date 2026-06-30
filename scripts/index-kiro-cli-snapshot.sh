#!/usr/bin/env bash
# Snapshot kiro-cli legacy sqlite and index the copy (not the live DB).
set -euo pipefail

LIVE_DB="${KIRO_CLI_DB:-$HOME/.local/share/kiro-cli/data.sqlite3}"
IMPORTS_DIR="${CONVMEM_IMPORTS:-$HOME/.local/share/convmem/imports}"
SNAPSHOT="$IMPORTS_DIR/kiro-cli-snapshot.sqlite3"

usage() {
  cat <<EOF
Usage: $0

Backs up the live kiro-cli DB to a static copy, then indexes the copy.
The live DB stays on the watch deny list (OOM risk if watch re-indexes it).

  LIVE_DB:    $LIVE_DB
  SNAPSHOT:   $SNAPSHOT

Weekly timer: systemd/convmem-kiro-cli-snapshot.timer.example
Session jsonl (current chats): docs/KIRO-SESSION-ADAPTER.md
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -f "$LIVE_DB" ]]; then
  echo "kiro-cli DB not found: $LIVE_DB" >&2
  exit 1
fi

mkdir -p "$IMPORTS_DIR"
echo "Backing up $LIVE_DB → $SNAPSHOT"
sqlite3 "$LIVE_DB" ".backup '$SNAPSHOT'"

convmem doctor >/dev/null
echo "Indexing snapshot…"
convmem index --file "$SNAPSHOT"
echo "Done. Verify: convmem stats  (kiro row should reflect snapshot units)"
