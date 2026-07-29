# Shadow writer coverage inventory (C3 writer gate)

| Field | Value |
|---|---|
| Proof class | code-path static + hermetic (C3 writer gate; not live activation) |
| `production_chroma_write_session` call sites | **8** |
| `open_production_write_store` call sites | **6** |
| Legacy `open_chroma_for_write` / `chroma_write_session` prod sites | **0** |
| Sites that must use gated session but bypass | **0** |

## Finding

Production mutating writers open Chroma through `production_chroma_write_session`
or `open_production_write_store` (shared writer lease, then live config load).
Remaining direct `ChromaStore(...)` sites are allowlisted read-only / dry-run /
helper / factory-internal / replay constructors, plus C6's mechanically isolated
private scratch-only canary constructors. VERIFY **V3b** and **V3d** remain
**PASS** at this tip for code-path coverage under the C3 boundary.

Hermetic control still proves that a *hypothetical* direct ctor with eligible
cfg attaches no sink — that is why the gated session boundary remains mandatory.

**Not proved:** that a live ingest with `enabled=true` wrote a shadow line —
activation against the live corpus is forbidden for this verification slice.

## must_use_factory bypass list

*(empty — C3 migration complete)*

## Production gated routing

| Site | Via |
|---|---|
| `convmem.py:1449` | `production_chroma_write_session` |
| `convmem.py:373` | `production_chroma_write_session` |
| `convmem.py:477` | `production_chroma_write_session` |
| `convmem.py:642` | `production_chroma_write_session` |
| `ingest.py:478` | `production_chroma_write_session` |
| `ingest.py:535` | `production_chroma_write_session` |
| `ingest.py:751` | `production_chroma_write_session` |
| `inter_model_index.py:155` | `production_chroma_write_session` |
| `observe.py:230` | `open_production_write_store` |
| `propose_decision.py:529` | `open_production_write_store` |
| `propose_decision.py:562` | `open_production_write_store` |
| `refine.py:272` | `open_production_write_store` |
| `refine.py:718` | `open_production_write_store` |
| `source_purge.py:317` | `open_production_write_store` |

## allowlisted_direct (not a V3d failure)

| Site | Class |
|---|---|
| `ask.py:550` | `read_only` |
| `chroma_store.py:64` | `read_factory_helper` |
| `chroma_store.py:89` | `read_factory_helper` |
| `chroma_write_store.py:409` | `factory_internal` |
| `convmem.py:134` | `read_only` |
| `convmem.py:626` | `dry_run_no_sink` |
| `mcp_server.py:897` | `read_only` |
| `mcp_server.py:944` | `read_only` |
| `shadow_canary.py:514` | `canary_scratch_cold_validation` |
| `shadow_canary.py:621` | `canary_scratch_warmup` |
| `shadow_canary.py:635` | `canary_scratch_workload` |
| `shadow_replay.py:177` | `replay_internal` |

## Reclassified read

| Site | Routing |
|---|---|
| `propose_decision.py` (open_chroma_for_read) | `open_chroma_for_read` |
