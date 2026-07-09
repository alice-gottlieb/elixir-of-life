"""Adapter registry: maps canonical database names (and aliases) to adapter classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rapidfuzz import process

from elixir_query.errors import UnknownDatabaseError

if TYPE_CHECKING:
    from elixir_query.core.base import BaseAdapter


_REGISTRY: dict[str, type[BaseAdapter]] = {}


def register(adapter_cls: type[BaseAdapter]) -> type[BaseAdapter]:
    """Class decorator: register ``adapter_cls`` under its canonical name and aliases.

    Raises ValueError if the canonical name or any alias is already taken.
    """
    meta = adapter_cls.meta
    names = (meta.name, *meta.aliases)
    for n in names:
        key = n.lower()
        if key in _REGISTRY and _REGISTRY[key] is not adapter_cls:
            raise ValueError(
                f"adapter name collision: {n!r} already registered for "
                f"{_REGISTRY[key].__name__}, cannot register {adapter_cls.__name__}"
            )
        _REGISTRY[key] = adapter_cls
    return adapter_cls


def resolve(name: str) -> type[BaseAdapter]:
    """Return the adapter class for ``name``. Raises UnknownDatabaseError on miss."""
    key = name.lower().strip()
    if key in _REGISTRY:
        return _REGISTRY[key]
    # Fuzzy suggestion.
    canonical_names = sorted({cls.meta.name for cls in _REGISTRY.values()})
    match = process.extractOne(key, canonical_names, score_cutoff=60)
    suggestion = match[0] if match else None
    raise UnknownDatabaseError(name, suggestion)


def list_names() -> list[str]:
    """Return a sorted list of canonical adapter names (no aliases)."""
    return sorted({cls.meta.name for cls in _REGISTRY.values()})


def all_adapters() -> list[type[BaseAdapter]]:
    """Return every registered adapter class (unique)."""
    seen: set[int] = set()
    out: list[type[BaseAdapter]] = []
    for cls in _REGISTRY.values():
        if id(cls) not in seen:
            seen.add(id(cls))
            out.append(cls)
    return out


def _clear_for_tests() -> None:
    """Test helper: wipe the registry. Don't call from production code."""
    _REGISTRY.clear()


__all__ = ["register", "resolve", "list_names", "all_adapters"]
