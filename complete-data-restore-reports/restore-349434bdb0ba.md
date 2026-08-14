# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-07-29T01:48:08Z
- finished: 2026-07-29T01:48:08Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-7tj_rf6h/wrong-root'] do not match data root [/tmp/convmem-restic-t1-7tj_rf6h/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=349434bdb0baee2a48f1ace573e0c39ff308a99e2466da06b0fd2d404a778dd1 |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-7tj_rf6h/wrong-root'] do not match data root [/tmp/convmem-restic-t1-7tj_rf6h/data-root] |

