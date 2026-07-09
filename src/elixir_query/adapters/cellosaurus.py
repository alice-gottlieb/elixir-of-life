"""Cellosaurus adapter (cell line knowledgebase).

Docs: https://api.cellosaurus.org/api-methods
Notes: docs/adapter-notes/cellosaurus.md (consulted 2026-05-02).

REST base: https://api.cellosaurus.org
  - /cell-line/{accession}           -> single cell line
  - /search/cell-line?q=...          -> free-text search (offset-paginated)
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://api.cellosaurus.org"
_BULK_URL = "https://ftp.expasy.org/databases/cellosaurus/cellosaurus.txt"

_JSON_HEADERS = {"Accept": "application/json"}
_TTL_QUERY_SECONDS = 7 * 24 * 3600


def _extract_cell_lines(data: Any) -> list[dict[str, Any]]:
    """Pull the cell-line-list from the Cellosaurus JSON envelope."""
    if not isinstance(data, dict):
        raise ParseError("cellosaurus", f"expected dict, got {type(data).__name__}")
    cell_lines = (data.get("Cellosaurus") or {}).get("cell-line-list") or []
    if not isinstance(cell_lines, list):
        raise ParseError(
            "cellosaurus",
            f"expected list under Cellosaurus.cell-line-list, got {type(cell_lines).__name__}",
        )
    return cell_lines


def _flatten_cell_line(cl: dict[str, Any]) -> dict[str, Any]:
    """Flatten one cell-line dict; extract the most useful scalar fields."""
    row: dict[str, Any] = {}
    for k, v in cl.items():
        if isinstance(v, (dict, list)):
            row[k] = _json.dumps(v)
        else:
            row[k] = v

    # Convenience scalars extracted from nested structures.
    accessions = cl.get("accession") or []
    for acc in accessions:
        if isinstance(acc, dict) and acc.get("type") == "primary":
            row["primary_accession"] = acc.get("value", "")

    names = cl.get("name") or []
    for n in names:
        if isinstance(n, dict) and n.get("type") == "identifier":
            row["identifier"] = n.get("value", "")

    species = cl.get("species-of-origin") or []
    if species and isinstance(species[0], dict):
        row["species"] = species[0].get("value", "")

    return row


@register
class CellosaurusAdapter(BaseAdapter):
    """Cellosaurus cell-line knowledgebase REST adapter."""

    meta = AdapterMeta(
        name="cellosaurus",
        aliases=("cvcl",),
        homepage="https://www.cellosaurus.org",
        citation=(
            "Bairoch A. The Cellosaurus, a cell-line knowledge resource. "
            "J. Biomol. Tech. 29:25–38 (2018)."
        ),
        supports_bulk=True,
        example_params={"accession": "CVCL_0030"},
        description=(
            "Cellosaurus — cell line knowledgebase. Call with accession='CVCL_0030' "
            "for HeLa (exact lookup) or search='HeLa' for a text search."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        accession: str | None = None,
        search: str | None = None,
        fields: str | None = None,
        limit: int = 50,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch Cellosaurus cell-line records.

        Args:
            accession: Cellosaurus accession (e.g. ``"CVCL_0030"`` for HeLa).
            search: Free-text query over all Cellosaurus fields.
            fields: Comma-joined field codes (e.g. ``"id,ac,sy,ca,sx,ox"``).
                If omitted the full record is returned.
            limit: Max rows for search results.
        """
        if accession is None and search is None:
            raise ValueError("pass accession='CVCL_XXXX' or search='text'")

        # ---- single cell-line lookup ----
        if accession is not None:
            acc = accession.upper()
            params_key = {"kind": "cell_line", "accession": acc, "fields": fields}
            cached = self.ctx.cache.get_query(
                "cellosaurus", params_key, ttl_seconds=_TTL_QUERY_SECONDS
            )
            if cached is not None:
                return cached
            params: dict[str, Any] = {}
            if fields:
                params["fields"] = fields
            resp = self.ctx.http.get(
                f"{_BASE}/cell-line/{acc}", params=params, headers=_JSON_HEADERS, db="cellosaurus"
            )
            cell_lines = _extract_cell_lines(resp.json())
            if not cell_lines:
                raise ParseError("cellosaurus", f"no cell line returned for accession={acc!r}")
            df = records_to_df([_flatten_cell_line(cl) for cl in cell_lines], db="cellosaurus")
            self.ctx.cache.put_query(
                "cellosaurus", params_key, df, url=str(resp.request.url)
            )
            return df

        # ---- free-text search (offset-paginated) ----
        assert search is not None
        params_key = {"kind": "search", "q": search, "limit": limit, "fields": fields}
        cached = self.ctx.cache.get_query(
            "cellosaurus", params_key, ttl_seconds=_TTL_QUERY_SECONDS
        )
        if cached is not None:
            return cached
        rows: list[dict[str, Any]] = []
        start = 0
        page_size = min(limit, 50)
        while len(rows) < limit:
            p: dict[str, Any] = {"q": search, "rows": page_size, "start": start}
            if fields:
                p["fields"] = fields
            resp = self.ctx.http.get(
                f"{_BASE}/search/cell-line", params=p, headers=_JSON_HEADERS, db="cellosaurus"
            )
            cell_lines = _extract_cell_lines(resp.json())
            if not cell_lines:
                break
            for cl in cell_lines:
                rows.append(_flatten_cell_line(cl))
                if len(rows) >= limit:
                    break
            if len(cell_lines) < page_size:
                break
            start += page_size
        if not rows:
            raise ParseError("cellosaurus", f"no results for search={search!r}")
        df = records_to_df(rows, db="cellosaurus")
        self.ctx.cache.put_query("cellosaurus", params_key, df, url=f"{_BASE}/search/cell-line")
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(self, **_: Any) -> pl.LazyFrame:
        """Stream the Cellosaurus flat-text file and return a LazyFrame.

        Extracts a minimal (accession, identifier) index from the flat file
        and returns a LazyFrame over the cached Parquet. For the full structured
        data, use ``query(accession=...)`` per entry.
        """
        key = {"kind": "cellosaurus_txt"}
        parquet = self.ctx.cache.bulk_ready("cellosaurus", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        raw, parquet_path, _meta = self.ctx.cache.bulk_paths("cellosaurus", key)
        self.ctx.http.stream_to_file(_BULK_URL, raw, db="cellosaurus")

        # Extract ID and AC lines from the flat file.
        # Format: each record ends with "//"; fields are 2-char tags followed by space.
        rows: list[dict[str, str]] = []
        current: dict[str, str] = {}
        with open(raw, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if line.startswith("ID "):
                    current["identifier"] = line[3:].strip()
                elif line.startswith("AC "):
                    current["accession"] = line[3:].strip()
                elif line.startswith("CA "):
                    current["category"] = line[3:].strip()
                elif line == "//":
                    if current.get("accession"):
                        rows.append(dict(current))
                    current = {}
        if not rows:
            raise ParseError("cellosaurus", "bulk file parsed to zero records")
        df = pl.DataFrame(rows)
        df.write_parquet(parquet_path)
        df.write_csv(raw.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "cellosaurus",
            key,
            url=_BULK_URL,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
