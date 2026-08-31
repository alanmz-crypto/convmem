# [Arc Naturalistic ConvMem product-value evaluation] ChatGPT Handoff — G6/T0 Readiness Review

**Date:** 2026-08-31

**From:** Ryan routing (packet prepared by Cursor after Kiro G5C re-review PASS)

**For:** ChatGPT — independent methodology / G6/T0 **readiness** reviewer

**Authority:** **Advisory only.** This review does **not** authorize G6, T0 freeze,
Agent A, natural episode collection, corpus access, Agent B, scoring, live
parameter selection, or any product disposition. Ryan retains every grant.

**Same-seed preference:** Ryan requests **continuity with your prior G5 corrective
advisory** ([`CHATGPT-2026-08-30-naturalistic-g5-corrective-advisory-handoff.md`](CHATGPT-2026-08-30-naturalistic-g5-corrective-advisory-handoff.md))
if the session seed can be preserved. This is continuation of an already-developed
methodology judgment—not a fresh adversarial second opinion unless you find a
material new risk.

---

## Resume state

| Field | Value |
|---|---|
| **State** | `NOT_STARTED` (awaiting Ryan merge of G5C, then this review) |
| **Prerequisite** | Ryan squash-merges `fix/2026-08-30-naturalistic-g5c-corrective` to `main` |
| **G5C implementation tip** | `a64b566a78daa0286a832cdbcdacca24c6239e2d` |
| **G5C branch tip (docs)** | `d0281b5db83536ff90c64415cfe1f300d6d3fef5` |
| **Kiro G5C re-review** | **PASS** at `a64b566` (same-seed; corrective closes sole flagged defect) |
| **Accepted design carrier** | `c0890701b01f6a2d88a4e37a67bc06ab9551bac4` |
| **Classification** | `methodology_validation_not_product_evidence` — not product evidence |
| **Ryan GATE after you** | Your verdict informs whether Ryan should issue a **narrowly bounded G6 grant**; only Ryan grants G6 |

---

## Context brief

**Who:** ChatGPT judges whether the **now-corrected G5 substrate** is strong enough
to support a **prospective G6/T0 freeze** without yet running the study. Kiro
closed the implementation-review loop; Cursor is parked except mechanical
post-merge doc refresh.

**What:** Independent evidence-packet review of landed G1–G5 + G5C corrective
machinery and synthetic dry-run claims—not a live study audit.

**When:** After G5C merge to `main`; G6 remains **Ryan-LOCKED** until this
review completes and Ryan separately grants G6 if warranted.

**Why:** Ryan locked G6 closed until independent ChatGPT review. Favorable
synthetic `0.3` and dry-run green cannot open G6. The six D1–D6 choices from your
prior advisory were **design inputs** to the corrective; they are **not**
authority to execute G6.

**How:** Read the evidence packet below, answer the readiness questions, return
one gate verdict with an exact **STOP boundary**. Do not implement or authorize.

---

## Sequencing (Ryan-owned)

```text
1. Merge G5C  — Kiro PASS at a64b566 closes implementation review; optional
                 KeyError hardening is NOT a merge blocker.
2. ChatGPT     — this readiness review (you).
3. Ryan        — may issue narrowly bounded G6 grant ONLY if verdict + Ryan lock.
```

---

## Evidence packet (read at post-merge `main` or pre-merge branch tip)

### Verification commands (re-run independently)

```bash
git fetch origin main fix/2026-08-30-naturalistic-g5c-corrective
# After merge: use main tip. Pre-merge review: checkout a64b566 or d0281b5.

python -m pytest -q \
  tests/test_naturalistic_contracts.py \
  tests/test_naturalistic_adjudication.py \
  tests/test_naturalistic_probe.py \
  tests/test_naturalistic_analysis.py \
  tests/test_naturalistic_dry_run.py

python -m compileall -q eval_naturalistic tests
python -m eval_naturalistic.dry_run
```

### Cursor-reported invariant bundle at `a64b566` (Kiro confirmed)

| Check | Result |
|---|---|
| Focused pytest | **119 passed**, 8 subtests |
| `eval_naturalistic.dry_run` | exit 0; **34** scenarios |
| `fixture_seed` | `20260830` |
| Happy-path ledger | **11** individual T0–T10 entries |
| `conditional_effect` (synthetic) | `0.3` — descriptive fixture only |
| `disposition` | `blocked_non_estimable` |
| `g6_authority_assumed` | `false` |
| `product_disposition_emitted` | `false` |
| `all_required_fail_closed_demonstrated` | `true` |

### Review lineage (do not skip)

| Artifact | SHA / role |
|---|---|
| G5C corrective implementation | `a64b566` — Kiro re-review **PASS** |
| Prior G5C implementation | `a77b50f` — Kiro **CORRECTIVE REQUIRED** (import defect) |
| Accepted design carrier | `c089070` |
| Historical G5 on `main` | PR #259 `6843bbee…`; Kiro PASS `23b24959…` (superseded for composition by G5C arc) |
| Kiro re-review handoff | [`CURSOR-2026-08-31-naturalistic-g5c-kiro-rereview-handoff.md`](CURSOR-2026-08-31-naturalistic-g5c-kiro-rereview-handoff.md) |

### Folded D1–D6 context (your prior advisory — not re-decide unless G5C failed them)

These were **advisory inputs** to the corrective design; judge whether **landed
G5C code + fixtures** now honor them:

| ID | Topic |
|---|---|
| D1 | Missingness / treatment-dependent evaluability |
| D2 | Whether a product-value scalar should exist |
| D3 | Opportunity authority (sealed registry) |
| D4 | Boundable versus invalid failures |
| D5 | Disposition precedence and reason taxonomy |
| D6 | Minimum defensible C0/C1 isolation / paired replay |

---

## What you are judging (readiness questions)

Answer each with **evidence** (file, test name, or scenario id)—not chat summary.

1. **Methodology boundary exercised:** Does G5C genuinely exercise its claimed
   T0–T10 methodology boundary (individual ledger, serialized-byte T0 completeness,
   registry authority, bounds, precedence, replay)—not only grouped `stage_ok` flags?

2. **Substantive fail-closed:** Are fail-closed controls **substantive** rather than
   fixture theater? Do adversarial scenarios prove rejection paths, not just happy-path labels?

3. **Synthetic `0.3` quarantine:** Is the favorable synthetic `0.3` **structurally
   prevented** from becoming product evidence (disposition, classification, gate slots)?

4. **G1–G4 guarantees:** Did G5C bypass or weaken any landed G1–G4 guarantee without
   an explicit corrective contract? (`run_g4_safe_synthetic_example()` semantics?)

5. **Legitimate PENDING parameters:** What numerical / gate slots **legitimately
   remain PENDING** after G5C, and are they blocked from silent defaults?

6. **Bounded G6 feasibility:** Can G6 be defined so it **stops before** Agent A,
   natural episode collection, corpus/index access, Agent B execution, live scoring,
   and product interpretation—while still constituting a meaningful prospective
   **T0 freeze** grant?

7. **Optional hardening (non-blocking):** Kiro noted a pre-existing unreachable
   `KeyError` on bare partial manifest dicts (masked by old `NameError`). Does this
   affect G6/T0 readiness, or is it correctly deferred?

---

## Required output shape

Return exactly one primary gate verdict:

### Option A — `G6/T0 READY FOR BOUNDED GRANT`

Use only if you believe the corrected substrate supports authorizing Ryan to
issue a **narrowly bounded G6/T0 freeze grant** (roles, schedule/window shell,
environment contracts, parameter **slots** still pending—not live values).

Include:

- **Bounded G6 sketch** — what a grant may include vs must exclude (bullet STOP list).
- **Ryan must lock** — decisions Ryan cannot delegate to architecture.
- **Ryan may defer** — safe defaults already in EXECUTION/ARCHITECTURE.
- **Residual risks** — ranked; which block live study vs which are T7+ concerns.

### Option B — `CORRECTIVE/PREREQUISITE REQUIRED BEFORE G6`

Use if methodology, fixtures, or docs must change before G6 can even be bounded.

Include:

- **Prerequisite list** — bounded file/section scope; no drive-by redesign.
- **What does NOT need reopening** — preserve surgical continuity.
- **Re-review trigger** — exact artifact tip or test that must pass next.

### Mandatory footer (both options)

```text
STOP boundary: [One paragraph — what this ChatGPT review authorizes and explicitly
does NOT authorize. State that G6/T0 READY is NOT G6 execution, NOT Agent A/B,
NOT corpus access, NOT product conclusion. Only Ryan grants G6.]

ChatGPT does NOT: implement, merge, select live parameters, access natural evidence,
or infer product value from synthetic 0.3.
```

---

## Read these first

| Purpose | Path |
|---|---|
| Arc brief | [`../plans/STATUS-naturalistic-product-value.md`](../plans/STATUS-naturalistic-product-value.md) |
| Architecture (corrective amendment on branch) | [`../plans/ARCHITECTURE-naturalistic-product-value.md`](../plans/ARCHITECTURE-naturalistic-product-value.md) |
| Execution contract | [`../plans/EXECUTION-naturalistic-product-value.md`](../plans/EXECUTION-naturalistic-product-value.md) |
| G5C orchestrator + scenarios | [`../../eval_naturalistic/dry_run.py`](../../eval_naturalistic/dry_run.py) |
| G5C contracts / T0 validator | [`../../eval_naturalistic/contracts.py`](../../eval_naturalistic/contracts.py) |
| Analysis / bounds / precedence | [`../../eval_naturalistic/analysis.py`](../../eval_naturalistic/analysis.py) |
| Dry-run tests | [`../../tests/test_naturalistic_dry_run.py`](../../tests/test_naturalistic_dry_run.py) |
| Prior ChatGPT D1–D6 advisory | [`CHATGPT-2026-08-30-naturalistic-g5-corrective-advisory-handoff.md`](CHATGPT-2026-08-30-naturalistic-g5-corrective-advisory-handoff.md) |
| Kiro G5C re-review PASS | [`CURSOR-2026-08-31-naturalistic-g5c-kiro-rereview-handoff.md`](CURSOR-2026-08-31-naturalistic-g5c-kiro-rereview-handoff.md) |

---

## Do not do

- No code, tests, schemas, config, or generated artifacts
- No numerical parameter selection, sample size, seed, or study window values
- No corpus/Chroma/natural evidence inspection
- No authorization of G6 execution, Agent A/B, scoring, or product disposition
- No treating this verdict as Ryan's G6 grant

---

**TL;DR:** [Arc Naturalistic] After Ryan merges G5C, ChatGPT judges whether the
corrected G5 substrate supports a **bounded G6/T0 freeze grant** without running
the study. Return `G6/T0 READY FOR BOUNDED GRANT` or `CORRECTIVE/PREREQUISITE
REQUIRED BEFORE G6` with an exact STOP boundary. Same-seed continuity preferred.
This review does not open G6 — Ryan does.
