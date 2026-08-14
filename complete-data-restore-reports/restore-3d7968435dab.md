# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-07-30T20:42:53Z
- finished: 2026-07-30T20:42:54Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-x9bw4eeb/wrong-root'] do not match data root [/tmp/convmem-restic-t1-x9bw4eeb/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=3d7968435dabe230211102c9aeb1776192bca6b1528270c07f9795f5b8bd7d32 |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-x9bw4eeb/wrong-root'] do not match data root [/tmp/convmem-restic-t1-x9bw4eeb/data-root] |

