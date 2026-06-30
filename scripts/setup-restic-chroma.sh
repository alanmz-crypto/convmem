#!/usr/bin/env bash
# One-time Restic setup for convmem chroma backups.
# Creates restic.env + password file if missing, inits repo, runs first snapshot.
set -euo pipefail

CONVMEM_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_DST="$HOME/.config/convmem/restic.env"
PASS_FILE="$HOME/.config/convmem/restic.password"
REPO_DIR="$HOME/.local/share/convmem-restic"

mkdir -p "$HOME/.config/convmem" "$REPO_DIR"

if [[ ! -f "$ENV_DST" ]]; then
  sed \
    -e "s|^RESTIC_REPOSITORY=.*|RESTIC_REPOSITORY=$REPO_DIR|" \
    -e "s|^RESTIC_PASSWORD_FILE=.*|RESTIC_PASSWORD_FILE=$PASS_FILE|" \
    "$CONVMEM_ROOT/config/restic.env.example" > "$ENV_DST"
  chmod 600 "$ENV_DST"
  echo "Created $ENV_DST"
fi

if [[ ! -f "$PASS_FILE" ]]; then
  openssl rand -base64 32 > "$PASS_FILE"
  chmod 600 "$PASS_FILE"
  echo "Created $PASS_FILE (keep this secret; back it up offline)"
fi

export CONVMEM_RESTIC_ENV="$ENV_DST"
# shellcheck disable=SC1090
source "$ENV_DST"
export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE

if ! command -v restic >/dev/null 2>&1; then
  echo "ERROR: restic not on PATH. Install: pacman -S restic" >&2
  echo "  or: conda install -n convmem -c conda-forge restic" >&2
  echo "  then: ln -sf ~/miniforge3/envs/convmem/bin/restic ~/.local/bin/restic" >&2
  exit 1
fi

if ! restic snapshots >/dev/null 2>&1; then
  echo "Initializing restic repo at $RESTIC_REPOSITORY"
  restic init
fi

"$CONVMEM_ROOT/scripts/restic-ensure-chroma-snapshot.sh"
echo "setup-restic-chroma: OK"
