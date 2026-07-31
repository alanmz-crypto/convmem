# Retrieval-gap triage protocol

**Status:** plan-only investigation. This document authorizes no `convmem add`,
bulk indexing, verification, ledger mutation, census access, Shadow operation,
configuration change, or service action.

**Evidence basis:** the read-only 2026-07-30 `convmem unresolved` result lists
11 open observations: five coding/WordPress retrieval gaps and six staging2
header-monitor observations. Kiro was unavailable because its monthly request
limit was reached; no DeepSeek connector is exposed. This is a Codex fallback
plan, not a delegated verdict.

The deployed checkout remains at
`76126e07a97187f68d925dd8b431d2d03967084f` through 2026-08-07 00:00 UTC.

## Priority order

### 1. Current testing phase and canonical CLI syntax

Observations: `obs_67af0873f738` and `obs_a379f07d0878`.

These are one navigation problem with two ledger observations. First search
the canonical Phase 3 handoff and then verify the exact `convmem add` syntax:

```text
convmem "Phase 3 Continue Crush handoff current testing phase"
convmem "convmem add author keyword syntax"
```

An optional question pass, only if the local ask path is available, is:

```text
convmem ask "What is the current testing phase and canonical convmem add syntax? Cite the authoritative handoff or plan and flag stale sources."
```

Complete means one current authoritative source names the phase and one
authoritative source shows the complete command shape, including required
author and repeated keyword fields. A result that finds Phase 3 but omits
syntax, or syntax without freshness/provenance, remains partial.

### 2. Background synthesis pointer and phase gates

Observation: `obs_806985bc5697`.

Use exact-title searches to recover the canonical pointer without duplicating
the plan:

```text
convmem "BUILT-PLANS-2026-06-24-to-2026-06-29 Phase 0 Phase 1 Phase 2 gates"
convmem "background synthesis pointer Phase 1 shipped Phase 2 deferred"
```

Complete means the result identifies the canonical plan, states which phases
shipped or remain gate-bound, and distinguishes a pointer from an implementation
instruction. Do not create a new summary when the canonical plan is found.

### 3. Willowy Hollow precedent and webdev guide

Observations: `obs_885c236b34fd` and `obs_e1520bf6e193`.

This is a separate-repository/site-scoped track. It must not block the two
coding-tooling tracks and must remain read-only in
`/home/lauer/WordPress/willowyhollow-practice`. The bounded lookup is the exact
guide path plus the Method A deployment precedent. Do not inspect or mutate
WordPress content or database state as part of this triage.

Complete means the guide path and the site-specific session-loop precedent are
both identified, with their freshness and repository path. A general search
hit without the guide contents or site scope is partial.

The six staging2 CSP, HSTS, and Referrer-Policy observations remain external
monitor work. They are not retrieval-gap closure targets in this worktree.

## Evidence table

Keep each result in chat or this worktree document only:

| Field | Required value |
|---|---|
| Observation(s) | Exact `obs_` IDs and plain-language title. |
| Query family | Exact search or ask text used. |
| Authoritative source | Path/title and source date or revision, if available. |
| Answer | One sentence answering the observation. |
| Completeness | `complete`, `partial`, `conflicting`, or `not found`. |
| Freshness risk | Why a newer handoff could supersede it. |
| Next action | One bounded follow-up or `stop`. |

Do not include payload-bearing corpus excerpts, stable user identifiers, or
unnecessary session transcript text in a shareable note.

## Stop conditions and escalation

Stop the search and mark the observation `partial` or `conflicting` when:

- two sources disagree on the current phase or command syntax;
- the newest source is stale relative to a later handoff;
- two query families fail to locate an authoritative source;
- closure would require `convmem add`, bulk indexing, verification, live
  artifact access, or a config/service operation; or
- a result would require changing an observation rather than documenting a
  finding.

Escalate only the bounded question and the evidence table to Ryan. Ryan alone
decides whether a new observation, ledger record, or cross-repository action is
authorized. No retrieval result closes an observation automatically.

**Verdict: HOLD ON LEDGER WRITES.** The next harmless action is a read-only
search pass for Priority 1, followed by Priority 2 if the first pass is
complete or clearly blocked. Findings remain in chat or this isolated worktree.
