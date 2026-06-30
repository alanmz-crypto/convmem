> **ARCHIVED** — abandoned miniPC deploy plan. See [`README.md`](README.md). Current: [`docs/SYSTEMD-DEPLOY.md`](../../SYSTEMD-DEPLOY.md).

# miniPC deploy — always-on convmem

Operational guide for the canonical index host (recommended: miniPC).  
Code milestones through **F2b** are signed off; this is install + systemd only.

---

## Prerequisites

On the miniPC (same layout as dev machine):

```bash
# Conda env + deps (see README)
mamba create -n convmem python=3.12
mamba activate convmem
pip install -r ~/Projects/convmem/requirements.txt

# Config + secrets
mkdir -p ~/.config/convmem ~/.local/share/convmem
cp ~/Projects/convmem/config.example.toml ~/.config/convmem/config.toml
# Edit paths if chat sources live elsewhere on this host

# ~/.config/convmem/env.local
export DEEPSEEK_API_KEY=...
convmem() {
  ~/miniforge3/envs/convmem/bin/python ~/Projects/convmem/convmem.py "$@"
}
```

**systemd:** `EnvironmentFile=` does not accept `export` or shell functions. Maintain a parallel file for units:

```bash
# ~/.config/convmem/env.systemd  (KEY=value lines only)
DEEPSEEK_API_KEY=...
```

Point units at `EnvironmentFile=%h/.config/convmem/env.systemd` or strip `export` from a dedicated file.  
Templates: `config/env.local.shell.example`, `config/env.systemd.example`.

**Ollama** on the miniPC (`nomic-embed-text` at minimum). No sudo required if you use Docker (user `lab` is in the `docker` group):

```bash
docker run -d --restart unless-stopped \
  -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec ollama ollama pull nomic-embed-text
```

Set `ollama_host = "http://localhost:11434"` in `config.toml`.  
**Single writer:** only one host should own `~/.local/share/convmem/chroma/`.

Sanity:

```bash
source ~/.config/convmem/env.local
convmem stats
python -m unittest discover -s ~/Projects/convmem/tests
```

---

## User systemd units

Copy examples and adjust `ExecStart` python path if not miniforge3:

```bash
CONVMEM=~/Projects/convmem
UNIT_DIR=~/.config/systemd/user
mkdir -p "$UNIT_DIR"

cp "$CONVMEM/systemd/convmem-watch.service.example"     "$UNIT_DIR/convmem-watch.service"
cp "$CONVMEM/systemd/convmem-refine.service.example"     "$UNIT_DIR/convmem-refine.service"
cp "$CONVMEM/systemd/convmem-monitor.service.example"   "$UNIT_DIR/convmem-monitor.service"
cp "$CONVMEM/systemd/convmem-monitor.timer.example"       "$UNIT_DIR/convmem-monitor.timer"

systemctl --user daemon-reload
```

### Enable (order matters)

```bash
systemctl --user enable --now convmem-watch.service
systemctl --user enable --now convmem-refine.service
systemctl --user enable --now convmem-monitor.timer

# Optional: run monitor once immediately
systemctl --user start convmem-monitor.service
```

### Verify

```bash
systemctl --user status convmem-watch convmem-refine
systemctl --user list-timers convmem-monitor.timer
journalctl --user -u convmem-watch -n 20
journalctl --user -u convmem-refine -n 20
journalctl --user -u convmem-monitor -n 20
```

| Unit | Role |
|------|------|
| `convmem-watch` | inotify → `index --file` on new Cursor JSONL |
| `convmem-refine` | F1 daemon (dedupe, semantic queue, audits) |
| `convmem-monitor.timer` | Hourly F2b HTTP probes → staging2 |

Backfill is **complete** (0 untagged). Default `config.example.toml` runs `confidence_audit` in the refine daemon (no LLM cost); re-add `backfill_domain` to `[refine].jobs` only if a large untagged intake returns.

---

## Manual / cron alternative

Without systemd timer:

```bash
# Hourly cron
0 * * * * source ~/.config/convmem/env.local && ~/Projects/convmem/scripts/monitor-staging2.sh >> ~/.local/share/convmem/logs/monitor.log 2>&1
```

Dry-run:

```bash
./scripts/monitor-staging2.sh --dry-run
```

---

## inotify limits

Large `~/.cursor/projects` trees may need higher watch limits — see comments in `systemd/convmem-watch.service.example`.

---

## Dev machine → miniPC SSH

Agents and scripts use key-based auth (no password prompt):

```bash
ssh-copy-id lab@10.0.0.18
ssh -o BatchMode=yes lab@10.0.0.18 'hostname'
```

Remote deploy from dev (key auth; `SSHPASS` only if keys are missing):

```bash
./scripts/remote-deploy-minipc.sh
```

**Linger** (services survive logout/reboot):

```bash
# on miniPC
loginctl enable-linger lab
loginctl show-user lab -p Linger   # Linger=yes
```

---

## After miniPC is running

1. Confirm one monitor cycle in `journalctl` (4 verifications + TLS obs/ver as applicable).
2. **F2c** (Crush adapter) — Builder gates on `sqlite3 … ".schema"` + `SELECT * FROM messages LIMIT 2` before code.

---

*2026-06 — post F2b sign-off.*
