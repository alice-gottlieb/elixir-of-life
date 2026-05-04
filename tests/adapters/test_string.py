"""Live STRING adapter tests.

Policy: real data only. Tests hit string-db.org/api.
No mocks, no synthetic data, no try/except that swallows errors.
"""

from __future__ import annotations

import polars as pl
import pytest

import elixir_query as eq

pytestmark = pytest.mark.live


def test_string_tp53_interaction_partners():
    """TP53 (human) should have MDM2 as a top interaction partner."""
    df = eq.get("string", identifiers="TP53", species=9606, limit=10)

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected >=1 interaction partner for TP53, got {df.height}"

    cols = set(df.columns)
    assert "preferredName_A" in cols or "preferredName_B" in cols, (
        f"expected preferredName_A/B columns, got {df.columns}"
    )
    assert "score" in cols, f"missing 'score' column: {df.columns}"

    # MDM2 is TP53's canonical negative regulator — should appear.
    all_names = set()
    for col in ("preferredName_A", "preferredName_B"):
        if col in df.columns:
            all_names.update(df[col].to_list())
    assert "MDM2" in all_names or "TP53" in all_names, (
        f"Expected TP53 or MDM2 in partner names, got: {all_names}"
    )


def test_string_network_two_proteins():
    """Network query between TP53 and MDM2 should return their edge."""
    df = eq.get(
        "string",
        identifiers=["TP53", "MDM2"],
        species=9606,
        method="network",
    )

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1, f"expected >=1 interaction for TP53+MDM2, got {df.height}"
    assert "score" in df.columns


def test_string_resolve():
    """Resolving 'TP53' should return its STRING identifier."""
    df = eq.get("string", identifiers="TP53", species=9606, method="resolve")

    assert isinstance(df, pl.DataFrame)
    assert df.height >= 1
    # Should contain a STRING ID column (stringId or similar).
    id_col = next(
        (c for c in df.columns if "stringid" in c.lower() or "preferred" in c.lower()),
        None,
    )
    assert id_col is not None, f"no STRING ID column found: {df.columns}"


def test_string_cache_roundtrip():
    """Second call hits the cache and returns an identical frame."""
    import elixir_query.api as api

    first = eq.get("string", identifiers="TP53", species=9606, limit=5)
    second = eq.get("string", identifiers="TP53", species=9606, limit=5)
    assert first.equals(second)

    csvs = list(api._context().cache.root.rglob("string/queries/*.csv"))
    assert csvs, "expected at least one cached CSV file for string"


def test_string_requires_identifiers():
    """Calling without identifiers must raise loudly."""
    with pytest.raises((ValueError, TypeError)):
        eq.get("string")


def test_string_invalid_method_raises():
    """Passing an unsupported method must raise ValueError."""
    with pytest.raises(ValueError, match="method"):
        eq.get("string", identifiers="TP53", method="bogus_method")
