#!/usr/bin/env bash
# Fail-closed Restic gate for ConvMem production-data snapshots.
#
# Stale threshold (pinned, matches docs/ROADMAP.md):
#   Latest snapshot tagged convmem-data-v1 must cover the configured data root and
#   be from the **current local calendar day** (time >= local midnight today).
#   Not "last commit", not "last approved write".
#
# Flags:
#   --check-only       Toolchain + repo reachable; does not backup; ignores staleness.
#   --require-current  Exit 1 if no snapshot covering today (for doctor / audit).
#   --dry-run          Report actions only; no backup (still validates toolchain).
#
# Exit codes: 0 ok | 1 fail-closed (blocks live writes)
set -euo pipefail

ENV_FILE="${CONVMEM_RESTIC_ENV:-$HOME/.config/convmem/restic.env}"
TAG="convmem-data-v1"
LEGACY_TAG="convmem-chroma"

CHECK_ONLY=false
REQUIRE_CURRENT=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check-only) CHECK_ONLY=true; shift ;;
    --require-current) REQUIRE_CURRENT=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *)
      echo "restic-gate: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

fail() {
  echo "restic-gate: ERROR: $*" >&2
  exit 1
}

if ! command -v restic >/dev/null 2>&1; then
  fail "restic not on PATH (install: pacman -S restic, or conda-forge in convmem env)"
fi

[[ -f "$ENV_FILE" ]] || fail "missing $ENV_FILE — copy config/restic.env.example and run scripts/setup-restic-chroma.sh"

# shellcheck disable=SC1090
source "$ENV_FILE"

[[ -n "${RESTIC_REPOSITORY:-}" ]] || fail "RESTIC_REPOSITORY unset in $ENV_FILE"
[[ -n "${RESTIC_PASSWORD_FILE:-}" ]] || fail "RESTIC_PASSWORD_FILE unset in $ENV_FILE"
[[ -f "$RESTIC_PASSWORD_FILE" ]] || fail "RESTIC_PASSWORD_FILE not found: $RESTIC_PASSWORD_FILE"

CHROMA_DIR="${CONVMEM_CHROMA_DIR:-$HOME/.local/share/convmem/chroma}"
DATA_ROOT="${CONVMEM_DATA_ROOT:-$(dirname "$CHROMA_DIR")}"
[[ -d "$DATA_ROOT" ]] || fail "data root missing: $DATA_ROOT"
[[ -d "$CHROMA_DIR" ]] || fail "chroma dir missing: $CHROMA_DIR"

DATA_ROOT="$(readlink -f "$DATA_ROOT")"
CHROMA_DIR="$(readlink -f "$CHROMA_DIR")"
[[ "$CHROMA_DIR" != "$DATA_ROOT" ]] \
  || fail "data root cannot be the Chroma directory; configure its parent"
case "$CHROMA_DIR/" in
  "$DATA_ROOT/"*) ;;
  *) fail "chroma dir must be inside data root: chroma=$CHROMA_DIR data_root=$DATA_ROOT" ;;
esac

PASSWORD_FILE_ABS="$(readlink -f "$RESTIC_PASSWORD_FILE")"
case "$PASSWORD_FILE_ABS" in
  "$DATA_ROOT"|"$DATA_ROOT"/*)
    fail "RESTIC_PASSWORD_FILE must be outside the backed-up data root"
    ;;
esac

case "$RESTIC_REPOSITORY" in
  /*)
    REPOSITORY_ABS="$(readlink -m "$RESTIC_REPOSITORY")"
    case "$REPOSITORY_ABS" in
      "$DATA_ROOT"|"$DATA_ROOT"/*)
        fail "RESTIC_REPOSITORY must be outside the backed-up data root"
        ;;
    esac
    ;;
  *:*) ;; # Remote/backend repository URL.
  *) fail "local RESTIC_REPOSITORY must be an absolute path" ;;
esac

CACHE_ROOT="${RESTIC_CACHE_DIR:-${CONVMEM_RESTIC_CACHE_DIR:-${TMPDIR:-/tmp}/convmem-restic-cache}}"
mkdir -p "$CACHE_ROOT"
export RESTIC_CACHE_DIR="$CACHE_ROOT"

export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE

snapshot_freshness() {
  # Prints: current | stale | none | wrong-path | error
  CONVMEM_RESTIC_TAG="$TAG" python3 - "$DATA_ROOT" <<'PY'
import json
import os
import subprocess
import sys
from datetime import datetime

tag = os.environ["CONVMEM_RESTIC_TAG"]
data_root = os.path.realpath(sys.argv[1])
proc = subprocess.run(
    ["restic", "snapshots", "--tag", tag, "--json"],
    capture_output=True,
    text=True,
    env=os.environ,
)
if proc.returncode != 0:
    print("error", proc.stderr.strip() or proc.stdout.strip(), file=sys.stderr)
    sys.exit(4)
snaps = json.loads(proc.stdout or "[]")
if not snaps:
    print("none")
    sys.exit(0)
covered = [
    snap
    for snap in snaps
    if any(os.path.realpath(path) == data_root for path in snap.get("paths") or [])
]
if not covered:
    print("wrong-path")
    sys.exit(0)
latest = max(covered, key=lambda s: s["time"])
ts = datetime.fromisoformat(latest["time"].replace("Z", "+00:00"))
local_day = ts.astimezone().date()
today = datetime.now().astimezone().date()
if local_day >= today:
    print("current")
else:
    print("stale")
PY
}

ensure_repo() {
  if restic cat config >/dev/null 2>&1; then
    return 0
  fi
  if $DRY_RUN; then
    echo "restic-gate: dry-run — would run restic init"
    return 0
  fi
  echo "restic-gate: initializing repository $RESTIC_REPOSITORY"
  restic init || fail "restic init failed"
}

ensure_repo

freshness="$(snapshot_freshness)" || {
  code=$?
  if [[ $code -eq 4 ]]; then
    fail "restic snapshots command failed"
  fi
  fail "snapshot freshness check failed"
}

if $CHECK_ONLY; then
  echo "restic-gate: toolchain OK (freshness=$freshness, data_root=$DATA_ROOT, repo=$RESTIC_REPOSITORY)"
  exit 0
fi

if [[ "$freshness" == "current" ]]; then
  echo "restic-gate: current — data-root snapshot covers today (tag=$TAG)"
  exit 0
fi

if $REQUIRE_CURRENT; then
  fail "snapshot not current (freshness=$freshness; threshold=local calendar day)"
fi

if $DRY_RUN; then
  echo "restic-gate: dry-run — would backup $DATA_ROOT (freshness=$freshness)"
  exit 0
fi

day_tag="convmem-$(date +%Y-%m-%d)"
echo "restic-gate: snapshot-if-stale — backing up $DATA_ROOT (was $freshness)"
restic backup "$DATA_ROOT" \
  --exclude "$DATA_ROOT/worktrees" \
  --exclude "$DATA_ROOT/restore-drill/runs" \
  --tag "$TAG" \
  --tag "$LEGACY_TAG" \
  --tag "$day_tag" || fail "restic backup failed"

freshness="$(snapshot_freshness)" || fail "post-backup freshness check failed"
[[ "$freshness" == "current" ]] || fail "snapshot still not current after backup"

echo "restic-gate: snapshot OK (tag=$TAG compatibility_tag=$LEGACY_TAG tag=$day_tag)"
exit 0
