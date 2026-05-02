"""Live MGnify adapter tests.

Sentinels: MGYS00001598 — a stable public study in the MGnify database.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_mgnify_single_study():
    """Single study lookup returns non-empty DataFrame with id field."""
    df = eq.get("mgnify", study_accession="MGYS00001598")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 row for MGYS00001598, got {df.height}"
    assert "id" in df.columns, f"missing id; columns={df.columns}"
    assert df["id"][0] == "MGYS00001598", f"id mismatch: {df['id'][0]!r}"


def test_mgnify_study_has_attributes():
    """Study record contains typical metagenomics metadata fields."""
    df = eq.get("mgnify", study_accession="MGYS00001598")

    # JSON:API attributes are unpacked into columns
    expected = {"accession", "study-name", "bioproject"}
    present = set(df.columns)
    assert expected & present, (
        f"expected at least one of {expected!r} but got columns: {df.columns}"
    )


def test_mgnify_list_studies():
    """Listing studies returns ≥1 row."""
    df = eq.get("mgnify", list_studies=True, limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 study in list"


def test_mgnify_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="study_accession|sample|runs_for|list_studies"):
        eq.get("mgnify")


def test_mgnify_cache_roundtrip():
    """Second call returns identical cached frame."""
    first = eq.get("mgnify", study_accession="MGYS00001598")
    second = eq.get("mgnify", study_accession="MGYS00001598")
    assert first.equals(second)
