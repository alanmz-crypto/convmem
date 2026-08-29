# R2b v2 I1–I3 authority-boundary corrective II evidence

**Arc:** R2b Capture Authorization
**Current base:** `a19b5cbb2e431aafeda304057c98e6bd81aa0ffd` (PR #247)
**Prior review tip (failed):** `b28078ebba59edcfbf19e5cb7281410048f549f6` / `4ba6550ec164245190476094d7f64ce5ec5778bc`
**Status:** Authority-boundary corrective II — NOT operational VERIFY

## Two-SHA model

| Role | SHA |
|---|---|
| `implementation_tip` | `5d72f45` |
| `evidence_tip` | *(this commit)* |

Inventory digest: `1d151a01c91bfd0aae835e601afc150b9556ab94061f34847e5fb469cbb8f54d`

## Authority-boundary design (corrective II)

- Source-authority mint internalized: `compose_and_mint_source_authority` requires live lease+coverage handles and cross-slice binding checks
- No public `mint_source_authority_record` or `register_custodian` on `authority_registry` import surface
- Custodian registration lifecycle-only via `_register_lease_custodian` (overwrite refused)
- Registry minting remains in `_registry_mint.py` (not public import surface)
- Diagnostic census provenance seal required to consume tickets
- Coverage mint requires consumed ticket one-shot; mint seal + epoch on records
- Source authority proof opaque, registry-backed, epoch-bound
- Custodian resolved by registry ID (not mutable holder reference)
- Coverage-to-lease handle binding prevents cross-chain replay
- Implementation revision must be authoritative git SHA outside test override

## Restart/reload adjudication

Process-local I1–I3: registry epoch invalidation destroys prior handles/proofs.
Durable run-ID uniqueness: **DEFERRED — PRE-I4 BLOCKER**.

## TOCTOU note (probe 10)

`SourceAuthorityProof` is inert at I1–I3. Issuance revalidates live lease/custodian
but does not claim atomic kernel-lock + census + registry validation.

## Authority boundaries (unchanged)

I4–I8: NONE | Production gate: NOT ACQUIRED | Live authority: NONE | 900s: NOT RATIFIED
