"""Live OrthoDB adapter tests.

Policy: real data only. Tests hit data.orthodb.org/v12.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_orthodb_group_details():
    """4977at9604 is a stable Hominidae-level orthologous group (TP53 family)."""
    df = eq.get("orthodb", og_id="4977at9604")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected >=1 row for OG 4977at9604, got {df.height}"

    # Should report the level taxid (9604 = Hominidae) somewhere.
    level_col = next(
        (c for c in df.columns if "level" in c.lower() or "taxid" in c.lower()),
        None,
    )
    assert level_col is not None, f"no level/taxid column in {df.columns}"


def test_orthodb_search():
    """A simple text search returns at least one OG."""
    df = eq.get("orthodb", search="p53", level=33208, take=5)

    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 5
    # Each row should have a 'value' (OG ID string) or a flat dict.
    assert df.width >= 1


def test_orthodb_orthologs_in_group():
    """Orthologs in OG 4977at9604 should return at least one gene."""
    df = eq.get("orthodb", orthologs_in="4977at9604")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1


def test_orthodb_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("orthodb", og_id="4977at9604")
    second = eq.get("orthodb", og_id="4977at9604")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("orthodb/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for orthodb"


def test_orthodb_requires_some_arg():
    """Calling without any selector must raise loudly."""
    with pytest.raises(ValueError, match="og_id|search|gene|orthologs"):
        eq.get("orthodb")
