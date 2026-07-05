#!/usr/bin/env bash
# Install or refresh user systemd timer for weekly cross-project digest (read-only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/.config/systemd/user"
mkdir -p "$DEST"
cp "$ROOT/systemd/convmem-cross-project-digest.service.example" "$DEST/convmem-cross-project-digest.service"
cp "$ROOT/systemd/convmem-cross-project-digest.timer.example" "$DEST/convmem-cross-project-digest.timer"
systemctl --user daemon-reload
systemctl --user enable convmem-cross-project-digest.timer
systemctl --user start convmem-cross-project-digest.timer
systemctl --user list-timers convmem-cross-project-digest.timer --no-pager
echo "Installed read-only weekly digest timer (Mon 09:00 local + jitter)."
