# Plan: Streaming synthesis for `convmem ask`

---
builder_lens:
  primary: ousterhout
  secondary: manning
  verify: golden queries + convmem ask
---

**Date**: 2026-06-29
**Author**: DeepSeek V4 Pro (Crush)
**Status**: Phase 1 **shipped** (2026-07-05); Phase 2 draft — pre-flight pending
**Relates to**: `dec_prop_20260623_161428_c311`

## Problem

`ask` synthesizes an answer from retrieved excerpts with a hard 45s timeout. On timeout
(or any error), it falls back to raw citation lines — the user gets no synthesis at all.
The underlying LLM APIs (DeepSeek, Ollama) both support `stream: True`, but convmem
sets `"stream": False` explicitly and buffers nothing during generation.

**Claude's observation**: Streamable HTTP would let you stream synthesis tokens
progressively — partial synthesis instead of a hard fallback at the wall. The MCP SDK
(1.28.0) already ships `run_streamable_http_async`.

## Current state

| Piece | Where | Status |
|-------|-------|--------|
| LLM streaming | `llm.py` | `generate_stream()` — DeepSeek SSE + Ollama NDJSON (**Phase 1 shipped**) |
| Timeout | `ask.py` | `_ASK_SYNTHESIS_TIMEOUT = 45.0`; wall-clock via `threading.Timer` |
| Fallback | `ask.py` | partial → `synthesis_interrupted`; empty buffer → `synthesis_failed` |
| MCP `ask` fields | `mcp_server.py` | `synthesis_failed`, `synthesis_interrupted` in JSON response |
| MCP transport | `mcp_server.py` | `mcp.run_stdio_async()` — stdio only (Phase 2 pending pre-flight) |

## Design

### Phase 1 — Internal streaming + partial fallback (~55 lines)

No transport change. No MCP tool signature change. The existing `ask()` function returns
the same dict shape. The only difference: on timeout, it returns whatever synthesis text
was generated before the timeout, annotated with a `[Synthesis interrupted]` notice.

**`llm.py`** — new `generate_stream()` (~40 lines)

```python
def generate_stream(
    prompt, model, ollama_host, deepseek_base_url, *, timeout=None
):
    """Yield synthesis tokens one at a time. Same provider routing as generate().

    DeepSeek:  SSE lines → yield choices[0].delta.content
    Ollama:    NDJSON lines → yield response field

    Caller collects tokens in a buffer; on timeout/interrupt the buffer
    contains whatever was generated so far.
    """
```

- Timeout is a true wall-clock limit: `threading.Timer(timeout).start()` sets a
  `threading.Event`; the iteration loop checks `stop.is_set()` on every chunk and
  **raises `TimeoutError`** — not `return`. Raising is critical: a clean `return`
  exits the generator normally, the `for` loop in `ask.py` completes without
  hitting the `except` block, and partial text is returned silently without the
  `[Synthesis interrupted]` annotation. Raising makes the `except` branch fire
  with a non-empty buffer.
  `requests.post(..., timeout=10)` is a connection/read-stall timeout only,
  not a synthesis deadline.
- DeepSeek path: parse `data: {"choices":[{"delta":{"content":"..."}}]}` lines
- Ollama path: parse `{"response":"...","done":false}` lines
- Skip `[DONE]` and empty deltas
- Timer is cancelled in a `finally` block

**`ask.py`** — replace the `try/except` block in `ask()` (~20 lines)

```python
buffer = []
synthesis_failed = False
try:
    for token in generate_stream(prompt, model=model, ...,
                                 timeout=_ASK_SYNTHESIS_TIMEOUT):
        buffer.append(token)
    answer = "".join(buffer)
except Exception as e:
    if buffer:
        # Partial synthesis — better than raw citations
        answer = "".join(buffer) + (
            f"\n\n[Synthesis interrupted ({type(e).__name__}). "
            f"Partial answer above.]"
        )
        warning = f"{warning}\nSynthesis interrupted; partial answer returned." \
            if warning else "Synthesis interrupted; partial answer returned."
    else:
        # Nothing generated at all — existing fallback
        synthesis_failed = True
        ...  # same raw-citation dump as today
```

**What doesn't change**:
- `_ASK_SYNTHESIS_TIMEOUT` stays 45s
- The `ask()` return dict shape is identical
- MCP `ask` tool is untouched
- CLI `convmem ask` is untouched
- No new dependencies

### Phase 2 — Streamable HTTP transport (~120 lines)

Progressive token-by-token delivery to MCP clients over SSE. Builds on Phase 1's
`generate_stream()`.

**`ask.py`** — new async `run_ask_stream()` (~55 lines)

```python
async def run_ask_stream(
    question, *, top_k=5, domain=None, site=None, evidence=False, history=None
):
    """Async generator: yield progressive events for streaming MCP clients.

    Events:
      {"type": "citations", "citations": [...], "confidence": ..., "warning": ...}
      {"type": "token", "text": "..."}
      ...
      {"type": "done", "confidence": ..., "warning": ...}
    """
```

- Retrieval runs synchronously (Chroma isn't async), emits citations immediately
- `generate_stream()` is a sync generator — cannot be used directly with
  `async for`. Bridge it through `asyncio.Queue` + `loop.run_in_executor()`:
  a producer thread pushes `{"type": "token", "text": …}` events onto the queue;
  the async loop `await queue.get()` and yields them. A `None` sentinel marks
  completion.
- Tokens yielded as they arrive
- On thread timeout (wall-clock via `threading.Timer`): yield final token
  `"[Synthesis interrupted]"`, then `done`

**`mcp_server.py`** — new `ask_stream` tool + transport switch (~65 lines)

```python
@mcp.tool()
async def ask_stream(
    question: str, top_k: int = 5, domain: str = "", site: str = "",
    evidence: bool = False,
):
    """Streaming ask — yields citations then synthesis tokens progressively."""
    async for event in run_ask_stream(question, top_k=top_k, ...):
        yield json.dumps(event)

# Entrypoint: CONVMEM_TRANSPORT env or --transport flag
if __name__ == "__main__":
    transport = os.environ.get("CONVMEM_TRANSPORT", "stdio")
    if transport == "streamable-http":
        asyncio.run(mcp.run_streamable_http_async())
    else:
        asyncio.run(mcp.run_stdio_async())
```

**`config.example.toml`** — optional stanza

```toml
[mcp]
transport = "stdio"  # or "streamable-http"
host = "127.0.0.1"
port = 8000
```

**What doesn't change**:
- Existing `ask` MCP tool (non-streaming) stays — backward compatible
- CLI `convmem ask` stays synchronous
- `llm.py` unchanged from Phase 1

## Files touched

| File | Phase 1 | Phase 2 | Total |
|------|---------|---------|-------|
| `llm.py` | +40 | — | 40 |
| `ask.py` | +20 | +55 | 75 |
| `mcp_server.py` | — | +65 | 65 |
| `config.example.toml` | — | +5 | 5 |
| **Total** | **60** | **140** | **200** |

## Risk assessment

| Risk | Phase | Mitigation |
|------|-------|------------|
| SSE parsing bugs (malformed chunks) | 1 | Defensive parsing: skip lines that don't parse as JSON; never crash the loop |
| DeepSeek/Ollama stream format divergence | 1 | Both formats are well-documented and stable; each has its own code path |
| `requests.iter_lines()` blocks the event loop | 2 | `asyncio.Queue` + `run_in_executor()` — producer thread feeds async consumer |
| MCP clients don't support async generators | 2 | Existing `ask` tool stays; `ask_stream` fails gracefully for non-streaming clients |
| Streamable HTTP needs auth/CORS | 2 | Bind to `127.0.0.1` only; no auth needed (local agent use) |

## Rollout

1. **Phase 1** ships immediately — zero API surface change, pure improvement. The worst
   case (empty buffer on timeout) degrades to existing raw-citation fallback.
2. **Pre-flight for Phase 2**: before building Phase 2, verify that the target MCP
   client (Cursor, Crush) actually renders async generator tool results progressively.
   Write a minimal `ask_stream` stub that yields three strings with `asyncio.sleep(1)`
   between them; confirm the client shows tokens as they arrive rather than buffering
   until completion. If the client buffers, Phase 2's progressive UX gain disappears
   and only the transport complexity remains.
3. **Phase 2** ships after pre-flight passes. MCP clients that support async generator
   tools get progressive UX; all others use the Phase 1 `ask` tool unchanged.
