# Codex packet — P1.3 source-trust (handoff + execution)

**Purpose:** Single paste for Codex: harbor-map handoff + full EXECUTION plan.

**Canonical EXECUTION path:** [`../plans/EXECUTION-2026-07-21-source-trust-ranking.md`](../plans/EXECUTION-2026-07-21-source-trust-ranking.md)

---

# Codex packet — paste both sections

## Part 1 — Harbor-map handoff

# Codex handoff — P1.3 source-trust ranking

**From:** Cursor (this session)
**To:** Codex
**When:** 2026-07-21
**Job:** Implement P1.3 from `origin/main` after #75/#76. Open a feat PR. Stop at merge (Ryan squash-merges).

Ryan already ledgered the plan approval: `dec_prop_20260722_013340_dc60` → relates to `dec_prop_20260707_014137_02d1`. Docs PR with the written plan: https://github.com/alanmz-crypto/convmem/pull/77 (open; tip `205e91d` on `docs/2026-07-21-p13-source-trust-handoff`).

---

## Metaphorical map to Cursor's memory

Think of the corpus as a **harbor city**. You do not need Cursor's live brain — the maps are already posted on the notice boards.

```text
                    ┌─────────────────────────────┐
                    │  LIGHTHOUSE (start here)     │
                    │  docs/inter-model/LATEST.md │
                    └──────────────┬──────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
   ┌───────────────┐     ┌─────────────────┐     ┌──────────────────┐
   │  HARBORMASTER │     │  SHIP'S LOG     │     │  DRY DOCK        │
   │  Codex brief  │     │  EXECUTION plan │     │  Already shipped │
   │  handoff.md   │     │  (+ corpus twin)│     │  #75 #76 main    │
   └───────┬───────┘     └────────┬────────┘     └────────┬─────────┘
           │                      │                       │
           └──────────┬───────────┴───────────┬───────────┘
                      ▼                       ▼
            ┌──────────────────┐    ┌─────────────────────┐
            │  CARGO HOLD      │    │  WHISPER ARCHIVE    │
            │  (this chat)     │    │  "chat-only deltas" │
            │  4d0fbf93-…jsonl │    │  R0401, omit-zero,  │
            │  32 active units │    │  /tmp eval gate     │
            └──────────────────┘    └─────────────────────┘
```

| Landmark | What it is | How to find it |
|----------|------------|----------------|
| **Lighthouse** | Single pointer for "what's active" | `convmem "LATEST P1.3 source-trust"` or read `docs/inter-model/LATEST.md` |
| **Harbormaster** | Everything you need to execute without Cursor session memory | `convmem "P1.3 source-trust ranking Codex handoff"` → `CURSOR-2026-07-21-p13-source-trust-codex-handoff.md` |
| **Ship's log** | Phased EXECUTION + acceptance | Repo: `docs/plans/EXECUTION-2026-07-21-source-trust-ranking.md` · Searchable twin: `CURSOR-2026-07-21-p13-source-trust-execution.md` · `convmem "EXECUTION source-trust pipeline fuse trust"` |
| **Cargo hold** | This Cursor conversation distilled into units | Source: `…/agent-transcripts/4d0fbf93-e1cb-4f47-99d2-0871231f5dbd/…jsonl` · `convmem "source-trust ranking criticality ksweep-routing"` / `convmem "Ranking pipeline order trust stage after rank fusion"` |
| **Ledger stamp** | Ryan's approval that the plan is real | `dec_prop_20260722_013340_dc60` |
| **Dry dock** | Prerequisites already on main — do not rebuild | #75 `6feae58` steering ingest · #76 `b4af44f` search postfilters |
| **Prior pier (closed)** | who-fixes-retrieval Rounds 1–4 — inherit or dismiss; not a new grant | [`CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md`](CURSOR-2026-07-22-who-fixes-retrieval-closed-to-p13.md) · `convmem "who-fixes-retrieval closed to P1.3 inherit dismiss"` · cargo `566966f0-…jsonl` |
| **Fog bank (ignore)** | Crush `ksweep-routing` stopgap | Leave it; sunset is a follow-up after P1.3 is live |

**Ritual entry to the city:**

```bash
convmem doctor
convmem brief --stdout-only
convmem "P1.3 source-trust ranking Codex handoff"
convmem "EXECUTION source-trust ranking"
```

---

## Problem (one breath)

Crush grepped `~` for `#ksweep-deploy` because **search ranked a stale chat distillation above real `.kiro/steering/` files**. Ritual was fine; ranking was wrong. Ingest (#75) and postfilters (#76) shipped; **P1.3 adds source-trust boosts** so trusted sources win.

---

## Locked design (do not renegotiate mid-flight)

**Tiers (first match):**
1. `kiro_steering` / path `.kiro/steering/` → **0.15**
2. ledger decision/observation/verification → **0.12**
3. `inter_model_doc` / `docs/inter-model/` → **0.08**
4. else → **0**

`source_trust_boost = source_trust_weight * tier` — **omit the field when 0** (unlike `evidence_boost`).
`rank_score = rank_fusion_score + source_trust_boost`
Config example: `[query] source_trust_weight = 1.0` (live weight is Ryan's after merge).

**Pipeline:**

```text
fuse (scores only; no final retrieval_rank)
  → apply_source_trust
  → truncate top_k
  → merge ledger priority
  → postfilters (#76)
  → final retrieval_rank 1..n
```

Ask evidence graph unchanged; trust only changes **admission/order**. Trace: `QueryUnitTrace.source_trust`. Compact/MCP traces may show boost when present — **never ordinary citations**.

**Code placement:** helpers only in `evidence.py`. Lazy-import from `query.py`. **No new leaf module** — #76 taught CI R0401 churn.

**Eval:** main → write `/tmp/p13-main-baseline.json` via `eval-retrieval.py --update-baseline`; branch compare against that. **Never** `--update-baseline` on the committed golden fixture.

---

## Do this

1. `git fetch &&` update `main` (must include #75/#76).
2. `convmem work start feat source-trust-ranking`
3. Implement Phases A–D in the EXECUTION plan.
4. Smoke: `convmem "ksweep-deploy"` — steering should beat chat. Index steering file if missing.
5. Open feat PR; push with explicit refspec; **do not merge**.

## Do not

- Invent `source_trust.py` / new ranking leaf module
- Put boosts on ordinary ask citations
- Sunset Crush routing in this PR
- Update committed golden baseline
- Force-push / merge `main`

**Tension to know:** older Codex/Kiro chat units argue for default weight **0.0** (opt-in). Cursor+Ryan locked plan uses example **1.0**. Prefer the locked EXECUTION / Ryan decision unless Ryan changes it.

---

## Acceptance (short)

- [ ] ksweep-class smoke: steering ≥ chat at top ranks
- [ ] omit-when-zero; final ranks after trust+postfilters
- [ ] no P@k regression vs `/tmp` main baseline; committed baseline untouched
- [ ] helpers in `evidence.py`; CI green
- [ ] feat PR open for Ryan

---

Copy the harbor map + locked design into your first Codex prompt, then run the four `convmem` searches so you load from shared memory instead of guessing.

**TL;DR:** Codex should start at LATEST → Codex handoff → EXECUTION twin, then implement source-trust in `evidence.py` from main after #75/#76; Ryan's stamp is `dec_prop_20260722_013340_dc60` and the written maps are PR #77 plus chat `4d0fbf93…`.


---

## Part 2 — Execution plan

# Execution Plan — P1.3 Source-Trust Ranking

```text
Planning Status

Phase:        EXECUTION plan ready (design locked; Codex implements)
Characters:   Cursor (plan + handoff) → Codex (implement) → Ryan (squash-merge) → Crush sunset follow-up
Lanes:        Codex implements; Cursor handoff only; Ryan merges; no Copilot audit unless Ryan asks
Authority:    Locked design in this plan + Codex handoff
Repo path:    docs/plans/EXECUTION-2026-07-21-source-trust-ranking.md
Handoff:      docs/inter-model/CURSOR-2026-07-21-p13-source-trust-codex-handoff.md
```

## Problem

Crush grepped the home folder for `#ksweep-deploy` because **retrieval ordered a stale chat distillation above real steering files**. Ritual/hooks were fine; the corpus ranked chat over `kiro_steering` / ledger / inter-model docs. P1.0a (#75) ingest and P1.1 (#76) postfilters shipped; Crush `ksweep-routing` is a temporary stopgap. P1.3 makes trusted sources win on ranking so that stopgap can sunset.

## Locked design (no mid-flight choice)

### Tiers (first match wins)

| Tier | Match | Additive tier value |
|------|--------|---------------------|
| Steering | `source_type == kiro_steering` **or** `source_path` contains `.kiro/steering/` | `0.15` |
| Ledger | `ledger_kind` in `{decision, observation, verification}` (or equivalent type fields) | `0.12` |
| Inter-model | `source_type == inter_model_doc` **or** path under `docs/inter-model/` | `0.08` |
| Chat / other | everything else | `0` |

`source_trust_boost = source_trust_weight * tier`  
Omit `source_trust_boost` from the hit dict when boost is `0` or trust is skipped — **do not emit `0` like `evidence_boost`**.

Default config: `[query] source_trust_weight = 1.0` in [`config.example.toml`](../../config.example.toml). Live `~/.config/convmem/config.toml` weight is **Ryan-owned** after merge.

**Strong calibration is intentional** (~10-position override vs live near-ties ~1.000 vs ~0.984).

### Score formula (search path)

After fusion:

```text
rank_score = rank_fusion_score + source_trust_boost
```

Ask evidence graph (`apply_evidence_rerank`) stays unchanged: it continues to use `rank_fusion_score` (+ evidence + recency). Trust affects **which units survive truncate / admission** into ask; it does not rewrite the evidence graph.

### Pipeline order in `query_units`

```text
… → CrossEncoder → fuse (scores only; no final retrieval_rank)
  → apply_source_trust (sort by rank_score)
  → truncate to top_k
  → merge ledger priority hits
  → postfilters (supersede + ledger dedupe; already on main via #76)
  → assign final retrieval_rank = 1..n
  → return
```

Change `_fuse_retrieval_ranks` so it **does not** assign lasting `retrieval_rank` (scores only). Final ranks are assigned once after trust + merge + postfilters.

### Code placement (CI lesson from #76)

- Put helpers in [`evidence.py`](../../evidence.py) only: `source_trust_tier`, `source_trust_boost`, `apply_source_trust`.
- **Do not** add `source_trust.py` or `query_result_filters.py` — new leaf modules churn pylint R0401 on Python 3.12.
- Wire from [`query.py`](../../query.py) with a **lazy import** (same pattern as `_apply_unit_result_postfilters`).
- Extend [`QueryUnitTrace`](../../query.py): `source_trust: list[dict] = field(default_factory=list)`.
- Ask / MCP compact traces: include `source_trust_boost` **conditionally** when present. **Never** put it on ordinary ask citations.

### Eval gate

Committed golden fixture must **not** be updated with `--update-baseline` unless Ryan explicitly authorizes.

Concrete procedure (tools today):

1. On `origin/main` tip (post-#75/#76):  
   `python scripts/eval-retrieval.py --baseline /tmp/p13-main-baseline.json --update-baseline`
2. On feature branch:  
   `python scripts/eval-retrieval.py --baseline /tmp/p13-main-baseline.json`  
   (fail on P@k regressions)
3. Diff stdout /tmp reports for **new P@1 / P@k flips** (improvements and regressions). Re-measure already-red main rows; do not hardcode review query names.
4. Optional small helper later: `--write-report` / `eval-compare` — not required if /tmp baselines + stdout diff are clear.

### Out of scope

- Crush `ksweep-routing` sunset (follow-up after P1.3 is live).
- P2 recurring negative-existence refine job.
- Changing evidence graph boost magnitudes.
- Forcing `ask` for every search.

## Stage 0 — prerequisites

1. Ritual: `convmem doctor` → `brief` → `unresolved`.
2. `git fetch origin && git switch main && git pull --ff-only` — tip must include #75 (`6feae58`) and #76 (`b4af44f`).
3. `convmem work start feat source-trust-ranking` (or resume). Single writer; `--worktree` if contested.
4. Smoke may need: `convmem index --file ~/.kiro/steering/ksweep-deploy.md` (or the actual deploy steering path) if steering units are missing from Chroma.
5. Confirm stale negative-existence unit remains forgotten (Ryan already ran `convmem forget` for that hash).

## Phase A — config + helpers

**Owner:** Codex.

1. Add `source_trust_weight = 1.0` under `[query]` in `config.example.toml` (and document in any adjacent comment briefly).
2. In `evidence.py`, implement tier / boost / `apply_source_trust` per locked table.
3. Unit tests in `tests/test_evidence_rerank.py` (or sibling): tier first-match, omit-when-zero, sort order, path `.kiro/steering/` without relying only on `source_type`.

## Phase B — wire `query_units`

**Owner:** Codex.

1. Fuse: scores only (no final `retrieval_rank`).
2. Apply trust; capture `retrieval_trace.source_trust` when trace present.
3. Truncate → merge → postfilters → final ranks.
4. Update ask compact row + MCP score fields: conditional `source_trust_boost` only.
5. Keep lazy imports; avoid twin wrappers (R0801).

## Phase C — eval + smoke

**Owner:** Codex.

1. Main-vs-branch golden gate (Stage procedure above). No committed baseline rewrite.
2. Live smoke: `convmem "ksweep-deploy"` / `search_fast` — steering / inter-model / ledger should outrank chat distillations for that class of query.
3. Ask with `--trace` (or equivalent): admission order reflects trust; evidence fields unchanged in meaning.
4. Full relevant unittest suite + pylint gate green.

## Phase D — ship

**Owner:** Codex opens PR; **Ryan** squash-merges.

1. Push with explicit refspec: `git push -u origin "$branch:refs/heads/$branch"`.
2. Open PR: user-facing title; body = problem / approach / tradeoffs (not commit list). Refs this EXECUTION + handoff.
3. Do **not** merge, force-push `main`, or set live `source_trust_weight` without Ryan.
4. After merge + live weight: separate follow-up to remove Crush `ksweep-routing` stopgap.

## Acceptance

- [ ] Steering hits for ksweep-class queries beat chat distillations at P@1 / top ranks in smoke.
- [ ] `source_trust_boost` omitted when zero; present in traces when non-zero.
- [ ] Final `retrieval_rank` assigned only after trust + postfilters.
- [ ] Golden: no P@k regression vs /tmp main baseline; committed baseline untouched.
- [ ] No new leaf ranking module; helpers live in `evidence.py`.
- [ ] PR open; Ryan merges.

## Related

- Incident chat: Cursor agent transcript `4d0fbf93-e1cb-4f47-99d2-0871231f5dbd`
- Merged: [#75](https://github.com/alanmz-crypto/convmem/pull/75) Kiro steering ingest; [#76](https://github.com/alanmz-crypto/convmem/pull/76) search postfilters
- Ledger relate (ksweep steering family): `dec_prop_20260707_014137_02d1`
- Fallback protocol anchor if needed: `dec_prop_20260623_161428_c311`

