#!/usr/bin/env bash
# Copy the current complete-data snapshot from the local Restic repo to the
# external (offsite) repo using an explicit snapshot ID resolved by
# restic_snapshot.py. Verifies destination lineage (D.original == S).
#
# Non-fatal by design: this is the OFFSITE leg, decoupled from the live-write
# gate. If the drive is not mounted (or nothing is configured), exit 0 with a
# notice — it must never block or fail a session. Exit non-zero ONLY when the
# external repo is reachable but the copy or lineage verification actually errors.
#
# Config (from ~/.config/convmem/restic.env):
#   RESTIC_REPOSITORY           local source repo
#   RESTIC_EXTERNAL_REPOSITORY  external/offsite target repo
#   RESTIC_PASSWORD_FILE        password for BOTH repos (same key)
#   CONVMEM_DATA_ROOT           complete-data root for path validation
#
# Exit codes: 0 ok | 25 stale (copies nothing) | nonzero on error
set -euo pipefail

CONVMEM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${CONVMEM_RESTIC_ENV:-$HOME/.config/convmem/restic.env}"
RESOLVER="$CONVMEM_ROOT/restic_snapshot.py"
TAG="convmem-chroma"
DATA_TAG="convmem-data-v1"

REPORT_DIR="${CONVMEM_BACKUP_REPORT_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/convmem/backup-audit}"

log() { echo "restic-copy-external: $*"; }
skip() { log "$*"; exit 0; }

[[ -f "$ENV_FILE" ]] || skip "missing $ENV_FILE — nothing to copy"

# shellcheck disable=SC1090
source "$ENV_FILE"

EXTERNAL="${RESTIC_EXTERNAL_REPOSITORY:-}"
[[ -n "$EXTERNAL" ]] || skip "RESTIC_EXTERNAL_REPOSITORY unset — offsite copy disabled"

command -v restic >/dev/null 2>&1 || skip "restic not on PATH — cannot copy"

[[ -n "${RESTIC_REPOSITORY:-}" ]] || skip "RESTIC_REPOSITORY unset"
[[ -n "${RESTIC_PASSWORD_FILE:-}" ]] || skip "RESTIC_PASSWORD_FILE unset"
[[ -f "$RESTIC_PASSWORD_FILE" ]] || skip "password file missing: $RESTIC_PASSWORD_FILE"

export RESTIC_PASSWORD_FILE

DATA_ROOT="${CONVMEM_DATA_ROOT:-}"
if [[ -z "$DATA_ROOT" ]]; then
  CHROMA_DIR="${CONVMEM_CHROMA_DIR:-$HOME/.local/share/convmem/chroma}"
  DATA_ROOT="$(dirname "$CHROMA_DIR")"
  log "CONVMEM_DATA_ROOT unset; derived from CHROMA_DIR as $DATA_ROOT"
fi

# Drive mounted / repo initialized?
[[ -f "$EXTERNAL/config" ]] || skip "external repo not reachable ($EXTERNAL) — USB unplugged?"

# Resolve current local source S
SOURCE_JSON="$(python3 "$RESOLVER" resolve   --repository "$RESTIC_REPOSITORY"   --password-file "$RESTIC_PASSWORD_FILE"   --expected-data-root "$DATA_ROOT"   --require-current-local-day 2>/dev/null)" || {
  code=$?
  if [[ $code -eq 25 ]]; then
    log "local source stale (exit 25) — copying nothing"
    exit 25
  fi
  log "resolver error (exit $code) — copying nothing"
  exit $code
}

SOURCE_ID="$(echo "$SOURCE_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
log "resolved local source S=$SOURCE_ID"

# Copy explicit S to external repository
log "copying S=$SOURCE_ID: $RESTIC_REPOSITORY -> $EXTERNAL"
restic -r "$EXTERNAL" copy "$SOURCE_ID"   --from-repo "$RESTIC_REPOSITORY"   --from-password-file "$RESTIC_PASSWORD_FILE" || {
  log "restic copy failed"
  exit 28
}

# Resolve and verify destination D
DEST_JSON="$(python3 "$RESOLVER" resolve-copy-destination   --repository "$EXTERNAL"   --password-file "$RESTIC_PASSWORD_FILE"   --source-json "$SOURCE_JSON" 2>/dev/null)" || {
  code=$?
  log "destination lineage verification failed (exit $code)"
  exit $code
}

DEST_ID="$(echo "$DEST_JSON" | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')"
DEST_ORIGINAL="$(echo "$DEST_JSON" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("original",""))')"

# Write report
mkdir -p "$REPORT_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT_JSON="$REPORT_DIR/copy-$STAMP.json"
REPORT_MD="$REPORT_DIR/copy-$STAMP.md"

python3 -c '
import json, sys, os
from datetime import datetime, timezone
now = datetime.now(timezone.utc).isoformat()
source = json.loads(sys.argv[1])
dest = json.loads(sys.argv[2])
report = {
    "meta": {
        "status": "pass",
        "kind": "restic_offsite_copy",
        "started_at": now,
        "finished_at": now,
        "source_repository": source["repository"],
        "destination_repository": dest["repository"],
        "source_id": source["id"],
        "destination_id": dest["id"],
        "destination_original": dest.get("original"),
    },
    "steps": [
        {"name": "resolve_source", "status": "PASS", "detail": source["id"]},
        {"name": "restic_copy", "status": "PASS"},
        {"name": "verify_lineage", "status": "PASS", "detail": f"D.original={dest.get("original","")[:12]} == S"},
    ],
}
print(json.dumps(report, indent=2))
' "$SOURCE_JSON" "$DEST_JSON" > "$REPORT_JSON"

# Markdown report
cat > "$REPORT_MD" <<MDEOF
# Restic offsite copy report

- status: **pass**
- source: \`$SOURCE_ID\`
- destination: \`$DEST_ID\`
- lineage: D.original = \`$DEST_ORIGINAL\` == S
- copy: \`$RESTIC_REPOSITORY\` → \`$EXTERNAL\`

MDEOF

log "OK — offsite copy complete (S=$SOURCE_ID D=$DEST_ID)"
log "report=$REPORT_JSON"
exit 0
