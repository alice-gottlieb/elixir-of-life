"""Live ENA Portal API adapter tests.

Sentinels: AB000001 — a stable EMBL/ENA sequence accession.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_ena_sequence_by_accession():
    """Single sequence lookup by accession returns expected row."""
    df = eq.get("ena", accession="AB000001")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 row for AB000001, got {df.height}"

    assert "accession" in df.columns, f"missing 'accession' column: {df.columns}"
    assert "description" in df.columns, f"missing 'description' column: {df.columns}"

    accessions = df["accession"].to_list()
    assert "AB000001" in accessions, f"AB000001 not in accessions: {accessions}"


def test_ena_sequence_fields():
    """Extended field list is returned when scientific_name requested."""
    df = eq.get("ena", accession="AB000001", fields=["accession", "description", "scientific_name", "sequence_length"])

    assert "scientific_name" in df.columns, f"missing scientific_name; columns={df.columns}"
    assert "sequence_length" in df.columns, f"missing sequence_length; columns={df.columns}"


def test_ena_study_result_type():
    """study_accession shorthand switches result type to study."""
    df = eq.get("ena", study_accession="PRJNA257197")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 row"
    assert "study_accession" in df.columns or "secondary_study_accession" in df.columns


def test_ena_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="accession|query|study"):
        eq.get("ena")


def test_ena_cache_roundtrip():
    """Second call returns identical frame (cache hit)."""
    first = eq.get("ena", accession="AB000001")
    second = eq.get("ena", accession="AB000001")
    assert first.equals(second)
