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
