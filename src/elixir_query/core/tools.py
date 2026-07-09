"""Detection for optional third-party CLI tools (aspera, datasets, etc.)."""

from __future__ import annotations

import shutil

from elixir_query.errors import MissingToolError


def require(db: str, tool: str, *, install_hint: str) -> str:
    """Return the absolute path to ``tool`` on PATH or raise MissingToolError."""
    path = shutil.which(tool)
    if path is None:
        raise MissingToolError(db, tool, install_hint=install_hint)
    return path


def available(tool: str) -> bool:
    return shutil.which(tool) is not None


__all__ = ["available", "require"]
