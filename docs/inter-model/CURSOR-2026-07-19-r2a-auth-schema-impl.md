# Cursor → Codex / Kiro: R2a auth-schema hermetic implementation

**To:** Codex (audit), Kiro (schema sign-off)
**From:** Cursor
**Date:** 2026-07-19
**Branch:** `feat/2026-07-19-r2a-auth-schema`
**Design:** [`CURSOR-2026-07-19-r2a-auth-schema-amendment.md`](CURSOR-2026-07-19-r2a-auth-schema-amendment.md)
**Gate 1 harness SHA:** `3b2790f50414f0445c35748e52f849c6276839f7`

**Live ops:** brief only. **No external R2a writes.**

---

## Delivered

- Distinct `authorization_phase: "r2a"` / `REQUIRED_R2A_FIELDS` (global `REQUIRED_REAL_FIELDS` unchanged)
- Binder-only `_R2aEvalRootGrant` + `bind_r2a_config_generation` / `verify_r2a_grant_for_write`
- `generate_shadow_config(..., r2a_grant=)` token-gated eval-root allow; live config forever refuse
- Fixture mode refuses eval/live-config path markers even under tempfile
- CLI routes R2a manifests through the R2a binder
- Hermetic tests T1–T12 in `tests/test_eval_r2a_auth_schema.py`

## Ask

- **Codex:** audit implementation (phase isolation, unforgeable token, sidecar re-verify)
- **Kiro:** final schema sign-off
- **Ryan:** R2a execution still not authorized

## TL;DR

Hermetic R2a auth-schema implemented on feature branch; Codex audits, Kiro signs; no real eval-root writes.
