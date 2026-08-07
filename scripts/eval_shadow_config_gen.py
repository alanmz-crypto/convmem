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
    parser.add_argument(
        "--enrichment-path",
        type=Path,
        default=None,
        help="Explicit decisions-approved.jsonl path for the shadow config",
    )
    parser.add_argument("--embed-model", required=True)
    parser.add_argument("--embed-host", default="http://127.0.0.1:11434")
    parser.add_argument("--authorize-fixture", action="store_true")
    parser.add_argument("--run-manifest", type=Path, default=None)
    parser.add_argument("--grant", type=Path, default=None, help="Single-use operation grant")
    parser.add_argument("--grant-id", default=None, help="Grant identity bound to this attempt")
    parser.add_argument("--attempt-id", default=None, help="One-shot config attempt identity")
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
                f"Refusing config_generation: source identity verification failed: {exc}",
                file=sys.stderr,
            )
            return 2

    from config import load_config
    from eval_corpus.run_manifest import (
        bind_config_generation,
        bind_r2a_config_generation,
        consume_bound_operation_grant,
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
    auth = None
    try:
        if args.run_manifest is not None and not args.authorize_fixture:
            preview = load_run_manifest(args.run_manifest)
            if str(preview.get("authorization_phase") or "") == "r2a":
                r2a_grant = bind_r2a_config_generation(
                    run_manifest_path=args.run_manifest,
                    runtime=runtime,
                )
            else:
                auth = bind_config_generation(
                    authorize_fixture=False,
                    run_manifest_path=args.run_manifest,
                    runtime=runtime,
                )
        else:
            auth = bind_config_generation(
                authorize_fixture=args.authorize_fixture,
                run_manifest_path=args.run_manifest,
                runtime=runtime,
            )
        if auth is not None:
            consume_bound_operation_grant(
                auth,
                grant_path=args.grant,
                grant_id=args.grant_id,
                attempt_id=args.attempt_id,
                manifest_path=args.run_manifest,
                runtime=runtime,
            )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"Refusing config_generation: {exc}", file=sys.stderr)
        return 2

    live = load_config(live_config)
    if args.run_manifest is not None and not args.authorize_fixture:
        preview = load_run_manifest(args.run_manifest)
        if str(preview.get("execution_mode") or "") == "real":
            expected = (preview.get("paths") or {}).get("enrichment_path")
            if not expected or args.enrichment_path is None:
                print(
                    "Refusing config_generation: real mode requires manifest-bound "
                    "enrichment_path",
                    file=sys.stderr,
                )
                return 2
            if args.enrichment_path.expanduser().resolve(strict=False) != Path(
                str(expected)
            ).expanduser().resolve(strict=False):
                print(
                    "Refusing config_generation: enrichment_path mismatch",
                    file=sys.stderr,
                )
                return 2
    path, violations = generate_shadow_config(
        live_cfg=None if r2a_grant is not None else live,
        out_dir=out_dir,
        chroma_dir=chroma_dir,
        enrichment_path=args.enrichment_path.expanduser()
        if args.enrichment_path
        else None,
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
