# Review handoff: challenge ConvMem's general-purpose memory direction

**Date:** 2026-10-31  
**Author:** Codex, assessment and research synthesis  
**For:** Claude Fable, independent adversarial reviewer  
**Arc:** none (ad-hoc strategic assessment; no new implementation arc)  
**Authorization:** Ryan requested a project assessment, deeper web research, and then: “Create a handoff so Claude fable can do an adversarial review. Make sure to save your work. Create a field guide to your work if there's a lot and easy to lose track of.”

The decision is whether this proposed direction deserves a bounded implementation plan. Your job is to find consequential errors, missing alternatives, weak evidence and bad sequencing. You may reject the direction. Do not optimize for agreeing with the author or for producing a predetermined number of findings.

## Resume state

| Field | Value |
|---|---|
| Review state | `DELIVERED`; verdict: `REVISE_BEFORE_PLANNING`; reviewer: [CLAUDE-2026-10-31-convmem-general-memory-adversarial-review.md](CLAUDE-2026-10-31-convmem-general-memory-adversarial-review.md) |
| Assessed source | `d54f92bcd78248c8aee8a54df758564752d79aa4` |
| Delivery branch | `docs/2026-10-31-general-memory-fable-review` |
| Exact content target | The delivery commit supplied with this handoff and `review-pack-2026-10-31-convmem/PACKET-MANIFEST.json`; report both in your verdict |
| Research | Completed synthesis; 184 requested search-result slots across 30 Exa searches/six workstreams, including duplicates and rejected results |
| Implementation | None of the proposed improvements has been implemented by this work |
| PR | Not opened by this handoff |
| Next lane | Claude Fable — adversarial document/code-evidence review |
| Ryan gate | None for the requested review; later implementation, deployment and existing arc operations are separate decisions |
| Track A | This cloud chat was not ingested into the preserved runtime; the saved packet is the handoff record |

The branch is a delivery location, not an immutable review identity. Resolve its commit once, then review that revision. The manifest deliberately excludes itself and the mutable LATEST routing pointer to avoid circular identity claims.

## Product goal and user constraints

ConvMem is intended to be an all-purpose memory project for AI, operating locally on Ryan's PC under his control. Existing coding/security use must not define its ceiling. Representative files span changing projects, documents, structured records, learning, procedures and media. The PC is in transit; this is an opportunity to improve direction, not a deadline to deploy.

The previous review sampled both user-named Drives to understand work patterns. Those files are examples of the eventual local corpus; connected-app restrictions do not constrain the PC design. Private evidence is in a separately saved companion, not this public repository packet. If you cannot access it, distinguish unverified corpus-fit claims from the technical questions you can assess.

## Reading order

1. [Field guide](review-pack-2026-10-31-convmem/FIELD-GUIDE.md) — map, authority, limits and review routes.
2. [Assessment](review-pack-2026-10-31-convmem/ASSESSMENT.md) — source findings and the initial recommendation, with public-safe examples.
3. [Research synthesis](review-pack-2026-10-31-convmem/RESEARCH.md) — readable Markdown copy of the preserved research report. [PDF](review-pack-2026-10-31-convmem/convmem-research.pdf) and [HTML](review-pack-2026-10-31-convmem/research.html) are alternate renderings.
4. [Claim register](review-pack-2026-10-31-convmem/CLAIMS.md) — consequential assertions, evidence and falsifiers.
5. Relevant source files at the assessed commit, then original public papers for claims that affect your verdict. The research bibliography is a starting point, not a substitute for verifying a paper's actual result.

Do not begin by reading every historical handoff or rerunning the full test suite. This is a strategy review, not certification of the current live corpus.

## Proposal under review

The author recommends keeping ConvMem's existing core while prioritizing:

1. A trustworthy source/runtime/recovery baseline before production changes; isolated work can proceed independently.
2. A bounded ordinary-document pilot with preserved original evidence, stable source revisions/locations, independent lexical plus semantic retrieval, bounded source expansion, basic explicit correction handling and no repeated expensive processing of unchanged content.
3. Current-state views derived from identified source revisions, with explicit uncertainty, correction relationships and learned/effective time distinctions.
4. Contrasting PDF/Thai and structured-table tasks before claiming broad format capability.
5. Small, evidence-linked lessons and a project-resumption context package through existing CLI/MCP interfaces.

Optional graph/database replacement, broad autonomous memory rewriting, all-file ingestion, and additional connector/publication work are deferred unless measured failures justify them. This is a proposed prioritization, not cancellation of existing work or a change to its authorization.

## Adversarial review specification

### Inputs and integration points

Inspect `adapters/detect.py`, `distill.py`, `query.py`, `ask.py`, `chunk_expand.py`, `mcp_server.py`, `evidence.py`, `ledger.py`, the source/generation modules and relevant current arc briefs as needed. Use the assessed commit to evaluate what the original assessment observed; report newer branch/main differences separately.

The prospective integration points are adapter detection and provenance, candidate retrieval, source expansion into synthesis, derived-state freshness, and incremental processing. No API/schema design has been approved or implemented by this packet.

### Questions worth trying to disprove

- Does the proposal address the user's broad goal, or quietly reduce it to document question-answering? What is missing for preferences, episodic experience, reusable procedures, ongoing tasks or media?
- Would a simpler local file-search baseline solve most demonstrated needs? Conversely, would retaining the current architecture entrench a fundamental limitation that warrants replacement?
- Are source preservation and derived views compatible with the actual current authority/recovery model? Identify any unsafe implied migration or duplicated source of truth.
- Does independent lexical retrieval address the observed failures, or are extraction, scoping, indexing coverage and synthesis more consequential bottlenecks?
- Could existing expansion, document ingestion or temporal mechanisms already solve a supposedly missing capability? Verify partial support rather than declaring features wholly absent.
- Are ordinary document indexing and incremental caching genuinely a bounded first slice, given publication, provenance, source removal and crash semantics?
- Does the temporal proposal handle old documents arriving late, future-effective changes, unknown dates, conflicting witnesses, and different sources owning different claims? Two timestamps alone do not resolve authority.
- Can stale derived briefs, OCR errors, AI-authored summaries or duplicated evidence be promoted into false certainty? What minimum invariants prevent this without adding another large governance subsystem?
- Is the three-domain pilot too homogeneous? Are PDF, Thai, structured calculation and procedural transfer staged sensibly?
- Is the evaluation fair and diagnostic? Challenge budget matching, oracle misuse, held-out leakage, small samples, LLM graders, missing ingestion costs and unsupported/pending cases disappearing from denominators.
- Are public research claims represented faithfully? Check category regressions, excluded unanswerable cases, synthetic datasets, model differences, and vendor/self-evaluation incentives. Search-result volume is not evidence strength.
- Is deferring Switchboard or graph work actually justified by marginal value and dependencies, rather than dislike of complexity or document length?

You can add stronger questions. A strategic preference is not a defect unless you connect it to the user's objective, evidence, expected cost or a concrete failure.

### Required output

Return a review with:

1. **Target:** delivery commit, manifest digest and assessed source commit; which private evidence, code and primary sources you actually inspected.
2. **Verdict:** `PASS_FOR_BOUNDED_PLANNING`, `REVISE_BEFORE_PLANNING`, or `INSUFFICIENT_EVIDENCE`. None means implementation/deployment approval.
3. **Findings:** stable ID, severity, claim/path, evidence, consequence, smallest useful correction, and verification needed. Separate blockers from improvements and open questions. A hypothesis must be labelled as such.
4. **Strongest alternative:** the best competing next move, its likely advantage, and a fair experiment that could make you choose it.
5. **Revised first slice:** a concrete deliverable, dependencies, exclusions and acceptance observations. Explain what should be removed from the author's proposal as well as what should be added.
6. **Evidence limits:** unavailable sources, historical-only runtime facts and remaining uncertainty. Do not silently turn an access limitation into a product flaw or a pass.

Suggested saved review path: `docs/inter-model/CLAUDE-2026-10-31-convmem-general-memory-adversarial-review.md` on a separate `docs/YYYY-MM-DD-...` review branch. Preserve the author's reviewed packet; record corrections in the review rather than editing it during assessment. Keep private URLs and personal details in a private companion. A chat verdict is also useful if the reviewer has no repository write capability.

## What not to do during this review

Do not implement the proposed mechanisms, ingest private files, start watchers, alter the preserved corpus, call paid generation services, replace embeddings, merge, create a PR or reopen gated experiments merely to review this packet. Do not construct live attacks. Conceptual counterexamples and isolated synthetic fixtures can support findings; any optional test must have inspected, bounded effects and be reported accurately.

The author previously attempted the migrated runtime's doctor check. It did not pass because local model access and workstation-specific configuration were unavailable here. This did not certify or diagnose the travelling PC. Do not make a fresh live-runtime pass a prerequisite for reviewing the documents.

## Acceptance of the review

- The verdict is tied to exact saved content, not a moving branch or conversation recollection.
- Important code/literature claims are challenged against source evidence.
- Recommendations respect local-PC scope and the broad memory goal.
- The review identifies a better next decision or experiment, not only a longer list of requirements.
- Unverified private-corpus claims and historical runtime observations remain visibly qualified.
- No prospective experiment is described as executed and no author self-review is called Claude Fable's independent review.

## Delivery and later PR description

The requested deliverable is this saved review packet. If Ryan later requests a PR, a suitable title is **“Preserve the general-memory assessment for adversarial review.”**

Suggested description: “This documentation packet preserves the October 31 ConvMem assessment and external research, and gives Claude Fable a bounded adversarial-review brief and claim register. It adds a field guide and integrity manifest so reviewers can distinguish code observations, historical runtime evidence and untested proposals. It changes no runtime behavior. Validation covers document links, packet hashes and public/private separation; no live retrieval evaluation was run.”

## Jargon TL;DR

| Term | Meaning |
|---|---|
| Packet | The saved assessment, research, navigation and review instructions in this delivery |
| Derived view | A brief, summary or extracted assertion computed from identified evidence rather than an independent authority |
| Learned/effective time | When the system recorded a claim versus when the claim applied in the world |
| Oracle evidence | Preselected correct passages used to diagnose reasoning; not a fair ordinary-search competitor |
| Switchboard | The existing optional OpenClaw-to-ConvMem integration effort; its status/permissions remain unchanged |
| Track A | Repository convention for ingesting the session transcript, distinct from saving this handoff |

**Handoff state:** assessment and research saved for review; Claude Fable's verdict remains pending.
