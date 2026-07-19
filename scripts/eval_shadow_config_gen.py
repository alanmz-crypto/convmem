#!/usr/bin/env python3
"""Generate allowlisted shadow TOML under --out-dir."""

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
    parser.add_argument("--embed-host", default="http://127.0.0.1:11434")
    parser.add_argument("--authorize-fixture", action="store_true")
    parser.add_argument("--run-manifest", type=Path, default=None)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from config import load_config
    from eval_corpus.run_manifest import (
        bind_config_generation,
        bind_r2a_config_generation,
        load_run_manifest,
    )
    from eval_corpus.shadow_config import generate_shadow_config

    live_config = args.live_config.expanduser()
    out_dir = args.out_dir.expanduser()
    chroma_dir = args.chroma_dir.expanduser()
    runtime = {
        "live_config": live_config,
        "out_dir": out_dir,
        "chroma_dir": chroma_dir,
        "embed_model": args.embed_model,
        "embed_host": args.embed_host,
    }

    r2a_grant = None
    try:
        if args.run_manifest is not None and not args.authorize_fixture:
            preview = load_run_manifest(args.run_manifest)
            if str(preview.get("authorization_phase") or "") == "r2a":
                r2a_grant = bind_r2a_config_generation(
                    run_manifest_path=args.run_manifest,
                    runtime=runtime,
                )
            else:
                bind_config_generation(
                    authorize_fixture=False,
                    run_manifest_path=args.run_manifest,
                    runtime=runtime,
                )
        else:
            bind_config_generation(
                authorize_fixture=args.authorize_fixture,
                run_manifest_path=args.run_manifest,
                runtime=runtime,
            )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Refusing config_generation: {exc}", file=sys.stderr)
        return 2

    live = load_config(live_config)
    path, violations = generate_shadow_config(
        live_cfg=live,
        out_dir=out_dir,
        chroma_dir=chroma_dir,
        embed_model=args.embed_model,
        ollama_host=args.embed_host,
        r2a_grant=r2a_grant,
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
