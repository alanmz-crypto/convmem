# ConvMem — Five Priority Arcs

This document is the concise orientation map for ConvMem’s next five major
planning moves. It is the human-readable companion to the formal
dependability/provenance architecture and execution plans.

## 1. CI Merge Gate

Make the full test suite, Pylint, and CodeQL required before ordinary merges.
This is prerequisite infrastructure for the Trust Arc, not a provenance
implementation task.

## 2. Trust Baseline and Evidence Coverage

Define what trustworthy ConvMem means: claims, owners, severity, degraded
states, and measurable reliability expectations. Inventory existing CG-1,
CG-2, backup, restore, projection, and provider evidence before adding tests.
The failure matrix belongs here as a gap-driven method, not as a duplicate test
program.

## 3. Compatibility and Provenance

Make durable formats, schema evolution, acknowledgement boundaries, source
lineage, transformer identity, input binding, and integrity propagation
explicit and testable. T1 and T2 must be complete and accepted before this
arc receives an implementation grant.

## 4. Security, Privacy, and Egress

Define how hostile memory, retrieval poisoning, secrets, cloud synthesis, and
external data transmission are handled. Establish a real local-only hard stop
and explicit rules for any cloud-bound operation.

## 5. Operational Envelope

Set evidence-based limits for endurance, memory, latency, corpus growth,
backlog age, backup age, restore time, and resource behavior under sustained
load. Use soak and scale tests only after the reliability contract identifies
which limits matter.

## Current status

The active planning branch is formalizing this roadmap and its dependencies.
This package is planning-only: it does not implement provenance, alter runtime
behavior, activate CG-2 or Shadow Ledger, migrate live data, or change cloud
policy.

## Discoveries and recommendations

ConvMem already has unusually strong recovery, write safety, verification,
invariants, restore drills, and human authorization. The main professional
project gap is that too much reliability still depends on plans and people
remembering to prove things.

The recommended progression is:

> manual rule → executable rule → automatic gate → human judgment only where required

The five items are one dependency-aware roadmap, not five independent projects:

- CI is enforced independently as prerequisite infrastructure.
- Existing CG-1 and CG-2 proofs are inventoried before new fault tests are written.
- Compatibility/provenance waits for the Trust Baseline and evidence-gap oracle.
- Local-only and egress rules begin early; broader poisoning and privacy defenses remain scoped to Security/Egress.
- Endurance and scale testing follows the reliability contract instead of creating arbitrary gates.
- Governance ceremony is not added where mechanical enforcement is possible.
