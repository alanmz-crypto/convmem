"""Load convmem configuration from ~/.config/convmem/config.toml."""

import tomllib
from pathlib import Path

CONFIG_PATH = Path("~/.config/convmem/config.toml").expanduser()

# Keys whose string values are filesystem paths and should be expanduser()'d.
_PATH_KEYS = {"chroma_dir", "processed_log", "units_export", "inventory"}


def _expand(value):
    if isinstance(value, str):
        return str(Path(value).expanduser())
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


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
