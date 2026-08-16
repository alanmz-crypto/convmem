# kiro-cli session transcripts (jsonl_kiro_session)

kiro-cli 2.x stores **full agent chat transcripts** at:

```
~/.kiro/sessions/
  <hash>/
    sess_<uuid>/
      messages.jsonl    ← indexed
      session.json
    snapshots/          ← excluded
  cli/
    *.history           ← excluded (thin prompt sidecars only)
```

This is **kiro-cli transcript storage** — not a separate “Kiro IDE” product. Soak docs called it “vibe mode”; on disk it is the same `kiro-cli` binary you run in the terminal.

## This document is a living reference — add gaps when you find them

Not every adapter edge case or Track A limitation is documented here. If you
encounter a situation where Track A behaves unexpectedly (silent 0-chunk ingest,
unrecognized format, missing transcript, intentional exclusion), check whether
it is already explained in this file. If it is not, **add a section before
closing the session** — include what happened, why it is by design (or whether
it is a real bug), and what the correct model protocol is.

The goal is that the next model hitting the same wall finds the answer here
instead of rediscovering it from scratch.

## kiro-cli chat sessions (Track A gap — by design)

`kiro-cli chat` (the terminal chat command) writes **only** a thin prompt sidecar
at `~/.kiro/sessions/cli/<id>.history`. That file contains Ryan's input text
only — no model responses, no tool calls. Indexing it would produce misleading
half-conversation units, so it is intentionally excluded.

**There is no full `messages.jsonl` for `kiro-cli chat` sessions.** The binary
does not write one. This is a product gap in `kiro-cli chat`, not a convmem
adapter bug.

**What to do when Track A is blocked in a `kiro-cli chat` session:**

1. Acknowledge the block clearly — "Track A index is unavailable: this session
   ran via `kiro-cli chat` which does not produce an indexable transcript."
2. Do **not** attempt to index the `.history` sidecar — it silently ingests
   nothing (0 chunks) and provides false reassurance.
3. Substitute with a verbal session summary at handoff so Ryan and the next
   model have the context that would otherwise be in the corpus.
4. Note the gap in any handoff doc or LATEST bullet so downstream lanes know
   this session is not in the index.

This is **not a project flaw** — it is a known, intentional design boundary.
If Ryan later needs this session's content in the corpus, the only path is a
manual summary document that can be indexed as an inter-model doc or markdown
artifact.

## Legacy sqlite

Chats through ~April 2026 may still live in `~/.local/share/kiro-cli/data.sqlite3` (`sqlite_kiro` adapter). That live DB must **not** be watch-indexed (OOM risk). Refresh via:

```bash
scripts/index-kiro-cli-snapshot.sh
```

## Config

Add to `~/.config/convmem/config.toml` (see [config.example.toml](../config.example.toml)):

```toml
"~/.kiro/sessions",
```

## Backfill (Ryan — count before bulk)

Some sessions contain sensitive client context. Count first:

```bash
find ~/.kiro/sessions -name messages.jsonl \
  -not -path '*/snapshots/*' -not -path '*/cli/*' | wc -l
```

After approving the count:

```bash
find ~/.kiro/sessions -name messages.jsonl \
  -not -path '*/snapshots/*' -not -path '*/cli/*' \
  -exec convmem index --file {} \;
```

## Verify

```bash
convmem search "convmem doctor"
```

A hit with `source_path` under `~/.kiro/sessions/` confirms the pipeline.

## Detection

`adapters/detect.py` matches:

```python
path.name == "messages.jsonl"
and path.parent.name.startswith("sess_")
and "snapshots" not in path.parts
```

Tool metadata tag: `kiro` (same as legacy sqlite).
