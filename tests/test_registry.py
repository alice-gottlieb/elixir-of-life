"""Unit tests for the adapter registry."""

from __future__ import annotations

import polars as pl
import pytest

from elixir_query import registry
from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.errors import UnknownDatabaseError


def _make_dummy(name: str, aliases: tuple[str, ...] = (), **kwargs):
    class Dummy(BaseAdapter):
        meta = AdapterMeta(name=name, aliases=aliases, **kwargs)

        def query(self, **params):  # type: ignore[override]
            return pl.DataFrame({"x": [1]})

    Dummy.__name__ = f"Dummy_{name}"
    return Dummy


@pytest.fixture(autouse=True)
def _clean_registry(monkeypatch):
    # Snapshot and restore the registry so live adapters aren't perturbed.
    saved = dict(registry._REGISTRY)
    registry._REGISTRY.clear()
    yield
    registry._REGISTRY.clear()
    registry._REGISTRY.update(saved)


def test_register_and_resolve_by_canonical_name():
    Dummy = _make_dummy("foo")
    registry.register(Dummy)
    assert registry.resolve("foo") is Dummy


def test_resolve_is_case_insensitive():
    Dummy = _make_dummy("bar")
    registry.register(Dummy)
    assert registry.resolve("BaR") is Dummy
    assert registry.resolve(" bar ") is Dummy


def test_resolve_by_alias():
    Dummy = _make_dummy("baz", aliases=("qux", "quux"))
    registry.register(Dummy)
    assert registry.resolve("qux") is Dummy
    assert registry.resolve("quux") is Dummy


def test_unknown_database_raises_with_suggestion():
    Dummy = _make_dummy("uniprot")
    registry.register(Dummy)
    with pytest.raises(UnknownDatabaseError) as exc:
        registry.resolve("uinprot")  # typo
    assert exc.value.suggestion == "uniprot"


def test_collision_on_duplicate_registration():
    registry.register(_make_dummy("dup"))
    with pytest.raises(ValueError, match="collision"):
        registry.register(_make_dummy("dup"))


def test_list_names_returns_canonical_only():
    registry.register(_make_dummy("aaa", aliases=("aaa_alias",)))
    registry.register(_make_dummy("bbb"))
    names = registry.list_names()
    assert names == ["aaa", "bbb"]  # sorted, no aliases


def test_all_adapters_unique():
    D1 = _make_dummy("one", aliases=("uno",))
    D2 = _make_dummy("two")
    registry.register(D1)
    registry.register(D2)
    assert set(registry.all_adapters()) == {D1, D2}
