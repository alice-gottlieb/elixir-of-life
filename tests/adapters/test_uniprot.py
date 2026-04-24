"""Live UniProt adapter tests.

Policy: real data only. These tests hit rest.uniprot.org with small stable
queries. If the endpoint is unreachable, the schema has drifted, or the parse
fails, the test must fail LOUDLY — no mocks, no synthetic data, no try/except
that swallows upstream errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_uniprot_single_accession_p00533():
    """P00533 is EGFR_HUMAN — a stable, canonical test accession."""
    df = eq.get("uniprot", accession="P00533")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, "expected at least one row for P00533"

    # Schema sanity — these column names come from fields=accession,id,protein_name,
    # gene_names,organism_name,organism_id,length,reviewed. UniProt humanises them
    # in the TSV header, so check for the leading "Entry" / "Organism" patterns.
    columns_joined = " ".join(df.columns).lower()
    assert "entry" in columns_joined, f"'Entry' column missing: {df.columns}"
    assert "organism" in columns_joined, f"'Organism' column missing: {df.columns}"

    # Sentinel: P00533's organism id must be 9606 (Homo sapiens) and its length 1210.
    org_id_col = next((c for c in df.columns if "organism" in c.lower() and "id" in c.lower()), None)
    length_col = next((c for c in df.columns if c.lower() == "length"), None)
    assert org_id_col, f"could not find organism ID column in {df.columns}"
    assert length_col, f"could not find length column in {df.columns}"

    org_id = df[org_id_col][0]
    length = df[length_col][0]
    assert int(org_id) == 9606, f"P00533 organism_id should be 9606, got {org_id!r}"
    assert int(length) == 1210, f"P00533 length should be 1210, got {length!r}"


def test_uniprot_search_with_limit():
    """Small Lucene search, limit=5 — verifies pagination + parsing path."""
    df = eq.get(
        "uniprot",
        query="gene:insulin AND organism_id:9606 AND reviewed:true",
        limit=5,
    )

    assert isinstance(df, pl.DataFrame)
    assert 1 <= df.height <= 5, f"expected 1..5 rows, got {df.height}"
    cols = " ".join(df.columns).lower()
    assert "entry" in cols


def test_uniprot_cache_roundtrip(tmp_path):
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("uniprot", accession="P00533")
    second = eq.get("uniprot", accession="P00533")
    assert first.equals(second)

    # And the cache directory should now hold a CSV + Parquet pair.
    csvs = list(api._context().cache.root.rglob("*.csv"))
    parquets = list(api._context().cache.root.rglob("*.parquet"))
    assert csvs, "expected at least one cached CSV file per project preference"
    assert parquets, "expected at least one cached Parquet file"


def test_uniprot_requires_accession_or_query():
    """Calling without either parameter must raise loudly, not return empty data."""
    with pytest.raises(ValueError, match="accession|query"):
        eq.get("uniprot")


def test_uniprot_aliases_register():
    """swissprot, trembl, uniprotkb should all resolve to the UniProt adapter."""
    assert "uniprot" in eq.list_databases()
    # Aliases should not leak into list_databases (canonical only) but should resolve.
    from elixir_query import registry

    assert registry.resolve("swissprot").meta.name == "uniprot"
    assert registry.resolve("uniprotkb").meta.name == "uniprot"
