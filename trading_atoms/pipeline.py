from __future__ import annotations

from collections.abc import Callable


def run_strategy(strategy: Callable[..., dict | None], day_bars: list[dict], **params) -> dict | None:
    """Minimal generic strategy runner.

    Keeps future strategy calls uniform while the HTTP layer remains in server.py.
    """
    return strategy(day_bars, **params)
