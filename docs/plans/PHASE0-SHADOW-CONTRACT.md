# Phase 0 Shadow Ledger Contract

**Who:** Cursor Execute of approved
[`EXECUTION-shadow-ledger-phase0.md`](EXECUTION-shadow-ledger-phase0.md).
**What:** Human-readable mirror of locked Architecture decisions for Phase 0.
**When:** Created during Execute (T1).
**Why:** Freeze the provisional envelope, activation rules, and non-authority
language before wiring sinks.
**How:** Implementers and VERIFY use this alongside Architecture; this document
is **not** a canonical observation-schema proposal and does **not** authorize
production activation.

## Authority

| Claim | Phase 0 status |
|---|---|
| Chroma `knowledge_units` | Tier-1 / authoritative |
| Shadow JSONL | Non-authoritative diagnostic / candidate evidence |
| Backup / restore source | Chroma-first unchanged; shadow is never a restore source |
| Cutover / schema freeze | Out of scope |
| Production activation | Separate Ryan grant after Execute + VERIFY |

## Configuration (disabled by default)

```toml
[shadow_ledger]
enabled = false
ledger_path = "~/.local/share/convmem/shadow_ledger.jsonl"
activation_manifest_path = "~/.local/share/convmem/shadow_activation.json"
health_path = "~/.local/share/convmem/shadow_health.json"
```

- Absent `[shadow_ledger]` ≡ `enabled = false` → no sink constructed or injected.
- `enabled = true` only permits an activation **attempt**; sink injection requires
  a complete matching activation manifest, valid shadow file identity, and exact
  resolved Chroma root match.
- Live `~/.config/convmem/config.toml` is not modified by this Execute arc.
- Shadow ledger and sidecars are mode `0600`.

## Activation baseline

Machine-readable activation manifest fields include: manifest version; unique
baseline ID; completion status; UTC activation timestamp; code commit; resolved
Chroma root and collection identity; active and total unit counts; per-entity
document/metadata/state hashes; configured vs observed embedding identity and
dimensions; shadow identity and starting sequence; hashing rules/version.

Incomplete manifests cannot enable the sink. Writes use temp → flush/`fsync` →
atomic rename → parent-directory `fsync`.

## Envelope (provisional)

Schema label: `shadow_schema_version` (Phase 0 uses `1`). Operations:
`create`, `replace`, `metadata_update`, `supersede`, `restore`, `delete`.
Hashes: SHA-256 over UTF-8 canonical JSON (`sort_keys=true`, compact separators,
no NaN). Raw embeddings never enter the ledger. Unknown embed provenance is
`UNVERIFIABLE`, never equality PASS.

## Scope of proof

Phase 0 proves **post-activation delta** for touched stable entity IDs only —
not historic corpus rebuild, migration readiness, or authority transfer.

## Stop / non-goals

No production read-path change; no Neutral/Office; no Restic/restore doctrine
change; no `conversation_summaries` shadowing; no quarantine-and-continue on
corruption (fail-closed).


## Strict validation API (C1)

Single shared entry point (implemented in `shadow_validation.py`):

```text
validate_shadow_activation(config_path, chroma_dir, mode)
  -> ShadowValidationResult(
       state, inject_eligible, activation_id, refusals, facts)
```

Modes: `writer`, `prepare`, `doctor`, `inventory`, `verify`. Mode selects
additional checks; it never changes the meaning of a refusal code. Refusals are
deterministic, deduplicated, stably ordered, redacted, and carry
`code` / `artifact` / `blocking` / `detail`.

Malformed manifests, corrupt ledgers, invalid counts/hashes/sequences, unsafe
paths, and permission failures never return `inject_eligible=true`. Production
writer wiring to this API is a later slice; C1 validates the contract directly.

### Path and permission policy (Ryan-resolved)

- Shadow artifacts live in a dedicated Shadow directory under the convmem data
  root.
- That directory is a sibling of, and outside, the Chroma root.
- Shadow directory ownership: effective production user; exact mode `0700`.
- The shared data-root parent is **not** required to be `0700`.
- Ledger, manifest, and health files: exact mode `0600`, regular files, link
  count one.
- Symlinked leaf or ancestor components are refused.
- Artifact paths and device/inode identities must be pairwise distinct.
- No Shadow artifact may be inside the Chroma root.
- C1 validation does not create or modify live directories or artifacts.

### Ledger identity header

Committed ledgers begin with a non-payload `ledger_header` JSONL record binding
`activation_id`, `ledger_identity`, schema version, UTC, and `starting_sequence`.
Events after the header must be contiguous starting at `starting_sequence + 1`.

## Secure ledger I/O (C2)

Header-only ledger creation (`create_shadow_ledger_header`) opens the private
`0700` Shadow parent with `O_DIRECTORY|O_NOFOLLOW`, creates the leaf with
`O_CREAT|O_EXCL|O_NOFOLLOW` mode `0600`, `fchmod`/`fstat`-verifies the
descriptor **before** any bytes, writes the C1 `ledger_header` record, then
fsyncs the file and parent. No mutation payload is written at create time.

`JsonlUnitMutationSink` does not create a missing ledger. Append opens an
existing private ledger, validates the header, allocates the next sequence from
a bounded header/tail read (no whole-ledger scan), appends one complete event
line, and measures the complete path through health-sidecar persistence.
Duplicate event IDs may appear as distinct contiguous sequences; replay keeps
the first valid occurrence. The 500 ms marker remains a degradation signal, not
an activation SLO.
