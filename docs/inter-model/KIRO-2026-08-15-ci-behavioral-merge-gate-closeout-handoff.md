# Implementation Handoff: CI Behavioral Merge Gate — Closeout Planning

**Date:** 2026-08-15  
**Author:** Kiro (design review)  
**For:** Codex (architecture/planning)  
**Authorization:** Ryan, 2026-08-15 (verbal — "give me a handoff for the best agent which I believe is Codex")

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `plan/2026-08-15-ci-behavioral-merge-gate-closeout` |
| **Tip SHA** | see branch tip after this commit |
| **Push status** | pushed to origin |
| **PR** | not opened |
| **Ryan GATE** | Ryan decides scope: full arc docs vs. lightweight evidence-only close |
| **Track A ingest** | Kiro session (this handoff) |

---

## What to build

Close the CI Behavioral Merge Gate as a proper convmem arc. The mechanical work is already done (PR #187 landed pytest CI; `Protect Main` ruleset now requires both `pylint (3.12)` and `pytest (3.12)`). What's missing is the planning/evidence trail that makes this discoverable, verifiable, and durable by convmem's own standards.

**Why this exists:** ConvMem's test suite (1,284+ tests) previously ran only locally. PR #187 (merged 2026-08-15 as `c2c6429`) added a hermetic pytest job to GitHub Actions and Ryan immediately made it a required status check. There is no ARCHITECTURE decision record explaining the gate's design, no negative-control evidence proving the gate actually blocks, no critical-invariant manifest, and no LATEST.md pointer. This handoff authorizes Codex to plan the closeout.

---

## Current state (what already exists)

### Implemented (on `main`)

1. **`.github/workflows/pylint.yml` pytest job** — hermetic runner, Python 3.12, temp config at `/tmp/convmem-ci/config.toml`, no live Ollama/Chroma/Restic, golden-eval skipped via `GITHUB_ACTIONS` env check. Runs `python -m pytest -q`.

2. **`Protect Main` ruleset (id 19156572)** — active enforcement, strict status policy:
   - `pylint (3.12)` required (integration_id 15368)
   - `pytest (3.12)` required (integration_id 15368)
   - Pull request required (0 approvals, thread resolution required)
   - Deletion protection, non-fast-forward protection
   - Ryan account bypass present (break-glass)

3. **Hermeticity fixes in #187** — `test_eval_golden.py` skip, `test_mcp_roots_probe.py` / `test_mcp_site.py` / `test_readonly_store.py` / `test_restic_systemd.py` / `test_shadow_activation.py` / `test_watch.py` all adapted for clean GitHub runner (no hardcoded home paths, no live corpus).

### Missing (Codex scope)

| Item | Priority | Description |
|------|----------|-------------|
| **ARCHITECTURE doc** | P1 | Decision record: why the gate exists, hermeticity contract, what's in/out, residual risks. Short — maybe 60 lines. Models similar to `ARCHITECTURE-ci-wait-workflow.md` in structure. |
| **Negative-control evidence** | P1 | One throwaway branch with a deliberate `assert False` in a tracked test, push, observe `pytest (3.12)` red, observe merge blocked. Screenshot or CI run URL is sufficient evidence. |
| **Critical-invariant manifest** | P2 | A small file (JSON or TOML) listing test paths whose disappearance from collection would be catastrophic. Not enforced in v1 — just documented. Future hardening could make CI compare collection against this floor. |
| **LATEST.md pointer** | P1 | One bullet in "Recently merged / settled" for PR #187. |
| **VERIFY doc (optional)** | P3 | Lightweight — confirm the gate works, record SHA and run IDs. Could be as small as the negative-control evidence formatted into a VERIFY table. |

---

## Integration point

No code changes needed. All outputs are documentation:

- `docs/plans/ARCHITECTURE-ci-behavioral-merge-gate.md` — new file
- `docs/inter-model/LATEST.md` — add bullet for #187
- `tests/ci-critical-invariants.txt` or similar — new file (manifest)
- `docs/plans/VERIFY-ci-behavioral-merge-gate.md` — optional new file

---

## Specification

### Architecture doc structure

Follow the pattern in `ARCHITECTURE-ci-wait-workflow.md` and `ARCHITECTURE-bugbot-pr-gate.md`:

1. Status/Owner/Scope/Decision table
2. Problem statement (tests existed but didn't gate merge)
3. Decision (hermetic pytest + required status check)
4. Hermeticity contract (what CI gets: no Ollama, no live Chroma, no Restic creds, no systemd, no DeepSeek key)
5. What the gate proves and what it doesn't
6. Relationship to other gates (Pylint regression, BugBot, CodeQL)
7. Break-glass / bypass policy
8. Non-goals (no coverage gate, no matrix, no perf benchmark)
9. Residual risks (test-discovery silent drop, timing drift, bypass permanence)
10. Acceptance criteria

### Negative-control experiment

```
1. Branch from main: fix/2026-08-XX-negative-control-ci-gate
2. Add to any test file: assert False, "CI gate negative control"
3. Push to origin
4. Open PR targeting main
5. Wait for pytest (3.12) to fail
6. Record: run URL, red status, merge blocked confirmation
7. Close PR without merging, delete branch
```

### Critical-invariant manifest

A flat text file listing test paths (one per line) that represent the most important behavioral proofs. Suggested initial contents based on CG-1 and CG-2:

```
tests/test_file_generation_pointer.py
tests/test_serving_authority.py
tests/test_source_reconciler.py
tests/test_logical_accounting.py
tests/test_mixed_mode_proof.py
tests/test_cg2_rehearsal.py
tests/test_shadow_activation.py
tests/test_chroma_store.py
tests/test_readonly_store.py
```

This is advisory documentation only — no CI enforcement in v1.

---

## What NOT to build

- No coverage-percentage gate
- No Python version matrix (3.11/3.13)
- No OS matrix (Windows/macOS)
- No live-Ollama or live-DeepSeek test tier
- No performance benchmark gate
- No test refactoring or new tests
- No STATUS file (this is a bounded closeout, not a multi-phase arc)
- No changes to the workflow or ruleset (already working)
- No collection-regression CI step (future hardening, separate grant)

---

## Test expectations

No new runtime tests needed. The negative-control experiment is a one-time manual verification, not a permanent test.

---

## Acceptance criteria

- [ ] `ARCHITECTURE-ci-behavioral-merge-gate.md` committed with decision record
- [ ] Negative-control experiment performed — CI run URL recorded showing pytest failure blocks merge
- [ ] `LATEST.md` has #187 bullet in "Recently merged / settled"
- [ ] Critical-invariant manifest file exists (advisory, not enforced)
- [ ] All new files pass Pylint/ruff (markdown exempt)
- [ ] Branch pushed, PR ready for Ryan review

---

## Branch convention

```
plan/2026-08-15-ci-behavioral-merge-gate-closeout
```

Codex may switch to `docs/2026-08-XX-ci-behavioral-merge-gate-closeout` if the work is purely docs, per taxonomy. Push immediately after each commit.

---

## Related files

| What | Path |
|------|------|
| Current workflow (pytest job) | `.github/workflows/pylint.yml` |
| PR that landed it | [#187](https://github.com/alanmz-crypto/convmem/pull/187) |
| Ruleset (GitHub) | `Protect Main` (id 19156572) |
| Similar arc (CI wait) | `docs/plans/ARCHITECTURE-ci-wait-workflow.md` |
| Similar arc (BugBot gate) | `docs/plans/ARCHITECTURE-bugbot-pr-gate.md` |
| CG-1 test evidence | LATEST.md CG-1 G4b bullet (1,284 + 230 subtests) |

---

## Codex delegation guidance

**Reasoning tier:** This is planning/documentation — `medium` reasoning effort is sufficient. No intensive code generation needed.

**Key context Codex should read first:**
1. This handoff file
2. `.github/workflows/pylint.yml` (to understand what the gate actually does)
3. `docs/plans/ARCHITECTURE-ci-wait-workflow.md` (structural template for the ARCHITECTURE doc)
4. `docs/plans/ARCHITECTURE-bugbot-pr-gate.md` (another example of how convmem documents gates)

**Codex sandbox note:** The negative-control experiment requires GitHub Actions and network access to push/observe. If Codex cannot perform that in sandbox, it should produce the ARCHITECTURE doc + manifest + LATEST bullet and leave negative-control as a `BLOCKED_ON_RYAN` item with instructions for Ryan to execute manually.

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed (on pushed branch)
- [ ] `LATEST.md` bullet at top with link and resume state
- [ ] Branch pushed
- [ ] Track A: session indexed

**Implementer (picking up):**

- [ ] Read this file before first edit
- [ ] `convmem work resume plan/2026-08-15-ci-behavioral-merge-gate-closeout` or start fresh branch
- [ ] Produce ARCHITECTURE doc, manifest, LATEST bullet
- [ ] Attempt or document negative-control experiment
