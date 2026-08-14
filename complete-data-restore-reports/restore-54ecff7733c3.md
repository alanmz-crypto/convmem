# Complete-data restore preflight report

- status: **FAIL**
- started: 2026-08-13T20:38:56Z
- finished: 2026-08-13T20:38:57Z
- exit_code: 24
- restic_version: None
- snapshot.id: `None`
- snapshot.tree: `None`
- snapshot.original: `None`
- snapshot.tags: `None`
- snapshot.paths: `None`
- snapshot.repository: `None`
- detail: snapshot paths ['/tmp/convmem-restic-t1-ln_hbhin/wrong-root'] do not match data root [/tmp/convmem-restic-t1-ln_hbhin/data-root]

## Classifications


## Evidence comparisons


## Steps

| # | Step | Status | Detail |
|---|------|--------|--------|
| 1 | resolve_and_restore | RUNNING | id=54ecff7733c36e4e3a3317edb73302b617f6aa58553c82eab37a5500f0eb8c42 |
| 2 | resolve_and_restore | FAIL | snapshot paths ['/tmp/convmem-restic-t1-ln_hbhin/wrong-root'] do not match data root [/tmp/convmem-restic-t1-ln_hbhin/data-root] |

