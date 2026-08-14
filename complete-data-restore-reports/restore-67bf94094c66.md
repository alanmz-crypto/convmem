# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-07-29T01:12:27Z
- finished: 2026-07-29T01:12:27Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-0q5fgksc/wrong-root'] do not match data root [/tmp/convmem-restic-t1-0q5fgksc/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=67bf94094c66dbdc1fe92fd77436ca93c0f982bbd513279206f91778de2600dd |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-0q5fgksc/wrong-root'] do not match data root [/tmp/convmem-restic-t1-0q5fgksc/data-root] |

