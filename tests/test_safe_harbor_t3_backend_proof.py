# pylint: disable=protected-access,redefined-outer-name,import-outside-toplevel
"""Isolated Safe Harbor T3 pinned-backend proof (V4 ordering gate only).

Qualified entry:

    python -I -S -B tests/_safe_harbor_t3_backend_worker.py run-proof
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

if os.environ.get("SAFE_HARBOR_T3_BOOTSTRAPPED") != "1":
    raise SystemExit(
        "refusing test module import without launcher isolation: run "
        "python -I -S -B tests/_safe_harbor_t3_backend_worker.py run-proof"
    )
try:
    from tests._safe_harbor_bootstrap import require_expected_uid_match

    require_expected_uid_match()
except RuntimeError as exc:
    raise SystemExit(str(exc)) from exc

import pytest  # pylint: disable=wrong-import-position  # isolation must precede pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WORKER = ROOT / "tests" / "_safe_harbor_t3_backend_worker.py"
COLLECTION = "harbor_proof"
COLLECTION_B = "harbor_proof_b"
PROD_HOME = Path("/home/lauer")
PROD_DATA = PROD_HOME / ".local/share/convmem"
PROD_CONFIG = PROD_HOME / ".config/convmem"
RUNTIME_MAIN = PROD_HOME / "Projects/convmem/.worktrees/runtime-main"

from tests._safe_harbor_t3_backend_worker import (  # pylint: disable=wrong-import-position,ungrouped-imports  # pre-bootstrap import order
    build_allowlisted_env,
    ENV_PATH_KEYS,
    _constrain_under_fixture,
    _fixture_root,
    _require_isolated as _require_isolated_process,
    _collection_segments,
    cosine_vectors_equal,
    embedding_from_seed,
    live_backend_identity_client_free,
    read_persisted_embedding_vector,
    seq_id,
    segment_vector_synced,
    sqlite_schema_digest,
)


def _worker_env() -> dict[str, str]:
    allowed = {
        "HOME",
        "PATH",
        "LANG",
        "LC_ALL",
        "TZ",
        "PYTHONPATH",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONNOUSERSITE",
        "PYTHONHASHSEED",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD",
        *ENV_PATH_KEYS,
        "SAFE_HARBOR_T3_BOOTSTRAPPED",
        "SAFE_HARBOR_T3_EXPECTED_UID",
        "SAFE_HARBOR_T3_FIXTURE_ROOT",
        "SAFE_HARBOR_T3_EVIDENCE_ROOT",
        "CHROMA_TELEMETRY",
        "ANONYMIZED_TELEMETRY",
        "OTEL_SDK_DISABLED",
    }
    return {key: os.environ[key] for key in os.environ if key in allowed}


def _worker(*args: str, timeout: float = 180) -> subprocess.CompletedProcess[str]:
    for arg in args:
        if arg.startswith("/"):
            _constrain_under_fixture(Path(arg))
    return subprocess.run(
        [sys.executable, "-s", "-B", str(WORKER), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=_worker_env(),
    )


@dataclass(frozen=True)
class BackendIdentity:
    chromadb_version: str
    client_api: str
    chroma_api_impl: str
    rust_binding_sha256: str
    sqlite_migrations: tuple[int, ...]
    sqlite_schema_digest: str
    hnswlib: str


@dataclass(frozen=True)
class PersistedReleaseEvidence:
    collection_name: str
    collection_id: str
    metadata_segment_id: str
    vector_segment_id: str
    vector_watermark: int
    segment_digests: dict[str, str]
    backend_identity: BackendIdentity


def _segment_digests(seg_dir: Path) -> dict[str, str]:
    from chroma_write_guard import SEGMENT_FILES

    out: dict[str, str] = {}
    for name in SEGMENT_FILES:
        path = seg_dir / name
        if path.is_file():
            out[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _sqlite_ro(chroma: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{chroma / 'chroma.sqlite3'}?mode=ro", uri=True)


def backend_identity_from_probe(chroma: Path, collection: str) -> BackendIdentity:
    probe_out = chroma / ".backend-probe.json"
    done = _worker("probe_backend", str(chroma), collection, str(probe_out))
    if done.returncode != 0:
        raise RuntimeError(done.stderr[-2000:])
    probe = json.loads(probe_out.read_text(encoding="utf-8"))
    static = live_backend_identity_client_free(chroma)
    if probe.get("rust_binding_sha256") != static["rust_binding_sha256"]:
        raise RuntimeError("probe rust binding digest disagrees with module digest")
    return BackendIdentity(
        chromadb_version=static["chromadb_version"],
        client_api=static["client_api"],
        chroma_api_impl=static["chroma_api_impl"],
        rust_binding_sha256=static["rust_binding_sha256"],
        sqlite_migrations=tuple(static["sqlite_migrations"]),
        sqlite_schema_digest=static["sqlite_schema_digest"],
        hnswlib=static["hnswlib"],
    )


def capture_persisted_release_evidence(
    chroma: Path, collection: str, backend_identity: BackendIdentity
) -> PersistedReleaseEvidence:
    con = _sqlite_ro(chroma)
    try:
        con.execute("BEGIN")
        collection_id, meta_seg, vec_seg = _collection_segments(con, collection)
        applied = {sid: seq_id(raw) for sid, raw in con.execute("select segment_id, seq_id from max_seq_id")}
        if vec_seg not in applied:
            raise KeyError(f"vector segment {vec_seg} missing from max_seq_id at capture")
        vector_watermark = applied[vec_seg]
        if vector_watermark <= 0:
            raise ValueError("vector watermark must be positive at capture")
    finally:
        con.execute("ROLLBACK")
        con.close()
    vec_dir = chroma / vec_seg
    if not vec_dir.is_dir():
        raise FileNotFoundError(f"vector segment directory missing: {vec_dir}")
    return PersistedReleaseEvidence(
        collection_name=collection,
        collection_id=collection_id,
        metadata_segment_id=meta_seg,
        vector_segment_id=vec_seg,
        vector_watermark=vector_watermark,
        segment_digests=_segment_digests(vec_dir),
        backend_identity=backend_identity,
    )


def _identity_mismatch_reason(live: BackendIdentity, saved: BackendIdentity) -> str:
    if live.sqlite_schema_digest != saved.sqlite_schema_digest:
        return "sqlite_schema_digest_mismatch"
    if live.chromadb_version != saved.chromadb_version:
        return "chromadb_version_mismatch"
    if live.chroma_api_impl != saved.chroma_api_impl:
        return "chroma_api_impl_mismatch"
    if live.rust_binding_sha256 != saved.rust_binding_sha256:
        return "rust_binding_sha256_mismatch"
    if live.sqlite_migrations != saved.sqlite_migrations:
        return "sqlite_migrations_mismatch"
    if live.client_api != saved.client_api:
        return "client_api_mismatch"
    return "backend_identity_mismatch"


def _check_collection_position(chroma: Path, snap: PersistedReleaseEvidence) -> tuple[bool, str]:
    con = _sqlite_ro(chroma)
    try:
        con.execute("BEGIN")
        row = con.execute("select id, name from collections where name = ?", (snap.collection_name,)).fetchone()
        if not row:
            return False, "collection_missing"
        collection_id, _ = row
        if collection_id != snap.collection_id:
            return False, "collection_id_mismatch"
        scopes = dict(
            con.execute("select scope, id from segments where collection = ?", (collection_id,)).fetchall()
        )
        meta_seg, vec_seg = scopes.get("METADATA"), scopes.get("VECTOR")
        if meta_seg != snap.metadata_segment_id or vec_seg != snap.vector_segment_id:
            return False, "segment_identity_mismatch"
        applied = {sid: seq_id(raw) for sid, raw in con.execute("select segment_id, seq_id from max_seq_id")}
        if vec_seg not in applied:
            return False, "sequence_evidence_missing"
        meta_wm = applied.get(meta_seg)
        vec_wm = applied[vec_seg]
        if meta_wm is None:
            return False, "sequence_evidence_missing"
        if meta_wm != snap.vector_watermark or vec_wm != snap.vector_watermark:
            return False, f"watermark_drift meta={meta_wm} vec={vec_wm} saved={snap.vector_watermark}"
        pending = con.execute(
            "select count(*) from embeddings_queue where topic like ? and seq_id > ?",
            (f"%/{collection_id}", snap.vector_watermark),
        ).fetchone()[0]
        if pending:
            return False, f"queue_pending={pending}"
    finally:
        con.execute("ROLLBACK")
        con.close()
    return True, "positions_match"


def evaluate_persisted_release_predicate(chroma: Path, snap: PersistedReleaseEvidence) -> tuple[bool, str]:
    from chroma_write_guard import validate_segment, vector_census

    static = live_backend_identity_client_free(chroma)
    live = BackendIdentity(
        chromadb_version=static["chromadb_version"],
        client_api=static["client_api"],
        chroma_api_impl=static["chroma_api_impl"],
        rust_binding_sha256=static["rust_binding_sha256"],
        sqlite_migrations=tuple(static["sqlite_migrations"]),
        sqlite_schema_digest=static["sqlite_schema_digest"],
        hnswlib=static["hnswlib"],
    )
    if live != snap.backend_identity:
        return False, _identity_mismatch_reason(live, snap.backend_identity)
    if snap.vector_watermark <= 0:
        return False, "missing_vector_watermark"
    positions_ok, position_reason = _check_collection_position(chroma, snap)
    if not positions_ok:
        return False, position_reason
    vec_dir = chroma / snap.vector_segment_id
    if not vec_dir.is_dir():
        return False, "vector_segment_missing"
    if _segment_digests(vec_dir) != snap.segment_digests:
        return False, "segment_digest_mismatch"
    report = validate_segment(vec_dir)
    if not report.ok:
        return False, f"structural_invalid {list(report.failures)}"
    try:
        census_all = vector_census(chroma)
    except (FileNotFoundError, sqlite3.Error, OSError) as exc:
        return False, f"census_unavailable {exc}"
    row = census_all.get(snap.collection_name)
    if row is None:
        return False, "census_missing"
    if row.get("lost") or row.get("extra"):
        return False, f"census_mismatch {row}"
    return True, "admit"


def evaluate_census_only_predicate(chroma: Path, collection: str) -> bool:
    from chroma_write_guard import vector_census

    row = vector_census(chroma).get(collection)
    if row is None:
        return False
    return row.get("lost", 1) == 0 and row.get("extra", 1) == 0


def observe_metadata_int(chroma: Path, collection: str, embedding_id: str, key: str = "n") -> int | None:
    con = _sqlite_ro(chroma)
    try:
        con.execute("BEGIN")
        _, meta_seg, _ = _collection_segments(con, collection)
        row = con.execute(
            """
            select em.int_value
            from embeddings e
            join embedding_metadata em on em.id = e.id
            where e.segment_id = ? and e.embedding_id = ? and em.key = ?
            """,
            (meta_seg, embedding_id, key),
        ).fetchone()
        return int(row[0]) if row and row[0] is not None else None
    finally:
        con.execute("ROLLBACK")
        con.close()


def assert_persisted_metadata_vector_alignment(
    chroma: Path, collection: str, embedding_id: str, vector_segment_id: str
) -> None:
    meta_n = observe_metadata_int(chroma, collection, embedding_id)
    if meta_n is None:
        raise AssertionError(f"missing metadata for {embedding_id}")
    seg_dir = chroma / vector_segment_id
    if not segment_vector_synced(seg_dir, embedding_id):
        raise AssertionError(f"vector not synced for {embedding_id}; cannot assert persisted alignment")
    persisted = read_persisted_embedding_vector(seg_dir, embedding_id)
    expected = embedding_from_seed(meta_n)
    if not cosine_vectors_equal(persisted, expected):
        raise AssertionError(
            f"stale_or_misaligned: metadata n={meta_n} does not match persisted vector for {embedding_id}"
        )


def run_admission_and_safety_workflow(
    chroma: Path,
    snap: PersistedReleaseEvidence,
    collection: str,
    *,
    use_strict_predicate: bool,
    safety_ids: tuple[str, ...],
) -> tuple[bool, str, bool]:
    """Admission predicate then shared independent safety assertion on persisted bytes."""
    if use_strict_predicate:
        admitted, reason = evaluate_persisted_release_predicate(chroma, snap)
    else:
        admitted = evaluate_census_only_predicate(chroma, collection)
        reason = "census_only_admit" if admitted else "census_only_refuse"
    if not admitted:
        return False, reason, False
    safety_failed = False
    for embedding_id in safety_ids:
        try:
            assert_persisted_metadata_vector_alignment(chroma, collection, embedding_id, snap.vector_segment_id)
        except AssertionError:
            safety_failed = True
            break
    return True, reason, safety_failed


def simulate_same_generation_file_replacement(vec_dir: Path, backup: Path) -> None:
    from chroma_write_guard import SEGMENT_FILES

    for name in SEGMENT_FILES:
        src = backup / name
        if not src.is_file():
            continue
        staging = vec_dir / f".{name}.replacement-test"
        shutil.copy2(src, staging)
        os.replace(staging, vec_dir / name)


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    evidence_root = Path(os.environ["SAFE_HARBOR_T3_EVIDENCE_ROOT"])
    root = _constrain_under_fixture(tmp_path)
    inherited = os.environ.get("SAFE_HARBOR_T3_EXPECTED_UID", "").strip()
    parent_uid = int(inherited) if inherited else os.getuid()
    env = build_allowlisted_env(root, evidence_root, expected_uid=parent_uid)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    for key in (
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "CONVMEM_SKIP_RESTIC_GATE",
        "CONVMEM_RESTIC_GATE_EXCEPTION",
        "CONVMEM_CONFIRM_PROD",
        "CONVMEM_CONFIRM_LAB",
        "CONVMEM_T1_ISOLATED",
        "RESTIC_REPOSITORY",
        "RESTIC_PASSWORD_FILE",
        "RESTIC_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    _require_isolated_process()
    return root


@pytest.fixture
def chroma_dir(isolated: Path) -> Path:
    path = isolated / "chroma"
    path.mkdir()
    return path


@pytest.fixture
def evidence_path(isolated: Path) -> Path:
    return isolated / "v4-backend-proof-evidence.json"


def test_worker_path_safety_controls(chroma_dir: Path, evidence_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tests import _safe_harbor_t3_backend_worker as worker_module

    outside = chroma_dir.parent.parent / "unused-outside-case"
    link = chroma_dir / "escape-link"
    link.symlink_to(outside, target_is_directory=True)
    observations = []
    for label, target, output in (
        ("target", outside / "chroma", chroma_dir / "out.json"),
        ("output", chroma_dir, outside / "out.json"),
        ("symlink", link / "chroma", chroma_dir / "out.json"),
    ):
        done = subprocess.run(
            [sys.executable, "-s", "-B", str(WORKER), "observe", str(target), COLLECTION, str(output)],
            cwd=ROOT, env=_worker_env(), capture_output=True, text=True, timeout=30, check=False,
        )
        assert done.returncode != 0 and "refusing path outside fixture root" in done.stderr, done.stderr
        observations.append({"case": label, "returncode": done.returncode, "stderr": done.stderr})
    assert not outside.exists()
    assert not (chroma_dir / "out.json").exists()
    assert not (chroma_dir / "chroma.sqlite3").exists()
    with monkeypatch.context() as changed:
        changed.setattr(worker_module.os, "getuid", lambda: 0)
        with pytest.raises(RuntimeError, match="refusing root uid"):
            worker_module._require_isolated()
    # A flag-free entry must refuse before pytest or any project imports.
    env = _worker_env()
    env.pop("SAFE_HARBOR_T3_BOOTSTRAPPED")
    done = subprocess.run(
        [sys.executable, "-I", "-S", "-B", str(Path(__file__))],
        env=env, cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
    )
    assert done.returncode != 0 and "refusing test module import without launcher isolation" in done.stderr
    evidence_path.write_text(json.dumps({"worker_path_safety": observations,
        "uid_refusal": f"simulated uid 0; actual process uid {os.getuid()}",
        "unsafe_entry_returncode": done.returncode}, indent=2), encoding="utf-8")


@pytest.mark.parametrize("value", [None, "1", b""])
def test_unknown_sequence_encoding_refuses(value: Any) -> None:
    with pytest.raises((TypeError, ValueError)):
        seq_id(value)


def test_pinned_backend_identity(chroma_dir: Path, evidence_path: Path) -> None:
    import importlib.metadata
    import numpy as np

    identity = backend_identity_from_probe(chroma_dir, COLLECTION)
    static = live_backend_identity_client_free(chroma_dir)
    assert identity.chromadb_version == "1.5.9"
    assert identity.client_api == static["client_api"]
    assert identity.chroma_api_impl == static["chroma_api_impl"]
    assert identity.rust_binding_sha256 == static["rust_binding_sha256"]
    assert identity.sqlite_schema_digest == sqlite_schema_digest(chroma_dir)
    payload = {
        "python": sys.version.split()[0],
        "interpreter": sys.executable,
        "interpreter_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        "harness_sha256": {
            "test": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "worker": hashlib.sha256(WORKER.read_bytes()).hexdigest(),
        },
        "numpy": np.__version__,
        "hnswlib": importlib.metadata.version("hnswlib"),
        "uid": os.getuid(),
        "fixture_root": str(_fixture_root()),
        "backend_identity": asdict(identity),
        "client_free_identity": static,
        "probe_server_api_observed": json.loads(
            (chroma_dir / ".backend-probe.json").read_text(encoding="utf-8")
        ).get("server_api_observed"),
    }
    evidence_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_operation_sequence_monotonic_queue_purge_and_restart(chroma_dir: Path, evidence_path: Path) -> None:
    out = chroma_dir / "sequence.json"
    done = _worker("sequence", str(chroma_dir), COLLECTION, str(out))
    assert done.returncode == 0, done.stderr[-2000:]
    trace = json.loads(out.read_text(encoding="utf-8"))["trace"]
    watermarks: list[tuple[int | None, int | None]] = []
    queue_lengths: list[int] = []
    queue_traces: list[list[dict[str, Any]]] = []
    for row in trace:
        snap = row["sqlite_after"]
        watermarks.append((snap["metadata_watermark"], snap["vector_watermark"]))
        queue_lengths.append(snap["queue_total"])
        queue_traces.append(snap["queue_rows"])
    for prev, cur in zip(watermarks, watermarks[1:], strict=False):
        assert cur[0] is not None and prev[0] is not None and cur[0] >= prev[0]
        if prev[1] is not None:
            assert cur[1] is not None and cur[1] >= prev[1], (prev, cur)
    decreases = [i for i in range(len(queue_lengths) - 1) if queue_lengths[i + 1] < queue_lengths[i]]
    assert decreases, f"expected adjacent queue decrease, lengths={queue_lengths}"
    purge_idx = decreases[0]
    before_rows = queue_traces[purge_idx]
    after_rows = queue_traces[purge_idx + 1]
    assert before_rows, "expected queue rows before purge"
    assert len(after_rows) < len(before_rows) or queue_lengths[purge_idx + 1] < queue_lengths[purge_idx]
    restart = _worker("restart_ping", str(chroma_dir), COLLECTION)
    assert restart.returncode == 0, restart.stderr
    after = json.loads(restart.stdout)
    assert after["count"] == 1
    assert after["document"] == "doc-a3"
    assert after["metadata_n"] == 4
    assert after["client_embedding_matches_seed_200"] is True
    assert after["sqlite"]["metadata_watermark"] == watermarks[-1][0]
    assert after["sqlite"]["vector_watermark"] == watermarks[-1][1]
    if after["sqlite"]["metadata_watermark"] == after["sqlite"]["vector_watermark"]:
        assert after["persisted_vector_matches_seed_200"] is True
    else:
        # A current client read can replay pending work without a new vector save.
        assert after["sqlite"]["queue_pending_after_floor"] > 0
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    evidence["sequence"] = {
        "worker_mode": "sequence",
        "worker_returncode": done.returncode,
        "watermarks": watermarks,
        "queue_lengths": queue_lengths,
        "queue_purge_index": purge_idx,
        "queue_rows_before_purge": before_rows,
        "queue_rows_after_purge": after_rows,
        "restart": after,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def seed_native_capacity(collection: Any) -> None:
    """Native inserts only: fill the initial 100-slot capacity for valid controls."""
    collection.upsert(
        ids=[f"padding-{n}" for n in range(98)],
        embeddings=[embedding_from_seed(1000 + n) for n in range(98)],
        metadatas=[{"n": 1000 + n} for n in range(98)],
    )


def test_valid_releasable_control_after_restart(chroma_dir: Path, evidence_path: Path) -> None:
    import chromadb

    identity = backend_identity_from_probe(chroma_dir, COLLECTION)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection(
        COLLECTION,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 2, "batch_size": 1}},
    )
    col.upsert(ids=["a"], embeddings=[embedding_from_seed(1)], metadatas=[{"n": 1}])
    col.upsert(ids=["b"], embeddings=[embedding_from_seed(2)], metadatas=[{"n": 2}])
    seed_native_capacity(col)
    client.close()
    snap = capture_persisted_release_evidence(chroma_dir, COLLECTION, identity)
    vec_dir = chroma_dir / snap.vector_segment_id
    backup = chroma_dir / "vec-backup-releasable"
    shutil.copytree(vec_dir, backup)
    restart = _worker("restart_ping", str(chroma_dir), COLLECTION)
    assert restart.returncode == 0, restart.stderr
    admitted, reason, safety_failed = run_admission_and_safety_workflow(
        chroma_dir, snap, COLLECTION, use_strict_predicate=True, safety_ids=("a", "b")
    )
    assert admitted and not safety_failed, (reason, safety_failed)
    simulate_same_generation_file_replacement(vec_dir, backup)
    observe = _worker("client_free_observe", str(chroma_dir), COLLECTION)
    assert observe.returncode == 0, observe.stderr
    observed = json.loads(observe.stdout)
    assert observed["segment_digests"] == snap.segment_digests
    ok_replace, reason_replace = evaluate_persisted_release_predicate(chroma_dir, snap)
    assert ok_replace, reason_replace
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    evidence["releasable_control"] = {
        "predicate_admit": True,
        "predicate_reason": reason,
        "same_generation_replacement_admit": ok_replace,
        "same_generation_replacement_reason": reason_replace,
        "client_free_observe_returncode": observe.returncode,
        "client_free_observe": observed,
        "snapshot": asdict(snap),
    }
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def test_stale_vector_refusal_and_census_blind_spot(chroma_dir: Path, evidence_path: Path) -> None:
    import chromadb

    identity = backend_identity_from_probe(chroma_dir, COLLECTION)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection(
        COLLECTION,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 2, "batch_size": 1}},
    )
    col.upsert(ids=["a"], embeddings=[embedding_from_seed(1)], metadatas=[{"n": 1}])
    col.upsert(ids=["b"], embeddings=[embedding_from_seed(2)], metadatas=[{"n": 2}])
    seed_native_capacity(col)
    client.close()
    snap = capture_persisted_release_evidence(chroma_dir, COLLECTION, identity)
    vec_dir = chroma_dir / snap.vector_segment_id
    backup = chroma_dir / "vec-backup-stale"
    shutil.copytree(vec_dir, backup)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_collection(COLLECTION)
    col.update(ids=["a"], embeddings=[embedding_from_seed(99)], metadatas=[{"n": 99}])
    col.upsert(ids=["b"], embeddings=[embedding_from_seed(2)], metadatas=[{"n": 2}])
    client.close()
    shutil.rmtree(vec_dir)
    shutil.copytree(backup, vec_dir)
    observed_n = observe_metadata_int(chroma_dir, COLLECTION, "a")
    assert observed_n == 99, f"expected sqlite metadata n=99, got {observed_n}"
    persisted_a = read_persisted_embedding_vector(vec_dir, "a")
    assert cosine_vectors_equal(persisted_a, embedding_from_seed(1))
    assert not cosine_vectors_equal(persisted_a, embedding_from_seed(99))
    strict_admitted, strict_reason, _ = run_admission_and_safety_workflow(
        chroma_dir, snap, COLLECTION, use_strict_predicate=True, safety_ids=("a",)
    )
    assert not strict_admitted, strict_reason
    census_admitted, census_reason, census_safety_failed = run_admission_and_safety_workflow(
        chroma_dir, snap, COLLECTION, use_strict_predicate=False, safety_ids=("a",)
    )
    assert census_admitted and census_safety_failed, (census_reason, census_safety_failed)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    evidence["stale_control"] = {
        "observed_metadata_n": observed_n,
        "strict_refuses": strict_reason,
        "census_admits_then_safety_fails": census_safety_failed,
        "census_reason": census_reason,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def test_binding_two_collections_and_negative_controls(chroma_dir: Path, evidence_path: Path) -> None:
    import chromadb

    identity = backend_identity_from_probe(chroma_dir, COLLECTION)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    col_a = client.get_or_create_collection(
        COLLECTION,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 2, "batch_size": 1}},
    )
    col_b = client.get_or_create_collection(
        COLLECTION_B,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 2, "batch_size": 1}},
    )
    col_a.upsert(
        ids=["a", "c"],
        embeddings=[embedding_from_seed(1), embedding_from_seed(3)],
        metadatas=[{"n": 1}, {"n": 3}],
    )
    seed_native_capacity(col_a)
    col_b.upsert(ids=["x"], embeddings=[embedding_from_seed(50)], metadatas=[{"n": 50}])
    client.close()
    snap_a = capture_persisted_release_evidence(chroma_dir, COLLECTION, identity)
    client = chromadb.PersistentClient(path=str(chroma_dir))
    client.get_collection(COLLECTION_B).upsert(
        ids=["x"], embeddings=[embedding_from_seed(51)], metadatas=[{"n": 51}]
    )
    client.close()
    ok_a, reason_a = evaluate_persisted_release_predicate(chroma_dir, snap_a)
    assert ok_a, reason_a
    refusal_reasons = {}
    for label, damaged, expected_reason in (
        ("wrong_segment", replace(snap_a, vector_segment_id="00000000-0000-0000-0000-000000000000"),
         "segment_identity_mismatch"),
        ("wrong_collection", replace(snap_a, collection_id="00000000-0000-0000-0000-000000000000"),
         "collection_id_mismatch"),
        ("missing_watermark", replace(snap_a, vector_watermark=0), "missing_vector_watermark"),
        ("backend_version", replace(snap_a, backend_identity=replace(identity, chromadb_version="0.0.0")),
         "chromadb_version_mismatch"),
        ("schema", replace(snap_a, backend_identity=replace(identity, sqlite_schema_digest="0" * 64)),
         "sqlite_schema_digest_mismatch"),
    ):
        admitted, refusal = evaluate_persisted_release_predicate(chroma_dir, damaged)
        assert not admitted and refusal == expected_reason, (label, admitted, refusal)
        refusal_reasons[label] = refusal
    vec_dir = chroma_dir / snap_a.vector_segment_id
    digests_before = _segment_digests(vec_dir)
    header = vec_dir / "header.bin"
    header_backup = chroma_dir / "header.bin.bak"
    shutil.copy2(header, header_backup)
    raw = bytearray(header.read_bytes())
    raw[-1] ^= 0x01
    header.write_bytes(bytes(raw))
    ok_digest, reason_digest = evaluate_persisted_release_predicate(chroma_dir, snap_a)
    assert not ok_digest and reason_digest == "segment_digest_mismatch"
    shutil.copy2(header_backup, header)
    os.utime(header, (time.time() + 5000, time.time() + 5000))
    assert _segment_digests(vec_dir) == digests_before
    ok_mtime, reason_mtime = evaluate_persisted_release_predicate(chroma_dir, snap_a)
    assert ok_mtime, reason_mtime
    con = sqlite3.connect(chroma_dir / "chroma.sqlite3")
    try:
        con.execute("delete from max_seq_id where segment_id = ?", (snap_a.vector_segment_id,))
        con.commit()
    finally:
        con.close()
    ok_seq, reason_seq = evaluate_persisted_release_predicate(chroma_dir, snap_a)
    assert not ok_seq and reason_seq == "sequence_evidence_missing"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    evidence["binding_controls"] = {
        "collection_a_admits_after_b_mutation": reason_a,
        **refusal_reasons,
        "sequence_evidence_missing": reason_seq,
        "digest_mismatch": reason_digest,
        "mtime_only_still_admits": reason_mtime,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
