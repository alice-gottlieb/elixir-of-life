"""ChEMBL adapter (bioactive molecules).

Docs: https://www.ebi.ac.uk/chembl/api/data/docs
Notes: docs/adapter-notes/chembl.md (consulted 2026-04-27).

REST base: https://www.ebi.ac.uk/chembl/api/data
  - /molecule/{chembl_id}.json     -> single molecule
  - /molecule.json?<filters>       -> filtered, paginated list
  - /target/{target_chembl_id}     -> single target
  - /activity.json?molecule_chembl_id={id}  -> bioactivities for a molecule
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://www.ebi.ac.uk/chembl/api/data"
_JSON_HEADERS = {"Accept": "application/json"}

_TTL_QUERY_SECONDS = 7 * 24 * 3600  # 7 days


def _flatten(d: dict[str, Any]) -> dict[str, Any]:
    """Flatten one level: nested dicts/lists become JSON strings."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            out[k] = _json.dumps(v)
        else:
            out[k] = v
    return out


@register
class ChEMBLAdapter(BaseAdapter):
    """ChEMBL bioactive-molecule REST API adapter."""

    meta = AdapterMeta(
        name="chembl",
        aliases=("chemblid",),
        homepage="https://www.ebi.ac.uk/chembl/",
        citation=(
            "Zdrazil B, et al. The ChEMBL Database in 2023. "
            "Nucleic Acids Res. 51:D1180–D1192 (2023)."
        ),
        supports_bulk=False,
        example_params={"molecule_chembl_id": "CHEMBL25"},
        description=(
            "ChEMBL — manually curated database of bioactive molecules with "
            "drug-like properties. Call with molecule_chembl_id='CHEMBL25' "
            "for aspirin, target_chembl_id='CHEMBL204' for a target, or "
            "filters={'pref_name__icontains':'ibuprofen'} for a list query."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        molecule_chembl_id: str | None = None,
        target_chembl_id: str | None = None,
        activities_for: str | None = None,
        filters: dict[str, Any] | None = None,
        resource: str = "molecule",
        limit: int | None = None,
        page_size: int = 200,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch ChEMBL records.

        Args:
            molecule_chembl_id: Single molecule lookup (e.g. ``"CHEMBL25"``).
            target_chembl_id: Single target lookup (e.g. ``"CHEMBL204"``).
            activities_for: Molecule ChEMBL ID to fetch its bioactivities.
            filters: Mapping of filter-field -> value. Common ChEMBL field
                lookups include ``pref_name__icontains``, ``molecule_type``,
                ``max_phase``, ``molecule_chembl_id__in`` (comma-joined).
            resource: Resource name when using ``filters`` (default ``"molecule"``).
            limit: Stop after ``limit`` rows (across pages).
            page_size: Server-side page size (max 1000).
        """
        if not any([molecule_chembl_id, target_chembl_id, activities_for, filters]):
            raise ValueError(
                "pass molecule_chembl_id=, target_chembl_id=, activities_for=, or filters=..."
            )

        # ---------- single-molecule lookup ----------
        if molecule_chembl_id is not None:
            params_key = {"kind": "molecule", "id": molecule_chembl_id}
            cached = self.ctx.cache.get_query("chembl", params_key, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = f"{_BASE}/molecule/{molecule_chembl_id}.json"
            resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="chembl")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("chembl", f"expected dict from /molecule/, got {type(data).__name__}")
            df = records_to_df([_flatten(data)], db="chembl")
            if df.height == 0:
                raise ParseError("chembl", f"no record returned for molecule {molecule_chembl_id!r}")
            self.ctx.cache.put_query("chembl", params_key, df, url=str(resp.request.url))
            return df

        # ---------- single-target lookup ----------
        if target_chembl_id is not None:
            params_key = {"kind": "target", "id": target_chembl_id}
            cached = self.ctx.cache.get_query("chembl", params_key, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = f"{_BASE}/target/{target_chembl_id}.json"
            resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="chembl")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("chembl", f"expected dict from /target/, got {type(data).__name__}")
            df = records_to_df([_flatten(data)], db="chembl")
            if df.height == 0:
                raise ParseError("chembl", f"no record returned for target {target_chembl_id!r}")
            self.ctx.cache.put_query("chembl", params_key, df, url=str(resp.request.url))
            return df

        # ---------- activities for a molecule ----------
        if activities_for is not None:
            return self._paginated(
                resource="activity",
                key={"kind": "activity", "molecule": activities_for},
                params={"molecule_chembl_id": activities_for, "limit": page_size},
                limit=limit,
            )

        # ---------- filtered list ----------
        assert filters is not None
        params: dict[str, Any] = {**filters, "limit": page_size}
        return self._paginated(
            resource=resource,
            key={"kind": resource, **filters, "limit": limit},
            params=params,
            limit=limit,
        )

    # -------------------------------------------------------------- helper
    def _paginated(
        self,
        *,
        resource: str,
        key: dict[str, Any],
        params: dict[str, Any],
        limit: int | None,
    ) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("chembl", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        url: str | None = f"{_BASE}/{resource}.json"
        next_params: dict[str, Any] | None = dict(params)
        while url:
            resp = self.ctx.http.get(url, params=next_params, headers=_JSON_HEADERS, db="chembl")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("chembl", f"expected paginated dict, got {type(data).__name__}")
            page_records = data.get(resource) or data.get(resource + "s") or []
            if not isinstance(page_records, list):
                raise ParseError("chembl", f"expected list under '{resource}', got {type(page_records).__name__}")
            for r in page_records:
                rows.append(_flatten(r) if isinstance(r, dict) else {"value": r})
                if limit is not None and len(rows) >= limit:
                    break
            if limit is not None and len(rows) >= limit:
                break
            page_meta = data.get("page_meta") or {}
            next_path = page_meta.get("next")
            if not next_path:
                break
            # next is a path like "/chembl/api/data/molecule.json?..."
            url = "https://www.ebi.ac.uk" + next_path if next_path.startswith("/") else next_path
            next_params = None  # full URL already has params

        if not rows:
            raise ParseError("chembl", f"no rows returned for {resource} with params {params!r}")
        df = records_to_df(rows, db="chembl")
        self.ctx.cache.put_query("chembl", key, df, url=f"{_BASE}/{resource}.json")
        return df
