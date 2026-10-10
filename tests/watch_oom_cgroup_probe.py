"""Throwaway service probe for the gated cgroup measurement route."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("success", "oom", "exit"), required=True)
    parser.add_argument("--ready", type=Path, required=True)
    parser.add_argument("--expected-bytes", type=int, required=True)
    args = parser.parse_args()

    from tests.watch_oom_cgroup_runner import (
        DENIED_PATH_MARKER,
        NETWORK_DENIED_MARKER,
        wait_for_parent_ready,
        worker_limit_claim,
    )

    wait_for_parent_ready(args.ready)
    claim = worker_limit_claim(args.expected_bytes)
    print("cgroup probe stderr captured", file=sys.stderr, flush=True)
    if args.mode == "success":
        print(json.dumps({
            "status": "succeeded", "claim": claim,
            "denied_paths": [DENIED_PATH_MARKER],
            "network_denied": [NETWORK_DENIED_MARKER],
        }), flush=True)
        return 0
    if args.mode == "exit":
        print(json.dumps({
            "status": "exited", "claim": claim,
            "denied_paths": [DENIED_PATH_MARKER],
            "network_denied": [NETWORK_DENIED_MARKER],
        }), flush=True)
        return 17

    # The 64 MiB throwaway cap makes this a small, controlled OOM proof.
    blocks = []
    while True:
        block = bytearray(4 * 1024 * 1024)
        for offset in range(0, len(block), 4096):
            block[offset] = 1
        blocks.append(block)


if __name__ == "__main__":
    raise SystemExit(main())
