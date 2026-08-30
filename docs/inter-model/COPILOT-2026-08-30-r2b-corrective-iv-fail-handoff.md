# Implementation Handoff: [Arc Unbroken Key] Corrective IV authority-boundary FAIL

**Date:** 2026-08-30  
**Author:** GitHub Copilot audit lane  
**For:** Cursor implementation  
**Authorization:** Ryan, 2026-08-30 (failed review returns the candidate to implementation; explicit handoff request)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `IN_PROGRESS` — a local Corrective V candidate exists but is unpushed, unreviewed, and has no PR |
| **Implementation branch** | `fix/2026-08-30-2026-08-30-r2b-v2-corrective-v` |
| **Local candidate tip** | `20d7f567184500c33c9c82eb0d1c4d90fe6bc5f2` |
| **Failed reviewed tip** | `6b5a8f9e441d028bafe8d586ec91199c3ecca219` |
| **Integration base** | `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d` |
| **Push status** | **local-only** — remote Corrective V branch still points to `e930ae4`; local branch is 13 commits ahead |
| **PR** | #252 remains the failed Corrective IV candidate; Corrective V has no PR |
| **Ryan GATE** | First confirm single-writer ownership, stabilize and push Corrective V with an explicit refspec, and obtain CI-green immutable bytes. Kiro review, merge, activation, live authority, and I4-I8 remain blocked until a fresh exact-tip Copilot PASS. |
| **Track A ingest** | `~/.copilot/session-state/2f91a6c3-9e08-4065-9d0e-3bd460104bb0/events.jsonl` |

## Arc identity and current standing

**Arc: Unbroken Key**

The name captures the governing invariant: trusted R2b source authority may
exist only while the genuine canonical writer-gate remains continuously
possessed by its original custodian. Metadata that describes a lock, an
in-process token, a private Python object, or a registry entry is not possession.

Copilot independently reviewed the immutable Corrective IV tip
`6b5a8f9e441d028bafe8d586ec91199c3ecca219` and returned:

> **FAIL — blocking authority path remains**

Corrective IV preserved the valid hermetic lifecycle and closed stale authority
after genuine kernel-lock loss. It did not establish an authority boundary
against ordinary imported Python code.

## Exact candidate lineage

| Role | SHA |
|------|-----|
| Integration base | `e930ae4c2fb67eabbfa570f7caacda8d9ddac79d` |
| Failed Corrective III tip | `99014697b0b0e9a4c563ea0ca0d89135513a33b5` |
| Corrective IV semantic implementation | `1b0dd44fe8797d12c8627512b36e079f677adcc0` |
| Corrective IV pre-lint evidence tip | `d3c248e960368e2e57b01d7bc851813a72f358da` |
| Reviewed final CI-green tip | `6b5a8f9e441d028bafe8d586ec91199c3ecca219` |
| Local unreviewed Corrective V candidate | `20d7f567184500c33c9c82eb0d1c4d90fe6bc5f2` |

As of this handoff, #252 remains an open draft at the reviewed SHA. All five
required GitHub checks are green. CI success is not authority-boundary evidence.
Separately, Cursor created local commit `20d7f56` on
`fix/2026-08-30-2026-08-30-r2b-v2-corrective-v`. Its commit message claims a
vault-backed corrective, exact revision binding, and per-operation sink
scanning. Copilot has not inspected or reviewed those bytes. The remote branch
still points to the integration base, so this candidate is not yet a durable
review target.

## What to build

Inspect, stabilize, and prove the local Corrective V candidate. It must make
trusted I1-I3 authority unmanufacturable, unmodifiable, and unusable by ordinary
imported Python unless the authority owner itself continuously possesses the
genuine canonical kernel lock. Treat commit `20d7f56` as an implementation
claim, not as evidence that any review category is closed.

**Why this exists:** Corrective IV relies on in-process Python secrecy and
encapsulation. Ordinary callers can recover the mint secret, reconstruct
production capabilities, substitute a fake custodian, and recover the live
registry from a closure.

## Blocking findings

| Severity | Location | Defect | Authority classes |
|----------|----------|--------|-------------------|
| HIGH | `eval_corpus/r2b_v2/_authority_capability.py:28` | `_CAPABILITY_ISSUER_SECRET`, `_binding_digest`, and writable slots allow `object.__new__` reconstruction of production mint capabilities; lease mint accepts a duck-typed fake custodian. | manufacture, mint phase, gate substitution, test/production equivalence, custodian substitution, replay, proof reconstruction |
| HIGH | `eval_corpus/r2b_v2/_registry_mint.py:500` | `_registry_op.__closure__` exposes the live `_TrustedRegistry`; callers can enable `_internal_mutation_active` and rewrite all backing authority state. | registry fabrication, stale authority, custodian substitution, replay, reconstruction |
| MEDIUM | `eval_corpus/r2b_v2/coverage/proof.py:340` | Production revision resolution binds authority to inventory SHA `1b0dd44f...` while executing reviewed code at `6b5a8f9...`. | implementation-revision substitution |
| MEDIUM | `eval_corpus/r2b_v2/coverage/inventory.py:391` | Generation-pointer mutation discovery suppresses new sinks solely because their filename is already classified as `cg2_d4`. | mutation-sink governance concealment |

All four are semantic authority-boundary defects, not publication-only drift.

## Reproducers that the next candidate must defeat

### 1. Reconstructed production mint capability

The complete executed chain is preserved in Track A. Its critical primitive is:

```python
import eval_corpus.r2b_v2._authority_capability as caps

capability = object.__new__(caps.AuthorityMintCapability)
capability._issuer_secret = caps._CAPABILITY_ISSUER_SECRET
capability._phase = caps.MintPhase.LEASE
capability._binding_digest = caps._binding_digest(
    caps.MintPhase.LEASE,
    attacker_selected_binding,
)
capability._capability_id = "attacker-lease"
capability._trust_class = "production"
capability._census_stage = 0
```

The review then passed this forged capability plus a duck-typed custodian whose
`verify()` returned successfully through `mint_lease_handle`, followed by a
forged source capability through `compose_and_mint_source_authority`.

Observed final result:

```text
SourceAuthorityProof attacker-run True production
```

The next candidate must reject the complete chain, not only this spelling.

### 2. Live registry recovery and mutation

```python
import eval_corpus.r2b_v2._registry_mint as mint

facade = mint._registry_op.__closure__[0].cell_contents
inner = facade["op"]
registry = next(
    cell.cell_contents
    for cell in inner.__closure__
    if isinstance(cell.cell_contents, mint._TrustedRegistry)
)

registry._internal_mutation_active = True
registry._lease_records["attacker"] = "fabricated-live-registry-entry"
registry._internal_mutation_active = False
assert registry._lease_records["attacker"] == "fabricated-live-registry-entry"
```

Moving state into another Python closure, object, descriptor, or private module
does not close this class.

### 3. Stale implementation revision

```python
from chroma_write_store import current_code_revision
from eval_corpus.r2b_v2.coverage.inventory import load_v2_implementation_tip
from eval_corpus.r2b_v2.coverage.proof import _resolve_implementation_revision

assert current_code_revision() == \
    "6b5a8f9e441d028bafe8d586ec91199c3ecca219"
assert load_v2_implementation_tip() == \
    "1b0dd44fe8797d12c8627512b36e079f677adcc0"
assert _resolve_implementation_revision(
    code_revision=None,
    test_override=False,
) == "1b0dd44fe8797d12c8627512b36e079f677adcc0"
```

Production authority must fail closed unless its full immutable implementation
identity matches the executing authority implementation.

### 4. Known-filename mutation-sink concealment

```python
from unittest import mock
import eval_corpus.r2b_v2.coverage.inventory as inventory

inventory.clear_inventory_scan_cache()
with mock.patch.object(
    inventory,
    "_scan_repo_pattern",
    return_value=["cg2_rehearsal.py:888"],
):
    assert inventory._scan_generation_pointer_write_uncached() == []
```

The next candidate must report the simulated new sink as ungoverned. A known
route or filename cannot grant blanket governance to new mutation operations.

## Required implementation properties

1. Production mint authority and authoritative registry state must not live in
   the ordinary caller's Python interpreter. Do not replace the current closure
   with another reflective Python container.
2. The component that owns production mint authority must itself own and
   continuously verify the canonical kernel lock. Caller-supplied gate metadata,
   custodian objects, or successful `verify()` methods are insufficient.
3. Production callers receive only opaque, chain-bound references whose use is
   mediated by the isolated authority owner. Copying, serialization,
   `object.__new__`, monkeypatching, closure inspection, or structural
   substitution must not create production-equivalent authority.
4. Revocation must propagate through lease, coverage, source authority,
   custodian release, kernel-lock loss, epoch invalidation, fork, and relevant
   reload behavior.
5. Every authority chain must bind the exact full implementation identity used
   to execute it. Evidence and runtime identity mismatches fail closed.
6. Mutation coverage must govern exact sinks or equivalent semantic call sites.
   A new sink in an existing file must be independently discovered and refused
   until explicitly governed.

## What NOT to build

- Do not treat underscore names, internal modules, `__all__`, hidden attributes,
  slots, context managers, stack inspection, closures, or documentation as the
  security boundary.
- Do not add another test-only policy, revision override, fake custodian, or
  fixture that normal verification accepts as production authority.
- Do not acquire live production authority or run a production capture.
- Do not advance I4-I8, ratify concrete durations, merge #252, or activate R2b.
- Do not change CG-2 or Recovery Authority semantics except where exact
  mutation-sink accounting requires reading their existing routes.

## Test expectations

Add focused adversarial regressions that:

1. Attempt the complete capability-forging chain above and prove no production
   coverage, lease, source handle, or public proof is issued.
2. Exhaust ordinary Python reflection surfaces and prove no authoritative
   registry object or mutable backing state is recoverable.
3. Substitute fake custodians, fake lock objects, alternate gates, copied or
   reconstructed handles, stale records, and cross-chain material.
4. Release the actual kernel lock while preserving all caller-held memory and
   prove every dependent source authority fails closed.
5. Exercise fork and relevant reload behavior.
6. Prove implementation identity mismatch and abbreviated or arbitrary revision
   values fail closed.
7. Inject a new generation-pointer mutation sink into an already-known route
   and prove the scanner reports it as ungoverned.
8. Preserve the legitimate hermetic canonical lifecycle.

## Acceptance criteria

- [ ] All thirteen adjudication categories from the review are `CLOSED`.
- [ ] Ordinary imported Python cannot manufacture production mint authority.
- [ ] Ordinary imported Python cannot recover or rewrite authoritative registry state.
- [ ] A fake or structurally equivalent custodian cannot authorize a lease.
- [ ] Actual kernel-lock loss invalidates all dependent authority.
- [ ] Cross-chain and stale-handle replay fail closed.
- [ ] Runtime and evidence bind the same full immutable implementation identity.
- [ ] New mutation sinks in known files are detected independently.
- [ ] The legitimate hermetic canonical lifecycle still succeeds.
- [ ] Focused R2b tests, full pytest, pylint, CodeQL, and both Analyze jobs pass.
- [ ] Copilot independently reviews one new immutable tip and returns PASS.
- [ ] Only after Copilot PASS does Kiro review that same exact tip.

## Adjudication state at departure

| Category | Disposition |
|----------|-------------|
| Authority-capability manufacture | `RESIDUAL DEFECT` |
| Caller-accessible mint phase | `RESIDUAL DEFECT` |
| Backing registry fabrication | `RESIDUAL DEFECT` |
| Canonical-gate substitution | `RESIDUAL DEFECT` |
| Test/production authority equivalence | `RESIDUAL DEFECT` |
| Custodian substitution | `RESIDUAL DEFECT` |
| Kernel-lock-loss survival | `CLOSED` |
| Stale dependent authority | `RESIDUAL DEFECT` |
| Cross-chain replay | `RESIDUAL DEFECT` |
| Proof reconstruction | `RESIDUAL DEFECT` |
| Issuance TOCTOU | `CLOSED` |
| Implementation-revision substitution | `RESIDUAL DEFECT` |
| Mutation-sink governance concealment | `RESIDUAL DEFECT` |

## Related files

| What | Path |
|------|------|
| Arc status | `docs/plans/STATUS-r2b-capture-auth.md` |
| Normative architecture | `docs/plans/ARCHITECTURE-r2b-mutable-source-quiescence-v2.md` |
| Execution plan | `docs/plans/EXECUTION-2026-08-27-r2b-v2-quiescence.md` |
| Verification plan | `docs/plans/VERIFY-r2b-v2-quiescence.md` |
| Candidate evidence | `docs/inter-model/CURSOR-2026-08-29-r2b-v2-i1-i3-evidence.md` at reviewed tip |
| Exact candidate diff | `https://github.com/alanmz-crypto/convmem/compare/e930ae4c2fb67eabbfa570f7caacda8d9ddac79d...6b5a8f9e441d028bafe8d586ec91199c3ecca219` |

## Leaving / picking up checklist

**Author (leaving):**

- [x] Exact reviewed SHA and immutable base recorded
- [x] Blocking reproducers and adjudication matrix recorded
- [x] `LATEST.md` points to this handoff
- [x] `STATUS-r2b-capture-auth.md` reflects the failed gate
- [x] Arc codename added to canonical protocol surfaces
- [x] Handoff branch pushed

**Implementer (picking up):**

- [ ] Read this file before editing
- [ ] Confirm no other agent owns the shared Corrective V checkout
- [ ] Inspect local commit `20d7f56` and preserve the failed #252 history
- [ ] Push the stabilized branch with an explicit refspec; remote is currently still at `e930ae4`
- [ ] State Goal / role / system state / next action under **Arc Unbroken Key**
- [ ] Preserve the scope locks and produce a new immutable review tip

**TL;DR:** **[Arc Unbroken Key]** Corrective IV is CI-green but fails the
ordinary-Python authority boundary. Local Corrective V candidate `20d7f56`
exists but is unpushed and unreviewed; stabilize and publish it before fresh
Copilot review, then Kiro only after PASS.
