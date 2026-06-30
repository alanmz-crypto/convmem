# Restic snapshot safety gate — session close (2026-06-30)

**Author:** composer-2.5-fast (Cursor)  
**Chains to:** `dec_prop_20260630_205008_f0d2` (operational gate verify), `dec_prop_20260630_153326_e91f` (roadmap execute-ready arc)  
**Trigger:** Ryan — close Restic/snapshot gate before further feature work; no retrieval/synthesis/adapter changes.

---

## Summary

Live Chroma writes are now **fail-closed** behind a Restic snapshot gate. Hygiene/index pass complete; inventory pending 0; doctor passes. Two bisectable commits on `main`: scripts + doctor (`f6e44e0`), inline CLI wiring (`273ab4f`).

---

## Done — gate implementation

| Layer | Detail |
|-------|--------|
| **Snapshot script** | `scripts/restic-ensure-chroma-snapshot.sh` — snapshot if stale (local calendar day); exit 1 on any Restic failure |
| **Wrapper** | `scripts/convmem-live-write.sh` — same gate, then `convmem` |
| **CLI integration** | `restic_gate.py` → `ensure_chroma_snapshot_for_live_write()` called from `convmem.py` before `record --approve-last` ingest and `add --upsert` |
| **Test escape** | `CONVMEM_SKIP_RESTIC_GATE=1` for unit tests |
| **Doctor** | `_check_restic()` — reports whether today's `convmem-chroma` snapshot exists |
| **Setup / verify** | `scripts/setup-restic-chroma.sh`, `scripts/verify-restic-gate.sh`, `config/restic.env.example` |
| **Docs** | `docs/ROADMAP.md`, `docs/RECOVER.md` — bare `convmem` gated; wrapper optional |

### Commits

| Hash | Message |
|------|---------|
| `f6e44e0` | Add fail-closed Restic snapshot gate for live Chroma writes |
| `273ab4f` | Wire Restic fail-closed gate into live CLI write paths |

---

## Done — operational state (this host)

From `docs/logs/2026-06-30-restic-gate-operational.md`:

- Local repo: `~/.local/share/convmem-restic`
- Local snapshot `42e6d795` (50.4 MiB chroma, 2026-06-30)
- External: `/run/media/lauer/rxBUlauer-128Gfs/convmem-backups` — snapshot `6da7cdd5` via `restic copy`
- `convmem doctor` PASS including `restic_gate: snapshot covers today`

---

## Verification (session close)

| Check | Result |
|-------|--------|
| `convmem doctor` | PASS (restic_gate covers today) |
| `python3 -m unittest tests.test_restic_gate tests.test_chroma_approve_index tests.test_doctor` | 10 tests OK |
| `bash scripts/verify-restic-gate.sh` | PASS (happy path + fail-closed) |

---

## Policy after close

| Path | Behavior |
|------|----------|
| `convmem record --approve-last` | Gate runs automatically (unless `--no-index` skips ingest path — gate still runs when upsert happens) |
| `convmem add --file … --upsert` | Gate runs before upsert |
| `scripts/convmem-live-write.sh …` | Equivalent (double gate harmless) |

**Stale threshold:** latest `convmem-chroma` snapshot must be from **local calendar day**; otherwise auto-backup before write.

---

## Not done (deferred / manual)

- [ ] Offline backup of `~/.config/convmem/restic.password`
- [ ] Optional `RESTIC_EXTERNAL_REPOSITORY` in `restic.env`
- [ ] Optional `scripts/restic-copy-external.sh` helper
- Retrieval tuning, synthesis, rerank, streaming, TUI, adapters, new proposal features (explicitly out of scope)

---

## Related

- `docs/logs/2026-06-30-restic-gate-operational.md` — host setup + external copy walkthrough
- `docs/RECOVER.md` — restore + gate policy
- `docs/ROADMAP.md` — Pre-live-write gate (Restic) section

---

## Record block

Ryan runs:

```bash
convmem record \
  --relates-to dec_prop_20260630_205008_f0d2 \
  --summary "convmem repo: Restic snapshot gate closed — inline CLI fail-closed on record --approve-last and add --upsert" \
  --rationale "Done: f6e44e0 (scripts, doctor, wrapper, verify) + 273ab4f (restic_gate.py wired into convmem.py live write paths). Snapshot-if-stale on local calendar day; block on any Restic failure. Tests: test_restic_gate, test_chroma_approve_index, test_doctor — all PASS; verify-restic-gate.sh PASS. Bare convmem record --approve-last now safe without wrapper. Operational: local repo + external rxBUlauer-128Gfs copy documented in docs/logs/2026-06-30-restic-gate-operational.md. Open: offline restic.password backup; optional external env helper. Not my lane: retrieval, synthesis, adapters, miniPC doc cleanup (separate uncommitted work)." \
  --author composer-2.5-fast

convmem record --approve-last
```
