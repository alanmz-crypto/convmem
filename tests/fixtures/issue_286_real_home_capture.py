"""Stdlib-only capture of operator HOME before isolation redirects."""

from __future__ import annotations

import os
from pathlib import Path

REAL_HOME_ENV = "CONVMEM_TEST_REAL_HOME"


def capture_operator_home_now() -> Path:
    existing = os.environ.get(REAL_HOME_ENV)
    if existing is not None and str(existing).strip() != "":
        return Path(existing).expanduser().resolve()
    real = Path(os.environ.get("HOME", "/")).expanduser().resolve()
    os.environ[REAL_HOME_ENV] = str(real)
    return real


capture_operator_home_now()
