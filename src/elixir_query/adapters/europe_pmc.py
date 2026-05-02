"""Europe PMC adapter (literature search).

Docs: https://europepmc.org/RestfulWebService
Notes: docs/adapter-notes/europe_pmc.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/europepmc/webservices/rest
  - /search?query=...&resultType=core&cursorMark=*&pageSize=25&format=json
  - cursor-mark pagination: nextCursorMark in each response body
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_JSON_HEADERS = {"Accept": "application/json"}
_TTL = 7 * 24 * 3600  # 7 days


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
    """Europe PMC full-text literature database REST adapter."""

    meta = AdapterMeta(
        name="europe_pmc",
        aliases=("europepmc", "epmc", "europe-pmc"),
        homepage="https://europepmc.org",
        citation=(
            "Ferguson A, et al. Europe PMC: a full-text literature database "
            "for the life sciences. Nucleic Acids Res. 47:D1155–D1162 (2019)."
        ),
        supports_bulk=False,
        example_params={"query": "EXT_ID:30106370 AND SRC:MED"},
        description=(
            "Europe PMC — open-access literature database for the life sciences. "
            "Call with query='insulin AND reviewed:true' for keyword search, or "
            "pmid='30106370' for a single PubMed article."
        ),
    )

    def query(
        self,
        *,
        query: str | None = None,
        pmid: str | None = None,
        pmcid: str | None = None,
        result_type: str = "core",
        page_size: int = 25,
        limit: int | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Search Europe PMC.

        Args:
            query: Lucene-style query (e.g. ``"insulin AND SRC:MED"``).
            pmid: Single PubMed ID — shorthand for ``query='EXT_ID:{pmid} AND SRC:MED'``.
            pmcid: Single PMC ID (e.g. ``"PMC6137631"``).
            result_type: ``"lite"`` (metadata) or ``"core"`` (includes abstract).
            page_size: Records per page (max 1000).
            limit: Stop after this many rows.
        """
        if pmid is not None:
            query = f"EXT_ID:{pmid} AND SRC:MED"
        elif pmcid is not None:
            query = f"EXT_ID:{pmcid} AND SRC:PMC"
        elif query is None:
            raise ValueError("pass query=, pmid=, or pmcid= to europe_pmc.get()")

        key = {"query": query, "result_type": result_type, "limit": limit}
        cached = self.ctx.cache.get_query("europe_pmc", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        cursor = "*"
        while True:
            params = {
                "query": query,
                "resultType": result_type,
                "cursorMark": cursor,
                "pageSize": page_size,
                "format": "json",
            }
            resp = self.ctx.http.get(_SEARCH_URL, params=params, headers=_JSON_HEADERS, db="europe_pmc")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("europe_pmc", f"expected dict, got {type(data).__name__}")

            result_list = data.get("resultList") or {}
            results = result_list.get("result") or []
            if not isinstance(results, list):
                raise ParseError("europe_pmc", f"expected list under resultList.result, got {type(results).__name__}")

            for r in results:
                rows.append(_flatten(r) if isinstance(r, dict) else {"raw": r})
                if limit is not None and len(rows) >= limit:
                    break

            if limit is not None and len(rows) >= limit:
                break

            next_cursor = data.get("nextCursorMark")
            if not next_cursor or next_cursor == cursor or not results:
                break
            cursor = next_cursor

        if not rows:
            raise ParseError("europe_pmc", f"no results for query {query!r}")

        df = records_to_df(rows, db="europe_pmc")
        if limit is not None:
            df = df.head(limit)
        self.ctx.cache.put_query("europe_pmc", key, df, url=_SEARCH_URL)
        return df
