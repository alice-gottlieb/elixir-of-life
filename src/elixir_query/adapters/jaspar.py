"""JASPAR adapter (transcription-factor binding profiles).

Docs: https://jaspar.genereg.net/api/v1/docs/
Notes: docs/adapter-notes/jaspar.md (consulted 2026-05-03).

REST base: https://jaspar.genereg.net/api/v1
  - /matrix/{matrix_id}/?format=json   -> single binding profile
  - /matrix/?format=json                -> paginated list of all matrices
  - /species/?format=json
  - /collections/?format=json
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://jaspar.genereg.net/api/v1"
_TTL_QUERY_SECONDS = 7 * 24 * 3600


def _flatten(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {"value": _json.dumps(d)}
    return {k: (_json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in d.items()}


@register
class JASPARAdapter(BaseAdapter):
    """JASPAR transcription-factor binding profiles REST adapter."""

    meta = AdapterMeta(
        name="jaspar",
        aliases=("jaspar_db",),
        homepage="https://jaspar.genereg.net",
        citation=(
            "Rauluseviciute I, et al. JASPAR 2024: 20th anniversary of the open-access "
            "database of transcription factor binding profiles. "
            "Nucleic Acids Res. 52:D174–D182 (2024)."
        ),
        supports_bulk=True,
        example_params={"matrix_id": "MA0002.1"},
        description=(
            "JASPAR — transcription factor binding profiles. Call with "
            "matrix_id='MA0002.1' for RUNX1, list_matrices=True for a "
            "filtered list (use tax_group='vertebrates', collection='CORE'), "
            "or list_species=True / list_collections=True for metadata."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        matrix_id: str | None = None,
        list_matrices: bool = False,
        tax_group: str | None = None,
        collection: str | None = None,
        list_species: bool = False,
        list_collections: bool = False,
        limit: int | None = 100,
        page_size: int = 100,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch JASPAR records.

        Args:
            matrix_id: Profile ID (e.g. ``"MA0002.1"`` for RUNX1).
            list_matrices: List matrices (paginated). Combine with ``tax_group``
                (e.g. ``"vertebrates"``, ``"plants"``) and/or ``collection``
                (e.g. ``"CORE"``) to filter.
            list_species: List all species in JASPAR.
            list_collections: List all collections.
            limit: Row cap for list queries.
            page_size: Server-side page size.
        """
        if not any([matrix_id, list_matrices, list_species, list_collections]):
            raise ValueError(
                "pass matrix_id=..., list_matrices=True, list_species=True, "
                "or list_collections=True"
            )

        # ---- single matrix ----
        if matrix_id is not None:
            key = {"kind": "matrix", "matrix_id": matrix_id}
            cached = self.ctx.cache.get_query("jaspar", key, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = f"{_BASE}/matrix/{matrix_id}/"
            resp = self.ctx.http.get(url, params={"format": "json"}, db="jaspar")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("jaspar", f"expected dict for matrix, got {type(data).__name__}")
            df = records_to_df([_flatten(data)], db="jaspar")
            if df.height == 0:
                raise ParseError("jaspar", f"no record for matrix_id={matrix_id!r}")
            self.ctx.cache.put_query("jaspar", key, df, url=str(resp.request.url))
            return df

        # ---- list matrices (paginated, with optional filters) ----
        if list_matrices:
            params: dict[str, Any] = {"format": "json", "page_size": page_size}
            if tax_group:
                params["tax_group"] = tax_group
            if collection:
                params["collection"] = collection
            return self._paginated(
                url=f"{_BASE}/matrix/",
                key={
                    "kind": "matrices",
                    "tax_group": tax_group,
                    "collection": collection,
                    "limit": limit,
                },
                params=params,
                limit=limit,
            )

        # ---- list species ----
        if list_species:
            return self._paginated(
                url=f"{_BASE}/species/",
                key={"kind": "species", "limit": limit},
                params={"format": "json", "page_size": page_size},
                limit=limit,
            )

        # ---- list collections ----
        assert list_collections
        return self._paginated(
            url=f"{_BASE}/collections/",
            key={"kind": "collections", "limit": limit},
            params={"format": "json", "page_size": page_size},
            limit=limit,
        )

    def _paginated(
        self,
        *,
        url: str,
        key: dict[str, Any],
        params: dict[str, Any],
        limit: int | None,
    ) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("jaspar", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        rows: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params: dict[str, Any] | None = dict(params)
        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, db="jaspar")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("jaspar", f"unexpected response: {type(data).__name__}")
            results = data.get("results") or []
            for r in results:
                rows.append(_flatten(r))
                if limit is not None and len(rows) >= limit:
                    break
            if limit is not None and len(rows) >= limit:
                break
            next_url = data.get("next")
            next_params = None
        if not rows:
            raise ParseError("jaspar", f"no rows returned from {url}")
        df = records_to_df(rows, db="jaspar")
        self.ctx.cache.put_query("jaspar", key, df, url=url)
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(
        self,
        *,
        tax_group: str = "vertebrates",
        collection: str = "CORE",
        **_: Any,
    ) -> pl.LazyFrame:
        """Page all matrices for a tax group + collection into Parquet.

        Default fetches all vertebrate CORE matrices (~600 profiles).
        """
        key = {"kind": "all_matrices", "tax_group": tax_group, "collection": collection}
        parquet = self.ctx.cache.bulk_ready("jaspar", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        rows: list[dict[str, Any]] = []
        next_url: str | None = f"{_BASE}/matrix/"
        next_params: dict[str, Any] | None = {
            "format": "json",
            "page_size": 100,
            "tax_group": tax_group,
            "collection": collection,
        }
        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, db="jaspar")
            data = resp.json()
            for r in data.get("results") or []:
                rows.append(_flatten(r))
            next_url = data.get("next")
            next_params = None
        if not rows:
            raise ParseError("jaspar", f"bulk for {tax_group}/{collection} returned no rows")
        df = records_to_df(rows, db="jaspar")
        raw, parquet_path, _meta = self.ctx.cache.bulk_paths("jaspar", key)
        df.write_parquet(parquet_path)
        df.write_csv(raw.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "jaspar",
            key,
            url=f"{_BASE}/matrix/?tax_group={tax_group}&collection={collection}",
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
