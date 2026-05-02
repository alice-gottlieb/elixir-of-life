"""OrthoDB adapter (orthologous groups database).

Docs: https://www.ezlab.org/orthodb_v11_userguide.html
Notes: docs/adapter-notes/orthodb.md (consulted 2026-05-02).

REST base: https://data.orthodb.org/v11.0
  - /search?query={term}&take=100&skip=0  -> OG search
  - /group?id={og_id}                     -> single OG details
  - /members?id={og_id}                   -> genes in OG
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://data.orthodb.org/v11.0"
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
class OrthoDBAdapter(BaseAdapter):
    """OrthoDB orthologous group REST adapter."""

    meta = AdapterMeta(
        name="orthodb",
        aliases=("orthodb_db",),
        homepage="https://www.orthodb.org",
        citation=(
            "Kuznetsov D, et al. OrthoDB v11: annotation of orthologs in the "
            "widest sampling of organismal diversity. "
            "Nucleic Acids Res. 51:D445–D451 (2023)."
        ),
        supports_bulk=False,
        example_params={"query": "TP53"},
        description=(
            "OrthoDB — hierarchical catalogue of orthologs. "
            "Call with query='TP53' to search for ortholog groups, "
            "group_id='...' to get OG details, or "
            "members_of='...' to list OG gene members."
        ),
    )

    def query(
        self,
        *,
        query: str | None = None,
        group_id: str | None = None,
        members_of: str | None = None,
        level: str | None = None,
        take: int = 100,
        skip: int = 0,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch OrthoDB data.

        Args:
            query: Gene name / keyword to search ortholog groups (e.g. ``"TP53"``).
            group_id: OrthoDB OG ID (e.g. ``"9606_0:002c41"``).
            members_of: OG ID to retrieve gene members.
            level: Taxonomic level (NCBI taxon ID, e.g. ``"9606"`` for human).
            take: Max results to return from search.
            skip: Offset for search pagination.
        """
        if query is not None:
            return self._search(query, level=level, take=take, skip=skip)
        if group_id is not None:
            return self._group(group_id)
        if members_of is not None:
            return self._members(members_of)
        raise ValueError("pass query=, group_id=, or members_of=... to orthodb.get()")

    def _search(self, query: str, *, level: str | None, take: int, skip: int) -> pl.DataFrame:
        key = {"kind": "search", "query": query, "level": level, "take": take, "skip": skip}
        cached = self.ctx.cache.get_query("orthodb", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/search"
        params: dict[str, Any] = {"query": query, "take": take, "skip": skip}
        if level:
            params["level"] = level
        resp = self.ctx.http.get(url, params=params, headers=_JSON_HEADERS, db="orthodb")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("orthodb", f"expected dict from search, got {type(data).__name__}")

        bigdata = data.get("bigdata") or []
        og_ids = data.get("data") or []

        if bigdata and isinstance(bigdata, list):
            rows = [_flatten(r) if isinstance(r, dict) else {"id": r} for r in bigdata]
        elif og_ids:
            rows = [{"id": oid, "query": query} for oid in og_ids]
        else:
            raise ParseError("orthodb", f"no results for query {query!r}")

        df = records_to_df(rows, db="orthodb")
        self.ctx.cache.put_query("orthodb", key, df, url=str(resp.request.url))
        return df

    def _group(self, group_id: str) -> pl.DataFrame:
        key = {"kind": "group", "id": group_id}
        cached = self.ctx.cache.get_query("orthodb", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/group"
        params = {"id": group_id}
        resp = self.ctx.http.get(url, params=params, headers=_JSON_HEADERS, db="orthodb")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("orthodb", f"expected dict for group {group_id}, got {type(data).__name__}")

        result = data.get("data") or data
        if isinstance(result, dict):
            rows = [_flatten(result)]
        elif isinstance(result, list):
            rows = [_flatten(r) if isinstance(r, dict) else {"id": r} for r in result]
        else:
            raise ParseError("orthodb", f"unexpected 'data' type: {type(result).__name__}")

        df = records_to_df(rows, db="orthodb")
        if df.height == 0:
            raise ParseError("orthodb", f"empty group response for {group_id!r}")
        self.ctx.cache.put_query("orthodb", key, df, url=str(resp.request.url))
        return df

    def _members(self, group_id: str) -> pl.DataFrame:
        key = {"kind": "members", "id": group_id}
        cached = self.ctx.cache.get_query("orthodb", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/members"
        params = {"id": group_id}
        resp = self.ctx.http.get(url, params=params, headers=_JSON_HEADERS, db="orthodb")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("orthodb", f"expected dict for members, got {type(data).__name__}")

        members = data.get("data") or []
        if not isinstance(members, list):
            raise ParseError("orthodb", f"expected list under data, got {type(members).__name__}")
        if not members:
            raise ParseError("orthodb", f"no members returned for OG {group_id!r}")

        rows = [_flatten(r) if isinstance(r, dict) else {"gene_id": r} for r in members]
        df = records_to_df(rows, db="orthodb")
        self.ctx.cache.put_query("orthodb", key, df, url=str(resp.request.url))
        return df
