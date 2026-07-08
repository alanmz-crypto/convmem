# 2026-07-06 — hook deny JSON fix + ksweep

## Hook fix

`_deny()` in `convmem-allow.sh` was emitting only to stderr before `exit 2`. For the `agent` tool, Crush swallowed the stderr and reported the call as orphaned — the ritual gate was invisible.

**Fix:** `_deny` now emits `{"decision":"deny","message":"..."}` to stdout before `exit 2`, matching the `{"decision":"allow"}` pattern used by `_allow_readonly_convmem_bash`. This lets Crush surface the denial message cleanly.

**Files changed (both, identical):**

- `~/.config/crush/hooks/convmem-allow.sh` (live, immediate)
- `~/Projects/convmem/scripts/crush-hook-convmem-allow.sh` (SSoT, survives redeploy)

### Second fix — cross-session cache bypass (2026-07-07 00:08)

`_ritual_complete()` had a `project_complete` fallback: a 12-hour TTL cache file
that let any new Crush session sharing the same CWD skip the ritual entirely.
This meant the hook appeared broken — the gate simply never fired for 12 hours
after the first ritual.

**Fix:** removed the `project_complete` shortcut. `_ritual_complete()` now checks
only per-session progress files. Each Crush session must earn its own
doctor/brief/unresolved before survey tools are allowed.

Also removed:
- `project_hash` variable (no longer needed)
- `project_complete` variable
- `project-*.complete` file creation in `_record_progress()`
- 20 stale `project-*.complete` files cleaned from cache

### Third fix — search-first gate + context injection (2026-07-07 00:11)

After ritual is complete, `grep`/`glob`/`ls`/`view`/`agent` calls are **denied**
until `mcp_convmem_search_fast`, `mcp_convmem_search`, `mcp_convmem_ask`, or
bash `convmem search` has been called at least once in the session.

Per-session `search_seen` flag gates survey tools:
- No search yet → `_deny "The convmem corpus has the answers. Use search_fast first."`
- Search recorded → tool allowed normally

Also emits `{"context":"..."}` on the first few calls for extra visibility.

### Bugfix pass (2026-07-07 00:13)

- **Ritual-gate bypass:** ritual-not-complete bash path used `convmem[[:space:]]` (too broad — matched `record`, `add`, `index`, `verify`). Narrowed to `convmem[[:space:]]+(doctor|brief|unresolved|search|ask|stats)`.
- **Dead variable:** removed `project=` variable (unused since `project_complete` cache deleted).

## ksweep-willowyhollow-practice

Ran the full sweep on the practice stack (:8081) after belated convmem ritual. Results:

| Check | Status | Notes |
|-------|--------|-------|
| Stack health | PASS | Both containers Up, DB alive, HTTP 200 |
| Core integrity | PASS | Checksums verify; siteurl/home correct |
| Backups | PASS | All 3 types backed up Jul 6; newest OK integrity |
| Git clean | WARN | 5 dirty tracked files + untracked scripts/docs |
| functions.php sync | PASS | Repo = container |
| URL leaks | PASS | Only `localhost:8081` |
| Plugins/theme | WARN | 5 plugins + astra parent have updates |
| WPCode cache | PASS | OK |
| Pages exist | PASS | All 7 key pages published |
| Images attached | PASS | IDs 1031, 1032, 1033 present |
| Security | PASS | 1 admin, debug OFF |
| Disk | INFO | 1.7G site, 411M backups, 20.5G Docker volumes |

**Verdict:** NOT READY TO PUSH — dirty git tree + pending plugin updates.
