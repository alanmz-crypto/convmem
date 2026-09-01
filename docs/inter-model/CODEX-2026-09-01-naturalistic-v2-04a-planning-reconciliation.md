# [Arc Naturalistic ConvMem product-value evaluation] V2-04A planning-authority reconciliation

**Date:** 2026-09-01
**Author:** Luna
**Status:** `PLANNING TIP ONLY — V2-04A GRANT READY FOR RYAN DECISION`

## Purpose

This is a narrow routing reconciliation for the existing PRE-G6
implementation plan. It does not rewrite the historical plan, amend the V3
canonical JSON, redesign the execution sequence, or authorize implementation.
It exists so future V2-04A and V2-05 work cannot accidentally treat historical
V2 as the current semantic authority or confuse semantic ancestry with Git
implementation ancestry.

## Authority ledger

| Role | Exact authority | Meaning after this reconciliation |
|---|---|---|
| Accepted semantic authority | `naturalistic-pre-g6-contract-v3` at `d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7`; RFC 8785/JCS digest `f5cc62a3881bc06ddb0d0f1bc3b68d8c3e2cb29b5abda9675e32c84eea04d2a4`; 48,268 canonical bytes | Ryan-accepted successor PRE-G6 semantic authority for future bounded work |
| Historical semantic authority | `naturalistic-pre-g6-contract-v2` at `9f4791c2744c02d742fdb9c0fa1e9dd150591ac1`; digest `917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e` | Immutable historical V2 record; superseded semantically for future PRE-G6 work, never rewritten |
| Existing implementation-plan authority | `1a72a761b2cca3d9f955ad09d7b8b265d1fcaa9c`, `docs/plans/EXECUTION-naturalistic-pre-g6-v2-implementation.md` | Historical planning lineage; this file supplements its routing and does not rewrite that commit |
| Existing V2-04 implementation parent | `872390db8ac76157b3a0223d947a8eb5da66473c` | Required Git implementation parent for any later V2-04A grant; independently passed V2-04 blindness/noninterference boundary remains closed |

The accepted V3 semantic authority and the V2-04 implementation parent are
different authority dimensions. V3 is the semantic input; `872390db…` is the
required implementation Git parent. Neither is substituted for the other.

## Reconciled future routing

### V2-04A

If Ryan grants the bounded packet
[`CURSOR-2026-09-01-naturalistic-v2-04a-implementation-grant.md`](CURSOR-2026-09-01-naturalistic-v2-04a-implementation-grant.md), Cursor must:

- start from implementation parent `872390db8ac76157b3a0223d947a8eb5da66473c`;
- bind the implementation to accepted V3 commit
  `d5b03a6c8c53cfebbb7239ea4fb3ac31721e1ad7` and digest
  `f5cc62a3881bc06ddb0d0f1bc3b68d8c3e2cb29b5abda9675e32c84eea04d2a4`;
- extend only the V2-04 sealed P1/P3 semantic closure needed by later work;
- preserve the existing P2-after-closure firewall and V2-04 blindness boundary;
- not implement a registry, multiplicity estimator, T9/T10 behavior, or any
  live/naturalistic path.

### V2-05

V2-05 remains unimplemented and ungranted. Any later V2-05 plan or grant must
name the same accepted V3 commit/digest, cite the V2-04A implementation
lineage and exact-tip independent review, and identify V2 only as immutable
historical context. V2-05 may not infer semantic target state from the old
`CandidateClosureV2` digest-only interface or from absence of recovered
candidates.

## Result

The minimum reconciliation is complete: accepted V3 is the sole semantic SSoT
for future PRE-G6 bounded implementation, historical V2 remains immutable,
`1a72a761…` remains the existing implementation-plan authority, and
`872390db…` remains the exact implementation parent for V2-04A. No semantic
redesign, canonical-artifact edit, runtime implementation, or downstream grant
is included.

## Hard stops

- Do not modify `docs/plans/artifacts/naturalistic-pre-g6-contract-v3.json` or
  its sidecar. A canonical-byte change would invalidate the accepted digest and
  must stop for Ryan's decision.
- Do not rewrite or amend the historical V2 artifact or the `1a72a761…` plan
  commit.
- Do not implement V2-04A, V2-05, V2-06, G6/T0, evidence capture, Agent A/B,
  scoring, or product inference from this reconciliation.
- Stop if V2-04A requires changing accepted V3 semantics, reopening the blinded
  interface, or making P2 participate in semantic candidate closure.

**TL;DR:** Accepted V3 now governs future PRE-G6 semantic routing; historical
V2 and the `1a72a761…` plan remain immutable lineage, while `872390db…` is the
required V2-04A implementation parent. This is a narrow planning tip, not an
implementation or grant.
