# Round 4 architecture — `retrieve_for_ask` extraction

**Status:** Draft for partner review — **not authorized for code** until Ryan says go.
**Author:** Cursor (ChatGPT + Continue-DeepSeek V4 consensus)
**Date:** 2026-07-16
**Base:** `main` @ `549f74d` (Round 3 source diversification shipped via [PR #39](https://github.com/alanmz-crypto/convmem/pull/39))

**Partner lock:** close Round 3 docs → extract `retrieve_for_ask` (parity-only) → make **retrieval-eval rewrite** the next arc. MCP `evidence` default unchanged. Staging2 postponed.

---

## Sequencing

| Step | Deliverable | This PR? |
|---|---|---|
| 0 | Close Round 3 into `reference/round-3-source-diversity/` (+ stubs) | Yes (docs) |
| 1 | Extract `retrieve_for_ask` → `RetrievalBundle` (behavior-preserving) | Yes (code) |
| 2 | Retrieval-eval rewrite against the bundle | **Next arc** (not this PR) |
| — | MCP `evidence` default flip | Ryan product call — deferred |

---

## Why extract now

Trace + diversification are on `main`. Eval needs a retrieval-only target that does not pull synthesis / LLM. A bounded extraction:

- gives a falsifiable retrieval contract (query → filter → diversify → format → optional trace);
- lets future strategy swaps avoid touching `ask()` synthesis;
- avoids duplicating pipeline logic in the evaluator.

**Non-goals for this PR:** no new ranking, filtering, cardinality, diversification policy, or response-shape changes.

---

## Boundary

```text
ask()
  ├─ retrieve_for_ask(...) -> RetrievalBundle
  └─ _synthesize_answer(...) / empty canned answer
```

| In `retrieve_for_ask` | Stays in `ask()` |
|---|---|
| `_retrieval_query`, `query_units` / `query_raw` | `_synthesize_answer` / LLM |
| evidence + recent inject | Final answer string / synthesis flags |
| `_select_units_or_hybrid` + diversify | Response assembly (`citations[:top_k]`, etc.) |
| `_format_selection`, `_apply_context_char_limit` | Interactive loop |
| Trace stages through `final_context` + `source_diversity` + envelope inputs | |

---

## Shape (stay in `ask.py` this PR)

```python
@dataclass(frozen=True)
class RetrievalBundle:
    search_q: str
    results: list[dict]          # pre-diversity diagnostic slice (as today)
    selection: list[dict]
    citations: list[dict]
    context: str                 # post char-limit
    context_delivery: dict
    confidence: float | None
    warning: str | None
    stages: dict                 # empty when trace=False
    dropped: list[dict]
```

```python
def retrieve_for_ask(
    question: str,
    *,
    top_k: int = 5,
    raw: bool = False,
    history: list[tuple[str, str]] | None = None,
    domain: str | None = None,
    site: str | None = None,
    evidence: bool = False,
    trace: bool = False,
    cfg: dict | None = None,
) -> RetrievalBundle:
    ...
```

Lift the current pre-synthesis body of `ask()` into this function. `ask()` becomes: retrieve → synthesize (or canned empty answer when `not bundle.results`).

Helpers stay in `ask.py`. Do **not** move to a new module in this PR (parity risk). Eval arc may import from `ask` or relocate later.

---

## Acceptance — parity (hermetic)

New `tests/test_retrieve_for_ask.py` (mock `query_*`; no LLM inside retrieve):

| Path | Prove |
|---|---|
| Normal units | Bundle matches today’s pre-synthesis outputs |
| Evidence | Stages / recent inject / citations unchanged |
| Hybrid | diversify `limit=fetch_k`; flags/origins preserved |
| Raw | diversify `limit=fetch_k`; skipped evidence stages when `trace=True` |
| Empty | `results=[]`; stages still build when `trace=True` |
| Trace on/off | `trace=True` → identical `convmem.ask.trace.v1` shape vs current |

Regression (must stay green): `tests.test_ask_trace`, `tests.test_ask_source_diversity`, `tests.test_ledger_recent`.

---

## Process (light)

- This one architecture doc + one code PR (`fix/2026-07-16-retrieve-for-ask`).
- Focused suites + local pylint regression gate.
- One independent partner PASS on exact tip before Ryan merges.
- No Round-2-style ack-chain.

---

## Out of scope

- MCP `evidence` default flip
- Ranking / diversify / cardinality changes
- Title-collapse
- staging2 headers / background synthesis
- New `retrieve_ask.py` package (this PR)
- Full retrieval-eval rewrite (**immediate next arc** after merge)

---

## Done when

1. Round 3 docs under `reference/round-3-source-diversity/` with stubs.
2. `ask()` is retrieve → synthesize; CLI/MCP behavior unchanged.
3. Parity tests cover normal / evidence / hybrid / raw / empty / trace.
4. Partner PASS + Ryan merge; then open retrieval-eval against `RetrievalBundle`.

---

## Related

- Round 3 ship: PR #39 @ `549f74d`
- Round 2 board (historical T2): [CURSOR-round-2-board-decision.md](../CURSOR-round-2-board-decision.md)
- ChatGPT preferred shape: [CHATGPT-top-two-problems-and-plans.md](../CHATGPT-top-two-problems-and-plans.md) (§ Preferred internal shape)
