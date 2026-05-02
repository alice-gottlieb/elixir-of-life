"""Live GWAS Catalog adapter tests.

Sentinels:
  - rs7903146: TCF7L2 T2D SNP — the most replicated GWAS association ever.
  - GCST000001: First GWAS Catalog study (Klein et al. 2005, AMD/CFH).
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_gwas_snp_lookup():
    """SNP lookup for rs7903146 returns one row with expected rsId."""
    df = eq.get("gwas_catalog", rsid="rs7903146")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 row for rs7903146, got {df.height}"

    assert "rsId" in df.columns, f"missing rsId column; columns={df.columns}"
    assert df["rsId"][0] == "rs7903146", f"rsId mismatch: {df['rsId'][0]!r}"


def test_gwas_snp_functional_class():
    """rs7903146 should have genomic/functional class annotations."""
    df = eq.get("gwas_catalog", rsid="rs7903146")
    assert "functionalClass" in df.columns or "genomicContexts" in df.columns, (
        f"missing functional annotation columns; columns={df.columns}"
    )


def test_gwas_study_lookup():
    """Study lookup returns one row with accessionId."""
    df = eq.get("gwas_catalog", study_accession="GCST000001")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 row for GCST000001"
    assert "accessionId" in df.columns, f"missing accessionId; columns={df.columns}"
    assert df["accessionId"][0] == "GCST000001"


def test_gwas_snp_associations():
    """Associations for rs7903146 returns ≥1 row with pvalue fields."""
    df = eq.get("gwas_catalog", snp_associations="rs7903146", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1
    assert "pvalueMantissa" in df.columns or "pvalue" in df.columns, (
        f"missing p-value column; columns={df.columns}"
    )


def test_gwas_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="rsid|study|associations"):
        eq.get("gwas_catalog")
