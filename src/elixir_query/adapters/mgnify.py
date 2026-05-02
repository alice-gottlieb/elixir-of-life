"""MGnify (metagenomics) adapter.

Docs: https://docs.mgnify.org/src/docs/api.html
Notes: docs/adapter-notes/mgnify.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/metagenomics/api/v1
  - JSON:API format; data.attributes contains actual fields
  - pagination via links.next
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://www.ebi.ac.uk/metagenomics/api/v1"
_JSONAPI_HEADERS = {"Accept": "application/vnd.api+json"}
_TTL = 7 * 24 * 3600  # 7 days


def _jsonapi_to_flat(obj: dict[str, Any]) -> dict[str, Any]:
    """Flatten a JSON:API resource object: combine id + type + attributes."""
    flat: dict[str, Any] = {"id": obj.get("id"), "type": obj.get("type")}
    attrs = obj.get("attributes") or {}
    for k, v in attrs.items():
        if isinstance(v, (dict, list)):
            flat[k] = _json.dumps(v)
        else:
            flat[k] = v
    return flat


@register
class MGnifyAdapter(BaseAdapter):
    """MGnify metagenomics data REST adapter (JSON:API)."""

    meta = AdapterMeta(
        name="mgnify",
        aliases=("metagenomics_ebi", "emg"),
        homepage="https://www.ebi.ac.uk/metagenomics/",
        citation=(
            "Richardson L, et al. MGnify: the microbiome sequence data analysis "
            "resource in 2023. Nucleic Acids Res. 51:D753–D759 (2023)."
        ),
        supports_bulk=False,
        example_params={"study_accession": "MGYS00001598"},
        description=(
            "MGnify — microbiome / metagenomics database. Call with "
            "study_accession='MGYS00001598' for a single study, "
            "sample_accession='ERS487899' for a sample, or list_studies=True."
        ),
    )

    def query(
        self,
        *,
        study_accession: str | None = None,
        sample_accession: str | None = None,
        runs_for: str | None = None,
        list_studies: bool = False,
        limit: int | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch MGnify records.

        Args:
            study_accession: MGnify study accession (e.g. ``"MGYS00001598"``).
            sample_accession: MGnify / ENA sample accession.
            runs_for: Study accession to list associated runs.
            list_studies: Retrieve the first page(s) of public studies.
            limit: Stop after this many rows for list queries.
        """
        if study_accession is not None:
            return self._single("studies", study_accession)
        if sample_accession is not None:
            return self._single("samples", sample_accession)
        if runs_for is not None:
            url = f"{_BASE}/runs"
            key = {"kind": "runs", "study": runs_for, "limit": limit}
            return self._paginated(url, params={"study_accession": runs_for}, key=key, limit=limit)
        if list_studies:
            url = f"{_BASE}/studies"
            key = {"kind": "list_studies", "limit": limit}
            return self._paginated(url, params={}, key=key, limit=limit)
        raise ValueError(
            "pass study_accession=, sample_accession=, runs_for=, or list_studies=True to mgnify.get()"
        )

    def _single(self, resource: str, accession: str) -> pl.DataFrame:
        key = {"kind": resource, "accession": accession}
        cached = self.ctx.cache.get_query("mgnify", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/{resource}/{accession}"
        resp = self.ctx.http.get(url, headers=_JSONAPI_HEADERS, db="mgnify")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("mgnify", f"expected dict for {accession}, got {type(data).__name__}")

        obj = data.get("data")
        if isinstance(obj, list) and obj:
            rows = [_jsonapi_to_flat(r) for r in obj]
        elif isinstance(obj, dict):
            rows = [_jsonapi_to_flat(obj)]
        else:
            raise ParseError("mgnify", f"no 'data' object in response for {accession!r}")

        df = records_to_df(rows, db="mgnify")
        if df.height == 0:
            raise ParseError("mgnify", f"empty response for {resource}/{accession}")
        self.ctx.cache.put_query("mgnify", key, df, url=str(resp.request.url))
        return df

    def _paginated(
        self, start_url: str, *, params: dict[str, Any], key: dict[str, Any], limit: int | None
    ) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("mgnify", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        next_url: str | None = start_url
        next_params: dict[str, Any] | None = dict(params)

        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, headers=_JSONAPI_HEADERS, db="mgnify")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("mgnify", f"expected dict, got {type(data).__name__}")

            objects = data.get("data") or []
            if not isinstance(objects, list):
                raise ParseError("mgnify", f"expected list under 'data', got {type(objects).__name__}")

            for obj in objects:
                rows.append(_jsonapi_to_flat(obj) if isinstance(obj, dict) else {"id": obj})
                if limit is not None and len(rows) >= limit:
                    break

            if limit is not None and len(rows) >= limit:
                break

            links = data.get("links") or {}
            next_url = links.get("next")
            next_params = None

        if not rows:
            raise ParseError("mgnify", f"no records returned from {start_url!r}")

        df = records_to_df(rows, db="mgnify")
        if limit is not None:
            df = df.head(limit)
        self.ctx.cache.put_query("mgnify", key, df, url=start_url)
        return df
