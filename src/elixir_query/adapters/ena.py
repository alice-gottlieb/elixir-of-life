"""ENA (European Nucleotide Archive) adapter.

Docs: https://www.ebi.ac.uk/ena/portal/api/swagger-ui/index.html
Notes: docs/adapter-notes/ena.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/ena/portal/api
  - /search?result=sequence&query=...&fields=...&format=tsv&limit=...&offset=...
  - offset/limit pagination; TSV response
"""

from __future__ import annotations

from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import read_tsv
from elixir_query.errors import ParseError
from elixir_query.registry import register

_SEARCH_URL = "https://www.ebi.ac.uk/ena/portal/api/search"
_TTL = 7 * 24 * 3600  # 7 days

_DEFAULT_SEQUENCE_FIELDS = (
    "accession",
    "description",
    "scientific_name",
    "tax_id",
    "sequence_length",
    "base_count",
    "mol_type",
)

_DEFAULT_STUDY_FIELDS = (
    "study_accession",
    "secondary_study_accession",
    "study_title",
    "scientific_name",
    "tax_id",
    "center_name",
    "study_description",
    "first_public",
)

_RESULT_DEFAULT_FIELDS: dict[str, tuple[str, ...]] = {
    "sequence": _DEFAULT_SEQUENCE_FIELDS,
    "study": _DEFAULT_STUDY_FIELDS,
}


@register
class ENAAdapter(BaseAdapter):
    """ENA Portal API adapter for sequences, studies, runs, and samples."""

    meta = AdapterMeta(
        name="ena",
        aliases=("european_nucleotide_archive", "embl-bank"),
        homepage="https://www.ebi.ac.uk/ena/",
        citation=(
            "Burgin J, et al. The European Nucleotide Archive in 2022. "
            "Nucleic Acids Res. 51:D121–D125 (2023)."
        ),
        supports_bulk=False,
        example_params={"accession": "AB000001"},
        description=(
            "ENA (European Nucleotide Archive) — nucleotide sequences, studies, "
            "runs and samples. Call with accession='AB000001' for a single sequence, "
            "query='...' for a filtered search, or study_accession='PRJNA...' for a study."
        ),
    )

    def query(
        self,
        *,
        accession: str | None = None,
        query: str | None = None,
        study_accession: str | None = None,
        result: str = "sequence",
        fields: list[str] | tuple[str, ...] | None = None,
        limit: int = 100,
        offset: int = 0,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Search ENA Portal.

        Args:
            accession: ENA / EMBL accession (e.g. ``"AB000001"``). Builds a
                simple ``accession=...`` query against the ``sequence`` result type.
            query: EMBL Portal query string (e.g. ``"tax_eq(9606) AND mol_type=mRNA"``).
            study_accession: Study / project accession (e.g. ``"PRJNA507278"``).
            result: ENA result type: ``"sequence"`` (default), ``"study"``,
                ``"experiment"``, ``"run"``, ``"sample"``.
            fields: Columns to return.  Defaults to a curated subset per result type.
            limit: Maximum rows to return (server pages are 100 by default).
            offset: Starting row offset.
        """
        if accession is not None:
            query = f"accession={accession}"
        elif study_accession is not None:
            query = f"study_accession={study_accession}"
            if result == "sequence":
                result = "study"
        elif query is None:
            raise ValueError("pass accession=, query=, or study_accession= to ena.get()")

        default_fields = _RESULT_DEFAULT_FIELDS.get(result, ("accession", "description"))
        fields_str = ",".join(fields or default_fields)

        key = {"query": query, "result": result, "fields": fields_str, "limit": limit, "offset": offset}
        cached = self.ctx.cache.get_query("ena", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        rows: list[pl.DataFrame] = []
        seen = 0
        cur_offset = offset
        page_size = min(limit, 500)

        while seen < limit:
            params: dict[str, Any] = {
                "result": result,
                "query": query,
                "fields": fields_str,
                "format": "tsv",
                "limit": min(page_size, limit - seen),
                "offset": cur_offset,
            }
            resp = self.ctx.http.get(_SEARCH_URL, params=params, db="ena")
            text = resp.text.strip()
            if not text or text == "\t".join(fields or default_fields):
                break
            page = read_tsv(text, db="ena")
            if page.height == 0:
                break
            rows.append(page)
            seen += page.height
            if page.height < page_size:
                break
            cur_offset += page.height

        if not rows:
            raise ParseError("ena", f"no rows returned for query {query!r} result={result!r}")

        df = pl.concat(rows, how="vertical_relaxed").head(limit)
        self.ctx.cache.put_query("ena", key, df, url=_SEARCH_URL)
        return df
