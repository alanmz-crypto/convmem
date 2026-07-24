# Canonical Observation Proposal

## Design principles

1. The canonical record expresses **durable truth** — not retrieval optimization.
2. Fields that exist only for Chroma search (embeddings, computed keywords) are derived, not canonical.
3. Schema evolution is explicit: every record carries a `schema_version`.
4. Old records remain readable: new fields have defaults; removed fields are ignored.
5. Application-specific state (indexing progress, projection receipts) lives outside the canonical record.

## Proposed canonical observation record (schema v1)

```json
{
  "schema_version": 1,
  "ledger_id": "obs_staging2_lh_csp-missing",
  "kind": "observation",
  "timestamp": "2026-07-24T14:00:00Z",
  "author": "lighthouse-ci",
  "source_identity": "site:staging2.willowyhollow.com",
  "source_revision": "",
  "domain": "web_stack.security",
  "site": "staging2.willowyhollow.com",
  "severity": "medium",
  "title": "Missing Content-Security-Policy header",
  "summary": "The response from staging2.willowyhollow.com lacks a Content-Security-Policy header, allowing unrestricted resource loading.",
  "evidence": {
    "header": "Content-Security-Policy",
    "url": "https://staging2.willowyhollow.com"
  },
  "confidence": 0.85,
  "relates_to": "",
  "status": "",
  "supersedes": ""
}
```

## Field classification

### Durable truth (canonical)

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `schema_version` | int | Yes | Schema evolution marker |
| `ledger_id` | string | Yes | Stable, deterministic identity |
| `kind` | enum | Yes | `observation`, `decision`, `verification` |
| `timestamp` | ISO 8601 | Yes | When the record was created |
| `author` | string | Yes | Producer identity (model name, tool, human) |
| `source_identity` | string | Yes | What produced this (site URL, file path, session ID) |
| `source_revision` | string | No | Content hash or version of the source at observation time |
| `domain` | string | Yes | Taxonomic classification |
| `site` | string | No | Site scope (empty for non-site observations) |
| `severity` | enum | No | `critical`, `high`, `medium`, `low`, `info` |
| `title` | string | Yes | Short human-readable label |
| `summary` | string | Yes | Self-contained description |
| `evidence` | object | No | Structured proof/data supporting the observation |
| `confidence` | float | Yes | 0.0–1.0 producer confidence |
| `relates_to` | string | No | Parent ledger_id (required for decision/verification) |
| `status` | string | No | Lifecycle state (`accepted`, `rejected`, etc.) |
| `supersedes` | string | No | Ledger_id of the record this replaces |

### Decision-specific canonical fields

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `rationale` | string | Yes (decision) | Why this decision was made |
| `alternatives_rejected` | list[string] | No | What else was considered |
| `constraints` | list[string] | No | Known limitations |
| `proposal_id` | string | Yes (governed) | Links to approval protocol |

### Verification-specific canonical fields

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `result` | enum | Yes (verification) | `pass`, `fail`, `partial`, `deferred` |
| `notes` | string | No | Verifier commentary |

### Derived / recomputed (NOT canonical)

| Field | Why derived |
|-------|-------------|
| `id` (Chroma UUID) | Assigned by projection layer; not stable across rebuilds |
| `embedding` | Computed from summary + keywords by embedding model |
| `keywords` | Can be recomputed from summary + domain + metadata |
| `content_hash` | Deterministic from canonical fields; recomputed on read |
| `type` (legacy) | Mapped from `kind`; kept for backward compat only |
| `tool` | Alias for `author`; redundant |
| `verifier_model` | Projection-layer state; verification record is separate |
| `verified_at`, `verified_confidence` | Inline verification state; superseded by separate verification records |
| `superseded`, `superseded_by` | Projection-layer tombstone state |
| `start_offset`, `conversation_id`, `session_id` | Ingest pipeline artifacts |

### Application-owned (outside canonical record)

| Field | Owner |
|-------|-------|
| Projection checkpoint | Projection subsystem |
| Embedding model version | Projection subsystem |
| Index status | Search/retrieval layer |
| Supersession tombstone | Refine/dedupe subsystem |

## Schema evolution strategy

1. Every record carries `schema_version`.
2. Readers accept any version ≤ their max supported version.
3. New fields in later versions have safe defaults (empty string, null, empty list).
4. Removed fields are ignored by newer readers.
5. A migration function upgrades old records to the current schema on read (no in-place mutation of the ledger).
6. The content hash computation includes `schema_version` to prevent cross-version collisions.

## Backward compatibility

Legacy records (no `schema_version`) are treated as schema v0. A v0→v1 migration:
- Sets `schema_version = 1`
- Maps `type` → `kind` (solution/explanation/pattern → observation; decision → decision)
- Generates a deterministic `ledger_id` from `source_path` + original `id`
- Sets `author` from `tool` or `author_model`
- Sets `source_identity` from `source_path`
- Preserves all existing fields as-is

## Example: fabricated decision record

```json
{
  "schema_version": 1,
  "ledger_id": "dec_20260724_csp-nginx",
  "kind": "decision",
  "timestamp": "2026-07-24T15:00:00Z",
  "author": "kiro-review",
  "source_identity": "site:staging2.willowyhollow.com",
  "domain": "web_stack.security",
  "site": "staging2.willowyhollow.com",
  "title": "Add CSP through nginx config",
  "summary": "Deploy Content-Security-Policy header via nginx server block rather than application-level middleware.",
  "rationale": "Nginx-level headers apply uniformly to all responses including static assets. Application middleware misses error pages and redirects.",
  "alternatives_rejected": ["WordPress plugin header injection", "PHP output buffer filter"],
  "constraints": ["Requires nginx reload", "Must coordinate with SiteGround support"],
  "confidence": 0.8,
  "relates_to": "obs_staging2_lh_csp-missing",
  "status": "accepted",
  "proposal_id": "dec_prop_20260724_150000_ab12"
}
```

## What this proposal does NOT include

- No implementation code.
- No migration scripts.
- No changes to the production write path.
- No Neutral Core or Office Team modifications.
- No embedding model selection or retrieval tuning.
