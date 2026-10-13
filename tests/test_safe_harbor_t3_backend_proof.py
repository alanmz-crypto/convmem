# pylint: disable=protected-access,redefined-outer-name,import-outside-toplevel
"""Isolated Safe Harbor T3 pinned-backend proof (V4 ordering gate only).

Synthetic Chroma 1.5.9 scratch stores under disposable /tmp roots. No production
CLI, corpus, doctor, indexing or Restic access. The test-local strict release
predicate mirrors execution E1's empty-changed-set oracle; it is not production code.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import pwd
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tests" / "_safe_harbor_t3_backend_worker.py"
PYTHON = sys.executable
COLLECTION = "harbor_proof"
PROD_HOME = Path("/home/lauer")
PROD_DATA = PROD_HOME / ".local/share/convmem"
PROD_CONFIG = PROD_HOME / ".config/convmem"
RUNTIME_MAIN = PROD_HOME / "Projects/convmem/.worktrees/runtime-main"

_SCRUBBED_ENV = (
    "CONVMEM_SKIP_RESTIC_GATE",
    "CONVMEM_RESTIC_GATE_EXCEPTION",
    "CONVMEM_CONFIRM_PROD",
    "CONVMEM_CONFIRM_LAB",
    "CONVMEM_T1_ISOLATED",
    "RESTIC_REPOSITORY",
    "RESTIC_PASSWORD_FILE",
    "RESTIC_PASSWORD",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
)


def _production_roots() -> list[Path]:
    roots = [PROD_DATA, PROD_CONFIG, RUNTIME_MAIN]
    try:
        account = Path(pwd.getpwuid(os.getuid()).pw_dir)
        roots += [account / ".local/share/convmem", account / ".config/convmem"]
    except KeyError:
        pass
    return [r.resolve(strict=False) for r in roots]


def _refuse_production(path: Path) -> Path:
    resolved = Path(path).expanduser().resolve(strict=False)
    for banned in _production_roots():
        if resolved == banned or banned in resolved.parents or resolved in banned.parents:
            raise RuntimeError(f"refusing production-overlapping path {resolved}")
    return resolved


def _require_isolated_process() -> None:
    home = Path.home().resolve()
    if home == PROD_HOME:
        raise RuntimeError(f"refusing production HOME {home}")
    _refuse_production(home)
    for key in (
        "CONVMEM_CONFIG",
        "CONVMEM_ROOT",
        "CONVMEM_RESTIC_ENV",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "RESTIC_CACHE_DIR",
        "TMPDIR",
    ):
        raw = os.environ.get(key, "")
        if not raw or not Path(raw).is_absolute():
            raise RuntimeError(f"refusing unset/relative {key}={raw!r}")
        _refuse_production(Path(raw))
    for key in _SCRUBBED_ENV:
        if key in os.environ:
            raise RuntimeError(f"refusing inherited {key}")


def _seq_id(value: Any) -> int:
    if isinstance(value, bytes):
        return int.from_bytes(value, "big")
    return int(value or 0)


def _embedding(seed: int) -> list[float]:
    digest = hashlib.sha256(f"safe-harbor-t3:{seed}".encode()).digest()
    return [((digest[i] % 200) - 100) / 100.0 for i in range(16)]


def _worker(*args: str, timeout: float = 180) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    done = subprocess.run(
        [PYTHON, str(WORKER), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )
    return done


def _vector_segment_dir(chroma: Path) -> Path:
    for entry in chroma.iterdir():
        if entry.is_dir() and (entry / "header.bin").is_file():
            return entry
    raise FileNotFoundError(f"no vector segment under {chroma}")


@dataclass(frozen=True)
class SavedVectorSource:
    collection_name: str
    collection_id: str
    metadata_segment_id: str
    vector_segment_id: str
    vector_watermark: int
    segment_signature: list[list[Any]]
    segment_digests: dict[str, str]
    expected_embeddings: dict[str, list[float]]
    chromadb_version: str


def _segment_digests(seg_dir: Path) -> dict[str, str]:
    from chroma_write_guard import SEGMENT_FILES

    out: dict[str, str] = {}
    for name in SEGMENT_FILES:
        path = seg_dir / name
        if path.is_file():
            out[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def capture_saved_vector_source(chroma: Path, collection: str, expected: dict[str, list[float]]) -> SavedVectorSource:
    import chromadb
    from chroma_write_guard import segment_signature

    db = chroma / "chroma.sqlite3"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        collection_id, _ = con.execute("select id, name from collections where name = ?", (collection,)).fetchone()
        scopes = dict(
            con.execute("select scope, id from segments where collection = ?", (collection_id,)).fetchall()
        )
        meta_seg, vec_seg = scopes["METADATA"], scopes["VECTOR"]
        applied = {sid: _seq_id(seq) for sid, seq in con.execute("select segment_id, seq_id from max_seq_id")}
    finally:
        con.close()
    vec_dir = chroma / str(vec_seg)
    if not vec_dir.is_dir():
        vec_dir = _vector_segment_dir(chroma)
    return SavedVectorSource(
        collection_name=collection,
        collection_id=collection_id,
        metadata_segment_id=meta_seg,
        vector_segment_id=vec_seg,
        vector_watermark=applied[vec_seg],
        segment_signature=segment_signature(vec_dir),
        segment_digests=_segment_digests(vec_dir),
        expected_embeddings=expected,
        chromadb_version=chromadb.__version__,
    )


def evaluate_strict_release_predicate(chroma: Path, snap: SavedVectorSource) -> tuple[bool, str]:
    """Test-local E1 empty-changed-set oracle (not production release code)."""
    import chromadb
    from chroma_write_guard import segment_signature, vector_census

    if chromadb.__version__ != snap.chromadb_version:
        return False, "chromadb_version_mismatch"
    if snap.vector_watermark <= 0:
        return False, "missing_vector_watermark"
    db = chroma / "chroma.sqlite3"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
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
        applied = {sid: _seq_id(seq) for sid, seq in con.execute("select segment_id, seq_id from max_seq_id")}
        meta_wm = applied.get(meta_seg, 0)
        vec_wm = applied.get(vec_seg, 0)
        if meta_wm != snap.vector_watermark or vec_wm != snap.vector_watermark:
            return False, f"watermark_drift meta={meta_wm} vec={vec_wm} saved={snap.vector_watermark}"
        pending = con.execute(
            "select count(*) from embeddings_queue where topic like ? and seq_id > ?",
            (f"%/{collection_id}", snap.vector_watermark),
        ).fetchone()[0]
        if pending:
            return False, f"queue_pending={pending}"
    finally:
        con.close()
    vec_dir = chroma / str(snap.vector_segment_id)
    if segment_signature(vec_dir) != snap.segment_signature:
        return False, "segment_signature_mismatch"
    if _segment_digests(vec_dir) != snap.segment_digests:
        return False, "segment_digest_mismatch"
    census = vector_census(chroma).get(snap.collection_name, {})
    if census.get("lost") or census.get("extra"):
        return False, f"census_mismatch {census}"
    read = _worker("read_embeddings", str(chroma), snap.collection_name, json.dumps(sorted(snap.expected_embeddings)))
    if read.returncode != 0:
        return False, f"embedding_read_failed {read.stderr[-500:]}"
    payload = json.loads(read.stdout)
    for id_, expected in snap.expected_embeddings.items():
        got = payload[id_]["embedding"]
        if got is None or len(got) != len(expected):
            return False, f"embedding_missing {id_}"
        if any(abs(a - b) > 1e-6 for a, b in zip(got, expected, strict=True)):
            return False, f"embedding_stale {id_}"
    return True, "admit"


def evaluate_census_only_predicate(chroma: Path, collection: str) -> bool:
    from chroma_write_guard import vector_census

    row = vector_census(chroma).get(collection, {})
    return row.get("lost", 1) == 0 and row.get("extra", 1) == 0


@pytest.fixture(autouse=True)
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = _refuse_production(tmp_path / "t3")
    home = root / "home"
    for path in (
        home,
        root / "xdg-config",
        root / "xdg-data",
        root / "xdg-cache",
        root / "convmem-root",
        root / "restic-cache",
        root / "config",
    ):
        path.mkdir(parents=True)
    (root / "config" / "config.toml").write_text("[index]\nchroma_dir = \"\"\n", encoding="utf-8")
    for key in _SCRUBBED_ENV:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(root / "xdg-config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(root / "xdg-data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(root / "xdg-cache"))
    monkeypatch.setenv("CONVMEM_ROOT", str(root / "convmem-root"))
    monkeypatch.setenv("CONVMEM_CONFIG", str(root / "config" / "config.toml"))
    monkeypatch.setenv("CONVMEM_RESTIC_ENV", str(root / "restic.env"))
    monkeypatch.setenv("RESTIC_CACHE_DIR", str(root / "restic-cache"))
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setenv("PYTHONNOUSERSITE", "1")
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


def test_pinned_backend_identity(chroma_dir: Path, evidence_path: Path) -> None:
    import chromadb
    import numpy as np

    from chroma_write_guard import vector_census

    assert chromadb.__version__ == "1.5.9"
    hnswlib = importlib.metadata.version("hnswlib")
    payload = {
        "python": sys.version.split()[0],
        "interpreter": PYTHON,
        "chromadb": chromadb.__version__,
        "numpy": np.__version__,
        "hnswlib": hnswlib,
        "uid": os.getuid(),
        "client_api": "PersistentClient",
    }
    import chromadb as cd

    client = cd.PersistentClient(path=str(chroma_dir))
    client.get_or_create_collection(COLLECTION)
    client.close()
    payload["vector_census_empty"] = vector_census(chroma_dir)
    evidence_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_operation_sequence_monotonic_queue_purge_and_restart(chroma_dir: Path, evidence_path: Path) -> None:
    out = chroma_dir / "sequence.json"
    done = _worker("sequence", str(chroma_dir), COLLECTION, str(out))
    assert done.returncode == 0, done.stderr[-2000:]
    trace = json.loads(out.read_text(encoding="utf-8"))["trace"]
    watermarks: list[tuple[int, int]] = []
    queue_lengths: list[int] = []
    for row in trace:
        snap = row["sqlite"]
        watermarks.append((snap["metadata_watermark"], snap["vector_watermark"]))
        queue_lengths.append(snap["queue_total"])
    for prev, cur in zip(watermarks, watermarks[1:], strict=False):
        assert cur[0] >= prev[0] and cur[1] >= prev[1], (prev, cur)
    assert max(queue_lengths) >= 2, queue_lengths
    assert min(queue_lengths) < max(queue_lengths), "expected queue purge after vector sync"
    restart = _worker("restart_ping", str(chroma_dir), COLLECTION)
    assert restart.returncode == 0, restart.stderr
    after = json.loads(restart.stdout)
    assert after["sqlite"]["vector_watermark"] == watermarks[-1][1]
    assert after["sqlite"]["metadata_watermark"] == watermarks[-1][0]
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    evidence["sequence"] = {"watermarks": watermarks, "queue_lengths": queue_lengths, "restart": after}
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def test_valid_releasable_control_after_restart(chroma_dir: Path, evidence_path: Path) -> None:
    import chromadb

    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection(
        COLLECTION,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 2, "batch_size": 1}},
    )
    expected = {"a": _embedding(1), "b": _embedding(2)}
    col.upsert(ids=["a"], embeddings=[expected["a"]], metadatas=[{"n": 1}])
    col.upsert(ids=["b"], embeddings=[expected["b"]], metadatas=[{"n": 2}])
    client.close()
    snap = capture_saved_vector_source(chroma_dir, COLLECTION, expected)
    restart = _worker("restart_ping", str(chroma_dir), COLLECTION)
    assert restart.returncode == 0, restart.stderr
    ok, reason = evaluate_strict_release_predicate(chroma_dir, snap)
    assert ok, reason
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    evidence["releasable_control"] = {"admit": ok, "reason": reason, "snapshot": asdict(snap)}
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def test_stale_vector_refusal_and_census_blind_spot(chroma_dir: Path, evidence_path: Path) -> None:
    import chromadb

    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection(
        COLLECTION,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 2, "batch_size": 1}},
    )
    col.upsert(ids=["a"], embeddings=[_embedding(1)], metadatas=[{"n": 1}])
    col.upsert(ids=["b"], embeddings=[_embedding(2)], metadatas=[{"n": 2}])
    vec_seg = _vector_segment_dir(chroma_dir)
    backup = chroma_dir / "vec-backup"
    shutil.copytree(vec_seg, backup)
    snap = capture_saved_vector_source(chroma_dir, COLLECTION, {"a": _embedding(1), "b": _embedding(2)})
    col.update(ids=["a"], embeddings=[_embedding(99)], metadatas=[{"n": 99}])
    col.upsert(ids=["b"], embeddings=[_embedding(2)], metadatas=[{"n": 2}])
    client.close()
    shutil.rmtree(vec_seg)
    shutil.copytree(backup, vec_seg)
    assert evaluate_census_only_predicate(chroma_dir, COLLECTION)
    ok, reason = evaluate_strict_release_predicate(chroma_dir, snap)
    assert not ok, reason
    read = _worker("read_embeddings", str(chroma_dir), COLLECTION, json.dumps(["a"]))
    assert read.returncode == 0, read.stderr
    stale = json.loads(read.stdout)["a"]["embedding"]
    assert stale is not None and abs(stale[0] - _embedding(1)[0]) < 1e-6
    assert abs(stale[0] - _embedding(99)[0]) > 1e-3
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    evidence["stale_control"] = {
        "census_only_admits": True,
        "strict_refuses": reason,
        "metadata_claims_n99": True,
        "vector_is_old": stale[:3],
    }
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")


def test_binding_and_missing_watermark_refusals(chroma_dir: Path, evidence_path: Path) -> None:
    import chromadb

    client = chromadb.PersistentClient(path=str(chroma_dir))
    col = client.get_or_create_collection(
        COLLECTION,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 2, "batch_size": 1}},
    )
    col.upsert(ids=["a"], embeddings=[_embedding(1)], metadatas=[{"n": 1}])
    col.upsert(ids=["b"], embeddings=[_embedding(2)], metadatas=[{"n": 2}])
    client.close()
    snap = capture_saved_vector_source(chroma_dir, COLLECTION, {"a": _embedding(1), "b": _embedding(2)})
    wrong_seg = SavedVectorSource(
        collection_name=snap.collection_name,
        collection_id=snap.collection_id,
        metadata_segment_id=snap.metadata_segment_id,
        vector_segment_id="00000000-0000-0000-0000-000000000000",
        vector_watermark=snap.vector_watermark,
        segment_signature=snap.segment_signature,
        segment_digests=snap.segment_digests,
        expected_embeddings=snap.expected_embeddings,
        chromadb_version=snap.chromadb_version,
    )
    ok_wrong, reason_wrong = evaluate_strict_release_predicate(chroma_dir, wrong_seg)
    assert not ok_wrong and reason_wrong == "segment_identity_mismatch"
    missing_wm = SavedVectorSource(
        collection_name=snap.collection_name,
        collection_id=snap.collection_id,
        metadata_segment_id=snap.metadata_segment_id,
        vector_segment_id=snap.vector_segment_id,
        vector_watermark=0,
        segment_signature=snap.segment_signature,
        segment_digests=snap.segment_digests,
        expected_embeddings=snap.expected_embeddings,
        chromadb_version=snap.chromadb_version,
    )
    ok_missing, reason_missing = evaluate_strict_release_predicate(chroma_dir, missing_wm)
    assert not ok_missing and reason_missing == "missing_vector_watermark"
    con = sqlite3.connect(f"file:{chroma_dir / 'chroma.sqlite3'}?mode=ro", uri=True)
    pending_vs_saved = con.execute(
        "select count(*) from embeddings_queue where topic like ? and seq_id > ?",
        (f"%/{snap.collection_id}", snap.vector_watermark),
    ).fetchone()[0]
    con.close()
    assert pending_vs_saved == 0
    vec_dir = chroma_dir / str(snap.vector_segment_id)
    header = vec_dir / "header.bin"
    raw = bytearray(header.read_bytes())
    raw[-1] ^= 0x01
    header.write_bytes(bytes(raw))
    ok_digest, reason_digest = evaluate_strict_release_predicate(chroma_dir, snap)
    assert not ok_digest and reason_digest in {"segment_signature_mismatch", "segment_digest_mismatch"}
    evidence = json.loads(evidence_path.read_text(encoding="utf-8")) if evidence_path.exists() else {}
    evidence["binding_controls"] = {
        "wrong_segment": reason_wrong,
        "missing_watermark": reason_missing,
        "empty_queue_digest_mismatch": reason_digest,
        "queue_pending_vs_saved_at_capture": pending_vs_saved,
    }
    evidence["verdict"] = "DEMONSTRATED"
    evidence_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
