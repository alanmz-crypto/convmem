# ConvMem Dependability and Provenance Integrity
## Claude review handoff — 2026-08-15

### Review target

This handoff accompanies the planning package for ConvMem's dependability and
provenance-integrity arc.

- Branch: `plan/2026-08-15-dependability-provenance`
- Exact pushed revision: `75caa444a6274ff070b02483d8e3bbb22bb15b50`
- Package status: planning-only; no runtime or live-data changes
- Intended reviewer: Claude, for an independent architecture challenge

Review the package against the exact revision above. Do not assume that a
proposed module or migration already exists merely because the plan names it.

### What this arc is

This arc defines how ConvMem preserves and evaluates provenance integrity as
memory passes through ingestion, truncation, summarization, distillation,
embedding, storage, reconstruction, deduplication, export, and retrieval.

Its goal is conservative evidence preservation, not automatic truth scoring.
It must make provenance laundering and silent authority upgrades difficult to
express, while being explicit about what ConvMem cannot enforce downstream.

The arc keeps these dimensions separate:

- provenance integrity;
- factual truth;
- temporal validity and supersession;
- retrieval priority, including the existing `source_trust_tier()` heuristic;
- CG-2 serving-generation authority;
- downstream tool, code, git, or other action authority.

### How the plan originated

The plan began with the dependability literature handoff and addendum, not
with a request to redesign CG-2. The research connected ConvMem's existing
CG-1, R2b, Shadow, JudgeBench, and retrieval-freshness work to assurance
cases, memory poisoning, provenance laundering, lifecycle testing, temporal
validity, and multi-agent fault injection.

The decisive source was the full TMA-NM paper. Its relevant lesson was not
simply “add a source label.” A derived memory must not gain authority merely
because an agent summarized, embedded, distilled, or corroborated lower-trust
content. Its guarantees also depend on authenticated origin binding and an
action monitor, assumptions ConvMem does not currently satisfy.

The literature claims were then traced into the actual repository. The trace
found these concrete gaps:

- `ingest.py` renders bounded/truncated message views for generation;
- `distill.normalize_unit()` drops provenance information;
- inter-model indexing accepts caller-provided `source_type` and
  `author_model` values;
- exported units and canonical reconstruction omit the required provenance
  envelope;
- exact dedupe and semantic dedupe lacked a cross-provenance assertion rule;
- R2b proves capture authorization, not content provenance;
- Shadow observes mutations but cannot validate a writer's provenance logic;
- CG-1 durability can preserve poisoned content perfectly;
- no current production channel establishes authenticated origin identity.

The documents under `/home/lauer/Documents/Computing/` were initially
misnamed `convmem_cg2-*`. Their contents belonged to this broader arc, so they
were renamed `convmem_dependability-*`. CG-2 is now treated as a separate
serving-authority dependency rather than the name of this work.

### Normative contract to challenge

The central rule is:

```text
I(output) = meet(I(all completely bound dynamic inputs),
                 cap(producer/transformation))
```

with the ordered lattice:

```text
untrusted < agent < trusted
```

The intended consequences are:

- a verified exact, content-preserving copy may preserve input integrity only
  under an explicit tested preservation contract;
- an LLM summary, distillation, or rewrite is capped at `agent`;
- any untrusted or unknown contributor makes the derived result untrusted;
- incomplete ancestry is untrusted;
- a trusted implementation is not automatically a trusted semantic
  transformer;
- equivalence/deduplication does not merge independent provenance assertions;
- downstream action enforcement remains outside ConvMem unless a consuming
  harness mediates it.

The provenance envelope distinguishes the information supplier from the
current representation producer. It includes producer class and assurance,
root-origin evidence where applicable, input bindings, derivation kind,
transformer identity/version/recipe, ancestry completeness, policy version,
and a derived/cache-only effective-integrity value.

For normal ingest, a binding must identify both the source record and the
exact view consumed by the transformation: stable record locator, raw-record
hash, rendered/truncated input-view hash, selection parameters, and binding
version. “Complete ancestry” means every dynamic data input presented to the
supported transformation boundary is bound; it does not claim to enumerate
model weights or every causal influence on an LLM.

### Assertion identity and recursive verification

The final revision adds the lock-critical details:

- assertion IDs are content-independent, monitor-minted, atomically reserved,
  immutable, and commitment-bound;
- valid replay is idempotent and creates no new corroboration or authority;
- identical content alone is never identity;
- invalid ID/commitment replay cannot retain the supplied identity; retained
  content receives a fresh untrusted identity;
- parent ID/commitment edges are immutable and cannot be rebound to equivalent
  content;
- if any historical parent envelope, commitment, policy, recipe, binding, or
  ancestry link cannot be resolved and verified, recomputation returns
  `untrusted`;
- cycles, divergent envelopes, parent substitution, and commitment mismatch
  fail closed;
- VERIFY includes missing-ancestor and valid-looking-child negative controls.

These are the most important areas for Claude to challenge. In particular,
check whether the commitment construction is sufficiently canonical to make
“same assertion” and “new assertion” unambiguous across export, import,
reconstruction, and deduplication.

### Review history

The review sequence matters because the current package is the result of
several corrections:

1. An initial Sol-High draft was too broad, functioning as a general
   dependability umbrella before making the provenance substrate operational.
2. Kiro rejected that version because the invariant, envelope, exact input
   bindings, and dedupe rules were not concrete enough.
3. Sol-High narrowed the first slice and added the transformer-aware lattice,
   exact rendered-view bindings, assertion-preserving dedupe, and mandatory
   continuity checks.
4. Kiro and Copilot then identified two remaining lock issues: assertion-ID
   semantics and fail-closed handling of unavailable historical parents.
5. Sol-High corrected those issues and pushed the current revision.
6. Same-SHA Sol-High Kiro-role and Copilot-role reviews both returned PASS.

The final reviews confirmed that the package authorizes no runtime
implementation, live corpus/Chroma mutation, Shadow or R2b operation, CG-2
activation, downstream action enforcement, migration, cloud-policy change, or
external-configuration change.

### Current implementation boundary

This is an architecture package, not an implementation branch. The next
work is intentionally split into separate Ryan-authorized grants:

- P1: provenance policy, authoritative assertion identity/store boundary, and
  complete-boundary propagation;
- P2: ingest/provider payload binding, canonical unit/Chroma/export/
  reconstruction continuity, and legacy conservative handling;
- P3: provenance-aware dedupe, retrieval visibility, and downstream consumer
  contract surfaces.

Each P1/P2/P3 slice requires its own branch/worktree, PR, verification, and
review gate. No single “Stage 1” grant should authorize all three.

### Residual limitations

The plan explicitly does not claim:

- an authenticated production origin channel;
- factual correctness merely from provenance correctness;
- automatic poisoning detection;
- automatic trust elevation or Sybil-resistant corroboration;
- end-to-end TMA-NM action guarantees;
- ConvMem control over Codex/Cursor tool, code, git, or external actions;
- live Shadow, R2b, CG-1, or CG-2 activation.

Implementation evidence, historical policy/recipe retention, and assertion
storage-pressure behavior remain pending.

### Questions for Claude

Please return a verdict tied to the exact revision, with blocking and
nonblocking findings separated. Focus on:

1. Can assertion identity and commitment canonicalization survive all
   reconstruction, re-import, replay, and dedupe paths without accidental
   aliasing or authority creation?
2. Does recursive recomputation truly fail closed whenever any historical
   dependency is unavailable, unverifiable, cyclic, substituted, or governed
   by an unavailable policy/recipe version?
3. Is “complete ancestry” achievable and testable at each named transformation
   boundary without overclaiming universal causal completeness?
4. Are trusted exact-copy exceptions narrow enough to prevent deterministic but
   semantically lossy selectors from preserving authority?
5. Does the plan prevent low-trust duplicates from downgrading independent
   trusted assertions and prevent trusted duplicates from elevating untrusted
   assertions?
6. Are provenance integrity, temporal validity, retrieval priority, CG-2
   serving authority, factual truth, and downstream action authority kept
   independent throughout the execution and verification plan?
7. Are P1, P2, and P3 sufficiently isolated for bounded implementation, or is
   any slice still too broad?
8. What material architecture defect remains despite the Sol-High/Kiro/Copilot
   PASS reviews?

### Package contents

The companion zip contains the four planning documents from the exact final
revision plus this handoff. The GitHub repository zip may contain surrounding
repository context; this handoff is the orientation and challenge brief for
the provenance arc specifically.

The primary document to open first is:

`docs/plans/ARCHITECTURE-dependability-provenance.md`

