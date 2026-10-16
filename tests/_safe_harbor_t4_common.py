# pylint: disable=too-many-lines,protected-access
"""Isolated subprocess worker for Safe Harbor T4 V5 evidence.

Must run under SAFE_HARBOR_T3_BOOTSTRAPPED with fixture-bound CONVMEM_CONFIG.
Validates confinement before importing project modules.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T2_RUNNER = ROOT / "tests" / "_safe_harbor_t2_cli.py"
SUBPROCESS_TIMEOUT = 300.0


def _load_bootstrap():
    # pylint: disable=duplicate-code
    # Independent stdlib child bootstrap must precede package imports.
    path = ROOT / "tests" / "_safe_harbor_bootstrap.py"
    spec = importlib.util.spec_from_file_location("safe_harbor_t4_bootstrap", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bootstrap from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# pylint: enable=duplicate-code

def _fixture_root() -> Path:
    raw = os.environ.get("SAFE_HARBOR_T3_FIXTURE_ROOT", "").strip()
    if not raw:
        raise RuntimeError("SAFE_HARBOR_T3_FIXTURE_ROOT required")
    return Path(raw).resolve(strict=False)


def _refuse_outside_fixture(path: Path) -> Path:
    root = _fixture_root()
    resolved = path.expanduser().resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise RuntimeError(f"refusing path outside fixture root: {resolved}")
    return resolved


def _require_child_isolation() -> None:
    bootstrap = _load_bootstrap()
    bootstrap.require_t3_bootstrap()
    if not getattr(sys, "_safe_harbor_t4_network_refused", False):
        raise RuntimeError("T4 network refusal hook missing before project imports")
    backend = bootstrap.load_stdlib_module(
        ROOT / "tests" / "_safe_harbor_t3_backend_worker.py",
        "safe_harbor_t4_backend_worker_isolation",
    )
    backend._require_isolated()  # pylint: disable=protected-access


def _run_t2_cli(
    *args: str,
    env: dict[str, str] | None = None,
    stdin: str | None = None,
    expect_rc: int | None = None,
) -> subprocess.CompletedProcess[str]:
    if not os.environ.get("SAFE_HARBOR_T2_NOW"):
        raise RuntimeError("SAFE_HARBOR_T2_NOW must be set before admission")
    from tests._safe_harbor_t4_harness import run_fixture_child
    proc = run_fixture_child(
        [sys.executable, "-s", "-B", str(T2_RUNNER), "cli", *args],
        env=dict(os.environ) if env is None else env,
        input_text=stdin,
        timeout=SUBPROCESS_TIMEOUT,
    )
    if proc.returncode is None:
        raise RuntimeError("subprocess missing returncode")
    if expect_rc is not None and proc.returncode != expect_rc:
        raise RuntimeError(
            f"cli {args!r} rc={proc.returncode} expected {expect_rc}: "
            f"{proc.stdout}{proc.stderr}"
        )
    return proc


def _install_fakes() -> None:
    runner = ROOT / "tests" / "_safe_harbor_t2_cli.py"
    spec = importlib.util.spec_from_file_location("safe_harbor_t2_cli_probe", runner)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load t2 cli for fakes")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._install_fakes()
    hook = os.environ.get("SAFE_HARBOR_T2_HOOK", "").strip()
    if hook:
        mod._install_hook()


def _emit(payload: dict[str, Any], *, rc: int = 0) -> int:
    print(json.dumps(payload, sort_keys=True))
    return rc


def _identity() -> dict[str, Any]:
    import chromadb

    return {
        "verdict": "PASS",
        "python": sys.version.split()[0],
        "chromadb": chromadb.__version__,
        "executable": sys.executable,
    }


def _load_cfg():
    import config

    cfg = config.load_config()
    _refuse_outside_fixture(Path(cfg["index"]["chroma_dir"]))
    export = cfg["index"].get("units_export")
    if export:
        _refuse_outside_fixture(Path(export))
    return cfg


def _dump_state(cfg) -> dict[str, Any]:
    data = Path(cfg["index"]["chroma_dir"]).expanduser().parent
    files = [
        str(data / "knowledge_units.jsonl"),
        str(data / "pending_decisions.jsonl"),
        str(data / "decisions-approved.jsonl"),
        str(data / "pending_decision_events.jsonl"),
    ]
    from tests._safe_harbor_t4_harness import run_fixture_child
    proc = run_fixture_child(
        [sys.executable, "-s", "-B", str(T2_RUNNER), "dump", *files],
        env=os.environ.copy(),
        timeout=SUBPROCESS_TIMEOUT,
    )
    if proc.returncode is None:
        raise RuntimeError("dump subprocess missing returncode")
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("dump produced empty stdout")
    return json.loads(lines[-1])


def _pid_events(cfg, pid: str) -> list[dict]:
    from propose_decision import data_dir

    path = data_dir(cfg) / "pending_decision_events.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [row for row in rows if row.get("proposal_id") == pid]


def _approved_row(cfg, pid: str) -> dict:
    from propose_decision import approved_for_proposal

    row = approved_for_proposal(cfg, pid)
    if row is None:
        raise RuntimeError(f"missing approved row for {pid}")
    return row


def _recover(cfg, pid: str) -> str:
    from propose_decision import recover_approval

    return recover_approval(cfg, pid)


def _setup_event_only(cfg) -> str:
    """Mirror test_safe_harbor_t2._event_only_state: propose then indexed approve."""
    _run_t2_cli(
        "record",
        "--relates-to",
        "dec_prop_t4_parent",
        "--summary",
        "T4 probe",
        "--rationale",
        "fixture",
        "--author",
        "cursor",
        "--constraint",
        "none-identified",
        stdin="y\n",
        expect_rc=0,
    )
    qpath = Path(cfg["index"]["chroma_dir"]).expanduser().parent / "pending_decisions.jsonl"
    pid = json.loads(qpath.read_text(encoding="utf-8").splitlines()[-1])["id"]
    os.environ["SAFE_HARBOR_T2_HOOK"] = "fail_after_chroma_ingest"
    proc = _run_t2_cli("record", "--approve", pid, stdin="y\n")
    os.environ.pop("SAFE_HARBOR_T2_HOOK", None)
    if proc.returncode != 1:
        raise RuntimeError(f"expected interrupted approve rc=1: {proc.stdout}{proc.stderr}")
    if "Approval apply deferred for recovery" not in proc.stdout:
        raise RuntimeError(f"missing deferred recovery message: {proc.stdout}")
    return pid


def _setup_approval_started(cfg) -> str:
    os.environ.pop("SAFE_HARBOR_T2_HOOK", None)
    _run_t2_cli(
        "record",
        "--relates-to",
        "dec_prop_t4_parent",
        "--summary",
        "T4 started",
        "--rationale",
        "fixture",
        "--author",
        "cursor",
        "--constraint",
        "none-identified",
        stdin="y\n",
        expect_rc=0,
    )
    qpath = Path(cfg["index"]["chroma_dir"]).expanduser().parent / "pending_decisions.jsonl"
    pid = json.loads(qpath.read_text(encoding="utf-8").splitlines()[-1])["id"]
    _run_t2_cli("record", "--approve", pid, "--no-index", stdin="y\n", expect_rc=0)
    return pid


def _unit_for_pid(state: dict, pid: str) -> dict:
    for unit in state["chroma"].get("units") or []:
        if (unit.get("metadata") or {}).get("proposal_id") == pid:
            return unit
    raise RuntimeError(f"no chroma unit for proposal {pid}")


def _ledger_id_for_pid(cfg, pid: str) -> str:
    row = _approved_row(cfg, pid)
    return str(row.get("id") or row.get("ledger_id") or pid)


def _independent_ingest_hash(approved_row: dict) -> str:
    from ledger import ledger_unit_metadata, normalize_ledger_record

    unit = normalize_ledger_record(approved_row)
    if unit is None:
        raise RuntimeError("approved row failed normalization")
    digest = str(ledger_unit_metadata(unit).get("content_hash") or "").strip()
    if len(digest) != 64:
        raise RuntimeError("independent ingest hash missing")
    return digest


def _expected_embedding_sha(document: str) -> str:
    base = (sum(ord(c) for c in document) % 997) / 997.0
    vec = [round(float(base), 6)] * 768
    return hashlib.sha256(json.dumps(vec).encode()).hexdigest()


def _lifecycle_state(cfg, pid: str) -> str:
    from conflict_events import load_events, reduce_events

    return reduce_events(load_events(cfg))[pid]["lifecycle_state"]


def _assert_event_only_unit_unchanged(before_unit: dict, after_unit: dict) -> None:
    assert before_unit["id"] == after_unit["id"]
    assert before_unit.get("document") == after_unit.get("document")
    assert before_unit.get("embedding_sha") == after_unit.get("embedding_sha")
    assert before_unit.get("metadata") == after_unit.get("metadata")


def _matrix_create_absence(cfg) -> dict[str, Any]:
    pid = _setup_approval_started(cfg)
    before = _dump_state(cfg)
    action = _recover(cfg, pid)
    after = _dump_state(cfg)
    row = _approved_row(cfg, pid)
    expected_hash = _independent_ingest_hash(row)
    unit = _unit_for_pid(after, pid)
    assert unit["metadata"].get("content_hash") == expected_hash
    assert action == "retry_chroma"
    export_path = Path(cfg["index"]["units_export"])
    ledger_id = _ledger_id_for_pid(cfg, pid)
    exports = [
        json.loads(line)
        for line in export_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("ledger_id") == ledger_id
    ]
    assert len(exports) == 1
    assert exports[0]["id"] == unit["id"]
    events = _pid_events(cfg, pid)
    assert [e["event_type"] for e in events].count("APPROVED") == 1
    assert _lifecycle_state(cfg, pid) == "APPROVED"
    return {
        "verdict": "PASS",
        "action": action,
        "pid": pid,
        "before_units": len(before["chroma"].get("units") or []),
        "after_units": len(after["chroma"].get("units") or []),
        "export_id": exports[0]["id"],
        "chroma_id": unit["id"],
        "embedding_sha": unit.get("embedding_sha"),
    }


def _matrix_event_only(cfg) -> dict[str, Any]:
    pid = _setup_event_only(cfg)
    before = _dump_state(cfg)
    before_unit = _unit_for_pid(before, pid)
    assert _expected_embedding_sha(before_unit.get("document") or "") == before_unit.get(
        "embedding_sha"
    )
    action = _recover(cfg, pid)
    after = _dump_state(cfg)
    after_unit = _unit_for_pid(after, pid)
    assert action == "approve"
    _assert_event_only_unit_unchanged(before_unit, after_unit)
    ledger_id = _ledger_id_for_pid(cfg, pid)
    exports = [
        json.loads(line)
        for line in Path(cfg["index"]["units_export"]).read_text(encoding="utf-8").splitlines()
        if line.strip() and json.loads(line).get("ledger_id") == ledger_id
    ]
    assert len(exports) == 1
    assert exports[0]["id"] == after_unit["id"]
    assert exports[0].get("summary") == after_unit["metadata"].get("summary")
    events = _pid_events(cfg, pid)
    assert [e["event_type"] for e in events].count("APPROVED") == 1
    assert _lifecycle_state(cfg, pid) == "APPROVED"
    return {"verdict": "PASS", "action": action, "pid": pid}


def _prime_ledger_cache(_cfg) -> None:
    from chroma_write_store import open_production_recovery_write_store
    from ledger import build_ledger_index

    session = open_production_recovery_write_store(entrypoint="propose_decision.write")
    try:
        build_ledger_index(session.store)
    finally:
        session.store.close()


def _matrix_warm_same_process(cfg) -> dict[str, Any]:
    pid = _setup_event_only(cfg)
    _prime_ledger_cache(cfg)
    first = _recover(cfg, pid)
    _prime_ledger_cache(cfg)
    second = _recover(cfg, pid)
    assert first == "approve"
    assert second == "approve"
    assert [e["event_type"] for e in _pid_events(cfg, pid)].count("APPROVED") == 1
    return {"verdict": "PASS", "first": first, "second": second, "pid": pid}


def _matrix_cli_recover(cfg, command="propose_decision") -> dict[str, Any]:
    pid = _setup_event_only(cfg)
    proc = subprocess.run(
        [sys.executable, "-s", "-B", str(T2_RUNNER), "cli", command, "--recover", pid],
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT,
        check=False,
    )
    if proc.returncode is None:
        raise RuntimeError("cli recover missing returncode")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert [e["event_type"] for e in _pid_events(cfg, pid)].count("APPROVED") == 1
    return {"verdict": "PASS", "stdout": proc.stdout.strip(), "pid": pid}


def _matrix_cli_record(cfg) -> dict[str, Any]:
    return _matrix_cli_recover(cfg, command="record")


def _resolve_pid(cfg) -> str:
    preseed = os.environ.get("SAFE_HARBOR_T4_PRESEEDED_PID", "").strip()
    if preseed:
        return preseed
    return _setup_event_only(cfg)


def _matrix_unbound_helper(cfg) -> dict[str, Any]:
    pid = _resolve_pid(cfg)
    from propose_decision import recover_approval

    action = recover_approval(cfg, pid)
    assert action == "approve"
    return {"verdict": "PASS", "action": action, "pid": pid, "probe_pid": os.getpid()}


def _recover_only(cfg) -> dict[str, Any]:
    pid = _resolve_pid(cfg)
    action = _recover(cfg, pid)
    return {"verdict": "PASS", "action": action, "pid": pid, "probe_pid": os.getpid()}


def _matrix_marker_repair(cfg) -> dict[str, Any]:
    pid = _setup_event_only(cfg)
    state = _dump_state(cfg)
    unit = _unit_for_pid(state, pid)
    chroma_id = unit["id"]
    doc_before = unit.get("document")
    emb_before = unit.get("embedding_sha")
    from chroma_write_store import open_production_recovery_write_store
    from purge_locks import index_write_flock

    with index_write_flock(cfg):
        session = open_production_recovery_write_store(entrypoint="propose_decision.write")
        store = session.store
        try:
            meta = dict(unit["metadata"])
            meta["proposal_id"] = ""
            store.update_unit_metadata(chroma_id, meta)
        finally:
            store.close()
    action = _recover(cfg, pid)
    assert action == "repair_marker"
    after = _dump_state(cfg)
    after_unit = _unit_for_pid(after, pid)
    assert after_unit["id"] == chroma_id
    assert after_unit.get("document") == doc_before
    assert after_unit.get("embedding_sha") == emb_before
    assert after_unit["metadata"].get("proposal_id") == pid
    return {"verdict": "PASS", "action": action, "pid": pid}


def _spawn_probe_case(case: str, *, pid: str) -> tuple[int, dict[str, Any]]:
    cmd = [sys.executable, "-s", "-B", str(ROOT / "tests" / "_safe_harbor_t4_probe.py"), case]
    env = os.environ.copy()
    env["SAFE_HARBOR_T4_PRESEEDED_PID"] = pid
    from tests._safe_harbor_t4_harness import run_fixture_child
    proc = run_fixture_child(
        cmd,
        env=env,
        timeout=SUBPROCESS_TIMEOUT,
    )
    if proc.returncode is None:
        raise RuntimeError(f"missing returncode for child {case}")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"empty child stdout for {case}: {proc.stderr}")
    payload = json.loads(lines[-1])
    return proc.returncode, payload


def _matrix_fresh_process_retry(cfg) -> dict[str, Any]:
    pid = _setup_event_only(cfg)
    rc1, payload1 = _spawn_probe_case("recover.only", pid=pid)
    rc2, payload2 = _spawn_probe_case("recover.only", pid=pid)
    assert rc1 == 0 and payload1.get("verdict") == "PASS"
    assert rc2 == 0 and payload2.get("verdict") == "PASS"
    assert payload1.get("probe_pid") != payload2.get("probe_pid")
    count = [e["event_type"] for e in _pid_events(cfg, pid)].count("APPROVED")
    assert count == 1
    return {
        "verdict": "PASS",
        "pid": pid,
        "approved_count": count,
        "child_probe_pids": [payload1.get("probe_pid"), payload2.get("probe_pid")],
    }


def _matrix_base_retry(cfg) -> dict[str, Any]:
    _run_t2_cli(
        "record",
        "--relates-to",
        "dec_prop_t4_base_parent",
        "--summary",
        "Base decision",
        "--rationale",
        "seed chroma",
        "--author",
        "cursor",
        "--constraint",
        "none-identified",
        stdin="y\n",
        expect_rc=0,
    )
    _run_t2_cli("record", "--approve-last", stdin="y\n", expect_rc=0)
    state = _dump_state(cfg)
    base_unit = next(
        u
        for u in state["chroma"]["units"]
        if (u.get("metadata") or {}).get("summary") == "Base decision"
    )
    ledger_id = base_unit["metadata"]["ledger_id"]
    from propose_decision import approve, propose

    revision = propose(
        cfg,
        relates_to=ledger_id,
        summary="Base decision revised",
        rationale="targeted update",
        author="cursor",
        constraints=["none-identified"],
        target_ledger_id=ledger_id,
    )
    pid = revision["id"]
    approve(cfg, pid, signer="ryan", ledger_id=ledger_id)
    action = _recover(cfg, pid)
    assert action == "retry_chroma"
    after = _dump_state(cfg)
    unit = next(
        u for u in after["chroma"]["units"] if (u.get("metadata") or {}).get("ledger_id") == ledger_id
    )
    row = _approved_row(cfg, pid)
    assert unit["metadata"].get("content_hash") == _independent_ingest_hash(row)
    assert unit["metadata"].get("proposal_id") == pid
    return {"verdict": "PASS", "action": action, "pid": pid}
