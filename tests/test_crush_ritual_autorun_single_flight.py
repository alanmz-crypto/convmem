"""Crush ritual-autorun hook: single-flight per session + global doctor lock."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "scripts" / "crush-hook-convmem-ritual-autorun.sh"

STUB_CONVMEM = """#!/usr/bin/env bash
set -euo pipefail
log="${CONVMEM_STUB_LOG:?}"
case "${1:-}" in
  doctor)
    echo doctor >>"$log"
    sleep "${CONVMEM_STUB_DOCTOR_SLEEP:-1}"
    ;;
  brief)
    echo brief >>"$log"
    sleep "${CONVMEM_STUB_BRIEF_SLEEP:-0.2}"
    ;;
  unresolved)
    echo unresolved >>"$log"
    ;;
  *)
    echo "unknown:$*" >>"$log"
    ;;
esac
exit 0
"""


def _count_lines(log: Path, word: str) -> int:
    if not log.is_file():
        return 0
    return sum(1 for line in log.read_text().splitlines() if line.strip() == word)


@unittest.skipUnless(shutil.which("bash") and HOOK.is_file(), "needs bash + hook script")
class CrushRitualAutorunSingleFlightTests(unittest.TestCase):
    def _ritual_dir(self, cache: Path) -> Path:
        d = cache / "convmem-crush-ritual"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _markers_ok(self, ritual_dir: Path, session: str) -> bool:
        base = ritual_dir / f"progress-{session}"
        return all((Path(f"{base}.{s}")).is_file() for s in ("doctor", "brief", "unresolved"))

    def _run_hook(self, *, cache: Path, bin_dir: Path, session: str, log: Path) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env["XDG_CACHE_HOME"] = str(cache)
        env["CRUSH_SESSION_ID"] = session
        env["CONVMEM_STUB_LOG"] = str(log)
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
        return subprocess.run(
            ["bash", str(HOOK)],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    def _install_stub(self, tmp: Path) -> tuple[Path, Path, Path]:
        cache = tmp / "cache"
        cache.mkdir()
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        stub = bin_dir / "convmem"
        stub.write_text(STUB_CONVMEM, encoding="utf-8")
        stub.chmod(0o755)
        log = tmp / "convmem-invocations.log"
        log.touch()
        return cache, bin_dir, log

    def test_five_parallel_invocations_single_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            cache, bin_dir, log = self._install_stub(tmp)
            session = "parallel-sess-1"
            env_base = {
                "CONVMEM_STUB_DOCTOR_SLEEP": "1.5",
                "CONVMEM_STUB_BRIEF_SLEEP": "0.3",
            }

            def worker() -> subprocess.CompletedProcess:
                env = dict(os.environ)
                env.update(env_base)
                env["XDG_CACHE_HOME"] = str(cache)
                env["CRUSH_SESSION_ID"] = session
                env["CONVMEM_STUB_LOG"] = str(log)
                env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
                return subprocess.run(
                    ["bash", str(HOOK)],
                    cwd=REPO_ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )

            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = [pool.submit(worker) for _ in range(5)]
                results = [f.result() for f in as_completed(futures)]

            ritual_dir = self._ritual_dir(cache)
            for out in results:
                self.assertEqual(out.returncode, 0, f"stderr={out.stderr!r}")
            self.assertTrue(self._markers_ok(ritual_dir, session))
            self.assertEqual(_count_lines(log, "doctor"), 1)
            self.assertEqual(_count_lines(log, "brief"), 1)
            self.assertEqual(_count_lines(log, "unresolved"), 1)

    def test_global_doctor_lock_two_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            cache, bin_dir, log = self._install_stub(tmp)
            os.environ["CONVMEM_STUB_DOCTOR_SLEEP"] = "2"
            os.environ["CONVMEM_STUB_BRIEF_SLEEP"] = "0.1"

            errors: list[str] = []

            def run_a() -> None:
                out = self._run_hook(cache=cache, bin_dir=bin_dir, session="sess-a", log=log)
                if out.returncode != 0:
                    errors.append(f"a rc={out.returncode} stderr={out.stderr}")

            thread = threading.Thread(target=run_a)
            thread.start()
            # Let sess-a take the global doctor lock before sess-b runs.
            import time

            time.sleep(0.3)
            out_b = self._run_hook(cache=cache, bin_dir=bin_dir, session="sess-b", log=log)
            thread.join(timeout=60)
            self.assertFalse(errors, errors)
            self.assertEqual(out_b.returncode, 0, out_b.stderr)

            ritual_dir = self._ritual_dir(cache)
            self.assertTrue(self._markers_ok(ritual_dir, "sess-a"))
            self.assertTrue(self._markers_ok(ritual_dir, "sess-b"))
            self.assertEqual(_count_lines(log, "doctor"), 1)
            self.assertGreaterEqual(_count_lines(log, "brief"), 1)
            self.assertGreaterEqual(_count_lines(log, "unresolved"), 1)

    def test_disable_flag_skips_ritual(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            cache, bin_dir, log = self._install_stub(tmp)
            env = dict(os.environ)
            env["XDG_CACHE_HOME"] = str(cache)
            env["CRUSH_SESSION_ID"] = "opt-out"
            env["CONVMEM_STUB_LOG"] = str(log)
            env["CONVMEM_DISABLE_RITUAL_AUTORUN"] = "1"
            env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
            out = subprocess.run(
                ["bash", str(HOOK)],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(out.returncode, 0)
            self.assertEqual(_count_lines(log, "doctor"), 0)
            ritual_dir = self._ritual_dir(cache)
            self.assertFalse(self._markers_ok(ritual_dir, "opt-out"))


if __name__ == "__main__":
    unittest.main()
