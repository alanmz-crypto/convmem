# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-08-13T22:29:47Z
- finished: 2026-08-13T22:29:47Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-dab1ggsr/wrong-root'] do not match data root [/tmp/convmem-restic-t1-dab1ggsr/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=f090683bc4f4cdc0b1913aed01665e23d896c237f91e1e3dcdb8af20c49124de |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-dab1ggsr/wrong-root'] do not match data root [/tmp/convmem-restic-t1-dab1ggsr/data-root] |

