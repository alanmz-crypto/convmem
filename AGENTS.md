## convmem protocol

Canonical session-start protocol: `config/agent-protocol.md` (three capability tiers).

Generated per-surface slices via `scripts/generate-agent-protocol.sh`.
Deployed via `scripts/deploy-agent-protocol.sh`.

**Do not duplicate session-start steps here** — they live in the global rule (Cursor `.mdc`, MCP `instructions=`, Codex global).

**Repo-specific only:** `.codex/config.toml.example` for sandbox network override in this repo. Copy to `.codex/config.toml` to allow `convmem ask` in Codex.

**Lost?** Read [`docs/MODEL-WORKFLOW.md`](docs/MODEL-WORKFLOW.md) — which repo, which script, which reference (prod digest, lab fork, record blocks).

**Codex / DeepSeek verify work:** [`docs/CODEX-DEEPSEEK-VERIFY.md`](docs/CODEX-DEEPSEEK-VERIFY.md)

---

## Commit message quality

Every commit message in this repo must be understandable to someone unfamiliar with the codebase. Before writing a message, verify this litmus test: a new contributor reading only the commit message should understand what problem this solves, why it matters, and the impact — without opening files, reading the diff, or knowing internal code names.

**Rules:**
- First line under 72 characters.
- Focus on *why* the change exists and what outcome it enables, not a list of files or implementation details.
- Use clear, accurate verbs: `add` = new capability, `update` = enhancement, `fix` = bug fix.
- Avoid code identifiers, filenames, function names, and implementation details unless they are necessary for user-facing understanding.
- Add a body only when it explains reasoning, tradeoffs, or important context; wrap body at 72 characters.
- Every commit must stand alone as a readable unit — no "see previous commit" dependencies.
- Prefer squashing WIP commits into one coherent message before merge.
- Bad: `fix: nil pointer in session.go`
- Good: `fix: prevent session loading from crashing on missing metadata`

## PR summary quality

Every pull request must have a summary that explains the change without requiring the reader to open files or inspect the diff.

**Rules:**
- Title: concise, user-facing description of what changed and why.
- Body (1-2 paragraphs max): problem being solved, approach taken, any notable tradeoffs or risks.
- List related issues/decisions if applicable (use `Closes #...` or `Refs dec_prop_...`).
- If this is a multi-commit PR, the body should summarize the overall change, not re-list individual commits.
- Bad title: `Refactor session store initialization`
- Good title: `Make session loading resilient to corrupt metadata files`

**All surfaces (Cursor, Crush, Kiro, Codex) producing commits or PRs in this repo must follow these rules.**
