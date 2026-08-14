# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-07-27T21:49:39Z
- finished: 2026-07-27T21:49:39Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-6qdsq4ea/wrong-root'] do not match data root [/tmp/convmem-restic-t1-6qdsq4ea/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=0cee7ce1f970124f1aca424e50c6208c37a6a094e87d629d9488bba6cde9dcca |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-6qdsq4ea/wrong-root'] do not match data root [/tmp/convmem-restic-t1-6qdsq4ea/data-root] |

