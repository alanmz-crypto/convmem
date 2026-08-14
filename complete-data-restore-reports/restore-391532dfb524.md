# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-08-07T03:40:11Z
- finished: 2026-08-07T03:40:12Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-tja68cds/wrong-root'] do not match data root [/tmp/convmem-restic-t1-tja68cds/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=391532dfb5245548c28125f10de6a290586bb5bb8ef4ce57d691669d10742130 |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-tja68cds/wrong-root'] do not match data root [/tmp/convmem-restic-t1-tja68cds/data-root] |

