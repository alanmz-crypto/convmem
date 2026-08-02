# Safe-Work Lane Test Strategy

**Status:** planning-only; no test execution authorized

**Freeze boundary:** the deployed checkout remains at
`76126e07a97187f68d925dd8b431d2d03967084f` through 2026-08-07 00:00 UTC.

## Purpose

Define the test-planning boundary for safe work while the deployed checkout is
frozen. This document does not authorize tests, code changes, generated
artifacts, ledger writes, service control, or changes to live state.

## Scope inventory

Before implementation, the authorized implementer should inventory existing
tests, including `tests/test_doctor.py`, and map them to these planning areas:

- doctor and standing-check reporting;
- frozen-checkout and writer-gate safety assumptions;
- C6 evidence-contract validation;
- retrieval and reranker diagnostic boundaries; and
- documentation-only transition checks.

The inventory should identify coverage gaps and duplicate or environment-
dependent assertions without modifying or executing any test.

## Coverage design

For each selected case, the future test plan should specify inputs, expected
outputs, isolation assumptions, and stop conditions in prose before code is
written. Priority cases are:

1. doctor check aggregation remains deterministic when every check is mocked;
2. the frozen revision is treated as an invariant, never as a value to change;
3. C6 evidence validation rejects payload-bearing or non-hermetic artifacts;
4. retrieval/reranker diagnostics remain synthetic or mocked; and
5. planning documents cannot be mistaken for execution authorization.

The test plan must include a named enumeration of all doctor checks so that
adding a new check without a corresponding mock entry fails the test suite
explicitly rather than silently exercising local environment state.

## Authorization gate

No implementation or test run proceeds until Ryan authorizes the scope and
assigns implementation to Cursor. Any later work order must name the exact
files, test command, allowed artifact locations, and whether writes are
permitted. The implementation lane must re-check the deployed checkout HEAD
before and after its worktree-only activity.

## Stop conditions

Stop and return for review if the work would touch the deployed checkout,
`session-events.jsonl`, Chroma or Shadow state, writer configuration, services,
live sites, external headers, or the ledger; if a test requires live corpus
data; or if the expected result cannot be expressed without changing runtime
configuration.

## Handoff

This strategy is a planning artifact only. It does not close any unresolved
observation, clear either due standing check, lift C6 HOLD, arm C7, enable
Shadow, or authorize a commit, merge, or deployment.
