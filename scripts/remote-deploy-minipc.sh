#!/usr/bin/env bash
# Full miniPC deploy from dev machine.
#
#   ./scripts/remote-deploy-minipc.sh
#   SSHPASS='your-password' ./scripts/remote-deploy-minipc.sh   # if keys not set up
#
# Optional: MINIPC_HOST=10.0.0.18 MINIPC_USER=lab

set -euo pipefail

HOST="${MINIPC_HOST:-10.0.0.18}"
USER="${MINIPC_USER:-lab}"
REMOTE="${USER}@${HOST}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ASKPASS="$ROOT/scripts/ssh-askpass.sh"
chmod +x "$ASKPASS"

if ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new "$REMOTE" true 2>/dev/null; then
  echo "[+] SSH key auth to $REMOTE"
  SSH=(ssh -o StrictHostKeyChecking=accept-new)
  RSYNC_SSH="ssh -o StrictHostKeyChecking=accept-new"
  run_ssh() { "${SSH[@]}" "$REMOTE" "$@"; }
else
  SSHPASS="${SSHPASS:?Set SSHPASS to lab@10.0.0.18 password (or run ssh-copy-id)}"
  export SSHPASS DISPLAY=
  SSH=(ssh -o StrictHostKeyChecking=accept-new -o PreferredAuthentications=password -o PubkeyAuthentication=no)
  RSYNC_SSH="ssh -o StrictHostKeyChecking=accept-new -o PreferredAuthentications=password -o PubkeyAuthentication=no"
  run_ssh() {
    SSH_ASKPASS="$ASKPASS" SSH_ASKPASS_REQUIRE=force "${SSH[@]}" "$REMOTE" "$@"
  }
fi

echo "[+] Probe $REMOTE"
run_ssh 'hostname && whoami'
run_ssh 'mkdir -p ~/Projects ~/.config/convmem ~/.local/share/convmem'

echo "[+] Sync convmem repo"
rsync -av --delete \
  --exclude .venv --exclude __pycache__ --exclude .git \
  -e "$RSYNC_SSH" "$ROOT/" "$REMOTE:Projects/convmem/"

echo "[+] Sync chroma corpus (~/.local/share/convmem)"
rsync -av \
  -e "$RSYNC_SSH" "$HOME/.local/share/convmem/" "$REMOTE:.local/share/convmem/"

echo "[+] Sync config"
run_ssh 'mkdir -p ~/.config/convmem'
if [[ -f "$HOME/.config/convmem/env.systemd" ]]; then
  rsync -av -e "$RSYNC_SSH" \
    "$HOME/.config/convmem/env.systemd" "$REMOTE:.config/convmem/env.systemd"
fi
if [[ -f "$HOME/.config/convmem/config.toml" ]]; then
  rsync -av -e "$RSYNC_SSH" \
    "$HOME/.config/convmem/config.toml" "$REMOTE:.config/convmem/config.toml"
  run_ssh "sed -i 's|/home/lauer|/home/lab|g' ~/.config/convmem/config.toml"
  run_ssh "sed -i 's|ollama_host.*=.*|ollama_host = \"http://localhost:11434\"|' ~/.config/convmem/config.toml"
else
  run_ssh 'cp ~/Projects/convmem/config.example.toml ~/.config/convmem/config.toml'
fi
run_ssh 'chmod 600 ~/.config/convmem/env.systemd 2>/dev/null || true'

echo "[+] Install miniforge + convmem env (if missing)"
run_ssh 'bash -s' <<'REMOTE_BOOT'
set -euo pipefail
if [ ! -x "$HOME/miniforge3/bin/mamba" ]; then
  curl -fsSL https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -o /tmp/mf.sh
  bash /tmp/mf.sh -b -p "$HOME/miniforge3"
fi
source "$HOME/miniforge3/bin/activate"
if ! mamba env list | awk '{print $1}' | grep -qx convmem; then
  mamba create -n convmem python=3.12 -y
fi
mamba run -n convmem pip install -r "$HOME/Projects/convmem/requirements.txt"
REMOTE_BOOT

echo "[+] Run deploy-minipc.sh on remote"
run_ssh 'chmod +x ~/Projects/convmem/scripts/deploy-minipc.sh && CONVMEM_PYTHON=$HOME/miniforge3/envs/convmem/bin/python ~/Projects/convmem/scripts/deploy-minipc.sh'

echo ""
echo "[✓] miniPC deploy complete."
echo "    On dev (archlinux), stop duplicate writers:"
echo "    systemctl --user disable --now convmem-watch convmem-refine convmem-monitor.timer"
