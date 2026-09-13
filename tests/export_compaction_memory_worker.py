"""Fresh-process RSS worker for bounded export compaction measurements."""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Keep this import set identical for baseline and workload processes.
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


def _write_fixture(path: Path, *, kind: str, size_mib: int) -> dict:
    target = size_mib * 1024 * 1024
    last_by_id: dict[str, bytes] = {}
    order: list[str] = []
    hasher = hashlib.sha256()
    written = 0
    n = 0
    with path.open("wb") as handle:
        while written < target:
            if kind == "duplicate":
                uid = f"id-{n % 8}"
            else:
                uid = f"id-{n}"
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
        expected_hash = hasher.hexdigest()
        unique_ids = n
        expected_rows = n
    else:
        expected = b"".join(last_by_id[uid] for uid in order)
        expected_hash = hashlib.sha256(expected).hexdigest()
        unique_ids = len(order)
        expected_rows = unique_ids
    return {
        "rows": n,
        "unique_ids": unique_ids,
        "bytes": written,
        "expected_sha256": expected_hash,
        "expected_rows": expected_rows,
        "expected_removed": n - expected_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=("duplicate", "unique"), required=True)
    parser.add_argument("--size-mib", type=int, required=True)
    parser.add_argument("--baseline-only", action="store_true")
    args = parser.parse_args()

    # Match the authorized diagnostic's address-space ceiling.
    limit = 2 * 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    if args.baseline_only:
        json.dump({"baseline_rss_bytes": _rss_bytes(), "peak_rss_bytes": _peak_rss_bytes()}, sys.stdout)
        sys.stdout.write("\n")
        return 0

    baseline = _rss_bytes()
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
            **meta,
        }
        json.dump(report, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
