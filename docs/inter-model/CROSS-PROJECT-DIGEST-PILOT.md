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
| 5 | 2026-06-30 | — | Recency injection shipped (Run 5 section) |
| 6 | 2026-07-01 | 0 | **Phase 0 closed** — Ryan defaults: no `--propose`; Phase 2 held |
| 7 | 2026-07-02 | 0 | Recency tighten shipped — see Run 7 |
| 8 | 2026-07-05 | 0 | **`--propose` trial** — `dec_prop_20260705_152603_2c96` **rejected**; pipeline OK; Ryan filing habit confirmed |

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

## Run 5 — 2026-06-30 (recency injection shipped)

**Context:** Builder-reference continuation plan Step 2 — `ledger_recent.py` + forced recent approved decisions in `ask()` when `evidence=True` (MCP default).

**Commands:**

```bash
convmem doctor
.venv/bin/python3 -c "
from ask import ask
from cross_project_digest import DIGEST_ASK_QUESTION
from ledger_recent import recent_decisions_for_cfg
from config import load_config
cfg = load_config()
recent = [r['id'] for r in recent_decisions_for_cfg(cfg)[:5]]
r = ask(DIGEST_ASK_QUESTION, evidence=True, top_k=8)
cited = [c['ledger_id'] for c in r['citations'] if c.get('ledger_id')]
print('recent', recent)
print('cited', cited)
print('overlap', set(recent) & set(cited))
"
```

**Quality notes:**

| Check | Result |
|-------|--------|
| Recency | **PASS** — context + citations include Jul 1 band (`032034`, `031758`, `031411`); overlap with `load_recent_decisions()` header ids (fixes Run 4 split) |
| False links | 0 |
| Golden eval | `scripts/eval-retrieval.py` P@k 83.33% (5/6); no regression vs baseline |
| MCP | `ask` default `evidence=True`; new read-only `unresolved()` tool |

**Verdict:** Recency gap **closed** for digest ask path. `--propose` trial still Ryan-gated.

---

## Run 6 — 2026-07-01 (Phase 0 close — Ryan defaults)

**Context:** Step 2 hygiene session. ChatGPT literature on ice. Cursor ran digest automation; Ryan chose defaults (Phase 0 complete, no `--propose`, Phase 2 held, log + LATEST update).

**Commands:**

```bash
convmem doctor
~/Projects/convmem/scripts/cross-project-digest.sh
```

**Output:** `~/.local/share/convmem/digests/2026-07-01.md` (regenerated 2026-07-01T19:45:26Z)

**Quality notes:**

| Check | Result |
|-------|--------|
| Recency | **PASS** — Jul 1 band cited (`182803`, `192155`, `181506`, builder-reference thread) |
| False links | 0 |
| Coordination unresolved | 1 (`obs_806985bc5697` — background synthesis phase gates) |
| Client deploy bleed | Low — coordination lane |
| Handoff | STALE until LATEST updated (same session) |

**Ryan decisions (defaults):**

| Decision | Choice |
|----------|--------|
| Phase 0 complete | **Yes** |
| `--propose` today | **No** |
| Phase 2 linker product | **Held** |
| Log Run 6 + LATEST | **Yes** |

**Verdict:** **Phase 0 closed.** Manual weekly digest + ask synthesis validated. `--propose` remains Ryan-gated; do not enable timer `--propose` without explicit approval. Phase 2 linker **held** on `obs_806985bc5697`.

---

## Run 7 — 2026-07-02 (recency tighten)

**Context:** Lane 1 follow-up — explicit recent-id injection in digest ask prompt + automated Recency check section in output. Aligns header limit with `RECENT_DECISIONS_LIMIT` (8).

**Shipped (code):**
- `digest_ask_question()` — appends recent approved decision ids to ask prompt
- `recency_check()` + `## Recency check` in digest markdown (PASS/WARN on header ↔ citations overlap)
- Script + systemd example comments updated (Phase 0 closed; `--propose` Ryan-gated)

**Commands:**

```bash
convmem doctor
python -m pytest tests/test_cross_project_digest.py -v
~/Projects/convmem/scripts/cross-project-digest.sh
```

**Output:** `~/.local/share/convmem/digests/2026-07-02.md`

**Quality notes:**

| Check | Result |
|-------|--------|
| Recency | **PASS** — 4 header ids in ask citations (`212051`, `002522`, `002841`, `004322`) |
| False links | 0 |
| Coordination unresolved | 1 (`obs_806985bc5697`) |
| Automation | Timer example = read-only; `--propose` still Ryan-gated |

**Verdict:** Recency injection **tightened** — digest self-validates overlap. Phase 1 automation ready for weekly timer install (host ops). Phase 2 `--propose` **held**.

---

## Run 8 — 2026-07-05 (first `--propose` trial + lab port validation)

**Context:** After lab S1–S5, prod `load_attempts` / Do-not-retry port, dual-model verify (Codex + DeepSeek), and `attempts.jsonl` seeded from example. First approved `--propose` evaluation run.

**Commands:**

```bash
convmem doctor
~/Projects/convmem/scripts/cross-project-digest.sh --propose
```

**Output:** `~/.local/share/convmem/digests/2026-07-05.md`

**Proposal queued:** `dec_prop_20260705_152603_2c96` → `pending_decisions.jsonl` → **REJECTED** by Ryan (stale prod-gap line in ask prose; pipeline validated)

**Ryan (2026-07-05):** prose drafts from normal `record` filing are fine; auto-`--propose` remains optional, not auto-approve.

**Quality notes:**

| Check | Result |
|-------|--------|
| Recency | **PASS** — 4 header ids in ask citations (`125637`, `125652`, `125713`, `152249`) |
| False links | 0 |
| Stale synthesis line | 1 — ask claims "prod still lacks load_attempts port" (incorrect; ported same session) — retrieval lag |
| Do not retry | **Rendered** — example `attempts.jsonl` rows visible |
| Coordination unresolved | 1 (`obs_806985bc5697`) |
| `--propose` relates_to | Fallback `dec_prop_20260623_161428_c311` — ask used `[1][4]` citations not inline `dec_prop_*` in prose |

**Verdict:** Full digest + recency **PASS**. `--propose` pipeline **works** (draft queued and rejected on merit). Phase 2 linker product still **held** on agent-habit gate.

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

Timer install is host ops — **active** on this machine (`convmem-cross-project-digest.timer`, Mon 09:00 read-only; refresh via `scripts/install-cross-project-digest-timer.sh`). **Run 8 `--propose` trial (2026-07-05):** closed — `2c96` rejected; Ryan OK with manual record prose. Agent-habit gate still blocks treating Phase 2 linker as shipped product (`obs_806985bc5697`).

---

## Lab port — attempts + Do not retry (2026-07-05)

Validated in `convmem-lab` (`smoke-synthesis.sh` PASS); shipped to prod:

| Artifact | Prod path |
|----------|-----------|
| `load_attempts()` + digest section | [`cross_project_digest.py`](../../cross_project_digest.py) |
| Schema + ops doc | [`docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md`](../CROSS-PROJECT-DIGEST-ATTEMPTS.md) |
| Example rows | [`config/attempts.jsonl.example`](../../config/attempts.jsonl.example) |
| Precheck | [`scripts/precheck-path.sh`](../../scripts/precheck-path.sh) |
| Smoke | [`scripts/smoke-cross-project-digest.sh`](../../scripts/smoke-cross-project-digest.sh) |

**Ryan setup:** `cp config/attempts.jsonl.example ~/.local/share/convmem/attempts.jsonl` and replace example obs ids with real rows. *(Example file seeded 2026-07-05 — smoke Do-not-retry PASS.)*

**Smoke:** `bash scripts/smoke-cross-project-digest.sh` — Do-not-retry checks active once file exists with failed/partial rows.
