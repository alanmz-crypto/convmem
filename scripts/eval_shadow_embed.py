#!/usr/bin/env python3
"""CLI entry for embed-only shadow build (live/model runs require R4 or R5).

Hermetic tests inject fake embeddings via the library. This CLI refuses without
authorization and, even when authorized, requires an explicit --embed-mode.
Default under R1 is library-only; real Ollama embedding is opt-in and out of R1.
"""

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


def _fake_embed(dimensions: int):
    def _embed(text: str) -> list[float]:
        base = (sum(ord(c) for c in text) % 997) / 997.0
        return [base] * dimensions

    return _embed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Eval shadow embed build (requires R4 or R5)")
    parser.add_argument("--authorize-r4", action="store_true", help="Nomic shadow authorization")
    parser.add_argument(
        "--authorize-r5", action="store_true", help="Challenger shadow authorization"
    )
    parser.add_argument("--package", type=Path, help="corpus_package.jsonl")
    parser.add_argument("--manifest", type=Path, help="build-manifest.json intent (JSON)")
    parser.add_argument("--chroma-dir", type=Path, help="Shadow chroma root")
    parser.add_argument("--result", type=Path, default=None, help="build-result.json path")
    parser.add_argument("--journal", type=Path, default=None, help="build-journal.jsonl path")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--embed-mode",
        choices=("fake", "ollama"),
        default="fake",
        help="fake=deterministic injectable vectors (hermetic); ollama=real model (not R1)",
    )
    args = parser.parse_args(argv)

    if not (args.authorize_r4 or args.authorize_r5):
        print(
            "Refusing shadow build: pass --authorize-r4 or --authorize-r5 after Ryan grant.",
            file=sys.stderr,
        )
        return 2

    if not args.package or not args.manifest or not args.chroma_dir:
        print(
            "Authorization flag present, but --package, --manifest, and --chroma-dir "
            "are required to run the embed-only builder.",
            file=sys.stderr,
        )
        return 3

    if args.embed_mode == "ollama":
        print(
            "Refusing --embed-mode=ollama under default R1 completion path. "
            "Use library/tests with fake embeddings, or a later R4/R5 session that "
            "explicitly authorizes model operations.",
            file=sys.stderr,
        )
        return 4

    sys.path.insert(0, str(REPO))
    from eval_corpus.shadow_build import run_shadow_build

    units = _load_units(args.package.expanduser())
    manifest = json.loads(args.manifest.expanduser().read_text(encoding="utf-8"))
    dims = int(manifest["embed_dimensions"])
    result = run_shadow_build(
        units=units,
        chroma_dir=args.chroma_dir.expanduser(),
        manifest=manifest,
        embed_fn=_fake_embed(dims),
        batch_size=args.batch_size,
        resume=args.resume,
        manifest_path=args.manifest.expanduser(),
        result_path=args.result.expanduser() if args.result else None,
        journal_path=args.journal.expanduser() if args.journal else None,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
