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
