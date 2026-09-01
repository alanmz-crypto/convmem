# Luna Handoff — [Arc Naturalistic ConvMem product-value evaluation] V2-01C unified corrective

**Status:** `READY_FOR_INDEPENDENT_REVIEW`
**Arc:** Naturalistic ConvMem product-value evaluation
**Agent:** Luna
**Role:** bounded corrective implementer
**G6:** `CLOSED`
**V2-02C:** `NOT AUTHORIZED`

## Exact review target

| Item | Value |
|---|---|
| Corrective parent | `767d176d29abf1d0ca64d7902c6a229652bb85fd` |
| Implementation commit / exact review target | `8e92af9` — `fix: enforce host-held V2 authority admission` |
| Full implementation SHA | `8e92af95aad34edc7d558b38e09c5883d7085ec1` |
| Implementation branch tip (review target) | `8e92af95aad34edc7d558b38e09c5883d7085ec1` |
| Branch | `fix/2026-09-01-naturalistic-v2-01c-authority-boundary-from-359` |
| Push status | pushed to `origin` with explicit refspec |
| Review owner | fresh Kiro or other independent reviewer; Luna must not self-certify |

The implementation SHA is the immutable code/test review target. Any later
documentation-only commit on this branch does not alter those implementation
bytes.

## What changed

Corrective A now requires every authority resolver to be host-provisioned into
a private identity registry before `validate_authority_source()` accepts it.
Resolver shape remains a structural prerequisite, but shape alone is rejected.
The host-provisioned source is held outside claimant-created repositories and
is checked by exact object identity through a weak reference. The existing
positive fixture is provisioned through the internal host integration seam;
there is no public claimant factory or self-registration API.

Corrective B preserves the historical P0 representation. Parsing records
whether `authorized_capture_issuer_grants` was absent. Historical manifests
omit that field on `to_dict()` and therefore recompute their original canonical
bytes, content digest, and artifact ID. New sealing always emits the modern
field, including an explicit empty list when no grants are supplied.

Corrective C determination: **Case 1 — enforcement realization only.** The
issuer-grant record is implementation-level authority metadata that makes the
locked P0 construct/frame and P1 occurrence/evidence authority enforceable; it
does not change the locked stage graph, estimands, scientific constructs, or
Issue #263 source/verbatim/summary axes. The locked canonical contract files
were not changed. No semantic expansion of P0 is claimed by this corrective.

## Exact changed-file inventory

The implementation commit `8e92af95aad34edc7d558b38e09c5883d7085ec1` changes exactly:

- `eval_naturalistic/v2/authority_substrate.py`
- `eval_naturalistic/v2/p0_construct.py`
- `tests/fixtures/naturalistic_v2_p1.py`
- `tests/test_naturalistic_v2_p1_source_backed_authority.py`

The handoff/routing documents are documentation-only follow-up changes.

## Verification at implementation SHA `8e92af95aad34edc7d558b38e09c5883d7085ec1`

| Check | Result |
|---|---|
| Focused authority suite | **58 passed** — `tests/test_naturalistic_v2_p1_source_backed_authority.py` |
| Full V2 selection | **113 passed** — `tests/test_naturalistic_v2_*.py` |
| Broader naturalistic selection | **222 passed, 8 subtests passed** — `tests/test_naturalistic_*.py` |
| Production V2 Pylint error gate | **PASS** — `python -m pylint --persistent=n -E eval_naturalistic/v2` |
| Python compilation | **PASS** — `python -m compileall -q eval_naturalistic/v2` |
| Parent-to-implementation diff check | **PASS** — `git diff --check 767d176..8e92af9` |

The repository-wide Pylint regression wrapper was also run. It reports the
known branch-wide baseline mismatch because `origin/main` predates this V2
implementation (including the documented branch-wide duplicate-code and
new-file findings); the production V2 error-only gate above is the applicable
bounded result. Ruff was not used as an acceptance gate, consistent with the
delegation’s known 80 branch-wide findings.

## Required authority and compatibility outcomes

- Former explicit-source claimant-resolver xfail: now a normal passing
  rejection test; no xfail remains for it.
- Former repository-derived claimant-resolver xfail: now a normal passing
  rejection test; no xfail remains for it.
- Arbitrary resolver-shaped claimant objects cannot pass authority admission.
- Legitimate host-provisioned resolution and full positive P1 verification
  remain passing.
- Historical pre-field P0 canonical bytes are frozen directly in the regression
  test, parse under the new implementation, verify as sealed P0, preserve
  content digest `5891a86576157f9c740c58b77ff0cb352e69ea2efe86c1da93843c2d438a0ad1`,
  preserve artifact ID
  `nps2_construct-freeze-manifest-v2_5891a86576157f9c740c58b77ff0cb352e69ea2efe86c1da93843c2d438a0ad1`,
  and round-trip without introducing the new field.
- Modern P0 sealing preserves an explicitly present empty grants collection,
  and existing positive modern artifacts carry source-issuer grants.
- Issue #263 orthogonality remains intact; source presence, verbatim evidence,
  and summary evidence remain separate and the naturalistic suite passes.
- No forged P1 chain was constructed or executed during this corrective.

## Full repository state

`python -m pytest -q` was **not a PASS**. The run was operator-interrupted at
the 6% progress marker because the repository suite was too slow for this
bounded lane. The captured stream had **148 passed and 7 failures** before the
interrupt; failures had already appeared, so this was not a runtime-only
interruption. A bounded `python -m pytest -q --maxfail=1` rerun reproduced the
first unrelated failure:
`tests/test_add_severity.py::AddSeverityTests::test_invalid_severity_rejected`
(1 failed, 2 warnings in 3.19s; CLI error text capture). No V2 or naturalistic
corrective failure appeared.

## Scope and authorization confirmation

No V2-02C, V2-03C, V2-04/P3, V2-05, V2-06, G6/T0, live episode collection,
Agent A/B execution, scorer/controller work, product-value inference, Issue
#263 reinterpretation, locked canonical-contract change, or unrelated cleanup
was implemented. The security phase remains complete; no additional
end-to-end forgery construction was performed.

I finished: V2-01C unified authority/compatibility corrective
Next step: fresh independent exact-tip review
Next lane: Kiro independent review → Ryan gate
G6: CLOSED
V2-02C: NOT AUTHORIZED

**TL;DR:** Luna’s exact implementation target `8e92af95aad34edc7d558b38e09c5883d7085ec1` closes claimant-resolver admission and historical-P0 canonical drift, with focused/V2/naturalistic tests green; fresh independent review is required before any further grant.
