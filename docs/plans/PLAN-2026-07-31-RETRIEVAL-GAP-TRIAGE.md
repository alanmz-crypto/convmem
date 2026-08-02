# Retrieval-gap triage protocol

**Status:** plan-only investigation. This document authorizes no `convmem add`,
bulk indexing, verification, ledger mutation, census access, Shadow operation,
configuration change, or service action.

**Branch PR title:** `docs: freeze-safe analysis plans for C6 hold, standing
checks, and retrieval gaps`

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
monitor work. They are not retrieval-gap closure targets in this worktree. A
separate [staging2 header verification checklist](PLAN-2026-07-31-STAGING2-HEADER-VERIFICATION.md)
is plan-only and does not authorize external changes.

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

### First bounded pass: Phase 3 and CLI syntax (diagnostic cross-check)

This read-only pass is recorded here so the next investigator does not repeat
it:

| Observation(s) | Evidence | Result | Disposition |
|---|---|---|---|
| `obs_67af0873f738`, `obs_a379f07d0878` | `docs/inter-model/PLAN-2026-06-29-searchable-cli-chats-HANDOFF.md`, dated 2026-06-29, names Phase 3 as Continue + Crush, verify-only. | Phase 3 identity is supported, but the finding is not a complete current-state brief. | `partial`; recheck against the newest handoff before closure. |
| Same pair | Frozen-checkout `convmem.py` declares `--author` and repeatable `--keyword` with a minimum of three keywords. | Canonical single-record flag shape is supported by source, but no ledger write was attempted. | `partial`; keep the exact source revision and do not run `add`. |
| Same pair | Search result `obs_d348798e5fdd` and `BUILT-PLANS-2026-06-24-to-2026-06-29.md` say only `--type observation` was accepted, while frozen `convmem.py` help declares additional types. | Type behavior is conflicting or stale and remains unverified. | `conflicting`; resolve from read-only source/tests or Ryan after the freeze. |

The evidence table is a draft review artifact. A future `convmem add` requires
Ryan's explicit post-freeze authorization and may not be inferred from a
complete table row.

The compact table above is a diagnostic cross-check, not the structured
evidence table below; it is retained to show the original three-source
comparison without duplicating the full schema.

### Priority 1 result: current phase and CLI syntax recheck

The exact-title search returned
`docs/inter-model/PLAN-2026-06-29-searchable-cli-chats-HANDOFF.md`. Its Phase 3
section names the work as **Continue + Crush (verify only)** and calls for
`convmem stats` plus Continue/Crush spot-check searches. The source is dated
2026-06-29, so it establishes the canonical phase handoff but is not proof
that no later phase superseded it by 2026-07-31.

The frozen source revision and a read-only `convmem add --help` invocation agree
on the single-record command shape: `--title`, `--summary`, `--author`, and at
least three repeatable `--keyword` values; `--type` accepts observation,
solution, decision, explanation, or pattern. No `add` command was run.

| Observation(s) | Query family | Authoritative source | Answer | Completeness | Freshness risk | Next action |
|---|---|---|---|---|---|---|
| `obs_67af0873f738`, `obs_a379f07d0878` | `convmem "current testing phase CLI syntax retrieval gap coding.tooling"`; `convmem "current testing phase not surfaced by search"` | `docs/inter-model/PLAN-2026-06-29-searchable-cli-chats-HANDOFF.md` dated 2026-06-29; frozen `convmem.py`; read-only `convmem add --help` | Phase identity and CLI flag shape are independently recoverable, but phase freshness remains limited to the 2026-06-29 handoff. | `partial` | A later handoff may supersede the 2026-06-29 phase label. | Recheck the newest handoff after the freeze; do not close or write a ledger update. |

### Priority 2 result: background synthesis pointer

The exact-title search found the canonical
`docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md`, compiled 2026-06-29.
Its reconciled status states:

- Phase 0 manual digest: closed at Run 6; Run 8 completed the first approved
  `--propose` trial.
- Phase 1 `cross-project-digest.sh`: shipped; the weekly timer is read-only,
  while timer-driven `--propose` remains Ryan-gated.
- Phase 2 autonomous linker: deferred; the agent-habit/value gate and manual
  `link_queue.jsonl` review remain open.
- `obs_806985bc5697` remains the searchable pointer for those deferred linker
  gates; no new summary is needed.

This is complete for source identity and phase-gate status, but it does not
close the ledger observation. The companion query
`background synthesis pointer Phase 1 shipped Phase 2 deferred` failed inside
the read-only reranker with `ValueError: Unsupported input type: NoneType`.
That is likely a retrieval-path diagnostic, not evidence that the canonical source is
missing. Do not change reranker configuration or fix code in this frozen
checkout; the [isolated reranker diagnostic plan](PLAN-2026-07-31-RERANKER-NONETYPE-DIAGNOSTIC.md)
defines the future test-only investigation.

| Observation(s) | Query family | Authoritative source | Answer | Completeness | Freshness risk | Next action |
|---|---|---|---|---|---|---|
| `obs_806985bc5697` | `convmem "BUILT-PLANS-2026-06-24-to-2026-06-29 Phase 0 Phase 1 Phase 2 gates"`; `convmem "background synthesis pointer Phase 1 shipped Phase 2 deferred"` | `docs/inter-model/BUILT-PLANS-2026-06-24-to-2026-06-29.md`, compiled 2026-06-29 | Canonical source and phase-gate status are complete; the pointer observation remains open and no new summary is needed. | `complete` | Later synthesis status may supersede phase status; the companion query also exposed a reranker diagnostic. | Stop; preserve the pointer and do not create a ledger or implementation update. |

### Priority 3 result: Willowy Hollow guide and header precedent

Read-only file discovery in
`/home/lauer/WordPress/willowyhollow-practice` did **not** find the named
`docs/WILLOWYHOLLOW-WEBDEV-GUIDE.md`. It did find:

- `scripts/staging2-security-headers.htaccess.snippet`, dated 2026-07-08,
  identifying `dec_prop_20260623_153615_a66c` and specifying exact CSP, HSTS,
  and Referrer-Policy header values;
- `docs/plans/s2_hotfix_reconcile.md`, marked accepted 2026-07-11, with a
  broader S2 remediation history and explicit external-change HOLDs; and
- `logs/2026-06-30-pull-staging2-fix.md`, documenting a prior empty-dump
  failure and its script fix.

This supports partial precedent retrieval, not current live verification. The
snippet's historical “monitor dry-run pass” conflicts in time/scope with the
current unresolved staging2 monitor observations. Do not infer that the
headers are deployed, copy the snippet into live configuration, or close
`obs_885c236b34fd` or `obs_e1520bf6e193` from these files alone.

| Observation(s) | Query family | Authoritative source | Answer | Completeness | Freshness risk | Next action |
|---|---|---|---|---|---|---|
| `obs_885c236b34fd`, `obs_e1520bf6e193` | Read-only file discovery for the named guide and staging2 header precedent in `/home/lauer/WordPress/willowyhollow-practice` | Guide not found; historical `scripts/staging2-security-headers.htaccess.snippet` dated 2026-07-08 plus S2 plan/log paths | Historical precedent was found, but it is not current live verification and the named guide remains not found. | `partial` | The 2026-07-08 snippet conflicts in time/scope with current unresolved monitor observations. | Seek separately authorized current evidence after the freeze; do not copy headers or close observations. A retrieval gap does not authorize access to or changes in the WordPress environment. |

## Stop conditions and escalation

Stop the search and mark the observation `partial` or `conflicting` when:

- two sources disagree on the current phase or command syntax;
- a `convmem ask` result disagrees with the corresponding search result;
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
