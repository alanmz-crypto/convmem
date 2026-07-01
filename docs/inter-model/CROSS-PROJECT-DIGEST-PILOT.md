# Cross-project digest — manual pilot log

**Started:** 2026-06-29  
**Plan:** wait on background synth agent; Phase 0 manual pilots before automation.

Automation: [`scripts/cross-project-digest.sh`](../../scripts/cross-project-digest.sh)  
Output: `~/.local/share/convmem/digests/YYYY-MM-DD.md` (never auto-indexed)

---

## Run 1 — 2026-06-29

**Commands:**

```bash
convmem doctor
convmem brief --stdout-only
convmem unresolved
convmem ask "Cross-project themes and open threads this week; cite ledger ids only. Focus coordination lane (convmem protocol, surface coverage, agent habit) not client deploy."
```

**Quality notes:**

| Check | Result |
|-------|--------|
| Grounded in ledger | Partial — cited `dec_prop_20260625_203408_f9b3` but missed newer `dec_prop_20260629_005903_51b4` |
| False links | None observed |
| Client deploy bleed | Low — staging2 obs correctly absent from ask answer when scoped |
| Stale corpus hit | Ask leaned on Jun 25 decision vs Jun 29 soak close — **recency gap** |
| Actionable | Yes — confirms P2/habit soak still open |

**Verdict:** Synthesis quality **good enough for Phase 1 automation** with explicit recency inputs (recent decisions JSONL + brief staleness alarm). Not ready for auto-approve.

---

## Runs 2–4 (weekly)

Repeat manual block above **or** run:

```bash
~/Projects/convmem/scripts/cross-project-digest.sh
# Phase 2 draft (optional):
~/Projects/convmem/scripts/cross-project-digest.sh --propose
```

Log each run below with date, false-link count, and whether Ryan filed a `convmem record`.

| Run | Date | False links | Record filed? |
|-----|------|-------------|---------------|
| 2 | 2026-06-29 | 0 | Yes — `dec_prop_20260629_150516_6d70` (Arch matrix), `dec_prop_20260629_150527_46f0` (soak close) |
| 3 | 2026-06-29 | 0 | N/A (validation rerun post-records) |
| 4 | 2026-07-01 | 0 | Pending Ryan — Phase 0 close (see Run 4 section) |

---

## Run 4 — 2026-07-01 (post v4 org cleanup)

**Context:** After v4 repo organization shipped (`dec_prop_20260701_000837_8ab4`, inbox 160→33). First run after `SYNTHESIS-STATUS.md` rename.

**Commands:**

```bash
convmem doctor
convmem brief --stdout-only
~/Projects/convmem/scripts/cross-project-digest.sh
convmem ask "Cross-project themes and open threads this week; cite ledger ids only. Focus coordination lane (convmem protocol, surface coverage, agent habit) not client deploy."
```

**Output:** `~/.local/share/convmem/digests/2026-07-01.md`

**Quality notes:**

| Check | Result |
|-------|--------|
| Recency | **Split** — digest header lists Jul 1 v4/org decisions (`000837`, `001127`, etc.); embedded ask synthesis still anchors on `dec_prop_20260629_054023_84ac` / Jun 25 `f9b3` (same recency lag as run 1) |
| False links | 0 |
| Client deploy bleed | Low — coordination lane; 7 coordination unresolved obs |
| Actionable | Yes — habit soak + tooling.kiro obs + v4 ship visible in recent-decisions block |
| Standalone ask | Thin — only cited `054023` chain; confirms recency gap in raw ask without digest context |

**Verdict:** **Phase 0 complete.** Phase 1 automation stable post-v4. **`--propose` eligible for evaluation** (trial run OK; still propose-only). Linker Phase 2 product remains **held** on agent-habit gate (`213047`).

---

## Run 2 — 2026-06-29

**Command:**

```bash
~/Projects/convmem/scripts/cross-project-digest.sh
```

**Output:** `~/.local/share/convmem/digests/2026-06-29.md`

**Quality notes:**

| Check | Result |
|-------|--------|
| Recency | **Better** — recent decisions JSONL includes Jun 29 system-health runbooks (`125741`, `125949`, boot/journal children) |
| False links | None observed |
| Coordination lane | 6 open tooling.kiro obs; habit soak thread cited |
| Handoff staleness | Flagged: `LATEST.md` older than BUILT-PLANS — fixed in same session |
| `ledger_link` probe | `convmem refine --once --job ledger_link --limit 10` → 0 pairs queued (queue empty / no matches) |

**Verdict:** Phase 1 automation validated. Phase 2 `--propose` still gated on runs 3–4 + record anchors.

---

## Run 3 — 2026-06-29 (post-record validation)

**Context:** After `dec_prop_20260629_150516_6d70` (Arch matrix) and `dec_prop_20260629_150527_46f0` (soak close) approved.

**Command:** `cross-project-digest.sh` (same as run 2)

**Also shipped in 2026-06-29 session (plan/code):**
- `obs_806985bc5697` — background synthesis plan pointer in corpus
- Growing jsonl re-index fix in [`ingest.py`](../ingest.py) + tests
- `ledger_link` full run → 0 pairs (no duplicate site/title obs to queue)

**Verdict:** Run 3 confirms digest stable after ledger anchors. One more weekly run (or timer fire) before enabling `--propose`.

---

## Filed record blocks (approved 2026-06-29)

| Ledger | Topic |
|--------|-------|
| `dec_prop_20260629_150516_6d70` | Arch Linux health prompt matrix → `125741` |
| `dec_prop_20260629_150527_46f0` | Global protocol soak close + digest Phase 0–1 → `005903` |
| `dec_prop_20260629_213047_8f73` | Plans vs records alignment (P1c ≠ linker Phase 2) → `212545` |

Copy-paste templates for these are obsolete — search ledger ids for full rationale.

---

## Phase 2 (cron + `--propose`)

Timer install is host ops (see `systemd/convmem-cross-project-digest.{service,timer}.example`). **Plan gate (2026-07-01):** pilot run **4** passed — `--propose` trial runs are **eligible**; do not enable in timer until Ryan approves. Agent-habit gate still blocks treating Phase 2 as shipped product.
