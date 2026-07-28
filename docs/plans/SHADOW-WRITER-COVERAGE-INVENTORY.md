# Shadow writer coverage inventory (factory routing)

| Field | Value |
|---|---|
| Proof class | code-path static + hermetic (not live activation) |
| `open_chroma_for_write` prod call sites | **10** |
| `chroma_write_session` prod call sites | **4** (wraps factory) |
| Sites that must use factory but bypass | **0** |

## Finding

Production mutating writers now open Chroma through `open_chroma_for_write`
(or `chroma_write_session`, which calls the factory). Remaining direct
`ChromaStore(...)` sites are allowlisted read-only / helper / factory-internal
constructors. VERIFY **V3b** and **V3d** are **PASS** at this tip for code-path
coverage.

Hermetic control still proves that a *hypothetical* direct ctor with eligible
cfg attaches no sink — that is why the factory boundary remains mandatory.

**Not proved:** that a live ingest with `enabled=true` wrote a shadow line —
activation against the live corpus is forbidden for this verification slice.

## must_use_factory bypass list

*(empty — migration complete)*

## Production factory routing

| Site | Via |
|---|---|
| `convmem.py:377` | `open_chroma_for_write` |
| `convmem.py:474` | `open_chroma_for_write` |
| `convmem.py:616` | `open_chroma_for_write` |
| `convmem.py:1422` | `open_chroma_for_write` |
| `observe.py:233` | `open_chroma_for_write` |
| `propose_decision.py:529` | `open_chroma_for_write` |
| `propose_decision.py:556` | `open_chroma_for_write` |
| `refine.py:272` | `open_chroma_for_write` |
| `refine.py:716` | `open_chroma_for_write` |
| `source_purge.py:317` | `open_chroma_for_write` |
| `ingest.py:478` | `chroma_write_session` |
| `ingest.py:533` | `chroma_write_session` |
| `ingest.py:747` | `chroma_write_session` |
| `inter_model_index.py:155` | `chroma_write_session` |

## allowlisted_direct (not a V3d failure)

| Site | Class |
|---|---|
| `ask.py:550` | read_only |
| `chroma_store.py:64` | read_factory_helper |
| `chroma_store.py:89` | read_factory_helper |
| `chroma_write_store.py:48` | factory_internal |
| `convmem.py:134` | read_only |
| `mcp_server.py:897` | read_only |
| `mcp_server.py:944` | read_only |
| `shadow_replay.py:176` | replay_internal (`mutation_sink=None`) |

## Reclassified read

| Site | Routing |
|---|---|
| `propose_decision.py:168` | `open_chroma_for_read` |
