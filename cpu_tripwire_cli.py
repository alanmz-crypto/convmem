"""Operator-facing tripwire commands; reads and mutations share doctor's evidence."""

from __future__ import annotations

import json
import shlex
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

import typer

from cpu_tripwire import (
    SignalRead,
    evaluate,
    evaluate_signals,
    read_boot_id,
    read_signals,
)
from cpu_tripwire_ack import (
    AckError,
    DurabilityUnconfirmed,
    Operator,
    TtyRequired,
    load_acks,
    record_key,
    revoke_ack,
    write_ack,
)
from cpu_tripwire_events import EventKey, ackable


def _snapshot() -> tuple[SignalRead, str | None]:
    from config import load_config

    return read_signals(load_config()), read_boot_id()


def _ack_command(key: EventKey) -> str:
    return shlex.join(
        [
            "convmem",
            "tripwire",
            "ack",
            "--boot-id",
            key.boot_id,
            "--realtime-us",
            str(key.realtime_us),
            "--source-monotonic-us",
            str(key.source_monotonic_us),
            "--message-sha256",
            key.message_sha256,
            "--cursor",
            key.cursor,
            "--by",
            "ryan",
            "--reason",
            "<reason>",
        ]
    )


def show_payload(signals: SignalRead, boot_id: str | None) -> dict[str, Any]:
    acks = load_acks()
    context = signals.ack_context(boot_id)
    selection = acks.select(context)
    applied = {fault.key for fault, _ in selection.applied}
    existing = {record_key(record) for record in acks.records}
    faults = []
    for fault in signals.journal.faults:
        can_ack = (
            acks.problem is None
            and context.problem is None
            and ackable(fault, signals.known_bad)
            and fault.key not in existing
            and sum(other.key == fault.key for other in signals.journal.faults) == 1
        )
        status = (
            "warn"
            if fault.key in applied
            else evaluate([fault], [], set(), signals.known_bad).status
        )
        faults.append(
            {
                "description": fault.describe(),
                "classification": status,
                "key": asdict(fault.key) if fault.key else None,
                "ack_id": fault.key.ack_id if fault.key else None,
                "acknowledgeable": can_ack,
                "ack_command": _ack_command(fault.key) if can_ack else None,
            }
        )
    verdict = evaluate_signals(signals, acks, boot_id)
    return {
        "current_boot_id": boot_id,
        "verdict": asdict(verdict),
        "faults": faults,
        "acknowledgments": selection.states,
        "problem": acks.problem or context.problem,
    }


def run_show(json_output: bool = False) -> int:
    payload = show_payload(*_snapshot())
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=True, indent=2))
        return 0
    verdict = payload["verdict"]
    typer.echo(f"{verdict['status'].upper()}: {verdict['detail']}")
    if payload["problem"]:
        typer.echo(payload["problem"])
    for fault in payload["faults"]:
        typer.echo(f"{fault['classification'].upper()}: {fault['description']}")
        if fault["key"]:
            typer.echo(json.dumps(fault["key"], sort_keys=True))
        if fault["ack_command"]:
            typer.echo(fault["ack_command"])
    for item in payload["acknowledgments"]:
        typer.echo(f"{item['record']['ack_id']}: {item['state']}")
    return 0


def _run_write(operation: Callable[[], tuple[str, bool]], verb: str) -> int:
    try:
        identifier, changed = operation()
    except TtyRequired as exc:
        typer.echo(str(exc), err=True)
        return 2
    except DurabilityUnconfirmed as exc:
        typer.echo(
            f"Document was written, but durability is unconfirmed: {exc}", err=True
        )
        return 3
    except (AckError, OSError, EOFError) as exc:
        typer.echo(f"Refused: {exc}", err=True)
        return 1
    typer.echo(f"{verb if changed else 'Already ' + verb.lower()}: {identifier}")
    signals, boot_id = _snapshot()
    verdict = evaluate_signals(signals, load_acks(), boot_id)
    typer.echo(f"{verdict.status.upper()}: {verdict.detail}")
    return 0


def run_ack(key: EventKey, operator: Operator) -> int:
    def read_context():
        signals, boot_id = _snapshot()
        return signals.ack_context(boot_id)

    return _run_write(lambda: write_ack(key, operator, read_context), "Acknowledged")


def run_revoke(identifier: str, operator: Operator) -> int:
    return _run_write(lambda: revoke_ack(identifier, operator), "Revoked")


# ref: ./cpu_tripwire.py, ./cpu_tripwire_ack.py, ./convmem.py — shared evidence and thin Typer handlers
# src: ./docs/plans/ARCHITECTURE-doctor-fault-acknowledgment.md — operator command and authority contract
