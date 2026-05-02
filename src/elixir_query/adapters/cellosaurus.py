"""Cellosaurus adapter (cell line knowledgebase).

Docs: https://api.cellosaurus.org/
Notes: docs/adapter-notes/cellosaurus.md (consulted 2026-05-02).

REST base: https://api.cellosaurus.org
  - /cell-line/{accession}?format=json     -> single cell line
  - /search/cell-line?q=...&format=json    -> paginated search
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://api.cellosaurus.org"
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


def _normalise_record(r: Any) -> dict[str, Any]:
    """Extract a flat dict from a Cellosaurus cell line JSON object."""
    if not isinstance(r, dict):
        return {"raw": _json.dumps(r)}
    result: dict[str, Any] = {}
    for k, v in r.items():
        if isinstance(v, (dict, list)):
            result[k] = _json.dumps(v)
        else:
            result[k] = v
    return result


@register
class CellosaurusAdapter(BaseAdapter):
    """Cellosaurus cell line knowledge base REST adapter."""

    meta = AdapterMeta(
        name="cellosaurus",
        aliases=("cellosaurus_db",),
        homepage="https://www.cellosaurus.org",
        citation=(
            "Bairoch A. The Cellosaurus, a cell-line knowledge resource. "
            "J. Proteome Res. 17:4408–4417 (2018)."
        ),
        supports_bulk=False,
        example_params={"accession": "CVCL_0004"},
        description=(
            "Cellosaurus — encyclopaedic knowledge resource on cell lines. "
            "Call with accession='CVCL_0004' for HeLa, or "
            "query='HeLa' to search by name."
        ),
    )

    def query(
        self,
        *,
        accession: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch Cellosaurus cell line records.

        Args:
            accession: CVCL accession (e.g. ``"CVCL_0004"``).
            query: Free-text search (name, accession, synonym).
            limit: Maximum records returned in search mode.
            offset: Search offset.
        """
        if accession is not None:
            return self._single(accession)
        if query is not None:
            return self._search(query, limit=limit, offset=offset)
        raise ValueError("pass accession=... or query=... to cellosaurus.get()")

    def _single(self, accession: str) -> pl.DataFrame:
        key = {"kind": "cell_line", "accession": accession}
        cached = self.ctx.cache.get_query("cellosaurus", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/cell-line/{accession}"
        params = {"format": "json"}
        resp = self.ctx.http.get(url, params=params, headers=_JSON_HEADERS, db="cellosaurus")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("cellosaurus", f"expected dict for {accession}, got {type(data).__name__}")

        # Cellosaurus wraps the record under "Cell-line-list" → first item
        cell_lines = data.get("Cell-line-list") or data.get("cell_line_list") or []
        if isinstance(cell_lines, list) and cell_lines:
            record = _normalise_record(cell_lines[0])
        else:
            record = _normalise_record(data)

        df = records_to_df([record], db="cellosaurus")
        if df.height == 0:
            raise ParseError("cellosaurus", f"empty response for accession {accession!r}")
        self.ctx.cache.put_query("cellosaurus", key, df, url=str(resp.request.url))
        return df

    def _search(self, query: str, *, limit: int, offset: int) -> pl.DataFrame:
        key = {"kind": "search", "query": query, "limit": limit, "offset": offset}
        cached = self.ctx.cache.get_query("cellosaurus", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/search/cell-line"
        params = {"q": query, "format": "json", "limit": limit, "offset": offset}
        resp = self.ctx.http.get(url, params=params, headers=_JSON_HEADERS, db="cellosaurus")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("cellosaurus", f"expected dict from search, got {type(data).__name__}")

        cell_lines = (
            data.get("Cell-line-list")
            or data.get("cell_line_list")
            or data.get("results")
            or []
        )
        if not isinstance(cell_lines, list):
            raise ParseError("cellosaurus", f"expected list in search response, got {type(cell_lines).__name__}")

        rows = [_normalise_record(r) for r in cell_lines]
        if not rows:
            raise ParseError("cellosaurus", f"no results for query {query!r}")

        df = records_to_df(rows, db="cellosaurus")
        self.ctx.cache.put_query("cellosaurus", key, df, url=str(resp.request.url))
        return df
