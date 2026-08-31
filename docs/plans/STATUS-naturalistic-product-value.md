# Arc Brief — Naturalistic ConvMem Product-Value Evaluation

> **Every model working on this arc must read this file at session start.**
> After reading, state: "Goal: [one sentence]. My role: [what I'm here to do].
> The system currently: [what exists]. Missing: [what doesn't exist yet]."

**Arc:** Naturalistic ConvMem product-value evaluation

**Current state:** G1–G5 methodology machinery is on `main` (PR #255, PR #259).
PRE-G6 Contract V2 is **architecture-locked** at commit
`9f4791c2744c02d742fdb9c0fa1e9dd150591ac1` (canonical digest
`917ad129a4f9641f65b809e143467b1f2c48ea41203166365b8e3efd459b627e`, 47,330
JCS bytes) on branch
`fix/2026-08-31-naturalistic-pre-g6-v2-firewall-corrective`. Classification
remains **methodology validation, not product evidence**. **G6 and T0 are not
authorized.** Implementation remains unauthorized; bounded implementation planning
and independent verification must precede any separate Ryan reconsideration of
G6/T0.

---

## 1. What This Is For (product goal)

This arc asks whether ConvMem creates measurable product value during ordinary
work: compared with the same fresh agent without ConvMem, does ConvMem improve
meaningful recovery and continuation when evaluated prospectively, symmetrically,
and with sealed evidence?

**Done means:** a later, separately authorized prospective study can produce an
auditable co-primary report and an allowed product disposition. A methodology
merge, dry-run, architecture lock, or partial result is not a product conclusion.

## 2. System Design (how the pieces connect)

```
Ryan-frozen construct (P0)
            │
            ▼
P1 evidence seal → P2 opaque resolution → P3 blinded registry seal
            │
            ▼
T3 sample seal → T4 probe/key seal → T5 C1 snapshot/diagnosis
            │
            ▼
T6 C0/C1 readiness → T7 execution → T8 scoring → T9 aggregation → T10 gate
            │
            ▼
           later allowed product disposition (T10 only)
```

**Canonical authority:** [`naturalistic-pre-g6-contract-v2.json`](artifacts/naturalistic-pre-g6-contract-v2.json)
at locked digest `917ad129…`. Architecture and execution prose are explanatory
projections only.

Key invariants (compatible with locked V2):

- every episode remains in the opportunity denominator;
- target count cannot weight an episode more than once in paired analysis;
- adjudicators see `AdjudicationEvidenceViewV1`, not P2 resolver internals;
- P1/P2 firewall denies canonical `resolver_result` and `capability_vector`
  from P1 material and adjudicator-visible surfaces;
- Issue #263: source present but verbatim unavailable must never collapse into
  source absent;
- malformed, duplicate, orphaned, sparse, and non-evaluable inputs fail closed;
- G4/T10 ceiling: no product conclusion from G1–G5 machinery or synthetic fixtures.

## 3. What Exists Right Now (file map)

| Surface | State |
|---|---|
| [`naturalistic-pre-g6-contract-v2.json`](artifacts/naturalistic-pre-g6-contract-v2.json) | **Architecture-locked** @ `9f4791c` / digest `917ad129…` (branch-only until merge) |
| [`ARCHITECTURE-naturalistic-product-value.md`](ARCHITECTURE-naturalistic-product-value.md) | Explanatory projection reconciled to V2 (this branch) |
| [`EXECUTION-naturalistic-product-value.md`](EXECUTION-naturalistic-product-value.md) | Explanatory execution projection reconciled to V2 (this branch) |
| `eval_naturalistic/*` on `main` | G1–G5 methodology substrate + synthetic dry-run; **does not satisfy V2 runtime obligations** |
| PRE-G6 V2 runtime (P1 identity, P2 resolver, manifests listed in §5) | **Not implemented or not verified** |
| Live runner, study controller, Agent A/B, corpus access | Absent and unauthorized |

## 4. Completion State

| Gate | State | Evidence / next authority |
|---|---|---|
| G1–G4 methodology | **DONE on `main`** | PR #255 |
| G5 synthetic dry-run | **DONE on `main`** | PR #259; Kiro PASS @ `23b24959`; not product evidence |
| PRE-G6 Contract V2 architecture | **LOCKED** (Ryan, 2026-08-31) | `9f4791c` / digest `917ad129…`; Luna EXACT-BYTE PASS |
| G6 planning reconciliation to V2 | **IN PROGRESS** (this branch) | Docs-only; awaiting independent review |
| Bounded implementation plan | **NOT STARTED** | Requires planning-doc review + Ryan grant |
| G6/T0 prospective freeze | **NOT AUTHORIZED** | Separate Ryan grant after implementation verification |
| Product disposition | **UNAVAILABLE** | T10 only, after full authorized path |

## 5. Your Role (read this to know what you're here to do)

If Ryan sent you for **G6/T0/live study**, stop — not authorized.

If Ryan sent you for **implementation**, stop unless a bounded grant names exact
scope. Architecture lock ≠ implementation authorization.

If Ryan sent you for **planning reconciliation or review**, read locked V2 JSON
first, then reconciled ARCHITECTURE/EXECUTION/STATUS. Do not treat prose as
authority over the canonical contract.

**Not yet implemented or verified** (forward obligations — architecture lock
does not prove runtime conformance):

- richer P1 evidence identity and envelope commitments;
- P2 opaque resolver and P1/P2 canonical-field firewall;
- capability vector semantics;
- unknown target multiplicity bounds;
- transitive provenance firewall;
- scorer/runtime implementation binding;
- `ControllerEvidencePackageV2`, `C0C1EqualityManifestV2`,
  `SessionIsolationManifestV2`, `ConditionOrderManifestV2`;
- informative-missingness checks.

## 6. What Remains Before "Live"

- [x] Land G1–G5 on `main`.
- [x] PRE-G6 Contract V2 architecture lock (Ryan @ `9f4791c`).
- [ ] G6 planning docs reconciled to locked V2 (this branch).
- [ ] Independent planning-doc review.
- [ ] Bounded implementation plan/grant → Ryan approval.
- [ ] Independent implementation verification against locked V2.
- [ ] Ryan separate G6/T0 grant (if warranted).
- [ ] Only authorized T10 path may produce product disposition.

## 7. Hard Stops (models cannot cross)

| Stop | Owner / invariant | What it blocks |
|---|---|---|
| Canonical JSON authority | Locked V2 @ `917ad129…` | Prose overrides; canonical byte edits without amendment |
| Architecture lock ≠ implement | `implementation_authorized: false` | Runtime code, live study |
| G6/T0 grant | Ryan after implementation verification | Prospective freeze, Agent A/B, natural evidence |
| Adjudicator firewall | V2 role access | P2 internals, `resolver_result`, `capability_vector` in adjudication |
| Issue #263 invariant | V2 provenance root | Collapsing verbatim-unavailable into source-absent |
| G4/T10 ceiling | Analysis contract | Product conclusion from machinery or synthetic fixtures |
| Corpus/live boundary | Arc execution plan | Corpus access or ordinary-work campaign from this lane |

## 8. Relationship to ConvMem (the bigger picture)

Evaluation arc — not a serving-path change. Separately governed from JudgeBench,
R2b, Shadow, Recovery Authority.

## 9. Key Design Files (for deep dives)

| Purpose | Path |
|---|---|
| **Canonical architecture (SSoT)** | [`artifacts/naturalistic-pre-g6-contract-v2.json`](artifacts/naturalistic-pre-g6-contract-v2.json) @ `9f4791c` |
| Explanatory architecture projection | [`ARCHITECTURE-naturalistic-product-value.md`](ARCHITECTURE-naturalistic-product-value.md) |
| Explanatory execution projection | [`EXECUTION-naturalistic-product-value.md`](EXECUTION-naturalistic-product-value.md) |
| Cross-arc routing | [`../inter-model/LATEST.md`](../inter-model/LATEST.md) |

## 10. How to Update This Brief (departure protocol)

Snapshot only — one Update Log line per milestone. Session narrative → Track A.

### Update Log

- 2026-08-30 — G1–G5 landed on `main`; G6 Ryan-gated pending review (superseded).
- 2026-08-31 — PRE-G6 V2 architecture locked @ `9f4791c` / digest `917ad129…`; Luna EXACT-BYTE PASS; G6 planning reconciliation to V2 in progress; G6/T0 remain unauthorized.

**TL;DR:** G1–G5 on `main`. PRE-G6 V2 locked @ `9f4791c`. Planning docs reconciling to V2. Implementation unauthorized. G6/T0 require separate Ryan grant after implementation verification.
