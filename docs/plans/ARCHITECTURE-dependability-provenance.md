# Architecture Direction — Dependability and Provenance Trust Arc

```text
Planning Status
Phase:        Architecture Planning
Characters:   Contract Designer, Assurance-Case Designer, Scope Guardian
Functions:    Codex authors; Kiro reviews; Ryan locks architecture
Authority:    Planning only — implementation and operational grants remain separate
Baseline:     origin/main @ 2f427fcfb8818dd665310bae7e8cd5ffa066bdcc
```

## Goal

Define what trustworthy ConvMem means, bind each claim to observable evidence,
inventory the proofs already supplied by CG-1/CG-2 and existing recovery work,
and close only the gaps that remain. Later fault, compatibility, security, and
endurance work must have an oracle defined before implementation begins.

## Human consequence

If Ryan locks this architecture, the next lane may prepare a bounded execution
plan and evidence inventory. This document does **not** authorize production
activation, a CG-2 soak, owner cutover, GC, bulk mutation, cloud-policy changes,
or a deliberate failing-PR experiment.

## Trust model

ConvMem is a local-first memory system whose ledger and durable source material
must remain authoritative over derived projections and model interpretations.
LLM output, retrieved text, summaries, and external provider responses are
untrusted data until deterministic provenance, authority, and lifecycle rules
bind them to a permitted operation.

The arc begins at T1. CI merge protection is prerequisite infrastructure, not a
Trust Arc milestone. Pytest/Pylint/CodeQL enforcement is tracked separately.

## Trust Baseline claim schema

Every claim is recorded with:

| Field | Purpose |
|---|---|
| Claim | Plain-language property ConvMem promises |
| Lifecycle | Write / Store / Retrieve / Execute / Share / Forget |
| Authority | Ledger, generation pointer, backup, config, or other source |
| Failure mode | Concrete way the claim can be violated |
| Evidence | Test, invariant, measurement, or independent oracle |
| Expected degraded state | What remains true after failure |
| Consequence | Catastrophic / Critical / Degraded / Advisory |
| Gate | Fail-closed, warn/degrade, or informational |
| Owner | Lane or human who decides disposition |
| Scope | Production, isolated rehearsal, restore drill, or docs only |

Severity prevents every check from becoming a P0. Catastrophic and critical
claims may require fail-closed gates; degraded and advisory claims may warn when
the contract explicitly permits continued operation.

## Initial baseline claims

These are candidate claims for architecture review, not ratified thresholds.

| Candidate claim | Consequence | Initial evidence direction |
|---|---|---|
| No silently acknowledged-data loss | Catastrophic | Durable write/backup contract plus crash and restore evidence |
| Ledger/source remains authoritative over projections | Critical | Projection accounting, replay, and source-vs-serving checks |
| Wrong authority generation is never served as current | Critical | CG-2 authority and pointer proofs; negative controls |
| Corrupt immutable state cannot silently become service state | Critical | Cold-start rejection and recovery tests |
| `local_only = true` permits no corpus-bearing network request | Critical | Egress inventory, network-deny test, provider-call audit |
| Backup freshness remains within approved RPO | Critical | Snapshot gate and restore drill |
| Restore returns a usable service within approved RTO | Critical | Complete-data restore and queryability proof |
| Latency/backlog exceed targets only as declared degradation | Degraded | Measured budgets and visible health state |
| Optional provenance diagnostic unavailable | Advisory | Warn-only output with owner and follow-up |

RPO/RTO/SLO numbers must be derived from the failure they prevent and Ryan's
tolerance, not copied from literature or chosen as round numbers.

## Egress and local-only invariant

The baseline must inventory every operation capable of transmitting corpus
content, including synthesis, distillation, evaluation, telemetry, error
reporting, and future adapters. Each operation names provider, payload class,
authorization mode, and redaction behavior.

The invariant is stronger than “the config normally points local”:

> When `local_only = true`, no corpus-bearing network request is possible.

The first implementation slice may use a deterministic transport boundary and a
deny-by-default network test. PII scanning, poisoning defenses, and full
lifecycle remediation remain later T4 work.

## Evidence-first failure matrix

T2 begins by inventorying existing proofs, not by creating another test suite.
For each T1 claim, classify current evidence as **sufficient**, **partial**, or
**absent**. The inventory must include CG-1 durability/cold-validation evidence,
CG-2 authority/source freshness/reconciliation/logical accounting/mixed-mode/
rollback evidence, backup and restore drills, doctor/projection/synthesis/index
gates, and provider timeout/fallback safeguards.

Only partial/absent claims receive new fault tests. Candidate shapes are kill
during promotion, corruption/truncation, disk-full/read-only/short-write,
Chroma loss or underfill, source drift/lost notification, backup/config failure,
and model timeout/truncation/malformed output. Each row states the expected
post-failure state and recovery boundary.

## Compatibility and provenance boundary

The following are durable interfaces: ledger records, knowledge-unit JSONL,
Chroma metadata, generation pointers, configuration, evaluation records, MCP
responses, and backups. T3 defines versioning, N-1 → N migration, future-version
rejection, backup-before-migrate, atomic migration, rollback, old-state fixtures,
and embedding identity.

This track coordinates with CG-2 but does not reopen its authority design or
authorize activation/GC. The recurring legacy embedding-identity warning is a
candidate compatibility item, not permission for live corpus mutation.

## Security lifecycle boundary

T4 turns the baseline into controls across Write → Store → Retrieve → Execute →
Share → Forget: provenance-bound authority, poisoning/repair tests, named-cloud
payload classes, secret/PII handling, provider failure behavior, and Shadow
activation evidence mapped to the same claims. The old quarantined capture packet
and all live capture/Shadow activation grants remain hard stops.

## Operational envelope

T5 follows correctness and security contracts. It measures 24/72-hour watch and
refine behavior, RSS, latency, backlog, restore time, maintenance signals, and
dependency/security checks. Reproducible packaging and transitive locking may
proceed alongside T5 but must not delay T1. Formal releases remain later unless
external distribution becomes immediate.

## Architectural decisions and non-goals

1. CI merge protection is outside this arc.
2. T1 blends reliability contract, threat model, egress inventory, local-only,
   and severity classification.
3. T2 is proof-gap analysis against existing CG-1/CG-2 evidence.
4. T3 owns durable-format compatibility and provenance, not CG-2 activation.
5. T4 owns poisoning and broader cloud/security controls; T1 owns the minimal
   egress/local-only invariant.
6. Retrieval freshness/ranking remains separate unless a direct integrity or
   authority failure is demonstrated.
7. `doctor PASS` is one health signal, not the complete trust verdict.
8. Every measurable property has one authoritative owner and threshold.
9. Literature supplies hypotheses and test shapes; reported numbers are not
   ConvMem evidence until primary-source verified and locally calibrated.

## Planned phases

| Phase | Deliverable | Depends on | Gate |
|---|---|---|---|
| Prerequisite | CI checks required by GitHub ruleset | Existing CI | Ryan/platform settings |
| T1 | Trust Baseline and assurance matrix | Current main evidence | Architecture lock |
| T2 | Existing-proof inventory and gap matrix | T1 | Evidence design review |
| T3 | Compatibility/provenance contract | T1/T2 | Ryan Execute grant |
| T4 | Egress, poisoning, and lifecycle controls | T1/T2/T3 | Security review/grants |
| T5 | Endurance, resource, maintenance envelope | T1–T4 | VERIFY and Ryan gate |

## Reading and source boundary

Planning inputs are preserved in the 2026-08-14 literature handoff/addendum and
the Desktop synthesis. ConvMem evidence sources are:

- `docs/inter-model/HANDOFF-CG1-DEPENDABILITY-2026-08-10.md`
- `docs/plans/VERIFY-cg2-production-activation.md`
- `docs/plans/PHASE0-SHADOW-CONTRACT.md`
- `docs/plans/STATUS-shadow-ledger-phase0.md`
- `docs/builder-reference/zeller-builder-digest.md`
- `docs/builder-reference/hard-parts-builder-digest.md`
- `docs/builder-reference/evolutionary-architectures-builder-digest.md`
