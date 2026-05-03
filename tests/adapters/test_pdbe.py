"""Live PDBe adapter tests.

Policy: real data only. Tests hit www.ebi.ac.uk/pdbe/api.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_pdbe_entry_summary_1cbs():
    """1CBS is cellular retinoic-acid binding protein II — a stable test accession."""
    df = eq.get("pdbe", pdb_id="1cbs")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected >=1 row for 1cbs, got {df.height}"

    cols = set(df.columns)
    assert "pdb_id" in cols, f"missing 'pdb_id' column: {df.columns}"
    assert "title" in cols, f"missing 'title' column: {df.columns}"

    assert df["pdb_id"][0].lower() == "1cbs"
    title = str(df["title"][0]).upper()
    assert "RETINOIC" in title or "BINDING" in title, (
        f"1CBS title should mention RETINOIC/BINDING, got {title!r}"
    )


def test_pdbe_experiment_kind():
    """kind='experiment' returns experimental details including method."""
    df = eq.get("pdbe", pdb_id="1cbs", kind="experiment")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1
    # Experimental method should be present.
    method_col = next(
        (c for c in df.columns if "method" in c.lower() or "technique" in c.lower()), None
    )
    assert method_col is not None, f"no method/technique column found in {df.columns}"


def test_pdbe_case_insensitive():
    """PDB IDs are case-insensitive — '1CBS' and '1cbs' must return the same data."""
    lower = eq.get("pdbe", pdb_id="1cbs")
    upper = eq.get("pdbe", pdb_id="1CBS")
    assert lower["pdb_id"][0].lower() == upper["pdb_id"][0].lower()


def test_pdbe_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("pdbe", pdb_id="1cbs")
    second = eq.get("pdbe", pdb_id="1cbs")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("pdbe/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for pdbe"


def test_pdbe_requires_pdb_id():
    """Calling without pdb_id must raise loudly."""
    with pytest.raises(ValueError, match="pdb_id"):
        eq.get("pdbe")


def test_pdbe_invalid_kind_raises():
    """Passing an unsupported kind must raise ValueError, not make a bad request."""
    with pytest.raises(ValueError, match="kind"):
        eq.get("pdbe", pdb_id="1cbs", kind="bogus_kind")
