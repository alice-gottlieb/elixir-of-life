"""Live Ensembl Genomes adapter tests.

Policy: real data only. These tests hit rest.ensembl.org for plant / fungi /
protist queries. No mocks, no synthetic data, no try/except that swallows.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_ensembl_genomes_lookup_arabidopsis():
    """AT3G52260 (PUB48) is a stable Arabidopsis thaliana protein-coding gene."""
    df = eq.get("ensembl_genomes", id="AT3G52260")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for AT3G52260, got {df.height}"

    cols = set(df.columns)
    assert "species" in cols, f"missing 'species' column: {df.columns}"
    assert "biotype" in cols, f"missing 'biotype' column: {df.columns}"

    species = df["species"][0]
    biotype = df["biotype"][0]
    assert species == "arabidopsis_thaliana", (
        f"AT3G52260 species should be arabidopsis_thaliana, got {species!r}"
    )
    assert biotype == "protein_coding", (
        f"AT3G52260 biotype should be protein_coding, got {biotype!r}"
    )


def test_ensembl_genomes_lookup_yeast():
    """YJR104C is a stable Saccharomyces cerevisiae gene (SOD1)."""
    df = eq.get("ensembl_genomes", id="YJR104C")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert "species" in df.columns
    assert df["species"][0] == "saccharomyces_cerevisiae", (
        f"YJR104C species should be saccharomyces_cerevisiae, got {df['species'][0]!r}"
    )


def test_ensembl_genomes_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("ensembl_genomes", id="AT3G52260")
    second = eq.get("ensembl_genomes", id="AT3G52260")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("ensembl_genomes/queries/*.csv"))
    parquets = list(api._context().cache.root.rglob("ensembl_genomes/queries/*.parquet"))
    assert csvs, "expected at least one cached CSV file for ensembl_genomes"
    assert parquets, "expected at least one cached Parquet file for ensembl_genomes"


def test_ensembl_genomes_requires_some_arg():
    """Calling without any selector must raise loudly, not return empty data."""
    with pytest.raises(ValueError, match="id|symbol|division"):
        eq.get("ensembl_genomes")
