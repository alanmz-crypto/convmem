# Handoff: Pinwheel Pytest CI Planning Package

**Date:** 2026-08-16
**Author:** Codex
**For:** Ryan, Kiro, ChatGPT, and Cursor
**State:** `IMPLEMENTED_LOCALLY__READY_FOR_PR__DISPOSABLE_CONTROLS_PENDING`

## Consequence

The Pinwheel plan now has two independent PASS-with-conditions reviews and
binds the conditions into the architecture, execution, and VERIFY records.
Ryan authorized Cursor execution. Implementation is complete locally on
`fix/2026-08-16-pinwheel-pytest-ci`. Disposable GitHub controls remain
unauthorized until Ryan grants them.

## Current system

PR #189 merged Arc CI Kryptonite to `main` as
`bc83c85d0522023ea6e404bff4aaed135c47815a`. The active Protect Main ruleset
`19156572` requires `pylint (3.12)` and `pytest (3.12)`. On `main`, pytest remains unpinned. The fix branch pins `pytest==9.1.1`,
enforces the 16-entry manifest, and adds executable-line contract tests. CodeQL
checks pass when produced but are not required.

## Binding amendments from review

1. `tests/test_ci_contract.py` will be added to the manifest, taking it from
   15 to 16 entries.
2. The contract test must protect both exact pins, the complete
   `python -m pytest -q` command, and the dedicated manifest-checker invocation,
   all scoped to the named workflow jobs.
3. The checker must validate strict repository-relative manifest syntax,
   reject duplicates and malformed entries, require file existence, and run
   each path separately under `CONVMEM_CONFIG`.
4. Collection success is based only on subprocess return code 0 from
   `python -m pytest --collect-only -q <path>`. Exit code 5 and every other
   nonzero code fail. Human-readable output is diagnostic only.
5. The exact pytest patch version must be selected from fresh Python 3.12
   evidence before the implementation pin is written.

## Review and execution boundary

- Kiro: PASS with conditions.
- ChatGPT: PASS with conditions; the two conditions above are now binding.
- Codex: architecture/execution/VERIFY/handoff owner.
- Cursor: implementation only after Ryan authorization.
- Ryan: owns branch/execution authorization, disposable PRs, external GitHub
  state, bypass decisions, and merge.

No implementation or disposable experiment is authorized by this handoff.
Pinwheel must not modify Protect Main, CodeQL, status context names, runtime
code, production data, or general collection-count policy.

## Next action

Ryan reviews the planning package and decides whether to authorize Cursor's
implementation from current `main`. If authorized, Cursor must record the
fresh-runner version choice, implement the locked contract, run focused checks,
and return for the Ryan-authorized negative controls.

## Merge reading

- [`STATUS-pinwheel-pytest-ci.md`](../plans/STATUS-pinwheel-pytest-ci.md)
- [`ARCHITECTURE-pinwheel-pytest-ci.md`](../plans/ARCHITECTURE-pinwheel-pytest-ci.md)
- [`EXECUTION-pinwheel-pytest-ci.md`](../plans/EXECUTION-pinwheel-pytest-ci.md)
- [`VERIFY-pinwheel-pytest-ci.md`](../plans/VERIFY-pinwheel-pytest-ci.md)
- [`LATEST.md`](LATEST.md)


## Implementation status (Cursor)

- **Branch:** `fix/2026-08-16-pinwheel-pytest-ci`
- **Local verification:** 19 contract tests; manifest checker; full suite (2 pre-existing failures isolated)
- **Pending:** implementation PR (V3d); disposable GitHub controls (V0d, V5c–V5d); restoration (V6a)
- **Compare:** https://github.com/alanmz-crypto/convmem/compare/main...fix/2026-08-16-pinwheel-pytest-ci
