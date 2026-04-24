"""Helpers for turning upstream responses into Polars DataFrames.

Project-wide preference: when persisting text artifacts we write **CSV** rather than TSV.
APIs that only offer TSV are accepted over the wire and normalised in memory.
"""

from __future__ import annotations

import gzip
import io
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import polars as pl

from elixir_query.errors import ParseError


def read_tsv(text: str, *, db: str, **kwargs: Any) -> pl.DataFrame:
    """Parse TSV text into a DataFrame. Raises ParseError on failure."""
    try:
        return pl.read_csv(io.StringIO(text), separator="\t", **kwargs)
    except Exception as e:
        raise ParseError(db, f"failed to parse TSV: {e}") from e


def read_csv(text: str, *, db: str, **kwargs: Any) -> pl.DataFrame:
    try:
        return pl.read_csv(io.StringIO(text), **kwargs)
    except Exception as e:
        raise ParseError(db, f"failed to parse CSV: {e}") from e


def records_to_df(records: Iterable[dict[str, Any]], *, db: str) -> pl.DataFrame:
    """Build a DataFrame from an iterable of flat dict records."""
    rows = list(records)
    if not rows:
        # Return a truly empty DataFrame; callers can assert height > 0 to enforce
        # non-empty contract.
        return pl.DataFrame()
    try:
        return pl.from_dicts(rows)
    except Exception as e:
        raise ParseError(db, f"failed to build DataFrame from records: {e}") from e


def read_json_bytes(data: bytes, *, db: str) -> Any:
    try:
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        raise ParseError(db, f"failed to decode JSON: {e}") from e


def gunzip_to_file(src: Path, dest: Path, *, chunk: int = 1 << 20) -> int:
    """Decompress a gzip file to ``dest``. Returns uncompressed byte count."""
    written = 0
    with gzip.open(src, "rb") as fh, open(dest, "wb") as out:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            out.write(buf)
            written += len(buf)
    return written


__all__ = ["read_tsv", "read_csv", "records_to_df", "read_json_bytes", "gunzip_to_file"]
