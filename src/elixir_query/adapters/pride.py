"""PRIDE Archive adapter (proteomics data).

Docs: https://www.ebi.ac.uk/pride/ws/archive/v2/docs/api-guide.html
Notes: docs/adapter-notes/pride.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/pride/ws/archive/v2
  - /projects/{accession}             -> single project
  - /projects?keyword=...             -> keyword search (paginated)
  - /projects/{accession}/files       -> files for a project
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
_TTL_QUERY_SECONDS = 7 * 24 * 3600


def _flatten(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {"value": _json.dumps(d)}
    return {k: (_json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in d.items()}


def _hal_next(data: dict) -> str | None:
    return ((data.get("_links") or {}).get("next") or {}).get("href")


@register
class PRIDEAdapter(BaseAdapter):
    """PRIDE Archive proteomics metadata REST adapter."""

    meta = AdapterMeta(
        name="pride",
        aliases=("pride_archive",),
        homepage="https://www.ebi.ac.uk/pride/archive",
        citation=(
            "Perez-Riverol Y, et al. The PRIDE database and related tools in 2019. "
            "Nucleic Acids Res. 47:D442–D450 (2019)."
        ),
        supports_bulk=False,
        example_params={"accession": "PXD000001"},
        description=(
            "PRIDE Archive — proteomics identifications database. Call with "
            "accession='PXD000001' for a single project, keyword='cancer' for "
            "a search, or files_for='PXD000001' for the file list of a project."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        accession: str | None = None,
        keyword: str | None = None,
        files_for: str | None = None,
        limit: int | None = 100,
        page_size: int = 100,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch PRIDE Archive project metadata.

        Args:
            accession: PXD project accession (e.g. ``"PXD000001"``).
            keyword: Free-text keyword search over project metadata.
            files_for: PXD accession; returns file list for that project.
            limit: Row cap for list/search queries.
            page_size: Server-side page size.
        """
        if accession is None and keyword is None and files_for is None:
            raise ValueError("pass accession=, keyword=, or files_for=")

        # ---- single project ----
        if accession is not None:
            key = {"kind": "project", "accession": accession}
            cached = self.ctx.cache.get_query("pride", key, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = f"{_BASE}/projects/{accession}"
            resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="pride")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("pride", f"expected dict for project, got {type(data).__name__}")
            df = records_to_df([_flatten(data)], db="pride")
            if df.height == 0:
                raise ParseError("pride", f"no record returned for accession={accession!r}")
            self.ctx.cache.put_query("pride", key, df, url=str(resp.request.url))
            return df

        # ---- project files ----
        if files_for is not None:
            return self._paginated(
                url=f"{_BASE}/projects/{files_for}/files",
                embedded_key="files",
                key={"kind": "files", "accession": files_for, "limit": limit},
                params={"pageSize": page_size, "page": 0},
                limit=limit,
            )

        # ---- keyword search ----
        assert keyword is not None
        return self._paginated(
            url=f"{_BASE}/projects",
            embedded_key="compactprojects",
            key={"kind": "search", "keyword": keyword, "limit": limit},
            params={"keyword": keyword, "pageSize": page_size, "page": 0},
            limit=limit,
        )

    def _paginated(
        self,
        *,
        url: str,
        embedded_key: str,
        key: dict[str, Any],
        params: dict[str, Any],
        limit: int | None,
    ) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("pride", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        rows: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params: dict[str, Any] | None = dict(params)
        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, headers=_JSON_HEADERS, db="pride")
            data = resp.json()
            # Files endpoint returns a bare list; project search returns a HAL-wrapped dict.
            if isinstance(data, list):
                records = data
                next_url = None
            elif isinstance(data, dict):
                records = (data.get("_embedded") or {}).get(embedded_key) or []
                next_url = _hal_next(data)
            else:
                raise ParseError("pride", f"unexpected response: {type(data).__name__}")
            for r in records:
                rows.append(_flatten(r))
                if limit is not None and len(rows) >= limit:
                    break
            if limit is not None and len(rows) >= limit:
                break
            next_params = None
        if not rows:
            raise ParseError("pride", f"no rows returned for {embedded_key}")
        df = records_to_df(rows, db="pride")
        self.ctx.cache.put_query("pride", key, df, url=url)
        return df
