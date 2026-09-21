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
from pathlib import Path

_FIXTURE_DIR = Path(__file__).resolve().parent
if str(_FIXTURE_DIR) not in sys.path:
    sys.path.insert(0, str(_FIXTURE_DIR))

from allowlist import assert_allowlist  # noqa: E402
from constants import (  # noqa: E402
    ALL_NEGATIVE_CONTROLS,
    CODE_BASELINE_SHA,
    CONTROL_ARBITRARY_SUITE,
    CONTROL_CHANGED_DEP,
    CONTROL_EXPECTED_REASON_PREFIX,
    CONTROL_EXPOSED_CANARY,
    CONTROL_EXTRA_FD,
    CONTROL_HOST_USR,
    CONTROL_MISSING_DEP,
    CONTROL_PRODUCTION_FAKE,
    CONTROL_UNLISTED_FILE,
    CONTROL_WRONG_ENV,
    CONTROL_WRONG_NAMESPACE,
    EXPECTED_TEST_RUNTIME_TREE_SHA256,
    HEX40_RE,
    INNER_ROLE_ENV,
    PREFLIGHT_OK_PATH,
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
        _die(
            "invalid_cli: exact args required: "
            "--source-commit HEX40 --plan-sha HEX40 --runtime-root ABS --suite all"
        )
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
            "import sys;"
            "sys.path.insert(0, '/src/tests/fixtures/openclaw_strict');"
            "import run_isolated as ri;"
            "raise SystemExit(ri._inner_main())"
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


def _sha256_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _write_synthetic_dep(
    fixture: Path,
    *,
    mode: str,
) -> None:
    """Disposable synthetic dependency root under the fixture (not /runtime)."""
    root = fixture / "synthetic_dep"
    tree = root / "tree"
    tree.mkdir(parents=True, exist_ok=True)
    good = b"synthetic-dependency-v1\n"
    if mode == "missing":
        inventory = [
            {
                "mode": "0644",
                "path": "dep.txt",
                "sha256": _sha256_bytes(good),
            }
        ]
        # tree intentionally lacks dep.txt
    elif mode == "changed":
        inventory = [
            {
                "mode": "0644",
                "path": "dep.txt",
                "sha256": _sha256_bytes(good),
            }
        ]
        (tree / "dep.txt").write_bytes(b"mutated-synthetic-dependency\n")
        os.chmod(tree / "dep.txt", 0o644)
    elif mode == "unlisted":
        inventory = [
            {
                "mode": "0644",
                "path": "dep.txt",
                "sha256": _sha256_bytes(good),
            }
        ]
        (tree / "dep.txt").write_bytes(good)
        os.chmod(tree / "dep.txt", 0o644)
        (tree / "extra_unlisted.txt").write_bytes(b"unlisted\n")
        os.chmod(tree / "extra_unlisted.txt", 0o644)
    else:
        raise SystemExit(f"unknown_synthetic_mode:{mode}")
    (root / "inventory.json").write_text(
        json.dumps(inventory, sort_keys=True), encoding="utf-8"
    )


def _write_synthetic_host_usr(fixture: Path) -> None:
    """Disposable synthetic root for host_usr — outer /usr bind stays runtime sysroot."""
    root = fixture / "synthetic_host_usr"
    tree = root / "tree"
    tree.mkdir(parents=True, exist_ok=True)
    planted = tree / "HOST_USR_UNLISTED"
    planted.write_bytes(b"synthetic-host-usr-unlisted\n")
    os.chmod(planted, 0o644)
    # Empty inventory → planted file fails closed as unlisted_or_host_usr.
    (root / "inventory.json").write_text(json.dumps([], sort_keys=True), encoding="utf-8")


def _usr_ro_bind_source(argv: list[str]) -> str | None:
    for i, arg in enumerate(argv):
        if arg == "--ro-bind" and i + 2 < len(argv) and argv[i + 2] == "/usr":
            return argv[i + 1]
    return None


def _evaluate_negative_control(
    *,
    control: str,
    proc: subprocess.CompletedProcess[str],
    fixture: Path,
    bwrap_argv: list[str],
) -> dict:
    """Control passes only with valid report, exact reason prefix, no sentinel, nonzero."""
    expected = CONTROL_EXPECTED_REASON_PREFIX[control]
    report_path = fixture / "preflight_report.json"
    if not report_path.is_file():
        _die(
            f"negative_control_invalid:{control}:missing_preflight_report:"
            f"rc={proc.returncode}:stderr={(proc.stderr or '')[:300]}"
        )
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _die(f"negative_control_invalid:{control}:preflight_report_unreadable")
    error = str(report.get("error", ""))
    if not error.startswith(expected):
        _die(
            f"negative_control_invalid:{control}:expected_prefix={expected!r}:"
            f"got={error!r}"
        )
    if (fixture / "preflight_ok").exists():
        _die(f"negative_control_invalid:{control}:import_sentinel_written")
    if report.get("import_sentinel") == "written":
        _die(f"negative_control_invalid:{control}:import_sentinel_written")
    if proc.returncode == 0:
        _die(f"negative_control_invalid:{control}:zero_exit")
    result = {
        "control": control,
        "returncode": proc.returncode,
        "status": "FAIL_AS_REQUIRED",
        "independent_failure_reason": error,
        "import_sentinel": report.get("import_sentinel", "not_written"),
        "expected_reason_prefix": expected,
    }
    if control == CONTROL_HOST_USR:
        usr_src = _usr_ro_bind_source(bwrap_argv)
        # Evidence must show no live host /usr as a --ro-bind source.
        live_host_usr_source = False
        for i, arg in enumerate(bwrap_argv):
            if arg == "--ro-bind" and i + 1 < len(bwrap_argv) and bwrap_argv[i + 1] == "/usr":
                live_host_usr_source = True
                break
        if usr_src is None or usr_src == "/usr" or live_host_usr_source:
            _die(
                f"negative_control_invalid:{control}:live_host_usr_in_bwrap_argv:"
                f"usr_bind_source={usr_src!r}"
            )
        result["bwrap_usr_bind_source"] = usr_src
        result["live_host_usr_source_absent"] = True
        result["bwrap_argv_ro_bind_pairs"] = [
            [bwrap_argv[i + 1], bwrap_argv[i + 2]]
            for i, arg in enumerate(bwrap_argv)
            if arg == "--ro-bind" and i + 2 < len(bwrap_argv)
        ]
    print(json.dumps(result, sort_keys=True))
    return result


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

    extra_ro_binds: list[tuple[str, str]] = []
    extra_env: dict[str, str] = {}

    if control == CONTROL_EXPOSED_CANARY:
        extra_ro_binds.append((str(canary_root), str(canary_root)))
    elif control == CONTROL_HOST_USR:
        # Outer boundary unchanged: runtime sysroot remains at /usr.
        # Fail via disposable synthetic root through the inventory oracle.
        _write_synthetic_host_usr(fixture)
    elif control == CONTROL_MISSING_DEP:
        _write_synthetic_dep(fixture, mode="missing")
    elif control == CONTROL_CHANGED_DEP:
        _write_synthetic_dep(fixture, mode="changed")
    elif control == CONTROL_UNLISTED_FILE:
        _write_synthetic_dep(fixture, mode="unlisted")
    elif control == CONTROL_WRONG_NAMESPACE:
        # Keep every namespace flag. Substitute incorrect observation only.
        (fixture / "ns_observation.json").write_text(
            json.dumps(
                {"child_net_ns": "net:[synthetic]", "host_net_ns": "net:[synthetic]"},
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    elif control == CONTROL_WRONG_ENV:
        extra_env["CONVMEM_OPENCLAW_SENTINEL_CRED"] = "leaked-sentinel"
    elif control == CONTROL_EXTRA_FD:
        # Substitute incorrect FD observation; outer boundary unchanged.
        (fixture / "fd_observation.json").write_text(
            json.dumps({"fds": [0, 1, 2, 7]}, sort_keys=True),
            encoding="utf-8",
        )
    elif control == CONTROL_ARBITRARY_SUITE:
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
        inner_argv=_inner_argv(),
        extra_ro_binds=extra_ro_binds,
        extra_env=extra_env,
    )
    proc = launch_contained(argv, timeout=180)
    return _evaluate_negative_control(
        control=control, proc=proc, fixture=fixture, bwrap_argv=argv
    )


def _inner_main() -> int:
    validate_frozen_selectors()
    if Path("/fixture/force_arbitrary_suite").is_file():
        from preflight import validate_suite_argv
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
    # Plugin inventory is recorded from the live strict pytest process (packet contract).
    print(json.dumps({"preflight": report["status"]}, sort_keys=True))

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

    try:
        emit_complete_manifest()
    except ManifestNotAvailable as exc:
        print(
            json.dumps(
                {"fixture_manifest": "not_available_t0a", "detail": str(exc)},
                sort_keys=True,
            )
        )

    source_root = export_source_commit(repo, args.source_commit)
    bwrap = require_bwrap()
    canary_root = create_canary_root()

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

    fixture = create_fixture_root()
    canary_paths = [str(canary_root / "outside_a"), str(canary_root / "outside_b")]
    _prepare_fixture(
        fixture, canary_paths=canary_paths, frozen_entries=prelaunch["entries"]
    )
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
                "prelaunch_test_runtime_tree_sha256": prelaunch[
                    "test_runtime_tree_sha256"
                ],
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
