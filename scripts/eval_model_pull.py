#!/usr/bin/env python3
"""Manifest/grant-bound R3 model pull; never available in fixture mode."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Authorized Ollama model acquisition")
    parser.add_argument("--run-manifest", type=Path, required=True)
    parser.add_argument("--grant", type=Path, required=True)
    parser.add_argument("--grant-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--model-tag", required=True)
    parser.add_argument("--model-digest", required=True)
    parser.add_argument("--embed-host", required=True)
    parser.add_argument("--ollama-bin", type=Path, required=True)
    parser.add_argument("--model-store-path", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(REPO))
    try:
        from eval_corpus.model_acquisition import run_authorized_model_pull
        from eval_corpus.ollama_identity import OllamaEmbedClient
        from eval_corpus.run_manifest import (
            bind_model_pull,
            consume_bound_operation_grant,
        )
        from eval_corpus.secure_fs import write_absent_json

        runtime = {
            "model_tag": args.model_tag,
            "model_digest": args.model_digest,
            "embed_host": args.embed_host,
            "ollama_bin": args.ollama_bin.expanduser(),
            "model_store_path": args.model_store_path.expanduser(),
            "pull_out": args.out.expanduser(),
        }
        auth = bind_model_pull(
            authorize_fixture=False,
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
        out = args.out.expanduser()
        client = OllamaEmbedClient(args.embed_host)
        report = run_authorized_model_pull(
            ollama_binary=args.ollama_bin,
            model_store_path=args.model_store_path,
            model_tag=args.model_tag,
            expected_digest=args.model_digest,
            ollama_host=args.embed_host,
            identity_client=client,
            authorized=True,
        )
        write_absent_json(out, report, approved_root=out.parent)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Model pull failed closed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
