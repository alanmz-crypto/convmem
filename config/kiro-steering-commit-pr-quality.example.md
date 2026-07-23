---
inclusion: always
name: commit-pr-quality
description: Commit message and PR summary quality guidance (reader-first, no automated enforcement).
---

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

## PR summaries

Title: concise, user-facing description of what changed and why.

**Required body shape (consequence → 5 Ws → TL;DR):** lead with what changes
for Ryan (or the next human), then Who/What/When/Why/How, then a short TL;DR.
Keep identifiers copy-pasteable. Scale down for tiny PRs; do not omit the human
layer on arc-close or Execute PRs.

**Also keep mapping detail when it exists:** Test plans, VERIFY check tables,
SHAs, and scope locks stay — they help agents map the project. The human layer
sits **above** that machinery; it does not replace it.

After the human layer: problem/approach/tradeoffs as needed; related issues
(`Closes #...`, `Refs dec_prop_...`). Summarize the overall change — not
individual commits.

<!-- Canonical source: AGENTS.md. This Kiro deployed template is copied from
config/kiro-steering-commit-pr-quality.example.md by deploy-agent-protocol.sh. -->
