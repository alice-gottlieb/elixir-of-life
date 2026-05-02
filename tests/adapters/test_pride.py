"""Live PRIDE Archive adapter tests.

Sentinels: PXD000001 — the first PRIDE project (Geiger et al. 2012 proteome map).
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_pride_single_project():
    """Single project lookup returns one row with expected accession."""
    df = eq.get("pride", accession="PXD000001")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 row for PXD000001, got {df.height}"

    assert "accession" in df.columns, f"missing accession; columns={df.columns}"
    assert df["accession"][0] == "PXD000001", f"accession mismatch: {df['accession'][0]!r}"


def test_pride_project_has_title():
    """Project record has a non-empty title field."""
    df = eq.get("pride", accession="PXD000001")

    assert "title" in df.columns, f"missing title; columns={df.columns}"
    assert df["title"][0], f"title is empty: {df['title'][0]!r}"


def test_pride_search():
    """Keyword search returns ≥1 result."""
    df = eq.get("pride", query="human proteome", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 result for search, got {df.height}"
    assert "accession" in df.columns or "projectAccession" in df.columns


def test_pride_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="accession|query"):
        eq.get("pride")


def test_pride_cache_roundtrip():
    """Second call returns identical cached frame."""
    first = eq.get("pride", accession="PXD000001")
    second = eq.get("pride", accession="PXD000001")
    assert first.equals(second)
