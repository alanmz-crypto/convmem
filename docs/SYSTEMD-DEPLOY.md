# Systemd deploy — always-on convmem

Install **user** systemd units on the machine where you already run Cursor, Kiro, and Continue.  
Watch, refine, and monitor are background daemons on **this workstation** — not a separate always-on host.

Code milestones through **F2b** are signed off; this doc is install + systemd only.

---

## Prerequisites

```bash
# Conda env + deps (see README)
mamba create -n convmem python=3.12
mamba activate convmem
pip install -r ~/Projects/convmem/requirements.txt

# Config + secrets
mkdir -p ~/.config/convmem ~/.local/share/convmem
cp ~/Projects/convmem/config.example.toml ~/.config/convmem/config.toml
# Edit paths if chat sources live elsewhere

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

**Ollama** local (`nomic-embed-text` at minimum). Set `ollama_host = "http://localhost:11434"` in `config.toml`.

**Process locks:** `watch.lock` and `refine.lock` ensure one watch and one refine daemon at a time. Do not rsync or NFS-mount `~/.local/share/convmem/chroma/` to another machine while services run (`dec_convmem_single_writer_chroma`).

Sanity:

```bash
source ~/.config/convmem/env.local
convmem stats
python -m unittest discover -s ~/Projects/convmem/tests
```

---

## Quick install

```bash
./scripts/deploy-always-on.sh
```

This copies unit files, enables linger, and starts watch + refine + monitor.timer.

---

## Manual unit setup

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

## Restic complete-data backup timers (examples only)

Two **independent** user timer units manage complete-data-v2 Restic snapshots
and offsite copies. Example files live in `systemd/`; copy to
`~/.config/systemd/user/` only after Ryan grants the post-merge timer live step.
Merging this code does **not** install, enable, start, or reload any unit.

### Local daily snapshot (`convmem-restic-local`)

Creates or verifies a current-day `convmem-data-v2` snapshot of
`CONVMEM_DATA_ROOT` (profile `complete-data-v2`).

```bash
cp systemd/convmem-restic-local.{service,timer}.example ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now convmem-restic-local.timer
systemctl --user list-timers convmem-restic-local.timer
```

**Schedule:** daily at **00:15** local, up to 5 min jitter (`RandomizedDelaySec=300`).
`Persistent=true` catches up one missed run after host resume.

### External offsite copy (`convmem-restic-external`)

Copies the current complete-data-v2 snapshot to the external USB repository
using an **explicit** snapshot ID with lineage verification (`D.original == S`).
Never uses `--latest`.

```bash
cp systemd/convmem-restic-external.{service,timer}.example ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now convmem-restic-external.timer
```

**Schedule:** every 2 hours starting at **01:00** (`*-*-* 01/2:00:00` → 01:00,
03:00, 05:00, …). `Persistent=true` as above.

The external **service** declares `After=convmem-restic-local.service` for
queuing convenience only. That `After=` is **non-authoritative**: it does not
pull in the local service, does not prove local success, and is never a
protection claim. A stale local source exits `25`, copies nothing, and is
visible via `systemctl --user status` / journal.

### Monitoring (after live grant only)

```bash
systemctl --user list-timers convmem-restic-*
systemctl --user status convmem-restic-local.service
systemctl --user status convmem-restic-external.service
journalctl --user -u convmem-restic-local -f
journalctl --user -u convmem-restic-external -f
```

### Pre-requisites

- `restic >= 0.19.0` on PATH
- `~/.config/convmem/restic.env` with `CONVMEM_BACKUP_PROFILE=complete-data-v2`,
  mandatory `CONVMEM_DATA_ROOT`, `RESTIC_REPOSITORY`,
  `RESTIC_EXTERNAL_REPOSITORY`, `RESTIC_PASSWORD_FILE`
- Profile remains `legacy-chroma` / unset until Ryan grants profile activation;
  doctor must emit `WARN_LEGACY_ONLY` until all four post-merge grants finish

Never rely on timer ordering for backup safety. Authoritative protection comes
from path-bound snapshot resolution and explicit IDs — see
`docs/RECOVER.md` and the Architecture/VERIFY companions for this arc.


## Linger (services survive logout/reboot)

```bash
loginctl enable-linger "$USER"
loginctl show-user "$USER" -p Linger   # Linger=yes
```

`deploy-always-on.sh` runs this automatically.

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

## After services are running

1. Confirm one monitor cycle in `journalctl` (4 verifications + TLS obs/ver as applicable).
2. `convmem doctor` should show watch/refine/monitor active.

---

*2026-06 — post F2b sign-off. Single-workstation model.*

**Archived:** abandoned miniPC two-host deploy — [`docs/archive/minipc-deploy/`](archive/minipc-deploy/README.md).
