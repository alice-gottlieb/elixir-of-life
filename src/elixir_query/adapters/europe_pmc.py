"""Europe PMC adapter (literature database).

Docs: https://europepmc.org/RestfulWebService
Notes: docs/adapter-notes/europe_pmc.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/europepmc/webservices/rest
  - /search?query=...&format=json&cursorMark=*  (main search, cursor-paginated)
  - /article/{source}/{id}                       (single article)
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
_SEARCH_URL = _BASE + "/search"
_ARTICLE_URL = _BASE + "/article/{source}/{id}"

_JSON_HEADERS = {"Accept": "application/json"}
_TTL_QUERY_SECONDS = 7 * 24 * 3600  # 7 days


def _flatten(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            out[k] = _json.dumps(v)
        else:
            out[k] = v
    return out


@register
class EuropePMCAdapter(BaseAdapter):
    """Europe PMC literature REST adapter (cursor-paginated JSON)."""

    meta = AdapterMeta(
        name="europe_pmc",
        aliases=("europepmc", "epmc"),
        homepage="https://europepmc.org",
        citation=(
            "Europe PMC Consortium. Europe PMC: a full-text literature database. "
            "Nucleic Acids Res. 43:D1042–D1048 (2015)."
        ),
        supports_bulk=False,
        example_params={"pmid": "28209558"},
        description=(
            "Europe PMC — full-text literature database covering life sciences. "
            "Call with pmid='28209558' for a single article, or query='insulin AND "
            "TITLE:diabetes' for a Lucene-style search."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        pmid: str | None = None,
        pmcid: str | None = None,
        source: str = "MED",
        query: str | None = None,
        result_type: str = "lite",
        limit: int | None = None,
        page_size: int = 200,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch Europe PMC records.

        Args:
            pmid: PubMed ID (e.g. ``"28209558"``). Triggers the single-article
                endpoint with ``source="MED"``.
            pmcid: PMC ID (e.g. ``"PMC5414121"``). Triggers single-article
                endpoint with ``source="PMC"``.
            source: Source code for single-article lookup when using a raw ``id``
                query (``"MED"``, ``"PMC"``, ``"PPR"``, etc.).
            query: Lucene-style full-text query string (e.g.
                ``"TITLE:CRISPR AND OPEN_ACCESS:Y"``).
            result_type: ``"lite"`` (default) or ``"core"`` for full metadata.
            limit: Stop after ``limit`` rows across pages.
            page_size: Server-side page size (max 1000).
        """
        if pmid is None and pmcid is None and query is None:
            raise ValueError("pass pmid=..., pmcid=..., or query=...")

        # ---------- single-article lookup ----------
        if pmid is not None:
            return self._article("MED", pmid)
        if pmcid is not None:
            cid = pmcid.upper().replace("PMC", "")
            return self._article("PMC", cid)

        # ---------- cursor-paginated search ----------
        assert query is not None
        key = {"kind": "search", "query": query, "result_type": result_type, "limit": limit}
        cached = self.ctx.cache.get_query("europe_pmc", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        cursor = "*"
        prev_cursor: str | None = None
        while True:
            params = {
                "query": query,
                "format": "json",
                "resultType": result_type,
                "pageSize": page_size,
                "cursorMark": cursor,
            }
            resp = self.ctx.http.get(_SEARCH_URL, params=params, db="europe_pmc")
            data = resp.json()
            result_list = (data.get("resultList") or {}).get("result") or []
            if not isinstance(result_list, list):
                raise ParseError(
                    "europe_pmc",
                    f"expected list under resultList.result, got {type(result_list).__name__}",
                )
            for r in result_list:
                rows.append(_flatten(r) if isinstance(r, dict) else {"value": r})
                if limit is not None and len(rows) >= limit:
                    break
            if limit is not None and len(rows) >= limit:
                break
            next_cursor = data.get("nextCursorMark")
            if not next_cursor or next_cursor == cursor or next_cursor == prev_cursor:
                break
            prev_cursor, cursor = cursor, next_cursor

        if not rows:
            raise ParseError("europe_pmc", f"no results for query {query!r}")
        df = records_to_df(rows, db="europe_pmc")
        self.ctx.cache.put_query("europe_pmc", key, df, url=_SEARCH_URL)
        return df

    def _article(self, src: str, eid: str) -> pl.DataFrame:
        key = {"kind": "article", "source": src, "id": eid}
        cached = self.ctx.cache.get_query("europe_pmc", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        url = _ARTICLE_URL.format(source=src, id=eid)
        resp = self.ctx.http.get(url, params={"format": "json"}, db="europe_pmc")
        data = resp.json()
        # Single-article endpoint wraps the record in a list at resultList.result.
        result_list = (data.get("resultList") or {}).get("result") or []
        if not isinstance(result_list, list) or not result_list:
            raise ParseError("europe_pmc", f"no record returned for {src}/{eid}")
        df = records_to_df([_flatten(result_list[0])], db="europe_pmc")
        self.ctx.cache.put_query("europe_pmc", key, df, url=str(resp.request.url))
        return df
