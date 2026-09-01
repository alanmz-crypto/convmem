# Implementation Handoff: Security-hardening branch review sign-off + two correctives

**Date:** 2026-09-01
**Author:** Kiro (design/review)
**For:** Codex Luna (implementation) — routed to Luna per Ryan 2026-09-01 (not Cursor)
**Authorization:** Ryan, 2026-09-01 (verbal — "using your best judgement make the decisions to complete this work"; then "give the two items to Luna")

---

## Luna invocation (read first)

Codex authored this hardening branch (`e4ae69d`), so these two correctives return to the
Codex/Luna lane. On this machine the `codex` CLI exposes a single model id (`gpt-5.6-luna`);
the tier is the reasoning effort, and the default config silently pins it to `low`. Set it
**explicitly**:

- **Recommended tier: T4** — `codex -m gpt-5.6-luna -c 'model_reasoning_effort="low"'`.
  Both correctives are well-scoped and mechanical (comment relabeling; removing one clamp and
  updating one test assertion). The spec below leaves no design judgement to the implementer.
- If the query-test rewrite (Corrective B) wants more headroom, T5 medium is available:
  `codex -m gpt-5.6-luna -c 'model_reasoning_effort="medium"'`.

Protocol reminders for the Luna session: push every commit with an explicit refspec to
`origin/fix/2026-09-01-security-hardening`; do not edit tracked files on `main`; do not touch
`origin/main` or force-push; if the sandbox blocks editing, identify the exact change and say
so — the shell lane will apply the mechanical commit. If a gate/test/lint fails twice, stop
and escalate the full state up the ladder rather than retrying.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` (Codex hardening on branch; two Kiro-decided correctives assigned to Luna) |
| **Branch** | `fix/2026-09-01-security-hardening` |
| **Tip SHA** | `d8aa057` (rebased hardening tip) + this handoff commit |
| **Push status** | `pushed to origin` |
| **Assigned to** | Codex Luna (T4 `low`; T5 `medium` if needed) |
| **PR** | `not opened` |
| **Ryan GATE** | none for the two correctives (routine-reversible). Ryan owns the eventual squash-merge. |
| **Track A ingest** | this Kiro session `messages.jsonl` (degraded — DeepSeek 401; watcher retries) |

---

## Review verdict (the sign-off part)

I reviewed `git diff b03a856..e4ae69d` (15 files, 446/72) against convmem's planned and
completed security work. Focused security suite re-run in the worktree: **50/50 pass**.

**Codex did NOT degrade planned or completed security work.** Specifically confirmed:

- **Writer-gate protocol untouched.** `chroma_writer_gate.lock` lives in
  `chroma_write_store.py` and uses `fcntl.flock` (LOCK_SH/LOCK_EX). The changed
  `process_lock.py` is a *different* mechanism, imported only by `watch.py` and `refine.py`.
  R2b / Shadow writer-gate work is unaffected.
- **`process_lock.py` hardening reuses convmem's own primitives** (`shadow_authorization.
  open_directory_nofollow` / `AuthorizationRefused`), adds O_EXCL + O_NOFOLLOW + 0600 +
  fsync + descriptor-relative cleanup. Equal-or-better than what existed; design-coherent.
- **`watch.py` timeout is additive** — the landed `_scoped_index_cmd` memory cap (PR #245)
  is preserved; the timeout wraps it. OOM error-passthrough behavior retained.
- **`ingest.py` / `chroma_store.py` / `ask.py`** — atomic processed-state write via the
  existing `atomic_write_text` helper; paged metadata read preserves superseded filtering;
  prompt-injection markers additive.
- **Base state clean.** The branch was originally based at `b03a856`; the remote branch has
  since been rebased onto current `main` (hardening tip `d8aa057`, content identical). The
  review was performed at the original `b03a856..e4ae69d` diff; the rebase preserved every
  hunk, and the corrective line numbers below still match the rebased tree.

Two items require correction before merge. Both are Kiro-decided below (Ryan authorized
best-judgement). **These two correctives are the only remaining implementation work.**

---

## What to build

Two small, reversible correctives on the same branch:

### Corrective A — de-ratify the watch subprocess timeout default

**Why this exists:** The timeout *mechanism* (Popen + `communicate(timeout=…)` +
process-group SIGTERM→SIGKILL) is approved — it is a secondary liveness backstop against a
*hung* child, distinct from the memory cap that handles OOM. The problem is only that a bare
`subprocess_timeout_seconds = 900` in `config.example.toml` reads as a **ratified/recommended
value**, which conflicts with the active watch-OOM guidance (the full-file-reindex design;
R2b v2 handoff states plainly "900 seconds is not ratified"). Keep the mechanism; stop the
docs/comment from implying 900s is tuned or endorsed.

### Corrective B — decouple the DoS bound from internal scoped over-fetch (fix recall regression)

**Why this exists:** `query.py` introduced `MAX_QUERY_FETCH = 300` and applied it to the
*internal* adaptive over-fetch inside `_fetch_scoped_units` (via `collection_bound`) and to
`scoped_fetch_k` on the keyword-fallback path. That internal over-fetch was never
caller-controlled — it is bounded by `count_units()` — so capping it at 300 buys **no**
additional DoS protection while **reducing recall** for sparse domain/site queries on the
33k-unit corpus (e.g. `web_stack.security` monitor queries, relocation-scope work). The DoS
concern is fully handled by `validate_top_k` (1–100) on the public `top_k`. Restore the
internal scoped fetch to grow up to collection size; keep the public cap on `top_k` /
`candidate_k` only.

---

## Integration point

### Corrective A

`watch.py:23` — timeout constant:

```python
_DEFAULT_INDEX_TIMEOUT_SECONDS = 15 * 60  # relabel as unratified interim backstop
```

`config.example.toml:62-63` — the commented block currently reads:

```toml
# Maximum runtime for one child index operation before the watcher releases it.
# subprocess_timeout_seconds = 900
```

### Corrective B

`query.py:280-285` — `_fetch_scoped_units`, `collection_bound`:

```python
    try:
        collection_bound = min(
            max(candidate_k, int(repo.count_units())), MAX_QUERY_FETCH
        )
    except Exception:  # pylint: disable=broad-exception-caught
        collection_bound = candidate_k
```

`query.py:489` — keyword-fallback scoped fetch:

```python
        scoped_fetch_k = min(candidate_k * 3, MAX_QUERY_FETCH)
```

---

## Specification

### Corrective A — behavior

1. Keep the timeout mechanism exactly as implemented (no logic change).
2. Change the `watch.py:23` comment to mark the constant as an **unratified interim liveness
   backstop**, not a tuned value — e.g.:

   ```python
   # Interim liveness backstop only (UNRATIFIED). The primary OOM control is the
   # per-child memory scope (_scoped_index_cmd). A tuned value awaits the watch-OOM
   # full-file-reindex design; do not treat 15*60 as endorsed.
   _DEFAULT_INDEX_TIMEOUT_SECONDS = 15 * 60
   ```

3. Rewrite the `config.example.toml` comment so the value cannot be read as recommended:

   ```toml
   # Interim liveness backstop for a HUNG (not memory-exceeding) index child.
   # UNRATIFIED placeholder — the per-child memory cap above is the primary OOM control,
   # and a tuned timeout awaits the watch-OOM design. Uncomment only to set an explicit
   # ceiling; the shipped default is an interim backstop, not a recommendation.
   # subprocess_timeout_seconds = 900
   ```

   Keep the line commented (default behavior unchanged). Do **not** invent a new numeric
   default here — the point is to stop implying 900s is ratified, not to ratify a different
   number.

### Corrective B — behavior

1. In `_fetch_scoped_units`, bound `collection_bound` by the collection size only (its
   pre-branch behavior), removing the `MAX_QUERY_FETCH` clamp:

   ```python
       try:
           collection_bound = max(candidate_k, int(repo.count_units()))
       except Exception:  # pylint: disable=broad-exception-caught
           collection_bound = candidate_k
   ```

2. On the keyword-fallback path, restore scoped over-fetch to `candidate_k * 3` without the
   `MAX_QUERY_FETCH` clamp:

   ```python
           scoped_fetch_k = candidate_k * 3
   ```

3. Keep `validate_top_k` (1–100) and the `candidate_k = min(..., MAX_QUERY_RESULTS)` cap at
   `query.py:479-481` — those are the real, caller-facing DoS bounds and must stay.
4. `MAX_QUERY_FETCH` may now be unused. Remove the constant if nothing else references it, or
   leave a one-line comment explaining it is retained only for the public-limit relationship.
   Confirm with `grep -n MAX_QUERY_FETCH query.py` after the edit.

### Output / contract

- Corrective A: no runtime behavior change; comments/labels only.
- Corrective B: public API still rejects `top_k > 100`; sparse domain/site retrieval regains
  pre-branch recall (adaptive over-fetch may scan up to the full collection).

---

## What NOT to build

- Do NOT remove or weaken the timeout mechanism, the process-group kill, or the memory cap.
- Do NOT implement the watch-OOM full-file-reindex design (append cursor, units-in-flight
  bound, per-path cooldown) here — that is a separate, unauthorized arc.
- Do NOT relax `validate_top_k` or the `candidate_k`/`MAX_QUERY_RESULTS` public cap.
- Do NOT touch `process_lock.py`, `chroma_write_store.py`, `ask.py`, `ingest.py`, or
  `chroma_store.py` — those changes reviewed clean.
- Do NOT touch the dirty Naturalistic V2 work in the main checkout.

---

## Test expectations

Existing focused suites must stay green: `tests/test_watch_subprocess_memcap.py`,
`tests/test_query_search_harden.py`, `tests/test_retrieve_for_ask.py`.

Add / adjust in `tests/test_query_search_harden.py`:

1. **sparse-scope over-fetch not capped at 300:** with a mocked repo reporting
   `count_units()` well above 300 and a domain filter active, assert `_fetch_scoped_units`
   can issue a `query_units` fetch larger than 300 when fewer than `candidate_k` scoped hits
   appear in the first page (i.e. `collection_bound` reflects collection size, not 300).
2. **public limit still enforced:** `validate_top_k(101)` raises `ValueError`;
   `validate_top_k(True)` raises `TypeError` (existing coverage — keep).

`test_query_search_harden.py` currently asserts an "absolute cap on scoped adaptive fetches"
at 300 — update that assertion to reflect the collection-size bound, not `MAX_QUERY_FETCH`.

Use fixtures / mocked repos; do not depend on the live corpus.

---

## Acceptance criteria

- [ ] `config.example.toml` no longer presents 900s as a recommended/ratified value; comment
      marks it an unratified interim backstop and points to the memory cap as primary.
- [ ] `watch.py` timeout constant is labeled unratified interim; mechanism unchanged.
- [ ] `_fetch_scoped_units` and the keyword-fallback path over-fetch bounded by collection
      size, not `MAX_QUERY_FETCH`.
- [ ] Public `top_k` cap (1–100) via `validate_top_k` and `MAX_QUERY_RESULTS` intact.
- [ ] Updated/added query tests pass; watch + retrieve suites green.
- [ ] No regression in existing suite.
- [ ] Ruff / pylint clean per repo gates.

---

## Branch convention

Stay on `fix/2026-09-01-security-hardening` (correctives belong with the hardening PR).
Push immediately after each commit with an explicit refspec. Open PR when acceptance
criteria pass. Squash OK.

---

## Related files

| What | Path |
|------|------|
| Watch timeout constant + config read | `watch.py:23`, `watch.py:210` |
| Watch config doc | `config.example.toml:62-63` |
| Scoped over-fetch (primary) | `query.py:280-294` `_fetch_scoped_units` |
| Scoped over-fetch (keyword fallback) | `query.py:489` |
| Public limit validator (keep) | `query.py:43` `validate_top_k`, `query.py:479-481` |
| Writer gate (untouched — do not edit) | `chroma_write_store.py` `fcntl.flock` |
| Landed OOM memory cap (context) | PR #245 `_scoped_index_cmd` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed on `fix/2026-09-01-security-hardening`
- [ ] `LATEST.md` bullet (main checkout is dirty with Naturalistic V2 — add the bullet on the
      branch's LATEST or defer to the PR body; do not edit the dirty main checkout)
- [ ] Branch pushed with explicit refspec before cloud pickup
- [ ] Track A: index this Kiro session transcript

**Implementer — Codex Luna (picking up):**

- [ ] Launch at the correct tier: `codex -m gpt-5.6-luna -c 'model_reasoning_effort="low"'` (T4)
- [ ] Read this file before first edit
- [ ] `convmem work resume fix/2026-09-01-security-hardening` (or work the existing worktree at `/home/lauer/.local/share/convmem/worktrees/fix-2026-09-01-security-hardening`)
- [ ] Apply Corrective A and B, update tests, run focused suites + ruff/pylint
- [ ] Commit each corrective; push with explicit refspec `fix/2026-09-01-security-hardening:refs/heads/fix/2026-09-01-security-hardening`
- [ ] If sandbox blocks the edit, state the exact change so the shell lane applies it

<!-- Kiro review sign-off + corrective handoff for the Codex 2026-09-01 security branch. Correctives routed to Codex Luna (Ryan 2026-09-01). -->
