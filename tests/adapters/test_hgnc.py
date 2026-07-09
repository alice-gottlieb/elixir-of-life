"""Live HGNC adapter tests.

Policy: real data only. Tests hit rest.genenames.org.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq

pytestmark = pytest.mark.live


def test_hgnc_fetch_brca2_by_symbol():
    """BRCA2 is a well-known HGNC entry with stable identifiers."""
    df = eq.get("hgnc", symbol="BRCA2")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for BRCA2, got {df.height}"

    cols = set(df.columns)
    assert "hgnc_id" in cols, f"missing 'hgnc_id' column: {df.columns}"
    assert "symbol" in cols, f"missing 'symbol' column: {df.columns}"
    assert "locus_type" in cols, f"missing 'locus_type' column: {df.columns}"

    assert df["hgnc_id"][0] == "HGNC:1101", (
        f"BRCA2 hgnc_id should be 'HGNC:1101', got {df['hgnc_id'][0]!r}"
    )
    assert df["symbol"][0] == "BRCA2"
    assert df["locus_type"][0] == "gene with protein product", (
        f"BRCA2 locus_type should be 'gene with protein product', got {df['locus_type'][0]!r}"
    )


def test_hgnc_fetch_by_ensembl_id():
    """Looking up BRCA2 by its Ensembl gene ID should return the same record."""
    df = eq.get("hgnc", ensembl_gene_id="ENSG00000139618")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1
    assert df["symbol"][0] == "BRCA2"


def test_hgnc_search():
    """Free-text search for 'BRCA' should return multiple entries."""
    df = eq.get("hgnc", search="BRCA")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 2, f"expected >=2 results for 'BRCA', got {df.height}"
    symbols = set(df["symbol"].to_list())
    assert "BRCA1" in symbols or "BRCA2" in symbols, symbols


def test_hgnc_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("hgnc", symbol="BRCA2")
    second = eq.get("hgnc", symbol="BRCA2")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("hgnc/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for hgnc"


def test_hgnc_requires_some_arg():
    """Calling without any lookup argument must raise loudly."""
    with pytest.raises(ValueError, match="symbol|hgnc_id|search"):
        eq.get("hgnc")
