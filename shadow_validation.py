# pylint: disable=too-many-lines,too-many-branches,too-many-statements,too-many-locals
"""Strict Shadow activation validation and filesystem-policy contract (C1).

This module defines the shared typed validation boundary. It does not activate
Shadow, create live artifacts, or wire production writers. Later slices consume
``validate_shadow_activation`` for doctor, inventory, activation, and writers.
"""

from __future__ import annotations

import json
import os
import stat
import tomllib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

from chroma_readonly import collection_uuid as readonly_collection_uuid
from shadow_ledger import (
    ARTIFACT_FILE_MODE,
    COLLECTION_KNOWLEDGE_UNITS,
    ENTITY_CLASSIFICATIONS,
    LEDGER_HEADER_RECORD_TYPE,
    SHADOW_DIR_MODE,
    SUPPORTED_HASH_RULES_VERSION,
    SUPPORTED_MANIFEST_VERSION,
    SUPPORTED_SHADOW_SCHEMA_VERSION,
    compute_aggregate_baseline_digest,
    compute_ledger_header_hash,
    compute_manifest_canonical_hash,
    lexical_abspath,
    parse_complete_jsonl_line,
    resolve_shadow_settings,
)

# ---------------------------------------------------------------------------
# Refusal vocabulary (C1 implemented + reserved for later slices)
# ---------------------------------------------------------------------------

REFUSAL_CODES_C1: tuple[str, ...] = (
    "manifest_missing",
    "manifest_corrupt",
    "manifest_version_unsupported",
    "manifest_incomplete",
    "collection_mismatch",
    "code_revision_mismatch",
    "baseline_count_invalid",
    "baseline_hash_invalid",
    "ledger_missing",
    "ledger_corrupt",
    "ledger_identity_mismatch",
    "starting_sequence_invalid",
    "path_collision",
    "path_inside_chroma",
    "path_not_private",
    "path_wrong_owner",
    "symlink_refused",
    "permission_invalid",
    "prepared_not_committed",
)

REFUSAL_CODES_RESERVED: tuple[str, ...] = (
    "config_changed",
    "config_corrupt",
    "config_activation_mismatch",
    "authorization_missing",
    "authorization_expired",
    "authorization_mismatch",
    "authorization_reused",
    "health_missing",
    "health_corrupt",
    "writer_quiesce_timeout",
    "legacy_writer_process",
    "collection_unavailable",
    "ledger_exists_unbound",
    "artifact_type_invalid",
    "directory_not_private",
    "config_filesystem_unsupported",
    "config_cross_device",
    "first_event_missing",
    "first_event_mismatch",
    "performance_budget_missing",
    "performance_budget_exceeded",
)

ALL_REFUSAL_CODES: tuple[str, ...] = REFUSAL_CODES_C1 + REFUSAL_CODES_RESERVED

# Stable total order for deterministic refusal lists.
REFUSAL_CODE_ORDER: dict[str, int] = {
    code: index for index, code in enumerate(ALL_REFUSAL_CODES)
}

ARTIFACT_CONFIG = "config"
ARTIFACT_MANIFEST = "manifest"
ARTIFACT_LEDGER = "ledger"
ARTIFACT_HEALTH = "health"
ARTIFACT_SHADOW_DIR = "shadow_dir"
ARTIFACT_CHROMA = "chroma"
ARTIFACT_BASELINE = "baseline"
ARTIFACT_COLLECTION = "collection"
ARTIFACT_CODE = "code_revision"
ARTIFACT_PATHS = "paths"


class ValidationMode(str, Enum):
    WRITER = "writer"
    PREPARE = "prepare"
    DOCTOR = "doctor"
    INVENTORY = "inventory"
    VERIFY = "verify"


class ShadowState(str, Enum):
    DISABLED = "disabled"
    PREPARED = "prepared"
    COMMITTED = "committed"
    INVALID = "invalid"


@dataclass(frozen=True)
class ShadowRefusal:
    code: str
    artifact: str
    blocking: bool
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "artifact": self.artifact,
            "blocking": self.blocking,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ShadowValidationResult:
    state: str
    inject_eligible: bool
    activation_id: str | None
    refusals: tuple[ShadowRefusal, ...]
    facts: Mapping[str, Any] = field(default_factory=dict)

    def codes(self) -> tuple[str, ...]:
        return tuple(r.code for r in self.refusals)

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "inject_eligible": self.inject_eligible,
            "activation_id": self.activation_id,
            "refusals": [r.as_dict() for r in self.refusals],
            "facts": dict(self.facts),
        }


StatFunc = Callable[[str | Path], os.stat_result]
UuidFunc = Callable[[str | Path, str], str | None]


@dataclass
class _RefusalBag:
    _items: dict[tuple[str, str], ShadowRefusal] = field(default_factory=dict)

    def add(
        self,
        code: str,
        artifact: str,
        detail: str,
        *,
        blocking: bool = True,
    ) -> None:
        if code not in REFUSAL_CODE_ORDER:
            raise ValueError(f"unknown refusal code: {code}")
        key = (code, artifact)
        if key in self._items:
            return
        self._items[key] = ShadowRefusal(
            code=code,
            artifact=artifact,
            blocking=blocking,
            detail=redact_detail(detail),
        )

    def ordered(self) -> tuple[ShadowRefusal, ...]:
        return tuple(
            sorted(
                self._items.values(),
                key=lambda r: (REFUSAL_CODE_ORDER[r.code], r.artifact, r.detail),
            )
        )


def redact_detail(detail: str) -> str:
    """Redact absolute home/data path prefixes; keep mechanical codes readable."""
    text = str(detail)
    home = str(Path.home())
    if home and home in text:
        text = text.replace(home, "<home>")
    # Collapse long absolute prefixes under /home or /var
    out = []
    for token in text.split():
        if token.startswith("/") and len(token) > 24:
            out.append("<path:" + Path(token).name + ">")
        else:
            out.append(token)
    return " ".join(out)


def _mode_bits(st: os.stat_result) -> int:
    return stat.S_IMODE(st.st_mode)


def _is_lnk(st: os.stat_result) -> bool:
    return stat.S_ISLNK(st.st_mode)


def _is_reg(st: os.stat_result) -> bool:
    return stat.S_ISREG(st.st_mode)


def _is_dir(st: os.stat_result) -> bool:
    return stat.S_ISDIR(st.st_mode)


def _load_cfg(config_path: str | Path | None, cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    if cfg is not None:
        return dict(cfg)
    if config_path is None:
        raise ValueError("config_path or cfg is required")
    path = Path(config_path).expanduser()
    with open(path, "rb") as handle:
        loaded = tomllib.load(handle)
    if not isinstance(loaded, dict):
        raise ValueError("config must be a TOML table")
    return loaded


def _activation_id_from_manifest(manifest: Mapping[str, Any]) -> str | None:
    value = manifest.get("activation_id") or manifest.get("baseline_id")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _path_has_symlink_component(
    path: Path, *, lstat: StatFunc
) -> tuple[bool, str | None]:
    """Walk absolute path components; return (hit, component) on symlink."""
    parts = path.parts
    if not parts:
        return False, None
    if path.is_absolute():
        cur = Path("/")
        iter_parts = parts[1:]
    else:
        cur = Path()
        iter_parts = parts
    for part in iter_parts:
        cur = cur / part
        try:
            st = lstat(cur)
        except OSError:
            # Missing components are not symlink hits; existence checked elsewhere.
            return False, None
        if _is_lnk(st):
            return True, str(cur)
    return False, None


def _validate_symlink_free(path: Path, artifact: str, bag: _RefusalBag, *, lstat: StatFunc) -> None:
    hit, _component = _path_has_symlink_component(path, lstat=lstat)
    if hit:
        bag.add(
            "symlink_refused",
            artifact,
            f"symlink component refused artifact={artifact}",
        )


def _validate_artifact_file(
    path: Path,
    artifact: str,
    bag: _RefusalBag,
    *,
    lstat: StatFunc,
    euid: int,
    must_exist: bool,
) -> os.stat_result | None:
    _validate_symlink_free(path, artifact, bag, lstat=lstat)
    try:
        st = lstat(path)
    except FileNotFoundError:
        if must_exist:
            if artifact == ARTIFACT_MANIFEST:
                bag.add("manifest_missing", ARTIFACT_MANIFEST, "manifest file absent")
            elif artifact == ARTIFACT_LEDGER:
                bag.add("ledger_missing", ARTIFACT_LEDGER, "ledger file absent")
            elif artifact == ARTIFACT_HEALTH:
                bag.add("health_missing", ARTIFACT_HEALTH, "health file absent")
        return None
    except OSError as exc:
        if artifact == ARTIFACT_MANIFEST:
            bag.add("manifest_corrupt", ARTIFACT_MANIFEST, f"manifest unstatable: {exc}")
        elif artifact == ARTIFACT_LEDGER:
            bag.add("ledger_corrupt", ARTIFACT_LEDGER, f"ledger unstatable: {exc}")
        else:
            bag.add("artifact_type_invalid", artifact, f"unstatable: {exc}")
        return None

    if _is_lnk(st):
        bag.add("symlink_refused", artifact, f"symlink leaf refused artifact={artifact}")
        return st
    if not _is_reg(st):
        bag.add(
            "artifact_type_invalid",
            artifact,
            f"non-regular artifact type mode={oct(_mode_bits(st))}",
        )
        return st
    if st.st_nlink != 1:
        bag.add(
            "artifact_type_invalid",
            artifact,
            f"hardlink or multi-link refused nlink={st.st_nlink}",
        )
    if st.st_uid != euid:
        bag.add(
            "path_wrong_owner",
            artifact,
            f"owner uid={st.st_uid} expected={euid}",
        )
    if _mode_bits(st) != ARTIFACT_FILE_MODE:
        bag.add(
            "permission_invalid",
            artifact,
            f"file mode={oct(_mode_bits(st))} expected={oct(ARTIFACT_FILE_MODE)}",
        )
    return st


def _validate_shadow_directory(
    shadow_dir: Path,
    chroma_dir: Path,
    bag: _RefusalBag,
    *,
    lstat: StatFunc,
    euid: int,
) -> None:
    _validate_symlink_free(shadow_dir, ARTIFACT_SHADOW_DIR, bag, lstat=lstat)
    try:
        st = lstat(shadow_dir)
    except OSError:
        bag.add(
            "directory_not_private",
            ARTIFACT_SHADOW_DIR,
            "dedicated shadow directory missing",
        )
        return
    if _is_lnk(st):
        bag.add("symlink_refused", ARTIFACT_SHADOW_DIR, "shadow directory is symlink")
        return
    if not _is_dir(st):
        bag.add(
            "directory_not_private",
            ARTIFACT_SHADOW_DIR,
            "shadow path is not a directory",
        )
        return
    if st.st_uid != euid:
        bag.add(
            "path_wrong_owner",
            ARTIFACT_SHADOW_DIR,
            f"shadow dir owner uid={st.st_uid} expected={euid}",
        )
    if _mode_bits(st) != SHADOW_DIR_MODE:
        bag.add(
            "permission_invalid",
            ARTIFACT_SHADOW_DIR,
            f"shadow dir mode={oct(_mode_bits(st))} expected={oct(SHADOW_DIR_MODE)}",
        )
        bag.add(
            "directory_not_private",
            ARTIFACT_SHADOW_DIR,
            f"shadow dir not private mode={oct(_mode_bits(st))}",
        )

    # Sibling / outside Chroma policy.
    try:
        _chroma_st = lstat(chroma_dir)
    except OSError:
        _chroma_st = None
    if shadow_dir == chroma_dir:
        bag.add("path_inside_chroma", ARTIFACT_SHADOW_DIR, "shadow dir equals chroma root")
    else:
        try:
            shadow_dir.relative_to(chroma_dir)
            bag.add(
                "path_inside_chroma",
                ARTIFACT_SHADOW_DIR,
                "shadow dir inside chroma root",
            )
        except ValueError:
            pass
    if shadow_dir.parent != chroma_dir.parent:
        bag.add(
            "path_not_private",
            ARTIFACT_SHADOW_DIR,
            "shadow dir must be sibling of chroma under data root",
        )


def _validate_path_policy(
    *,
    ledger_path: Path,
    manifest_path: Path,
    health_path: Path,
    chroma_dir: Path,
    bag: _RefusalBag,
    lstat: StatFunc,
    euid: int,
    require_files: bool,
) -> None:
    paths = {
        ARTIFACT_LEDGER: lexical_abspath(ledger_path),
        ARTIFACT_MANIFEST: lexical_abspath(manifest_path),
        ARTIFACT_HEALTH: lexical_abspath(health_path),
    }
    chroma = lexical_abspath(chroma_dir)

    # Lexical collisions among configured paths.
    lexical_seen: dict[str, str] = {}
    for artifact, path in paths.items():
        key = str(path)
        if key in lexical_seen:
            bag.add(
                "path_collision",
                ARTIFACT_PATHS,
                f"lexical path collision {lexical_seen[key]} vs {artifact}",
            )
        else:
            lexical_seen[key] = artifact

    # Dedicated shadow directory = common parent of the three artifacts.
    try:
        shadow_dir = Path(os.path.commonpath([str(p) for p in paths.values()]))
    except ValueError:
        bag.add(
            "path_not_private",
            ARTIFACT_PATHS,
            "artifact paths do not share a dedicated shadow directory",
        )
        shadow_dir = paths[ARTIFACT_MANIFEST].parent

    # Artifacts must be files under shadow_dir (not the dir itself).
    for artifact, path in paths.items():
        if path == shadow_dir:
            bag.add(
                "path_not_private",
                artifact,
                "artifact path equals shadow directory",
            )
            continue
        try:
            path.relative_to(shadow_dir)
        except ValueError:
            bag.add(
                "path_not_private",
                artifact,
                "artifact outside dedicated shadow directory",
            )
        # Chroma containment (lexical).
        if path == chroma:
            bag.add("path_inside_chroma", artifact, "artifact path equals chroma root")
        else:
            try:
                path.relative_to(chroma)
                bag.add("path_inside_chroma", artifact, "artifact path inside chroma root")
            except ValueError:
                pass

    _validate_shadow_directory(shadow_dir, chroma, bag, lstat=lstat, euid=euid)

    stats: dict[str, os.stat_result] = {}
    for artifact, path in paths.items():
        must = require_files and artifact in {ARTIFACT_MANIFEST, ARTIFACT_LEDGER}
        # Health existence is not a C1 writer hard requirement unless verify;
        # still validate metadata when present.
        if artifact == ARTIFACT_HEALTH:
            must = False
        st = _validate_artifact_file(
            path, artifact, bag, lstat=lstat, euid=euid, must_exist=must
        )
        if st is not None and _is_reg(st):
            stats[artifact] = st

    # Device/inode collisions among existing regular artifacts.
    inode_seen: dict[tuple[int, int], str] = {}
    for artifact, st in stats.items():
        key = (st.st_dev, st.st_ino)
        if key in inode_seen:
            bag.add(
                "path_collision",
                ARTIFACT_PATHS,
                f"device/inode collision {inode_seen[key]} vs {artifact}",
            )
        else:
            inode_seen[key] = artifact


def _load_manifest_strict(
    path: Path, bag: _RefusalBag
) -> dict[str, Any] | None:
    if not path.is_file() and not path.exists():
        # missing handled by path policy when required
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        bag.add("manifest_corrupt", ARTIFACT_MANIFEST, f"manifest JSON invalid: {type(exc).__name__}")
        return None
    if not isinstance(data, dict):
        bag.add("manifest_corrupt", ARTIFACT_MANIFEST, "manifest must be a JSON object")
        return None
    return data


def _validate_manifest_fields(
    manifest: Mapping[str, Any],
    bag: _RefusalBag,
    *,
    chroma_dir: Path,
    runtime_code_revision: str | None,
    configured_activation_id: str | None,
    configured_manifest_sha: str | None,
) -> str | None:
    activation_id = _activation_id_from_manifest(manifest)

    # Versions
    for key, supported, code in (
        ("manifest_version", SUPPORTED_MANIFEST_VERSION, "manifest_version_unsupported"),
        ("shadow_schema_version", SUPPORTED_SHADOW_SCHEMA_VERSION, "manifest_version_unsupported"),
        ("hash_rules_version", SUPPORTED_HASH_RULES_VERSION, "manifest_version_unsupported"),
    ):
        value = manifest.get(key)
        if value is None:
            bag.add("manifest_incomplete", ARTIFACT_MANIFEST, f"missing field {key}")
        elif not isinstance(value, int) or isinstance(value, bool) or value != supported:
            bag.add(
                code,
                ARTIFACT_MANIFEST,
                f"{key}={value!r} supported={supported}",
            )

    required_complete = (
        "activation_id",
        "completion_status",
        "activation_timestamp_utc",
        "code_commit",
        "chroma_root",
        "collection",
        "collection_uuid",
        "active_unit_count",
        "historical_unit_count",
        "total_unit_count",
        "entity_baselines",
        "aggregate_baseline_digest",
        "shadow_ledger_identity",
        "ledger_header_hash",
        "starting_sequence",
        "manifest_canonical_hash",
        "hash_rules_version",
        "shadow_schema_version",
        "manifest_version",
    )
    # Accept baseline_id as legacy alias only if activation_id present elsewhere;
    # require activation_id for strict contract.
    for key in required_complete:
        if key == "activation_id":
            if activation_id is None:
                bag.add("manifest_incomplete", ARTIFACT_MANIFEST, "missing activation_id")
            continue
        if manifest.get(key) is None:
            bag.add("manifest_incomplete", ARTIFACT_MANIFEST, f"missing field {key}")

    if manifest.get("completion_status") != "complete":
        bag.add(
            "manifest_incomplete",
            ARTIFACT_MANIFEST,
            f"completion_status={manifest.get('completion_status')!r}",
        )

    # Type checks for counts / baselines
    entity_baselines = manifest.get("entity_baselines")
    if entity_baselines is not None and not isinstance(entity_baselines, dict):
        bag.add("manifest_corrupt", ARTIFACT_MANIFEST, "entity_baselines must be object")
        entity_baselines = None

    counts_ok = True
    for key in ("active_unit_count", "historical_unit_count", "total_unit_count", "starting_sequence"):
        value = manifest.get(key)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            bag.add("manifest_corrupt", ARTIFACT_MANIFEST, f"{key} type invalid")
            counts_ok = False
        elif value < 0:
            if key == "starting_sequence":
                bag.add(
                    "starting_sequence_invalid",
                    ARTIFACT_MANIFEST,
                    f"starting_sequence negative: {value}",
                )
            else:
                bag.add(
                    "baseline_count_invalid",
                    ARTIFACT_BASELINE,
                    f"{key} negative: {value}",
                )
            counts_ok = False

    if (
        counts_ok
        and isinstance(entity_baselines, dict)
        and all(
            isinstance(manifest.get(k), int) and not isinstance(manifest.get(k), bool)
            for k in ("active_unit_count", "historical_unit_count", "total_unit_count")
        )
    ):
        active = int(manifest["active_unit_count"])
        historical = int(manifest["historical_unit_count"])
        total = int(manifest["total_unit_count"])
        if total != len(entity_baselines):
            bag.add(
                "baseline_count_invalid",
                ARTIFACT_BASELINE,
                f"total_unit_count={total} entry_count={len(entity_baselines)}",
            )
        if active + historical != total:
            bag.add(
                "baseline_count_invalid",
                ARTIFACT_BASELINE,
                f"active+historical={active + historical} total={total}",
            )
        active_class = 0
        historical_class = 0
        for _eid, payload in entity_baselines.items():
            if not isinstance(payload, dict):
                bag.add(
                    "manifest_corrupt",
                    ARTIFACT_BASELINE,
                    "entity baseline entry type invalid",
                )
                continue
            classification = payload.get("classification")
            if classification not in ENTITY_CLASSIFICATIONS:
                bag.add(
                    "baseline_count_invalid",
                    ARTIFACT_BASELINE,
                    "entity classification invalid",
                )
                continue
            if classification == "active":
                active_class += 1
            else:
                historical_class += 1
            for hkey in ("document_hash", "metadata_hash", "state_hash"):
                hval = payload.get(hkey)
                if not isinstance(hval, str) or len(hval) != 64:
                    bag.add(
                        "baseline_hash_invalid",
                        ARTIFACT_BASELINE,
                        f"entity hash field invalid field={hkey}",
                    )
        if active_class != active or historical_class != historical:
            bag.add(
                "baseline_count_invalid",
                ARTIFACT_BASELINE,
                "classification counts disagree with declared counts",
            )

        expected_digest = compute_aggregate_baseline_digest(entity_baselines)
        declared = manifest.get("aggregate_baseline_digest")
        if declared != expected_digest:
            bag.add(
                "baseline_hash_invalid",
                ARTIFACT_BASELINE,
                "aggregate_baseline_digest mismatch",
            )

    # Canonical hash
    declared_hash = manifest.get("manifest_canonical_hash")
    if isinstance(declared_hash, str):
        expected_hash = compute_manifest_canonical_hash(manifest)
        if declared_hash != expected_hash:
            bag.add(
                "manifest_corrupt",
                ARTIFACT_MANIFEST,
                "manifest_canonical_hash mismatch",
            )
    elif declared_hash is not None:
        bag.add("manifest_corrupt", ARTIFACT_MANIFEST, "manifest_canonical_hash type invalid")

    # Collection identity
    collection = manifest.get("collection")
    if collection is not None and collection != COLLECTION_KNOWLEDGE_UNITS:
        bag.add(
            "collection_mismatch",
            ARTIFACT_COLLECTION,
            f"collection name {collection!r}",
        )
    manifest_root = manifest.get("chroma_root")
    if isinstance(manifest_root, str):
        if lexical_abspath(manifest_root) != lexical_abspath(chroma_dir):
            bag.add(
                "collection_mismatch",
                ARTIFACT_CHROMA,
                "manifest chroma_root identity mismatch",
            )

    # Code revision
    code_commit = manifest.get("code_commit")
    if runtime_code_revision is not None and code_commit is not None:
        if str(code_commit) != str(runtime_code_revision):
            bag.add(
                "code_revision_mismatch",
                ARTIFACT_CODE,
                "runtime code revision differs from manifest",
            )

    # Config binding
    if configured_activation_id is not None and activation_id is not None:
        if str(configured_activation_id) != str(activation_id):
            bag.add(
                "config_activation_mismatch",
                ARTIFACT_CONFIG,
                "config activation_id differs from manifest",
            )
    if configured_manifest_sha is not None and isinstance(declared_hash, str):
        if str(configured_manifest_sha) != declared_hash:
            bag.add(
                "config_activation_mismatch",
                ARTIFACT_CONFIG,
                "config manifest_sha256 differs from manifest_canonical_hash",
            )

    return activation_id


def _validate_ledger(
    path: Path,
    bag: _RefusalBag,
    *,
    expected_activation_id: str | None,
    expected_ledger_identity: str | None,
    expected_header_hash: str | None,
    expected_starting_sequence: int | None,
    require_present: bool,
) -> dict[str, Any] | None:
    if not path.exists():
        if require_present:
            bag.add("ledger_missing", ARTIFACT_LEDGER, "ledger file absent")
        return None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        bag.add("ledger_corrupt", ARTIFACT_LEDGER, f"ledger unreadable: {type(exc).__name__}")
        return None
    if not raw:
        bag.add("ledger_corrupt", ARTIFACT_LEDGER, "ledger empty")
        return None
    if not raw.endswith(b"\n"):
        bag.add("ledger_corrupt", ARTIFACT_LEDGER, "ledger truncated incomplete final line")
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        bag.add("ledger_corrupt", ARTIFACT_LEDGER, "ledger encoding invalid")
        return None

    lines = text.splitlines(keepends=True)
    header: dict[str, Any] | None = None
    sequences: list[int] = []
    for index, line in enumerate(lines):
        try:
            obj = parse_complete_jsonl_line(line if line.endswith("\n") else line + "\n")
        except (ValueError, json.JSONDecodeError):
            bag.add(
                "ledger_corrupt",
                ARTIFACT_LEDGER,
                f"ledger line corrupt index={index + 1}",
            )
            return header
        if index == 0:
            header = obj
            continue
        seq = obj.get("sequence")
        if not isinstance(seq, int) or isinstance(seq, bool):
            bag.add(
                "ledger_corrupt",
                ARTIFACT_LEDGER,
                f"event sequence type invalid index={index + 1}",
            )
            return header
        sequences.append(seq)
        if obj.get("shadow_schema_version") != SUPPORTED_SHADOW_SCHEMA_VERSION:
            bag.add(
                "ledger_corrupt",
                ARTIFACT_LEDGER,
                f"event schema unsupported index={index + 1}",
            )

    if header is None:
        bag.add("ledger_corrupt", ARTIFACT_LEDGER, "ledger header missing")
        return None

    if header.get("record_type") != LEDGER_HEADER_RECORD_TYPE:
        bag.add("ledger_corrupt", ARTIFACT_LEDGER, "ledger header record_type invalid")
    if header.get("shadow_schema_version") != SUPPORTED_SHADOW_SCHEMA_VERSION:
        bag.add("ledger_corrupt", ARTIFACT_LEDGER, "ledger header schema unsupported")
    for key in ("activation_id", "ledger_identity", "created_at_utc", "starting_sequence"):
        if header.get(key) is None:
            bag.add("ledger_corrupt", ARTIFACT_LEDGER, f"ledger header missing {key}")

    starting = header.get("starting_sequence")
    if isinstance(starting, bool) or not isinstance(starting, int) or starting < 0:
        bag.add(
            "starting_sequence_invalid",
            ARTIFACT_LEDGER,
            f"header starting_sequence invalid: {starting!r}",
        )
        starting = None
    elif expected_starting_sequence is not None and starting != expected_starting_sequence:
        bag.add(
            "starting_sequence_invalid",
            ARTIFACT_LEDGER,
            "header starting_sequence disagrees with manifest",
        )

    if expected_activation_id is not None and header.get("activation_id") != expected_activation_id:
        bag.add(
            "ledger_identity_mismatch",
            ARTIFACT_LEDGER,
            "ledger header activation_id mismatch",
        )
    if (
        expected_ledger_identity is not None
        and header.get("ledger_identity") != expected_ledger_identity
    ):
        bag.add(
            "ledger_identity_mismatch",
            ARTIFACT_LEDGER,
            "ledger header ledger_identity mismatch",
        )

    header_hash = compute_ledger_header_hash(header)
    if expected_header_hash is not None and header_hash != expected_header_hash:
        bag.add(
            "ledger_identity_mismatch",
            ARTIFACT_LEDGER,
            "ledger_header_hash mismatch",
        )

    if starting is not None and sequences:
        expected = starting + 1
        for seq in sequences:
            if seq != expected:
                bag.add(
                    "starting_sequence_invalid",
                    ARTIFACT_LEDGER,
                    "ledger event sequence noncontiguous",
                )
                break
            expected += 1
    return header


def _validate_live_collection(
    bag: _RefusalBag,
    *,
    chroma_dir: Path,
    manifest: Mapping[str, Any],
    uuid_provider: UuidFunc,
    mode: ValidationMode,
) -> None:
    declared_uuid = manifest.get("collection_uuid")
    if not isinstance(declared_uuid, str) or not declared_uuid:
        return
    try:
        live = uuid_provider(chroma_dir, COLLECTION_KNOWLEDGE_UNITS)
    except OSError:
        bag.add(
            "collection_unavailable",
            ARTIFACT_COLLECTION,
            "collection uuid unreadable",
        )
        return
    if live is None:
        # Prepare/writer need the collection; doctor still reports.
        if mode in {
            ValidationMode.WRITER,
            ValidationMode.PREPARE,
            ValidationMode.VERIFY,
        }:
            bag.add(
                "collection_unavailable",
                ARTIFACT_COLLECTION,
                "collection missing or uuid unavailable",
            )
        return
    if live != declared_uuid:
        bag.add(
            "collection_mismatch",
            ARTIFACT_COLLECTION,
            "immutable collection uuid mismatch",
        )


def _prepare_live_baseline_check(
    bag: _RefusalBag,
    *,
    chroma_dir: Path,
    manifest: Mapping[str, Any],
) -> None:
    """Prepare mode only: compare declared totals to live distinct IDs (count).

    Does not require live hashes to match after activation; prepare recomputes
    equality against the quiesced corpus. Entity hash recompute is out of scope
    unless entity documents are available read-only — count mismatch is enough
    to refuse prepare consistency here.
    """
    from chroma_readonly import collection_count

    total = manifest.get("total_unit_count")
    if not isinstance(total, int) or isinstance(total, bool):
        return
    try:
        live_count = collection_count(chroma_dir, COLLECTION_KNOWLEDGE_UNITS)
    except (OSError, FileNotFoundError):
        bag.add(
            "collection_unavailable",
            ARTIFACT_COLLECTION,
            "live baseline count unavailable",
        )
        return
    if live_count != total:
        bag.add(
            "baseline_count_invalid",
            ARTIFACT_BASELINE,
            f"prepare live count={live_count} manifest total={total}",
        )


def validate_shadow_activation(  # pylint: disable=too-many-arguments
    config_path: str | Path | None,
    chroma_dir: str | Path,
    mode: str | ValidationMode,
    *,
    cfg: Mapping[str, Any] | None = None,
    runtime_code_revision: str | None = None,
    expected_uid: int | None = None,
    lstat: StatFunc | None = None,
    collection_uuid_provider: UuidFunc | None = None,
    check_first_event: bool | None = None,
) -> ShadowValidationResult:
    """Validate Shadow activation artifacts under the strict C1 contract.

    Parameters
    ----------
    config_path:
        Path to a TOML config file, or None when ``cfg`` is provided.
    chroma_dir:
        Authoritative store root for this validation call.
    mode:
        One of writer / prepare / doctor / inventory / verify.
    """
    if not isinstance(mode, ValidationMode):
        mode = ValidationMode(str(mode))
    bag = _RefusalBag()
    facts: dict[str, Any] = {
        "mode": mode.value,
        "redacted": True,
    }
    euid = os.geteuid() if expected_uid is None else int(expected_uid)
    stat_fn: StatFunc = lstat or os.lstat
    uuid_fn: UuidFunc = collection_uuid_provider or readonly_collection_uuid
    chroma = lexical_abspath(chroma_dir)

    try:
        loaded = _load_cfg(config_path, cfg)
    except FileNotFoundError:
        bag.add("config_corrupt", ARTIFACT_CONFIG, "config path missing")
        return ShadowValidationResult(
            state=ShadowState.INVALID.value,
            inject_eligible=False,
            activation_id=None,
            refusals=bag.ordered(),
            facts=facts,
        )
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        bag.add(
            "config_corrupt",
            ARTIFACT_CONFIG,
            f"config unreadable: {type(exc).__name__}",
        )
        return ShadowValidationResult(
            state=ShadowState.INVALID.value,
            inject_eligible=False,
            activation_id=None,
            refusals=bag.ordered(),
            facts=facts,
        )

    settings = resolve_shadow_settings(loaded)
    # Prefer lexical paths for policy; settings.resolve() follows symlinks — re-read raw.
    section = loaded.get("shadow_ledger") if isinstance(loaded.get("shadow_ledger"), dict) else {}
    from shadow_ledger import DEFAULT_HEALTH_PATH, DEFAULT_LEDGER_PATH, DEFAULT_MANIFEST_PATH

    ledger_path = lexical_abspath(section.get("ledger_path", DEFAULT_LEDGER_PATH) if section else DEFAULT_LEDGER_PATH)
    manifest_path = lexical_abspath(
        section.get("activation_manifest_path", DEFAULT_MANIFEST_PATH)
        if section
        else DEFAULT_MANIFEST_PATH
    )
    health_path = lexical_abspath(
        section.get("health_path", DEFAULT_HEALTH_PATH) if section else DEFAULT_HEALTH_PATH
    )

    configured_root = None
    index = loaded.get("index")
    if isinstance(index, dict) and index.get("chroma_dir"):
        configured_root = lexical_abspath(index["chroma_dir"])
    if configured_root is not None and configured_root != chroma:
        bag.add(
            "collection_mismatch",
            ARTIFACT_CHROMA,
            "configured chroma_dir differs from validation chroma_dir",
        )

    configured_activation_id = None
    configured_manifest_sha = None
    if section:
        if section.get("activation_id") is not None:
            configured_activation_id = str(section.get("activation_id"))
        if section.get("manifest_sha256") is not None:
            configured_manifest_sha = str(section.get("manifest_sha256"))

    facts.update(
        {
            "enabled": settings.enabled,
            "ledger_name": ledger_path.name,
            "manifest_name": manifest_path.name,
            "health_name": health_path.name,
            "euid": euid,
        }
    )

    artifact_exists = any(p.exists() for p in (ledger_path, manifest_path, health_path))

    if not settings.enabled:
        if artifact_exists:
            # Prepared / leftover artifacts without committed enablement.
            bag.add(
                "prepared_not_committed",
                ARTIFACT_CONFIG,
                "shadow artifacts present while enabled=false",
            )
            refusals = bag.ordered()
            return ShadowValidationResult(
                state=ShadowState.PREPARED.value
                if not any(r.blocking and r.code != "prepared_not_committed" for r in refusals)
                else ShadowState.INVALID.value,
                inject_eligible=False,
                activation_id=configured_activation_id,
                refusals=refusals,
                facts=facts,
            )
        return ShadowValidationResult(
            state=ShadowState.DISABLED.value,
            inject_eligible=False,
            activation_id=None,
            refusals=(),
            facts=facts,
        )

    # Enabled path: full contract.
    require_committed_files = mode != ValidationMode.PREPARE
    _validate_path_policy(
        ledger_path=ledger_path,
        manifest_path=manifest_path,
        health_path=health_path,
        chroma_dir=chroma,
        bag=bag,
        lstat=stat_fn,
        euid=euid,
        require_files=require_committed_files,
    )

    manifest = None
    if manifest_path.exists():
        manifest = _load_manifest_strict(manifest_path, bag)
    elif require_committed_files:
        bag.add("manifest_missing", ARTIFACT_MANIFEST, "manifest file absent")

    activation_id = None
    if manifest is not None:
        activation_id = _validate_manifest_fields(
            manifest,
            bag,
            chroma_dir=chroma,
            runtime_code_revision=runtime_code_revision,
            configured_activation_id=configured_activation_id,
            configured_manifest_sha=configured_manifest_sha,
        )
        if activation_id:
            facts["activation_id"] = activation_id
            facts["manifest_sha256"] = manifest.get("manifest_canonical_hash")
            facts["collection_uuid"] = manifest.get("collection_uuid")
            facts["active_unit_count"] = manifest.get("active_unit_count")
            facts["total_unit_count"] = manifest.get("total_unit_count")

        if mode in {
            ValidationMode.WRITER,
            ValidationMode.PREPARE,
            ValidationMode.VERIFY,
            ValidationMode.DOCTOR,
            ValidationMode.INVENTORY,
        }:
            _validate_live_collection(
                bag,
                chroma_dir=chroma,
                manifest=manifest,
                uuid_provider=uuid_fn,
                mode=mode,
            )
        if mode == ValidationMode.PREPARE:
            _prepare_live_baseline_check(bag, chroma_dir=chroma, manifest=manifest)

    expected_identity = None
    expected_header_hash = None
    expected_starting = None
    if manifest is not None:
        expected_identity = manifest.get("shadow_ledger_identity")
        expected_header_hash = manifest.get("ledger_header_hash")
        if isinstance(manifest.get("starting_sequence"), int) and not isinstance(
            manifest.get("starting_sequence"), bool
        ):
            expected_starting = int(manifest["starting_sequence"])

    require_ledger = require_committed_files
    header = _validate_ledger(
        ledger_path,
        bag,
        expected_activation_id=activation_id,
        expected_ledger_identity=str(expected_identity) if expected_identity else None,
        expected_header_hash=str(expected_header_hash) if expected_header_hash else None,
        expected_starting_sequence=expected_starting,
        require_present=require_ledger,
    )
    if header is not None:
        facts["ledger_identity"] = header.get("ledger_identity")
        try:
            st = stat_fn(ledger_path)
            facts["ledger_inode"] = st.st_ino
            facts["ledger_dev"] = st.st_dev
        except OSError:
            pass

    if mode == ValidationMode.VERIFY or check_first_event:
        # Reserved first-event gates: header-only ledger lacks first event.
        if header is not None:
            # Count event lines
            try:
                text = ledger_path.read_text(encoding="utf-8")
                event_lines = max(0, len(text.splitlines()) - 1)
            except OSError:
                event_lines = 0
            if event_lines == 0:
                bag.add(
                    "first_event_missing",
                    ARTIFACT_LEDGER,
                    "verify mode requires first event",
                )

    refusals = bag.ordered()
    blocking = [r for r in refusals if r.blocking]
    inject_eligible = settings.enabled and not blocking
    if inject_eligible:
        state = ShadowState.COMMITTED.value
    else:
        state = ShadowState.INVALID.value

    # Safety: never inject on any C1 mechanical failure class.
    if any(
        r.code
        in {
            "manifest_missing",
            "manifest_corrupt",
            "manifest_version_unsupported",
            "manifest_incomplete",
            "collection_mismatch",
            "code_revision_mismatch",
            "baseline_count_invalid",
            "baseline_hash_invalid",
            "ledger_missing",
            "ledger_corrupt",
            "ledger_identity_mismatch",
            "starting_sequence_invalid",
            "path_collision",
            "path_inside_chroma",
            "path_not_private",
            "path_wrong_owner",
            "symlink_refused",
            "permission_invalid",
            "prepared_not_committed",
            "artifact_type_invalid",
            "directory_not_private",
            "config_activation_mismatch",
            "config_corrupt",
            "collection_unavailable",
        }
        for r in refusals
    ):
        inject_eligible = False

    return ShadowValidationResult(
        state=state if settings.enabled else ShadowState.DISABLED.value,
        inject_eligible=inject_eligible,
        activation_id=activation_id,
        refusals=refusals,
        facts=facts,
    )


def build_valid_manifest_fixture(  # pylint: disable=too-many-arguments
    *,
    activation_id: str,
    code_commit: str,
    chroma_root: str | Path,
    collection_uuid: str,
    entity_baselines: Mapping[str, Mapping[str, Any]] | None = None,
    shadow_ledger_identity: str,
    ledger_header_hash: str,
    starting_sequence: int = 0,
    configured_embed_model: str | None = "nomic-embed-text",
) -> dict[str, Any]:
    """Helper for tests/later prepare: construct a hash-consistent complete manifest."""
    baselines = {
        eid: dict(payload) for eid, payload in (entity_baselines or {}).items()
    }
    active = sum(1 for p in baselines.values() if p.get("classification") == "active")
    historical = sum(
        1 for p in baselines.values() if p.get("classification") == "historical"
    )
    total = len(baselines)
    manifest: dict[str, Any] = {
        "manifest_version": SUPPORTED_MANIFEST_VERSION,
        "shadow_schema_version": SUPPORTED_SHADOW_SCHEMA_VERSION,
        "hash_rules_version": SUPPORTED_HASH_RULES_VERSION,
        "activation_id": activation_id,
        "baseline_id": activation_id,
        "completion_status": "complete",
        "activation_timestamp_utc": "2026-07-28T00:00:00Z",
        "code_commit": code_commit,
        "chroma_root": str(lexical_abspath(chroma_root)),
        "collection": COLLECTION_KNOWLEDGE_UNITS,
        "collection_uuid": collection_uuid,
        "active_unit_count": active,
        "historical_unit_count": historical,
        "total_unit_count": total,
        "entity_baselines": baselines,
        "aggregate_baseline_digest": compute_aggregate_baseline_digest(baselines),
        "configured_embed_model": configured_embed_model,
        "observed_embed_model": "unknown",
        "observed_embed_dimensions": None,
        "shadow_ledger_identity": shadow_ledger_identity,
        "ledger_header_hash": ledger_header_hash,
        "starting_sequence": starting_sequence,
    }
    manifest["manifest_canonical_hash"] = compute_manifest_canonical_hash(manifest)
    return manifest
