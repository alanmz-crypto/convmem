#!/usr/bin/env bash
# ARCHIVED — see docs/archive/minipc-deploy/README.md. Do not run.
# Install convmem always-on stack (watch + refine + monitor timer).
# Run on the canonical index host (miniPC). See docs/MINIPC-DEPLOY.md.
#
# Usage:
#   ./scripts/deploy-minipc.sh
#   ./scripts/deploy-minipc.sh --sync-chroma user@dev-host   # rsync corpus from dev

set -euo pipefail

SYNC_FROM=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sync-chroma)
      SYNC_FROM="${2:?--sync-chroma requires user@host}"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

CONVMEM="${CONVMEM_ROOT:-$HOME/Projects/convmem}"
PYTHON="${CONVMEM_PYTHON:-}"
if [[ -z "$PYTHON" ]]; then
  for candidate in \
    "$HOME/miniforge3/envs/convmem/bin/python" \
    "$HOME/miniforge3/envs/convmem/bin/python3" \
    "$HOME/mambaforge/envs/convmem/bin/python"; do
    if [[ -x "$candidate" ]]; then
      PYTHON="$candidate"
      break
    fi
  done
fi
if [[ -z "$PYTHON" || ! -x "$PYTHON" ]]; then
  echo "[!] convmem python not found. Set CONVMEM_PYTHON or create mamba env first." >&2
  exit 1
fi

if [[ ! -f "$CONVMEM/convmem.py" ]]; then
  echo "[!] Repo not found at $CONVMEM" >&2
  exit 1
fi

echo "[+] Using python: $PYTHON"
echo "[+] Repo: $CONVMEM"

mkdir -p "$HOME/.config/convmem" "$HOME/.local/share/convmem" "$HOME/.config/systemd/user"

if [[ ! -f "$HOME/.config/convmem/config.toml" ]]; then
  cp "$CONVMEM/config.example.toml" "$HOME/.config/convmem/config.toml"
  echo "[+] Wrote ~/.config/convmem/config.toml from example"
fi

if [[ ! -f "$HOME/.config/convmem/env.systemd" ]]; then
  if [[ -f "$HOME/.config/convmem/env.local" ]]; then
    grep -E '^export DEEPSEEK_API_KEY=' "$HOME/.config/convmem/env.local" \
      | sed 's/^export //' > "$HOME/.config/convmem/env.systemd" || true
  fi
  if [[ ! -s "$HOME/.config/convmem/env.systemd" ]]; then
    echo "[!] Create ~/.config/convmem/env.systemd with DEEPSEEK_API_KEY=..." >&2
    cp "$CONVMEM/config/env.systemd.example" "$HOME/.config/convmem/env.systemd"
    echo "    Edit env.systemd then re-run." >&2
    exit 1
  fi
  chmod 600 "$HOME/.config/convmem/env.systemd"
  echo "[+] Created env.systemd from env.local"
fi

if [[ -n "$SYNC_FROM" ]]; then
  echo "[+] Rsync chroma corpus from $SYNC_FROM (single-writer migration)"
  rsync -av --progress "${SYNC_FROM}:.local/share/convmem/" "$HOME/.local/share/convmem/"
fi

echo "[+] Sanity check"
"$PYTHON" "$CONVMEM/convmem.py" stats 2>&1 | head -20 || true

UNIT_DIR="$HOME/.config/systemd/user"
for src in "$CONVMEM"/systemd/convmem-*.example; do
  base=$(basename "$src" .example)
  dst="$UNIT_DIR/$base"
  sed "s|%h/miniforge3/envs/convmem/bin/python|$PYTHON|g" "$src" \
    | sed "s|%h|$HOME|g" > "$dst"
  echo "[+] Wrote $dst"
done

loginctl enable-linger "$USER" 2>/dev/null || true
systemctl --user daemon-reload

systemctl --user enable --now convmem-watch.service
systemctl --user enable --now convmem-refine.service
systemctl --user enable --now convmem-monitor.timer
systemctl --user start convmem-monitor.service

echo ""
echo "[✓] Deploy complete. Verify:"
echo "    systemctl --user status convmem-watch convmem-refine"
echo "    systemctl --user list-timers convmem-monitor.timer"
echo "    journalctl --user -u convmem-monitor -n 20"
