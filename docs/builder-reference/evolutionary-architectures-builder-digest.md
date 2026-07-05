# Ford, Parsons, Kua, Sadalage — builder digest (convmem)

**Source:** *Building Evolutionary Architectures*, 2nd ed. — fitness-function chapters only (Ch. 2–3, ~pp. 23–76). Skip the incremental-change-in-large-orgs material (teams, services, organizational coupling) — this project doesn't have those problems.

**Read when:** touching `scripts/verify-builder-reference.sh`, `scripts/validate-builder-reference-surfaces.sh`, designing any new automated check on the builder-reference canon, or when two scripts disagree on a threshold and nobody can explain why.

**Scope note:** This is a slice, not a full digest — written to resolve the specific threshold-mismatch problem and provide vocabulary for future fitness-function design in this repo. It does not stand alone as a new architectural tier.

## Principles

- **A fitness function is any automated mechanism that objectively measures how
  close a system is to an architectural goal.** The word "objective" matters —
  two mechanisms measuring the same property should converge on the same verdict
  for the same input. If they don't, at least one of them isn't actually
  measuring the stated goal; it's measuring something else and mislabeling it.

- **Fitness functions have a type, and the type determines the correct
  threshold — not intuition.** Picking a round number without stating what bad
  outcome it prevents is decoration, not engineering.

- **Multiple fitness functions measuring the same dimension must be reconciled
  into a single source of truth for that dimension, or explicitly declared to
  measure different things.** The failure mode isn't "having two scripts" — it's
  having two scripts that both claim to answer "is this digest done" without
  agreeing on what "done" means.

- **Thresholds should be derived from what the fitness function is actually
  protecting against.** A threshold exists to prevent a specific bad outcome. If
  nobody can state the outcome a 1,500-word gate prevents versus the outcome a
  2,500-word gate prevents, the numbers are decoration, not fitness functions.

## Taxonomy (the distinctions that matter here)

### Atomic vs. holistic

An **atomic** fitness function tests one property in isolation (e.g., "is this
file present," "is the sha256 correct"). A **holistic** fitness function tests
an emergent property across several atomic checks (e.g., "is this digest ready
to ship," "is this surface correctly configured").

The word-count check is being treated as atomic, but it's actually a proxy for a
holistic judgment — "is this digest complete enough." When two scripts answer
that holistic question with different atomic cutoffs, neither one is wrong in
isolation; the system is wrong because it has two uncoordinated answers to one
question.

### Triggered vs. continual

A **triggered** fitness function runs on demand (a script someone runs by hand
or an agent invokes before a deploy). A **continual** one runs automatically on
every relevant change (CI, a pre-commit hook, a file-system watcher).

Both convmem scripts are triggered today. That's appropriate for the current
workflow, but it means neither one is authoritative by default — whichever one a
person happens to run becomes the verdict for that session. This is exactly how
a mismatch goes unnoticed: the two scripts never run in the same context, so
their disagreement is invisible unless someone reads both scripts side by side.

### Static vs. dynamic thresholds

A **static** threshold is a hardcoded number (≥1500 words). A **dynamic**
threshold adapts to context (e.g., "above the 25th percentile of existing
digests," or "more words than the previous version"). Static is simpler and
easier to reason about. Dynamic is appropriate when the population changes
frequently and the meaning of "good enough" shifts with it.

Convmem's word-count checks are correctly static — the population of digests is
small and curated, and the meaning of "shippable" doesn't drift with each new
addition.

### Fitness-function drift

The book names this failure mode explicitly: as a system evolves, fitness
functions that were once aligned can drift apart because they were never
connected to a shared definition of what they're protecting. The symptom is two
checks disagreeing on the same property without anyone noticing until someone
reads both.

The remedy is ownership: each measurable property has exactly one authoritative
fitness function. Other scripts may report on that property for informational
purposes, but only one script's exit code gates the workflow.

## Applying this to convmem

### The two scripts are not redundant

Read closely, they check different scopes:

| Script | What it checks | Type |
|--------|---------------|------|
| `verify-builder-reference.sh` | Repo state + deploy state: file existence, surface deployment, sha256 match for Crush copies. Word count is one check among several. | Holistic ship gate |
| `validate-builder-reference-surfaces.sh` | Per-surface config depth: is each agent surface correctly wired, and is the digest substance deep enough to be useful. | Holistic maturity signal |

Under the book's taxonomy, these are two different fitness functions that happen
to share one atomic check (word count) without agreeing on what threshold that
check should enforce for their respective purposes. The bug was never "which
number is right" — it was "these two scripts were never designed to agree, and
nobody decided which one owns the word-count property."

### Resolution (already applied)

The reconciliation follows the book's prescription:

1. **`verify-builder-reference.sh` owns the word-count ship gate.** It's the
   presence/deploy-state script. Its threshold: WARN < 1500, PASS ≥ 1500. This
   is the atomic, triggered check that decides "is this digest allowed to
   deploy."

2. **`validate-builder-reference-surfaces.sh` uses the same PASS threshold
   (≥1500) as the ship gate**, plus an aspirational WARN band (1500–2499) that
   signals "shippable but thin." The ≥2500 target remains visible as the ideal
   band, not a contradicting gate.

3. **Each threshold is stated with its rationale in the script header:**
   - ≥1500 exists because that's where a digest stops being a stub (below this,
     the principles section alone can't cover a chapter's worth of material).
   - ≥2500 exists because that's where a digest has enough chapter coverage to
     be cited confidently across multiple change types. The most-cited digests
     (Ousterhout, Manning, Zeller) all sit at 2,300–2,900 words.

### When to add a new fitness function

Before adding a new automated check to this repo, answer three questions from
the book's framework:

1. **What specific bad outcome does this check prevent?** If you can't name the
   outcome, you don't have a fitness function — you have a lint rule looking for
   a home.

2. **Is this atomic or holistic?** If holistic, which atomic checks compose it?
   If atomic, which holistic function does it feed into? Orphaned atomic checks
   are how threshold drift starts.

3. **Who owns this check?** Exactly one script should gate a workflow on this
   property. Other scripts may report it, but only one exit code matters.

## convmem Hooks

- **`convmem doctor` is a holistic fitness function.** It composes several
  atomic checks (Ollama reachable, Chroma populated, index drift within
  bounds, MCP registered). Each atomic check has a clear bad outcome it
  prevents. The holistic verdict is "can this agent session proceed safely."

- **`verify-builder-reference.sh` owns the word-count ship gate.** Do not add
  word-count exit-code logic to other scripts without explicitly documenting
  which one is authoritative.

- **Threshold rationale belongs in the script header, not in external docs.**
  The person reading the script at 2 AM should not have to find a separate
  document to understand why the number is what it is.

- **Fitness-function drift is a known failure mode.** When adding a new
  script that checks a property already checked elsewhere, search for existing
  checks first (`grep -r "wc -w\|word_count" scripts/`). If you find one,
  either reuse it or explicitly document why yours measures something different.

- **The golden-query workflow (Manning digest) is a fitness function.** It's
  atomic (one query, one expected result), triggered (run manually), and its
  threshold is binary (PASS/FAIL). Name it as such when discussing it.

- **The synthesis gate in `convmem doctor` is a fitness function.** It's
  continual (checked every session), atomic (empty-buffer failure count in 7
  days), with a static threshold (>=3 triggers investigation). Partial
  synthesis (`synthesis_interrupted`) is observable but not gate-counted —
  P1c Phase 1 shipped 2026-07-05.

## Anti-patterns for Agents

- **Do not add a threshold without stating what it protects against.** "Seems
  like a good number" is not a rationale. If the rationale is missing, the
  threshold will drift — and the drift will be invisible because nobody
  remembers what the number was supposed to prevent.

- **Do not let two scripts gate on the same property with different numbers.**
  One of them is wrong, or they're measuring different things. Either reconcile
  them or rename them so the difference is explicit.

- **Do not make fitness functions continual without a reason.** Triggered checks
  are simpler and cheaper. Move to continual only when triggered checks have
  provably missed a regression (i.e., a bad state persisted between manual
  runs long enough to cause damage).

- **Do not conflate "informational reporting" with "gating."** A script that
  prints a WARN but always exits 0 is a report. A script that exits 1 on a
  condition is a gate. These are different tools. Mixing them in one script
  without clear documentation is how threshold drift starts.

- **Do not create holistic fitness functions that can't be decomposed.** If a
  check fails and you can't tell which atomic property caused the failure,
  the holistic function is too coarse. Break it down.

- **Do not assume "more checks = safer."** Each fitness function is maintenance
  surface area. An unmaintained check that silently passes on stale data is
  worse than no check at all — it provides false confidence.

## Related digests

- **Zeller** — verification workflow: a fitness function that fails is a bug
  report; apply the reproduce → isolate → fix → verify cycle to threshold
  failures the same way you would to code failures.
- **Ousterhout** — protecting module depth over time: fitness functions are the
  mechanism that ensures deep modules stay deep as the codebase evolves. A
  threshold that drifts is a module boundary eroding.
- **Hard Parts** — the trade-off worksheet for "should this check exist" is the
  same shape as "should this service be split": what does it cost, what does
  it protect, and is the protection worth the maintenance.
