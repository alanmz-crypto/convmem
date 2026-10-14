"""Parent-side helpers for Safe Harbor T4 V5 subprocess evidence."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "_safe_harbor_t4_probe.py"
T2_RUNNER = ROOT / "tests" / "_safe_harbor_t2_cli.py"
PYTHON_CHILD = [sys.executable, "-s", "-B"]
PROBE_TIMEOUT = 600.0

TRACKED_INPUT_PATHS = (
    PROBE,
    ROOT / "tests" / "_safe_harbor_t4_harness.py",
    ROOT / "tests" / "_safe_harbor_t4_worker.py",
    T2_RUNNER,
    ROOT / "tests" / "_safe_harbor_bootstrap.py",
    ROOT / "tests" / "_safe_harbor_t3_backend_worker.py",
    ROOT / "tests" / "_safe_harbor_restic_ci.py",
    ROOT / "tests" / "test_safe_harbor_t4_matrix.py",
)


def tracked_input_hashes() -> dict[str, str]:
    paths = list(TRACKED_INPUT_PATHS)
    paths.extend(sorted(ROOT.glob("tests/test_safe_harbor_t4*.py")))
    paths.extend(sorted(ROOT.glob("tests/_safe_harbor_t4*.py")))
    return file_hashes(paths)


def file_hashes(paths) -> dict[str, str]:
    """Fail on missing evidence inputs and hash every supplied file."""
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError(f"T4 tracked inputs missing: {missing}")
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def run_fixture_child(cmd, *, env, timeout, input_text=None, pass_fds=()):
    """Captured subprocess contract shared by T4 fixture drivers."""
    # pylint: disable=duplicate-code
    # Existing T1 subprocess assertions are independent and outside this task.
    return subprocess.run(
        cmd, cwd=ROOT, env=env, input=input_text, capture_output=True,
        text=True, timeout=timeout, check=False, pass_fds=pass_fds,
    )
    # pylint: enable=duplicate-code


def assert_tracked_inputs_unchanged(before: dict[str, str], after: dict[str, str]) -> None:
    if before != after:
        drift = {
            k: (before.get(k), after.get(k))
            for k in set(before) | set(after)
            if before.get(k) != after.get(k)
        }
        raise AssertionError(f"T4 harness input drift detected: {drift}")


def expected_embedding_sha256(document: str) -> str:
    """Match _safe_harbor_t2_cli._chroma_state rounding (6 decimal places)."""
    base = (sum(ord(c) for c in document) % 997) / 997.0
    vec = [round(float(base), 6)] * 768
    return hashlib.sha256(json.dumps(vec).encode()).hexdigest()


def _fixture_root() -> Path:
    raw = os.environ.get("SAFE_HARBOR_T3_FIXTURE_ROOT", "").strip()
    if not raw:
        raise RuntimeError("SAFE_HARBOR_T3_FIXTURE_ROOT must be set by launcher")
    return Path(raw).expanduser().resolve(strict=False)


def assert_cli_confined(cli) -> None:
    root = _fixture_root()
    for path in (
        cli.s.root,
        cli.config,
        cli.s.chroma,
        cli.export,
    ):
        resolved = Path(path).expanduser().resolve(strict=False)
        if resolved != root and root not in resolved.parents:
            raise AssertionError(f"cli path {resolved} outside fixture root {root}")


def probe_env(cli, *, case: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    assert_cli_confined(cli)
    env = dict(os.environ)
    if "SAFE_HARBOR_T3_EXPECTED_UID" not in env:
        raise RuntimeError("SAFE_HARBOR_T3_EXPECTED_UID must be inherited from launcher")
    env.setdefault("SAFE_HARBOR_T3_BOOTSTRAPPED", "1")
    env.setdefault("SAFE_HARBOR_T3_FIXTURE_ROOT", str(_fixture_root()))
    env["CONVMEM_CONFIG"] = str(cli.config)
    env["SAFE_HARBOR_T4_CASE"] = case
    if extra:
        env.update(extra)
    return env


def run_probe(
    cli,
    case: str,
    *,
    extra_env: dict[str, str] | None = None,
    timeout: float = PROBE_TIMEOUT,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    before = tracked_input_hashes()
    env = probe_env(cli, case=case, extra=extra_env)
    cmd = [*PYTHON_CHILD, str(PROBE), case]
    proc = run_fixture_child(cmd, env=env, timeout=timeout)
    after = tracked_input_hashes()
    assert_tracked_inputs_unchanged(before, after)
    if proc.returncode is None:
        raise AssertionError(f"probe missing returncode for case {case}")
    meta = {
        "argv": cmd,
        "case": case,
        "returncode": proc.returncode,
        "timed_out": False,
        "stdout_sha256": hashlib.sha256((proc.stdout or "").encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256((proc.stderr or "").encode()).hexdigest(),
    }
    lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
    if not lines:
        raise AssertionError(
            f"probe empty stdout for case {case}: rc={proc.returncode} stderr={proc.stderr}"
        )
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"probe non-json stdout for {case}: {proc.stdout!r} stderr={proc.stderr!r}"
        ) from exc
    payload["_harness_meta"] = meta
    return proc, payload


def expect_probe_ok(cli, case: str, **kwargs: Any) -> dict[str, Any]:
    proc, payload = run_probe(cli, case, **kwargs)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert payload.get("verdict") == "PASS", payload
    return payload


def expect_probe_refused(cli, case: str, **kwargs: Any) -> dict[str, Any]:
    proc, payload = run_probe(cli, case, **kwargs)
    assert proc.returncode != 0, f"expected refusal for {case}: {proc.stdout}"
    assert payload.get("verdict") in {"REFUSED", "FAIL"}, payload
    return payload


def independent_ingest_content_hash(approved_row: dict) -> str:
    from ledger import ledger_unit_metadata, normalize_ledger_record

    unit = normalize_ledger_record(approved_row)
    if unit is None:
        raise ValueError("cannot normalize approved row")
    return str(ledger_unit_metadata(unit).get("content_hash") or "")


def read_export_rows(export_path: Path, ledger_id: str) -> list[dict]:
    if not export_path.is_file():
        return []
    rows: list[dict] = []
    for raw in export_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if str(row.get("ledger_id") or "").strip() == ledger_id.strip():
            rows.append(row)
    return rows


def reduce_proposal_events(events_path: Path) -> dict[str, dict]:
    from conflict_events import reduce_events

    rows = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
    return reduce_events(rows)
