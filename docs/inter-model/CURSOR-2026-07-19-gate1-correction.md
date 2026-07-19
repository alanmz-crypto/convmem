# Cursor → Codex / Ryan: Gate 1 correction — Codex PASS, merge pending

**To:** Ryan (squash-merge), Codex (complete)
**From:** Cursor
**Date:** 2026-07-19
**Branch:** `feat/2026-07-19-embed-eval-harness`
**Tip:** `dbac4327a52b13e918a72e0a633deb496fb11834`
**PR:** [#44](https://github.com/alanmz-crypto/convmem/pull/44) — mergeable/CLEAN
**Runbook:** [`docs/plans/EXECUTION-embedding-model-eval.md`](../plans/EXECUTION-embedding-model-eval.md)

**Live ops:** `convmem brief` only. Do not treat this post as corpus truth.

---

## TL;DR

- Codex verification **PASS** on tip `dbac432` (doctor catch-all + schema-incompatible SQLite WARN regression).
- PR #44 is ready for Ryan’s **squash merge**; pin the resulting merge SHA as the immutable Gate 1 harness version.
- Gate 2 remains **blocked** — no real 25–40-query pilot / live capture/eval until Ryan authorizes.
- Methodology data stays **schema fixtures only**.

---

## Status (final for Gate 1 tip)

| Check | Result |
|-------|--------|
| Codex independent diff | PASS — tip contains only intended doctor + regression-test correction vs prior green tip |
| Focused identity tests | 2 passed |
| Doctor suite | 60 passed |
| Full pytest | 626 passed, 45 subtests |
| `git diff --check origin/main...HEAD` | clean |
| PR #44 head | matches `dbac432`; mergeable/CLEAN |
| CI | pylint pass; Approval Agent pass; Bugbot skipped (stale human-review request superseded by Codex) |

## Final correction on this tip (`dbac432`)

Restored intentional containment in `doctor._check_embed_collection_identity`:

```python
except Exception as exc:  # pylint: disable=broad-exception-caught
```

Regression: temporary schema-incompatible `chroma.sqlite3` (no `collection_metadata`) returns WARN rather than raising (`sqlite3.OperationalError`).

## Earlier Gate 1 deliveries (on branch; squash will collapse history)

| Constraint | Delivery |
|------------|----------|
| C1 SQLite-preserving fallback | Wrong-dim fake embed; `fallback_exercised` only on sentinel hit |
| C2 Isolation ≠ latency workers | One-shot isolation workers; long-lived warm latency (5+20, counterbalanced); startup ms separate |
| C3 Operation-specific binders | Per-op exact fields; external `.approved.sha256`; real acceptance forced |
| C4 Isolation evidence | Shadow fake vs live-canary (zero); unreachable live paths; worker identity banner |
| C5 Schema ≠ real pilot | `eval_schema_*` / `eval_methodology_schema_*`; real pilot deferred |
| Provenance gate | Metadata + actual ID set / row count pre-worker; build-result identity in real mode |
| Real compare binding | `mode=subprocess` required; evidence controls bound or rejected |

## Ask of Ryan

1. Squash-merge PR #44.
2. Pin the resulting merge SHA as the immutable Gate 1 harness version.
3. Do **not** treat this as Gate 2 authorization.

## Out of scope here

- Real corpus capture / shadow / Ollama model ops
- Preparing the real 25–40-query pilot (post-merge / pre-Gate 2 prep)
- Gate 2 authorization

---

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| Gate 1 | Approve completed evaluator harness (code/tests/fixtures); no live capture/eval |
| Gate 2 | Human review of first real comparison evidence; never auto-promotion |
| run-manifest | Mechanical authorization file; real mode needs external approval sidecar SHA |
| binder | Per-operation exact runtime-field check (missing/extra/mismatch → refuse) |
| methodology schema fixture | Synthetic categorized queries for reporting tests — not real corpus evaluation |
| `fallback_exercised` | Report flag set only when fallback-only sentinel is returned after forced vector failure |
