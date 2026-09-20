# Handoff: bounded verbatim evidence retrieval for issue #263

**Date:** 2026-09-20  
**Author:** Codex (architecture/planning lane)  
**For:** Kiro review, then Cursor implementation if approved  
**Authorization:** Ryan's instruction to begin unattended work outside the
72-hour active-agent window; implementation remains review-gated

---

## Resume state

| Field | Value |
|-------|-------|
| **State** | `READY_FOR_REVIEW` |
| **Branch** | `plan/2026-09-20-263-verbatim-evidence-contract` |
| **Tip SHA** | `a90cb0c` |
| **Push status** | pushed to `origin` |
| **PR** | not opened |
| **Ryan GATE** | No additional Ryan gate for Kiro architecture review; Cursor implementation requires the normal reviewed-plan/Execute path |
| **Track A ingest** | Codex session indexed with `convmem index --file`; no log artifact created |

The architecture document is:
[`docs/plans/ARCHITECTURE-verbatim-evidence-retrieval.md`](../plans/ARCHITECTURE-verbatim-evidence-retrieval.md)

`LATEST.md` was intentionally not edited because it has been touched within the
72-hour active-agent window. The current Codex/Claude/R2b/OOM work remains out
of scope for this handoff.

---

## Product goal

When semantic retrieval identifies a conversation containing a relevant
end-of-chat missive, ConvMem should return a bounded excerpt from the original
source message with provenance. If exact source evidence cannot be read or
matched, the system must say so explicitly rather than claim the source is
absent.

The confirmed reproduction is Crush session `d82521a1-4535-4ef2-b920-b819f548c25a`
in `/home/lauer/.crush/crush.db`, where the assistant missive containing
`Social Infrastructure Density (SID)` exists in SQLite but only a generated
conversation summary reaches retrieval.

---

## Current system

- `query_raw()` searches the Chroma `conversation_summaries` projection.
- Ingested summary metadata already carries `source_path`, `session_id`,
  `conversation_id` where available, and chunk offsets.
- `adapters/sqlite_chat.py` already parses Crush text parts while excluding
  reasoning/finish metadata, but query-time retrieval has no message-level
  source read.
- Chroma is derived serving state; source databases remain read-only authority.
- No source paths, watch paths, live configuration, or corpus data should change
  in this slice.

---

## Kiro review request

Review the architecture document at the exact pushed tip and answer:

1. Is a read-only source evidence adapter the correct boundary, rather than
   storing verbatim text in Chroma?
2. Are `available`, `unavailable_source`, `unavailable_match`, and
   `invalid_locator` sufficient and honest states?
3. Are the locator, message/byte limits, source digest, and provenance fields
   sufficient to prevent a summary hit from being presented as verbatim proof?
4. Does the Crush-only first slice keep privacy, authority, and blast radius
   appropriately bounded?
5. Are the acceptance tests strong enough to prevent fabricated evidence,
   hidden reasoning/tool-part leakage, unbounded transcript output, and live
   source/config mutation?

Return a verdict on this exact tip: `PASS`, `FAIL`, or `CONDITIONAL PASS`, with
any required changes named by section.

---

## Cursor implementation boundary after Kiro PASS

Only after Kiro review passes should Cursor implement the first slice:

- a small evidence result type and adapter protocol;
- a Crush read-only adapter using fixed parameterized queries;
- fixture coverage for the SID missive and a negative control;
- explicit summary versus `verbatim_source` context labels;
- bounded excerpt/message budgets and source provenance;
- missing-source, unsupported-source, no-match, truncation, and hidden-part
  tests.

The implementation must use temporary fixtures and must not depend on the real
Crush database.

---

## Hard stops

Do not:

- implement code before Kiro reviews the architecture;
- add raw transcript bodies to Chroma;
- expose arbitrary SQL;
- scan an entire source when the locator is missing or ambiguous;
- treat semantic summary similarity as exact message evidence;
- change `[sources].paths`, `[watch].extra_paths`, or live model configuration;
- ingest, purge, or repair the user's real corpus;
- touch the active Arc Codex, Claude Gate 2, R2b, or OOM branches.

---

## Acceptance bar for the eventual implementation

1. Exact SID fixture returns bounded text plus source/session/message provenance.
2. Near-match returns `unavailable_match`, never fabricated verbatim evidence.
3. Missing/unsupported source returns `unavailable_source` without traceback.
4. Reasoning/tool parts are excluded.
5. Oversized output truncates deterministically with an indicator.
6. Ask context labels summary and source excerpt separately.
7. Negative control proves summary similarity alone cannot create a
   `verbatim_source` result.
8. Tests perform no Chroma writes, source mutations, live config changes, or
   dependence on real user data.

---

## Leaving / picking-up checklist

**Codex (leaving):**

- [x] Architecture document written and pushed.
- [x] This handoff written on the same pushed branch.
- [x] No active-agent files or live configuration touched.
- [x] Session indexed; no `logs/*.md` artifact created.
- [ ] `LATEST.md` update intentionally deferred because it is inside the
      current 72-hour active-agent window.

**Kiro (picking up):**

- [ ] Read the architecture document at tip `a90cb0c`.
- [ ] Review the boundary and acceptance bar above.
- [ ] Return an exact-tip verdict with section-level findings.

**Cursor (only after Kiro PASS):**

- [ ] Start/resume an implementation branch from the reviewed plan/base.
- [ ] Use fixtures only; keep the adapter read-only and bounded.
- [ ] Stop at evidence and hand off for review; do not alter live routing.

