# convmem workspace — Copilot scope guidance

This is a Python CLI and MCP server for a local knowledge corpus.

## Token economy

- Do NOT search or read the entire repository when answering questions.
- Limit file reads to the specific module(s) relevant to the task.
- Avoid `#codebase` broad retrieval unless the user explicitly asks for repo-wide analysis.
- Never open `.crush/`, `.venv/`, `__pycache__/`, `handoff-*.tar.gz`, or `staging/` — these are binary/generated and contain no useful source.

## Project structure (quick orientation)

- **Source modules:** `*.py` in repo root (CLI commands, stores, adapters)
- **Adapters:** `adapters/` — file-format parsers for chat transcripts
- **Tests:** `tests/`
- **Scripts:** `scripts/` — shell utilities for indexing, deployment, syncing
- **Docs:** `docs/` — architecture plans, inter-model handoffs, builder reference
- **Config templates:** `config/` — example configs for various editors/agents

## Conventions

- Python 3.11+, no type stubs required (runtime-typed)
- Follow the repository's Pylint regression gate for Python changes.
- Tests run with `pytest`
- Branch before editing: never commit directly to `main`

## What NOT to do

- Do not run `convmem add`, `convmem index` (without `--file`), or `convmem verify` autonomously.
- Do not create markdown files, logs, or summaries unless explicitly asked.
- Do not review or summarize the entire repository unprompted.
