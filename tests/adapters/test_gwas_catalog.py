"""Live GWAS Catalog adapter tests.

Policy: real data only. Tests hit www.ebi.ac.uk/gwas/rest/api.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq

pytestmark = pytest.mark.live


def test_gwas_catalog_single_study():
    """GCST000001 is the first GWAS Catalog study — a stable canonical sentinel."""
    df = eq.get("gwas_catalog", study="GCST000001")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for GCST000001, got {df.height}"

    cols = set(df.columns)
    assert "accessionId" in cols, f"missing 'accessionId' column: {df.columns}"
    assert df["accessionId"][0] == "GCST000001", (
        f"accessionId should be 'GCST000001', got {df['accessionId'][0]!r}"
    )
    # The trait should relate to cancer (breast cancer study).
    diseaseTrait = str(df.get_column("diseaseTrait").to_list()[0]).lower()
    assert "cancer" in diseaseTrait or "breast" in diseaseTrait or "gcst" in diseaseTrait, (
        f"GCST000001 diseaseTrait should mention cancer/breast: {diseaseTrait!r}"
    )


def test_gwas_catalog_snp_lookup():
    """rs2981582 is a well-known FGFR2 breast-cancer GWAS hit."""
    df = eq.get("gwas_catalog", rsid="rs2981582")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    # rsId field should reflect the query.
    rs_col = next(
        (c for c in df.columns if "rsid" in c.lower() or c.lower() == "rsid"), None
    )
    assert rs_col is not None, f"no rsId column found: {df.columns}"
    assert str(df[rs_col][0]).lower() in ("rs2981582", "rs2981582")


def test_gwas_catalog_study_associations():
    """Study GCST000001 should have at least one association."""
    df = eq.get("gwas_catalog", associations_for="GCST000001", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected >=1 association for GCST000001, got {df.height}"


def test_gwas_catalog_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("gwas_catalog", study="GCST000001")
    second = eq.get("gwas_catalog", study="GCST000001")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("gwas_catalog/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for gwas_catalog"


def test_gwas_catalog_requires_some_arg():
    """Calling without any selector must raise loudly."""
    with pytest.raises(ValueError, match="study|rsid|efo|list"):
        eq.get("gwas_catalog")
