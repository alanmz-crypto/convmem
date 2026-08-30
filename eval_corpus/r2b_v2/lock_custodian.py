"""Dedicated subprocess exclusive lock holder for R2b v2 lease (I2)."""

from __future__ import annotations

import fcntl
import multiprocessing as mp
import os
from multiprocessing.connection import Connection
from typing import Any

_CUSTODIAN_IO_TIMEOUT_SEC = 5.0


class LockCustodianError(RuntimeError):
    """Lock custodian acquisition, verification, or release failure."""


def _recv_response(conn: Connection, *, timeout: float = _CUSTODIAN_IO_TIMEOUT_SEC) -> dict[str, Any]:
    if not conn.poll(timeout):
        raise LockCustodianError("custodian communication timeout")
    return conn.recv()


def _custodian_worker(lock_path: str, parent_pid: int, conn: Connection) -> None:
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    exclusive = False
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        exclusive = True
    except BlockingIOError:
        conn.send({"ok": False, "error": "acquire_blocked"})
        os.close(fd)
        return
    inode = os.fstat(fd).st_ino
    conn.send({"ok": True, "inode": inode, "custodian_pid": os.getpid()})

    while True:
        try:
            msg = conn.recv()
        except EOFError:
            break
        cmd = msg.get("cmd")
        if cmd == "verify":
            if not exclusive:
                conn.send({"ok": False, "reason": "released"})
                continue
            if os.getppid() != parent_pid:
                conn.send({"ok": False, "reason": "parent_dead"})
                continue
            conn.send({"ok": True, "inode": inode})
        elif cmd == "release":
            exclusive = False
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            conn.send({"ok": True})
            return
        elif cmd == "force_unlock":
            exclusive = False
            fcntl.flock(fd, fcntl.LOCK_UN)
            conn.send({"ok": True})
        elif cmd == "downgrade_sh":
            exclusive = False
            fcntl.flock(fd, fcntl.LOCK_SH)
            conn.send({"ok": True})
        else:
            conn.send({"ok": False, "reason": f"unknown command {cmd!r}"})


class LockCustodian:
    """Opaque handle to a subprocess that owns the original exclusive kernel lock."""

    __slots__ = ("_conn", "_proc", "inode", "lock_path")

    def __init__(self, proc: mp.Process, conn: Connection, *, inode: int, lock_path: str) -> None:
        self._proc = proc
        self._conn = conn
        self.inode = inode
        self.lock_path = lock_path

    def verify(self) -> None:
        if self._proc.exitcode is not None:
            raise LockCustodianError("custodian process exited")
        try:
            self._conn.send({"cmd": "verify"})
            resp = _recv_response(self._conn)
        except (EOFError, ConnectionResetError, BrokenPipeError, OSError) as exc:
            raise LockCustodianError("custodian communication failed") from exc
        if not resp.get("ok"):
            raise LockCustodianError(str(resp.get("reason", "custodian verify failed")))

    def release(self) -> None:
        if self._proc.is_alive():
            self._conn.send({"cmd": "release"})
            try:
                _recv_response(self._conn)
            except (EOFError, LockCustodianError):
                pass
            self._proc.join(timeout=5)
        if self._proc.is_alive():
            self._proc.terminate()
            self._proc.join(timeout=2)

    def force_unlock_for_tests(self) -> None:
        self._conn.send({"cmd": "force_unlock"})
        _recv_response(self._conn)

    def downgrade_to_shared_for_tests(self) -> None:
        self._conn.send({"cmd": "downgrade_sh"})
        _recv_response(self._conn)


def spawn_lock_custodian(lock_path: str) -> LockCustodian:
    """Spawn a dedicated holder that acquires LOCK_EX on lock_path."""
    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=True)
    proc = ctx.Process(
        target=_custodian_worker,
        args=(lock_path, os.getpid(), child_conn),
    )
    proc.start()
    child_conn.close()
    resp = parent_conn.recv()
    if not resp.get("ok"):
        proc.join(timeout=2)
        raise LockCustodianError(str(resp.get("error", "custodian failed to acquire")))
    return LockCustodian(proc, parent_conn, inode=int(resp["inode"]), lock_path=lock_path)


def custodian_for_tests(holder: Any) -> LockCustodian:
    """Test seam: return the live custodian behind a lease holder."""
    return holder.custodian
