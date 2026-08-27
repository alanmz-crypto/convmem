# pylint: disable=too-many-lines
"""Shadow Phase 0 activation/rollback transaction (C5, disabled by default).

This module owns the durable state machine.  It never changes Chroma and never
starts or stops services.  Operators suspend/resume the census-listed services;
the module verifies their state, holds the exclusive C3 writer gate through the
baseline and config-last commit, and compensates by disabling Shadow only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

from chroma_readonly import collection_metadata_rows, collection_uuid
from chroma_write_store import (
    WRITER_GATE_PROTOCOL_VERSION,
    current_code_revision,
    exclusive_writer_lease,
    list_pids_with_open_path,
    load_attestation,
)
from config import (
    SUPPORTED_SHADOW_CONFIG_FILESYSTEMS,
    ShadowConfigUpdateRefused,
    atomic_shadow_config_update,
    load_config,
    render_shadow_config_update,
)
from shadow_authorization import (
    AuthorizationRefused,
    NonceStore,
    ValidatedAuthorization,
    ensure_private_directory,
    load_authorization_payload,
    load_private_json,
    open_directory_nofollow,
    secure_atomic_write_json,
    validate_authorization_token,
)
from shadow_ledger import (
    COLLECTION_KNOWLEDGE_UNITS,
    compute_ledger_header_hash,
    compute_manifest_canonical_hash,
    create_shadow_ledger_header,
    lexical_abspath,
    projection_state_hash,
    SecureLedgerRefused,
    sha256_canonical,
)
from shadow_validation import (
    ValidationMode,
    build_valid_manifest_fixture,
    validate_shadow_activation,
)

FIRST_EVENT_TIMEOUT_SECONDS = 300
QUIESCE_TIMEOUT_SECONDS = 30
BASELINE_DERIVATION = "sorted_entity_state_sha256_v1"
MANIFEST_DERIVATION = "canonical_manifest_without_self_hash_v1"


class ActivationState(str, Enum):
    DISABLED = "disabled"
    PREPARING = "preparing"
    QUIESCED = "quiesced"
    BASELINE_CAPTURED = "baseline_captured"
    ARTIFACTS_VALIDATED = "artifacts_validated"
    PREPARED_NOT_COMMITTED = "prepared_not_committed"
    COMMITTED = "committed"
    FIRST_EVENT_OBSERVED = "first_event_observed"
    VERIFIED = "verified"
    ABORTED_PRECOMMIT = "aborted_precommit"
    ROLLBACK_PENDING = "rollback_pending"
    DISABLED_AFTER_ROLLBACK = "disabled_after_rollback"


ALLOWED_TRANSITIONS: Mapping[ActivationState, frozenset[ActivationState]] = {
    ActivationState.DISABLED: frozenset({ActivationState.PREPARING}),
    ActivationState.PREPARING: frozenset(
        {ActivationState.QUIESCED, ActivationState.ABORTED_PRECOMMIT}
    ),
    ActivationState.QUIESCED: frozenset(
        {ActivationState.BASELINE_CAPTURED, ActivationState.ABORTED_PRECOMMIT}
    ),
    ActivationState.BASELINE_CAPTURED: frozenset(
        {ActivationState.ARTIFACTS_VALIDATED, ActivationState.ABORTED_PRECOMMIT}
    ),
    ActivationState.ARTIFACTS_VALIDATED: frozenset(
        {
            ActivationState.COMMITTED,
            ActivationState.PREPARED_NOT_COMMITTED,
            ActivationState.ABORTED_PRECOMMIT,
        }
    ),
    ActivationState.PREPARED_NOT_COMMITTED: frozenset(
        {ActivationState.ABORTED_PRECOMMIT}
    ),
    ActivationState.COMMITTED: frozenset(
        {ActivationState.FIRST_EVENT_OBSERVED, ActivationState.ROLLBACK_PENDING}
    ),
    ActivationState.FIRST_EVENT_OBSERVED: frozenset(
        {ActivationState.VERIFIED, ActivationState.ROLLBACK_PENDING}
    ),
    ActivationState.ROLLBACK_PENDING: frozenset(
        {ActivationState.DISABLED_AFTER_ROLLBACK}
    ),
    ActivationState.VERIFIED: frozenset({ActivationState.ROLLBACK_PENDING}),
    ActivationState.ABORTED_PRECOMMIT: frozenset(),
    ActivationState.DISABLED_AFTER_ROLLBACK: frozenset(),
}


def assert_state_transition(current: str, target: str) -> None:
    """Reject state skips; repeated writes within one state are allowed."""
    try:
        current_state = ActivationState(current)
        target_state = ActivationState(target)
    except ValueError as exc:
        raise ActivationRefused("prepared_not_committed", "unknown activation state") from exc
    if current_state == target_state:
        return
    if target_state not in ALLOWED_TRANSITIONS[current_state]:
        raise ActivationRefused(
            "prepared_not_committed",
            f"invalid activation transition {current_state.value}->{target_state.value}",
        )


class ActivationRefused(RuntimeError):
    """A mechanical C5 refusal carrying a stable reason code."""

    def __init__(self, code: str, detail: str, *, state: str | None = None):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.state = state


@dataclass(frozen=True)
class BaselineSnapshot:
    collection_uuid: str
    entities: Mapping[str, Mapping[str, Any]]
    active_unit_count: int
    historical_unit_count: int
    total_unit_count: int
    aggregate_digest: str

    def canonical_identity(self) -> str:
        return sha256_canonical(
            {
                "collection_uuid": self.collection_uuid,
                "entities": self.entities,
                "active_unit_count": self.active_unit_count,
                "historical_unit_count": self.historical_unit_count,
                "total_unit_count": self.total_unit_count,
                "aggregate_digest": self.aggregate_digest,
            }
        )


@dataclass(frozen=True)
class ActivationLayout:  # pylint: disable=too-many-instance-attributes
    activation_id: str
    config_path: Path
    chroma_dir: Path
    shadow_dir: Path
    ledger_path: Path
    manifest_path: Path
    health_path: Path
    nonce_store_path: Path
    writer_lock_path: Path
    census_path: Path
    journal_path: Path
    staging_dir: Path


@dataclass(frozen=True)
class ActivationOutcome:
    activation_id: str
    state: str
    committed: bool
    refusal_code: str | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class ActivationHooks:  # pylint: disable=too-many-instance-attributes
    """Hermetic seams for time, host state, and crash fault injection."""

    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    monotonic: Callable[[], float] = time.monotonic
    sleep: Callable[[float], None] = time.sleep
    revision: Callable[[], str] = current_code_revision
    baseline: Callable[[Path], BaselineSnapshot] | None = None
    service_state: Callable[[str], str] | None = None
    process_pids: Callable[[Mapping[str, Any], Path], list[int]] | None = None
    checkpoint: Callable[[str], None] = lambda _name: None
    mountinfo: Callable[[], str] = lambda: Path("/proc/self/mountinfo").read_text(
        encoding="utf-8"
    )


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path(value: Any, *, field_name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ActivationRefused("authorization_mismatch", f"{field_name} missing")
    return lexical_abspath(value)


def _layout_from_payload(
    payload: Mapping[str, Any], *, config_path: Path, census_path: Path, nonce_store_path: Path, writer_lock_path: Path
) -> ActivationLayout:
    activation_id = str(payload.get("activation_id") or "").strip()
    if not activation_id:
        raise ActivationRefused("authorization_mismatch", "activation_id missing")
    shadow_dir = _path(payload.get("shadow_dir"), field_name="shadow_dir")
    return ActivationLayout(
        activation_id=activation_id,
        config_path=lexical_abspath(config_path),
        chroma_dir=Path(),
        shadow_dir=shadow_dir,
        ledger_path=_path(payload.get("ledger_path"), field_name="ledger_path"),
        manifest_path=_path(payload.get("manifest_path"), field_name="manifest_path"),
        health_path=_path(payload.get("health_path"), field_name="health_path"),
        nonce_store_path=lexical_abspath(nonce_store_path),
        writer_lock_path=lexical_abspath(writer_lock_path),
        census_path=lexical_abspath(census_path),
        journal_path=shadow_dir / f"activation-{activation_id}.journal.json",
        staging_dir=shadow_dir,
    )


def _bind_chroma(layout: ActivationLayout, chroma_dir: Path) -> ActivationLayout:
    return ActivationLayout(**{**layout.__dict__, "chroma_dir": lexical_abspath(chroma_dir)})


def _validate_layout(layout: ActivationLayout) -> None:
    if layout.shadow_dir.parent != layout.chroma_dir.parent or layout.shadow_dir == layout.chroma_dir:
        raise ActivationRefused(
            "authorization_mismatch", "shadow_dir must be a sibling outside Chroma"
        )
    artifacts = (layout.ledger_path, layout.manifest_path, layout.health_path)
    if any(path.parent != layout.shadow_dir for path in artifacts):
        raise ActivationRefused(
            "authorization_mismatch", "Shadow artifacts must be direct children of shadow_dir"
        )
    if len(set(artifacts)) != len(artifacts):
        raise ActivationRefused("authorization_mismatch", "Shadow artifact paths collide")
    if layout.nonce_store_path.parent != layout.shadow_dir:
        raise ActivationRefused(
            "authorization_mismatch", "nonce store must be inside shadow_dir"
        )
    if layout.writer_lock_path == layout.chroma_dir or layout.writer_lock_path in artifacts:
        raise ActivationRefused("authorization_mismatch", "writer lock path collides")
    try:
        chroma_fd = open_directory_nofollow(layout.chroma_dir)
    except AuthorizationRefused as exc:
        raise ActivationRefused(
            "collection_unavailable", "Chroma root is missing or contains a symlink"
        ) from exc
    os.close(chroma_fd)


def authorization_expectation(
    layout: ActivationLayout, *, code_revision: str
) -> dict[str, Any]:
    target_config = {
        "activation_id": layout.activation_id,
        "activation_manifest_path": str(layout.manifest_path),
        "enabled": True,
        "health_path": str(layout.health_path),
        "ledger_path": str(layout.ledger_path),
        "manifest_sha256": {"derive": MANIFEST_DERIVATION},
    }
    return {
        "activation_id": layout.activation_id,
        "allowed_filesystems": sorted(SUPPORTED_SHADOW_CONFIG_FILESYSTEMS),
        "baseline_derivation": BASELINE_DERIVATION,
        "census_path": str(layout.census_path),
        "code_revision": code_revision,
        "config_path": str(layout.config_path),
        "first_event_timeout_seconds": FIRST_EVENT_TIMEOUT_SECONDS,
        "health_path": str(layout.health_path),
        "ledger_path": str(layout.ledger_path),
        "manifest_derivation": MANIFEST_DERIVATION,
        "manifest_path": str(layout.manifest_path),
        "nonce_store_path": str(layout.nonce_store_path),
        "quiesce_timeout_seconds": QUIESCE_TIMEOUT_SECONDS,
        "shadow_dir": str(layout.shadow_dir),
        "target_config": target_config,
        "writer_lock_path": str(layout.writer_lock_path),
    }


def capture_baseline(chroma_dir: Path) -> BaselineSnapshot:
    """Capture the complete deterministic knowledge_units projection read-only."""
    coll_uuid = collection_uuid(chroma_dir, COLLECTION_KNOWLEDGE_UNITS)
    if not coll_uuid:
        raise ActivationRefused("collection_unavailable", "collection UUID unavailable")
    rows = collection_metadata_rows(chroma_dir, COLLECTION_KNOWLEDGE_UNITS)
    entities: dict[str, dict[str, Any]] = {}
    for raw in rows:
        entity_id = str(raw.get("id") or "").strip()
        if not entity_id or entity_id in entities:
            raise ActivationRefused("baseline_count_invalid", "baseline entity ID invalid")
        document = raw.get("document")
        metadata = {key: value for key, value in raw.items() if key not in {"id", "document"}}
        deleted = bool(metadata.get("deleted"))
        historical = deleted or bool(metadata.get("superseded"))
        entities[entity_id] = {
            "classification": "historical" if historical else "active",
            "document_hash": sha256_canonical(document),
            "metadata_hash": sha256_canonical(metadata),
            "state_hash": projection_state_hash(
                stable_entity_id=entity_id,
                deleted=deleted,
                document=document,
                metadata=metadata,
            ),
        }
    ordered = {entity_id: entities[entity_id] for entity_id in sorted(entities)}
    historical_count = sum(
        1 for value in ordered.values() if value["classification"] == "historical"
    )
    total = len(ordered)
    return BaselineSnapshot(
        collection_uuid=coll_uuid,
        entities=ordered,
        active_unit_count=total - historical_count,
        historical_unit_count=historical_count,
        total_unit_count=total,
        aggregate_digest=sha256_canonical(ordered),
    )


def _load_census(path: Path, *, revision: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ActivationRefused("census_missing", "writer census missing") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ActivationRefused("census_stale", "writer census unreadable") from exc
    if not isinstance(data, dict):
        raise ActivationRefused("census_stale", "writer census must be an object")
    if data.get("protocol_version") != WRITER_GATE_PROTOCOL_VERSION:
        raise ActivationRefused("census_stale", "writer census protocol mismatch")
    if data.get("code_revision") != revision:
        raise ActivationRefused("census_stale", "writer census revision mismatch")
    for key in ("systemd_units", "cmdline_signatures"):
        if not isinstance(data.get(key), list) or not all(
            isinstance(item, str) and item for item in data[key]
        ):
            raise ActivationRefused("census_stale", f"writer census {key} invalid")
    return data


def _default_service_state(unit: str) -> str:
    proc = subprocess.run(
        ["systemctl", "is-active", unit],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return proc.stdout.strip() or f"unknown:{proc.returncode}"


def _pid_start_time(pid: int) -> str | None:
    try:
        value = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        return value.rsplit(")", 1)[-1].split()[19]
    except (OSError, IndexError):
        return None


def _pid_executable(pid: int) -> str | None:
    try:
        return os.path.realpath(f"/proc/{pid}/exe")
    except OSError:
        return None


def _default_process_pids(census: Mapping[str, Any], chroma_dir: Path) -> list[int]:
    found = set(list_pids_with_open_path(chroma_dir))
    patterns = [re.compile(value) for value in census.get("cmdline_signatures", [])]
    for proc_dir in Path("/proc").iterdir():
        if not proc_dir.name.isdigit():
            continue
        pid = int(proc_dir.name)
        try:
            cmdline = (proc_dir / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except OSError:
            continue
        if any(pattern.search(cmdline) for pattern in patterns):
            found.add(pid)
    found.discard(os.getpid())
    return sorted(found)


def verify_quiescence(
    census: Mapping[str, Any],
    *,
    chroma_dir: Path,
    revision: str,
    attest_dir: Path,
    hooks: ActivationHooks,
) -> None:
    state_provider = hooks.service_state or _default_service_state
    for unit in census.get("systemd_units", []):
        try:
            state = state_provider(unit)
        except Exception as exc:
            raise ActivationRefused(
                "writer_quiesce_timeout", "writer service state unavailable"
            ) from exc
        if state not in {"inactive", "failed"}:
            raise ActivationRefused(
                "writer_quiesce_timeout", f"writer service is not suspended: {unit}"
            )

    pid_provider = hooks.process_pids or _default_process_pids
    for pid in pid_provider(census, chroma_dir):
        attestation = load_attestation(pid, attest_dir=attest_dir)
        actual_start = _pid_start_time(pid)
        actual_exe = _pid_executable(pid)
        if attestation is None or actual_start is None or actual_exe is None:
            raise ActivationRefused(
                "legacy_writer_process", "writer PID cannot be classified"
            )
        if (
            attestation.get("start_time") != actual_start
            or attestation.get("code_revision") != revision
            or attestation.get("protocol_version") != WRITER_GATE_PROTOCOL_VERSION
            or attestation.get("executable") != actual_exe
        ):
            raise ActivationRefused(
                "legacy_writer_process", "writer attestation mismatch"
            )


def _config_preimage(path: Path) -> tuple[bytes, str, dict[str, Any]]:
    try:
        data = path.read_bytes()
        cfg = load_config(path)
    except (OSError, ValueError) as exc:
        raise ActivationRefused("config_corrupt", "config cannot be loaded") from exc
    return data, hashlib.sha256(data).hexdigest(), cfg


def _journal_payload(
    layout: ActivationLayout,
    *,
    state: ActivationState,
    authorization: ValidatedAuthorization,
    revision: str,
    config_preimage_sha256: str,
    now: datetime,
    artifacts: Mapping[str, Any] | None = None,
    committed: bool = False,
) -> dict[str, Any]:
    return {
        "journal_version": 1,
        "activation_id": layout.activation_id,
        "state": state.value,
        "committed": committed,
        "owner_pid": os.getpid(),
        "owner_start_time": _pid_start_time(os.getpid()),
        "recorded_at_utc": _iso_utc(now),
        "code_revision": revision,
        "token_sha256": authorization.token_sha256,
        "nonce": authorization.nonce,
        "config_path": str(layout.config_path),
        "config_preimage_sha256": config_preimage_sha256,
        "shadow_dir": str(layout.shadow_dir),
        "staging_dir": str(layout.staging_dir),
        "ledger_path": str(layout.ledger_path),
        "manifest_path": str(layout.manifest_path),
        "health_path": str(layout.health_path),
        "artifacts": dict(artifacts or {}),
    }


def _write_journal(path: Path, payload: Mapping[str, Any], hooks: ActivationHooks) -> None:
    existing = path.exists() or path.is_symlink()
    if existing:
        try:
            st = os.lstat(path)
            if (
                not stat.S_ISREG(st.st_mode)
                or st.st_uid != os.geteuid()
                or stat.S_IMODE(st.st_mode) != 0o600
                or st.st_nlink != 1
            ):
                raise ActivationRefused(
                    "prepared_not_committed", "existing journal is not private"
                )
            previous = load_private_json(path)
            assert_state_transition(str(previous.get("state")), str(payload.get("state")))
        except (OSError, AuthorizationRefused) as exc:
            raise ActivationRefused(
                "prepared_not_committed", "existing journal is corrupt"
            ) from exc
    try:
        secure_atomic_write_json(path, payload, replace_existing=existing)
    except FileExistsError as exc:
        raise ActivationRefused(
            "prepared_not_committed", "journal appeared during publication"
        ) from exc
    hooks.checkpoint(str(payload.get("state")))


def _private_identity(path: Path) -> dict[str, int | str]:
    st = os.lstat(path)
    if not stat.S_ISREG(st.st_mode) or stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1:
        raise ActivationRefused("authorization_mismatch", "artifact privacy invalid")
    return {"path": str(path), "dev": st.st_dev, "ino": st.st_ino}


def _install_absent(source: Path, target: Path) -> dict[str, int | str]:
    if target.exists() or target.is_symlink():
        raise ActivationRefused("ledger_exists_unbound", "activation artifact already exists")
    if source.parent.stat().st_dev != target.parent.stat().st_dev:
        raise ActivationRefused("config_cross_device", "artifact install crossed devices")
    _private_identity(source)
    try:
        os.link(source, target, follow_symlinks=False)
    except FileExistsError as exc:
        raise ActivationRefused(
            "ledger_exists_unbound", "activation artifact appeared during install"
        ) from exc
    try:
        source.unlink()
    except OSError:
        try:
            target.unlink()
        except OSError:
            pass
        raise
    dir_fd = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return _private_identity(target)


def _build_manifest(
    *,
    layout: ActivationLayout,
    revision: str,
    baseline: BaselineSnapshot,
    ledger_identity: str,
    header_hash: str,
    configured_embed_model: str | None,
    now: datetime,
) -> dict[str, Any]:
    manifest = build_valid_manifest_fixture(
        activation_id=layout.activation_id,
        code_commit=revision,
        chroma_root=layout.chroma_dir,
        collection_uuid=baseline.collection_uuid,
        entity_baselines=baseline.entities,
        shadow_ledger_identity=ledger_identity,
        ledger_header_hash=header_hash,
        starting_sequence=0,
        configured_embed_model=configured_embed_model,
    )
    manifest["activation_timestamp_utc"] = _iso_utc(now)
    manifest.pop("manifest_canonical_hash", None)
    manifest["manifest_canonical_hash"] = compute_manifest_canonical_hash(manifest)
    return manifest


def _staged_cfg(
    candidate_cfg: Mapping[str, Any],
    *,
    staged_ledger: Path,
    staged_manifest: Path,
    staged_health: Path,
) -> dict[str, Any]:
    value = json.loads(json.dumps(candidate_cfg))
    section = value["shadow_ledger"]
    section["ledger_path"] = str(staged_ledger)
    section["activation_manifest_path"] = str(staged_manifest)
    section["health_path"] = str(staged_health)
    return value


def _validate_prepared(
    cfg: Mapping[str, Any], layout: ActivationLayout, *, revision: str
) -> None:
    result = validate_shadow_activation(
        None,
        layout.chroma_dir,
        ValidationMode.PREPARE,
        cfg=cfg,
        runtime_code_revision=revision,
        collection_uuid_provider=lambda *_args: collection_uuid(
            layout.chroma_dir, COLLECTION_KNOWLEDGE_UNITS
        ),
    )
    if result.refusals:
        first = result.refusals[0]
        raise ActivationRefused(first.code, first.detail)


def _cleanup_identity(record: Mapping[str, Any]) -> None:
    path_value = record.get("path")
    if not isinstance(path_value, str):
        return
    path = lexical_abspath(path_value)
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return
    if (st.st_dev, st.st_ino) != (record.get("dev"), record.get("ino")):
        raise ActivationRefused(
            "prepared_not_committed", "artifact identity changed; cleanup refused"
        )
    path.unlink()




def _read_shadow_health_failure_class(health_path: Path) -> str | None:
    """Return last_failure_class or raise on unreadable health (fail closed)."""
    if not health_path.is_file():
        return None
    try:
        payload = json.loads(health_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ActivationRefused(
            "health_unreadable", "shadow health unavailable for first-event gate"
        ) from exc
    if not isinstance(payload, dict):
        raise ActivationRefused(
            "health_unreadable", "shadow health payload invalid"
        )
    klass = payload.get("last_failure_class")
    return str(klass) if isinstance(klass, str) else None


def _rollback_first_event_refusal(
    layout: ActivationLayout,
    journal: dict[str, Any],
    h: ActivationHooks,
    *,
    refusal_code: str,
) -> ActivationOutcome:
    journal["state"] = ActivationState.ROLLBACK_PENDING.value
    journal["first_event_refusal"] = refusal_code
    _write_journal(layout.journal_path, journal, h)
    rollback_activation(
        config_path=layout.config_path,
        activation_id=layout.activation_id,
        writer_lock_path=layout.writer_lock_path,
        journal_path=layout.journal_path,
        mountinfo_text=h.mountinfo(),
    )
    return ActivationOutcome(
        layout.activation_id,
        ActivationState.DISABLED_AFTER_ROLLBACK.value,
        False,
        refusal_code=refusal_code,
    )

def _load_first_event(path: Path) -> tuple[dict[str, Any], dict[str, Any]] | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ActivationRefused("first_event_missing", "ledger unavailable") from exc
    if len(lines) < 2:
        return None
    try:
        header = json.loads(lines[0])
        event = json.loads(lines[1])
    except json.JSONDecodeError as exc:
        raise ActivationRefused("first_event_mismatch", "first event JSON invalid") from exc
    if not isinstance(header, dict) or not isinstance(event, dict):
        raise ActivationRefused("first_event_mismatch", "first event record invalid")
    return header, event


def _verify_first_event(layout: ActivationLayout, *, revision: str) -> dict[str, Any] | None:
    pair = _load_first_event(layout.ledger_path)
    if pair is None:
        return None
    header, event = pair
    if header.get("activation_id") != layout.activation_id or event.get("sequence") != 1:
        raise ActivationRefused("first_event_mismatch", "first event identity or sequence mismatch")
    post = event.get("post_state")
    entity_id = event.get("stable_entity_id")
    if not isinstance(post, dict) or not isinstance(entity_id, str):
        raise ActivationRefused("first_event_mismatch", "first event payload incomplete")
    document = post.get("document")
    metadata = post.get("metadata") if isinstance(post.get("metadata"), dict) else {}
    deleted = bool(post.get("deleted"))
    if (
        event.get("metadata_hash") != sha256_canonical(metadata)
        or event.get("state_hash")
        != projection_state_hash(
            stable_entity_id=entity_id,
            deleted=deleted,
            document=document,
            metadata=metadata,
        )
    ):
        raise ActivationRefused("first_event_mismatch", "first event hashes mismatch")
    rows = {
        str(row.get("id")): row
        for row in collection_metadata_rows(layout.chroma_dir, COLLECTION_KNOWLEDGE_UNITS)
    }
    expected_document_hash = None if deleted or document is None else sha256_canonical(document)
    if event.get("document_hash") != expected_document_hash:
        raise ActivationRefused("first_event_mismatch", "first event document hash mismatch")
    live = rows.get(entity_id)
    if deleted:
        if live is not None:
            raise ActivationRefused(
                "first_event_mismatch", "deleted first event remains present in Chroma"
            )
    else:
        if live is None:
            raise ActivationRefused(
                "first_event_mismatch", "first event entity missing in Chroma"
            )
        live_document = live.get("document")
        live_metadata = {
            key: value for key, value in live.items() if key not in {"id", "document"}
        }
        if document != live_document or metadata != live_metadata:
            raise ActivationRefused(
                "first_event_mismatch", "first event differs from Chroma post-state"
            )
    result = validate_shadow_activation(
        layout.config_path,
        layout.chroma_dir,
        ValidationMode.VERIFY,
        runtime_code_revision=revision,
        collection_uuid_provider=lambda *_args: collection_uuid(
            layout.chroma_dir, COLLECTION_KNOWLEDGE_UNITS
        ),
        check_first_event=True,
    )
    if result.refusals:
        first = result.refusals[0]
        raise ActivationRefused(first.code, first.detail)
    return {"event_id": event.get("event_id"), "sequence": event.get("sequence")}


def rollback_activation(  # pylint: disable=too-many-arguments
    *,
    config_path: Path,
    activation_id: str,
    writer_lock_path: Path,
    journal_path: Path | None = None,
    mountinfo_text: str | None = None,
) -> ActivationOutcome:
    """Disable one committed activation under the exclusive writer gate."""
    _data, preimage, cfg = _config_preimage(lexical_abspath(config_path))
    section = cfg.get("shadow_ledger") if isinstance(cfg, dict) else None
    if not isinstance(section, dict) or section.get("activation_id") != activation_id:
        raise ActivationRefused("config_activation_mismatch", "activation ID mismatch")
    if section.get("enabled") is not True:
        if journal_path and journal_path.is_file():
            try:
                journal = load_private_json(journal_path)
                state = str(journal.get("state"))
                if state == ActivationState.ROLLBACK_PENDING.value:
                    journal["state"] = ActivationState.DISABLED_AFTER_ROLLBACK.value
                    journal["committed"] = False
                    journal["rollback_at_utc"] = _iso_utc(datetime.now(timezone.utc))
                    _write_journal(journal_path, journal, ActivationHooks())
            except AuthorizationRefused as exc:
                raise ActivationRefused(
                    "prepared_not_committed", "rollback journal is not private"
                ) from exc
        return ActivationOutcome(activation_id, ActivationState.DISABLED_AFTER_ROLLBACK.value, False)
    journal: dict[str, Any] | None = None
    if journal_path and journal_path.is_file():
        journal = load_private_json(journal_path)
        assert_state_transition(
            str(journal.get("state")), ActivationState.ROLLBACK_PENDING.value
        )
        journal["state"] = ActivationState.ROLLBACK_PENDING.value
        _write_journal(journal_path, journal, ActivationHooks())
    with exclusive_writer_lease(
        lock_path=lexical_abspath(writer_lock_path),
        timeout_ms=QUIESCE_TIMEOUT_SECONDS * 1000,
    ):
        current = lexical_abspath(config_path).read_bytes()
        if hashlib.sha256(current).hexdigest() != preimage:
            raise ActivationRefused("config_changed", "config changed before rollback")
        try:
            atomic_shadow_config_update(
                config_path,
                expected_preimage_sha256=preimage,
                replacements={"enabled": False},
                expected_enabled=True,
                mountinfo_text=mountinfo_text,
            )
        except ShadowConfigUpdateRefused as exc:
            raise ActivationRefused(exc.code, exc.detail) from exc
    if journal_path and journal is not None:
        assert_state_transition(
            str(journal.get("state")), ActivationState.DISABLED_AFTER_ROLLBACK.value
        )
        journal["state"] = ActivationState.DISABLED_AFTER_ROLLBACK.value
        journal["committed"] = False
        journal["rollback_at_utc"] = _iso_utc(datetime.now(timezone.utc))
        _write_journal(journal_path, journal, ActivationHooks())
    return ActivationOutcome(
        activation_id,
        ActivationState.DISABLED_AFTER_ROLLBACK.value,
        False,
    )


def recover_prepared_activation(
    *,
    journal_path: Path,
    config_path: Path,
    activation_id: str,
    writer_lock_path: Path,
) -> ActivationOutcome:
    """Identity-scoped cleanup for a dead, disabled precommit activation."""
    try:
        journal = load_private_json(journal_path)
    except AuthorizationRefused as exc:
        raise ActivationRefused(
            "prepared_not_committed", "private recovery journal unavailable"
        ) from exc
    if journal.get("activation_id") != activation_id or journal.get("committed") is True:
        raise ActivationRefused("prepared_not_committed", "journal identity mismatch")
    if journal.get("state") not in {
        ActivationState.PREPARING.value,
        ActivationState.QUIESCED.value,
        ActivationState.BASELINE_CAPTURED.value,
        ActivationState.ARTIFACTS_VALIDATED.value,
        ActivationState.PREPARED_NOT_COMMITTED.value,
    }:
        raise ActivationRefused("prepared_not_committed", "journal state is not recoverable")
    if not isinstance(journal.get("nonce"), str) or not isinstance(
        journal.get("token_sha256"), str
    ):
        raise ActivationRefused("prepared_not_committed", "journal token binding missing")
    cfg = load_config(config_path)
    section = cfg.get("shadow_ledger") if isinstance(cfg, dict) else None
    if isinstance(section, dict) and section.get("enabled") is True:
        raise ActivationRefused("config_changed", "enabled config forbids precommit cleanup")
    owner_pid = journal.get("owner_pid")
    owner_start = journal.get("owner_start_time")
    if isinstance(owner_pid, int) and _pid_start_time(owner_pid) == owner_start:
        raise ActivationRefused("prepared_not_committed", "activation owner is still alive")
    if lexical_abspath(str(journal.get("config_path"))) != lexical_abspath(config_path):
        raise ActivationRefused("prepared_not_committed", "journal config path mismatch")
    shadow_dir = lexical_abspath(str(journal.get("shadow_dir")))
    journal_artifacts = journal.get("artifacts")
    if not isinstance(journal_artifacts, dict):
        raise ActivationRefused("prepared_not_committed", "journal artifacts invalid")
    for record in journal_artifacts.values():
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise ActivationRefused("prepared_not_committed", "journal artifact record invalid")
        record_path = lexical_abspath(record["path"])
        if record_path.parent != shadow_dir or record_path == lexical_abspath(journal_path):
            raise ActivationRefused(
                "prepared_not_committed", "journal artifact escaped Shadow directory"
            )
    with exclusive_writer_lease(
        lock_path=writer_lock_path,
        timeout_ms=QUIESCE_TIMEOUT_SECONDS * 1000,
    ):
        for record in journal_artifacts.values():
            if isinstance(record, dict):
                _cleanup_identity(record)
        journal["state"] = ActivationState.ABORTED_PRECOMMIT.value
        journal["recovered_at_utc"] = _iso_utc(datetime.now(timezone.utc))
        _write_journal(journal_path, journal, ActivationHooks())
    return ActivationOutcome(activation_id, ActivationState.ABORTED_PRECOMMIT.value, False)


def activate_shadow(  # pylint: disable=too-many-locals,too-many-statements,too-many-arguments,too-many-branches
    *,
    token_path: Path,
    config_path: Path,
    census_path: Path,
    nonce_store_path: Path,
    writer_lock_path: Path,
    attest_dir: Path,
    hooks: ActivationHooks | None = None,
) -> ActivationOutcome:
    """Execute the config-last activation transaction and first-event gate."""
    h = hooks or ActivationHooks()
    revision = h.revision()
    try:
        untrusted = load_authorization_payload(token_path)
    except AuthorizationRefused as exc:
        raise ActivationRefused(exc.code, exc.detail) from exc
    layout = _layout_from_payload(
        untrusted,
        config_path=config_path,
        census_path=census_path,
        nonce_store_path=nonce_store_path,
        writer_lock_path=writer_lock_path,
    )
    _data, config_preimage, cfg = _config_preimage(layout.config_path)
    chroma_dir = cfg.get("index", {}).get("chroma_dir") if isinstance(cfg.get("index"), dict) else None
    if not isinstance(chroma_dir, str):
        raise ActivationRefused("config_corrupt", "index.chroma_dir missing")
    layout = _bind_chroma(layout, Path(chroma_dir))
    _validate_layout(layout)
    section = cfg.get("shadow_ledger")
    if not isinstance(section, dict) or section.get("enabled") is not False:
        raise ActivationRefused("config_changed", "Shadow must be explicitly disabled")

    nonce_store = NonceStore(layout.nonce_store_path)
    expectation = authorization_expectation(layout, code_revision=revision)
    try:
        authorization = validate_authorization_token(
            token_path, expected=expectation, nonce_store=nonce_store, now=h.now()
        )
    except AuthorizationRefused as exc:
        raise ActivationRefused(exc.code, exc.detail) from exc
    census = _load_census(layout.census_path, revision=revision)
    verify_quiescence(
        census,
        chroma_dir=layout.chroma_dir,
        revision=revision,
        attest_dir=attest_dir,
        hooks=h,
    )

    try:
        ensure_private_directory(layout.shadow_dir)
    except AuthorizationRefused as exc:
        raise ActivationRefused(exc.code, exc.detail) from exc
    artifacts: dict[str, Any] = {}
    journal = _journal_payload(
        layout,
        state=ActivationState.PREPARING,
        authorization=authorization,
        revision=revision,
        config_preimage_sha256=config_preimage,
        now=h.now(),
    )
    _write_journal(layout.journal_path, journal, h)
    committed = False
    nonce_consumed = False
    try:
        with exclusive_writer_lease(
            lock_path=layout.writer_lock_path,
            timeout_ms=QUIESCE_TIMEOUT_SECONDS * 1000,
        ):
            verify_quiescence(
                census,
                chroma_dir=layout.chroma_dir,
                revision=revision,
                attest_dir=attest_dir,
                hooks=h,
            )
            if hashlib.sha256(layout.config_path.read_bytes()).hexdigest() != config_preimage:
                raise ActivationRefused("config_changed", "config changed before quiescence")
            journal["state"] = ActivationState.QUIESCED.value
            _write_journal(layout.journal_path, journal, h)

            provider = h.baseline or capture_baseline
            first = provider(layout.chroma_dir)
            second = provider(layout.chroma_dir)
            if first.canonical_identity() != second.canonical_identity():
                raise ActivationRefused("baseline_hash_invalid", "baseline snapshots differ")
            baseline = second
            journal["state"] = ActivationState.BASELINE_CAPTURED.value
            journal["baseline_digest"] = baseline.aggregate_digest
            _write_journal(layout.journal_path, journal, h)

            ledger_identity = str(uuid.uuid4())
            stage_prefix = f".{layout.activation_id}."
            staged_ledger = layout.shadow_dir / f"{stage_prefix}{layout.ledger_path.name}.stage"
            staged_manifest = layout.shadow_dir / f"{stage_prefix}{layout.manifest_path.name}.stage"
            staged_health = layout.shadow_dir / f"{stage_prefix}{layout.health_path.name}.stage"
            try:
                header = create_shadow_ledger_header(
                    staged_ledger,
                    activation_id=layout.activation_id,
                    ledger_identity=ledger_identity,
                    starting_sequence=0,
                    created_at_utc=_iso_utc(h.now()),
                )
            except SecureLedgerRefused as exc:
                raise ActivationRefused(
                    "ledger_exists_unbound", "staged ledger creation refused"
                ) from exc
            artifacts["staged_ledger"] = _private_identity(staged_ledger)
            manifest = _build_manifest(
                layout=layout,
                revision=revision,
                baseline=baseline,
                ledger_identity=ledger_identity,
                header_hash=compute_ledger_header_hash(header),
                configured_embed_model=cfg.get("models", {}).get("embed_model")
                if isinstance(cfg.get("models"), dict)
                else None,
                now=h.now(),
            )
            try:
                secure_atomic_write_json(
                    staged_manifest, manifest, replace_existing=False
                )
            except (AuthorizationRefused, FileExistsError, OSError) as exc:
                raise ActivationRefused(
                    "prepared_not_committed", "staged manifest publication failed"
                ) from exc
            artifacts["staged_manifest"] = _private_identity(staged_manifest)

            replacements = dict(authorization.payload["target_config"])
            replacements["manifest_sha256"] = manifest["manifest_canonical_hash"]
            candidate = render_shadow_config_update(
                layout.config_path.read_bytes(),
                replacements=replacements,
                expected_enabled=False,
            )
            if candidate.preimage_sha256 != config_preimage:
                raise ActivationRefused("config_changed", "config changed while preparing")
            _validate_prepared(
                _staged_cfg(
                    candidate.parsed,
                    staged_ledger=staged_ledger,
                    staged_manifest=staged_manifest,
                    staged_health=staged_health,
                ),
                layout,
                revision=revision,
            )
            journal["state"] = ActivationState.ARTIFACTS_VALIDATED.value
            journal["artifacts"] = artifacts
            journal["manifest_sha256"] = manifest["manifest_canonical_hash"]
            _write_journal(layout.journal_path, journal, h)

            artifacts["ledger"] = _install_absent(staged_ledger, layout.ledger_path)
            artifacts.pop("staged_ledger", None)
            journal["artifacts"] = artifacts
            _write_journal(layout.journal_path, journal, h)
            h.checkpoint("ledger_installed")
            artifacts["manifest"] = _install_absent(staged_manifest, layout.manifest_path)
            artifacts.pop("staged_manifest", None)
            journal["artifacts"] = artifacts
            _write_journal(layout.journal_path, journal, h)
            h.checkpoint("manifest_installed")
            _validate_prepared(candidate.parsed, layout, revision=revision)

            try:
                revalidated = validate_authorization_token(
                    token_path, expected=expectation, nonce_store=nonce_store, now=h.now()
                )
            except AuthorizationRefused as exc:
                raise ActivationRefused(exc.code, exc.detail) from exc
            if (
                revalidated.token_sha256 != authorization.token_sha256
                or revalidated.nonce != authorization.nonce
            ):
                raise ActivationRefused(
                    "authorization_mismatch", "authorization token changed under gate"
                )
            authorization = revalidated
            nonce_store.consume(
                nonce=authorization.nonce,
                activation_id=layout.activation_id,
                token_sha256=authorization.token_sha256,
                consumed_at_utc=_iso_utc(h.now()),
            )
            nonce_consumed = True
            h.checkpoint("nonce_consumed")
            atomic_shadow_config_update(
                layout.config_path,
                expected_preimage_sha256=config_preimage,
                replacements=replacements,
                expected_enabled=False,
                mountinfo_text=h.mountinfo(),
            )
            committed = True
            journal["state"] = ActivationState.COMMITTED.value
            journal["committed"] = True
            journal["artifacts"] = artifacts
            _write_journal(layout.journal_path, journal, h)

        deadline = h.monotonic() + FIRST_EVENT_TIMEOUT_SECONDS
        while h.monotonic() < deadline:
            try:
                health_klass = _read_shadow_health_failure_class(layout.health_path)
            except ActivationRefused as exc:
                return _rollback_first_event_refusal(
                    layout, journal, h, refusal_code=exc.code
                )
            if health_klass == "event_too_large":
                return _rollback_first_event_refusal(
                    layout, journal, h, refusal_code="first_event_too_large"
                )
            try:
                evidence = _verify_first_event(layout, revision=revision)
            except ActivationRefused as exc:
                journal["state"] = ActivationState.ROLLBACK_PENDING.value
                journal["first_event_refusal"] = exc.code
                _write_journal(layout.journal_path, journal, h)
                rollback_activation(
                    config_path=layout.config_path,
                    activation_id=layout.activation_id,
                    writer_lock_path=layout.writer_lock_path,
                    journal_path=layout.journal_path,
                    mountinfo_text=h.mountinfo(),
                )
                return ActivationOutcome(
                    layout.activation_id,
                    ActivationState.DISABLED_AFTER_ROLLBACK.value,
                    False,
                    refusal_code=exc.code,
                )
            if evidence is not None:
                journal["state"] = ActivationState.FIRST_EVENT_OBSERVED.value
                journal["first_event"] = evidence
                _write_journal(layout.journal_path, journal, h)
                return ActivationOutcome(
                    layout.activation_id,
                    ActivationState.FIRST_EVENT_OBSERVED.value,
                    True,
                    evidence=evidence,
                )
            h.sleep(min(1.0, max(0.0, deadline - h.monotonic())))

        journal["state"] = ActivationState.ROLLBACK_PENDING.value
        _write_journal(layout.journal_path, journal, h)
        rollback_activation(
            config_path=layout.config_path,
            activation_id=layout.activation_id,
            writer_lock_path=layout.writer_lock_path,
            journal_path=layout.journal_path,
            mountinfo_text=h.mountinfo(),
        )
        return ActivationOutcome(
            layout.activation_id,
            ActivationState.DISABLED_AFTER_ROLLBACK.value,
            False,
            refusal_code="first_event_timeout",
        )
    except ShadowConfigUpdateRefused as exc:
        if exc.committed:
            try:
                live_cfg = load_config(layout.config_path)
                live_section = live_cfg.get("shadow_ledger")
                committed = bool(
                    isinstance(live_section, dict)
                    and live_section.get("enabled") is True
                    and live_section.get("activation_id") == layout.activation_id
                )
            except (OSError, ValueError):
                committed = False
        if committed:
            journal["state"] = ActivationState.COMMITTED.value
            journal["committed"] = True
        elif nonce_consumed:
            journal["state"] = ActivationState.PREPARED_NOT_COMMITTED.value
            journal["committed"] = False
        journal["artifacts"] = artifacts
        _write_journal(layout.journal_path, journal, h)
        raise ActivationRefused(exc.code, exc.detail) from exc
    except Exception as exc:
        if not committed:
            journal["committed"] = False
            if nonce_consumed:
                journal["state"] = ActivationState.PREPARED_NOT_COMMITTED.value
                journal["artifacts"] = artifacts
                _write_journal(layout.journal_path, journal, h)
            else:
                for record in list(artifacts.values()):
                    if isinstance(record, dict) and record:
                        _cleanup_identity(record)
                journal["state"] = ActivationState.ABORTED_PRECOMMIT.value
                journal["artifacts"] = {}
                _write_journal(layout.journal_path, journal, h)
        if isinstance(exc, ActivationRefused):
            raise
        if isinstance(exc, AuthorizationRefused):
            raise ActivationRefused(exc.code, exc.detail) from exc
        if isinstance(exc, TimeoutError):
            raise ActivationRefused(
                "writer_quiesce_timeout", "exclusive writer gate timed out"
            ) from exc
        if isinstance(exc, OSError):
            raise ActivationRefused(
                "prepared_not_committed", "activation durable I/O failed"
            ) from exc
        raise
