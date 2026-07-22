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

