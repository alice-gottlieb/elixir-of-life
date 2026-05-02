"""JASPAR adapter (transcription factor binding profiles).

Docs: https://jaspar.elixir.no/api/v1/docs/
Notes: docs/adapter-notes/jaspar.md (consulted 2026-05-02).

REST base: https://jaspar.elixir.no/api/v1
  - /matrix/{id}/          -> single TF profile
  - /matrix/?collection=..&page=1&page_size=50  -> paginated list
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://jaspar.elixir.no/api/v1"
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
class JASPARAdapter(BaseAdapter):
    """JASPAR TF binding profile REST adapter."""

    meta = AdapterMeta(
        name="jaspar",
        aliases=("jaspar_db",),
        homepage="https://jaspar.elixir.no",
        citation=(
            "Castro-Mondragon JA, et al. JASPAR 2022: the 9th release of the "
            "open-access database of transcription factor binding profiles. "
            "Nucleic Acids Res. 50:D165–D173 (2022)."
        ),
        supports_bulk=False,
        example_params={"matrix_id": "MA0139.1"},
        description=(
            "JASPAR — open-access database of transcription factor binding profiles. "
            "Call with matrix_id='MA0139.1' for CTCF, or "
            "collection='CORE', tax_group='vertebrates' to browse."
        ),
    )

    def query(
        self,
        *,
        matrix_id: str | None = None,
        collection: str | None = None,
        tax_group: str | None = None,
        name: str | None = None,
        page_size: int = 50,
        limit: int | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch JASPAR matrix profiles.

        Args:
            matrix_id: JASPAR matrix ID (e.g. ``"MA0139.1"``).
            collection: Filter by collection (e.g. ``"CORE"``, ``"UNVALIDATED"``).
            tax_group: Filter by taxonomy group (e.g. ``"vertebrates"``).
            name: Filter by TF name substring.
            page_size: Results per page.
            limit: Stop after this many rows when browsing.
        """
        if matrix_id is not None:
            return self._single(matrix_id)
        if any(x is not None for x in (collection, tax_group, name)):
            return self._browse(
                collection=collection, tax_group=tax_group, name=name,
                page_size=page_size, limit=limit
            )
        raise ValueError(
            "pass matrix_id=, or at least one of collection=, tax_group=, name= to jaspar.get()"
        )

    def _single(self, matrix_id: str) -> pl.DataFrame:
        key = {"kind": "matrix", "id": matrix_id}
        cached = self.ctx.cache.get_query("jaspar", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/matrix/{matrix_id}/"
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="jaspar")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("jaspar", f"expected dict for {matrix_id}, got {type(data).__name__}")
        df = records_to_df([_flatten(data)], db="jaspar")
        if df.height == 0:
            raise ParseError("jaspar", f"empty response for matrix {matrix_id!r}")
        self.ctx.cache.put_query("jaspar", key, df, url=str(resp.request.url))
        return df

    def _browse(
        self,
        *,
        collection: str | None,
        tax_group: str | None,
        name: str | None,
        page_size: int,
        limit: int | None,
    ) -> pl.DataFrame:
        params: dict[str, Any] = {"page_size": page_size}
        if collection:
            params["collection"] = collection
        if tax_group:
            params["tax_group"] = tax_group
        if name:
            params["name"] = name

        key = {"kind": "browse", **params, "limit": limit}
        cached = self.ctx.cache.get_query("jaspar", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        next_url: str | None = f"{_BASE}/matrix/"
        next_params: dict[str, Any] | None = dict(params)

        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, headers=_JSON_HEADERS, db="jaspar")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("jaspar", f"expected dict, got {type(data).__name__}")

            results = data.get("results") or []
            for r in results:
                rows.append(_flatten(r) if isinstance(r, dict) else {"raw": r})
                if limit is not None and len(rows) >= limit:
                    break

            if limit is not None and len(rows) >= limit:
                break

            next_url = data.get("next")
            next_params = None

        if not rows:
            raise ParseError("jaspar", f"no matrices returned for params {params!r}")

        df = records_to_df(rows, db="jaspar")
        if limit is not None:
            df = df.head(limit)
        self.ctx.cache.put_query("jaspar", key, df, url=f"{_BASE}/matrix/")
        return df
