"""Live Rhea adapter tests.

Policy: real data only. These tests hit www.rhea-db.org with small stable
queries. If the endpoint is unreachable, the schema has drifted, or the parse
fails, the test must fail LOUDLY — no mocks, no synthetic data, no try/except
that swallows upstream errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq

pytestmark = pytest.mark.live


def test_rhea_single_id_10044():
    """RHEA:10044 is L-lactate dehydrogenase — stable canonical sentinel."""
    df = eq.get("rhea", rhea_id="RHEA:10044")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, "expected at least one row for RHEA:10044"

    # Find the equation column (humanised header from Rhea's TSV).
    eq_col = next((c for c in df.columns if "equation" in c.lower()), None)
    assert eq_col, f"could not find equation column in {df.columns}"

    equation = str(df[eq_col][0]).lower()
    assert "lactate" in equation, f"RHEA:10044 equation should mention lactate: {equation!r}"
    assert "pyruvate" in equation, f"RHEA:10044 equation should mention pyruvate: {equation!r}"

    # Reaction id column should round-trip 10044.
    id_col = next((c for c in df.columns if "reaction" in c.lower() and "id" in c.lower()), None)
    if id_col is None:
        id_col = next((c for c in df.columns if c.lower() in {"rhea-id", "rhea_id", "id"}), None)
    assert id_col, f"could not find reaction id column in {df.columns}"
    assert "10044" in str(df[id_col][0]), f"id round-trip failed: {df[id_col][0]!r}"


def test_rhea_search_with_limit():
    """Small query, limit=5 — verifies the search/parse path."""
    df = eq.get("rhea", query="glucose", columns=["rhea-id", "equation"], limit=5)

    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 5, f"expected 1..5 rows, got {df.height}"
    cols = " ".join(df.columns).lower()
    assert "equation" in cols


def test_rhea_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("rhea", rhea_id="RHEA:10044")
    second = eq.get("rhea", rhea_id="RHEA:10044")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("*.csv"))
    parquets = list(api._context().cache.root.rglob("*.parquet"))
    assert csvs, "expected at least one cached CSV file"
    assert parquets, "expected at least one cached Parquet file"


def test_rhea_requires_id_or_query():
    """Calling without either parameter must raise loudly."""
    with pytest.raises(ValueError, match="rhea_id|query"):
        eq.get("rhea")


def test_rhea_alias_resolves():
    """The 'rhea-db' alias resolves to the Rhea adapter."""
    from elixir_query import registry

    assert "rhea" in eq.list_databases()
    assert registry.resolve("rhea-db").meta.name == "rhea"
