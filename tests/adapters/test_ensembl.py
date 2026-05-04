"""Live Ensembl adapter tests.

Policy: real data only. These tests hit rest.ensembl.org with small stable
queries. No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq

pytestmark = pytest.mark.live


def test_ensembl_lookup_brca2():
    """ENSG00000139618 is BRCA2 (human) — a stable canonical sentinel."""
    df = eq.get("ensembl", id="ENSG00000139618")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected exactly one row for ENSG00000139618, got {df.height}"

    cols = set(df.columns)
    assert "species" in cols, f"missing 'species' column: {df.columns}"
    assert "biotype" in cols, f"missing 'biotype' column: {df.columns}"

    species = df["species"][0]
    biotype = df["biotype"][0]
    assert species == "homo_sapiens", f"BRCA2 species should be homo_sapiens, got {species!r}"
    assert biotype == "protein_coding", f"BRCA2 biotype should be protein_coding, got {biotype!r}"


def test_ensembl_overlap_region_returns_features():
    """Small region overlap returns a non-empty list of gene features."""
    df = eq.get(
        "ensembl",
        species="homo_sapiens",
        region="13:32315474-32400266",
        feature="gene",
    )

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, "expected at least one gene overlapping the BRCA2 locus"
    assert "id" in df.columns or "gene_id" in df.columns, df.columns
    # BRCA2 should be among the overlapping genes.
    id_col = "id" if "id" in df.columns else "gene_id"
    ids = set(df[id_col].to_list())
    assert "ENSG00000139618" in ids, f"BRCA2 not in overlap result: {ids}"


def test_ensembl_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("ensembl", id="ENSG00000139618")
    second = eq.get("ensembl", id="ENSG00000139618")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("ensembl/queries/*.csv"))
    parquets = list(api._context().cache.root.rglob("ensembl/queries/*.parquet"))
    assert csvs, "expected at least one cached CSV file for ensembl"
    assert parquets, "expected at least one cached Parquet file for ensembl"


def test_ensembl_requires_some_arg():
    """Calling without any selector must raise loudly."""
    with pytest.raises(ValueError, match="id|symbol|region"):
        eq.get("ensembl")
