# Implementation Handoff: Runway Ledger — Claude Review Pre-Soak Fixes

**Date:** 2026-08-20  
**Author:** Kiro (review triage)  
**For:** Cursor (implementation)  
**Authorization:** Ryan, 2026-08-20 (Claude review Conditional PASS; fixes required before hook-enable GATE)

---

## Resume state

| Field | Value |
|-------|--------|
| **State** | `NOT_STARTED` |
| **Branch** | `fix/2026-08-20-runway-ledger-review-fixes` (create from `feat/2026-08-20-agent-run-ledger` tip `5c3506f`) |
| **Tip SHA** | n/a — not started |
| **Push status** | n/a |
| **PR** | Target: update PR #215 or open a stacked PR |
| **Ryan GATE** | These fixes are required before Ryan enables hooks (`enabled: true`) |
| **Track A ingest** | n/a |

---

## What to build

Two bug fixes identified by Claude's independent security review. Both are required before the live hook soak GATE.

**Why this exists:** Claude found that (1) two sessions without native IDs in the same cwd silently collide on `delivery_event_id`, causing the second session's start to be swallowed with zero trace, and (2) the hook adapter's blanket `except Exception: return 0` hides all failure evidence, violating the architecture's own invariant that "fail-open must not mean reporting a successful capture when no durable event was written."

---

## Fix 1: delivery_event_id collision (Claude Q4)

### Problem

`delivery_event_id()` in `agent_run_ledger.py` (~line 143) hashes:
```
"kiro-delivery-v1|{client}|{hook_event_name}|{session_id or ''}|{cwd or ''}|{source_ref}"
```

When `session_id` is `None` (the `session_start_missing_id.json` fixture proves this is expected), two different sessions with the same `cwd` produce the **identical `event_id`**. The second session's `append_event` finds the same event_id with different content (different `recorded_at`, different `run_id`) and raises `CorruptionError`. That exception is swallowed by Fix 2's problem, so the second start is silently dropped.

### Required fix

Add a disambiguator when `session_id` is absent. Options (pick one):

**Option A (preferred — include run_id in the hash):**
```python
def delivery_event_id(
    *,
    client: str,
    hook_event_name: str,
    session_id: str | None,
    cwd: str | None,
    source_ref: str,
    run_id: str | None = None,  # NEW — pass for start events
) -> str:
    material = "|".join(
        [
            "kiro-delivery-v1",
            client,
            hook_event_name,
            session_id or "",
            cwd or "",
            source_ref,
            run_id or "",  # NEW — breaks collision for different runs
        ]
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return f"arevt_{digest}"
```

But this means start events can't use a pre-generated `run_id` for idempotency. So:

**Option B (simpler — don't use delivery_event_id for start when session_id is None):**

In `scripts/kiro-agent-run-hook.py`, when `native` is None on start:
```python
if mode == "start":
    if native is None:
        # No stable idempotency key possible — use a fresh event_id.
        # Duplicate delivery of a no-ID start is rare and harmless (creates two runs,
        # both with identity_completeness=partial, reconcilable later).
        event_id = None  # Let start_run generate a random one
    else:
        event_id = delivery_event_id(...)
```

This preserves idempotent retry for sessions that DO have IDs (the common case), and falls back to unique IDs when there's nothing stable to hash. A duplicate delivery in the no-ID case creates two partial runs — visible, reconcilable, never silently lost.

### Test

Add to `tests/test_agent_run_ledger.py`:
```python
def test_q4_two_sessions_no_native_id_same_cwd(tmp_path: Path):
    """Two sessions without native IDs must not collide."""
    ledger = arl.AgentRunLedger(data_dir=tmp_path)
    # Simulate two starts from same cwd, both missing session_id
    r1 = arl.start_run(
        ledger,
        client="kiro",
        native_session_id=None,
        source_kind="kiro_hook",
        source_ref="SessionStart",
        cwd="/home/lauer/Projects/convmem",
        collect_git=False,
    )
    r2 = arl.start_run(
        ledger,
        client="kiro",
        native_session_id=None,
        source_kind="kiro_hook",
        source_ref="SessionStart",
        cwd="/home/lauer/Projects/convmem",
        collect_git=False,
    )
    assert r1["run_id"] != r2["run_id"]
    assert r1["created"] is True
    assert r2["created"] is True
    reduced = ledger.load()
    assert len(reduced.runs) == 2
```

---

## Fix 2: Silent exception swallowing (Claude Q7)

### Problem

In `scripts/kiro-agent-run-hook.py`, the outer handler:
```python
    except Exception:  # noqa: BLE001 — fail-open for client lifecycle
        return 0
```

This is correct for fail-open (must never block Kiro), but it violates the architecture invariant by producing **zero observable signal** when capture fails. No stderr, no diagnostic event, nothing.

### Required fix

```python
    except Exception as exc:  # noqa: BLE001 — fail-open for client lifecycle
        try:
            print(
                f"convmem agent-run hook ({mode}): {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
        except Exception:  # noqa: BLE001
            pass
        return 0
```

This preserves:
- Empty stdout (mandatory for SessionStart context injection)
- Exit 0 (mandatory for fail-open)
- Adds: stderr visibility for debugging/soak observation

### Test

Update the existing `test_v8_kiro_hook_adapter_fail_open` — add a case where the writer is broken (e.g., point at a directory as the log path) and verify stderr is non-empty:

```python
def test_q7_hook_failure_writes_stderr(tmp_path: Path, monkeypatch):
    """Hook failures must produce stderr output, not total silence."""
    import subprocess, sys
    # Make the log path a directory (causes OSError on open-for-append)
    bad_dir = tmp_path / "agent_runs.jsonl"
    bad_dir.mkdir()
    monkeypatch.setenv("CONVMEM_AGENT_RUN_DATA_DIR", str(tmp_path))
    script = Path(__file__).resolve().parents[1] / "scripts" / "kiro-agent-run-hook.py"
    fixture = Path(__file__).resolve().parent / "fixtures" / "agent_run_ledger" / "stdin"
    result = subprocess.run(
        [sys.executable, str(script), "start"],
        input=(fixture / "session_start_ok.json").read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "CONVMEM_AGENT_RUN_DATA_DIR": str(tmp_path)},
    )
    assert result.returncode == 0  # still fail-open
    assert result.stdout == ""     # still empty stdout
    assert "convmem agent-run hook" in result.stderr  # but stderr says what happened
```

---

## What NOT to build

- No fix for Q2/Q8 (log-read performance) — that's a later optimization, not pre-soak
- No `../` path rejection — nice-to-have, not blocking
- No repository-narrowing behavior change — that's pre-ingest-GATE, not pre-hook-GATE
- No nested validator `_reject_forbidden_keys` additions — low priority
- No changes to the reducer, CLI, or ingest resolver

---

## Acceptance criteria

- [ ] Two genuinely different no-ID sessions from the same cwd both successfully create separate runs (test_q4)
- [ ] Hook adapter failure produces stderr output (test_q7)
- [ ] Existing 34 focused tests still pass
- [ ] No regression in full suite
- [ ] Ruff / pylint clean

---

## Branch convention

```
fix/2026-08-20-runway-ledger-review-fixes
```

Push immediately. Can be merged into the existing PR #215 branch or opened as a stacked fix. Ryan squash-merges.

---

## Related files

| What | Path |
|------|------|
| Core module (Fix 1 target) | `agent_run_ledger.py` (~line 143, `delivery_event_id`) |
| Hook adapter (Fix 1 + Fix 2 target) | `scripts/kiro-agent-run-hook.py` (~line 80 + ~line 135) |
| Tests | `tests/test_agent_run_ledger.py` |
| Claude review (full findings) | `CONVMEM-RUNWAY-LEDGER-CLAUDE-REVIEW-PACKAGE-2026-08-20.md` (local) |
| Architecture invariants | `docs/plans/ARCHITECTURE-agent-run-ledger.md` (locked invariant 9) |

---

## Leaving / picking up checklist

**Author (leaving):**

- [x] This file committed (or on pushed branch)
- [x] `LATEST.md` updated (not needed — original bullet still applies, state unchanged)
- [x] Branch pushed

**Implementer (picking up):**

- [ ] Read this file
- [ ] Both fixes are ~10 lines of code total + 2 new tests
- [ ] Push to `feat/2026-08-20-agent-run-ledger` or stack a fix branch
- [ ] Verify all 34+ focused tests pass
