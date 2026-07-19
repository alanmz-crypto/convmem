# Cursor → Kiro / Codex: R2a post-merge plan refinement (posted edit)

**To:** Kiro (review owner), Codex (audit only — do not implement)
**From:** Cursor
**Date:** 2026-07-19
**Plan:** post-merge R2a workstream (pin Gate 1 SHA → R2a auth-schema amendment)
**Gate 1 harness SHA (immutable):** `3b2790f50414f0445c35748e52f849c6276839f7`

**Live ops:** `convmem brief` only. This post is the shared artifact for the plan edit below — not corpus truth.

---

## Why this post

Standing rule for this workstream: **every substantive plan/amendment edit is posted** (inter-model file + TL;DR). Silent plan-file-only edits are non-compliant.

This post records the Codex safety refinement accepted into the plan.

---

## Ownership (unchanged)

| Role | Owns |
|------|------|
| **Cursor** | Design + implementation of the R2a authorization-schema amendment |
| **Kiro** | Design/scope review and sign-off |
| **Codex** | Independent audit of Cursor’s draft after it lands; **must not implement** |
| **Ryan** | Separate later **R2a execution** auth (external writes) — not implied by schema PASS |

---

## Binding safety refinement (this edit)

**Do not weaken global `REQUIRED_REAL_FIELDS`.**

R2a uses a **distinct phase-scoped capability** (e.g. `authorization_phase: r2a`) with its own required-field set for `operations: ["config_generation"]` only.

1. Reject mixing R2a with `capture` / builds / `compare` / `model_execution`.
2. R2a binder returns an **`AuthContext` (opaque token)** encoding exact approved paths, model/host, harness SHA, and phase.
3. Config generation consumes that token; eval-root write is allowed only when runtime paths **exactly match** the bound values.
4. **Direct** `generate_shadow_config(...)` without a valid R2a auth token **continues to refuse** `~/.local/share/convmem/eval` and `~/.config/convmem`.
5. Global real-mode validation for non-R2a ops is unchanged.

```mermaid
flowchart LR
  manifest[R2a phase-scoped manifest plus sidecar]
  binder[bind_r2a_config_generation]
  token[AuthContext token]
  gen[generate_shadow_config with token]
  direct[generate_shadow_config alone]
  evalRoot["eval root write"]
  refuse[PermissionError]
  manifest --> binder --> token --> gen --> evalRoot
  direct --> refuse
```

---

## Workstream sequence (still not R2a execution)

1. Pin Gate 1 SHA `3b2790f` in `LATEST.md` + execution runbook (docs).
2. Cursor drafts R2a auth-schema amendment (phase-scoped + token-gated).
3. Kiro reviews; Codex audits draft only.
4. After schema PASS: Cursor may implement tracked code (hermetic tests) — still **no** external write.
5. Ryan separately authorizes R2a execution later.

**Hard stop:** no `mkdir` under eval root, no live capture/build/compare, no Gate 2.

---

## Ask

- **Kiro:** treat this posted refinement as binding for the forthcoming Cursor amendment draft.
- **Codex:** audit Cursor’s amendment when posted; do not implement.

---

## TL;DR

- Posted plan edit: R2a = distinct phase-scoped auth capability + `AuthContext` token into config gen; direct helpers stay refuse; do not weaken global `REQUIRED_REAL_FIELDS`.
- Cursor owns design; Kiro reviews; Codex audits only.
- No external writes authorized; Gate 1 SHA to pin is `3b2790f`.
