#!/usr/bin/env bash
# Copy the latest convmem-chroma snapshot from the local Restic repo to the
# external (offsite) repo on the removable USB drive.
#
# Non-fatal by design: this is the OFFSITE leg, decoupled from the live-write
# gate. If the drive is not mounted (or nothing is configured), exit 0 with a
# notice — it must never block or fail a session. Exit non-zero ONLY when the
# external repo is reachable but `restic copy` actually errors.
#
# Config (from ~/.config/convmem/restic.env):
#   RESTIC_REPOSITORY           local source repo (enforced by the gate)
#   RESTIC_EXTERNAL_REPOSITORY  external/offsite target repo (this script's dest)
#   RESTIC_PASSWORD_FILE        password for BOTH repos (same key)
#
# Driven every 2h by systemd/convmem-restic-external.timer.example.
set -euo pipefail

ENV_FILE="${CONVMEM_RESTIC_ENV:-$HOME/.config/convmem/restic.env}"
TAG="convmem-chroma"

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

# Drive mounted / repo initialized? A valid restic repo has a top-level config.
[[ -f "$EXTERNAL/config" ]] || skip "external repo not reachable ($EXTERNAL) — USB unplugged?"

log "copying latest $TAG: $RESTIC_REPOSITORY -> $EXTERNAL"
restic -r "$EXTERNAL" copy latest \
  --from-repo "$RESTIC_REPOSITORY" \
  --from-password-file "$RESTIC_PASSWORD_FILE" \
  --tag "$TAG"

log "OK — offsite copy current"
