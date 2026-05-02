"""GWAS Catalog adapter (NHGRI-EBI GWAS Catalog).

Docs: https://www.ebi.ac.uk/gwas/rest/docs/api
Notes: docs/adapter-notes/gwas_catalog.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/gwas/rest/api
  - HAL JSON; pagination via _links.next.href
  - /studies/{accession}
  - /associations/search/findByStudyAccession?studyAccession={accession}
  - /singleNucleotidePolymorphisms/{rsid}
  - /singleNucleotidePolymorphisms/{rsid}/associations
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://www.ebi.ac.uk/gwas/rest/api"
_JSON_HEADERS = {"Accept": "application/json"}
_TTL = 7 * 24 * 3600  # 7 days


def _flatten(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if k == "_links":
            continue  # skip HAL navigation links
        if isinstance(v, (dict, list)):
            out[k] = _json.dumps(v)
        else:
            out[k] = v
    return out


@register
class GWASCatalogAdapter(BaseAdapter):
    """NHGRI-EBI GWAS Catalog REST adapter."""

    meta = AdapterMeta(
        name="gwas_catalog",
        aliases=("gwas", "nhgri_gwas"),
        homepage="https://www.ebi.ac.uk/gwas/",
        citation=(
            "Sollis E, et al. The NHGRI-EBI GWAS Catalog: knowledgebase and "
            "deposition resource. Nucleic Acids Res. 51:D977–D985 (2023)."
        ),
        supports_bulk=False,
        example_params={"rsid": "rs7903146"},
        description=(
            "GWAS Catalog — curated GWAS associations and studies. "
            "Call with rsid='rs7903146' for SNP metadata, "
            "study_accession='GCST000001' for a study, or "
            "associations_for='GCST000001' for all its associations."
        ),
    )

    def query(
        self,
        *,
        rsid: str | None = None,
        study_accession: str | None = None,
        associations_for: str | None = None,
        snp_associations: str | None = None,
        limit: int | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch GWAS Catalog data.

        Args:
            rsid: dbSNP rsID (e.g. ``"rs7903146"``).  Returns SNP metadata.
            study_accession: GWAS Catalog study accession (e.g. ``"GCST000001"``).
                Returns one row of study-level metadata.
            associations_for: Study accession — returns all its associations
                (paginated).
            snp_associations: rsID — returns all associations for that SNP.
            limit: Stop after this many rows for paginated results.
        """
        if rsid is not None:
            return self._snp(rsid)
        if study_accession is not None:
            return self._study(study_accession)
        if associations_for is not None:
            url = f"{_BASE}/associations/search/findByStudyAccession"
            key = {"kind": "assoc_study", "study": associations_for, "limit": limit}
            return self._paginated_embedded(
                url,
                params={"studyAccession": associations_for, "size": 100},
                embedded_key="associations",
                key=key,
                limit=limit,
            )
        if snp_associations is not None:
            url = f"{_BASE}/singleNucleotidePolymorphisms/{snp_associations}/associations"
            key = {"kind": "assoc_snp", "rsid": snp_associations, "limit": limit}
            return self._paginated_embedded(
                url,
                params={"size": 100},
                embedded_key="associations",
                key=key,
                limit=limit,
            )
        raise ValueError(
            "pass rsid=, study_accession=, associations_for=, or snp_associations= to gwas_catalog.get()"
        )

    def _snp(self, rsid: str) -> pl.DataFrame:
        key = {"kind": "snp", "rsid": rsid}
        cached = self.ctx.cache.get_query("gwas_catalog", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached
        url = f"{_BASE}/singleNucleotidePolymorphisms/{rsid}"
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="gwas_catalog")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("gwas_catalog", f"expected dict for SNP {rsid}, got {type(data).__name__}")
        df = records_to_df([_flatten(data)], db="gwas_catalog")
        if df.height == 0:
            raise ParseError("gwas_catalog", f"empty response for SNP {rsid!r}")
        self.ctx.cache.put_query("gwas_catalog", key, df, url=str(resp.request.url))
        return df

    def _study(self, accession: str) -> pl.DataFrame:
        key = {"kind": "study", "accession": accession}
        cached = self.ctx.cache.get_query("gwas_catalog", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached
        url = f"{_BASE}/studies/{accession}"
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="gwas_catalog")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("gwas_catalog", f"expected dict for study {accession}, got {type(data).__name__}")
        df = records_to_df([_flatten(data)], db="gwas_catalog")
        if df.height == 0:
            raise ParseError("gwas_catalog", f"empty response for study {accession!r}")
        self.ctx.cache.put_query("gwas_catalog", key, df, url=str(resp.request.url))
        return df

    def _paginated_embedded(
        self,
        start_url: str,
        *,
        params: dict[str, Any],
        embedded_key: str,
        key: dict[str, Any],
        limit: int | None,
    ) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("gwas_catalog", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        rows: list[dict[str, Any]] = []
        next_url: str | None = start_url
        next_params: dict[str, Any] | None = dict(params)

        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, headers=_JSON_HEADERS, db="gwas_catalog")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("gwas_catalog", f"expected dict, got {type(data).__name__}")

            embedded = data.get("_embedded") or {}
            records = embedded.get(embedded_key) or []
            if not isinstance(records, list):
                raise ParseError("gwas_catalog", f"expected list under _embedded.{embedded_key}")

            for r in records:
                rows.append(_flatten(r) if isinstance(r, dict) else {"value": r})
                if limit is not None and len(rows) >= limit:
                    break

            if limit is not None and len(rows) >= limit:
                break

            links = data.get("_links") or {}
            next_link = links.get("next")
            if next_link and isinstance(next_link, dict):
                next_url = next_link.get("href")
            else:
                next_url = None
            next_params = None  # href already carries params

        if not rows:
            raise ParseError("gwas_catalog", f"no {embedded_key} returned from {start_url!r}")

        df = records_to_df(rows, db="gwas_catalog")
        if limit is not None:
            df = df.head(limit)
        self.ctx.cache.put_query("gwas_catalog", key, df, url=start_url)
        return df
