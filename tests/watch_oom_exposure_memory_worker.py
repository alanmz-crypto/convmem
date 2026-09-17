# pylint: disable=wrong-import-position,protected-access
"""Hermetic exposure-window worker: path denial, probe-only RSS, brief-chain RSS."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.linux_proc import peak_rss_bytes as _peak_rss_bytes
from tests.linux_proc import rss_bytes as _rss_bytes
from tests.watch_oom_hermetic_isolation import (
    DENIED,
    forbidden_provenance_keys,
    hermetic_brief_cfg,
)
from tests.watch_oom_memory_worker_shared import (
    C5_MODES,
    denied_exit_code,
    emit_worker_json,
    run_worker_main,
)


def _dispatch(args: argparse.Namespace) -> int:
    if args.mode == "probe":
        from doctor import _exposure_window_probe
        from tests.watch_oom_exposure_hermetic import EXPOSURE_ROW, exposure_cfg

        baseline = _rss_bytes()
        due, detail = _exposure_window_probe(
            EXPOSURE_ROW, exposure_cfg(Path(args.chroma_dir))
        )
        emit_worker_json(
            {
                "baseline_rss_bytes": baseline,
                "peak_rss_bytes": _peak_rss_bytes(),
                "due": due,
                "detail": detail,
                "digest": hashlib.sha256(f"{due}|{detail}".encode()).hexdigest(),
                "denied_paths": DENIED,
            }
        )
        return denied_exit_code()

    import brief
    from doctor import _exposure_window_probe, standing_register_status
    from tests.watch_oom_brief_hermetic import freeze_brief_probes
    from tests.watch_oom_exposure_hermetic import EXPOSURE_ROW, exposure_cfg

    cfg = hermetic_brief_cfg(args.chroma_dir, args.processed, args.inventory)
    out = Path(args.out_path)
    baseline = _rss_bytes()
    register = Path(args.register)
    with freeze_brief_probes(), patch(
        "doctor.standing_register_status",
        wraps=standing_register_status,
    ), patch("doctor._standing_register_path", return_value=register):
        data = brief.gather_brief_data(cfg)
        brief.write_brief(cfg, out_path=out, quiet=True)
    rows = data.get("recent_decisions") or []
    due, detail = _exposure_window_probe(
        EXPOSURE_ROW, exposure_cfg(Path(args.chroma_dir))
    )
    probe_digest = hashlib.sha256(f"{due}|{detail}".encode()).hexdigest()
    emit_worker_json(
        {
            "baseline_rss_bytes": baseline,
            "peak_rss_bytes": _peak_rss_bytes(),
            "units": data.get("units"),
            "probe_digest": probe_digest,
            "output_digest": hashlib.sha256(out.read_bytes()).hexdigest(),
            "denied_paths": DENIED,
            "forbidden_in_rows": forbidden_provenance_keys(rows),
        }
    )
    return denied_exit_code()


def main() -> int:
    def _extra_args(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--out-path", default="")
        parser.add_argument("--register", default="")

    return run_worker_main(
        mode_choices=("baseline", "probe", "brief", *C5_MODES),
        extra_args=_extra_args,
        dispatch=_dispatch,
    )


if __name__ == "__main__":
    raise SystemExit(main())
