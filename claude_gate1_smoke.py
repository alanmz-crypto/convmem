"""Hermetic Gate 1 smoke launcher for Claude ``index --file``.

Synthetic scratch-only preparation for Arc Claude Watch Parity. Does not read,
list, or index live Claude transcripts. Uses deterministic fake providers and
reuses the reviewed jsonl production-integration isolation boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from incremental_jsonl_isolation import (
    ISOLATION_ENV_ALLOWLIST,
    ISOLATION_MODE,
    ISOLATION_MODE_ENV,
    ISOLATION_ROOT_ENV,
    ISOLATION_TOKEN_ENV,
    IsolationBoundary,
    IsolationViolation,
    create_fresh_root,
    install_network_denial,
    known_production_roots,
    sanitized_worker_env,
)

REPO_ROOT = Path(__file__).resolve().parent
WORKER = REPO_ROOT / "tests" / "claude_gate1_smoke_worker.py"

_CREDENTIAL_MARKERS = ("API_KEY", "SECRET", "PASSWORD", "CREDENTIAL")
_SYNTHETIC_SESSION_ID = "sess-hermetic-gate1-001"
_SYNTHETIC_UNIT: dict[str, Any] = {
    "type": "explanation",
    "title": "Hermetic Claude Gate 1 unit",
    "summary": "Synthetic on-demand index smoke knowledge unit.",
    "keywords": ["claude", "hermetic", "gate1"],
    "confidence": 0.95,
    "domain": "general",
}

# Mirror config.py path keys without importing ConvMem runtime modules.
_CONFIG_PATH_KEYS = frozenset(
    {
        "chroma_dir",
        "processed_log",
        "units_export",
        "inventory",
        "state_dir",
        "ledger_path",
        "activation_manifest_path",
        "health_path",
    }
)
_DEFAULT_INCREMENTAL_STATE_DIR = "~/.local/share/convmem/incremental-jsonl"
_DEFAULT_WRITER_LOCK = "~/.local/share/convmem/locks/chroma_writer_gate.lock"
_DEFAULT_WRITER_ATTEST_DIR = "~/.local/share/convmem/writer_attestations"
_DEFAULT_WRITER_CENSUS_DIR = "~/.local/share/convmem/writer-census"
_DEFAULT_BRIEF_PATH = "~/.local/share/convmem/brief.md"


@dataclass(frozen=True)
class ConfigIdentity:
    """Immutable fingerprint of the validated scratch config."""

    path: str
    digest: str
    device: int
    inode: int
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class OutputContainmentPreflight:
    """Proof that scratch config and mutable targets are confined before imports."""

    config_path: Path
    config_identity: ConfigIdentity
    validated_targets: tuple[str, ...]


@dataclass(frozen=True)
class HermeticEvidence:
    """Content-free smoke result for Ryan review."""

    files_processed: int
    files_skipped: int
    chunks_indexed: int
    units_indexed: int
    format_name: str
    scratch_root: str
    transcript_digest: str
    config_path: str
    exit_code: int

    @property
    def passed(self) -> bool:
        return (
            self.exit_code == 0
            and self.files_processed == 1
            and self.files_skipped == 0
            and self.units_indexed > 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "files_processed": self.files_processed,
            "files_skipped": self.files_skipped,
            "chunks_indexed": self.chunks_indexed,
            "units_indexed": self.units_indexed,
            "format_name": self.format_name,
            "scratch_root": self.scratch_root,
            "transcript_digest": self.transcript_digest,
            "config_path": self.config_path,
            "exit_code": self.exit_code,
            "passed": self.passed,
        }


def _claude_record(
    *,
    rtype: str,
    content: object,
    session_id: str = _SYNTHETIC_SESSION_ID,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "type": rtype,
        "sessionId": session_id,
        "uuid": f"uuid-{rtype}",
        "cwd": "/tmp/hermetic-project",
        "isSidechain": False,
        "timestamp": "2026-09-18T12:00:00.000Z",
    }
    if rtype in ("user", "assistant"):
        record["message"] = {"role": rtype, "content": content}
    return record


def write_synthetic_claude_transcript(home: Path) -> Path:
    """Place a Claude-shaped fixture under ``HOME/.claude/projects/...``."""
    transcript_dir = home / ".claude" / "projects" / "hermetic-gate1-slug"
    transcript_dir.mkdir(parents=True, exist_ok=True)
    transcript = transcript_dir / "session-uuid-hermetic.jsonl"
    rows = [
        _claude_record(rtype="system", content=""),
        _claude_record(
            rtype="user",
            content="Hello from the hermetic Gate 1 Claude smoke fixture.",
        ),
        _claude_record(
            rtype="assistant",
            content=[{"type": "text", "text": "Acknowledged hermetic fixture."}],
        ),
    ]
    transcript.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    return transcript.resolve(strict=True)


def scrub_credentials(env: dict[str, str]) -> dict[str, str]:
    """Drop inherited credential env vars while preserving isolation markers."""
    cleaned = dict(env)
    for name in list(cleaned):
        if name in ISOLATION_ENV_ALLOWLIST:
            continue
        if any(marker in name.upper() for marker in _CREDENTIAL_MARKERS):
            cleaned.pop(name, None)
    return cleaned


def prepare_hermetic_fixture(
    parent: Path | None = None,
    *,
    home: Path | None = None,
) -> tuple[Path, str, dict[str, str], Path]:
    """Create a fresh scratch root, env, and synthetic Claude transcript."""
    root, token = create_fresh_root(parent)
    env = scrub_credentials(
        sanitized_worker_env(
            root,
            token,
            forbidden_roots=known_production_roots(home=home),
        )
    )
    transcript = write_synthetic_claude_transcript(Path(env["HOME"]))
    return root, token, env, transcript


def install_fake_providers() -> None:
    """Replace paid/network providers with deterministic local transforms."""
    import ingest  # noqa: PLC0415

    if os.environ.get("CONVMEM_GATE1_FORCE_ZERO_UNITS") == "1":
        ingest.summarize = lambda *_a, **_k: "summary:forced-zero"
        ingest.ollama_embed = lambda *_a, **_k: [0.0] * 8
        ingest.distill = lambda *_a, **_k: []
        return

    def fake_summarize(
        text: str,
        model: str,
        ollama_host: str,
        deepseek_base_url: str = "https://api.deepseek.com",
    ) -> str:
        return f"summary:{hashlib.sha256(text.encode()).hexdigest()[:16]}"

    def fake_embed(text: str, model: str, host: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        return [((digest[index] / 255.0) * 2.0) - 1.0 for index in range(8)]

    def fake_distill(
        text: str,
        model: str,
        ollama_host: str,
        deepseek_base_url: str = "https://api.deepseek.com",
    ) -> list[dict[str, Any]]:
        return [dict(_SYNTHETIC_UNIT)]

    ingest.summarize = fake_summarize
    ingest.ollama_embed = fake_embed
    ingest.distill = fake_distill


def _expand_path_value(value: object) -> object:
    if isinstance(value, str):
        return str(Path(value).expanduser())
    if isinstance(value, list):
        return [_expand_path_value(item) for item in value]
    return value


def _expand_section_paths(section: dict[str, Any]) -> None:
    for key, value in list(section.items()):
        if isinstance(value, dict):
            _expand_section_paths(value)
        elif key in _CONFIG_PATH_KEYS:
            section[key] = _expand_path_value(value)


def _expand_config_paths(cfg: dict[str, Any]) -> None:
    sources = cfg.get("sources")
    if isinstance(sources, dict) and isinstance(sources.get("paths"), list):
        sources["paths"] = _expand_path_value(sources["paths"])
    for section in cfg.values():
        if isinstance(section, dict):
            _expand_section_paths(section)


def _require_env_path(name: str) -> Path:
    raw = os.environ.get(name, "")
    if not raw:
        raise IsolationViolation(f"{name} missing for scratch config discovery")
    return Path(raw)


def _resolved_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def validate_scratch_environment(boundary: IsolationBoundary) -> dict[str, Path]:
    """Bind scratch HOME/XDG roots to the isolated layout before config load."""
    layout = boundary.layout
    bindings = {
        "HOME": layout["home"],
        "XDG_CONFIG_HOME": layout["xdg_config"],
        "XDG_DATA_HOME": layout["xdg_data"],
        "XDG_CACHE_HOME": layout["xdg_cache"],
    }
    resolved: dict[str, Path] = {}
    for env_name, expected in bindings.items():
        actual = boundary.resolve_mutable(
            _require_env_path(env_name),
            label=env_name,
        )
        expected_resolved = boundary.resolve_mutable(
            expected,
            label=f"expected {env_name}",
        )
        if actual != expected_resolved:
            raise IsolationViolation(
                f"{env_name} does not match scratch isolation layout"
            )
        resolved[env_name.lower()] = actual
    config_path = layout["user_config"]
    if not config_path.is_file():
        raise IsolationViolation("scratch config missing under isolated HOME")
    resolved["config_path"] = boundary.resolve_mutable(
        config_path,
        label="effective config",
    )
    return resolved


def _read_scratch_config_bytes(config_path: Path) -> bytes:
    if config_path.is_symlink():
        raise IsolationViolation("scratch config must not be a symlink")
    try:
        return config_path.read_bytes()
    except OSError as exc:
        raise IsolationViolation(f"cannot read scratch config: {exc}") from exc


def _parse_scratch_config(raw: bytes) -> dict[str, Any]:
    try:
        cfg = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise IsolationViolation("scratch config is not valid TOML") from exc
    if not isinstance(cfg, dict):
        raise IsolationViolation("scratch config must be a TOML table")
    _expand_config_paths(cfg)
    return cfg


def _load_scratch_config(config_path: Path) -> dict[str, Any]:
    return _parse_scratch_config(_read_scratch_config_bytes(config_path))


def _capture_config_identity(config_path: Path) -> ConfigIdentity:
    raw = _read_scratch_config_bytes(config_path)
    stat_result = config_path.stat()
    return ConfigIdentity(
        path=str(config_path),
        digest=hashlib.sha256(raw).hexdigest(),
        device=stat_result.st_dev,
        inode=stat_result.st_ino,
        size=stat_result.st_size,
        mtime_ns=stat_result.st_mtime_ns,
    )


def replace_config_scalar(config_path: Path, key: str, value: Path) -> None:
    """Rewrite one top-level scalar in the scratch TOML config."""
    text = config_path.read_text(encoding="utf-8")
    replacement = f'{key} = {json.dumps(str(value))}'
    updated, count = re.subn(
        rf"^{key} = .*$",
        replacement,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError(f"could not rewrite config key {key}")
    config_path.write_text(updated, encoding="utf-8")


def _assert_scratch_config_layout(cfg: dict[str, Any], boundary: IsolationBoundary) -> None:
    """Prove HOME-based discovery selected the generated scratch config."""
    layout = boundary.layout
    index = cfg.get("index")
    if not isinstance(index, dict):
        raise IsolationViolation("scratch config index table missing")
    expected_pairs = (
        ("chroma_dir", layout["chroma"]),
        ("processed_log", layout["processed"]),
        ("units_export", layout["export"]),
    )
    for key, expected in expected_pairs:
        actual = index.get(key)
        if not isinstance(actual, str) or not actual.strip():
            raise IsolationViolation(f"scratch config missing index.{key}")
        if _resolved_path(Path(actual)) != _resolved_path(expected):
            raise IsolationViolation(
                f"scratch config index.{key} does not match isolated layout"
            )
    incremental = index.get("incremental_jsonl")
    if not isinstance(incremental, dict):
        raise IsolationViolation("scratch config incremental_jsonl table missing")
    state_dir = incremental.get("state_dir", _DEFAULT_INCREMENTAL_STATE_DIR)
    if not isinstance(state_dir, str) or not state_dir.strip():
        raise IsolationViolation("scratch config state_dir must be a non-empty string")
    if _resolved_path(Path(state_dir)) != _resolved_path(layout["state"]):
        raise IsolationViolation(
            "scratch config state_dir does not match isolated layout"
        )


def collect_index_mutable_targets(cfg: dict[str, Any]) -> list[tuple[str, Path]]:
    """Return every path the index command may create or mutate."""
    targets: list[tuple[str, Path]] = []
    index = cfg.get("index")
    if isinstance(index, dict):
        for key in ("chroma_dir", "processed_log", "units_export", "inventory"):
            value = index.get(key)
            if isinstance(value, str) and value.strip():
                targets.append((f"index.{key}", Path(value)))
        incremental = index.get("incremental_jsonl")
        if isinstance(incremental, dict):
            state_dir = incremental.get("state_dir", _DEFAULT_INCREMENTAL_STATE_DIR)
            if isinstance(state_dir, str) and state_dir.strip():
                targets.append(
                    ("index.incremental_jsonl.state_dir", Path(state_dir))
                )
    sources = cfg.get("sources")
    if isinstance(sources, dict):
        inventory = sources.get("inventory")
        if isinstance(inventory, str) and inventory.strip():
            targets.append(("sources.inventory", Path(inventory)))
    shadow = cfg.get("shadow_ledger")
    if isinstance(shadow, dict):
        for key in ("ledger_path", "activation_manifest_path", "health_path"):
            value = shadow.get(key)
            if isinstance(value, str) and value.strip():
                targets.append((f"shadow_ledger.{key}", Path(value)))
    for label, raw in (
        ("writer_lock(default)", _DEFAULT_WRITER_LOCK),
        ("writer_attestations(default)", _DEFAULT_WRITER_ATTEST_DIR),
        ("writer_census(default)", _DEFAULT_WRITER_CENSUS_DIR),
        ("brief(default)", _DEFAULT_BRIEF_PATH),
    ):
        targets.append((label, Path(raw).expanduser()))
    expanded: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for label, path in targets:
        resolved = _resolved_path(path)
        token = str(resolved)
        if token in seen:
            continue
        seen.add(token)
        expanded.append((label, resolved))
        parent = resolved.parent
        parent_token = str(parent)
        if parent_token not in seen:
            seen.add(parent_token)
            expanded.append((f"{label}:parent", parent))
    return expanded


def validate_output_containment(boundary: IsolationBoundary) -> OutputContainmentPreflight:
    """Fail closed on config/env/output paths before ConvMem indexing imports."""
    env_paths = validate_scratch_environment(boundary)
    config_path = env_paths["config_path"]
    cfg = _load_scratch_config(config_path)
    _assert_scratch_config_layout(cfg, boundary)
    validated: list[str] = []
    seen: set[str] = set()
    for label, path in collect_index_mutable_targets(cfg):
        token = f"{label}:{path}"
        if token in seen:
            continue
        seen.add(token)
        boundary.resolve_mutable(path, label=label)
        validated.append(label)
    return OutputContainmentPreflight(
        config_path=config_path,
        config_identity=_capture_config_identity(config_path),
        validated_targets=tuple(validated),
    )


def _validate_index_output_containment(
    cfg: dict[str, Any],
    boundary: IsolationBoundary,
) -> None:
    seen: set[str] = set()
    for label, path in collect_index_mutable_targets(cfg):
        token = f"{label}:{path}"
        if token in seen:
            continue
        seen.add(token)
        boundary.resolve_mutable(path, label=label)


def assert_config_identity_unchanged(
    preflight: OutputContainmentPreflight,
    boundary: IsolationBoundary,
) -> None:
    """Fail closed when the validated config changes before ConvMem consumes it."""
    identity = preflight.config_identity
    config_path = boundary.resolve_mutable(
        preflight.config_path,
        label="effective config",
    )
    if str(config_path) != identity.path:
        raise IsolationViolation("scratch config path changed after preflight")
    if config_path.is_symlink():
        raise IsolationViolation("scratch config must not be a symlink")
    try:
        stat_result = config_path.stat()
    except OSError as exc:
        raise IsolationViolation(
            f"scratch config unreadable after preflight: {exc}"
        ) from exc
    current_identity = (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )
    expected_identity = (
        identity.device,
        identity.inode,
        identity.size,
        identity.mtime_ns,
    )
    if current_identity != expected_identity:
        raise IsolationViolation("scratch config identity changed after preflight")
    raw = _read_scratch_config_bytes(config_path)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != identity.digest:
        raise IsolationViolation("scratch config contents changed after preflight")
    cfg = _parse_scratch_config(raw)
    _assert_scratch_config_layout(cfg, boundary)
    _validate_index_output_containment(cfg, boundary)


def maybe_apply_test_post_preflight_tamper(config_path: Path) -> None:
    """Test-only hook: mutate config after preflight to prove TOCTOU refusal."""
    key = os.environ.get("CONVMEM_GATE1_TEST_POST_PREFLIGHT_TAMPER_KEY", "")
    target = os.environ.get("CONVMEM_GATE1_TEST_POST_PREFLIGHT_TAMPER_PATH", "")
    if not key or not target:
        return
    replace_config_scalar(config_path, key, Path(target))


def assert_transcript_under_claude_projects(transcript: Path, home: Path) -> None:
    """Fail closed when the fixture is not under the scratch Claude tree."""
    projects_root = (home / ".claude" / "projects").resolve()
    try:
        transcript.resolve().relative_to(projects_root)
    except ValueError as exc:
        raise IsolationViolation(
            "transcript must live under HOME/.claude/projects for Gate 1 detection"
        ) from exc


def run_hermetic_index_cli(
    transcript: Path,
    *,
    preflight: OutputContainmentPreflight,
) -> tuple[int, dict[str, int], str]:
    """Invoke the real ``convmem index --file`` command in-process after guards."""
    if not isinstance(preflight, OutputContainmentPreflight):
        raise IsolationViolation(
            "output containment preflight required before index CLI"
        )
    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    assert_config_identity_unchanged(preflight, boundary)
    home = Path(os.environ["HOME"])
    resolved = boundary.resolve_mutable(transcript, label="claude transcript")
    assert_transcript_under_claude_projects(resolved, home)
    from typer.testing import CliRunner  # noqa: PLC0415

    from convmem import app  # noqa: PLC0415

    install_fake_providers()
    runner = CliRunner()
    result = runner.invoke(app, ["index", "--file", str(resolved)])
    stats = _parse_index_stats(result.stdout)
    return result.exit_code, stats, result.stdout


def _parse_index_stats(stdout: str) -> dict[str, int]:
    stats = {
        "files_processed": 0,
        "files_skipped": 0,
        "chunks_indexed": 0,
        "units_indexed": 0,
    }
    for line in stdout.splitlines():
        if not line.startswith("Done."):
            continue
        for key in stats:
            token = f"{key}="
            if token in line:
                fragment = line.split(token, 1)[1].split()[0]
                stats[key] = int(fragment)
    return stats


def capture_path_fingerprint(path: Path) -> dict[str, Any] | None:
    """Return inode/size/mtime facts for a path, or None when absent."""
    try:
        stat_result = path.stat()
    except OSError:
        return None
    return {
        "path": str(path),
        "device": stat_result.st_dev,
        "inode": stat_result.st_ino,
        "size": stat_result.st_size,
        "mtime_ns": stat_result.st_mtime_ns,
    }


def production_fingerprint_paths(home: Path | None = None) -> tuple[Path, ...]:
    """Paths that hermetic smoke must not mutate."""
    home = (home or Path.home()).expanduser()
    return (
        home / ".local/share/convmem/chroma",
        home / ".local/share/convmem/processed.json",
        home / ".local/share/convmem/knowledge_units.jsonl",
        home / ".config/convmem/config.toml",
    )


def production_fingerprints(home: Path | None = None) -> list[dict[str, Any]]:
    """Fingerprint default production paths that must remain unchanged."""
    fingerprints: list[dict[str, Any]] = []
    for path in production_fingerprint_paths(home=home):
        fp = capture_path_fingerprint(path)
        if fp is not None:
            fingerprints.append(fp)
    return fingerprints


def run_worker(
    command: str,
    transcript: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run the hermetic worker subprocess with a sanitized environment."""
    cmd = [sys.executable, "-I", str(WORKER), command, str(transcript)]
    return subprocess.run(
        cmd,
        env=env,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def run_hermetic_smoke(parent: Path | None = None) -> HermeticEvidence:
    """End-to-end hermetic smoke using the worker subprocess."""
    root, _token, env, transcript = prepare_hermetic_fixture(parent)
    before = production_fingerprints()
    completed = run_worker("run", transcript, env)
    after = production_fingerprints()
    if before != after:
        raise IsolationViolation("production fingerprint drift during hermetic smoke")
    worker_exit = completed.returncode
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    return HermeticEvidence(
        files_processed=int(payload.get("files_processed", 0)),
        files_skipped=int(payload.get("files_skipped", 0)),
        chunks_indexed=int(payload.get("chunks_indexed", 0)),
        units_indexed=int(payload.get("units_indexed", 0)),
        format_name=str(payload.get("format_name", "")),
        scratch_root=str(root),
        transcript_digest=hashlib.sha256(transcript.read_bytes()).hexdigest(),
        config_path=str(Path(env["HOME"]) / ".config" / "convmem" / "config.toml"),
        exit_code=worker_exit,
    )


def _main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    if not argv or argv[0] != "run":
        print(
            "Usage: python claude_gate1_smoke.py run\n"
            "Hermetic synthetic Gate 1 preparation only; no live Claude source.",
            file=sys.stderr,
        )
        return 2
    evidence = run_hermetic_smoke()
    print(json.dumps(evidence.to_dict(), indent=2, sort_keys=True))
    return 0 if evidence.passed else 1


if __name__ == "__main__":
    raise SystemExit(_main())
