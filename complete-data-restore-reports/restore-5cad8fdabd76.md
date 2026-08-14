# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-08-13T22:16:19Z
- finished: 2026-08-13T22:16:20Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-qfzi4lg9/wrong-root'] do not match data root [/tmp/convmem-restic-t1-qfzi4lg9/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=5cad8fdabd76fb5883f09ad0c174a139777774bb46f6bc60c4717dbbdf5ac3c3 |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-qfzi4lg9/wrong-root'] do not match data root [/tmp/convmem-restic-t1-qfzi4lg9/data-root] |

