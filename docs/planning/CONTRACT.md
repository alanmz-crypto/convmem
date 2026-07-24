# Planning Guide Contract v2

**Probe Version:** v2

Python module `planning_contract.py` is the single source of truth. This
file mirrors it for human readers.

## Required headings

Every phase guide under `docs/planning/` (except `CONTRACT.md` and
`EXECUTION-CLOSURE-*.md`) must contain:

- `## Phase Initialization`
- `## Objective`
- `## Responsibilities`
- `## Exit Criteria`

## Required metadata

The Phase Initialization section must name these fields:

- Phase
- Characters
- Functions
- Lanes
- Authority
- Probe Version

The Phase Initialization table must include the **exact** current probe version
value (`v2` while Contract v2 is active), not merely the field label.

## Structure vs operational content

Contract v2 verifies **structure only** (headings, metadata field names, exact
probe version value, HITL stop lines). A guide may pass doctor while
Objective/Responsibilities remain TBD — that means the skeleton is valid, not
that the phase is operational.

## Required exit intent

Every guide must contain:

- `Active phase lane must stop here.`
- `Await HITL.`

## Future versions

When adding sections (e.g. `## Verification`), bump to Contract v3 and
probe version — do not silently change v2 expectations.
