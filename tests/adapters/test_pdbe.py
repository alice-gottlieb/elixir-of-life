"""Live PDBe adapter tests.

Sentinels: 1CBS — crystal structure of cellular retinoic-acid-binding protein type II,
a classic, long-stable PDB entry deposited 1993.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_pdbe_summary():
    """Entry summary for 1CBS contains known fields and values."""
    df = eq.get("pdbe", pdb_id="1cbs")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 row for 1CBS, got {df.height}"

    cols = set(df.columns)
    assert "pdb_id" in cols, f"missing pdb_id; columns={df.columns}"
    assert "title" in cols, f"missing title; columns={df.columns}"

    assert df["pdb_id"][0] == "1cbs", f"pdb_id mismatch: {df['pdb_id'][0]!r}"


def test_pdbe_experimental_method():
    """1CBS was solved by X-ray diffraction."""
    df = eq.get("pdbe", pdb_id="1cbs")
    assert "experimental_method" in df.columns, f"missing experimental_method; columns={df.columns}"
    method_str = str(df["experimental_method"][0])
    assert "X-ray" in method_str or "diffraction" in method_str.lower(), (
        f"unexpected experimental_method: {method_str!r}"
    )


def test_pdbe_molecules_section():
    """Molecules section returns entity information."""
    df = eq.get("pdbe", pdb_id="1cbs", section="molecules")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 molecule for 1CBS"


def test_pdbe_requires_pdb_id():
    """Calling without pdb_id raises ValueError."""
    with pytest.raises(ValueError, match="pdb_id"):
        eq.get("pdbe")


def test_pdbe_cache_roundtrip():
    """Second call returns identical cached frame."""
    first = eq.get("pdbe", pdb_id="1cbs")
    second = eq.get("pdbe", pdb_id="1cbs")
    assert first.equals(second)
