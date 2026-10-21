#!/usr/bin/env python3
"""Independent Restic profile for Ryan's thirteen named project data roots.

The profile deliberately has no prune command. A successful backup is not a
two-copy result until the destination snapshot and its lineage are verified.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone


HOME = Path("/home/lauer")
SHARE = HOME / ".local/share"
RESTIC = HOME / ".local/bin/restic"
RESTIC_SHA256 = "20683e7746b70e99dd0538cc2740abd222dbb6b3a6851071be9880e3fe02694c"
LOCAL = SHARE / "restic-projects"
EXTERNAL_MOUNT = Path("/run/media/lauer/rxBUlauer-128Gfs")
EXTERNAL_UUID = "f1bd69b4-e567-4ef3-89ec-13faff0602e9"
EXTERNAL = EXTERNAL_MOUNT / "restic-projects"
RECOVERY_MOUNT = Path("/run/media/lauer/BIT-Brg-larch-7t")
RECOVERY_UUID = "b742a9e3-bc28-445b-b37f-e68fa959e70f"
RECOVERY = RECOVERY_MOUNT / "restic-projects-secrets/restic.password"
PRIVATE = HOME / ".config/restic-projects"
PASSWORD = PRIVATE / "restic.password"
STATE = HOME / ".local/state/restic-projects"
FULL_MARKER = STATE / "full-restore-verified.json"
TAG = "personal-projects-v1"

SOURCES = tuple(HOME / name for name in (
    "Projects/SubProjects/butsabad-email-ops",
    "Projects/SubProjects/ButsabaJobScout",
    "Projects/SubProjects/ButsabaPersonalHealth",
    "Projects/SubProjects/Ryan-Job_Scout",
    ".local/share/butsaba-calendar-mcp",
    ".local/share/butsaba-google-tools",
    ".local/share/butsaba-health-index",
    ".local/share/butsaba-health-index-batch3",
    ".local/share/butsaba-health-index-candidate",
    ".local/share/butsaba-health-index-rebase",
    ".local/share/butsaba-index-preview",
    ".local/share/butsaba-workspace-index",
    ".local/share/ryan-index-preview",
))

# Reviewed on 2026-10-21: these belong to the separate Google integration
# backup profile, not the thirteen requested project-data roots.
REVIEWED_ADJACENT = {"butsaba-google-backup", "butsaba-drive-tools"}
WRITER_SERVICES = (
    "butsabad-email-ops.timer",
    "butsabad-email-ops.service",
    "butsaba-health-index.service",
    "butsaba-workspace-index.service",
    "job-list-sync.service",
)


class GateError(RuntimeError):
    pass


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def digest(path: Path, *, deadline: float | None = None) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            if deadline is not None and time.monotonic() > deadline:
                raise GateError("Writer quiescence exceeded the 30-minute limit")
            h.update(block)
    return h.hexdigest()


def mounted_uuid(path: Path, expected: str) -> None:
    if path.is_symlink() or not path.is_mount():
        raise GateError(f"Required removable drive is not mounted: {path}")
    result = subprocess.run(
        ["findmnt", "-n", "-o", "UUID", "-T", str(path)],
        capture_output=True, text=True, check=True,
    )
    if result.stdout.strip() != expected or path.stat().st_dev == HOME.stat().st_dev:
        raise GateError(f"Removable drive identity mismatch: {path}")


def symlink_report() -> dict:
    external = []
    unreviewed = []
    total = 0
    for root in SOURCES:
        for parent, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                link = Path(parent) / name
                if not link.is_symlink():
                    continue
                total += 1
                target = Path(os.path.realpath(link))
                if not any(inside(target, source) for source in SOURCES):
                    external.append({"path": str(link), "target": str(target)})
                    fixture = inside(link, SHARE / "ryan-index-preview/crush-tests-v2") \
                        and target == Path("/etc/hosts")
                    stale_socket = inside(link, SHARE / "butsaba-index-preview") \
                        and link.name == "SingletonSocket" \
                        and str(target).startswith("/tmp/scoped_dir")
                    if not (fixture or stale_socket):
                        unreviewed.append({"path": str(link), "target": str(target)})
    payload = json.dumps(external, sort_keys=True, separators=(",", ":")).encode()
    return {
        "total": total,
        "outside_manifest": len(external),
        "outside_manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "reviewed_outside": len(external) - len(unreviewed),
        "unreviewed_outside": unreviewed[:20],
    }


def reviewed_socket(path: Path) -> bool:
    return inside(path, SHARE / "butsaba-index-preview") and \
        "profiles" in path.parts and "runtime" in path.parts


def reviewed_fifo(path: Path) -> bool:
    return inside(path, SHARE / "ryan-index-preview/crush-tests-v2") and \
        "evidence" in path.parts and \
        any(part.startswith("save-snapshot-") for part in path.parts) and \
        path.name == "pipe"


def special_report() -> dict:
    sockets = 0
    fifos = 0
    unreviewed = []
    for root in SOURCES:
        for parent, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                path = Path(parent) / name
                mode = path.lstat().st_mode
                if stat.S_ISSOCK(mode):
                    sockets += 1
                    if not reviewed_socket(path):
                        unreviewed.append(str(path))
                elif stat.S_ISFIFO(mode):
                    fifos += 1
                    if not reviewed_fifo(path):
                        unreviewed.append(str(path))
                elif stat.S_ISBLK(mode) or stat.S_ISCHR(mode):
                    unreviewed.append(str(path))
    return {"runtime_sockets_not_restorable": sockets,
            "fifo_entries": fifos, "unreviewed": unreviewed[:20]}


def preflight(*, require_local: bool = False,
              require_external: bool = False) -> dict:
    errors = []
    if len(SOURCES) != 13 or len(set(SOURCES)) != 13:
        errors.append("Source manifest must contain exactly thirteen unique roots")
    for source in SOURCES:
        if source.is_symlink() or not source.is_dir() or source.resolve() != source:
            errors.append(f"Missing, redirected, or noncanonical source: {source}")
    for i, source in enumerate(SOURCES):
        if any(inside(source, other) or inside(other, source)
               for other in SOURCES[i + 1:]):
            errors.append(f"Nested source roots: {source}")
    for destination in (LOCAL, EXTERNAL, PASSWORD, RECOVERY, STATE):
        resolved = destination.resolve(strict=False)
        if destination.is_symlink() or any(
            inside(candidate, source) or inside(source, candidate)
            for source in SOURCES for candidate in (destination, resolved)
        ):
            errors.append(f"Backup destination overlaps a source: {destination}")
    mounts = subprocess.run(["findmnt", "-rn", "-o", "TARGET"],
                            capture_output=True, text=True, check=True)
    for entry in mounts.stdout.splitlines():
        mount = Path(entry)
        if any(inside(mount, source) for source in SOURCES):
            errors.append(f"Mounted filesystem inside a source needs review: {mount}")
    adjacent = {p.name for p in SHARE.iterdir()
                if p.is_dir() and (p.name.startswith("butsaba") or
                                   p.name.startswith("ryan"))}
    known = {p.name for p in SOURCES if p.parent == SHARE} | REVIEWED_ADJACENT
    unreviewed = sorted(adjacent - known)
    if unreviewed:
        errors.append("New adjacent directories need scope review: " +
                      ", ".join(unreviewed))
    if not RESTIC.is_file() or digest(RESTIC) != RESTIC_SHA256:
        errors.append(f"Pinned Restic executable missing or changed: {RESTIC}")
    if require_external:
        for mount, uuid in ((EXTERNAL_MOUNT, EXTERNAL_UUID),
                            (RECOVERY_MOUNT, RECOVERY_UUID)):
            try:
                mounted_uuid(mount, uuid)
            except (GateError, subprocess.CalledProcessError) as exc:
                errors.append(str(exc))
    if require_local or require_external:
        for repo in ((LOCAL, EXTERNAL) if require_external else (LOCAL,)):
            if not (repo / "config").is_file():
                errors.append(f"Repository not initialized: {repo}")
        if PASSWORD.is_symlink() or not PASSWORD.is_file() or \
                stat.S_IMODE(PASSWORD.stat().st_mode) != 0o600:
            errors.append(f"Missing or unsafe password: {PASSWORD}")
        elif require_external and (not RECOVERY.is_file() or RECOVERY.is_symlink() or \
                stat.S_IMODE(RECOVERY.stat().st_mode) != 0o600 or \
                digest(PASSWORD) != digest(RECOVERY)):
            errors.append(f"Offline password copy missing or differs: {RECOVERY}")
    links = symlink_report() if not errors else None
    if links and links["unreviewed_outside"]:
        errors.append("Symlinks outside manifest need review")
    specials = special_report() if not errors else None
    if specials and specials["unreviewed"]:
        errors.append("Special files need review")
    return {"ok": not errors, "sources": [str(p) for p in SOURCES],
            "reviewed_adjacent": sorted(REVIEWED_ADJACENT),
            "unreviewed_adjacent": unreviewed, "symlinks": links,
            "special_files": specials,
            "errors": errors}


def require_ready() -> dict:
    result = preflight(require_external=True)
    if not result["ok"]:
        raise GateError("Preflight failed: " + "; ".join(result["errors"]))
    return result


def require_local_ready() -> dict:
    result = preflight(require_local=True)
    if not result["ok"]:
        raise GateError("Local preflight failed: " + "; ".join(result["errors"]))
    return result


def restic(repo: Path, *args: str, json_result: bool = False,
           from_repo: Path | None = None, recovery: bool = False,
           timeout: float | None = None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("RESTIC_")}
    env["GOMAXPROCS"] = "2"
    key = RECOVERY if recovery else PASSWORD
    command = [str(RESTIC), "--no-cache", "--repo", str(repo),
               "--password-file", str(key)]
    command.append(args[0])
    if from_repo is not None:
        command += ["--from-repo", str(from_repo),
                    "--from-password-file", str(PASSWORD)]
    command += list(args[1:])
    result = subprocess.run(command, env=env, capture_output=True, text=True,
                            timeout=timeout)
    if result.returncode:
        raise GateError(f"Restic {args[0]} exited {result.returncode}: " +
                        result.stderr[-1200:])
    return json.loads(result.stdout) if json_result else result.stdout


def private_directory(path: Path) -> None:
    if path.is_symlink():
        raise GateError(f"Refusing symlink directory: {path}")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise GateError(f"Directory must be owned by user with mode 700: {path}")


def initialize() -> None:
    base = preflight()
    if not base["ok"]:
        raise GateError("Preflight failed: " + "; ".join(base["errors"]))
    mounted_uuid(EXTERNAL_MOUNT, EXTERNAL_UUID)
    mounted_uuid(RECOVERY_MOUNT, RECOVERY_UUID)
    for folder in (PRIVATE, STATE, EXTERNAL, RECOVERY.parent):
        private_directory(folder)
    if not PASSWORD.exists():
        if (LOCAL / "config").exists() or (EXTERNAL / "config").exists() or RECOVERY.exists():
            raise GateError("Repository or recovery key exists; refusing to replace password")
        fd = os.open(PASSWORD, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w") as handle:
            handle.write(secrets.token_urlsafe(48) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
    if PASSWORD.is_symlink() or stat.S_IMODE(PASSWORD.stat().st_mode) != 0o600:
        raise GateError("Local password must be mode 600 and not a symlink")
    if not RECOVERY.exists():
        fd = os.open(RECOVERY, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(PASSWORD.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
    if RECOVERY.is_symlink() or stat.S_IMODE(RECOVERY.stat().st_mode) != 0o600 or \
            digest(RECOVERY) != digest(PASSWORD):
        raise GateError("Offline password copy is missing, unsafe, or mismatched")
    if not (LOCAL / "config").exists():
        restic(LOCAL, "init")
    if not (EXTERNAL / "config").exists():
        restic(EXTERNAL, "init", "--copy-chunker-params", from_repo=LOCAL)
    require_ready()


def snapshot_id(output: str) -> str:
    summaries = [json.loads(line) for line in output.splitlines()
                 if line.startswith("{") and
                 json.loads(line).get("message_type") == "summary"]
    if len(summaries) != 1 or not summaries[0].get("snapshot_id"):
        raise GateError("Restic did not emit one complete snapshot ID")
    return summaries[0]["snapshot_id"]


def exact_snapshot(repo: Path, sid: str, *, original: str | None = None) -> dict:
    snapshots = restic(repo, "snapshots", "--json", sid, json_result=True)
    selected = [s for s in snapshots if s["id"] == sid]
    if len(selected) != 1 or set(selected[0].get("paths", [])) != {str(p) for p in SOURCES}:
        raise GateError(f"Snapshot lacks the exact thirteen source roots: {sid}")
    if original is not None and selected[0].get("original") != original:
        raise GateError(f"Offsite lineage does not match local snapshot: {sid}")
    return selected[0]


def copy_and_verify(sid: str, *, full_read: bool) -> dict:
    mounted_uuid(EXTERNAL_MOUNT, EXTERNAL_UUID)
    exact_snapshot(LOCAL, sid)
    restic(EXTERNAL, "copy", sid, from_repo=LOCAL)
    snapshots = restic(EXTERNAL, "snapshots", "--json", json_result=True)
    matches = [s for s in snapshots if s.get("original") == sid and
               set(s.get("paths", [])) == {str(p) for p in SOURCES}]
    if len(matches) != 1:
        raise GateError(f"Cannot identify one offsite copy of {sid}")
    copied = matches[0]["id"]
    exact_snapshot(EXTERNAL, copied, original=sid)
    for repo in (LOCAL, EXTERNAL):
        restic(repo, "check", "--read-data" if full_read else "--read-data-subset=5%")
    return {"local_snapshot": sid, "external_snapshot": copied,
            "external_original": matches[0]["original"],
            "data_read": "full" if full_read else "5% each repository"}


def source_inventory(*, deadline: float | None = None) -> tuple[dict, list[Path]]:
    """Hash every regular source file while known writers are stopped."""
    entries: dict[str, dict] = {}
    samples: list[Path] = []
    for root in SOURCES:
        sample = None
        for parent, dirs, files in os.walk(root, followlinks=False):
            if deadline is not None and time.monotonic() > deadline:
                raise GateError("Writer quiescence exceeded the 30-minute limit")
            dirs.sort()
            for name in sorted(dirs + files):
                path = Path(parent) / name
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode):
                    entries[str(path)] = {"link": os.readlink(path)}
                elif stat.S_ISREG(mode):
                    entries[str(path)] = {"sha256": digest(path, deadline=deadline),
                                          "size": path.stat().st_size,
                                          "mode": stat.S_IMODE(mode)}
                    if sample is None:
                        sample = path
                elif stat.S_ISSOCK(mode) and reviewed_socket(path):
                    # Restic cannot archive a live Unix socket endpoint.
                    continue
                elif stat.S_ISFIFO(mode) and reviewed_fifo(path):
                    entries[str(path)] = {"fifo": stat.S_IMODE(mode)}
                elif not stat.S_ISDIR(mode):
                    raise GateError(f"Unsupported source type: {path}")
        if sample is None:
            raise GateError(f"No regular file available for restore test: {root}")
        samples.append(sample)
    return entries, samples


def writable_open_files() -> list[str]:
    """Find currently open writable descriptors into a requested root."""
    found = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            for fd in (proc / "fd").iterdir():
                try:
                    target = Path(os.readlink(fd))
                    if not any(inside(target, root) for root in SOURCES):
                        continue
                    flags = next(line.split()[1] for line in
                                 (proc / "fdinfo" / fd.name).read_text().splitlines()
                                 if line.startswith("flags:"))
                    if int(flags, 8) & os.O_ACCMODE:
                        found.append(f"pid={proc.name} path={target}")
                except FileNotFoundError:
                    continue
        except (FileNotFoundError, PermissionError):
            continue
    return found[:30]


def systemctl(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(["systemctl", "--user", *args],
                                capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired as exc:
        raise GateError(f"systemctl {' '.join(args)} timed out") from exc
    if check and result.returncode:
        raise GateError(f"systemctl {' '.join(args)} failed: " + result.stderr[-500:])
    return result


def quiesce_services() -> list[str]:
    active = []
    try:
        for unit in WRITER_SERVICES:
            if systemctl("is-active", "--quiet", unit, check=False).returncode == 0:
                active.append(unit)
                systemctl("stop", unit)
                if systemctl("is-active", "--quiet", unit, check=False).returncode == 0:
                    raise GateError(f"Writer did not stop: {unit}")
    except Exception:
        restart_services(active)
        raise
    return active


def restart_services(active: list[str]) -> None:
    failures = []
    for unit in reversed(active):
        try:
            systemctl("start", unit)
            if systemctl("is-active", "--quiet", unit, check=False).returncode != 0:
                raise GateError(f"Writer did not resume: {unit}")
        except GateError as exc:
            failures.append(str(exc))
    if failures:
        raise GateError("; ".join(failures))


def restored_path(target: Path, original: Path) -> Path:
    return target / original.relative_to(Path("/"))


def restore_drill(sid: str, samples: list[Path], before: dict,
                  *, full: bool) -> dict:
    with tempfile.TemporaryDirectory(prefix="restic-projects-restore-",
                                     dir=HOME / "tmp") as scratch:
        target = Path(scratch) / "restore"
        target.mkdir(mode=0o700)
        command = ["restore", sid, "--target", str(target), "--verify"]
        if not full:
            for sample in samples:
                command += ["--include", str(sample)]
        restic(EXTERNAL, *command, recovery=True)
        for sample in samples:
            restored = restored_path(target, sample)
            if not restored.is_file() or digest(restored) != before[str(sample)]["sha256"]:
                raise GateError(f"Representative restore mismatch: {sample}")
        sqlite_checked = 0
        if full:
            for parent, _, files in os.walk(target):
                for name in files:
                    path = Path(parent) / name
                    if path.is_symlink() or not path.is_file():
                        continue
                    with path.open("rb") as handle:
                        if handle.read(16) != b"SQLite format 3\x00":
                            continue
                    # Deliberately corrupt databases inside test fixtures are
                    # backed up byte-for-byte, but are not operational stores.
                    if "crush-tests" in path.parts or "crush-tests-v2" in path.parts:
                        continue
                    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                    try:
                        answer = connection.execute("PRAGMA integrity_check").fetchone()
                    finally:
                        connection.close()
                    if answer != ("ok",):
                        raise GateError(f"Restored SQLite integrity failed: {path}")
                    sqlite_checked += 1
        return {"restore": "full" if full else "one file per root",
                "sample_files_verified": len(samples),
                "sqlite_integrity_checked": sqlite_checked}


def backup(*, quiesce: bool, full_read: bool) -> dict:
    if not quiesce:
        raise GateError("Backup requires an explicit approved writer-quiescence mode")
    require_local_ready()
    if not FULL_MARKER.is_file():
        full_read = True
    else:
        try:
            last_full = datetime.fromisoformat(json.loads(
                FULL_MARKER.read_text())["timestamp_utc"])
            if (datetime.now(timezone.utc) - last_full).days >= 30:
                full_read = True
        except (KeyError, ValueError, json.JSONDecodeError):
            full_read = True
    local_sid = None
    before = None
    samples = None
    stopped: list[str] = []
    capture_error = None
    try:
        stopped = quiesce_services()
        deadline = time.monotonic() + 1800
        open_files = writable_open_files()
        if open_files:
            raise GateError("Unknown writable open files: " + "; ".join(open_files))
        before, samples = source_inventory(deadline=deadline)
        output = restic(LOCAL, "backup", "--json", "--tag", TAG,
                        *map(str, SOURCES),
                        timeout=max(1, deadline - time.monotonic()))
        local_sid = snapshot_id(output)
        exact_snapshot(LOCAL, local_sid)
        after, _ = source_inventory(deadline=deadline)
        postflight = preflight()
        if not postflight["ok"]:
            raise GateError("Post-capture manifest check failed: " +
                            "; ".join(postflight["errors"]))
        if before != after:
            raise GateError("A source changed during capture; snapshot retained but not trusted")
    except Exception as exc:
        capture_error = exc
    finally:
        try:
            restart_services(stopped)
        except GateError as exc:
            capture_error = GateError(f"Service restart failed: {exc}; capture={capture_error}")
    if capture_error:
        return {"result": "FAIL", "local_snapshot": local_sid,
                "external_copy": "not attempted", "error": str(capture_error)}
    assert local_sid and before is not None and samples is not None
    try:
        copied = copy_and_verify(local_sid, full_read=full_read)
        drill = restore_drill(copied["external_snapshot"], samples, before,
                              full=full_read)
        return {"result": "TWO_COPY_VERIFIED", "entries": len(before),
                **copied, **drill}
    except Exception as exc:
        return {"result": "LOCAL_ONLY", "local_snapshot": local_sid,
                "external_copy": "failed or unverified", "error": str(exc)}


def report(result: dict) -> None:
    result.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    print(json.dumps(result, sort_keys=True), flush=True)


def save_report(result: dict) -> None:
    result.setdefault("timestamp_utc", datetime.now(timezone.utc).isoformat())
    private_directory(STATE)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=STATE,
                                     prefix="report-", delete=False) as handle:
        path = Path(handle.name)
        json.dump(result, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(path, STATE / "last-run.json")
    fd = os.open(STATE, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_full_marker(result: dict) -> None:
    if result.get("result") != "TWO_COPY_VERIFIED" or \
            result.get("data_read") != "full" or result.get("restore") != "full":
        return
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=STATE,
                                     prefix="full-", delete=False) as handle:
        path = Path(handle.name)
        json.dump({"timestamp_utc": result["timestamp_utc"],
                   "local_snapshot": result["local_snapshot"],
                   "external_snapshot": result["external_snapshot"]}, handle)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(path, FULL_MARKER)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "init", "backup", "copy"))
    parser.add_argument("--snapshot-id", help="full local snapshot ID for copy")
    parser.add_argument("--full-read", action="store_true")
    parser.add_argument("--quiesce-known-writers", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.command == "preflight":
            result = preflight()
            report(result)
            return 0 if result["ok"] else 1
        if args.command == "init":
            initialize()
            report({"result": "INITIALIZED", "local": str(LOCAL),
                    "external": str(EXTERNAL), "password_backup": str(RECOVERY)})
            return 0
        if args.command == "backup":
            private_directory(STATE)
            with (STATE / "profile.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                result = backup(quiesce=args.quiesce_known_writers,
                                full_read=args.full_read)
                save_report(result)
                save_full_marker(result)
                report(result)
                return 0 if result["result"] == "TWO_COPY_VERIFIED" else 1
        if not args.snapshot_id or len(args.snapshot_id) != 64 or \
                any(c not in "0123456789abcdef" for c in args.snapshot_id):
            raise GateError("copy requires one explicit full 64-character snapshot ID")
        private_directory(STATE)
        with (STATE / "profile.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require_ready()
            result = {"result": "COPY_CHECKED", **copy_and_verify(
                args.snapshot_id, full_read=args.full_read)}
            save_report(result)
            report(result)
        return 0
    except (GateError, OSError, subprocess.CalledProcessError) as exc:
        failure = {"result": "FAIL", "error": str(exc)}
        if args.command in ("backup", "copy") and STATE.is_dir():
            try:
                save_report(failure)
            except OSError:
                pass
        report(failure)
        return 1


if __name__ == "__main__":
    sys.exit(main())

# ref: ../docs/backup/restic-personal-projects.md — activation and recovery procedure
# src: ../config/restic.env.example — existing ConvMem profile boundary (kept separate)
