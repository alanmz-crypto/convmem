# Issue: doctor ack/revoke can report refusal after a durable commit when lock close fails

**Status:** Open — required finding from the final closure review of merged tree `4b4796b`.
**Severity:** High — the CLI reports failure after changing durable state, which can lead an operator to retry or misread the acknowledged state.
**Discovered:** 2026-10-25, final closure review.
**Scope:** Post-commit result reporting for `tripwire ack` and `tripwire revoke`; no live data mutation is authorized by this issue.

## Finding

In the reviewed tree, `cpu_tripwire_ack.py:350` can raise from `finally: os.close(fd)` after the store replacement and sync have committed the acknowledgment or revocation. The CLI path in `cpu_tripwire_cli.py:126` then prints `Refused` and exits 1 although the committed record is valid on disk.

The closure probe `lock_close` injects a real kernel EBADF after closing the lock descriptor. Both verbs returned exit 1 and printed the refusal while leaving a valid committed record.

## Acceptance

- [ ] For both ack and revoke, a post-commit close error cannot be reported as a refusal or as an uncommitted operation.
- [ ] The CLI reports the durable outcome accurately, including any cleanup warning.
- [ ] A regression probe confirms the on-disk record and CLI outcome agree for the injected lock-close error.
- [ ] Pre-commit failures still fail without claiming a commit.

<!-- src: /home/lauer/tmp/codex-closure-merged/cpu_tripwire_ack.py, /home/lauer/tmp/codex-closure-merged/cpu_tripwire_cli.py, /home/lauer/tmp/codex-closure-probes.py -->
