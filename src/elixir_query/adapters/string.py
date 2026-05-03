"""STRING adapter (protein–protein interaction network).

Docs: https://string-db.org/help/api/
Notes: docs/adapter-notes/string.md (consulted 2026-05-02).

REST base: https://string-db.org/api
  - /tsv/get_string_ids          -> resolve gene names to STRING IDs
  - /tsv/network                 -> pairwise interaction network
  - /tsv/interaction_partners    -> interaction partners for one protein
  - /tsv/functional_annotation   -> GO/KEGG annotations
"""

from __future__ import annotations

from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import read_tsv
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://string-db.org/api"
# The human protein links bulk file (v12.0).
_BULK_URL = (
    "https://stringdb-downloads.org/download/"
    "protein.links.v12.0/9606.protein.links.v12.0.txt.gz"
)

_TTL_QUERY_SECONDS = 7 * 24 * 3600


@register
class STRINGAdapter(BaseAdapter):
    """STRING protein–protein association network REST adapter."""

    meta = AdapterMeta(
        name="string",
        aliases=("string_db", "string-db"),
        homepage="https://string-db.org",
        citation=(
            "Szklarczyk D, et al. The STRING database in 2023. "
            "Nucleic Acids Res. 51:D638–D646 (2023)."
        ),
        supports_bulk=True,
        example_params={"identifiers": "TP53", "species": 9606},
        description=(
            "STRING — protein–protein association networks. Call with "
            "identifiers='TP53' (or a list) + species=9606 for interaction "
            "partners, network= for a pairwise network, or resolve=True to "
            "map gene names to STRING IDs."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        identifiers: str | list[str],
        species: int = 9606,
        method: str = "interaction_partners",
        limit: int = 10,
        required_score: int = 400,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch STRING interaction data.

        Args:
            identifiers: One protein name/STRING ID or a list. Gene symbols
                (e.g. ``"TP53"``), UniProt ACs (e.g. ``"P04637"``), or STRING
                IDs (e.g. ``"9606.ENSP00000269305"``) are all accepted.
            species: NCBI taxon ID (default 9606 = Homo sapiens).
            method: One of:
                ``"interaction_partners"`` (default) — top partners for a single
                protein with their combined scores;
                ``"network"`` — pairwise interactions among all listed proteins;
                ``"resolve"`` — map gene names to STRING IDs;
                ``"functional_annotation"`` — GO/KEGG annotations.
            limit: Max interaction partners to return (for interaction_partners).
            required_score: Minimum combined score (0–1000; default 400).
        """
        if not identifiers:
            raise ValueError("identifiers must be a non-empty string or list")

        ids = identifiers if isinstance(identifiers, list) else [identifiers]
        ids_param = "\r".join(ids)  # STRING API joins multiple IDs with %0d%0a

        valid_methods = ("interaction_partners", "network", "resolve", "functional_annotation")
        if method not in valid_methods:
            raise ValueError(f"method must be one of {valid_methods}, got {method!r}")

        key = {
            "kind": method,
            "identifiers": sorted(ids),
            "species": species,
            "limit": limit,
            "required_score": required_score,
        }
        cached = self.ctx.cache.get_query("string", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached

        endpoint_map = {
            "interaction_partners": "interaction_partners",
            "network": "network",
            "resolve": "get_string_ids",
            "functional_annotation": "functional_annotation",
        }
        params: dict[str, Any] = {
            "identifiers": ids_param,
            "species": species,
            "output_format": "tsv",
        }
        if method == "interaction_partners":
            params["limit"] = limit
            params["required_score"] = required_score
        elif method == "network":
            params["required_score"] = required_score
        elif method == "resolve":
            params["limit"] = 1

        url = f"{_BASE}/tsv/{endpoint_map[method]}"
        resp = self.ctx.http.get(url, params=params, db="string")
        text = resp.text.strip()
        if not text or text.startswith("Error"):
            raise ParseError("string", f"STRING API error for {method}: {text[:200]!r}")

        df = read_tsv(text, db="string")
        if df.height == 0:
            raise ParseError(
                "string",
                f"no results from {method} for identifiers={ids!r} species={species}",
            )
        self.ctx.cache.put_query("string", key, df, url=str(resp.request.url))
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(
        self,
        *,
        species: int = 9606,
        **_: Any,
    ) -> pl.LazyFrame:
        """Stream the STRING protein links file for a species into a LazyFrame.

        Currently only species=9606 (Homo sapiens) is implemented. The file is
        ~1 GB compressed; the Parquet is written once and re-used.

        Columns: ``protein1``, ``protein2``, ``combined_score``.
        """
        if species != 9606:
            raise NotImplementedError(
                "bulk() currently only supports species=9606 (Homo sapiens). "
                "Download other species from https://stringdb-downloads.org/download/"
            )
        from elixir_query.core.io import gunzip_to_file

        key = {"kind": "protein_links", "species": species}
        parquet = self.ctx.cache.bulk_ready("string", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        raw_gz, parquet_path, _meta = self.ctx.cache.bulk_paths("string", key)
        self.ctx.http.stream_to_file(_BULK_URL, raw_gz, db="string")
        decompressed = raw_gz.with_suffix(".txt")
        gunzip_to_file(raw_gz, decompressed)
        text = decompressed.read_text(encoding="utf-8")
        # The file uses single-space separator and a header line.
        df = read_tsv(text, db="string", separator=" ")
        if df.height == 0:
            raise ParseError("string", f"bulk download {_BULK_URL} parsed to zero rows")
        df.write_parquet(parquet_path)
        df.write_csv(raw_gz.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "string",
            key,
            url=_BULK_URL,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
