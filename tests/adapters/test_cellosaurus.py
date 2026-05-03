"""Live Cellosaurus adapter tests.

Policy: real data only. Tests hit api.cellosaurus.org.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_cellosaurus_hela():
    """CVCL_0030 is HeLa — the canonical cancer cell line sentinel."""
    df = eq.get("cellosaurus", accession="CVCL_0030")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for CVCL_0030, got {df.height}"

    cols = set(df.columns)
    assert "primary_accession" in cols, f"missing 'primary_accession': {df.columns}"
    assert "identifier" in cols, f"missing 'identifier': {df.columns}"
    assert "species" in cols, f"missing 'species': {df.columns}"

    assert df["primary_accession"][0] == "CVCL_0030", (
        f"primary_accession should be 'CVCL_0030', got {df['primary_accession'][0]!r}"
    )
    assert df["identifier"][0] == "HeLa", (
        f"identifier should be 'HeLa', got {df['identifier'][0]!r}"
    )
    assert "Homo sapiens" in str(df["species"][0]), (
        f"species should be Homo sapiens, got {df['species'][0]!r}"
    )


def test_cellosaurus_search():
    """Searching for 'HeLa' should return at least one result."""
    df = eq.get("cellosaurus", search="HeLa", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 5
    identifiers = [str(v) for v in df["identifier"].to_list()]
    assert any("HeLa" in i for i in identifiers), identifiers


def test_cellosaurus_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("cellosaurus", accession="CVCL_0030")
    second = eq.get("cellosaurus", accession="CVCL_0030")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("cellosaurus/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for cellosaurus"


def test_cellosaurus_requires_some_arg():
    """Calling without any argument must raise loudly."""
    with pytest.raises(ValueError, match="accession|search"):
        eq.get("cellosaurus")
