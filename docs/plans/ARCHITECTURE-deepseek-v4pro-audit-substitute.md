# Architecture — DeepSeek V4-Pro Copilot audit-lane substitute

**Status:** Binding design for Ryan-authorized substitute audits.  
**audit_protocol_version:** `deepseek-v4pro-audit.v2` (current)
**response_schema_version:** `deepseek-v4pro-checklist.v1`  
**Runner:** `scripts/deepseek_audit_substitute.py`  
**Supersedes:** obsolete Cursor plan packet for merged PR #66 (do not execute that packet).

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
