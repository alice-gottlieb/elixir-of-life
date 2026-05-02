"""Live HGNC adapter tests.

Sentinels: EGFR — a well-known, stable HGNC gene symbol (HGNC:3236).
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_hgnc_fetch_by_symbol():
    """Fetch EGFR by symbol returns one row with known field values."""
    df = eq.get("hgnc", symbol="EGFR")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 row for EGFR, got {df.height}"

    cols = set(df.columns)
    for col in ("hgnc_id", "symbol", "name"):
        assert col in cols, f"missing column {col!r}; columns={df.columns}"

    assert df["symbol"][0] == "EGFR", f"symbol mismatch: {df['symbol'][0]!r}"
    assert df["hgnc_id"][0] == "HGNC:3236", f"hgnc_id mismatch: {df['hgnc_id'][0]!r}"


def test_hgnc_name_field():
    """Name field contains 'epidermal growth factor receptor'."""
    df = eq.get("hgnc", symbol="EGFR")

    name = str(df["name"][0]).lower()
    assert "epidermal" in name, f"unexpected name: {df['name'][0]!r}"


def test_hgnc_fetch_by_id():
    """Fetch by HGNC:3236 returns same record as by symbol."""
    df = eq.get("hgnc", hgnc_id="HGNC:3236")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1
    assert df["symbol"][0] == "EGFR"


def test_hgnc_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="symbol|hgnc_id|search"):
        eq.get("hgnc")


def test_hgnc_cache_roundtrip():
    """Second call is served from cache and returns identical frame."""
    first = eq.get("hgnc", symbol="EGFR")
    second = eq.get("hgnc", symbol="EGFR")
    assert first.equals(second)
