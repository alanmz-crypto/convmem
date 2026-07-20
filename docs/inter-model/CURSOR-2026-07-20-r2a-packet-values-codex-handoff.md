# Cursor → Codex: propose filled R2a permission packets

**Updated:** 2026-07-20  
**From:** Cursor (Phase D after #52 merge)  
**To:** Codex  
**Why:** Ryan wants the one-job Copilot CLI R2a exception, but does **not** have the concrete path/hash values for the two permission forms. Codex must **find or propose** them. Cursor must not invent them.

## Status (do not re-litigate)

| Item | State |
|------|--------|
| #52 R2a auth (hermetic) | Merged on `main` at `6a2bd97af32f331caf47bcde8564c25e88ccbf26` |
| Tree identity | Reviewed tip `e585a095…` tree == merge SHA tree |
| #51 | Closed superseded |
| Phase D docs PR | [#59](https://github.com/alanmz-crypto/convmem/pull/59) — operator handoff template |
| Live R2a / eval-root writes | **Not authorized** until Ryan accepts **filled** packets |
| Ryan verbal `GRANT: yes` | **Not sufficient alone** — packets were empty |

## Your job (Codex)

1. Read:
   - [`CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md`](CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md)
   - [`../plans/EXECUTION-2026-07-20-post-54-backlog-clear.md`](../plans/EXECUTION-2026-07-20-post-54-backlog-clear.md) Phase D
   - Path contract in [`CURSOR-2026-07-19-r2a-auth-schema-amendment.md`](CURSOR-2026-07-19-r2a-auth-schema-amendment.md)
   - Binder/CLI: `eval_corpus/run_manifest.py` + whatever CLI entry creates R2a manifests / shadow.toml
2. Discover or propose **exact** values for **two** packets (baseline + challenger). Prefer existing approved manifests/sidecars if any; otherwise propose new manifest paths + contents Ryan would need to approve, and say so clearly.
3. Return a **paste-ready** block Ryan can accept or edit. Include both packets and the one-line exception grant text from the Phase D handoff.
4. For hashes: compute from real file bytes when files exist; if proposing new manifests, mark hashes `PENDING_AFTER_WRITE` and list the create steps (Ryan/Cursor) — do not write eval-root yourself.

### Known live defaults (hints only — verify)

From Ryan’s machine at handoff time (re-read; do not trust stale):

- Live config: `/home/lauer/.config/convmem/config.toml`
- `embed_model`: `nomic-embed-text`
- Ollama host field in config: `http://localhost:11434` (map to packet `embed_host` only if binder expects that same string)
- Canonical eval layout: `~/.local/share/convmem/eval/<run_id>/{baseline,challenger}/` with `shadow.toml` under each; `chroma/` path bound but **need not exist** for R2a

Pick a concrete `run_id` (date-slug) and spell full absolute paths.

### Packet fields Codex must fill (each arm)

```text
arm_id: baseline | challenger
manifest_path:
manifest_file_sha256:
approved_manifest_body_sha256:
approval_sidecar_path:
approval_sidecar_expected_contents:
authorization_phase: r2a
execution_mode: real
status: approved
operations: [config_generation]
merged_harness_sha256: 3b2790f50414f0445c35748e52f849c6276839f7
service_policy:
prohibited_actions:
live_config:
out_dir:
chroma_dir:
embed_model:
embed_host:
allowed_directories:
exact_command_tuple:
authorized_revision: 6a2bd97af32f331caf47bcde8564c25e88ccbf26
```

Also propose `exact_command_tuple` as the real CLI invocation(s) for baseline then challenger (from code/docs — not a guess of flags that do not exist).

## Hard stops

- Do **not** write under `~/.local/share/convmem/eval/`
- Do **not** create/approve sidecars on disk unless Ryan separately authorizes that step
- Do **not** run Copilot CLI / live `config_generation`
- Do **not** authorize R2b+, Gate 2, promotion, or cleanup
- Do **not** merge to `main`

## Done when

You paste back to Ryan:

1. Two filled packets (or “propose create manifests first” with full proposed file bodies + paths).  
2. Exception grant text.  
3. Short note: what you verified vs what is still pending (e.g. sidecar not on disk yet).  
4. Recommended next owner after Ryan accepts (usually Copilot CLI operator, then Kiro verify).

## Ryan note

You do not need to invent paths. Accept, edit, or reject Codex’s proposal. Empty packets + “yes” still means **no run**.
