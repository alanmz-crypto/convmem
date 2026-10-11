"""Pure Codex rollout admission predicate for guarded incremental routing."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from adapters.detect import detect_format
from adapters.jsonl_prefix import prefix_boundary

ADMISSION_SKEW_SECONDS = 120
DEFAULT_MAX_TRANSFORM_CHUNKS_PER_RUN = 20
DEFAULT_MAX_SOURCE_BYTES = 256 * 1024 * 1024

ROLLOUT_BASENAME_RE = re.compile(
    r"^rollout-(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}-\d{2}-\d{2})-"
    r"(?P<uuid>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\.jsonl$"
)


@dataclass(frozen=True)
class CodexRolloutAdmissionSettings:
    root: Path
    admitted_after: datetime
    max_transform_chunks_per_run: int
    max_source_bytes: int


def make_uuid7(unix_ms: int, *, rand: int = 0) -> uuid.UUID:
    """Construct a UUIDv7 for hermetic tests (Python 3.13 lacks uuid.uuid7)."""
    unix_ms &= (1 << 48) - 1
    rand_a = rand & ((1 << 12) - 1)
    rand_b = (rand >> 12) & ((1 << 62) - 1)
    value = unix_ms << 80
    value |= 0x7 << 76
    value |= rand_a << 64
    value |= 0x2 << 62
    value |= rand_b
    return uuid.UUID(int=value)


def uuid7_unix_ms(uid: uuid.UUID) -> int:
    return uid.int >> 80


def parse_rollout_basename(path: Path) -> tuple[uuid.UUID, datetime]:
    """Parse rollout filename uuid and local naive timestamp."""
    match = ROLLOUT_BASENAME_RE.match(path.name)
    if not match:
        raise ValueError("rollout basename mismatch")
    uid = uuid.UUID(match.group("uuid"))
    stamp = f"{match.group('date')}T{match.group('time').replace('-', ':')}"
    return uid, datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S")


def _canonical_path_no_symlink(path: Path) -> Path:
    candidate = path.expanduser().absolute()
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink component")
    return candidate.resolve(strict=False)


def _strictly_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return path != root


def admits_path_checks_1_4(
    settings: CodexRolloutAdmissionSettings,
    path_key: str,
    detected_format: str | None,
) -> bool:
    if detected_format != "jsonl_codex_rollout":
        return False
    try:
        path = _canonical_path_no_symlink(Path(path_key))
        root = _canonical_path_no_symlink(settings.root)
    except (OSError, ValueError):
        return False
    if not _strictly_under(path, root):
        return False
    try:
        uid, filename_local = parse_rollout_basename(path)
    except ValueError:
        return False
    if uid.version != 7:
        return False
    local_tz = datetime.now().astimezone().tzinfo
    filename_aware = filename_local.replace(tzinfo=local_tz)
    uuid_ts = uuid7_unix_ms(uid) / 1000.0
    if abs(filename_aware.timestamp() - uuid_ts) > ADMISSION_SKEW_SECONDS:
        return False
    uuid_dt = datetime.fromtimestamp(uuid_ts, tz=timezone.utc)
    if uuid_dt < settings.admitted_after:
        return False
    return True


def first_complete_json_record(raw_prefix: bytes) -> dict | None:
    boundary = prefix_boundary(raw_prefix)
    prefix = raw_prefix[:boundary]
    offset = 0
    for line in prefix.splitlines(keepends=True):
        end = offset + len(line)
        stripped = line.strip()
        offset = end
        if not stripped:
            continue
        try:
            record = json.loads(stripped.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if isinstance(record, dict):
            return record
        return None
    return None


def _parse_session_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def verify_session_meta_identity(path: Path, raw_prefix: bytes) -> str | None:
    """Return a refusal outcome when D1 check 5 fails, else None."""
    try:
        uid, filename_local = parse_rollout_basename(path)
    except ValueError:
        return "codex_session_identity_mismatch"
    record = first_complete_json_record(raw_prefix)
    if not isinstance(record, dict) or record.get("type") != "session_meta":
        return "codex_session_identity_mismatch"
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return "codex_session_identity_mismatch"
    if str(payload.get("id")) != str(uid):
        return "codex_session_identity_mismatch"
    meta_ts = _parse_session_timestamp(payload.get("timestamp"))
    if meta_ts is None:
        return "codex_session_identity_mismatch"
    local_tz = datetime.now().astimezone().tzinfo
    filename_aware = filename_local.replace(tzinfo=local_tz)
    uuid_ts = uuid7_unix_ms(uid) / 1000.0
    if abs(meta_ts.timestamp() - uuid_ts) > ADMISSION_SKEW_SECONDS:
        return "codex_session_identity_mismatch"
    if abs(filename_aware.timestamp() - uuid_ts) > ADMISSION_SKEW_SECONDS:
        return "codex_session_identity_mismatch"
    return None


def is_production_source_granted(
    *,
    path_key: str,
    live_sources: tuple[str, ...],
    admission: CodexRolloutAdmissionSettings | None,
    detected_format: str | None,
) -> bool:
    if path_key in live_sources:
        return True
    if admission is None:
        return False
    return admits_path_checks_1_4(admission, path_key, detected_format)


def detect_format_for_path(path: str) -> str | None:
    return detect_format(path)
