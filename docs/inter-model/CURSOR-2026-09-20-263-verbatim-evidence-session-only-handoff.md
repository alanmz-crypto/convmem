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
