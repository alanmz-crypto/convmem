# R2b v2 I1–I3 authority-boundary corrective evidence

**Arc:** R2b Capture Authorization
**Current base:** `a19b5cbb2e431aafeda304057c98e6bd81aa0ffd` (PR #247)
**Prior review tip (failed):** `98e49a32f888133b7ef26f061c00e2929c72a779` (PR #249)
**Status:** Authority-boundary corrective — NOT operational VERIFY

## Two-SHA model

| Role | SHA |
|---|---|
| `implementation_tip` | `b28078ebba59edcfbf19e5cb7281410048f549f6` |
| `evidence_tip` | *(this commit)* |

Inventory digest: `a8bed0dd605b971dd4f479a59b09faea1d290395b9d678d51ef5cfd80e6ca669`

## Authority-boundary design

- Registry minting internalized in `_registry_mint.py` (not public import surface)
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
