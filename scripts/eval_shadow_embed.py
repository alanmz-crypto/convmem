#!/usr/bin/env python3
"""CLI for embed-only shadow build (approved run-manifest or fixture auth)."""

from __future__ import annotations

import argparse
import hashlib
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


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    parser.add_argument(
        "--require-acceptance",
        action="store_true",
        help="Ignored for real mode (acceptance forced by auth context)",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--embed-mode",
        choices=("fake", "http-fake", "ollama"),
        default="fake",
    )
    parser.add_argument("--embed-host", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--arm",
        choices=("baseline", "challenger"),
        default="baseline",
    )
    parser.add_argument("--build-identity", default="fixture-build")
    parser.add_argument("--config-identity-sha256", default="0" * 64)
    parser.add_argument("--enrichment-sha256", default="0" * 64)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    from eval_corpus.embed_adapters import (
        fake_embed_fn,
        http_embed_fn,
        ollama_embed_fn,
        start_fake_embed_server,
        stop_fake_embed_server,
    )
    from eval_corpus.fingerprint import corpus_fingerprint_hex, package_sha256_hex
    from eval_corpus.run_manifest import (
        assert_build_authorized,
        bind_model_execution,
    )
    from eval_corpus.shadow_build import run_shadow_build

    package = args.package.expanduser()
    manifest_path = args.manifest.expanduser()
    chroma_dir = args.chroma_dir.expanduser()
    parent = package.parent
    result = (args.result or (parent / "result.json")).expanduser()
    journal = (args.journal or (parent / "journal.jsonl")).expanduser()
    capture_dir = (args.capture_dir or (parent / "capture")).expanduser()

    units = _load_units(package)
    build_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dims = int(build_manifest["embed_dimensions"])
    model = str(build_manifest.get("embed_model") or "fake")

    runtime = {
        "package": package,
        "manifest": manifest_path,
        "chroma_dir": chroma_dir,
        "result": result,
        "journal": journal,
        "capture_dir": capture_dir,
        "model_tag": model,
        "embed_host": args.embed_host,
        "corpus_package_sha256": package_sha256_hex(units)
        if units
        else (_sha_file(package) if package.is_file() else "0" * 64),
        "unit_corpus_fingerprint": corpus_fingerprint_hex(units)
        if units
        else "0" * 64,
        "config_identity_sha256": args.config_identity_sha256,
        "enrichment_sha256": args.enrichment_sha256,
        "build_identity": args.build_identity,
    }

    try:
        auth = assert_build_authorized(
            authorize_fixture=args.authorize_fixture,
            run_manifest_path=args.run_manifest,
            runtime=runtime,
            arm=args.arm,
        )
    except Exception as exc:
        print(f"Refusing shadow build: {exc}", file=sys.stderr)
        return 2

    # Acceptance forced from auth context for real mode — CLI flag cannot disable.
    require_acceptance = bool(auth.require_corpus_acceptance) or bool(
        args.require_acceptance and auth.execution_mode == "fixture"
    )

    server = None
    try:
        if args.embed_mode == "fake":
            embed_fn = fake_embed_fn(dims)
        elif args.embed_mode == "http-fake":
            server, base, _thr, _state = start_fake_embed_server(dimensions=dims)
            embed_fn = http_embed_fn(base, model=model, dimensions=dims)
        else:
            if args.authorize_fixture:
                print(
                    "Refusing --embed-mode=ollama under --authorize-fixture "
                    "(use fake/http-fake).",
                    file=sys.stderr,
                )
                return 4
            try:
                bind_model_execution(
                    authorize_fixture=False,
                    run_manifest_path=args.run_manifest,
                    runtime={
                        "model_tag": model,
                        "embed_host": args.embed_host,
                        "chroma_dir": chroma_dir,
                    },
                )
            except Exception as exc:
                print(f"Refusing model_execution: {exc}", file=sys.stderr)
                return 4
            embed_fn = ollama_embed_fn(args.embed_host, model)

        result_doc = run_shadow_build(
            units=units,
            chroma_dir=chroma_dir,
            manifest=build_manifest,
            embed_fn=embed_fn,
            resume=args.resume,
            manifest_path=manifest_path,
            result_path=result,
            journal_path=journal,
            capture_dir=capture_dir if require_acceptance else (
                args.capture_dir.expanduser() if args.capture_dir else None
            ),
            require_corpus_acceptance=require_acceptance,
        )
    finally:
        if server is not None:
            stop_fake_embed_server(server)

    print(json.dumps(result_doc, indent=2, sort_keys=True))
    return 0 if result_doc.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
