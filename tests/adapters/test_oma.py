"""Live OMA adapter tests.

Policy: real data only. Tests hit omabrowser.org/api.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq

pytestmark = pytest.mark.live


def test_oma_protein_yeast():
    """YEAST00012 is a stable OMA entry ID for a S. cerevisiae protein."""
    df = eq.get("oma", protein="YEAST00012")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for YEAST00012, got {df.height}"

    cols = set(df.columns)
    assert "omaid" in cols, f"missing 'omaid' column: {df.columns}"

    assert df["omaid"][0] == "YEAST00012", (
        f"omaid should be 'YEAST00012', got {df['omaid'][0]!r}"
    )


def test_oma_orthologs_for_protein():
    """A yeast protein should have at least a few orthologs."""
    df = eq.get("oma", orthologs_for="YEAST00012", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected >=1 ortholog for YEAST00012, got {df.height}"


def test_oma_genome_lookup():
    """Genome 559292 is S. cerevisiae S288C — a stable reference genome."""
    df = eq.get("oma", genome=559292)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    # Genome record should mention species name somewhere.
    species_field = next(
        (c for c in df.columns if "species" in c.lower() or "scientific" in c.lower()), None
    )
    assert species_field is not None, f"no species column found: {df.columns}"
    species_text = str(df[species_field][0]).lower()
    assert "saccharomyces" in species_text or "cerevisiae" in species_text or "yeast" in species_text, (
        f"genome 559292 should be S. cerevisiae, got species={species_text!r}"
    )


def test_oma_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("oma", protein="YEAST00012")
    second = eq.get("oma", protein="YEAST00012")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("oma/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for oma"


def test_oma_requires_some_arg():
    """Calling without any selector must raise loudly."""
    with pytest.raises(ValueError, match="protein|orthologs|hog|genome"):
        eq.get("oma")
