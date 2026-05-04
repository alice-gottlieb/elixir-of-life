"""Live Reactome adapter tests.

Policy: real data only. These tests hit reactome.org/ContentService with
small stable queries. No mocks, no synthetic data.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq

pytestmark = pytest.mark.live


def test_reactome_query_cell_cycle_checkpoints():
    """R-HSA-69620 is the 'Cell Cycle Checkpoints' pathway in human."""
    df = eq.get("reactome", id="R-HSA-69620")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for R-HSA-69620, got {df.height}"

    cols = set(df.columns)
    assert "stId" in cols, f"missing 'stId' column: {df.columns}"
    assert "displayName" in cols, f"missing 'displayName' column: {df.columns}"
    assert "speciesName" in cols, f"missing 'speciesName' column: {df.columns}"

    assert df["stId"][0] == "R-HSA-69620"
    assert df["displayName"][0] == "Cell Cycle Checkpoints", (
        f"R-HSA-69620 displayName should be 'Cell Cycle Checkpoints', got {df['displayName'][0]!r}"
    )
    assert df["speciesName"][0] == "Homo sapiens"


def test_reactome_top_pathways_for_human():
    """Top-level pathways for human (taxon 9606) — should be a non-empty list."""
    df = eq.get("reactome", top_for=9606)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 5, f"expected at least 5 top-level human pathways, got {df.height}"
    assert "stId" in df.columns
    # Every entry should be human-prefixed.
    assert all(s.startswith("R-HSA-") for s in df["stId"].to_list()), df["stId"].to_list()


def test_reactome_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("reactome", id="R-HSA-69620")
    second = eq.get("reactome", id="R-HSA-69620")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("reactome/queries/*.csv"))
    parquets = list(api._context().cache.root.rglob("reactome/queries/*.parquet"))
    assert csvs, "expected at least one cached CSV file for reactome"
    assert parquets, "expected at least one cached Parquet file for reactome"


def test_reactome_requires_some_arg():
    """Calling without any selector must raise loudly, not return empty data."""
    with pytest.raises(ValueError, match="id|contained|top|participants"):
        eq.get("reactome")
