# pylint: disable=wrong-import-position,protected-access
"""Hermetic brief-metadata worker: path denial, C0 parity, RSS curve."""

from __future__ import annotations

import argparse
import builtins
import hashlib
import json
import os
import resource
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.linux_proc import peak_rss_bytes as _peak_rss_bytes
from tests.linux_proc import rss_bytes as _rss_bytes

PRODUCTION_PREFIXES = (
    str((Path.home() / ".local/share/convmem").resolve()),
    str((Path.home() / ".config/convmem").resolve()),
)
DEFAULT_BRIEF = str((Path.home() / ".local/share/convmem/brief.md").expanduser())
DENIED: list[str] = []


class ProductionPathDenied(RuntimeError):
    """Attempted to open a production ConvMem path from a hermetic worker."""


def _denied(path: object) -> bool:
    try:
        raw = os.fspath(path)
    except TypeError:
        return False
    expanded = str(Path(raw).expanduser())
    try:
        resolved = str(Path(expanded).resolve())
    except OSError:
        resolved = expanded
    if DEFAULT_BRIEF in (expanded, resolved):
        return True
    for prefix in PRODUCTION_PREFIXES:
        if resolved.startswith(prefix) or expanded.startswith(prefix):
            return True
    return False


def install_path_denial() -> None:
    import io

    real_open = builtins.open
    real_os_open = os.open
    real_connect = sqlite3.connect
    real_io_open = io.open
    real_path_open = Path.open

    def guarded_open(file, *args, **kwargs):
        if _denied(file):
            DENIED.append(str(file))
            raise ProductionPathDenied(str(file))
        return real_open(file, *args, **kwargs)

    def guarded_os_open(path, *args, **kwargs):
        if _denied(path):
            DENIED.append(str(path))
            raise ProductionPathDenied(str(path))
        return real_os_open(path, *args, **kwargs)

    def guarded_io_open(file, *args, **kwargs):
        if _denied(file):
            DENIED.append(str(file))
            raise ProductionPathDenied(str(file))
        return real_io_open(file, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        if _denied(self):
            DENIED.append(str(self))
            raise ProductionPathDenied(str(self))
        return real_path_open(self, *args, **kwargs)

    def guarded_connect(database, *args, **kwargs):
        target = database
        if isinstance(database, str) and database.startswith("file:"):
            target = database[5:].split("?", 1)[0]
        if _denied(target):
            DENIED.append(str(database))
            raise ProductionPathDenied(str(database))
        return real_connect(database, *args, **kwargs)

    builtins.open = guarded_open  # type: ignore[assignment]
    os.open = guarded_os_open  # type: ignore[assignment]
    io.open = guarded_io_open  # type: ignore[assignment]
    Path.open = guarded_path_open  # type: ignore[assignment]
    sqlite3.connect = guarded_connect  # type: ignore[assignment]


def _projected_keys(rows: list[dict]) -> list[str]:
    keys: set[str] = set()
    for row in rows:
        keys.update(row)
    return sorted(keys)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("baseline", "c0", "memory", "c5-negative"),
        required=True,
    )
    parser.add_argument("--chroma-dir", default="")
    parser.add_argument("--out-path", default="")
    parser.add_argument("--inventory", default="")
    parser.add_argument("--processed", default="")
    parser.add_argument("--tmp-root", default="")
    args = parser.parse_args()
    install_path_denial()
    limit = 2 * 1024 * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))

    if args.mode == "c5-negative":
        from brief import refresh_brief_after_change

        cfg = {
            "index": {
                "chroma_dir": args.chroma_dir,
                "processed_log": args.processed,
            },
            "sources": {"inventory": args.inventory},
            "query": {"rerank": False},
        }
        try:
            refresh_brief_after_change(cfg)
        except ProductionPathDenied as exc:
            DENIED.append(str(exc))
        json.dump({"denied": bool(DENIED), "denied_paths": DENIED}, sys.stdout)
        sys.stdout.write("\n")
        return 0 if DENIED else 2

    import brief
    from tests.watch_oom_brief_hermetic import freeze_brief_probes, write_c0_fixture
    from tests.test_watch_oom_stream_brief_c0 import _chroma_core, _normalize_render

    if args.mode == "baseline":
        json.dump(
            {
                "baseline_rss_bytes": _rss_bytes(),
                "peak_rss_bytes": _peak_rss_bytes(),
            },
            sys.stdout,
        )
        sys.stdout.write("\n")
        return 0

    if args.mode == "c0":
        tmp = Path(args.tmp_root)
        fx = write_c0_fixture(tmp)
        out = Path(args.out_path)
        with freeze_brief_probes():
            data = brief.gather_brief_data(fx["cfg"])
            rendered = _normalize_render(brief.render_brief_markdown(data), tmp)
            brief.write_brief(fx["cfg"], out_path=out, quiet=True)
        core = _chroma_core(data)
        json.dump(
            {
                "core": core,
                "render_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
                "render": rendered,
                "denied_paths": DENIED,
                "peak_rss_bytes": _peak_rss_bytes(),
                "projected_keys": _projected_keys(
                    data.get("recent_decisions") or []
                ),
            },
            sys.stdout,
        )
        sys.stdout.write("\n")
        return 0 if not DENIED else 3

    cfg = {
        "index": {
            "chroma_dir": args.chroma_dir,
            "processed_log": args.processed,
        },
        "sources": {"inventory": args.inventory},
        "query": {"rerank": False},
    }
    out = Path(args.out_path)
    baseline = _rss_bytes()
    with freeze_brief_probes():
        data = brief.gather_brief_data(cfg)
        brief.write_brief(cfg, out_path=out, quiet=True)
    rows = data.get("recent_decisions") or []
    json.dump(
        {
            "baseline_rss_bytes": baseline,
            "peak_rss_bytes": _peak_rss_bytes(),
            "units": data.get("units"),
            "unresolved_count": data.get("unresolved_count"),
            "output_digest": hashlib.sha256(out.read_bytes()).hexdigest(),
            "projected_keys": _projected_keys(rows),
            "denied_paths": DENIED,
            "forbidden_in_rows": sorted(
                {
                    key
                    for row in rows
                    for key in (
                        "provenance_envelope",
                        "provenance_commitment",
                        "provenance_assertion_id",
                    )
                    if key in row
                }
            ),
        },
        sys.stdout,
    )
    sys.stdout.write("\n")
    return 0 if not DENIED else 3


if __name__ == "__main__":
    raise SystemExit(main())
