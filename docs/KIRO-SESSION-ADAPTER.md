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
