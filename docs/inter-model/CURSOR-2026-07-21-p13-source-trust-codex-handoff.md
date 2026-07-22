# Cursor → Codex: P1.3 source-trust ranking

**To:** Codex (implement)  
**From:** Cursor  
**Date:** 2026-07-21  
**Status:** Design locked — execute from `origin/main` after #75/#76  
**Branch to start:** `convmem work start feat source-trust-ranking`  
**Canonical plan:** [`../plans/EXECUTION-2026-07-21-source-trust-ranking.md`](../plans/EXECUTION-2026-07-21-source-trust-ranking.md)

**Live ops:** implement + open PR only. Ryan squash-merges. Do not change live `source_trust_weight` without Ryan. Do not sunset Crush routing in this PR.

---

## Why this exists

Crush grepped `~` for `#ksweep-deploy` because search ranked a stale chat unit (“no standalone ksweep file”) above real files under `.kiro/steering/`. Ingest (#75) and postfilters (#76) are on main; ranking still needs **source-trust boosts** so trusted docs beat chat distillations.

## Done already (do not redo)

| Item | Where |
|------|--------|
| Ritual-first `global_context_paths` | live |
| Crush `ksweep-routing` stopgap | live — **leave until after P1.3** |
| `convmem forget` + Chroma undo fix | live |
| Tombstone stale negative-existence unit | Ryan ran `forget` |
| Kiro steering ingest | **#75** merged `6feae58` |
| Decision supersede + ledger dedupe on `query_units` | **#76** merged `b4af44f` |

## Chat-only deltas Codex must not rediscover the hard way

1. **Extend [`evidence.py`](../../evidence.py) only.** A new leaf module (e.g. `query_result_filters.py` / `source_trust.py`) bumped CI Python 3.12 **R0401** 12→13 during #76. Move helpers into `evidence.py`; lazy-import from `query.py`.
2. **Live near-ties** (~1.000 vs ~0.984) motivate strong tiers (**+0.15** steering). Calibration is intentional, not a bug.
3. Smoke may need `convmem index --file …/ksweep-deploy.md` (steering path) if Chroma lacks the unit.
4. Re-measure **already-red** main golden rows; do not hardcode reviewer query names as the only gate.
5. **Never** `--update-baseline` on the committed golden fixture. Use `/tmp/…` baselines for main-vs-branch compare (see EXECUTION).
6. **No** `source_trust_boost` on ordinary ask citations — compact/MCP/ask **trace** only, and only when present.
7. Fuse assigns **scores only**; **final `retrieval_rank`** after trust → truncate → merge → postfilters.
8. Ask evidence graph (`apply_evidence_rerank`) **unchanged**; trust changes admission ordering into ask.

## Locked tiers (first match)

1. `kiro_steering` / path `.kiro/steering/` → **0.15**
2. ledger decision/observation/verification → **0.12**
3. `inter_model_doc` / `docs/inter-model/` → **0.08**
4. chat/other → **0**

`source_trust_boost = weight * tier` — **omit field when 0**.  
`rank_score = rank_fusion_score + source_trust_boost` after trust.  
Config: `[query] source_trust_weight = 1.0` in example toml.

## Pipeline

```text
fuse (no final rank) → trust → truncate → merge → postfilters → retrieval_rank 1..n
```

Trace: `QueryUnitTrace.source_trust: list[dict]`.

## Test checklist

- Unit: tier first-match; omit-when-zero; path-based steering match
- `python scripts/eval-retrieval.py` main→`/tmp` baseline, then branch vs that baseline
- Smoke: `convmem "ksweep-deploy"` prefers steering over chat
- Ask `--trace`: boost in compact stage rows when non-zero; citations clean
- Pylint / CI green; no new ranking leaf module
- Open PR; **do not merge**

## Search strings for shared memory

Codex should start with:

```bash
convmem doctor
convmem brief --stdout-only
convmem "P1.3 source-trust ranking Codex handoff"
convmem "EXECUTION source-trust ranking"
```

Indexed targets after Cursor lands this docs PR (or indexes locally):

- `docs/plans/EXECUTION-2026-07-21-source-trust-ranking.md`
- `docs/inter-model/CURSOR-2026-07-21-p13-source-trust-codex-handoff.md`
- `docs/inter-model/LATEST.md` (active pointer)
- Cursor chat: `…/agent-transcripts/4d0fbf93-e1cb-4f47-99d2-0871231f5dbd/…jsonl`

## Relates-to for Ryan record

`dec_prop_20260707_014137_02d1` (ksweep steering family). Fallback: `dec_prop_20260623_161428_c311`.

## Ask

- **Codex:** implement Phases A–D of the EXECUTION plan; open PR; stop at merge.
- **Ryan:** merge; set live weight if needed; later authorize Crush routing sunset + P2 refine.
- **Cursor:** handoff complete — no further P1.3 implementation in this lane unless Ryan reassigns.

## TL;DR

Codex: from main after #75/#76, add source-trust boosts in `evidence.py`, wire fuse→trust→final ranks, gate with /tmp golden compare, open PR — do not invent a new module or update the committed baseline.
