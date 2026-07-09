"""ENA (European Nucleotide Archive) adapter.

Docs: https://ena-docs.readthedocs.io/en/latest/retrieval/programmatic-access/
Notes: docs/adapter-notes/ena.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/ena/portal/api
  - /search  — main TSV/JSON search with offset pagination
"""

from __future__ import annotations

from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import read_tsv
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://www.ebi.ac.uk/ena/portal/api"
_SEARCH_URL = _BASE + "/search"

_DEFAULT_READ_RUN_FIELDS = (
    "accession",
    "study_accession",
    "sample_accession",
    "experiment_accession",
    "run_accession",
    "scientific_name",
    "tax_id",
    "instrument_platform",
    "library_strategy",
    "read_count",
    "base_count",
)

_DEFAULT_SAMPLE_FIELDS = (
    "accession",
    "study_accession",
    "scientific_name",
    "tax_id",
    "collection_date",
    "country",
    "description",
)

_DEFAULT_STUDY_FIELDS = (
    "study_accession",
    "secondary_study_accession",
    "study_title",
    "study_type",
    "center_name",
    "first_public",
)

_DEFAULT_FIELDS_BY_RESULT: dict[str, tuple[str, ...]] = {
    "read_run": _DEFAULT_READ_RUN_FIELDS,
    "sample": _DEFAULT_SAMPLE_FIELDS,
    "study": _DEFAULT_STUDY_FIELDS,
}

_TTL_QUERY_SECONDS = 7 * 24 * 3600
_PAGE_SIZE = 1000


@register
class ENAAdapter(BaseAdapter):
    """ENA Portal API adapter — sequences, runs, samples, studies."""

    meta = AdapterMeta(
        name="ena",
        aliases=("european_nucleotide_archive",),
        homepage="https://www.ebi.ac.uk/ena/browser/",
        citation=(
            "Harrison PW, et al. The European Nucleotide Archive in 2020. "
            "Nucleic Acids Res. 2021."
        ),
        supports_bulk=True,
        example_params={"query": "study_accession=ERP000001", "result": "read_run"},
        description=(
            "ENA — European Nucleotide Archive. Call with query='study_accession=ERP000001'"
            " and result='read_run' (or 'sample', 'study', 'sequence', etc.)."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        query: str,
        result: str = "read_run",
        fields: list[str] | tuple[str, ...] | None = None,
        limit: int = 1000,
        page_size: int = _PAGE_SIZE,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Search the ENA Portal API.

        Args:
            query: ENA query string (e.g. ``"study_accession=ERP000001"`` or
                ``"tax_eq(9606) AND instrument_platform=ILLUMINA"``).
            result: Result type: ``"read_run"``, ``"sample"``, ``"study"``,
                ``"sequence"``, ``"analysis"``, etc.
            fields: List of field names to return. Defaults to a sensible subset
                based on ``result``.
            limit: Total row cap. Use a large number or ``0`` for unlimited.
            page_size: Rows per page (server max ~100000; keep ≤1000 for safety).
        """
        if not query:
            raise ValueError("query must be a non-empty ENA Portal query string")

        flds = list(fields or _DEFAULT_FIELDS_BY_RESULT.get(result, ("accession", "description")))
        key = {"kind": "search", "query": query, "result": result, "fields": flds, "limit": limit}
        cached = self.ctx.cache.get_query("ena", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached

        rows: list[pl.DataFrame] = []
        offset = 0
        total = 0
        while True:
            effective_limit = page_size if limit == 0 else min(page_size, limit - total)
            if effective_limit <= 0:
                break
            params: dict[str, Any] = {
                "query": query,
                "result": result,
                "fields": ",".join(flds),
                "format": "tsv",
                "limit": effective_limit,
                "offset": offset,
            }
            resp = self.ctx.http.get(_SEARCH_URL, params=params, db="ena")
            page = read_tsv(resp.text, db="ena")
            if page.height == 0:
                break
            rows.append(page)
            total += page.height
            if page.height < effective_limit:
                break  # last page
            offset += page.height

        if not rows:
            raise ParseError("ena", f"no rows returned for query {query!r} result={result!r}")
        df = pl.concat(rows, how="vertical_relaxed")
        self.ctx.cache.put_query("ena", key, df, url=_SEARCH_URL)
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(
        self,
        *,
        query: str,
        result: str = "read_run",
        fields: list[str] | tuple[str, ...] | None = None,
        **_: Any,
    ) -> pl.LazyFrame:
        """Stream a full (unlimited) ENA search result into a Parquet LazyFrame.

        Uses the same Portal API as ``query()`` but with ``limit=0`` and
        materialises every page into a single Parquet file.
        """
        flds = list(fields or _DEFAULT_FIELDS_BY_RESULT.get(result, ("accession", "description")))
        key = {"kind": "bulk", "query": query, "result": result, "fields": flds}
        parquet = self.ctx.cache.bulk_ready("ena", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        raw, parquet_path, _meta = self.ctx.cache.bulk_paths("ena", key)
        rows: list[pl.DataFrame] = []
        offset = 0
        while True:
            params: dict[str, Any] = {
                "query": query,
                "result": result,
                "fields": ",".join(flds),
                "format": "tsv",
                "limit": _PAGE_SIZE,
                "offset": offset,
            }
            resp = self.ctx.http.get(_SEARCH_URL, params=params, db="ena")
            page = read_tsv(resp.text, db="ena")
            if page.height == 0:
                break
            rows.append(page)
            if page.height < _PAGE_SIZE:
                break
            offset += page.height

        if not rows:
            raise ParseError("ena", f"bulk query {query!r} returned no rows")
        df = pl.concat(rows, how="vertical_relaxed")
        df.write_parquet(parquet_path)
        df.write_csv(raw.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "ena",
            key,
            url=_SEARCH_URL,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
