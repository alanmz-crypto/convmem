# Builder Reference

Curated Markdown digests for the books that most directly affect agent
behavior in this repo.

These are not verbatim book dumps. They are compact principle cards written in
our own words so they can be loaded into agent surfaces without polluting the
repo with copyrighted source text.

## Tier A — deployed to agent surfaces

Copied to Cursor, Kiro, Codex pointers, and Crush `global_context_paths` (four
digests only — ~13.5k standing tokens). Deploy:
`bash scripts/deploy-builder-reference.sh`

| Book | Digest | Read when touching |
| --- | --- | --- |
| A Philosophy of Software Design | [ousterhout-builder-digest.md](ousterhout-builder-digest.md) | `convmem.py`, `brief.py`, `mcp_server.py`, CLI surface, module boundaries, protocol generation, ask() timeout/fallback, multi-surface consistency |
| Introduction to Information Retrieval | [manning-builder-digest.md](manning-builder-digest.md) | retrieval ranking, `recency_weight`, `rerank`, chunk sizing, evaluation, golden-query workflows, PASS/PARTIAL/FAIL grader design |
| Why Programs Fail | [zeller-builder-digest.md](zeller-builder-digest.md) | `convmem doctor`, unresolved triage, repro steps, observation/diagnostic workflow, fix verification |
| Software Architecture: The Hard Parts | [hard-parts-builder-digest.md](hard-parts-builder-digest.md) | service-split trade-offs, ledger vs Chroma ownership, ingest/watch boundaries, MCP vs CLI surfaces, decision pipeline saga analysis |

## Tier B — repo + cheap surfaces (on-demand)

Listed in Cursor/Kiro/Codex config; **not** in Crush `global_context_paths`
(Crush loads full digest text every session — no glob-scoped rules; adding tier-B
requires an explicit Ryan token-budget decision).

| Book | Digest | Read when touching |
| --- | --- | --- |
| Designing Data-Intensive Applications | [ddia-builder-digest.md](ddia-builder-digest.md) | ledger as async-replication leader, Chroma as follower, single-writer rationale, watch daemon as stream consumer, event-time vs processing-time, exactly-once via idempotency |
| Architecture Patterns with Python | [arch-patterns-python-builder-digest.md](arch-patterns-python-builder-digest.md) | ingest adapters, repository pattern, Unit of Work, F1 refine job queue, event/command vocabulary, aggregate boundaries |
| Building Evolutionary Architectures | [evolutionary-architectures-builder-digest.md](evolutionary-architectures-builder-digest.md) | `verify-builder-reference.sh`, `validate-builder-reference-surfaces.sh`, fitness-function design, threshold reconciliation, adding new automated checks |

## Archive

Background on knowledge-capture and craftsmanship — not first-pass drivers for
infra work unless the change is specifically about capture workflow.

| Book | Digest | Read when touching |
| --- | --- | --- |
| How to Take Smart Notes | [archive/smart-notes-builder-digest.md](archive/smart-notes-builder-digest.md) | observation/decision/verification ledger design, evidence graph traversal, Zettelkasten principles |
| Building a Second Brain | [archive/second-brain-builder-digest.md](archive/second-brain-builder-digest.md) | capture-to-express pipeline, PARA organization, progressive summarization |
| The Pragmatic Programmer | [archive/pragmatic-programmer-builder-digest.md](archive/pragmatic-programmer-builder-digest.md) | DRY across protocol surfaces, orthogonality, tracer bullet approach, Design by Contract |

### Notes

| Note | Purpose |
| --- | --- |
| [suggested-application-of-builder-material.md](notes/suggested-application-of-builder-material.md) | Operational guide for applying the canon without turning it into a second canon |

## Format

- One digest per book.
- Each digest starts with `Source`, `Read when`, and the design focus.
- Each digest uses the same internal structure:
  - principles in plain language
  - convmem-specific hooks
  - anti-patterns for agents

## Source Ledger

Use `SOURCES.md` for PDF paths and page ranges. Keep the source list separate
from the digest text so the digest files stay clean and readable.

## Deploy and verify

```bash
cd ~/Projects/convmem
bash scripts/deploy-builder-reference.sh
bash scripts/verify-builder-reference.sh
bash scripts/validate-builder-reference-surfaces.sh
```

| Script | Role |
|--------|------|
| `verify-builder-reference.sh` | Repo files, sha256 vs Crush copies, `global_context_paths`; **ship gate ≥1500 words** |
| `validate-builder-reference-surfaces.sh` | Per-surface config depth; **≥2500 words aspirational WARN** |

Verifier checks repo digests, per-surface config, and sha256 match for Crush
copies. Exit 1 on FAIL; WARN on thin digests or stale deploy.

## CLI validation log

| Date | `verify` | `validate-surfaces` | Notes |
|------|----------|---------------------|-------|
| 2026-07-01 | PASS | WARN | Tier A/B README; DDIA+arch-patterns on Cursor/Kiro/Codex; Crush tier-A only; script thresholds reconciled |

## Interactive soak (manual)

Run the same prompt on each surface when convenient:

> I'm editing `ask.py` recency behavior. Before proposing changes, cite which
> builder-reference digest applies and one principle from it.

| Date | Surface | Pass? | Notes |
|------|---------|-------|-------|
| 2026-07-01 | Cursor | pass | Cited Manning (ranking / recency) |
| 2026-07-01 | Kiro | pass | Cited Manning |
| 2026-07-01 | Codex | pass | Cited Manning |
| 2026-07-01 | Crush | pass | Cited Manning |

Interactive soak complete (Ryan, 2026-07-01).
