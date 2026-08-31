# Implementation Handoff: R2b Corrective VII — independent re-review (Kiro)

**Date:** 2026-08-30  
**Author:** Cursor (implementation lane)  
**For:** Kiro (independent technical/security review — read-only)  
**Authorization:** Ryan, 2026-08-30 (appointed Cursor Corrective VI/VII; appointed Kiro review on VI; VII awaits re-review)

**Arc:** R2b Capture Authorization — Corrective VII

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` (Kiro independent re-review) |
| **Branch** | `fix/2026-08-30-2026-08-30-r2b-v2-corrective-vi` |
| **Frozen tip SHA** | `ea7bc9de10b8eed34a6f8ab11d8f50d3106df614` |
| **Push status** | `pushed to origin` |
| **PR** | [#252](https://github.com/alanmz-crypto/convmem/pull/252) (open; Corrective V lineage — Corrective VI/VII commits on separate branch pending re-freeze) |
| **Ryan GATE** | Kiro PASS/FAIL on exact tip `ea7bc9de10b8eed34a6f8ab11d8f50d3106df614` → Ryan merge/hold decision. No merge, baseline ratification, or I4–I8 advance until PASS. |
| **Prior review verdicts** | Corrective V **FAIL** @ `81becac`; Corrective VI **FAIL** @ `5ccb6be` (Break 1 closed, Break 2 reintroduced via `_MUTATION_GUARD`) |

---

## What to build

**Nothing.** This is a read-only independent review handoff. Kiro verifies whether R2b v2 I1–I3 authority boundary is closed at frozen tip `ea7bc9d`.

**Why this exists:** Corrective V failed closure-introspection (ledger injection + mutation-guard bypass). Corrective VI closed Break 1 but reintroduced Break 2 by moving the guard secret to reachable module global `_MUTATION_GUARD`. Corrective VII removes that global and makes the registry mutation guard frame-based (same pattern as the ledger guard that Kiro verified closed in VI).

---

## Integration point

Primary file: `eval_corpus/r2b_v2/_authority_vault.py`

| Symbol | Role |
|--------|------|
| `_vault_internal_frame_active` | Stack walk: `co_name ∈ allowed` **and** `f_globals["__name__"] == vault module` |
| `_GuardedLedger` / `_GuardedLedgerRecord` / `_GuardedConsumedSet` | Break 1 guards (unchanged since VI — Kiro PASS) |
| `_REGISTRY_MUTATION_FRAMES` | Allowed registry mutation caller frames |
| `_SealedStore._guard_mutation` | Now calls `_vault_internal_frame_active(_REGISTRY_MUTATION_FRAMES)` — **no** `_MUTATION_GUARD`, **no** ContextVar closure |
| `vault_dispatch` | Module-level function, `__closure__ is None` |
| `_VaultHolder` | Opaque wrapper over inner dispatch |

Adversarial tests: `tests/test_r2b_v2_authority_boundary_vi.py` (includes `test_03b`, `test_03c` for global/frame-spoof bypass).

---

## Specification

### Review dimensions (same eight as prior R2b reviews)

1. **Closure-vault reachability** — `vault_dispatch` must not expose ledger/registry/issuer in caller-reachable `__closure__`.
2. **Capability authority** — possession required; ledger injection blocked.
3. **Mutation guard** — no external path to mutate `_SealedStore` without authorized vault-module frame.
4. **Revision binding** — unchanged; moot if 1–3 fail.
5. **Registry/custodian/lease continuity** — unchanged; moot if forged handles possible.
6. **Adversarial-test strength** — tests must prove invariants, not name-absence or guard shape only.
7. **Mutation-sink census** — unchanged scope.
8. **R0801 duplicated-code** — +2 baseline from Corrective V still declarative-only; ratification moot until PASS.

### Required adversarial probes (minimum)

**Break 1 (should stay CLOSED):**

```python
import eval_corpus.r2b_v2._authority_vault as av
inner = object.__getattribute__(
    object.__getattribute__(av, "_vault_holder"), "_VaultHolder__inner"
)
ledger = inner.__closure__[0].cell_contents  # _capability_ledger
ledger["forged"] = {...}  # must raise AuthorityCapabilityError
```

**Break 2 (must be CLOSED at VII — was FAIL at VI):**

```python
# VI attack — must NOT work at ea7bc9d:
getattr(av, "_MUTATION_GUARD")  # must raise AttributeError (global removed)

# Direct store write after reaching registry via inner closure:
registry = inner.__closure__[4].cell_contents
registry._lease_records["evil"] = "payload"  # must raise AuthorityRegistryError

# Foreign frame spoof:
def mint_lease_handle():
    registry._lease_records["spoof"] = "x"
mint_lease_handle()  # must raise AuthorityRegistryError (wrong module)
```

**Dispatch surface:**

```python
assert av.vault_dispatch.__closure__ is None
```

### Test command

```bash
git worktree add /tmp/r2b-review-ea7bc9d ea7bc9d
cd /tmp/r2b-review-ea7bc9d
PYTHONPATH=. python -m pytest tests/test_r2b_v2_* -q
# Expect 139 passed (Cursor claim at handoff time)
git worktree remove /tmp/r2b-review-ea7bc9d --force
```

Use **detached worktree at exact SHA** — do not rely on shared checkout branch (concurrent agents may switch branches mid-review; discard spurious full-suite failures if cwd tip ≠ `ea7bc9d`).

---

## What NOT to build

- No code changes, baseline updates, merge, or I4–I8 advancement from Kiro lane.
- No `convmem record` block unless Ryan says **record block** / **closing** (read-only review).
- Do not re-open Corrective V/VI scope unless new evidence at `ea7bc9d` warrants it.

---

## Test expectations

Cursor claims at `ea7bc9d`:

| Suite | Result |
|-------|--------|
| `tests/test_r2b_v2_*` | **139/139 PASS** |
| Manual Break 1 replay | BLOCKED |
| Manual Break 2 replay (VI `_MUTATION_GUARD` path) | BLOCKED (global absent) |
| Manual direct `_SealedStore` write | BLOCKED |

Kiro must independently confirm on frozen tip.

---

## Acceptance criteria (review PASS)

- [ ] Break 1 remains CLOSED (ledger injection, forged capability, foreign `_issue_capability` name spoof).
- [ ] Break 2 CLOSED: no module-global or closure path opens `_SealedStore` mutation guard.
- [ ] `vault_dispatch.__closure__` is None; inner dispatch reachability does not defeat guarded sinks.
- [ ] Adversarial suite `test_r2b_v2_authority_boundary_vi.py` covers invariant (not just guard shape) — flag gaps if any remain.
- [ ] Full R2b v2 pytest green at exact tip.
- [ ] Verdict: **PASS** or **FAIL** with reproducible evidence (same format as VI review).

---

## Branch convention

```
fix/2026-08-30-2026-08-30-r2b-v2-corrective-vi
```

Lineage: merges PR #252 base (`81becac`) + main integration + Corrective VI (`5ccb6be`) + Corrective VII (`ea7bc9d`).

---

## Related files

| What | Path |
|------|------|
| Authority vault | `eval_corpus/r2b_v2/_authority_vault.py` |
| Corrective VI/VII adversarial tests | `tests/test_r2b_v2_authority_boundary_vi.py` |
| Corrective V adversarial tests | `tests/test_r2b_v2_authority_boundary_v.py` |
| Evidence / inventory | `docs/inter-model/CURSOR-2026-08-29-r2b-v2-i1-i3-evidence.md` |
| Arc brief | `docs/plans/STATUS-r2b-capture-auth.md` |
| Open PR | [#252](https://github.com/alanmz-crypto/convmem/pull/252) |
| VI FAIL review | Kiro session 2026-08-30 (Break 2 `_MUTATION_GUARD` bypass) |
| V FAIL review | Kiro session 2026-08-30 @ `81becac` (closure ledger + ContextVar bypass) |

---

## Governance / sequencing note

Charter default: Copilot audit-lane PASS on same tip before Kiro. Ryan appointed Kiro directly on Corrective VI; flagging so the record stays clean. Verdict stands on merit regardless. After Kiro PASS: Ryan may authorize Copilot audit if charter requires before merge.

**Squash-merge:** OK unless Ryan needs preserved history (silence = squash OK).

---

## Leaving / picking up checklist

**Author (Cursor — leaving):**

- [x] This file on pushed branch
- [ ] `LATEST.md` bullet at top
- [ ] Branch pushed after handoff commit

**Reviewer (Kiro — picking up):**

- [ ] Read this file before review
- [ ] Detached worktree at `ea7bc9d`
- [ ] Run adversarial probes + full pytest
- [ ] Issue PASS/FAIL verdict with dimension table
- [ ] Stop after verdict — no implementation

---

## TL;DR

Corrective VII @ `ea7bc9d` removes `_MUTATION_GUARD` and makes registry mutation frame-based like the ledger guard Kiro already accepted in VI. Kiro re-reviews frozen tip; PASS unlocks Ryan merge/hold on PR #252 lineage; FAIL sends Cursor to Corrective VIII.
