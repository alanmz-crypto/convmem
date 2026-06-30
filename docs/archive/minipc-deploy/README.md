# Archived — miniPC deploy (abandoned 2026-06)

**Status:** Historical only. **Do not run** these scripts or follow this guide for current ops.

The separate always-on miniPC as canonical corpus host was abandoned. convmem runs on one workstation; watch/refine/monitor use user systemd units on that machine.

**Current ops:** [`docs/SYSTEMD-DEPLOY.md`](../../SYSTEMD-DEPLOY.md) and [`scripts/deploy-always-on.sh`](../../../scripts/deploy-always-on.sh).

## Contents (restored from git, 2026-06-30)

| File | Was at |
|------|--------|
| [`MINIPC-DEPLOY.md`](MINIPC-DEPLOY.md) | `docs/MINIPC-DEPLOY.md` |
| [`deploy-minipc.sh`](deploy-minipc.sh) | `scripts/deploy-minipc.sh` |
| [`remote-deploy-minipc.sh`](remote-deploy-minipc.sh) | `scripts/remote-deploy-minipc.sh` |
| [`ssh-askpass.sh`](ssh-askpass.sh) | `scripts/ssh-askpass.sh` (password SSH helper for remote deploy) |

Ledger context: `dec_convmem_dev_machine_canonical` — dev machine is canonical; miniPC was cold standby briefly, then reverted.
