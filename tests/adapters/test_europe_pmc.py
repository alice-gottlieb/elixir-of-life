"""Live Europe PMC adapter tests.

Policy: real data only. Tests hit europepmc.org REST API.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_europe_pmc_pmid_article():
    """PMID 28209558 is a well-known GWAS paper (Yengo et al. height 2018)."""
    df = eq.get("europe_pmc", pmid="28209558")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for PMID 28209558, got {df.height}"

    cols = set(df.columns)
    assert "title" in cols, f"missing 'title' column: {df.columns}"
    assert "pmid" in cols, f"missing 'pmid' column: {df.columns}"

    pmid = str(df["pmid"][0])
    title = str(df["title"][0]).lower()
    assert pmid == "28209558", f"pmid should be '28209558', got {pmid!r}"
    assert "height" in title or "stature" in title or "genome" in title, (
        f"PMID 28209558 title should relate to height GWAS, got {title!r}"
    )


def test_europe_pmc_search_returns_results():
    """A simple keyword search should return at least one article."""
    df = eq.get(
        "europe_pmc",
        query="TITLE:insulin AND OPEN_ACCESS:Y",
        limit=5,
        page_size=5,
    )

    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 5, f"expected 1..5 rows, got {df.height}"
    assert "title" in df.columns


def test_europe_pmc_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("europe_pmc", pmid="28209558")
    second = eq.get("europe_pmc", pmid="28209558")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("europe_pmc/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for europe_pmc"


def test_europe_pmc_requires_some_arg():
    """Calling without any selector must raise loudly."""
    with pytest.raises(ValueError, match="pmid|pmcid|query"):
        eq.get("europe_pmc")
