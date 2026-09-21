"""OpenClaw activation controller — B/C production entrypoints refuse."""

from __future__ import annotations

import sys

RUNTIME_NOT_QUALIFIED = "runtime_not_qualified"
EX_CONFIG = 78


def refuse_runtime_not_qualified() -> None:
    print(RUNTIME_NOT_QUALIFIED, file=sys.stderr)
    raise SystemExit(EX_CONFIG)


def start(*_args, **_kwargs):
    refuse_runtime_not_qualified()


def main(argv: list[str] | None = None) -> int:
    refuse_runtime_not_qualified()
    return EX_CONFIG


if __name__ == "__main__":
    main()
