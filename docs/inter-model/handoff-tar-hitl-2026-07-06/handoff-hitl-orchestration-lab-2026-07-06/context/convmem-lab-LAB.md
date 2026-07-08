# convmem-lab — isolated experiment fork

**Status:** ready  
**Owner:** Ryan  
**Sunset:** 2026-09-01 — re-read or archive; spikes graduate or defer explicitly

**Agents — lost?** Read [`~/Projects/convmem/docs/MODEL-WORKFLOW.md`](../../convmem/docs/MODEL-WORKFLOW.md) section **C (lab track)** first.

**Not production.** Lab output is **disposable** — synthetic corpus, lab `LATEST.md`, and queue JSONL under `~/.local/share/convmem-lab/` may diverge from prod at any time. Wipe and re-seed is normal; do not treat lab pointer history as canonical.

---

## Non-goals

- No MCP registration for the lab clone
- No watch/refine/systemd timers against lab paths
- No production corpus copy or full reindex in lab
- No retrieval tuning or golden-eval work in lab

---

## Lane separation

| Lane | Validates | Tools |
|------|-----------|-------|
| **Lab** | **Coordination semantics** — pointer lifecycle, obs defer/revisit, recurring-failure surfacing, handoff discipline | `convmem-lab.sh`, synthetic fixtures, diff-only scripts |
| **Prod** | **Retrieval quality** — ranking, recency, evidence selection | `scripts/eval-retrieval.py`, golden queries, `convmem ask` / search |

Do not use lab to tune retrieval or mine corpus scale. **Builder-reference:** DDIA + Arch Patterns for lab; Manning for prod only.

---

## Reference routing

Use [`docs/lab-reference/`](lab-reference/README.md) (this repo) first for lab coordination, gate policy, synthesis smoke, and refresh/deploy wrapper work.

Use [`~/Projects/convmem/docs/builder-reference/`](../../convmem/docs/builder-reference/README.md) only when the task changes prod architecture, module boundaries, workflow design, or other durable system behavior — not for routine lab fixture or smoke work.

If both apply: read builder-reference first for system shape, then lab-reference for the lab-specific policy and gates.

---

## Isolation map

| Tier | Production | Lab |
|------|------------|-----|
| Source | `~/Projects/convmem` | `~/Projects/convmem-lab` (`lab/main` branch) |
| Config | `~/.config/convmem` | `~/.config/convmem-lab` |
| Data | `~/.local/share/convmem` | `~/.local/share/convmem-lab` |

### Anti-leak guard

**Never register the lab clone in Cursor, Continue, Kiro, or Crush MCP configs until a spike graduates.** Use `scripts/convmem-lab.sh` only.

---

## CLI setup

```bash
mkdir -p ~/.config/convmem-lab ~/.local/share/convmem-lab
cp ~/Projects/convmem-lab/config/convmem-lab-config.toml.example \
   ~/.config/convmem-lab/config.toml

chmod +x ~/Projects/convmem-lab/scripts/convmem-lab.sh
bash ~/Projects/convmem-lab/lab/scripts/seed-fixtures.sh
```

Wrapper sets (core code reads **only** `CONVMEM_CONFIG`):

- `CONVMEM_CONFIG=~/.config/convmem-lab/config.toml`
- `CONVMEM_ROOT=~/Projects/convmem-lab`
- `CONVMEM_SKIP_RESTIC_GATE=1` (wrapper only — not a core env hook)

### Fixture corpus

- `lab/fixtures/*.jsonl` — synthetic, reproducible, never prod Chroma
- Reset: `rm -rf ~/.local/share/convmem-lab/chroma && bash lab/scripts/seed-fixtures.sh`

### Session workflow

```bash
bash ~/Projects/convmem-lab/lab/scripts/seed-fixtures.sh
~/Projects/convmem-lab/scripts/convmem-lab.sh doctor
~/Projects/convmem-lab/scripts/convmem-lab.sh unresolved
~/Projects/convmem-lab/scripts/convmem-lab.sh unresolved --deferred
~/Projects/convmem-lab/scripts/convmem-lab.sh unresolved --due
~/Projects/convmem-lab/scripts/propose-latest-pointer.sh   # diff only unless exercising --accept
bash ~/Projects/convmem-lab/lab/scripts/trend-report.sh
bash ~/Projects/convmem-lab/lab/scripts/handoff-warn.sh      # advisory WARN, exit 0
```

**Sequence:** Spike 1 until boring → Spike 2 → Spike 3 → Spike 4 advisory.

**Synthesis acceleration (big picture):** see [LAB-SYNTHESIS-PLAN.md](LAB-SYNTHESIS-PLAN.md) — Codex execution plan to harden digest/`--propose` in lab before prod trial.

---

## Spike 1 — LATEST pointer lifecycle (active)

**Mode: read-only by default**

| Command | Effect |
|---------|--------|
| `propose-latest-pointer.sh` (default) | Unified diff only — **no file writes** |
| `propose-latest-pointer.sh --accept` | Writes **lab repo only** `docs/inter-model/LATEST.md` — does not change prod |

Uses [`brief._handoff_staleness`](../brief.py) (same signal as `⚠ STALE HANDOFF` in brief).

**Owner:** Ryan  
**Fitness function (EA):** `propose-latest-pointer.sh` + brief staleness signal (`_handoff_staleness` / `_newest_inter_model_file`)

### Lab-only exit criteria

- [x] 3+ diff-only runs; output matches brief `newest_file`
- [x] Pointer rules documented below (boring / repeatable)
- [x] One lab `--accept`; verify staleness clears on lab brief, resurfaces when newer file added

### Pointer rules (spike 1)

- Qualifying files: `docs/inter-model/*.md` except `README.md`, `LATEST.md`
- Default: diff only; never suppress brief staleness alarm
- `--accept`: prepend one Active handoff bullet + update `**Updated:**` date
- Lab `LATEST.md` divergence from prod is expected and disposable

### Prod graduation criteria (separate)

- [ ] Rules reviewed; owner remains **Ryan**; fitness function as above
- [ ] Graduate script to prod repo + `convmem record --relates-to` from search
- [ ] **`--accept` stays opt-in** — default diff-only until Ryan has used prod diff-only several times and explicitly chooses to accept

---

## Spike 2 — Defer / revisit / resolution (next)

**Pinned:** defer is **workflow state** in append-only `defer_queue.jsonl`, not mutable observation state.

```json
{"ledger_id":"obs_lab_deferred_001","status":"deferred","owner":"ryan","next_review":"2026-07-15","sunset":null,"note":"...","deferred_at":"2026-07-01T12:00:00Z"}
```

| Field | Format | Semantics |
|-------|--------|-----------|
| `next_review` | date-only `YYYY-MM-DD`, UTC calendar day | Due when `next_review <= today_utc_date` |
| `deferred_at` | ISO UTC timestamp | When defer row was written (audit) |
| `sunset` | date-only `YYYY-MM-DD` or null | When `today_utc_date > sunset`, **suppresses `--due` and re-open eligibility** — obs stays in full unresolved as archived-deferred; not informational-only |

**Read path:** join Chroma obs + latest defer row per `ledger_id`. No auto-resolve.

### Lab-only exit criteria

- [x] `defer_queue.jsonl` in lab data dir (`lab/fixtures/defer_queue.jsonl` → seed)
- [x] `convmem-lab.sh unresolved --deferred` / `--due` on synthetic set
- [x] Sunset suppresses due/re-open as pinned above

**CLI:**

```bash
# Append defer row (does not mutate Chroma obs)
~/Projects/convmem-lab/scripts/convmem-lab.sh defer obs_lab_coord_001 \
  --next-review 2026-08-01 --note "revisit after spike"

~/Projects/convmem-lab/scripts/convmem-lab.sh unresolved --deferred
~/Projects/convmem-lab/scripts/convmem-lab.sh unresolved --due
```

### Prod graduation criteria (separate)

- [ ] Spike 1 done; obs Chroma rows unchanged; record + CLI merge

---

## Spike 3 — Trend detector

Lab stdout report on synthetic fixtures. Not a Manning eval.

```bash
bash ~/Projects/convmem-lab/lab/scripts/trend-report.sh
```

- Lab exit: surfaces repeat class (2+ obs with similar title stem in same domain)
- Prod graduation: optional digest appendix only

---

## Spike 4 — Health-before-handoff

**Advisory only in lab.** WARN not FAIL on `doctor` until Zeller soak evidence.

```bash
bash ~/Projects/convmem-lab/lab/scripts/handoff-warn.sh   # always exit 0
```

- Lab exit: advisory script; `doctor` still exit 0 (handoff warn is separate)
- Prod graduation: separate record; never conflate lab WARN with prod `doctor` policy

---

## Graduation (lab → prod)

1. **DDIA:** single-writer / ledger authority unchanged
2. **EA:** one fitness-function owner per check (human owner + named script/signal)
3. **Zeller:** doctor + golden eval on prod
4. **Ryan:** `convmem record --relates-to` from search
5. MCP registration only after explicit approval

## Reference routing

Use `docs/lab-reference/` for lab coordination, generated slices, and refresh/deploy wrapper work.

Use `~/Projects/convmem/docs/builder-reference/` when the task changes prod architecture, boundaries, or durable system behavior.

If both apply, read `builder-reference` first for system shape, then `lab-reference` for the lab-specific policy.

## Lab reference

The curated reasoning slices live in [`docs/lab-reference/`](lab-reference/README.md).
Application guide (gate registry, big-picture synthesis test): [`docs/lab-reference/NOTES.md`](lab-reference/NOTES.md).

```bash
bash scripts/refresh-lab-reference.sh    # regenerate index + verify
bash lab/scripts/compile-synthesis-brief.sh   # deterministic big-picture brief
bash lab/scripts/smoke-synthesis.sh        # full synthesis + lab-reference gate
```

## Prod dependency

Lab requires `CONVMEM_CONFIG` in production [`config.py`](../config.py) (shipped).
