"""Live InterPro adapter tests.

Sentinels: IPR000001 = Kringle domain — one of the oldest stable InterPro entries.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_interpro_single_entry():
    """Single entry lookup returns one row with expected accession and type."""
    df = eq.get("interpro", accession="IPR000001")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected 1 row for IPR000001, got {df.height}"

    assert "accession" in df.columns, f"missing 'accession' column: {df.columns}"
    assert "type" in df.columns, f"missing 'type' column: {df.columns}"

    assert df["accession"][0] == "IPR000001", f"accession mismatch: {df['accession'][0]!r}"
    assert df["type"][0] == "Domain", f"type should be Domain, got {df['type'][0]!r}"


def test_interpro_name_field():
    """Entry name JSON contains 'Kringle' (the domain name)."""
    df = eq.get("interpro", accession="IPR000001")

    assert "name" in df.columns, f"missing 'name' column: {df.columns}"
    assert "Kringle" in str(df["name"][0]), f"expected Kringle in name: {df['name'][0]!r}"


def test_interpro_protein_entries():
    """Fetching entries for human EGFR (P00533) returns ≥1 InterPro entry."""
    df = eq.get("interpro", protein="P00533", limit=10)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 entry for P00533, got {df.height}"
    assert "accession" in df.columns


def test_interpro_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="accession|protein|list_all"):
        eq.get("interpro")


def test_interpro_cache_roundtrip():
    """Second identical call is served from cache."""
    first = eq.get("interpro", accession="IPR000001")
    second = eq.get("interpro", accession="IPR000001")
    assert first.equals(second)
