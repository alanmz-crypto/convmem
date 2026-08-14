# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-07-27T22:01:05Z
- finished: 2026-07-27T22:01:06Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-ofkunwhb/wrong-root'] do not match data root [/tmp/convmem-restic-t1-ofkunwhb/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=90e646e6f48ceadc79bb0ecbf2ac4563352a52796759c759b56ba079112df4f4 |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-ofkunwhb/wrong-root'] do not match data root [/tmp/convmem-restic-t1-ofkunwhb/data-root] |

