# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-07-27T22:08:44Z
- finished: 2026-07-27T22:08:45Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-3netsfsb/wrong-root'] do not match data root [/tmp/convmem-restic-t1-3netsfsb/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=952e0dbc35343dae6fd662d2261f09ded30493fcd73864f104998bcc0e3d5c23 |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-3netsfsb/wrong-root'] do not match data root [/tmp/convmem-restic-t1-3netsfsb/data-root] |

