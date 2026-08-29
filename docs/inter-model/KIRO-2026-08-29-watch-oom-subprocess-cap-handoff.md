# Implementation Handoff: Bound watch index subprocess to stop recurring OOM

**Date:** 2026-08-29
**Author:** Kiro (design/review)
**For:** Cursor (implementation)
**Authorization:** Ryan, 2026-08-29 (verbal — "use your best judgement" / "go to the next
step" on the convmem-watch OOM incident)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `READY_FOR_PR` |
| **Branch** | `fix/2026-08-29-2026-08-29-watch-index-subprocess-memcap` |
| **Tip SHA** | `b0d2a8f` |
| **Push status** | pushed to origin |
| **PR** | `not opened` |
| **Ryan GATE** | none (routine ops reliability fix; not arc-scoped) |
| **Track A ingest** | this Kiro session `messages.jsonl` |

---

## What to build

Stop `convmem-watch.service` from being OOM-killed (recurring; last: 2026-08-28 23:50, 4G
peak, then crash-loop re-spawning `index --file ~/.codex/history.jsonl`).

**Why this exists:** The watch parent has a known-good ~92MB steady state (fixed in
`dec_prop_20260625_000800_d7fe`). It is currently observed at VmRSS 104MB but **VmPeak
2.6G** — it spikes. Each changed file is indexed via a blocking `subprocess.run` child that
loads the embedding model + Chroma. Under `MemoryMax=4G` / `MemorySwapMax=0`, a parent
spike + one unbounded index child sharing the cgroup with no swap = hard OOM-kill.
`history.jsonl` is not the cause (4.4M, trivial prompts-only parse) — it is just the most
frequent spawn trigger.

Ledger rules out the tempting non-fixes:
- Raising ceiling / adding swap — contradicted by "Do not increase swap when workload
  exceeds RAM".
- Excluding `history.jsonl` — loses prompt data and does not stop the next OOM from a
  Kiro/Cursor rollout file.

---

## Integration point

`watch.py:154` — `_flush_path_subprocess()`, the `cmd` / `subprocess.run` call site.

```python
def _flush_path_subprocess(path: str, *, verbose: bool) -> dict:
    import subprocess
    cmd = _convmem_cli_argv() + ["index", "--file", path]
    # ← wrap cmd in a memory-scoped systemd-run --user --scope when available
    proc = subprocess.run(cmd, text=True, capture_output=not verbose)
    ...
```

---

## Specification

### Inputs

- New optional config keys under [watch] in config.toml: subprocess_memory_max (default
  "2G"), subprocess_memory_high (default "1500M"). Read via existing load_config().
- No env changes.

### Algorithm / behavior

1. Add a helper _scoped_index_cmd(inner_cmd, cfg) -> list[str]:
   - If shutil.which("systemd-run") is present AND running under a user systemd session,
     return:

     ```text
     ["systemd-run", "--user", "--scope", "--quiet",
      "-p", f"MemoryMax={mem_max}",
      "-p", f"MemoryHigh={mem_high}",
      "-p", "MemorySwapMax=0", "--"] + inner_cmd
     ```

   - Else return inner_cmd unchanged (graceful fallback; log once at verbose).

2. _flush_path_subprocess builds inner_cmd as today, then runs _scoped_index_cmd(inner_cmd,
   cfg).
3. If the child is OOM-killed inside its own scope, subprocess.run returns non-zero; the
   existing raise RuntimeError(...) path already surfaces it as [watch] error processing
   <path> without killing the watch unit. Keep that behavior.
4. Do NOT add concurrency handling — the main loop already serializes spawns
   (subprocess.run blocks; one child at a time). Confirm this in the PR description.

### Output / contract

- Existing return {"subprocess": True, "path": path} unchanged.
- On child OOM: watch stays alive, logs one error line for that file, moves on.

### Constants

```python
_DEFAULT_INDEX_MEM_MAX = "2G"
_DEFAULT_INDEX_MEM_HIGH = "1500M"
```

---

## What NOT to build

- Do NOT exclude history.jsonl from watch (rejected — data loss, non-fix).
- Do NOT raise the service MemoryMax or enable swap (ledger-contradicted).
- Do NOT add threading/async concurrency to the spawn loop.
- Do NOT touch the systemd unit file in this PR (the child scope is created at runtime; the
  unit stays as-is). A separate follow-up may profile the parent 2.6G spike — out of scope
  here.

---

## Test expectations

`tests/test_watch_subprocess_memcap.py`:

1. scoped cmd when systemd-run present: monkeypatch shutil.which → returns path; assert
   _scoped_index_cmd prepends systemd-run --user --scope with
   MemoryMax/MemoryHigh/MemorySwapMax=0 and the -- separator before the inner cmd.
2. fallback when absent: shutil.which → None; assert returned cmd == inner cmd unchanged.
3. config override: custom subprocess_memory_max in cfg flows into the -p MemoryMax= arg.
4. non-zero child still raises: monkeypatch subprocess.run → returncode 137 (OOM); assert
   RuntimeError raised (loop-caught, unit survives).

Use fixtures/monkeypatch only; do NOT spawn real systemd-run or index in CI.

---

## Acceptance criteria

- [ ] Index child runs in its own memory-capped scope when systemd-run --user is available;
  graceful passthrough otherwise.
- [ ] A child OOM surfaces as a per-file watch error and does NOT terminate
  convmem-watch.service.
- [ ] Serialized-spawn behavior confirmed (no concurrency added).
- [ ] New config keys documented with defaults; absent config → defaults apply.
- [ ] New tests pass; no regression in existing suite.
- [ ] Ruff / pylint clean per repo gates.

Manual verification (Ryan/Cursor on host): after deploy, systemctl --user restart
convmem-watch, then during an index spawn check systemctl --user status convmem-watch shows
the child in a transient run-*.scope with its own MemoryMax, and unit peak stays well under
4G.

---

## Branch convention

`fix/2026-08-29-watch-index-subprocess-memcap` — off main, NOT the current
feat/…-cg2-d5-rehearsal branch. Push immediately after each commit. Squash OK.

---

## Related files

| What | Path |
|------|------|
| Spawn site | watch.py:154 _flush_path_subprocess |
| CLI argv helper | watch.py _convmem_cli_argv |
| Config loader | config.py load_config |
| Systemd unit (reference only, do not edit) | ~/.config/systemd/user/convmem-watch.service |
| Prior fix (context) | ledger dec_prop_20260625_000800_d7fe (RSS flat at 92MB) |
