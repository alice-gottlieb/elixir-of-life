"""PRIDE (PRoteomics IDEntifications) Archive adapter.

Docs: https://www.ebi.ac.uk/pride/ws/archive/v2/docs/api-guide.html
Notes: docs/adapter-notes/pride.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/pride/ws/archive/v2
  - /projects/{accession}        -> single project JSON
  - /projects?q=...&page=0&pageSize=100  -> paginated search
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://www.ebi.ac.uk/pride/ws/archive/v2"
_JSON_HEADERS = {"Accept": "application/json"}
_TTL = 7 * 24 * 3600  # 7 days


def _flatten(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if k == "_links":
            continue
        if isinstance(v, (dict, list)):
            out[k] = _json.dumps(v)
        else:
            out[k] = v
    return out


@register
class PRIDEAdapter(BaseAdapter):
    """PRIDE Archive proteomics dataset REST adapter."""

    meta = AdapterMeta(
        name="pride",
        aliases=("pride_archive",),
        homepage="https://www.ebi.ac.uk/pride/",
        citation=(
            "Perez-Riverol Y, et al. The PRIDE database resources in 2022: "
            "a hub for mass spectrometry-based proteomics evidences. "
            "Nucleic Acids Res. 50:D543–D552 (2022)."
        ),
        supports_bulk=False,
        example_params={"accession": "PXD000001"},
        description=(
            "PRIDE Archive — proteomics datasets. Call with "
            "accession='PXD000001' for a single project, or "
            "query='human cancer' to search."
        ),
    )

    def query(
        self,
        *,
        accession: str | None = None,
        query: str | None = None,
        page_size: int = 100,
        limit: int | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch PRIDE Archive project data.

        Args:
            accession: PRIDE project accession (e.g. ``"PXD000001"``).
            query: Free-text search query.
            page_size: Results per page (≤100).
            limit: Stop after this many rows when using query=.
        """
        if accession is not None:
            return self._single(accession)
        if query is not None:
            return self._search(query, page_size=page_size, limit=limit)
        raise ValueError("pass accession=... or query=... to pride.get()")

    def _single(self, accession: str) -> pl.DataFrame:
        key = {"kind": "project", "accession": accession}
        cached = self.ctx.cache.get_query("pride", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/projects/{accession}"
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="pride")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("pride", f"expected dict for {accession}, got {type(data).__name__}")
        df = records_to_df([_flatten(data)], db="pride")
        if df.height == 0:
            raise ParseError("pride", f"empty response for accession {accession!r}")
        self.ctx.cache.put_query("pride", key, df, url=str(resp.request.url))
        return df

    def _search(self, query: str, *, page_size: int, limit: int | None) -> pl.DataFrame:
        key = {"kind": "search", "query": query, "limit": limit}
        cached = self.ctx.cache.get_query("pride", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        page = 0
        url = f"{_BASE}/projects"

        while True:
            params: dict[str, Any] = {"q": query, "pageSize": page_size, "page": page}
            resp = self.ctx.http.get(url, params=params, headers=_JSON_HEADERS, db="pride")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("pride", f"expected dict from search, got {type(data).__name__}")

            embedded = data.get("_embedded") or {}
            projects = (
                embedded.get("compactprojects")
                or embedded.get("projects")
                or embedded.get("datasets")
                or []
            )
            if not isinstance(projects, list):
                raise ParseError("pride", f"expected list in _embedded, got {type(projects).__name__}")

            for r in projects:
                rows.append(_flatten(r) if isinstance(r, dict) else {"accession": r})
                if limit is not None and len(rows) >= limit:
                    break

            if limit is not None and len(rows) >= limit:
                break
            if len(projects) < page_size:
                break

            links = data.get("_links") or {}
            if not links.get("next"):
                break
            page += 1

        if not rows:
            raise ParseError("pride", f"no projects returned for query {query!r}")

        df = records_to_df(rows, db="pride")
        if limit is not None:
            df = df.head(limit)
        self.ctx.cache.put_query("pride", key, df, url=url)
        return df
