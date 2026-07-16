# CURSOR — Verification plan: Round 2 ask(trace)

**Date:** 2026-07-16
**From:** Cursor
**Status:** Shipped on PR tip — awaiting independent partner verification (Kiro + R1), then Ryan merge
**PR:** [PR #35](https://github.com/alanmz-crypto/convmem/pull/35) (`fix/2026-07-15-ask-trace` @ `503add7`)
**Architecture:** [CURSOR-architecture-round-2-trace.md](CURSOR-architecture-round-2-trace.md)
**Red-flag disposition (A1/A2):** [CURSOR-executive-redflag-disposition-round-2-trace.md](CURSOR-executive-redflag-disposition-round-2-trace.md)

---

## Work log (Cursor execution)

| Step | What happened |
|---|---|
| Go | Ryan authorized Steps 1–5. A1/A2 are **merge gates** (implemented on tip), not a go-deadlock. |
| Baseline | `origin/main` @ `48e816f`. `python3 -m unittest discover -s tests -q` → OK (484). `python3 convmem.py doctor` → OK. |
| Delivery | **Greenfield from `main`**, not naive rebase of old tip `90835a8` (that tip still reverted Round 1). |
| Tip | `503add7` pushed with `git push --force-with-lease origin HEAD:fix/2026-07-15-ask-trace` (replaced `90835a8`). |
| Files | `ask.py`, `convmem.py`, `mcp_server.py`, `tests/test_ask_trace.py` only. |
| Round 1 kept | `max(1, total_limit // 3)` present; `with ChromaStore(...)` present; `tests/test_ledger_recent.py` **unchanged** vs `main`; `_EXCLUDE_PATH_TOKENS` intact. |
| Contract | `schema: convmem.ask.trace.v1`; stages `candidates` → `evidence_reranked` → `ledger_deduped` → `recent_injected` (admitted only) → `final_context`; A1 `items_total`/`truncated`; A2 `context_delivery`; MCP piggyback `evidence_status`+`ledger_id`; CLI `--trace`. |
| Cursor local verify | `tests.test_ledger_recent` + `tests.test_ask_trace` green; full suite green; doctor green post-impl; live `ask(..., evidence=True, trace=True)` probe showed five stages + `context_delivery`. |
| PR state | MERGEABLE on `main`. **Do not merge** until Kiro + R1 confirm below. |

Partners: treat the table above as Cursor’s claim. Re-run the checklist; do not trust chat alone.

---

## Verification checklist

For each item: **PASS / FAIL / SKIP** + one evidence line (exit code, SHA, or grep hit).

### A — Tip and Round 1 invariants (shell)

```bash
git fetch origin main fix/2026-07-15-ask-trace
git rev-parse origin/fix/2026-07-15-ask-trace
# expect: 503add77cb07a85699705aee94372c1cb609b2ca (or newer tip if amended — note SHA)

cd "$(git rev-parse --show-toplevel)"   # checkout of fix/2026-07-15-ask-trace preferred
rg -n 'max\(1, total_limit // 3\)' ask.py
rg -n 'with ChromaStore' ask.py
git diff origin/main...origin/fix/2026-07-15-ask-trace -- tests/test_ledger_recent.py
# expect: empty diff
rg -n '_EXCLUDE_PATH_TOKENS' adapters/inter_model_doc.py
```

| # | Check | PASS criteria |
|---|---|---|
| A1 | Tip SHA | Matches `503add7…` (or document newer) |
| A2 | Minority cap | `max(1, total_limit // 3)` in `ask.py` |
| A3 | ChromaStore | `with ChromaStore` in evidence path |
| A4 | Ledger tests | No diff vs `main` for `tests/test_ledger_recent.py` |
| A5 | Nested exclude | `_EXCLUDE_PATH_TOKENS` still present |

### B — Contract structure (shell / unit)

```bash
python3 -m unittest tests.test_ask_trace -v
```

| # | Check | PASS criteria |
|---|---|---|
| B1 | `trace=False` | No `trace` key in ask result |
| B2 | Schema | `trace.schema == convmem.ask.trace.v1` |
| B3 | Five stages | `candidates`, `evidence_reranked`, `ledger_deduped`, `recent_injected`, `final_context` all present when `trace=True` |
| B4 | Skipped shape | Skipped stages are `{status, reason, items:[]}` — never `null` |
| B5 | A1 bounds | Stage has `items_total` + `truncated`; exact final ID equality only when `final_context.truncated == false` |
| B6 | A2 delivery | `context_delivery.max_chars == 12000`; when truncated, `chars_after > max_chars` (marker appended) |
| B7 | Stage split | `evidence_reranked` and `ledger_deduped` are separate keys |
| B8 | Admitted recent | `recent_injected` items all have `evidence_status == recent_decision` (when evidence path ran) |
| B9 | No bodies | Compact rows have no document bodies |
| B10 | Three paths | `final_context` fidelity covered for normal, raw, and hybrid (see tests) |

### C — Focused + full suite + doctor

```bash
python3 -m unittest tests.test_ledger_recent tests.test_ask_trace -v
python3 -m unittest discover -s tests -q
python3 convmem.py doctor
```

| # | Check | PASS criteria |
|---|---|---|
| C1 | Focused | Both modules OK |
| C2 | Full suite | discover exit 0 (or zero **new** failures vs baseline `48e816f` — document any pre-existing) |
| C3 | Doctor | exit 0 |

### D — Live probe (Tier A shell)

```bash
python3 - <<'PY'
from ask import ask
import json
tr = ask("what is the Round 1 evidence minority cap formula?", top_k=5, evidence=True, trace=True)["trace"]
print("schema", tr.get("schema"))
print("stages", list((tr.get("stages") or {}).keys()))
print("context_delivery", tr.get("context_delivery"))
print("request.evidence", (tr.get("request") or {}).get("evidence"))
print("request.retrieval_query", (tr.get("request") or {}).get("retrieval_query"))
PY
# or: convmem ask "…" --evidence --trace
```

| # | Check | PASS criteria |
|---|---|---|
| D1 | Schema | `convmem.ask.trace.v1` |
| D2 | Stages | All five keys present |
| D3 | Request truth | `request.evidence` matches call; `retrieval_query` non-empty |
| D4 | Delivery | `context_delivery` present with `max_chars` |

### E — MCP (Tier B / Cursor MCP)

| # | Check | PASS criteria |
|---|---|---|
| E1 | `trace=False` | Payload omits `trace` key |
| E2 | Piggyback | Citations include `evidence_status` and `ledger_id` (may be empty string / null) |
| E3 | `trace=True` | Versioned envelope present |

DeepSeek/MCP-only: run E; SKIP A–D shell or ask Ryan to paste.

### F — Partner sign-off

| Lane | Role | Status |
|---|---|---|
| Kiro | Confirm after independent check | pending |
| R1 | Confirm structure + `retrieval_query` / evidence in payload | pending |
| ChatGPT / V4 / Grok | Optional spot-check | optional |
| Ryan | Merge when checklist green | pending |

**Report:** Comment on PR #35 or file a short review under `planning/` with PASS/FAIL per section.

---

## Out of scope (do not fail the PR for these)

- MCP `evidence` default flip
- Source diversification
- Retrieval-eval rewrite
- `retrieve_for_ask` extraction
