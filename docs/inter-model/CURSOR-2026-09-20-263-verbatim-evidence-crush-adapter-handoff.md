# Implementation Handoff: issue #263 Crush verbatim evidence slice

**Date:** 2026-09-20
**Author:** Cursor (implementation lane)
**For:** GitHub Copilot audit lane (safety/isolation), then Kiro design review if needed
**Authorization:** Ryan accepted Kiro PASS on architecture tip `3a49408`; Cursor Execute for the bounded Crush-only read-only adapter slice

**Arc:** none (ad-hoc issue #263)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `READY_FOR_REVIEW` |
| **Branch** | `feat/2026-09-20-263-verbatim-evidence-crush-adapter` |
| **Tip SHA** | `git rev-parse origin/feat/2026-09-20-263-verbatim-evidence-crush-adapter` after fetch (do not trust a stale embedded SHA) |
| **Push status** | pushed to `origin` |
| **PR** | not opened |
| **Ryan GATE** | none for audit; PR open remains Ryan-gated |
| **Track A ingest** | Cursor agent transcript for this chat (nudge at handoff) |

Architecture base: `3a49408` on `plan/2026-09-20-263-verbatim-evidence-contract`
(`docs/plans/ARCHITECTURE-verbatim-evidence-retrieval.md`).

---

## What to build (done)

Bounded, read-only Crush adapter that returns provenance-bearing message excerpts
for summary hits, or an honest unavailable state — never fabricates verbatim text
from summary similarity alone.

**Why this exists:** Crush session evidence (e.g. SID missive) lives in SQLite while
retrieval only surfaces generated summaries.

---

## Integration point

- `verbatim_evidence/` — types, NFC+LF normalize/digest, Crush adapter, ask labels
- `ask.py` — opt-in `verbatim_source=False` on `retrieve_for_ask` / `ask`
- `tests/test_verbatim_evidence_crush.py` — eight acceptance tests + invalid locator

```python
from verbatim_evidence import retrieve_verbatim_evidence, EvidenceLocator
result = retrieve_verbatim_evidence(locator, query_text)
```

---

## Specification

### Inputs

- `EvidenceLocator`: `source_path`, optional `session_id` / `conversation_id`,
  optional `start_offset` / `end_offset`
- `query_text` for conservative exact-term match (NFC+LF; case-insensitive fallback)

### Algorithm / behavior

1. Validate locator (missing identity → `invalid_locator`; never source-wide scan).
2. Open Crush DB URI `mode=ro`; unsupported/missing → `unavailable_source`.
3. Bound candidate window: offsets → session+conversation → session alone.
4. Parse text parts only (reuse Crush ingest filter; drop reasoning/tool/finish).
5. Match normalized query; truncate to API budgets; digest **post-truncation** excerpt.
6. Ask path (`verbatim_source=True`): label `summary` vs `verbatim_source` (or unavailable).

### Output / contract

Four states: `available`, `unavailable_source`, `unavailable_match`, `invalid_locator`.

Budgets (API constants, not live config):
- `DEFAULT_MAX_CANDIDATE_MESSAGES = 64`
- `DEFAULT_MAX_RESULT_MESSAGES = 3`
- `DEFAULT_MAX_EXCERPT_CHARS = 2000`

### NFC consistency

Matching and SHA-256 digests both use Unicode NFC + LF normalization (UTF-8).

---

## What NOT to build

- Chroma schema / reindex / raw bodies in Chroma
- Live `[sources]` / `[watch]` / model config changes
- Non-Crush adapters
- Arbitrary SQL
- Default-on ask behavior (`verbatim_source` stays opt-in)
- Arc Codex / Claude Gate 2 / R2b / OOM work

---

## Test expectations

`tests/test_verbatim_evidence_crush.py` (fixtures only):

1. Exact SID fixture → available + provenance
2. Near-match / negative control → `unavailable_match`
3. Missing + unsupported source → `unavailable_source`
4. Reasoning/tool parts excluded
5. Truncation + post-truncation digest
6. Ask context labels summary vs verbatim_source
7. Summary similarity alone cannot create `verbatim_source`
8. Hermetic: no real Crush DB / Chroma writes

Run:

```bash
python -m pytest tests/test_verbatim_evidence_crush.py -v
```

---

## Acceptance criteria

- [x] Eight architecture acceptance tests pass on fixtures
- [x] NFC+LF applied to match and digest
- [x] Four evidence states preserved
- [x] Message/byte budgets enforced
- [x] No live corpus / config mutation
- [ ] Copilot audit PASS on exact pushed tip
- [ ] Ryan authorizes PR (if desired)

---

## Branch convention

`feat/2026-09-20-263-verbatim-evidence-crush-adapter` from architecture tip `3a49408`.

---

## Audit lane request

Review exact pushed tip for:

1. Read-only URI opens; no writes to fixtures or live DBs
2. No fabricated verbatim from summary similarity
3. Hidden part exclusion
4. Locator fallback never widens to unbounded scan
5. Digest over post-truncation NFC+LF excerpt only
6. Opt-in ask wiring does not change default behavior

Return PASS / FAIL / CONDITIONAL PASS on the exact tip SHA.
