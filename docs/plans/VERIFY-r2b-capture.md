# Verify Plan — R2b capture

```
Planning Status

Phase:        Verify (R2b capture — stub)
Characters:   Independent Reviewer
Functions:    Reviewer
Lanes:        Cursor (mechanical); Kiro (sign-off); Ryan (GATE)
Authority:    Post-Execute HITL — do not trust prior chat claims alone
```

**Subject / tip:** _(fill after grant)_  
**PR(s):** _(planning PR; live capture separate)_  
**EXECUTION:** [`EXECUTION-2026-07-20-r2b-capture.md`](EXECUTION-2026-07-20-r2b-capture.md)  
**CLI:** `scripts/eval_corpus_capture.py`  
**Goal:** Prove one authorized R2b capture produced an immutable corpus package within scope — no B-Accept / Gate 2 creep.

**Report format:** PASS / FAIL / SKIP + one line of evidence.  
**GATE** = Ryan process step.

**Status:** **STUB** — fill before live capture. Live R2b **not authorized** until Ryan grant.

---

## Scope lock

| In scope | Out of scope |
|----------|--------------|
| One (or Ryan-named count) real-mode `capture` with approved manifest + sidecar | B-Accept, C0, R3–R7, Gate 2 |
| Artifacts under packet-bound `capture_dir` + required Chroma path | Promotion, cleanup, overwrite without new auth |
| Absolute `restic_gate: PASS` | Hermetic `--authorize-fixture` as a substitute for live grant |

---

## V0 — Safety gate

| ID | Check | PASS |
|----|-------|------|
| V0a | `restic_gate: PASS` | Absolute for live capture |
| V0b | Authorized revision on `main` ancestry | _(fill)_ |

---

## V1 — Grant + packet integrity

| ID | Check | PASS |
|----|-------|------|
| V1a | No `PENDING_AFTER_WRITE` | |
| V1b | Manifest file SHA + three-way body/sidecar digest | |
| V1c | `operations` includes `capture` as authorized (exact list per grant) | |
| V1d | Runtime bindings match argv: `export`, `processed`, `capture_dir`, `chroma_dir` | |

---

## V2 — Pre-state STOP

| ID | Check | PASS |
|----|-------|------|
| V2a | `capture_dir` absent (or Ryan-authorized empty) | STOP if pre-existing without auth |
| V2b | No symlinks under run root | |
| V2c | Resolved paths equal packet paths | |

---

## V3 — Execution evidence

| ID | Check | PASS |
|----|-------|------|
| V3a | Exact argv vector recorded | |
| V3b | Exit status `0` | |
| V3c | stdout reports package SHA / fingerprint fields | |
| V3d | No refusal text | |

---

## V4 — Artifact + inventory

| ID | Check | PASS |
|----|-------|------|
| V4a | Expected capture artifacts present; hashes recorded | |
| V4b | Whole-run inventory matches grant (no extras) | |
| V4c | Live config hash unchanged | |

---

## V5 — Independent sign-off

| ID | Check | PASS |
|----|-------|------|
| V5a | Kiro (or named) written PASS/FAIL naming packet + package hashes + revision | No cleanup by verifier |

---

## Evidence log

```text
VERIFY-r2b-capture — tip <sha> — runner <lane> — <ISO-8601>
STUB — not run
```
