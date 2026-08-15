# CG-2 delta confirmation — exact-SHA review

**Date:** 2026-08-15  
**Target:** `e680ce837653698a5be8b78ba02db2f880c40c63`  
**Baseline reviewed:** `1222b1ede2d6cc5da582388768f06d60b36c5e50`  
**Branch:** `plan/2026-08-14-cg2-production-activation`

## Prompt

Confirm that the N1–N3 dispositions and formal model preserve the locked identity
decision: CG-1 path-derived ownership remains authoritative; CG-2 does not introduce
stable logical owner IDs or a mutable locator registry; canonical rename is explicit
old-owner → new-owner migration; pre-migration frozen readers may finish against the
old owner, while no newly resolved authority vector admits both owners.

## Verdicts

| Lane | Verdict | Summary |
|------|---------|---------|
| **Cursor** | **PASS** | N1–N3 addenda resolve prior risks without reopening identity; §8/§14 preserve path-derived ownership and explicit rename migration; formal model checks `RenameVectorExclusive` / `RenameGroupStable` |
| **Kiro** | **PASS** | Identity anchors unchanged; `PromoteCandidate` for `NewOwner` requires `OldOwner ∈ auth.retired`; typed fallback, watchdog-independent reconciler, and retry-budget terminal state integrated and model-checked |
| **Crush** | **PASS** | Identity decision preserved in prose and TLA+; frozen legacy readers protected; no stable logical owner ID or mutable locator registry introduced |

**Sol-High:** Not invoked — no same-revision Kiro/Copilot PASS/FAIL conflict.

## Identity anchors verified at `e680ce8`

1. `ownership_key(path)` remains `source:<Path.resolve(strict=False)>` (architecture §3, §8).
2. Canonical-path rename creates a **new** owner; continuity is explicit old-owner → new-owner migration with retirement (§8).
3. §14 rejects “changing CG-1 owner identity to an unrelated stable-ID scheme.”
4. Formal model: `RenameVectorExclusive`, `RenameGroupStable`, `FrozenLegacyProtected`, `FrozenLegacyFinishEnabled`.

## N1–N3 disposition check

| Item | Architecture | Formal model |
|------|--------------|--------------|
| **N1** Fallback guard | §5.3 typed `ServingAuthorityError` / `ServingBackendIntegrityError` fail closed; only `ServingBackendTransient` may fall back | `AuthorityFailuresNeverFallback`, `FallbackIsMediated` |
| **N2** Reconciliation | §7.1 watchdog-independent periodic sweep within `max_reconciliation_staleness` | `LostDriftEventuallyHandled` under fair `Reconcile` |
| **N3** Retry budget | §5.1 `authority_resolution_retry_budget` → terminal `AUTHORITY_UNSTABLE` | `RetryBudgetTerminates`, `ResolutionEventuallyTerminates` |

## Review reading

- [Architecture delta](https://github.com/alanmz-crypto/convmem/compare/1222b1ede2d6cc5da582388768f06d60b36c5e50...e680ce837653698a5be8b78ba02db2f880c40c63)
- [Canonical architecture](https://github.com/alanmz-crypto/convmem/blob/e680ce837653698a5be8b78ba02db2f880c40c63/docs/plans/ARCHITECTURE-cg2-production-activation.md)
- [Formal model evidence](https://github.com/alanmz-crypto/convmem/blob/e680ce837653698a5be8b78ba02db2f880c40c63/docs/plans/formal/cg2/README.md)

## Next gate

Ryan Architecture HITL lock on `e680ce8`, then Codex execution + VERIFY planning (separate grants).
