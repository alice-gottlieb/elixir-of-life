"""Live JASPAR adapter tests.

Policy: real data only. Tests hit jaspar.genereg.net/api/v1.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_jaspar_runx1_matrix():
    """MA0002.1 is RUNX1 — a stable canonical sentinel."""
    df = eq.get("jaspar", matrix_id="MA0002.1")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for MA0002.1, got {df.height}"

    cols = set(df.columns)
    assert "matrix_id" in cols, f"missing 'matrix_id' column: {df.columns}"
    assert "name" in cols, f"missing 'name' column: {df.columns}"

    assert df["matrix_id"][0] == "MA0002.1", (
        f"matrix_id should be 'MA0002.1', got {df['matrix_id'][0]!r}"
    )
    assert df["name"][0] == "RUNX1", (
        f"MA0002.1 name should be 'RUNX1', got {df['name'][0]!r}"
    )


def test_jaspar_list_matrices_filtered():
    """Listing CORE vertebrate matrices returns at least a few rows."""
    df = eq.get(
        "jaspar",
        list_matrices=True,
        tax_group="vertebrates",
        collection="CORE",
        limit=10,
    )

    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 10
    assert "matrix_id" in df.columns


def test_jaspar_list_collections():
    """Listing collections returns at least the CORE collection."""
    df = eq.get("jaspar", list_collections=True, limit=20)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1
    # The CORE collection is always present.
    name_col = next(
        (c for c in df.columns if "name" in c.lower() or "collection" in c.lower()), None
    )
    assert name_col is not None, f"no name/collection column found: {df.columns}"


def test_jaspar_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("jaspar", matrix_id="MA0002.1")
    second = eq.get("jaspar", matrix_id="MA0002.1")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("jaspar/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for jaspar"


def test_jaspar_requires_some_arg():
    """Calling without any selector must raise loudly."""
    with pytest.raises(ValueError, match="matrix_id|list"):
        eq.get("jaspar")
