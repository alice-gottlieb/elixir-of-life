"""Unit tests for the on-disk cache."""

from __future__ import annotations

import json
import time
from pathlib import Path

import polars as pl

from elixir_query.core.cache import Cache, stable_key


def test_stable_key_is_deterministic():
    a = stable_key("uniprot", {"query": "insulin", "limit": 10})
    b = stable_key("uniprot", {"limit": 10, "query": "insulin"})  # different order
    assert a == b


def test_stable_key_distinguishes_params():
    a = stable_key("uniprot", {"query": "insulin"})
    b = stable_key("uniprot", {"query": "p53"})
    assert a != b


def test_put_and_get_query_roundtrip(tmp_path: Path):
    cache = Cache(tmp_path)
    df = pl.DataFrame({"accession": ["P00533", "Q9Y243"], "length": [1210, 480]})
    params = {"query": "kinase", "limit": 2}
    cache.put_query("uniprot", params, df, url="https://example/")

    got = cache.get_query("uniprot", params, ttl_seconds=None)
    assert got is not None
    assert got.equals(df)


def test_query_cache_writes_both_csv_and_parquet(tmp_path: Path):
    cache = Cache(tmp_path)
    df = pl.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    params = {"id": 7}
    parquet = cache.put_query("test", params, df)

    csv_path = parquet.with_suffix(".csv")
    assert parquet.exists(), "parquet file must be written"
    assert csv_path.exists(), "CSV file must be written (project-wide preference)"
    csv_text = csv_path.read_text()
    assert "a,b" in csv_text.splitlines()[0], "CSV header must use comma separator"


def test_query_cache_respects_ttl(tmp_path: Path):
    cache = Cache(tmp_path)
    df = pl.DataFrame({"x": [1]})
    params = {"id": 1}
    cache.put_query("db", params, df)
    # Rewrite metadata to be "old".
    meta = next((tmp_path / "db" / "queries").glob("*.json"))
    data = json.loads(meta.read_text())
    data["created_at"] = time.time() - 10_000
    meta.write_text(json.dumps(data))

    assert cache.get_query("db", params, ttl_seconds=1) is None
    assert cache.get_query("db", params, ttl_seconds=None) is not None


def test_clear_removes_files(tmp_path: Path):
    cache = Cache(tmp_path)
    cache.put_query("a", {"k": 1}, pl.DataFrame({"x": [1]}))
    cache.put_query("b", {"k": 2}, pl.DataFrame({"x": [2]}))
    removed = cache.clear("a")
    assert removed >= 3  # parquet + csv + meta
    assert cache.get_query("a", {"k": 1}, ttl_seconds=None) is None
    assert cache.get_query("b", {"k": 2}, ttl_seconds=None) is not None

    cache.clear()
    assert cache.get_query("b", {"k": 2}, ttl_seconds=None) is None
