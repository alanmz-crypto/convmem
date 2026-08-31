# [Arc Naturalistic ConvMem product-value evaluation] Ryan Gate — Merge G5C, Then ChatGPT

**Date:** 2026-08-31

**Author:** Cursor implementation lane (coordination only — no further code)

**For:** Ryan (merge authority); ChatGPT (next substantive reviewer)

**Authorization:** Kiro same-seed re-review **PASS** at `a64b566`. G6 remains
**closed** until ChatGPT readiness review + Ryan explicit grant.

---

## Resume state

| Lane | State | Next action |
|---|---|---|
| **Ryan** | `READY_TO_MERGE_G5C` | Squash-merge PR; then send ChatGPT the readiness packet |
| **ChatGPT** | `NOT_STARTED` | Independent G6/T0 readiness review after merge |
| **Cursor** | `PARKED` | Post-merge STATUS/LATEST refresh only if Ryan asks |
| **Kiro** | `DONE` (G5C loop) | No reopen unless new corrective |
| **G6** | `NOT AUTHORIZED` | ChatGPT verdict ≠ grant |

---

## Step 1 — Ryan merges G5C (no reopen for KeyError hardening)

| Item | Value |
|---|---|
| Branch | `fix/2026-08-30-naturalistic-g5c-corrective` |
| Tip | `d0281b5db83536ff90c64415cfe1f300d6d3fef5` |
| Implementation | `a64b566` (+ full G5C body `a77b50f`) |
| Kiro | PASS at `a64b566` (same-seed re-review) |
| Squash | **OK** (default) |

**PR title:** `fix: repair G5 synthetic methodology composition (G5C corrective)`

**Merge reading after squash:**

- [`docs/plans/STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md)
- [`docs/inter-model/CHATGPT-2026-08-31-naturalistic-g6-t0-readiness-handoff.md`](CHATGPT-2026-08-31-naturalistic-g6-t0-readiness-handoff.md)
- [`docs/plans/EXECUTION-naturalistic-product-value.md`](../plans/EXECUTION-naturalistic-product-value.md)

**Non-blocker deferred:** Kiro flagged unreachable `KeyError` on bare partial
manifest dicts — pre-existing, not introduced by G5C corrective; optional future
tiny slice if Ryan wants.

---

## Step 2 — ChatGPT G6/T0 readiness review

**Packet:** [`CHATGPT-2026-08-31-naturalistic-g6-t0-readiness-handoff.md`](CHATGPT-2026-08-31-naturalistic-g6-t0-readiness-handoff.md)

**Same-seed:** preserve ChatGPT continuity with
[`CHATGPT-2026-08-30-naturalistic-g5-corrective-advisory-handoff.md`](CHATGPT-2026-08-30-naturalistic-g5-corrective-advisory-handoff.md)
if possible.

**Expected verdict (one of):**

- `G6/T0 READY FOR BOUNDED GRANT` — Ryan may *consider* a narrow G6 grant document
- `CORRECTIVE/PREREQUISITE REQUIRED BEFORE G6` — more methodology work before G6 can be bounded

**ChatGPT review does NOT authorize G6.** Ryan alone grants G6 after verdict + lock.

---

## Step 3 — Cursor mechanical refresh (only if Ryan asks)

After merge to `main`, update in one docs commit:

1. **`docs/plans/STATUS-naturalistic-product-value.md`** — overwrite sections 3–6:
   - G5C **DONE on `main`** (post-merge SHA)
   - G6 **NOT AUTHORIZED — ChatGPT GATE in flight / complete**
   - Remove `NOT_STARTED` G5C implementation language
   - One Update Log line: merge + Kiro PASS + ChatGPT gate state

2. **`docs/inter-model/LATEST.md`** — top bullet: G5C LANDED; ChatGPT G6/T0 readiness active

**Do not** send Cursor for implementation unless ChatGPT returns
`CORRECTIVE/PREREQUISITE REQUIRED` with a bounded grant, or Ryan authorizes optional KeyError slice.

---

## Lane routing summary

```text
Ryan merge G5C
    → ChatGPT readiness review (advisory)
    → Ryan decides bounded G6 grant (or not)
    → [future] G6 T0 freeze implementation lane (not Cursor unless authorized)
```

Synthetic `0.3` remains **methodology fixture only** — not product evidence.

---

**TL;DR:** Merge G5C now (Kiro PASS). Next substantive gate is ChatGPT G6/T0
readiness — packet at `CHATGPT-2026-08-31-naturalistic-g6-t0-readiness-handoff.md`.
Cursor parked except optional post-merge STATUS/LATEST. G6 still Ryan-gated.
