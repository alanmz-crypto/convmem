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

A fresh Agent B, operating in its normal environment **plus ConvMem**, recovers
Portland facts — especially paraphrased, vague, synthesis, and current-vs-stale
queries — that it **cannot** recover, or can recover only materially harder, in
the same environment **without ConvMem**.

"Materially harder" is made mechanical in §8 (lower Hit@k / MRR, or requires
manual artifact spelunking the baseline agent would not perform unprompted).

## 2. Null / baseline hypothesis (H0)

Agent B recovers the same Portland facts equally well without ConvMem, because
the facts are already reachable through ordinary context: repo docs, handoffs,
indexed chat transcripts, model-native memory, or generic web/search. If H0
holds, ConvMem adds no unique recovery value **for this domain** and the
observed "shared memory" is artifact recovery, not ConvMem recovery.

## 3. Exact experimental conditions

Two conditions, **same question set**, paired per question.

| Condition | Agent B environment | ConvMem access |
|-----------|--------------------|----------------|
| **C0 — Baseline** | Fresh session, no Agent-A transcript, no Portland facts in any reachable repo doc/handoff/artifact, no ConvMem tools | **Disabled** |
| **C1 — ConvMem** | Identical fresh session and identical prohibited-artifact controls | **Enabled** (`search` / `ask` / `ask --trace`, scoped) |

The **only** intended difference between C0 and C1 is ConvMem availability.
Everything else (model, prompt scaffolding, question wording, allowed generic
tools) is held constant. Contamination controls in §6 apply to **both**
conditions so C0 is a genuine "no privileged Portland source" baseline.

Run order: run **C0 first** for every question, then C1. This prevents C1
retrieval output from leaking into the operator's framing of C0.


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

Agent B must start with **no** Agent-A transcript and **no** handoff containing
the answers. Setup:

1. New agent session, new session id. Do not load or reference Agent A's
   transcript file.
2. No handoff document that contains substantive Portland facts is placed on
   any branch Agent B can read (see §6). A *coordination* handoff (naming the
   experiment, the branch, the question count) is allowed **only** if it
   contains zero Portland answer content.
3. Agent B receives an identical task prompt in both conditions: "Answer these
   questions about the Portland relocation. Use the tools available to you."
   The prompt does not itself contain any answer.
4. In **C1**, Agent B is told ConvMem is available and may set the session read
   scope (`convmem scope set relocation`) or query with `--domain`. This mirrors
   the PR #247 scoped-retrieval baseline; the operator records whether Agent B
   used scope, and whether cross-domain widening was needed for K10.
5. In **C0**, ConvMem tools are removed from the agent's tool set entirely (not
   merely "asked not to use them").

## 6. Preventing / detecting artifact leakage

This is the load-bearing control. ConvMem's own indexer ingests agent
transcripts from `~/.codex/`, `~/.cursor/`, `~/.kiro/`, `~/.continue/`,
`.crush/crush.db`, plus repo handoffs — so "fresh agent shares memory" can be
**artifact recovery**, not ConvMem retrieval. We must separate the two.

**Prohibited from leaking into the C0-reachable environment:**
- Portland facts in any `docs/inter-model/*.md`, `docs/plans/*.md`, `LATEST.md`,
  or other tracked repo file readable on Agent B's branch.
- Portland facts in a handoff, README, or copied artifact.
- The Agent-A transcript file being present/loadable in Agent B's session.

**Detection / control checklist (run before Phase B, both conditions):**
- [ ] `grep -ri "portland\|<seed keywords>"` across the repo working tree on
      Agent B's branch returns **only** this brief and the eval fixtures — never
      the answer values. (This brief uses *illustrative* placeholders, not the
      real seeded values, precisely so it is safe to commit.)
- [ ] Confirm no `docs/inter-model/` file added in this arc contains seed values.
- [ ] Confirm Agent B's session directory does not contain the Agent-A rollout.
- [ ] For C0: confirm ConvMem tools are absent from the tool manifest.
- [ ] For C1: capture `ask --trace` provenance so every recovered fact is tied
      to an Agent-A source unit (proves ConvMem path, not artifact path).

**The decisive contrast:** a fact that Agent B recovers in C1 with a ConvMem
trace pointing to an Agent-A source unit, but *cannot* recover in C0 after the
leakage checklist passes, is genuine ConvMem recovery.


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

Reuse existing tooling (§10). Encode Q1–Q8 as a golden fixture in the exact
`golden_queries.jsonl` schema (`query`, `acceptable_ids`, `top_k`, `note`),
where `acceptable_ids` are the ledger/unit ids of the seeded Agent-A source
units for each expected fact.

Per question, per condition, mechanically compute (via `eval_corpus/metrics.py`
+ `scripts/eval-retrieval.py`):
- **P@1** — is the correct source unit the top hit?
- **Hit@k / Recall@k** — does a correct unit appear in top-k?
- **MRR** — rank quality of the first correct unit.

Condition-level result = paired comparison C1 vs C0 on the **same** questions
(reuse `eval_corpus/paired_stats.py` for the paired delta). Primary readout:

> ΔHit@k and ΔMRR (C1 − C0), per question and aggregate.

Answer-level scoring (does the agent's *answer* contain the expected fact) is
recorded as a secondary, mechanically-graded field: expected-fact string/id
present in the answer = pass. Avoid subjective "seemed better" — every cell is
Hit/MRR or fact-present/absent.

**Decisive-value metric:** count of questions where C1 = hit AND C0 = miss,
with a C1 `ask --trace` provenance chain to an Agent-A source unit. This is the
"recovered through ConvMem, unavailable via baseline" count that answers H1.


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
  provenance chain for §8's decisive-value metric and the §9 provenance label.
- **Scoring:** `eval_corpus/metrics.py` (`p_at_1`, `hit_at_k`, `recall_at_k`,
  `recall_at_k_complete`, `mrr`, `first_relevant_rank`) and
  `scripts/eval-retrieval.py` (runs a `golden_queries.jsonl` fixture through
  `query_units`, emits P@1 / P@k / MRR / recall@k JSON).
- **Paired comparison:** `eval_corpus/paired_stats.py` for the C1−C0 paired delta.
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
- [ ] Leakage checklist (§6) passes on Agent B's branch (grep clean of answer values).
- [ ] Portland golden fixture written in `golden_queries.jsonl` schema.
- [ ] C0 tool-manifest confirmed ConvMem-free; C1 confirmed ConvMem-enabled.

**STOP conditions:**
- If results show H1 (ConvMem recovers what baseline cannot): **stop the
  experiment as designed.** Report the decisive-value count and per-label misses.
- If the result exposes a **new architectural problem** (automatic contextual
  inference, cross-domain policy, temporal-state reconstruction, capture-quality
  control): **STOP before designing any solution** and first identify relevant
  literature / prior art. Research precedes solution design — not this diagnostic.
- If H0 holds (baseline matches ConvMem): report that ConvMem adds no unique
  value *for this domain* and that observed sharing was artifact recovery.

---

## Answers to the required questions

**Can this experiment be run now?**
Yes. Every piece of machinery it depends on (capture via `index`/`record`,
scoped retrieval + trace from PR #247, and P@1/Hit@k/MRR/Recall@k scoring in
`eval_corpus/metrics.py` + `scripts/eval-retrieval.py`) is already on `main`.
The remaining work is experiment setup, not new architecture.

**Is any unfinished existing ConvMem plan genuinely prerequisite?**
No. JudgeBench, Shadow Ledger Phase 0, and embedding-model eval were each
checked and are not on this experiment's path. No concrete dependency found.

**Is any additional literature research required before running it?**
No — not to *run* the diagnostic. Literature research is required only *after*,
and only *if*, the result exposes a new architectural problem (per §12 STOP).

**What is the smallest implementation / setup work needed to execute it?**
1. Agent A performs real Portland work; capture K1–K10 via normal `index`/
   `record`, recording provenance ids. (~1 short session)
2. Author the K8→K9 supersession through the existing ledger path.
3. Write one Portland `golden_queries.jsonl` fixture (Q1–Q8 → seeded unit ids).
4. Prepare two runnable Agent-B harness configs: C0 (ConvMem tools removed) and
   C1 (ConvMem enabled, relocation scope). Run C0 then C1 on the fixed Q set.
5. Score with `scripts/eval-retrieval.py` + `paired_stats.py`; capture C1
   `ask --trace` provenance; fill the §9 label table for any miss.

No new evaluator, no new retrieval code, no schema change.

---

## TL;DR

- Smallest paired experiment: **C0 (fresh agent, no ConvMem, no leaked Portland
  artifacts)** vs **C1 (same agent + ConvMem scoped retrieval)** on one fixed
  8-question set over ~10 varied seeded Portland facts.
- Decisive metric: count of questions C1 hits and C0 misses **with an
  `ask --trace` provenance chain** to an Agent-A source unit — that is ConvMem
  recovery, not artifact recovery.
- Contamination control is load-bearing: ConvMem indexes agent transcripts +
  handoffs, so the baseline must strip Portland facts from every C0-reachable
  artifact and remove ConvMem tools entirely; this brief uses placeholder
  values so it is safe to commit.
- Reuses only landed machinery (PR #247 scope + trace, `eval_corpus/metrics.py`,
  `eval-retrieval.py`, `golden_queries.jsonl`, supersession). No dependency on
  JudgeBench / Shadow Ledger / embedding eval.
- **Runnable now.** Setup only (seed + fixture + two harness configs). Stop after
  design — implementation and run not started.

## Jargon TL;DR

| Term | Meaning |
|------|---------|
| C0 / C1 | Baseline condition (no ConvMem) / treatment condition (fresh agent + ConvMem) |
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
| Artifact recovery | Finding a fact via GitHub/handoff/indexed-transcript search rather than via ConvMem retrieval — the confound this experiment isolates |
| HITL | Human-in-the-loop (Ryan authorizes/merges) |
