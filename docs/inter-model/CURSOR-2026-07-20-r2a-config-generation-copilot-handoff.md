# R2a config_generation handoff — Copilot CLI operator (pending exception)

**Updated:** 2026-07-20  
**Authority tip:** #52 squash-merge `6a2bd97af32f331caf47bcde8564c25e88ccbf26` (tree-identical to reviewed head `e585a0955e0e92f556646e2ad9e4277d5ef6d9b0`).  
**Binding plan:** [`../plans/EXECUTION-2026-07-20-post-54-backlog-clear.md`](../plans/EXECUTION-2026-07-20-post-54-backlog-clear.md) Phase D.

## Role split

| Role | Who | Scope |
|------|-----|--------|
| Exact-tip audit (Phase C) | GitHub Copilot audit lane + Kiro | Hermetic authorization implementation in #52 — **done** |
| Later operator (Phase D) | **Copilot CLI operator under a pending one-job R2a exception** | Two bounded `config_generation` invocations only, after Ryan packets |

> Copilot CLI acts as the designated operator for this R2a job only under two exact Ryan authorization packets. This does not establish an execution lane or alter the charter's default routing.

## Exception status

**Pending.** Cursor does **not** assert approval. Ryan grants the one-job exception **together with** the two arm packets (baseline + challenger). Until those packets exist with exact values, no live R2a `config_generation` is authorized.

## Executable scope (matches #52)

Authorized when packets land:

1. Create each approved `out_dir` (mkdir as performed by the binder path).
2. Write `out_dir/shadow.toml`.
3. Bind the approved future `chroma_dir` path into that config.

**Not** part of this authorization: creating Chroma storage directories, R2b, B-Accept, C0, R3–R7, Gate 2, promotion, cleanup, or any other eval-root mutation beyond the above.

Pre/post inventory expects (per arm): `out_dir/` and `out_dir/shadow.toml`. Do **not** require either `chroma_dir` to exist.

## Exclusions

R2b capture; B-Accept; C0; R3–R7; Gate 2 evidence review; promotion; destructive cleanup; live eval-root writes outside packet-bound `out_dir`/`shadow.toml`.

## Two arm packets (templates)

Fill **two** packets (baseline + challenger). Each packet authorizes one `(live_config, out_dir, chroma_dir, embed_model, embed_host)` tuple → one shadow.toml. Manifest remains authoritative; fields below make Ryan’s grant readable without inferring scope from a hash alone.

```text
arm_id: baseline | challenger

manifest_path:
manifest_file_sha256:              # hash of file bytes (inventory)
approved_manifest_body_sha256:     # binder canonical body digest
approval_sidecar_path:
approval_sidecar_expected_contents: # literal digest expected in sidecar

authorization_phase: r2a
execution_mode: real
status: approved
operations: [config_generation]
merged_harness_sha256: 3b2790f50414f0445c35748e52f849c6276839f7
service_policy:
prohibited_actions:

live_config:
out_dir:
chroma_dir:          # path binding only — existence not required by R2a
embed_model:
embed_host:

allowed_directories:
exact_command_tuple:
authorized_revision: 6a2bd97af32f331caf47bcde8564c25e88ccbf26
```

## Partial-failure rules

- Fail mid-arm → **stop**; preserve inventories/artifacts.
- No retry, cleanup, or overwrite without **new** Ryan authorization.
- Sibling arm: if shared state contaminated, do not start; if fully isolated, still require Ryan confirmation before starting the sibling after a failure.

## Procedural controls

- Approved command path only (no generic/manual mkdir outside the authorized command).
- Pre/post read-only inventory of `out_dir/` and `out_dir/shadow.toml` for both arms.
- Diff inventories; stop on unexpected paths.
- Note if the shell is unrestricted (procedural risk).
- Independent post-run verify: **Kiro** (not Copilot CLI self-audit).

## Template text for Ryan (exception + packets)

When ready to authorize (not yet):

```text
ONE-JOB R2A EXCEPTION GRANTED for Copilot CLI operator.
Arms: baseline + challenger packets attached / pasted below.
authorized_revision: 6a2bd97af32f331caf47bcde8564c25e88ccbf26
This does not authorize R2b+, Gate 2, or any other operation.
```

Until Ryan posts that grant with both filled packets, exception remains **pending**.
