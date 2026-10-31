# Field guide: ConvMem assessment and research

**Date:** 2026-10-31. **Arc:** none (ad-hoc). **Next reader:** Claude Fable.

Start with the [review handoff](../CODEX-2026-10-31-convmem-general-memory-fable-review-handoff.md). It states the actual assignment, the review target and the expected verdict. This guide prevents the supporting material from becoming another maze of handoffs.

## The work in one paragraph

Ryan asked how ConvMem should become an all-purpose AI memory system on his PC, beyond its existing coding/security workflows. Codex reviewed the source and representative material from two authorized Drives, then researched retrieval, temporal memory, document ingestion, learning and evaluation. The recommendation is to prove a small cross-domain source-retrieval pilot, preserve original evidence, keep current state and lessons traceable to their inputs, and measure whether they improve continuation of real work. This is a recommendation awaiting adversarial review, not an accepted architecture or implementation grant.

## File map

| File | Purpose | Authority / status |
|---|---|---|
| [Handoff](../CODEX-2026-10-31-convmem-general-memory-fable-review-handoff.md) | Claude's task, scope, adversarial questions, verdict contract | Current assignment for this review |
| [ASSESSMENT.md](ASSESSMENT.md) | Repository findings, corpus-fit synthesis, initial next moves | Author assessment; challenge against pinned code/private evidence |
| [RESEARCH.md](RESEARCH.md) | Full research synthesis, experiments and bibliography | Review-friendly generated text view |
| [research.html](research.html) | Original complete research report | Preserved report source; original links and qualification language |
| [convmem-research.pdf](convmem-research.pdf) | Nine-page reading/printing copy | Alternate rendering, not extra evidence |
| [CLAIMS.md](CLAIMS.md) | Claims, source types, evidence and falsifiers | Fast route to consequential objections |
| [SOURCE-REGISTER.json](SOURCE-REGISTER.json) | Selected public references and research accounting | Navigation ledger; not raw search logs or proof of full-paper reads |
| [PACKET-MANIFEST.json](PACKET-MANIFEST.json) | SHA-256 and size of delivered packet files | Integrity of this snapshot, not correctness of its conclusions |
| [make_pdf.py](make_pdf.py) | Original local PDF renderer | Optional reproduction helper; not part of ConvMem runtime |

The original reports under `/workspace/exa-results/convmem-research-2026-10-31/` were copied into this packet. The public delivery is in Git; a private archive also contains the corpus evidence map and a delivery receipt. The final delivery message supplies exact links and the commit. No raw private corpus or Drive exports are included in the public copy.

## Choose a reading route

**Ten-minute orientation:** handoff → this guide → assessment recommendation → research section 4 (implementation sequence) and section 5 (experiments).

**Technical challenge:** claim register → referenced code at `d54f92bcd78248c8aee8a54df758564752d79aa4` → relevant current arc briefs. Separate later code changes from errors in the assessment of that revision.

**Research challenge:** research sections 2–3 → original cited papers → their evaluation setup, negative results and limitations. Scores from different papers are not a shared leaderboard.

**Corpus-fit challenge:** private companion `PRIVATE-EVIDENCE.md` → authorized original Drive files. Without access, label those claims unverified and continue with public technical review. The private notes are sampling summaries, not immutable copies of the files.

## Which state wins?

1. The user's stated product goal controls this task: broad local-PC memory.
2. The review commit/manifest identify the proposal under review.
3. Source code at the assessed revision establishes implementation facts.
4. Exact dated runtime evidence establishes only the conditions it actually measured.
5. Specific current arc briefs generally outrank old rollups, but even a brief can lag git history.
6. The report's proposals and external research do not establish deployed behavior or user benefit.

In particular: `d54f92b` is the assessed GitHub source. The preserved runtime was based on `1a686753d8fd1b710883050e8a4f9c45b7ae1e26` with cloud-specific corrections. They are different artifacts. A merge does not prove PC deployment; a cloud failure does not prove PC failure.

## What is done and what is not

**Done:** source/status review; bounded Drive sampling; external research synthesis; local report/PDF; author-side skeptical check; this saved handoff, field guide and evidence register.

**Not done:** Claude Fable review; fresh live retrieval benchmark; complete Drive inventory; prototype adapters; new temporal schema; lexical-index implementation; parser/model comparisons; the proposed 48-case suite or six continuation tasks; a production restore rehearsal; implementation or deployment.

The proposed evaluation cases and pass conditions are specifications. No result can be inferred from their presence in a document. An author-side critique was used to improve sequencing and pending-case reporting; it is not the independent review now requested.

## Changes made after the initial assessment

- Preservation and source retrieval moved ahead of a broad extracted-claim framework.
- Basic caching/idempotency moved into the first adapter rather than a later optimization.
- Current project state became a source-backed view with freshness rather than another authoritative summary.
- The evaluation gained raw-source/oracle controls, out-of-order updates, deletion/availability checks and total processing cost.
- The first packet explicitly retains source-ownership and correction statements; later packets generalize their handling.
- Passed, failed and pending cases must be reported separately, including not-yet-supported formats.

These refinements are the active recommendation. Older wording in the initial assessment provides reasoning history rather than a competing execution plan.

## Practical verification

At the delivery commit, compare each manifest entry's SHA-256 and byte count with the file. Paths in the manifest are relative to the repository root. The manifest itself and `LATEST.md` are excluded; no self-referential digest is claimed. The PDF is included as saved bytes; rebuilding may change PDF metadata and therefore its hash without changing the prose.

The separate private archive has its own manifest and a `DELIVERY.json` receipt. It contains the public packet plus private source pointers and limitations. Keep those private notes out of commits and public review comments.

## Jargon TL;DR

| Term | Meaning |
|---|---|
| Evidence versus proposal | What was actually observed versus what the author recommends trying |
| Source family | Related originals, versions and derivatives that should not be counted as independent corroboration |
| Source-backed view | A generated brief whose statements and freshness can be traced to identified source revisions |
| Idempotency | Repeating the same ingestion has no additional semantic effect or repeated expensive processing |

**Next step:** Claude Fable challenges the pinned packet and returns a verdict with evidence and a revised first slice.
