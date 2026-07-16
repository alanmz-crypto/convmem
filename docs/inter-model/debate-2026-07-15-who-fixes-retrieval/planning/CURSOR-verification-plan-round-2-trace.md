# CURSOR — Verification plan: Round 2 ask(trace) (corrected tip)

**Date:** 2026-07-16
**From:** Cursor
**Status:** **MERGE-READY** — Kiro + R1 confirmed on `43b5f33`; GitHub Pylint green. Ryan merges.
**PR:** [PR #35](https://github.com/alanmz-crypto/convmem/pull/35) (`fix/2026-07-15-ask-trace` @ `43b5f33`)
**Supersedes:** first-round checklist on `503add7` (ChatGPT REQUEST CHANGES)

---

## Work log (Cursor)

| Step | Result |
|---|---|
| Tip `503add7` | ChatGPT REQUEST CHANGES: `[1][1][1]` numbering, empty-shape regression, red Pylint |
| §§1–4 executed | Numbering via `_format_context(..., start_n=)` / `_format_context_item`; empty return = main keys only (+ `trace` when enabled); Pylint gate green without baseline bless (normalize `(#/#)` / `(line #)` in gate); strengthened tests |
| New tip | `43b5f33` (`43b5f33eea85f4b01ea1db9da921257965c6524d`) pushed to `fix/2026-07-15-ask-trace` |
| Local verify | focused + full suite + doctor + Pylint regression gate PASS; Round 1 self-check OK |
| Prior partner verdicts on `503add7` | **Superseded** — re-confirm this tip only |

**MERGEABLE ≠ checks green.** Require GitHub Actions **Pylint regression gate** green on `43b5f33`.

---

## Pre-push self-check (acceptance item 8 — paste evidence)

```bash
git fetch origin fix/2026-07-15-ask-trace main
git rev-parse origin/fix/2026-07-15-ask-trace
# expect: 43b5f33eea85f4b01ea1db9da921257965c6524d

rg -n 'max\(1, total_limit // 3\)' ask.py
rg -n 'with ChromaStore' ask.py
git diff origin/main...origin/fix/2026-07-15-ask-trace -- tests/test_ledger_recent.py
# expect: empty
```

Cursor recorded: formula @ ask.py:212; `with ChromaStore` present; ledger tests unchanged vs main.

---

## A — Tip and Round 1

| # | Check | PASS |
|---|---|---|
| A1 | Tip SHA `43b5f33`… | |
| A2 | Minority cap formula | |
| A3 | `with ChromaStore` | |
| A4 | `test_ledger_recent.py` empty diff vs main | |
| A5 | `_EXCLUDE_PATH_TOKENS` present | |

## B — Contract + ChatGPT regression tests

```bash
python3 -m unittest tests.test_ask_trace -v
```

| # | Check | PASS |
|---|---|---|
| B1 | `trace=False` omits `trace` | |
| B2 | Schema `convmem.ask.trace.v1` | |
| B3 | Five stages | |
| B4 | Skipped `{status, reason, items:[]}` | |
| B5 | A1 bounds + **final_context prefix when truncated** | |
| B6 | A2 `context_delivery` **e2e via ask()** | |
| B7 | Dedupe: `ledger_deduped.items_total < evidence_reranked.items_total` | |
| B8 | Admitted-recent edges (overlap / cap / domain) | |
| B9 | No document bodies | |
| B10 | Three paths | |
| B11 | **Prompt parity** + excerpt headers `[1] (` / `[2] (` / `[3] (` | |
| B12 | **Empty shape** exact main keys; `trace=True` adds only `trace` | |
| B13 | **CLI `--trace`** stderr JSON | |

## C — Suites (focused always green)

```bash
python3 -m unittest tests.test_ledger_recent tests.test_ask_trace -v
python3 -m unittest discover -s tests -q
python3 convmem.py doctor
```

| # | Check | PASS |
|---|---|---|
| C1 | Focused — **must** be green (no baseline loophole) | |
| C2 | Full discover — green or zero new vs baseline `48e816f` | |
| C3 | Doctor exit 0 | |

## G — Pylint regression gate (required)

```bash
set +e
pylint $(git ls-files "*.py") --output-format=json > pylint-report.json
PYLINT_STATUS=$?
set -e
BASE_REF=$(git merge-base HEAD origin/main)
python3 scripts/pylint_regression_gate.py ci \
  --report pylint-report.json \
  --pylint-status "${PYLINT_STATUS}" \
  --branch-baseline ci/pylint-baseline.json \
  --base-ref "${BASE_REF}"
```

**PASS:** gate exits 0 **or** GitHub Actions job **Pylint / Pylint regression gate** green on `43b5f33`.

Do **not** edit `ci/pylint-baseline.json` to bless new debt.

## D — Live probe (include numbering)

```bash
python3 - <<'PY'
from ask import ask
tr = ask("what is the Round 1 evidence minority cap formula?", top_k=3, evidence=True, trace=True)["trace"]
print(tr["schema"], list(tr["stages"]), tr["context_delivery"]["max_chars"])
PY
# Also: convmem ask "…" --evidence --trace   # stderr JSON
```

| # | Check | PASS |
|---|---|---|
| D1–D4 | Schema, stages, request truth, delivery | |
| D5 | Prompt / CLI path not all `[1]` (covered by B11; spot-check OK) | |

## E — MCP

Unit tests cover E1–E3 (`test_mcp_omit_trace_key_and_piggyback_fields`). Live MCP audit optional.

## Acceptance map (executive 1–8)

| Item | Sections |
|---|---|
| 1 Round 1 | A, pre-push |
| 2 trace=False + citation piggyback | B1, E |
| 3 schema/stages/bounds | B2–B6 |
| 4 admitted recent | B8 |
| 5 final_context + delivery | B5, B6, B10–B12 |
| 6 rerank ≠ dedupe | B7 |
| 7 suites + doctor | C (+ G for CI) |
| 8 self-check + probe | Pre-push, D, G |

## F — Partner sign-off

| Lane | Status |
|---|---|
| Kiro | **PASS** on `43b5f33` |
| R1 | **PASS** on `43b5f33` |
| Ryan | merge when checklist + Pylint CI green |

## Out of scope

MCP evidence default flip; diversification; retrieval-eval; `retrieve_for_ask`.
