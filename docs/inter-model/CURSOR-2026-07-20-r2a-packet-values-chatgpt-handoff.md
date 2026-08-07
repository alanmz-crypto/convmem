# Cursor → ChatGPT Cloud: propose / confirm R2a permission packets

**Updated:** 2026-07-20  
**From:** Cursor (Phase D after #52 merge)  
**To:** ChatGPT Cloud (strategy / synthesis — no code edits, no prod writes)  
**Why:** Ryan wants filled permission forms for the one-job Copilot CLI R2a exception. He does not invent path/hash values himself. **Codex is reserved for intense local work** — this packet-discovery job is ChatGPT’s lane.

## Lane note

| Lane | Role here |
|------|-----------|
| ChatGPT Cloud | Propose or confirm the two packet bodies + grant wording |
| Cursor | After Ryan ACCEPT: write manifests/sidecars on disk; recompute hashes; post filled grant |
| Copilot CLI | Later operator — runs only after filled grant |
| Kiro | Independent post-run verify of the two `shadow.toml` files |
| Codex | **Not** this job — keep for heavy local investigation |

## Status (do not re-litigate)

| Item | State |
|------|--------|
| #52 R2a auth (hermetic) | Merged on `main` at `6a2bd97af32f331caf47bcde8564c25e88ccbf26` |
| Phase D docs PR | [#59](https://github.com/alanmz-crypto/convmem/pull/59) |
| Live R2a / eval-root writes | **Not authorized** until Ryan accepts **filled** packets |
| Prior Codex draft | Exists in chat (nomic vs mxbai under `2026-07-20-r2a-nomic-vs-mxbai`) — treat as **draft input**, not grant |

## Your job (ChatGPT)

1. Read (or use pasted excerpts from Ryan):
   - [`CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md`](CURSOR-2026-07-20-r2a-config-generation-copilot-handoff.md)
   - Path contract in [`CURSOR-2026-07-19-r2a-auth-schema-amendment.md`](CURSOR-2026-07-19-r2a-auth-schema-amendment.md)
   - Optional: the Codex draft bodies Ryan already saw (baseline = `nomic-embed-text`, challenger = `mxbai-embed-large:latest`)
2. Either **confirm** that draft with path newlines fixed, or **propose edits** with clear rationale.
3. Return paste-ready text for Ryan: two manifest JSON bodies + grant one-liner. Mark all hashes `PENDING_AFTER_WRITE` unless Ryan pasted real file digests.
4. Do not claim files exist on disk. Do not authorize the Copilot run.

### Known live defaults (hints — Ryan/Cursor verify)

- Live config: `/home/lauer/.config/convmem/config.toml`
- Live embed today: `nomic-embed-text` @ `http://localhost:11434`
- Eval layout: `~/.local/share/convmem/eval/<run_id>/{baseline,challenger}/` → `shadow.toml`; `chroma/` path bound only

### Exact commands (after grant only — do not tell anyone to run yet)

```bash
python3 scripts/eval_shadow_config_gen.py \
  --run-manifest <baseline_manifest.json> \
  --live-config /home/lauer/.config/convmem/config.toml \
  --out-dir /home/lauer/.local/share/convmem/eval/2026-07-20-r2a-nomic-vs-mxbai/baseline \
  --chroma-dir /home/lauer/.local/share/convmem/eval/2026-07-20-r2a-nomic-vs-mxbai/baseline/chroma \
  --embed-model nomic-embed-text \
  --embed-host http://localhost:11434

python3 scripts/eval_shadow_config_gen.py \
  --run-manifest <challenger_manifest.json> \
  --live-config /home/lauer/.config/convmem/config.toml \
  --out-dir /home/lauer/.local/share/convmem/eval/2026-07-20-r2a-nomic-vs-mxbai/challenger \
  --chroma-dir /home/lauer/.local/share/convmem/eval/2026-07-20-r2a-nomic-vs-mxbai/challenger/chroma \
  --embed-model mxbai-embed-large:latest \
  --embed-host http://localhost:11434
```

(Adjust paths if you change `run_id` or model names.)

## Hard stops

- No code edits; no prod writes; no eval-root writes
- No Copilot CLI / live `config_generation`
- No R2b+, Gate 2, promotion, cleanup
- Empty packets + verbal “yes” = **no run**

## Done when

Paste to Ryan:

1. Confirmed or revised baseline + challenger JSON bodies (single-line paths).  
2. Exception grant text (pending until Cursor writes files + hashes).  
3. What Ryan should say next: `ACCEPT` / `ACCEPT AND GRANT` / `EDIT` / `REJECT` to Cursor.

## Ryan note

You can skip a new ChatGPT pass and reply `ACCEPT` to Cursor on the cleaned Codex draft if you already like it. ChatGPT is optional confirmation when you want a second opinion without burning a Codex session.
