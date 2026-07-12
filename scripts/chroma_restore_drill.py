#!/usr/bin/env python3
"""Chroma restore drill — prove a Restic snapshot restores a queryable store.

Architecture: docs/plans/ARCHITECTURE-chroma-restore-drill.md
Does not touch live Chroma. Run directory is disposable; report is durable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from chroma_store import (  # noqa: E402
    SUMMARIES,
    UNITS,
    open_chroma_for_verify,
)

DEFAULT_PARENT = Path.home() / ".local/share/convmem" / "restore-drill"
DEFAULT_FIXTURE = REPO / "tests" / "fixtures" / "chroma_restore_drill.json"
MISSING_COLLECTION = "__convmem_restore_drill_missing__"
INTENTIONAL_BAD_SNAPSHOT = "0000000000000000000000000000000000000000000000000000000000000000"


class DrillError(Exception):
    """Checked failure with a short machine-usable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_restic_env() -> dict[str, str]:
    env_file = Path(
        os.environ.get("CONVMEM_RESTIC_ENV", Path.home() / ".config/convmem/restic.env")
    )
    if not env_file.is_file():
        raise DrillError("restic_env", f"missing restic env: {env_file}")
    env = os.environ.copy()
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip("'").strip('"')
        if key:
            env[key] = val
    if not env.get("RESTIC_REPOSITORY"):
        raise DrillError("restic_env", "RESTIC_REPOSITORY unset")
    if not env.get("RESTIC_PASSWORD_FILE"):
        raise DrillError("restic_env", "RESTIC_PASSWORD_FILE unset")
    cache = env.get("RESTIC_CACHE_DIR") or env.get("CONVMEM_RESTIC_CACHE_DIR")
    if not cache:
        cache = str(Path(os.environ.get("TMPDIR", "/tmp")) / "convmem-restic-cache")
    Path(cache).mkdir(parents=True, exist_ok=True)
    env["RESTIC_CACHE_DIR"] = cache
    return env


def list_tagged_snapshots(env: dict[str, str], tag: str = "convmem-chroma") -> list[dict]:
    proc = subprocess.run(
        ["restic", "snapshots", "--tag", tag, "--json"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise DrillError("restic_list", proc.stderr.strip() or "restic snapshots failed")
    snaps = json.loads(proc.stdout or "[]")
    return sorted(snaps, key=lambda s: s.get("time") or "")


def resolve_snapshot(snaps: list[dict], snapshot_id: str) -> dict:
    sid = snapshot_id.strip().lower()
    matches = [
        s
        for s in snaps
        if str(s.get("id", "")).lower().startswith(sid)
        or str(s.get("short_id", "")).lower() == sid
    ]
    if not matches:
        raise DrillError(
            "snapshot_missing",
            f"no convmem-chroma snapshot matches id {snapshot_id!r}",
        )
    if len(matches) > 1 and not any(str(s.get("id", "")).lower() == sid for s in matches):
        # Ambiguous short prefix
        ids = [s.get("short_id") for s in matches]
        raise DrillError("snapshot_ambiguous", f"ambiguous snapshot id {snapshot_id!r}: {ids}")
    if any(str(s.get("id", "")).lower() == sid for s in matches):
        return next(s for s in matches if str(s.get("id", "")).lower() == sid)
    return matches[0]


def parse_snapshot_time(snap: dict) -> datetime:
    raw = snap.get("time") or ""
    # restic: 2026-07-12T12:43:01.131567078-05:00
    if "." in raw:
        head, rest = raw.split(".", 1)
        # drop fractional to seconds, keep tz
        frac_and_tz = rest
        tz = ""
        for i, ch in enumerate(frac_and_tz):
            if ch in "+-" or (ch == "Z"):
                # find tz start: first + or - after digits, or Z
                pass
        # simpler: use fromisoformat after trimming nanos to micros
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            # trim fractional to 6 digits
            import re

            m = re.match(
                r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?([+-]\d{2}:\d{2}|Z)?",
                raw,
            )
            if not m:
                raise DrillError("snapshot_time", f"unparseable snapshot time: {raw!r}")
            frac = (m.group(2) or "")[:7]  # . + 6 digits
            tz = m.group(3) or "+00:00"
            if tz == "Z":
                tz = "+00:00"
            return datetime.fromisoformat(f"{m.group(1)}{frac}{tz}")
    return datetime.fromisoformat(raw)


def load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_created_at(fixture: dict) -> datetime:
    raw = fixture["created_at"]
    dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def assert_fixture_eligible(snap: dict, fixture: dict) -> None:
    snap_dt = parse_snapshot_time(snap)
    if snap_dt.tzinfo is None:
        snap_dt = snap_dt.replace(tzinfo=timezone.utc)
    created = fixture_created_at(fixture)
    if snap_dt < created:
        raise DrillError(
            "fixture_ineligible",
            f"snapshot time {snap_dt.isoformat()} predates fixture created_at {created.isoformat()}",
        )


def discover_chroma_root(run_dir: Path) -> Path:
    matches = sorted(run_dir.rglob("chroma.sqlite3"))
    if not matches:
        raise DrillError("discover_root", f"no chroma.sqlite3 under {run_dir}")
    if len(matches) > 1:
        # Prefer the deepest path that looks like a chroma dir (has sqlite + dirs)
        roots = [m.parent for m in matches]
        raise DrillError(
            "discover_root",
            f"multiple chroma.sqlite3 under run dir: {[str(r) for r in roots]}",
        )
    return matches[0].parent


# SQLite / PersistentClient sidecars created on open even for get_collection reads.
# Excluding them keeps the fingerprint sensitive to real mutations (new segments,
# collection dirs, document files) without false-failing on WAL/SHM.
# PersistentClient read-opens rewrite sqlite bookkeeping and HNSW segment
# bytes. Asserted "no mutation" uses a readonly logical fingerprint
# (collections + embedding ids) that stays stable across verify opens while
# still failing if units/collections are added or removed.
def fingerprint_logical(root: Path) -> str:
    """Readonly SQLite: collection names + sorted embedding ids."""
    db = root / "chroma.sqlite3"
    uri = f"file:{db}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM collections ORDER BY name")
        cols = cur.fetchall()
        lines: list[str] = []
        for cid, name in cols:
            cur.execute(
                """
                SELECT e.embedding_id
                FROM embeddings e
                JOIN segments s ON e.segment_id = s.id
                WHERE s.collection = ? AND s.scope = 'METADATA'
                ORDER BY e.embedding_id
                """,
                (cid,),
            )
            ids = [row[0] for row in cur.fetchall()]
            lines.append(f"{name}\0{len(ids)}\0{','.join(ids)}")
        return hashlib.sha256("\n".join(lines).encode()).hexdigest()
    finally:
        conn.close()


def fingerprint_tree(root: Path) -> str:
    """Logical store fingerprint (stable across read-only PersistentClient opens)."""
    return fingerprint_logical(root)


def ollama_reachable(host: str, timeout: float = 2.0) -> bool:
    url = host.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception:
        return False


class Report:
    def __init__(self, path: Path):
        self.path = path
        self.started = _utc_now()
        self.steps: list[dict[str, Any]] = []
        self.meta: dict[str, Any] = {
            "status": "in_progress",
            "started_at": self.started,
            "finished_at": None,
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
            f"# Chroma restore drill report",
            "",
            f"- status: **{self.meta.get('status')}**",
            f"- started: {self.meta.get('started_at')}",
            f"- finished: {self.meta.get('finished_at')}",
        ]
        for k in (
            "snapshot_id",
            "snapshot_short_id",
            "snapshot_time",
            "snapshot_paths",
            "run_dir",
            "chroma_root",
            "fixture",
        ):
            if k in self.meta:
                lines.append(f"- {k}: `{self.meta[k]}`")
        if self.meta.get("final_detail"):
            lines.append(f"- detail: {self.meta['final_detail']}")
        lines.append("")
        lines.append("| Step | Status | Detail |")
        lines.append("|------|--------|--------|")
        for s in self.steps:
            detail = (s.get("detail") or "").replace("|", "\\|")
            lines.append(f"| {s['name']} | {s['status']} | {detail} |")
        lines.append("")
        md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    t0 = time.monotonic()
    out = fn()
    return out, time.monotonic() - t0


def restic_restore(env: dict[str, str], snapshot_id: str, target: Path) -> None:
    proc = subprocess.run(
        ["restic", "restore", snapshot_id, "--target", str(target)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise DrillError(
            "restic_restore",
            (proc.stderr or proc.stdout or "restic restore failed").strip(),
        )


def run_mandatory_verify(chroma_root: Path, fixture: dict, report: Report) -> None:
    store = open_chroma_for_verify(str(chroma_root))
    try:
        # Missing collection must fail cleanly
        t0 = time.monotonic()
        try:
            store.client.get_collection(MISSING_COLLECTION)
            raise DrillError("missing_collection", "expected missing collection lookup to fail")
        except DrillError:
            raise
        except Exception as exc:
            report.step(
                "missing_collection",
                "PASS",
                f"{type(exc).__name__}: {exc}",
                duration_s=time.monotonic() - t0,
            )

        primary = fixture.get("primary_collection") or UNITS
        col = store._collection(primary)
        count = col.count()
        if count <= 0:
            raise DrillError("structural_count", f"{primary} count is {count}, need > 0")
        report.step("structural_count", "PASS", f"{primary} count={count}")

        for name in fixture.get("optional_collections") or [SUMMARIES]:
            t0 = time.monotonic()
            store._collection(name)  # existence only
            report.step(
                f"optional_exists:{name}",
                "PASS",
                "collection present",
                duration_s=time.monotonic() - t0,
            )

        for unit in fixture.get("units") or []:
            t0 = time.monotonic()
            got = store.get_unit(unit["chroma_id"], include_embedding=True)
            if got is None:
                raise DrillError("pinned_unit", f"missing chroma id {unit['chroma_id']}")
            meta = got.get("metadata") or {}
            lid = meta.get("ledger_id") or ""
            if lid != unit["ledger_id"]:
                raise DrillError(
                    "pinned_unit",
                    f"ledger_id mismatch: got {lid!r} want {unit['ledger_id']!r}",
                )
            digest = hashlib.sha256((got.get("document") or "").encode()).hexdigest()
            if digest != unit["document_sha256"]:
                raise DrillError(
                    "pinned_unit",
                    f"document sha256 mismatch for {unit['ledger_id']}: {digest} != {unit['document_sha256']}",
                )
            emb = got.get("embedding")
            if not emb:
                raise DrillError("vector_roundtrip", f"no embedding for {unit['chroma_id']}")
            hits = store.query_units(emb, top_k=3)
            hit_ids = [h.get("id") or (h.get("metadata") or {}).get("id") for h in hits]
            # query_units returns metadata with id often as chroma id in 'id' field of result
            ids = []
            for h in hits:
                ids.append(h.get("id"))
                mid = (h.get("metadata") or {}).get("id")
                if mid:
                    ids.append(mid)
            if unit["chroma_id"] not in ids:
                raise DrillError(
                    "vector_roundtrip",
                    f"unit {unit['chroma_id']} not in top-3: {hit_ids}",
                )
            report.step(
                "pinned_and_vector",
                "PASS",
                f"{unit['ledger_id']} digest ok; vector top-3 hit",
                duration_s=time.monotonic() - t0,
            )
    finally:
        store.close()


def run_optional_semantic(chroma_root: Path, report: Report, limit: int = 3) -> None:
    from config import load_config

    cfg = load_config()
    host = cfg.get("models", {}).get("ollama_host") or "http://localhost:11434"
    if not ollama_reachable(str(host)):
        report.step("semantic_subset", "SKIP", f"ollama unreachable at {host}")
        return
    eval_script = REPO / "scripts" / "eval-retrieval.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(eval_script),
            "--chroma-dir",
            str(chroma_root),
            "--limit",
            str(limit),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )
    if proc.returncode != 0:
        # Optional: SKIP on soft failure? Arch says PASS when expected IDs appear;
        # FAIL only when Ollama up and checks fail. Nonzero = FAIL for semantic.
        report.step(
            "semantic_subset",
            "FAIL",
            (proc.stderr or proc.stdout or "eval-retrieval failed")[-500:],
        )
        raise DrillError("semantic_subset", "optional semantic check failed while Ollama reachable")
    report.step("semantic_subset", "PASS", f"eval-retrieval --limit {limit}")


def ensure_parent(parent: Path) -> tuple[Path, Path]:
    runs = parent / "runs"
    reports = parent / "reports"
    runs.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    return runs, reports


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chroma Restic restore drill")
    parser.add_argument(
        "--snapshot",
        default="",
        help="Explicit snapshot id or short id (required unless --intentional-missing-snapshot)",
    )
    parser.add_argument(
        "--intentional-missing-snapshot",
        action="store_true",
        help="Exercise failure path with a nonexistent snapshot id",
    )
    parser.add_argument(
        "--parent",
        type=Path,
        default=Path(os.environ.get("CONVMEM_RESTORE_DRILL_PARENT", str(DEFAULT_PARENT))),
        help="Parent for runs/ and reports/ (gate 1 default under ~/.local/share/convmem/restore-drill)",
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--skip-semantic", action="store_true")
    parser.add_argument("--semantic-limit", type=int, default=3)
    parser.add_argument("--keep-run-dir", action="store_true", help="Skip cleanup (debug)")
    args = parser.parse_args(argv)

    runs_parent, reports_parent = ensure_parent(args.parent.expanduser())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = reports_parent / f"drill-{stamp}.json"
    report = Report(report_path)
    report.set_meta(fixture=str(args.fixture), parent=str(args.parent))

    run_dir: Path | None = None

    def cleanup() -> None:
        if run_dir is not None and run_dir.exists() and not args.keep_run_dir:
            shutil.rmtree(run_dir, ignore_errors=True)

    try:
        fixture = load_fixture(args.fixture)
        snapshot_id = (
            INTENTIONAL_BAD_SNAPSHOT
            if args.intentional_missing_snapshot
            else (args.snapshot or "").strip()
        )
        if not snapshot_id:
            raise DrillError("usage", "pass --snapshot ID or --intentional-missing-snapshot")

        env = _load_restic_env()
        snaps, dt = timed(lambda: list_tagged_snapshots(env))
        report.step("list_snapshots", "PASS", f"{len(snaps)} tagged", duration_s=dt)

        try:
            snap, dt = timed(lambda: resolve_snapshot(snaps, snapshot_id))
        except DrillError as exc:
            report.step("select_snapshot", "FAIL", exc.message)
            if args.intentional_missing_snapshot and exc.code == "snapshot_missing":
                # Architecture: intentional failure exits nonzero and still reports.
                report.finalize(
                    "FAIL",
                    "intentional missing-snapshot: selection failed as expected",
                )
                print(f"FAIL intentional-missing-snapshot (expected): {exc.message}")
                print(f"report={report_path}")
                return 1
            raise

        report.set_meta(
            snapshot_id=snap.get("id"),
            snapshot_short_id=snap.get("short_id"),
            snapshot_time=snap.get("time"),
            snapshot_paths=snap.get("paths"),
        )
        report.step(
            "select_snapshot",
            "PASS",
            f"{snap.get('short_id')} @ {snap.get('time')}",
            duration_s=dt,
        )

        assert_fixture_eligible(snap, fixture)
        report.step("fixture_gate", "PASS", f"fixture created_at={fixture['created_at']}")

        run_dir = Path(tempfile.mkdtemp(prefix="run-", dir=str(runs_parent)))
        report.set_meta(run_dir=str(run_dir))
        report.step("run_dir", "PASS", str(run_dir))

        _, dt = timed(lambda: restic_restore(env, str(snap["id"]), run_dir))
        report.step("restic_restore", "PASS", "exit 0", duration_s=dt)

        chroma_root, dt = timed(lambda: discover_chroma_root(run_dir))
        report.set_meta(chroma_root=str(chroma_root))
        report.step("discover_root", "PASS", str(chroma_root), duration_s=dt)

        fp_before, dt = timed(lambda: fingerprint_tree(chroma_root))
        report.step("fingerprint_before", "PASS", fp_before[:16] + "…", duration_s=dt)

        t0 = time.monotonic()
        run_mandatory_verify(chroma_root, fixture, report)
        report.step("mandatory_verify", "PASS", "all mandatory checks", duration_s=time.monotonic() - t0)

        if args.skip_semantic:
            report.step("semantic_subset", "SKIP", "--skip-semantic")
        else:
            run_optional_semantic(chroma_root, report, limit=args.semantic_limit)

        fp_after, dt = timed(lambda: fingerprint_tree(chroma_root))
        if fp_after != fp_before:
            raise DrillError(
                "fingerprint",
                f"restored root mutated during verify: {fp_before} -> {fp_after}",
            )
        report.step("fingerprint_after", "PASS", "unchanged", duration_s=dt)

        report.finalize("PASS", "happy path complete")
        print(f"PASS report={report_path}")
        print(f"  md={report_path.with_suffix('.md')}")
        return 0
    except DrillError as exc:
        report.step(exc.code, "FAIL", exc.message)
        report.finalize("FAIL", f"{exc.code}: {exc.message}")
        print(f"FAIL [{exc.code}] {exc.message}", file=sys.stderr)
        print(f"report={report_path}", file=sys.stderr)
        return 1
    except Exception as exc:
        report.step("crash", "FAIL", f"{type(exc).__name__}: {exc}")
        report.finalize("FAIL", str(exc))
        print(f"FAIL crash: {exc}", file=sys.stderr)
        print(f"report={report_path}", file=sys.stderr)
        return 1
    finally:
        cleanup()
        if run_dir is not None:
            exists = run_dir.exists()
            report.step(
                "cleanup",
                "PASS" if (not exists or args.keep_run_dir) else "FAIL",
                "kept" if args.keep_run_dir and exists else ("removed" if not exists else "still present"),
            )
            # rewrite after cleanup note
            if report.meta.get("status") == "PASS" and exists and not args.keep_run_dir:
                report.finalize("FAIL", "run dir not cleaned up")
            else:
                report._write()


if __name__ == "__main__":
    raise SystemExit(main())
