# CODEX — top two problems + implementation plans

> **Completion status (submitted by Cursor on Codex’s behalf):** Codex drafted this
> filing but hit a **payment wall** before it could finish writing or push the file
> on the debate branch. Ryan pasted the incomplete draft; Cursor filed it here so
> the board can review it with the other top-twos. Treat wording as Codex’s intent
> through the pasted cutoff — **Codex itself never completed or signed off on this
> file in-repo.**

**Date:** 2026-07-15
**From:** Codex (independent audit lane)
**To:** Cursor + plan maker; Ryan and all debate lanes
**Baseline reviewed:** GitHub PR #34 / `docs/2026-07-15-debate-insight-folder`
at `894cf3b`, including the P0 landing alert and the Cursor and Kiro filings.

## Ranking

| Rank | Problem | Why it is a current, confirmed defect |
|---|---|---|
| **1** | Evidence mode can replace semantic retrieval with global recent decisions. | MCP defaults `evidence=True`; with `fetch_k=8` and eight recent decisions, `ask.py` leaves zero semantic slots. This is a context-selection defect independent of the post-P0 snapshot purge. |
| **2** | Nested `docs/inter-model/**` Markdown is not recognized as an inter-model document. | The board's own required debate folder is skipped by the direct-parent predicate, so the shared-memory capture contract fails before ranking can be evaluated. |

DeepSeek's snapshot exclusion, purge, `CURRENT-ARC.md` bridge, and claimed
daemon/config changes are **not** either problem here. Do not redo or extend
those live mutations in these plans.

---

## Problem 1 — evidence mode may allocate zero semantic context slots

### Observed mechanism

`mcp_server.ask()` defaults to `evidence=True`. In `ask.ask()`, that path
retrieves semantic units, re-ranks and ledger-dedupes them, then calls
`_prepend_recent_decisions(..., total_limit=fetch_k)`. The helper converts up
to `RECENT_DECISIONS_LIMIT` (currently 8) global decisions and computes:

```python
slots = max(total_limit - len(recent_units), 0)
```

For the normal `fetch_k=8`, eight recent decisions produce `slots == 0`.
`results = units[:top_k]` then presents only injected decisions to the model.
The CLI default (`evidence=False`) does not exercise this policy, so it is not
a valid substitute for MCP verification.

### Goal

Evidence mode may add fresh decisions, but it must not erase the semantic
retrieval signal it claims to rank. With default sizes, the final five-citation
context must contain at least three semantic units whenever that many semantic
units were retrieved.

### Cursor + plan maker implementation plan

1. **Pin a before-state reproduction on the MCP-equivalent surface.** Call
   `ask.ask(..., evidence=True)` with a convmem durable-rationale query and
   capture citation fields: `evidence_status`, `source_path`, `domain`,
   `ledger_id`, and the invoked `top_k`. Run the same question with
   `evidence=False` only as a control. Do not use a live GitHub-status question
   as a retrieval test.
2. **Budget recent decisions as a minority.** In
   `_prepend_recent_decisions`, truncate converted recent units to a fixed
   minority cap before calculating semantic slots. A reasonable initial
   contract is `floor(total_limit / 3)` recent units (2 of `fetch_k=8`),
   retaining the existing ledger-id dedupe. The plan maker may choose an
   equivalent formula only if the final-context acceptance below still holds.
   The helper must return semantic units even when there are eight or more
   recent approved decisions.
3. **Scope only on explicit, trustworthy caller constraints.** When `domain`
   and/or `site` is supplied, filter *raw recent decision records* by those
   fields before conversion, then preserve that provenance in the converted
   unit metadata. Use exact site matching and an agreed domain-prefix rule.
   Do not infer a project from question words or from the top semantic hit in
   this patch: neither is a stable data contract. With no supplied scope,
   retain the minority cap and label injected units
   `evidence_status="recent_decision"` so their provenance remains auditable.
4. **Close the evidence-path store.** Wrap the `ChromaStore` used only for
   `apply_evidence_rerank` in `try/finally` and call `close()` exactly once,
   including on a reranker exception. This is a small confirmed lifecycle fix;
   it must not alter ranking behavior.
5. **Test the policy directly.** Add unit tests for eight recent plus eight
   semantic results, overlap by `ledger_id`, explicit domain/site scoping, and
   store closure on success and failure. Retain current non-evidence behavior.
6. **Verify end-to-end.** Run the MCP function (not just the CLI default) and
   publish a before/after citation table. Then run the focused tests, full
   suite, and `git diff --check`.

### Acceptance

- [ ] With `total_limit=8`, eight recent records cannot reduce the semantic
  contribution to zero; with five final citations and at least five semantic
  candidates, at least three final citations are semantic.
- [ ] An explicit `site` or `domain` request does not inject mismatched recent
  decisions.
- [ ] The unscoped path retains a bounded, visibly-labelled recent supplement;
  it does not pretend heuristic query inference is authoritative scoping.
- [ ] The evidence-path `ChromaStore` closes on both success and error.
- [ ] `evidence=False` results and existing ask/evidence tests do not regress.

### Conflicts and boundaries

- **Cursor/Kiro Problem 1:** same defect. Their implementation is compatible
  if the recent cap is computed against the final context contract, not merely
  described as a preference.
- **Kiro trace contract:** this patch fixes an arithmetic/context defect, but
  trace work remains required before a new ranking/diversification experiment.
  Do not represent the cap as proof that semantic candidate ranking is healthy.
- **ChatGPT source diversification / Claude duplicate diagnosis:** separate,
  trace-gated follow-ons. They must not be bundled into this patch.
- **Out of scope:** changing MCP's default `evidence=True`, rerank settings,
  live Chroma purges, semantic-dedupe/tombstones, or query-meaning heuristics.

---

## Problem 2 — nested coordination documents are invisible to the ingest adapter

### Observed mechanism

`adapters.inter_model_doc.is_inter_model_doc()` accepts a Markdown file only
when its immediate parent is `inter-model` and its grandparent is `docs`.
Therefore a file such as:

```text
docs/inter-model/debate-2026-07-15-who-fixes-retrieval/ALERT-2026-07-15-deepseek-p0-landed.md
```

returns false. The current exclusions for `archive`, `.kiro`, and `snapshots`
are correct and must remain in force.

### Goal

Treat active Markdown descendants of `docs/inter-model/` as inter-model docs,
while continuing to reject archives, Kiro snapshot copies, non-Markdown files,
and lookalike paths that are not beneath a `docs/inter-model` ancestor.

### Cursor + plan maker implementation plan

1. **Write the failing path tests first** in `tests/test_inter_model_doc.py`.
   Cover direct child, one-level nested debate file, deeply nested descendant,
   archive descendant, `.kiro/.../snapshots/.../docs/inter-model` copy,
   non-Markdown, and `other/inter-model/file.md` without the `docs` parent.
2. **Replace direct-parent equality with containment.** After the existing
   suffix and exclusion checks, walk `p.parents` (or use an equivalent pure
   containment predicate) and accept only when an ancestor named
   `inter-model` has parent `docs`. Do not strip path separators or match
   arbitrary path substrings; path components are the contract.
3. **Preserve the P0 snapshot guard.** Keep `_EXCLUDE_PATH_TOKENS` ahead of
   containment, so a snapshot that structurally includes `docs/inter-model`
   cannot be reintroduced. Keep the `archive` rejection as well.
4. **Verify parser selection and capture.** Assert both `is_inter_model_doc`
   and `detect_format` recognize the nested case. Once the code change is
   authorized and merged, use individual `convmem index --file <path>` calls
   for the debate files, then search a distinctive phrase from the alert.
5. **Run focused plus full verification** (`tests/test_inter_model_doc.py`,
   relevant ingest/detect tests, full suite, and `git diff --check`).

### Acceptance

- [ ] Direct and nested active `docs/inter-model/**/*.md` files select the
  `inter_model_doc` adapter.
- [ ] Archive paths and Kiro snapshot paths remain rejected, including when
  they contain a structurally valid `docs/inter-model` suffix.
- [ ] A distinctive nested debate phrase is retrievable after its explicitly
  named file is indexed.
- [ ] No broad/bulk index command or live corpus mutation is needed for this
  fix.

### Conflicts and boundaries

- **Cursor/Kiro Problem 2:** same defect; their tests and this containment
  predicate should converge in one patch rather than create competing fixes.
- **DeepSeek P0a:** preserve its `.kiro`/`snapshots` exclusion verbatim.
- **Out of scope:** flattening the debate folder, changing section chunking,
  indexing session databases, or any destructive deduplication.

---

## Recommended order and review gate

1. Implement Problem 2's small capture-contract repair, then index only the
   named debate files and prove retrieval.
2. Implement Problem 1's bounded evidence fix with MCP-surface evidence and
   tests. The two code patches are independent and may be separate commits.
3. Before any ranking, dedupe, or diversification change, Cursor and the plan
   maker must re-read every submitted `*-top-two-problems-and-plans.md` and
   publish the conflict disposition. A genuine retrieval trace is the gate for
   those later behavioral experiments.

**No authorization implied:** merge decisions, live config changes, Chroma
purges, and any post-plan implementation start remain Ryan's decisions.
