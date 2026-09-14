# pylint: disable=protected-access,wrong-import-position
"""Pause after SQLite batches so a parent test can SIGKILL compaction."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import export_compaction  # noqa: E402  # pylint: disable=wrong-import-position


def main() -> int:
    export_path = Path(sys.argv[1])
    sentinel = Path(sys.argv[2])
    pause_after = int(sys.argv[3])
    real = export_compaction._index_row
    seen = 0

    def wrapped(conn, uid, seq, offset, length):
        nonlocal seen
        real(conn, uid, seq, offset, length)
        seen += 1
        if seen == pause_after:
            sentinel.write_text("ready\n", encoding="utf-8")
            while True:
                time.sleep(60)

    export_compaction._index_row = wrapped
    export_compaction.compact_units_export(export_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
