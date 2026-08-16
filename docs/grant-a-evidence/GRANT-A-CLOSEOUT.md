# Grant A evidence closeout — Arc CodeQL Complex Therapy

| Field | Value |
|---|---|
| Arc | CodeQL Complex Therapy |
| Grant | A (ruleset mutation + positive control) |
| Ruleset | Protect Main `19156572` |
| Positive PR | [#198](https://github.com/alanmz-crypto/convmem/pull/198) |
| Branch | `feat/2026-08-16-2026-08-16-codeql-grant-a` |
| Grant B | **Withheld — not run** |

## Functional result

**Provisionally PASS.** The live `Protect Main` ruleset now requires all five
contexts with the intended integration IDs. PR #198 demonstrated ordinary
merge eligibility (`mergeStateStatus=CLEAN`, `mergeable=MERGEABLE`) with all
five checks successful and no bypass.

## HTTP method deviation (pending ratification)

The execution plan authorized `PATCH /repos/alanmz-crypto/convmem/rulesets/19156572`.

1. **PATCH returned HTTP 404** — see `patch-404-response.txt`.
2. **GitHub's documented ruleset update operation is PUT** — see
   [Update a repository ruleset](https://docs.github.com/en/rest/repos/rules#update-a-repository-ruleset).
3. **A single subsequent PUT** targeted the same ruleset (`19156572`) with the
   exact intended final values — see `put-payload.json` and `put-response.json`.
4. **No further ruleset mutation is authorized** under Grant A or this closeout.

This PUT deviation is **not ratified**. Ryan and Kiro must review the evidence
commit and record an explicit ratification decision before treating the method
deviation as accepted.

### Proposed ratification text (not yet ratified)

> Grant A method deviation accepted: GitHub's documented ruleset-update endpoint
> is PUT, not PATCH. Cursor's PATCH returned 404; the subsequent single PUT
> targeted the same ruleset and intended final values. No further mutation is
> authorized by this ratification.

## Evidence file index

| File | Purpose |
|---|---|
| `ruleset-19156572-pre-patch.json` | Ruleset snapshot before mutation |
| `ruleset-19156572-post-patch.json` | Ruleset snapshot after mutation |
| `ruleset-19156572-semantic-diff.txt` | Machine-readable proof of intended-only change |
| `put-payload.json` | Request body for successful PUT |
| `put-response.json` | HTTP 200 response from successful PUT |
| `patch-404-response.txt` | HTTP 404 response from attempted PATCH |
| `pr198-check-runs-pre-patch.json` | Check-runs captured before ruleset mutation |
| `pr198-check-runs-post-patch.json` | Check-runs captured after ruleset mutation |
| `POSITIVE-CONTROL.md` | Marker for the documentation-only positive PR |
| `GRANT-A-CLOSEOUT.md` | This closeout note |

Fresh post-closeout check evidence for the new PR head after this commit is
reported in the Cursor handback only (not committed, to preserve SHA equality).

## Grant B status

Grant B (disposable negative control, conditional producer probe, cleanup)
remains **withheld**. No disposable PR, workflow edit, producer probe, bypass
exercise, or disposable cleanup was performed.
