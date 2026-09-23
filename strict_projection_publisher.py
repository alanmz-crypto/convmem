"""Fixture-only strict projection publisher (M3 / T2).

Owns enrollment, cumulative authority/source-cutoff/history, fence→unavailable
→cold projection→serving publication, full publication-payload CAS, current-
head/current-contract rollback (no expiry renewal), nonempty-slot refusal
(proof-shaped data is never authority; no publisher slot mutation on publish),
crash recovery, and deterministic fault injection at every parent-fixed
write/fsync/rename/pointer boundary.

Does not own a manager, invent retirement, or admit T3–T5 reader/server paths.
Production uses a fresh interpreter for cold qualification; fixture calls
``strict_projection.qualify_authority_generation`` in-process after durable
authority writes.
"""

from __future__ import annotations

import argparse
import ast
import fcntl
import hashlib
import json
import os
import stat
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, MutableMapping, Sequence

from bound_read_scope import (
    BoundScopeError,
    EffectiveSelectors,
    authorize_row,
    resolve_scope,
    sha256_digest,
)
from strict_evidence_state import (
    REDUCER_VERSION,
    StrictEvidenceError,
    build_citation_map,
    build_projection_rows_and_graph,
    citation_ref,
    disposition_id,
    materialize_authority_records,
    public_ledger_id,
    reduce_complete_bound_state,
    state_sha256,
    validate_dispositions,
)
from strict_grounding import (
    QualificationTuple,
    StrictGroundingError,
    assert_cumulative_grounding,
    assert_cumulative_provenance_context,
    compute_added_grounding_refs,
    compute_added_provenance_ids,
    load_bound_issuer_inventories,
    qualify_assertions,
    strict_canonical_bytes,
    validate_provenance_context,
)
from strict_projection import (
    StrictProjectionError,
    qualify_authority_generation,
)

# ---------------------------------------------------------------------------
# Public constants / fault injection
# ---------------------------------------------------------------------------

BUILDER_VERSION = "strict-projection-publisher/v1"
SEARCH_KERNEL = "lexical_v1"
SEARCH_KERNEL_VERSION = "1"
IDENTITY_VERSION = "v2"
CANONICALIZATION_VERSION = "v1"
GROUNDING_VERSION = "v1"
TOKENIZER_UNICODE_VERSION = "15.1.0"
REQUIRED_MAX_PROJECTION_ROWS = 10000
REQUIRED_MAX_PROJECTION_BYTES = 67108864
REQUIRED_TELEMETRY = False

_STRICT_CONFIG_FIELDS = frozenset(
    {
        "schema",
        "projection_root",
        "max_projection_rows",
        "max_projection_bytes",
        "telemetry",
    }
)
_SEMANTIC_CONTRACT_FIELDS = frozenset(
    {
        "schema",
        "reducer_version",
        "grounding_version",
        "canonicalization_version",
        "identity_version",
        "search_kernel",
        "search_kernel_version",
        "tokenizer_unicode_version",
        "schema_digests",
        "contract_payload_sha256",
    }
)
_REQUIRED_SEMANTIC_CONTRACT = {
    "reducer_version": REDUCER_VERSION,
    "grounding_version": GROUNDING_VERSION,
    "canonicalization_version": CANONICALIZATION_VERSION,
    "identity_version": IDENTITY_VERSION,
    "search_kernel": SEARCH_KERNEL,
    "search_kernel_version": SEARCH_KERNEL_VERSION,
    "tokenizer_unicode_version": TOKENIZER_UNICODE_VERSION,
}

# Parent-fixed write/fsync/rename/pointer boundaries (Architecture §6.5.4 / case 52).
FAULT_HOOKS: dict[str, Callable[[], None]] = {}

__all__ = [
    "BUILDER_VERSION",
    "FAULT_HOOKS",
    "StrictPublisherError",
    "enroll_fixture",
    "main",
    "publish_projection",
    "recover_projection",
    "rebuild_projection",
    "rollback_projection",
]


class StrictPublisherError(ValueError):
    """Fail-closed fixture publisher error."""


# ---------------------------------------------------------------------------
# Small durable I/O helpers
# ---------------------------------------------------------------------------


def _fault(name: str) -> None:
    hook = FAULT_HOOKS.get(name)
    if hook is not None:
        hook()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise StrictPublisherError(f"duplicate_key:{key}")
        out[key] = value
    return out


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise StrictPublisherError(f"missing_file:{path}")
    raw = path.read_bytes()
    try:
        obj = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrictPublisherError(f"json_invalid:{path}") from exc
    if not isinstance(obj, dict):
        raise StrictPublisherError(f"json_object_required:{path}")
    # Reject noncanonical on-disk bytes; never repair then accept.
    if strict_canonical_bytes(obj) != raw:
        raise StrictPublisherError(f"json_noncanonical:{path}")
    return obj


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise StrictPublisherError(f"missing_file:{path}")
    raw = path.read_bytes()
    if not raw:
        return []
    if not raw.endswith(b"\n"):
        raise StrictPublisherError(f"jsonl_noncanonical:{path}")
    rows: list[dict[str, Any]] = []
    lines = raw.split(b"\n")[:-1]  # exact trailing newline required above
    for line_no, line in enumerate(lines, start=1):
        if not line:
            raise StrictPublisherError(f"jsonl_empty_line:{path}:{line_no}")
        try:
            obj = json.loads(line.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StrictPublisherError(f"jsonl_invalid:{path}:{line_no}") from exc
        if not isinstance(obj, dict):
            raise StrictPublisherError(f"jsonl_object_required:{path}:{line_no}")
        if strict_canonical_bytes(obj) != line:
            raise StrictPublisherError(f"jsonl_noncanonical:{path}:{line_no}")
        rows.append(obj)
    return rows


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _self_hash(obj: Mapping[str, Any], field: str) -> str:
    if field not in obj:
        raise StrictPublisherError(f"self_hash_field_missing:{field}")
    body = {k: v for k, v in obj.items() if k != field}
    return sha256_digest(strict_canonical_bytes(body))


def _set_self_hash(obj: MutableMapping[str, Any], field: str) -> str:
    digest = _self_hash(obj, field)
    obj[field] = digest
    return digest


def _sha256hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _authority_snapshot_id(manifest: Mapping[str, Any]) -> str:
    body = {
        k: v
        for k, v in manifest.items()
        if k not in {"snapshot_id", "manifest_payload_sha256"}
    }
    return "snap2_" + _sha256hex(strict_canonical_bytes(body))


def _projection_generation_id(manifest: Mapping[str, Any]) -> str:
    body = {
        k: v
        for k, v in manifest.items()
        if k not in {"generation_id", "manifest_payload_sha256"}
    }
    return "gen2_" + _sha256hex(strict_canonical_bytes(body))


def _canonical_jsonl_bytes(objects: Sequence[Mapping[str, Any]]) -> bytes:
    if not objects:
        return b""
    return b"".join(strict_canonical_bytes(obj) + b"\n" for obj in objects)


def _jsonl_sha256(objects: Sequence[Mapping[str, Any]]) -> str:
    return sha256_digest(_canonical_jsonl_bytes(objects))


def _write_bytes_atomic(
    path: Path,
    data: bytes,
    *,
    before_rename: str | None = None,
    after_rename: str | None = None,
    before_dir_fsync: str | None = None,
    after_dir_fsync: str | None = None,
    before_file_fsync: str | None = None,
    after_file_fsync: str | None = None,
) -> None:
    """Write then fsync file; os.replace; fsync parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as handle:
        handle.write(data)
        handle.flush()
        if before_file_fsync:
            _fault(before_file_fsync)
        os.fsync(handle.fileno())
        if after_file_fsync:
            _fault(after_file_fsync)
    if before_rename:
        _fault(before_rename)
    os.replace(tmp, path)
    if after_rename:
        _fault(after_rename)
    if before_dir_fsync:
        _fault(before_dir_fsync)
    _fsync_dir(path.parent)
    if after_dir_fsync:
        _fault(after_dir_fsync)


def _write_json_atomic(
    path: Path,
    obj: Mapping[str, Any],
    *,
    before_rename: str | None = None,
    after_rename: str | None = None,
    before_dir_fsync: str | None = None,
    after_dir_fsync: str | None = None,
    before_file_fsync: str | None = None,
    after_file_fsync: str | None = None,
) -> None:
    _write_bytes_atomic(
        path,
        strict_canonical_bytes(obj),
        before_rename=before_rename,
        after_rename=after_rename,
        before_dir_fsync=before_dir_fsync,
        after_dir_fsync=after_dir_fsync,
        before_file_fsync=before_file_fsync,
        after_file_fsync=after_file_fsync,
    )


def _write_jsonl_atomic(
    path: Path,
    objects: Sequence[Mapping[str, Any]],
    *,
    before_file_fsync: str | None = None,
    after_file_fsync: str | None = None,
) -> None:
    _write_bytes_atomic(
        path,
        _canonical_jsonl_bytes(objects),
        before_file_fsync=before_file_fsync,
        after_file_fsync=after_file_fsync,
    )


def _utc_now_iso() -> str:
    # Fixture clock is operator-supplied via bundle/clock review; enrollment
    # uses a fixed synthetic stamp only when the enrollment object already
    # carries published_at semantics through the publication record.
    return "1970-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# Builder tree / semantic contract helpers
# ---------------------------------------------------------------------------

# Parent-fixed §6.5.9 CORE (nine files). Production-local literal — never imported
# from tests or discovered by filesystem glob.
_CORE_MEMBERS: tuple[str, ...] = (
    "canonical_json.py",
    "provenance.py",
    "provenance_binding.py",
    "domains.py",
    "bound_read_scope.py",
    "strict_grounding.py",
    "strict_evidence_state.py",
    "strict_projection.py",
    "requirements.txt",
)

# Parent-fixed Gate B (24) + Gate C (7) schema inventory from Execution §2.
_SCHEMAS_BC: tuple[str, ...] = (
    "schemas/convmem-bound-read-scope-v2.schema.json",
    "schemas/convmem-project-binding-registry-v3.schema.json",
    "schemas/convmem-bound-authority-record-v3.schema.json",
    "schemas/convmem-authority-disposition-v1.schema.json",
    "schemas/convmem-strict-provenance-context-v2.schema.json",
    "schemas/convmem-strict-grounding-v1.schema.json",
    "schemas/convmem-capture-receipt-v1.schema.json",
    "schemas/convmem-strict-fixture-bundle-v2.schema.json",
    "schemas/convmem-strict-citation-map-v1.schema.json",
    "schemas/convmem-bound-authority-manifest-v3.schema.json",
    "schemas/convmem-bound-projection-row-v2.schema.json",
    "schemas/convmem-strict-graph-v1.schema.json",
    "schemas/convmem-bound-projection-manifest-v3.schema.json",
    "schemas/convmem-strict-generation-layout-v2.schema.json",
    "schemas/convmem-strict-publication-v2.schema.json",
    "schemas/convmem-strict-enrollment-v1.schema.json",
    "schemas/convmem-strict-slot-v1.schema.json",
    "schemas/convmem-strict-source-cutoff-v1.schema.json",
    "schemas/convmem-strict-semantic-contract-v1.schema.json",
    "schemas/convmem-strict-state-v2.schema.json",
    "schemas/convmem-clock-review-v1.schema.json",
    "schemas/convmem-raw-evidence-v3.schema.json",
    "schemas/convmem-error-v1.schema.json",
    "schemas/convmem-strict-config-v2.schema.json",
    "schemas/convmem-openclaw-connector-launch-v2.schema.json",
    "schemas/convmem-openclaw-activation-v2.schema.json",
    "schemas/convmem-activation-control-v1.schema.json",
    "schemas/convmem-activation-retirement-v1.schema.json",
    "schemas/convmem-activation-launch-policy-v1.schema.json",
    "schemas/convmem-activation-manager-policy-v1.schema.json",
    "schemas/convmem-controller-socket-policy-v1.schema.json",
)

_BUILDER_MEMBERS: tuple[str, ...] = tuple(
    sorted(set(_CORE_MEMBERS) | set(_SCHEMAS_BC) | {"strict_projection_publisher.py"})
)

_ALLOWED_LOCAL_IMPORT_STEMS: frozenset[str] = frozenset(
    {Path(p).stem for p in _CORE_MEMBERS if p.endswith(".py")}
    | {"strict_projection_publisher"}
)


def _production_root(root: Path | None = None) -> Path:
    if root is not None:
        return root
    return Path(__file__).resolve().parent


def _reject_builder_import_drift(base: Path) -> None:
    """Fail closed if this module imports tests or unlisted local modules."""
    pub_path = base / "strict_projection_publisher.py"
    if pub_path.is_symlink() or not pub_path.is_file():
        raise StrictPublisherError("builder_missing:strict_projection_publisher.py")
    source = pub_path.read_bytes().decode("utf-8")
    try:
        tree = ast.parse(source, filename=str(pub_path))
    except SyntaxError as exc:
        raise StrictPublisherError("builder_import_drift:syntax") from exc
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        for name in names:
            top = name.split(".", 1)[0]
            if top == "tests" or name.startswith("tests."):
                raise StrictPublisherError("builder_import_drift:tests")
            if "component_inventory" in name.split("."):
                raise StrictPublisherError("builder_import_drift:tests")
            local = base / f"{top}.py"
            if local.is_file() and top not in _ALLOWED_LOCAL_IMPORT_STEMS:
                raise StrictPublisherError(f"builder_import_drift:{top}")


def _member_entry(base: Path, rel: str) -> dict[str, str]:
    path = base / rel
    if path.is_symlink():
        raise StrictPublisherError(f"builder_symlink:{rel}")
    if not path.is_file():
        raise StrictPublisherError(f"builder_missing:{rel}")
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode):
        raise StrictPublisherError(f"builder_not_regular:{rel}")
    mode = f"{st.st_mode & 0o7777:04o}"
    if len(mode) != 4 or any(ch not in "01234567" for ch in mode):
        raise StrictPublisherError(f"builder_mode_invalid:{rel}")
    return {
        "path": rel,
        "mode": mode,
        "sha256": sha256_digest(path.read_bytes()),
    }


def _builder_tree_sha256(root: Path | None = None) -> str:
    """SHA-256 of sorted {path,mode,sha256} over parent-fixed builder inventory.

    Fail closed on missing/symlink/non-regular/import drift. Never hash names only.
    """
    base = _production_root(root)
    _reject_builder_import_drift(base)
    entries = [_member_entry(base, rel) for rel in _BUILDER_MEMBERS]
    if len(entries) != len(_BUILDER_MEMBERS):
        raise StrictPublisherError("builder_inventory_drift")
    return sha256_digest(strict_canonical_bytes(entries))


def _schema_digests(root: Path | None = None) -> list[dict[str, str]]:
    """Exact Gate B/C schema digests; every member must be present (fail closed)."""
    base = _production_root(root)
    digests: list[dict[str, str]] = []
    for rel in sorted(_SCHEMAS_BC):
        path = base / rel
        if path.is_symlink():
            raise StrictPublisherError(f"schema_symlink:{rel}")
        if not path.is_file():
            raise StrictPublisherError(f"schema_missing:{rel}")
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode):
            raise StrictPublisherError(f"schema_not_regular:{rel}")
        digests.append(
            {
                "path": rel,
                "sha256": sha256_digest(path.read_bytes()),
            }
        )
    return digests


def _validate_strict_config(config: Mapping[str, Any]) -> Path:
    """Closed convmem.strict-config.v2 — exact keys/constants; absolute projection_root."""
    if set(config) != _STRICT_CONFIG_FIELDS:
        raise StrictPublisherError("strict_config_keys")
    if config["schema"] != "convmem.strict-config.v2":
        raise StrictPublisherError("strict_config_schema")
    root_s = config["projection_root"]
    if not isinstance(root_s, str) or not root_s:
        raise StrictPublisherError("projection_root_type")
    root = Path(root_s)
    if not root.is_absolute():
        raise StrictPublisherError("projection_root_not_absolute")
    rows = config["max_projection_rows"]
    if (
        not isinstance(rows, int)
        or isinstance(rows, bool)
        or rows != REQUIRED_MAX_PROJECTION_ROWS
    ):
        raise StrictPublisherError("max_projection_rows")
    nbytes = config["max_projection_bytes"]
    if (
        not isinstance(nbytes, int)
        or isinstance(nbytes, bool)
        or nbytes != REQUIRED_MAX_PROJECTION_BYTES
    ):
        raise StrictPublisherError("max_projection_bytes")
    telemetry = config["telemetry"]
    if not isinstance(telemetry, bool) or telemetry is not REQUIRED_TELEMETRY:
        raise StrictPublisherError("telemetry")
    return root


def _validate_semantic_contract(contract: Mapping[str, Any]) -> str:
    """Closed semantic contract with frozen versions and Gate B/C schema digests."""
    if set(contract) != _SEMANTIC_CONTRACT_FIELDS:
        raise StrictPublisherError("semantic_contract_keys")
    if contract["schema"] != "convmem.strict-semantic-contract.v1":
        raise StrictPublisherError("semantic_contract_schema")
    if unicodedata.unidata_version != TOKENIZER_UNICODE_VERSION:
        raise StrictPublisherError("tokenizer_unicode_runtime")
    for key, expected in _REQUIRED_SEMANTIC_CONTRACT.items():
        if contract[key] != expected:
            raise StrictPublisherError(f"semantic_contract_{key}")
    digests = contract["schema_digests"]
    if not isinstance(digests, list):
        raise StrictPublisherError("schema_digests_type")
    expected = _schema_digests()
    if strict_canonical_bytes(digests) != strict_canonical_bytes(expected):
        raise StrictPublisherError("schema_digests_mismatch")
    sc_hash = _self_hash(contract, "contract_payload_sha256")
    if contract["contract_payload_sha256"] != sc_hash:
        raise StrictPublisherError("semantic_contract_hash")
    return sc_hash


def _empty_source_cutoff(*, lineage_id: str, mode: str = "fixture") -> dict[str, Any]:
    cutoff: dict[str, Any] = {
        "schema": "convmem.strict-source-cutoff.v1",
        "lineage_id": lineage_id,
        "mode": mode,
        "operations": [],
        "cutoff_payload_sha256": "sha256:" + ("0" * 64),
    }
    _set_self_hash(cutoff, "cutoff_payload_sha256")
    return cutoff


def _publication_hash(publication: Mapping[str, Any]) -> str:
    return _self_hash(publication, "publication_payload_sha256")


def _seal_publication(publication: MutableMapping[str, Any]) -> str:
    return _set_self_hash(publication, "publication_payload_sha256")


def _history_path(root: Path, publication_payload_sha256: str) -> Path:
    hex_part = publication_payload_sha256.removeprefix("sha256:")
    return root / "active" / "history" / f"{hex_part}.json"


def _active_path(root: Path, lineage_id: str) -> Path:
    return root / "active" / f"{lineage_id}.json"


def _require_fixture_mode(enrollment: Mapping[str, Any]) -> None:
    if enrollment.get("mode") != "fixture":
        raise StrictPublisherError("fixture_mode_required")


def _require_empty_slot(slot: Mapping[str, Any]) -> None:
    """Publisher admits only an already-empty slot.

    Nonempty/unknown slots refuse even when the caller supplies retirement or
    empty-domain proof-shaped data. The publisher never mutates slot state and
    never treats proof payloads as authority (T5 owns the fake retirement port).
    """
    state = slot.get("state")
    if state == "empty":
        return
    if state not in {"starting", "active", "retiring", "quarantined"}:
        raise StrictPublisherError("slot_state_unknown")
    raise StrictPublisherError("retire_first_required")


def _load_slot(root: Path) -> dict[str, Any]:
    return _read_json(root / "control" / "slot.json")


def _seal_slot(slot: MutableMapping[str, Any]) -> str:
    return _set_self_hash(slot, "slot_payload_sha256")


def _write_slot(root: Path, slot: Mapping[str, Any]) -> None:
    """Enrollment-only slot write. Publish/rebuild/rollback/recover never call this."""
    sealed = dict(slot)
    _seal_slot(sealed)
    _write_json_atomic(root / "control" / "slot.json", sealed)


def _create_lock_files(root: Path, *, lineage_id: str, slot_id: str) -> None:
    """Create empty lock files at enrollment. Does not acquire exclusive locks."""
    locks = root / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    for name in (f"{slot_id}.transition.lock", f"{lineage_id}.lock"):
        path = locks / name
        if path.is_symlink():
            raise StrictPublisherError(f"lock_symlink:{name}")
        if not path.exists():
            path.write_bytes(b"")
            fd = os.open(str(path), os.O_RDWR)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            _fsync_dir(locks)


@contextmanager
def _held_publisher_locks(
    root: Path, *, lineage_id: str, slot_id: str
) -> Iterator[None]:
    """Acquire and hold slot-transition then lineage locks (parent fixture order).

    Exclusive ``fcntl.flock`` on pre-created lock files — not mere file creation.
    Concurrent writers serialize; the lock is held across the full CAS/write path.
    """
    locks = root / "locks"
    ordered = (
        locks / f"{slot_id}.transition.lock",
        locks / f"{lineage_id}.lock",
    )
    fds: list[int] = []
    try:
        for path in ordered:
            if path.is_symlink() or not path.is_file():
                raise StrictPublisherError(f"lock_missing:{path.name}")
            fd = os.open(str(path), os.O_RDWR)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
            except OSError:
                os.close(fd)
                raise
            fds.append(fd)
        yield
    finally:
        for fd in reversed(fds):
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)


def _commit_publication(
    root: Path,
    publication: MutableMapping[str, Any],
    *,
    rename_tag: str,
) -> str:
    """Write immutable history entry, then atomically replace current pointer."""
    digest = _seal_publication(publication)
    history = _history_path(root, digest)
    if history.exists():
        prior = _read_json(history)
        if prior != dict(publication):
            raise StrictPublisherError("history_collision")
    else:
        _write_json_atomic(
            history,
            publication,
            before_file_fsync=f"before_history_fsync_{rename_tag}",
            after_file_fsync=f"after_history_fsync_{rename_tag}",
        )
    active = _active_path(root, str(publication["lineage_id"]))
    _write_json_atomic(
        active,
        publication,
        before_rename=f"before_pointer_rename_{rename_tag}",
        after_rename=f"after_pointer_rename_{rename_tag}",
        before_dir_fsync=f"before_pointer_dir_fsync_{rename_tag}",
        after_dir_fsync=f"after_pointer_dir_fsync_{rename_tag}",
        before_file_fsync=f"before_pointer_fsync_{rename_tag}",
        after_file_fsync=f"after_pointer_fsync_{rename_tag}",
    )
    return digest


def _current_publication(root: Path, lineage_id: str) -> dict[str, Any]:
    return _read_json(_active_path(root, lineage_id))


def _require_cas(current: Mapping[str, Any], expected: str) -> None:
    digest = _publication_hash(current)
    if digest != expected:
        raise StrictPublisherError("publication_cas_mismatch")


def _find_operation_outcome(
    root: Path, *, operation_id: str, input_sha256: str
) -> dict[str, Any] | None:
    """Return historic publication for exact operation+input if present in history."""
    history_dir = root / "active" / "history"
    if not history_dir.is_dir():
        return None
    matches: list[dict[str, Any]] = []
    for path in sorted(history_dir.glob("*.json")):
        if path.is_symlink() or not path.is_file():
            continue
        pub = _read_json(path)
        pending = pub.get("pending_operation_id")
        # Historic outcomes store operation on fenced records; admitted heads
        # retain authority identity. Look up via authority input when present.
        if pending == operation_id:
            matches.append(pub)
            continue
        snap = pub.get("authority_snapshot_id")
        if not isinstance(snap, str):
            continue
        input_path = root / "authority" / snap / "input.json"
        if not input_path.is_file():
            continue
        input_obj = _read_json(input_path)
        field = (
            "fixture_payload_sha256"
            if input_obj.get("schema") == "convmem.strict-fixture-bundle.v2"
            else "artifact_payload_sha256"
        )
        if input_obj.get(field) == input_sha256 and input_obj.get("operation_id") == operation_id:
            matches.append(pub)
    if not matches:
        return None
    # Prefer highest epoch admitted (non-fenced) outcome.
    matches.sort(key=lambda p: int(p["epoch"]))
    return matches[-1]


# ---------------------------------------------------------------------------
# Enrollment (empty genesis)
# ---------------------------------------------------------------------------


def enroll_fixture(
    *,
    enrollment_path: str | Path,
    semantic_contract_path: str | Path,
    strict_config_path: str | Path,
) -> dict[str, Any]:
    """Create empty-root enrolled genesis: epoch1 unavailable/seq0, never serving."""
    enrollment = _read_json(Path(enrollment_path))
    if set(enrollment) != {
        "schema",
        "lineage_id",
        "slot_id",
        "mode",
        "owner_digest",
        "operator_uid",
        "controller_uid",
        "supervisor_uid",
        "runtime_uid",
        "scope_sha256",
        "registry_sha256",
        "semantic_contract_sha256",
        "initial_source_cutoff_sha256",
        "enrollment_payload_sha256",
    }:
        raise StrictPublisherError("enrollment_keys")
    if enrollment["schema"] != "convmem.strict-enrollment.v1":
        raise StrictPublisherError("enrollment_schema")
    _require_fixture_mode(enrollment)
    if _self_hash(enrollment, "enrollment_payload_sha256") != enrollment[
        "enrollment_payload_sha256"
    ]:
        raise StrictPublisherError("enrollment_hash")

    semantic_contract = _read_json(Path(semantic_contract_path))
    sc_hash = _validate_semantic_contract(semantic_contract)
    if enrollment["semantic_contract_sha256"] != sc_hash:
        raise StrictPublisherError("enrollment_semantic_contract_link")

    config = _read_json(Path(strict_config_path))
    root = _validate_strict_config(config)
    if root.is_symlink():
        raise StrictPublisherError("projection_root_symlink")
    if root.exists():
        # Empty root only: no prior enrollment or retained history.
        if any(root.iterdir()):
            raise StrictPublisherError("enrollment_root_not_empty")
    else:
        root.mkdir(parents=True, exist_ok=True)

    lineage_id = enrollment["lineage_id"]
    slot_id = enrollment["slot_id"]
    if not isinstance(lineage_id, str) or len(lineage_id) != 32:
        raise StrictPublisherError("lineage_id")
    if not isinstance(slot_id, str) or len(slot_id) != 32:
        raise StrictPublisherError("slot_id")

    empty_cutoff = _empty_source_cutoff(lineage_id=lineage_id, mode="fixture")
    if enrollment["initial_source_cutoff_sha256"] != empty_cutoff["cutoff_payload_sha256"]:
        raise StrictPublisherError("enrollment_cutoff_mismatch")

    layout = {
        "schema": "convmem.strict-generation-layout.v2",
        "authority_dir": "authority",
        "projection_dir": "projection",
        "active_dir": "active",
        "locks_dir": "locks",
        "control_dir": "control",
        "layout_payload_sha256": "sha256:" + ("0" * 64),
    }
    _set_self_hash(layout, "layout_payload_sha256")

    for sub in ("authority", "projection", "active", "active/history", "locks", "control", "control/clock"):
        (root / sub).mkdir(parents=True, exist_ok=True)

    _create_lock_files(root, lineage_id=lineage_id, slot_id=slot_id)

    with _held_publisher_locks(root, lineage_id=lineage_id, slot_id=slot_id):
        _write_json_atomic(root / "layout.json", layout)
        _write_json_atomic(root / "control" / "enrollment.json", enrollment)
        _write_json_atomic(root / "control" / "semantic-contract.json", semantic_contract)

        slot = {
            "schema": "convmem.strict-slot.v1",
            "slot_id": slot_id,
            "lineage_id": lineage_id,
            "activation_id": None,
            "activation_manifest_sha256": None,
            "unit_invocation_id": None,
            "state": "empty",
            "retirement_ref": None,
            "slot_payload_sha256": "sha256:" + ("0" * 64),
        }
        _seal_slot(slot)
        _write_slot(root, slot)

        publication: dict[str, Any] = {
            "schema": "convmem.strict-publication.v2",
            "lineage_id": lineage_id,
            "owner_digest": enrollment["owner_digest"],
            "epoch": 1,
            "authority_seq": 0,
            "authority_snapshot_id": None,
            "authority_manifest_sha256": None,
            "authority_source_cutoff_sha256": empty_cutoff["cutoff_payload_sha256"],
            "serving_generation_id": None,
            "projection_manifest_sha256": None,
            "semantic_contract_sha256": sc_hash,
            "pending_operation_id": None,
            "mode": "unavailable",
            "previous_publication_sha256": None,
            "freshness_anchor": None,
            "published_at": _utc_now_iso(),
            "publication_payload_sha256": "sha256:" + ("0" * 64),
        }
        digest = _commit_publication(root, publication, rename_tag="enroll")
        publication["publication_payload_sha256"] = digest
        return dict(publication)


# ---------------------------------------------------------------------------
# Build / publish path
# ---------------------------------------------------------------------------


def _load_root_context(
    *,
    scope_path: str | Path,
    registry_path: str | Path,
    strict_config_path: str | Path,
) -> tuple[Path, Any, Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = _read_json(Path(strict_config_path))
    root = _validate_strict_config(config)
    if root.is_symlink() or not root.is_dir():
        raise StrictPublisherError("projection_root_invalid")
    resolved = resolve_scope(scope_path=scope_path, registry_path=registry_path)
    enrollment = _read_json(root / "control" / "enrollment.json")
    _require_fixture_mode(enrollment)
    if enrollment["scope_sha256"] != resolved.scope.scope_sha256:
        raise StrictPublisherError("enrollment_scope_link")
    if enrollment["registry_sha256"] != resolved.registry.registry_sha256:
        raise StrictPublisherError("enrollment_registry_link")
    if enrollment["owner_digest"] != resolved.owner_digest:
        raise StrictPublisherError("enrollment_owner_digest")
    semantic_contract = _read_json(root / "control" / "semantic-contract.json")
    sc_hash = _validate_semantic_contract(semantic_contract)
    if enrollment["semantic_contract_sha256"] != sc_hash:
        raise StrictPublisherError("enrollment_semantic_contract_link")
    return root, resolved.scope, resolved.registry, enrollment, semantic_contract, config


def _parent_heads_by_logical(
    records: Sequence[Mapping[str, Any]], dispositions: Mapping[str, Mapping[str, Any]]
) -> dict[str, list[str]]:
    reduced = reduce_complete_bound_state(records, dispositions)
    heads: dict[str, list[str]] = {}
    for assertion_id, state in reduced.items():
        if state.authority_state in {"current", "conflict"}:
            # Map via record logical_id
            pass
    by_assertion = {r["assertion_id"]: r for r in records}
    for assertion_id, state in reduced.items():
        if state.authority_state not in {"current", "conflict"}:
            continue
        logical = by_assertion[assertion_id]["logical_id"]
        heads.setdefault(logical, []).append(assertion_id)
    for logical in heads:
        heads[logical] = sorted(set(heads[logical]))
    return heads


def _build_rows_and_graph(
    *,
    records: Sequence[Mapping[str, Any]],
    reduced: Mapping[str, Any],
    lineage_id: str,
    authority_seq: int,
    authority_manifest_sha256: str,
    semantic_contract_sha256: str,
    binding_public_ref: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return build_projection_rows_and_graph(
        records=records,
        reduced=reduced,
        lineage_id=lineage_id,
        authority_seq=authority_seq,
        authority_manifest_sha256=authority_manifest_sha256,
        semantic_contract_sha256=semantic_contract_sha256,
        binding_public_ref=binding_public_ref,
    )


def _freshness_anchor_for(
    *,
    snapshot_id: str,
    boot_id: str,
    sampled_wall_time: str,
    sampled_boottime_ns: int,
    snapshot_deadline_boottime_ns: int,
    clock_review_ref: str,
) -> dict[str, Any]:
    return {
        "boot_id": boot_id,
        "authority_snapshot_id": snapshot_id,
        "sampled_wall_time": sampled_wall_time,
        "sampled_boottime_ns": sampled_boottime_ns,
        "snapshot_deadline_boottime_ns": snapshot_deadline_boottime_ns,
        "clock_review_ref": clock_review_ref,
    }


def publish_projection(
    *,
    bundle: Mapping[str, Any] | None = None,
    bundle_path: str | Path | None = None,
    scope_path: str | Path,
    registry_path: str | Path,
    strict_config_path: str | Path,
    expected_publication_sha256: str,
    retirement_proof: Mapping[str, Any] | None = None,
    empty_domain_proof: Mapping[str, Any] | None = None,
    admit_source: bool = True,
    target_generation_id: str | None = None,
    rebuild: bool = False,
    rollback: bool = False,
) -> dict[str, Any]:
    """Core build/admit/rebuild/rollback publication path used by tests and CLI."""
    # Proof-shaped kwargs are never authority; nonempty slots refuse regardless.
    del retirement_proof, empty_domain_proof

    root, scope, registry, enrollment, semantic_contract, _config = _load_root_context(
        scope_path=scope_path,
        registry_path=registry_path,
        strict_config_path=strict_config_path,
    )
    lineage_id = enrollment["lineage_id"]
    slot_id = enrollment["slot_id"]

    with _held_publisher_locks(root, lineage_id=lineage_id, slot_id=slot_id):
        return _publish_projection_locked(
            root=root,
            scope=scope,
            registry=registry,
            enrollment=enrollment,
            semantic_contract=semantic_contract,
            expected_publication_sha256=expected_publication_sha256,
            bundle=bundle,
            bundle_path=bundle_path,
            admit_source=admit_source,
            target_generation_id=target_generation_id,
            rebuild=rebuild,
            rollback=rollback,
        )


def _publish_projection_locked(
    *,
    root: Path,
    scope: Any,
    registry: Any,
    enrollment: Mapping[str, Any],
    semantic_contract: Mapping[str, Any],
    expected_publication_sha256: str,
    bundle: Mapping[str, Any] | None,
    bundle_path: str | Path | None,
    admit_source: bool,
    target_generation_id: str | None,
    rebuild: bool,
    rollback: bool,
) -> dict[str, Any]:
    """Publication body; caller must already hold slot→lineage exclusive locks."""
    lineage_id = enrollment["lineage_id"]
    slot = _load_slot(root)
    _require_empty_slot(slot)

    current = _current_publication(root, lineage_id)
    _require_cas(current, expected_publication_sha256)
    sc_hash = _self_hash(semantic_contract, "contract_payload_sha256")
    owner = enrollment["owner_digest"]
    binding_id = scope.allowed_project_bindings[0]
    binding = registry.binding(binding_id)

    if rollback:
        return _rollback_serving(
            root=root,
            scope=scope,
            registry=registry,
            enrollment=enrollment,
            semantic_contract=semantic_contract,
            current=current,
            target_generation_id=target_generation_id,
            owner=owner,
            sc_hash=sc_hash,
        )

    if rebuild or not admit_source:
        return _rebuild_serving(
            root=root,
            scope=scope,
            registry=registry,
            enrollment=enrollment,
            semantic_contract=semantic_contract,
            current=current,
            owner=owner,
            sc_hash=sc_hash,
            binding=binding,
        )

    if bundle is None:
        if bundle_path is None:
            raise StrictPublisherError("bundle_required")
        bundle = _read_json(Path(bundle_path))
    if not isinstance(bundle, Mapping):
        raise StrictPublisherError("bundle_type")
    if bundle.get("schema") != "convmem.strict-fixture-bundle.v2":
        raise StrictPublisherError("bundle_schema")
    if set(bundle) != {
        "schema",
        "lineage_id",
        "operation_id",
        "expected_parent_manifest_sha256",
        "batches",
        "dispositions",
        "provenance_context",
        "grounding",
        "built_at",
        "as_of",
        "expires_at",
        "fixture_payload_sha256",
    }:
        raise StrictPublisherError("bundle_keys")
    if bundle["lineage_id"] != lineage_id:
        raise StrictPublisherError("bundle_lineage")
    input_sha256 = _self_hash(bundle, "fixture_payload_sha256")
    if bundle["fixture_payload_sha256"] != input_sha256:
        raise StrictPublisherError("bundle_hash")
    operation_id = bundle["operation_id"]
    if not isinstance(operation_id, str) or len(operation_id) != 32:
        raise StrictPublisherError("operation_id")

    # Exact operation retry: same bytes → historic outcome + current head.
    historic = _find_operation_outcome(
        root, operation_id=operation_id, input_sha256=input_sha256
    )
    if historic is not None:
        # Detect conflicting bytes under same operation via input mismatch path:
        # if history has this operation_id with different input, reject.
        for path in sorted((root / "active" / "history").glob("*.json")):
            pub = _read_json(path)
            snap = pub.get("authority_snapshot_id")
            if not isinstance(snap, str):
                continue
            input_path = root / "authority" / snap / "input.json"
            if not input_path.is_file():
                continue
            prior_input = _read_json(input_path)
            if prior_input.get("operation_id") != operation_id:
                continue
            prior_hash = prior_input.get("fixture_payload_sha256")
            if prior_hash != input_sha256:
                raise StrictPublisherError("operation_bytes_conflict")
        # Idempotent: report historic meaning with unchanged current head.
        return {
            "outcome": "exact_retry",
            "historic_publication_payload_sha256": historic["publication_payload_sha256"],
            "current_publication": current,
            "current_publication_payload_sha256": current["publication_payload_sha256"],
        }

    # Parent-head rules: expected parent must match current authority head.
    expected_parent = bundle["expected_parent_manifest_sha256"]
    parent_grounding: dict[str, Any] | None = None
    parent_context: dict[str, Any] | None = None
    candidate_batches = bundle["batches"]
    if not isinstance(candidate_batches, list):
        raise StrictPublisherError("batches_type")
    if current["authority_seq"] == 0:
        if expected_parent is not None:
            raise StrictPublisherError("parent_head_mismatch")
        parent_snapshot_id = None
        parent_manifest_sha256 = None
        parent_records: list[dict[str, Any]] = []
        parent_dispositions: list[dict[str, Any]] = []
        parent_cutoff = _empty_source_cutoff(lineage_id=lineage_id)
        prior_batches: list[Any] = []
        next_seq = 1
    else:
        if expected_parent != current["authority_manifest_sha256"]:
            raise StrictPublisherError("parent_head_mismatch")
        parent_snapshot_id = current["authority_snapshot_id"]
        parent_manifest_sha256 = current["authority_manifest_sha256"]
        if not isinstance(parent_snapshot_id, str):
            raise StrictPublisherError("parent_snapshot_missing")
        parent_dir = root / "authority" / parent_snapshot_id
        parent_records = _read_jsonl(parent_dir / "records.jsonl")
        parent_dispositions = _read_jsonl(parent_dir / "dispositions.jsonl")
        parent_cutoff = _read_json(parent_dir / "source-cutoff.json")
        parent_grounding = _read_json(parent_dir / "grounding.json")
        parent_context = _read_json(parent_dir / "provenance-context.json")
        parent_input = _read_json(parent_dir / "input.json")
        prior_batches_raw = parent_input.get("batches")
        if not isinstance(prior_batches_raw, list):
            raise StrictPublisherError("parent_batches")
        prior_batches = list(prior_batches_raw)
        next_seq = int(current["authority_seq"]) + 1

    # §6.5.5: admitted fixture batches are cumulative; later bundles must carry
    # the prior committed batches as an exact canonical prefix.
    if len(candidate_batches) < len(prior_batches):
        raise StrictPublisherError("batches_not_prefix")
    if strict_canonical_bytes(list(candidate_batches[: len(prior_batches)])) != (
        strict_canonical_bytes(prior_batches)
    ):
        raise StrictPublisherError("batches_not_prefix")

    if current["authority_seq"] != 0:
        try:
            qualify_authority_generation(
                root=root,
                scope=scope,
                registry=registry,
                expected_publication_sha256=current["publication_payload_sha256"],
                require_serving=False,
            )
        except StrictProjectionError as exc:
            raise StrictPublisherError(f"parent_cold_qualify:{exc}") from exc

    # Validate candidate vs parent before any fence/history mutation.
    provenance_context = dict(bundle["provenance_context"])
    grounding = dict(bundle["grounding"])
    if grounding.get("schema") != "convmem.strict-grounding.v1":
        raise StrictPublisherError("grounding_schema")
    g_hash = _self_hash(grounding, "grounding_payload_sha256")
    if grounding["grounding_payload_sha256"] != g_hash:
        raise StrictPublisherError("grounding_hash")
    try:
        provenance_context = validate_provenance_context(
            provenance_context, expected_grounding_sha256=g_hash
        )
        assert_cumulative_grounding(parent_grounding, grounding)
        assert_cumulative_provenance_context(parent_context, provenance_context)
    except StrictGroundingError as exc:
        raise StrictPublisherError(f"provenance_context:{exc}") from exc

    registered: dict[str, Any] = {}
    for entry in provenance_context["registered_assertions"]:
        aid = entry["assertion_id"]
        if aid in registered:
            raise StrictPublisherError("registered_assertion_duplicate")
        registered[aid] = entry

    issuer_inventory = None
    if registered:
        try:
            issuer_inventory = load_bound_issuer_inventories(binding.capture_issuers)
        except StrictGroundingError as exc:
            raise StrictPublisherError(f"issuer_inventory:{exc}") from exc

    originals: dict[str, dict[str, str]] = {}
    for rec in parent_records:
        env = rec.get("provenance_envelope")
        pq = rec.get("provenance_qualification")
        if isinstance(env, Mapping) and isinstance(pq, Mapping):
            pid = env.get("assertion_id")
            if isinstance(pid, str) and pid:
                originals[pid] = {
                    "commitments": str(pq["commitments"]),
                    "byte_grounding": str(pq["byte_grounding"]),
                    "capture": str(pq["capture"]),
                    "transformer_cap": str(pq["transformer_cap"]),
                }

    try:
        qual_map = qualify_assertions(
            grounding=grounding,
            provenance_context=provenance_context,
            issuer_inventory=issuer_inventory,
            capture_issuers=binding.capture_issuers,
            allowed_issuer_ids={i.issuer_id for i in binding.capture_issuers},
            allowed_source_registration_ids={
                r.id for r in binding.source_registrations
            },
            original_qualifications=originals or None,
        )
        for _aid, shared in qual_map.items():
            if not isinstance(shared, QualificationTuple):
                raise StrictPublisherError("qualification_type")
    except StrictGroundingError as exc:
        raise StrictPublisherError(f"grounding:{exc}") from exc

    added_records: list[dict[str, Any]] = []
    # Cumulative batches: only materialize the suffix beyond the prior prefix.
    delta_batches = list(candidate_batches[len(prior_batches) :])
    for batch in delta_batches:
        if not isinstance(batch, Mapping):
            raise StrictPublisherError("batch_type")
        try:
            new_recs = materialize_authority_records(
                binding=binding,
                source_registration_id=batch["source_registration_id"],
                scan=batch["source"],
                registered_assertions=registered,
                qualification_by_provenance=qual_map,
                prior_records=parent_records + added_records,
            )
        except StrictEvidenceError as exc:
            raise StrictPublisherError(f"materialize:{exc}") from exc
        added_records.extend(new_recs)

    parent_ids = {r["assertion_id"] for r in parent_records}
    parent_disp_map = {disposition_id(d): d for d in parent_dispositions}
    parent_heads = _parent_heads_by_logical(parent_records, parent_disp_map)
    staging_records = list(parent_records) + [dict(r) for r in added_records]
    try:
        new_disp_map = validate_dispositions(
            list(bundle["dispositions"]),
            records=staging_records,
            parent_snapshot_id=parent_snapshot_id,
            parent_heads_by_logical=parent_heads if parent_heads else None,
        )
    except StrictEvidenceError as exc:
        raise StrictPublisherError(f"dispositions:{exc}") from exc

    from strict_evidence_state import payload_sha256, semantic_sha256

    added_by_id = {r["assertion_id"]: dict(r) for r in added_records}
    for disp_id, disp in new_disp_map.items():
        subject = disp["subject_assertion_id"]
        action = disp["action"]
        if subject in parent_ids:
            continue  # dispositions affect parent only via reducer
        if subject not in added_by_id:
            raise StrictPublisherError("disposition_subject_unknown")
        rec = added_by_id[subject]
        if action in {"decision_approved", "decision_rejected"}:
            rec["decision_disposition_ref"] = disp_id
        elif action == "supersession_authorized":
            rec["supersession_disposition_ref"] = disp_id
            rec["supersedes_assertion_ids"] = sorted(set(disp["target_assertion_ids"]))
        added_by_id[subject] = rec
    for rec in added_by_id.values():
        rec["semantic_sha256"] = semantic_sha256(rec)
        rec["payload_sha256"] = payload_sha256(rec)
    added_records = list(added_by_id.values())
    all_records = sorted(
        list(parent_records) + added_records, key=lambda r: r["assertion_id"]
    )
    if len({r["assertion_id"] for r in all_records}) != len(all_records):
        raise StrictPublisherError("record_id_collision")

    all_dispositions = list(parent_dispositions) + [
        new_disp_map[k] for k in sorted(new_disp_map)
    ]
    all_dispositions.sort(key=lambda d: disposition_id(d))
    disp_map = {disposition_id(d): d for d in all_dispositions}

    operations = list(parent_cutoff.get("operations", []))
    if operation_id in {op["operation_id"] for op in operations}:
        raise StrictPublisherError("operation_id_duplicate")
    # §6.5.5: source_prefix_sha256 digests the current cumulative batches array.
    source_prefix = sha256_digest(strict_canonical_bytes(candidate_batches))
    operations.append(
        {
            "operation_id": operation_id,
            "input_sha256": input_sha256,
            "source_prefix_sha256": source_prefix,
        }
    )
    new_cutoff = {
        "schema": "convmem.strict-source-cutoff.v1",
        "lineage_id": lineage_id,
        "mode": "fixture",
        "operations": operations,
        "cutoff_payload_sha256": "sha256:" + ("0" * 64),
    }
    _set_self_hash(new_cutoff, "cutoff_payload_sha256")

    try:
        citation_map = build_citation_map(all_records)
        added_provenance_ids = compute_added_provenance_ids(
            parent_context, provenance_context
        )
        added_grounding_refs = compute_added_grounding_refs(parent_grounding, grounding)
    except (StrictEvidenceError, StrictGroundingError) as exc:
        raise StrictPublisherError(f"citation_or_delta:{exc}") from exc

    records_digest = _jsonl_sha256(all_records)
    dispositions_digest = _jsonl_sha256(all_dispositions)
    builder_tree = _builder_tree_sha256()
    manifest = {
        "schema": "convmem.bound-authority-manifest.v3",
        "lineage_id": lineage_id,
        "authority_seq": next_seq,
        "owner_digest": owner,
        "snapshot_id": "pending",
        "parent_snapshot_id": parent_snapshot_id,
        "parent_manifest_sha256": parent_manifest_sha256,
        "scope_sha256": scope.scope_sha256,
        "registry_sha256": registry.registry_sha256,
        "input_sha256": input_sha256,
        "source_cutoff_sha256": new_cutoff["cutoff_payload_sha256"],
        "operation_id": operation_id,
        "authority_records_sha256": records_digest,
        "record_count": len(all_records),
        "dispositions_sha256": dispositions_digest,
        "disposition_count": len(all_dispositions),
        "citation_map_sha256": citation_map["citation_map_payload_sha256"],
        "provenance_context_sha256": provenance_context["context_payload_sha256"],
        "grounding_sha256": g_hash,
        "added_assertion_ids": sorted(r["assertion_id"] for r in added_records),
        "added_disposition_ids": sorted(new_disp_map),
        "added_provenance_ids": added_provenance_ids,
        "added_grounding_refs": added_grounding_refs,
        "semantic_contract_sha256": sc_hash,
        "reducer_version": semantic_contract["reducer_version"],
        "canonicalization_version": semantic_contract["canonicalization_version"],
        "builder_version": BUILDER_VERSION,
        "builder_tree_sha256": builder_tree,
        "built_at": bundle["built_at"],
        "as_of": bundle["as_of"],
        "expires_at": bundle["expires_at"],
        "manifest_payload_sha256": "sha256:" + ("0" * 64),
    }
    snapshot_id = _authority_snapshot_id(manifest)
    manifest["snapshot_id"] = snapshot_id
    _set_self_hash(manifest, "manifest_payload_sha256")
    if _authority_snapshot_id(manifest) != snapshot_id:
        raise StrictPublisherError("snapshot_id_unstable")

    # 1–2. Fence after parent cold-qualify + cumulative/delta proof.
    fenced = {
        "schema": "convmem.strict-publication.v2",
        "lineage_id": lineage_id,
        "owner_digest": owner,
        "epoch": int(current["epoch"]) + 1,
        "authority_seq": current["authority_seq"],
        "authority_snapshot_id": current["authority_snapshot_id"],
        "authority_manifest_sha256": current["authority_manifest_sha256"],
        "authority_source_cutoff_sha256": current["authority_source_cutoff_sha256"],
        "serving_generation_id": None,
        "projection_manifest_sha256": None,
        "semantic_contract_sha256": sc_hash,
        "pending_operation_id": operation_id,
        "mode": "fenced",
        "previous_publication_sha256": current["publication_payload_sha256"],
        "freshness_anchor": current["freshness_anchor"],
        "published_at": bundle["built_at"],
        "publication_payload_sha256": "sha256:" + ("0" * 64),
    }
    _fault("before_fence_fsync")
    fence_digest = _commit_publication(root, fenced, rename_tag="fence")
    _fault("after_fence")
    fenced["publication_payload_sha256"] = fence_digest

    # 3. Persist immutable authority files for the already-validated candidate.
    try:
        auth_dir = root / "authority" / snapshot_id
        if auth_dir.exists():
            raise StrictPublisherError("authority_dir_exists")
        auth_dir.mkdir(parents=True, exist_ok=True)

        _fault("before_authority_fsync")
        _write_json_atomic(auth_dir / "input.json", bundle)
        _write_json_atomic(auth_dir / "source-cutoff.json", new_cutoff)
        _write_jsonl_atomic(
            auth_dir / "records.jsonl",
            all_records,
            before_file_fsync="before_authority_records_fsync",
            after_file_fsync="after_authority_records_fsync",
        )
        _write_jsonl_atomic(auth_dir / "dispositions.jsonl", all_dispositions)
        _write_json_atomic(auth_dir / "citation-map.json", citation_map)
        _write_json_atomic(auth_dir / "provenance-context.json", provenance_context)
        _write_json_atomic(auth_dir / "grounding.json", grounding)
        _write_json_atomic(
            auth_dir / "manifest.json",
            manifest,
            before_file_fsync="before_authority_manifest_fsync",
            after_file_fsync="after_authority_manifest_fsync",
        )
        _fsync_dir(auth_dir)
        _fault("after_authority_fsync")

        # Cold qualify authority (fixture in-process; production: fresh interpreter).
        # Publish unavailable head first so qualifier sees admitted authority.
        unavailable: dict[str, Any] = {
            "schema": "convmem.strict-publication.v2",
            "lineage_id": lineage_id,
            "owner_digest": owner,
            "epoch": int(fenced["epoch"]) + 1,
            "authority_seq": next_seq,
            "authority_snapshot_id": snapshot_id,
            "authority_manifest_sha256": manifest["manifest_payload_sha256"],
            "authority_source_cutoff_sha256": new_cutoff["cutoff_payload_sha256"],
            "serving_generation_id": None,
            "projection_manifest_sha256": None,
            "semantic_contract_sha256": sc_hash,
            "pending_operation_id": None,
            "mode": "unavailable",
            "previous_publication_sha256": fence_digest,
            "freshness_anchor": None,  # filled below
            "published_at": bundle["built_at"],
            "publication_payload_sha256": "sha256:" + ("0" * 64),
        }
        # Persist clock review + freshness for this head (unchanged on rollback).
        clock = {
            "schema": "convmem.clock-review.v1",
            "lineage_id": lineage_id,
            "authority_snapshot_id": snapshot_id,
            "boot_id": "fixture-boot",
            "expires_at": bundle["expires_at"],
            "reviewed_wall_time": bundle["built_at"],
            "reviewer_uid": enrollment["operator_uid"],
            "review_payload_sha256": "sha256:" + ("0" * 64),
        }
        _set_self_hash(clock, "review_payload_sha256")
        clock_ref = "clock:" + clock["review_payload_sha256"].removeprefix("sha256:")
        _write_json_atomic(
            root / "control" / "clock" / f"{clock['review_payload_sha256'].removeprefix('sha256:')}.json",
            clock,
        )
        anchor = _freshness_anchor_for(
            snapshot_id=snapshot_id,
            boot_id="fixture-boot",
            sampled_wall_time=bundle["built_at"],
            sampled_boottime_ns=0,
            snapshot_deadline_boottime_ns=10_000_000_000,
            clock_review_ref=clock_ref,
        )
        unavailable["freshness_anchor"] = anchor
        unavail_digest = _commit_publication(root, unavailable, rename_tag="unavailable")
        unavailable["publication_payload_sha256"] = unavail_digest
        _fault("after_authority_unavailable")

        # Fresh cold qualification of unavailable head.
        try:
            qualify_authority_generation(
                root=root,
                scope=scope,
                registry=registry,
                expected_publication_sha256=unavail_digest,
                require_serving=False,
            )
        except StrictProjectionError as exc:
            raise StrictPublisherError(f"cold_qualify:{exc}") from exc

        # 5. Cold build projection for SAME head.
        reduced = reduce_complete_bound_state(all_records, disp_map)
        selectors = EffectiveSelectors(
            project=scope.project,
            site=scope.site,
            site_mode=scope.site_mode,
            domain=scope.domain,
            binding_id=binding_id,
        )
        for rec in all_records:
            try:
                authorize_row(
                    scope=scope,
                    registry=registry,
                    selectors=selectors,
                    project_binding_id=rec["project_binding_id"],
                    source_registration_id=rec["source_registration_id"],
                    authority_site=rec["authority_site"],
                    authority_domain=rec["authority_domain"],
                )
            except BoundScopeError as exc:
                raise StrictPublisherError(f"authorization:{exc}") from exc

        rows, graph = _build_rows_and_graph(
            records=all_records,
            reduced=reduced,
            lineage_id=lineage_id,
            authority_seq=next_seq,
            authority_manifest_sha256=manifest["manifest_payload_sha256"],
            semantic_contract_sha256=sc_hash,
            binding_public_ref=binding.public_ref,
        )
        rows_digest = _jsonl_sha256(rows)
        prev_gen = current.get("serving_generation_id")
        proj_manifest: dict[str, Any] = {
            "schema": "convmem.bound-projection-manifest.v3",
            "lineage_id": lineage_id,
            "authority_seq": next_seq,
            "owner_digest": owner,
            "generation_id": "pending",
            "previous_generation_id": prev_gen,
            "snapshot_id": snapshot_id,
            "authority_manifest_sha256": manifest["manifest_payload_sha256"],
            "scope_sha256": scope.scope_sha256,
            "registry_sha256": registry.registry_sha256,
            "semantic_contract_sha256": sc_hash,
            "rows_sha256": rows_digest,
            "row_count": len(rows),
            "graph_sha256": graph["graph_payload_sha256"],
            "graph_node_count": len(graph["nodes"]),
            "search_kernel": semantic_contract["search_kernel"],
            "search_kernel_version": semantic_contract["search_kernel_version"],
            "tokenizer_unicode_version": semantic_contract["tokenizer_unicode_version"],
            "builder_version": BUILDER_VERSION,
            "builder_tree_sha256": builder_tree,
            "built_at": bundle["built_at"],
            "as_of": bundle["as_of"],
            "expires_at": bundle["expires_at"],
            "manifest_payload_sha256": "sha256:" + ("0" * 64),
        }
        generation_id = _projection_generation_id(proj_manifest)
        proj_manifest["generation_id"] = generation_id
        _set_self_hash(proj_manifest, "manifest_payload_sha256")
        if _projection_generation_id(proj_manifest) != generation_id:
            raise StrictPublisherError("generation_id_unstable")

        gen_dir = root / "projection" / generation_id
        if gen_dir.exists():
            raise StrictPublisherError("projection_dir_exists")
        gen_dir.mkdir(parents=True, exist_ok=True)
        _fault("before_projection_fsync")
        _write_jsonl_atomic(gen_dir / "rows.jsonl", rows)
        _write_json_atomic(gen_dir / "graph.json", graph)
        _write_json_atomic(
            gen_dir / "manifest.json",
            proj_manifest,
            before_file_fsync="before_projection_manifest_fsync",
            after_file_fsync="after_projection_manifest_fsync",
        )
        _fsync_dir(gen_dir)
        _fault("after_projection_fsync")

        # 6. Recheck CAS under lock; publish serving for SAME head (retain anchor).
        recheck = _current_publication(root, lineage_id)
        if recheck["publication_payload_sha256"] != unavail_digest:
            raise StrictPublisherError("publication_changed_under_lock")
        serving: dict[str, Any] = {
            "schema": "convmem.strict-publication.v2",
            "lineage_id": lineage_id,
            "owner_digest": owner,
            "epoch": int(unavailable["epoch"]) + 1,
            "authority_seq": next_seq,
            "authority_snapshot_id": snapshot_id,
            "authority_manifest_sha256": manifest["manifest_payload_sha256"],
            "authority_source_cutoff_sha256": new_cutoff["cutoff_payload_sha256"],
            "serving_generation_id": generation_id,
            "projection_manifest_sha256": proj_manifest["manifest_payload_sha256"],
            "semantic_contract_sha256": sc_hash,
            "pending_operation_id": None,
            "mode": "serving",
            "previous_publication_sha256": unavail_digest,
            "freshness_anchor": anchor,
            "published_at": bundle["built_at"],
            "publication_payload_sha256": "sha256:" + ("0" * 64),
        }
        serving_digest = _commit_publication(root, serving, rename_tag="serving")
        serving["publication_payload_sha256"] = serving_digest

        # Cold qualify serving.
        try:
            qualify_authority_generation(
                root=root,
                scope=scope,
                registry=registry,
                expected_publication_sha256=serving_digest,
                require_serving=True,
            )
        except StrictProjectionError as exc:
            raise StrictPublisherError(f"cold_qualify_serving:{exc}") from exc

        return serving

    except Exception:
        # Leave durable fence/unavailable for recovery; do not claim serving.
        raise


def _rebuild_serving(
    *,
    root: Path,
    scope: Any,
    registry: Any,
    enrollment: Mapping[str, Any],
    semantic_contract: Mapping[str, Any],
    current: Mapping[str, Any],
    owner: str,
    sc_hash: str,
    binding: Any,
) -> dict[str, Any]:
    """Rebuild projection from exact current authority; never admit new source."""
    if current["authority_seq"] == 0 or current["authority_snapshot_id"] is None:
        raise StrictPublisherError("rebuild_requires_authority")
    if current["mode"] == "fenced":
        raise StrictPublisherError("rebuild_while_fenced")
    snapshot_id = current["authority_snapshot_id"]
    auth_dir = root / "authority" / snapshot_id
    manifest = _read_json(auth_dir / "manifest.json")
    records = _read_jsonl(auth_dir / "records.jsonl")
    dispositions = _read_jsonl(auth_dir / "dispositions.jsonl")
    disp_map = {disposition_id(d): d for d in dispositions}
    reduced = reduce_complete_bound_state(records, disp_map)
    rows, graph = _build_rows_and_graph(
        records=records,
        reduced=reduced,
        lineage_id=enrollment["lineage_id"],
        authority_seq=int(current["authority_seq"]),
        authority_manifest_sha256=str(current["authority_manifest_sha256"]),
        semantic_contract_sha256=sc_hash,
        binding_public_ref=binding.public_ref,
    )
    builder_tree = _builder_tree_sha256()
    proj_manifest: dict[str, Any] = {
        "schema": "convmem.bound-projection-manifest.v3",
        "lineage_id": enrollment["lineage_id"],
        "authority_seq": int(current["authority_seq"]),
        "owner_digest": owner,
        "generation_id": "pending",
        "previous_generation_id": current.get("serving_generation_id"),
        "snapshot_id": snapshot_id,
        "authority_manifest_sha256": current["authority_manifest_sha256"],
        "scope_sha256": scope.scope_sha256,
        "registry_sha256": registry.registry_sha256,
        "semantic_contract_sha256": sc_hash,
        "rows_sha256": _jsonl_sha256(rows),
        "row_count": len(rows),
        "graph_sha256": graph["graph_payload_sha256"],
        "graph_node_count": len(graph["nodes"]),
        "search_kernel": semantic_contract["search_kernel"],
        "search_kernel_version": semantic_contract["search_kernel_version"],
        "tokenizer_unicode_version": semantic_contract["tokenizer_unicode_version"],
        "builder_version": BUILDER_VERSION,
        "builder_tree_sha256": builder_tree,
        "built_at": manifest["built_at"],
        "as_of": manifest["as_of"],
        "expires_at": manifest["expires_at"],  # never renew
        "manifest_payload_sha256": "sha256:" + ("0" * 64),
    }
    generation_id = _projection_generation_id(proj_manifest)
    proj_manifest["generation_id"] = generation_id
    _set_self_hash(proj_manifest, "manifest_payload_sha256")
    gen_dir = root / "projection" / generation_id
    gen_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl_atomic(gen_dir / "rows.jsonl", rows)
    _write_json_atomic(gen_dir / "graph.json", graph)
    _write_json_atomic(gen_dir / "manifest.json", proj_manifest)

    serving: dict[str, Any] = {
        "schema": "convmem.strict-publication.v2",
        "lineage_id": enrollment["lineage_id"],
        "owner_digest": owner,
        "epoch": int(current["epoch"]) + 1,
        "authority_seq": current["authority_seq"],
        "authority_snapshot_id": snapshot_id,
        "authority_manifest_sha256": current["authority_manifest_sha256"],
        "authority_source_cutoff_sha256": current["authority_source_cutoff_sha256"],
        "serving_generation_id": generation_id,
        "projection_manifest_sha256": proj_manifest["manifest_payload_sha256"],
        "semantic_contract_sha256": sc_hash,
        "pending_operation_id": None,
        "mode": "serving",
        "previous_publication_sha256": current["publication_payload_sha256"],
        "freshness_anchor": current["freshness_anchor"],  # retain; no renewal
        "published_at": manifest["built_at"],
        "publication_payload_sha256": "sha256:" + ("0" * 64),
    }
    digest = _commit_publication(root, serving, rename_tag="rebuild")
    serving["publication_payload_sha256"] = digest
    return serving


def _rollback_serving(
    *,
    root: Path,
    scope: Any,
    registry: Any,
    enrollment: Mapping[str, Any],
    semantic_contract: Mapping[str, Any],
    current: Mapping[str, Any],
    target_generation_id: str | None,
    owner: str,
    sc_hash: str,
) -> dict[str, Any]:
    """Select retained generation of EXACT current authority; no expiry renewal."""
    if target_generation_id is None:
        raise StrictPublisherError("target_generation_required")
    if not target_generation_id.startswith("gen2_"):
        raise StrictPublisherError("target_generation_id")
    if current["authority_seq"] == 0 or current["authority_manifest_sha256"] is None:
        raise StrictPublisherError("rollback_requires_authority")
    if current["mode"] == "fenced":
        raise StrictPublisherError("rollback_while_fenced")

    gen_dir = root / "projection" / target_generation_id
    if not gen_dir.is_dir():
        raise StrictPublisherError("target_generation_missing")
    proj_manifest = _read_json(gen_dir / "manifest.json")
    if proj_manifest["authority_manifest_sha256"] != current["authority_manifest_sha256"]:
        raise StrictPublisherError("rollback_wrong_authority")
    if proj_manifest["semantic_contract_sha256"] != sc_hash:
        raise StrictPublisherError("rollback_wrong_contract")
    if proj_manifest["snapshot_id"] != current["authority_snapshot_id"]:
        raise StrictPublisherError("rollback_wrong_snapshot")
    # expires_at must equal current authority expiry (no renewal).
    auth_manifest = _read_json(
        root / "authority" / str(current["authority_snapshot_id"]) / "manifest.json"
    )
    if proj_manifest["expires_at"] != auth_manifest["expires_at"]:
        raise StrictPublisherError("rollback_expiry_mismatch")
    if proj_manifest["as_of"] != auth_manifest["as_of"]:
        raise StrictPublisherError("rollback_as_of_mismatch")

    # Cold qualify target generation files against current authority.
    try:
        qualify_authority_generation(
            root=root,
            scope=scope,
            registry=registry,
            expected_publication_sha256=current["publication_payload_sha256"],
            require_serving=False,
        )
    except StrictProjectionError as exc:
        raise StrictPublisherError(f"rollback_qualify:{exc}") from exc

    serving: dict[str, Any] = {
        "schema": "convmem.strict-publication.v2",
        "lineage_id": enrollment["lineage_id"],
        "owner_digest": owner,
        "epoch": int(current["epoch"]) + 1,
        "authority_seq": current["authority_seq"],
        "authority_snapshot_id": current["authority_snapshot_id"],
        "authority_manifest_sha256": current["authority_manifest_sha256"],
        "authority_source_cutoff_sha256": current["authority_source_cutoff_sha256"],
        "serving_generation_id": target_generation_id,
        "projection_manifest_sha256": proj_manifest["manifest_payload_sha256"],
        "semantic_contract_sha256": sc_hash,
        "pending_operation_id": None,
        "mode": "serving",
        "previous_publication_sha256": current["publication_payload_sha256"],
        "freshness_anchor": current["freshness_anchor"],
        "published_at": auth_manifest["built_at"],
        "publication_payload_sha256": "sha256:" + ("0" * 64),
    }
    digest = _commit_publication(root, serving, rename_tag="rollback")
    serving["publication_payload_sha256"] = digest
    return serving


def rebuild_projection(
    *,
    scope_path: str | Path,
    registry_path: str | Path,
    strict_config_path: str | Path,
    expected_publication_sha256: str,
    retirement_proof: Mapping[str, Any] | None = None,
    empty_domain_proof: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return publish_projection(
        scope_path=scope_path,
        registry_path=registry_path,
        strict_config_path=strict_config_path,
        expected_publication_sha256=expected_publication_sha256,
        retirement_proof=retirement_proof,
        empty_domain_proof=empty_domain_proof,
        admit_source=False,
        rebuild=True,
    )


def rollback_projection(
    *,
    scope_path: str | Path,
    registry_path: str | Path,
    strict_config_path: str | Path,
    expected_publication_sha256: str,
    target_generation: str,
    retirement_proof: Mapping[str, Any] | None = None,
    empty_domain_proof: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return publish_projection(
        scope_path=scope_path,
        registry_path=registry_path,
        strict_config_path=strict_config_path,
        expected_publication_sha256=expected_publication_sha256,
        retirement_proof=retirement_proof,
        empty_domain_proof=empty_domain_proof,
        admit_source=False,
        rollback=True,
        target_generation_id=target_generation,
    )


def recover_projection(
    *,
    scope_path: str | Path,
    registry_path: str | Path,
    strict_config_path: str | Path,
    expected_publication_sha256: str,
) -> dict[str, Any]:
    """Recover: clear abandoned unratified fence only with no durable intent/admission.

    Ambiguity → unavailable/quarantine. Never rolls back authority or admits source.
    """
    root, scope, registry, enrollment, semantic_contract, _config = _load_root_context(
        scope_path=scope_path,
        registry_path=registry_path,
        strict_config_path=strict_config_path,
    )
    lineage_id = enrollment["lineage_id"]
    slot_id = enrollment["slot_id"]
    with _held_publisher_locks(root, lineage_id=lineage_id, slot_id=slot_id):
        return _recover_projection_locked(
            root=root,
            scope=scope,
            registry=registry,
            enrollment=enrollment,
            semantic_contract=semantic_contract,
            expected_publication_sha256=expected_publication_sha256,
        )


def _recover_projection_locked(
    *,
    root: Path,
    scope: Any,
    registry: Any,
    enrollment: Mapping[str, Any],
    semantic_contract: Mapping[str, Any],
    expected_publication_sha256: str,
) -> dict[str, Any]:
    lineage_id = enrollment["lineage_id"]
    current = _current_publication(root, lineage_id)
    _require_cas(current, expected_publication_sha256)

    if current["mode"] == "fenced":
        pending = current.get("pending_operation_id")
        # Durable intent exists if authority dir for a newer seq appeared, or
        # input for pending operation was committed.
        durable_intent = False
        if isinstance(pending, str):
            for auth in sorted((root / "authority").glob("snap2_*")):
                input_path = auth / "input.json"
                if not input_path.is_file():
                    continue
                inp = _read_json(input_path)
                if inp.get("operation_id") == pending:
                    durable_intent = True
                    break
        if durable_intent:
            # Leave unavailable/quarantine; do not auto-serve.
            if current["authority_seq"] == 0:
                raise StrictPublisherError("recover_ambiguous_genesis_fence")
            unavailable = dict(current)
            unavailable["mode"] = "unavailable"
            unavailable["pending_operation_id"] = None
            unavailable["serving_generation_id"] = None
            unavailable["projection_manifest_sha256"] = None
            unavailable["epoch"] = int(current["epoch"]) + 1
            unavailable["previous_publication_sha256"] = current["publication_payload_sha256"]
            unavailable["publication_payload_sha256"] = "sha256:" + ("0" * 64)
            digest = _commit_publication(root, unavailable, rename_tag="recover_unavail")
            unavailable["publication_payload_sha256"] = digest
            return unavailable
        # Abandoned unratified fence: clear back to prior head via history.
        prev = current.get("previous_publication_sha256")
        if not isinstance(prev, str):
            raise StrictPublisherError("recover_missing_predecessor")
        prior_path = _history_path(root, prev)
        prior = _read_json(prior_path)
        restored = dict(prior)
        restored["epoch"] = int(current["epoch"]) + 1
        restored["previous_publication_sha256"] = current["publication_payload_sha256"]
        restored["publication_payload_sha256"] = "sha256:" + ("0" * 64)
        # Requalify same head with unchanged expiry (anchor retained from prior).
        digest = _commit_publication(root, restored, rename_tag="recover_clear_fence")
        restored["publication_payload_sha256"] = digest
        try:
            qualify_authority_generation(
                root=root,
                scope=scope,
                registry=registry,
                expected_publication_sha256=digest,
                require_serving=restored.get("mode") == "serving",
            )
        except StrictProjectionError as exc:
            raise StrictPublisherError(f"recover_qualify:{exc}") from exc
        return restored

    if current["mode"] == "unavailable":
        # Requalify current head; do not invent serving.
        try:
            qualify_authority_generation(
                root=root,
                scope=scope,
                registry=registry,
                expected_publication_sha256=current["publication_payload_sha256"],
                require_serving=False,
            )
        except StrictProjectionError as exc:
            raise StrictPublisherError(f"recover_qualify:{exc}") from exc
        return dict(current)

    if current["mode"] == "serving":
        try:
            qualify_authority_generation(
                root=root,
                scope=scope,
                registry=registry,
                expected_publication_sha256=current["publication_payload_sha256"],
                require_serving=True,
            )
        except StrictProjectionError as exc:
            raise StrictPublisherError(f"recover_qualify:{exc}") from exc
        return dict(current)

    raise StrictPublisherError("recover_unknown_mode")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="strict_projection_publisher")
    sub = parser.add_subparsers(dest="command", required=True)

    p_enroll = sub.add_parser("enroll-fixture")
    p_enroll.add_argument("--enrollment", required=True)
    p_enroll.add_argument("--semantic-contract", required=True)
    p_enroll.add_argument("--strict-config", required=True)

    p_build = sub.add_parser("build-fixture")
    p_build.add_argument("--bundle", required=True)
    p_build.add_argument("--scope", required=True)
    p_build.add_argument("--registry", required=True)
    p_build.add_argument("--strict-config", required=True)
    p_build.add_argument("--expected-publication", required=True)

    p_rebuild = sub.add_parser("rebuild-fixture")
    p_rebuild.add_argument("--scope", required=True)
    p_rebuild.add_argument("--registry", required=True)
    p_rebuild.add_argument("--strict-config", required=True)
    p_rebuild.add_argument("--expected-publication", required=True)

    p_rollback = sub.add_parser("rollback-fixture")
    p_rollback.add_argument("--scope", required=True)
    p_rollback.add_argument("--registry", required=True)
    p_rollback.add_argument("--strict-config", required=True)
    p_rollback.add_argument("--expected-publication", required=True)
    p_rollback.add_argument("--target-generation", required=True)

    p_recover = sub.add_parser("recover-fixture")
    p_recover.add_argument("--scope", required=True)
    p_recover.add_argument("--registry", required=True)
    p_recover.add_argument("--strict-config", required=True)
    p_recover.add_argument("--expected-publication", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "enroll-fixture":
            result = enroll_fixture(
                enrollment_path=args.enrollment,
                semantic_contract_path=args.semantic_contract,
                strict_config_path=args.strict_config,
            )
        elif args.command == "build-fixture":
            result = publish_projection(
                bundle_path=args.bundle,
                scope_path=args.scope,
                registry_path=args.registry,
                strict_config_path=args.strict_config,
                expected_publication_sha256=args.expected_publication,
            )
        elif args.command == "rebuild-fixture":
            result = rebuild_projection(
                scope_path=args.scope,
                registry_path=args.registry,
                strict_config_path=args.strict_config,
                expected_publication_sha256=args.expected_publication,
            )
        elif args.command == "rollback-fixture":
            result = rollback_projection(
                scope_path=args.scope,
                registry_path=args.registry,
                strict_config_path=args.strict_config,
                expected_publication_sha256=args.expected_publication,
                target_generation=args.target_generation,
            )
        elif args.command == "recover-fixture":
            result = recover_projection(
                scope_path=args.scope,
                registry_path=args.registry,
                strict_config_path=args.strict_config,
                expected_publication_sha256=args.expected_publication,
            )
        else:
            raise StrictPublisherError("unknown_command")
    except (
        StrictPublisherError,
        StrictProjectionError,
        StrictEvidenceError,
        StrictGroundingError,
        BoundScopeError,
    ) as exc:
        print(f"error: {exc}", flush=True)
        return 1

    print(strict_canonical_bytes(result).decode("utf-8"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
