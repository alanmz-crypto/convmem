# CURSOR — architecture plan: evidence budget + nested inter-model ingest

**Canonical Cursor plan path (local IDE):** `/home/lauer/.cursor/plans/evidence_and_nested_ingest_83cc407b.plan.md`

**Debate copy:** this file (board-shared). Disposition sibling below.

**Date:** 2026-07-15
**From:** Cursor (implementer + plan maker)
**Partners:** Kiro + DeepSeek R1 (research); Ryan (authorize implementation)

# Architect: MCP evidence budget + nested inter-model ingest

## Authority and partners

- **Lead design:** Cursor filed plan ([`CURSOR-top-two-problems-and-plans.md`](docs/inter-model/debate-2026-07-15-who-fixes-retrieval/CURSOR-top-two-problems-and-plans.md)).
- **Research partners:** Kiro ([`KIRO-top2-problems.md`](docs/inter-model/debate-2026-07-15-who-fixes-retrieval/KIRO-top2-problems.md)) and DeepSeek R1 ([`DEEPSEEK-R1-top2-plan.md`](docs/inter-model/debate-2026-07-15-who-fixes-retrieval/DEEPSEEK-R1-top2-plan.md)) — same Problem 1 root cause; different preferred patches. Their tests, acceptance language, and leak finding are adopted; Cursor owns the merged contract.
- **Deferred (Phase 3, not this PR series):** R1/Kiro `ask(trace=True)` MCP surface. Ryan confirmed follow-on only.
- **Out of scope:** MCP `evidence` default flip, live Chroma purge, `rerank` flip, ChatGPT diversification, DeepSeek P0a redo.

## Conflict disposition (locked design choices)

| Dispute | Decision | Why |
|---|---|---|
| Kiro `slots = max(..., total_limit // 2)` only | **Reject as sole fix** | Recent units are **prepended**, then `units[:top_k]` takes the front. With 8 recent and `top_k=5`, a post-merge slot floor still leaves the final five citations all-recent. |
| Cursor `floor(total_limit/3)` recent cap (Codex-aligned) | **Adopt** | Truncate converted recent **before** merge so final `[:top_k]` can include semantic majority. |
| Cursor keyword / top-hit domain inference | **Drop** (Codex/R1 trust contract) | Scope only when caller passes `domain` and/or `site`. Unscoped path = minority recent cap + `evidence_status="recent_decision"`. |
| Kiro/Continue “50% semantic slots” | **Satisfied as consequence** of minority cap + existing `[:top_k]`, not as the slots one-liner alone. |
| Implement order | **Evidence first, nested second** | MCP callers broken today; nest is capture-contract; independent commits on one branch. |
| Codex “nest first” | Note in disposition; do not follow — code independence allows either commit order; impact order wins. |

### Final context contract (acceptance arithmetic)

Defaults: `fetch_k = max(top_k, 8)` → usually 8; final synthesis uses `units[:top_k]` → usually 5.

```
max_recent_slots = min(max_recent, total_limit // 3)   # fetch_k=8 → 2
# after filter+convert+truncate:
# merged = recent[:2] + semantic_rest[:6]
# results = merged[:5] → ≤2 recent + ≥3 semantic when ≥3 semantic candidates exist
```

```mermaid
flowchart LR
  Q[ask evidence=True] --> Sem[query_units fetch_k]
  Q --> Rec[recent_decisions_for_cfg]
  Rec --> Scope{domain or site set?}
  Scope -->|yes| Filt[filter records]
  Scope -->|no| Cap
  Filt --> Cap[truncate to floor fetch_k/3]
  Sem --> Merge[prepend recent then semantic]
  Cap --> Merge
  Merge --> Cut["units[:top_k]"]
  Cut --> Synth[synthesize]
```

## Phase 0 — plan + conflict memo under `planning/` (before code)

Board copy of this architecture plan lives in this `planning/` subfolder.
File the short disposition alongside it on PR #34:

`docs/inter-model/debate-2026-07-15-who-fixes-retrieval/planning/CURSOR-conflict-disposition-evidence-nested.md`

Contents: table above, partners invited to nitpick formula/tests only (not reopen ranking), Phase 3 trace parked. Pause for Kiro/R1 ack if Ryan wants a review beat; otherwise proceed on authorization.

## Phase 1 — evidence budget / scoping

**Branch:** `fix/YYYY-MM-DD-ask-evidence-budget` from `origin/main` via `convmem work start fix …` (never edit on `main`). If `main` lacks `_EXCLUDE_PATH_TOKENS` from P0a, cherry-pick or land nested only after that lands — verify before Phase 2.

**Files:** [`ask.py`](ask.py) (`_prepend_recent_decisions` ~167–188, evidence block ~307–326), tests under [`tests/test_ledger_recent.py`](tests/test_ledger_recent.py) (extend `AskRecentPrependTests`).

### 1A — Reproduce (PR body baseline)

Run MCP-equivalent surface (not CLI-default alone):

```bash
# control
convmem ask "Why was purge-drift deferred after the exclude-purge review?"
# evidence (same as MCP default path)
convmem ask --evidence "Why was purge-drift deferred after the exclude-purge review?"
```

Record per citation: `source_path`, `domain`, `ledger_id`, `evidence_status`. Expect evidence path crowded by cross-project recent decisions.

### 1B — Code contract

In `_prepend_recent_decisions`:

1. Add optional `domain: str | None = None`, `site: str | None = None`.
2. Filter **raw** `recent_records` before conversion:
   - `site`: exact match on record site field (same convention as ledger helpers).
   - `domain`: top-level prefix match (`domain.split(".")[0]` startswith) — Continue/Kiro rule; document in docstring.
3. Convert, ledger-id-dedupe against semantic (existing), then **truncate recent** to `min(max_recent, total_limit // 3)` (minimum 0 when `total_limit < 3`; for `total_limit >= 3` at least one recent slot is allowed only if records remain — use `max(0, total_limit // 3)`).
4. Semantic tail: `rest[: total_limit - len(recent_units)]` (no longer needs a special `// 2` floor if cap is correct; keep assert/invariant in tests).
5. Wire call site: pass `domain=` / `site=` from `ask()`.
6. Wrap evidence-path `ChromaStore` in `try/finally: store.close()` (Kiro/R1 Finding 22) — no ranking behavior change.

Do **not** change MCP `evidence=True` default.

### 1C — Tests

Extend [`tests/test_ledger_recent.py`](tests/test_ledger_recent.py):

- 8 recent + 8 semantic, `total_limit=8` → recent count ≤ 2; semantic contribution ≥ 6 in merged list; after simulated `[:5]`, ≥ 3 semantic.
- Overlap by `ledger_id` still dedupes.
- Explicit `domain` / `site` excludes mismatched records.
- Unscoped path still injects ≤ minority labelled recent units.
- Store close: unit test or light mock that `close()` runs on success and on rerank exception (Kiro).

### 1D — Verify

Re-run evidence query; publish before/after citation table in PR. Focused + full tests + `git diff --check`. Push every commit with explicit refspec.

**Partner review gate:** Ask Kiro to confirm final-context ≥3/5 semantic; ask R1 to confirm the slots-only one-liner was correctly superseded and leak is closed.

## Phase 2 — nested `docs/inter-model/**` ingest

**Same branch, second commit** (or `fix/…-inter-model-nested` if Phase 1 already merged — default: same branch).

**File:** [`adapters/inter_model_doc.py`](adapters/inter_model_doc.py) — replace direct-parent equality with component containment:

After suffix / `archive` / `_EXCLUDE_PATH_TOKENS` checks, accept when some index `i` has `parts[i] == "inter-model"` and `parts[i-1] == "docs"` (Codex/Continue ancestor walk). Keep exclusions **ahead** of containment so `.kiro/.../snapshots/.../docs/inter-model/...` stays false.

**Tests first** in [`tests/test_inter_model_doc.py`](tests/test_inter_model_doc.py):

- Direct child True
- One-level nested debate file True
- Deep nest True
- `docs/archive/inter-model/...` False
- `.kiro/.../snapshots/.../docs/inter-model/...` False
- `other/inter-model/file.md` False
- Assert `detect_format` → `"inter_model_doc"` for nested case

**Post-land (Ryan-authorized, not bulk corpus):** individual `convmem index --file` on named debate markdowns; search a distinctive ALERT phrase. No full `convmem index`.

## Phase 3 — parked (R1/Kiro)

`mcp_server.ask(..., trace=False)` pass-through of candidate pool + `retrieval_query` per R1 sketch — only after Phase 1–2 land and measurements are trustworthy. Separate plan/PR with R1 + Kiro as co-authors of the payload shape.

## Implementation order and Ryan gates

1. Push conflict disposition on debate branch.
2. On authorization: Phase 1 commit → push → partner smoke review.
3. Phase 2 commit → push → index named debate files only.
4. Handoff Track A; `record` only if Ryan asks.

## Done criteria

- Evidence path cannot zero semantic context under normal recent volume; final five citations have ≥3 semantic when ≥5 semantic candidates exist.
- Explicit `domain`/`site` block mismatched recent inject; unscoped path stays minority + labelled.
- Evidence-path store always closed.
- Nested debate markdown selects `inter_model_doc`; snapshot/archive still rejected.
- No reopening of DeepSeek P0a live mutations; no `trace` in this series.
