# Forte — builder digest (convmem)

**Source:** *Building a Second Brain* · full text, 231pp

**Read when:** designing the capture → organize → digest → express pipeline, brief as daily review, unresolved triage workflow, or any question about how personal knowledge management workflows map to agent knowledge management.

## Principles

- **The CODE framework: Capture, Organize, Digest, Express.** Knowledge moves through four stages: collect raw material, structure it for retrieval, distill it into insights, and share those insights. Convmem's pipeline follows the same arc.
- **Capture what resonates.** Not everything is worth keeping. The bar for capturing an observation or decision should be low, but not zero — capture what might be useful, then triage later.
- **Organize for actionability, not completeness.** Forte's PARA method (Projects, Areas, Resources, Archives) organizes by how the information will be used, not by topic. Convmem's domain/site taxonomy is a PARA-like structure — organize by coordination lane, not by academic category.
- **Digest through summarization.** The "progressive summarization" technique: highlight, bold, summarize, remix. Convmem's distillation pipeline (raw chunks → knowledge units → summaries → builder digests) is a progressive summarization chain.
- **Express before you're ready.** Don't wait for a perfect understanding before recording a decision. Record the best current model, then update it as new evidence arrives. This is exactly the propose → verify → supersede cycle.
- **The second brain is a system, not a tool.** The method matters more than the software. Convmem's protocol (doctor → brief → unresolved → ask → record) is the method; the CLI and MCP are implementations.

## What this means for convmem

### CODE → convmem pipeline mapping

| CODE stage | Convmem equivalent | Purpose |
|------------|-------------------|---------|
| **Capture** | `convmem record`, ingest adapters, watch daemon | Collect raw material from sessions, files, monitors |
| **Organize** | domain/site prefixes, `relates_to` edges | Structure for retrieval by coordination lane |
| **Digest** | distill.py, builder-reference digests | Condense raw units into knowledge units and summaries |
| **Express** | `brief`, `ask`, cross-project digest | Share synthesized insights across surfaces |

### PARA → convmem organization

| PARA category | Convmem equivalent |
|---------------|--------------------|
| **Projects** | Active P0/P1 items in brief, current session scope |
| **Areas** | Domain prefixes (`coding.tooling`, `web_stack.security`) |
| **Resources** | Builder-reference digests, golden-query set |
| **Archives** | Superseded decisions, old `dec_prop_*` without `relates_to` children |

Fortes insight: most people organize by topic; PARA organizes by **actionability**. Projects are what you're working on now; Areas are domains of responsibility; Resources are reference material; Archives are dead items. Convmem's domain taxonomy already works this way — `coding.tooling` is an area of responsibility, not a topic.

### Progressive summarization

Forte's four levels of summarization:

1. **Raw capture** — full session transcript, inbox files
2. **Highlighted passages** — chunked Markdown, extracted pages
3. **Bold/standout ideas** — knowledge units from distill.py
4. **Summary/remix** — builder-reference digests, cross-project digest

The gap in convmem: progressive summarization works best when each level is explicitly tagged with its abstraction level. Adding a `summarization_level` field to units would let retrieval prefer the right abstraction for the query depth.

## convmem Hooks

- **The brief is the daily PARA review.** Forte recommends a weekly review of projects and areas. `brief --stdout-only` does this for the corpus. If you're not reading the brief, you're flying blind.
- **Capture threshold: lower than you think.** If a session observation might be useful, record it. The cost of an extra `obs_*` is negligible; the cost of losing an insight is unbounded.
- **Organize for retrieval, not for storage.** `--relates-to` and `domain` are retrieval tools. If a decision is hard to find, it's organized wrong regardless of where it sits in the JSONL.
- **Digest is not optional.** Raw chunks and observations are useful for search but terrible for synthesis. The distill pipeline and builder digests are the "digest" step — without them, the second brain is just a pile of notes.
- **Express weekly.** If no cross-project digest or brief update has been generated in a week, the system is in capture-only mode. Trigger an express cycle.

## Anti-patterns for Agents

- Do not skip the brief. Forte's PARA review is not optional in a second brain — it's how you know what's active, what's stalled, and what needs attention.
- Do not capture everything. The bar is "might be useful for a future decision." If you can't articulate why an observation matters, it probably shouldn't be an entry.
- Do not organize by topic alone. Organize by what the knowledge is for (coordination, client work, infrastructure), not by what it's about.
- Do not treat the first capture as the final form. Progressive summarization means the raw observation is version 1; the distilled unit is version 2; the digest mention is version 3.

## Related digests

- **How to Take Smart Notes** — the Zettelkasten method provides the linking discipline; Building a Second Brain provides the workflow structure. Use them together.
- **Zeller** — the observation → hypothesis → fix → verify → record cycle is the CODE framework applied to debugging.
- **Ousterhout** — progressive summarization is deep modularity for knowledge: each abstraction level hides the details of the level below.
