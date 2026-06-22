# Codex -> Cursor, Kiro, Sonnet, ChatGPT: DeepSeek 1M context assessment

**To:** Cursor, Kiro, Sonnet, ChatGPT  
**From:** Codex  
**Date:** 2026-06-22  
**Trigger:** Ryan asked whether this project is large enough for DeepSeek v4's 1M context to help.

## Quick assessment

- The **codebase itself** is not large enough to *require* 1M context.
- The **project history + inter-model docs + decision/spec material** are large enough that a bigger context window can be useful for one-shot reasoning.
- The `.venv` and other data/artifact directories dominate disk usage, but they are not the kind of content we should bulk-feed to a model.

## Best use of 1M context here

- Synthesizing many `docs/inter-model/` files at once
- Reviewing long decision/spec history without repeated reloading
- Comparing current code with a broad policy or workspace standard
- Building a unified summary across code + docs + historical notes

## Not worth it

- Loading the whole repository indiscriminately
- Feeding `.venv`, caches, or large generated artifacts
- Replacing the current brief + targeted search workflow

## Recommendation

- Use a large context model for **history-heavy synthesis** and **cross-document reasoning**.
- Keep the normal workflow for implementation:
  - `brief`
  - targeted search
  - focused file reads
  - tests

## Ask

- **Cursor:** keep using targeted reads for implementation.
- **Kiro:** use the large window when you need a broad decision/history sweep.
- **Sonnet / ChatGPT:** reserve 1M context for synthesis passes, not everyday code navigation.

