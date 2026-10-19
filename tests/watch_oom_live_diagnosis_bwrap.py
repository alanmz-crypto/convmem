"""Test-only bwrap envelope for D1 outer worker isolation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def bwrap_available() -> bool:
    return shutil.which("bwrap") is not None


def bwrap_userns_available() -> bool:
    """True when bubblewrap can unshare user namespaces (CI may lack this)."""
    if not bwrap_available():
        return False
    probe = subprocess.run(
        ["bwrap", "--unshare-user", "--ro-bind", "/", "/", "--", "true"],
        capture_output=True,
        check=False,
        timeout=10,
    )
    return probe.returncode == 0


def d1_bwrap_integration_available() -> bool:
    """Skip bwrap-only integration probes when the host cannot run user-ns bwrap."""
    return bwrap_userns_available()


BWRAP_RO_ROOT_ARGS: tuple[str, ...] = (
    "--ro-bind",
    "/",
    "/",
    "--proc",
    "/proc",
    "--dev",
    "/dev",
)


def production_convmem_mask_ro_binds(scratch_root: Path) -> list[tuple[str, str]]:
    """RO-bind empty dirs over production ConvMem paths (hide corpus + config)."""
    mask_root = scratch_root.resolve() / ".bwrap-production-mask"
    share_empty = mask_root / "empty-local-share-convmem"
    config_empty = mask_root / "empty-config-convmem"
    share_empty.mkdir(parents=True, exist_ok=True)
    config_empty.mkdir(parents=True, exist_ok=True)
    prod_share = (Path.home() / ".local/share/convmem").resolve()
    prod_config = (Path.home() / ".config/convmem").resolve()
    return [
        (str(share_empty), str(prod_share)),
        (str(config_empty), str(prod_config)),
    ]


def build_bwrap_command(
    inner_argv: list[str],
    *,
    scratch_root: Path,
    source_path: Path,
    repo_root: Path,
    external_ro_binds: list[Path] | None = None,
) -> list[str]:
    """Wrap worker argv: RO root via /, scratch writable bind, source RO (no repo overlay)."""
    if not bwrap_available():
        raise RuntimeError("bwrap_unavailable")
    scratch_root = scratch_root.resolve()
    source_path = source_path.resolve()
    repo_root = repo_root.resolve()
    if scratch_root.is_relative_to(repo_root):
        pass  # scratch must stay a separate bind; never ro-bind repo_root on top
    cmd: list[str] = [
        "bwrap",
        "--unshare-user",
        "--unshare-net",
        "--die-with-parent",
        *BWRAP_RO_ROOT_ARGS,
        "--tmpfs",
        "/tmp",
    ]
    for empty, target in production_convmem_mask_ro_binds(scratch_root):
        cmd.extend(["--ro-bind", empty, target])
    prod_share = (Path.home() / ".local/share/convmem").resolve()
    chdir = str(repo_root)
    if repo_root.is_relative_to(prod_share / "worktrees"):
        wt_mount = "/tmp/convmem-worktree-repo"
        cmd.extend(["--ro-bind", str(repo_root), wt_mount])
        chdir = wt_mount
    cmd.extend(
        [
            "--bind",
            str(scratch_root),
            str(scratch_root),
            "--ro-bind",
            str(source_path),
            str(source_path),
            "--chdir",
            chdir,
        ]
    )
    for bind_path in external_ro_binds or ():
        resolved = bind_path.expanduser().resolve()
        if resolved.is_file():
            cmd.extend(["--ro-bind", str(resolved), str(resolved)])
        elif resolved.is_dir():
            cmd.extend(["--ro-bind", str(resolved), str(resolved)])
    cmd.extend(["--", *inner_argv])
    return cmd


def production_convmem_dirs() -> tuple[Path, Path]:
    return (
        (Path.home() / ".local/share/convmem").resolve(),
        (Path.home() / ".config/convmem").resolve(),
    )


def write_denied_without_mutation(path: Path) -> bool:
    """True when *path* cannot be opened for writing; never writes, creates, or truncates."""
    target = path if os.path.lexists(path) else path.parent
    if os.access(target, os.W_OK):
        return False
    if not os.path.isfile(path):
        return True
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return True
    os.close(fd)
    return False


def production_dirs_hidden() -> bool:
    """True when production ConvMem dirs are visible only as empty masks."""
    for prod in production_convmem_dirs():
        try:
            if os.listdir(prod):
                return False
        except FileNotFoundError:
            continue
        except OSError:
            return False
    return True


def production_dirs_write_denied() -> bool:
    return all(write_denied_without_mutation(prod) for prod in production_convmem_dirs())


def run_bwrap_capability_check(
    *,
    scratch_root: Path,
    source_path: Path,
    repo_root: Path,
    repo_probe_file: Path,
    timeout: float = 30.0,
) -> dict[str, bool]:
    """FS capability proof inside bwrap; only the scratch probe writes."""
    script = (
        "import json, os, sys\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(repo_root.resolve())!r})\n"
        "from tests.watch_oom_live_diagnosis_bwrap import (\n"
        "    production_dirs_hidden, production_dirs_write_denied,\n"
        "    write_denied_without_mutation,\n"
        ")\n"
        f"scratch = {str(scratch_root)!r}\n"
        f"source = Path({str(source_path)!r})\n"
        f"repo_probe = Path({str(repo_probe_file)!r})\n"
        "out = {}\n"
        "p = os.path.join(scratch, 'bwrap_write_probe.txt')\n"
        "try:\n"
        "    with open(p, 'w', encoding='utf-8') as handle:\n"
        "        handle.write('ok\\n')\n"
        "    out['scratch_writable'] = os.path.isfile(p)\n"
        "except OSError:\n"
        "    out['scratch_writable'] = False\n"
        "out['source_readonly'] = write_denied_without_mutation(source)\n"
        "out['repo_readonly'] = write_denied_without_mutation(repo_probe)\n"
        "out['production_share_read_blocked'] = production_dirs_hidden()\n"
        "out['production_share_write_blocked'] = production_dirs_write_denied()\n"
        "print(json.dumps(out))\n"
    )
    cmd = build_bwrap_command(
        [sys.executable, "-c", script],
        scratch_root=scratch_root,
        source_path=source_path,
        repo_root=repo_root,
    )
    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"bwrap_capability_check_failed:{result.stderr.strip()}")
    payload = json.loads(result.stdout.strip())
    return {
        "scratch_writable": bool(payload.get("scratch_writable")),
        "source_readonly": bool(payload.get("source_readonly")),
        "repo_readonly": bool(payload.get("repo_readonly")),
        "production_share_read_blocked": bool(payload.get("production_share_read_blocked")),
        "production_share_write_blocked": bool(payload.get("production_share_write_blocked")),
    }


D1_PARENT_NETNS_ENV = "CONVMEM_LIVE_DIAG_PARENT_NETNS"


def verify_d1_kernel_envelope(
    *,
    scratch_root: Path,
    source_path: Path,
    repo_root: Path,
) -> None:
    """Behavioral check: RO root, writable scratch, net ns distinct from parent hint."""
    scratch_root = scratch_root.resolve()
    source_path = source_path.resolve()
    repo_root = repo_root.resolve()
    probe = scratch_root / ".d1_envelope_write_probe"
    try:
        probe.write_text("1\n", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise RuntimeError("d1_envelope_scratch_not_writable") from exc
    repo_marker = repo_root / "tests" / "watch_oom_live_diagnosis_bwrap.py"
    if not write_denied_without_mutation(repo_marker):
        raise RuntimeError("d1_envelope_root_not_readonly")
    if not write_denied_without_mutation(source_path):
        raise RuntimeError("d1_envelope_source_not_readonly")
    if not production_dirs_hidden():
        raise RuntimeError("d1_envelope_production_share_visible")
    if not production_dirs_write_denied():
        raise RuntimeError("d1_envelope_production_share_writable")
    parent_ns = os.environ.get(D1_PARENT_NETNS_ENV, "").strip()
    if not parent_ns:
        raise RuntimeError("d1_envelope_parent_netns_missing")
    self_ns = net_namespace_id(os.getpid())
    if not self_ns or self_ns == parent_ns:
        raise RuntimeError("d1_envelope_net_not_isolated")


def net_namespace_id(pid: int) -> str | None:
    link = Path(f"/proc/{pid}/ns/net")
    if not link.is_symlink():
        return None
    try:
        return os.readlink(link)
    except OSError:
        return None
