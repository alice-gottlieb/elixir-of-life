"""Live ChEBI adapter tests (routed through OLS4).

Policy: real data only. These tests hit www.ebi.ac.uk/ols4 with small stable
queries. No mocks, no synthetic data.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_chebi_water():
    """CHEBI:15377 is water — a stable canonical sentinel."""
    df = eq.get("chebi", id="CHEBI:15377")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for CHEBI:15377, got {df.height}"

    cols = set(df.columns)
    assert "label" in cols, f"missing 'label' column: {df.columns}"
    assert "obo_id" in cols or "short_form" in cols, (
        f"missing identifier column ('obo_id' or 'short_form'): {df.columns}"
    )

    label = df["label"][0]
    assert label == "water", f"CHEBI:15377 label should be 'water', got {label!r}"
    if "obo_id" in cols:
        assert df["obo_id"][0] == "CHEBI:15377"


def test_chebi_id_normalisation_accepts_bare_digits():
    """'15377' (no prefix) should resolve to the same record as 'CHEBI:15377'."""
    df_a = eq.get("chebi", id="CHEBI:15377")
    df_b = eq.get("chebi", id="15377")
    assert df_a["label"][0] == df_b["label"][0] == "water"


def test_chebi_search_caffeine():
    """A free-text search for 'caffeine' should return at least one hit."""
    df = eq.get("chebi", search="caffeine", limit=5)
    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 5
    labels_lower = {str(s).lower() for s in df["label"].to_list()}
    assert any("caffeine" in s for s in labels_lower), labels_lower


def test_chebi_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("chebi", id="CHEBI:15377")
    second = eq.get("chebi", id="CHEBI:15377")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("chebi/queries/*.csv"))
    parquets = list(api._context().cache.root.rglob("chebi/queries/*.parquet"))
    assert csvs, "expected at least one cached CSV file for chebi"
    assert parquets, "expected at least one cached Parquet file for chebi"


def test_chebi_requires_some_arg():
    """Calling without any selector must raise loudly."""
    with pytest.raises(ValueError, match="id|search"):
        eq.get("chebi")


def test_chebi_bad_id_format_raises():
    """A malformed identifier should raise ValueError, not return empty data."""
    with pytest.raises(ValueError, match="ChEBI"):
        eq.get("chebi", id="not-an-id")
