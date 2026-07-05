# convmem — Local knowledge corpus

You have access to a local knowledge corpus via convmem. Use it before repeating past work.


1. **`convmem doctor`** — run first. Must exit 0 before any ask/search. Confirms Ollama/Chroma health.
2. **`convmem brief --stdout-only`** — session orientation: corpus state, recent decisions, monitor results, unresolved count. When also calling MCP **`brief()`**, pass **project=<slug>** inferred from cwd (see Tier B).
3. **`convmem unresolved`** — check open observations. Add `--site <hostname>` for client-specific issues (e.g. `--site staging2.willowyhollow.com`). For multiple sites, prefer **separate** `convmem unresolved --site …` calls (or one call without `--site`). Avoid `echo` separators unless comparing output side-by-side.
4. **Before answering history/architecture questions:** use `convmem "search query"` or `convmem ask "question"` to ground responses in the ledger.

**Cursor with shell:** run `convmem doctor` before MCP `brief()` — doctor confirms infra; brief does not.

**Codex-specific:** if `convmem ask` fails with a network error (sandbox blocks localhost), retry with:
```
bash -lc 'convmem ask "your question here"'
```
The `-l` flag sources `~/.zshrc`/`~/.bashrc` where Ollama's PATH is set. For permanent access in the convmem repo: `cp .codex/config.toml.example .codex/config.toml` to enable `network_access = true`.


## Builder reference

Before convmem architecture edits, read the relevant digest in `docs/builder-reference/`.

- `ousterhout-builder-digest.md` for module boundaries and protocol surfaces
- `manning-builder-digest.md` for ranking, chunking, retrieval, and evaluation
- `zeller-builder-digest.md` for reproduction, triage, and verification
- `hard-parts-builder-digest.md` for trade-offs, data ownership, and split decisions

## Read-only guard

Do not run `convmem add`, `convmem index`, or `convmem verify` without user direction.

## Workflow routing (when unsure)


**Cheat sheet:** `docs/MODEL-WORKFLOW.md` — read when lost.

| If cwd / task is… | Read first | Run |
|-------------------|------------|-----|
| Any session | — | `convmem doctor` → `brief` → `unresolved` |
| `~/Projects/convmem` + cross-project digest | `docs/CROSS-PROJECT-DIGEST-ATTEMPTS.md` | `scripts/cross-project-digest.sh --skip-ask`; smoke: `scripts/smoke-cross-project-digest.sh` |
| `~/Projects/convmem` + architecture | `docs/builder-reference/README.md` | matching digest, then code |
| `~/Projects/convmem-lab` | `docs/lab-reference/NOTES.md` | `scripts/convmem-lab.sh doctor`; `lab/scripts/compile-synthesis-brief.sh`; `lab/scripts/smoke-synthesis.sh` |
| Session close / record | `docs/inter-model/SESSION-CLOSE-RECORD.md` | output `convmem record` block; Ryan approves |

**Split:** `lab-reference/` = lab gates & synthesis smoke (lab repo). `builder-reference/` = prod architecture. Never mix prod/lab data paths. Lab: no MCP registration. `--propose` on prod digest: Ryan-gated.

**Codex / DeepSeek:** verify shipped work via `docs/CODEX-DEEPSEEK-VERIFY.md` (independent checklist — do not trust chat claims alone).


Full cheat sheet: `docs/MODEL-WORKFLOW.md`

## Verify shipped work (Codex / DeepSeek)

Independent checklist: `docs/CODEX-DEEPSEEK-VERIFY.md` — pytest, smoke scripts, MCP spot-checks. Do not trust prior chat claims without running it.
