#!/usr/bin/env python3
"""Closed OpenClaw T0–T5 isolated fixture runner (Execution §5.1).

Closed CLI only:
  --source-commit HEX40 --plan-sha HEX40 --runtime-root ABS --suite all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_FIXTURE_DIR = Path(__file__).resolve().parent
if str(_FIXTURE_DIR) not in sys.path:
    sys.path.insert(0, str(_FIXTURE_DIR))

from allowlist import assert_allowlist  # noqa: E402
from constants import (  # noqa: E402
    ALL_NEGATIVE_CONTROLS,
    CANARY_PATHS_FILE,
    CODE_BASELINE_SHA,
    CONTROL_ARBITRARY_SUITE,
    CONTROL_CHANGED_DEP,
    CONTROL_EXPOSED_CANARY,
    CONTROL_EXTRA_FD,
    CONTROL_HOST_USR,
    CONTROL_MISSING_DEP,
    CONTROL_PRODUCTION_FAKE,
    CONTROL_UNLISTED_FILE,
    CONTROL_WRONG_ENV,
    CONTROL_WRONG_NAMESPACE,
    EXPECTED_TEST_RUNTIME_TREE_SHA256,
    FROZEN_INVENTORY_PATH,
    HEX40_RE,
    HOST_NETNS_FILE,
    INNER_ROLE_ENV,
    PREFLIGHT_OK_PATH,
    PREFLIGHT_REPORT_PATH,
    SEMANTIC_PARENT_SHA,
    SUITE_WALL_DEADLINE_SEC,
)
from containment import (  # noqa: E402
    build_bwrap_argv,
    create_canary_root,
    create_fixture_root,
    host_net_ns,
    launch_contained,
    require_bwrap,
)
from fixture_manifest import ManifestNotAvailable, emit_complete_manifest  # noqa: E402
from inventory import verify_runtime_tree  # noqa: E402
from limits import run_suite_with_limits  # noqa: E402
from preflight import PreflightFailure, run_preflight  # noqa: E402
from source_export import export_source_commit  # noqa: E402
from suites import all_suite_commands, validate_frozen_selectors  # noqa: E402


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    raw = list(sys.argv[1:] if argv is None else argv)
    if len(raw) != 8:
        _die("invalid_cli: exact args required: --source-commit HEX40 --plan-sha HEX40 --runtime-root ABS --suite all")
    expected_order = ["--source-commit", "--plan-sha", "--runtime-root", "--suite"]
    values: dict[str, str] = {}
    for i in range(0, 8, 2):
        key, val = raw[i], raw[i + 1]
        if key != expected_order[i // 2]:
            _die("invalid_cli: arg_order")
        values[key] = val
    source_commit = values["--source-commit"]
    plan_sha = values["--plan-sha"]
    runtime_root_s = values["--runtime-root"]
    suite = values["--suite"]
    if not re.fullmatch(HEX40_RE, source_commit):
        _die("invalid_source_commit")
    if not re.fullmatch(HEX40_RE, plan_sha):
        _die("invalid_plan_sha")
    if plan_sha != SEMANTIC_PARENT_SHA:
        _die(f"plan_sha_mismatch: expected {SEMANTIC_PARENT_SHA}")
    if suite != "all":
        _die("suite_must_be_all")
    runtime_root = Path(runtime_root_s)
    if not runtime_root.is_absolute():
        _die("runtime_root_must_be_absolute")
    if not runtime_root.is_dir():
        _die("runtime_root_missing")
    return argparse.Namespace(
        source_commit=source_commit,
        plan_sha=plan_sha,
        runtime_root=runtime_root_s,
        suite=suite,
    )


def _repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        close_fds=True,
    )
    if proc.returncode != 0:
        _die("git_repo_required")
    return Path(proc.stdout.strip())


def _inner_argv() -> list[str]:
    return [
        "/runtime/bin/python",
        "-I",
        "-c",
        (
            "import runpy; "
            "runpy.run_path('/src/tests/fixtures/openclaw_strict/run_isolated.py', "
            "run_name='__inner__')"
        ),
    ]


def _prepare_fixture(
    fixture: Path,
    *,
    canary_paths: list[str],
    frozen_entries: list[dict[str, str]],
) -> None:
    (fixture / "canary_paths.json").write_text(json.dumps(canary_paths), encoding="utf-8")
    (fixture / "frozen_runtime_inventory.json").write_text(
        json.dumps(frozen_entries, sort_keys=True), encoding="utf-8"
    )
    (fixture / "host_net_ns").write_text(host_net_ns() + "\n", encoding="utf-8")


def _run_negative_control(
    *,
    control: str,
    bwrap: str,
    source_root: Path,
    runtime_root: Path,
    frozen_entries: list[dict[str, str]],
    canary_root: Path,
) -> dict:
    fixture = create_fixture_root()
    canary_paths = [str(canary_root / "outside_a"), str(canary_root / "outside_b")]
    _prepare_fixture(fixture, canary_paths=canary_paths, frozen_entries=frozen_entries)

    usr_source = None
    extra_ro_binds: list[tuple[str, str]] = []
    extra_binds: list[tuple[str, str]] = []
    hide_runtime_bin = False
    runtime_bin_overlay: list[tuple[str, str]] = []
    unshare_net = True
    extra_env: dict[str, str] = {}
    pass_fds: list[int] = []
    inner = _inner_argv()
    synthetic_fd = None

    if control == CONTROL_EXPOSED_CANARY:
        # Mount the distinct canary root at its host path so canaries become readable.
        extra_ro_binds.append((str(canary_root), str(canary_root)))
    elif control == CONTROL_HOST_USR:
        usr_source = Path("/usr")
    elif control == CONTROL_MISSING_DEP:
        hide_runtime_bin = True
        runtime_bin_overlay = [(str(runtime_root / "bin" / "python"), "/runtime/bin/python")]
        # node intentionally omitted from overlay
    elif control == CONTROL_CHANGED_DEP:
        # Overlay a mutated disposable file over an inventoried runtime path.
        target_rel = "sysroot/usr/share/zoneinfo/UTC"
        target = runtime_root / target_rel
        if not target.is_file():
            # Fall back to a small inventoried file under sysroot/usr/share if present.
            share = runtime_root / "sysroot" / "usr" / "share"
            candidates = [p for p in share.rglob("*") if p.is_file() and p.stat().st_size < 65536]
            if not candidates:
                _die("changed_dep_no_small_target")
            target = candidates[0]
            target_rel = target.relative_to(runtime_root).as_posix()
        mutated = fixture / "changed_dep_bytes"
        mutated.write_bytes(b"mutated-dependency-bytes\n" + target.read_bytes()[:16])
        # Map overlay onto mounted /usr path when under sysroot/usr, else /runtime.
        if target_rel.startswith("sysroot/usr/"):
            sandbox_path = "/usr/" + target_rel[len("sysroot/usr/") :]
        else:
            sandbox_path = "/runtime/" + target_rel
        extra_ro_binds.append((str(mutated), sandbox_path))
    elif control == CONTROL_UNLISTED_FILE:
        unlisted = fixture / "unlisted_bytes"
        unlisted.write_text("unlisted\n", encoding="utf-8")
        extra_binds.append((str(unlisted), "/runtime/UNLISTED_CANARY"))
    elif control == CONTROL_WRONG_NAMESPACE:
        unshare_net = False
    elif control == CONTROL_WRONG_ENV:
        extra_env["CONVMEM_OPENCLAW_SENTINEL_CRED"] = "leaked-sentinel"
    elif control == CONTROL_EXTRA_FD:
        synthetic_fd = os.open(os.devnull, os.O_RDONLY)
        pass_fds = [synthetic_fd]
    elif control == CONTROL_ARBITRARY_SUITE:
        # Marker causes the inner driver to feed a non-frozen suite argv into the
        # same independent selector validator before any integration import.
        (fixture / "force_arbitrary_suite").write_text("1\n", encoding="utf-8")
    elif control == CONTROL_PRODUCTION_FAKE:
        extra_env["OPENCLAW_FIXTURE_SELECT_FAKE"] = "1"
    else:
        _die(f"unknown_control:{control}")

    argv = build_bwrap_argv(
        bwrap=bwrap,
        source_root=source_root,
        runtime_root=runtime_root,
        fixture_root=fixture,
        inner_argv=inner,
        usr_source=usr_source,
        extra_ro_binds=extra_ro_binds,
        extra_binds=extra_binds,
        runtime_bin_overlay=runtime_bin_overlay,
        hide_runtime_bin=hide_runtime_bin,
        unshare_net=unshare_net,
        extra_env=extra_env,
    )
    try:
        proc = launch_contained(argv, timeout=180, pass_fds=pass_fds)
    finally:
        if synthetic_fd is not None:
            try:
                os.close(synthetic_fd)
            except OSError:
                pass

    report_path = fixture / "preflight_report.json"
    failure_reason = None
    import_sentinel = "absent"
    if report_path.is_file():
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
            failure_reason = report.get("error")
            import_sentinel = report.get("import_sentinel", "absent")
        except json.JSONDecodeError:
            failure_reason = "preflight_report_unreadable"
    if (fixture / "preflight_ok").exists():
        import_sentinel = "written_unexpectedly"
    if proc.returncode == 0 or (fixture / "preflight_ok").exists():
        _die(
            f"negative_control_did_not_fail:{control}:"
            f"rc={proc.returncode}:reason={failure_reason}:stderr={proc.stderr[:500]}"
        )
    result = {
        "control": control,
        "returncode": proc.returncode,
        "status": "FAIL_AS_REQUIRED",
        "independent_failure_reason": failure_reason or (proc.stderr or proc.stdout or "")[:500],
        "import_sentinel": import_sentinel,
    }
    print(json.dumps(result, sort_keys=True))
    return result


def _inner_main() -> int:
    validate_frozen_selectors()
    # Arbitrary-suite control: if marker present, attempt forbidden discovery argv check.
    if Path("/fixture/force_arbitrary_suite").is_file():
        from preflight import PreflightFailure, validate_suite_argv
        from suites import strict_pytest_argv

        try:
            validate_suite_argv(["pytest", "-q"], strict_pytest_argv())
        except PreflightFailure as exc:
            print(f"preflight_fail: {exc}", file=sys.stderr)
            Path("/fixture/preflight_report.json").write_text(
                json.dumps(
                    {
                        "status": "FAIL",
                        "error": str(exc),
                        "import_sentinel": "not_written",
                    },
                    sort_keys=True,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            return 1
    try:
        report = run_preflight()
    except PreflightFailure as exc:
        print(f"preflight_fail: {exc}", file=sys.stderr)
        return 1
    if not Path(PREFLIGHT_OK_PATH).exists():
        print("preflight_sentinel_missing", file=sys.stderr)
        return 1
    print(json.dumps({"preflight": report["status"]}, sort_keys=True))

    # After sentinel: run exact three suites with live limits.
    overall_rc = 0
    results = []
    for name, argv in all_suite_commands():
        result = run_suite_with_limits(name, argv)
        results.append(
            {
                "name": result.name,
                "returncode": result.returncode,
                "elapsed_sec": result.elapsed_sec,
                "combined_output_bytes": result.combined_output_bytes,
                "max_tmp_bytes": result.max_tmp_bytes,
                "tmp_sample_interval_sec": result.tmp_sample_interval_sec,
                "killed_reason": result.killed_reason,
            }
        )
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if result.killed_reason:
            print(f"suite_{result.killed_reason}:{name}", file=sys.stderr)
            overall_rc = 1
        elif result.returncode != 0:
            overall_rc = result.returncode or 1
    Path("/fixture/suite_results.json").write_text(
        json.dumps(results, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return overall_rc


def outer_main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo = _repo_root()
    changed = assert_allowlist(repo, args.source_commit)
    print(json.dumps({"allowlist_changed_paths": changed}, sort_keys=True))

    runtime_root = Path(args.runtime_root)
    prelaunch = verify_runtime_tree(runtime_root, EXPECTED_TEST_RUNTIME_TREE_SHA256)
    print(
        json.dumps(
            {
                "prelaunch_test_runtime_tree_sha256": prelaunch["test_runtime_tree_sha256"],
                "regular_file_count": prelaunch["regular_file_count"],
            },
            sort_keys=True,
        )
    )

    # T0a: complete manifest emission fails closed (T0b owns component digests).
    try:
        emit_complete_manifest()
    except ManifestNotAvailable as exc:
        print(json.dumps({"fixture_manifest": "not_available_t0a", "detail": str(exc)}, sort_keys=True))

    source_root = export_source_commit(repo, args.source_commit)
    bwrap = require_bwrap()
    canary_root = create_canary_root()
    canary_paths = [str(canary_root / "outside_a"), str(canary_root / "outside_b")]

    control_results = []
    for control in ALL_NEGATIVE_CONTROLS:
        control_results.append(
            _run_negative_control(
                control=control,
                bwrap=bwrap,
                source_root=source_root,
                runtime_root=runtime_root,
                frozen_entries=prelaunch["entries"],
                canary_root=canary_root,
            )
        )

    # Success path.
    fixture = create_fixture_root()
    _prepare_fixture(fixture, canary_paths=canary_paths, frozen_entries=prelaunch["entries"])
    argv = build_bwrap_argv(
        bwrap=bwrap,
        source_root=source_root,
        runtime_root=runtime_root,
        fixture_root=fixture,
        inner_argv=_inner_argv(),
    )
    proc = launch_contained(argv, timeout=SUITE_WALL_DEADLINE_SEC * 3 + 180)
    sys.stdout.write(proc.stdout or "")
    sys.stderr.write(proc.stderr or "")

    # Independently recompute runtime inventory/hash after all children terminate.
    post = verify_runtime_tree(runtime_root, EXPECTED_TEST_RUNTIME_TREE_SHA256)
    if post["test_runtime_tree_sha256"] != prelaunch["test_runtime_tree_sha256"]:
        _die("runtime_digest_changed_after_run")

    print(
        json.dumps(
            {
                "outer_returncode": proc.returncode,
                "fixture_root": str(fixture),
                "canary_root": str(canary_root),
                "source_export": str(source_root),
                "baseline": CODE_BASELINE_SHA,
                "plan_sha": args.plan_sha,
                "source_commit": args.source_commit,
                "prelaunch_test_runtime_tree_sha256": prelaunch["test_runtime_tree_sha256"],
                "postlaunch_test_runtime_tree_sha256": post["test_runtime_tree_sha256"],
                "negative_controls": control_results,
                "preflight_ok": (fixture / "preflight_ok").exists(),
            },
            sort_keys=True,
        )
    )
    return proc.returncode


if __name__ == "__inner__" or os.environ.get(INNER_ROLE_ENV) == "inner":
    raise SystemExit(_inner_main())

if __name__ == "__main__":
    if os.environ.get(INNER_ROLE_ENV) == "inner":
        raise SystemExit(_inner_main())
    raise SystemExit(outer_main())
