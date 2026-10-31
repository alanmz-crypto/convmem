# ConvMem assessment preserved for review

**Date:** 2026-10-31. **Arc:** none (ad-hoc). **Assessed source:** `d54f92bcd78248c8aee8a54df758564752d79aa4`.

This is a public-safe preservation of the first assessment and its reasoning. Private source links are in the separately saved companion. The subsequent [research synthesis](RESEARCH.md) refines the sequencing; the [handoff](../CODEX-2026-10-31-convmem-general-memory-fable-review-handoff.md) defines Claude Fable's assignment.

## User goal

Build an all-purpose memory project for AI on the user's own PC. Do not constrain its future to the coding/security workflows it currently serves. The PC is in transit, so the requested work is assessment and planning. The user explicitly permitted reading two connected Drives as examples of the work the system should eventually help with locally.

## What was inspected

- Repository README, agent protocol, status pointers, active arc briefs, issue descriptions, source and selected test fixtures.
- Current main source at the revision above, independently matched between local checkout and GitHub.
- The preserved cloud runtime and migration status records, kept separate from main and from current PC health.
- Purposeful samples from both Drives. One account review covered the root, 16 relevant folders and substantive examples from five workflow areas. The other covered the first 100 root items, one folder-discovery page, relevant folders and eight representative files. This was not an exhaustive inventory or a validation of every binary file.

No full unit-test run, live retrieval quality measurement, performance benchmark or corpus migration was performed for this assessment. The migrated runtime's doctor exited nonzero because local model access and workstation-specific backup/client configuration were unavailable in this environment. That result is not a diagnosis of the PC or evidence that earlier bounded migration checks never passed.

## Existing strengths

The project already contains local retrieval, multiple transcript adapters, CLI/MCP access, provenance, durable decision intent, evidence relationships, bounded original-source expansion, operational recovery controls and several evaluation surfaces. These are valuable assets. The proposal is to test whether they can support broader sources and tasks, not assume a rewrite is required.

Relevant public sources: [README](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/README.md), [source expansion](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/chunk_expand.py), [MCP](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/mcp_server.py), [authority map](https://github.com/alanmz-crypto/convmem/blob/d54f92bcd78248c8aee8a54df758564752d79aa4/docs/audit-ledger-first/CURRENT-OBSERVATION-AUTHORITY.md).

## Consequential gaps

| Observation | Why it matters | Qualification |
|---|---|---|
| Adapter routing is specialized around chats and recognized/registered project documents | Ordinary local documents need a first-class ingestion route | Do not claim all Markdown is unsupported; special routes already exist |
| Distillation and synthesis prompts emphasize coding and short technical summaries | Conditions, minor details, rejected options and nontechnical work can be distorted or omitted | This is an implementation bias, not proof of failure on every noncoding query |
| Normal retrieval begins with a limited vector candidate set | Keyword scoring/reranking cannot recover a passage never admitted to that set | Some exact-ID and fallback paths exist; distinguish them from general lexical candidate union |
| Bounded source expansion exists but normal ask does not automatically call it | A stored original conclusion can be absent from the evidence supplied to synthesis | Extend/integrate existing machinery rather than build it again |
| Current general semantic structures do not provide the proposed claim-level temporal/entity contract | “Current,” “historical,” “hypothetical,” and “confirmed” require more than file mtime | Existing timestamps, decision supersession and provenance are partial support, not nothing |
| Source authority is split and JSONL is not a complete immutable event history | A storage migration or recovery assumption can lose meaning/data | Keep current authority intact until separately demonstrated migration/rebuildability |

Code reading points: `adapters/detect.py`, `distill.py`, `domains.py`, `query.py`, `ask.py`, `chunk_expand.py`, `evidence.py`, `ledger.py`, source-generation/publication modules. [CLAIMS.md](CLAIMS.md) supplies review challenges.

## Corpus-derived needs, generalized for public review

These are patterns inferred from authorized samples, not a complete list of the user's work and not evidence of implemented capability. The examples below are generalized review scenarios.

| Work pattern | Memory behavior to test |
|---|---|
| Changing opportunity or project terms | Distinguish historical advertisement, hypothetical scenario, proposal and actual agreement |
| Coordinated logistics | Preserve owning sources, dependencies, dates/timezones and changed assumptions |
| Repeated research | Retrieve lessons, failed approaches and cost assumptions without treating illustrative numbers as facts |
| Administrative records | Distinguish “not recorded” from “none,” and planned steps from completed events |
| Learning/reference materials | Find exact passages, preserve chapter/page references and handle Thai/English queries |
| Tables and numerical records | Preserve typed numbers and formulas; compute reproducibly with cell-level provenance |
| Media collections | Catalog identity, format, versions and use; not every asset needs transcription |
| Software and AI conversations | Recover original conclusions, verified actions, decisions and unresolved work |

The common requirement is to preserve what a statement is, where it came from, when it applied and whether it has changed. It is not to build eight separate domain applications. Domain labels alone do not solve source interpretation or structured computation.

## Status corrections that prevent repeating old work

- The last inspected PC snapshot described Codex incremental admission and same-source publication fencing as live at runtime `1a68675`. It did not establish all sources as incremental; Crush/Cursor remained legacy routes, and no Kiro sources were selected. This is dated runtime evidence.
- Main includes doctor-acknowledgment PR #416 as `4b4796b`, followed by #419 at `d54f92b`, despite older pointer text still describing #416 as open. Source merge is not deployment proof.
- Issue #263 is only partly unresolved: expansion shipped, while discovery/default-answer evidence handling still needs assessment.
- Issue #320's historical 7/10 golden score is not a current measurement. Q08/Q10 expectations have changed; the candidate-recall concern remains relevant. Do not report the old score as freshly reproduced.
- The migration manifest had an older top-level pending status and a newer section recording successful bounded correction/startup/retrieval checks. Preserve both dates/scopes; neither establishes all future sessions or the PC as healthy.

## Initial prioritization and subsequent refinement

The initial assessment proposed: establish a restart/recovery baseline; build a small cross-domain pilot; improve original evidence recall; require efficient updates; and prove broader generality with reference material and structured calculations.

Research then sharpened this into a source-preserving pilot before a broad claim/graph layer. Basic caching belongs in the first adapter. Current state should be a reproducible source-backed view. Explicit lessons can be tested before autonomous extraction. Recovery qualification gates live writes, while isolated development can proceed during transit.

The proposed 48-case suite and six continuation tasks have not been built or executed. Their purpose is to identify failures and decide the next intervention, not produce a universal benchmark claim. Compare against ordinary source search; use preselected correct evidence only as a diagnostic oracle.

## Strategic tradeoff to challenge

The author proposes deferring optional Switchboard integration/publication and graph/database replacement while the core proves value across tasks. The grounds are marginal product value and existing CLI/MCP access, not an assertion that operational safeguards are wrong. Existing arc evidence and grants remain intact. Claude should challenge whether a deferred dependency is actually necessary, whether a smaller replacement would be better, or whether the incremental approach preserves too much complexity.

## Jargon TL;DR

| Term | Meaning |
|---|---|
| Candidate recall | Whether required evidence enters the set that later ranking can consider |
| Source expansion | Reading surrounding original material after a search result identifies a relevant location |
| Publication fencing | Existing controls that prevent competing/stale ingestion from publishing an invalid active generation |
| Derived view | A generated summary or state representation whose authority comes from its identified inputs |

**Assessment status:** useful direction proposed; corpus fit, prioritization and implementation scope await adversarial review.
