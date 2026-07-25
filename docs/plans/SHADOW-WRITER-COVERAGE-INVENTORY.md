# Shadow writer coverage inventory (factory bypass proof)

| Field | Value |
|---|---|
| Proof class | code-path static + hermetic (not live activation) |
| `open_chroma_for_write` prod call sites | **0** |
| Sites that must use factory but bypass | **14** |

## Finding

Production mutating (or conservatively classified write) call sites construct
`ChromaStore(...)` directly. Sink injection only happens inside
`open_chroma_for_write`, which has **zero** production callers. Therefore
VERIFY **V3b** and **V3d** are **FAIL** at this tip.

**Not proved:** that a live ingest with `enabled=true` missed a shadow line —
activation against the live corpus is forbidden for this verification slice.

## must_use_factory bypass list

| Site | Class |
|---|---|
| `convmem.py:377` | mutates_units |
| `convmem.py:474` | mutates_units |
| `convmem.py:1371` | mutates_units |
| `ingest.py:477` | mutates_units |
| `ingest.py:532` | mutates_units |
| `ingest.py:745` | mutates_units |
| `inter_model_index.py:155` | mutates_units |
| `observe.py:231` | mutates_units |
| `propose_decision.py:168` | mutates_units |
| `propose_decision.py:526` | mutates_units |
| `propose_decision.py:553` | mutates_units |
| `refine.py:271` | mutates_units |
| `refine.py:715` | mutates_units |
| `source_purge.py:317` | mutates_units |

## allowlisted_direct (not a V3d failure)

| Site | Class |
|---|---|
| `ask.py:550` | read_only |
| `chroma_store.py:64` | read_factory_helper |
| `chroma_store.py:89` | read_factory_helper |
| `chroma_write_store.py:47` | factory_internal |
| `convmem.py:134` | read_only |
| `convmem.py:616` | read_only |
| `mcp_server.py:897` | read_only |
| `mcp_server.py:944` | read_only |
