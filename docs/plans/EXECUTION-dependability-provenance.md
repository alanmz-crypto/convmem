# Execution Plan — Dependability and Provenance Trust Arc

```text
Planning Status
Phase:        Execution Planning
Characters:   Task Decomposer, Evidence Mapper, Scope Guardian
Lanes:        Codex authors; Kiro reviews; Cursor implements after Ryan grant
Authority:    No Execute authorization in this document
Baseline:     origin/main @ 2f427fcfb8818dd665310bae7e8cd5ffa066bdcc
```

## Goal and sequencing

Turn the Trust Baseline into a bounded evidence package without duplicating
CG-1/CG-2. Each phase produces the oracle needed by the next.

```text
CI prerequisite → T1 Trust Baseline → T2 proof inventory/gaps
                 → T3 compatibility/provenance → T4 security boundary
                 → T5 endurance and enforcement
```

## Scope lock

### In scope

- Claim matrix covering durability, authority, provenance, egress, recovery, and
  declared degraded states.
- Inventory of CG-1/CG-2, backup, restore, doctor, and provider proofs.
- Gap-driven failure matrix with expected post-failure states.
- Schema/version/migration policy and old-state fixture requirements.
- Minimal hard local-only boundary and authoritative egress inventory.
- Later poisoning/lifecycle, endurance, resource, and maintenance evidence.
- Filled VERIFY evidence and independent review before closure.

### Out of scope

- CI workflow or GitHub ruleset implementation; prerequisite infrastructure is
  tracked separately.
- CG-2 soak, owner activation, generation cutover, or GC.
- Shadow activation, live capture, live configuration, or bulk mutation.
- Retrieval ranking/recency tuning absent a direct integrity failure.
- New governance surfaces when existing standing checks can carry the risk.
- Cloud policy changes beyond a separately named exact operation.

## Ordered tasks

| ID | Deliverable | Depends on | Owner lane | Gate |
|---|---|---|---|---|
| T0 | Confirm CI prerequisite status and required-check evidence | Existing #187 | Ryan/platform | External settings |
| T1 | Trust Baseline claim matrix and assurance structure | — | Codex | Ryan architecture lock |
| T2 | Existing-proof inventory and classified gaps | T1 | Codex/Crush | Evidence-map review |
| T3 | Compatibility/provenance contract and fixtures | T1/T2 | Codex | Ryan Execute grant |
| T4 | Security boundary and lifecycle controls | T1/T2/T3 | Codex/Cursor | Security review/grants |
| T5 | Operational envelope, soak, and maintenance plan | T1–T4 | Cursor | VERIFY/Ryan gate |

T1 and T2 are planning deliverables before implementation. T3–T5 may become
separate implementation slices after the architecture and evidence map are
accepted; they are not authorized by this document.

## T1 — Trust Baseline v1

Produce one row per claim with `claim`, `lifecycle`, `authority`, `failure_mode`,
`evidence`, `expected_degraded_state`, `consequence`, `gate`, `owner`, `scope`,
and `measurement/threshold`.

Required initial claims include acknowledged-data durability, ledger authority,
generation authority, corrupt-state refusal, backup RPO, restore RTO, projection
completeness, provenance preservation, egress inventory, and local-only network
denial. No threshold is accepted without a stated bad outcome.

## T2 — Evidence inventory and gap analysis

For every T1 claim:

1. cite the existing implementation or test;
2. name the independent oracle;
3. record exact scope and revision;
4. classify sufficient, partial, or absent;
5. identify the smallest missing proof.

Inspect CG-2 VERIFY rows explicitly rather than reimplementing their coverage.
Admit a new fault test only when the inventory shows a partial or absent claim.
Candidate gaps include process kill, immutable corruption, short writes/full or
read-only storage, Chroma failure/underfill, source drift, backup/config failure,
and provider timeout or malformed output.

## T3 — Compatibility and provenance

Define the durable-format contract before writing migration code: version fields,
supported window, N-1 → N migration, future-version rejection, dry-run,
backup-before-migrate, atomic replacement, rollback, old-backup fixtures,
embedding identity, and ownership for pointer/manifest/MCP/evaluation/backup
schemas. No live migration or corpus rewrite is authorized here.

## T4 — Security boundary

Implement only after T1 names the egress surface and T2 identifies existing
controls. Cover local-only transport denial, named-cloud payload classes,
provenance-bound instruction/data separation, Write → Store → Retrieve → Execute
→ Share → Forget poisoning/repair, provider loss, malformed output, and secret
handling. The local-only invariant is T1; its broader adversarial suite is T4.

## T5 — Operational envelope

After correctness/security gates are defined, measure 24/72-hour behavior and
resource limits: RSS, latency, backlog age, restore time, provider-degradation
rate, projection lag, and maintenance freshness. Each metric has one owner and
action threshold. Packaging/locking may proceed alongside T5; release artifacts
are later unless public distribution becomes immediate.

## Review and stop conditions

Each implementation slice reports focused tests, proof mapping, negative
controls, fault/compatibility evidence where applicable, full regression, exact
revision, and residual risks with consequence and owner. No model self-assessment
is sufficient as the only evidence for a critical claim.

Stop if a test duplicates CG evidence without a new failure window, a threshold
lacks a bad outcome or single owner, a warning is treated as a critical pass,
live state would be mutated without exact authorization, or literature numbers
are used without primary-source verification and local calibration.

## Handoff

After Ryan locks architecture, Codex may refine this plan into implementation
briefs. Cursor owns implementation, Kiro required design review, and Ryan owns
architecture lock, external settings, named operational grants, and merge.
