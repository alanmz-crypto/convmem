# pylint: disable=protected-access,consider-using-with
"""Isolated Safe Harbor T1 evidence: incident authority at the existing guard.

Each test creates its own home, config, and data directories before it imports
or runs project code that could touch a user directory. Production corpus and
runtime-main paths are still refused. Standard pytest does not need an
external isolation flag.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from chroma_write_guard import (
    INCIDENT_SCHEMA,
    INCIDENT_VERSION,
    ChromaContainmentUnavailableError,
    ChromaWriteGuard,
    ChromaWriteGuardError,
    ChromaWriteQuarantinedError,
    _exclusive_flock,
    _finding_spec,
    canonical_target,
)

ROOT = Path(__file__).resolve().parents[1]
PROD_DATA = Path("/home/lauer/.local/share/convmem")
RUNTIME_MAIN = Path("/home/lauer/Projects/convmem/.worktrees/runtime-main")
PROD_HOME = Path("/home/lauer")


def _refuse_production(path: Path) -> Path:
    resolved = path.resolve()
    for banned in (PROD_DATA, RUNTIME_MAIN):
        if resolved == banned or banned in resolved.parents:
            raise RuntimeError(f"refusing production path {resolved}")
    return resolved


def _banned(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    for banned in (PROD_DATA, RUNTIME_MAIN, PROD_HOME):
        if resolved == banned or banned in resolved.parents:
            return True
    return False


def _require_isolated_process() -> None:
    """Refuse a process whose home, config, or data roots can reach production."""
    home = Path.home().resolve()
    if (
        home == PROD_HOME
        or home == PROD_DATA
        or PROD_DATA in home.parents
        or RUNTIME_MAIN in home.parents
    ):
        raise RuntimeError(f"refusing production HOME {home}")
    required = {
        "CONVMEM_CONFIG": os.environ.get("CONVMEM_CONFIG", ""),
        "XDG_CONFIG_HOME": os.environ.get("XDG_CONFIG_HOME", ""),
        "XDG_DATA_HOME": os.environ.get("XDG_DATA_HOME", ""),
        "XDG_CACHE_HOME": os.environ.get("XDG_CACHE_HOME", ""),
        "CONVMEM_ROOT": os.environ.get("CONVMEM_ROOT", ""),
    }
    for key, raw in required.items():
        path = Path(raw).expanduser()
        if not raw or not path.is_absolute() or _banned(path):
            raise RuntimeError(f"refusing {key} {raw}")


@pytest.fixture(autouse=True)
def _isolate_t1_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point this test and its children at a fresh directory before project imports."""
    root = tmp_path / "process-isolation"
    home = root / "home"
    config_dir = root / "config"
    data = root / "data"
    cache = root / "cache"
    for path in (home, config_dir, data, cache, root / "root"):
        path.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_dir))
    monkeypatch.setenv("XDG_DATA_HOME", str(data))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    monkeypatch.setenv("CONVMEM_CONFIG", str(config_file))
    monkeypatch.setenv("CONVMEM_ROOT", str(root / "root"))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CONVMEM_T1_ISOLATED", raising=False)
    _require_isolated_process()


def _run(tmp: Path, code: str, *args: str, env_extra: dict[str, str] | None = None, timeout: float = 180):
    _refuse_production(tmp)
    _require_isolated_process()
    env = os.environ.copy()
    env.pop("CONVMEM_T1_ISOLATED", None)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _findings(document: dict) -> list[dict]:
    return [finding for incident in document["incidents"] for finding in incident["findings"]]


def assert_findings_retained(document: dict, finding_ids: set[str]) -> None:
    """Independent retention check. An overwrite that drops an id must fail here."""
    present = {finding["id"] for finding in _findings(document)}
    missing = finding_ids - present
    assert not missing, f"missing findings {sorted(missing)}"


def _marker(guard: ChromaWriteGuard) -> dict:
    return json.loads(guard.quarantine_path.read_text(encoding="utf-8"))


def _publish(guard: ChromaWriteGuard, *specs: dict) -> None:
    with _exclusive_flock(guard.lock_path, 5):
        guard._publish_findings(list(specs))


ADMIT = """
import sys
from chroma_write_guard import ChromaWriteGuard
ChromaWriteGuard(sys.argv[1]).require_not_quarantined()
print("admitted")
"""

AUDIT = """
import json, sys
from chroma_write_guard import ChromaWriteGuard
print(json.dumps(ChromaWriteGuard(sys.argv[1]).audit()))
"""

RECOVER = """
import sys
from chroma_write_guard import recover
recover(sys.argv[1])
print("admitted")
"""

WRITE = """
import sys
from chroma_store import ChromaStore
from chroma_write_guard import ChromaWriteGuard
from tests._chroma_write_guard_worker import embedding
store = ChromaStore(sys.argv[1], write_guard=ChromaWriteGuard(sys.argv[1]))
try:
    store.add_summary(sys.argv[2], "doc", embedding(sys.argv[2]), {"source_path": "/fixture"})
    print("admitted")
finally:
    store.close()
"""


def test_process_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _require_isolated_process()
    _refuse_production(tmp_path)
    isolated_home = os.environ["HOME"]
    isolated_config = os.environ["CONVMEM_CONFIG"]
    assert Path(isolated_home).resolve() != PROD_HOME
    assert os.environ.get("CONVMEM_T1_ISOLATED") is None
    with pytest.raises(RuntimeError, match="refusing production path"):
        _refuse_production(PROD_DATA)
    with pytest.raises(RuntimeError, match="refusing production path"):
        _refuse_production(RUNTIME_MAIN / "chroma")
    monkeypatch.setenv("HOME", str(PROD_HOME))
    with pytest.raises(RuntimeError, match="refusing production HOME"):
        _require_isolated_process()
    monkeypatch.setenv("HOME", isolated_home)
    monkeypatch.setenv("CONVMEM_CONFIG", str(PROD_DATA / "config.toml"))
    with pytest.raises(RuntimeError, match="refusing CONVMEM_CONFIG"):
        _require_isolated_process()
    monkeypatch.setenv("CONVMEM_CONFIG", isolated_config)
    _require_isolated_process()


def test_only_a_missing_marker_is_absent(tmp_path: Path) -> None:
    _require_isolated_process()
    chroma = _refuse_production(tmp_path / "chroma")
    chroma.mkdir()
    guard = ChromaWriteGuard(chroma)
    assert guard.read_authority().state == "absent"
    guard.require_not_quarantined()
    assert guard.clear_quarantine() is False
    guard.root.mkdir()

    cases = {
        "null": b"null\n",
        "number": b"1\n",
        "string": b'"x"\n',
        "empty-object": b"{}\n",
        "unknown-schema": b'{"schema":"other"}\n',
        "invalid-json": b"{not-json",
        "invalid-set": json.dumps(
            {"schema": INCIDENT_SCHEMA, "version": INCIDENT_VERSION, "target": str(guard.chroma_dir), "incidents": {}}
        ).encode(),
        "unknown-version": json.dumps(
            {
                "schema": INCIDENT_SCHEMA,
                "version": 99,
                "target": str(guard.chroma_dir),
                "incidents": [],
            }
        ).encode(),
    }
    for name, payload in cases.items():
        guard.quarantine_path.write_bytes(payload)
        view = guard.read_authority()
        assert view.state == "blocked" and view.blocking, name
        with pytest.raises(ChromaWriteQuarantinedError):
            guard.require_not_quarantined()
        with pytest.raises(ChromaWriteGuardError, match="ordinary clear refuses"):
            guard.clear_quarantine()
        assert guard.quarantine_path.read_bytes() == payload, name

    wrong = _empty_document(guard)
    wrong["target"] = "/wrong/target"
    payload = (json.dumps(wrong) + "\n").encode()
    guard.quarantine_path.write_bytes(payload)
    view = guard.read_authority()
    assert view.blocking and "does not match" in view.summary
    with pytest.raises(ChromaWriteGuardError, match="refusing to replace"):
        _publish(guard, _finding_spec("seg", "structural", "new", ("x",)))
    assert guard.quarantine_path.read_bytes() == payload


def test_read_error_blocks_and_is_not_absence(tmp_path: Path) -> None:
    _require_isolated_process()
    assert os.geteuid() != 0, "chmod read-failure is not meaningful as root"
    chroma = _refuse_production(tmp_path / "chroma")
    chroma.mkdir()
    guard = ChromaWriteGuard(chroma)
    guard.root.mkdir()
    guard.quarantine_path.write_bytes(b'{"reason":"legacy","segment":"seg"}\n')
    guard.quarantine_path.chmod(0)
    try:
        view = guard.read_authority()
        assert view.state == "blocked" and view.state != "absent"
        assert "unreadable" in view.summary
        with pytest.raises(ChromaWriteQuarantinedError):
            guard.require_not_quarantined()
    finally:
        guard.quarantine_path.chmod(0o600)


def test_legacy_adoption_preserves_original_bytes(tmp_path: Path) -> None:
    _require_isolated_process()
    chroma = _refuse_production(tmp_path / "chroma")
    chroma.mkdir()
    guard = ChromaWriteGuard(chroma)
    original = b'{"failures":["torn header"],"reason":"legacy tear","segment":"seg-a"}\n'
    guard.root.mkdir()
    guard.quarantine_path.write_bytes(original)
    assert guard.read_authority().legacy is True
    assert guard.quarantine_path.read_bytes() == original
    _publish(guard, _finding_spec("seg-b", "structural", "second finding", ("bad count",)))
    assert guard.legacy_bytes_path.read_bytes() == original
    document = _marker(guard)
    reasons = {finding["reason"] for finding in _findings(document)}
    assert reasons == {"legacy tear", "second finding"}
    assert document["legacy_original_sha256"]
    assert_findings_retained(document, {finding["id"] for finding in _findings(document)})


def test_reobservation_is_stable_and_a_change_bumps_revision(tmp_path: Path) -> None:
    _require_isolated_process()
    chroma = _refuse_production(tmp_path / "chroma")
    chroma.mkdir()
    guard = ChromaWriteGuard(chroma)
    spec = _finding_spec("seg", "structural", "same failure", ("header",))
    _publish(guard, spec)
    first = _marker(guard)
    finding = _findings(first)[0]
    assert finding["revision"] == 1
    before = guard.quarantine_path.read_bytes()
    _publish(guard, spec)
    assert guard.quarantine_path.read_bytes() == before
    changed = _finding_spec("seg", "structural", "same failure", ("header", "links"))
    _publish(guard, changed)
    second = _findings(_marker(guard))[0]
    assert second["revision"] == 2
    assert second["digest"] != finding["digest"]
    assert len(_marker(guard)["incidents"]) == 1
    assert len(_findings(_marker(guard))) == 1


def test_persisted_empty_incident_set_refuses_fresh_admission(tmp_path: Path) -> None:
    """A schema-valid empty set is present state. Missing remains the admit control."""
    _require_isolated_process()
    from doctor import _check_chroma_write_guard

    chroma = _make_store(tmp_path)
    guard = ChromaWriteGuard(chroma)
    assert guard.read_authority().state == "absent"
    guard.require_not_quarantined()
    payload = (json.dumps(_empty_document(guard), indent=2, sort_keys=True) + "\n").encode()
    guard.root.mkdir(parents=True, exist_ok=True)
    guard.quarantine_path.write_bytes(payload)
    view = guard.read_authority()
    assert view.state == "unresolved" and view.blocking
    assert "persisted empty incident set" in view.summary
    admission = _run(tmp_path, ADMIT, str(chroma))
    assert admission.returncode != 0, admission.stderr
    assert "admitted" not in admission.stdout
    assert "quarantine" in admission.stderr.lower()
    writer = _run(tmp_path, WRITE, str(chroma), "empty-set-write")
    assert writer.returncode != 0, writer.stderr
    assert "admitted" not in writer.stdout
    assert not _embedding_id_present(chroma, "empty-set-write")
    assert guard.quarantine_path.read_bytes() == payload
    cfg = {"index": {"chroma_dir": str(chroma)}}
    assert _check_chroma_write_guard(cfg).effective_status() == "fail"
    assert guard.quarantine_path.read_bytes() == payload
    _publish(guard, _finding_spec("seg", "structural", "merged onto empty", ("kept",)))
    retained = _marker(guard)
    assert_findings_retained(retained, {finding["id"] for finding in _findings(retained)})
    still_refused = _run(tmp_path, ADMIT, str(chroma))
    assert still_refused.returncode != 0
    assert "admitted" not in still_refused.stdout


def test_canonical_alias_shares_one_guard_and_competing_legacy_refuses(tmp_path: Path) -> None:
    _require_isolated_process()
    real = _refuse_production(tmp_path / "chroma")
    real.mkdir()
    link = tmp_path / "link-chroma"
    link.symlink_to(real, target_is_directory=True)
    via_link = ChromaWriteGuard(link)
    via_real = ChromaWriteGuard(real)
    assert via_link.chroma_dir == via_real.chroma_dir == canonical_target(real)
    assert via_link.root == via_real.root
    assert via_link.lock_path == via_real.lock_path
    _publish(via_link, _finding_spec("seg", "structural", "from alias", ("x",)))
    assert via_real.read_authority().blocking
    assert _marker(via_real)["target"] == str(via_real.chroma_dir)

    done = _run(
        tmp_path,
        """
import sys
from chroma_write_guard import ChromaWriteGuard, _exclusive_flock
link, real = sys.argv[1:]
left, right = ChromaWriteGuard(link), ChromaWriteGuard(real)
assert left.lock_path == right.lock_path
with _exclusive_flock(left.lock_path, 2):
    with _exclusive_flock(right.lock_path, 2):
        print("reentered")
""",
        str(link),
        str(real),
        timeout=30,
    )
    assert done.returncode == 0, done.stderr
    assert "reentered" in done.stdout


def test_competing_legacy_guard_location_refuses_adoption(tmp_path: Path) -> None:
    _require_isolated_process()
    real = _refuse_production(tmp_path / "real-store")
    real.mkdir()
    link = tmp_path / "alias-store"
    link.symlink_to(real, target_is_directory=True)
    lexical = tmp_path / "alias-store.write-guard"
    lexical.mkdir()
    (lexical / "QUARANTINE.json").write_bytes(b'{"reason":"old","segment":"seg"}\n')
    canonical_root = real.parent / "real-store.write-guard"
    conflicted = ChromaWriteGuard(link)
    with pytest.raises(ChromaWriteGuardError, match="competing guard locations") as raised:
        conflicted.require_not_quarantined()
    text = str(raised.value)
    assert str(lexical) in text and str(canonical_root) in text
    assert not canonical_root.exists()


def test_alias_store_shares_the_canonical_client_cache(tmp_path: Path) -> None:
    """An alias store must not refresh bookkeeping for a different stale client."""
    _require_isolated_process()
    from chromadb.api.shared_system_client import SharedSystemClient

    from chroma_store import ChromaStore
    from chroma_write_guard import _SYSTEM_VIEWS
    from tests._chroma_write_guard_worker import embedding

    real = _refuse_production(tmp_path / "chroma")
    real.mkdir()
    link = tmp_path / "alias-chroma"
    link.symlink_to(real, target_is_directory=True)
    older = ChromaStore(str(real))
    alias = ChromaStore(str(link))
    guarded = None
    try:
        assert older.count_summaries() == 0
        canonical = str(canonical_target(real))
        assert older.chroma_dir == alias.chroma_dir == canonical
        assert str(link.resolve()) == canonical
        identifiers = SharedSystemClient._identifier_to_system
        assert canonical in identifiers
        assert str(link) not in identifiers
        assert len([key for key in identifiers if key in {canonical, str(link)}]) == 1
        alias.add_summary("alias-row", "doc", embedding("alias-row"), {"source_path": "/fixture"})
        assert older.count_summaries() == 1
        assert str(link) not in _SYSTEM_VIEWS
        assert canonical in _SYSTEM_VIEWS
        guarded = ChromaStore(str(real), write_guard=ChromaWriteGuard(link))
        guarded.add_summary("guarded-row", "doc", embedding("guarded-row"), {"source_path": "/fixture"})
        assert older.count_summaries() == 2
    finally:
        if guarded is not None:
            guarded.close()
        alias.close()
        older.close()


def test_competing_legacy_location_refuses_an_alias_store(tmp_path: Path) -> None:
    _require_isolated_process()
    from chroma_store import ChromaStore
    from tests._chroma_write_guard_worker import embedding

    real = _refuse_production(tmp_path / "real-store")
    real.mkdir()
    link = tmp_path / "alias-store"
    link.symlink_to(real, target_is_directory=True)
    lexical = tmp_path / "alias-store.write-guard"
    lexical.mkdir()
    (lexical / "QUARANTINE.json").write_bytes(b'{"reason":"old","segment":"seg"}\n')
    original = (lexical / "QUARANTINE.json").read_bytes()
    canonical_root = real.parent / "real-store.write-guard"
    store = ChromaStore(str(link), write_guard=ChromaWriteGuard(link))
    try:
        with pytest.raises(ChromaWriteGuardError, match="competing guard locations"):
            store.add_summary(
                "should-not-land",
                "doc",
                embedding("should-not-land"),
                {"source_path": "/fixture"},
            )
    finally:
        store.close()
    assert not canonical_root.exists()
    assert (lexical / "QUARANTINE.json").read_bytes() == original


def test_ordinary_clear_and_doctor_do_not_mutate(tmp_path: Path) -> None:
    _require_isolated_process()
    from doctor import _check_chroma_audit, _check_chroma_write_guard

    chroma = _refuse_production(tmp_path / "chroma")
    chroma.mkdir()
    guard = ChromaWriteGuard(chroma)
    _publish(guard, _finding_spec("seg", "structural", "kept", ("torn",)))
    marker = guard.quarantine_path.read_bytes()
    cfg = {"index": {"chroma_dir": str(chroma)}}
    assert _check_chroma_write_guard(cfg).effective_status() == "fail"
    assert guard.quarantine_path.read_bytes() == marker
    guard.quarantine_path.write_bytes(b"null\n")
    malformed = guard.quarantine_path.read_bytes()
    failed = _check_chroma_write_guard(cfg)
    assert failed.effective_status() == "fail" and "QUARANTINED" in failed.detail
    assert guard.quarantine_path.read_bytes() == malformed

    script = [
        sys.executable,
        str(ROOT / "scripts" / "chroma_guard.py"),
        "clear-quarantine",
        "--chroma-dir",
        str(chroma),
    ]
    cleared = subprocess.run(
        script,
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert cleared.returncode == 1, cleared.stdout + cleared.stderr
    assert "ordinary clear refuses" in cleared.stderr
    assert guard.quarantine_path.read_bytes() == malformed

    guard.audit_path.write_text(
        json.dumps(
            {
                "status": "error",
                "reason": "containment unavailable: injected",
                "containment": "unavailable",
                "ts": "2026-10-11T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    audit_bytes = guard.audit_path.read_bytes()
    audit_check = _check_chroma_audit(cfg)
    assert audit_check.effective_status() == "fail"
    assert "containment unavailable" in audit_check.detail
    assert guard.audit_path.read_bytes() == audit_bytes
    assert guard.quarantine_path.read_bytes() == malformed


OVERWRITE_PUBLISH = """
import sys
from chroma_write_guard import (
    ChromaWriteGuard,
    _empty_incident_document,
    _exclusive_flock,
    _finding_spec,
    _upsert_finding,
)
guard = ChromaWriteGuard(sys.argv[1])
finding_a = _finding_spec("seg-a", "structural", "finding A", ("a",))
finding_b = _finding_spec("seg-b", "structural", "finding B", ("b",))
with _exclusive_flock(guard.lock_path, 5):
    guard._publish_findings([finding_a])
# Deliberately faulty publisher: replace the unresolved set with only B.
replacement = _empty_incident_document(str(guard.chroma_dir))
_upsert_finding(replacement, finding_b)
with _exclusive_flock(guard.lock_path, 5):
    guard._publish_marker(replacement)
print("overwritten")
"""

REAL_PUBLISH = """
import sys
from chroma_write_guard import ChromaWriteGuard, _exclusive_flock, _finding_spec
guard = ChromaWriteGuard(sys.argv[1])
specs = (
    _finding_spec("seg-a", "structural", "finding A", ("a",)),
    _finding_spec("seg-b", "structural", "finding B", ("b",)),
)
for spec in specs:
    with _exclusive_flock(guard.lock_path, 5):
        guard._publish_findings([spec])
print("published")
"""


def test_overwrite_publisher_fails_retention_and_real_publisher_keeps_both(tmp_path: Path) -> None:
    """The faulty A-then-B publisher must fail retention; the real one must pass."""
    _require_isolated_process()
    from chroma_write_guard import _finding_id

    faulty_root = _refuse_production(tmp_path / "faulty")
    faulty_root.mkdir()
    overwritten = _run(tmp_path, OVERWRITE_PUBLISH, str(faulty_root))
    assert overwritten.returncode == 0, overwritten.stderr
    assert "overwritten" in overwritten.stdout
    faulty_marker = _marker(ChromaWriteGuard(faulty_root))
    id_a = _finding_id("seg-a", "structural", "finding A")
    id_b = _finding_id("seg-b", "structural", "finding B")
    assert {finding["id"] for finding in _findings(faulty_marker)} == {id_b}
    with pytest.raises(AssertionError, match="missing findings"):
        assert_findings_retained(faulty_marker, {id_a, id_b})

    real_root = _refuse_production(tmp_path / "real")
    real_root.mkdir()
    published = _run(tmp_path, REAL_PUBLISH, str(real_root))
    assert published.returncode == 0, published.stderr
    assert "published" in published.stdout
    retained = _marker(ChromaWriteGuard(real_root))
    assert_findings_retained(retained, {id_a, id_b})
    admission = _run(tmp_path, ADMIT, str(real_root))
    assert admission.returncode != 0
    assert "admitted" not in admission.stdout
    assert "quarantine" in admission.stderr.lower()
    assert_findings_retained(_marker(ChromaWriteGuard(real_root)), {id_a, id_b})


def _empty_document(guard: ChromaWriteGuard) -> dict:
    return {
        "schema": INCIDENT_SCHEMA,
        "version": INCIDENT_VERSION,
        "target": str(guard.chroma_dir),
        "incidents": [],
    }


def _make_store(tmp_path: Path) -> Path:
    import chromadb

    from chroma_store import SUMMARIES, UNITS

    chroma = _refuse_production(tmp_path / "chroma")
    client = chromadb.PersistentClient(path=str(chroma))
    for name in (SUMMARIES, UNITS):
        client.get_or_create_collection(
            name,
            configuration={"hnsw": {"space": "cosine", "sync_threshold": 100, "batch_size": 10}},
        )
    client.close()
    return chroma


def _write_records(chroma: Path, start: int, count: int) -> None:
    done = _run(
        chroma.parent,
        """
import sys
from chroma_store import ChromaStore
from tests._chroma_write_guard_worker import embedding, write_one
store = ChromaStore(sys.argv[1])
try:
    start, count = int(sys.argv[2]), int(sys.argv[3])
    for index in range(start, start + count):
        write_one(store, index)
finally:
    store.close()
""",
        str(chroma),
        str(start),
        str(count),
        timeout=180,
    )
    assert done.returncode == 0, done.stderr[-2000:]


def _embedding_id_present(chroma: Path, doc_id: str) -> bool:
    database = chroma / "chroma.sqlite3"
    uri = f"file:{database.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        row = connection.execute("select 1 from embeddings where embedding_id = ?", (doc_id,)).fetchone()
    finally:
        connection.close()
    return row is not None


def test_audit_retains_sequential_incidents_and_two_findings(tmp_path: Path) -> None:
    _require_isolated_process()
    from chroma_write_guard import segment_dirs

    from tests.test_chroma_write_guard import _set_header_count

    chroma = _make_store(tmp_path)
    _write_records(chroma, 0, 200)
    seg_id, seg = next(iter(segment_dirs(chroma).items()))
    header = (seg / "header.bin").read_bytes()
    _set_header_count(seg / "header.bin", 1)
    first = _run(tmp_path, AUDIT, str(chroma))
    assert first.returncode == 0, first.stderr[-2000:]
    assert json.loads(first.stdout)["status"] == "fail"
    after_first = _marker(ChromaWriteGuard(chroma))
    structural = [finding for finding in _findings(after_first) if finding["kind"] == "structural"]
    assert len(structural) == 1 and structural[0]["revision"] == 1
    first_ids = {finding["id"] for finding in _findings(after_first)}

    second_dir = chroma / "second-segment"
    second_dir.mkdir()
    (second_dir / "header.bin").write_bytes(b"\x00" * 10)
    second = _run(tmp_path, AUDIT, str(chroma))
    assert second.returncode == 0, second.stderr[-2000:]
    combined = _marker(ChromaWriteGuard(chroma))
    assert_findings_retained(combined, first_ids)
    segments = {incident["segment"] for incident in combined["incidents"]}
    assert seg_id in segments and "second-segment" in segments
    import pickle

    from chroma_write_guard import load_segment_id_map

    id_map = load_segment_id_map(seg)
    assert id_map is not None
    victim = next(iter(id_map["id_to_label"]))
    label = id_map["id_to_label"].pop(victim)
    id_map["label_to_id"].pop(label, None)
    (seg / "index_metadata.pickle").write_bytes(pickle.dumps(id_map))
    both = _run(tmp_path, AUDIT, str(chroma))
    assert both.returncode == 0, both.stderr[-2000:]
    documented = _marker(ChromaWriteGuard(chroma))
    kinds = {
        finding["kind"]
        for finding in _findings(documented)
        if _incident_segment(documented, finding) == seg_id
    }
    assert "structural" in kinds and "lost_vectors" in kinds
    assert_findings_retained(documented, first_ids)

    (seg / "header.bin").write_bytes(header)
    passed = _run(tmp_path, AUDIT, str(chroma))
    assert passed.returncode == 0, passed.stderr[-2000:]
    # Restoring the header does not release incidents already recorded.
    assert_findings_retained(_marker(ChromaWriteGuard(chroma)), first_ids)
    admission = _run(tmp_path, ADMIT, str(chroma))
    assert admission.returncode != 0
    assert "admitted" not in admission.stdout
    assert "quarantine" in admission.stderr.lower()


def _incident_segment(document: dict, finding: dict) -> str:
    for incident in document["incidents"]:
        if finding in incident["findings"]:
            return incident["segment"]
    raise AssertionError("finding missing")


def test_pass_skip_and_error_do_not_clear_incidents(tmp_path: Path) -> None:
    _require_isolated_process()
    import fcntl

    chroma = _make_store(tmp_path)
    guard = ChromaWriteGuard(chroma)
    _publish(guard, _finding_spec("seg", "structural", "sticky", ("torn",)))
    marker = guard.quarantine_path.read_bytes()
    passed = _run(tmp_path, AUDIT, str(chroma))
    assert passed.returncode == 0, passed.stderr[-2000:]
    assert json.loads(passed.stdout)["status"] == "pass"
    assert guard.quarantine_path.read_bytes() == marker

    guard.root.mkdir(parents=True, exist_ok=True)
    handle = os.open(guard.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(handle, fcntl.LOCK_EX)
        skipped = guard.audit(lock_timeout_seconds=0.2)
    finally:
        os.close(handle)
    assert skipped["status"] == "skipped"
    assert guard.quarantine_path.read_bytes() == marker

    import chroma_write_guard

    def explode(_path):
        raise sqlite3.DatabaseError("injected census failure")

    original = chroma_write_guard.vector_census
    chroma_write_guard.vector_census = explode
    try:
        errored = guard.audit()
    finally:
        chroma_write_guard.vector_census = original
    assert errored["status"] == "error"
    assert "injected census failure" in errored["reason"]
    assert guard.quarantine_path.read_bytes() == marker
    assert "containment unavailable" not in errored["reason"]


def _wait_until(ready: Path, proc: subprocess.Popen[str], message: str) -> None:
    deadline = time.monotonic() + 30
    while not ready.exists():
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            raise AssertionError(f"{message}: exited {proc.returncode}\n{stdout}\n{stderr}")
        if time.monotonic() > deadline:
            raise AssertionError(message)
        time.sleep(0.01)


def test_recover_and_write_recheck_after_the_lock(tmp_path: Path) -> None:
    _require_isolated_process()
    chroma = _make_store(tmp_path)
    ready = tmp_path / "recover-ready"
    release = tmp_path / "recover-release"
    proc = subprocess.Popen(
        [sys.executable, "-c", RECOVER, str(chroma)],
        cwd=ROOT,
        env={**os.environ, "CONVMEM_GUARD_ADMISSION_BARRIER": f"{ready}:{release}"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_until(ready, proc, "recover did not reach the admission barrier")
        guard = ChromaWriteGuard(chroma)
        _publish(guard, _finding_spec("seg", "structural", "published in the gap", ("gap",)))
        release.write_text("go", encoding="utf-8")
        stdout, stderr = proc.communicate(timeout=60)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.communicate()
    assert proc.returncode != 0
    assert "admitted" not in stdout
    assert "published in the gap" in stderr


def test_guarded_write_rechecks_after_the_lock(tmp_path: Path) -> None:
    _require_isolated_process()
    chroma = _make_store(tmp_path)
    ready = tmp_path / "write-ready"
    release = tmp_path / "write-release"
    writer = subprocess.Popen(
        [sys.executable, "-c", WRITE, str(chroma), "gap-write"],
        cwd=ROOT,
        env={**os.environ, "CONVMEM_GUARD_ADMISSION_BARRIER": f"{ready}:{release}"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_until(ready, writer, "writer did not reach the admission barrier")
        _publish(ChromaWriteGuard(chroma), _finding_spec("seg", "structural", "published in the gap", ("gap",)))
        release.write_text("go", encoding="utf-8")
        out, err = writer.communicate(timeout=60)
    finally:
        if writer.poll() is None:
            writer.kill()
            writer.communicate()
    assert writer.returncode != 0
    assert "admitted" not in out
    assert not _embedding_id_present(chroma, "gap-write")
    assert "published in the gap" in err


def test_audit_publication_excludes_a_concurrent_writer(tmp_path: Path) -> None:
    _require_isolated_process()
    from chroma_write_guard import segment_dirs

    from tests.test_chroma_write_guard import _set_header_count

    chroma = _make_store(tmp_path)
    _write_records(chroma, 0, 120)
    _seg_id, seg = next(iter(segment_dirs(chroma).items()))
    _set_header_count(seg / "header.bin", 3)
    ready = tmp_path / "audit-ready"
    release = tmp_path / "audit-release"
    audit = subprocess.Popen(
        [sys.executable, "-c", AUDIT, str(chroma)],
        cwd=ROOT,
        env={**os.environ, "CONVMEM_GUARD_LOCK_BARRIER": f"{ready}:{release}"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    writer: subprocess.Popen[str] | None = None
    try:
        _wait_until(ready, audit, "audit did not reach the lock barrier")
        writer = subprocess.Popen(
            [sys.executable, "-c", WRITE, str(chroma), "during-audit"],
            cwd=ROOT,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        release.write_text("go", encoding="utf-8")
        audit_out, audit_err = audit.communicate(timeout=120)
        write_out, write_err = writer.communicate(timeout=120)
    finally:
        if audit.poll() is None:
            audit.kill()
            audit.communicate()
        if writer is not None and writer.poll() is None:
            writer.kill()
            writer.communicate()
    assert audit.returncode == 0, audit_err[-2000:]
    result = json.loads(audit_out)
    assert result["status"] == "fail"
    assert writer.returncode != 0
    assert "admitted" not in write_out
    assert not _embedding_id_present(chroma, "during-audit")
    assert "structural" in {finding["kind"] for finding in _findings(_marker(ChromaWriteGuard(chroma)))}
    assert write_err


def test_publication_failure_aborts_before_mutation(tmp_path: Path, monkeypatch) -> None:
    _require_isolated_process()
    from chroma_write_guard import segment_dirs

    from tests.test_chroma_write_guard import _set_header_count

    chroma = _make_store(tmp_path)
    _write_records(chroma, 0, 150)
    _seg_id, seg = next(iter(segment_dirs(chroma).items()))
    before = (seg / "header.bin").read_bytes()
    _set_header_count(seg / "header.bin", 4)
    torn = (seg / "header.bin").read_bytes()

    def fail_file_fsync(self, path: Path, *, directory: bool = False) -> None:
        del self
        if not directory and ".QUARANTINE.json." in path.name:
            raise OSError("injected fsync failure")
        from chroma_write_guard import _fsync

        _fsync(path, directory=directory)

    monkeypatch.setattr(ChromaWriteGuard, "_fsync_published", fail_file_fsync)
    with pytest.raises(ChromaContainmentUnavailableError, match="containment unavailable") as raised:
        from chroma_write_guard import recover

        recover(chroma)
    assert "process-level containment" in str(raised.value)
    assert "not a durable stop" in str(raised.value)
    assert (seg / "header.bin").read_bytes() == torn
    assert not ChromaWriteGuard(chroma).quarantine_path.exists()

    monkeypatch.undo()

    def short_write(self, path: Path, payload: bytes) -> None:
        del self
        if ".QUARANTINE.json." in path.name:
            payload = payload[:8]
        path.write_bytes(payload)

    monkeypatch.setattr(ChromaWriteGuard, "_write_bytes", short_write)
    with pytest.raises(ChromaContainmentUnavailableError, match="containment unavailable"):
        from chroma_write_guard import recover

        recover(chroma)
    assert (seg / "header.bin").read_bytes() == torn
    assert not ChromaWriteGuard(chroma).quarantine_path.exists()
    monkeypatch.undo()

    def fail_dir_fsync(self, path: Path, *, directory: bool = False) -> None:
        del self
        if directory and path.name.endswith(".write-guard"):
            raise OSError("injected directory fsync failure")
        from chroma_write_guard import _fsync

        _fsync(path, directory=directory)

    monkeypatch.setattr(ChromaWriteGuard, "_fsync_published", fail_dir_fsync)
    with pytest.raises(ChromaContainmentUnavailableError, match="not a durable stop"):
        from chroma_write_guard import recover

        recover(chroma)
    assert (seg / "header.bin").read_bytes() == torn
    assert before != torn


def test_child_publication_failure_does_not_admit_the_write(tmp_path: Path) -> None:
    _require_isolated_process()
    from chroma_write_guard import segment_dirs

    from tests.test_chroma_write_guard import _set_header_count

    chroma = _make_store(tmp_path)
    _write_records(chroma, 0, 150)
    _seg_id, seg = next(iter(segment_dirs(chroma).items()))
    header = (seg / "header.bin").read_bytes()
    _set_header_count(seg / "header.bin", 2)
    code = """
import os, sys
from pathlib import Path
from chroma_store import ChromaStore
from chroma_write_guard import ChromaWriteGuard, _fsync
from tests._chroma_write_guard_worker import embedding

def fail_file_fsync(self, path, *, directory=False):
    if not directory and ".QUARANTINE.json." in path.name:
        raise OSError("injected fsync failure")
    _fsync(path, directory=directory)

ChromaWriteGuard._fsync_published = fail_file_fsync
store = ChromaStore(sys.argv[1], write_guard=ChromaWriteGuard(sys.argv[1]))
try:
    store.add_summary("should-not-land", "doc", embedding("should-not-land"), {"source_path": "/fixture"})
    print("admitted")
finally:
    store.close()
"""
    done = _run(tmp_path, code, str(chroma), timeout=180)
    assert done.returncode != 0, done.stdout
    assert "containment unavailable" in done.stderr
    assert "admitted" not in done.stdout
    assert not _embedding_id_present(chroma, "should-not-land")
    assert (seg / "header.bin").read_bytes() != header
    assert not ChromaWriteGuard(chroma).quarantine_path.exists()
