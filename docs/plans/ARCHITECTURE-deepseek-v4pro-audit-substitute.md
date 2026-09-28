# Architecture — DeepSeek V4-Pro Copilot audit-lane substitute

**Status:** Implemented v2 baseline; consolidated v3 derived-evidence contract
awaiting exact-tip Kiro recheck and separate Ryan implementation authorization.
**audit_protocol_version:** `deepseek-v4pro-audit.v2` (implemented);
`deepseek-v4pro-audit.v3` (specified below, not implemented or activated)
**response_schema_version:** `deepseek-v4pro-checklist.v1`  
**Runner:** `scripts/deepseek_audit_substitute.py`  
**Supersedes:** obsolete Cursor plan packet for merged PR #66 (do not execute that packet).

**Arc:** none (ad-hoc). Switchboard is out of scope.
**Pinned producer baseline:** `1f8216345066b59ecc7521e0dd617b586c1393c5`.
The objects at this commit contain v2, not the older working-tree v1 document.
**Planning grant:** consolidate the corrected v3 contract in this document in
an isolated planning worktree; feature-branch commit and push only. No code or
test changes, PR creation, real inventory generation, transformation,
transmission, service action, or freeze release.

## Contract status and precedence

The sections from **Role** through **Plan / doc maintenance** document the
implemented v2 baseline and historical v1 behavior. The **Consolidated v3
derived-evidence contract** below freezes the previously conversational v0.3
contract, v0.4 addendum, and the final UTF-8/boundary clarifications in one
tracked document. There is no separate hand-maintained charter twin.

For a future v3 implementation, the consolidated contract overrides v2 only
where it explicitly changes inventory, disclosure, scanning, rendering,
versioning, and identity. Locked transport/configuration, strict response
validation, static-review framing, producer-path dirty rejection, nonce and
envelope handling, and authority boundaries otherwise remain intact.

This planning commit does not implement v3 or clear the known v2 password-form
scanner gap. A credential-bearing v2 candidate remains inadmissible for model
input or transmission. `egress_hits: []` from that scanner is not proof of
credential-free evidence. No existing candidate or historical artifact is
rewritten by approval of this document.

## Role

DeepSeek **V4-Pro via the official API** may act as a **Ryan-authorized substitute** for the **GitHub Copilot audit lane** on one exact tip+base.

It is **not**: Crush lane, `convmem ask` / Tier B synthesis, PR Steward, Kiro sign-off, Sol-High, or merge/grant/ledger authority.

**Default:** Copilot remains the governing audit lane. DeepSeek substitute activates only when Ryan explicitly assigns it for a named PR and tip.

## Locked request

| Field | Value |
|-------|--------|
| Endpoint | DeepSeek official chat completions |
| Model | `deepseek-v4-pro` |
| Thinking | `{ "type": "enabled" }` |
| Effort | `reasoning_effort: "high"` |
| Response | `response_format: { "type": "json_object" }` |
| `max_tokens` | `8192` |
| `stream` | `false` |
| Tools | omitted |

Forbidden transports: Crush, `convmem ask`, any tool-using agent session as the audit channel.

## Audit spec (`--audit-spec`, required)

Slice 3A audits load a JSON spec (`audit_spec_version: slice-3a-audit-spec.v0.1`) that defines:

- `mode` — e.g. `pre_pr_static_git_evidence`
- `criteria` — authoritative checklist IDs `C1` … `C7` with meanings (bound into system prompt)
- `required_dependencies` — unchanged files included at **tip** revision via `git show`

`spec_digest` = SHA-256 of canonical spec JSON. Bound into evidence packet header and `AUDIT_RUN_KEY`.

Malformed spec, wrong criteria ID set, or missing dependency at tip → preparation STOP (`INVALID_EXECUTION`).

## Static review framing

The harness performs **static Git-evidence review only**. A constant framing string is included in the system prompt and PR comment output. Model responses claiming executed commands, live inspection, operational readiness, or freeze/release authority are rejected (`detect_unsupported_execution_claims`).

## Producer provenance (v2)

Producer identity comes from the **runner checkout** (`scripts/deepseek_audit_substitute.py` → repo root), **not** `--repo`.

Authorized producer paths (exact set):

- `eval_corpus/deepseek_audit_substitute.py`
- `scripts/deepseek_audit_substitute.py`
- `tests/test_deepseek_audit_substitute.py`
- `docs/plans/ARCHITECTURE-deepseek-v4pro-audit-substitute.md`

`resolve_producer_identity` records HEAD SHA + blob OID per path. Dirty status on **any** authorized path blocks preparation. Unrelated dirty files do not block.

`producer_identity_digest` binds producer HEAD + path→blob pairs into `AUDIT_RUN_KEY` v2. Unrelated movement of audited checkout HEAD does **not** change the run key when tip/base/spec/evidence/producer identity are pinned.

## Evidence packet (Git objects only)

Build from `git diff` changed files + required unchanged dependencies at tip. Per-status:

| Status | Include |
|--------|---------|
| A | tip blob + tip OID |
| M | tip + base blobs (or exact path patch + both OIDs) |
| R* | old/new path, similarity, tip blob at new path, base at old when available |
| D | base blob + deletion record |
| symlink | link-target bytes from Git; never FS-dereference |
| binary | OIDs + sizes + hashes only; no raw dump |

Header binds `audit_protocol_version`, `spec_digest`, `tip`, `base`. Dependency section records tip blobs for each required dependency.

`evidence_packet_sha256` hashes the deterministic evidence core and **excludes** `BOUNDARY_NONCE`.

## Boundary nonce

CSPRNG only: `os.urandom(16).hex()` (or `uuid.uuid4().hex`), fresh per framing. Never derive from tip/base/timestamp. Purpose: delimiter/collision protection only (not response binding unless a future protocol version requires echo).

Markers: `BEGIN_AUDIT_PACKET_${NONCE}` / `END_…` / `INTEGRITY_METADATA_${NONCE}` / `END_…`. Collision-scan evidence blobs before finalize; STOP on hit → `INVALID_EXECUTION`.

## Dual digests

1. **evidence_packet_sha256** — evidence core only.
2. **request_envelope_sha256** — length-prefixed concatenation of: system prompt bytes, user message bytes, locked API param canonical JSON.

Identical retry (at most one) allowed only for transport failure or empty content, and only if `request_envelope_sha256` is unchanged.

**Length-prefix rule:** for each part, append `uint64_be(len(part)) || part` (big-endian length, then bytes). Hash SHA-256 of the concatenated stream. Same rule for `AUDIT_RUN_KEY` fields (UTF-8 encode strings).

## Terminals

| State | Meaning |
|-------|---------|
| `VALID_PASS` | Valid response; all checklist items PASS; local overall PASS |
| `VALID_FAIL` | Valid response; ≥1 FAIL |
| `INVALID_EXECUTION` | Harness/provider failure — STOP; do not claim DeepSeek rejected the PR |

## Validation (strict)

- Exactly one choice; nonempty `content`; `finish_reason == stop`
- No `tool_calls`; model `deepseek-v4-pro`; nonempty `id` + `system_fingerprint`
- JSON Schema (`additionalProperties: false`); reject duplicate keys / NaN / infinity
- Exact checklist ID set; nonempty evidence per item
- Locally computed overall must equal reported `verdict`
- Reject unsupported execution / operational-readiness claims in model content

## AUDIT_RUN_KEY v2 + post

```
AUDIT_RUN_KEY = SHA256( length_prefixed(
  protocol_version, model, base, tip,
  evidence_packet_sha256, system_prompt_sha256,
  response_schema_version, spec_digest,
  producer_identity_digest,
  locked_request_config_canonical_json
))
```

Exclude only the fresh nonce. Post hidden HTML comment marker with key; accept duplicates only from authorized actor. Recheck tip/base/merge-base before post; before merge-ready, re-list **all** unresolved review threads.

## Egress (structure vs content)

Egress is split:

1. **`validate_locked_envelope_structure`** — parse outbound JSON; require `max_tokens` (not `max_completion_tokens`); validate messages array shape.
2. **`egress_scan_decoded_content`** — credential patterns in decoded message **content** only; diagnostics name pattern class, never echo secret values.
3. **`egress_scan_outbound_body`** — parse JSON, run structure validation, scan each message content block. No path allowlist parameter.

Bare English word `token` alone does **not** trigger egress (removed v1 false positive).

Hit → `INVALID_EXECUTION` (no silent redaction).

## Historical protocol v1 (artifacts only)

`audit_protocol_version: deepseek-v4pro-audit.v1` artifacts used `audit_run_key_v1`, binding `runner_git_sha` from the audited checkout HEAD instead of producer identity + spec digest. Preserved as `audit_run_key_v1()` for verifying historical packets only. New runs must use v2.

```
AUDIT_RUN_KEY_v1 = SHA256( length_prefixed(
  protocol_version, model, base, tip,
  evidence_packet_sha256, system_prompt_sha256,
  response_schema_version, runner_git_sha,
  locked_request_config_canonical_json
))
```

## Plan / doc maintenance

Single tracked canonical: this file + runner. No hand-maintained condensed twin. Surgical + justified consistency edits only; section inventory before each protocol revision.

## Consolidated v3 derived-evidence contract

### 1. Purpose, scope, and separate authority gates

Produce a credential-free **derived disclosure view** of pinned Git evidence,
with honest original-versus-derived provenance and fail-closed validation.
This is an explicitly approved transformation policy, never silent redaction
or a scanner bypass. The local/Ollama substitute route is withdrawn; this
contract does not revive it or authorize inference on any route.

A later bounded synthetic-only implementation may touch exactly:

- `eval_corpus/deepseek_audit_substitute.py`
- `scripts/deepseek_audit_substitute.py`
- `tests/test_deepseek_audit_substitute.py`
- `docs/plans/ARCHITECTURE-deepseek-v4pro-audit-substitute.md`

Needing a fifth producer file, dependency, installed audit platform, WordPress
change, or unrelated modernization is a stop-for-Ryan condition. This is not
an implementation grant. Cursor implements only after a separate bounded
grant; Kiro reviews design; Ryan owns acceptance, grants, and merges.

Keep these gates separate:

1. Exact-tip design recheck of this consolidated contract.
2. Ryan's synthetic-only implementation grant; disposable repositories and
   synthetic credentials only, with network/API/posting disabled.
3. Implementation acceptance and any separately authorized delivery steps.
4. Separately authorized real inventory generation and review/freeze of its
   private selector-policy and inventory inputs.
5. Separately authorized real transformation and packet regeneration, followed
   by local evidence/disclosure validation.
6. Separately authorized model/API transmission and any later posting.

No gate implies the next. No real packet bytes, credential values, value maps,
per-value hashes, raw diagnostics, or private inventory are emitted into
hosted chat or tracked inputs. Private artifacts remain outside watched/
indexed paths, with directories mode 700 and files mode 600. A failure stops
the route; it never permits silent transformation, retry-by-policy-expansion,
model shopping, or a freeze release.

### 2. Evidence and audit-spec coordinates

The proposed v3 protocol is `deepseek-v4pro-audit.v3` and the amended evidence
spec version is `slice-3a-audit-spec.v0.2`. The response schema remains
`deepseek-v4pro-checklist.v1`. Existing v1/v2 artifacts keep their original
versions, meanings, hashes, and keys; never relabel them v3.

The pending Slice 3A audit is static Git-evidence review at:

- WordPress base: `83b803257c852d79bb32b600eeab8f1d487ff56e`.
- WordPress tip: `2f687ff4c3077cd8a9a7b6d90b064c8aeb1c7aa7`.
- Producer design baseline: `1f8216345066b59ecc7521e0dd617b586c1393c5`.
  A future implemented producer is pinned separately; do not falsely identify
  new producer code as the baseline commit.

Changed-file evidence follows the v2 Git-status rules above, retaining base
versions where required, for these seven paths only:

- `scripts/sync-preview-to-practice.sh`
- `scripts/sync-preview-to-practice-preflight.sh`
- `tests/sync-preview-to-practice-preflight-wiring.sh`
- `tests/sync-preview-to-practice-safety.sh`
- `README.md`
- `scripts/README.md`
- `AGENTS.md`

Required unchanged dependencies remain tip-bound:

- `docker-compose.yml`
- `.gitignore`
- `scripts/practice-theme-preflight.sh`
- `tests/practice-theme-preflight.sh`

Every included original blob and required dependency must appear in the source
manifest and be considered by the private inventory gate. Missing dependencies
or source bytes, stale identities, unassessable required evidence, or an
unreviewed source-set expansion block preparation. Git objects, not ambient
working-tree bytes, are the source of truth. Symlink evidence is never
filesystem-dereferenced; binary evidence remains metadata-only as in v2.

The approved nine criterion IDs and meanings are not redesigned here:

- **C1 — Scope:** seven-file scope and unchanged theme/helper/Compose boundaries.
- **C2a — Paths:** physical effective destination, cross-checkout behavior,
  equal/nested paths, symlinks, and protected-ancestor replacement.
- **C2b — Runtime:** engine/running prerequisites, project/service/database
  storage and bind identity; failures or ambiguity must fail closed.
- **C3 — Permissions/failures:** execution-user operations and runtime access;
  enumeration/command failures before mutation; no repair or bypass.
- **C4a — Preservation:** theme, both configurations, and reviewed exclusions
  survive transfer, deletion, type replacement, and metadata effects.
- **C4b — Optional MU-plugin:** present unchanged, absent stays absent even
  when preview has it; no creation, editing, enabling, or new tracking.
- **C5 — Removed operations:** recursive chowns, persistent startup, and local
  config regeneration removed; theme `--no-baseline-verify` policy retained.
- **C6 — Coverage:** actual-script fixtures and substantive no-mutation/content/
  metadata assertions; reading tests is not independently executing them.
- **C7 — Honest delivery:** accurate documentation/static framing and remaining
  DB recovery/coordination/freeze gaps; no operational-readiness claim.

The private approved spec remains authoritative for full criterion wording.
Its amendment must disclose derived evidence and withheld credential values,
retain all nine IDs/meanings and required dependencies, and include verbatim:

> Any producer-verified equality relationship is local producer evidence, not independent model verification.

Equality-preserving transformations are deferred in this contract. A criterion
that needs a hidden value or cross-location value equality must report
insufficient evidence, not silently PASS or treat placeholder differences as
proof of unequal original values. A well-formed evidence-gap FAIL is distinct
from `INVALID_EXECUTION` caused by broken preparation/response validation.
Neither authorizes a second auditor or operational execution.

### 3. Private inventory schema and freeze

Each inventory record has exactly these ten fields; unknown fields reject:

```text
slot_id
source_revision
source_path
source_blob_oid
source_content_sha256
credential_syntax_class
quote_style
value_start_byte
value_end_byte
placeholder
```

`source_revision` is the pinned base or tip Git commit for that section.
`source_path` is a normalized relative POSIX path, with no absolute path,
traversal component, or control character. The source OID and lowercase
SHA-256 must identify the actual original Git blob and its full content, never
a credential-value hash. No record contains a credential value or its hash.
`slot_id` is a unique nonempty identifier; placeholders are unique too.

The closed syntax-class enum is:

```text
yaml_scalar
dotenv_assignment
shell_assignment
cli_long_equals
cli_long_separate
cli_short_attached
php_define_string
```

The quote-style enum is `none`, `single`, or `double`. Offsets are zero-based
UTF-8 **byte** offsets into the original blob, end exclusive, covering only
the credential value, not its quote delimiters, key, flag, assignment
delimiter, comment, or executable code. Offsets must be integers, not Boolean
values, and satisfy:

```text
0 <= value_start_byte < value_end_byte <= source_byte_length
```

Offsets must fall on valid UTF-8 boundaries. Invalid UTF-8, unsupported syntax,
ambiguous quoting/escaping/expansion, multiline values, overlapping spans,
duplicate slots or locations, stale source references, unknown credential
locations, or unapproved selector forms reject. Do not guess or autoextend the
inventory/policy when detection finds another form.

Freeze the reviewed inventory at its digest, pinned base/tip,
source-manifest digest, and transformation-policy digest. Changing a source,
selector, offset, class, quote style, placeholder, or any record requires a new
reviewed freeze coordinate before real transformation. Digest calculation
alone does not confer review approval. An empty record list may represent a
reviewed credential-free source set; absence of inventory review cannot.

### 4. Independent credential-context check

For each slot, the parser independently derives the value boundaries from
the original Git bytes and declared syntax form, then compares them with the
inventory. **Any mismatch is a hard reject. Never snap, reconcile, or repair
parser boundaries toward the inventory.**

The surrounding credential key, flag, or PHP constant must belong to the
frozen policy's explicit selector list and the quote style must match. A span
that is a value under a noncredential key still rejects. Inventory approval
cannot authorize arbitrary code/evidence redaction.

Class consistency requires at least:

- `yaml_scalar`: the scalar value of a selected mapping entry.
- `dotenv_assignment` / `shell_assignment`: the value on the right side of a
  selected `KEY=VALUE` assignment, not any key or comment text.
- `cli_long_equals`: the value after a selected `--flag=`.
- `cli_long_separate`: the separate value argument of a selected `--flag`.
- `cli_short_attached`: the attached password value of a policy-listed
  database executable. Arbitrary programs' `-pVALUE` are not password slots.
- `php_define_string`: the string value argument of a `define` call for a
  selected credential constant, not the constant name or surrounding code.

Each supported parser must reject unsupported escaping, expansion, multiline
syntax, or ambiguous argument/context boundaries rather than broaden its
interpretation. Selector lists are reviewed input data, not implementer-
inferred lists or generic permission to hide any assignment.

### 5. Placeholders, transformation, and final scan

The exact placeholder grammar is `AUDIT_WITHHELD_CREDENTIAL_` followed by six
decimal digits; for example `AUDIT_WITHHELD_CREDENTIAL_000001`. Tokens are
distinct per occurrence, including equal original values. No equality map,
salted/truncated value digest, or value-derived token enters the disclosed
packet or diagnostics.

A reserved-placeholder collision in original content rejects. Replacement
changes only the approved value spans and preserves all other original bytes,
including keys, flag names, delimiters, quotes, and surrounding code.
Independently reconstruct the expected disclosed body from original Git bytes
and the approved replacements; validate actual body equality, not just a
supplied content hash.

The placeholder allow-set is structural: exact token identity **and** its
declared transformed credential-value location, derived from the frozen
inventory and independently reconstructed output. No namespace/prefix regex,
substring, path, or digest exemption is admissible. An approved token at an
undeclared credential-value location rejects. Metadata declaring a slot is
not a new authorization to place its token elsewhere in evidence content.

Retain existing v2 credential detections and add fail-closed detection for
supported password assignments and command-line forms, including the observed
`MYSQL_PASSWORD:` / `--password=` classes. Their detections are not exemptions.
Scan final decoded disclosure content and the final outbound message content,
not only the original candidate or known-good envelope. The locked envelope
structure validation remains separate, so `max_tokens` remains legitimate.

Remaining credential forms, undeclared tokens, uncertain syntax, missing
coverage, or evidence failures produce `INVALID_EXECUTION`, with safe
reason/class diagnostics only. Never echo matched values or value hashes.
No silent redaction or scan-then-broad-whitelist repair is allowed.

### 6. Canonical serialization and digest input bytes

`CJ(x)` is JSON with **recursively sorted object keys**, compact separators
(`,` and `:`), `ensure_ascii=false`, and no trailing newline, encoded as strict
UTF-8 **bytes**. Reject duplicate object keys, NaN/infinity, unknown fields,
and inputs that cannot be encoded in UTF-8. Arrays retain their explicitly
specified order; sorting object keys never silently sorts arrays.

`LP(parts)` uses the existing SHA-256 primitive. For each **byte sequence**
append `uint64_be(len(part)) || part`, then SHA-256 the concatenated stream.
Encode every string into UTF-8 before measuring its length or hashing. Length
means encoded **byte count**, never Python `str` length or character count.

The four literal domain labels are:

```text
deepseek-v4pro-audit.v3/source-manifest
deepseek-v4pro-audit.v3/transformation-policy
deepseek-v4pro-audit.v3/frozen-inventory
deepseek-v4pro-audit.v3/transformation-manifest
```

For each corresponding object below, digest exactly:

```text
LP([UTF8(exact_domain_label), CJ(exact_payload_object)])
```

This fixes the input layout to two length-prefixed byte sequences, not a
concatenation of individually hashed fields. Object field lists below are
exact, not optional suggestions. Each digest is lowercase hexadecimal.
No object hashes itself or includes a recursive self-hash field.

#### Source-manifest payload

Exactly `schema_version`, `base`, `tip`, and `sources`; schema version is
`slice3a-source-manifest.v1`. Each source has exactly:

```text
source_revision
source_path
source_blob_oid
source_content_sha256
source_byte_length
```

Sort sources lexicographically by `(source_revision, source_path)`; duplicate
coordinates reject. Length is original Git-content byte count, integer not
Boolean. Each original section, including every required unchanged dependency,
must resolve to one corresponding source coordinate.

#### Transformation-policy payload

Exactly these fields:

```text
schema_version = "slice3a-transformation-policy.v1"
syntax_classes[]
credential_keys[]
cli_password_flags[]
cli_executables[]
php_credential_constants[]
quote_styles[]
placeholder_prefix = "AUDIT_WITHHELD_CREDENTIAL_"
placeholder_digits = 6
equality_mode = "distinct_per_occurrence"
span_unit = "utf8_bytes"
end_boundary = "exclusive"
```

The six list fields are sorted unique strings; syntax and quote entries must
be members of their closed enums. Selector lists are explicit reviewed inputs,
never automatically expanded. This schema does **not** approve or freeze a
real selector list.

#### Frozen-inventory payload

Exactly these fields:

```text
schema_version = "slice3a-frozen-inventory.v1"
base
tip
source_manifest_digest
transformation_policy_digest
records[]
```

Each record has exactly the ten fields in section 3. Sort records by
`(source_revision, source_path, value_start_byte)`. This digest is
`inventory_digest` and binds the review/freeze coordinate. Equal/overlapping
positions, duplicate slot IDs/placeholders, or any invalid source reference
reject before transformation.

#### Transformation-manifest payload

Exactly these fields:

```text
schema_version = "slice3a-transformation-manifest.v1"
source_manifest_digest
transformation_policy_digest
inventory_digest
sections[]
```

Each section has exactly:

```text
source_revision
source_path
disclosure_kind
disclosed_content_sha256
slot_ids[]
```

`disclosure_kind` is `original` or `derived`. Sections sort by
`(source_revision, source_path)`, with no duplicate coordinates. Slot IDs
follow ascending source-offset order. An original section has no replacements
and an empty slot list; a derived section lists exactly its approved applied
slots. Every emitted source body has a section; omissions or undeclared slots
reject. The manifest binds `inventory_digest` transitively into the run key.

### 7. Original-versus-derived rendering and validation

Every textual evidence section separates these structures:

```text
source:
  revision
  path
  git_blob_oid
  content_sha256
disclosure:
  kind: original | derived
  content_sha256
  policy_digest
  slot_ids
body:
  disclosed content
```

`source.content_sha256` hashes the full original Git bytes.
`disclosure.content_sha256` hashes the actual disclosed body bytes.
`policy_digest` identifies the frozen transformation policy; slot IDs connect
to the manifest, not secret values. For `original`, body must equal Git blob
bytes and both hashes must match them. For `derived`, independently applying
only the approved slots to those Git bytes must yield the body exactly; all
non-slot bytes must be identical.

The renderer must **not** reuse the v2 fused
`--- path=... blob=... sha256=... ---` assertion line for derived sections.
`git_blob_oid` lives only under source provenance, never on an assertion line
identifying a derived content hash. The original Git OID authenticates the
source reference, not the derived body. Derived bytes labelled `original`,
or source metadata presented as identity of the disclosed bytes, reject.

Deterministic disclosed packet construction retains pinned base/tip,
name-status evidence, required dependencies, spec binding, and section order.
No confidential value map or per-value digest may be embedded in headers,
trailers, prompts, transformation metadata, or safe summaries.

### 8. v3 evidence identity and exact run-key order

For v3, `evidence_packet_sha256` is SHA-256 of the actual deterministic
**disclosed evidence-core bytes**, excluding the fresh boundary nonce and
request framing as before. It is the disclosed-evidence digest, not a hash
of the credential-bearing original candidate. Bind it **once** in the v3 key.
Keep any original candidate hash separately labelled historical source
evidence; never overwrite an old artifact or reinterpret its v1/v2 hash.

`spec_digest` remains SHA-256 of canonical amended audit-spec JSON bytes.
`system_prompt_sha256` hashes the actual system-prompt bytes. Response-schema
version remains bound. Locked request configuration and envelope digest keep
their v2 meanings. The nonce stays CSPRNG-generated, collision-checked, and
excluded from deterministic evidence/run identity; the request-envelope digest
still binds the complete nonce-bearing request bytes.

Preserve producer-identity construction verbatim from the pinned v2 producer:

```text
producer_identity_digest = SHA256(UTF8(
  producer_head_sha + "\n" +
  "\n".join(sorted "path:blob_oid" pairs)
))
```

Sort pairs by producer path as the existing implementation does. This inner
construction is intentional plain SHA-256, not LP. Its lowercase hex result
is one opaque UTF-8 field in the v3 LP key. Do not harmonize or silently
version its internals. Producer HEAD and all four relevant path OIDs remain
pinned; relevant staged/unstaged/untracked dirt rejects, unrelated dirt does
not.

The v3 key uses the new protocol string as its domain and exactly this order:

```text
AUDIT_RUN_KEY_v3 = LP([
  UTF8("deepseek-v4pro-audit.v3"),
  UTF8(model),
  UTF8(base),
  UTF8(tip),
  UTF8(source_manifest_digest),
  UTF8(evidence_packet_sha256),
  UTF8(system_prompt_sha256),
  UTF8(response_schema_version),
  UTF8(spec_digest),
  UTF8(producer_identity_digest),
  UTF8(transformation_policy_digest),
  UTF8(transformation_manifest_digest),
  CJ(locked_request_config)
])
```

Do not reuse a v1/v2 run key. The inventory digest is bound through the
transformation manifest. Source, spec, policy, inventory/manifest, producer,
or disclosed-evidence changes must invalidate the old identity as appropriate.
Unrelated movement of audited working-tree HEAD must not change it when all
evidence coordinates and producer are pinned.

### 9. Synthetic-only falsifying acceptance tests

These are obligations for a later authorized implementation, not claims of
tests executed by this planning lane. Drive preparation/validation entrypoints
with disposable repositories and synthetic credentials; block API/network and
GitHub posting. No real private packet or inventory is needed for these tests.

Require paired positives and negatives, including:

1. Locked `max_tokens` passes structure validation while synthetic API keys,
   Bearer values, password assignments, and CLI credential values in content
   reject safely. Diagnostics never contain matched values or value hashes.
2. Correct synthetic inventory transforms only independently parsed selected
   value spans. Key/comment/code-line spans, a noncredential key, wrong quotes,
   parser-offset mismatch, unsupported syntax, stale OID/hash, overlap, missing
   source/dependency, and undeclared edits reject without boundary repair.
3. Database executable `-pVALUE` is handled only under reviewed policy;
   non-database `-pVALUE` rejects as an inventoried password slot.
4. Placeholder collision, unknown/moved/reused token, undeclared location,
   incomplete inventory, original-value remnants, and scanner failure reject.
   Only exact approved tokens at their reconstructed declared value positions
   pass; no prefix/path/pattern bypass. Original credential-bearing input
   remains rejected without an approved transformation.
5. Reconstruct every derived body independently and prove non-slot bytes
   unchanged. Reject derived-as-original sections, wrong body hashes, source
   OIDs presented as derived identities, and fused v2 derived headers.
6. A non-ASCII JSON fixture proves recursive key sorting, UTF-8 encoding before
   LP length measurement, byte count distinct from character count, and exact
   two-part domain-plus-CJ layouts. Independently constructed expected digests
   catch self-comparison tests and wrong domains/array order.
7. Change each relevant source/policy/inventory/manifest/disclosed/spec/
   producer binding independently and require old digests/run identity to
   fail. Historical and v3 artifacts cannot be cross-substituted despite a
   same-named hash field. Do not require raw hashes to differ solely because
   of protocol version; the versioned structure and run-key domain bind the
   meaning, and changed disclosed bytes change their own content hash.
8. Run actual preparation against a genuinely dirty relevant producer path
   (staged and unstaged) and assert STOP with no usable packet publication;
   move disposable audited HEAD while pinned inputs stay fixed and assert
   stable deterministic identity. Keep unrelated-dirt behavior intact.
9. Withholding-dependent criteria cannot PASS through producer assertions or
   placeholders. Preserve exact nine IDs, evidence-gap versus invalid status,
   static-review framing, and rejection of execution/readiness claims.
10. All success/rejection diagnostics and artifacts obey privacy rules; fixtures
    cannot write outside their disposable directories. No test calls APIs,
    posts to GitHub, executes WordPress, starts services, or releases a freeze.

### 10. Data gate and next review

Schemas and hash-domain literals do **not** freeze real selector lists,
inventory records, or transformation approval. Those are private reviewed
inputs, separately Ryan-gated. Equality preservation is not in scope. No
credential-bearing raw candidate is admitted merely because this design
passes review or a synthetic implementation passes tests.

Kiro's next review is a targeted delta on this exact tracked contract: confirm
the v0.3/v0.4 consolidation, corrected pinned v2 grounding, independently
parsed hard-reject boundaries, recursively sorted UTF-8-byte CJ/LP rules,
literal digest payloads, historical-versus-v3 identity, and honest renderer.
No transport debate, WordPress architecture, Switchboard work, or uncontested
full-system re-audit is reopened. Unresolved privacy/correctness defects still
remain below no discretionary stop rule: the guardrails never waive that floor.

After a satisfactory exact-tip recheck, Ryan may separately grant a bounded
synthetic-only Cursor implementation. That later grant does not authorize real
inventory generation, transformation, regeneration, API transmission, posting,
activation, operational-script execution, or freeze release.
