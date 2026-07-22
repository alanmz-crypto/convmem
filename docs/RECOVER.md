# Recover convmem + MCP after data loss

Ryan backs up **`~/Projects/convmem`** (source, docs, examples). This guide assumes that
backup exists. It separates what the **hook hard-protects**, what is **easy to recreate
from the repo**, and what needs a **separate data backup**.

---

## Three tiers

| Tier | Location | If wiped | Agent hook |
|------|----------|----------|------------|
| **1 — Corpus** | `~/.local/share/convmem/` | Restore from your **data backup** or full reindex (slow) | **Blocks** shell delete/move/truncate |
| **2 — Runtime config** | `~/.config/convmem/` | Copy examples below; re-enter API key | **Blocks** shell delete/move/truncate |
| **3 — Wiring + source** | `~/Projects/convmem`, `~/.cursor/mcp.json`, `~/.kiro/settings/mcp.json`, `~/.kiro/settings/permissions.yaml`, `~/.config/crush/crush.json`, `~/.copilot/mcp-config.json`, `~/.copilot/agents/`, Continue YAML | Restore project backup or git; copy MCP/permissions examples | **Not blocked** — edits encouraged |

**Not in the Git repo:** Tier 1 (`chroma/`, `processed.json`, `knowledge_units.jsonl`,
`decisions-approved.jsonl`, `attempts.jsonl` (optional), etc.). Include `~/.local/share/convmem/` in backups if you want
fast recovery without reindexing.

---

## Restic snapshot gate (live Chroma writes)

**Policy:** fail-closed. If Restic cannot verify or create a current snapshot, **do not**
run live `record --approve-last` or `add --upsert` on the production corpus.

**Stale threshold (pinned):** latest snapshot tagged `convmem-chroma` must be from the
**current local calendar day** (snapshot time ≥ local midnight today).

### One-time setup

```bash
# Install restic (pick one)
sudo pacman -S restic
# or: conda install -n convmem -c conda-forge restic && ln -sf ~/miniforge3/envs/convmem/bin/restic ~/.local/bin/restic

bash ~/Projects/convmem/scripts/setup-restic-chroma.sh
```

**Manual secret (Ryan):** `~/.config/convmem/restic.password` — created by setup if missing.
Back up this file offline; without it you cannot restore from the Restic repo.

**Config:** `~/.config/convmem/restic.env` (from `config/restic.env.example`).

### Live writes

`convmem record --approve-last` and `convmem add --file … --upsert` run the Restic gate **fail-closed** before writing Chroma. **Scope:** only these overwrite/durable-merge paths gate; `convmem index` and plain `add` (no `--upsert`) are append-only and reindexable, so they are intentionally ungated (see ROADMAP "Pre-live-write gate"). Gating every mutation was declined by design.

Optional wrapper (same gate, then `convmem`):

```bash
~/Projects/convmem/scripts/convmem-live-write.sh record --approve-last
~/Projects/convmem/scripts/convmem-live-write.sh add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

### Verify gate

```bash
restic snapshots --tag convmem-chroma          # list chroma backups
bash ~/Projects/convmem/scripts/restic-ensure-chroma-snapshot.sh --check-only
bash ~/Projects/convmem/scripts/verify-restic-gate.sh   # happy + fail-closed negative
convmem doctor                                   # includes restic_gate check
```

### Restore chroma from Restic

```bash
source ~/.config/convmem/restic.env
export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
restic restore latest --tag convmem-chroma --target /tmp/convmem-chroma-restore
# Inspect, then stop watch/refine and replace ~/.local/share/convmem/chroma/ deliberately
```

---

## Fast path (project backup only)

Use when Tier 1 corpus still exists or you accept reindexing later.

```bash
# 1. Restore source tree (your normal backup restore)
cd ~/Projects
# … restore convmem directory …

# 2. Runtime config
mkdir -p ~/.config/convmem
cp ~/Projects/convmem/config.example.toml ~/.config/convmem/config.toml
cp ~/Projects/convmem/config/env.local.shell.example ~/.config/convmem/env.local
cp ~/Projects/convmem/config/env.systemd.example ~/.config/convmem/env.systemd
# Edit env.local + env.systemd: set DEEPSEEK_API_KEY

# 3. Shell alias
source ~/.config/convmem/env.local

# 4. Cursor MCP
cp ~/Projects/convmem/config/cursor-mcp.json.example ~/.cursor/mcp.json
# Edit API key in mcp.json or rely on env.local

# 5. Continue MCP
mkdir -p ~/.continue/mcpServers
cp ~/Projects/convmem/config/continue-mcp.json.example ~/.continue/mcpServers/convmem.json
# Add mcpServers block from config/continue-mcp-servers.yaml.example to ~/.continue/config.yaml
# Tier-A agent models: merge config/continue-models-tier-a.example.yaml under models:

# 5b. Copilot CLI MCP (if installed)
mkdir -p ~/.copilot/agents
cp ~/Projects/convmem/config/copilot-mcp-config.json.example ~/.copilot/mcp-config.json
# Agent protocol also deploys ~/.copilot/agents/convmem.md

# 6. Systemd (optional always-on)
cp ~/Projects/convmem/systemd/convmem-watch.service.example ~/.config/systemd/user/convmem-watch.service
cp ~/Projects/convmem/systemd/convmem-refine.service.example ~/.config/systemd/user/convmem-refine.service
systemctl --user daemon-reload
systemctl --user enable --now convmem-watch.service convmem-refine.service

# 7. Deploy agent protocol surfaces (Cursor .mdc, Codex AGENTS.md, Kiro steering + MCP + permissions.yaml, Crush, Copilot)
bash ~/Projects/convmem/scripts/deploy-agent-protocol.sh
# Kiro: enable MCP in Settings after deploy (see script manual steps)

# 8. Verify
convmem stats
~/Projects/convmem/scripts/verify-continue.sh
# Restart Cursor / Continue / Kiro / Copilot after MCP config changes
# After mcp_server.py updates: bash scripts/restart-convmem-mcp.sh (kills stale stdio subprocesses)
```

---

## Corpus lost (Tier 1)

If `~/.local/share/convmem/chroma/` is gone:

1. Complete **Fast path** above.
2. Restore `~/.local/share/convmem/` from a **data backup** if you have one, **or**
3. Rebuild corpus (hours, GPU/LLM cost):

```bash
mkdir -p ~/.local/share/convmem
convmem inventory          # refresh inventory.jsonl
convmem index              # full index from inventory
convmem refine --once      # optional cleanup pass
convmem stats
```

Approved decisions in `decisions-approved.jsonl` can be re-ingested with
`convmem add` if you still have that file from backup.

### Index drift (doctor `index_drift` check)

`convmem doctor` compares Chroma `knowledge_units` count to
`knowledge_units.jsonl` (config `index.units_export`). Compares Chroma count to
**unique unit ids** in the export (append-only JSONL may have duplicate lines).
WARN below ~30% indexed; FAIL below ~15% or empty Chroma with non-empty export.

**One-command rebuild** (Ryan terminal — clears incremental index state):

```bash
rm ~/.local/share/convmem/processed.json
convmem index
convmem doctor   # index_drift should pass
```

If Chroma itself is corrupt, restore from Restic (above) before reindexing.

---

## What agents may change freely

- Any file under `~/Projects/convmem/` (code, tests, docs)
- `mcp_server.py`, `watch.py`, `brief.py`, etc.
- `~/.cursor/mcp.json`, `~/.kiro/settings/mcp.json`, `~/.copilot/mcp-config.json`, and Continue `mcpServers` (MCP wiring)
- `~/.config/convmem/config.toml` (paths, models)

## What needs Ryan (hook blocks shell destruction)

- `rm` / `mv` / `truncate` on `~/.local/share/convmem/` or `~/.config/convmem/`
- Bulk wipe of Chroma or `processed.json` (use deliberate terminal, not agent)

---

## Related

- `config.example.toml` — index paths and models
- `scripts/verify-continue.sh` — CLI MCP smoke test
- `docs/SYSTEMD-DEPLOY.md` — systemd + env details
- `docs/archive/minipc-deploy/` — archived miniPC deploy (historical; do not run)
- `docs/inter-model/CONTINUE-VERIFY.md` — Continue UI checklist
