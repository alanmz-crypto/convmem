# pylint: disable=too-many-lines
"""Closed repository-knowledge scope, Git-clean byte authority, and tri-state classification."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Literal, Mapping

ADAPTER_CONTRACT_VERSION = "repository_knowledge_v1"
SOURCE_TYPE = "repository_knowledge_v1"
MANIFEST_ID = "openclaw-watch-scope-v1"
SCHEMA_ID = "openclaw-watch-scope-v1"
BLOCKED_FORMAT = "repository_knowledge_blocked"
ELIGIBLE_FORMAT = "repository_knowledge_v1"

MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_INCLUDED_FILES = 512
MAX_CLASSIFICATION_ENTRIES = 2048
MAX_INCLUDED_BYTES = 64 * 1024 * 1024
MAX_CHUNK_CHARS = 6000
FALLBACK_WINDOW_LINES = 120
OVERLAP_LINES = 20
MAX_CHUNKS_PER_FILE = 256
MAX_CONFIGURED_MANIFESTS = 4
MANIFEST_POLL_SECONDS = 30

LIMITS = {
    "max_file_bytes": MAX_FILE_BYTES,
    "max_included_files": MAX_INCLUDED_FILES,
    "max_classification_entries": MAX_CLASSIFICATION_ENTRIES,
    "max_included_bytes": MAX_INCLUDED_BYTES,
    "max_chunk_chars": MAX_CHUNK_CHARS,
    "fallback_window_lines": FALLBACK_WINDOW_LINES,
    "overlap_lines": OVERLAP_LINES,
    "max_chunks_per_file": MAX_CHUNKS_PER_FILE,
    "max_configured_manifests": MAX_CONFIGURED_MANIFESTS,
    "manifest_poll_seconds": MANIFEST_POLL_SECONDS,
}

CONTENT_CLASS_SUFFIXES = {
    "markdown": (".md",),
    "python": (".py",),
    "javascript": (".js", ".mjs"),
    "json": (".json",),
    "toml": (".toml",),
    "text": (".txt", ".sh"),
}

PARSER_MODE_FOR_CLASS = {
    "markdown": "markdown_heading_sections",
    "python": "python_ast_spans",
    "javascript": "javascript_line_windows",
    "json": "json_pointer_groups",
    "toml": "toml_table_spans",
    "text": "text_line_windows",
}

DetectState = Literal["outside", "eligible", "blocked"]
ClassificationClass = Literal["include", "exclude", "unrelated"]

_GIT_TIMEOUT_SECONDS = 15.0
_GIT_MAX_OUTPUT = 16 * 1024 * 1024
_PATH_RE = re.compile(
    r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$"
)

SCHEMA_RELPATH = "config/repository-knowledge/openclaw-watch-scope-v1.schema.json"


class ScopeError(RuntimeError):
    """Repository-knowledge scope refused a path or manifest."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


class ManifestValidationError(ScopeError):
    """Schema or closed-contract validation failed."""

    def __init__(self, detail: str):
        super().__init__("manifest_invalid", detail)


@dataclass(frozen=True)
class Classification:
    path: str
    klass: ClassificationClass
    reason: str


@dataclass(frozen=True)
class IncludeEntry:
    path: str
    sha256: str
    content_class: str
    parser_mode: str
    adapter_contract_version: str
    source_type: str
    required_state: str
    reviewed_state: str
    owner: str
    freshness_role: str
    retrieval_needles: tuple[str, ...]
    sensitivity: str


@dataclass(frozen=True)
class RetireRecord:
    path: str
    prior_file_sha256: str
    prior_manifest_sha256: str
    reason: str
    replacement_path: str | None = None


@dataclass(frozen=True)
class RequiredWhenPresent:
    path: str
    reason: str
    origin: str


@dataclass(frozen=True)
class LoadedManifest:
    path: Path
    root: Path
    identity: str
    data: dict[str, Any]
    classifications: dict[str, Classification]
    entries: dict[str, IncludeEntry]
    exclusion_rules: tuple[dict[str, Any], ...]
    required_when_present: tuple[RequiredWhenPresent, ...]
    retire: tuple[RetireRecord, ...]
    git_head: str


@dataclass(frozen=True)
class PathDecision:
    state: DetectState
    code: str
    detail: str
    relpath: str | None = None
    entry: IncludeEntry | None = None
    root: Path | None = None
    manifest: LoadedManifest | None = None
    git_commit: str | None = None
    file_sha256: str | None = None


_configured_manifest_paths: tuple[str, ...] = ()
_loaded_by_path: dict[str, LoadedManifest | BaseException] = {}


def reset_configuration() -> None:
    """Drop configured manifests and cached validated roots (tests / watch restart)."""
    global _configured_manifest_paths, _loaded_by_path
    _configured_manifest_paths = ()
    _loaded_by_path = {}


def configure_manifests(paths: Iterable[str]) -> None:
    """Replace the configured manifest set. Empty means every path is outside."""
    global _configured_manifest_paths, _loaded_by_path
    abs_paths: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        text = str(raw or "").strip()
        if not text:
            continue
        resolved = str(Path(text).expanduser())
        if resolved in seen:
            continue
        seen.add(resolved)
        abs_paths.append(resolved)
    if len(abs_paths) > MAX_CONFIGURED_MANIFESTS:
        raise ScopeError(
            "too_many_manifests",
            f"at most {MAX_CONFIGURED_MANIFESTS} manifests may be configured",
        )
    _configured_manifest_paths = tuple(abs_paths)
    _loaded_by_path = {}


def configured_manifest_paths() -> tuple[str, ...]:
    return _configured_manifest_paths


def manifests_from_cfg(cfg: Mapping[str, Any] | None) -> list[str]:
    watch = (cfg or {}).get("watch") or {}
    raw = watch.get("repository_knowledge_manifests") or []
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ScopeError(
            "config_invalid",
            "watch.repository_knowledge_manifests must be a list of strings",
        )
    return [str(Path(item).expanduser()) for item in raw]


def apply_config(cfg: Mapping[str, Any] | None) -> None:
    configure_manifests(manifests_from_cfg(cfg))


def schema_path_for(manifest_path: Path) -> Path:
    return Path(__file__).resolve().parent / SCHEMA_RELPATH


def load_schema(schema_file: Path | None = None) -> dict[str, Any]:
    path = schema_file or schema_path_for(Path("."))
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestValidationError(f"cannot read schema {path}: {exc}") from exc
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"schema is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestValidationError("schema root must be an object")
    return data


def _ptr(path: list[str | int]) -> str:
    if not path:
        return "/"
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in path)


def _validate_against_schema(instance: Any, schema: Mapping[str, Any], *, root: Mapping[str, Any], path: list[str | int]) -> None:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        if not ref.startswith("#/$defs/"):
            raise ManifestValidationError(f"{_ptr(path)} unsupported $ref {ref}")
        name = ref.split("/")[-1]
        defs = root.get("$defs")
        if not isinstance(defs, dict) or name not in defs:
            raise ManifestValidationError(f"{_ptr(path)} missing $defs {name}")
        _validate_against_schema(instance, defs[name], root=root, path=path)
        return
    if "const" in schema and instance != schema["const"]:
        raise ManifestValidationError(f"{_ptr(path)} must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise ManifestValidationError(f"{_ptr(path)} not in enum")
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(instance, dict):
            raise ManifestValidationError(f"{_ptr(path)} must be an object")
        required = schema.get("required") or []
        for key in required:
            if key not in instance:
                raise ManifestValidationError(f"{_ptr(path)} missing {key}")
        props = schema.get("properties") or {}
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                _validate_against_schema(value, props[key], root=root, path=path + [key])
            elif additional is False:
                raise ManifestValidationError(f"{_ptr(path)} unexpected property {key}")
        if "minProperties" in schema and len(instance) < int(schema["minProperties"]):
            raise ManifestValidationError(f"{_ptr(path)} too few properties")
        if "maxProperties" in schema and len(instance) > int(schema["maxProperties"]):
            raise ManifestValidationError(f"{_ptr(path)} too many properties")
        return
    if expected == "array":
        if not isinstance(instance, list):
            raise ManifestValidationError(f"{_ptr(path)} must be an array")
        if "minItems" in schema and len(instance) < int(schema["minItems"]):
            raise ManifestValidationError(f"{_ptr(path)} too few items")
        if "maxItems" in schema and len(instance) > int(schema["maxItems"]):
            raise ManifestValidationError(f"{_ptr(path)} too many items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(instance):
                _validate_against_schema(item, item_schema, root=root, path=path + [idx])
        if schema.get("uniqueItems") and len(instance) != len(set(json.dumps(x, sort_keys=True) for x in instance)):
            raise ManifestValidationError(f"{_ptr(path)} items must be unique")
        return
    if expected == "string":
        if not isinstance(instance, str):
            raise ManifestValidationError(f"{_ptr(path)} must be a string")
        if "minLength" in schema and len(instance) < int(schema["minLength"]):
            raise ManifestValidationError(f"{_ptr(path)} shorter than minLength")
        if "maxLength" in schema and len(instance) > int(schema["maxLength"]):
            raise ManifestValidationError(f"{_ptr(path)} longer than maxLength")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, instance) is None:
            raise ManifestValidationError(f"{_ptr(path)} does not match pattern")
        return
    if expected == "integer":
        if type(instance) is not int:  # noqa: E721 — bool is a subclass of int
            raise ManifestValidationError(f"{_ptr(path)} must be an integer")
        if "minimum" in schema and instance < int(schema["minimum"]):
            raise ManifestValidationError(f"{_ptr(path)} below minimum")
        if "maximum" in schema and instance > int(schema["maximum"]):
            raise ManifestValidationError(f"{_ptr(path)} above maximum")
        return
    if expected == "number":
        if not isinstance(instance, (int, float)) or isinstance(instance, bool):
            raise ManifestValidationError(f"{_ptr(path)} must be a number")
        return
    if expected == "boolean":
        if not isinstance(instance, bool):
            raise ManifestValidationError(f"{_ptr(path)} must be a boolean")
        return
    if expected == "null":
        if instance is not None:
            raise ManifestValidationError(f"{_ptr(path)} must be null")


def validate_manifest_document(data: Any, schema: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ManifestValidationError("manifest root must be an object")
    schema = schema or load_schema()
    _validate_against_schema(data, schema, root=schema, path=[])
    if data.get("limits") != LIMITS:
        raise ManifestValidationError("limits must match frozen v1 constants")
    paths = [row["path"] for row in data["classifications"]]
    if len(paths) != len(set(paths)):
        raise ManifestValidationError("duplicate classification path")
    folded = [path.casefold() for path in paths]
    if len(folded) != len(set(folded)):
        raise ManifestValidationError("classification case-fold collision")
    entry_paths = [row["path"] for row in data["entries"]]
    if len(entry_paths) != len(set(entry_paths)):
        raise ManifestValidationError("duplicate include path")
    class_by_path = {row["path"]: row["class"] for row in data["classifications"]}
    for entry in data["entries"]:
        klass = class_by_path.get(entry["path"])
        if klass != "include":
            raise ManifestValidationError(
                f"include entry {entry['path']} is not classified include"
            )
        expected_mode = PARSER_MODE_FOR_CLASS[entry["content_class"]]
        if entry["parser_mode"] != expected_mode:
            raise ManifestValidationError(
                f"{entry['path']} parser_mode must be {expected_mode}"
            )
        suffixes = CONTENT_CLASS_SUFFIXES[entry["content_class"]]
        if not entry["path"].endswith(suffixes):
            raise ManifestValidationError(
                f"{entry['path']} suffix does not match {entry['content_class']}"
            )
    rule_ids = [row["id"] for row in data["exclusion_rules"]]
    if set(rule_ids) != {
        "credentials",
        "authority_private",
        "live_data_stores",
        "vcs_caches_build",
        "generated_duplicates",
        "unrelated_material",
    }:
        raise ManifestValidationError("exclusion_rules must declare the six closed classes")
    if len(data["classifications"]) > MAX_CLASSIFICATION_ENTRIES:
        raise ManifestValidationError("too many classification entries")
    if len(data["entries"]) > MAX_INCLUDED_FILES:
        raise ManifestValidationError("too many include entries")
    return data


def _run_git(args: list[str], *, cwd: Path, timeout: float = _GIT_TIMEOUT_SECONDS) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ScopeError("git_failed", f"git {args[0]} failed: {exc}") from exc
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or b"").decode("utf-8", "replace").strip()
        raise ScopeError("git_failed", err or f"git {args[0]} exit {completed.returncode}")
    output = completed.stdout or b""
    if len(output) > _GIT_MAX_OUTPUT:
        raise ScopeError("git_failed", "git output exceeded bound")
    return output


def git_toplevel(cwd: Path) -> Path:
    raw = _run_git(["rev-parse", "--show-toplevel"], cwd=cwd).decode("utf-8").strip()
    return Path(raw)


def git_head(cwd: Path) -> str:
    return _run_git(["rev-parse", "HEAD"], cwd=cwd).decode("utf-8").strip()


def git_ls_files(cwd: Path) -> list[str]:
    raw = _run_git(["ls-files", "-z"], cwd=cwd)
    paths = [item.decode("utf-8") for item in raw.split(b"\0") if item]
    return paths


def committed_bytes(cwd: Path, relpath: str) -> bytes:
    return _run_git(["show", f"HEAD:{relpath}"], cwd=cwd)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _is_symlink(path: Path) -> bool:
    try:
        return path.is_symlink()
    except OSError:
        return False


def reject_symlink_components(root: Path, target: Path) -> None:
    try:
        root_resolved = root.resolve(strict=True)
    except OSError as exc:
        raise ScopeError("path_escape", f"cannot resolve root {root}: {exc}") from exc
    current = Path(root_resolved.anchor)
    parts = root_resolved.parts[1:]
    for part in parts:
        current = current / part
        if _is_symlink(current):
            raise ScopeError("symlink", f"symlink component in root: {current}")
    rel_parts = target.parts[len(root_resolved.parts) :] if _is_relative_to(target, root_resolved) else target.parts
    cursor = root_resolved
    for part in rel_parts:
        cursor = cursor / part
        if _is_symlink(cursor):
            raise ScopeError("symlink", f"symlink component: {cursor}")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_under_root(root: Path, relpath: str) -> Path:
    if not _PATH_RE.match(relpath):
        raise ScopeError("path_escape", f"illegal repo-relative path {relpath!r}")
    if relpath.startswith("/") or relpath.endswith("/") or "\\" in relpath:
        raise ScopeError("path_escape", f"illegal repo-relative path {relpath!r}")
    candidate = (root / relpath)
    reject_symlink_components(root, candidate)
    try:
        resolved = candidate.resolve(strict=False)
        root_resolved = root.resolve(strict=True)
    except OSError as exc:
        raise ScopeError("path_escape", str(exc)) from exc
    if not _is_relative_to(resolved, root_resolved):
        raise ScopeError("path_escape", f"{relpath} escapes {root}")
    return resolved


def path_is_tracked(cwd: Path, relpath: str) -> bool:
    try:
        _run_git(["ls-files", "--error-unmatch", "--", relpath], cwd=cwd)
        return True
    except ScopeError:
        return False


def git_clean_for_path(cwd: Path, relpath: str) -> None:
    if not path_is_tracked(cwd, relpath):
        raise ScopeError("untracked", f"{relpath} is not tracked at HEAD")
    work = _run_git(["diff", "--name-only", "HEAD", "--", relpath], cwd=cwd)
    index = _run_git(["diff", "--cached", "--name-only", "HEAD", "--", relpath], cwd=cwd)
    if work.strip() or index.strip():
        staged = bool(index.strip())
        raise ScopeError(
            "dirty_staged" if staged and not work.strip() else "dirty",
            f"{relpath} differs from HEAD",
        )
    untracked = _run_git(
        ["ls-files", "--others", "--exclude-standard", "-z", "--", relpath],
        cwd=cwd,
    )
    if untracked.strip(b"\0"):
        raise ScopeError("untracked", f"{relpath} is untracked")


def exclusion_rule_matches(relpath: str, rule: Mapping[str, Any]) -> bool:
    match = rule.get("match") or {}
    basename = Path(relpath).name
    for prefix in match.get("path_prefixes") or []:
        if relpath == prefix or relpath.startswith(str(prefix).rstrip("/") + "/"):
            return True
    lowered = relpath.lower()
    base_lower = basename.lower()
    for substr in match.get("path_substrings") or []:
        needle = str(substr).lower()
        if needle and (needle in lowered or needle in base_lower):
            return True
    for glob in match.get("basename_globs") or []:
        if fnmatch.fnmatch(basename, str(glob)) or fnmatch.fnmatch(base_lower, str(glob).lower()):
            return True
    return False


def matching_exclusion_rule(relpath: str, rules: Iterable[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for rule in rules:
        if exclusion_rule_matches(relpath, rule):
            return rule
    return None


def content_class_for_path(relpath: str) -> str | None:
    lower = relpath.lower()
    for klass, suffixes in CONTENT_CLASS_SUFFIXES.items():
        if lower.endswith(suffixes):
            return klass
    return None


def _parse_entry(raw: Mapping[str, Any]) -> IncludeEntry:
    return IncludeEntry(
        path=str(raw["path"]),
        sha256=str(raw["sha256"]),
        content_class=str(raw["content_class"]),
        parser_mode=str(raw["parser_mode"]),
        adapter_contract_version=str(raw["adapter_contract_version"]),
        source_type=str(raw["source_type"]),
        required_state=str(raw["required_state"]),
        reviewed_state=str(raw["reviewed_state"]),
        owner=str(raw["owner"]),
        freshness_role=str(raw["freshness_role"]),
        retrieval_needles=tuple(str(item) for item in raw["retrieval_needles"]),
        sensitivity=str(raw["sensitivity"]),
    )


def load_and_validate_manifest(manifest_path: Path, *, schema: Mapping[str, Any] | None = None) -> LoadedManifest:
    path = Path(manifest_path)
    if _is_symlink(path) or any(_is_symlink(parent) for parent in path.parents):
        raise ScopeError("symlink", f"manifest path has a symlink component: {path}")
    if not path.is_file() or path.is_symlink():
        raise ScopeError("manifest_missing", f"manifest is not a regular file: {path}")
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScopeError("manifest_unreadable", str(exc)) from exc
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"manifest is not JSON: {exc}") from exc
    validate_manifest_document(data, schema or load_schema())
    try:
        root = git_toplevel(path.parent)
    except ScopeError as exc:
        raise ScopeError("manifest_outside_checkout", str(exc)) from exc
    if data["coverage_root"] != ".":
        raise ManifestValidationError("v1 coverage_root must be .")
    reject_symlink_components(root, path)
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ScopeError("manifest_outside_checkout", str(exc)) from exc
    git_clean_for_path(root, str(path.resolve().relative_to(root.resolve())))
    tracked = git_ls_files(root)
    class_rows = {
        row["path"]: Classification(row["path"], row["class"], row["reason"])
        for row in data["classifications"]
    }
    missing = [item for item in tracked if item not in class_rows]
    extra = [item for item in class_rows if item not in set(tracked)]
    if missing:
        raise ManifestValidationError(
            f"{len(missing)} unclassified tracked path(s); first={missing[0]}"
        )
    if extra:
        raise ManifestValidationError(
            f"classification for untracked path {extra[0]}"
        )
    folded: dict[str, str] = {}
    for item in tracked:
        key = item.casefold()
        if key in folded and folded[key] != item:
            raise ManifestValidationError(f"case-fold collision {folded[key]} vs {item}")
        folded[key] = item
    entries = {row["path"]: _parse_entry(row) for row in data["entries"]}
    included_bytes = 0
    for relpath, entry in entries.items():
        rule = matching_exclusion_rule(relpath, data["exclusion_rules"])
        if rule is not None:
            raise ManifestValidationError(
                f"exclusion {rule['id']} wins over include {relpath}"
            )
        abs_file = resolve_under_root(root, relpath)
        if not abs_file.is_file() or abs_file.is_symlink():
            raise ScopeError("not_regular", f"{relpath} is not a regular file")
        git_clean_for_path(root, relpath)
        blob = committed_bytes(root, relpath)
        if b"\x00" in blob:
            raise ScopeError("binary", f"{relpath} contains NUL bytes")
        if len(blob) > MAX_FILE_BYTES:
            raise ScopeError("resource_limit", f"{relpath} exceeds max_file_bytes")
        digest = sha256_bytes(blob)
        if digest != entry.sha256:
            raise ScopeError("hash_mismatch", f"{relpath} sha256 does not match manifest")
        work = abs_file.read_bytes()
        if sha256_bytes(work) != digest:
            raise ScopeError("dirty", f"{relpath} working tree differs from HEAD")
        included_bytes += len(blob)
        if entry.sensitivity == "strict_example":
            _reject_strict_example_bytes(relpath, blob)
        elif entry.sensitivity == "source_code":
            _reject_private_key_bytes(relpath, blob)
        elif entry.sensitivity == "synthetic" and b"BEGIN " in blob and b"PRIVATE KEY" in blob:
            raise ScopeError("credentials", f"{relpath} contains private-key material")
    if included_bytes > MAX_INCLUDED_BYTES:
        raise ScopeError("resource_limit", "aggregate included bytes exceed limit")
    identity = sha256_bytes(committed_bytes(root, str(path.resolve().relative_to(root.resolve()))))
    required = tuple(
        RequiredWhenPresent(row["path"], row["reason"], row["origin"])
        for row in data["required_when_present"]
    )
    retire = tuple(
        RetireRecord(
            path=row["path"],
            prior_file_sha256=row["prior_file_sha256"],
            prior_manifest_sha256=row["prior_manifest_sha256"],
            reason=row["reason"],
            replacement_path=row.get("replacement_path"),
        )
        for row in data["retire"]
    )
    return LoadedManifest(
        path=path.resolve(),
        root=root.resolve(),
        identity=identity,
        data=data,
        classifications=class_rows,
        entries=entries,
        exclusion_rules=tuple(data["exclusion_rules"]),
        required_when_present=required,
        retire=retire,
        git_head=git_head(root),
    )


_PRIVATE_KEY_MARKERS = (
    b"BEGIN OPENSSH PRIVATE KEY",
    b"BEGIN RSA PRIVATE KEY",
    b"BEGIN EC PRIVATE KEY",
    b"BEGIN PRIVATE KEY",
)
_CREDENTIAL_KEY_RE = re.compile(
    r"(api_key|secret_key|access_token|private_key|password)\s*=\s*['\"]?(?!your_|changeme|placeholder|xxxx|redacted)[^\s'\"]+",
    re.IGNORECASE,
)


def _reject_private_key_bytes(relpath: str, blob: bytes) -> None:
    upper = blob.upper()
    for marker in _PRIVATE_KEY_MARKERS:
        if marker in upper:
            raise ScopeError("credentials", f"{relpath} contains private-key material")


def _reject_strict_example_bytes(relpath: str, blob: bytes) -> None:
    _reject_private_key_bytes(relpath, blob)
    name = Path(relpath).name.lower()
    if name.startswith(".env") or name.endswith(".pem") or name.endswith(".key"):
        raise ScopeError("credentials", f"{relpath} has a credential filename")
    try:
        text = blob.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ScopeError("invalid_utf8", f"{relpath} is not UTF-8") from exc
    if _CREDENTIAL_KEY_RE.search(text):
        raise ScopeError(
            "credentials",
            f"{relpath} assigns a non-placeholder credential-shaped key",
        )


def _cached_manifest(manifest_abs: str) -> LoadedManifest:
    cached = _loaded_by_path.get(manifest_abs)
    if isinstance(cached, LoadedManifest):
        try:
            current = sha256_file(Path(manifest_abs))
            head = git_head(cached.root)
        except (OSError, ScopeError) as exc:
            _loaded_by_path[manifest_abs] = exc
            raise
        if current == cached.identity and head == cached.git_head:
            return cached
    try:
        loaded = load_and_validate_manifest(Path(manifest_abs))
    except BaseException as exc:
        _loaded_by_path[manifest_abs] = exc
        raise
    _loaded_by_path[manifest_abs] = loaded
    return loaded


def _iter_configured() -> Iterator[str]:
    yield from _configured_manifest_paths


def classify_detect_state(path: Path | str) -> DetectState:
    return decide_path(path).state


def _without_following_final(path: Path) -> Path:
    raw = path if path.is_absolute() else Path.cwd() / path
    try:
        parent = raw.parent.resolve(strict=False)
    except OSError:
        parent = raw.parent
    return parent / raw.name


def decide_path(path: Path | str) -> PathDecision:
    if not _configured_manifest_paths:
        return PathDecision("outside", "outside_unconfigured", "no repository-knowledge manifests configured")
    try:
        original = Path(path)
        lexical = _without_following_final(original)
        abs_path = lexical
    except OSError as exc:
        return PathDecision("blocked", "path_escape", str(exc))
    under_any_root = False
    last_error: PathDecision | None = None
    for manifest_abs in _iter_configured():
        try:
            loaded = _cached_manifest(manifest_abs)
        except BaseException as exc:
            code = getattr(exc, "code", "manifest_invalid")
            detail = getattr(exc, "detail", str(exc))
            # A configured root whose manifest cannot load still blocks paths
            # beneath that root once the root can be guessed from the path.
            guessed_root = Path(manifest_abs).resolve().parents[1] if Path(manifest_abs).name else None
            try:
                root = git_toplevel(Path(manifest_abs).parent)
                guessed_root = root
            except ScopeError:
                pass
            if guessed_root is not None:
                try:
                    resolved = abs_path.resolve(strict=False)
                    if _is_relative_to(resolved, guessed_root.resolve(strict=False)):
                        under_any_root = True
                        last_error = PathDecision("blocked", str(code), str(detail), root=guessed_root)
                except OSError:
                    under_any_root = True
                    last_error = PathDecision("blocked", str(code), str(detail))
            else:
                last_error = PathDecision("blocked", str(code), str(detail))
            continue
        lexical_under_root = False
        try:
            lexical_under_root = _is_relative_to(lexical, loaded.root)
        except (OSError, ValueError):
            lexical_under_root = False
        if lexical_under_root and lexical.exists() and lexical.is_symlink():
            return PathDecision(
                "blocked",
                "symlink",
                f"symlink component: {lexical}",
                root=loaded.root,
                manifest=loaded,
            )
        try:
            resolved = abs_path.resolve(strict=False)
        except OSError as exc:
            return PathDecision("blocked", "path_escape", str(exc), root=loaded.root, manifest=loaded)
        if not _is_relative_to(resolved, loaded.root):
            continue
        under_any_root = True
        decision = _decide_under_manifest(loaded, resolved, original_rel_hint=str(original))
        return decision
    if under_any_root and last_error is not None:
        return last_error
    if under_any_root:
        return PathDecision("blocked", "manifest_invalid", "configured root failed validation")
    return PathDecision("outside", "outside_root", "path is not under a configured repository root")


def _repo_relpath(root: Path, resolved: Path) -> str:
    rel = resolved.relative_to(root)
    return rel.as_posix()


def _decide_under_manifest(loaded: LoadedManifest, resolved: Path, *, original_rel_hint: str) -> PathDecision:
    try:
        reject_symlink_components(loaded.root, resolved)
    except ScopeError as exc:
        return PathDecision("blocked", exc.code, exc.detail, root=loaded.root, manifest=loaded)
    try:
        relpath = _repo_relpath(loaded.root, resolved)
    except ValueError:
        return PathDecision("blocked", "path_escape", "resolved path escaped root", root=loaded.root, manifest=loaded)
    if relpath != Path(relpath).as_posix() or relpath.startswith("/"):
        return PathDecision("blocked", "path_escape", "non-posix relpath", relpath=relpath, root=loaded.root, manifest=loaded)
    try:
        file_toplevel = git_toplevel(resolved.parent if resolved.exists() else loaded.root)
    except ScopeError as exc:
        return PathDecision("blocked", "nested_worktree", exc.detail, relpath=relpath, root=loaded.root, manifest=loaded)
    if file_toplevel.resolve() != loaded.root:
        return PathDecision(
            "blocked",
            "nested_worktree",
            "path is not in the configured checkout",
            relpath=relpath,
            root=loaded.root,
            manifest=loaded,
        )
    rule = matching_exclusion_rule(relpath, loaded.exclusion_rules)
    row = loaded.classifications.get(relpath)
    if rule is not None:
        return PathDecision(
            "blocked",
            f"exclude_{rule['id']}",
            str(rule.get("reason") or rule["id"]),
            relpath=relpath,
            root=loaded.root,
            manifest=loaded,
        )
    if row is None:
        return PathDecision(
            "blocked",
            "unlisted",
            "path is not classified in the reviewed manifest",
            relpath=relpath,
            root=loaded.root,
            manifest=loaded,
        )
    if row.klass != "include":
        return PathDecision(
            "blocked",
            f"classified_{row.klass}",
            row.reason,
            relpath=relpath,
            root=loaded.root,
            manifest=loaded,
        )
    entry = loaded.entries.get(relpath)
    if entry is None:
        return PathDecision(
            "blocked",
            "unlisted",
            "classified include without an entry",
            relpath=relpath,
            root=loaded.root,
            manifest=loaded,
        )
    try:
        if not resolved.exists():
            raise ScopeError("missing", f"{relpath} is missing")
        if resolved.is_symlink() or not resolved.is_file():
            raise ScopeError("not_regular", f"{relpath} is not a regular file")
        mode = resolved.stat().st_mode
        if not stat.S_ISREG(mode):
            raise ScopeError("not_regular", f"{relpath} is not a regular file")
        git_clean_for_path(loaded.root, relpath)
        blob = committed_bytes(loaded.root, relpath)
        digest = sha256_bytes(blob)
        if digest != entry.sha256:
            raise ScopeError("hash_mismatch", "committed bytes do not match the manifest hash")
        work = resolved.read_bytes()
        if sha256_bytes(work) != digest:
            raise ScopeError("dirty", "working tree bytes do not match HEAD")
        if b"\x00" in blob:
            raise ScopeError("binary", "NUL bytes")
        if len(blob) > MAX_FILE_BYTES:
            raise ScopeError("resource_limit", "file exceeds max_file_bytes")
        blob.decode("utf-8")
    except UnicodeDecodeError as exc:
        return PathDecision(
            "blocked",
            "invalid_utf8",
            str(exc),
            relpath=relpath,
            entry=entry,
            root=loaded.root,
            manifest=loaded,
        )
    except ScopeError as exc:
        return PathDecision(
            "blocked",
            exc.code,
            exc.detail,
            relpath=relpath,
            entry=entry,
            root=loaded.root,
            manifest=loaded,
        )
    return PathDecision(
        "eligible",
        "eligible",
        "git-clean included bytes",
        relpath=relpath,
        entry=entry,
        root=loaded.root,
        manifest=loaded,
        git_commit=loaded.git_head,
        file_sha256=entry.sha256,
    )


def source_identity(decision: PathDecision) -> str:
    if decision.state != "eligible" or decision.manifest is None or decision.relpath is None:
        raise ScopeError("not_eligible", "source identity requires an eligible path")
    return "|".join(
        [
            str(decision.root),
            decision.relpath,
            decision.file_sha256 or "",
            decision.git_commit or "",
            decision.manifest.identity,
            ADAPTER_CONTRACT_VERSION,
        ]
    )


def validate_prior_identity(
    *,
    manifest: LoadedManifest,
    relpath: str,
    prior_file_sha256: str,
    prior_manifest_sha256: str,
) -> None:
    if not _PATH_RE.match(relpath):
        raise ScopeError("path_escape", f"illegal retire path {relpath}")
    if prior_manifest_sha256 != manifest.identity and not any(
        rec.prior_manifest_sha256 == prior_manifest_sha256 and rec.path == relpath
        for rec in manifest.retire
    ):
        # Caller supplies the prior identity; the retire record must match it.
        pass
    rec = next((item for item in manifest.retire if item.path == relpath), None)
    if rec is None:
        raise ScopeError("retire_missing", f"no retire record for {relpath}")
    if rec.prior_file_sha256 != prior_file_sha256:
        raise ScopeError("identity_mismatch", "prior file hash does not match retire record")
    if rec.prior_manifest_sha256 != prior_manifest_sha256:
        raise ScopeError("identity_mismatch", "prior manifest hash does not match retire record")


def audit_manifest(manifest_path: Path) -> dict[str, Any]:
    loaded = load_and_validate_manifest(manifest_path)
    counts = {"include": 0, "exclude": 0, "unrelated": 0}
    for row in loaded.classifications.values():
        counts[row.klass] += 1
    present = {item.path for item in loaded.required_when_present if item.path in loaded.classifications}
    return {
        "manifest": str(loaded.path),
        "root": str(loaded.root),
        "manifest_sha256": loaded.identity,
        "git_head": loaded.git_head,
        "tracked": len(loaded.classifications),
        "include": counts["include"],
        "exclude": counts["exclude"],
        "unrelated": counts["unrelated"],
        "required_when_present": len(loaded.required_when_present),
        "required_when_present_now_present": sorted(present),
        "retire": len(loaded.retire),
        "unclassified": 0,
    }


def inventory_table(loaded: LoadedManifest) -> str:
    lines = [
        "| Class | Path | Content | Sensitivity | Reason / needles |",
        "|---|---|---|---|---|",
    ]
    for relpath in sorted(loaded.entries):
        entry = loaded.entries[relpath]
        needles = "; ".join(entry.retrieval_needles)
        lines.append(
            f"| include | `{relpath}` | {entry.content_class} | {entry.sensitivity} | {needles} |"
        )
    for relpath in sorted(loaded.classifications):
        row = loaded.classifications[relpath]
        if row.klass == "include":
            continue
        lines.append(
            f"| {row.klass} | `{relpath}` | — | — | {row.reason} |"
        )
    lines.append("")
    lines.append("### required_when_present")
    lines.append("")
    lines.append("| Path | Origin | Reason |")
    lines.append("|---|---|---|")
    for item in loaded.required_when_present:
        lines.append(f"| `{item.path}` | {item.origin} | {item.reason} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a repository-knowledge scope manifest")
    sub = parser.add_subparsers(dest="cmd", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--manifest", required=True)
    audit.add_argument("--table", action="store_true")
    args = parser.parse_args(argv)
    if args.cmd == "audit":
        result = audit_manifest(Path(args.manifest))
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        if args.table:
            loaded = load_and_validate_manifest(Path(args.manifest))
            sys.stdout.write(inventory_table(loaded))
        return 0
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ScopeError, ManifestValidationError) as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
