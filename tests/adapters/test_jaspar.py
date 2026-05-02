"""Live JASPAR adapter tests.

Sentinels: MA0139.1 = CTCF — one of the most studied TF binding profiles.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_jaspar_single_matrix():
    """Single matrix lookup for CTCF returns one row with expected fields."""
    df = eq.get("jaspar", matrix_id="MA0139.1")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected 1 row for MA0139.1, got {df.height}"

    assert "matrix_id" in df.columns, f"missing matrix_id; columns={df.columns}"
    assert "name" in df.columns, f"missing name; columns={df.columns}"

    assert df["matrix_id"][0] == "MA0139.1", f"matrix_id mismatch: {df['matrix_id'][0]!r}"
    assert df["name"][0] == "CTCF", f"name mismatch: {df['name'][0]!r}"


def test_jaspar_pfm_present():
    """CTCF profile includes position frequency matrix data."""
    df = eq.get("jaspar", matrix_id="MA0139.1")

    assert "pfm" in df.columns, f"missing pfm; columns={df.columns}"
    assert df["pfm"][0], "pfm field should not be empty"


def test_jaspar_browse_core_vertebrates():
    """Browsing CORE vertebrate profiles returns ≥1 result."""
    df = eq.get("jaspar", collection="CORE", tax_group="vertebrates", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 profile, got {df.height}"
    assert "matrix_id" in df.columns


def test_jaspar_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="matrix_id|collection|tax_group|name"):
        eq.get("jaspar")


def test_jaspar_cache_roundtrip():
    """Second call returns identical cached frame."""
    first = eq.get("jaspar", matrix_id="MA0139.1")
    second = eq.get("jaspar", matrix_id="MA0139.1")
    assert first.equals(second)
