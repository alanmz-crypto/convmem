"""Hermetic Gate 1 smoke launcher for Claude ``index --file``.

Synthetic scratch-only preparation for Arc Claude Watch Parity. Does not read,
list, or index live Claude transcripts. Uses deterministic fake providers and
reuses the reviewed jsonl production-integration isolation boundary.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
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


def assert_transcript_under_claude_projects(transcript: Path, home: Path) -> None:
    """Fail closed when the fixture is not under the scratch Claude tree."""
    projects_root = (home / ".claude" / "projects").resolve()
    try:
        transcript.resolve().relative_to(projects_root)
    except ValueError as exc:
        raise IsolationViolation(
            "transcript must live under HOME/.claude/projects for Gate 1 detection"
        ) from exc


def run_hermetic_index_cli(transcript: Path) -> tuple[int, dict[str, int], str]:
    """Invoke the real ``convmem index --file`` command in-process after guards."""
    from typer.testing import CliRunner  # noqa: PLC0415

    from convmem import app  # noqa: PLC0415

    boundary = IsolationBoundary.from_environment()
    install_network_denial()
    home = Path(os.environ["HOME"])
    resolved = boundary.resolve_mutable(transcript, label="claude transcript")
    assert_transcript_under_claude_projects(resolved, home)
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
    payload = json.loads(completed.stdout or "{}")
    return HermeticEvidence(
        files_processed=int(payload.get("files_processed", 0)),
        files_skipped=int(payload.get("files_skipped", 0)),
        chunks_indexed=int(payload.get("chunks_indexed", 0)),
        units_indexed=int(payload.get("units_indexed", 0)),
        format_name=str(payload.get("format_name", "")),
        scratch_root=str(root),
        transcript_digest=hashlib.sha256(transcript.read_bytes()).hexdigest(),
        config_path=str(Path(env["HOME"]) / ".config" / "convmem" / "config.toml"),
        exit_code=int(payload.get("exit_code", completed.returncode)),
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
