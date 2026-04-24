"""UniProt adapter.

Docs: https://www.uniprot.org/help/api_queries
Notes: docs/adapter-notes/uniprot.md (consulted 2026-04-24).

REST base: https://rest.uniprot.org/uniprotkb/
  - /search       -> paginated Lucene query, returns TSV/JSON/XML/...
  - /{accession}  -> single entry (append ?format=tsv)

No CSV format is offered by the API; we accept TSV over the wire and let the
cache layer persist the DataFrame as both CSV (text) and Parquet (fast reload).
"""

from __future__ import annotations

from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import read_tsv
from elixir_query.errors import ParseError
from elixir_query.registry import register

_SEARCH_URL = "https://rest.uniprot.org/uniprotkb/search"
_ENTRY_URL = "https://rest.uniprot.org/uniprotkb/{accession}"

_DEFAULT_FIELDS = (
    "accession",
    "id",
    "protein_name",
    "gene_names",
    "organism_name",
    "organism_id",
    "length",
    "reviewed",
)

_TTL_QUERY_SECONDS = 7 * 24 * 3600  # 7 days per plan


@register
class UniProtAdapter(BaseAdapter):
    """UniProtKB via the rest.uniprot.org search + entry endpoints."""

    meta = AdapterMeta(
        name="uniprot",
        aliases=("swissprot", "trembl", "uniprotkb"),
        homepage="https://www.uniprot.org",
        citation="The UniProt Consortium. Nucleic Acids Res. 2025 (D609–D617).",
        supports_bulk=True,
        example_params={"accession": "P00533"},
        description=(
            "UniProt Knowledgebase — protein sequence and functional information. "
            "Call with either accession='P00533' for a single entry or query='...' "
            "for a Lucene-style search."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        accession: str | None = None,
        query: str | None = None,
        fields: list[str] | tuple[str, ...] | None = None,
        limit: int | None = None,
        size: int = 500,
        **extra: Any,
    ) -> pl.DataFrame:
        """Fetch UniProtKB entries.

        Args:
            accession: Single UniProt accession (e.g. "P00533"). If given,
                ``query`` is ignored.
            query: Lucene-like query string (e.g. ``"insulin AND reviewed:true"``).
            fields: Column list to return. Defaults to a useful subset.
            limit: Stop after ``limit`` rows (across all pages).
            size: Per-page size (<=500).

        Returns:
            Polars DataFrame with one row per UniProtKB entry.
        """
        if accession is None and query is None:
            raise ValueError("pass either accession=... or query=... to uniprot.get()")

        fields_csv = ",".join(fields or _DEFAULT_FIELDS)

        if accession is not None:
            params = {"accession": accession, "fields": fields_csv}
            cached = self.ctx.cache.get_query("uniprot", params, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = _ENTRY_URL.format(accession=accession)
            resp = self.ctx.http.get(url, params={"format": "tsv", "fields": fields_csv}, db="uniprot")
            df = read_tsv(resp.text, db="uniprot")
            if df.height == 0:
                raise ParseError("uniprot", f"no row returned for accession {accession!r}")
            self.ctx.cache.put_query("uniprot", params, df, url=str(resp.request.url))
            return df

        # Search path with Link-header pagination.
        assert query is not None
        key_params = {"query": query, "fields": fields_csv, "size": size, "limit": limit}
        cached = self.ctx.cache.get_query("uniprot", key_params, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached

        params = {"query": query, "format": "tsv", "fields": fields_csv, "size": size}
        rows: list[pl.DataFrame] = []
        seen = 0
        for resp in self.ctx.http.paginate_link(_SEARCH_URL, params=params, db="uniprot"):
            page = read_tsv(resp.text, db="uniprot")
            if page.height == 0:
                break
            rows.append(page)
            seen += page.height
            if limit is not None and seen >= limit:
                break

        if not rows:
            raise ParseError("uniprot", f"empty result for query {query!r}")
        df = pl.concat(rows, how="vertical_relaxed")
        if limit is not None:
            df = df.head(limit)
        self.ctx.cache.put_query("uniprot", key_params, df, url=_SEARCH_URL)
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(
        self,
        *,
        query: str = "reviewed:true",
        fields: list[str] | tuple[str, ...] | None = None,
        **_: Any,
    ) -> pl.LazyFrame:
        """Materialise a large search as Parquet and return a LazyFrame.

        Defaults to all reviewed (Swiss-Prot) entries. For TrEMBL-scale queries
        consider paging directly with ``query(...)`` to control memory.
        """
        fields_csv = ",".join(fields or _DEFAULT_FIELDS)
        key = {"query": query, "fields": fields_csv, "kind": "search"}
        parquet = self.ctx.cache.bulk_ready("uniprot", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        params = {"query": query, "format": "tsv", "fields": fields_csv, "size": 500}
        rows: list[pl.DataFrame] = []
        total = 0
        for resp in self.ctx.http.paginate_link(_SEARCH_URL, params=params, db="uniprot"):
            page = read_tsv(resp.text, db="uniprot")
            if page.height == 0:
                break
            rows.append(page)
            total += page.height
        if not rows:
            raise ParseError("uniprot", f"bulk query {query!r} returned no rows")
        df = pl.concat(rows, how="vertical_relaxed")

        raw, parquet_path, _meta = self.ctx.cache.bulk_paths("uniprot", key)
        df.write_parquet(parquet_path)
        # Keep a CSV mirror for inspection per project preference.
        df.write_csv(raw.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "uniprot",
            key,
            url=_SEARCH_URL,
            rows=total,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
