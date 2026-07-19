#!/usr/bin/env python3
"""CLI for embed-only shadow build (approved run-manifest or fixture auth)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _load_units(package: Path) -> list[dict]:
    rows: list[dict] = []
    for line in package.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval shadow embed build")
    parser.add_argument("--authorize-fixture", action="store_true")
    parser.add_argument("--run-manifest", type=Path, default=None)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--chroma-dir", type=Path, required=True)
    parser.add_argument("--result", type=Path, default=None)
    parser.add_argument("--journal", type=Path, default=None)
    parser.add_argument("--capture-dir", type=Path, default=None)
    parser.add_argument("--require-acceptance", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--embed-mode",
        choices=("fake", "http-fake", "ollama"),
        default="fake",
    )
    parser.add_argument("--embed-host", default="http://127.0.0.1:11434")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from eval_corpus.embed_adapters import (
        fake_embed_fn,
        http_embed_fn,
        ollama_embed_fn,
        start_fake_embed_server,
        stop_fake_embed_server,
    )
    from eval_corpus.run_manifest import assert_build_authorized
    from eval_corpus.shadow_build import run_shadow_build

    try:
        assert_build_authorized(
            authorize_fixture=args.authorize_fixture,
            run_manifest_path=args.run_manifest,
            chroma_dir=args.chroma_dir.expanduser(),
            package_path=args.package.expanduser(),
        )
    except Exception as exc:
        print(f"Refusing shadow build: {exc}", file=sys.stderr)
        return 2

    units = _load_units(args.package.expanduser())
    manifest = json.loads(args.manifest.expanduser().read_text(encoding="utf-8"))
    dims = int(manifest["embed_dimensions"])
    model = str(manifest.get("embed_model") or "fake")

    server = None
    try:
        if args.embed_mode == "fake":
            embed_fn = fake_embed_fn(dims)
        elif args.embed_mode == "http-fake":
            server, base, _thr = start_fake_embed_server(dimensions=dims)
            embed_fn = http_embed_fn(base, model=model, dimensions=dims)
        else:
            # Implemented but Gate 1 fixture path must not hit live Ollama.
            if args.authorize_fixture:
                print(
                    "Refusing --embed-mode=ollama under --authorize-fixture "
                    "(use fake/http-fake).",
                    file=sys.stderr,
                )
                return 4
            embed_fn = ollama_embed_fn(args.embed_host, model)

        result = run_shadow_build(
            units=units,
            chroma_dir=args.chroma_dir.expanduser(),
            manifest=manifest,
            embed_fn=embed_fn,
            resume=args.resume,
            manifest_path=args.manifest.expanduser(),
            result_path=args.result.expanduser() if args.result else None,
            journal_path=args.journal.expanduser() if args.journal else None,
            capture_dir=args.capture_dir.expanduser() if args.capture_dir else None,
            require_corpus_acceptance=args.require_acceptance,
        )
    finally:
        if server is not None:
            stop_fake_embed_server(server)

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
