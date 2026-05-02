"""Live OMA adapter tests.

Sentinels: P00533 = human EGFR — a canonical UniProt accession accepted by OMA.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_oma_protein_by_uniprot():
    """Protein lookup by UniProt accession returns expected fields."""
    df = eq.get("oma", protein="P00533")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 row for P00533, got {df.height}"

    assert "omaid" in df.columns or "canonicalid" in df.columns, (
        f"missing omaid/canonicalid; columns={df.columns}"
    )


def test_oma_protein_human_origin():
    """EGFR (P00533) should belong to a human (HUMAN) entry."""
    df = eq.get("oma", protein="P00533")
    omaid = str(df["omaid"][0]) if "omaid" in df.columns else ""
    canonicalid = str(df["canonicalid"][0]) if "canonicalid" in df.columns else ""
    assert "HUMAN" in omaid or "P00533" in canonicalid or "P00533" in omaid, (
        f"unexpected omaid={omaid!r}, canonicalid={canonicalid!r}"
    )


def test_oma_orthologs():
    """Pairwise orthologs for P00533 returns ≥1 row."""
    df = eq.get("oma", orthologs="P00533", limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 ortholog for P00533"


def test_oma_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="protein|orthologs|group_id"):
        eq.get("oma")


def test_oma_cache_roundtrip():
    """Second call returns identical cached frame."""
    first = eq.get("oma", protein="P00533")
    second = eq.get("oma", protein="P00533")
    assert first.equals(second)
