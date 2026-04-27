"""Rhea adapter.

Docs: https://www.rhea-db.org/help/rest-api
Notes: docs/adapter-notes/rhea.md (consulted 2026-04-27).

REST base: https://www.rhea-db.org/rhea
  - GET /rhea?query=...&columns=...&format=tsv&limit=...   (search, single endpoint)

FTP bulk: https://ftp.expasy.org/databases/rhea/tsv/
  - rhea-reactions.tsv etc. (used for bulk()).

The REST endpoint returns TSV (preferred), JSON, RXN, or RD. We accept TSV over the
wire and let `core.cache` persist as CSV + Parquet per the project-wide preference.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import read_tsv
from elixir_query.errors import ParseError
from elixir_query.registry import register

_REST_URL = "https://www.rhea-db.org/rhea"
_FTP_BASE = "https://ftp.expasy.org/databases/rhea/tsv"

_DEFAULT_COLUMNS = (
    "rhea-id",
    "equation",
    "chebi",
    "chebi-id",
    "ec",
    "uniprot",
)

_TTL_QUERY_SECONDS = 7 * 24 * 3600  # 7 days


def _normalise_rhea_id(rhea_id: str | int) -> str:
    """Return the numeric portion of a Rhea identifier ('RHEA:10044' -> '10044')."""
    s = str(rhea_id).strip()
    if s.upper().startswith("RHEA:"):
        s = s.split(":", 1)[1]
    if not s.isdigit():
        raise ValueError(f"invalid Rhea id {rhea_id!r}; expected 'RHEA:10044' or '10044'")
    return s


@register
class RheaAdapter(BaseAdapter):
    """Rhea reactions via the rhea-db.org REST endpoint and Expasy FTP."""

    meta = AdapterMeta(
        name="rhea",
        aliases=("rhea-db",),
        homepage="https://www.rhea-db.org",
        citation="Bansal P. et al. Rhea, the reaction knowledgebase in 2022. NAR 50:D693–D700.",
        supports_bulk=True,
        example_params={"rhea_id": "RHEA:10044"},
        description=(
            "Rhea — expert-curated biochemical reactions, the reference vocabulary used "
            "by UniProtKB. Call with rhea_id='RHEA:10044' for a single reaction or "
            "query='glucose' / query='uniprot:P00533' for a search."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        rhea_id: str | int | None = None,
        query: str | None = None,
        columns: list[str] | tuple[str, ...] | None = None,
        limit: int | None = None,
        **_: Any,
    ) -> pl.DataFrame:
        """Fetch Rhea reaction rows.

        Args:
            rhea_id: Single Rhea identifier (e.g. ``"RHEA:10044"`` or ``10044``).
                If given, ``query`` is ignored.
            query: Free-text or field-qualified Rhea query
                (``"glucose"``, ``"uniprot:P00533"``, ...).
            columns: Columns to request. Defaults to a useful subset.
            limit: Server-side row cap (Rhea's REST endpoint is not paginated).

        Returns:
            Polars DataFrame with one row per reaction.
        """
        if rhea_id is None and query is None:
            raise ValueError("pass either rhea_id=... or query=... to rhea.get()")

        cols_csv = ",".join(columns or _DEFAULT_COLUMNS)

        if rhea_id is not None:
            num = _normalise_rhea_id(rhea_id)
            params = {"query": f"rhea:{num}", "columns": cols_csv, "format": "tsv", "limit": "1"}
            cache_key = {"rhea_id": num, "columns": cols_csv}
            cached = self.ctx.cache.get_query("rhea", cache_key, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            resp = self.ctx.http.get(_REST_URL, params=params, db="rhea")
            df = read_tsv(resp.text, db="rhea")
            if df.height == 0:
                raise ParseError("rhea", f"no row returned for Rhea id {rhea_id!r}")
            self.ctx.cache.put_query("rhea", cache_key, df, url=str(resp.request.url))
            return df

        # Search path.
        assert query is not None
        params = {"query": query, "columns": cols_csv, "format": "tsv"}
        if limit is not None:
            params["limit"] = str(int(limit))
        cache_key = {"query": query, "columns": cols_csv, "limit": limit}
        cached = self.ctx.cache.get_query("rhea", cache_key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached

        resp = self.ctx.http.get(_REST_URL, params=params, db="rhea")
        df = read_tsv(resp.text, db="rhea")
        if df.height == 0:
            raise ParseError("rhea", f"empty result for query {query!r}")
        self.ctx.cache.put_query("rhea", cache_key, df, url=str(resp.request.url))
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(
        self,
        *,
        file: str = "rhea-reactions.tsv",
        **_: Any,
    ) -> pl.LazyFrame:
        """Stream a Rhea FTP TSV dump and expose it as a LazyFrame.

        Args:
            file: Filename under ``https://ftp.expasy.org/databases/rhea/tsv/``.
                Defaults to ``rhea-reactions.tsv`` (one row per directional reaction).
        """
        if "/" in file or ".." in file:
            raise ValueError(f"invalid bulk file name {file!r}")

        key = {"file": file}
        parquet = self.ctx.cache.bulk_ready("rhea", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        url = f"{_FTP_BASE}/{file}"
        raw_path, parquet_path, _meta = self.ctx.cache.bulk_paths("rhea", key)
        self.ctx.http.stream_to_file(url, raw_path, db="rhea")

        try:
            df = pl.read_csv(raw_path, separator="\t", infer_schema_length=10_000)
        except Exception as e:
            raise ParseError("rhea", f"failed to parse bulk file {file!r}: {e}") from e
        if df.height == 0:
            raise ParseError("rhea", f"bulk file {file!r} parsed to zero rows")

        df.write_parquet(parquet_path)
        df.write_csv(raw_path.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "rhea",
            key,
            url=url,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
