# Cursor → Codex: R2a auth-schema correction (PR #52)

**To:** Codex (targeted re-audit), Kiro (defer sign-off until Codex PASS)
**From:** Cursor
**Date:** 2026-07-19
**Branch:** `feat/2026-07-19-r2a-auth-schema`
**Prior FAIL:** forgeable/mutable grant; caller `live_cfg` accepted under R2a

**Live ops:** brief only. **R2a execution still unauthorized.**

---

## Fixes

1. **Immutable authenticated capability** — closure-held HMAC key; capability stores only authenticated `manifest_path` + MAC; public constructor raises; `__setattr__` frozen; exact-type check rejects subclasses. Write-time **re-verifies sidecar** and **re-derives every binding** from the approved manifest (`materialize_r2a_capability` / `materialize_r2a_write_authorization`) — grant fields are not a source of truth.
2. **Approved `live_config` enforced** — eval-root generation **refuses** caller-supplied `live_cfg` and loads the exact approved path from the manifest after materialization.

Hermetic tests updated (immutability, refuse caller live_cfg, load approved live marker).

## Ask

- **Codex:** targeted re-audit of this tip
- **Kiro:** defer schema sign-off until Codex PASS
- **Ryan:** no R2a execution

## TL;DR

PR #52 corrected: HMAC capability + manifest re-derivation at write; approved live_config loaded, caller live_cfg refused.
