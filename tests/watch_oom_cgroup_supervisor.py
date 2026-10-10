"""Keep a transient cgroup alive while its child's final counters are read."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TELEMETRY_MARKER = "CONVMEM_CGROUP_EXIT_TELEMETRY:"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if len(sys.argv) < 3:
        raise RuntimeError("supervisor requires a cap and worker command")

    from tests.watch_oom_cgroup_runner import worker_limit_claim

    expected_bytes = int(sys.argv[1])
    claim = worker_limit_claim(expected_bytes)
    worker = subprocess.run(sys.argv[2:], check=False)
    group = Path(claim["cgroup_path"])
    peak = int((group / "memory.peak").read_text(encoding="ascii").strip())
    events = {
        key: int(value)
        for key, value in (
            line.split()
            for line in (group / "memory.events").read_text(encoding="ascii").splitlines()
        )
    }
    print(
        TELEMETRY_MARKER
        + json.dumps(
            {
                "claim": claim,
                "peak_bytes": peak,
                "events": events,
                "worker_returncode": worker.returncode,
            },
            sort_keys=True,
        ),
        file=sys.stderr,
        flush=True,
    )
    return worker.returncode if worker.returncode >= 0 else 128 - worker.returncode


if __name__ == "__main__":
    raise SystemExit(main())
