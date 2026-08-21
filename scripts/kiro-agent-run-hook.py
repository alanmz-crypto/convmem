#!/usr/bin/env python3
"""Kiro edge adapter for Arc Runway Ledger (fail-open).

Reads hook STDIN JSON, calls the shared agent-run API, always exits 0 with
empty stdout so SessionStart never injects capture chatter into agent context.
Never persists assistant_response / prompts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from repo root without install.
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from agent_run_ledger import (
    AgentRunLedger,
    AgentRunLedgerError,
    AmbiguityError,
    NotFoundError,
    build_diagnostic_event,
    delivery_event_id,
    start_run,
    stop_run,
)

_START_ALIASES = frozenset({"SessionStart", "agentSpawn"})
_STOP_ALIASES = frozenset({"Stop", "stop", "agentStop"})


def _read_stdin() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _native_id(payload: dict) -> str | None:
    value = payload.get("session_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _event_name(payload: dict, fallback: str) -> str:
    name = payload.get("hook_event_name")
    if isinstance(name, str) and name:
        return name
    return fallback


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    if mode not in {"start", "stop"}:
        # Fail-open: never block Kiro for wrapper misuse.
        return 0

    payload = _read_stdin()
    # Drop forbidden content immediately; never log it.
    payload.pop("assistant_response", None)
    payload.pop("USER_PROMPT", None)
    payload.pop("prompt", None)

    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None
    native = _native_id(payload)
    fallback = "SessionStart" if mode == "start" else "Stop"
    hook_name = _event_name(payload, fallback)
    ledger = AgentRunLedger()

    try:
        if mode == "start":
            if hook_name not in _START_ALIASES and hook_name not in {"SessionStart"}:
                # Still allow start when wrapper was invoked as start.
                pass
            # No stable idempotency key without a native session ID — use a
            # fresh event_id so two no-ID sessions in the same cwd do not
            # collide and silently drop the second start (Claude Q4).
            if native is None:
                event_id = None
            else:
                event_id = delivery_event_id(
                    client="kiro",
                    hook_event_name=hook_name,
                    session_id=native,
                    cwd=cwd,
                    source_ref="SessionStart",
                )
            start_run(
                ledger,
                client="kiro",
                native_session_id=native,
                source_kind="kiro_hook",
                source_ref="SessionStart",
                cwd=cwd,
                event_id=event_id,
                collect_git=True,
            )
            return 0

        # stop
        if native is None:
            event_id = None
        else:
            event_id = delivery_event_id(
                client="kiro",
                hook_event_name=hook_name,
                session_id=native,
                cwd=cwd,
                source_ref="Stop",
            )
        try:
            stop_run(
                ledger,
                client="kiro",
                status="completed",
                source_kind="kiro_hook",
                source_ref="Stop",
                native_session_id=native,
                cwd=cwd,
                event_id=event_id,
                collect_git=True,
            )
        except (NotFoundError, AmbiguityError) as exc:
            reason = (
                "unmatched_stop"
                if isinstance(exc, NotFoundError)
                else "ambiguous_stop"
            )
            if native is None and isinstance(exc, NotFoundError):
                reason = "unmatched_stop_missing_native_id"
            diag = build_diagnostic_event(
                client="kiro",
                source_kind="kiro_hook",
                reason=reason,
                native_session_id=native,
                repository=None,
                event_id=(
                    None
                    if native is None
                    else delivery_event_id(
                        client="kiro",
                        hook_event_name=f"diagnostic:{hook_name}",
                        session_id=native,
                        cwd=cwd,
                        source_ref=reason,
                    )
                ),
            )
            try:
                ledger.append_event(diag)
            except AgentRunLedgerError:
                pass
        return 0
    except Exception as exc:  # noqa: BLE001 — fail-open for client lifecycle
        try:
            print(
                f"convmem agent-run hook ({mode}): {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
        except Exception:  # noqa: BLE001,S110
            pass
        return 0


if __name__ == "__main__":
    # Empty stdout is mandatory for SessionStart (context injection).
    raise SystemExit(main(sys.argv))
