# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-08-07T03:19:34Z
- finished: 2026-08-07T03:19:35Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-t8l9tvmu/wrong-root'] do not match data root [/tmp/convmem-restic-t1-t8l9tvmu/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=a3a5f6326653a78542ab048c52d5920495d1e385f3325b489006e5f8b258342f |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-t8l9tvmu/wrong-root'] do not match data root [/tmp/convmem-restic-t1-t8l9tvmu/data-root] |

