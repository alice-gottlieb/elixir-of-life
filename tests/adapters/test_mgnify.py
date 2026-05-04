"""Live MGnify adapter tests.

Policy: real data only. Tests hit www.ebi.ac.uk/metagenomics/api.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_mgnify_single_study():
    """ERP009004 is a stable public MGnify study (used in their docs as the example)."""
    df = eq.get("mgnify", resource="studies", accession="ERP009004")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for ERP009004, got {df.height}"

    cols = set(df.columns)
    assert "type" in cols, f"missing 'type' column: {df.columns}"
    assert "id" in cols, f"missing 'id' column: {df.columns}"

    assert df["type"][0] == "studies", f"resource type should be 'studies', got {df['type'][0]!r}"


def test_mgnify_samples_for_study():
    """ERP009004 has samples — fetching them should return non-empty rows."""
    df = eq.get("mgnify", samples_for="ERP009004", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected >=1 sample for ERP009004, got {df.height}"
    assert df["type"][0] == "samples"


def test_mgnify_list_studies():
    """list_resource='studies' returns a paginated list."""
    df = eq.get("mgnify", list_resource="studies", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 5
    assert "type" in df.columns
    assert df["type"][0] == "studies"


def test_mgnify_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("mgnify", resource="studies", accession="ERP009004")
    second = eq.get("mgnify", resource="studies", accession="ERP009004")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("mgnify/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for mgnify"


def test_mgnify_requires_some_arg():
    """Calling without any selector must raise loudly."""
    with pytest.raises(ValueError, match="accession|samples_for|list_resource"):
        eq.get("mgnify")
