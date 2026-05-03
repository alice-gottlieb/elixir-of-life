"""Live ENA Portal API adapter tests.

Policy: real data only. Tests hit www.ebi.ac.uk/ena/portal/api.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_ena_read_run_by_study():
    """Study ERP000001 is a well-known public ENA study (1000 Genomes pilot)."""
    df = eq.get("ena", query="study_accession=ERP000001", result="read_run", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected >=1 row for ERP000001, got {df.height}"

    assert "accession" in df.columns, f"missing 'accession' column: {df.columns}"
    assert "study_accession" in df.columns

    study_accessions = set(df["study_accession"].to_list())
    assert "ERP000001" in study_accessions, (
        f"study_accession ERP000001 not in result: {study_accessions}"
    )


def test_ena_sample_query():
    """A sample query returns accession + scientific_name."""
    df = eq.get(
        "ena",
        query="study_accession=ERP000001",
        result="sample",
        limit=3,
        fields=["accession", "scientific_name", "tax_id"],
    )

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1
    assert "accession" in df.columns
    assert "scientific_name" in df.columns


def test_ena_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("ena", query="study_accession=ERP000001", result="read_run", limit=3)
    second = eq.get("ena", query="study_accession=ERP000001", result="read_run", limit=3)
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("ena/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for ena"


def test_ena_requires_query():
    """Calling without query must raise loudly."""
    with pytest.raises((ValueError, TypeError)):
        eq.get("ena")
