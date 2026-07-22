# Verify Plan — Retrieval Reliability (PR #55)

```
Planning Status

Phase:        Verify (retrieval reliability — reusable gate)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical re-run); Kiro (AC / sign-off); Ryan (merge + escalate)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Subject:** `feat/2026-07-19-retrieval-reliability`  
**Tip:** `027f29b8910402358b1052e7f9f7d4655c36da08` (`feat: finalize retrieval reliability milestone`)  
**PR:** https://github.com/alanmz-crypto/convmem/pull/55  
**Base:** `origin/main`  
**Sources:** PR #55 Validation block; `scripts/eval-retrieval.py`; `scripts/pylint_regression_gate.py`; [`CODEX-DEEPSEEK-VERIFY.md`](../CODEX-DEEPSEEK-VERIFY.md) evidence style  
**Goal:** Confirm mandatory reranking, full ranking-field exposure, ingest exact-suppress + semantic queue, golden-eval stability, and pylint regression cleanliness — without expanding scope into unrelated retrieval tuning.

**Report format:** For each check, state **PASS / FAIL / SKIP** and one line of evidence (exit code, command output snippet, or artifact path).  
**GATE** = process step for Ryan (merge); not a mechanical agent PASS.

**Flow:** Complete **V0–V6** → declare **Mechanical PASS|FAIL** → Kiro **sign-off** (separate) → Ryan **merge GATE**. Do not fold sign-off into the mechanical verdict.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| Mandatory CrossEncoder rerank (legacy `query.rerank` ignored) | New ranking signals / weight tuning beyond shipped defaults |
| Ask-trace + MCP exposure of the 7 ranking fields | Client WordPress / staging2 work |
| Ingest exact suppress + audit JSONL; semantic queue (never auto-suppress) | Bulk reindex / `rm processed.json` |
| Golden eval: no per-query `p_at_k` regression vs baseline | `--update-baseline` during verify |
| Pylint regression gate vs PR base | Raising baseline without Ryan approval |

---

## Ranking fields (canonical set of 7)

Required on each ask compact unit row and MCP search payload hit:

1. `semantic_rank`
2. `pre_rerank_rank`
3. `rerank_score`
4. `rerank_score_norm`
5. `rerank_rank`
6. `rank_fusion_score`
7. `retrieval_rank`

---

## 0. Preconditions — branch / PR scope (V0)

```bash
cd ~/Projects/convmem
# Prefer worktree if branch already checked out elsewhere:
#   /home/lauer/.local/share/convmem/worktrees/feat-2026-07-19-retrieval-reliability
git fetch origin
git rev-parse HEAD
git log origin/main..HEAD --oneline
git diff --stat origin/main...HEAD
gh pr view 55 --json url,headRefName,baseRefName,state,mergeable
```

| ID | Check | PASS |
|----|-------|------|
| V0a | On PR head branch | `feat/2026-07-19-retrieval-reliability` |
| V0b | Tip lineage | Includes finalize tip `027f29b` (or later tip on same branch) |
| V0c | Three feat commits present | mandatory rerank; ingest dedupe; finalize |
| V0d | PR metadata | head/base match; state OPEN or MERGED as appropriate; `gh pr view 55` |
| V0e | Diff scope | Rerank/query/ask/mcp + `ingest_dedupe.py` + listed tests; no client WP paths |

---

## 1. Targeted pytest (V1)

```bash
python -m pytest -q \
  tests/test_ingest_dedupe.py \
  tests/test_refine.py \
  tests/test_eval_corpus_gate1_correction.py \
  tests/test_eval_corpus_phase_a.py \
  tests/test_eval_corpus_phase_a_complete.py \
  tests/test_rerank_contract.py \
  tests/test_ask_trace.py \
  tests/test_evidence_rerank.py \
  tests/test_mcp_rerank_scores.py \
  tests/test_query_recency.py \
  tests/test_query_ledger_lookup.py \
  tests/test_exclude_source_purge.py
echo "pytest exit: $?"
```

**PASS:** exit `0`.

Core smoke (not a substitute for pre-merge full list):

```bash
python -m pytest -q \
  tests/test_rerank_contract.py \
  tests/test_ask_trace.py \
  tests/test_mcp_rerank_scores.py \
  tests/test_ingest_dedupe.py \
  tests/test_evidence_rerank.py
```

---

## 2. Golden eval gate (V2)

```bash
python scripts/eval-retrieval.py
echo "eval-retrieval exit: $?"
```

**PASS (explicit thresholds):**

- Exit code `0`
- Stdout contains `No regression vs baseline.`
- Meaning: every golden query that had `p_at_k: true` in `tests/fixtures/golden_queries_baseline.json` still has `p_at_k: true` (acceptable ledger id within that row’s `top_k`). Losing a previously-passing hit → exit `1` / `REGRESSION vs baseline:` → **FAIL**.
- Do **not** treat `[eval] retrieval_p_at_1_min` as this script’s exit gate.
- Baseline aggregates are informational only (recorded: `p_at_1=0.75`, `p_at_k=1.0`, `mrr=0.875`).
- Never run `--update-baseline` during verify.

---

## 3. Pylint regression gate (V3)

```bash
set +e
pylint $(git ls-files "*.py") --output-format=json > /tmp/pylint-report-pr55.json
st=$?
set -e
python scripts/pylint_regression_gate.py ci \
  --report /tmp/pylint-report-pr55.json \
  --pylint-status "$st" \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref "$(git merge-base HEAD origin/main)"
```

**PASS:** prints `Pylint regression gate PASS` (no new/increased fingerprints vs base; no fatal/usage bits).

Also confirm GitHub: `gh pr checks 55` → `pylint (3.12)` success before merge.

**Known tip status (2026-07-20):** CI run [29709937574](https://github.com/alanmz-crypto/convmem/actions/runs/29709937574/job/88252387046) reported `+1 R0401/cyclic-import` (12→13). Treat unresolved R0401 growth as a **merge blocker** until fixed or Ryan-approved baseline update.

---

## 4. Runtime — mandatory rerank despite legacy flag (V4)

```bash
# Mechanical (no GPU required)
python -m pytest -q tests/test_rerank_contract.py::MandatoryRerankQueryTests -v

# Live: prod config may still show brief `rerank: False` — that is the case under test
# Prefer PR tip code if main checkout is on another branch:
#   PY=$HOME/miniforge3/envs/convmem/bin/python
#   WT=.../worktrees/feat-2026-07-19-retrieval-reliability
#   "$PY" "$WT/convmem.py" ask --trace "..." > /tmp/ask-trace-pr55.out 2>/tmp/ask-rerank.err
convmem ask --trace "Global convmem protocol soak close" \
  > /tmp/ask-trace-pr55.out 2>/tmp/ask-rerank.err
# Trace JSON is on stderr for this CLI; answer text is on stdout
rg -n 'rerank_score|rerank_rank' /tmp/ask-rerank.err | head
# stderr may also show CrossEncoder load or CUDA→CPU fallback
```

**PASS:**

- `MandatoryRerankQueryTests` exit `0` (`query.rerank=False` still calls rerank)
- Live ask/trace shows non-null `rerank_score` / `rerank_rank` on `origin=unit` hits (or SKIP live if DeepSeek/network unavailable — still require unit test PASS). Injected/non-unit rows may have null ranking fields.

Code anchor: `query_units` always calls `rerank.rerank` except eval `rerank_mode == "identity"`.

---

## 5. Runtime — all 7 ranking fields (V5)

```bash
python -m pytest -q tests/test_mcp_rerank_scores.py tests/test_ask_trace.py -q
echo "field-tests exit: $?"

# Optional live assert against ask --trace output
python - <<'PY'
import json, re, sys
from pathlib import Path
text = Path("/tmp/ask-trace-pr55.out").read_text(encoding="utf-8", errors="replace")
required = {
    "semantic_rank", "pre_rerank_rank", "rerank_score", "rerank_score_norm",
    "rerank_rank", "rank_fusion_score", "retrieval_rank",
}
missing = sorted(k for k in required if k not in text)
print("missing_from_trace_text:", missing or "none")
sys.exit(1 if missing else 0)
PY
```

**PASS:** pytest exit `0`; live text/JSON includes all 7 keys (or SKIP live if V4 live was SKIP — unit/MCP tests still required).

---

## 6. Runtime — ingest exact suppress + semantic queue (V6)

```bash
python -m pytest -q tests/test_ingest_dedupe.py -v
echo "ingest-dedupe exit: $?"

# Live artifacts (sibling of chroma_dir parent; typically ~/.local/share/convmem/)
# After a verbose ingest that hits duplicates, expect log lines:
#   [dedupe] exact {id8} = {id8} (suppressed)
#   [dedupe?] {sim:.3f} {id8} ~ {id8} (queued)
ls -la ~/.local/share/convmem/ingest_duplicate_suppressions.jsonl \
       ~/.local/share/convmem/dedupe_queue.jsonl 2>/dev/null || true
```

Config (`[ingest_dedup]` in `config.example.toml`):

| Key | Default | Role |
|-----|---------|------|
| `semantic_similarity` | `0.92` | Near-dupe queue threshold |
| `candidate_k` | `10` | Neighbor fetch from store |
| `max_semantic_candidates_per_unit` | `3` | Cap queued pairs per new unit |

**PASS:**

- `tests/test_ingest_dedupe.py` exit `0`
- Exact: suppressed (not indexed) + audit row (`suppressed_id`, `matched_id`, `content_hash`, `source_path`, `suppressed_at`)
- Semantic: still indexed; queue row `status=pending`, `source=ingest` — never auto-suppressed

Live JSONL presence alone is informational if no new ingest was run this session.

---

## 7. Post-merge monitoring (24–48h) — V7

| Watch item | Failure signal | Owner | Response path |
|------------|----------------|-------|---------------|
| Golden eval drift | `eval-retrieval.py` exit ≠ 0 / `REGRESSION vs baseline` | Cursor run; Kiro confirm | Open `fix/`; do not `--update-baseline` without Ryan |
| Rerank latency / OOM | ask/search slow; Watch RSS near MemoryMax; CUDA OOM → CPU thrash | Cursor triage; Ryan if service impact | Handoff note; candidate_k / model follow-up |
| Ingest dedupe noise | Spike in suppressions JSONL or `dedupe_queue.jsonl` | Cursor measure; Kiro review semantics | Fix false exact suppress; tune threshold / open F2 |
| Pylint CI green | New fingerprint on main CI | Cursor | Block related PRs until gate green |
| MCP field regressions | MCP search missing any of 7 fields | Kiro AC re-check | Hotfix or revert |

**Rollback / escalate triggers (Ryan):**

- Golden eval regression on `main` after merge
- Exact-dupe suppress removing intended distinct units
- Production ask/MCP unavailable or systematically empty rerank fields

**Escalation path:** Cursor files evidence → Kiro confirms AC break → Ryan decides revert vs targeted hotfix.

---

## 8. Evidence template

Header for a completed run:

```
VERIFY-retrieval-reliability — tip <sha> — runner <lane> — <ISO-8601>
Mechanical: PASS|FAIL
Sign-off: PASS|FAIL|PENDING (Kiro)
Merge GATE: Ryan
```

Checklist (fill Actual / Verdict / Artifact per run):

| ID | Command | Expected | Actual | Verdict | Artifact |
|----|---------|----------|--------|---------|----------|
| V0 | `git log` / `gh pr view 55` | tip lineage; PR head/base OK | | | oneline + URL |
| V1 | full pytest list above | exit 0 | | | terminal snippet |
| V2 | `python scripts/eval-retrieval.py` | exit 0; `No regression vs baseline.` | | | `/tmp/eval-retrieval-pr55.log` |
| V3 | `pylint_regression_gate.py ci` | `Pylint regression gate PASS` | | | `/tmp/pylint-report-pr55.json` |
| V4 | `MandatoryRerankQueryTests` + `ask --trace` | rerank called; scores non-null | | | `/tmp/ask-trace-pr55.out` |
| V5 | 7-field assert + MCP/ask tests | all 7 keys present | | | field dump |
| V6 | `test_ingest_dedupe` (+ jsonl tails) | exact audit + semantic pending | | | suppression/queue paths |
| V7 | 24–48h watch notes | no escalate triggers | | | date + owner |

---

## 9. Non-blocking follow-ups

**F1 — Operator / changelog note:** Legacy `query.rerank` is ignored. CrossEncoder rerank is always on (except eval `rerank_mode=identity`). `brief` may still display `rerank: False` from config — that does **not** disable reranking. Add/keep an operator-facing note so ops do not try to “turn off” rerank via the dead key.

**F2 — Ingest scale watch:** Design does one Chroma neighbor read per unit in a batch (`candidate_k`). Open a perf follow-up when batch ingest wall time grows ~linear with corpus size in a way that blocks watch/index SLOs, or when dedupe phase dominates ingest. Not a merge blocker.

---

## Evidence log — Cursor mechanical run 2026-07-20

```
VERIFY-retrieval-reliability — tip 027f29b8910402358b1052e7f9f7d4655c36da08 — runner Cursor — 2026-07-20T02:30Z
Mechanical: PASS (local). Note: GitHub pylint check on PR was FAIL earlier; local gate PASS on same tip — re-run CI before merge.
Sign-off: PENDING (Kiro — prior AC claim stands; confirm after CI pylint green)
Merge GATE: Ryan (blocked until GitHub pylint (3.12) green or Ryan waives)
```

| ID | Command | Expected | Actual | Verdict | Artifact |
|----|---------|----------|--------|---------|----------|
| V0 | `git log` / `gh pr view 55` | tip `027f29b`; PR head/base OK | tip `027f29b`; 3 commits; head `feat/2026-07-19-retrieval-reliability`; MERGEABLE; scope matches rerank+dedupe files | PASS | `/tmp/v0-scope-pr55.log` |
| V1 | full targeted pytest | exit 0 | `119 passed, 19 subtests passed in 33.63s` | PASS | `/tmp/pytest-pr55.log` |
| V2 | `python scripts/eval-retrieval.py` | exit 0; `No regression vs baseline.` | exit 0; P@1 87.5% P@k 100% MRR 0.9062; `No regression vs baseline.` | PASS | `/tmp/eval-retrieval-pr55.log` |
| V3 | `pylint_regression_gate.py ci` | `Pylint regression gate PASS` | Local: PASS (519 findings, 275 fingerprints). GitHub Actions run 29709937574: FAIL `+1 R0401` — treat CI as merge gate until re-run green | PASS local / FAIL CI (pending re-run) | `/tmp/pylint-gate-pr55.log`, `/tmp/pylint-report-pr55.json` |
| V4 | `MandatoryRerankQueryTests` + live ask | rerank despite `query.rerank=false` | Unit exit 0; live config `rerank = false`; ask exit 0 with non-null `rerank_score`/`rerank_rank` in trace | PASS | `/tmp/v4-mandatory-rerank.log`, `/tmp/ask-rerank.err` |
| V5 | 7-field assert | all 7 keys present | Keys present on all hit rows; **13** `origin=unit` hits with all 7 non-null (sample `retrieval_rank=1`, `rerank_score≈0.98`); injected/non-reranked rows may be null — expected; MCP/ask tests exit 0 | PASS | `/tmp/ask-rerank.err`, `/tmp/v5-v6-tests.log` |
| V6 | `test_ingest_dedupe` | exact audit + semantic queue policy | pytest exit 0; `dedupe_queue.jsonl` present; `ingest_duplicate_suppressions.jsonl` absent (no live exact suppress yet this session) | PASS (tests); live suppressions SKIP | `/tmp/v5-v6-tests.log` |
| V7 | 24–48h watch | N/A pre-merge | Not started | SKIP | post-merge |

**Mechanical verdict:** PASS on V0–V2, V4–V6 (local). **Merge GATE:** hold for GitHub `pylint (3.12)` green (re-run recommended; local gate already PASS on tip `027f29b`).

For future re-runs, append a new dated Evidence log block rather than overwriting history.

---

## Evidence log — Cursor V7 post-merge 2026-07-22

```
VERIFY-retrieval-reliability — main tip dba9795 (post #55/#56; includes #86) — runner Cursor — 2026-07-22T17:57Z
V7 overall: FAIL (golden eval escalate trigger)
Sign-off: PENDING (Kiro confirm on golden regression)
Owner next: Cursor opens fix/ for golden retrieval; do not --update-baseline
Steward checkout left untouched (docs/2026-07-22-2026-07-22-pr-steward-prompt)
```

| ID | Command | Expected | Actual | Verdict | Artifact |
|----|---------|----------|--------|---------|----------|
| V7a | `python scripts/eval-retrieval.py` | exit 0; `No regression vs baseline.` | exit **1**; `REGRESSION vs baseline` on 2 queries: `Global convmem protocol soak close`, `Arch Linux health prompt matrix`; P@1 62.5% P@k 75% MRR 0.6875 (pre-merge V2 was P@1 87.5% P@k 100%) | **FAIL** — escalate | `/tmp/v7-eval-retrieval2.log` |
| V7b | ask `--trace` 7 ranking fields | unit hits have all 7 non-null | ask exit 0; **4** `origin=unit` hits with all 7 non-null despite live `query.rerank=false` | PASS | `/tmp/v7-ask.err` |
| V7c | dedupe artifacts | no pending flood / suppressions sane | `dedupe_queue.jsonl` 1186 lines, **0 pending**, 0 `source=ingest` (ingest semantic queue paused via #86); suppressions JSONL 265 lines present | PASS (no pending flood) | `/tmp/v7-dedupe-sizes.log` |
| V7d | MCP/ask availability | not systematically empty rerank | scores present on unit hits | PASS | `/tmp/v7-ask.err` |
| V7e | Rollback triggers | none of: empty fields, exact-suppress wrong units, ask down | Only golden eval regression fired | FAIL limited to V7a | this block |

**V7 escalate path (per plan):** Cursor files evidence (this block) → Kiro confirms AC break on golden → Ryan decides revert vs targeted `fix/` (prefer fix golden retrieval; do **not** run `--update-baseline` without Ryan).

**Note:** #85/#86 semantic-dedupe hygiene is a separate follow-on arc that paused ingest queue growth; it is not a rollback of #55 mandatory rerank / field exposure.
