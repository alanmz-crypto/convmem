# SYNTHESIS-STATUS — Background synthesis Phase 0 complete

**Lane:** synthesis / cross-project digest (not global protocol — see [`docs/inter-model/LATEST.md`](docs/inter-model/LATEST.md) for protocol handoff).

**Date:** 2026-07-01  
**Author:** composer-2.5-fast (pilot run 4)

---

## Canonical plan (do not duplicate)

**Background conversation linking / cross-project synthesis:**

| Doc | Role |
|-----|------|
| [`docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md`](docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md) | § *Cross-project background synthesis* — gates, Phases 0–3, execution status |
| [`docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md`](docs/inter-model/CROSS-PROJECT-DIGEST-PILOT.md) | Manual pilot log — runs 1–4 complete |
| [`scripts/cross-project-digest.sh`](scripts/cross-project-digest.sh) | Phase 1 read-only reporter (shipped) |

**Phase 2 `--propose`:** eligible for **evaluation trial** (propose-only — never auto `record --approve-last`). Autonomous linker product still **held** on agent-habit gate.

**Not the same track:** ROADMAP **P1c** (ask streaming on timeout) is orthogonal — see [`docs/ROADMAP.md`](docs/ROADMAP.md) and `dec_prop_20260629_213047_8f73`.

---

## Execution checklist

### Phase 0 (digest pilots)

- [x] Pilot run 2 — `cross-project-digest.sh` → `~/.local/share/convmem/digests/2026-06-29.md`
- [x] Pilot run 3 — post-record validation (same script)
- [x] Pilot run 4 — `~/.local/share/convmem/digests/2026-07-01.md` (post v4 org cleanup)
- [x] Ledger anchors filed — `150516`, `150527`, `213047` (see BUILT-PLANS filed table)
- [x] Growing-session re-index — [`ingest.py`](ingest.py) + [`tests/test_watch_skip.py`](tests/test_watch_skip.py)
- [x] Coordination plan searchable — `obs_806985bc5697`

### Prerequisites before linker Phase 2 (product)

- [ ] Agent habit — still the main synthesis-value gate (`213047`)
- [x] `link_queue.jsonl` review — `ledger_link` → 0 pairs (vacuous pass)
- [ ] Inter-model `docs/inter-model/*.md` watch-index — still open (workaround: `obs_806985bc5697`)

### Later (after gates)

- Trial: `cross-project-digest.sh --propose` (weekly, propose-only) — **Ryan approves first run**
- Optional: install timer from `systemd/convmem-cross-project-digest.{service,timer}.example`
- Change feed (Phase 3) — temporal diff, separate from thematic linking

---

## Current state

- **Phase 0 manual pilots: complete** (2026-07-01)
- Phase 1 digest script **shipped**; linker Phase 2 product **deferred** (agent habit)
- Known limitation: ask synthesis prose lags recent-decisions header (recency gap — same as run 1; mitigated by digest JSONL block)
- Global protocol: see [`docs/inter-model/VERIFICATION-MATRIX.md`](docs/inter-model/VERIFICATION-MATRIX.md) and [`docs/inter-model/CONTINUE-VERIFY.md`](docs/inter-model/CONTINUE-VERIFY.md)

---

## Soak data (archival — Jun 25 matrix)

Pre-Qwen-close snapshot; newer Continue headless rows in [`docs/inter-model/SOAK-REPORT-2026-06-25.md`](docs/inter-model/SOAK-REPORT-2026-06-25.md) (#19–#22).

| # | Dir | Surface | Convmem reached? |
|---|-----|---------|-----------------|
| 5 | pavlomassage-practice | Continue | **❌** (qwen3-coder:30b later **PASS** — see CONTINUE-VERIFY) |
| 6 | pavlomassage-practice | Crush | **❌** |

---

## Next agent

1. BUILT-PLANS § *Cross-project background synthesis* — single source of truth
2. **Optional:** trial `cross-project-digest.sh --propose` (Ryan approves; review `pending_decisions.jsonl`)
3. Do **not** treat linker Phase 2 as shipped until agent-habit gate passes
4. P1c ask streaming is the **coding** next item on roadmap (separate track)
5. For global protocol / Continue verify handoff use [`docs/inter-model/LATEST.md`](docs/inter-model/LATEST.md)
