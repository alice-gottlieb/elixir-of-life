"""GWAS Catalog adapter (genome-wide association studies).

Docs: https://www.ebi.ac.uk/gwas/rest/docs/api
Notes: docs/adapter-notes/gwas_catalog.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/gwas/rest/api
  - /studies/{accession}                    -> single study
  - /studies/{accession}/associations       -> associations for a study
  - /singleNucleotidePolymorphisms/{rsid}   -> single SNP
  - /efoTraits/{efo_id}                     -> EFO trait
  - /studies?page=0&size=20                 -> paginated list
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
_BULK_URL = "https://www.ebi.ac.uk/gwas/api/search/downloads/full"

_JSON_HEADERS = {"Accept": "application/json"}
_TTL_QUERY_SECONDS = 7 * 24 * 3600


def _flatten(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {"value": _json.dumps(d)}
    return {
        k: (_json.dumps(v) if isinstance(v, (dict, list)) else v)
        for k, v in d.items()
    }


def _hal_records(data: dict[str, Any], resource: str) -> list[dict[str, Any]]:
    """Extract records from a HAL-style ``_embedded`` response."""
    embedded = data.get("_embedded") or {}
    # GWAS uses plural resource names in _embedded.
    records = embedded.get(resource) or embedded.get(resource + "s") or []
    if not isinstance(records, list):
        raise ParseError(
            "gwas_catalog",
            f"expected list under _embedded.{resource}, got {type(records).__name__}",
        )
    return records


def _hal_next(data: dict[str, Any]) -> str | None:
    links = data.get("_links") or {}
    nxt = links.get("next")
    if isinstance(nxt, dict):
        return nxt.get("href")
    return None


@register
class GWASCatalogAdapter(BaseAdapter):
    """GWAS Catalog HAL-JSON REST adapter."""

    meta = AdapterMeta(
        name="gwas_catalog",
        aliases=("gwas", "gwas-catalog"),
        homepage="https://www.ebi.ac.uk/gwas/",
        citation=(
            "Sollis E, et al. The NHGRI-EBI GWAS Catalog. "
            "Nucleic Acids Res. 51:D977–D985 (2023)."
        ),
        supports_bulk=True,
        example_params={"study": "GCST000001"},
        description=(
            "GWAS Catalog — curated genome-wide association studies. Call with "
            "study='GCST000001' for a single study, rsid='rs2981582' for a SNP, "
            "efo_id='EFO_0000305' for a trait, or associations_for='GCST000001' "
            "for the associations of a study."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        study: str | None = None,
        rsid: str | None = None,
        efo_id: str | None = None,
        associations_for: str | None = None,
        list_studies: bool = False,
        limit: int | None = 100,
        page_size: int = 100,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch GWAS Catalog records.

        Args:
            study: GWAS Catalog study accession (e.g. ``"GCST000001"``).
            rsid: SNP rsID (e.g. ``"rs2981582"``).
            efo_id: EFO trait identifier (e.g. ``"EFO_0000305"``).
            associations_for: Study accession; returns its associations.
            list_studies: If True, return the first ``limit`` studies.
            limit: Row cap for list/association queries.
            page_size: Server-side page size (default 100, max 500).
        """
        if not any([study, rsid, efo_id, associations_for, list_studies]):
            raise ValueError(
                "pass study=, rsid=, efo_id=, associations_for=, or list_studies=True"
            )

        # ---- single study ----
        if study is not None:
            return self._single(f"{_BASE}/studies/{study}", {"kind": "study", "id": study})

        # ---- single SNP ----
        if rsid is not None:
            return self._single(
                f"{_BASE}/singleNucleotidePolymorphisms/{rsid}",
                {"kind": "snp", "rsid": rsid},
            )

        # ---- single EFO trait ----
        if efo_id is not None:
            return self._single(
                f"{_BASE}/efoTraits/{efo_id}",
                {"kind": "trait", "efo_id": efo_id},
            )

        # ---- study associations (paginated) ----
        if associations_for is not None:
            return self._paginated(
                url=f"{_BASE}/studies/{associations_for}/associations",
                resource="associations",
                key={"kind": "study_associations", "study": associations_for, "limit": limit},
                params={"size": page_size},
                limit=limit,
            )

        # ---- list studies ----
        assert list_studies
        return self._paginated(
            url=f"{_BASE}/studies",
            resource="studies",
            key={"kind": "list_studies", "limit": limit},
            params={"size": page_size},
            limit=limit,
        )

    def _single(self, url: str, key: dict[str, Any]) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("gwas_catalog", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="gwas_catalog")
        data = resp.json()
        if not isinstance(data, dict):
            raise ParseError("gwas_catalog", f"expected dict, got {type(data).__name__}")
        df = records_to_df([_flatten(data)], db="gwas_catalog")
        if df.height == 0:
            raise ParseError("gwas_catalog", f"empty result from {url}")
        self.ctx.cache.put_query("gwas_catalog", key, df, url=str(resp.request.url))
        return df

    def _paginated(
        self,
        *,
        url: str,
        resource: str,
        key: dict[str, Any],
        params: dict[str, Any],
        limit: int | None,
    ) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("gwas_catalog", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        rows: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params: dict[str, Any] | None = dict(params)
        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, headers=_JSON_HEADERS, db="gwas_catalog")
            data = resp.json()
            for r in _hal_records(data, resource):
                rows.append(_flatten(r))
                if limit is not None and len(rows) >= limit:
                    break
            if limit is not None and len(rows) >= limit:
                break
            next_url = _hal_next(data)
            next_params = None
        if not rows:
            raise ParseError("gwas_catalog", f"no rows returned for {resource}")
        df = records_to_df(rows, db="gwas_catalog")
        self.ctx.cache.put_query("gwas_catalog", key, df, url=url)
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(self, **_: Any) -> pl.LazyFrame:
        """Stream the full GWAS Catalog TSV dump and return a LazyFrame.

        The full download is ~120 MB (tab-delimited, ~130k associations). Columns
        include DATE_ADDED_TO_CATALOG, PUBMEDID, FIRST_AUTHOR, DISEASE/TRAIT,
        SNPS, P-VALUE, OR or BETA, MAPPED_GENE, and more.
        """
        from elixir_query.core.io import read_tsv

        key = {"kind": "full_catalog"}
        parquet = self.ctx.cache.bulk_ready("gwas_catalog", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        raw, parquet_path, _meta = self.ctx.cache.bulk_paths("gwas_catalog", key)
        self.ctx.http.stream_to_file(_BULK_URL, raw, db="gwas_catalog")
        text = raw.read_text(encoding="utf-8")
        df = read_tsv(text, db="gwas_catalog")
        if df.height == 0:
            raise ParseError("gwas_catalog", f"bulk download {_BULK_URL} parsed to zero rows")
        df.write_parquet(parquet_path)
        df.write_csv(raw.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "gwas_catalog",
            key,
            url=_BULK_URL,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
