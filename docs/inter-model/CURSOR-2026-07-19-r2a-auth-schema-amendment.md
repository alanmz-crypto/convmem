# Cursor → Kiro / Codex: R2a authorization-schema amendment (draft)

**To:** Kiro (schema sign-off), Codex (implementation audit — do not implement)
**From:** Cursor
**Date:** 2026-07-19
**Base:** `main` @ `b307a8a` (includes merged PR #45 refinement posts)
**Gate 1 harness SHA (immutable):** `3b2790f50414f0445c35748e52f849c6276839f7`
**Prior binding posts:**
- [`CURSOR-2026-07-19-r2a-plan-refinement.md`](CURSOR-2026-07-19-r2a-plan-refinement.md)
- [`CURSOR-2026-07-19-r2a-codex-pass-token-constraints.md`](CURSOR-2026-07-19-r2a-codex-pass-token-constraints.md)

**Live ops:** `convmem brief` only. This amendment is tracked design for hermetic schema work. **No external R2a writes are authorized.**

---

## TL;DR

- Introduce a **distinct** `authorization_phase: "r2a"` real-manifest capability; **do not** weaken global `REQUIRED_REAL_FIELDS`.
- Eval-root writes require a **binder-only unforgeable grant token**, plus `authorization_phase == "r2a"` and **original sidecar** re-verify — not path-string matching alone.
- Direct `generate_shadow_config(...)` without that grant continues to refuse `~/.local/share/convmem/eval` and `~/.config/convmem`.
- Implementation + hermetic tests are Cursor-owned; Codex audits the code; Kiro issues final schema sign-off. Ryan R2a **execution** remains a separate later gate.

---

## Problem

Real R2a (isolated eval dirs + `shadow.toml` only) is schema-blocked:

1. `validate_run_manifest_schema` applies full `REQUIRED_REAL_FIELDS` to every `execution_mode=real` manifest — corpus/query/uncertainty fields do not exist yet at R2a.
2. `generate_shadow_config` unconditionally refuses `/.local/share/convmem/eval` and `/.config/convmem`.
3. Existing public `AuthContext` dataclass is caller-constructible and must **not** unlock eval-root writes.

---

## Non-goals (this amendment)

- No `mkdir` / writes under the real `~/.local/share/convmem/eval` tree in CI or agent sessions under this auth.
- No R2b capture, B-Accept, C0, R3–R5, R7, Gate 2, R8, promotion.
- No weakening of global real-manifest validation for capture/build/compare/model_execution.
- No Codex implementation.

---

## Canonical path contract (R2a)

| Role | Path |
|------|------|
| Eval root | `~/.local/share/convmem/eval/<run_id>/` |
| Baseline arm | `…/<run_id>/baseline/` → `shadow.toml`, `chroma/` |
| Challenger arm | `…/<run_id>/challenger/` → `shadow.toml`, `chroma/` |
| Live config | **read-only** source (`live_config`); never write under `~/.config/convmem` |
| Live Chroma / data | unreachable / unused |

Hermetic tests must use a **temp path that contains the substring** `/.local/share/convmem/eval` (current forbid check is substring-based) so policy is exercised without touching the real home eval root.

---

## Phase-scoped schema (distinct capability)

### Manifest requirements when `authorization_phase == "r2a"`

| Field | Rule |
|-------|------|
| `authorization_phase` | Exactly `"r2a"` |
| `execution_mode` | `"real"` |
| `status` | `"approved"` |
| `operations` | Exactly `["config_generation"]` (no other ops) |
| `merged_harness_sha256` | Exactly Gate 1 SHA `3b2790f50414f0445c35748e52f849c6276839f7` |
| `paths` | Nonempty; must supply bind targets for `CONFIG_GENERATION_FIELDS` |
| `service_policy` | Present |
| `prohibited_actions` | Present |
| `ryan_approved_manifest_sha256` | Must equal external sidecar digest |
| External sidecar | `<manifest>.approved.sha256` required; `assert_manifest_file_matches_approval` |

**Must not apply** global `REQUIRED_REAL_FIELDS` to R2a manifests. Route validation:

```text
if execution_mode == "real" and authorization_phase == "r2a":
    validate_r2a_manifest_schema(manifest)   # REQUIRED_R2A_FIELDS only
elif execution_mode == "real":
    validate via REQUIRED_REAL_FIELDS        # unchanged
```

### `REQUIRED_R2A_FIELDS` (proposed)

`authorization_phase`, `execution_mode`, `status`, `operations`, `merged_harness_sha256`, `paths`, `service_policy`, `prohibited_actions`

(plus in-file `ryan_approved_manifest_sha256` checked against sidecar as today)

### Reject

- R2a + any of `capture`, `adjudicate`, `baseline_build`, `challenger_build`, `compare`, `model_execution`, `model_exec`
- R2a missing `authorization_phase` or phase ≠ `"r2a"`
- Real non-R2a manifests missing any `REQUIRED_REAL_FIELDS` entry (regression)

---

## Unforgeable grant token

Do **not** use the public `AuthContext` dataclass as the eval-root unlock.

### New type (module-private)

```python
# eval_corpus/run_manifest.py (sketch)
_R2A_SENTINEL = object()

class _R2aEvalRootGrant:
    """Binder-only. Callers cannot construct a valid instance."""

    __slots__ = ("_sentinel", "out_dir", "chroma_dir", "embed_model", "embed_host",
                 "merged_harness_sha256", "manifest_path", "body_sha256", "phase")

    def __init__(self, sentinel, **bound):
        if sentinel is not _R2A_SENTINEL:
            raise PermissionError("R2a grant is binder-only")
        ...
```

- Only `bind_r2a_config_generation(...)` may call `_R2aEvalRootGrant(_R2A_SENTINEL, ...)`.
- Public `AuthContext` remains for other ops; it **never** unlocks eval-root writes.

### Binder: `bind_r2a_config_generation`

1. Require `--run-manifest` (fixture mode **cannot** produce an R2a grant).
2. Load manifest; require `authorization_phase == "r2a"`.
3. `assert_manifest_file_matches_approval` (sidecar + in-file digest).
4. `validate_r2a_manifest_schema`; `assert_operation_allowed(..., "config_generation")`.
5. Exact-bind `CONFIG_GENERATION_FIELDS` against runtime.
6. Verify `merged_harness_sha256` matches Gate 1 pin.
7. Return `_R2aEvalRootGrant` encoding exact resolved paths + body SHA + manifest path + phase.

---

## Config generation consume path

### `generate_shadow_config` signature change

Add optional keyword-only `r2a_grant: _R2aEvalRootGrant | None = None`.

Policy:

| Case | Result |
|------|--------|
| Path under `/.config/convmem` | Always `PermissionError` |
| Path under `/.local/share/convmem/eval` **without** valid grant | `PermissionError` (unchanged default) |
| Eval-root path **with** grant | Allow only if grant.phase == `"r2a"` **and** grant’s stored sidecar body SHA still matches `assert_manifest_file_matches_approval` re-check on `grant.manifest_path` **and** runtime `out_dir`/`chroma_dir`/`embed_model`/`embed_host` exactly equal grant fields |
| Temp / other paths without grant | Current behavior (temp OK for fixtures) |

Re-verify sidecar at write time so a stolen/stale grant object cannot outlive revoked approval.

### CLI `scripts/eval_shadow_config_gen.py`

When `--run-manifest` points at an R2a-phase manifest:

1. Call `bind_r2a_config_generation` (not plain `bind_config_generation`).
2. Pass returned grant into `generate_shadow_config(..., r2a_grant=grant)`.

Plain `bind_config_generation` for non-R2a real manifests must **not** produce a grant; those paths still cannot be eval-root.

---

## Hermetic test matrix (`tests/test_eval_r2a_auth_schema.py`)

All under `tempfile`; no real home eval writes.

| # | Case | Expect |
|---|------|--------|
| T1 | Real non-R2a manifest missing a `REQUIRED_REAL_FIELDS` key | Schema errors (global intact) |
| T2 | R2a manifest without corpus/query fields | Schema OK |
| T3 | R2a + extra op in `operations` | Refuse |
| T4 | R2a wrong `merged_harness_sha256` | Refuse |
| T5 | R2a missing sidecar / mismatched sidecar | Refuse |
| T6 | `generate_shadow_config` to temp path containing `/.local/share/convmem/eval` **without** grant | `PermissionError` |
| T7 | Caller constructs fake grant / public `AuthContext` / random object as grant | Refuse |
| T8 | Valid `bind_r2a_config_generation` + matching paths + grant → write `shadow.toml` under hermetic eval-like temp path | OK |
| T9 | Valid grant but runtime `out_dir` mismatch | Refuse |
| T10 | Valid grant then corrupt sidecar before generate | Refuse on re-verify |
| T11 | Fixture `--authorize-fixture` cannot obtain grant / cannot write eval-like path | Refuse |
| T12 | Direct `generate_shadow_config` to `/.config/convmem`-like temp substring | Refuse always |

---

## Implementation file list (Cursor-owned; after Agent-mode code PR)

| File | Change |
|------|--------|
| `eval_corpus/run_manifest.py` | `REQUIRED_R2A_FIELDS`, `validate_r2a_manifest_schema`, branch in `validate_run_manifest_schema`, `_R2aEvalRootGrant`, `bind_r2a_config_generation` |
| `eval_corpus/shadow_config.py` | `r2a_grant` parameter; token-gated eval-root allow; live config forever refuse |
| `scripts/eval_shadow_config_gen.py` | Route R2a manifests through new binder + grant |
| `tests/test_eval_r2a_auth_schema.py` | Hermetic matrix T1–T12 |
| `docs/plans/EXECUTION-embedding-model-eval.md` | Pin Gate 1 SHA; R2a–R8 table; point at this amendment |

---

## Review ownership

| Role | Action |
|------|--------|
| **Kiro** | Final schema sign-off on this amendment (and follow-on code PR) |
| **Codex** | Audit implementation PR for phase isolation, unforgeable token, sidecar re-verify; **do not implement** |
| **Ryan** | Separate later auth for **R2a execution** (real eval-root writes) |

---

## Status of this post

| Item | State |
|------|--------|
| Design constraints (PR #45) | Merged on `main` (`b307a8a`) |
| This schema amendment draft | Posted for Kiro review |
| Tracked code + hermetic tests | Next Cursor PR (Agent mode required in this Cursor session) |
| R2a execution / external writes | **Not authorized** |

---

## TL;DR (close)

- R2a = distinct `authorization_phase: "r2a"` schema + binder-only `_R2aEvalRootGrant` + sidecar re-verify at write time.
- Global `REQUIRED_REAL_FIELDS` unchanged for non-R2a real ops; direct helpers stay refuse without grant.
- Hermetic test matrix T1–T12 specified; no external R2a writes. Kiro signs schema; Codex audits code only.
