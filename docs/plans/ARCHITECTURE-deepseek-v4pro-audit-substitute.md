# Architecture — DeepSeek V4-Pro Copilot audit-lane substitute

**Status:** Binding design for Ryan-authorized substitute audits.  
**audit_protocol_version:** `deepseek-v4pro-audit.v1`  
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

## Evidence packet (Git objects only)

Build from `git show` / blob OIDs — not the worktree. Per-status:

| Status | Include |
|--------|---------|
| A | tip blob + tip OID |
| M | tip + base blobs (or exact path patch + both OIDs) |
| R* | old/new path, similarity, tip blob at new path, base at old when available |
| D | base blob + deletion record |
| symlink | link-target bytes from Git; never FS-dereference |
| binary | OIDs + sizes + hashes only; no raw dump |

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

## AUDIT_RUN_KEY + post

```
AUDIT_RUN_KEY = SHA256( length_prefixed(
  protocol_version, model, base, tip,
  evidence_packet_sha256, system_prompt_sha256,
  response_schema_version, runner_git_sha,
  locked_request_config_canonical_json
))
```

Exclude only the fresh nonce. Post hidden HTML comment marker with key; accept duplicates only from authorized actor. Recheck tip/base/merge-base before post; before merge-ready, re-list **all** unresolved review threads.

## Egress

Scan the **final outbound HTTP JSON body** against allowlist + secret patterns. Hit → `INVALID_EXECUTION` (no silent redaction).

## Plan / doc maintenance

Single tracked canonical: this file + runner. No hand-maintained condensed twin. Surgical + justified consistency edits only; section inventory before each protocol revision.
