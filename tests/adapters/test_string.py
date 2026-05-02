"""Live STRING adapter tests.

Sentinels: TP53 (human, taxon 9606) — ubiquitous cancer gene with many known interaction partners.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq


pytestmark = pytest.mark.live


def test_string_interaction_partners():
    """TP53 has ≥1 interaction partner returned with score columns."""
    df = eq.get("string", protein="TP53", species=9606, limit=5)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 partner for TP53, got {df.height}"

    assert "preferredName_A" in df.columns or "preferredName_B" in df.columns, (
        f"missing protein name columns; columns={df.columns}"
    )
    assert "score" in df.columns, f"missing score column; columns={df.columns}"


def test_string_tp53_appears_in_partners():
    """At least one row references TP53."""
    df = eq.get("string", protein="TP53", species=9606, limit=10)

    all_vals = " ".join(
        str(v) for col in ("preferredName_A", "preferredName_B")
        if col in df.columns
        for v in df[col].to_list()
    )
    assert "TP53" in all_vals, f"TP53 not found in partner names: {all_vals[:200]!r}"


def test_string_network():
    """Network query for TP53+MDM2 returns interaction edges."""
    df = eq.get("string", proteins=["TP53", "MDM2"], species=9606)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected ≥1 edge for TP53+MDM2 network"


def test_string_requires_arg():
    """Calling without selector raises ValueError."""
    with pytest.raises(ValueError, match="protein|proteins|resolve"):
        eq.get("string")


def test_string_cache_roundtrip():
    """Second call returns identical cached frame."""
    first = eq.get("string", protein="TP53", species=9606, limit=5)
    second = eq.get("string", protein="TP53", species=9606, limit=5)
    assert first.equals(second)
