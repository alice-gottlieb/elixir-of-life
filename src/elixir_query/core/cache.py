"""On-disk cache for query results and bulk downloads.

Layout under ``cache_dir``::

    <db>/
        queries/
            <hash>.json      # metadata (url, params, created_at, ttl)
            <hash>.csv       # parsed DataFrame persisted as CSV (text)
            <hash>.parquet   # parsed DataFrame persisted as Parquet (fast reload)
        bulk/
            <key>.raw        # streamed raw download (gz/tsv/etc.)
            <key>.parquet    # converted Parquet for lazy scan
            <key>.json       # metadata
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl


def stable_key(db: str, params: dict[str, Any]) -> str:
    """Stable 16-char blake2b key derived from db + sorted params."""
    canonical = json.dumps({"db": db, "params": _sort_deep(params)}, sort_keys=True, default=str)
    h = hashlib.blake2b(canonical.encode("utf-8"), digest_size=8)
    return h.hexdigest()


def _sort_deep(x: Any) -> Any:
    if isinstance(x, dict):
        return {k: _sort_deep(v) for k, v in sorted(x.items())}
    if isinstance(x, (list, tuple)):
        return [_sort_deep(v) for v in x]
    return x


@dataclass
class CacheEntry:
    key: str
    parquet_path: Path
    csv_path: Path
    meta_path: Path
    created_at: float
    ttl_seconds: float | None

    def is_fresh(self, now: float | None = None) -> bool:
        if self.ttl_seconds is None:
            return True
        now = now if now is not None else time.time()
        return (now - self.created_at) < self.ttl_seconds


class Cache:
    """File-based cache backing query and bulk results."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- query path
    def _query_dir(self, db: str) -> Path:
        d = self.root / db / "queries"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_query(self, db: str, params: dict[str, Any], *, ttl_seconds: float | None) -> pl.DataFrame | None:
        key = stable_key(db, params)
        d = self._query_dir(db)
        parquet = d / f"{key}.parquet"
        meta_path = d / f"{key}.json"
        if not parquet.exists() or not meta_path.exists():
            return None
        meta = json.loads(meta_path.read_text())
        entry = CacheEntry(
            key=key,
            parquet_path=parquet,
            csv_path=d / f"{key}.csv",
            meta_path=meta_path,
            created_at=meta.get("created_at", 0.0),
            ttl_seconds=ttl_seconds,
        )
        if not entry.is_fresh():
            return None
        return pl.read_parquet(parquet)

    def put_query(self, db: str, params: dict[str, Any], df: pl.DataFrame, *, url: str | None = None) -> Path:
        """Persist ``df`` to disk as both CSV (text) and Parquet (fast reload)."""
        key = stable_key(db, params)
        d = self._query_dir(db)
        parquet = d / f"{key}.parquet"
        csv = d / f"{key}.csv"
        meta = d / f"{key}.json"
        df.write_parquet(parquet)
        df.write_csv(csv)
        meta.write_text(
            json.dumps(
                {
                    "db": db,
                    "params": params,
                    "url": url,
                    "created_at": time.time(),
                    "rows": df.height,
                    "columns": df.columns,
                },
                default=str,
                indent=2,
            )
        )
        return parquet

    # ----------------------------------------------------------------- bulk path
    def _bulk_dir(self, db: str) -> Path:
        d = self.root / db / "bulk"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def bulk_paths(self, db: str, params: dict[str, Any]) -> tuple[Path, Path, Path]:
        """Return (raw_path, parquet_path, meta_path) for a bulk key."""
        key = stable_key(db, params)
        d = self._bulk_dir(db)
        return d / f"{key}.raw", d / f"{key}.parquet", d / f"{key}.json"

    def bulk_ready(self, db: str, params: dict[str, Any], *, ttl_seconds: float | None = None) -> Path | None:
        raw, parquet, meta_path = self.bulk_paths(db, params)
        if not parquet.exists() or not meta_path.exists():
            return None
        if ttl_seconds is not None:
            meta = json.loads(meta_path.read_text())
            if (time.time() - meta.get("created_at", 0.0)) >= ttl_seconds:
                return None
        return parquet

    def record_bulk(self, db: str, params: dict[str, Any], *, url: str, rows: int, schema: dict[str, str]) -> None:
        _raw, _parquet, meta_path = self.bulk_paths(db, params)
        meta_path.write_text(
            json.dumps(
                {
                    "db": db,
                    "params": params,
                    "url": url,
                    "rows": rows,
                    "schema": schema,
                    "created_at": time.time(),
                },
                default=str,
                indent=2,
            )
        )

    # ---------------------------------------------------------------------- util
    def clear(self, db: str | None = None) -> int:
        """Remove cached artifacts. Returns number of files deleted."""
        target = self.root if db is None else self.root / db
        if not target.exists():
            return 0
        count = 0
        for p in sorted(target.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
                count += 1
            elif p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass
        if db is None:
            self.root.mkdir(parents=True, exist_ok=True)
        return count


__all__ = ["Cache", "CacheEntry", "stable_key"]
