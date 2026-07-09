"""HGNC adapter (HUGO Gene Nomenclature Committee).

Docs: https://www.genenames.org/help/rest/
Notes: docs/adapter-notes/hgnc.md (consulted 2026-05-02).

REST base: https://rest.genenames.org
  - /fetch/{field}/{value}   -> exact lookup (symbol, hgnc_id, uniprot_ids, ...)
  - /search/{query}          -> free-text search
  - /info                    -> service metadata
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://rest.genenames.org"
_BULK_URL = "https://ftp.ebi.ac.uk/pub/databases/genenames/hgnc/tsv/hgnc_complete_set.txt"

_JSON_HEADERS = {"Accept": "application/json"}
_TTL_QUERY_SECONDS = 7 * 24 * 3600

# Fields accepted by /fetch/{field}/
_FETCH_FIELDS = frozenset((
    "symbol", "hgnc_id", "uniprot_ids", "entrez_id",
    "ensembl_gene_id", "refseq_accession", "mgi_id",
    "rgd_id", "vega_id", "ucsc_id", "ccds_id",
))


def _flatten(d: dict[str, Any]) -> dict[str, Any]:
    return {
        k: (_json.dumps(v) if isinstance(v, (dict, list)) else v)
        for k, v in d.items()
    }


def _extract_docs(data: Any, *, url_hint: str = "") -> list[dict[str, Any]]:
    """Pull the docs list out of the HGNC response envelope."""
    if not isinstance(data, dict):
        raise ParseError("hgnc", f"expected dict, got {type(data).__name__}")
    docs = (data.get("response") or {}).get("docs")
    if not isinstance(docs, list):
        raise ParseError("hgnc", f"expected response.docs list (url={url_hint!r})")
    return docs


@register
class HGNCAdapter(BaseAdapter):
    """HGNC gene nomenclature REST adapter."""

    meta = AdapterMeta(
        name="hgnc",
        aliases=("genenames", "hugo"),
        homepage="https://www.genenames.org",
        citation=(
            "Tweedie S, et al. Genenames.org: the HGNC and VGNC resources in 2021. "
            "Nucleic Acids Res. 49:D939–D946 (2021)."
        ),
        supports_bulk=True,
        example_params={"symbol": "BRCA2"},
        description=(
            "HGNC — HUGO Gene Nomenclature Committee. Call with symbol='BRCA2' "
            "for an exact symbol lookup, hgnc_id='HGNC:1101', uniprot_ids='P51587', "
            "ensembl_gene_id='ENSG00000139618', or search='BRCA' for a free-text "
            "search across all fields."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        symbol: str | None = None,
        hgnc_id: str | None = None,
        uniprot_ids: str | None = None,
        entrez_id: str | None = None,
        ensembl_gene_id: str | None = None,
        search: str | None = None,
        fetch_field: str | None = None,
        fetch_value: str | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch HGNC gene records.

        Convenience shortcuts: ``symbol``, ``hgnc_id``, ``uniprot_ids``,
        ``entrez_id``, ``ensembl_gene_id``. For any other field supported by
        ``/fetch/{field}/{value}`` pass ``fetch_field`` + ``fetch_value``.

        ``search`` triggers the free-text ``/search/{query}`` endpoint.
        """
        # Resolve shortcut kwargs to a (field, value) pair.
        field_value: tuple[str, str] | None = None
        if symbol is not None:
            field_value = ("symbol", symbol)
        elif hgnc_id is not None:
            field_value = ("hgnc_id", hgnc_id)
        elif uniprot_ids is not None:
            field_value = ("uniprot_ids", uniprot_ids)
        elif entrez_id is not None:
            field_value = ("entrez_id", str(entrez_id))
        elif ensembl_gene_id is not None:
            field_value = ("ensembl_gene_id", ensembl_gene_id)
        elif fetch_field is not None and fetch_value is not None:
            field_value = (fetch_field, fetch_value)

        if field_value is None and search is None:
            raise ValueError(
                "pass symbol=, hgnc_id=, uniprot_ids=, entrez_id=, "
                "ensembl_gene_id=, fetch_field+fetch_value=, or search="
            )

        # ---- exact fetch ----
        if field_value is not None:
            field, value = field_value
            key = {"kind": "fetch", "field": field, "value": value}
            cached = self.ctx.cache.get_query("hgnc", key, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = f"{_BASE}/fetch/{field}/{value}"
            resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="hgnc")
            docs = _extract_docs(resp.json(), url_hint=url)
            if not docs:
                raise ParseError("hgnc", f"no docs returned for /fetch/{field}/{value}")
            df = records_to_df([_flatten(d) for d in docs], db="hgnc")
            self.ctx.cache.put_query("hgnc", key, df, url=str(resp.request.url))
            return df

        # ---- free-text search ----
        assert search is not None
        key = {"kind": "search", "q": search}
        cached = self.ctx.cache.get_query("hgnc", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        url = f"{_BASE}/search/{search}"
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="hgnc")
        docs = _extract_docs(resp.json(), url_hint=url)
        if not docs:
            raise ParseError("hgnc", f"no docs returned for search={search!r}")
        df = records_to_df([_flatten(d) for d in docs], db="hgnc")
        self.ctx.cache.put_query("hgnc", key, df, url=str(resp.request.url))
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(self, **_: Any) -> pl.LazyFrame:
        """Download the HGNC complete set TSV and return a LazyFrame.

        Tab-delimited flat file (~4 MB) with one row per approved HGNC gene entry.
        """
        from elixir_query.core.io import read_tsv

        key = {"kind": "hgnc_complete_set"}
        parquet = self.ctx.cache.bulk_ready("hgnc", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        raw, parquet_path, _meta = self.ctx.cache.bulk_paths("hgnc", key)
        self.ctx.http.stream_to_file(_BULK_URL, raw, db="hgnc")
        text = raw.read_text(encoding="utf-8")
        df = read_tsv(text, db="hgnc")
        if df.height == 0:
            raise ParseError("hgnc", f"bulk download {_BULK_URL} parsed to zero rows")
        df.write_parquet(parquet_path)
        df.write_csv(raw.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "hgnc",
            key,
            url=_BULK_URL,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
