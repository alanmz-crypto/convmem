# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-07-31T18:41:16Z
- finished: 2026-07-31T18:41:17Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-wuvj9xvq/wrong-root'] do not match data root [/tmp/convmem-restic-t1-wuvj9xvq/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=0493666b6c6bc21097902e9ee3096f5ae7f1a3691e4b8987df2cd22b2280d0a8 |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-wuvj9xvq/wrong-root'] do not match data root [/tmp/convmem-restic-t1-wuvj9xvq/data-root] |

