# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-07-29T16:55:44Z
- finished: 2026-07-29T16:55:45Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-6kdffsh0/wrong-root'] do not match data root [/tmp/convmem-restic-t1-6kdffsh0/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=3de5d07fc0e1dcbca9f8521d1d0c5f031601865fcb617f1b8e25cfee5edce6a9 |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-6kdffsh0/wrong-root'] do not match data root [/tmp/convmem-restic-t1-6kdffsh0/data-root] |

