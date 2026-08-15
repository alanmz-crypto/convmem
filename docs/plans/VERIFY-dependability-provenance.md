# Verify Plan — Dependability and Provenance Trust Arc

```text
Planning Status
Phase:        Verify (planning package; no Execute evidence yet)
Characters:   Independent Reviewer
Functions:    Review scope, claim matrix, evidence map, and later Execute proof
Lanes:        Codex planning; Kiro sign-off; Ryan GATE
Authority:    Planning artifact only — not implementation PASS
```

**Subject / tip:** planning branch tip; record exact SHA at review time

**ARCHITECTURE / EXECUTION:**
[`ARCHITECTURE-dependability-provenance.md`](ARCHITECTURE-dependability-provenance.md) /
[`EXECUTION-dependability-provenance.md`](EXECUTION-dependability-provenance.md)

**Goal:** Prove that eventual implementation closes classified trust-claim gaps
without duplicating CG-1/CG-2 or crossing separate operational boundaries.

## Human consequence

This planning VERIFY does not authorize implementation or production action. A
future filled VERIFY must show which baseline claims are proven, partial, or
intentionally advisory before Ryan can accept closure.

| | |
|---|---|
| **Who** | Codex authors; Kiro independently reviews; Ryan locks and gates. |
| **What** | Claim-to-evidence and gap-driven execution framework. |
| **When** | Before any dependability/provenance Execute grant. |
| **Why** | Existing mechanisms are strong but their combined envelope is not one explicit contract. |
| **How** | Severity-ranked claims, existing-proof inventory, degraded states, exact-revision evidence. |

**TL;DR:** Planning is ready for architecture review; no Execute evidence is
claimed.

## Scope lock

| In scope | Out of scope |
|---|---|
| Claims, severity, egress/local-only, proof inventory, and gap matrix | Runtime implementation under this planning branch |
| Mapping CG-1/CG-2, backup, restore, doctor, and provider evidence | CG-2 soak, owner activation, GC, Shadow activation, live capture |
| Compatibility, security, fault, and operational phase boundaries | Live migration, corpus mutation, cloud-policy changes |

## Verification design for eventual Execute

| Field | Planned answer |
|---|---|
| Independent oracle | Authoritative ledger/source/manifest state plus deterministic fixtures and restore/replay comparisons |
| Failure-injection method | Process kill, corruption/truncation, storage fault, provider fault, source drift, and network-deny fixtures admitted by T2 |
| Negative control | Bypassed authority, stale/corrupt pointer, unauthorized egress transport, or missing migration version must fail |
| Dual-path coverage | Production mutators, serving authority, backup/restore, and cloud-capable operations |

## V0 — Planning preconditions

| ID | Check | Result |
|---|---|---|
| V0a | Branch is based on current `origin/main` and separate from CG-2 | PASS when reviewed |
| V0b | Architecture, execution, status, and VERIFY files exist | PASS when reviewed |
| V0c | CI is explicitly outside the Trust Arc | PASS in planning package |
| V0d | T1 includes egress inventory, local-only, and severity | PASS in planning package |
| V0e | T2 requires proof inventory before new tests | PASS in planning package |
| V0f | No implementation or operational grant is implied | PASS in scope locks |

## V1 — Trust Baseline review

| ID | Check | Result |
|---|---|---|
| V1a | Every claim has authority, failure, evidence, degraded state, consequence, gate, and owner | Pending architecture review |
| V1b | Critical claims have deterministic measurements | Pending architecture review |
| V1c | Thresholds state the bad outcome they prevent | Pending architecture review |
| V1d | Local-only means no corpus-bearing network request is possible | Pending design/implementation |

## V2 — Existing-proof inventory

| ID | Check | Result |
|---|---|---|
| V2a | CG-1 durability/cold-validation evidence is mapped | Pending T2 |
| V2b | CG-2 authority/reconciliation/rollback/mixed-mode evidence is mapped | Pending T2 |
| V2c | Backup/restore/doctor/provider evidence is mapped | Pending T2 |
| V2d | Each claim is sufficient, partial, or absent | Pending T2 |
| V2e | New tests are admitted only for partial/absent claims | Pending T2 |

## V3 — Compatibility and provenance

| ID | Check | Result |
|---|---|---|
| V3a | Durable formats and owners are enumerated | Pending T3 |
| V3b | Migration, future rejection, backup, rollback, and old fixtures are specified | Pending T3 |
| V3c | Embedding identity and unknown behavior are explicit | Pending T3 |

## V4 — Security boundary

| ID | Check | Result |
|---|---|---|
| V4a | Corpus-bearing egress operations and payload classes are inventoried | Pending T1/T4 |
| V4b | Retrieved content cannot acquire instruction authority | Pending T4 |
| V4c | Write → Store → Retrieve → Execute → Share → Forget tests are scoped | Pending T4 |
| V4d | Activation/cloud grants remain separate | Pending T4 |

## V5 — Operational envelope

| ID | Check | Result |
|---|---|---|
| V5a | RSS, latency, backlog, restore, and provider measurements have one owner | Pending T5 |
| V5b | 24/72-hour soak scope and stop conditions are defined | Pending T5 |
| V5c | Maintenance/security checks do not duplicate gates | Pending T5 |

## V6 — Independent sign-off and Ryan GATE

| ID | Check | Result |
|---|---|---|
| V6a | Independent review names exact planning/implementation tip | Pending |
| V6b | Residual risks include consequence, owner, and disposition | Pending |
| V6c | Ryan locks architecture or returns the package | Pending Ryan GATE |

## Evidence log

```text
VERIFY-dependability-provenance — planning package on
plan/2026-08-15-dependability-provenance — 2026-08-15
Planning result: ready for architecture review; no Execute evidence claimed
```
