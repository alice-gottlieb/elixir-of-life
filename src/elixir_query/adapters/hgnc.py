"""HGNC (HUGO Gene Nomenclature Committee) adapter.

Docs: https://www.genenames.org/help/rest/
Notes: docs/adapter-notes/hgnc.md (consulted 2026-05-02).

REST base: https://rest.genenames.org
  - /fetch/symbol/{symbol}     -> full record(s) for approved symbol
  - /fetch/hgnc_id/{hgnc_id}  -> full record(s) by HGNC ID
  - /search/{field}/{value}    -> search (lightweight: hgnc_id+symbol+score)
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
class HGNCAdapter(BaseAdapter):
    """HGNC gene nomenclature REST adapter."""

    meta = AdapterMeta(
        name="hgnc",
        aliases=("genenames", "hugo"),
        homepage="https://www.genenames.org",
        citation=(
            "Tweedie S, et al. Genenames.org: the HGNC resources in 2021. "
            "Nucleic Acids Res. 49:D939–D946 (2021)."
        ),
        supports_bulk=False,
        example_params={"symbol": "EGFR"},
        description=(
            "HGNC — HUGO Gene Nomenclature Committee approved human gene symbols. "
            "Call with symbol='EGFR' or hgnc_id='HGNC:3236' for a full record, "
            "or search_field='name', search_value='epidermal growth factor' to search."
        ),
    )

    def query(
        self,
        *,
        symbol: str | None = None,
        hgnc_id: str | int | None = None,
        search_field: str | None = None,
        search_value: str | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch HGNC gene records.

        Args:
            symbol: Approved HGNC gene symbol (e.g. ``"EGFR"``).
            hgnc_id: HGNC ID (e.g. ``"HGNC:3236"`` or just ``3236``).
            search_field: Field to search (e.g. ``"name"``, ``"symbol"``).
            search_value: Value to search for.
        """
        if symbol is not None:
            return self._fetch("symbol", str(symbol).strip())
        if hgnc_id is not None:
            # normalise to bare number: "HGNC:3236" -> "3236"
            hid = str(hgnc_id).strip()
            if hid.upper().startswith("HGNC:"):
                hid = hid[5:]
            return self._fetch("hgnc_id", hid)
        if search_field is not None and search_value is not None:
            return self._search(search_field, search_value)
        raise ValueError("pass symbol=, hgnc_id=, or search_field=+search_value= to hgnc.get()")

    def _fetch(self, field: str, value: str) -> pl.DataFrame:
        key = {"kind": "fetch", "field": field, "value": value}
        cached = self.ctx.cache.get_query("hgnc", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/fetch/{field}/{value}"
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="hgnc")
        data = resp.json()
        docs = _extract_docs(data, url)
        df = records_to_df([_flatten(d) for d in docs], db="hgnc")
        if df.height == 0:
            raise ParseError("hgnc", f"no documents returned for {field}={value!r}")
        self.ctx.cache.put_query("hgnc", key, df, url=str(resp.request.url))
        return df

    def _search(self, field: str, value: str) -> pl.DataFrame:
        key = {"kind": "search", "field": field, "value": value}
        cached = self.ctx.cache.get_query("hgnc", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/search/{field}/{value}"
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="hgnc")
        data = resp.json()
        docs = _extract_docs(data, url)
        df = records_to_df([_flatten(d) for d in docs], db="hgnc")
        if df.height == 0:
            raise ParseError("hgnc", f"no results for search {field}={value!r}")
        self.ctx.cache.put_query("hgnc", key, df, url=str(resp.request.url))
        return df


def _extract_docs(data: Any, url: str) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        raise ParseError("hgnc", f"expected dict from {url}, got {type(data).__name__}")
    response = data.get("response") or {}
    docs = response.get("docs")
    if not isinstance(docs, list):
        raise ParseError("hgnc", f"expected list under response.docs, got {type(docs).__name__}")
    return docs
