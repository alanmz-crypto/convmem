# Commit and PR quality guidance

Write commits and PRs that a new contributor can understand without reading the
diff or knowing internal code names. This is guidance, not an enforced check —
there is no hook or CI gate.

## Commit messages

First line under 72 characters. Answer: what changed and why it matters — not
a diff summary.

- Use clear verbs: `add` (new capability), `update` (enhancement),
  `fix` (bug fix).
- Avoid code identifiers, function names, or filenames unless essential for the
  reader.
- Each commit should be self-contained and readable on its own — avoid
  "see previous commit."
- Body (if needed): reasoning, tradeoffs, or important context at 72-char wrap.

Bad: `fix: nil pointer in session.go`
Good: `fix: prevent session loading from crashing on missing metadata`

Bad: `refactor: move PromptBuilder into internal/agent`
Good: `refactor: make prompt assembly easier to maintain`

## PR summaries

Title: concise, user-facing description of what changed and why.
Body (1-2 paragraphs): problem, approach, tradeoffs or risks.
Reference related issues/decisions: `Closes #...`, `Refs dec_prop_...`.

The PR body should summarize the overall change — not re-list individual
commits.

<!-- Canonical source: AGENTS.md. This Crush deployed template is copied from
config/crush-rules-commit-pr-quality.example.md by deploy-agent-protocol.sh. -->
