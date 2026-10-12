"""Inner scope supervisor: two-stage gate, index child, final counters, parent ack."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from live_diagnosis import (  # pylint: disable=wrong-import-position
    GATE_SCOPE_READY,
    GATE_SPAWN_GRANTED,
    _HANDSHAKE_WAIT_SECONDS,
    publish_supervisor_pid,
    read_index_gate_state,
    write_index_gate_state,
    _run_configured_net_probe,
)

TELEMETRY_MARKER = "CONVMEM_LIVE_DIAG_INNER_FINAL_PATH"
ACK_ENV = "CONVMEM_LIVE_DIAG_INNER_ACK_PATH"
UNIT_ENV = "CONVMEM_LIVE_DIAG_INNER_SCOPE_UNIT"
SCOPE_READY_ENV = "CONVMEM_LIVE_DIAG_SCOPE_READY_PATH"


def _read_cgroup_events(group: Path) -> dict[str, int]:
    events_path = group / "memory.events"
    if not events_path.is_file():
        return {}
    try:
        return {
            key: int(value)
            for key, value in (
                line.split() for line in events_path.read_text(encoding="ascii").splitlines()
            )
        }
    except (OSError, ValueError):
        return {}


def _scope_group(unit: str) -> Path | None:
    from tests.watch_oom_cgroup_runner import _unit_property

    rel = _unit_property(unit, "ControlGroup")
    if not rel:
        return None
    return Path("/sys/fs/cgroup") / rel.lstrip("/")


def _write_final(unit: str, *, worker_rc: int) -> None:
    raw = os.environ.get(TELEMETRY_MARKER, "").strip()
    if not raw:
        raise RuntimeError("inner_final_path_missing")
    path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    group = _scope_group(unit)
    if group is None or not group.is_dir():
        raise RuntimeError("inner_cgroup_missing_for_final")
    peak_raw = (group / "memory.peak").read_text(encoding="ascii").strip()
    current_raw = (group / "memory.current").read_text(encoding="ascii").strip()
    events = _read_cgroup_events(group)
    if not events:
        raise RuntimeError("inner_memory_events_missing")
    payload = {
        "unit": unit,
        "worker_returncode": worker_rc,
        "memory_peak": int(peak_raw),
        "memory_current": int(current_raw),
        "memory_events": events,
        "ts": time.time(),
    }
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _wait_ack(*, timeout: float = 120.0) -> None:
    if os.environ.get("CONVMEM_LIVE_DIAG_SYNTHETIC_FAST") == "1":
        return
    raw = os.environ.get(ACK_ENV, "").strip()
    if not raw:
        raise RuntimeError("inner_ack_path_missing")
    ack = Path(raw)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if ack.is_file() and ack.read_text(encoding="ascii").strip() == "ack":
            return
        time.sleep(0.05)
    raise RuntimeError("inner_ack_timeout")


def _mark_scope_ready() -> None:
    raw = os.environ.get(SCOPE_READY_ENV, "").strip()
    if raw:
        path = Path(raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ready\n", encoding="ascii")


def _wait_spawn_granted(*, timeout: float = _HANDSHAKE_WAIT_SECONDS) -> None:
    if os.environ.get("CONVMEM_LIVE_DIAG_SYNTHETIC_FAST") == "1":
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = read_index_gate_state()
        if state == GATE_SPAWN_GRANTED:
            return
        if state in {None, "pending", GATE_SCOPE_READY}:
            time.sleep(0.05)
            continue
        raise RuntimeError(f"spawn_gate_invalid:{state}")
    raise RuntimeError("spawn_gate_timeout")


def main(argv: list[str]) -> int:
    if "--" not in argv:
        raise RuntimeError("inner supervisor requires -- separator")
    sep = argv.index("--")
    index_argv = argv[sep + 1 :]
    unit = os.environ.get(UNIT_ENV, "").strip()
    if not unit:
        raise RuntimeError("inner_scope_unit_missing")
    publish_supervisor_pid()
    _run_configured_net_probe("inner")
    _mark_scope_ready()
    write_index_gate_state(GATE_SCOPE_READY)
    _wait_spawn_granted()
    proc = subprocess.run(index_argv, check=False)
    _write_final(unit, worker_rc=proc.returncode)
    _wait_ack()
    return proc.returncode if proc.returncode >= 0 else 128 - proc.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
