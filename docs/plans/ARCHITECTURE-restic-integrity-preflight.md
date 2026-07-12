# Architecture — Restic Integrity Preflight (Gate 6 follow-on)

**Date:** 2026-07-12  
**Branch:** `plan/2026-07-12-restic-integrity-preflight`  
**Predecessor:** [`ARCHITECTURE-chroma-restore-drill.md`](ARCHITECTURE-chroma-restore-drill.md) (merged — Mechanical PASS @ `7e5a1ce`, PR #1)  
**Phase:** Architecture Planning → HITL before Execution Planning

```
Planning Status

Phase:        Architecture Planning
Characters:   Architect, Systems Thinker, Risk Reviewer
Functions:    Planner
Lanes:        Cursor (Tier A); Codex read-only if Ryan requests direction audit
Authority:    Awaiting HITL
```

---

## Architecture Direction — Restic repository integrity preflight

**Source:** Ryan “pick the next … task” after Chroma Restore Drill closed; Gate 6 deferred in restore-drill architecture until the basic drill (incl. vector round-trip) was proven.  
**Authority:** Awaiting HITL @ 2026-07-12  
**Problem:** A successful restore proves a *snapshot* is usable; it does **not** prove the *Restic repository* (packs/trees/indexes) is structurally sound or that pack data is readable — that is `restic check`.

### System boundary

**In scope**

- One-shot (this pass) integrity proof against the **local** `RESTIC_REPOSITORY` for tag `convmem-chroma`
- A small runner + durable report (outside any temp dir), same report/trap discipline as the restore drill
- Optional doctor **warn** surfacing “last integrity report age” (non-fatal; does **not** join the live-write gate)
- Hermetic tests for report shape / CLI wiring (no live Restic required for unit tests)

**Out of scope**

- Changing Restic snapshot cadence, write-gate, or `restic-ensure-chroma-snapshot.sh` fail-closed policy
- Full `--read-data` of every pack as the default (cost)
- Offsite/`RESTIC_EXTERNAL_REPOSITORY` integrity (doctor already has `restic_external` freshness; separate ops)
- Folding `restic check` into every restore-drill happy path (keeps restore drill fast)
- Bad-credentials exercise, manifest-at-snapshot recording (still deferred from restore-drill gates 4/5)
- Remediating today’s stale offsite copy (ops: `scripts/restic-copy-external.sh` / timer) — related but not this arc’s deliverable
- Stopping or mutating live Chroma

**Deferred with owner**

| Item | Owner |
|------|--------|
| Recurring timer for integrity check | Ryan after one-time PASS |
| External-repo `restic check` | Separate arc if needed |
| Wire integrity into restore-drill as optional `--with-integrity-preflight` | Only if one-time PASS proves value |

### Constraints and invariants

- Live Chroma never stopped/replaced/written by this arc
- Live-write gate (`restic_gate` / `convmem-live-write.sh`) remains **freshness of snapshot**, not integrity — integrity must not silently become fail-closed without an explicit gate decision
- Prefer explicit snapshot/host/tag filters over implicit “latest”
- Report initialized early; `EXIT` trap finalizes report; temp dirs cleaned; report retained
- Predecessor proof stands: restore drill happy-path report `drill-20260712T174915Z.json` (snapshot `1584dccd`)

### Options considered

| Option | Summary | Rejected because |
|--------|---------|------------------|
| A — Structural `restic check` only | Fast pack/tree/index consistency | Misses unread pack-data corruption; weaker than Gate 6 intent |
| B — Structural + `--read-data-subset` (recommended) | Consistency + sampled blob reads | — |
| C — Full `--read-data` every run | Strongest | Runtime cost; wrong default for on-demand proof |
| D — Bake into restore drill always-on | One command does restore+integrity | Couples slow integrity to every restore proof; violates restore-drill locked “no restic-gate changes / keep drill focused” |

### Chosen direction

**Option B, as a separate on-demand runner** (not part of the restore-drill happy path): run `restic check` against the local repo with tag filter `convmem-chroma`, structural verification **plus** a bounded `--read-data-subset` (default **5%**), write a durable JSON/MD report under `~/.local/share/convmem/integrity-check/reports/`, and expose a doctor **warn** (never fail) when no successful report exists within a configurable age (default **14 days**). Do **not** change the live-write gate. Optional later: restore-drill `--with-integrity-preflight` after this pass PASSes once.

### Risks and reversibility

- **Runtime:** even 5% read-data can take minutes on a large repo — keep cadence one-time/on-demand; doctor warn only
- **False confidence:** subset ≠ full read — document in report; full `--read-data` remains a manual Ryan override flag
- **Lock contention:** `restic check` can fail with exit 11 if repo locked — report must record lock errors distinctly; do not retry forever
- **Scope creep into fail-closed:** doctor must stay warn/skip; reversing would be a separate HITL decision
- **Rollback:** delete runner + doctor probe + reports; no data-path changes

### Downstream handoff

- Next phase: [`EXECUTION-PLANNING.md`](../planning/EXECUTION-PLANNING.md) after HITL approves this direction (and the gates below).
- Predecessor docs stay frozen: do not reopen restore-drill gates 1–5.

---

## Decisions Ryan must make before build

| # | Decision | Recommendation (default if you assent) |
|---|----------|------------------------------------------|
| 1 | Check depth | **Structural `restic check` + `--read-data-subset 5%`**; optional `--full-read-data` override for manual deep runs |
| 2 | Cadence this pass | **One-time proof** (like restore drill); no systemd timer yet |
| 3 | Doctor coupling | **Warn-only** if last PASS report older than **14 days** (or missing); never fail `doctor` / never join live-write gate |
| 4 | Coupling to restore drill | **Separate script** (`scripts/restic_integrity_check.py` or `.sh`); no change to restore-drill happy path |
| 5 | Repo scope | **Local `RESTIC_REPOSITORY` only**; external stays `restic_external` freshness |
| 6 | Report home | **`~/.local/share/convmem/integrity-check/reports/`** (sibling of restore-drill reports) |

---

## Locked (no re-open without new HITL)

- Does not modify Restic write-gate / snapshot cadence
- Does not stop or mutate live Chroma
- Integrity never silently becomes fail-closed
- Restore-drill Mechanical PASS remains valid without re-running for this arc

---

## Success (executive bar)

- One successful local-repo integrity run produces a durable report with command flags, duration, exit code, and subset parameters
- Doctor surfaces stale/missing integrity reports as **warn**, not fail
- Hermetic tests cover report wiring without requiring a live Restic repo
- Intentional failure path (e.g. wrong password file / missing repo) exits nonzero and still writes a report when possible

---

## Explicitly not picking

| Candidate | Why not now |
|-----------|-------------|
| WH-practice Tier 0 cleanup | Product/client; unlocked but separate session (charter: don’t mix with convmem infra) |
| Close `obs_e1520bf6e193` | Superseded by `dec_prop_20260706_032613_51dd` — ledger hygiene, not an arc |
| `obs_806985bc5697` synthesis pointer | Medium unresolved; not the recoverability follow-on |
| Offsite copy STALE | Ops run of `restic-copy-external.sh`; adjacent but not Gate 6 |

---

## Gates

Await Ryan: **accept defaults** or override rows 1–6 above. Then Cursor shapes EXECUTION on this branch.
