#!/usr/bin/env bash
# Create/refresh an OFFLINE copy of the Restic password so a Tier-2 config wipe
# (~/.config/convmem recreated) does not orphan BOTH restic repos.
#
# The password is the single secret that unlocks the local AND external repos.
# Losing ~/.config/convmem/restic.password with no other copy = permanent data
# loss. This copies it to a second, independent location and verifies the copy.
#
# Usage:
#   scripts/backup-restic-password.sh [DEST]
#   DEST defaults to $RESTIC_PASSWORD_BACKUP_FILE from restic.env.
#
# Safety: refuses to write the key INTO any restic repo dir or the chroma dir
# (never co-locate the key with the encrypted data it unlocks / that it snapshots).
set -euo pipefail

ENV_FILE="${CONVMEM_RESTIC_ENV:-$HOME/.config/convmem/restic.env}"
[[ -f "$ENV_FILE" ]] || { echo "backup-restic-password: missing $ENV_FILE" >&2; exit 1; }

# shellcheck disable=SC1090
source "$ENV_FILE"

SRC="${RESTIC_PASSWORD_FILE:-}"
DEST="${1:-${RESTIC_PASSWORD_BACKUP_FILE:-}}"

[[ -n "$SRC" ]] || { echo "backup-restic-password: RESTIC_PASSWORD_FILE unset" >&2; exit 1; }
[[ -f "$SRC" ]] || { echo "backup-restic-password: source not found: $SRC" >&2; exit 1; }
if [[ -z "$DEST" ]]; then
  echo "backup-restic-password: no destination. Pass a path or set RESTIC_PASSWORD_BACKUP_FILE in $ENV_FILE" >&2
  exit 1
fi

DEST="${DEST/#\~/$HOME}"
SRC_ABS="$(readlink -f "$SRC")"
[[ "$(readlink -f "$DEST" 2>/dev/null || echo "$DEST")" != "$SRC_ABS" ]] \
  || { echo "backup-restic-password: destination equals the primary password file" >&2; exit 1; }

# Never place the key inside a repo dir or the chroma dir.
for guard in "${RESTIC_REPOSITORY:-}" "${RESTIC_EXTERNAL_REPOSITORY:-}" "${CONVMEM_CHROMA_DIR:-}"; do
  [[ -n "$guard" ]] || continue
  guard_abs="$(readlink -f "$guard" 2>/dev/null || echo "$guard")"
  case "$(readlink -f "$(dirname "$DEST")" 2>/dev/null || dirname "$DEST")" in
    "$guard_abs"|"$guard_abs"/*)
      echo "backup-restic-password: refusing to store the key inside '$guard' (co-location defeats encryption)" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$DEST")"
umask 077
cp "$SRC" "$DEST"
chmod 600 "$DEST"

if [[ "$(sha256sum < "$SRC" | cut -d' ' -f1)" != "$(sha256sum < "$DEST" | cut -d' ' -f1)" ]]; then
  echo "backup-restic-password: ERROR — copy does not match source" >&2
  exit 1
fi

echo "backup-restic-password: OK — offline copy verified at $DEST"
echo "  (add RESTIC_PASSWORD_BACKUP_FILE=$DEST to $ENV_FILE if not already set)"
