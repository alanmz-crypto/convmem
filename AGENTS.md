## convmem protocol

Canonical session-start protocol: `config/agent-protocol.md` (three capability tiers).

Generated per-surface slices via `scripts/generate-agent-protocol.sh`.
Deployed via `scripts/deploy-agent-protocol.sh`.

**Do not duplicate session-start steps here** — they live in the global rule (Cursor `.mdc`, MCP `instructions=`, Codex global).

**Repo-specific only:** `.codex/config.toml.example` for sandbox network override in this repo. Copy to `.codex/config.toml` to allow `convmem ask` in Codex.

**Lost?** Read [`docs/MODEL-WORKFLOW.md`](docs/MODEL-WORKFLOW.md) — which repo, which script, which reference (prod digest, lab fork, record blocks).

**Codex / DeepSeek verify work:** [`docs/CODEX-DEEPSEEK-VERIFY.md`](docs/CODEX-DEEPSEEK-VERIFY.md)

---

## Commit message guidance

Write commit messages that a new contributor can understand without reading the diff or knowing internal code names. Treat this as a guideline, not an automated gate — there is no hook or CI check enforcing it.

**Guidelines:**
- First line under 72 characters.
- Focus on *why* the change exists and what outcome it enables, not a list of files or implementation details.
- Use clear, accurate verbs: `add` = new capability, `update` = enhancement, `fix` = bug fix.
- Avoid code identifiers, filenames, function names, and implementation details unless they are necessary for user-facing understanding.
- Add a body only when it explains reasoning, tradeoffs, or important context; wrap body at 72 characters.
- Prefer each commit to stand alone as a readable unit — avoid "see previous commit" dependencies.
- Prefer squashing WIP commits into one coherent message before merge.
- Bad: `fix: nil pointer in session.go`
- Good: `fix: prevent session loading from crashing on missing metadata`

## PR summary guidance

Write a PR summary that explains the change without requiring the reader to open files or inspect the diff. Same as commit messages: this is guidance, not an enforced check.

**Required body shape (consequence → 5 Ws → TL;DR):** lead with what changes for Ryan (or the next human), then Who/What/When/Why/How, then a short TL;DR. Keep identifiers (PR numbers, SHAs, paths) copy-pasteable. Scale down for tiny PRs (one consequence sentence + one-line 5 Ws or TL;DR is enough); do not omit the human layer on arc-close or Execute PRs.

**Also keep mapping detail when it exists:** Test plans, VERIFY check tables, SHAs, and scope locks stay — they help agents and future you map the project. The human layer sits **above** that machinery; it does not replace it.

**Guidelines:**
- Title: concise, user-facing description of what changed and why.
- After the human layer: problem/approach/tradeoffs as needed; related issues (`Closes #...`, `Refs dec_prop_...`).
- If this is a multi-commit PR, the body should summarize the overall change, not re-list individual commits.
- Bad title: `Refactor session store initialization`
- Good title: `Make session loading resilient to corrupt metadata files`

**All surfaces (Cursor, Crush, Kiro, Codex) should follow this guidance.** Keep
`.cursor/rules/commit-pr-quality.mdc`,
`config/crush-rules-commit-pr-quality.example.md`, and
`config/kiro-steering-commit-pr-quality.example.md` in sync with this section.
