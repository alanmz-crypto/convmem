# Architecture: bounded verbatim evidence retrieval

**Status:** proposed architecture for issue #263; no implementation authorized by
this document.

## Goal

When a semantic or summary hit points at a source conversation, ConvMem should
be able to return a small, provenance-bearing excerpt from the original source
message. If the source cannot be read or the message cannot be located, the
answer path must say that verbatim evidence is unavailable rather than imply
that the source content does not exist.

The first supported case is the Crush SQLite store and the confirmed
end-of-chat missive in `/home/lauer/.crush/crush.db`. The contract must be
source-adapter based so other stores can be added without putting source
database logic in ranking or synthesis code.

## Problem boundary

Today `query_raw()` searches the `conversation_summaries` Chroma collection.
Those rows contain source/session/window metadata and a generated summary, but
not the original message text. The existing SQLite adapter can parse Crush
messages for ingest, yet the retrieval path has no bounded, message-level read
operation. Consequently, a summary hit can identify the right conversation
while the synthesis prompt still lacks the exact missive.

This is a retrieval/evidence boundary problem, not an indexing-authority
problem. Chroma remains a rebuildable serving projection; source databases
remain read-only source authority.

## Chosen design

Add a read-only `verbatim_evidence` boundary between summary retrieval and
answer-context formatting:

```text
query
  -> summary/unit retrieval
  -> source_path + session/window locator
  -> source evidence adapter (read-only)
  -> bounded evidence result
  -> context formatter / citations
```

The boundary returns a typed result with one of these states:

- `available`: one or more bounded excerpts were found;
- `unavailable_source`: the source path is missing, unreadable, unsupported,
  or fails the read-only adapter contract;
- `unavailable_match`: the source was readable, but no message matched the
  requested query within the identified conversation/window;
- `invalid_locator`: the retrieved metadata did not contain a safe, usable
  source/session/window locator.

Only `available` evidence may be presented as verbatim source text. Other
states must remain visible to the caller and must not be converted into a
confident source-absence claim.

## Ownership and safety

- Ledger/source files own the original message text.
- Chroma owns summary and semantic-search geometry only.
- Evidence adapters open sources read-only and never write, index, mutate, or
  repair them.
- The query layer owns selection of candidate summaries; the evidence boundary
  owns source lookup; the answer formatter owns wording and citations.
- No generic raw-SQL escape hatch is exposed. Each adapter owns its fixed,
  parameterized query and output normalization.
- The first implementation must be opt-in to evidence retrieval from the
  existing ask path and must not change source paths, watch paths, or indexing
  configuration.

## Locator contract

The initial locator is derived from existing summary metadata:

- canonical `source_path`;
- `session_id` when available;
- `conversation_id` when available;
- summary `start_offset` and `end_offset` as a narrowing hint, not proof of
  message identity;
- query text used for bounded matching.

Adapters must treat offsets as untrusted hints. They must validate the source
identity and search only within a bounded candidate window. A missing or
ambiguous locator yields `invalid_locator`, not a whole-source scan.

For Crush, the adapter may use the existing `sessions` and `messages` tables
with parameterized queries, preserve `session_id`, `role`, `created_at`, and
message order, and reuse the existing text-part filtering that excludes
reasoning/tool metadata. It must not return hidden reasoning, tool payloads,
sidechains, or the entire transcript.

## Evidence result contract

Each returned excerpt should carry:

- source path;
- adapter/source kind;
- session identifier;
- message identifier when available;
- role;
- source timestamp when available;
- bounded message ordinal or source window;
- a short excerpt with an explicit truncation marker when truncated;
- a source-content digest for the returned excerpt;
- evidence status.

The contract should enforce both a maximum number of messages and a maximum
character/byte budget. The initial values belong in the function/API contract,
not an unreviewed live config change. A query that would exceed the budget
returns a bounded subset plus a truncation indicator.

## Matching policy

The first version should use conservative exact-term matching against normalized
message text, with a case-insensitive fallback for the query terms. It should
not claim semantic source matching merely because the summary was semantically
similar. If no message-level match is found, return `unavailable_match` and
retain the summary as a summary-origin citation only.

This keeps retrieval and generation separate: semantic retrieval identifies a
candidate source; message matching establishes whether the exact evidence can
be delivered.

## Ask-path behavior

The existing summary fallback remains valid. When verbatim evidence is
available, the answer context receives two clearly labeled items:

1. the generated summary, marked `summary`;
2. the bounded source excerpt, marked `verbatim_source`.

When it is unavailable, the context receives the summary plus a structured
evidence-unavailable marker. The synthesis instructions must distinguish:

- “the source contains this exact excerpt”;
- “the source was identified but exact evidence was unavailable”;
- “no source candidate was retrieved.”

The answer must never turn the second state into “the source does not exist.”

## Initial implementation scope

In scope for the first Cursor slice after review:

- a small evidence result type and adapter protocol;
- a Crush read-only adapter;
- focused fixture coverage for an exact end-of-chat missive and a negative
  control;
- query/ask integration behind an explicit evidence request or equivalent
  existing evidence mode;
- provenance fields and bounded rendering;
- tests for missing source, unsupported source, no match, truncation, and hidden
  reasoning/tool-part exclusion.

Out of scope:

- changing Chroma schema or reindexing existing sources;
- ingesting raw message bodies into Chroma;
- automatic watch/source-path changes;
- arbitrary SQL or user-supplied SQL;
- full transcript export;
- Claude/Codex incremental routing;
- ranking or recency retuning in the same slice.

## Acceptance tests

The implementation is ready for review only if it proves:

1. A fixture with an assistant final missive containing the SID heading returns
   the exact bounded excerpt and source/session/message provenance.
2. A near-match or unrelated query returns `unavailable_match`, not fabricated
   evidence.
3. A missing or unsupported source returns `unavailable_source` without a
   traceback or source-absence claim.
4. A source with reasoning/tool parts returns only permitted text parts.
5. A result over the budget is truncated deterministically and identifies that
   truncation.
6. The ask context labels summary and verbatim source separately.
7. The negative control proves that summary similarity alone does not create a
   `verbatim_source` result.
8. No test opens Chroma for writing, mutates a source database, changes live
   config, or depends on the user's real Crush database.

## Review and handoff gates

This document is the Codex planning slice for issue #263. Kiro should review
the boundary and acceptance criteria before Cursor implementation. The next
handoff should name the exact reviewed plan revision, the Cursor branch, and the
fixture/evidence contract. Implementation must remain isolated from the active
Codex/Claude/R2b work.

## Trade-offs

- **Read source at query time:** keeps Chroma rebuildable and avoids duplicate
  private text, at the cost of source availability and read latency.
- **Store verbatim text in Chroma:** would simplify retrieval but duplicates
  private source data, expands the serving projection, and creates a second
  authority copy. Rejected for this issue.
- **Exact-term matching first:** gives an honest evidence contract, at the cost
  of misses for paraphrased queries. Semantic source matching can be a later,
  separately evaluated extension.
- **Crush-only first adapter:** limits blast radius and makes the confirmed
  failure reproducible. Generalization comes after the boundary is proven.

