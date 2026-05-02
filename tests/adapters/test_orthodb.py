"""Live OrthoDB adapter tests.

Sentinels: TP53 — a universal tumour suppressor with orthologs across nearly all eukaryotes.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_orthodb_search_tp53():
    """Search for TP53 returns ≥1 orthologous group."""
    df = eq.get("orthodb", query="TP53")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 OG for TP53, got {df.height}"


def test_orthodb_search_has_id_column():
    """Search results have an identifier column."""
    df = eq.get("orthodb", query="TP53", take=5)

    assert "id" in df.columns or "og_id" in df.columns, (
        f"expected id column in {df.columns}"
    )


def test_orthodb_search_pagination():
    """skip/take pagination returns different slices."""
    df1 = eq.get("orthodb", query="kinase", take=5, skip=0)
    df2 = eq.get("orthodb", query="kinase", take=5, skip=5)

    assert isinstance(df1, pl.DataFrame)
    assert isinstance(df2, pl.DataFrame)
    # They should not be identical (different pages)
    if df1.height > 0 and df2.height > 0:
        assert not df1.equals(df2), "skip=0 and skip=5 should return different rows"


def test_orthodb_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="query|group_id|members_of"):
        eq.get("orthodb")


def test_orthodb_cache_roundtrip():
    """Second identical call is served from cache."""
    first = eq.get("orthodb", query="TP53")
    second = eq.get("orthodb", query="TP53")
    assert first.equals(second)
