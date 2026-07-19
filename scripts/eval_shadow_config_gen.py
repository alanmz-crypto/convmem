#!/usr/bin/env python3
"""Generate allowlisted shadow TOML under --out-dir (temp only for Gate 1)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate shadow config under out-dir")
    parser.add_argument("--live-config", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--chroma-dir", type=Path, required=True)
    parser.add_argument("--embed-model", required=True)
    parser.add_argument("--authorize-fixture", action="store_true")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from config import load_config
    from eval_corpus.run_manifest import _path_is_tempish
    from eval_corpus.shadow_config import generate_shadow_config

    if not args.authorize_fixture:
        print("Refusing: Gate 1 requires --authorize-fixture (temp out-dir only)", file=sys.stderr)
        return 2
    if not _path_is_tempish(args.out_dir):
        print("Refusing: --out-dir must be under /tmp for fixture mode", file=sys.stderr)
        return 2

    live = load_config(args.live_config.expanduser())
    path, violations = generate_shadow_config(
        live_cfg=live,
        out_dir=args.out_dir.expanduser(),
        chroma_dir=args.chroma_dir.expanduser(),
        embed_model=args.embed_model,
    )
    if violations:
        print("Allowlist violations:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
