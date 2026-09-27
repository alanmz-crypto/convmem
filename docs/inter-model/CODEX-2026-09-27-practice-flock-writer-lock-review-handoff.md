# Adversarial Review Handoff: Practice Writer Lock and Agent Instructions

**Date:** 2026-09-27  
**Author:** Codex (solo design)  
**For:** Independent review agent assigned by Ryan  
**Arc:** none (ad-hoc)  
**State:** `READY_FOR_REVIEW`  
**Authorization:** Ryan requested this handoff and an adversarial-review prompt. This authorizes review only, not implementation or operational execution.

**Canonical location:** This file and its `LATEST.md` pointer are on the pushed ConvMem docs branch. It authorizes independent review only; implementation and operational execution remain separately gated.

## Review target and current state

Review the design below against `origin/main` at `0a71373434631a60f0d8d4734d5f4772996a2fae`. The local checkout that produced this handoff is `main` at `9618ad8`, three commits behind that target. Inspect that exact Git object read-only; do not switch, reset, or checkout the shared workspace. For example:

```bash
git show 0a71373434631a60f0d8d4734d5f4772996a2fae:AGENTS.md
git show 0a71373434631a60f0d8d4734d5f4772996a2fae:scripts/practice-theme-preflight.sh
git show 0a71373434631a60f0d8d4734d5f4772996a2fae:scripts/sync-preview-to-practice.sh
git ls-tree -r --name-only 0a71373434631a60f0d8d4734d5f4772996a2fae -- .cursor/rules .kiro/steering
```

If the pinned object is unavailable, ask Ryan to fetch it or use a disposable worktree. Never checkout the pinned target in the shared workspace.

At the review target, the practice runtime's canonical child theme is tracked at `public_html/wp-content/themes/astra-child/`. The destructive-operation freeze remains in force. Slice 2 wires the read-only theme preflight into `scripts/sync-preview-to-practice.sh`, but that does not authorize executing the sync or other frozen operations. The writer-lock proposal is a design for later review and authorization; it must not be wired into scripts or used to run any operation as part of this review.

## Proposed design

### Writer lock

Add one host-local, advisory exclusive lock for **cooperating commands that mutate the practice runtime files or database**. Use a single stable lock path derived from `XDG_RUNTIME_DIR`, shared by the clients running as the same local user and outside both the Git checkout and `public_html`. If that runtime directory is unavailable, fail closed with a clear error; do not silently choose a per-checkout fallback that would split the lock namespace. Keep the lock file in place; do not unlink or replace it.

The common lock-aware entry point should acquire the lock before the first mutation and hold it through completion of the command and its children. Use non-blocking acquisition with a clear “practice writer busy” diagnostic and a stable busy exit status (proposed: 75). Read-only inspection should not acquire the exclusive lock. Avoid nested acquisition: define one outer boundary per mutating operation and keep lower-level helpers from reacquiring the same lock.

The intended first coverage set is local operations that write the practice DB or runtime tree: DB/file imports and restores, destination-side syncs, and mutating WP-CLI/install commands. Review must determine the exact entry-point list from the target revision before any implementation plan is approved. Commands that only read practice while writing another environment need separate classification; do not automatically call them practice writers.

`flock` is advisory. It protects only processes that acquire the same lock. It does **not** stop direct agent edits, raw Docker/SQL commands, browser-based WP Admin writes, a second user with a different runtime directory, or another machine. Therefore the design offers serialization for cooperating local command paths, not a hard guarantee that only one agent or all possible writers can change the project. Keep the broader one-active-agent rule as process guidance unless all write access is routed through a lock-enforcing broker.

### Canonical instructions

Keep the existing repo-root `AGENTS.md` as the only full canonical instruction text. Do not add whole-file symlinks in `.cursor/rules` or `.kiro/steering` by default:

- Cursor documents root `AGENTS.md` as an instruction source for IDE and CLI; project rules under `.cursor/rules` are a separate MDC mechanism.
- Kiro documents root `AGENTS.md` as automatically discovered workspace guidance, always included.
- A second copy can duplicate context. A symlink with the wrong extension or format can also fail to behave as a Cursor MDC rule.

The proposed four-client roster is **Cursor, Crush, Kiro, and Codex**. ConvMem records this set as consumers of shared repo instructions; the independent reviewer must verify this is the intended roster for this repo rather than substitute a different client by guesswork. If one of these clients fails to load the root file, add the smallest native adapter for that client (for example, a short rule that references the canonical file) and test that behavior. Do not duplicate the full policy text. Evidence for Cursor and Kiro does not establish support in Crush or Codex.

### Boundaries and non-goals

- Review only. No implementation, staging, deployment, DB mutation, restore, sync, install, push, or freeze change.
- Do not claim `flock` enforces writes that bypass the helper.
- Do not create client-specific copies of the full `AGENTS.md`.
- Do not introduce a new dependency, daemon, agent broker, or cross-machine lock service in this design.
- Do not expand into a general web-development standard; this lock is specific to the local practice workspace and its cooperating writers.

## Open design questions for the reviewer

1. Is the proposed lock domain precise enough: should it cover only practice DB/runtime-tree mutations, or is the intended invariant broader? What concrete writer bypass would make the current claim misleading?
2. Is `XDG_RUNTIME_DIR` the right shared lock namespace for every intended local client and invocation mode? Identify any relevant login, service, UID, worktree, container, or filesystem behavior that could split or defeat it.
3. Is the lock lifetime correctly placed around whole multi-step operations, including child processes and pipelines? Check for nested-lock deadlocks, early release, and paths that mutate before acquisition.
4. Which entry points at the pinned target mutate practice state, and which merely read it or mutate preview/staging? Does the proposal omit any high-impact local writer?
5. Do official/current client behaviors support the no-symlink decision for all four clients? Distinguish verified behavior from assumption; identify any client-specific adapter that is truly needed.
6. Does the target revision’s Slice 2 freeze or any other repository constraint prohibit a future implementation step as currently described? Keep review authorization separate from operational authorization.
7. Is proposed busy exit status 75 unused and suitable in this repo? An initial scan of target-revision `scripts/` found explicit script statuses 0 and 1, with no 75; confirm relevant callers and conventions before accepting it, and recommend the smallest correction if needed.
8. What is the smallest useful verification set for a later implementation (contention, release-on-exit, fail-closed behavior, cross-entry-point coverage, and instruction loading), without turning this into unnecessary infrastructure?

## Prompt for the independent reviewer

```text
You are conducting an independent adversarial design review only. Do not edit files, implement the proposal, run the practice stack, access WP Admin, execute sync/restore/install commands, touch the database, or change the destructive-operation freeze.

First read the handoff and verify the pinned target revision. The local author checkout is three commits behind origin/main. Inspect the exact pinned tree without changing the shared checkout; use read-only commands such as `git show 0a71373434631a60f0d8d4734d5f4772996a2fae:AGENTS.md`, `git show <sha>:<path>`, and `git ls-tree -r --name-only <sha> -- .cursor/rules .kiro/steering`. Do not run `git checkout`, `git switch`, or `git reset` in the shared worktree. If the object is unavailable, ask Ryan to fetch it or inspect it in a disposable worktree. Then inspect current target scripts and instruction-loading evidence relevant to this proposal.

Apply /home/lauer/Projects/convmem/docs/inter-model/DECISION-REVIEW-GUARDRAILS.md explicitly. Its non-negotiable floor remains in force: these guardrails never waive safety, review authority, or the operational freeze. Classify every material concern as local implementation, interface/contract, or architectural. If you and the coordinator disagree about a finding's level, state both classifications for Ryan; do not silently overrule one another.

Try to falsify these claims:
1. A single stable host-local flock path meaningfully serializes the intended cooperating practice writers.
2. The stated boundaries accurately distinguish cooperative CLI writers from bypassing writers, including direct file edits, WP Admin, Docker/SQL, other UIDs, and other machines.
3. The lock is acquired early enough and held long enough across subprocesses and multi-step operations, without nested-acquisition deadlocks or lock-path replacement hazards.
4. The proposed writer entry-point coverage matches the actual current scripts and helpers, including commands that only read practice while writing another environment.
5. Keeping root AGENTS.md without whole-file client symlinks is correct for **Cursor, Crush, Kiro, and Codex**. Verify this exact roster with Ryan if evidence indicates another intended set. Use current official documentation or direct, non-mutating loader evidence; do not infer all-four support from Cursor and Kiro alone.
6. The design stays compatible with the current destructive-operation freeze and does not accidentally imply authorization to execute frozen operations.
7. The proposed busy exit status 75 fits existing script/caller conventions and does not collide with an established meaning.

Also look for any material defect, unsafe assumption, or failure mode not anticipated by the claims above; the numbered list is a starting map, not a limit on adversarial review.

Report one of: SUPPORT, REVISE, or REJECT. For each material finding give (a) severity, (b) classification, (c) exact evidence path/line or official source, (d) concrete failure/attack scenario, (e) consequence, and (f) the smallest correction. Separate blockers from optional improvements; consolidate duplicates. Include the strongest counterargument to your verdict and list any remaining Ryan-owned decision.

Use one full-depth pass for this first review. Stop when the true current state is established and no plausible remaining finding would change the recommendation. If the design is revised later, any second review should be a delta review of the changes and genuinely new evidence. Never use the stop rule to waive a safety check or the operational freeze.

Do not implement. End with a concise handoff recommendation to Ryan identifying whether the design is ready for a separately authorized implementation plan.
```

## Evidence and references

- Current target repo state: `origin/main` `0a71373434631a60f0d8d4734d5f4772996a2fae` (Slice 2 theme-preflight wiring; operational freeze unchanged).
- Proposed instruction clients: Cursor, Crush, Kiro, and Codex (ConvMem shared-instructions record; reviewer should verify this roster applies here).
- Exit-code scan at the pinned target: scripts explicitly use statuses 0 and 1; no explicit status 75 was found. Reviewer still checks callers and proposes a stable code.
- Guardrails applied: [`DECISION-REVIEW-GUARDRAILS.md`](DECISION-REVIEW-GUARDRAILS.md).
- [Cursor: Rules and root `AGENTS.md`](https://docs.cursor.com/context/rules-for-ai)
- [Kiro: Steering and `AGENTS.md` discovery](https://kiro.dev/docs/steering/)
- [Linux `flock(1)` manual](https://man7.org/linux/man-pages/man1/flock.1.html)

## Resume state

This is a review-only handoff, not implementation authorization. Branch: `docs/2026-09-27-practice-flock-writer-lock-review`. The packet and `LATEST.md` pointer are pushed; no PR was opened. Ryan assigns the independent reviewer and decides after review whether to request an implementation plan. Any implementation remains separately authorized and must honor the freeze at the then-current repo tip.
