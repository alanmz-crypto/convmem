## convmem protocol

Canonical session-start protocol: `config/agent-protocol.md` (three capability tiers).

Generated per-surface slices via `scripts/generate-agent-protocol.sh`.
Deployed via `scripts/deploy-agent-protocol.sh`.

**Do not duplicate session-start steps here** — they live in the global rule (Cursor `.mdc`, MCP `instructions=`, Codex global).

**Codex Luna tier at launch — read this before delegating to Codex.** The `codex` CLI exposes a
single model id (`gpt-5.6-luna`); the tier is the reasoning effort, set explicitly — the default
config silently fixes it to `low`. Low/med/high (`-c 'model_reasoning_effort="low|medium|high"'`)
map to delegate-down tiers 4 / 5–6 / 9. Full invocation map: `~/.codex/CODE-X-delegate-down.md`.

**Repo-specific only:** `.codex/config.toml.example` for sandbox network override in this repo. Copy to `.codex/config.toml` to allow `convmem ask` in Codex.

**Lost?** Read [`docs/MODEL-WORKFLOW.md`](docs/MODEL-WORKFLOW.md) — which repo, which script, which reference (prod digest, lab fork, record blocks).

**Codex / DeepSeek verify work:** [`docs/CODEX-DEEPSEEK-VERIFY.md`](docs/CODEX-DEEPSEEK-VERIFY.md)

---

## Project goal awareness (STATUS files)

Every active arc has a `docs/plans/STATUS-<slug>.md` — an **arc brief** that gives models a complete mental landscape of the project they're working in. It answers:

1. **What is this project for?** — the product-level goal, why it matters.
2. **How does the system work?** — diagram of how pieces connect, data flow, key invariants.
3. **What exists on disk right now?** — file map with state (complete / stub / empty / missing).
4. **What's your role?** — what you're here to do based on why Ryan sent you.
5. **What's missing before it's live?** — sequential checklist from here to production.

**Mandatory read:** If you are working on an arc that has a STATUS file, read it before starting work. Your first response must state Goal / My role / System state / Next action (see `config/agent-protocol.md` for the exact format).

**Design intent:** A model should arrive and within one document have a strong enough mental image of the arc's design that it knows what exists, what's missing, and its exact role — stronger than its knowledge of the convmem project as a whole. The STATUS file is that document.

**Creation rule:** When starting a new arc (ARCHITECTURE + EXECUTION plan), create `docs/plans/STATUS-<slug>.md` using the JudgeBench template (10-section structure). The slug is kebab-case and must match the arc's ARCHITECTURE filename suffix (e.g. `ARCHITECTURE-shadow-ledger-phase0.md` → `STATUS-shadow-ledger-phase0.md`). Add the new entry to the **Active STATUS files** list below and in `config/agent-protocol.md`. A new arc without a STATUS file is incomplete.

**Update rule:** After any milestone changes state (PR merged, gate passed, blocker discovered), update the STATUS file in the same commit or a follow-up. Stale STATUS is worse than no STATUS.

**Departure protocol:** The STATUS file must stay a *current-state snapshot*, not a log. Overwrite sections to reflect reality now (delete completed items, move "branch" → "`main`", rewrite "Your Role" for the next model). Session narrative belongs in Track A, not here. One line in the Update Log. Test: could a fresh model read only this file and orient itself?

**Active STATUS files** (arc briefs — read when working that arc; closed arcs keep briefs for reference):
- [`docs/plans/STATUS-judgebench.md`](docs/plans/STATUS-judgebench.md) — JudgeBench semantic calibration v1
- [`docs/plans/STATUS-r2b-capture-auth.md`](docs/plans/STATUS-r2b-capture-auth.md) — R2b capture authorization
- [`docs/plans/STATUS-shadow-ledger-phase0.md`](docs/plans/STATUS-shadow-ledger-phase0.md) — Shadow Ledger Phase 0 delta capture
- [`docs/plans/STATUS-chroma-reconcile-tier-l.md`](docs/plans/STATUS-chroma-reconcile-tier-l.md) — Chroma Reconcile Tier L (**closed GREEN**; reference only)
- [`docs/plans/STATUS-complete-data-backup-correction-v2.md`](docs/plans/STATUS-complete-data-backup-correction-v2.md) — Complete-data backup correction v2
- [`docs/plans/STATUS-codeql-complex-therapy.md`](docs/plans/STATUS-codeql-complex-therapy.md) — CodeQL Complex Therapy merge protection
- [`docs/plans/STATUS-trapdoor-interlude-hunt.md`](docs/plans/STATUS-trapdoor-interlude-hunt.md) — Trapdoor Hunt FF1/T1 and FF2/T2 prerequisite contract

**Cross-arc rollup:** [`docs/inter-model/STATUS.md`](docs/inter-model/STATUS.md) — active vs closed arcs and next authorized actions (not a per-arc brief).

---

## Arc identity (required)

Every session working on a named arc must **know and state its arc codename** (e.g. "Arc Trapdoor Hunt", "Arc Pinwheel Pytest CI"). Full rule in `config/agent-protocol.md`; summary:

1. **Discover** your arc from Ryan's prompt, branch name, STATUS file, or handoff doc. If unclear, **ask**.
2. **Carry** — include `**Arc: <codename>**` in your first substantive response.
3. **Stamp** — include the arc codename in every TL;DR, forward announcement, and handoff doc header.
4. **Boundary** — do not cross into another arc's scope without Ryan's authorization.
5. **No arc = say so** — `**Arc: none (ad-hoc)**` for routine/maintenance work.

Known arc codenames (canonical list in `config/agent-protocol.md`):

| Codename | Subject | State |
|----------|---------|-------|
| Trapdoor Hunt | Dependability & provenance trust architecture | Active |
| Trapdoor Interlude Hunt | FF1/T1 trust baseline and FF2/T2 evidence-gap prerequisite | Active — FF1 draft |
| Full Fathom Five | Parent five-arc dependability roadmap (FF1–FF5) | Active — frozen |
| CI Kryptonite | Behavioral CI merge gate | **Closed** |
| Pinwheel Pytest CI | Reproducible pytest CI | **Closed** |
| CodeQL Complex Therapy | CodeQL merge protection | **Closed** — technical controls PASS; Ryan-owned recurring attestation |

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

**Proactive PR handoff:** When a branch is committed, pushed, and ready for a pull request, proactively include a copy-paste-ready PR title and Markdown description in the completion or handoff—even if Ryan did not separately ask for one. Apply the body shape and Merge reading rules below. Supplying the description does not authorize creating the PR; open it only after Ryan explicitly asks.

**Merge reading links:** when the PR closes an arc, lands Execute, or updates VERIFY/LATEST, include a short **Merge reading** list of markdown links to the docs Ryan should open after (or instead of) skimming the diff — typically `ARCHITECTURE-*`, `EXECUTION-*`, `VERIFY-*`, and the relevant `docs/inter-model/LATEST.md` Active handoff bullet. Prefer repo-relative paths that work on GitHub. Tiny drive-by PRs may omit this; arc-close / Execute must not.

**Also keep mapping detail when it exists:** Test plans, VERIFY check tables, SHAs, and scope locks stay — they help agents and future you map the project. The human layer sits **above** that machinery; it does not replace it.

**Squash-merge default (Ryan, 2026-07-23):** Ryan **squash-merges every PR** unless an agent **explicitly** says not to. Agents must assume squash is fine. When commit history on `main` must be preserved (rare — e.g. signed bisect points, commit-by-commit provenance already under review), the PR body and handoff must include a clear **`Do not squash`** line with a one-sentence reason. Silence = squash OK.

**Guidelines:**
- Title: concise, user-facing description of what changed and why.
- After the human layer: problem/approach/tradeoffs as needed; related issues (`Closes #...`, `Refs dec_prop_...`).
- If this is a multi-commit PR, the body should summarize the overall change, not re-list individual commits. Squash will collapse WIP history — write the PR title/body as the eventual `main` commit message.
- Bad title: `Refactor session store initialization`
- Good title: `Make session loading resilient to corrupt metadata files`

**All surfaces (Cursor, Crush, Kiro, Codex) should follow this guidance.** Keep
`.cursor/rules/commit-pr-quality.mdc`,
`config/crush-rules-commit-pr-quality.example.md`, and
`config/kiro-steering-commit-pr-quality.example.md` in sync with this section.
