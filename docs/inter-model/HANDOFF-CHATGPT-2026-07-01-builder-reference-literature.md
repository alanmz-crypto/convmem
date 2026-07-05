# Handoff: Builder-reference literature review — for ChatGPT

**Date:** 2026-07-01  
**From:** Cursor Auto  
**To:** ChatGPT (cloud — upload tarball or paste this file)  
**Purpose:** Recommend **additional literature** that would bring knowledge, wisdom, and experience to the convmem project **before** we execute the enriched application plan. Design/research only — **no code**, no corpus writes.

**Status:** open  
**Owner:** ChatGPT (recommendations) → Ryan (acquire/read) → Cursor (digest if approved)  
**Sunset:** after Ryan accepts/rejects recommendations and plan execution resumes

---

## What is convmem? (30 seconds)

A **local-first knowledge corpus** on one Arch Linux workstation. It indexes AI chat transcripts into ChromaDB (Ollama embeddings), keeps an authoritative JSONL **ledger** of decisions/observations, and exposes read-only search via CLI + MCP to Cursor, Continue, Kiro, Crush, and Codex. Ryan is the sole ledger writer; agents propose, humans approve.

North-star: **operate-and-document** — not greenfield. P0–P1b and global protocol are **shipped**. Optional gates ahead: P1c streaming synthesis, F1 refine job queue, P2 MCP tools (held).

---

## What we already have (do not re-recommend these)

Nine books are already digested under `builder-reference/` (principle cards in our own words — not book dumps):

| Book | Tier | Read when touching |
|------|------|-------------------|
| A Philosophy of Software Design (Ousterhout) | A (deployed) | CLI surfaces, module depth, protocol consistency |
| Introduction to Information Retrieval (Manning) | A | Ranking, chunking, evaluation, golden queries |
| Why Programs Fail (Zeller) | A | doctor, triage, repro, verification |
| Software Architecture: The Hard Parts | A | Trade-offs, data ownership, saga/decision pipeline |
| Designing Data-Intensive Applications (Kleppmann) | B (repo) | Ledger leader / Chroma follower, watch as stream |
| Architecture Patterns with Python | B (thin — needs expansion) | Repository, UoW, aggregates, F1 job queue |
| The Pragmatic Programmer | archive | DRY, orthogonality, tracer bullets |
| How to Take Smart Notes | archive | Zettelkasten → ledger linking |
| Building a Second Brain | archive | CODE/PARA capture pipeline |

Ryan already owns PDFs for all nine (see `builder-reference/SOURCES.md` in the tar).

---

## Why we're asking now

Cursor + Claude Cloud produced an **enriched application plan** (`PLAN-apply-builder-reference.md`) to wire these digests into past work and future gates. **Execution is paused** until we know whether missing literature would change priorities or reveal blind spots.

Claude's review surfaced **honest gaps** the current canon does not cover well:

| Gap | Example |
|-----|---------|
| **unmapped** domains | Restic fail-closed backup gate — no digest owns "backup-before-write" discipline |
| Thin coverage | `arch-patterns-python` digest (989 words) — F1 refine queue needs Command/Event/UoW depth |
| Multi-agent coordination | propose → review → approve saga; surface-specific agent habits |
| Streaming / partial failure | P1c `ask` synthesis timeout → partial fallback |
| Evaluation beyond IR | Alien-workspace soak grading, agent-behavior fitness functions |
| Knowledge durability | When to record vs when ritual is read-only; anti-patterns for "second canon" |
| Crush token economics | Standing context cost vs on-demand rules — no book, but related craft literature may exist |

We want books (or chapters) that **fill gaps**, **deepen weak mappings**, or **challenge assumptions** — not more of what Ousterhout/Manning/DDIA already give us.

---

## Read order in this archive

1. `HANDOFF.md` (this file)
2. `PLAN-apply-builder-reference.md` — enriched plan (pending execution)
3. `builder-reference/README.md` — digest index + soak results
4. `builder-reference/notes/suggested-application-of-builder-material.md` — how we use the canon
5. `context/ROADMAP.md` — optional gates (P1c, P2, F1, P3)
6. `context/MILESTONE-F.md` — F1 refine job queue (if recommending event-driven / data books)
7. Skim digest **titles and "Read when"** sections — do not need full text unless judging overlap

---

## Your deliverable

Write **`LITERATURE-RECOMMENDATIONS.md`** (markdown, 3–6 pages). Ryan will save to `docs/inter-model/CHATGPT-2026-07-01-literature-recommendations.md`.

### Required sections

1. **Executive summary** — top 3–5 recommendations ranked by expected payoff for convmem *before* plan execution
2. **Gap matrix** — map each identified gap (above + any you find) to recommended reading
3. **Recommended reading list** — for each title:
   - Full bibliographic citation
   - **Why this book** (one paragraph — specific to convmem, not generic praise)
   - **Which digest it complements or supersedes** (or "net new lane")
   - **Suggested tier:** A (daily agent surface) / B (repo digest) / archive (background) / **pass** (overlap too high)
   - **Suggested page ranges or chapters** (if known) — we extract slices, not whole books
   - **Read when touching** — one line, matching our digest format
4. **Deprioritized / pass list** — books often suggested for this stack but redundant with the nine we have
5. **Acquisition notes** — freely available vs purchase; editions to prefer
6. **Risks** — recommendations that would bloat the canon, duplicate protocol rules, or push toward distributed-systems scope we deliberately avoid

### Quality bar

- **Specific beats generic.** "Read Clean Code" without a convmem hook is a fail.
- **Prefer depth over breadth.** Five excellent fits beat fifteen maybes.
- **Challenge us.** If a recommended book argues *against* our single-writer monolith or MCP-read-only design, say so — that's valuable.
- **Respect constraints below.**

---

## Constraints (non-negotiable)

1. **No copyrighted text** — recommend titles/chapters; we write our own principle cards
2. **Single user, single machine** — not building for multi-tenant or cloud corpus
3. **Agent-facing output** — digest must help an AI agent *before editing code*, not impress a human book club
4. **Token budget** — tier-A digests deploy to Crush `global_context_paths` (~13.5k tokens standing today); new tier-A needs explicit justification vs on-demand loading
5. **Do not recommend** re-reading or re-digesting the nine books we already have unless a **specific uncovered chapter** justifies a second pass
6. **No implementation** — no CLI design, no `convmem record` blocks, no code

---

## Open work the literature might inform

| Gate | Shape | Current digest lens |
|------|-------|---------------------|
| P1c streaming synthesis | partial `ask` fallback on timeout | Ousterhout + Manning |
| F1 refine queue | tombstones, job order, UoW rollback | DDIA + Arch Patterns (thin) |
| P2 MCP `unresolved` | held — agent habit evidence required | Hard Parts + Zeller |
| P3 hybrid retrieval | needs eval regression | Manning |
| Builder-reference execution | README fix, script thresholds, DDIA promotion | meta — craft of fitness functions |
| Restic gate | **unmapped** | ? |

---

## Expected output format (example row)

```markdown
### [Book Title] — [Author] ([Year])

**Tier:** B  
**Complements:** Zeller (verification); fills Restic/backup discipline gap  
**Read when touching:** live-write gates, disaster recovery, fail-closed CLI design  
**Chapters:** Ch. 4 (backup invariants), Ch. 9 (testing recovery)  
**Why convmem:** ROADMAP Restic gate blocks `record --approve-last` on backup failure — we have replication theory (DDIA) but not operational backup craft.  
**Pass if:** we instead document Restic as ops runbook only (no digest).
```

---

## Return path

Ryan uploads your `LITERATURE-RECOMMENDATIONS.md` back to Cursor. Cursor will:

- Merge accepted titles into a literature backlog in the application plan
- Defer or reorder execution todos if a new book changes priorities
- **Not** auto-create digests — Ryan acquires PDF, then Cursor/Kiro digest on request

---

## Files in this archive

See `MANIFEST.md` in the tar root.

---

## Ryan → ChatGPT prompt

> Upload the tarball. Read `HANDOFF.md` and `PLAN-apply-builder-reference.md` first. Produce `LITERATURE-RECOMMENDATIONS.md` per the deliverable spec. Focus on gaps the nine existing books do not cover. Return markdown only.
