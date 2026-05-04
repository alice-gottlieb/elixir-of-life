"""MGnify adapter (microbiome sequence analysis).

Docs: https://www.ebi.ac.uk/metagenomics/api/docs/
Notes: docs/adapter-notes/mgnify.md (consulted 2026-05-03).

REST base: https://www.ebi.ac.uk/metagenomics/api/latest
  - /studies/{accession}        -> single study (JSON:API)
  - /studies                    -> paginated list of all studies
  - /studies/{accession}/samples -> samples for a study
  - /samples/{accession}        -> single sample
  - /runs/{accession}           -> single run
  - /biomes/{lineage}           -> biome metadata
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://www.ebi.ac.uk/metagenomics/api/latest"
_JSON_HEADERS = {"Accept": "application/json"}
_TTL_QUERY_SECONDS = 7 * 24 * 3600

_VALID_RESOURCES = ("studies", "samples", "runs", "biomes", "experiment-types")


def _flatten_jsonapi(record: Any) -> dict[str, Any]:
    """Flatten a JSON:API resource dict (`{type, id, attributes}`) into a flat row."""
    if not isinstance(record, dict):
        return {"value": _json.dumps(record)}
    row: dict[str, Any] = {
        "type": record.get("type"),
        "id": record.get("id"),
    }
    attrs = record.get("attributes") or {}
    if isinstance(attrs, dict):
        for k, v in attrs.items():
            row[k] = _json.dumps(v) if isinstance(v, (dict, list)) else v
    return row


@register
class MGnifyAdapter(BaseAdapter):
    """MGnify microbiome sequence resource REST adapter (JSON:API)."""

    meta = AdapterMeta(
        name="mgnify",
        aliases=("ebi_metagenomics", "metagenomics"),
        homepage="https://www.ebi.ac.uk/metagenomics/",
        citation=(
            "Richardson L, et al. MGnify: the microbiome sequence data analysis "
            "resource in 2023. Nucleic Acids Res. 51:D753–D759 (2023)."
        ),
        supports_bulk=False,
        example_params={"resource": "studies", "accession": "ERP009004"},
        description=(
            "MGnify — microbiome sequence data analysis. Call with "
            "resource='studies' (or 'samples'/'runs'/'biomes') + accession='...' "
            "for single records, samples_for='ERP009004' for sub-resources, "
            "or list_resource='studies' to page the full list."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        resource: str = "studies",
        accession: str | None = None,
        samples_for: str | None = None,
        list_resource: str | None = None,
        limit: int | None = 50,
        page_size: int = 50,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch MGnify records.

        Args:
            resource: One of ``"studies"``, ``"samples"``, ``"runs"``, ``"biomes"``,
                ``"experiment-types"``. Used together with ``accession`` for
                single-record lookup.
            accession: ENA-style or MGnify-style accession (e.g. ``"ERP009004"``).
            samples_for: Study accession; returns its samples list.
            list_resource: Resource to list (paginated). Mutually exclusive
                with ``accession`` and ``samples_for``.
            limit: Row cap for list/page queries.
            page_size: Server-side page size (default 50, max 250).
        """
        if resource not in _VALID_RESOURCES and list_resource is None and samples_for is None:
            raise ValueError(f"resource must be one of {_VALID_RESOURCES}, got {resource!r}")

        if accession is None and samples_for is None and list_resource is None:
            raise ValueError("pass accession=, samples_for=, or list_resource=")

        # ---- single record ----
        if accession is not None:
            key = {"kind": resource, "accession": accession}
            cached = self.ctx.cache.get_query("mgnify", key, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = f"{_BASE}/{resource}/{accession}"
            resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="mgnify")
            data = resp.json().get("data")
            if data is None:
                raise ParseError("mgnify", f"no 'data' in response for {url}")
            records = data if isinstance(data, list) else [data]
            df = records_to_df([_flatten_jsonapi(r) for r in records], db="mgnify")
            if df.height == 0:
                raise ParseError("mgnify", f"empty result for accession={accession!r}")
            self.ctx.cache.put_query("mgnify", key, df, url=str(resp.request.url))
            return df

        # ---- samples for a study ----
        if samples_for is not None:
            return self._paginated(
                url=f"{_BASE}/studies/{samples_for}/samples",
                key={"kind": "study_samples", "study": samples_for, "limit": limit},
                params={"page_size": page_size},
                limit=limit,
            )

        # ---- paginated list ----
        assert list_resource is not None
        if list_resource not in _VALID_RESOURCES:
            raise ValueError(
                f"list_resource must be one of {_VALID_RESOURCES}, got {list_resource!r}"
            )
        return self._paginated(
            url=f"{_BASE}/{list_resource}",
            key={"kind": "list", "resource": list_resource, "limit": limit},
            params={"page_size": page_size},
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
        cached = self.ctx.cache.get_query("mgnify", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        rows: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params: dict[str, Any] | None = dict(params)
        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, headers=_JSON_HEADERS, db="mgnify")
            payload = resp.json()
            data = payload.get("data") or []
            for r in data:
                rows.append(_flatten_jsonapi(r))
                if limit is not None and len(rows) >= limit:
                    break
            if limit is not None and len(rows) >= limit:
                break
            next_url = ((payload.get("links") or {}).get("next")) or None
            next_params = None
        if not rows:
            raise ParseError("mgnify", f"no rows returned from {url}")
        df = records_to_df(rows, db="mgnify")
        self.ctx.cache.put_query("mgnify", key, df, url=url)
        return df
