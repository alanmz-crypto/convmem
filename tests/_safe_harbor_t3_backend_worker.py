"""Subprocess helper and stdlib proof launcher for Safe Harbor T3 backend proof.

Qualified entry (stdlib-isolated interpreter, allowlisted env before pytest):

    /home/lauer/miniforge3/bin/python -I -S -B tests/_safe_harbor_t3_backend_worker.py run-proof

Worker modes require SAFE_HARBOR_T3_BOOTSTRAPPED=1 and an isolated fixture root.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).resolve()
TEST_MODULE = ROOT / "tests" / "test_safe_harbor_t3_backend_proof.py"
PYTHON = "/home/lauer/miniforge3/bin/python"
# The stdlib bootstrap uses -I -S -B. Children start with the clean environment
# already installed and need the pinned interpreter's installed packages.
PYTHON_CHILD = [PYTHON, "-s", "-B"]
PROD_HOME = Path("/home/lauer")
REQUIRED_UID = 1000
PROOF_TIMEOUT_SECONDS = 300.0


ENV_PATH_KEYS = (
        "CONVMEM_CONFIG",
        "CONVMEM_ROOT",
        "CONVMEM_RESTIC_ENV",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "XDG_RUNTIME_DIR",
        "RESTIC_CACHE_DIR",
        "TMPDIR",
)


def _require_uid() -> None:
    if os.getuid() != REQUIRED_UID:
        raise RuntimeError(f"refusing uid {os.getuid()} (required {REQUIRED_UID})")


def _fixture_root() -> Path:
    raw = os.environ.get("SAFE_HARBOR_T3_FIXTURE_ROOT", "")
    if not raw:
        raise RuntimeError("SAFE_HARBOR_T3_FIXTURE_ROOT unset")
    return Path(raw).resolve(strict=False)


def _constrain_under_fixture(path: Path) -> Path:
    root = _fixture_root()
    resolved = path.expanduser().resolve(strict=False)
    if resolved.is_symlink():
        raise RuntimeError(f"refusing symlink path {resolved}")
    if resolved != root and root not in resolved.parents:
        raise RuntimeError(f"refusing path outside fixture root {resolved} (root={root})")
    banned = [
        PROD_HOME / ".local/share/convmem",
        PROD_HOME / ".config/convmem",
        PROD_HOME / "Projects/convmem/.worktrees/runtime-main",
    ]
    for banned_path in banned:
        if resolved == banned_path or banned_path in resolved.parents:
            raise RuntimeError(f"refusing production-overlapping path {resolved}")
    return resolved


def _require_isolated() -> None:
    _require_uid()
    home = Path.home().resolve()
    if home == PROD_HOME:
        raise RuntimeError(f"refusing production HOME {home}")
    _constrain_under_fixture(home)
    for key in ENV_PATH_KEYS:
        raw = os.environ.get(key, "")
        if not raw or not Path(raw).is_absolute():
            raise RuntimeError(f"refusing unset/relative {key}={raw!r}")
        _constrain_under_fixture(Path(raw))
    for secret in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if secret in os.environ:
            raise RuntimeError(f"refusing inherited {secret}")


def build_allowlisted_env(fixture_root: Path, evidence_root: Path) -> dict[str, str]:
    """Stdlib-only clean environment for proof subprocesses."""
    fixture_root = fixture_root.resolve()
    evidence_root = evidence_root.resolve()
    home = fixture_root / "home"
    home.mkdir(parents=True, exist_ok=True)
    for sub in ("xdg-config", "xdg-data", "xdg-cache", "xdg-runtime", "convmem-root", "restic-cache", "config", "tmp"):
        (fixture_root / sub).mkdir(parents=True, exist_ok=True)
    config = fixture_root / "config" / "config.toml"
    if not config.is_file():
        config.write_text('[index]\nchroma_dir = ""\n', encoding="utf-8")
    return {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "PYTHONPATH": str(ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONHASHSEED": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "XDG_CONFIG_HOME": str(fixture_root / "xdg-config"),
        "XDG_DATA_HOME": str(fixture_root / "xdg-data"),
        "XDG_CACHE_HOME": str(fixture_root / "xdg-cache"),
        "XDG_RUNTIME_DIR": str(fixture_root / "xdg-runtime"),
        "CONVMEM_ROOT": str(fixture_root / "convmem-root"),
        "CONVMEM_CONFIG": str(config),
        "CONVMEM_RESTIC_ENV": str(fixture_root / "restic.env"),
        "RESTIC_CACHE_DIR": str(fixture_root / "restic-cache"),
        "TMPDIR": str(fixture_root / "tmp"),
        "SAFE_HARBOR_T3_BOOTSTRAPPED": "1",
        "SAFE_HARBOR_T3_FIXTURE_ROOT": str(fixture_root),
        "SAFE_HARBOR_T3_EVIDENCE_ROOT": str(evidence_root),
        "CHROMA_TELEMETRY": "FALSE",
        "ANONYMIZED_TELEMETRY": "FALSE",
        "OTEL_SDK_DISABLED": "true",
    }


def seq_id(value: Any) -> int:
    if value is None:
        raise ValueError("refusing None seq_id")
    if isinstance(value, bytes):
        if not value:
            raise ValueError("empty seq_id bytes")
        return int.from_bytes(value, "big")
    if isinstance(value, int):
        return int(value)
    raise TypeError(f"unsupported seq_id type {type(value)!r}")


def embedding_from_seed(seed: int) -> list[float]:
    digest = hashlib.sha256(f"safe-harbor-t3:{seed}".encode()).digest()
    return [((digest[i] % 200) - 100) / 100.0 for i in range(16)]


def cosine_vectors_equal(left: list[float], right: list[float], tol: float = 1e-5) -> bool:
    if len(left) != len(right):
        return False

    def _normalize(values: list[float]) -> list[float]:
        norm = sum(v * v for v in values) ** 0.5
        if norm <= 0:
            return values
        return [v / norm for v in values]

    normed_left = _normalize(left)
    normed_right = _normalize(right)
    return all(abs(a - b) <= tol for a, b in zip(normed_left, normed_right, strict=True))


def read_persisted_embedding_vector(seg_dir: Path, embedding_id: str) -> list[float]:
    """Read raw float32 vector bytes from data_level0.bin (no length.bin norm scaling)."""
    sys.path.insert(0, str(ROOT))
    import numpy as np
    from chroma_write_guard import _read_header, load_segment_id_map

    id_map = load_segment_id_map(seg_dir)
    if not id_map:
        raise KeyError(f"index_metadata.pickle missing under {seg_dir}")
    id_to_label = id_map.get("id_to_label")
    if not isinstance(id_to_label, dict) or embedding_id not in id_to_label:
        raise KeyError(f"embedding id {embedding_id!r} absent from id_to_label")
    target_label = int(id_to_label[embedding_id])
    header = _read_header(seg_dir / "header.bin")
    count = header["count"]
    if count == 0:
        raise KeyError(f"segment {seg_dir.name} has no synced elements")
    width = header["bytes_per_element"] // 4
    first_vec = header["offset_data"] // 4
    label_col = header["label_offset"] // 4
    rows = np.memmap(seg_dir / "data_level0.bin", dtype="<u4", mode="r", shape=(count, width))
    for row_idx in range(count):
        head = int(rows[row_idx, 0])
        if (head & 0x10000) != 0:
            continue
        label = int(rows[row_idx, label_col]) | (int(rows[row_idx, label_col + 1]) << 32)
        if label != target_label:
            continue
        raw = np.ascontiguousarray(rows[row_idx, first_vec:label_col]).view("<f4")
        return [float(x) for x in raw]
    raise KeyError(f"embedding id {embedding_id!r} not present in segment bytes")


def segment_vector_synced(seg_dir: Path, embedding_id: str) -> bool:
    sys.path.insert(0, str(ROOT))
    from chroma_write_guard import _read_header, load_segment_id_map

    try:
        header = _read_header(seg_dir / "header.bin")
    except (OSError, ValueError):
        return False
    if header["count"] == 0:
        return False
    id_map = load_segment_id_map(seg_dir)
    if not id_map:
        return False
    id_to_label = id_map.get("id_to_label")
    return isinstance(id_to_label, dict) and embedding_id in id_to_label


def sqlite_schema_digest(chroma: Path) -> str:
    con = sqlite3.connect(f"file:{chroma / 'chroma.sqlite3'}?mode=ro", uri=True)
    try:
        con.execute("BEGIN")
        rows = con.execute(
            "select type, name, sql from sqlite_master where name not like 'sqlite_%' order by type, name"
        ).fetchall()
    finally:
        con.execute("ROLLBACK")
        con.close()
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def live_backend_identity_client_free(chroma: Path) -> dict[str, Any]:
    """No PersistentClient(path=...) — module class, Settings API impl, sqlite digests."""
    import importlib.metadata

    import chromadb
    from chromadb.api.client import Client
    from chromadb.config import Settings

    from chromadb_rust_bindings import chromadb_rust_bindings as native_binding

    rust_path = Path(native_binding.__file__).resolve()
    if not rust_path.is_file():
        raise FileNotFoundError(f"missing rust binding at {rust_path}")
    rust_sha = hashlib.sha256(rust_path.read_bytes()).hexdigest()
    settings = Settings()
    chroma_api_impl = getattr(settings, "chroma_api_impl", None)
    con = sqlite3.connect(f"file:{chroma / 'chroma.sqlite3'}?mode=ro", uri=True)
    try:
        con.execute("BEGIN")
        migrations = tuple(row[0] for row in con.execute("select version from migrations order by version"))
    finally:
        con.execute("ROLLBACK")
        con.close()
    return {
        "chromadb_version": chromadb.__version__,
        "client_api": f"{Client.__module__}.{Client.__qualname__}",
        "chroma_api_impl": str(chroma_api_impl),
        "rust_binding_module": native_binding.__name__,
        "rust_binding_path": str(rust_path),
        "rust_binding_sha256": rust_sha,
        "sqlite_migrations": migrations,
        "sqlite_schema_digest": sqlite_schema_digest(chroma),
        "hnswlib": importlib.metadata.version("hnswlib"),
    }


def run_proof_launcher() -> int:
    """Run pytest + focused pylint under isolation; record subprocess evidence."""
    _require_uid()
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise RuntimeError("bootstrap requires python -I -S -B before run-proof")
    evidence_root = Path(tempfile.mkdtemp(prefix="safe-harbor-t3-", dir="/tmp"))
    fixture_root = evidence_root / "fixture"
    fixture_root.mkdir(parents=True)
    env = build_allowlisted_env(fixture_root, evidence_root)
    harness_before = {
        "test": hashlib.sha256(TEST_MODULE.read_bytes()).hexdigest(),
        "worker": hashlib.sha256(WORKER.read_bytes()).hexdigest(),
        "guard": hashlib.sha256((ROOT / "chroma_write_guard.py").read_bytes()).hexdigest(),
    }
    (evidence_root / "environment.json").write_text(json.dumps(env, indent=2, sort_keys=True), encoding="utf-8")
    pytest_cmd = [
        *PYTHON_CHILD,
        "-m",
        "pytest",
        str(TEST_MODULE),
        "-v",
        "--tb=line",
        "-p",
        "no:cacheprovider",
        f"--basetemp={fixture_root / 'pytest-tmp'}",
    ]
    summary: dict[str, Any] = {
        "pytest_command": pytest_cmd,
        "uid": os.getuid(),
        "interpreter": PYTHON,
        "bootstrap_flags": ["-I", "-S", "-B"],
        "child_flags": ["-s", "-B"],
        "harness_sha256_before": harness_before,
        "fixture_root": str(fixture_root),
        "evidence_root": str(evidence_root),
        "timeout_seconds": PROOF_TIMEOUT_SECONDS,
    }
    try:
        started = time.monotonic()
        pytest = subprocess.run(
            pytest_cmd,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=PROOF_TIMEOUT_SECONDS,
            check=False,
        )
        summary["pytest_returncode"] = pytest.returncode
        summary["pytest_elapsed_seconds"] = time.monotonic() - started
        (evidence_root / "pytest.log").write_text(pytest.stdout + pytest.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired as exc:
        summary["pytest_timed_out"] = True
        summary["pytest_returncode"] = None
        (evidence_root / "pytest.log").write_text(
            (exc.stdout or b"").decode(errors="replace") + (exc.stderr or b"").decode(errors="replace"),
            encoding="utf-8",
        )
        summary["harness_sha256_after"] = {
            "test": hashlib.sha256(TEST_MODULE.read_bytes()).hexdigest(),
            "worker": hashlib.sha256(WORKER.read_bytes()).hexdigest(),
            "guard": hashlib.sha256((ROOT / "chroma_write_guard.py").read_bytes()).hexdigest(),
        }
        (evidence_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 124

    lint_cmd = [*PYTHON_CHILD, "-m", "pylint", "-sn", str(TEST_MODULE), str(WORKER)]
    lint_started = time.monotonic()
    try:
        lint = subprocess.run(
            lint_cmd,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=PROOF_TIMEOUT_SECONDS,
            check=False,
        )
        summary["pylint_returncode"] = lint.returncode
        summary["pylint_elapsed_seconds"] = time.monotonic() - lint_started
        (evidence_root / "pylint.log").write_text(lint.stdout + lint.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired:
        summary["pylint_timed_out"] = True
        summary["pylint_returncode"] = None
        (evidence_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 124

    harness_after = {
        "test": hashlib.sha256(TEST_MODULE.read_bytes()).hexdigest(),
        "worker": hashlib.sha256(WORKER.read_bytes()).hexdigest(),
        "guard": hashlib.sha256((ROOT / "chroma_write_guard.py").read_bytes()).hexdigest(),
    }
    summary["harness_sha256_after"] = harness_after
    summary["pylint_command"] = lint_cmd
    if harness_after != harness_before:
        summary["harness_hash_mismatch"] = True
        (evidence_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 3

    (evidence_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if summary.get("pytest_returncode", 1) != 0:
        return int(summary["pytest_returncode"])
    return int(summary.get("pylint_returncode") or 0)


def _collection_segments(con: sqlite3.Connection, collection: str) -> tuple[str, str, str]:
    row = con.execute("select id, name from collections where name = ?", (collection,)).fetchone()
    if not row:
        raise KeyError(f"collection {collection!r} missing")
    collection_id, _ = row
    scopes = dict(con.execute("select scope, id from segments where collection = ?", (collection_id,)).fetchall())
    meta_seg = scopes.get("METADATA")
    vec_seg = scopes.get("VECTOR")
    if not meta_seg or not vec_seg:
        raise KeyError(f"collection {collection!r} missing METADATA/VECTOR segments")
    return collection_id, meta_seg, vec_seg


def _sqlite_metadata_int(con: sqlite3.Connection, meta_seg: str, embedding_id: str, key: str) -> int | None:
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


def _embedding_row_exists(con: sqlite3.Connection, meta_seg: str, embedding_id: str) -> bool:
    row = con.execute(
        "select 1 from embeddings where segment_id = ? and embedding_id = ? limit 1",
        (meta_seg, embedding_id),
    ).fetchone()
    return row is not None


def _queue_rows(con: sqlite3.Connection, collection_id: str) -> list[dict[str, Any]]:
    rows = con.execute(
        "select seq_id, topic from embeddings_queue where topic like ? order by seq_id",
        (f"%/{collection_id}",),
    ).fetchall()
    return [{"seq_id": seq_id(seq), "topic": topic} for seq, topic in rows]


def sqlite_snapshot(chroma: Path, collection: str) -> dict[str, Any]:
    db = chroma / "chroma.sqlite3"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        con.execute("BEGIN")
        collection_id, meta_seg, vec_seg = _collection_segments(con, collection)
        applied: dict[str, int] = {}
        for sid, raw in con.execute("select segment_id, seq_id from max_seq_id"):
            applied[sid] = seq_id(raw)
        meta_wm = applied.get(meta_seg)
        vec_wm = applied.get(vec_seg) if vec_seg in applied else None
        floor = min(meta_wm, vec_wm) if meta_wm is not None and vec_wm is not None else None
        queue_len = con.execute("select count(*) from embeddings_queue").fetchone()[0]
        pending = None if floor is None else con.execute(
            "select count(*) from embeddings_queue where topic like ? and seq_id > ?",
            (f"%/{collection_id}", floor),
        ).fetchone()[0]
        return {
            "collection_id": collection_id,
            "metadata_segment_id": meta_seg,
            "vector_segment_id": vec_seg,
            "metadata_watermark": meta_wm,
            "vector_watermark": vec_wm,
            "queue_total": queue_len,
            "queue_pending_after_floor": pending,
            "queue_rows": _queue_rows(con, collection_id),
        }
    finally:
        con.execute("ROLLBACK")
        con.close()


def _json_embedding(emb: Any) -> list[float]:
    if emb is None:
        raise ValueError("missing embedding from fixture client")
    if hasattr(emb, "tolist"):
        return [float(x) for x in emb.tolist()]
    return [float(x) for x in emb]


def _assert_fixture_client_state(col: Any, label: str, expectation: dict[str, Any]) -> None:
    if expectation.get("absent"):
        got = col.get(ids=[expectation["id"]], include=["embeddings", "metadatas", "documents"])
        assert got["ids"] == [], (label, got["ids"])
        return
    embedding_id = expectation["id"]
    got = col.get(ids=[embedding_id], include=["embeddings", "metadatas", "documents"])
    assert got["ids"] == [embedding_id], (label, got["ids"])
    if "metadata_n" in expectation:
        assert got["metadatas"][0]["n"] == expectation["metadata_n"], (label, got["metadatas"])
    if "document" in expectation:
        assert got["documents"][0] == expectation["document"], (label, got["documents"])
    if "embedding_seed" in expectation:
        client_emb = _json_embedding(got["embeddings"][0])
        expected = embedding_from_seed(expectation["embedding_seed"])
        assert cosine_vectors_equal(client_emb, expected), (label, embedding_id, "client embedding mismatch")


def _assert_step_outcome(
    chroma: Path,
    collection: str,
    col: Any,
    label: str,
    expectation: dict[str, Any],
) -> None:
    _assert_fixture_client_state(col, label, expectation)
    db = chroma / "chroma.sqlite3"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        _, meta_seg, vec_seg = _collection_segments(con, collection)
        if expectation.get("absent"):
            assert not _embedding_row_exists(con, meta_seg, expectation["id"]), label
            return
        embedding_id = expectation["id"]
        assert _embedding_row_exists(con, meta_seg, embedding_id), label
        if "metadata_n" in expectation:
            observed_n = _sqlite_metadata_int(con, meta_seg, embedding_id, "n")
            assert observed_n == expectation["metadata_n"], (label, observed_n, expectation["metadata_n"])
        seg_dir = chroma / vec_seg
        positions = sqlite_snapshot(chroma, collection)
        synced_current = positions["vector_watermark"] == positions["metadata_watermark"]
        if "embedding_seed" in expectation and synced_current and segment_vector_synced(seg_dir, embedding_id):
            persisted = read_persisted_embedding_vector(seg_dir, embedding_id)
            expected = embedding_from_seed(expectation["embedding_seed"])
            assert cosine_vectors_equal(persisted, expected), (label, embedding_id, "persisted vector mismatch")
    finally:
        con.close()


def _run_sequence(chroma: Path, collection: str) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    import chromadb  # pylint: disable=import-outside-toplevel

    client = chromadb.PersistentClient(path=str(chroma))
    col = client.get_or_create_collection(
        collection,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 3, "batch_size": 1}},
    )
    trace: list[dict[str, Any]] = []
    prev_meta_wm: int | None = None

    def step(label: str, fn, expectation: dict[str, Any]) -> None:
        nonlocal prev_meta_wm
        before = sqlite_snapshot(chroma, collection)
        fn()
        after = sqlite_snapshot(chroma, collection)
        meta_wm = after["metadata_watermark"]
        if meta_wm is None:
            raise AssertionError((label, "metadata watermark missing"))
        if prev_meta_wm is not None:
            assert meta_wm > prev_meta_wm, (label, prev_meta_wm, meta_wm)
        _assert_step_outcome(chroma, collection, col, label, expectation)
        trace.append(
            {
                "step": label,
                "sqlite_before": before,
                "sqlite_after": after,
                "expectation": expectation,
            }
        )
        prev_meta_wm = meta_wm

    step(
        "add_a",
        lambda: col.upsert(
            ids=["a"],
            documents=["doc-a"],
            embeddings=[embedding_from_seed(1)],
            metadatas=[{"n": 1}],
        ),
        {"id": "a", "metadata_n": 1, "document": "doc-a", "embedding_seed": 1},
    )
    step(
        "update_metadata_a",
        lambda: col.update(ids=["a"], metadatas=[{"n": 2}]),
        {"id": "a", "metadata_n": 2, "document": "doc-a", "embedding_seed": 1},
    )
    step(
        "update_embedding_a",
        lambda: col.update(ids=["a"], embeddings=[embedding_from_seed(99)]),
        {"id": "a", "metadata_n": 2, "document": "doc-a", "embedding_seed": 99},
    )
    step(
        "upsert_a",
        lambda: col.upsert(
            ids=["a"],
            documents=["doc-a2"],
            embeddings=[embedding_from_seed(100)],
            metadatas=[{"n": 3}],
        ),
        {"id": "a", "metadata_n": 3, "document": "doc-a2", "embedding_seed": 100},
    )
    step("delete_a", lambda: col.delete(ids=["a"]), {"id": "a", "absent": True})
    step(
        "reinsert_a",
        lambda: col.upsert(
            ids=["a"],
            documents=["doc-a3"],
            embeddings=[embedding_from_seed(200)],
            metadatas=[{"n": 4}],
        ),
        {"id": "a", "metadata_n": 4, "document": "doc-a3", "embedding_seed": 200},
    )
    client.close()
    return {"trace": trace}


def _restart_ping(chroma: Path, collection: str) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    import chromadb  # pylint: disable=import-outside-toplevel

    client = chromadb.PersistentClient(path=str(chroma))
    col = client.get_collection(collection)
    count = col.count()
    got = col.get(ids=["a"], include=["embeddings", "metadatas", "documents"])
    client.close()
    snap = sqlite_snapshot(chroma, collection)
    seg_dir = chroma / snap["vector_segment_id"]
    client_emb = _json_embedding(got["embeddings"][0])
    payload: dict[str, Any] = {
        "count": count,
        "sqlite": snap,
        "document": got["documents"][0],
        "metadata_n": got["metadatas"][0]["n"],
        "client_embedding_matches_seed_200": cosine_vectors_equal(client_emb, embedding_from_seed(200)),
    }
    if segment_vector_synced(seg_dir, "a"):
        persisted = read_persisted_embedding_vector(seg_dir, "a")
        payload["persisted_vector_a"] = persisted
        payload["persisted_vector_matches_seed_200"] = cosine_vectors_equal(persisted, embedding_from_seed(200))
    else:
        payload["persisted_vector_a"] = None
        payload["persisted_vector_matches_seed_200"] = False
    return payload


def client_free_observe(chroma: Path, collection: str) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from chroma_write_guard import SEGMENT_FILES

    snap = sqlite_snapshot(chroma, collection)
    vec_dir = chroma / snap["vector_segment_id"]
    digests: dict[str, str] = {}
    for name in SEGMENT_FILES:
        path = vec_dir / name
        if path.is_file():
            digests[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"sqlite": snap, "segment_digests": digests, "backend": live_backend_identity_client_free(chroma)}


def _probe_backend(chroma: Path, collection: str) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    import chromadb  # pylint: disable=import-outside-toplevel

    client = chromadb.PersistentClient(path=str(chroma))
    client.get_or_create_collection(
        collection,
        configuration={"hnsw": {"space": "cosine", "sync_threshold": 2, "batch_size": 1}},
    )
    client_api = f"{type(client).__module__}.{type(client).__qualname__}"
    server = getattr(client, "_server", None)
    server_api = f"{type(server).__module__}.{type(server).__qualname__}" if server is not None else None
    from chromadb_rust_bindings import chromadb_rust_bindings as native_binding

    assert isinstance(server.bindings, native_binding.Bindings), "active server is not using the recorded native module"
    client.close()
    payload = live_backend_identity_client_free(chroma)
    payload["client_api_observed"] = client_api
    payload["server_api_observed"] = server_api
    return payload


def main() -> None:
    _require_isolated()
    mode = sys.argv[1]
    if mode == "sequence":
        chroma = _constrain_under_fixture(Path(sys.argv[2]))
        collection = sys.argv[3]
        out = _constrain_under_fixture(Path(sys.argv[4]))
        payload = _run_sequence(chroma, collection)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print("ok", flush=True)
        return
    if mode == "observe":
        chroma = _constrain_under_fixture(Path(sys.argv[2]))
        collection = sys.argv[3]
        out = _constrain_under_fixture(Path(sys.argv[4]))
        out.write_text(json.dumps(sqlite_snapshot(chroma, collection), indent=2), encoding="utf-8")
        print("ok", flush=True)
        return
    if mode == "client_free_observe":
        chroma = _constrain_under_fixture(Path(sys.argv[2]))
        collection = sys.argv[3]
        print(json.dumps(client_free_observe(chroma, collection)), flush=True)
        return
    if mode == "restart_ping":
        chroma = _constrain_under_fixture(Path(sys.argv[2]))
        collection = sys.argv[3]
        print(json.dumps(_restart_ping(chroma, collection)), flush=True)
        return
    if mode == "probe_backend":
        chroma = _constrain_under_fixture(Path(sys.argv[2]))
        collection = sys.argv[3]
        out = _constrain_under_fixture(Path(sys.argv[4]))
        out.write_text(json.dumps(_probe_backend(chroma, collection), indent=2), encoding="utf-8")
        print("ok", flush=True)
        return
    raise SystemExit(f"unknown mode {mode!r}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "run-proof":
        raise SystemExit(run_proof_launcher())
    main()
