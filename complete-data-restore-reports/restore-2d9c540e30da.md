# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-08-07T03:49:47Z
- finished: 2026-08-07T03:49:48Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-97k5gqgp/wrong-root'] do not match data root [/tmp/convmem-restic-t1-97k5gqgp/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=2d9c540e30daff47d0295f6743d81ff28914a182d7efce5106e7c124d2b13d6f |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-97k5gqgp/wrong-root'] do not match data root [/tmp/convmem-restic-t1-97k5gqgp/data-root] |

