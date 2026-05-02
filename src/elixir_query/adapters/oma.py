"""OMA (Orthologous MAtrix) browser adapter.

Docs: https://omabrowser.org/api/docs
Notes: docs/adapter-notes/oma.md (consulted 2026-05-02).

REST base: https://omabrowser.org/api
  - /protein/{entry_id}/          -> protein metadata
  - /protein/{entry_id}/orthologs/ -> pairwise orthologs
  - /group/{oma_group_id}/        -> OMA group
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://omabrowser.org/api"
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
class OMAAdapter(BaseAdapter):
    """OMA (Orthologous MAtrix) browser REST adapter."""

    meta = AdapterMeta(
        name="oma",
        aliases=("omabrowser", "oma_browser"),
        homepage="https://omabrowser.org",
        citation=(
            "Altenhoff AM, et al. OMA orthology in 2021: website overhaul, "
            "conserved isoforms, ancestral gene order and more. "
            "Nucleic Acids Res. 49:D373–D379 (2021)."
        ),
        supports_bulk=False,
        example_params={"protein": "P00533"},
        description=(
            "OMA — Orthologous MAtrix pairwise and hierarchical orthology inference. "
            "Call with protein='P00533' for EGFR metadata, "
            "orthologs='P00533' for its pairwise orthologs, or "
            "group_id=... for an OMA group."
        ),
    )

    def query(
        self,
        *,
        protein: str | None = None,
        orthologs: str | None = None,
        group_id: str | int | None = None,
        limit: int | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch OMA data.

        Args:
            protein: OMA ID (e.g. ``"HUMAN17133"``) or UniProt accession
                (e.g. ``"P00533"``).  Returns protein metadata.
            orthologs: Same identifiers — returns pairwise orthologs.
            group_id: OMA group number or string ID.
            limit: Stop after this many rows for list endpoints.
        """
        if protein is not None:
            return self._protein(protein)
        if orthologs is not None:
            return self._orthologs(orthologs, limit=limit)
        if group_id is not None:
            return self._group(str(group_id))
        raise ValueError("pass protein=, orthologs=, or group_id=... to oma.get()")

    def _protein(self, entry_id: str) -> pl.DataFrame:
        key = {"kind": "protein", "id": entry_id}
        cached = self.ctx.cache.get_query("oma", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/protein/{entry_id}/"
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="oma")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("oma", f"expected dict for {entry_id}, got {type(data).__name__}")
        df = records_to_df([_flatten(data)], db="oma")
        if df.height == 0:
            raise ParseError("oma", f"empty response for protein {entry_id!r}")
        self.ctx.cache.put_query("oma", key, df, url=str(resp.request.url))
        return df

    def _orthologs(self, entry_id: str, *, limit: int | None) -> pl.DataFrame:
        key = {"kind": "orthologs", "id": entry_id, "limit": limit}
        cached = self.ctx.cache.get_query("oma", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        page = 1
        per_page = 100
        url = f"{_BASE}/protein/{entry_id}/orthologs/"

        while True:
            params: dict[str, Any] = {"page": page, "per_page": per_page}
            resp = self.ctx.http.get(url, params=params, headers=_JSON_HEADERS, db="oma")
            data = resp.json()

            if isinstance(data, list):
                page_rows = data
            elif isinstance(data, dict) and "results" in data:
                page_rows = data["results"]
            elif isinstance(data, dict):
                page_rows = [data]
            else:
                raise ParseError("oma", f"unexpected response type: {type(data).__name__}")

            for r in page_rows:
                rows.append(_flatten(r) if isinstance(r, dict) else {"entry": r})
                if limit is not None and len(rows) >= limit:
                    break

            if limit is not None and len(rows) >= limit:
                break
            if len(page_rows) < per_page:
                break
            page += 1

        if not rows:
            raise ParseError("oma", f"no orthologs returned for {entry_id!r}")

        df = records_to_df(rows, db="oma")
        if limit is not None:
            df = df.head(limit)
        self.ctx.cache.put_query("oma", key, df, url=url)
        return df

    def _group(self, group_id: str) -> pl.DataFrame:
        key = {"kind": "group", "id": group_id}
        cached = self.ctx.cache.get_query("oma", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/group/{group_id}/"
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="oma")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("oma", f"expected dict for group {group_id}, got {type(data).__name__}")
        df = records_to_df([_flatten(data)], db="oma")
        if df.height == 0:
            raise ParseError("oma", f"empty response for group {group_id!r}")
        self.ctx.cache.put_query("oma", key, df, url=str(resp.request.url))
        return df
