#!/usr/bin/env python3
"""CLI for embed-only shadow build (approved run-manifest or fixture auth)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import tomllib

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


def _manifest_bound_path(
    manifest: dict,
    *,
    key: str,
    label: str,
) -> Path:
    """Return one exact manifest path, rejecting absent or malformed bindings."""
    paths = manifest.get("paths") or {}
    raw = paths.get(key)
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"real build manifest paths must include {key} for {label}")
    return Path(raw).expanduser().resolve(strict=False)


def main(argv: list[str] | None = None) -> int:  # pylint: disable=too-many-locals
    parser = argparse.ArgumentParser(description="Eval shadow embed build")
    parser.add_argument("--authorize-fixture", action="store_true")
    parser.add_argument("--run-manifest", type=Path, default=None)
    parser.add_argument("--grant", type=Path, default=None, help="Single-use operation grant")
    parser.add_argument("--grant-id", default=None, help="Grant identity bound to this build")
    parser.add_argument("--attempt-id", default=None, help="One-shot build attempt identity")
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="C0b authoritative TOML; required for real mode",
    )
    parser.add_argument("--chroma-dir", type=Path, required=True)
    parser.add_argument(
        "--attempt-root",
        type=Path,
        default=None,
        help="Required real-build root; fixture mode defaults to the Chroma parent.",
    )
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
    parser.add_argument("--embed-host", default=None)
    parser.add_argument(
        "--arm",
        choices=("baseline", "challenger"),
        default="baseline",
    )
    parser.add_argument("--build-identity", default="fixture-build")
    parser.add_argument("--config-identity-sha256", default=None)
    parser.add_argument("--enrichment-sha256", default=None)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    if args.run_manifest is not None:
        try:
            from eval_corpus.source_identity import (
                SourceIdentityError,
                verify_manifest_path_source_identity,
            )

            verify_manifest_path_source_identity(args.run_manifest, repo_root=REPO)
        except (OSError, ValueError, SourceIdentityError) as exc:
            print(
                f"Refusing shadow build: source identity verification failed: {exc}",
                file=sys.stderr,
            )
            return 2

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
        consume_bound_operation_grant,
    )
    from eval_corpus.shadow_build import run_shadow_build

    package = args.package.expanduser()
    manifest_path = args.manifest.expanduser()
    chroma_dir = args.chroma_dir.expanduser()
    attempt_root = (args.attempt_root or chroma_dir.parent).expanduser()
    parent = package.parent
    result = (args.result or (parent / "result.json")).expanduser()
    journal = (args.journal or (parent / "journal.jsonl")).expanduser()
    capture_dir = (args.capture_dir or (parent / "capture")).expanduser()

    units = _load_units(package)
    build_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dims = int(build_manifest["embed_dimensions"])
    model = str(build_manifest.get("embed_model") or "fake")
    embed_host = args.embed_host or "http://127.0.0.1:11434"
    config_identity_sha256 = args.config_identity_sha256 or "0" * 64
    enrichment_sha256 = args.enrichment_sha256 or "0" * 64

    preview_manifest = None
    if args.run_manifest is not None:
        preview_manifest = json.loads(
            args.run_manifest.expanduser().read_text(encoding="utf-8")
        )
    if preview_manifest and str(preview_manifest.get("execution_mode") or "") == "real":
        if args.config is None:
            print("Refusing real build: --config is required", file=sys.stderr)
            return 2
        if args.embed_host is not None or args.config_identity_sha256 is not None:
            print(
                "Refusing real build: model host/config identity must come from --config",
                file=sys.stderr,
            )
            return 2
        config_path = args.config.expanduser().resolve(strict=True)
        config_bytes = config_path.read_bytes()
        try:
            effective_cfg = tomllib.loads(config_bytes.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            print(f"Refusing real build: invalid authoritative config: {exc}", file=sys.stderr)
            return 2
        expected_config = _manifest_bound_path(
            preview_manifest,
            key=f"{args.arm}_config",
            label=f"{args.arm} config",
        )
        if config_path != expected_config:
            print(
                "Refusing real build: --config differs from the manifest-bound "
                f"{args.arm}_config path",
                file=sys.stderr,
            )
            return 2
        models_cfg = effective_cfg.get("models") or {}
        index_cfg = effective_cfg.get("index") or {}
        eval_cfg = effective_cfg.get("eval") or {}
        model = str(models_cfg.get("embed_model") or "")
        embed_host = str(models_cfg.get("ollama_host") or "")
        configured_chroma = Path(str(index_cfg.get("chroma_dir") or "")).expanduser()
        if not model or not embed_host:
            print("Refusing real build: authoritative config lacks model/host", file=sys.stderr)
            return 2
        if configured_chroma.resolve(strict=False) != chroma_dir.resolve(strict=False):
            print("Refusing real build: Chroma path differs from authoritative config", file=sys.stderr)
            return 2
        if int(eval_cfg.get("embedding_dimensions") or 0) != dims:
            print("Refusing real build: dimension differs from authoritative config", file=sys.stderr)
            return 2
        if str((effective_cfg.get("query") or {}).get("fallback_policy") or "") != "forbid":
            print("Refusing real build: authoritative config must forbid fallback", file=sys.stderr)
            return 2
        if str(eval_cfg.get("embedding_request_contract") or "") != "ollama.embed.v1":
            print("Refusing real build: authoritative config must bind ollama.embed.v1", file=sys.stderr)
            return 2
        enrichment_path = Path(str(index_cfg.get("approved_decisions_path") or "")).expanduser()
        if not enrichment_path.is_file():
            print("Refusing real build: authoritative enrichment path is missing", file=sys.stderr)
            return 2
        expected_enrichment = _manifest_bound_path(
            preview_manifest,
            key=f"{args.arm}_enrichment_path"
            if f"{args.arm}_enrichment_path" in (preview_manifest.get("paths") or {})
            else "enrichment_path",
            label=f"{args.arm} enrichment",
        )
        if enrichment_path.resolve(strict=False) != expected_enrichment:
            print(
                "Refusing real build: authoritative enrichment path differs from "
                "the manifest-bound path",
                file=sys.stderr,
            )
            return 2
        config_identity_sha256 = hashlib.sha256(config_bytes).hexdigest()
        enrichment_sha256 = _sha_file(enrichment_path)
        config_model_digest = str(models_cfg.get("embed_model_digest") or "")
        expected_model_digest = str(build_manifest.get("embed_model_digest") or "")
        if not expected_model_digest:
            print("Refusing real build: build manifest must bind embed_model_digest", file=sys.stderr)
            return 2
        if config_model_digest != expected_model_digest:
            print(
                "Refusing real build: config embed_model_digest differs from "
                "the build manifest",
                file=sys.stderr,
            )
            return 2

    runtime = {
        "package": package,
        "manifest": manifest_path,
        "chroma_dir": chroma_dir,
        "result": result,
        "journal": journal,
        "capture_dir": capture_dir,
        "attempt_root": attempt_root,
        "model_tag": model,
        "model_digest": str(build_manifest.get("embed_model_digest") or ""),
        "embed_dimensions": dims,
        "embed_host": embed_host,
        "corpus_package_sha256": package_sha256_hex(units)
        if units
        else (_sha_file(package) if package.is_file() else "0" * 64),
        "unit_corpus_fingerprint": corpus_fingerprint_hex(units)
        if units
        else "0" * 64,
        "config_identity_sha256": config_identity_sha256,
        "enrichment_sha256": enrichment_sha256,
        "build_identity": args.build_identity,
        "embed_mode": args.embed_mode,
        "resume": args.resume,
    }

    try:
        auth = assert_build_authorized(
            authorize_fixture=args.authorize_fixture,
            run_manifest_path=args.run_manifest,
            runtime=runtime,
            arm=args.arm,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Refusing shadow build: {exc}", file=sys.stderr)
        return 2

    try:
        consume_bound_operation_grant(
            auth,
            grant_path=args.grant,
            grant_id=args.grant_id,
            attempt_id=args.attempt_id,
            manifest_path=args.run_manifest,
            runtime=runtime,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Refusing shadow build: single-use grant failed: {exc}", file=sys.stderr)
        return 2

    # Acceptance forced from auth context for real mode — CLI flag cannot disable.
    require_acceptance = bool(auth.require_corpus_acceptance) or bool(
        args.require_acceptance and auth.execution_mode == "fixture"
    )

    if auth.execution_mode == "real":
        if args.embed_mode != "ollama":
            print("Refusing real build: embed_mode must be ollama", file=sys.stderr)
            return 3
        if args.resume:
            print("Refusing real build: --resume is forbidden", file=sys.stderr)
            return 3
        if args.attempt_root is None:
            print("Refusing real build: --attempt-root is required", file=sys.stderr)
            return 3
        if chroma_dir.exists() or chroma_dir.is_symlink():
            print("Refusing real build: Chroma output must be absent", file=sys.stderr)
            return 3
        if str(build_manifest.get("embed_mode") or "") != "ollama":
            print(
                "Refusing real build: build manifest must bind embed_mode=ollama",
                file=sys.stderr,
            )
            return 3

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
                        "model_digest": str(build_manifest.get("embed_model_digest") or ""),
                        "embed_dimensions": dims,
                        "embed_host": embed_host,
                        "chroma_dir": chroma_dir,
                    },
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                print(f"Refusing model_execution: {exc}", file=sys.stderr)
                return 4
            embed_fn = ollama_embed_fn(embed_host, model, dimensions=dims)
            actual_identity = getattr(embed_fn, "__eval_model_identity__", {})
            expected_digest = str(build_manifest.get("embed_model_digest") or "")
            if str(actual_identity.get("model_digest") or "") != expected_digest:
                print(
                    "Refusing real build: resolved Ollama model digest differs from "
                    "the approved manifest",
                    file=sys.stderr,
                )
                return 4

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
            execution_mode=auth.execution_mode,
            embed_mode=args.embed_mode,
        )
    finally:
        if server is not None:
            stop_fake_embed_server(server)

    if auth.execution_mode == "real":
        expected_digest = str(build_manifest.get("embed_model_digest") or "")
        if str(result_doc.get("embed_model_digest") or "") != expected_digest:
            print(
                "Refusing real build: completed build result digest does not "
                "match the approved digest",
                file=sys.stderr,
            )
            return 4

    print(json.dumps(result_doc, indent=2, sort_keys=True))
    return 0 if result_doc.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
