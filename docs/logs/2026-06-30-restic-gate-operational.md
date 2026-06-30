# Restic gate — operational verification (2026-06-30)

**Author:** Auto (Cursor)  
**Trigger:** Ryan asked to get the Restic live-write gate running (step 1) and set up external backup.  
**Chains to:** `dec_prop_20260630_153326_e91f` (execute-ready roadmap — Restic gate arc)

---

## Summary

Local Restic pre-write gate is **operational**. External repo on `rxBUlauer-128Gfs` is **initialized** with today's chroma snapshot copied. One-time password offline backup still pending.

---

## Step 1 — Gate verification (all passed)

Commands run with `source ~/.config/convmem/env.local` and `source ~/.config/convmem/restic.env`.

| Check | Command | Result |
|-------|---------|--------|
| Health | `convmem doctor` | All checks passed; `restic_gate: snapshot covers today (tag=convmem-chroma)` |
| Gate script | `bash ~/Projects/convmem/scripts/verify-restic-gate.sh` | PASS 4a (happy path: init → snapshot → require-current → wrapper) and PASS 4b (fail-closed on missing password) |
| Local snapshots | `restic snapshots --tag convmem-chroma` | 1 snapshot: `42e6d795` @ 2026-06-30 14:21:23 CDT, 50.431 MiB, path `/home/lauer/.local/share/convmem/chroma` |

**Local repo path:** `~/.local/share/convmem-restic` (`RESTIC_REPOSITORY` in `~/.config/convmem/restic.env`)

---

## Step 2 — Live writes (mandatory wrapper)

Do **not** use bare `convmem` for operations that upsert the live corpus:

```bash
~/Projects/convmem/scripts/convmem-live-write.sh record --approve-last
~/Projects/convmem/scripts/convmem-live-write.sh add --file ~/.local/share/convmem/decisions-approved.jsonl --upsert
```

Optional alias in `~/.config/convmem/env.local`:

```bash
alias convmem-live-write='~/Projects/convmem/scripts/convmem-live-write.sh'
```

**Gate behavior:** stale chroma (no snapshot from local calendar day) → auto snapshot before write; any Restic failure → write blocked (fail-closed).

---

## Step 3 — Password backup (once, still open)

- File: `~/.config/convmem/restic.password` (mode 600, 45 bytes)
- **Action:** copy to password manager or encrypted USB
- Without this file, both local and external repos are unrecoverable

---

## Step 4 — External repo (rxBUlauer-128Gfs)

**Chosen path:** `/run/media/lauer/rxBUlauer-128Gfs/convmem-backups`

### Troubleshooting during setup

| Issue | Cause | Fix |
|-------|-------|-----|
| `repository does not exist … config: no such file` | Repo not initialized yet | One-time `restic init -r <external-path>` (not local) |
| `permission denied` on init | `convmem-backups` owned by root | `sudo chown -R lauer:lauer /run/media/lauer/rxBUlauer-128Gfs/convmem-backups` |
| `config file already exists` on local init | Local repo already exists | **Expected — do not re-init local.** Only init external path once |

### Current external state (verified)

```bash
source ~/.config/convmem/restic.env && export RESTIC_PASSWORD_FILE
restic snapshots --tag convmem-chroma \
  -r /run/media/lauer/rxBUlauer-128Gfs/convmem-backups
```

| Field | Value |
|-------|-------|
| Snapshot ID | `6da7cdd5` |
| Time | 2026-06-30 14:21:23 (same as local) |
| Tags | `convmem-chroma`, `convmem-2026-06-30` |
| Size | 50.431 MiB |

External repo initialized; chroma snapshot copied via `restic copy` (encrypted snapshot duplicate, not raw folder copy).

### Optional config addition

Add to `~/.config/convmem/restic.env`:

```bash
RESTIC_EXTERNAL_REPOSITORY=/run/media/lauer/rxBUlauer-128Gfs/convmem-backups
```

### Copy local → external (after live writes or nightly when drive mounted)

```bash
source ~/.config/convmem/restic.env
export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE

restic -r /run/media/lauer/rxBUlauer-128Gfs/convmem-backups copy latest \
  --from-repo "$RESTIC_REPOSITORY" \
  --tag convmem-chroma
```

If drive not mounted: skip external copy — **does not block local live writes**. Gate only checks local repo.

---

## Other mounted drives (not used for convmem backup)

At session time: `BIT-Brg-larch-7t`, `rszl-larch-5t-fs`, `BIT-25G-paula-fs`, `BIT-shf-larch-fs`, `nym-ollama-1T-fs`, `rxBUlauer-128Gfs`.

Canonical external choice: **rxBUlauer-128Gfs** (`convmem-backups`).

---

## Suggested routine

| When | Action |
|------|--------|
| Session with decision to record | `convmem-live-write.sh record --approve-last` |
| After live write (optional) | `restic copy` to external if drive mounted |
| Daily / before risky work | `convmem doctor` |
| Weekly | External `restic copy` + confirm password backup exists |

---

## Restore reference

See `docs/RECOVER.md`:

```bash
source ~/.config/convmem/restic.env
export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
restic restore latest --tag convmem-chroma --target /tmp/convmem-chroma-restore
```

Use `-r <external-path>` to restore from external repo instead of local.

---

## Still open

- [ ] Offline backup of `~/.config/convmem/restic.password`
- [ ] Add `RESTIC_EXTERNAL_REPOSITORY` to `restic.env` (optional convenience)
- [ ] Optional: `scripts/restic-copy-external.sh` helper script + `config/restic-external.env.example`
- [ ] Optional: `sudo pacman -S restic` for persistence across shells (conda restic works today)

---

## Related docs

- `docs/RECOVER.md` — setup, gate, restore
- `docs/ROADMAP.md` — Pre-live-write gate (Restic) section
- `docs/logs/2026-06-30-roadmap-polish-final.md` — execute sequence that included Restic gate
- `scripts/verify-restic-gate.sh` — CI/manual gate verification
- `scripts/convmem-live-write.sh` — fail-closed wrapper for live writes
