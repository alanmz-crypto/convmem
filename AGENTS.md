## convmem protocol

Canonical session-start protocol: `config/agent-protocol.md` (three capability tiers).

Generated per-surface slices via `scripts/generate-agent-protocol.sh`.
Deployed via `scripts/deploy-agent-protocol.sh`.

**Do not duplicate session-start steps here** — they live in the global rule (Cursor `.mdc`, MCP `instructions=`, Codex global).

**Repo-specific only:** `.codex/config.toml.example` for sandbox network override in this repo. Copy to `.codex/config.toml` to allow `convmem ask` in Codex.

**Lost?** Read [`docs/MODEL-WORKFLOW.md`](docs/MODEL-WORKFLOW.md) — which repo, which script, which reference (prod digest, lab fork, record blocks).

**Codex / DeepSeek verify work:** [`docs/CODEX-DEEPSEEK-VERIFY.md`](docs/CODEX-DEEPSEEK-VERIFY.md)

## Cursor Cloud specific instructions

convmem is a single-product Python 3.12 CLI + MCP server (no web app, no network DB). Setup/run/test commands live in `README.md`; only cloud-specific caveats are captured here.

**Python env:** The cloud VM has no conda/mamba. Deps live in a repo-local venv at `.venv` (the startup update script creates it and installs `requirements.txt` + `pylint==4.0.6 pytest`). Activate with `. .venv/bin/activate` (or call `.venv/bin/python`). Run the CLI as `python convmem.py <cmd>` — there is no `convmem` shell alias here.

**Ollama is required for `index`/`add`/`search` (embeddings) and is NOT auto-started.** systemd does not run in the VM, so the installed `ollama` service does not start on boot. Start it manually before any embedding/search work and keep it alive in a tmux session:
`ollama serve` (listens on `127.0.0.1:11434`), then confirm with `curl -s http://127.0.0.1:11434/api/version`. The `nomic-embed-text` embedding model is pre-pulled in the snapshot; if missing, run `ollama pull nomic-embed-text`.

**`ask`/`distill` need secrets/models not present by default:** `convmem ask` and `distill` require `DEEPSEEK_API_KEY` (add via Secrets) plus a local summarize model (`llama3.1:8b`, not pre-pulled). Pure `search`, `stats`, `add`, and `related` (graph traversal) work with only Ollama embeddings. `convmem doctor` exits non-zero because it probes the summarize/DeepSeek canaries — expected without those.

**Known environment-coupled test failures (not code bugs):** `python -m unittest discover -s tests` yields 4 failures in the cloud VM that assume the original developer's machine/corpus: `test_watch.test_is_live_watch_db_cursor_store` and both `test_mcp_site` brief-slug tests hardcode `/home/lauer/...` paths and config-specific project slugs; `test_eval_golden.test_golden_questions` needs a large live corpus + DeepSeek/summarize models. The other 472 pass.

**Lint:** CI (`.github/workflows/pylint.yml`) gates on a regression baseline, not raw pylint exit. There are ~523 pre-existing findings; the gate passes as long as no NEW findings are introduced. Reproduce locally: run `pylint $(git ls-files "*.py") --output-format=json > /tmp/pylint-report.json` then `python scripts/pylint_regression_gate.py ci --report /tmp/pylint-report.json --pylint-status <exit> --branch-baseline ci/pylint-baseline.json --base-ref HEAD`.
