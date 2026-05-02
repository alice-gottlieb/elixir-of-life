"""InterPro adapter (protein families and domains).

Docs: https://www.ebi.ac.uk/interpro/
Notes: docs/adapter-notes/interpro.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/interpro/api
  - /entry/interpro/{accession}/  -> single entry
  - /entry/interpro/protein/uniprot/{accession}/  -> entries for a protein
  - /entry/interpro/?format=json  -> paginated list (cursor next-link)
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://www.ebi.ac.uk/interpro/api"
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
class InterProAdapter(BaseAdapter):
    """InterPro protein families and domains REST adapter."""

    meta = AdapterMeta(
        name="interpro",
        aliases=("interpro7",),
        homepage="https://www.ebi.ac.uk/interpro/",
        citation=(
            "Blum M, et al. The InterPro protein families and domains database: "
            "20 years on. Nucleic Acids Res. 49:D344–D354 (2021)."
        ),
        supports_bulk=False,
        example_params={"accession": "IPR000001"},
        description=(
            "InterPro — protein families, domains and functional sites. "
            "Call with accession='IPR000001' for a single entry, "
            "protein='P00533' to list entries matching a UniProt protein, "
            "or list_all=True to page through all InterPro entries."
        ),
    )

    def query(
        self,
        *,
        accession: str | None = None,
        protein: str | None = None,
        list_all: bool = False,
        limit: int | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch InterPro entries.

        Args:
            accession: InterPro accession (e.g. ``"IPR000001"``).
            protein: UniProt accession — returns all InterPro entries
                matching that protein.
            list_all: Page through all InterPro entries (large; use limit).
            limit: Stop after this many rows when using protein= or list_all=.
        """
        if accession is not None:
            return self._single(accession)

        if protein is not None:
            url = f"{_BASE}/entry/interpro/protein/uniprot/{protein}/"
            key = {"kind": "protein_entries", "protein": protein, "limit": limit}
            return self._paginated(url, key, limit=limit)

        if list_all:
            url = f"{_BASE}/entry/interpro/"
            key = {"kind": "list_all", "limit": limit}
            return self._paginated(url, key, limit=limit)

        raise ValueError("pass accession=, protein=, or list_all=True to interpro.get()")

    def _single(self, accession: str) -> pl.DataFrame:
        key = {"kind": "entry", "accession": accession}
        cached = self.ctx.cache.get_query("interpro", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/entry/interpro/{accession}/"
        params = {"format": "json"}
        resp = self.ctx.http.get(url, params=params, headers=_JSON_HEADERS, db="interpro")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("interpro", f"expected dict for {accession}, got {type(data).__name__}")
        df = records_to_df([_flatten(data)], db="interpro")
        if df.height == 0:
            raise ParseError("interpro", f"no data returned for accession {accession!r}")
        self.ctx.cache.put_query("interpro", key, df, url=str(resp.request.url))
        return df

    def _paginated(self, start_url: str, key: dict[str, Any], limit: int | None) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("interpro", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        next_url: str | None = start_url
        next_params: dict[str, Any] | None = {"format": "json"}

        while next_url:
            resp = self.ctx.http.get(
                next_url, params=next_params, headers=_JSON_HEADERS, db="interpro"
            )
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("interpro", f"expected dict, got {type(data).__name__}")

            results = data.get("results")
            if not isinstance(results, list):
                raise ParseError("interpro", f"expected list under 'results', got {type(results).__name__}")

            for r in results:
                rows.append(_flatten(r) if isinstance(r, dict) else {"raw": r})
                if limit is not None and len(rows) >= limit:
                    break

            if limit is not None and len(rows) >= limit:
                break

            next_url = data.get("next")
            next_params = None  # next URL already carries params

        if not rows:
            raise ParseError("interpro", f"no results returned from {start_url!r}")

        df = records_to_df(rows, db="interpro")
        if limit is not None:
            df = df.head(limit)
        self.ctx.cache.put_query("interpro", key, df, url=start_url)
        return df
