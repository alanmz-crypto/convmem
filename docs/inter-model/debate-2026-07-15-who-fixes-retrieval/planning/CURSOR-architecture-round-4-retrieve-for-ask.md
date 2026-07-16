# Round 4 architecture — `retrieve_for_ask` extraction

**Status:** Revised per ChatGPT REVISE (2026-07-16) — **Round 3 docs close-out DONE**; **Phase 1 code HOLD** until this revision is the tip partners cite.
**Author:** Cursor (ChatGPT REVISE locks)
**Date:** 2026-07-16
**Base:** `main` @ `549f74d` ([PR #39](https://github.com/alanmz-crypto/convmem/pull/39))

**ChatGPT authorization:** GO for Round 3 documentation close-out (done on this branch). HOLD Round 4 code PR until these five locks are in the architecture. After that, extraction proceeds without reopening the broader retrieval debate.

---

## Sequencing (two operations — never mixed)

| Op | Branch / tip | Contents |
|---|---|---|
| **A — Docs** | `docs/2026-07-15-debate-insight-folder` | Round 3 → `reference/round-3-source-diversity/` + stubs + indexes |
| **B — Code** | `fix/2026-07-16-retrieve-for-ask` off exact `main` @ `549f74d` | Extraction + tests only |

Do **not** merge or cherry-pick the debate branch into the code branch.

Follow-on arc (not this PR): retrieval-eval rewrite against `RetrievalBundle`. MCP `evidence` default unchanged. Staging2 postponed.

---

## Extraction boundary (unchanged intent)

Retrieval, filtering, diversification, formatting, context limiting, and **completed** trace preparation belong in `retrieve_for_ask`. Synthesis and final response assembly stay in `ask()`.

**Non-goals:** no new ranking, filtering, cardinality, diversification policy, or response-shape “cleanups.”

---

## ChatGPT REVISE locks (required)

### 1. Separate docs close-out from the code PR

See sequencing table above. Already applied for Op A on this docs tip.

### 2. Configuration ownership — one snapshot

```python
def ask(...):
    cfg = load_config()
    bundle = retrieve_for_ask(..., cfg=cfg)
    models = cfg["models"]
    ...

def retrieve_for_ask(..., cfg=None):
    if cfg is None:
        cfg = load_config()
    ...
```

**Required tests:**

* `ask()` calls `load_config()` exactly once.
* Supplying `cfg=` to `retrieve_for_ask()` causes **no** additional `load_config()` call.

Prevents retrieval and synthesis from observing different config snapshots.

### 3. Bundle cardinalities (exact)

| Field | Meaning |
|---|---|
| `bundle.results` | **Normal/evidence:** filtered pre-diversity slice of at most `top_k`. **Hybrid/raw:** existing pre-diversity internal pool of at most `fetch_k`. |
| `bundle.selection` / `bundle.citations` | Full ordered context selection; may contain `fetch_k` items on raw/hybrid. |
| `ask()` return | Still `results[:top_k]` and `citations[:top_k]` (external contract unchanged). |

### 4. Completed trace on the bundle — not loose pieces

```python
@dataclass(frozen=True)
class RetrievalBundle:
    search_q: str
    results: list[dict]
    selection: list[dict]
    citations: list[dict]
    context: str
    context_delivery: dict
    confidence: float | None
    warning: str | None
    trace: dict | None  # full convmem.ask.trace.v1 when trace=True; else None
```

* `retrieve_for_ask(trace=True)` builds the **complete** `convmem.ask.trace.v1` envelope.
* `ask()` attaches `bundle.trace` **unchanged**.
* `dropped` stays an **internal local** (already represented via `final_context.source_diversity`).

Evaluator later consumes the same trace contract production callers receive.

### 5. Awkward-edge parity + implementation order

**Empty path (exact today):**

* does not synthesize;
* returns only `answer`, `citations`, `results`, `confidence`, `warning`, plus `trace` when requested;
* warning exactly `"No matches in index."`;
* zero-valued `context_delivery`;
* still constructs retrieval stages (inside the envelope) before returning.

**Hybrid warning:** may be based on the weak **unit** score even when merged raw raises returned confidence. Do **not** “fix” that incidental semantic.

**Code PR commit order (mandatory):**

1. Characterization tests against **current** `ask()` behavior (expected values locked).
2. Extraction commit — those expected values must not change.
3. Direct `retrieve_for_ask()` test: `generate_stream` is **never** called.
4. Existing `test_ask_trace`, `test_ask_source_diversity`, `test_ledger_recent` unchanged and green.

---

## Shape / API

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

Stay in `ask.py` this PR (no new module). Helpers stay put.

---

## Process (light)

- This architecture doc + one code PR (Op B only).
- Focused suites + local pylint gate.
- One independent partner PASS on exact tip before Ryan merges.
- No Round-2 ack-chain.

---

## Out of scope

MCP `evidence` default; ranking/diversify/cardinality changes; title-collapse; staging2; new package; retrieval-eval rewrite (next arc).

---

## Done when

1. Round 3 under `reference/round-3-source-diversity/` with stubs (**done** on docs tip).
2. Architecture includes all five ChatGPT locks (**this revision**).
3. Code PR (HOLD until Ryan go): characterization → extract → no-LLM retrieve test; partner PASS; Ryan merges.
4. Then open retrieval-eval against `RetrievalBundle.trace` / bundle fields.

---

## Related

- Round 3 ship: PR #39 @ `549f74d` — [reference/round-3-source-diversity/](../reference/round-3-source-diversity/)
- ChatGPT preferred shape (historical): [CHATGPT-top-two-problems-and-plans.md](../CHATGPT-top-two-problems-and-plans.md)
