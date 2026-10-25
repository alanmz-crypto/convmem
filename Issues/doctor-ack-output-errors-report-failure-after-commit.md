# Issue: doctor ack/revoke success-output errors report failure after commit

**Status:** Open — required finding from the final closure review of merged tree `4b4796b`.
**Severity:** Medium — an output failure turns a completed operation into an apparent failure and can prompt unsafe retries.
**Discovered:** 2026-10-25, final closure review.
**Scope:** Post-commit CLI output for `tripwire ack` and `tripwire revoke`; the injected failures were not observed as live failures.

## Finding

The two `typer.echo` calls after `_run_write` commits are unguarded. In the closure probes, injected failures at `first_echo` and `second_echo` left valid committed ack or revoke bytes on disk while the command exited 1. A first-output failure also omitted the completion message.

These probes establish that output errors after commit are presented as operation failures. They do not establish that such an I/O failure occurred during ordinary live use.

## Acceptance

- [ ] For both ack and revoke, failures in either post-commit output call do not imply that the durable operation was refused or rolled back.
- [ ] The CLI exposes the committed outcome truthfully even if secondary output fails.
- [ ] Regression probes cover both output positions and verify valid on-disk state against the reported result.
- [ ] Genuine pre-commit errors retain their existing failure behavior.

<!-- src: /home/lauer/tmp/codex-closure-merged/cpu_tripwire_cli.py, /home/lauer/tmp/codex-closure-probes.py -->
