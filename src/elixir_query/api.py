"""Public entry points: ``get``, ``list_databases``, ``describe``, ``clear_cache``."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import polars as pl

from elixir_query import registry
from elixir_query.config import get_config
from elixir_query.core.base import AdapterMeta, ElixirContext
from elixir_query.core.cache import Cache
from elixir_query.core.credentials import CredentialStore
from elixir_query.core.http import HttpClient

_CONTEXT: ElixirContext | None = None


def _context() -> ElixirContext:
    global _CONTEXT
    if _CONTEXT is None:
        cfg = get_config()
        _CONTEXT = ElixirContext(
            http=HttpClient(),
            cache=Cache(cfg.cache_dir),
            credentials=CredentialStore(cfg),
        )
    return _CONTEXT


def _reset_context_for_tests() -> None:
    """Test helper: drop the cached context so a new Config takes effect."""
    global _CONTEXT
    if _CONTEXT is not None:
        _CONTEXT.http.close()
    _CONTEXT = None


def get(database: str, *, bulk: bool = False, **params: Any) -> pl.DataFrame | pl.LazyFrame:
    """Fetch data from an ELIXIR database and return a Polars DataFrame (or LazyFrame).

    Args:
        database: Canonical name or alias (e.g. ``"uniprot"``, ``"swissprot"``).
        bulk: If True, request the adapter's bulk download path (returns LazyFrame).
        **params: Adapter-specific parameters; see ``elixir_query.describe(<db>)``.

    Raises:
        UnknownDatabaseError: if ``database`` is not registered.
        MissingCredentialError / MissingToolError: if creds/tools are needed.
        UpstreamError / ParseError: if the upstream call or parse fails.
    """
    cls = registry.resolve(database)
    adapter = cls(_context())
    if bulk:
        if not cls.meta.supports_bulk:
            raise ValueError(
                f"adapter {cls.meta.name!r} does not support bulk=True"
            )
        return adapter.bulk(**params)
    return adapter.query(**params)


def list_databases() -> list[str]:
    """Return the sorted list of canonical database names registered."""
    return registry.list_names()


def describe(database: str) -> dict[str, Any]:
    """Return a dict summarising the adapter's metadata (name, bulk support, etc.)."""
    cls = registry.resolve(database)
    meta: AdapterMeta = cls.meta
    return {
        **asdict(meta),
        "doc": (cls.__doc__ or "").strip(),
    }


def clear_cache(database: str | None = None) -> int:
    """Delete cached files for a single database or all databases. Returns file count."""
    ctx = _context()
    return ctx.cache.clear(database)


__all__ = ["get", "list_databases", "describe", "clear_cache"]
