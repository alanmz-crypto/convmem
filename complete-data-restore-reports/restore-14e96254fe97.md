# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-08-09T00:49:12Z
- finished: 2026-08-09T00:49:13Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-obr4qvnz/wrong-root'] do not match data root [/tmp/convmem-restic-t1-obr4qvnz/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=14e96254fe9768d58027cff99da8ecd46071e1f6f40e6b06c85b53ff25bc42a4 |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-obr4qvnz/wrong-root'] do not match data root [/tmp/convmem-restic-t1-obr4qvnz/data-root] |

