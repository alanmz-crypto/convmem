# [Arc Naturalistic ConvMem product-value evaluation] Luna Same-Seed Closure Re-Review — T0 Seal State

**Date:** 2026-08-31  
**Author:** Cursor (implementation)  
**For:** Codex Luna (same-seed narrow closure review) + Ryan (routing)  
**Authorization:** Ryan 2026-08-31 — Luna + Cursor sufficient; no Claude pass; G6 closed.

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `READY_FOR_LUNA_REREVIEW` |
| **Branch** | `fix/2026-08-30-naturalistic-g5c-corrective` |
| **Tip SHA** | `d902b4919a25c59ed272ac1961916f3f011866ab` |
| **Synthetic fixture seed** | `20260830` (`G4_SYNTHETIC_FIXTURE_SEED`) — **same seed as prior Luna pass** |
| **Ryan GATE** | Luna closure PASS → Ryan may merge G5C branch; G6 still separate grant |
| **G6 authority** | **CLOSED** |

---

## Context for Luna (not a redesign request)

| Revision | What Luna saw | Status |
|----------|---------------|--------|
| `a64b566` | Pending-at-freeze false-green (eight `PENDING` slots could pass T0 freeze) | **Closed** at `93d4ce4` via `validate_prospective_manifest_freeze_transition` |
| `a64b566` / post-`93d4ce4` | Freeze validator did not require `header.sealed=True` or independent seal metadata | **Closed** at this tip |

**Stale inference to discard:** “current G5C artifact still contains the original T0 false-green defect” — that referred to `a64b566`, not the post-`93d4ce4` branch.

---

## What changed at this tip (seal slice only)

`validate_prospective_manifest_freeze_transition()` now:

1. Requires `header.sealed=True` at `FRAME_FROZEN`.
2. Requires non-empty `seal_time`.
3. Verifies `content_digest` against body **excluding** `logged_freeze_digest` (post-seal field).
4. Preserves pending/frozen slot rules from `93d4ce4`.

**New adversarial scenario:** `unsealed_manifest_blocks_frame_frozen` — `sealed=False` with otherwise self-consistent `logged_freeze_digest` **fails** freeze transition.

**New unit test:** `test_unsealed_manifest_fails_freeze_transition_with_valid_digest`.

---

## Luna closure checklist (narrow — verify closure only)

| # | Question | Expected |
|---|----------|----------|
| 1 | Eight `PENDING` + sealed: draft OK, freeze FAIL | Yes (from `93d4ce4`) |
| 2 | Eight fixture-frozen + sealed: freeze PASS | Yes |
| 3 | `sealed=False` + self-consistent freeze digest: freeze FAIL | Yes (this tip) |
| 4 | T0 cannot PASS on unsealed manifest | Yes |
| 5 | T0 cannot PASS on pending manifest | Yes |
| 6 | Synthetic `0.3` still no product disposition / no G6 authority | Yes |
| 7 | No Agent A/B, corpus, live collection introduced | Yes |

---

## Verification commands

```bash
git fetch origin fix/2026-08-30-naturalistic-g5c-corrective
git checkout fix/2026-08-30-naturalistic-g5c-corrective
python -m pytest tests/test_naturalistic_*.py -q
python -m eval_naturalistic.dry_run
```

Inspect:

- `eval_naturalistic/contracts.py` — `_validate_frozen_artifact_seal`, `validate_prospective_manifest_freeze_transition`
- `eval_naturalistic/dry_run.py` — `_adversarial_unsealed_manifest_blocks_frame_frozen`
- `tests/test_naturalistic_contracts.py` — freeze transition tests

---

## Codex Luna invocation (same seed / same arc)

Use the same Luna posture as the prior naturalistic G5C review (`gpt-5.6-luna`,
high reasoning effort). Scope is **closure verification** at exact branch tip —
not methodology redesign, not source-authority formalization (separate track).

---

## Out of scope for this review

- Claude adversarial pass (Ryan: no action)
- Source-authority architecture formalization (Luna refinements → bounded formalization later)
- Resolver implementation before strict no-collection T0 freeze
- G6 grant, live collection, Agent A/B

---

## Related handoffs

| Doc | Role |
|-----|------|
| [`CURSOR-2026-08-31-naturalistic-g5c-t0-freeze-handoff.md`](CURSOR-2026-08-31-naturalistic-g5c-t0-freeze-handoff.md) | ChatGPT pending-at-freeze slice (`93d4ce4`) |
| [`CHATGPT-2026-08-31-naturalistic-g6-t0-readiness-handoff.md`](CHATGPT-2026-08-31-naturalistic-g6-t0-readiness-handoff.md) | ChatGPT readiness (prerequisite identified) |
| [`CURSOR-2026-08-31-naturalistic-g5c-kiro-rereview-handoff.md`](CURSOR-2026-08-31-naturalistic-g5c-kiro-rereview-handoff.md) | Kiro PASS at `a64b566` |

---

**TL;DR:** [Arc Naturalistic] Luna: same seed `20260830`, exact branch tip — verify
the seal-state hole is closed (unsealed manifest cannot pass freeze transition)
and pending-at-freeze remains closed. Not a redesign. G6 still closed.
