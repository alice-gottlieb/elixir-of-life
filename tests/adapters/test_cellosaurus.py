"""Live Cellosaurus adapter tests.

Sentinels: CVCL_0004 = HeLa — the most well-known cell line in the world.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_cellosaurus_single_by_accession():
    """Fetch HeLa by CVCL_0004 returns a non-empty DataFrame."""
    df = eq.get("cellosaurus", accession="CVCL_0004")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 row for CVCL_0004, got {df.height}"


def test_cellosaurus_hela_accession_present():
    """HeLa record contains CVCL_0004 accession somewhere in the row."""
    df = eq.get("cellosaurus", accession="CVCL_0004")
    row_str = " ".join(str(v) for v in df.row(0))
    assert "CVCL_0004" in row_str or "HeLa" in row_str, (
        f"expected CVCL_0004 or HeLa in row: {row_str[:200]!r}"
    )


def test_cellosaurus_search():
    """Search for HeLa returns ≥1 result."""
    df = eq.get("cellosaurus", query="HeLa", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 result for 'HeLa'"


def test_cellosaurus_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="accession|query"):
        eq.get("cellosaurus")


def test_cellosaurus_cache_roundtrip():
    """Second call returns identical cached frame."""
    first = eq.get("cellosaurus", accession="CVCL_0004")
    second = eq.get("cellosaurus", accession="CVCL_0004")
    assert first.equals(second)
