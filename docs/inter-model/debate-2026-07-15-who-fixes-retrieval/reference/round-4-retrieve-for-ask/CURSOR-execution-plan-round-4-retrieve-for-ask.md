# Round 4 execution plan — `retrieve_for_ask` extraction

**Status:** **Shipped** — [PR #40](https://github.com/alanmz-crypto/convmem/pull/40) merged @ `20fc85d`. Partner PASS @ `2c7e599`. Canonical archive copy.
**Date:** 2026-07-16
**Architecture:** [CURSOR-architecture-round-4-retrieve-for-ask.md](CURSOR-architecture-round-4-retrieve-for-ask.md) (ChatGPT REVISE @ docs tip `85b7084`)

## Exact anchors

| Anchor | SHA |
|---|---|
| Docs tip | `85b70849dd7c606d5082ac365513952363be6ee9` |
| Code base (`main`) | `549f74d5c85b03dd2bfb6ed2013fd18e15a5901d` |

## Operations (never mixed)

| Op | Where | Contents |
|---|---|---|
| A — Docs | `docs/2026-07-15-debate-insight-folder` | **DONE** — Round 3 → `reference/round-3-source-diversity/` |
| B — Code | `fix/2026-07-16-retrieve-for-ask` off `main` @ `549f74d` only | Extraction + tests — **no debate-branch merge/cherry-pick** |

---

## ChatGPT five locks (carry into code)

1. Docs vs code separated (Op A done; Op B pure).
2. One `cfg` snapshot: `ask()` loads once, passes `cfg=` into `retrieve_for_ask`; tests for exactly-one load and no reload when `cfg=` supplied.
3. Cardinalities: `bundle.results` pre-diversity (≤`top_k` normal/evidence; ≤`fetch_k` hybrid/raw); `selection`/`citations` full context (may be `fetch_k`); `ask()` still returns `results[:top_k]` / `citations[:top_k]`.
4. `RetrievalBundle.trace: dict | None` = completed `convmem.ask.trace.v1`; `ask()` attaches unchanged; `dropped` internal only.
5. Empty/hybrid awkward-edge parity preserved; characterization-first commit order mandatory.

---

## Mandatory commit sequence (Op B)

| Step | Commit / action |
|---|---|
| 1 | **Characterization tests** against current `ask()` (lock expected empty/hybrid/trace/cardinality values) |
| 2 | **Behavior-preserving extraction** (`RetrievalBundle` + `retrieve_for_ask`; thin `ask()`) — characterization must stay green |
| 3 | **Direct no-LLM test:** `retrieve_for_ask()` never calls `generate_stream` |
| 4 | Focused suites (`test_ask_trace`, `test_ask_source_diversity`, `test_ledger_recent`, new retrieve tests) + local pylint regression gate |
| 5 | One independent partner PASS on exact final PR tip |
| 6 | Ryan merge verdict |

### Empty path (exact)

- No synthesis; keys `answer`, `citations`, `results`, `confidence`, `warning` (+ `trace` if requested).
- Warning exactly `"No matches in index."`
- Zero-valued `context_delivery` inside envelope when traced.
- Stages still constructed inside the completed envelope.

### Hybrid warning

May reflect weak **unit** score even when merged confidence is higher — do not “fix.”

---

## Out of scope

MCP `evidence` default; ranking/diversify/cardinality changes; title-collapse; staging2; new module package; retrieval-eval rewrite (next arc).

---

## Authorization state

| Item | State |
|---|---|
| Op A docs | Done @ `85b7084` |
| Architecture REVISE | Published |
| This execution plan | Filed |
| Op B code | **Shipped** @ `20fc85d` (review tip `2c7e599`) |
