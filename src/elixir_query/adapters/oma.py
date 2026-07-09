"""OMA (Orthologous Matrix) adapter.

Docs: https://omabrowser.org/api/docs
Notes: docs/adapter-notes/oma.md (consulted 2026-05-03).

REST base: https://omabrowser.org/api
  - /protein/{entry_id}/                -> single protein
  - /protein/{entry_id}/orthologs/      -> pairwise orthologs (paginated)
  - /protein/{entry_id}/hog/            -> hierarchical orthologous group
  - /genome/{taxon_id}/                 -> genome metadata
  - /hog/{hog_id}/members/              -> members of a HOG
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
_TTL_QUERY_SECONDS = 7 * 24 * 3600


def _flatten(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {"value": _json.dumps(d)}
    return {k: (_json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in d.items()}


@register
class OMAAdapter(BaseAdapter):
    """OMA orthology REST adapter."""

    meta = AdapterMeta(
        name="oma",
        aliases=("oma_browser", "orthologous_matrix"),
        homepage="https://omabrowser.org",
        citation=(
            "Altenhoff AM, et al. The OMA orthology database in 2024. "
            "Nucleic Acids Res. 52:D513–D520 (2024)."
        ),
        supports_bulk=False,
        example_params={"protein": "YEAST00012"},
        description=(
            "OMA — Orthologous Matrix. Call with protein='YEAST00012' for a "
            "single protein, orthologs_for='YEAST00012' for pairwise orthologs, "
            "hog_for='YEAST00012' for the protein's HOG, hog_members='HOG:E0001' "
            "for HOG members, or genome='559292' for genome metadata."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        protein: str | None = None,
        orthologs_for: str | None = None,
        hog_for: str | None = None,
        hog_members: str | None = None,
        genome: str | int | None = None,
        rel_type: str | None = None,
        limit: int | None = 100,
        page_size: int = 100,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch OMA records.

        Args:
            protein: OMA entry ID (e.g. ``"YEAST00012"``), UniProt accession
                (e.g. ``"P04637"``), or canonical ID — single-record lookup.
            orthologs_for: Same identifier types as ``protein``; returns
                pairwise orthologs (paginated).
            hog_for: Same identifier types; returns the protein's HOG.
            hog_members: HOG ID (e.g. ``"HOG:E0001"``); returns its members.
            genome: NCBI taxon ID for a genome lookup.
            rel_type: Filter orthologs by relation type (``"1:1"``, ``"1:n"``,
                ``"m:1"``, ``"m:n"``).
            limit: Row cap for paginated queries.
            page_size: Server-side page size.
        """
        if not any([protein, orthologs_for, hog_for, hog_members, genome]):
            raise ValueError(
                "pass protein=, orthologs_for=, hog_for=, hog_members=, or genome="
            )

        # ---- single protein ----
        if protein is not None:
            return self._single(
                f"{_BASE}/protein/{protein}/", {"kind": "protein", "id": protein}
            )

        # ---- pairwise orthologs ----
        if orthologs_for is not None:
            params: dict[str, Any] = {"per_page": page_size}
            if rel_type:
                params["rel_type"] = rel_type
            return self._paginated(
                url=f"{_BASE}/protein/{orthologs_for}/orthologs/",
                key={
                    "kind": "orthologs",
                    "id": orthologs_for,
                    "rel_type": rel_type,
                    "limit": limit,
                },
                params=params,
                limit=limit,
            )

        # ---- HOG for a protein ----
        if hog_for is not None:
            return self._single(
                f"{_BASE}/protein/{hog_for}/hog/", {"kind": "hog", "id": hog_for}
            )

        # ---- HOG members ----
        if hog_members is not None:
            return self._paginated(
                url=f"{_BASE}/hog/{hog_members}/members/",
                key={"kind": "hog_members", "id": hog_members, "limit": limit},
                params={"per_page": page_size},
                limit=limit,
            )

        # ---- genome ----
        assert genome is not None
        return self._single(
            f"{_BASE}/genome/{genome}/", {"kind": "genome", "id": str(genome)}
        )

    def _single(self, url: str, key: dict[str, Any]) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("oma", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        resp = self.ctx.http.get(url, db="oma")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("oma", f"expected dict, got {type(data).__name__}")
        df = records_to_df([_flatten(data)], db="oma")
        if df.height == 0:
            raise ParseError("oma", f"empty result from {url}")
        self.ctx.cache.put_query("oma", key, df, url=str(resp.request.url))
        return df

    def _paginated(
        self,
        *,
        url: str,
        key: dict[str, Any],
        params: dict[str, Any],
        limit: int | None,
    ) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("oma", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        rows: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params: dict[str, Any] | None = dict(params)
        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, db="oma")
            data = resp.json()
            # OMA's list endpoints sometimes return a bare list, sometimes
            # the DRF envelope. Handle both.
            if isinstance(data, list):
                results = data
                next_url = None
            elif isinstance(data, dict):
                results = data.get("results")
                if results is None and "data" in data:
                    results = data.get("data")
                next_url = data.get("next")
            else:
                raise ParseError("oma", f"unexpected response: {type(data).__name__}")
            if not isinstance(results, list):
                raise ParseError("oma", f"results not a list: {type(results).__name__}")
            for r in results:
                rows.append(_flatten(r))
                if limit is not None and len(rows) >= limit:
                    break
            if limit is not None and len(rows) >= limit:
                break
            next_params = None
        if not rows:
            raise ParseError("oma", f"no rows returned from {url}")
        df = records_to_df(rows, db="oma")
        self.ctx.cache.put_query("oma", key, df, url=url)
        return df
