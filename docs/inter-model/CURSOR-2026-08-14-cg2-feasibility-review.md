# CG-2 Architecture — Implementation Feasibility Review

**Date:** 2026-08-14  
**Author:** Cursor (implementation feasibility lane)  
**Architecture revision:** `1222b1ede2d6cc5da582388768f06d60b36c5e50`  
**Handoff:** `docs/inter-model/KIRO-2026-08-14-cg2-feasibility-handoff.md` @ `196826e`  
**Code mapped against:** `origin/main` @ `0cf2268` (CG-1 substrate + production paths; identical to plan-branch code)

> **Supersession (2026-08-15):** Architecture locked at `e680ce8`. N1–N3 dispositions address
> several risks named here. Authoritative rollup:
> [`CURSOR-2026-08-15-cg2-delta-confirmation.md`](CURSOR-2026-08-15-cg2-delta-confirmation.md).
> This file preserves the `1222b1e` feasibility record only.

---

## 1. Summary verdict

**PASS WITH RISKS** — The CG-2 architecture at `1222b1e` can be implemented against today's codebase **without a ground-up rewrite**, but it requires a **bounded refactor** centered on a new `ServingIndexRepository` (or equivalent) that subsumes more than the four AST-classified `ChromaStore` constructor bypasses. The CG-1 `file_generation_*` modules provide the right seams (staging, cold validation, pointer publication, request-frozen active-map reads). Production query/CLI/MCP paths are structurally wrappable via composition around `open_chroma_for_read` / `ChromaStore`, but **multiple parallel entry points** (`query_units`, `query_raw`, `ask` evidence rerank, MCP `related`/`stats`, `chroma_readonly` helpers) must converge behind one boundary. **Source reconciliation (§7.1) is the largest gap:** `watch.py` has debounced event enqueue only — no overflow signal, no startup/periodic manifest reconciliation, and ingest uses **content-hash** idempotency in `processed.json`, not CG-2 owner/manifest source-hash promotion guards.

---

## 2. §3 repository-fact claim audit

| Architecture claim | Verdict | Evidence (`main`) |
|---|---|---|
| `ownership_key(path)` is `source:<Path.resolve(strict=False)>` | **Confirmed** | `file_generation_contract.py:33-44` — `canonical_source_path` uses `Path(...).resolve(strict=False)`; `ownership_key` prefixes `source:` |
| Production has no caller of CG-1 pointer/builder APIs | **Confirmed** | `grep` production `*.py` (excl. tests): only `file_generation_*` modules and tests import `file_generation_pointer` / `publish_active_pointer` / `build_candidate_generation` |
| Four `cg2-production-bypass` constructors in AST inventory | **Confirmed** | `tests/test_file_generation_read_path_inventory.py:17-61` — `ask._apply_evidence_and_recent`, `convmem.search`, `mcp_server.related`, `mcp_server.stats` |
| `FileGenerationStore` snapshots active map once per read and rechecks rows | **Confirmed** | `file_generation_store.py:521-548` — `active = dict(self._active_generations())` once in `_get_rows`; FILE_SCOPE rows rejected when `active.get(row_owner) != row_generation` |
| Hermetic store computes cosine distance in Python | **Confirmed** | `file_generation_store.py:616-665` — `_cosine_distance` over active row embeddings in Python loops |
| `query.py` catches broad failures and uses read-only fallback | **Confirmed** | `query.py:412-436` (`query_units`), `515-530` (`query_raw`) — bare `except Exception:` → `_fallback_query_rows` via `collection_metadata_rows` (SQLite metadata scan) |
| `doctor._check_index_drift` compares raw Chroma IDs with export IDs | **Confirmed** | `doctor.py:125-168` — `collection_ids` vs JSONL export id set; overlap/coverage math on **physical Chroma embedding ids** |
| `projection_parity.entity_key` prefers `ledger_id`, then `row["id"]` | **Confirmed** | `projection_parity.py:18-24` — `ledger:{id}` then `id:{unit_id}`; no generation-scoped namespace yet |
| Live doctor reports legacy embedding identity missing | **Confirmed** | `doctor.py:1272-1307` — `_check_embed_collection_identity` WARN when `convmem:embed_model` absent from collection metadata |

**Inaccurate / incomplete framing (non-blocking):** The architecture table's "four bypass constructors" is **accurate for the frozen inventory** but **incomplete for full serving surface area** — see §3 below. `query_units` / `query_raw` use `open_chroma_for_read` → `ChromaStore` (classified `core-storage`, not `cg2-production-bypass`), and several production paths use `chroma_readonly.open_readonly_unit_store` / `collection_metadata_rows` (SQLite `mode=ro`) without a `ChromaStore` constructor call.

---

## 3. Bypass inventory findings

**Verdict: Inventory is complete for its stated AST contract; N additional serving paths need explicit CG-2 boundary scope.**

### Verified (matches handoff)

The frozen test passes on `main` — all `EXPECTED` tuples match `_discover()` counts. The four `cg2-production-bypass` sites are real:

| Site | Location |
|---|---|
| Ask evidence rerank | `ask.py:554` — `ChromaStore` inside `_apply_evidence_and_recent` |
| CLI search thin-check | `convmem.py:136` — `ChromaStore` count probe inside `search()` when primary search thin |
| MCP related | `mcp_server.py:897` — direct `ChromaStore` for `related_chain` |
| MCP stats | `mcp_server.py:944` — direct `ChromaStore` for `units_metadata()` |

### Additional serving-adjacent paths (not `cg2-production-bypass` in inventory)

These **must** be included in execution-plan boundary scope or reclassified before generational serving:

| Path | Module | Mechanism | Risk |
|---|---|---|---|
| Primary unit search | `query.py:413` | `open_chroma_for_read` → `ChromaStore.query_units` | High — main ask/search path |
| Raw summary search | `query.py:516` | `open_chroma_for_read` → `query_summaries` | High — `convmem search --raw` |
| Keyword fallback | `query.py:170` | `collection_metadata_rows` (SQLite ro) | High — triggered on **any** Chroma exception |
| MCP unresolved | `mcp_server.py:879` | `open_readonly_unit_store` | Medium — serving-adjacent read |
| Brief / doctor / digest | `brief.py:540`, `doctor.py:786`, `cross_project_digest.py:373` | `open_readonly_unit_store` or `collection_metadata_rows` | Medium — not user Q&A but health/digest reads |
| CLI related (non-MCP) | `convmem.py:1276` | `open_readonly_unit_store` | Low-Medium |

`chroma_readonly._connect_readonly` is inventory-classified as `core-storage` (`chroma_readonly.py:14-19`). CG-2's `ServingIndexRepository` should treat **both** `ChromaStore` vector queries and readonly SQLite metadata walks as behind the same authority gate — otherwise `query.py` fallback becomes an authority bypass.

**No unexpected `PersistentClient` production bypasses** beyond `chroma_store.py` (inventory `core-storage`).

---

## 4. Serving boundary assessment

**Verdict: Wrappable with bounded refactor** — not a rewrite of `ChromaStore` internals; requires a **facade + dependency injection** pass across call sites.

### Can `ChromaStore` be composed without rewriting internals?

**Yes.** `ChromaStore` already exposes `query_units`, `query_summaries`, `units_metadata`, context-manager `close`, and collection accessors. A repository can:

1. Resolve request-frozen authority once.
2. Delegate vector reads to `open_chroma_for_read` / `ChromaStore` with generation filters (or legacy mode).
3. Optionally route metadata-only reads through the same authority policy.

No need to fork Chroma client code.

### `query.py` injection points

**Multiple call sites, one logical boundary:**

- `query_units` — single try/except block around `open_chroma_for_read` (`query.py:412-436`)
- `query_raw` — parallel block (`515-530`)
- `_fallback_query_rows` — separate SQLite path; must be **inside** repository or forbidden when authority mode is generational

A factory injected at module level (or passed `cfg`) can replace three direct opens with one repository instance per request.

### Broad-exception fallback narrowing

**Feasible without full error-handling rewrite.** Today `except Exception` at `query.py:428` and `523` treats contention, authority, and corruption identically. CG-2 needs:

- Typed exceptions for authority / fence / stale-generation (`GenerationReadError`, pointer errors already exist in CG-1 modules)
- Fallback permitted only for **transient Chroma contention** (reuse `is_chroma_contention_error` pattern from `chroma_store.py:74-76`)

This is localized surgery (~two except blocks + repository API), not a query rewrite.

### `--raw` summary search

**Same boundary as `query_raw`.** `convmem search --raw` → `query_raw` → `open_chroma_for_read` / fallback (`convmem.py:129`, `query.py:499-535`). No separate hidden Chroma path.

### MCP `related` / `stats`

**Direct `ChromaStore` today — must be rewired.** `mcp_server.py:897` and `944` bypass `query.py`. Repository injection in MCP layer is straightforward (same pattern as `query_units`).

---

## 5. Ingest/watch hooks assessment

**Verdict: Partial — major new mechanism needed for §7.1 reconciliation.**

| Hook | Current state | Gap |
|---|---|---|
| `IN_Q_OVERFLOW` / overflow signal | **Missing** | `watch.py` uses `watchdog.Observer` + in-process batch list (`334-357`). No queue depth or overflow export. Linux inotify overflow is not surfaced. |
| Startup reconciliation | **Missing** | `run_watch` starts observer only (`359+`). No full corpus manifest scan on boot. |
| Periodic/timer reconciliation | **Missing** | Debounce scheduler only; no ratified periodic scan. Would need new timer (systemd sidecar, watch loop tick, or separate service). |
| Reconciliation-enqueued ingest | **Partial** | Watch → `DebounceScheduler` → spawns `convmem index --file` (`watch.py` pattern). Same subprocess path could accept reconciliation jobs, but **no distinct admission class** or bounded bulk policy exists today. |
| Source-hash mechanism | **Partial / different model** | Ingest uses `sha256_file` content hash + `processed.json` path keys (`ingest.py:226-420`, `watch_skip_reason`). CG-2 needs **canonical source path owner key** + manifest `source_hash` at promotion — not wired to watch/ingest. |

Existing pieces that help: path-based skip logic (`watch_skip_reason`), exclusive processed-state lock (`ingest.py:104-125`), file hash idempotency. These are **inputs** to reconciliation but not a reconciliation engine.

---

## 6. Authority-resolution integration assessment

**Verdict: Clear integration point — new layer above `open_chroma_for_read`, pattern transfers from `FileGenerationStore`.**

### Where resolution happens

**Recommended:** At the start of each serving request (CLI search, ask retrieval, MCP tool), **before** any Chroma/SQLite open:

```
resolve_authority(cfg) → frozen AuthorityVector
repository = ServingIndexRepository(cfg, authority=frozen)
repository.query_units(...)
```

Not inside `ChromaStore.__init__` (keeps store reusable for admin/shadow paths).

### `FileGenerationStore` active-map pattern

**Transfers directly.** `FileGenerationStore.__init__` takes `active_generations: Callable[[], Mapping[str, str]]` (`file_generation_store.py:87-91`). Production can supply a closure reading pointer + fence artifacts per owner. Request-freezing is already demonstrated in `_get_rows` (single `dict(self._active_generations())` snapshot).

### Lock duration during query

**Evidence reads can be short.** Pointer/manifest/fence reads are file/small-store operations; frozen vector is immutable for request lifetime. Long Chroma vector query runs **without** holding pointer locks — matches architecture §5.1 seqlock-like pattern. `publish_active_pointer` already enforces fresh-process cold validation (`file_generation_pointer.py:400+`).

---

## 7. Overall risk summary

| Area | Difficulty | Notes |
|---|---|---|
| CG-1 substrate reuse | **Easy** | Modules on `main`; hermetic tests prove semantics |
| Global serving repository (legacy mode first) | **Medium** | Facade + inject at ~6–10 call sites; inventory + readonly helpers |
| Narrowing query fallback | **Medium** | Two except blocks; must not ship generational mode until fallback is authority-aware |
| MCP direct bypasses | **Easy** | Two functions, straightforward wiring |
| `projection_parity` / doctor drift semantics | **Medium** | Needs generation-aware keys and health accounting (architecture already flags) |
| Source reconciliation (§7.1) | **Hard** | New subsystem: startup scan, overflow handling, periodic cadence, bounded admission |
| Watch/ingest promotion guards | **Hard** | Bridge `processed.json` world to owner/manifest `source_hash` |
| Formal model / canary | **Out of scope** | Feasibility does not block; execution gated separately |

**Nothing structurally blocks CG-2** at `1222b1e`. The highest implementation risk is **accidentally leaving a readonly SQLite or keyword-fallback path ungated** — the inventory's four bypass sites are necessary but not sufficient for "zero serving bypasses."

---

## 8. SHA confirmation

This verdict applies **only** to architecture revision:

`1222b1ede2d6cc5da582388768f06d60b36c5e50`

If the architecture bytes change, this review is stale and must be re-run.

---

## Forward announcement

```
I finished: CG-2 implementation feasibility review (PASS WITH RISKS)
Next step:  Crush evidence/failure review (parallel); then Codex formal model if both PASS
Next lane:  Crush + Codex; Ryan Architecture HITL after reviewer dispositions
See my work: docs/inter-model/CURSOR-2026-08-14-cg2-feasibility-review.md on branch docs/2026-08-14-cg2-feasibility-review
```
