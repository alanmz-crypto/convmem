# Kiro Review Handoff — Gate 1 Embedding-Evaluation Hardening

## Review requested

Kiro is asked to perform a same-tip, non-implementing design and safety review
of the corrective implementation on this branch. Do not edit files, commit,
merge, grant execution, or issue a later-phase authorization.

Required verdict: `PASS`, `FAIL` with concrete objections, or `DEFER` with the
missing evidence needed to decide.

Review the exact branch tip that contains this handoff file. The tip must be
checked against the approved corrective plan and the implementation files,
not against chat claims or an earlier branch revision.

## Governing plan identity

- Plan: `docs/plans/EXECUTION-embedding-model-eval-gate1-corrective.md`
- Approved plan commit: `2159ec4dd9b78b5b18dfa04f6d8e435979b4b129`
- Approved plan size: `26,867` bytes
- Approved plan SHA-256: `39849369957cb77e9513c5affa82706ae13042cf48e8ca781b6534c7087a0aa0`
- Historical Gate 1 pin: `3b2790f50414f0445c35748e52f849c6276839f7`

The historical pin remains insufficient for R2b and R3–R7. A new corrective
execution pin has not been issued.

## Implementation under review

- Branch: `fix/2026-08-04-embedding-eval-gate1-hardening`
- Review scope: commits after the approved plan, through the tip containing
  this handoff
- Latest implementation checkpoint before this handoff: `55ded7f`
- Shared worktree: unrelated dirty state remains untouched

The implementation includes manifest-bound model pull and probe operations,
single-use grants, vector-only scoring, source and model identity checks,
query/package binding, ANN repeatability assessment, exact-vector diagnostics,
warm-residency checks, evidence-release primitives, and no-follow absent-only
JSON publication for model-pull and ANN reports.

## Verification available

- Evaluation-specific suite: `285 passed, 32 subtests passed`
- Focused secure-publication suite: `11 passed`
- Ruff: clean for `eval_corpus/secure_fs.py` and
  `tests/test_eval_secure_fs.py` with `--no-cache`
- `git diff --check`: clean
- No live model pull, production-corpus access, production Chroma access,
  R2b capture, R3 probe, R4/R5 build, R7 comparison, Gate 2 action, or
  promotion occurred

The full repository suite produced unrelated failures caused by the read-only
sandbox and pre-existing areas such as production writer locks, Restic `/tmp`
ownership behavior, and legacy CLI/MCP tests. Those failures were not changed
or repaired by this lane.

## Review questions

1. Does every real operation remain fail-closed and bound to the approved
   source, manifest, operation, attempt, paths and single-use grant?
2. Do model acquisition and probing remain separate, with no live operation
   reachable from fixture-only tests?
3. Do output writers preserve absent-leaf, no-follow, regular-file and
   single-link invariants under pre-existing-file and symlink races?
4. Does the implementation preserve the approved C0a/C0b boundary, unified-pin
   policy, production-swap objective, vector-only scoring rule, technical
   status/evidence verdict separation, ANN instability rule and latency stop
   rule?
5. Are the evidence-release primitives and source checks sufficient for the
   later exact-package review, without implying that implementation tests or
   this review authorize R2b or R3–R7?

## Review-client limitation

The local headless Kiro attempt for the prior implementation tip failed before
review with `attempt to write a readonly database`; it produced no verdict.
This handoff is therefore a routing request, not a Kiro approval.

## Authorization boundary

Corrective implementation and fixture-only Gate 1 testing are authorized by
Ryan's recorded approval. R2b, B-Accept, R3, R4, R5, R7, production corpus or
Chroma access, Gate 2 adjudication, and promotion remain blocked until this
exact final implementation revision receives the required review and a new
corrective execution pin is explicitly issued.
