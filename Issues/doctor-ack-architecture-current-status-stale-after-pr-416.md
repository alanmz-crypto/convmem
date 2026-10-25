# Issue: doctor acknowledgment architecture still states the pre-merge status

**Status:** Open — required documentation finding from the final closure review at Docs PR `#417` head `a0916d4`.
**Severity:** Medium — the binding design directs future readers to repeat completed work and misstates current doctor behavior.
**Discovered:** 2026-10-25, final closure review.
**Files:** `docs/plans/ARCHITECTURE-doctor-fault-acknowledgment.md`; omitted from Docs PR `#417`.

## Finding

Docs PR `#417` updates current-state claims that agree with the checked Git, GitHub, service, and disk state, but it omits the binding architecture. At reviewed head `a0916d4`, that document still presents PR `#416` as open and says `convmem doctor` fails for the current boot. The implementation PR was squash-merged on 2026-10-24 at `4b4796b`.

The review reported this check against the Docs checkout:

```sh
rg -n 'Phase:|PR #416 is open|Today.*doctor|After this design is implemented' docs/plans/ARCHITECTURE-doctor-fault-acknowledgment.md
```

## Follow-up

Update the architecture's current-state framing to reflect the merged implementation and present status while retaining dated design rationale and historical decisions. Keep the correction within the document's current-state sections.

## Acceptance

- [ ] The binding architecture no longer presents PR #416 as open or the old boot-specific doctor failure as current.
- [ ] Dated design history and rationale remain intact.
- [ ] The Docs PR includes this architecture file and its resulting claims are checked against the reviewed Git and live state.

<!-- ref: ../docs/plans/ARCHITECTURE-doctor-fault-acknowledgment.md — binding document with stale post-merge status -->
<!-- src: /home/lauer/tmp/codex-closure-docs/docs/plans/ARCHITECTURE-doctor-fault-acknowledgment.md -->
