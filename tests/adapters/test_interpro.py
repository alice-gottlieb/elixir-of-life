"""Live InterPro adapter tests.

Policy: real data only. Tests hit www.ebi.ac.uk/interpro/api.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_interpro_single_entry_wd40():
    """IPR001680 is the WD40 repeat — a stable, well-known InterPro entry."""
    df = eq.get("interpro", accession="IPR001680")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1, f"expected one row for IPR001680, got {df.height}"

    cols = set(df.columns)
    assert "accession" in cols, f"missing 'accession' column: {df.columns}"
    assert "type" in cols, f"missing 'type' column: {df.columns}"

    accession = df["accession"][0]
    entry_type = df["type"][0]
    assert accession == "IPR001680", f"accession should be IPR001680, got {accession!r}"
    assert str(entry_type).lower() in ("repeat", "homologous_superfamily", "domain"), (
        f"IPR001680 type should be a structural type, got {entry_type!r}"
    )


def test_interpro_pfam_entry_lookup():
    """PF00001 (7 transmembrane receptor) is a canonical Pfam entry."""
    df = eq.get("interpro", accession="PF00001")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert "accession" in df.columns
    assert df["accession"][0] == "PF00001"


def test_interpro_protein_entries():
    """P00533 (EGFR) should have multiple InterPro entries annotating it."""
    df = eq.get("interpro", protein_accession="P00533", limit=10)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected >=1 InterPro entry for P00533 (EGFR), got {df.height}"
    assert "accession" in df.columns


def test_interpro_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("interpro", accession="IPR001680")
    second = eq.get("interpro", accession="IPR001680")
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("interpro/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for interpro"


def test_interpro_requires_some_arg():
    """Calling without any selector must raise loudly."""
    with pytest.raises(ValueError, match="accession|protein"):
        eq.get("interpro")
