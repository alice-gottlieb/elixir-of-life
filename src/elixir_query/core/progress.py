"""Lightweight progress-bar helpers. tqdm if available, silent fallback otherwise."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any


@contextmanager
def progress_bar(total: int | None = None, desc: str = "", unit: str = "B", unit_scale: bool = True) -> Any:
    if os.environ.get("ELIXIR_QUERY_QUIET") == "1":
        yield _NullBar()
        return
    try:
        from tqdm.auto import tqdm
    except Exception:  # pragma: no cover - tqdm always present in our deps
        yield _NullBar()
        return
    bar = tqdm(total=total, desc=desc, unit=unit, unit_scale=unit_scale)
    try:
        yield bar
    finally:
        bar.close()


class _NullBar:
    def update(self, _n: int = 1) -> None:  # pragma: no cover
        return None
