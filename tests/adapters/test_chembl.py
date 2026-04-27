"""Live ChEMBL adapter tests.

Policy: real data only. These tests hit www.ebi.ac.uk/chembl/api/data with
small stable queries. No mocks, no synthetic data, no try/except that
swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_chembl_molecule_aspirin():
    """CHEMBL25 is aspirin — a stable canonical sentinel."""
    df = eq.get("chembl", molecule_chembl_id="CHEMBL25")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected exactly one row for CHEMBL25, got {df.height}"

    cols = set(df.columns)
    assert "molecule_chembl_id" in cols, f"missing 'molecule_chembl_id' column: {df.columns}"
    assert "pref_name" in cols, f"missing 'pref_name' column: {df.columns}"

    chembl_id = df["molecule_chembl_id"][0]
    pref_name = df["pref_name"][0]
    assert chembl_id == "CHEMBL25", f"chembl_id should be CHEMBL25, got {chembl_id!r}"
    assert pref_name == "ASPIRIN", f"CHEMBL25 pref_name should be ASPIRIN, got {pref_name!r}"


def test_chembl_filtered_search():
    """A small filtered list query exercises the pagination + parsing path."""
    df = eq.get(
        "chembl",
        filters={"pref_name__iexact": "ASPIRIN"},
        limit=5,
    )

    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 5, f"expected 1..5 rows, got {df.height}"
    assert "molecule_chembl_id" in df.columns


def test_chembl_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("chembl", molecule_chembl_id="CHEMBL25")
    second = eq.get("chembl", molecule_chembl_id="CHEMBL25")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("chembl/queries/*.csv"))
    parquets = list(api._context().cache.root.rglob("chembl/queries/*.parquet"))
    assert csvs, "expected at least one cached CSV file for chembl"
    assert parquets, "expected at least one cached Parquet file for chembl"


def test_chembl_requires_some_arg():
    """Calling without any selector must raise loudly, not return empty data."""
    with pytest.raises(ValueError, match="molecule|target|activit|filter"):
        eq.get("chembl")
