# Inspection Handoff: ComfyUI has no server shutdown path

**Date:** 2026-09-20
**Author:** Crush (investigation lane — non-implementing; no files changed)
**For:** Kiro (review / inspection — confirm or refute the claims below)
**Authorization:** Ryan, 2026-09-20 (verbal — "investigate further", then "create a handoff for kiro to inspect with")

**Arc:** none (ad-hoc)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `INSPECTION_REQUESTED` — no code written, no branch created |
| **Branch** | none created by this handoff |
| **Tip SHA** | upstream `Comfy-Org/ComfyUI` at `ee71d5c4` (v0.36.0), read-only clone at `/home/lauer/GitClones/ComfyUI` |
| **Push status** | n/a — no ComfyUI changes made |
| **PR** | not opened; none proposed |
| **Ryan GATE** | Ryan decides whether any fix is wanted at all. This doc does not request Execute. |
| **Track A ingest** | index this Crush session at handoff |

---

## Consequence first (what changes for the next human/agent)

ComfyUI does not shut down. It only **stops existing**, and the difference is
observable. Asked to "see it disconnect," the honest answer is that nothing in
ComfyUI ever initiates a disconnect: no server teardown, no client close, no
model unload, no VRAM manager deinit.

This matters beyond tidiness because it changes what a user can rely on:

- **Ctrl-C is the only exit that runs cleanup at all.** Every other termination
  (`pkill`, systemd `stop`, `timeout`, closing the shell, IDE stop button)
  skips it entirely.
- **The listening socket is never released deliberately.** A fast restart after a
  non-Ctrl-C kill can hit `EADDRINUSE` (`server.py:1436-1440`) until the OS
  reclaims the port.
- **Live browser/websocket clients are never told the server is going away.** They
  discover it only when the TCP connection dies.
- **No `comfy_aimdo.control.deinit()`**, so on the dynamic-VRAM path the device
  contexts are left to process teardown rather than released in order.

The reason to bring this to Kiro is that the claim is strong ("no shutdown path
exists") and rests on absence-of-code evidence, which is exactly the kind of claim
that needs independent checking rather than acceptance. If any one of the seven
claims below is wrong, a fix would be built on a false premise.

**Not claimed:** this is not a memory leak, not a crash, and not a regression. It
is missing teardown that has apparently never been written. Whether it *should*
be written is Ryan's call, not this doc's.

---

## The 5 Ws

- **Who** — Crush ran the investigation and is handing off. Kiro is asked to
  inspect. Ryan owns the decision on whether a fix proceeds.
- **What** — an absence-of-code claim about ComfyUI's exit path, plus two
  behaviour observations from live test runs.
- **When** — investigated 2026-09-20 against ComfyUI v0.36.0 (`ee71d5c4`).
- **Why** — Ryan asked why ComfyUI does not disconnect when run. The
  answer turned out to be "no shutdown sequence exists", which is a premise a
  future fix would depend on, so it needs review before anyone acts on it.
- **How** — Kiro inspects the claims below against the source at the stated
  revision. No fix is authorized by this document.

---

## What was asked

Ryan asked why ComfyUI does not disconnect every time it is run. The
investigation has two parts: a static reading of the exit path, and two live runs
to confirm behaviour. Both are reported below so they can be checked separately.

---

## The claims to inspect

Each claim is stated so it can be marked **CONFIRMED** or **REFUTED** with a
`file:line` reference. Line numbers are from `ee71d5c4`.

### C1 — `run()` blocks forever, so normal return to the cleanup block is unreachable

`main.py:412-418` gathers `start_multi_address(...)` and `publish_loop()`.

- `start_multi_address` (`server.py:1410-1460`) returns as soon as the sites are
  bound; its body just ends after the `call_on_start` call.
- `publish_loop` (`server.py:1402-1405`) is `while True:` over
  `self.messages.get()`, where `messages` is a plain `asyncio.Queue`
  (`server.py:229`).

`asyncio.gather` with the default `return_exceptions=False` completes only when
all awaitables complete, so the forever-loop holds `run()` open. Therefore
`event_loop.run_until_complete(x)` (`main.py:581`) can only exit by exception,
which in practice means `KeyboardInterrupt`.

**Inspector check:** is there any path that cancels `publish_loop`, puts a
sentinel into `messages`, or otherwise lets `run()` return normally? If yes, C1
is refuted.

### C2 — The only exit hook is reachable only via `KeyboardInterrupt`

`main.py:577-585` is the entire teardown:

```python
    event_loop, prompt_server, start_all_func = start_comfyui()
    try:
        x = start_all_func()
        app.logger.print_startup_warnings()
        event_loop.run_until_complete(x)
    except KeyboardInterrupt:
        logging.info("\nStopped server")
    finally:
        prompt_server.asset_manager.shutdown()
```

**Inspector check:** is there any other `except`/`finally`/`atexit`/context
manager in the launch path that would run on a non-`KeyboardInterrupt` exit?
(`atexit` hits in `comfy/model_management.py:771` and `:813` are
`weakref.finalize(...).atexit = False`, i.e. the opposite of registration.)

### C3 — No signal handler covers `SIGTERM` or `SIGHUP`

`signal.signal(signal.SIGINT, dump_traceback_on_sigint)` at `main.py:67` is
registered only under `args.debug_hang` (`main.py:57`), so even `SIGINT` uses the
default handler on a normal launch.

**Inspector check:** confirm no other `signal.signal(...)` call exists in the
launch path.

### C4 — No server teardown exists

No `runner.cleanup()`, no `site.stop()`, no `client_session.close()`, no
`add_on_shutdown` / `on_cleanup` / `cleanup_ctx` handler. Objects are created at
`server.py:1411` (`AppRunner`), `server.py:1435` (`TCPSite`), and
`server.py:1219-1221` (`ClientSession`).

**Inspector check:** confirm no teardown call site exists anywhere, including in
custom-node-facing hooks or `app/`.

### C5 — Client disconnect cleanup is per-client, not server-side

The websocket `finally` at `server.py:325-327` fires when a **client** leaves.
It is not invoked on server exit, so live sockets are dropped by the OS.

**Inspector check:** confirm nothing iterates `self.sockets` to close them on
server shutdown.

### C6 — Model and VRAM teardown is never called at exit

`unload_all_models()` (`comfy/model_management.py:2098`) has one call site,
`main.py:394`, driven by queue flags in `prompt_worker`. `comfy_aimdo.control`
is imported at `main.py:69` and `init()` is called at `main.py:72`;
`deinit` exists in the module surface (along with `get_devctx` / `devctxs`) but
has no call site.

**Inspector check:** confirm zero call sites for both at exit. Note whether
`comfy_aimdo` is a separate distribution, since its internals may not be in this
repo.

### C7 — `NoAssets` is the default, so the one shutdown handler is near-empty

`default_asset_manager()` (`app/assets/manager.py:220-227`) returns `NoAssets`
unless `--enable-assets`. Both classes' `shutdown()` call `_shutdown_assets()`
(`app/assets/manager.py:86`, `:145`), which is `asset_seeder.shutdown()` plus
`run_shutdown()` (`app/assets/lifecycle.py:145`). `main.py:500-501` already ran
`cleanup_temp_filesystem()` at startup when assets are disabled.

**Inspector check:** confirm that on a default launch the shutdown handler does
no work that was not already done at startup.

---

## Live-run observations

Both runs used `comfyui-env-311`, `--cpu`, `--port <8199|8200>`, with assets
disabled (the default).

### Run 1 — `SIGTERM`

- Process died immediately.
- **Zero** shutdown lines in the log: no `Stopped server`, no shutdown message.
- Consistent with C2 + C3: the `finally` cannot run, because `SIGTERM` has the
  default disposition.

### Run 2 — `SIGINT`

- Process died.
- `Stopped server` **was** logged, confirming the `except KeyboardInterrupt`
  path ran and the `finally` was entered.
- The log also contained `=> cannot schedule new futures after shutdown`, which
  is third-party (ComfyUI-Manager) async work racing interpreter teardown.

**Inspector check:** are these observations reproducible, and is the
ComfyUI-Manager race attributable to the shutdown path or independent of it?
No third-party teardown coordination exists in core, so the race is at minimum
unhandled by core.

---

## What is NOT claimed

- Not a memory leak, crash, or regression — the process exits and the OS
  reclaims resources.
- Not a defect in the asset path. That path is the only cleanup that exists and
  it runs as written.
- Not a request to fix anything. No fix is authorized by this document.
- Not a claim that the missing teardown causes user-visible data loss. No
  evidence of that was found or sought.

---

## What a fix would require (context only — not authorized)

Listed so the size of the change is visible to reviewers, not as a proposal:

1. A `SIGTERM`/`SIGHUP` handler that stops the event loop.
2. A cancellation path for `publish_loop`.
3. `runner.cleanup()` for the sites, and `client_session.close()`.
4. Closing live websockets before exit.
5. `unload_all_models()` and `comfy_aimdo.control.deinit()` before exit.

Items 3 and 5 interact with upstream `Comfy-Org/ComfyUI` ownership, so any fix
here would be an upstream discussion, not a local patch.

---

## Inspection deliverable

Kiro returns one row per claim with a verdict and evidence:

| Claim | Verdict | Evidence (`file:line` or command) |
|-------|---------|-----------------------------------|
| C1 | CONFIRMED / REFUTED | |
| C2 | CONFIRMED / REFUTED | |
| C3 | CONFIRMED / REFUTED | |
| C4 | CONFIRMED / REFUTED | |
| C5 | CONFIRMED / REFUTED | |
| C6 | CONFIRMED / REFUTED | |
| C7 | CONFIRMED / REFUTED | |

Plus: whether the two live-run observations are reproducible, and whether the
conclusion ("ComfyUI has no server shutdown path") follows from the confirmed
claims alone.

**This is an inspection, not a code review.** There is no diff. If Kiro finds the
claim sound, the outcome is the inspection table and nothing else — the decision
about whether to pursue a fix goes back to Ryan.

---

## Related files

Read at `ee71d5c4` in `/home/lauer/GitClones/ComfyUI`:

| What | Path |
|------|------|
| Launch + exit block | `main.py:489-585` |
| Async `run()` / gather | `main.py:412-418` |
| Debug-hang SIGINT handler | `main.py:57-67` |
| aimdo init | `main.py:69-80` |
| prompt_worker (only unload caller) | `main.py:319-409` |
| Server start / runner / site | `server.py:1402-1460` |
| ClientSession setup | `server.py:1219-1221` |
| Websocket handler + per-client finally | `server.py:268-327` |
| Messages queue | `server.py:229` |
| Asset manager selection | `app/assets/manager.py:220-227` |
| Asset shutdown | `app/assets/manager.py:86,145` |
| Shutdown lifecycle | `app/assets/lifecycle.py:145-160` |
| Model unload helper | `comfy/model_management.py:2098-2100` |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file written (commit + push status reported in the handoff message)
- [x] `LATEST.md` bullet added
- [ ] `STATUS-*.md` Update Log — not applicable, this is not a tracked arc
- [ ] Branch pushed — see push status in the handoff message

**Inspector (picking up):**

- [ ] Read this file before inspecting
- [ ] Check each of C1–C7 against the source at `ee71d5c4`
- [ ] Reproduce the two live runs if the static claims are disputed
- [ ] Return the inspection table; do not open a PR or propose a diff
