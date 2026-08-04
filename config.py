# pylint: disable=duplicate-code
"""Load convmem configuration and perform the bounded Shadow config commit."""

import errno
import hashlib
import json
import os
import re
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from shadow_authorization import open_directory_nofollow

CONFIG_PATH = Path(
    os.environ.get("CONVMEM_CONFIG", "~/.config/convmem/config.toml")
).expanduser()

# Keys whose string values are filesystem paths and should be expanduser()'d.
_PATH_KEYS = {
    "chroma_dir",
    "processed_log",
    "units_export",
    "inventory",
    # Phase 0 shadow ledger (optional [shadow_ledger] table)
    "ledger_path",
    "activation_manifest_path",
    "health_path",
}

SUPPORTED_SHADOW_CONFIG_FILESYSTEMS = frozenset({"ext4", "xfs", "btrfs", "tmpfs"})
_SHADOW_HEADER_RE = re.compile(r"^\s*\[shadow_ledger\]\s*(?:#.*)?$")
_ANY_TABLE_RE = re.compile(r"^\s*\[\[?[^\]]+\]\]?\s*(?:#.*)?$")
_TOML_KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")


class ShadowConfigUpdateRefused(RuntimeError):
    """A config transaction refusal with stable code and commit knowledge."""

    def __init__(self, code: str, detail: str, *, committed: bool = False):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.committed = committed


@dataclass(frozen=True)
class ShadowConfigCandidate:
    data: bytes
    parsed: Mapping[str, Any]
    preimage_sha256: str
    candidate_sha256: str


@dataclass(frozen=True)
class ShadowConfigUpdateResult:
    preimage_sha256: str
    committed_sha256: str
    parsed: Mapping[str, Any]


def _toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "[" + ", ".join(json.dumps(item, ensure_ascii=False) for item in value) + "]"
    raise ShadowConfigUpdateRefused(
        "config_corrupt", "shadow_ledger contains an unsupported TOML value"
    )


def _parse_config_bytes(data: bytes) -> dict[str, Any]:
    try:
        parsed = tomllib.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ShadowConfigUpdateRefused("config_corrupt", "config TOML is invalid") from exc
    if not isinstance(parsed, dict):
        raise ShadowConfigUpdateRefused("config_corrupt", "config must be a TOML table")
    return parsed


def render_shadow_config_update(
    current: bytes,
    *,
    replacements: Mapping[str, Any],
    expected_enabled: bool,
) -> ShadowConfigCandidate:
    """Replace only the existing shadow_ledger table and prove semantic isolation."""
    parsed_before = _parse_config_bytes(current)
    existing = parsed_before.get("shadow_ledger")
    if not isinstance(existing, dict):
        raise ShadowConfigUpdateRefused(
            "config_corrupt", "existing [shadow_ledger] table is required"
        )
    if existing.get("enabled", False) is not expected_enabled:
        raise ShadowConfigUpdateRefused(
            "config_changed", "shadow enabled precondition changed"
        )
    for key in replacements:
        if not _TOML_KEY_RE.fullmatch(str(key)):
            raise ShadowConfigUpdateRefused("config_corrupt", "invalid shadow config key")

    try:
        text = current.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ShadowConfigUpdateRefused("config_corrupt", "config is not UTF-8") from exc
    lines = text.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if _SHADOW_HEADER_RE.fullmatch(line.rstrip("\r\n"))]
    if len(starts) != 1:
        raise ShadowConfigUpdateRefused(
            "config_corrupt", "config must contain exactly one [shadow_ledger] table"
        )
    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        candidate = lines[index].rstrip("\r\n")
        if _ANY_TABLE_RE.fullmatch(candidate):
            end = index
            break

    target = dict(existing)
    target.update(dict(replacements))
    newline = "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"
    rendered = [lines[start] if lines[start].endswith(("\n", "\r\n")) else lines[start] + newline]
    for key in sorted(target):
        if not _TOML_KEY_RE.fullmatch(str(key)):
            raise ShadowConfigUpdateRefused(
                "config_corrupt", "shadow_ledger contains an unsupported key"
            )
        rendered.append(f"{key} = {_toml_scalar(target[key])}{newline}")
    if end < len(lines) and rendered[-1].strip():
        rendered.append(newline)
    candidate_text = "".join(lines[:start] + rendered + lines[end:])
    candidate_data = candidate_text.encode("utf-8")
    parsed_after = _parse_config_bytes(candidate_data)

    before_other = {key: value for key, value in parsed_before.items() if key != "shadow_ledger"}
    after_other = {key: value for key, value in parsed_after.items() if key != "shadow_ledger"}
    if before_other != after_other or parsed_after.get("shadow_ledger") != target:
        raise ShadowConfigUpdateRefused(
            "config_changed", "semantic diff escaped the shadow_ledger table"
        )
    return ShadowConfigCandidate(
        data=candidate_data,
        parsed=parsed_after,
        preimage_sha256=hashlib.sha256(current).hexdigest(),
        candidate_sha256=hashlib.sha256(candidate_data).hexdigest(),
    )


def _unescape_mount_path(value: str) -> str:
    for escaped, literal in (("\\040", " "), ("\\011", "\t"), ("\\012", "\n"), ("\\134", "\\")):
        value = value.replace(escaped, literal)
    return value


def filesystem_type_for_path(path: str | Path, mountinfo_text: str) -> str | None:
    """Resolve the longest matching mount and return its filesystem type."""
    target = os.path.abspath(os.path.expanduser(str(path)))
    best: tuple[int, str] | None = None
    for line in mountinfo_text.splitlines():
        if " - " not in line:
            continue
        before, after = line.split(" - ", 1)
        fields = before.split()
        after_fields = after.split()
        if len(fields) < 5 or not after_fields:
            continue
        mountpoint = _unescape_mount_path(fields[4])
        if target == mountpoint or target.startswith(mountpoint.rstrip("/") + "/"):
            size = len(mountpoint)
            best_size = best[0] if best is not None else -1
            if size > best_size:
                best = (size, after_fields[0])
    return best[1] if best else None


def _read_fd_all(fd: int) -> bytes:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)


def atomic_shadow_config_update(  # pylint: disable=too-many-arguments
    config_path: Path | str,
    *,
    expected_preimage_sha256: str,
    replacements: Mapping[str, Any],
    expected_enabled: bool,
    mountinfo_text: str | None = None,
    replace: Callable[..., None] = os.replace,
    fsync: Callable[[int], None] = os.fsync,
) -> ShadowConfigUpdateResult:
    """Commit one shadow-table update through same-device atomic replacement."""
    target = Path(os.path.abspath(os.path.expanduser(str(config_path))))
    try:
        parent_fd = open_directory_nofollow(target.parent)
    except Exception as exc:
        raise ShadowConfigUpdateRefused(
            "config_corrupt", "config parent missing or contains a symlink"
        ) from exc
    source_fd = -1
    temp_fd = -1
    temp_name: str | None = None
    replaced = False
    try:
        flags = os.O_RDONLY | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            source_fd = os.open(target.name, flags, dir_fd=parent_fd)
        except OSError as exc:
            raise ShadowConfigUpdateRefused("config_corrupt", "config cannot be opened") from exc
        source_st = os.fstat(source_fd)
        if (
            not stat.S_ISREG(source_st.st_mode)
            or source_st.st_nlink != 1
            or source_st.st_uid != os.geteuid()
        ):
            raise ShadowConfigUpdateRefused(
                "config_corrupt", "config must be a current-user regular file"
            )
        current = _read_fd_all(source_fd)
        candidate = render_shadow_config_update(
            current, replacements=replacements, expected_enabled=expected_enabled
        )
        if candidate.preimage_sha256 != expected_preimage_sha256:
            raise ShadowConfigUpdateRefused("config_changed", "config preimage changed")

        if mountinfo_text is None:
            try:
                mountinfo_text = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
            except OSError as exc:
                raise ShadowConfigUpdateRefused(
                    "config_filesystem_unsupported", "mount classification unavailable"
                ) from exc
        filesystem = filesystem_type_for_path(target, mountinfo_text)
        if filesystem not in SUPPORTED_SHADOW_CONFIG_FILESYSTEMS:
            raise ShadowConfigUpdateRefused(
                "config_filesystem_unsupported", "config filesystem is not approved"
            )

        temp_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            temp_flags |= os.O_NOFOLLOW
        for _attempt in range(100):
            candidate_name = f".{target.name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
            try:
                temp_fd = os.open(
                    candidate_name,
                    temp_flags,
                    stat.S_IMODE(source_st.st_mode),
                    dir_fd=parent_fd,
                )
                temp_name = candidate_name
                break
            except FileExistsError:
                continue
        if temp_fd < 0 or temp_name is None:
            raise ShadowConfigUpdateRefused(
                "config_changed", "cannot allocate config temporary file"
            )
        temp_st = os.fstat(temp_fd)
        if temp_st.st_dev != source_st.st_dev:
            raise ShadowConfigUpdateRefused(
                "config_cross_device", "config temporary file is on another device"
            )
        os.fchmod(temp_fd, stat.S_IMODE(source_st.st_mode))
        view = memoryview(candidate.data)
        offset = 0
        while offset < len(view):
            written = os.write(temp_fd, view[offset:])
            if written <= 0:
                raise OSError("config temporary write made no progress")
            offset += written
        fsync(temp_fd)
        os.close(temp_fd)
        temp_fd = -1

        # Compare the live dirent immediately before replacement.
        check_fd = os.open(target.name, flags, dir_fd=parent_fd)
        try:
            check_st = os.fstat(check_fd)
            check_data = _read_fd_all(check_fd)
        finally:
            os.close(check_fd)
        if (
            (check_st.st_dev, check_st.st_ino) != (source_st.st_dev, source_st.st_ino)
            or hashlib.sha256(check_data).hexdigest() != expected_preimage_sha256
        ):
            raise ShadowConfigUpdateRefused("config_changed", "config changed before commit")

        try:
            replace(temp_name, target.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                raise ShadowConfigUpdateRefused(
                    "config_cross_device", "atomic config replace crossed devices"
                ) from exc
            raise
        replaced = True
        temp_name = None
        try:
            fsync(parent_fd)
        except OSError as exc:
            raise ShadowConfigUpdateRefused(
                "config_changed", "config replace durability is uncertain", committed=True
            ) from exc
        return ShadowConfigUpdateResult(
            preimage_sha256=candidate.preimage_sha256,
            committed_sha256=candidate.candidate_sha256,
            parsed=candidate.parsed,
        )
    finally:
        if source_fd >= 0:
            os.close(source_fd)
        if temp_fd >= 0:
            os.close(temp_fd)
        if temp_name is not None and not replaced:
            try:
                os.unlink(temp_name, dir_fd=parent_fd)
            except OSError:
                pass
        os.close(parent_fd)


def _expand(value):
    if isinstance(value, str):
        return str(Path(value).expanduser())
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def parse_env_file(path: Path | str) -> dict[str, str]:
    """Parse KEY=VALUE and export KEY=VALUE lines from a shell env file."""
    env: dict[str, str] = {}
    path = Path(path)
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        if stripped.startswith("export "):
            stripped = stripped[7:]
        key, _, val = stripped.partition("=")
        key = key.strip()
        val = val.strip().strip("\"'")
        if key:
            env[key] = val
    return env


def resolve_deepseek_key() -> str:
    """DEEPSEEK_API_KEY from os.environ, then ~/.config/convmem/env.{local,systemd}."""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    cfg_dir = Path("~/.config/convmem").expanduser()
    for fname in ("env.local", "env.systemd"):
        parsed = parse_env_file(cfg_dir / fname)
        key = parsed.get("DEEPSEEK_API_KEY", "").strip()
        if key:
            return key
    return ""


def resolve_tokenrouter_key() -> str:
    """TOKENROUTER_API_KEY from os.environ, env.local.d/tokenrouter.env, env.local, env.systemd."""
    key = os.environ.get("TOKENROUTER_API_KEY", "").strip()
    if key:
        return key
    cfg_dir = Path("~/.config/convmem").expanduser()
    for fname in ("env.local.d/tokenrouter.env", "env.local", "env.systemd"):
        parsed = parse_env_file(cfg_dir / fname)
        key = parsed.get("TOKENROUTER_API_KEY", "").strip()
        if key:
            return key
    return ""


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    """Read the TOML config and expand user paths in known fields."""
    path = Path(path).expanduser()
    if not path.exists():
        raise FileNotFoundError(
            f"Config not found at {path}. Create it from the convmem template."
        )
    with open(path, "rb") as f:
        cfg = tomllib.load(f)

    # Expand the source paths list.
    if "sources" in cfg and isinstance(cfg["sources"].get("paths"), list):
        cfg["sources"]["paths"] = _expand(cfg["sources"]["paths"])

    # Expand any path-like scalar fields wherever they appear.
    for section in cfg.values():
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            if key in _PATH_KEYS:
                section[key] = _expand(value)

    return cfg


if __name__ == "__main__":
    print(json.dumps(load_config(), indent=2))
