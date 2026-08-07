#!/usr/bin/env python3
"""Manifest-bound model inventory/probe command; never performs a pull."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class _FixtureProbeClient:
    def __init__(self, model_tag: str, model_digest: str, dimensions: int) -> None:
        self.model_tag = model_tag
        self.model_digest = model_digest
        self.dimensions = dimensions

    def list_models(self):
        return [{"name": self.model_tag, "digest": self.model_digest}]

    def resolve_model(self, tag):
        if tag != self.model_tag:
            raise RuntimeError("fixture probe tag mismatch")
        return {"model_tag": tag, "model_digest": self.model_digest, "variant": "fixture"}

    def embed(self, text, *, model_tag, dimensions):
        from eval_corpus.embed_adapters import fake_embed_fn

        vector = fake_embed_fn(dimensions)(text)
        return vector, {
            "request": {
                "model": model_tag,
                "input": text,
                "dimensions": dimensions,
            },
            "dimension": dimensions,
            "finite": True,
            "norm": 1.0,
            "vector_fingerprint": hashlib.sha256(
                json.dumps(vector, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manifest-bound Ollama model probe")
    parser.add_argument("--authorize-fixture", action="store_true")
    parser.add_argument("--run-manifest", type=Path, default=None)
    parser.add_argument("--grant", type=Path, default=None)
    parser.add_argument("--grant-id", default=None)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--model-tag", required=True)
    parser.add_argument("--model-digest", required=True)
    parser.add_argument("--dimensions", type=int, required=True)
    parser.add_argument("--embed-host", default="http://127.0.0.1:11434")
    parser.add_argument("--probe-text", required=True)
    parser.add_argument("--transform-id", required=True)
    parser.add_argument("--transform-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
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
            print(f"Refusing model probe: source identity failed: {exc}", file=sys.stderr)
            return 2

    from eval_corpus.io_atomic import atomic_write_json
    from eval_corpus.model_probe import run_model_probe
    from eval_corpus.run_manifest import (
        bind_model_probe,
        consume_bound_operation_grant,
    )

    out = args.out.expanduser()
    runtime = {
        "model_tag": args.model_tag,
        "model_digest": args.model_digest,
        "embed_dimensions": args.dimensions,
        "embed_host": args.embed_host,
        "probe_out": out,
        "probe_text_sha256": hashlib.sha256(args.probe_text.encode("utf-8")).hexdigest(),
        "transform_id": args.transform_id,
        "transform_sha256": args.transform_sha256,
    }
    try:
        auth = bind_model_probe(
            authorize_fixture=args.authorize_fixture,
            run_manifest_path=args.run_manifest,
            runtime=runtime,
        )
        consume_bound_operation_grant(
            auth,
            grant_path=args.grant,
            grant_id=args.grant_id,
            attempt_id=args.attempt_id,
            manifest_path=args.run_manifest,
            runtime=runtime,
        )
        if out.exists() or out.is_symlink():
            raise PermissionError(f"probe output must be absent: {out}")
        if args.authorize_fixture:
            client = _FixtureProbeClient(args.model_tag, args.model_digest, args.dimensions)
        else:
            from eval_corpus.ollama_identity import OllamaEmbedClient

            client = OllamaEmbedClient(args.embed_host)
        report = run_model_probe(
            client,
            model_tag=args.model_tag,
            expected_digest=args.model_digest,
            dimensions=args.dimensions,
            probe_text=args.probe_text,
            transform_id=args.transform_id,
            transform_sha256=args.transform_sha256,
        )
        atomic_write_json(out, report)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Model probe failed closed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
