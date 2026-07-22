"""Load convmem configuration from ~/.config/convmem/config.toml."""

import os
import tomllib
from pathlib import Path

CONFIG_PATH = Path(
    os.environ.get("CONVMEM_CONFIG", "~/.config/convmem/config.toml")
).expanduser()

# Keys whose string values are filesystem paths and should be expanduser()'d.
_PATH_KEYS = {"chroma_dir", "processed_log", "units_export", "inventory"}


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
    import json

    print(json.dumps(load_config(), indent=2))
