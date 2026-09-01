# ConvMem: technical and research orientation

This document is the slow-moving entrance for readers who want to understand
the technical/research project. It explains the problem, proposed mechanism,
evaluation boundaries, and code-reading path. It is not a live status file.
For mutable implementation and experiment state, use the [cross-arc status
snapshot](inter-model/STATUS.md), the [JudgeBench arc brief](plans/STATUS-judgebench.md),
and the [naturalistic product-value arc brief](plans/STATUS-naturalistic-product-value.md).

## 1. Research problem

AI-assisted development is longitudinal, but the sessions that produce useful
knowledge are usually ephemeral. A decision made in one chat, a failed repair,
or a security finding from a tool may matter weeks later, yet ordinary chat
history and keyword search do not automatically turn those events into reliable
evidence for a later agent.

Long-lived memory introduces its own failure modes. A retrieved item can be
wrong, stale, superseded, missing its provenance, or detached from the decision
or verification that gives it meaning. Retrieval can fail even when a capable
generator is available; generation can fail even when retrieval succeeded. The
two failures should be diagnosable separately. Blindly injecting old text into a
new prompt also creates an epistemic problem—old text may not deserve trust—and
a security problem when archived text contains instructions aimed at the
current model.

ConvMem is a working investigation of what it takes to make personal,
long-lived AI memory inspectable. The useful question is not only “did a model
produce an answer?” It is also “what was remembered, where did it come from,
what relationships or later checks qualify it, and what should the system say
when the evidence is insufficient?”

## 2. Proposed mechanism

The core data flow is:

```text
source conversations / tool evidence / coordination records
                         |
                      adapters
                         |
               normalization / chunking
                         |
             derived units + provenance
                         |
       durable records / indexes / relationships
                         |
          multi-signal retrieval and ranking
                         |
             bounded evidence context
                         |
        direct retrieval or cited synthesis
                         |
      answer / abstention / degraded-state signal
```

Adapters recognize the local formats used by the current workflow, including
JSONL, SQLite, JSON, and Markdown from coding assistants, inter-model documents,
and tool output. Ingest normalizes messages, chunks source material, and
produces searchable units with source and provenance metadata. Tool-sourced
observations, decisions, and verifications can carry stable ledger identities
and `relates_to` relationships, allowing a later query to traverse an evidence
chain rather than treating every text fragment as an isolated document.

The serving path currently uses a local Chroma collection for the primary
`knowledge_units` search surface, with embeddings, lexical signals, optional
recency, optional cross-encoder reranking, domain/site scope, and evidence-aware
ranking. `ask` receives a bounded selection of retrieved excerpts, formats
citations, and asks a configured generation model to synthesize an answer. It
can also return retrieval-only information when there are no matches or when
synthesis fails or is interrupted. A trace mode records the stages and the
identity of the context delivered to synthesis.

There is no single universal authority rule hidden behind this diagram. Current
authority is record-, path-, and arc-specific. Chroma remains authoritative for
the existing Phase 0 observation/search path; approved decision intent has its
own durable approval record; JSONL exports are useful for backup and replay but
are incomplete and mutable today. The [current authority map](audit-ledger-first/CURRENT-OBSERVATION-AUTHORITY.md)
is the relevant source when recovery or projection claims matter. The longer-
term direction is to make serving indexes rebuildable projections of durable
authority without losing provenance or decision semantics.

The default deployment is a single workstation. Chroma and the corpus live
locally, and local Ollama can provide embeddings and summaries. A configured
provider may receive retrieved context or source material for synthesis or
distillation; “local-first” therefore does not mean that no data can leave the
machine. The repository also contains local MCP, agent-hook, background-service,
backup, recovery, and guarded shadow/evaluation surfaces. Their existence does
not mean that every surface is enabled or production-ready; current status and
authorization live in the relevant arc documents.

## 3. How this differs from ordinary conversation search or basic RAG

Embeddings, lexical retrieval, reranking, retrieval-augmented generation,
provenance, and language-model judging all have substantial prior art. ConvMem
does not claim to have invented those components. Its research interest is the
integration of several concerns in one longitudinal personal-memory system:

- durable identities for observations, decisions, and verifications;
- provenance describing how a derived unit relates to source material;
- evidence relationships that support decision and verification traversal;
- retrieval signals beyond vector similarity alone;
- an explicit boundary between retrieval and synthesis;
- visible abstention and degraded states when retrieval or generation is weak;
- corpus, recovery, and projection invariants that can be checked separately;
- evaluation gates that distinguish component behavior from end-to-end value;
- local-first operation over a private, evolving corpus;
- agent-oriented continuation across ordinary development sessions.

That combination may or may not produce meaningful value. The product-value
hypothesis is:

> Compared with the same fresh agent working without ConvMem, does ConvMem
> improve meaningful recovery and continuation during ordinary work?

This hypothesis has not yet been answered. A coherent mechanism and elaborate
governance are not evidence that the system improves productivity, memory
quality, or decisions.

## 4. Trust boundary

ConvMem treats retrieved historical text as data to inspect, not as a new source
of authority over the current interaction. In `ask.py`, retrieved excerpts are
delimited and explicitly framed as untrusted archived content. The JudgeBench
prompt wrappers apply the same rule independently to evidence and candidate
text: the judge is told to evaluate the supplied data and not follow
instructions embedded inside those data blocks.

The intended boundary is:

```text
stored/retrieved historical text
        |
        | untrusted data
        v
prompt data boundary
        |
        v
synthesis / judging
```

This is a deliberate mitigation and design constraint. It is not a security
proof, and it does not establish immunity to indirect prompt injection,
poisoned records, malicious provenance, or a model that ignores the boundary.
The security question remains empirical and adversarial.

## 5. Evaluation decomposition

ConvMem keeps several evaluation layers separate because a single score can
hide which part of the system failed:

1. **Corpus and source integrity** — whether source records, identities,
   projections, and recovery invariants hold.
2. **Retrieval** — whether relevant evidence reaches the candidate set and final
   context under a specified query and corpus.
3. **Synthesis** — whether the generator uses the delivered evidence faithfully,
   cites it, and reports insufficiency rather than inventing support.
4. **Semantic judging** — whether a judge's structured verdict agrees with
   locked labels under a specified rubric and model-identity policy.
5. **End-to-end product value** — whether people or agents actually recover and
   continue work better in a prospective comparison.
6. **Recovery and dependability** — whether the system remains inspectable and
   recoverable across failure, migration, and projection changes.

A failure in one layer must not silently become a pass in another. In
particular, an integrity check can show that a corpus repair preserved records;
it cannot show that users found the remembered material useful.

## 6. Evidence-status vocabulary

The following vocabulary keeps engineering state separate from scientific
claim status:

| Label | Meaning |
| --- | --- |
| **Hypothesis** | A proposed outcome not yet empirically established. |
| **Implemented** | A mechanism exists in the repository. |
| **Regression-tested** | Tests guard known behavior or invariants. |
| **Operationally validated** | A bounded operational condition was demonstrated. |
| **Methodology validated** | Experiment or evaluation machinery passed its methodological checks. |
| **Empirical evidence** | Observations from an executed study or evaluation bear on a scientific or product claim. |
| **Not yet tested** | A planned or implemented question has no relevant result yet. |

Repository words such as `PASS`, `GREEN`, `CLOSED`, `10/10`, or “merged” are
local engineering and governance statuses. Their scientific meaning depends on
what was actually tested. A GREEN corpus-repair operation is operational
integrity evidence, not evidence of memory usefulness. A methodology PASS is
not product evidence. A safeguard is not proof that the threat it addresses
cannot occur.

## 7. Current evidence and its limits

Mutable execution state belongs in the [JudgeBench status](plans/STATUS-judgebench.md),
the [naturalistic status](plans/STATUS-naturalistic-product-value.md), and the
[cross-arc rollup](inter-model/STATUS.md). The following is the narrow
interpretation of the current evidence surfaces.

### Retrieval regression fixture

The committed [`golden_queries_baseline.json`](../tests/fixtures/golden_queries_baseline.json)
contains eight developer-authored queries targeting known corpus records. Its
stored metrics are:

| Metric | Stored result | Interpretation |
| --- | ---: | --- |
| P@1 | 0.75 | The acceptable target was first for 6 of 8 queries. |
| hit@k / P@k | 1.0 | An acceptable target appeared within each query's configured top-k. |
| MRR | 0.875 | Mean reciprocal rank of the first acceptable target. |

To rerun this regression against the configured local corpus, use the
[`scripts/eval-retrieval.py`](../scripts/eval-retrieval.py) runner:

```bash
python scripts/eval-retrieval.py
```

The command compares current results with the stored baseline. This is an
engineering regression check, not a public benchmark or broad product-value
result.

This is a developer-authored retrieval regression fixture for known corpus
items, not a broad validation of semantic retrieval quality. It has `n=8`, is
corpus-specific and tied to a private/local environment, and its query
construction is not independent. Several questions closely resemble target
record titles or content, so lexical overlap is a major construct-validity
concern. These numbers support regression detection for these known targets;
they do not establish robust natural-language semantic recall.

The repository also contains a separate live golden-question test that depends
on the local corpus and skips in CI. That test is useful for local operational
checks, but an unavailable private corpus means it is not a public benchmark.

### Retrieval and synthesis failure separation

The `ask` path implements distinct `synthesis_failed` and
`synthesis_interrupted` outcomes. With no generated tokens it can return
retrieval citations only; after a partial stream it marks the answer as
interrupted and preserves the partial result. Retrieval-only behavior and
low-confidence/no-match warnings are separate paths. These are implemented and
tested behaviors. They are not evidence that users benefit from graceful
degradation.

### Traceability and evidence relationships

Ask tracing records retrieval stages and the identity/hash of the exact context
delivered to synthesis. This makes ranking and context-delivery changes more
diagnosable; it does not demonstrate ranking superiority. The
[`chain-demo.md`](../examples/chain-demo.md) example shows ledger-linked
observation, decision, and verification traversal without a separate graph
database. Legacy records without equivalent identity are not interchangeable
with fully linked ledger records.

### Corpus integrity

Chroma reconciliation, write-boundary checks, backup checks, and recovery
machinery provide operational integrity signals for bounded conditions. They
should be read as evidence that a particular invariant or operation held under
the tested conditions. They do not establish general data durability, complete
rebuildability, or product usefulness across all paths.

### JudgeBench

JudgeBench provides a frozen evidence/candidate corpus, structured semantic
judgment contracts, rubric validation, deterministic metrics, model identity,
and comparison-signature checks. The current [JudgeBench arc brief](plans/STATUS-judgebench.md)
is authoritative for whether calibration calls have run. At the documented
current stage, the 30-case corpus and calibration machinery exist, but the
provider/model calibration experiment has not run; judge selection remains a
separate gated decision. Do not call the judge calibrated merely because the
harness or its tests are green.

JudgeBench also records model identity and an `independence_class`, with
`model_digest_and_quant()` capturing local model context where available. This
matters because an LLM evaluator may recognize or favor its own or a related
model family's generations. Tracking origin and requiring an appropriate
independence class is an implemented evaluation safeguard. It does not prove
that the judge is unbiased or that cross-family judging is reliable.

### Naturalistic product-value study

The current [naturalistic product-value status](plans/STATUS-naturalistic-product-value.md)
classifies G1–G5 as methodology validation, not product evidence. Those stages
provide contracts, adjudication/probe scaffolds, bounded analysis, reliability
states, information-gate slots, and a synthetic dry-run. No prospective
naturalistic product verdict exists. G6 remains Ryan-locked pending the required
review and later explicit authorization. Favorable synthetic outputs cannot
open G6 and cannot be described as evidence that ConvMem helps ordinary work.

## 8. Threats to validity

### Construct validity

The eight-query retrieval fixture may reward lexical overlap because its queries
and acceptable records were authored together. It therefore measures a narrow
regression construct, not naturalistic memory usefulness or robust semantic
recall. Operational correctness—such as preserving an ID or returning a
citation—does not automatically equal useful recovery or a better decision.

### Internal validity

An evaluator and generator from the same model or family can create systematic
preference or recognition effects. Changes to models, prompts, corpora, or
retrieval settings can also change results. Comparison signatures,
model-identity checks, frozen cases, and pre-specified study machinery are
designed to reduce post-hoc adaptation. They only help if the relevant frozen
study is actually executed under those controls.

### External validity

The current system is shaped around one developer's workstation, workflow,
private longitudinal corpus, and AI-assisted software-development tasks. Results
from that setting do not automatically generalize to other people, tasks,
corpora, teams, or organizations.

### Reproducibility

Some source transformations, tests, contracts, and static fixtures are publicly
inspectable. Other checks depend on a private corpus, local Ollama/model state,
or provider calls. The repository does not currently provide one hermetic
command that reproduces every headline metric, and the live golden evaluation
is not equivalent to a public benchmark when its underlying corpus is
unavailable.

### Documentation and state drift

ConvMem changes quickly and retains historical handoffs for provenance. Dated
documents can describe a past branch or decision. Research interpretation
belongs here; current execution belongs in the status documents. Before
interpreting a result, verify the current status and the exact artifact or
fixture used by that result.

### Security validity

Delimiting retrieved content as untrusted data and instructing models not to
follow embedded instructions is a useful mitigation. It is not a complete
defense or security proof against indirect prompt injection, poisoned context,
or model noncompliance. The naturalistic methodology's blinding, frozen
sampling, adjudication, denominator handling, and symmetric control/treatment
conditions are methodological controls; they become product evidence only after
an authorized prospective study runs.

## 9. Prior art and intellectual context

ConvMem sits adjacent to several established research areas. The references
below position the work; they are not claims of direct intellectual descent or
of novelty for individual components.

- **Classical information retrieval:** Christopher D. Manning, Prabhakar
  Raghavan, and Hinrich Schütze, *Introduction to Information Retrieval*,
  Cambridge University Press, 2008. The repository's [builder-reference
  digest](builder-reference/manning-builder-digest.md) uses this as its
  classical retrieval anchor.
- **Retrieval-augmented generation:** Patrick Lewis et al., “Retrieval-
  Augmented Generation for Knowledge-Intensive NLP Tasks,” 2020,
  [arXiv:2005.11401](https://arxiv.org/abs/2005.11401). This situates the
  combination of parametric generation with non-parametric retrieved memory and
  the importance of provenance.
- **Adaptive/corrective retrieval:** Akari Asai et al., “Self-RAG: Learning to
  Retrieve, Generate, and Critique through Self-Reflection,” 2023,
  [arXiv:2310.11511](https://arxiv.org/abs/2310.11511); and Shi-Qi Yan et al.,
  “Corrective Retrieval Augmented Generation,” 2024,
  [arXiv:2401.15884](https://arxiv.org/abs/2401.15884). These are examples of
  treating retrieval necessity or quality as something to assess. ConvMem does
  not implement either method.
- **RAG evaluation decomposition:** Shahul Es et al., “RAGAS: Automated
  Evaluation of Retrieval Augmented Generation,” 2023,
  [arXiv:2309.15217](https://arxiv.org/abs/2309.15217); and Jon Saad-Falcon et
  al., “ARES: An Automated Evaluation Framework for Retrieval-Augmented
  Generation Systems,” 2023,
  [arXiv:2311.09476](https://arxiv.org/abs/2311.09476). These contextualize
  evaluating retrieval/context quality and generation quality separately;
  ConvMem's decomposition is not equivalent to either framework.
- **LLM judge self-preference:** Arjun Panickssery, Samuel R. Bowman, and Shi
  Feng, “LLM Evaluators Recognize and Favor Their Own Generations,” 2024,
  [arXiv:2404.13076](https://arxiv.org/abs/2404.13076). This motivates treating
  judge/generator origin as an evaluation-validity concern rather than ignoring
  it; it does not prove that ConvMem's safeguard removes bias.
- **Indirect prompt injection:** Jingwei Yi et al., “Benchmarking and
  Defending Against Indirect Prompt Injection Attacks on Large Language
  Models,” 2023, [arXiv:2312.14197](https://arxiv.org/abs/2312.14197). This
  provides context for distinguishing retrieved external/archive data from
  executable instructions. ConvMem's framing is a mitigation, not proof of
  immunity.

## 10. Reproducibility boundary

### Publicly inspectable and reproducible from repository material

- unit, contract, and regression tests that do not require the private corpus;
- static evaluation fixtures and locked JudgeBench case/rubric schemas;
- prompt-wrapper behavior and output validation;
- source, normalization, and provenance transformations where their fixtures
  are public;
- evidence relationship and retrieval-trace mechanics that can be exercised
  with available fixtures.

### Locally reproducible with additional dependencies or services

- Ollama-backed embeddings, summaries, and local-model evaluations;
- reranking with the configured cross-encoder and model weights;
- provider-backed synthesis or semantic judgments when credentials and the
  authorized model configuration are available;
- live-corpus retrieval and operational integrity checks on the author's
  workstation.

### Not publicly reproducible from this repository alone

- evaluations requiring the author's private conversation/security corpus;
- historical workstation state, local service state, or private corpus-health
  counts;
- any product-value result from a prospective live study that has not run or
  whose source corpus and sealed artifacts are not public;
- a universal reconstruction of current authority from JSONL exports alone.

This boundary is intentional. The project does not manufacture a public
benchmark by presenting private local results as if they were independently
reproducible.

## 11. Open questions

- Does ConvMem improve meaningful recovery and continuation during ordinary
  work?
- How much of current retrieval performance survives independently phrased,
  lexically distant questions?
- How should semantic-judge reliability be calibrated across model families?
- Do provenance and evidence relationships improve user decisions, rather than
  merely improving diagnosability?
- How robust is the system to poisoned or adversarial retrieved content?
- Which results generalize beyond one developer and one longitudinal corpus?
- Which authority/projection paths can eventually become fully rebuildable
  without losing provenance or decision semantics?

## 12. Where to inspect the implementation

Use this bounded path when reading code; it is separate from the operational
agent workflow in [`AGENTS.md`](../AGENTS.md) and [`MODEL-WORKFLOW.md`](MODEL-WORKFLOW.md).

- **Ingest and provenance:** [`ingest.py`](../ingest.py),
  [`provenance_binding.py`](../provenance_binding.py), and the adapter modules
  under [`adapters/`](../adapters/).
- **Retrieval and ranking:** [`query.py`](../query.py),
  [`evidence.py`](../evidence.py), and [`chroma_store.py`](../chroma_store.py).
- **Synthesis and failure handling:** [`ask.py`](../ask.py), including the
  bounded context delivery and `synthesis_failed`/
  `synthesis_interrupted` paths.
- **Evidence traversal and identities:** [`ledger.py`](../ledger.py),
  [`ledger_ids.py`](../ledger_ids.py), [`related.py`](../related.py), and the
  [`chain-demo.md`](../examples/chain-demo.md) example.
- **Evaluation provenance and JudgeBench:**
  [`eval_provenance.py`](../eval_provenance.py),
  [`eval_model_identity.py`](../eval_model_identity.py),
  [`eval_judgebench/`](../eval_judgebench/), and
  [`eval_judgebench/prompt_wrappers.py`](../eval_judgebench/prompt_wrappers.py).
- **Retrieval regression:** [`scripts/eval-retrieval.py`](../scripts/eval-retrieval.py)
  and [`tests/fixtures/golden_queries_baseline.json`](../tests/fixtures/golden_queries_baseline.json).
- **Product-value methodology:** [`eval_naturalistic/`](../eval_naturalistic/)
  and [`STATUS-naturalistic-product-value.md`](plans/STATUS-naturalistic-product-value.md).
- **Recovery and dependability:** the relevant recovery/provenance architecture
  and status documents under [`docs/plans/`](plans/) and the
  [`current authority map`](audit-ledger-first/CURRENT-OBSERVATION-AUTHORITY.md).

After this orientation, use the current status document for the specific arc or
experiment you intend to inspect. Do not treat this document, an old handoff,
or a test label as a substitute for the evidence produced by an authorized
run.
