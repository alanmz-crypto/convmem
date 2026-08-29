# Experiment Brief: Minimal Portland ConvMem Baseline

**Arc: none (ad-hoc — diagnostic experiment design)**
**Type:** experiment design only. Not implementation. No production state changed.
**Author lane:** Kiro (review-required; design/brief only)
**Branch:** `plan/2026-08-29-portland-baseline-experiment`

## Purpose

Answer one question with the smallest controlled experiment possible:

> Does ConvMem provide useful persistent memory that a fresh agent could
> **not** recover through its ordinary context, GitHub/handoff artifacts, or
> other standard agent capabilities?

Test domain: the real subject **moving to Portland**. Bounded, varied, small.

This is a *diagnostic* — it tests whether a missing capability exists. It does
**not** design a solution and does **not** start a new retrieval architecture
or evaluation program. PR #247 (relocation retrieval scope corrective) is
treated as the current baseline behavior, not something to rebuild.


---

## 1. Primary hypothesis (H1)

A fresh Agent B operating in its **real, ordinary environment plus ConvMem
(C1)** recovers Portland facts — especially paraphrased, vague, synthesis, and
current-vs-stale queries — either more successfully or with materially less
effort than the **same agent in the same ordinary environment without ConvMem
(C0)**.

The competing baseline is deliberately strong: C0 keeps the agent's normal
filesystem/search, GitHub access, agent-transcript directories, and other native
recovery paths. If those ordinary paths already recover the facts, that counts
**for** the baseline, not against it. "Materially less effort" is made mechanical
in §8 via a pre-declared, equal effort budget (tool-call/search-action count) —
not judged retrospectively.

## 2. Null / baseline hypothesis (H0)

The natural agent (C0) recovers the same Portland facts about as successfully,
and within about the same effort budget, **without** ConvMem — because the facts
are already reachable through ordinary means: filesystem search, GitHub/handoff
artifacts, indexed or on-disk agent transcripts, model-native context, or
generic search. If H0 holds, ConvMem adds no unique recovery value **for this
domain** over the agent's real existing environment. Under this design, C0
finding a fact by ordinary search is **legitimate baseline success**, not
contamination.

## 3. Exact experimental conditions

Two conditions, **same question set**, paired per question. The substantive
environment is held constant; **ConvMem is the only added capability.**

| Condition | Agent B environment | ConvMem access |
|-----------|--------------------|----------------|
| **C0 — Natural agent baseline** | Fresh session; **no** pasted Agent-A transcript and **no** answer-bearing experiment handoff. Otherwise **retains all ordinary capabilities**: normal tools, filesystem + `grep`/search, GitHub access, agent-transcript directories (`~/.codex`, `~/.cursor`, `~/.kiro`, …), and pre-existing artifacts. | **Disabled** (ConvMem tools removed from the manifest) |
| **C1 — Natural baseline + ConvMem** | **Identical** ordinary environment as C0, same fresh-session and same experiment-leakage controls | **Enabled** (normal ConvMem integration: `search` / `ask` / `ask --trace`) |

**What is controlled vs. what is preserved:**
- **Preserved in both:** every ordinary recovery path (filesystem search,
  GitHub, transcript directories, native context). These are the *competing
  baseline*, not contamination. If C0 independently finds a Portland fact by
  searching a Kiro/Cursor/Crush transcript, GitHub, or another ordinary
  artifact, **that is a legitimate C0 success** — record its source path (§8).
- **Excluded from both (experiment-created leakage only):** pasting the Agent-A
  transcript into Agent B's prompt, and any special handoff/brief that contains
  the K1–K10 answer values. See §6.
- **Never done:** specially teaching Agent B where the answers are.

The **only** intended difference between C0 and C1 is ConvMem availability
(model, prompt scaffolding, question wording, and ordinary tools held constant).

Run order: run **C0 first** for every question, then C1. This prevents C1
retrieval output from framing C0 — and §6 additionally freezes the C1 corpus so
C0's own session can never become a C1 source.


## 4. Knowledge items to seed (Phase A)

Agent A does **real** Portland relocation work and, through that work, learns a
small deliberately-varied set. Target ~10 items covering every retrieval
difficulty and every failure-taxonomy label (§9). Each item is captured into
ConvMem through **normal supported capture** (see §10) and carries provenance.

| # | Kind | Item (illustrative — Agent A produces the real values) | Difficulty exercised |
|---|------|--------------------------------------------------------|----------------------|
| K1 | Preference | Prefers a walkable neighborhood over car-dependent suburb | direct recall |
| K2 | Constraint | Budget ceiling for rent (a specific number) | direct + paraphrase |
| K3 | Neighborhood observation | Notes about a specific district (noise, transit, feel) | vague recall |
| K4 | Rental requirement | Must allow a large dog; needs a home office | synthesis (K1+K2+K4) |
| K5 | Rejected option | A specific listing/area rejected | rejected-option recall |
| K6 | Reason for rejection | *Why* K5 was rejected (e.g. flood risk, commute) | reason recall + provenance |
| K7 | Unresolved question | Open question with no answer yet (e.g. school district TBD) | unresolved recall |
| K8 | Changed decision (v1) | An early decision later reversed | temporal (stale) |
| K9 | Changed decision (v2, supersedes K8) | The current decision replacing K8 | current-vs-stale |
| K10 | Cross-domain-adjacent fact | A fact captured under a *non*-relocation domain (e.g. `finance` or `general`) that is nonetheless relevant | classification + cross-domain judgment |

Rules for the seed set:
- Small and varied beats large. Do **not** manufacture a big benchmark.
- K8→K9 must go through ConvMem's real **supersession/conflict** path so the
  temporal query in §7 has something genuine to resolve.
- K10 is deliberately mis/under-classified to exercise the classification and
  cross-domain-judgment labels — **without** building an auto-widening policy.
- Record exact provenance for every item: which Agent-A source unit (session
  transcript line / `record` ledger id) each fact originated from.


## 5. Fresh-agent isolation procedure (Phase B)

Agent B starts fresh with **no** pasted Agent-A transcript and **no**
answer-bearing handoff — but keeps its ordinary environment (§3). Setup:

1. New agent session, new session id. Do not paste or reference Agent A's
   transcript in the prompt. (The transcript may still exist on disk as an
   ordinary artifact the agent *could* find by its own search — that is a
   legitimate C0 path, not a plant.)
2. No experiment handoff/brief containing substantive Portland answers is placed
   where Agent B would read it. A *coordination* handoff (naming the experiment,
   branch, question count) is allowed **only** with zero Portland answer content.
3. **Identical neutral task prompt in both conditions**, containing no answers
   and no coaching:

   > "Answer these Portland-relocation questions using the tools normally
   >  available to you."

4. **Do not cue scope.** Do not instruct Agent B to `convmem scope set
   relocation` or to widen. If the *normal installed* ConvMem integration/rules
   already instruct the agent to query or scope memory, retain those in C1
   unchanged — they are part of the ConvMem system under evaluation — but add no
   experiment-specific coaching. Then **observe** (feeds the §9 automatic-subject
   and cross-domain labels): whether C1 invokes ConvMem at all; whether it
   chooses an appropriate scope; whether it widens when appropriate; and whether
   it returns to scope afterward.
5. In **C0**, ConvMem tools are removed from the tool manifest entirely (not
   merely "asked not to use them"). All other ordinary tools remain.

## 6. Experiment-created leakage exclusion + corpus freeze

Two distinct isolation jobs. **Do not conflate them.**

### 6a. Exclude experiment-created leakage (not natural artifacts)

Ordinary Agent-A artifacts (its on-disk transcript, any pre-existing repo doc it
naturally produced) are **legitimate C0 recovery paths** — leave them. What must
be excluded is leakage *manufactured by this experiment*:

**Prohibited (experiment-created):**
- Pasting the Agent-A transcript or the K1–K10 answer values into Agent B's prompt.
- Any experiment handoff/brief/README that lists the answer values.
- Putting K1–K10 answers into *this* brief or into `docs/inter-model/`/`LATEST.md`
  specifically to coordinate the experiment.

**Verification (run before Phase B):**
- [ ] `grep -ri "portland\|<seed keywords>"` over files **added by this arc**
      (this brief, the golden fixture, any coordination handoff) returns no
      answer values. This brief uses *illustrative placeholders*, not the real
      seeded values, so it is safe to commit.
- [ ] Confirm Agent B's prompt contains no Agent-A transcript paste and no answers.
- [ ] For C0: confirm ConvMem tools are absent from the tool manifest; confirm
      all other ordinary tools are present (so C0 is a real baseline, not a
      crippled one).

Naturally-occurring artifacts are explicitly **allowed** in C0. Their use is
scored as a baseline success with its source class recorded (§8), never flagged
as contamination.

### 6b. Freeze the ConvMem corpus against C0 → C1 contamination

ConvMem ingests agent transcripts, so **C0's own session could become a new C1
source** unless prevented. Bind this procedure before execution:

1. Agent A produces K1–K10.
2. Capture/index the intended Agent-A material into ConvMem (§10).
3. **Freeze** the exact ConvMem corpus/store state to be used for C1 — record a
   frozen marker: Chroma unit count + newest `ledger_id`/timestamp, or an
   isolated copy of the store directory. This frozen snapshot is the *only* thing
   C1 may retrieve from.
4. Run **C0**.
5. Ensure C0's transcript, guesses, questions, and outputs **cannot enter** the
   frozen C1 corpus: run C0 with ConvMem watch/index disabled or pointed away
   from the frozen store, or run C1 against an isolated copy taken at step 3.
6. Run **C1** against the pre-C0 frozen corpus/store state only.

**Critical invariant:**
> C1 may retrieve Agent-A knowledge, but **never** knowledge generated by C0 or
> by the operator after the freeze.

**Mechanical verification of the invariant (run after C1):**
- [ ] The C1 store's unit count / newest-id marker equals the step-3 frozen
      marker (no new units ingested between freeze and C1).
- [ ] For every C1 recovery, the `ask --trace` provenance chain resolves to a
      source unit whose id/timestamp predates the freeze (i.e. an Agent-A unit,
      never a C0-session unit).
- [ ] Grep the frozen store for any C0 session-id / C0 transcript path → zero hits.


## 7. Question set

One question per retrieval difficulty, each mapped to expected fact(s) and the
label(s) it exercises. Wording is fixed and identical across C0 and C1.

| Q | Type | Question (fixed wording) | Expected fact(s) | Labels |
|---|------|--------------------------|------------------|--------|
| Q1 | Direct factual | "What is the rent budget ceiling for the Portland move?" | K2 | retrieval quality |
| Q2 | Paraphrased | "How much can we afford for housing there each month?" | K2 | retrieval (paraphrase) |
| Q3 | Vague / underspecified | "What did we think about that one neighborhood?" | K3 | retrieval (vague) |
| Q4 | Synthesis | "Given the must-haves, what kind of place should we look for?" | K1+K2+K4 | retrieval + capture usefulness |
| Q5 | Current-vs-stale | "What's the current decision on X?" (X = subject of K8/K9) | **K9**, not K8 | temporal quality |
| Q6 | Rejected + reason | "Which option did we rule out and why?" | K5+K6 | retrieval + provenance |
| Q7 | Unresolved | "What's still open / undecided about the move?" | K7 | capture usefulness |
| Q8 | Cross-domain | "Is there anything relevant we filed elsewhere?" | K10 | classification + cross-domain judgment |

Q5 is the temporal probe: success requires K9 (current) to outrank/replace K8
(stale). Q8 is the classification/cross-domain probe: whether K10 is findable
under the relocation scope, and whether widening was required to reach it.

## 8. Metrics / scoring

Because C0 recovers via heterogeneous ordinary paths (filesystem, GitHub,
transcript search, native context) there is **no common ranked ConvMem result
list** from which a C0 MRR could be computed. So the **primary** paired outcome
is system-level, and ranked-retrieval metrics are demoted to C1-only
diagnostics.

### 8a. Primary paired system-value metrics (both conditions, same questions)

Declare a **fixed, equal effort budget before running** (e.g. *N tool
calls / search actions per question* — set the exact N in the run config, not
retrospectively). Per question, per condition, record mechanically:

- **Recovered?** expected fact correctly recovered within the budget — yes/no.
- **Source class used** (the path that produced the correct answer):
  `native/current-context` · `transcript-search` · `github/handoff/artifact` ·
  `other-ordinary` · `convmem`.
- **Effort to recovery:** number of tool calls / search actions before the
  correct fact appeared.
- **Failed-within-budget:** yes/no (miss once the budget is exhausted).

Paired readout (C1 vs C0 on the same questions):
> Δrecovered (count C1 − C0) and Δeffort (median actions-to-recovery C0 − C1),
> plus the source-class breakdown.

**Strongest ConvMem-value result:**
> C1 correctly recovers Kx within the budget via a ConvMem provenance chain,
> while C0 either fails within the same budget or needs measurably more ordinary
> search effort.

**Symmetric honesty:** if C0 readily finds the same fact by ordinary artifact /
transcript / GitHub search within budget, that is **evidence against unique
ConvMem value** — reported as such, never relabeled contamination.

### 8b. C1-only ConvMem retrieval diagnostics (secondary)

For C1 only, retain the existing tooling to *explain ConvMem's retrieval
behavior* (why a fact was hit or missed), not as the primary pass/fail:

- Encode Q1–Q8 as a golden fixture in the `golden_queries.jsonl` schema
  (`query`, `acceptable_ids`, `top_k`, `note`), `acceptable_ids` = seeded
  Agent-A source-unit ids.
- Compute **P@1 / Hit@k / Recall@k / MRR** via `eval_corpus/metrics.py` +
  `scripts/eval-retrieval.py`.
- Capture `ask --trace` provenance per question.

These localize any C1 miss to a §9 label (ranking vs capture vs classification
vs temporal vs provenance). They do **not** enter the paired C0/C1 verdict,
since C0 has no comparable ranked list.


## 9. Failure taxonomy (diagnostic labels, not new projects)

When a C1 question misses, classify with the existing audit categories. These
are labels applied to observed misses — not eight workstreams.

| Label | Question it answers | Signal to look for |
|-------|--------------------|--------------------|
| **Retrieval quality** | Did paraphrase / vague / crowded retrieval fail? | Correct unit exists in corpus but ranks below k (see trace candidates stage) |
| **Capture usefulness** | Was the fact never captured / never distilled? | No unit for the fact exists at all |
| **Classification** | Stored under wrong domain or `general`? | Unit exists but under a domain the scoped query excludes |
| **Automatic subject behavior** | Did the agent fail to recognize relocation was the active scope? | Agent queried unscoped / wrong scope; K10-style miss |
| **Cross-domain judgment** | Was the fact in another domain, needing widening? | Miss under scope, hit under `--cross-domain` |
| **Temporal quality** | Did a stale option outrank current state? | Q5 returns K8 above K9 |
| **Provenance / confidence** | Can the answer be tied to a source; are conflicts visible? | `ask --trace` lacks a source chain, or K8/K9 conflict not surfaced |

Do **not** build an auto-widening policy to fix a cross-domain miss during this
experiment — record it as a label and stop.

## 10. Minimal existing ConvMem machinery reused

Confirmed present on disk (inspected 2026-08-29):

- **Capture / seeding:** `convmem index --file` (single-file ingest, `--force`,
  `--supersede`) and `convmem record` / `record --approve-last` for durable
  facts. Normal supported capture — no new capture path.
- **Scoped retrieval (PR #247):** `convmem scope set|clear|show`; `search` /
  `ask` flags `--domain`, `--site`, `--cross-domain`. Strict-scope-is-baseline;
  explicit (not inferred) widening. This is C1's retrieval surface.
- **Retrieval trace:** `convmem ask --trace` → `convmem.ask.trace.v1`
  (five-stage: candidates → evidence rerank → dedupe → recent injection → final
  context; citations carry `evidence_status` + `ledger_id`). Supplies the
  ConvMem source-class attribution for §8a (proving a C1 recovery came *through
  ConvMem*, tied to a pre-freeze Agent-A unit) and the §9 provenance label.
- **Scoring:** `eval_corpus/metrics.py` (`p_at_1`, `hit_at_k`, `recall_at_k`,
  `recall_at_k_complete`, `mrr`, `first_relevant_rank`) and
  `scripts/eval-retrieval.py` (runs a `golden_queries.jsonl` fixture through
  `query_units`, emits P@1 / P@k / MRR / recall@k JSON).
- **Paired comparison:** `eval_corpus/paired_stats.py` may support the C1-only
  ranked-metric summary; the **primary** C0/C1 paired verdict is the system-value
  table in §8a (recovered? / source class / effort), scored per the run config.
- **Fixture schema:** `tests/fixtures/golden_queries.jsonl` (`query`,
  `acceptable_ids`, `top_k`, `note`) — Portland questions encode as one new
  fixture in this exact schema.
- **Supersession/conflict:** existing ledger supersession path (K8→K9) — reused,
  not rebuilt.

Reuse does **not** require running the unfinished JudgeBench or embedding-model
eval arcs. No concrete dependency on them was found (see §12).


## 11. Concrete dependencies

None that block execution. Specifically checked:

- **JudgeBench semantic calibration** (`STATUS-judgebench.md`, stale >14d, 2
  incomplete): a *judging* program for answer quality. This experiment scores
  mechanically (id-level Hit/MRR + fact-present), so JudgeBench is **not**
  prerequisite.
- **Shadow Ledger Phase 0** (`STATUS-shadow-ledger-phase0.md`, stale, 5
  incomplete): delta-capture plumbing; disabled by default (doctor:
  `shadow_ledger: disabled`). Not on the retrieval path this experiment uses.
- **Embedding-model eval** (`EXECUTION-embedding-model-eval.md`): compares embed
  models; irrelevant to a single-model within-corpus recovery test.

The only hard requirements are the already-landed pieces in §10.

## 12. Stop / go criteria

**GO to run** when:
- [ ] Seed set K1–K10 defined with real Agent-A values + provenance ids.
- [ ] Experiment-created-leakage check (§6a) passes: files added by this arc
      contain no answer values; Agent B prompt has no transcript paste/answers.
- [ ] ConvMem corpus **frozen** with a recorded marker (§6b step 3).
- [ ] Fixed effort budget N declared in the run config (§8a).
- [ ] Portland golden fixture written in `golden_queries.jsonl` schema (C1 diagnostic).
- [ ] C0 manifest confirmed ConvMem-free **with all other ordinary tools present**;
      C1 confirmed ConvMem-enabled on the frozen corpus.

**STOP conditions:**
- If results show H1 (ConvMem recovers within budget what the natural baseline
  cannot, or with materially less effort): **stop the experiment as designed.**
  Report Δrecovered, Δeffort, source-class breakdown, and per-label C1 misses.
- If the result exposes a **new architectural problem** (automatic contextual
  inference, cross-domain policy, temporal-state reconstruction, capture-quality
  control): **STOP before designing any solution** and first identify relevant
  literature / prior art. Research precedes solution design — not this diagnostic.
- If H0 holds (the natural agent matches ConvMem within budget): report that
  ConvMem adds no unique value *for this domain* over the agent's real existing
  environment — this is a legitimate result, not contamination.

---

## Answers to the required questions

**Can this experiment be run now?**
Yes. Every piece it depends on is already on `main`: capture via
`index`/`record`, ConvMem retrieval + `ask --trace` (PR #247), and the C1-only
ranked scoring in `eval_corpus/metrics.py` + `scripts/eval-retrieval.py`. The
primary system-value metrics (recovered? / source class / effort) are plain
mechanical observation of the two runs. The corpus freeze uses existing store
state + a recorded marker. Remaining work is experiment setup, not new
architecture.

**Is any unfinished existing ConvMem plan genuinely prerequisite?**
No. JudgeBench, Shadow Ledger Phase 0, and embedding-model eval were each
checked and are not on this experiment's path. No concrete dependency found.

**Is any additional literature research required before running it?**
No — not to *run* the diagnostic. Literature research is required only *after*,
and only *if*, the result exposes a new architectural problem (per §12 STOP).

**What is the smallest implementation / setup work needed to execute it?**
1. Agent A performs real Portland work; capture K1–K10 via normal `index`/
   `record`, recording provenance ids. (~1 short session)
2. Author the K8→K9 supersession through the existing ledger path, then **freeze
   the ConvMem corpus** and record the frozen marker (§6b).
3. Write one Portland `golden_queries.jsonl` fixture (Q1–Q8 → seeded unit ids)
   for the C1-only ranked diagnostics.
4. Prepare two runnable Agent-B harness configs with the **same neutral prompt
   and no scope cueing**: C0 (ConvMem tools removed, all other ordinary tools
   present, index disabled/redirected so C0 cannot write the frozen corpus) and
   C1 (ConvMem enabled against the frozen corpus). Declare the fixed effort
   budget N. Run C0 then C1 on the fixed Q set.
5. Score the §8a system-value table (recovered? / source class / effort) as the
   primary paired result; run `scripts/eval-retrieval.py` + capture C1
   `ask --trace` as secondary C1 diagnostics; verify the §6b corpus-freeze
   invariant; fill the §9 label table for any C1 miss.

No new evaluator, no new retrieval code, no schema change.

---

## TL;DR

- Smallest paired experiment: **C0 (natural agent — no ConvMem, but keeps its
  ordinary filesystem/GitHub/transcript search)** vs **C1 (same natural agent +
  ConvMem)** on one fixed 8-question set over ~10 varied seeded Portland facts.
- Ordinary recovery paths are the **competing baseline**, not contamination: if
  C0 finds a fact by ordinary search, that is legitimate baseline success and
  counts against unique ConvMem value.
- Primary metric is **system-level within a pre-declared effort budget**:
  recovered? / source class / actions-to-recovery — not a paired MRR (C0 has no
  ranked ConvMem list). P@1/Hit@k/MRR + `ask --trace` are retained as **C1-only**
  diagnostics.
- Two isolation jobs: exclude only *experiment-created* leakage (transcript
  paste / answer-bearing handoff), and **freeze the ConvMem corpus** so C0's own
  session can never become a C1 source (mechanically verified via the frozen
  marker + pre-freeze provenance timestamps).
- No scope cueing: identical neutral prompt in both conditions; whether C1
  invokes/scopes/widens ConvMem is *observed*, not instructed.
- Reuses only landed machinery (PR #247 scope + trace, `eval_corpus/metrics.py`,
  `eval-retrieval.py`, `golden_queries.jsonl`, supersession). No dependency on
  JudgeBench / Shadow Ledger / embedding eval. **Runnable now**, setup only.

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| C0 / C1 | Natural-agent baseline (no ConvMem, keeps ordinary search/GitHub/transcripts) / same natural agent + ConvMem |
| Natural baseline | C0 with all ordinary recovery paths intact — the competing mechanism, not contamination |
| Source class | Which path produced a correct answer: native context / transcript-search / github-artifact / other-ordinary / convmem |
| Effort budget | Pre-declared fixed cap of tool calls/search actions per question, so "materially harder" is mechanical, not retrospective |
| Corpus freeze | Snapshotting the ConvMem store state (marker: unit count + newest id/timestamp) before C0 so C0's session can never become a C1 source |
| Experiment-created leakage | Answer values injected by the experiment (transcript paste, answer-bearing handoff) — excluded; distinct from naturally-occurring Agent-A artifacts |
| Agent A / Agent B | Knowledge-creating agent (Phase A) / fresh recovery agent (Phase B) |
| K1–K10 | The seeded Portland knowledge items (see §4) |
| Q1–Q8 | The fixed recovery question set (see §7) |
| P@1 | Precision at 1 — correct source unit is the top retrieval hit |
| Hit@k / Recall@k | A correct unit appears within top-k results |
| MRR | Mean reciprocal rank — rank quality of the first correct hit |
| PR #247 | Landed relocation retrieval scope corrective: strict scope, non-sticky explicit widening (the C1 retrieval baseline) |
| scope set/clear/show | ConvMem session read-scope default for retrieval (from PR #247) |
| ask --trace | `convmem.ask.trace.v1` five-stage retrieval trace with citation provenance (`evidence_status`, `ledger_id`) |
| Track A | Indexing the session chat transcript into ConvMem |
| Supersession | Ledger mechanic where a newer decision (K9) replaces/tombstones a stale one (K8) |
| Artifact recovery | Finding a fact via GitHub/handoff/transcript search rather than ConvMem — here a **legitimate C0 baseline path**, not contamination; the experiment measures whether ConvMem beats it |
| HITL | Human-in-the-loop (Ryan authorizes/merges) |
