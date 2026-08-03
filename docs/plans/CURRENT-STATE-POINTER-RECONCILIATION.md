# Plan — Current-State Pointer Reconciliation

**Status:** Kiro PASS (2026-08-02); Ryan accepted the contract decisions on
2026-08-02. The paired post-freeze implementation remains separately gated.

**Purpose:** Replace conflicting current-state discovery rules with one compact, deterministic routing contract. This plan authorizes neither a deployed-checkout change nor code, corpus, ledger, service, or archival mutation.

## Why this work exists

The current agent-routing contract is contradictory:

- docs/inter-model/LATEST.md calls itself the single current-state pointer, but has grown to 239 lines despite the README describing a three-bullet pointer.
- docs/inter-model/README.md also instructs agents to read newest files by modification time.
- docs/README.md says operational truth is convmem brief plus the ledger, not folder mtime.
- Open retrieval observations show agents failing to surface the current test phase/CLI syntax and the background synthesis plan pointer.

File mtime is useful diagnostic evidence, but it cannot establish authority or currentness: copying, checkout operations, rebases, and archival moves can change it without changing the underlying decision.

## Outcome

Define a small manifest contract for docs/inter-model/LATEST.md that routes a new agent to the authoritative current artifact for every live lane. It must make genuinely open work visible, keep historical detail in linked artifacts, and remain compatible with a later generated view over ledger-backed evidence without requiring that generator now.

## Accepted Ryan decisions (2026-08-02)

Ryan confirmed the following contract choices:

1. `LATEST.md` will become a compact three-section manifest: **Active now**,
   **Waiting / gated**, and **Standing / deferred**. It has one row per live
   lane rather than a literal three-item list.
2. A row carries a canonical link, Next actor, a falsifiable Now/Next statement,
   and an observable evidence-backed recheck or removal condition. No pointer
   ID namespace or mutable ownership taxonomy is added.
3. The reconciled pointer will be the canonical current-testing-phase source.
   `convmem --help` and its frozen source implementation are the canonical CLI
   syntax source; historical handoffs are not.
4. The reconciliation must land only as a paired post-freeze change with the
   `brief.py` mtime-authority removal and tests. Until then neither `LATEST.md`
   nor archive placement changes.

The exact current-testing-phase assertion must be selected from evidence at the
time of the paired cutover. It must not be pre-filled from the historical
Continue/Crush Phase 3 handoff, whose verification completed on 2026-07-12.

## Scope and boundary

### In scope now

- Contract, migration, acceptance, and review design.
- Read-only inventory of existing pointer entries and conflicting routing text.
- A fixed, hermetic retrieval-regression query set and expected answers.
- A docs-only reconciliation proposal for an isolated worktree, after review.

### Later implementation only

- Changing brief.py mtime/staleness behavior.
- Adding a small validator or generated manifest view.
- Tests for manifest structure, links, freshness semantics, and retrieval evaluation.
- Any archival move after link and authority review.

### Out of scope

- Ledger writes or changes to Ryan-only authority.
- Corpus writes, reindexing, ranking, embedding, or reranker changes.
- Bulk history reformatting, new folder taxonomy, or a generic governance framework.
- Live services, configuration, and the frozen deployed checkout.

## Proposed contract

### One routing manifest, not a historical handoff

LATEST.md is a compact routing manifest, not an inbox, release history, session log, or postmortem. Detailed context belongs in the linked canonical artifact: Architecture/Execution/VERIFY, an approved status document, or an explicit decision record.

Use three fixed sections:

1. **Active now** — work that a lane may perform now.
2. **Waiting / gated** — work whose next step requires named external authority or a prerequisite.
3. **Standing / deferred** — durable work that is intentionally not active and has a named recheck event.

These sections are the visible status. Do not add a separate row-level status taxonomy, and do not retain a literal three-item cap. The invariant is one compact row per live lane; a high count signals work to resolve, not work to hide.

### Minimal row grammar

Each row has only these components:

- Canonical artifact link.
- Next actor: role that owns the next action, not historical authorship.
- Now: one current phase, exact valid command, or gate.
- Recheck/remove when: an observable event or evidence.

Rules:

- The canonical artifact path, PR, or existing ledger identifier is the row identity; invent no new pointer-ID namespace.
- Now must not contain narrative history or lessons.
- A non-closed row must link to evidence that independently supports its stated condition.
- A row leaves the manifest only when its event condition occurs and linked,
  checkable evidence demonstrates it; an assertion alone is insufficient.
- A top-level Reviewed UTC timestamp is an annotation and review prompt, not an authority or inclusion filter. Freshness never hides dormant-but-blocking work.

### Authority and generated-view compatibility

For the initial contract, the manifest remains a reviewed documentation artifact. It must not imply that editing LATEST.md grants ledger authority or closes a Ryan-gated decision.

The grammar must remain projection-friendly: a later implementation may derive rows from evidence-bearing records. The plan does not choose that implementation now. Any future generator must preserve the same linked evidence, sections, and removal conditions.

## Migration design

1. Inventory every current top-level pointer entry without moving its source.
2. Classify it as current live lane, durable procedure/reference, history/verification, duplicate, or disputed.
3. Retain only one compact row for each current lane. Route durable procedures to their existing canonical runbook. Leave history in its existing document or Git history.
4. Hold disputed entries in Waiting / gated until Kiro or Ryan resolves them.
5. Do not retroactively reformat all historical documents and do not move closed material merely to make the new pointer look clean.

This is forward-only content reconciliation: apply the new row grammar to live lanes at cutover; keep closed history intact and findable through its existing links.

## Routing alignment and staged delivery

The following sources must agree on routing semantics without duplicating volatile phase facts:

- docs/inter-model/README.md
- docs/README.md
- docs/STATUS.md
- docs/MODEL-WORKFLOW.md
- SYNTHESIS-STATUS.md
- docs/inter-model/LATEST.md

SYNTHESIS-STATUS.md remains the first status source for background synthesis; the large built-plans document remains supporting detail.

### Coupling rule

This draft plan is safe during the freeze. A later deployed routing change must pair the documentation transition with the brief.py mtime-semantics change and its tests. Until that paired implementation lands, the project must not claim that deterministic pointer routing is fully enforced; mtime may remain a non-authoritative diagnostic only.

## Retrieval evidence design

Before any reconciliation, freeze a small fixture-based benchmark with expected answers for:

1. the exact current testing phase;
2. the exact valid CLI syntax; and
3. the canonical background-synthesis status and plan pointer.

Add two or three paraphrases per core query, historical-trap queries, and unaffected control queries. Later compare baseline and candidate with corpus, chunking, embeddings, ranking, recency, reranking, query wording, and top-k held constant.

Before any candidate routing document changes, record the baseline results in a
committed fixture file so the comparison has a frozen reference point.

Required later acceptance evidence:

- core current-fact accuracy: 3/3;
- canonical source appears top 1 for core queries and top 3 for paraphrases;
- zero historical documents presented as current for those queries;
- no material regression on controls;
- mtime perturbation of historical files does not change current-state routing;
- a newer unlisted historical file does not become authoritative; and
- session-start routing reaches the canonical fact in at most two document hops.

The benchmark must use temporary fixtures only. No live corpus mutation or ranking change belongs to this plan.

## Stop conditions

Stop and obtain review rather than improvising if:

1. two artifacts plausibly claim to be canonical for one lane;
2. the current testing phase or CLI syntax lacks checkable evidence;
3. a row removal would require a Ryan decision or ledger action;
4. a proposal needs bulk archival, a new taxonomy, or a governance framework;
5. a row has no observable recheck/remove condition;
6. a field duplicates facts already carried by the linked artifact;
7. a migration would make docs routing deterministic while leaving brief.py to assert contradictory mtime authority; or
8. retrieval evaluation would change documentation and ranking/corpus state in the same comparison.

## Review questions

### Kiro

1. Are the three sections sufficient to replace the stale three-bullet rule?
2. Does Next actor avoid the false ownership semantics of a mutable Owner field while preserving accountability for the next step?
3. Should compound state be represented as two linked lanes rather than a row with compound status?
4. Is SYNTHESIS-STATUS.md correctly the canonical status source for the background-synthesis lane?
5. Which existing LATEST entries remain genuinely current, and which are history or durable procedure?
6. Should a future brief.py change remove mtime staleness entirely or retain it only as non-authoritative diagnostics?
7. Should every Now field be a falsifiable assertion that retrieval or a standing check can independently confirm or contradict?

### Ryan

The contract questions above are decided. The remaining Ryan decisions are:

1. Resolve any disputed current, waiting, or deferred lane at cutover.
2. Authorize the later paired implementation that changes shared routing and
   `brief.py`; no archival movement is included in that authorization.

## Independent-review checklist

| Check | Required outcome |
|---|---|
| Authority | Manifest does not create ledger or closure authority. |
| Honesty | Every live row has a canonical artifact and evidence-backed current fact. |
| Completeness | No known open lane is omitted merely to meet a count target. |
| Minimality | No new IDs, front matter, registry, or narrative-history field. |
| Migration | Sources remain in place; no bulk historical rewrite or archive move. |
| Consistency | README/workflow/status documents describe one routing rule. |
| Future proofing | Later brief.py enforcement is explicit and coupled, not implied. |
| Retrieval | Fixed fixture queries and mtime negative controls are defined before evaluation. |

## Post-freeze cutover sequence

1. Re-read the candidate classification and current source artifacts after the
   freeze; select a checkable current-testing-phase statement then, rather than
   reusing historical phase language.
2. Obtain Ryan's explicit implementation authorization and create a separate
   implementation worktree/branch. The paired change is limited to
   `docs/inter-model/LATEST.md`, the routing statements named above, `brief.py`,
   and focused tests unless an approved review expands it.
3. Make `brief.py` use the manifest for current-state routing. It may retain
   file mtime only as explicitly labelled non-authoritative diagnostics; it must
   not tell agents to read a newer file or treat a newer file as current.
4. Replace the long pointer with the reviewed manifest in the same change.
   Move no source files and do not archive history in this cutover.
5. Set the CLI row or linked canonical source to `convmem --help`; validate the
   exact current-testing-phase row against the current source evidence.
6. Add focused structure/link/mtime-perturbation tests and run the frozen
   retrieval fixture comparison without corpus, ranking, or configuration
   changes.
7. Require Kiro review of the exact diff and Ryan approval before merge. A
   wrong or unsupported current-phase assertion, a missing canonical link, or
   any continued mtime-authority output is a stop condition.

## Next action

The safe planning work is now complete. Hold the actual pointer, archive, and
`brief.py` edits until after the freeze and Ryan's paired-implementation grant.
