"""Live Europe PMC adapter tests.

All tests are marked live; they hit the real API.
Sentinels: PMID 30106370 = Ferguson et al. 2019 "Europe PMC: a full-text
literature database for the life sciences" (Nucleic Acids Res. 47:D1155-D1162).
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_europe_pmc_by_pmid():
    """Single PubMed article lookup returns exactly one row with known fields."""
    df = eq.get("europe_pmc", pmid="30106370")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected 1 row for PMID 30106370, got {df.height}"

    cols = set(df.columns)
    for col in ("pmid", "title", "journalTitle", "pubYear"):
        assert col in cols, f"missing column {col!r}; columns={df.columns}"

    assert df["pmid"][0] == "30106370", f"pmid mismatch: {df['pmid'][0]!r}"
    assert "Europe PMC" in str(df["title"][0]), f"unexpected title: {df['title'][0]!r}"
    assert df["pubYear"][0] in ("2019", 2019), f"unexpected pubYear: {df['pubYear'][0]!r}"


def test_europe_pmc_doi_present():
    """Core result type includes doi and citedByCount fields."""
    df = eq.get("europe_pmc", pmid="30106370", result_type="core")

    assert "doi" in df.columns, f"missing doi column; columns={df.columns}"
    assert df["doi"][0] == "10.1093/nar/gky1127", f"unexpected doi: {df['doi'][0]!r}"


def test_europe_pmc_query_search():
    """Keyword search returns multiple rows with expected columns."""
    df = eq.get("europe_pmc", query="Europe PMC AND SRC:MED", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 5, f"expected 1..5 rows, got {df.height}"
    assert "title" in df.columns
    assert "pmid" in df.columns


def test_europe_pmc_requires_arg():
    """Calling without any selector raises ValueError."""
    with pytest.raises(ValueError, match="query|pmid|pmcid"):
        eq.get("europe_pmc")


def test_europe_pmc_cache_roundtrip():
    """Second call returns identical frame (cache hit)."""
    first = eq.get("europe_pmc", pmid="30106370")
    second = eq.get("europe_pmc", pmid="30106370")
    assert first.equals(second)
