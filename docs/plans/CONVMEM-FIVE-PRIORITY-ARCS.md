# Arc Full Fathom Five — Canonical Parent Roadmap

Arc Full Fathom Five is one dependency-aware roadmap, not five parallel
projects. CI is a prerequisite outside the arc; the five arcs are the Trust
Arc itself.

## Canonical hierarchy

| Position | Name | Parent responsibility |
|---|---|---|
| **P0** | **CI Merge Gate** *(outside Full Fathom Five)* | Require full tests, Pylint, and CodeQL before ordinary merges. |
| **FF1 / T1** | **Trust Baseline** | Define trustworthy-state claims, owners, severity, and degraded states. |
| **FF2 / T2** | **Existing Evidence + Failure-Gap Matrix** | Inventory current proof and identify only the missing oracles. |
| **FF3 / T3** | **Compatibility & Provenance** | Preserve truth across durable formats, transformations, recovery, and time. |
| **FF4 / T4** | **Security, Privacy & Egress** | Bound hostile memory, secrets, poisoning, and external transmission. |
| **FF5 / T5** | **Operational Envelope** | Define endurance, scale, resource, performance, and maintenance limits. |

P0 is necessary infrastructure, but it is not FF1 and is not counted among the
five arcs. FF3 may be designed and reviewed early, but it cannot receive a P1,
P2, or P3 implementation grant until FF1/T1 and FF2/T2 are complete and
accepted. The detailed provenance, assertion, and authoritative-store recovery
documents are FF3 child design; they do not redefine FF1, FF2, FF4, or FF5.

## The five contracts

### FF1 / T1 — Trust Baseline

- **Purpose:** Define what ConvMem must preserve and what degraded states mean.
- **Required inputs:** Product trust goals, current durability/recovery claims,
  acknowledgement boundary, threat assumptions, and owner map.
- **Concrete output:** An accepted claim matrix containing property, owner,
  failure consequence, severity, oracle, and declared degraded state.
- **Entry gate:** P0 merge protection is closed; Full Fathom Five does not begin
  on an unclosed CI prerequisite.
- **Exit gate:** Ryan accepts the baseline vocabulary and every catastrophic or
  critical claim has one named oracle and owner.
- **Next dependency:** FF2 uses the matrix as its inventory and gap-analysis
  oracle.
- **Explicit non-goals:** No runtime gate redesign, new chaos suite, provenance
  implementation, cloud-policy change, or arbitrary SLO numbers.
- **Automatic instead of human procedure:** A canonical claim/severity/degraded-
  state contract becomes machine-checkable; humans decide only disputed claims
  and severity.

### FF2 / T2 — Existing Evidence + Failure-Gap Matrix

- **Purpose:** Determine what ConvMem already proves and where proof is absent,
  partial, or stale.
- **Required inputs:** FF1 claim matrix plus CG-1, CG-2, backup, restore,
  projection, provider, and existing test/VERIFY evidence.
- **Concrete output:** One evidence matrix mapping each claim to sufficient,
  partial, or absent proof, with the smallest missing oracle and expected state
  after failure.
- **Entry gate:** FF1 is accepted and its claim/severity vocabulary is frozen.
- **Exit gate:** Ryan accepts the gap list; duplicate checks are rejected, and
  each new check has a distinct failure window, owner, or oracle.
- **Next dependency:** FF3 uses the accepted gaps to define compatibility and
  provenance proof obligations.
- **Explicit non-goals:** No duplicate CG-1/CG-2 suite, broad chaos campaign,
  arbitrary test-count target, or implementation grant.
- **Automatic instead of human procedure:** Evidence coverage and gap status
  become a single reviewable matrix with one authoritative oracle per property;
  humans adjudicate only incomplete or conflicting evidence.

### FF3 / T3 — Compatibility & Provenance

- **Purpose:** Keep durable memory attributable, conservative, and consumable
  across schema evolution, transformation, export, restore, and retrieval.
- **Required inputs:** Accepted FF1 contract; accepted FF2 gap/oracle matrix;
  durable-format inventory; source, transformer, input-binding, and recovery
  requirements.
- **Concrete output:** A reviewed compatibility/provenance contract covering
  acknowledgement, schema versions, migration limits, lineage, integrity
  propagation, assertion identity, and the authoritative provenance-store
  recovery boundary.
- **Entry gate:** FF1/T1 and FF2/T2 outputs are complete and accepted. Kiro may
  review this child architecture earlier, but review approval is not an Execute
  grant.
- **Exit gate:** The FF3 parent design is locked; P1/P2/P3 are separately
  bounded, each with its own VERIFY oracle and later Ryan grant.
- **Next dependency:** FF4 uses the canonical provenance boundary to define
  poisoning, privacy, and egress controls.
- **Explicit non-goals:** No live migration, corpus rewrite, activation, GC,
  ranking change, or automatic trust elevation.
- **Automatic instead of human procedure:** Loaders reject incompatible or
  unknown state, writers bind canonical evidence, and recovery gates verify the
  complete store; humans authorize migrations and disputed lineage.

### FF4 / T4 — Security, Privacy & Egress

- **Purpose:** Prevent hostile content or external processing from violating
  integrity, privacy, or user expectations.
- **Required inputs:** FF1 threat/severity claims, FF2 failure gaps, and FF3
  provenance/egress boundaries.
- **Concrete output:** A threat model and policy contract for memory poisoning,
  secrets/PII, provider use, allowed data classes, and local-only operation.
- **Entry gate:** FF3 parent contract is locked and its boundaries are known.
- **Exit gate:** Egress inventory, local-only hard stop, cloud allowlist, and
  security test oracles are accepted; implementation remains separately granted.
- **Next dependency:** FF5 measures the resource and reliability consequences
  of the accepted security and privacy controls.
- **Explicit non-goals:** No unbounded security backlog, provider expansion,
  broad content moderation system, or policy change by documentation alone.
- **Automatic instead of human procedure:** Local-only mode blocks corpus-bearing
  network requests and allowlists classify cloud operations; humans decide only
  exceptions and ambiguous data classification.

### FF5 / T5 — Operational Envelope

- **Purpose:** Prove the accepted trust contracts continue to hold over time,
  at scale, and under resource pressure.
- **Required inputs:** FF1 claims, FF2 oracles, FF3 continuity guarantees,
  FF4 security controls, and measured workload characteristics.
- **Concrete output:** Evidence-based RPO/RTO/SLO, latency, backlog, memory,
  corpus-growth, backup-age, restore, soak, and maintenance budgets.
- **Entry gate:** FF1–FF4 contracts and their owners are accepted; no budget is
  invented merely because a metric is easy to measure.
- **Exit gate:** Endurance/scale evidence meets the declared envelope and each
  breach has an observable degraded state, owner, and response.
- **Next dependency:** The accepted envelope becomes the maintenance and release
  baseline; it does not authorize unrelated feature work.
- **Explicit non-goals:** No premature 10x campaign, arbitrary performance
  target, optimization project, or operational activation without a grant.
- **Automatic instead of human procedure:** Soak, resource, freshness, backup,
  and restore budgets gate or warn mechanically; humans judge exceptions and
  change the contract deliberately.

## Why this order and what may start early

The order follows the dependency of each oracle: define trust, inventory proof,
formalize durable continuity, bound hostile/external influence, then measure
sustained operation. Only review and design work may precede its parent gate.
No implementation grant, live migration, activation, GC, cloud-policy change,
or operational campaign may start early merely because its architecture is
interesting or has already been reviewed.

## Completion equation

```text
FULL_FATHOM_FIVE_DONE =
  P0_CI_CLOSED
  ∧ ACCEPTED(FF1)
  ∧ ACCEPTED(FF2)
  ∧ ACCEPTED(FF3)
  ∧ ACCEPTED(FF4)
  ∧ ACCEPTED(FF5)
  ∧ EACH_ARC_HAS_EVIDENCE_OWNER_ORACLE_AND_EXIT_STATE
  ∧ NO_PROHIBITED_EARLY_OPERATION
  ∧ RYAN_PARENT_LOCK
```

`ACCEPTED(FFn)` means the arc’s concrete output, entry/exit evidence, owner,
oracle, non-goals, and degraded-state behavior are recorded at one exact
revision. A later implementation or migration grant is never implied by this
parent equation.

## Governing rule and freeze boundary

> manual rule → executable rule → automatic gate → human only for judgment

Existing checks and review artifacts are reused. A new permanent checklist,
review, handoff, or gate is justified only by a distinct failure window, oracle,
or authorization decision. New trapdoors found during Kiro or Copilot review
are bounded findings against this frozen parent structure; they do not
automatically add scope or move the review SHA.

**Full Fathom Five parent structure frozen; further findings are review findings,
not automatic scope additions.**

This is planning-only. It authorizes no runtime code, live-data mutation,
migration, activation, GC, or cloud-policy change.
