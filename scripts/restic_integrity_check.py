#!/usr/bin/env python3
"""Restic integrity preflight — Gate 6 one-time proof (local repo only).

Architecture: docs/plans/ARCHITECTURE-restic-integrity-preflight.md
Does not touch live Chroma, restore-drill, write-gate, or doctor.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

TAG = "convmem-data-v1"
DEFAULT_PARENT = Path.home() / ".local/share/convmem" / "integrity-check"
DEFAULT_SUBSET = "5%"


class CheckError(Exception):
    """Checked failure with a short machine-usable code."""

    def __init__(self, code: str, message: str, exit_code: int | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_restic_env(env_file: Path | None = None) -> dict[str, str]:
    path = env_file or Path(
        os.environ.get("CONVMEM_RESTIC_ENV", Path.home() / ".config/convmem/restic.env")
    )
    if not path.is_file():
        raise CheckError("restic_env", f"missing restic env: {path}")
    env = os.environ.copy()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key:
            env[key] = val
    if not env.get("RESTIC_REPOSITORY"):
        raise CheckError("restic_env", "RESTIC_REPOSITORY unset")
    if not env.get("RESTIC_PASSWORD_FILE"):
        raise CheckError("restic_env", "RESTIC_PASSWORD_FILE unset")
    cache = env.get("RESTIC_CACHE_DIR") or env.get("CONVMEM_RESTIC_CACHE_DIR")
    if not cache:
        cache = str(Path(os.environ.get("TMPDIR", "/tmp")) / "convmem-restic-cache")
    Path(cache).mkdir(parents=True, exist_ok=True)
    env["RESTIC_CACHE_DIR"] = cache
    return env


def build_check_argv(
    *,
    tag: str = TAG,
    subset: str | None = DEFAULT_SUBSET,
    full_read_data: bool = False,
) -> list[str]:
    argv = ["restic", "check", "--tag", tag]
    if full_read_data:
        argv.append("--read-data")
    elif subset:
        argv.extend(["--read-data-subset", subset])
    return argv


def run_restic_check(
    env: dict[str, str],
    argv: list[str],
    *,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=timeout,
    )


def classify_check_result(proc: subprocess.CompletedProcess[str]) -> None:
    """Raise CheckError on non-zero; map restic exit 11 to lock."""
    if proc.returncode == 0:
        return
    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    detail = stderr or stdout or f"restic check exit {proc.returncode}"
    if proc.returncode == 11:
        raise CheckError("restic_lock", detail, exit_code=11)
    if proc.returncode == 10:
        raise CheckError("restic_missing_repo", detail, exit_code=10)
    if proc.returncode == 12:
        raise CheckError("restic_bad_password", detail, exit_code=12)
    raise CheckError("restic_check", detail, exit_code=proc.returncode)


class Report:
    def __init__(self, path: Path):
        self.path = path
        self.started = _utc_now()
        self.steps: list[dict[str, Any]] = []
        self.meta: dict[str, Any] = {
            "status": "in_progress",
            "started_at": self.started,
            "finished_at": None,
            "kind": "restic_integrity_check",
        }
        self._write()

    def set_meta(self, **kwargs: Any) -> None:
        self.meta.update(kwargs)
        self._write()

    def step(
        self,
        name: str,
        status: str,
        detail: str = "",
        duration_s: float | None = None,
        **extra: Any,
    ) -> None:
        entry: dict[str, Any] = {
            "name": name,
            "status": status,
            "detail": detail,
            "at": _utc_now(),
        }
        if duration_s is not None:
            entry["duration_s"] = round(duration_s, 3)
        entry.update(extra)
        self.steps.append(entry)
        self._write()

    def finalize(self, status: str, detail: str = "") -> None:
        self.meta["status"] = status
        self.meta["finished_at"] = _utc_now()
        if detail:
            self.meta["final_detail"] = detail
        self._write()

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"meta": self.meta, "steps": self.steps}
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        md = self.path.with_suffix(".md")
        lines = [
            "# Restic integrity check report",
            "",
            f"- status: **{self.meta.get('status')}**",
            f"- started: {self.meta.get('started_at')}",
            f"- finished: {self.meta.get('finished_at')}",
        ]
        for k in ("repository", "tag", "argv", "subset", "full_read_data"):
            if k in self.meta:
                lines.append(f"- {k}: `{self.meta[k]}`")
        if self.meta.get("final_detail"):
            lines.append(f"- detail: {self.meta['final_detail']}")
        lines += ["", "| Step | Status | Detail |", "|------|--------|--------|"]
        for s in self.steps:
            detail = (s.get("detail") or "").replace("|", "\\|")
            lines.append(f"| {s['name']} | {s['status']} | {detail} |")
        lines.append("")
        md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    t0 = time.monotonic()
    out = fn()
    return out, time.monotonic() - t0


def ensure_reports_dir(parent: Path) -> Path:
    reports = parent / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="One-time Restic integrity preflight (Gate 6). Local repo only."
    )
    parser.add_argument(
        "--parent",
        type=Path,
        default=DEFAULT_PARENT,
        help="Parent for reports/ (default: ~/.local/share/convmem/integrity-check)",
    )
    parser.add_argument("--tag", default=TAG, help=f"Snapshot tag filter (default: {TAG})")
    parser.add_argument(
        "--read-data-subset",
        default=DEFAULT_SUBSET,
        help="restic --read-data-subset value (default: 5%%)",
    )
    parser.add_argument(
        "--full-read-data",
        action="store_true",
        help="Use --read-data instead of --read-data-subset (manual deep run)",
    )
    parser.add_argument(
        "--intentional-missing-repo",
        action="store_true",
        help="Point RESTIC_REPOSITORY at a nonexistent path; expect nonzero + report",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Override CONVMEM_RESTIC_ENV / ~/.config/convmem/restic.env",
    )
    args = parser.parse_args(argv)

    if shutil.which("restic") is None:
        print("restic not on PATH", file=sys.stderr)
        return 2

    reports = ensure_reports_dir(args.parent.expanduser())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = reports / f"integrity-{stamp}.json"
    report = Report(report_path)

    exit_status = 0

    def _finish() -> int:
        print(f"report={report_path}")
        return exit_status

    try:
        env = load_restic_env(args.env_file)
        report.step("load_env", "PASS", str(args.env_file or "~/.config/convmem/restic.env"))

        if args.intentional_missing_repo:
            env = dict(env)
            env["RESTIC_REPOSITORY"] = str(
                Path("/tmp") / f"convmem-integrity-missing-repo-{os.getpid()}"
            )
            report.step(
                "intentional_missing_repo",
                "PASS",
                f"forced RESTIC_REPOSITORY={env['RESTIC_REPOSITORY']}",
            )

        repo = env["RESTIC_REPOSITORY"]
        check_argv = build_check_argv(
            tag=args.tag,
            subset=None if args.full_read_data else args.read_data_subset,
            full_read_data=args.full_read_data,
        )
        report.set_meta(
            repository=repo,
            tag=args.tag,
            argv=check_argv,
            subset=None if args.full_read_data else args.read_data_subset,
            full_read_data=args.full_read_data,
        )
        report.step("build_argv", "PASS", " ".join(check_argv))

        def _run() -> subprocess.CompletedProcess[str]:
            return run_restic_check(env, check_argv)

        proc, dt = timed(_run)
        report.set_meta(
            restic_exit_code=proc.returncode,
            restic_stdout_tail=(proc.stdout or "")[-2000:],
            restic_stderr_tail=(proc.stderr or "")[-2000:],
        )
        try:
            classify_check_result(proc)
        except CheckError as exc:
            report.step(
                "restic_check",
                "FAIL",
                exc.message[:500],
                duration_s=dt,
                code=exc.code,
                restic_exit_code=exc.exit_code,
            )
            report.finalize("FAIL", f"{exc.code}: {exc.message[:300]}")
            exit_status = exc.exit_code if exc.exit_code not in (None, 0) else 1
            return _finish()

        report.step("restic_check", "PASS", "exit 0", duration_s=dt, restic_exit_code=0)
        report.finalize("PASS", "integrity check complete")
        exit_status = 0
        return _finish()
    except CheckError as exc:
        report.step(exc.code, "FAIL", exc.message[:500])
        report.finalize("FAIL", f"{exc.code}: {exc.message[:300]}")
        exit_status = 1
        return _finish()
    except subprocess.TimeoutExpired as exc:
        report.step("restic_check", "FAIL", f"timeout: {exc}")
        report.finalize("FAIL", "timeout")
        exit_status = 1
        return _finish()
    except Exception as exc:  # noqa: BLE001 — always finalize
        report.step("unexpected", "FAIL", str(exc)[:500])
        report.finalize("FAIL", str(exc)[:300])
        exit_status = 1
        return _finish()


if __name__ == "__main__":
    raise SystemExit(main())
