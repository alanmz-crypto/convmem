# CG-1 Closure Gate G4a — Supplemental Context for ChatGPT

**Date:** 2026-08-10
**Author:** Kiro (consolidating Sol's closure output for GPT review)
**For:** ChatGPT (independent reviewer)
**Relates to:** `HANDOFF-CG1-DEPENDABILITY-2026-08-10.md` (read that first)

---

## Status update since the original handoff

Since the HANDOFF doc was written, **Codex Sol (Luna xHigh)** completed the CG-1
implementation, ran all gates, and produced a closure packet. The implementation
has advanced from "uncommitted in `/tmp/convmem-cg1`" to a proper stabilization
commit — but that commit is **local and unpushed**, pending independent review.

## Frozen artifact state

| Field | Value |
|-------|-------|
| Stabilization SHA | `7ac88cb3e38a96a9d7b4d03f4952a140d300c03c` |
| Tree hash | `149612bf1131599450ed8662196c59e0d5257e20` |
| Branch | `feat/2026-08-10-2026-08-10-cg1-committed-generation-substrate` |
| Worktree | `/tmp/convmem-cg1-delivery` (clean) |
| Baseline (main) | `0be0a05b9984ba2b23b2f1dc1728904951560d96` |
| Diff | 18 files, +4,567 / -20 |
| Push state | **Local only — one commit ahead of origin** |
| Remote/PR head | `7a35dbf0f5d081164ef2856ef4951f6b259878e8` |
| PR | [#172](https://github.com/alanmz-crypto/convmem/pull/172) — does NOT yet contain the stabilization commit |

**Important:** The stale `/tmp/convmem-cg1` worktree (referenced in the original
handoff) is superseded. The authoritative bytes are in `/tmp/convmem-cg1-delivery`.

## What changed between the original handoff and closure

The stabilization commit adds:
- Missing closure evidence (ext4 Bar-P probe results, replay-tail test, negative
  cold-validation test)
- Classification of the hermetic Chroma constructor
- Minor fixes surfaced during the full-suite run

The core architecture and module structure are unchanged from what the original
handoff described.

## Gate evidence summary

### G1 — Legacy dedupe compatibility
16 tests passed. The `generation_identity_fields=False` default preserves existing
caller behavior exactly. Key test: `test_commit_suppresses_exact_and_keeps_semantic_candidate`.

### G2 — Process/fault durability

**Process-crash tests:** 14 passed. `os._exit()` in child processes, parent reopens
Chroma and validates exact manifest row sets.

**Replay tail evidence:** Chroma embeddings_queue advanced from seq_id 1200 → 2000
while the vector segment remained at 1200. A fresh reopen recovered the exact
2,000-row set. This proves Chroma's internal WAL (the `embeddings_queue` table)
replays uncommitted segment writes on restart.

**Ext4 Bar-P (measured on production filesystem):**
- Device: `/dev/nvme0n1p2`, ext4
- `journal_mode = delete`
- `synchronous = 2` (FULL)
- Observed syscall pattern per transaction:
  1. `fsync(journal)`
  2. `fsync(directory)`
  3. `fsync(journal)`
  4. `fsync(database)`
  5. `unlink(journal)`
- **No directory fsync after journal unlink** — confirms FULL, not EXTRA
- **Complete power-loss durability explicitly unclaimed** (the unlink-without-final-
  dirsync gap means a recent transaction could roll back after sudden power loss)

### G3 — Fresh-process negative test
Persisted immutable document corruption (tampered bytes on disk) is rejected by a
fresh interpreter with an exact document-hash mismatch error. Proves the cold
validator actually compares content, not just structure.

### G5 — Full repository suite
1,275 tests passed, 230 subtests passed, 3 warnings, 0 failures.

### Representative scale
NOT GATED. The existing 1,300-owner / 20,000-unit test provides supplementary
evidence but no governing numeric threshold exists in the acceptance criteria.

### Ext4 probe evidence
Remains untracked at `.cg1-ext4-probe/` — outside the stabilization commit
(probe artifacts are measurement evidence, not implementation source).

## Sol's conformance review (self-review)

All areas PASS except one GAP:

| Area | Verdict |
|------|---------|
| Deterministic identity | PASS |
| Builder atomicity | PASS |
| Logical/physical identity | PASS |
| Legacy dedupe bridge | PASS |
| Inactive-generation isolation | PASS |
| Abandoned backpressure | PASS |
| Per-owner pointer/stale refusal | PASS |
| Recovery never guesses | PASS |
| Post-publication uncertainty | PASS |
| Cold validator | PASS |
| **Cold-validation binding to promotion** | **GAP** |

## The material GAP — cold-validation binding

### What Sol found

`publish_active_pointer()` accepts an arbitrary `exact_generation_validator`
callback. The API contract is:

```python
def publish_active_pointer(
    generation_root,
    manifest_reference,
    *,
    exact_generation_validator: Callable[[Mapping[str, Any]], Any],
    ...
) -> QualifiedActivePointer:
```

A caller can supply `lambda manifest: True` and the function will mint a
`QualifiedActivePointer` without any actual validation having occurred.

### Why it matters

The locked architecture lifecycle is:

```
built → validated → durably promoted → serving
```

"Validated" specifically means **fresh-process exact generation recovery** —
reopening Chroma in a new interpreter and confirming every manifest row exists
with exact immutable content. If the substrate permits promotion without that
step, the lifecycle invariant depends on caller discipline rather than structural
enforcement.

### Competing interpretations

1. **Acceptable dependency injection:** The pointer layer is a generic mechanism;
   the caller owns qualification and bears responsibility for supplying a real
   validator. The substrate's job is atomic pointer mechanics, not policy.

2. **Locked lifecycle violation:** The substrate itself must prevent promotion
   unless fresh-process qualification evidence exists. A permissive callback leaves
   the safety invariant unenforced at the API boundary.

### Sol's recommendation

Sol recommends interpretation 2 (structural enforcement). The locked sequence
explicitly places fresh-process exact validation *before* pointer promotion. A
permissive callback makes it possible to skip that step.

### What this means for review

**For ChatGPT's literature review:** Does the literature on atomic-commit protocols
support the principle that safety invariants should be structurally enforced at the
API boundary rather than left to caller convention? (Compare: a database that allows
`COMMIT` without checking constraints vs. one that rejects it.)

**For independent code review:** Should `publish_active_pointer()` require proof
that `run_cold_validation()` (or an equivalent subprocess validator) actually ran
on this specific manifest? What form should that proof take?

### If confirmed as a defect

Sol specified the mandated correction loop:
1. Minimum correction (structural binding)
2. Targeted tests
3. Ruff pass
4. Full suite pass
5. New stabilization commit/SHA
6. New Sol packet
7. New independent audit

No fix has been applied. The stabilization SHA `7ac88cb3...` contains the GAP.

## Closure equation

```
tested bytes       = 7ac88cb3…
Sol-reviewed bytes = 7ac88cb3…
independently reviewed bytes = NONE
Ryan-accepted bytes           = NONE
pushed bytes                  = 7a35dbf0… (does NOT include stabilization)
```

The acceptance condition:

```
tested bytes = reviewed bytes = accepted bytes = pushed bytes
```

is **not yet satisfied**. Independent review of the exact bytes (including the GAP
disposition) is required before push or merge.

## Explicit CG-2 deferrals (unchanged)

These are out of scope for CG-1 and not addressed:
- Production activation and read cutover
- Pruning/GC of abandoned generations
- `doctor.index_drift` update for generation-aware counting
- `projection_parity.entity_key` migration
- Semantic queue-depth growth from physical-pair uniqueness
- Legacy path-alias bootstrap
- Production read bypasses and TOCTOU
- Performance acceptance criteria
- Shadow Ledger activation or WAL

## What ChatGPT should do with this

1. **Read the original handoff first** (`HANDOFF-CG1-DEPENDABILITY-2026-08-10.md`)
   for architecture context and the 5 verification questions.

2. **Consider the GAP** in the context of the literature on atomic-commit protocols,
   type-level safety proofs, and API boundary enforcement. Is Sol's recommendation
   (structural enforcement) supported by the literature? What's the minimal fix?

3. **Review the gate evidence** against the literature:
   - Does the ext4 Bar-P measurement correctly characterize the durability boundary?
   - Is the replay-tail evidence sufficient for process-crash recovery claims?
   - Does the cold-validation negative test prove what it claims?

4. **Provide a verdict** on whether the stabilization bytes (minus the GAP fix)
   represent a sound implementation of the locked architecture.

5. **Disposition the GAP:** confirm, reject, or propose an alternative framing.
   If confirmed, the correction loop runs before push.
