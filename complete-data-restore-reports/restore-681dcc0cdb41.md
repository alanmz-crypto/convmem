# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-08-07T03:29:19Z
- finished: 2026-08-07T03:29:20Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-192i7wjf/wrong-root'] do not match data root [/tmp/convmem-restic-t1-192i7wjf/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=681dcc0cdb41c33077d77e116d16530bc5252a350adf266437f833b1c415cd0e |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-192i7wjf/wrong-root'] do not match data root [/tmp/convmem-restic-t1-192i7wjf/data-root] |

