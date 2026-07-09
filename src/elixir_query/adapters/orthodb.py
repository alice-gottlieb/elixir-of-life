"""OrthoDB adapter (orthologous groups across organisms).

Docs: https://www.ezlab.org/orthodb_v12_userguide.html
Notes: docs/adapter-notes/orthodb.md (consulted 2026-05-03).

REST base: https://data.orthodb.org/v12
  - /search?query=...&level=...     -> list of OG IDs
  - /group?id={og_id}               -> single orthologous group details
  - /genesearch?query=... | gid=N   -> gene search
  - /orthologs?id={og_id}           -> genes in an OG
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://data.orthodb.org/v12"
_TTL_QUERY_SECONDS = 7 * 24 * 3600


def _flatten(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {"value": _json.dumps(d)}
    return {k: (_json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in d.items()}


@register
class OrthoDBAdapter(BaseAdapter):
    """OrthoDB orthologous-groups REST adapter (v12)."""

    meta = AdapterMeta(
        name="orthodb",
        aliases=("ortho_db",),
        homepage="https://www.orthodb.org",
        citation=(
            "Kuznetsov D, et al. OrthoDB and BUSCO update: annotation of orthologs "
            "with wider sampling of genomes. Nucleic Acids Res. 53:D516–D523 (2025)."
        ),
        supports_bulk=False,
        example_params={"og_id": "4977at9604"},
        description=(
            "OrthoDB v12 — orthologous groups across organisms. Call with "
            "og_id='4977at9604' for a single OG, search='p53' for a text search, "
            "gene_id=1 for an NCBI gene lookup, or orthologs_in='4977at9604' "
            "for the genes of an OG."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        og_id: str | None = None,
        search: str | None = None,
        level: int | str | None = None,
        gene_id: int | str | None = None,
        gene_query: str | None = None,
        orthologs_in: str | None = None,
        take: int = 100,
        skip: int = 0,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch OrthoDB records.

        Args:
            og_id: Orthologous-group ID (format ``<cluster>at<clade_taxid>``,
                e.g. ``"4977at9604"``).
            search: Text query (``query=...``) on the search endpoint.
            level: NCBI taxon ID for the orthology level filter.
            gene_id: NCBI gene ID for ``/genesearch?gid=...``.
            gene_query: Gene query string for ``/genesearch?query=...``.
            orthologs_in: OG ID; returns the genes inside that OG.
            take: Page size for search/list endpoints (max 10000).
            skip: Offset for pagination.
        """
        if not any([og_id, search, gene_id, gene_query, orthologs_in]):
            raise ValueError(
                "pass og_id=, search=, gene_id=, gene_query=, or orthologs_in="
            )

        # ---- single OG details ----
        if og_id is not None:
            return self._single(
                f"{_BASE}/group", {"id": og_id}, key={"kind": "group", "id": og_id}
            )

        # ---- search ----
        if search is not None:
            params: dict[str, Any] = {"query": search, "take": take, "skip": skip}
            if level is not None:
                params["level"] = level
            return self._search_list(
                f"{_BASE}/search",
                params,
                key={"kind": "search", "query": search, "level": level, "take": take, "skip": skip},
            )

        # ---- gene by NCBI gene ID ----
        if gene_id is not None:
            return self._single(
                f"{_BASE}/genesearch",
                {"gid": str(gene_id)},
                key={"kind": "genesearch_gid", "gid": str(gene_id)},
            )

        # ---- gene by query string ----
        if gene_query is not None:
            return self._single(
                f"{_BASE}/genesearch",
                {"query": gene_query},
                key={"kind": "genesearch_query", "query": gene_query},
            )

        # ---- orthologs in an OG ----
        assert orthologs_in is not None
        return self._search_list(
            f"{_BASE}/orthologs",
            {"id": orthologs_in},
            key={"kind": "orthologs", "id": orthologs_in},
        )

    def _single(self, url: str, params: dict[str, Any], *, key: dict[str, Any]) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("orthodb", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        resp = self.ctx.http.get(url, params=params, db="orthodb")
        data = resp.json()
        # Some endpoints wrap singletons in {"data": {...}}.
        record = data.get("data") if isinstance(data, dict) and "data" in data else data
        if isinstance(record, list):
            # Wrap a list-of-strings (search-style) into rows.
            rows = [{"value": v} if not isinstance(v, dict) else _flatten(v) for v in record]
        elif isinstance(record, dict):
            rows = [_flatten(record)]
        else:
            raise ParseError("orthodb", f"unexpected response shape from {url}")
        if not rows:
            raise ParseError("orthodb", f"empty result from {url}?{params}")
        df = records_to_df(rows, db="orthodb")
        self.ctx.cache.put_query("orthodb", key, df, url=str(resp.request.url))
        return df

    def _search_list(
        self, url: str, params: dict[str, Any], *, key: dict[str, Any]
    ) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("orthodb", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        resp = self.ctx.http.get(url, params=params, db="orthodb")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("orthodb", f"expected dict, got {type(data).__name__}")
        items = data.get("data") or []
        rows: list[dict[str, Any]] = []
        for item in items:
            if isinstance(item, dict):
                rows.append(_flatten(item))
            else:
                rows.append({"value": str(item)})
        if not rows:
            raise ParseError("orthodb", f"no rows in /search response for {params!r}")
        df = records_to_df(rows, db="orthodb")
        self.ctx.cache.put_query("orthodb", key, df, url=str(resp.request.url))
        return df
