# Sonnet cloud review — brief MCP + per-project rollup

**You are reviewing offline.** No shell, no local MCP, no `/home/lauer` paths on your side.

## What this bundle is

Convmem change: expose read-only `brief` on MCP with **per-repo project rows** so cold agents can orient on `willowyhollow-dev`, `wp-sec-agent`, etc.

**Not in scope:** MCP writes (`propose_decision` stays CLI + signer only).

## Read order

1. `CONTEXT.md` — problem, prior critique, design intent
2. `QUESTIONS.md` — answer every item; PASS / PASS WITH NOTES / FAIL
3. `diff/brief-mcp-uncommitted.patch` — exact delta vs `main` @ 391c07a
4. `files/` — full changed modules for line-level review
5. `LIVE-RESULTS.md` — what Ryan's machine already verified (do not re-run; trust or challenge logically)

## Deliverable format

```markdown
## Verdict: PASS | PASS WITH NOTES | FAIL

## Findings (ranked)
- ...

## Boundary check (MCP read-only)
- ...

## One follow-up (single highest-leverage item)
- ...

## Answers to QUESTIONS.md
(copy each question with answer)
```

Post back to Ryan or `docs/inter-model/SONNET-2026-06-23-brief-mcp-review.md` in convmem repo.

## Do not recommend

- Adding `propose_decision` to MCP without signer gate
- Indexing all of `docs/inter-model/` into Chroma as default fix
- Git pre-commit lint revival
