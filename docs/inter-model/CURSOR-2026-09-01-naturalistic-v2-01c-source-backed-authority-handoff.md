# Cursor Handoff — V2-01C Source-Backed Authority Corrective (COMPLETE — REVIEW REQUIRED)

**Date:** 2026-09-01  
**Author:** Cursor  
**For:** Independent authority reviewer (Luna new seed preferred, or Kiro)  
**Arc:** Naturalistic ConvMem product-value evaluation  
**Authorization:** Ryan V2-01C grant `154f8dc054035758581fd397679a31e731fa50da` (remains in force)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `READY_FOR_REVIEW` — **STOP; do not start V2-02C** |
| **Parent SHA** | `632b0eff4e7fde5e0adb9fe8688980487ce69036` |
| **Branch** | `fix/2026-09-01-naturalistic-v2-01c-source-backed-authority` |
| **Tip SHA** | `ed971aea6c02b1799652ace4fb899d5ddd441318` |
| **Push status** | pushed to origin |
| **PR** | not opened (Ryan-owned) |
| **Ryan GATE** | Independent exact-tip authority review PASS before any V2-02C grant |
| **Locked V2** | `9f4791c2744c02d742fdb9c0fa1e9dd150591ac1` — untouched |

---

## Review question (exact)

> Can a malicious or mistaken caller still obtain P1 occurrence/evidence authority merely by supplying self-consistent identity, parent, lineage, digest, seal or attestation claims?

**PASS requires:** no.

---

## What changed

Second V2-01C corrective replacing assertion-based issuance with:

1. **Sealed source capture** (`source_authority.py`) — occurrence identity derived from verified capture bytes, not caller strings.
2. **Registered issuance** (`IssuanceAuthorityRepository`) — P1 verification resolves `occurrence_issuance_digest` against issuer-registered records; token-only construction cannot seal.
3. **Independent P0 parent** (`p0_construct.py`) — construct-freeze manifest resolved from authority repository; digest-consistency alone insufficient.
4. **Lineage attestation artifacts** (`lineage_attestation.py`) — `issuer_attested=true` requires registered sealed attestation artifact.
5. **Issuer implementation revision** — behavior-relevant module closure includes `canonical_json.py`; mismatch rejected at verify.

Preserved from `632b0ef`: canonical bytes, content/artifact-ID recomputation, strict parsing, sealed wrapper, adversarial integrity tests (extended).

---

## Test evidence

```bash
cd /path/to/convmem  # branch fix/2026-09-01-naturalistic-v2-01c-source-backed-authority @ ed971ae
python -m pytest tests/test_naturalistic_v2_*.py -q          # 80 passed
python -m pytest tests/test_naturalistic_*.py -q               # 189 passed (+ subtests)
git diff --check 632b0ef..ed971ae                              # clean
```

Adversarial suite: `tests/test_naturalistic_v2_p1_source_backed_authority.py` (20 negative + 6 positive per handoff).

---

## Scope firewall confirmation

**Not implemented:** V2-02C, V2-03C, V2-04/P3, V2-05, V2-06 transitive DAG, G6/T0, Agent A/B, scoring, product inference. Locked V2 JSON unchanged.

---

## See my work

```bash
git fetch origin && git log --oneline 632b0ef..ed971aea6c02b1799652ace4fb899d5ddd441318
git diff 632b0ef..ed971aea6c02b1799652ace4fb899d5ddd441318
```
