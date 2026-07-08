# Planning Guide Contract v1

**Probe Version:** v1

Python module `planning_contract.py` is the single source of truth. This
file mirrors it for human readers.

## Required headings

Every phase guide under `docs/planning/` (except this file) must contain:

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

## Required exit intent

Every guide must contain:

- `Cursor must stop here.`
- `Await HITL.`

## Future versions

When adding sections (e.g. `## Verification`), bump to Contract v2 and
probe version — do not silently change v1 expectations.
