# Cursor VERIFY — P1.3 source-trust ranking

**Canonical:** [`../plans/VERIFY-source-trust-ranking.md`](../plans/VERIFY-source-trust-ranking.md)

**Mechanical verdict:** FAIL (V5 golden P@k regression). Stop: Await Ryan GATE.

**Subject:** PR #78 tip `aecf5d3285992f887991400ca813c6a2066345c1`

---

# Verify Plan — Source-Trust Ranking (P1.3)

```
Planning Status

Phase:        Verify (source-trust ranking / P1.3)
Characters:   Independent Reviewer, Test-First Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro or Ryan-named lane (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust Codex chat claims alone
```

**Subject / tip:** `aecf5d3285992f887991400ca813c6a2066345c1` on `feat/2026-07-21-source-trust-ranking`  
**PR(s):** Implementation [#78](https://github.com/alanmz-crypto/convmem/pull/78); docs/EXECUTION [#77](https://github.com/alanmz-crypto/convmem/pull/77) tip `b4853eff826aecd3575e889b27607ddc8384f3a7`  
**Base (eval/lint):** `b4af44f64fdc05c955857423ac42c364ee931111`  
**EXECUTION:** [`EXECUTION-2026-07-21-source-trust-ranking.md`](EXECUTION-2026-07-21-source-trust-ranking.md)  
**Decision authority:** `dec_prop_20260722_013340_dc60` (relates `dec_prop_20260707_014137_02d1`)  
**Goal:** Prove PR #78 implements the locked post-fusion source-trust policy without out-of-scope side effects.

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line of evidence.  
**GATE** = Ryan process step; not a mechanical agent PASS.

**Flow:** Complete **V0–V8** → Mechanical PASS|FAIL → independent sign-off → Ryan GATE.

**Checkout used for mechanical runs:** `/tmp/convmem-p13-source-trust-ranking` @ `aecf5d3…`  
**Base checkout for V5:** `/tmp/convmem-p13-base-b4af44f` @ `b4af44f…`  
**VERIFY author branch:** `docs/2026-07-21-p13-source-trust-handoff` (PR #77)

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Source tiers and first-match precedence | Changing tier magnitudes or default weight |
| Trust after fusion, before truncation | Evidence-graph boost magnitude changes |
| Final `retrieval_rank` after merge + postfilters | New ranking leaf modules / broad refactors |
| Conditional compact/MCP trust diagnostics | Trust fields on ordinary ask citations |
| Fixed-base `/tmp` golden compare + ksweep smoke | Updating committed golden fixture |
| Exact PR #78 tip + green checks | Live `~/.config/convmem/config.toml` mutation |
| Chat tier 0 without ledger identity | Crush `ksweep-routing` sunset or P2 refine |

---

## V0 — Preconditions and immutable subject

```bash
convmem doctor
convmem brief --stdout-only
convmem unresolved
gh pr view 78 --json headRefOid,baseRefOid,state,url
git -C /tmp/convmem-p13-source-trust-ranking rev-parse HEAD
```

| ID | Check | PASS |
|----|-------|------|
| V0a | Ritual healthy | **PASS** — doctor exit 0 (1 non-fatal warning); brief @ 2026-07-22T03:35:33Z; 11 unresolved (pre-existing staging2/tooling) |
| V0b | PR #78 open vs main | **PASS** — state OPEN; url https://github.com/alanmz-crypto/convmem/pull/78 |
| V0c | Head SHA exact | **PASS** — `aecf5d3285992f887991400ca813c6a2066345c1` |
| V0d | Base SHA exact | **PASS** — `b4af44f64fdc05c955857423ac42c364ee931111` |
| V0e | Worktree pinned | **PASS** — `/tmp/convmem-p13-source-trust-ranking` clean at head |
| V0f | GitHub checks | **PASS** — `pylint (3.12)` pass (5m34s) on tip; later tip invalidates this row |

---

## V1 — Tier policy and omission contract

| ID | Check | PASS |
|----|-------|------|
| V1a | Steering 0.15 | **PASS** — `source_trust_tier` first branch; smoke hit boost=`0.15` for `kiro_steering` / `.kiro/steering/ksweep-deploy.md` |
| V1b | Ledger 0.12 | **PASS** — code + focused unit tests (`tests/test_evidence_rerank.py`) |
| V1c | Inter-model 0.08 | **PASS** — code + smoke rows with `inter_model_doc` boost=`0.08` |
| V1d | Chat/other 0; chat decision without ledger stays 0 | **PASS** — tier returns 0.0; unit tests; chat smoke rows omit boost |
| V1e | First-match ordering | **PASS** — steering before ledger/inter-model in `source_trust_tier` |
| V1f | Omit-when-zero | **PASS** — `apply_source_trust` pops key unless `boost > 0`; unit tests |

---

## V2 — Pipeline order and score authority

```text
CrossEncoder → score-only fusion → source trust → truncate top_k
  → merge ledger-priority → postfilters → final retrieval_rank 1..n
```

| ID | Check | PASS |
|----|-------|------|
| V2a | Order in `query_units` | **PASS** — fuse → `_apply_unit_source_trust` → `[:top_k]` → merge → postfilters → assign ranks (`query.py` ~475–496) |
| V2b | Fuse does not assign lasting `retrieval_rank` | **PASS** — `_fuse_retrieval_ranks` returns scores only (no rank loop) |
| V2c | Trust sees full fused pool | **PASS** — trust applied before `results[:top_k]` |
| V2d | Contiguous final ranks after filters | **PASS** — smoke ranks `[1..8]` |
| V2e | Evidence graph still uses `rank_fusion_score` | **PASS** — `apply_evidence_rerank` docstring/formula unchanged; bases on `rank_fusion_score` |

---

## V3 — Trace and citation boundaries

| ID | Check | PASS |
|----|-------|------|
| V3a | `QueryUnitTrace.source_trust` | **PASS** — field present; smoke `len(trace.source_trust)==20` |
| V3b | Compact/MCP conditional boost | **PASS** — `ask._compact_trace_row` / `mcp_server` only if key in result |
| V3c | Ordinary citations lack boost | **PASS** — `_format_context` has no `source_trust`; citation builders do not copy boost |
| V3d | Raw-mode trust skipped | **PASS** — `stages["source_trust"] = _skipped_stage("raw_mode")` |

---

## V4 — Code placement, tests, pylint

| ID | Check | PASS |
|----|-------|------|
| V4a | Helpers in `evidence.py` only | **PASS** — `source_trust_tier` / `source_trust_boost` / `apply_source_trust` |
| V4b | No new leaf ranking module | **PASS** — no `source_trust.py` / `query_result_filters.py` at tip |
| V4c | `config.example.toml` weight 1.0 | **PASS** — `source_trust_weight = 1.0` |
| V4d | Live config untouched | **PASS** — `~/.config/convmem/config.toml` mtime 2026-07-19; no verify writes |
| V4e | Focused pytest | **PASS** — 39 passed, 8 subtests, exit 0 (`/tmp/p13-v4-focused.txt`) |
| V4f | Full pytest | **PASS** — 756 passed, 99 subtests, exit 0 in 142.51s (`/tmp/p13-v4-full.txt`) |
| V4g | Pylint regression vs base | **PASS** — GitHub `pylint (3.12)` PASS; local gate: `Pylint regression gate PASS (520 findings, 275 fingerprints; no new/increased vs baseline)` with `--pylint-status 30` vs base `b4af44f…` (`/tmp/p13-pylint-gate.txt`) |

---

## V5 — Fixed-base retrieval evaluation

```bash
# base
cd /tmp/convmem-p13-base-b4af44f
python scripts/eval-retrieval.py --baseline /tmp/p13-main-baseline.json --update-baseline
# tip
cd /tmp/convmem-p13-source-trust-ranking
python scripts/eval-retrieval.py --baseline /tmp/p13-main-baseline.json
# fixture identity
sha256sum tests/fixtures/golden_queries_baseline.json  # both trees
```

| ID | Check | PASS |
|----|-------|------|
| V5a | `/tmp` baseline from base only | **PASS** — wrote `/tmp/p13-main-baseline.json` from `b4af44f…` |
| V5b | Tip vs `/tmp` baseline no new P@k regression | **FAIL** — exit 1; new miss: `Global convmem protocol soak close` (base rank=1 → tip none). Metrics tip P@1 62.5% / P@k 75.0% / MRR 0.6875 vs base P@1 75.0% / P@k 87.5% / MRR 0.7750 (`/tmp/p13-v5-tip2.txt`) |
| V5c | Committed golden baseline byte-unchanged | **PASS** — sha256 `177731d7583d359682f30baad5f6c09c3ae77271279ecf1f427cbd6281f49648` identical tip vs base |
| V5d | Already-red rows re-measured | **PASS** — `Arch Linux health prompt matrix` FAIL on both base and tip (not a new regression) |

**Flips (orientation):** Crush Tier A improved tip rank 5→2; soak-close newly missed at tip. Corpus may differ from Codex’s earlier session numbers — Cursor evidence is authoritative for this run.

---

## V6 — Incident-specific ksweep smoke

| ID | Check | PASS |
|----|-------|------|
| V6a | Steering ahead of chat with +0.15 | **PASS** — rank 1 `…/willowyhollow-dev/.kiro/steering/ksweep-deploy.md`, boost=0.15; first chat-like row rank 2 with boost omitted |
| V6b | Ordinary chat rows omit boost | **PASS** — transcript/session rows show `<omit>` |
| V6c | Contiguous final ranks | **PASS** — `[1..8]` |
| V6d | No corpus mutate to force PASS | **PASS** — query only; no `index`/`forget` during verify |

---

## V7 — Isolation and negative assertions

| ID | Check | PASS |
|----|-------|------|
| V7a | No committed golden update | **PASS** — fixture hash unchanged; no `--update-baseline` on committed path |
| V7b | No live config write | **PASS** — mtime unchanged during verify |
| V7c | No evidence-boost magnitude change | **PASS** — `_BOOST_*` / `_PENALTY_*` / `_BOOST_DECISION=0.02` unchanged vs base |
| V7d | No ordinary-citation schema change for trust | **PASS** — citations via `_format_context` without `source_trust` |
| V7e | No Crush routing sunset in #78 | **PASS** — no crush paths in `git diff --name-only b4af44f...HEAD` |
| V7f | Verifier made no implementation fixes | **PASS** — #78 worktree clean; only VERIFY docs on #77 |

---

## V8 — Independent sign-off and Ryan GATE

| ID | Check | PASS |
|----|-------|------|
| V8a | Request same-SHA independent PASS/FAIL | **PENDING** — request Kiro (or Ryan-named lane) against tip `aecf5d3285992f887991400ca813c6a2066345c1` |
| V8b | Independent verifier performs no cleanup | **n/a until sign-off** |
| V8c | Cursor does not self-sign / merge / record / close arc | **PASS** — this artifact stops at Await Ryan GATE |

### Independent sign-off slot

```text
Lane: _______________
Artifact: PR #78 tip aecf5d3285992f887991400ca813c6a2066345c1
Verdict: PASS | FAIL
Rationale (one line):
Residuals:
Date (ISO-8601):
```

---

## Evidence log

```text
VERIFY-source-trust-ranking — tip aecf5d3285992f887991400ca813c6a2066345c1 — runner cursor — 2026-07-22T03:40:00Z
V0: PASS (doctor/brief/unresolved; PR78 OPEN; tip+base pinned; GH pylint PASS)
V1: PASS (tiers/omit/first-match; focused tests + smoke)
V2: PASS (pipeline order; fuse scores-only; evidence base unchanged)
V3: PASS (trace/MCP/citations/raw skip)
V4: PASS (evidence.py helpers; 39+8 focused; 756+99 full; GH+local pylint gate PASS vs b4af44f)
V5: FAIL (new P@k regression: Global convmem protocol soak close; tip P@k 75% vs base 87.5%; committed baseline untouched)
V6: PASS (ksweep-deploy steering P@1 +0.15; chat omit; ranks contiguous)
V7: PASS (isolation negatives)
V8: PENDING independent sign-off
Mechanical: FAIL
Sign-off: pending (Kiro or Ryan-named lane, same SHA)
Stop: Await Ryan GATE
```

---

## Mechanical verdict

**FAIL** — V5 fixed-base golden comparison shows a new P@k regression at tip `aecf5d3…` versus `/tmp` baseline from `b4af44f…`. No implementation fix attempted by Cursor.

Ryan GATE owns whether to merge #78/#77, require a tip revision, or waive/retarget golden expectations.

**Stop: Await Ryan GATE**
