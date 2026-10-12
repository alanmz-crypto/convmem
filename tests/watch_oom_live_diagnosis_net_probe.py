"""Parent loopback listener + self AF_INET probe artifacts (issue #268 D1)."""

from __future__ import annotations

import json
import os
import socket
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from tests.watch_oom_live_diagnosis_bwrap import net_namespace_id

NET_PROBE_PORT_ENV = "CONVMEM_LIVE_DIAG_NET_PROBE_PORT"
NET_PROBE_OUTER_PATH_ENV = "CONVMEM_LIVE_DIAG_NET_PROBE_OUTER_PATH"
NET_PROBE_INNER_PATH_ENV = "CONVMEM_LIVE_DIAG_NET_PROBE_INNER_PATH"

MAX_PROBE_ARTIFACT_BYTES = 512
REQUIRED_PROBE_KEYS = ("role", "pid", "port", "netns_id", "connected", "status")


class NetProbeVerificationError(RuntimeError):
    """Fail-closed net isolation proof rejected."""


@contextmanager
def parent_loopback_listener():
    """Bind 127.0.0.1:0 in the parent namespace for isolation checks."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    stop = threading.Event()

    def accept_one() -> None:
        while not stop.is_set():
            try:
                sock.settimeout(0.2)
                conn, _ = sock.accept()
                conn.close()
            except OSError:
                continue

    thread = threading.Thread(target=accept_one, daemon=True)
    thread.start()
    try:
        yield port
    finally:
        stop.set()
        sock.close()


def parent_can_connect_loopback(port: int) -> bool:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.settimeout(1.0)
    try:
        probe.connect(("127.0.0.1", port))
    except OSError:
        return False
    finally:
        probe.close()
    return True


def parent_net_namespace_id() -> str | None:
    return net_namespace_id(os.getpid())


def write_self_loopback_probe(*, port: int, result_path: Path, role: str) -> None:
    """Target process attempts AF_INET connect to parent listener; writes scratch artifact."""
    if role not in {"outer", "inner"}:
        raise ValueError(f"net_probe_invalid_role:{role}")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "role": role,
        "pid": os.getpid(),
        "port": int(port),
        "netns_id": net_namespace_id(os.getpid()),
        "connected": False,
        "errno": None,
        "status": "connect_failed",
    }
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.connect(("127.0.0.1", port))
        payload["connected"] = True
        payload["status"] = "connect_ok"
    except OSError as exc:
        payload["errno"] = exc.errno
        payload["status"] = "connect_failed"
    finally:
        sock.close()
    raw = (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")
    if len(raw) > MAX_PROBE_ARTIFACT_BYTES:
        raise NetProbeVerificationError("net_probe_artifact_too_large")
    result_path.write_bytes(raw)


def _load_probe_artifact(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise NetProbeVerificationError("net_probe_artifact_missing")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_PROBE_ARTIFACT_BYTES:
        raise NetProbeVerificationError("net_probe_artifact_invalid_size")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NetProbeVerificationError("net_probe_artifact_invalid_json") from exc
    if not isinstance(payload, dict):
        raise NetProbeVerificationError("net_probe_artifact_not_object")
    for key in REQUIRED_PROBE_KEYS:
        if key not in payload:
            raise NetProbeVerificationError(f"net_probe_artifact_missing_field:{key}")
    return payload


def verify_dual_net_probe_artifacts(
    *,
    outer_path: Path,
    inner_path: Path,
    port: int,
    parent_netns: str | None,
    parent_positive_control: bool,
    outer_pid: int | None = None,
    inner_pid: int | None = None,
) -> None:
    """Parent verifies self-reported AF_INET probes; raises NetProbeVerificationError on failure."""
    if not parent_positive_control:
        raise NetProbeVerificationError("net_probe_parent_positive_control_failed")
    if not parent_netns:
        raise NetProbeVerificationError("net_probe_parent_netns_unavailable")
    outer = _load_probe_artifact(outer_path)
    inner = _load_probe_artifact(inner_path)
    if outer.get("role") != "outer" or inner.get("role") != "inner":
        raise NetProbeVerificationError("net_probe_role_mismatch")
    if int(outer.get("port", -1)) != port or int(inner.get("port", -1)) != port:
        raise NetProbeVerificationError("net_probe_port_mismatch")
    if outer.get("connected") or inner.get("connected"):
        raise NetProbeVerificationError("net_probe_target_connected_unexpected")
    outer_net = outer.get("netns_id")
    inner_net = inner.get("netns_id")
    if not outer_net or not inner_net or outer_net != inner_net:
        raise NetProbeVerificationError("net_probe_outer_inner_netns_mismatch")
    if outer_net == parent_netns:
        raise NetProbeVerificationError("net_probe_target_netns_equals_parent")
    if outer_pid is not None and int(outer.get("pid", -1)) != outer_pid:
        raise NetProbeVerificationError("net_probe_outer_pid_mismatch")
    if inner_pid is not None and int(inner.get("pid", -1)) != inner_pid:
        raise NetProbeVerificationError("net_probe_inner_pid_mismatch")


def run_configured_net_probe(role: str) -> None:
    """Run probe when port + result path env are set (outer worker or inner supervisor)."""
    port_raw = os.environ.get(NET_PROBE_PORT_ENV, "").strip()
    if not port_raw:
        return
    path_key = NET_PROBE_OUTER_PATH_ENV if role == "outer" else NET_PROBE_INNER_PATH_ENV
    path_raw = os.environ.get(path_key, "").strip()
    if not path_raw:
        raise NetProbeVerificationError(f"net_probe_path_missing:{role}")
    write_self_loopback_probe(port=int(port_raw), result_path=Path(path_raw), role=role)
