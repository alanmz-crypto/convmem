# Handoff: issue #263 bounded session-only Crush evidence

**Date:** 2026-09-20
**Author:** Codex
**Arc:** none (ad-hoc issue #263)
**For:** Cursor implementation lane
**Status:** contract published; implementation not approved

## Decision and scope

Ryan accepted option B: implement bounded session/conversation retrieval only.
The first slice does not add producer metadata or a source-generation field.

- An offset-only locator returns `offset_retrieval_unavailable` before opening
  the database.
- A locator carrying offsets and a session identifier ignores the offsets and
  performs session retrieval. The result is explicitly `scope=session` with
  reason `offsets_ignored_session_scope`.
- Session-only evidence is not claimed to be the summarized message window.
  The rendered preamble must say that it may come from elsewhere in the
  session.
- `conversation_id` remains an alias for the session key. If both identifiers
  are present and differ, return `invalid_locator`.
- Non-string locator fields, relative paths, empty normalized queries, and
  invalid budgets return `invalid_locator` or `invalid_budget` without opening
  the database.

Do not implement or retain a live offset-retrieval path. Future offset tests
must be isolated from the production adapter.

## Session retrieval contract

Search one session in deterministic `(created_at, id)` order. The session-local
ordinal is the zero-based index of accepted, non-empty, valid text messages
after role and part filtering. It is not a global producer offset.

Stream until one of these occurs:

- three matches are collected: complete `available` result;
- EOF: `unavailable_match` if no match, otherwise `available`;
- raw-row or byte cap: `scan_limit` if no match, otherwise `available` with
  `partial=true`;
- malformed or oversized row: `unavailable_source` if no match, otherwise
  `available` with `partial=true`;
- deadline: `unavailable_source` if no match, otherwise `available` with
  `partial=true`;
- source lock: `unavailable_source` with `source_busy`.

Partial results carry structured `partial_reason`. Stopping after three matches
is complete, not partial.

## Fixed limits and deadlines

```text
MAX_SCAN_ROWS     = 10_000
MAX_SCAN_BYTES    = 16 MiB
MAX_PARTS_BYTES   = 1 MiB
MAX_RESULTS       = 3
MAX_EXCERPT_CHARS = 2_000
MAX_QUERY_CHARS   = 2_000

TOTAL_READ_DEADLINE_SECONDS = 2.0
BUSY_TIMEOUT_MAX_SECONDS    = 0.25
PROGRESS_OPCODE_INTERVAL    = 1_000
```

The monotonic deadline begins before connection and covers lock waits,
`BEGIN`, SQLite execution, JSON parsing, normalization, and matching. Apply
the remaining time to each busy wait; do not add the busy timeout to the
deadline. Document approximately two seconds plus scheduler slack as the
total bound. Use the progress-handler flag and SQLite error code to distinguish
`deadline` from `source_busy`, never error-message text.

Reject non-integers, booleans, negative values, zero where prohibited, and
values above the fixed maxima with `invalid_budget`.

## SQLite and source safety

Use one read transaction for both stages. Initialization order is:

1. connect with the bounded timeout;
2. `PRAGMA query_only=ON`;
3. `PRAGMA trusted_schema=OFF`;
4. `BEGIN`;
5. install the narrow authorizer.

The authorizer permits only the required message/schema reads, `table_info`,
and `length`; transaction operations remain denied because `BEGIN` already ran.

Stage one orders compact keys and byte lengths only, with `LIMIT
MAX_SCAN_ROWS + 1`; it must not carry `parts` through the sorter. Stage two
fetches payloads by a verified unique key and reapplies both `session_id` and
the byte-size predicate. Use real row identity only after rejecting schemas
with columns named `rowid`, `oid`, or `_rowid_` (case-insensitive). Track stage
keys in a set and return `unavailable_source/duplicate_row_identity` on any
duplicate. If `WITHOUT ROWID` support is needed, verify a primary key through
`PRAGMA table_info` before using it.

Oversized rows must be identified separately from legitimate `NULL` parts and
must not be silently skipped. Catch malformed/deeply nested data in the
adapter, not the shared parser. The known residual risk is that SQLite may
read a large value internally while evaluating `length(CAST(parts AS BLOB))`;
document it rather than using `immutable=1` or an unverified `setlimit` path.

Require an absolute source path, resolve it once, escape the SQLite URI path,
and use that same resolved value for connect and stat. Check resolved path,
`st_dev`, and `st_ino` before and after every database-backed outcome. Do not
use mtime, size, or parent-directory mtime as mutation gates; test a WAL
fixture without `immutable=1`, symlink replacement, and the URI-decoy case.

## Matching, excerpts, and rendering

Normalize message and query with NFC+LF. Use documented length-preserving
`re.IGNORECASE` matching; this intentionally differs from full Unicode
`casefold()` behavior such as `STRASSE` versus `straße`.

- Cap the query before database access.
- Empty normalized query is invalid.
- Excerpts are measured in characters, including markers.
- Use the original normalized-text match span, never an index from `casefold`.
- Prefix every excerpt line with `│ ` and keep `Source:` and `Digest:` outside
  the quoted block.
- If the query cannot fit, return `unavailable_match` with
  `query_exceeds_excerpt_budget`.
- Digest the unescaped, final post-truncation NFC+LF excerpt with SHA-256.

All attacker-influenced rendered fields must be structure-safe: summary text,
excerpt text, labels, role, IDs, paths, timestamps, reasons, scope, partial
metadata, tool/when fields, and unavailable messages. Use `│ ` quoting for
multiline summary and excerpt text. Use a custom escaper or `ensure_ascii=True`
for single-line metadata, covering `Cc`, `Cf`, `Zl`, and `Zp`, including NUL,
CR, U+0085, U+2028, and terminal escape sequences. Add a hostile-content test
asserting that no attacker-controlled line creates a renderer-looking item
header. The scope preamble is conditional so existing non-session pinned
strings remain stable.

`EvidenceResult` carries `scope`, `partial`, and `partial_reason`; excerpts
carry `scope`. `SCAN_LIMIT` renders as generic evidence unavailability, never
source absence.

## Required verification

Run the Crush suite and the naturalistic contract files:

```bash
python -m pytest tests/test_verbatim_evidence_crush.py \
  tests/test_naturalistic_v2_contract_authority.py \
  tests/test_naturalistic_v2_capability_authority.py \
  tests/test_naturalistic_v2_resolver_authority.py \
  tests/fixtures/naturalistic_v2_p1.py -v
```

Add tests for session scope rendering, hostile Unicode/control content,
duplicate and shadowed row identities, two-stage snapshot consistency,
rollback-journal contention, query-plan cursor columns, malformed/oversized
rows before and after matches, exact maximum budgets, deadlines, WAL behavior,
URI decoys, symlink identity, and all outcome rules above.

No Chroma, watcher, routing, production configuration, live corpus, or live
Crush DB changes are authorized. After implementation, commit and push a new
exact tip, request independent security review, then Copilot audit when
available. No PR or activation yet.

## Excerpt-loop addendum

This addendum is part of the canonical contract. It supersedes any chat-only
excerpt corrections.

### Window oracle and span validation

`_bound_excerpt` requires a non-optional `match_span` and validates:

```text
0 <= start < end <= len(text)
```

Invalid or missing spans raise `ValueError` in direct unit tests. The production
adapter does not catch this programming error because `find_match_span` always
returns a valid span. There is no no-span or head-truncation fallback.

For small test strings, the oracle must exhaustively enumerate only windows
with `s <= match_start` and `e >= match_end`. A window is feasible when:

```text
(e - s) + M * (s > 0) + M * (e < len(text)) <= max_excerpt_chars
```

For every non-`None` implementation result, the test must also find an oracle
window whose rendered content exactly equals:

```text
(TRUNCATION_MARKER if s > 0 else "")
+ text[s:e]
+ (TRUNCATION_MARKER if e < len(text) else "")
```

The test must assert `cut_leading == (s > 0)` and
`cut_trailing == (e < len(text))`. It must assert that the implementation
returns `None` exactly when no feasible oracle window exists. Include the
feasibility boundaries at `M`, `M + query_length`, `2*M + query_length`, and
message lengths at, just above, and far above the budget. Include the 1,976 /
1,977 / 1,978 query cliff at the 2,000-character production budget.

### Stream outcomes and terminal conditions

A usable extra excerpt is the only condition that proves `result_limit`.
Matching messages whose excerpts return `None` are dropped, not counted, and
scanning continues.

The only terminal conditions are a usable extra match, EOF, source failure,
deadline, row cap, or byte cap. A dropped excerpt is non-terminal and can
co-occur with each terminal condition.

Test the matrix as follows:

- dropped excerpt + EOF → `available, partial=true,
  partial_reason=excerpt_budget` if a usable result exists; otherwise
  `unavailable_match/query_exceeds_excerpt_budget`;
- dropped excerpt + usable extra → `available, partial=true,
  partial_reason=result_limit`;
- dropped excerpt + scan cap → `scan_limit` if there is no prior usable
  excerpt, otherwise `available, partial=true, partial_reason=scan_limit`;
- dropped excerpt + byte cap → the analogous byte-cap outcome;
- dropped excerpt + source/deadline failure → `unavailable_source` if there is
  no prior usable excerpt, otherwise `available, partial=true` with the source
  or deadline reason.

“No prior usable excerpt” means dropped matches do not count as evidence.

When multiple terminal conditions occur on the same row, use this deterministic
tie-break order:

```text
deadline > row_cap > byte_cap > oversized/malformed
```

Test each terminal condition alone and test dropped-excerpt combinations with
each terminal condition. Do not write impossible tests that require a stream to
reach two mutually exclusive terminal conditions in sequence.

## Excerpt algorithm addendum (b4af28a failed review)

**Resume state: BLOCKED_ON_CURSOR.** Tip `b4af28a` (`_bound_excerpt`,
`verbatim_evidence/crush.py:268-319`) must not be sent to review again.

### Failure evidence

Adversarial grid over 9,150 cases (budgets 1..60, query length 1..budget):
length bound held; a visible marker was missing when `truncated=True` in 615
cases; the complete query was absent from an AVAILABLE excerpt in 5,040 cases.
At the production budget, a 1,977-character query returned a 2,000-character
excerpt without the query (1,976 passed). The loop returned the first plan that
merely fit the length and never checked that the window contained the match
span. The `(False, False)` plan and the no-span fallback both emit unmarked or
query-free text.

### Required rules

- **Pre-check:** reject early only when `len(stripped_query) > max_excerpt_chars`.
  Do not reject on marker cost before examining a message; a short message can
  hold a query equal to the budget with no marker.
- **Stripped query:** normalize, then strip once. Use that exact string for
  length validation, matching, span calculation, and feasibility. Add padding
  cases.
- **Candidates, in order** (`M = len(TRUNCATION_MARKER)`, `Q = match_end -
  match_start`): (1) whole text if `len(text) <= max_chars`, no markers;
  (2) left-anchored prefix plus one trailing marker, valid if `match_end <=
  max_chars - M`; (3) right-anchored leading marker plus suffix, valid if
  `len(text) - match_start <= max_chars - M`; (4) centered window with both
  markers, valid if `Q <= max_chars - 2*M`. If none fits, return `None`.
  Candidate 4 always cuts both sides; assert it.
- **No clipped markers.** If `max_chars < M` and the text needs truncation,
  return `None`. Never return marker-only or partial-query AVAILABLE evidence.
- **`None` handling:** the caller converts it per the Excerpt-loop addendum
  (dropped match; `unavailable_match/query_exceeds_excerpt_budget` only if no
  usable excerpt survives and the scan completed).
- **Structured flags:** add `cut_leading` and `cut_trailing` to
  `EvidenceExcerpt`; keep `truncated == (cut_leading or cut_trailing)`. Render
  both in `context.py`. Consumers and tests must not infer cuts from the
  in-band marker text, which source content can contain literally.
- **`partial_reason` is single-valued.** Precedence: source failure / deadline /
  busy / malformed / oversized > `scan_limit` > `result_limit` >
  `excerpt_budget`. Use `excerpt_budget` only when the scan completed and
  dropped matches are the only incompleteness.
- **Regressions:** the brute-force oracle and matrix in the two addenda, plus
  the full grid (budgets 1..60, unique-character queries; matches at start,
  near-start, middle, near-end, end; lengths at, one over, far over budget), a
  query equal to the budget in a short message, the 1,976/1,977/1,978 cliff, all
  matching messages unable to fit, some fitting and some dropped, and an
  end-to-end matching message that cannot yield a truthful excerpt.

Preserve NFC normalization, digest the final unescaped excerpt, and keep
default-off `verbatim_source` unchanged. After implementation run the focused
suites (Crush plus the naturalistic contract files), push a new exact tip, and
request independent security re-review.
