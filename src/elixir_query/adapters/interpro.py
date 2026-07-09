"""InterPro adapter (protein family and domain database).

Docs: https://github.com/ProteinsWebTeam/interpro7-api/blob/master/docs/README.md
Notes: docs/adapter-notes/interpro.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/interpro/api/
  - /entry/{db}/{accession}     -> single entry
  - /entry/{db}/                -> paginated list for a source DB
  - /protein/uniprot/{acc}/entry/interpro/  -> entries annotating a protein
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://www.ebi.ac.uk/interpro/api"

_JSON_HEADERS = {"Accept": "application/json"}
_TTL_QUERY_SECONDS = 7 * 24 * 3600

# Valid member-database slugs accepted by the API.
_VALID_DBS = frozenset(
    (
        "interpro",
        "pfam",
        "smart",
        "prints",
        "prosite",
        "cathgene3d",
        "tigrfams",
        "panther",
        "hamap",
        "pirsf",
        "sfld",
        "ssf",
        "ncbifam",
    )
)


def _flatten(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {"value": _json.dumps(d)}
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            out[k] = _json.dumps(v)
        else:
            out[k] = v
    return out


def _extract_metadata(record: dict[str, Any]) -> dict[str, Any]:
    """Hoist the nested 'metadata' sub-dict to the top level."""
    flat = _flatten(record)
    if "metadata" in record and isinstance(record["metadata"], dict):
        for k, v in record["metadata"].items():
            flat[k] = _json.dumps(v) if isinstance(v, (dict, list)) else v
    return flat


@register
class InterProAdapter(BaseAdapter):
    """InterPro protein family/domain annotation REST adapter."""

    meta = AdapterMeta(
        name="interpro",
        aliases=("interpro7",),
        homepage="https://www.ebi.ac.uk/interpro/",
        citation=(
            "Paysan-Lafosse T, et al. InterPro in 2022. "
            "Nucleic Acids Res. 51:D418–D427 (2023)."
        ),
        supports_bulk=True,
        example_params={"accession": "IPR001680"},
        description=(
            "InterPro — protein family and domain database. Call with "
            "accession='IPR001680' for a single entry, db='pfam' for a list "
            "of Pfam entries, or protein_accession='P00533' for all entries "
            "annotating that UniProt protein."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        accession: str | None = None,
        db: str = "interpro",
        protein_accession: str | None = None,
        limit: int | None = 200,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch InterPro records.

        Args:
            accession: InterPro accession (``"IPR001680"``) or member-DB accession
                (``"PF00001"`` for Pfam). Infers ``db`` from the prefix if not given.
            db: Member database slug (default ``"interpro"``). Ignored when
                ``protein_accession`` is set.
            protein_accession: UniProt accession; returns all InterPro entries
                annotating this protein.
            limit: Max rows for list/protein queries (None = all pages).
        """
        if accession is None and protein_accession is None:
            raise ValueError("pass accession=... or protein_accession=...")

        # Infer DB from accession prefix if not explicitly provided.
        resolved_db = db
        if accession is not None:
            acc_upper = accession.upper()
            if acc_upper.startswith("PF"):
                resolved_db = "pfam"
            elif acc_upper.startswith("SM"):
                resolved_db = "smart"
            elif acc_upper.startswith("IPR"):
                resolved_db = "interpro"

        # ---- single-entry lookup ----
        if accession is not None:
            key = {"kind": "entry", "db": resolved_db, "accession": accession}
            cached = self.ctx.cache.get_query("interpro", key, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = f"{_BASE}/entry/{resolved_db}/{accession}"
            resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="interpro")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError(
                    "interpro", f"expected dict from /entry/, got {type(data).__name__}"
                )
            row = _extract_metadata(data)
            df = records_to_df([row], db="interpro")
            if df.height == 0:
                raise ParseError("interpro", f"no record returned for {resolved_db}/{accession}")
            self.ctx.cache.put_query("interpro", key, df, url=str(resp.request.url))
            return df

        # ---- protein-annotation lookup ----
        assert protein_accession is not None
        return self._paginated(
            url=f"{_BASE}/protein/uniprot/{protein_accession}/entry/interpro/",
            key={"kind": "protein_entries", "accession": protein_accession},
            limit=limit,
        )

    # -------------------------------------------------------------------- bulk
    def bulk(
        self,
        *,
        db: str = "interpro",
        **_: Any,
    ) -> pl.LazyFrame:
        """Stream all entries for ``db`` into Parquet and return a LazyFrame.

        Args:
            db: Member-database slug (default ``"interpro"`` for all InterPro
                integrated entries).
        """
        if db not in _VALID_DBS:
            raise ValueError(f"db must be one of {sorted(_VALID_DBS)}, got {db!r}")
        key = {"kind": "bulk_entries", "db": db}
        parquet = self.ctx.cache.bulk_ready("interpro", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        url = f"{_BASE}/entry/{db}/"
        rows: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params: dict[str, Any] | None = None
        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, headers=_JSON_HEADERS, db="interpro")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("interpro", f"unexpected response shape: {type(data).__name__}")
            for record in data.get("results") or []:
                rows.append(_extract_metadata(record) if isinstance(record, dict) else {"value": record})
            next_url = data.get("next")
            next_params = None

        if not rows:
            raise ParseError("interpro", f"bulk for db={db!r} returned no rows")
        df = pl.from_dicts(rows)
        raw, parquet_path, _meta = self.ctx.cache.bulk_paths("interpro", key)
        df.write_parquet(parquet_path)
        df.write_csv(raw.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "interpro",
            key,
            url=url,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)

    # ------------------------------------------------------------------ helper
    def _paginated(self, *, url: str, key: dict[str, Any], limit: int | None) -> pl.DataFrame:
        cached = self.ctx.cache.get_query("interpro", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        rows: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params: dict[str, Any] | None = None
        while next_url:
            resp = self.ctx.http.get(next_url, params=next_params, headers=_JSON_HEADERS, db="interpro")
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("interpro", f"unexpected response: {type(data).__name__}")
            for record in data.get("results") or []:
                rows.append(_extract_metadata(record) if isinstance(record, dict) else {"value": record})
                if limit is not None and len(rows) >= limit:
                    break
            if limit is not None and len(rows) >= limit:
                break
            next_url = data.get("next")
            next_params = None
        if not rows:
            raise ParseError("interpro", f"no rows returned from {url}")
        df = records_to_df(rows, db="interpro")
        self.ctx.cache.put_query("interpro", key, df, url=url)
        return df
