# Review Handoff: CG-2 D1 integrated closure (D1R0–D1R12)

**Date:** 2026-08-30  
**Author:** Cursor (evidence executor)  
**For:** Kiro (independent review — non-implementing)  
**Authorization:** Ryan, 2026-08-30 (integrated D1 closure evidence run + prior per-row Kiro PASSes on D1R1, D1R9, D1R12)

**Arc:** CG-2 Design A → D1 reference-v2 corrective → integrated D1 closure

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `CLOSED` (global D1 ledger written, Ryan-delegated) |
| **Branch** | `fix/2026-08-30-cg2-d1r0-d1r11-closure-evidence` |
| **Integrated review tip** | `9cfb085836ca92c308d1a8f966aced9bbb48546e` |
| **Branch docs tip** | `2b16ead3095cfe5d6e281a1722496882603e592e` (docs-only after `9cfb085`) |
| **Push status** | pushed to origin (branch); handoff commit pending this file |
| **PR** | not opened |
| **Ryan GATE** | Kiro integrated PASS → Ryan may authorize ledger global D1 closure write (separate lane); **does not** authorize production D1, V8c, cutover, or activation |
| **Review seed** | **Fresh/different seed required** (continuity seed used by Cursor evidence run) |

---

## What to review

Perform **one integrated independent review** of D1 reference-v2 corrective evidence at exact implementation/model tip **`9cfb085836ca92c308d1a8f966aced9bbb48546e`**, covering **D1R0 through D1R12 together**.

**Why this exists:** VERIFY states D1R rows may be marked PASS only **together at one exact tip** after independent review. Cursor assembled integrated evidence at `9cfb085`; partial ledger PASS rows (D1R1, D1R9, D1R12) were recorded at earlier review contexts and must be re-bound or confirmed at this tip before global D1 closure.

**Your role:** Read-only review and PASS/FAIL verdict per row + integrated verdict. **Do not implement, commit, or mutate production.**

---

## Exact tip and identity (D1R0)

| Field | SHA / value |
|-------|-------------|
| **Integrated review tip (use this)** | `9cfb085836ca92c308d1a8f966aced9bbb48546e` |
| **Do not use as final tip** | `8897d1358f985e38a1070816189460d980824d75` (runtime PASS base only) |
| Accepted planning identity | `8b5b53e2a460753711392379535b127cefa244b8` (ancestor of tip) |
| Formal corrective | `7a8fd76350b7076f5d75e3ad53c7392647b2eac0` (ancestor of tip) |
| Commits after tip on branch | `d9f1c8b`, `2b16ead` — **docs-only** (VERIFY/LATEST partial row closure) |

Checkout:

```bash
cd ~/Projects/convmem
git fetch origin
git checkout 9cfb085836ca92c308d1a8f966aced9bbb48546e
```

Runtime delta `8897d135…` → `9cfb085…` (non-docs):

- `cg2_property_map.py`
- `cg2_retained_reference.py`
- `file_generation_contract.py`
- `file_generation_pointer.py`
- `tests/test_cg2_reference_v2.py`
- `docs/plans/formal/cg2/*` (formal model + TLC configs)

---

## Ledger state before integrated review

Authoritative table: [`docs/plans/VERIFY-cg2-production-activation.md`](../plans/VERIFY-cg2-production-activation.md) § D1 reference-v2 corrective gate.

| Row | Current ledger | Notes |
|-----|------------------|-------|
| D1R0 | PENDING | Identity review at `9cfb085` |
| D1R1 | SATISFIED / PASS | Prior Kiro PASS at `8897d135`; re-bind required at `9cfb085` |
| D1R2 | PENDING | Hermetic tests at tip |
| D1R3 | PENDING | Hermetic tests at tip |
| D1R4 | PENDING | Hermetic tests at tip |
| D1R5 | PENDING | Hermetic tests at tip |
| D1R6 | PENDING | Hermetic tests at tip |
| D1R7 | PENDING | Hermetic tests at tip |
| D1R8 | PENDING | Hermetic tests at tip |
| D1R9 | SATISFIED / PASS | Prior Kiro PASS; re-bind at `9cfb085` restored reader |
| D1R10 | PENDING | Hermetic tests at tip |
| D1R11 | PENDING | Hermetic + regression at tip |
| D1R12 | SATISFIED / PASS | Prior Kiro PASS at `7a8fd763`; confirm still applicable at `9cfb085` |

**Global D1 closure:** not declared. Ten rows still PENDING in ledger until integrated review.

---

## Cursor evidence packet (starting points)

| Artifact | Path |
|----------|------|
| Integrated manifest | `/tmp/d1-integrated-evidence-20260830/integrated_d1_evidence_manifest.json` |
| Reference-v2 pytest log | `/tmp/d1-integrated-evidence-20260830/d1-integrated-refv2-tests.log` |
| D1R9 drill evidence | `/tmp/d1r9-ra-drill-20260830/evidence/` |
| D1R9 restored state | `/tmp/d1r9-ra-drill-20260830/restore_target/` |
| D1R9 restic repo | `/tmp/d1r9-ra-drill-20260830/restic-repo/` |
| VERIFY ledger | `docs/plans/VERIFY-cg2-production-activation.md` |
| Architecture | `docs/plans/ARCHITECTURE-cg2-production-activation.md` |
| Execution | `docs/plans/EXECUTION-cg2-design-a.md` |

Cursor reported all rows **`EVIDENCE_READY`** at `9cfb085`. Kiro must independently verify or FAIL.

---

## Review procedure by row

### D1R0 — Identity

Confirm planning SHA, tip SHA, formal corrective ancestry, and no unreviewed runtime commits after `9cfb085`.

### D1R2 — Protocol identity

At tip, confirm:

- `convmem/cg2-rollback-baseline-reference-v2`
- `RETAINED_LEGACY_REFERENCE_V2` / `convmem/retained-legacy-reference-manifest-v2`
- `LEGACY_EXACT_VECTOR_UNKNOWN_MODEL_V1` unchanged
- Deterministic reference-v2 target ID

Primary test: `tests/test_cg2_reference_v2.py::test_deterministic_reference_v2_target_id`

### D1R3–D1R7 — Hermetic oracles

Run at tip:

```bash
pytest tests/test_cg2_reference_v2.py -v
```

| Row | Primary tests |
|-----|----------------|
| D1R3 | `test_adversarial_{duplicate,additional,wrong_owner,missing,substituted}_physical_id_refuses` |
| D1R4 | `test_adversarial_one_ulp_vector_drift_refuses` |
| D1R5 | `test_same_reader_spy_qualification_and_serving`, `test_reference_v2_first_cutover_rollback_same_reader_rehearsal` |
| D1R6 | `test_zero_copied_vector_rows`, `test_reference_v2_static_inventory_no_sidecar_or_copied_vector_authority`, `test_reference_v2_lookup_spy_no_sidecar_or_generation_get_rows` |
| D1R7 | `test_reference_v2_fresh_process_failure_refuses_retained_evidence` |

Cursor result: **20/20 PASS** in 13.22s.

### D1R1 — Re-bind at final tip (production read-only)

Repeat structurally read-only consume-unchanged check using code at `9cfb085`:

- `ChromaStore(create_collections=False, require_writer_boundary=False)`
- `load_ratified_d0_chain`, `_reread_rows_for_d0_chain`, root reproduction
- **No** production retain, write, pointer, fence, or GC

Frozen production authority (unchanged across prior reviews):

| Binding | Value |
|---------|-------|
| Candidate | `d4be814abc59e77a2d1420b6d7db8859f5a5fe6f449f107fbdd23eb9aecaa0be` |
| Validation | `4af9388454e80dedeb6988500647d2766333e22d4e5fecacadf055d14b667793` |
| Ratification | `ryan-d0-webui-2026-08-29` |
| Snapshot root | `8ee62dfd434e092b6c9d5367dbd53fa9e4402078dfa30aad2277f417ce1ebd49` |
| Vector root | `28df88466daaf16c270b1112d2a160fecc9d47c1014bc5bf91e94ae70e83a24e` |
| Query context | `df95af20d1774bb225d77fe2408450ee69ff3e7a9fee383ffa79e72febb370be` |
| Owner | `6daf07d443fbd1c4559f4c6516d7f1f585db25106f1aca3437b2ca7ecf0e39b3` |
| Row count | 37 LEGACY |

Cursor re-bind at `9cfb085`: **all checks PASS**.

### D1R9 — Re-bind at final tip (restored reader)

Use preserved drill (new backup **not** required unless restore missing):

- Restic snapshot: `7d9ea1465c129e778ce4787008ac06820bf6f9abc28fd76a9f47fcdd55d2d0e1`
- Target: `2740ec5b5f01f2f293d07bbf0677c4e26f8daadefab8192682410e6685af2364`
- Manifest SHA-256: `8ca18854215d6c100aa11ca686f88b590609bfcac7f21dec44fcbc9f70b8ab0c`

**Drill caveat (verify, do not dismiss):** Production lacked retained reference-v2 at drill time; complete target was materialized on **isolated scratch only** via `retain_reference_v2_rollback_baseline`. Production was not cut over.

Exercise restored reader with **`9cfb085` code**; confirm exact roots, 37 rows, recovery eligibility, membership, cold validation, path isolation.

Cursor re-bind at `9cfb085`: **all checks PASS**.

### D1R8 — Lifecycle

After R1–R7 and R9 clean: `test_retention_lifecycle_uses_retained_rollback_baseline_only` — no `G_RB_CONVERT_COLD_VALIDATED`, no `abandoned_d1`.

### D1R10 — Failed convert-v1 terminal

- `FAILED_CONVERT_V1_TARGET_ID` = `2d01dfca08ac388e7ac74d145e789a8a35d8b97c4bf2ee6d971a95a8a74c4b3c`
- Tests: `test_failed_convert_v1_target_id_refuses`, `test_reference_v2_id_differs_from_convert_v1`

### D1R11 — D0 exception contract

```bash
pytest tests/test_cg2_reference_v2.py::test_malformed_embedding_raises_d0_attestation_error \
       tests/test_cg2_legacy_vector_attestation.py::test_vector_float32_encoding_and_nonfinite_refusal \
       tests/test_cg2_rollback_baseline.py -q
```

Cursor result: **50/50 PASS**.

### D1R12 — Formal (do not redo unless needed)

Prior Kiro PASS at `7a8fd76350b7076f5d75e3ad53c7392647b2eac0`. Confirm:

- Formal corrective is ancestor of `9cfb085`
- `convmem/cg2-design-a-property-map-v3` at tip
- TLC configs present under `docs/plans/formal/cg2/`
- **Residual caveat unchanged:** jar SHA-attestation wrapper (`run-d1r12-tlc.sh`) separate/unattested control

---

## What NOT to do

- Do not activate production D1, retain reference-v2 into production, or cut over
- Do not mutate live pointers, fences, GC, or failed convert-v1 state
- Do not reratify D0 or perform V8c
- Do not implement code fixes (report FAIL and hand back to Cursor/Ryan)
- Do not self-merge or update VERIFY ledger (Ryan/Cursor ledger lane after your PASS)

---

## Acceptance criteria (Kiro output)

- [ ] Independent review at exact tip `9cfb085836ca92c308d1a8f966aced9bbb48546e` (fresh seed)
- [ ] Per-row PASS or FAIL for D1R0–D1R12 with evidence citations
- [ ] Integrated verdict: all rows PASS together, or named blocking row(s)
- [ ] D1R1 production read-only re-bind confirmed or FAIL with specifics
- [ ] D1R9 restored-reader re-bind confirmed or FAIL (including scratch-materialization caveat adjudication)
- [ ] Explicit statement: global D1 closure authorized or not (ledger write is separate Ryan/Cursor step)

---

## Merge reading

- [`VERIFY-cg2-production-activation.md`](../plans/VERIFY-cg2-production-activation.md)
- [`ARCHITECTURE-cg2-production-activation.md`](../plans/ARCHITECTURE-cg2-production-activation.md)
- [`EXECUTION-cg2-design-a.md`](../plans/EXECUTION-cg2-design-a.md)
- [`RUNBOOK-cg2-production-activation.md`](../plans/RUNBOOK-cg2-production-activation.md)
- [`docs/plans/formal/cg2/`](../plans/formal/cg2/)

---

## Related files

| What | Path |
|------|------|
| Reference-v2 tests | `tests/test_cg2_reference_v2.py` |
| Rollback baseline | `cg2_rollback_baseline.py` |
| Retained reference reader | `cg2_retained_reference.py` |
| Property map v3 | `cg2_property_map.py` |
| Formal model | `docs/plans/formal/cg2/CG2Authority.tla` |

---

## Leaving / picking up checklist

**Cursor (done):**

- [x] Integrated evidence run at `9cfb085`
- [x] This handoff file
- [ ] `LATEST.md` bullet (same commit)
- [ ] Branch pushed

**Kiro (pickup):**

- [ ] Read this file before review
- [ ] `git checkout 9cfb085836ca92c308d1a8f966aced9bbb48546e`
- [ ] Fresh seed; rerun critical checks independently
- [ ] Return integrated PASS/FAIL packet to Ryan
