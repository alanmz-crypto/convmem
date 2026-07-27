#!/usr/bin/env python3
"""Restic integrity preflight — thin reporter over backup_workflows.run_integrity_check.

Architecture: docs/plans/ARCHITECTURE-complete-data-backup-correction-v2.md
Does not touch live Chroma. Selection/check go through restic_snapshot via workflows.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from backup_workflows import run_integrity_check  # noqa: E402
from restic_snapshot import BackupContext, ResolverError  # noqa: E402

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


def build_check_argv(
    *,
    snapshot_id: str,
    subset: str | None = DEFAULT_SUBSET,
    full_read_data: bool = False,
) -> list[str]:
    """Document expected check argv shape (explicit id — never --tag/--latest)."""
    argv = ["restic", "check", snapshot_id]
    if full_read_data:
        argv.append("--read-data")
    elif subset:
        argv.extend(["--read-data-subset", subset])
    return argv


def classify_check_result(returncode: int, detail: str = "") -> None:
    """Raise CheckError on non-zero; map restic exit 10/11/12."""
    if returncode == 0:
        return
    if returncode == 11:
        raise CheckError("restic_lock", detail or "locked", exit_code=11)
    if returncode == 10:
        raise CheckError("restic_missing_repo", detail or "missing repo", exit_code=10)
    if returncode == 12:
        raise CheckError("restic_bad_password", detail or "bad password", exit_code=12)
    raise CheckError("restic_check", detail or f"exit {returncode}", exit_code=returncode)


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
        for k in ("repository", "tag", "argv", "subset", "full_read_data", "snapshot_id"):
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


def ensure_reports_dir(parent: Path) -> Path:
    reports = parent / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Restic integrity preflight via backup_workflows (explicit snapshot id)."
    )
    parser.add_argument(
        "--parent",
        type=Path,
        default=DEFAULT_PARENT,
        help="Parent for reports/ (default: ~/.local/share/convmem/integrity-check)",
    )
    parser.add_argument(
        "--snapshot-id",
        default=None,
        help="Full 64-char snapshot id (default: resolve correct-path current tag)",
    )
    parser.add_argument(
        "--read-data-subset",
        default=DEFAULT_SUBSET,
        help="restic --read-data-subset value (default: 5%%)",
    )
    parser.add_argument(
        "--full-read-data",
        action="store_true",
        help="Use --read-data instead of --read-data-subset",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Override CONVMEM_RESTIC_ENV / ~/.config/convmem/restic.env",
    )
    args = parser.parse_args(argv)

    reports = ensure_reports_dir(args.parent.expanduser())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = reports / f"integrity-{stamp}.json"
    report = Report(report_path)

    try:
        env_path = args.env_file or Path(
            os.environ.get("CONVMEM_RESTIC_ENV", Path.home() / ".config/convmem/restic.env")
        )
        ctx = BackupContext.from_env_file(env_path)
        report.step("load_env", "PASS", str(env_path))
        report.set_meta(
            repository=ctx.local_repository.locator,
            tag=ctx.default_tag(),
            subset=None if args.full_read_data else args.read_data_subset,
            full_read_data=args.full_read_data,
        )

        outcome = run_integrity_check(
            ctx,
            snapshot_id=args.snapshot_id,
            full_read_data=args.full_read_data,
            read_data_subset=args.read_data_subset,
        )
        argv_list = list(outcome.argv) if outcome.argv else []
        report.set_meta(
            argv=argv_list,
            snapshot_id=outcome.source.id if outcome.source else None,
            restic_exit_code=outcome.details.get("restic_exit_code", outcome.exit_code),
        )
        report.step("build_argv", "PASS", " ".join(argv_list) if argv_list else "(none)")

        if outcome.status != "PASS":
            try:
                classify_check_result(
                    outcome.details.get("restic_exit_code", outcome.exit_code),
                    outcome.message,
                )
            except CheckError as exc:
                report.step(
                    "restic_check",
                    "FAIL",
                    exc.message[:500],
                    code=exc.code,
                    restic_exit_code=exc.exit_code,
                )
                report.finalize("FAIL", f"{exc.code}: {exc.message[:300]}")
                print(f"report={report_path}")
                return exc.exit_code if exc.exit_code not in (None, 0) else outcome.exit_code or 1
            report.step("restic_check", "FAIL", outcome.message[:500])
            report.finalize("FAIL", outcome.message[:300])
            print(f"report={report_path}")
            return outcome.exit_code or 1

        report.step("restic_check", "PASS", f"id={outcome.source.id if outcome.source else '?'}")
        report.finalize("PASS", "integrity check complete")
        print(f"report={report_path}")
        return 0
    except ResolverError as exc:
        report.step("resolver", "FAIL", str(exc)[:500])
        report.finalize("FAIL", f"resolver:{exc.exit_code}: {exc}")
        print(f"report={report_path}")
        return exc.exit_code
    except CheckError as exc:
        report.step(exc.code, "FAIL", exc.message[:500])
        report.finalize("FAIL", f"{exc.code}: {exc.message[:300]}")
        print(f"report={report_path}")
        return exc.exit_code or 1
    except Exception as exc:  # noqa: BLE001
        report.step("unexpected", "FAIL", str(exc)[:500])
        report.finalize("FAIL", str(exc)[:300])
        print(f"report={report_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
