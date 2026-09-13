# pylint: disable=protected-access,wrong-import-position
"""Fresh-process RSS worker for bounded export compaction measurements."""

from __future__ import annotations

import argparse
import os
import hashlib
import json
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Keep this import set identical for baseline and workload processes.
import export_compaction as export_compaction_mod  # noqa: E402  # pylint: disable=wrong-import-position
from export_compaction import compact_units_export  # noqa: E402  # pylint: disable=wrong-import-position


def _rss_bytes() -> int:
    status = Path("/proc/self/status").read_text(encoding="utf-8")
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    return 0


def _peak_rss_bytes() -> int:
    status = Path("/proc/self/status").read_text(encoding="utf-8")
    for line in status.splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1]) * 1024
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_nonblank(path: Path) -> int:
    count = 0
    with path.open("rb") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _uid_for(kind: str, n: int) -> str:
    if kind == "duplicate":
        return f"id-{n % 8}"
    if kind == "mostly_unique":
        if n % 10 == 0:
            return f"dup-{n % 8}"
        return f"id-{n}"
    return f"id-{n}"


def _oracle_expected(path: Path) -> dict:
    last_by_id: dict[str, bytes] = {}
    order: list[str] = []
    rows = 0
    with path.open("rb") as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            rows += 1
            uid = json.loads(stripped)["id"]
            if uid not in last_by_id:
                order.append(uid)
            last_by_id[uid] = stripped + b"\n"
    expected = b"".join(last_by_id[uid] for uid in order)
    return {
        "rows": rows,
        "unique_ids": len(order),
        "expected_sha256": hashlib.sha256(expected).hexdigest(),
        "expected_rows": len(order),
        "expected_removed": rows - len(order),
    }


def _write_fixture(path: Path, *, kind: str, size_mib: int) -> dict:
    target = size_mib * 1024 * 1024
    last_by_id: dict[str, bytes] = {}
    order: list[str] = []
    hasher = hashlib.sha256()
    written = 0
    n = 0
    with path.open("wb") as handle:
        while written < target:
            uid = _uid_for(kind, n)
            pad = "x" * 64
            record = json.dumps({"id": uid, "n": n, "pad": pad}, separators=(",", ":"))
            raw = (record + "\n").encode("utf-8")
            handle.write(raw)
            hasher.update(raw)
            if kind == "duplicate":
                if uid not in last_by_id:
                    order.append(uid)
                last_by_id[uid] = raw.strip() + b"\n"
            written += len(raw)
            n += 1
    if kind == "unique":
        expected = {
            "rows": n,
            "unique_ids": n,
            "expected_sha256": hasher.hexdigest(),
            "expected_rows": n,
            "expected_removed": 0,
        }
    elif kind == "duplicate":
        body = b"".join(last_by_id[uid] for uid in order)
        expected = {
            "rows": n,
            "unique_ids": len(order),
            "expected_sha256": hashlib.sha256(body).hexdigest(),
            "expected_rows": len(order),
            "expected_removed": n - len(order),
        }
    else:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--oracle", str(path)],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        expected = json.loads(proc.stdout)
    return {"bytes": written, **expected}


def _fstype(path: str) -> str:
    raw = path.split(" (deleted)", 1)[0]
    probe = raw if os.path.exists(raw) else os.path.dirname(raw)
    probe = os.path.realpath(probe)
    best = ""
    best_len = -1
    with open("/proc/mounts", encoding="utf-8") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 3:
                continue
            mount = parts[1].replace("\\040", " ")
            fstype = parts[2]
            if probe == mount or probe.startswith(mount.rstrip("/") + "/"):
                if len(mount) > best_len:
                    best = fstype
                    best_len = len(mount)
    return best


def _deleted_sqlite_fds() -> list[str]:
    found: list[str] = []
    for entry in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(entry)
        except OSError:
            continue
        if "etilqs_" in target:
            found.append(target)
    return found


def _non_tmpfs_parent() -> Path:
    for candidate in (Path("/var/tmp"), Path.home()):
        if candidate.is_dir() and _fstype(str(candidate)) not in {"tmpfs", "ramfs"}:
            return candidate
    raise RuntimeError("no non-tmpfs directory available for SQLite temp evidence")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("duplicate", "unique", "mostly_unique"))
    parser.add_argument("--size-mib", type=int, default=0)
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--oracle", type=str, default="")
    args = parser.parse_args()

    if args.oracle:
        json.dump(_oracle_expected(Path(args.oracle)), sys.stdout)
        sys.stdout.write("\n")
        return 0

    if args.kind is None:
        parser.error("--kind is required unless --oracle is set")

    # Match the authorized diagnostic's address-space ceiling.
    limit = 2 * 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    if args.baseline_only:
        json.dump({"baseline_rss_bytes": _rss_bytes(), "peak_rss_bytes": _peak_rss_bytes()}, sys.stdout)
        sys.stdout.write("\n")
        return 0

    baseline = _rss_bytes()
    sqlite_parent = _non_tmpfs_parent()
    sqlite_tmp = tempfile.mkdtemp(prefix="convmem-sqlite-tmp.", dir=str(sqlite_parent))
    os.environ["SQLITE_TMPDIR"] = sqlite_tmp
    os.environ["TMPDIR"] = sqlite_tmp
    captured: dict[str, object] = {
        "sqlite_temp_fstype": _fstype(sqlite_tmp),
        "sqlite_deleted_temp_fds": [],
        "sqlite_database_file": None,
        "sqlite_temp_store": None,
    }
    real = export_compaction_mod._index_row
    seen = 0

    def wrapped(conn, uid, seq, offset, length):
        nonlocal seen
        real(conn, uid, seq, offset, length)
        seen += 1
        if seen % 4096 == 0:
            fds = _deleted_sqlite_fds()
            if fds:
                captured["sqlite_deleted_temp_fds"] = fds
                db_list = conn.execute("PRAGMA database_list").fetchall()
                captured["sqlite_database_file"] = db_list[0][2] if db_list else None
                captured["sqlite_temp_store"] = conn.execute("PRAGMA temp_store").fetchone()[0]

    export_compaction_mod._index_row = wrapped
    try:
        with tempfile.TemporaryDirectory() as tmp:
            export_path = Path(tmp) / "knowledge_units.jsonl"
            meta = _write_fixture(export_path, kind=args.kind, size_mib=args.size_mib)
            before = _sha256(export_path)
            started = time.perf_counter()
            removed = compact_units_export(export_path)
            elapsed = time.perf_counter() - started
            after = _sha256(export_path)
            out_rows = _count_nonblank(export_path)
            report = {
                "kind": args.kind,
                "size_mib": args.size_mib,
                "baseline_rss_bytes": baseline,
                "peak_rss_bytes": _peak_rss_bytes(),
                "elapsed_s": elapsed,
                "removed": removed,
                "sha256_before": before,
                "sha256_after": after,
                "output_rows": out_rows,
                "output_bytes": export_path.stat().st_size,
                **captured,
                **meta,
            }
            json.dump(report, sys.stdout)
            sys.stdout.write("\n")
    finally:
        try:
            os.rmdir(sqlite_tmp)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
