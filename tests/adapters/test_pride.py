"""Live PRIDE Archive adapter tests.

Policy: real data only. Tests hit www.ebi.ac.uk/pride/ws/archive/v2.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_pride_single_project_pxd000001():
    """PXD000001 is the first PRIDE project — a stable canonical sentinel."""
    df = eq.get("pride", accession="PXD000001")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for PXD000001, got {df.height}"

    cols = set(df.columns)
    assert "accession" in cols, f"missing 'accession' column: {df.columns}"
    assert "title" in cols, f"missing 'title' column: {df.columns}"

    assert df["accession"][0] == "PXD000001", (
        f"accession should be 'PXD000001', got {df['accession'][0]!r}"
    )
    assert df["title"][0], "title should be non-empty"


def test_pride_keyword_search():
    """Keyword search returns at least one project."""
    df = eq.get("pride", keyword="cancer", limit=3, page_size=3)

    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 3
    assert "accession" in df.columns


def test_pride_files_list():
    """PXD000001 should have associated files."""
    df = eq.get("pride", files_for="PXD000001", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected >=1 file for PXD000001, got {df.height}"


def test_pride_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("pride", accession="PXD000001")
    second = eq.get("pride", accession="PXD000001")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("pride/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for pride"


def test_pride_requires_some_arg():
    """Calling without any argument must raise loudly."""
    with pytest.raises(ValueError, match="accession|keyword|files"):
        eq.get("pride")
