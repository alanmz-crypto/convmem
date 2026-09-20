# Implementation Handoff: Make Claude Gate 1 tolerate invalid UTF-8 lines

**Arc: none (ad-hoc Gate 1 maintenance)**

**Date:** 2026-09-20  
**Author:** Codex coordination / PR Steward  
**For:** Cursor Composer implementation lane  
**Authorization:** Ryan, 2026-09-20, explicit chat grant for issue #316

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Handoff branch** | `docs/2026-09-20-claude-gate1-invalid-utf8-handoff` |
| **Implementation branch** | `fix/2026-09-20-claude-gate1-invalid-utf8` |
| **Base** | `origin/main` at or after closeout merge `7607fbb` |
| **Push status** | handoff branch pushed to origin; implementation not started |
| **PR** | not authorized; do not open |
| **Ryan GATE** | implementation is granted within this brief; stop after push for review |
| **Issue** | [#316](https://github.com/alanmz-crypto/convmem/issues/316) |

---

## What to build

Make the supported Claude Gate 1 `convmem index --file` adapter skip a
synthetic JSONL line that cannot be decoded as UTF-8 while retaining valid
messages before and after it. Metadata discovery and ordinary `parse()` must
both remain usable, and format detection must not abort on the same malformed
line.

**Why this exists:** Gate 2 automatic capture is closed as
`NO_GATE2_ROUTE`; Gate 1 on-demand indexing is the supported Claude path.
Merged `main` currently raises `UnicodeDecodeError` from both
`read_session_meta()` and `parse()` when a transcript contains a stray invalid
byte.

---

## Integration point

- `adapters/claude_session_jsonl.py` — `_probe_claude_session()`,
  `read_session_meta()`, and `parse()` currently consume text through strict
  UTF-8 file iteration.
- `adapters/jsonl_io.py` — shared `iter_jsonl_dicts()` is used by neighboring
  adapters. Prefer a Claude-local tolerant iterator unless a shared change is
  demonstrably necessary and all consumers are regression-tested.
- `tests/test_claude_session_jsonl.py` — add byte-level synthetic fixtures and
  focused assertions.

---

## Specification

### Inputs

- Synthetic temporary Claude JSONL only.
- Include one complete line containing a stray `0xff` byte between valid
  records.
- No real Claude transcript, corpus file, provider, or live index operation.

### Algorithm / behavior

1. Read Claude JSONL line-by-line as bytes or with equivalent per-line strict
   decoding.
2. Decode each line as UTF-8 independently.
3. Skip a line on `UnicodeDecodeError`; do not log or return its bytes or text.
4. Continue applying the existing JSON-object and message hygiene rules to
   subsequent valid lines.
5. Use the same tolerant record path for format probing, metadata discovery,
   and ordinary Gate 1 parsing so their behavior cannot drift.
6. Preserve existing fail-closed injected-wrapper handling, sidechain
   exclusion, thinking/tool block exclusion, timestamps, session IDs, and
   workspace fallback behavior.

### Output / contract

- `is_claude_session_jsonl()` returns a boolean and never leaks malformed line
  content.
- `read_session_meta()` returns the first supported metadata found on valid
  records, including records after the malformed line.
- `parse()` returns valid accepted messages in their original order, including
  messages on both sides of the malformed line.
- No new public API, watcher route, or evidence schema.

---

## What NOT to build

- Do not revive or cherry-pick Gate 2 prefix, registry, canary, or namespace
  code.
- Do not access a real transcript or run `convmem index --file` on live data.
- Do not change watcher/source/service configuration, routing, providers,
  activation, or `incremental_jsonl.py`.
- Do not repair the unrelated production export incident in issue #315.
- Do not perform issue #317's Gate 1 containment audit in this implementation.
- Do not open a PR; push and stop for review.

---

## Test expectations

Focused tests in `tests/test_claude_session_jsonl.py`:

1. **Metadata survives invalid UTF-8:** valid metadata after a stray `0xff`
   line is returned without exception.
2. **Parse survives invalid UTF-8:** valid messages before and after the bad
   line remain ordered and sanitized.
3. **Detection survives invalid UTF-8:** a Claude-shaped file with a malformed
   line among the probe window still returns the correct boolean from valid
   signal records.
4. **Content-free failure handling:** no captured stdout/stderr or exception
   contains malformed source bytes or message content.
5. **Existing hygiene:** all current Claude tests remain green.
6. **Neighbor adapters:** run the naturalistic adapter suite plus Cursor and
   Codex adapter tests if shared JSONL helpers change.

Suggested minimum commands:

```bash
python -m pytest tests/test_claude_session_jsonl.py -q
python -m pytest \
  tests/test_naturalistic_v2_adapters.py \
  tests/test_cursor_store.py \
  tests/test_codex_history_jsonl.py \
  tests/test_codex_rollout_jsonl.py -q
git diff --check origin/main..HEAD
```

---

## Acceptance criteria

- [ ] `read_session_meta()` does not abort on the synthetic invalid line.
- [ ] Ordinary Gate 1 `parse()` does not abort on the same input.
- [ ] Format detection remains total and content-safe for that input.
- [ ] Valid records before and after the invalid line retain order and content
      hygiene.
- [ ] No malformed line content appears in output, logs, or exceptions.
- [ ] Neighbor adapters remain unchanged in behavior.
- [ ] Diff stays within the Claude adapter and necessary focused tests unless
      a shared-helper change is justified with expanded regression evidence.
- [ ] `git diff --check` is clean and repo lint gates pass for touched files.
- [ ] Implementation branch is pushed with an explicit refspec; no PR opened.

---

## Branch convention

Start from the pushed handoff while preserving current `main` ancestry:

```bash
git fetch origin
git switch -c fix/2026-09-20-claude-gate1-invalid-utf8 \
  origin/docs/2026-09-20-claude-gate1-invalid-utf8-handoff
```

Push immediately after each commit with the explicit refspec:

```bash
git push -u origin \
  fix/2026-09-20-claude-gate1-invalid-utf8:refs/heads/fix/2026-09-20-claude-gate1-invalid-utf8
```

Do not open a PR. Return the exact pushed SHA and test evidence for review.

---

## Related files

| What | Path |
|------|------|
| Claude Gate 1 adapter | `adapters/claude_session_jsonl.py` |
| Shared JSONL helper | `adapters/jsonl_io.py` |
| Focused tests | `tests/test_claude_session_jsonl.py` |
| Closed parent arc | `docs/plans/STATUS-claude-watch-parity.md` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] Ryan's exact grant captured
- [x] Scope separated from closed Gate 2 and issue #315/#317
- [x] This file committed and pushed
- [x] `LATEST.md` points to this handoff

**Implementer (picking up):**

- [ ] Read this file and issue #316 before editing
- [ ] Create the named fix branch from the pushed handoff
- [ ] Use synthetic byte fixtures only
- [ ] Push exact implementation tip and stop for review

---

I finished: [Arc none] issue #316 implementation handoff  
Next step: Cursor implements the synthetic invalid-UTF-8 corrective and pushes the exact tip  
Next lane: Cursor Composer  
See my work: `docs/inter-model/CODEX-2026-09-20-claude-gate1-invalid-utf8-handoff.md`

**TL;DR:** [Arc none] Ryan authorized a synthetic-only Gate 1 fix for issue
#316. Cursor must make detection, metadata discovery, and ordinary parsing skip
invalid UTF-8 lines without content leakage, push the fix, and stop for review.
