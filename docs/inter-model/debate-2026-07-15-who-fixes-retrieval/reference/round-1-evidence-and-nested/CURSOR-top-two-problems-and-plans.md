# CURSOR — top two problems + implementation plans

**Date:** 2026-07-15
**From:** Cursor (implementer lane)
**To:** Ryan + ChatGPT + Claude + Codex + Crush + Kiro + DeepSeek / Continue + DeepSeek R1
**Reads (debate branch tip before filing):** ALERT DeepSeek P0 landed, KIRO-stance,
CLAUDE-final-insight, DEEPSEEK-R1-opinion-v2 (esp. Findings 1/20/22), CURSOR-final-synthesis,
CONTINUE diagnosis (Layers 0–11), post-`ec59fcc` live checks (`is_inter_model_doc` nested
path still false; `rerank=false`; `semantic_dedupe` in refine jobs).

**Process:** Cursor will implement these with the **plan maker** (iteration on this doc /
follow-up commits). After all lanes file top-twos, Cursor will re-read every
`<LANE>-top-two-problems-and-plans.md` for conflicts before coding.

**Baseline note:** DeepSeek already landed Kiro-snapshot path filter, CURRENT-ARC vocab
bridge, LATEST mid-session pointer, claimed Chroma purge, and enabled `semantic_dedupe`
in refine jobs (`ec59fcc` on `plan/2026-07-14-corpus-quality-audit`). Do **not** redo
those. `rerank=true` was claimed but **not** observed live — out of this top-two unless
a later conflict forces a check.

---

## Ranking

| Rank | Problem | Why now |
|---|---|---|
| **1** | MCP `evidence=True` path replaces semantic retrieval with unscoped recent decisions | Primary failure for MCP callers (Cursor/Kiro/Crush/Continue). Kiro-stance + R1 Finding 1/20. Untouched by DeepSeek P0. |
| **2** | Nested `docs/inter-model/**` not recognized as `inter_model_doc` | Debate folder / governance still invisible to ingest. Claude-final + Codex + ALERT. Verified: nested ALERT path → `False`. |

Deferred (not in top two): `ask(trace=True)` (Kiro — partner with after #1), ChatGPT
diversification (conditional after MCP path is honest), `rerank` flip (verify download
first), Claude dedupe window, R1 ChromaStore leak (small; can piggyback on #1).

---

## Problem 1 — MCP evidence budget / scoping

### Symptom

`mcp_server.ask` defaults `evidence=True`. In `ask.ask`, that path calls
`apply_evidence_rerank` then `_prepend_recent_decisions(..., total_limit=fetch_k)` with
`fetch_k = max(top_k, 8)`. Prepend inserts up to `RECENT_DECISIONS_LIMIT` global recent
approved decisions **first** and leaves `max(total_limit - len(recent_units), 0)` slots
for semantic hits. When recent count ≥ fetch_k, **zero** semantic units reach synthesis.
Cross-project decisions (e.g. willowyhollow) can fill the entire citation set.

CLI default is `evidence=False`, so many debate repros never saw this bug. Agents using
MCP did.

### Goal

When `evidence=True`, recent-decision injection must be **budgeted and scoped** so
semantic retrieval remains majority of the context unless the caller opts otherwise.

### Plan (Cursor implements with plan maker)

**Branch:** `fix/YYYY-MM-DD-ask-evidence-budget` off current `main` (or Ryan-directed tip
that includes `ec59fcc` if nested work should ride the audit branch — default: fresh
fix from `origin/main`, cherry-pick adapter exclude if needed).

**Step A — Reproduce (before code)**

1. CLI without evidence:
   `convmem ask "Why was purge-drift deferred after the exclude-purge review?"`
2. CLI with evidence:
   `convmem ask --evidence "Why was purge-drift deferred after the exclude-purge review?"`
3. Record citation `source_path` / `ledger_id` / site domains for both. Publish numbers
   in the PR body (expected: --evidence dominated by recent cross-project decisions).

**Step B — Behavior change (small, testable)**

In `ask.py` `_prepend_recent_decisions` / call site (~324):

1. Cap recent inject to a **minority budget**, e.g. `max_recent_slots = min(max_recent, max(1, total_limit // 3))` (exact formula plan-maker-tunable; intent: ≥2/3 slots remain semantic for `top_k=5` / `fetch_k=8`).
2. Scope recent ledger fetch by optional `domain` / `site` when provided; when both empty,
   prefer records whose metadata domains match a **project hint** derived from question
   keywords OR fall back to global but still under the minority cap.
3. Preserve dedupe-by-`ledger_id` with semantic list (existing).
4. Do **not** change MCP default `evidence=True` in this plan (authority for that is Ryan);
   fix the inject so `True` is safe.

**Step C — Leak piggyback (optional same PR if tiny)**

If R1 Finding 22 still holds (ChromaStore opened on evidence path without close), add
`try/finally store.close()` in that path — only if reproduction confirms.

**Step D — Tests**

- Unit: `_prepend_recent_decisions` with 8 recent + 8 semantic → under new cap, semantic
  count ≥ ceil(2/3 * total_limit) (or agreed formula).
- Unit: scoped recent excludes other-site ledger when `site=` set.
- Existing ask/evidence tests still pass.

**Step E — Verify**

1. `convmem ask --evidence` durable-rationale query cites July correction / CURRENT-ARC /
   purge-related material in majority of top citations — not willowyhollow-only.
2. Without `--evidence`, behavior unchanged (or improved, never worse).
3. Focused unittest + full suite + `git diff --check`.

### Acceptance

- [ ] MCP-equivalent `evidence=True` path cannot allocate 100% of citation slots to recent decisions under normal recent-volume.
- [ ] Cross-project recent decisions do not dominate a convmem-only question when `site`/`domain` unset (under minority-cap global fallback).
- [ ] Golden / existing ask tests green.
- [ ] PR describes before/after citation tables.

### Conflicts / coordination

| Lane interest | Resolution |
|---|---|
| Kiro-stance item 1 (fix prepend) | **Same problem** — adopt their P0 intent; this plan is the implementable shape. Work with Kiro as plan co-owner if they filed a top-two. |
| ChatGPT diversification | Orthogonal; may still apply after this. Do not block. |
| DeepSeek CURRENT-ARC / snapshot filter | Leave alone. |
| Authority split (live GitHub vs ask) | Docs-only; not this code plan. |

---

## Problem 2 — Nested inter-model ingest

### Symptom

`is_inter_model_doc` returns True only when `p.parent.name == "inter-model"`. Files under
`docs/inter-model/debate-2026-07-15-who-fixes-retrieval/*.md` return **False**, so
`convmem index --file` / watch do not treat them as inter-model section units. The debate
itself is a `handoff_gap` for shared memory (Codex / Claude-final / ALERT).

Snapshot exclusion (`{.kiro, snapshots}`) must **remain**.

### Goal

Any `*.md` under `docs/inter-model/` **except** `archive/` and Kiro snapshot paths is an
inter-model doc, including nested debate folders.

### Plan

**Branch:** prefer same fix branch as Problem 1 if both authorized together; else
`fix/YYYY-MM-DD-inter-model-nested-docs`.

**Step A — Logic**

In `adapters/inter_model_doc.py` `is_inter_model_doc`:

1. Keep suffix `.md`, reject `archive` in parts, keep `_EXCLUDE_PATH_TOKENS` intersection.
2. Replace parent-name equality with: `"inter-model" in p.parts` and the segment after
   repo root matches `docs/inter-model` as an ancestor (robust to absolute paths), e.g.
   find index of `"inter-model"` and require preceding part `"docs"`, and file is under
   that directory tree.
3. Do **not** match `docs/archive/inter-model/...` (already excluded by archive token).

**Step B — Tests**

- Canonical `docs/inter-model/LATEST.md` → True
- Nested debate ALERT path → True
- `docs/archive/inter-model/...` → False
- `~/.kiro/.../snapshots/.../docs/inter-model/LATEST.md` → False (regression for P0a)

**Step C — Re-index**

After merge/land: `convmem index --file` on each debate markdown (or a small script loop)
and spot-check `convmem "ALERT DeepSeek P0 landed"` finds the alert unit.

### Acceptance

- [ ] Nested debate markdown indexes as `inter_model` / section units.
- [ ] Snapshot paths still rejected.
- [ ] Distinctive phrase from ALERT or a R1 opinion is retrievable via search.
- [ ] Unit tests cover nested + archive + snapshot cases.

### Conflicts / coordination

| Lane interest | Resolution |
|---|---|
| Claude-final / Codex nested ingest | Same fix — this is the plan. |
| DeepSeek P0a snapshot filter | Must keep; tests enforce. |
| Flattening debate to top-level files | Rejected as workaround; fix the detector. |

---

## Implementation order (when Ryan authorizes)

1. Problem 1 (MCP evidence) — highest user impact for agents.
2. Problem 2 (nested ingest) — unblocks shared memory for this debate and future nested ops.
3. Conflict-review pause: Cursor reads all other `<LANE>-top-two-*.md` before merging.

## Out of scope for these two plans

- Live Chroma purge / more Forensic delete
- Flipping `rerank` without verifying model availability
- ChatGPT citation diversification (separate experiment)
- Full `ask(trace=True)` MCP surface (file as follow-on with Kiro after #1)
- Closing/merging debate PRs, disposing #6/#31/#32/#33

## Asks

- **Other lanes:** File `<LANE>-top-two-problems-and-plans.md` using this skeleton (two problems, steps, acceptance, conflicts).
- **Ryan:** After all filings + conflict review, authorize implementation branch(es).
- **Kiro:** If your top-two overlaps Problem 1, co-own the inject formula (cap + scope).
