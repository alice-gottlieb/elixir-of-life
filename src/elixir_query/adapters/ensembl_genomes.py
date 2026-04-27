"""Ensembl Genomes adapter (plants / fungi / protists / metazoa).

Docs: https://rest.ensembl.org (the unified REST host serves both vertebrate
Ensembl and Ensembl Genomes identifiers).
Notes: docs/adapter-notes/ensembl_genomes.md (consulted 2026-04-27).

This adapter is self-contained — it does not import from ``ensembl.py`` so the
two registries can evolve independently.
"""

from __future__ import annotations

import gzip
import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://rest.ensembl.org"
_LOOKUP_ID = _BASE + "/lookup/id/{id}"
_LOOKUP_SYMBOL = _BASE + "/lookup/symbol/{species}/{symbol}"
_HOMOLOGY_ID = _BASE + "/homology/id/{id}"
_INFO_DIVISION = _BASE + "/info/genomes/division/{division}"

_JSON_HEADERS = {"Accept": "application/json"}
_TTL_QUERY_SECONDS = 7 * 24 * 3600  # 7 days

_VALID_DIVISIONS = ("plants", "fungi", "protists", "metazoa", "bacteria", "pan_homology")
_DIVISION_FTP_HOST = "https://ftp.ensemblgenomes.org/pub"


def _flatten(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            out[k] = _json.dumps(v)
        else:
            out[k] = v
    return out


@register
class EnsemblGenomesAdapter(BaseAdapter):
    """Ensembl Genomes REST adapter for non-vertebrate species."""

    meta = AdapterMeta(
        name="ensembl_genomes",
        aliases=("ensemblgenomes", "ensembl-genomes"),
        homepage="https://ensemblgenomes.org",
        citation=(
            "Yates AD, et al. Ensembl Genomes 2022. "
            "Nucleic Acids Res. 50:D996–D1003 (2022)."
        ),
        supports_bulk=True,
        example_params={"id": "AT3G52260"},
        description=(
            "Ensembl Genomes — plants, fungi, protists, metazoa. Call with "
            "id='AT3G52260' for an Arabidopsis stable-ID lookup, symbol=...+species=... "
            "for symbol lookup, division=...+species=... bulk=True for FTP GTF."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        id: str | None = None,
        symbol: str | None = None,
        species: str | None = None,
        division: str | None = None,
        homology_compara: str | None = None,
        expand: int = 0,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch records from the Ensembl Genomes REST API.

        Args:
            id: Ensembl-Genomes stable ID (e.g. ``"AT3G52260"`` for Arabidopsis,
                ``"YJR104C"`` for yeast). Triggers ``/lookup/id/``. With
                ``homology_compara`` set, triggers ``/homology/id/``.
            symbol: Gene symbol; requires ``species`` (e.g. ``"PUB48"`` +
                ``species="arabidopsis_thaliana"``). Triggers ``/lookup/symbol/``.
            species: Ensembl-Genomes species name (lowercase, underscored).
            division: ``"plants" | "fungi" | "protists" | "metazoa" | "bacteria"``.
                When set without an ``id`` or ``symbol``, lists all genomes in
                the division via ``/info/genomes/division/``.
            homology_compara: One of ``plants``, ``fungi``, ``protists``,
                ``metazoa``, ``pan_homology``. Switches an ``id=`` lookup to the
                homology endpoint.
            expand: Pass through to ``/lookup/id/`` to include child features.
        """
        if id is None and symbol is None and division is None:
            raise ValueError("pass id=..., symbol=...+species=..., or division=...")
        if symbol is not None and species is None:
            raise ValueError("symbol=... requires species=...")
        if homology_compara is not None and homology_compara not in _VALID_DIVISIONS:
            raise ValueError(
                f"homology_compara must be one of {_VALID_DIVISIONS}, got {homology_compara!r}"
            )

        # ---- homology --------------------------------------------------------
        if id is not None and homology_compara is not None:
            params_key = {"kind": "homology", "id": id, "compara": homology_compara}
            cached = self.ctx.cache.get_query(
                "ensembl_genomes", params_key, ttl_seconds=_TTL_QUERY_SECONDS
            )
            if cached is not None:
                return cached
            url = _HOMOLOGY_ID.format(id=id)
            resp = self.ctx.http.get(
                url,
                params={"compara": homology_compara},
                headers=_JSON_HEADERS,
                db="ensembl_genomes",
            )
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError(
                    "ensembl_genomes",
                    f"expected dict from /homology/id/, got {type(data).__name__}",
                )
            entries = data.get("data") or []
            if not isinstance(entries, list):
                raise ParseError(
                    "ensembl_genomes", f"expected list under 'data', got {type(entries).__name__}"
                )
            df = records_to_df((_flatten(r) for r in entries), db="ensembl_genomes")
            if df.height == 0:
                raise ParseError("ensembl_genomes", f"no homologies for id={id!r}")
            self.ctx.cache.put_query(
                "ensembl_genomes", params_key, df, url=str(resp.request.url)
            )
            return df

        # ---- single lookup by id --------------------------------------------
        if id is not None:
            params_key = {"kind": "lookup_id", "id": id, "expand": expand}
            cached = self.ctx.cache.get_query(
                "ensembl_genomes", params_key, ttl_seconds=_TTL_QUERY_SECONDS
            )
            if cached is not None:
                return cached
            url = _LOOKUP_ID.format(id=id)
            resp = self.ctx.http.get(
                url, params={"expand": expand}, headers=_JSON_HEADERS, db="ensembl_genomes"
            )
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError(
                    "ensembl_genomes", f"expected dict from /lookup/id/, got {type(data).__name__}"
                )
            df = records_to_df([_flatten(data)], db="ensembl_genomes")
            if df.height == 0:
                raise ParseError("ensembl_genomes", f"no record for id={id!r}")
            self.ctx.cache.put_query(
                "ensembl_genomes", params_key, df, url=str(resp.request.url)
            )
            return df

        # ---- symbol lookup --------------------------------------------------
        if symbol is not None:
            params_key = {
                "kind": "lookup_symbol",
                "symbol": symbol,
                "species": species,
                "expand": expand,
            }
            cached = self.ctx.cache.get_query(
                "ensembl_genomes", params_key, ttl_seconds=_TTL_QUERY_SECONDS
            )
            if cached is not None:
                return cached
            url = _LOOKUP_SYMBOL.format(species=species, symbol=symbol)
            resp = self.ctx.http.get(
                url, params={"expand": expand}, headers=_JSON_HEADERS, db="ensembl_genomes"
            )
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError(
                    "ensembl_genomes",
                    f"expected dict from /lookup/symbol/, got {type(data).__name__}",
                )
            df = records_to_df([_flatten(data)], db="ensembl_genomes")
            if df.height == 0:
                raise ParseError("ensembl_genomes", f"no record for {species}/{symbol}")
            self.ctx.cache.put_query(
                "ensembl_genomes", params_key, df, url=str(resp.request.url)
            )
            return df

        # ---- division genome list ------------------------------------------
        assert division is not None
        if division not in _VALID_DIVISIONS:
            raise ValueError(f"division must be one of {_VALID_DIVISIONS}, got {division!r}")
        params_key = {"kind": "division", "division": division}
        cached = self.ctx.cache.get_query(
            "ensembl_genomes", params_key, ttl_seconds=_TTL_QUERY_SECONDS
        )
        if cached is not None:
            return cached
        url = _INFO_DIVISION.format(division=division)
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="ensembl_genomes")
        data = resp.json()
        if not isinstance(data, list):
            raise ParseError(
                "ensembl_genomes",
                f"expected list from /info/genomes/division/, got {type(data).__name__}",
            )
        df = records_to_df((_flatten(r) for r in data), db="ensembl_genomes")
        if df.height == 0:
            raise ParseError("ensembl_genomes", f"no genomes for division {division!r}")
        self.ctx.cache.put_query("ensembl_genomes", params_key, df, url=str(resp.request.url))
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(
        self,
        *,
        division: str = "plants",
        species: str = "arabidopsis_thaliana",
        release: str = "current",
        kind: str = "gtf",
        **_: Any,
    ) -> pl.LazyFrame:
        """Stream a per-species GTF dump from the Ensembl Genomes FTP.

        Args:
            division: ``plants``, ``fungi``, ``protists``, ``metazoa`` or ``bacteria``.
            species: Ensembl-Genomes species name.
            release: ``"current"`` or a numeric release like ``"60"``.
            kind: Currently only ``"gtf"`` is supported.
        """
        if kind != "gtf":
            raise ValueError(f"unsupported bulk kind {kind!r}; only 'gtf' is implemented")
        if division not in _VALID_DIVISIONS:
            raise ValueError(f"division must be one of {_VALID_DIVISIONS}, got {division!r}")
        key = {"division": division, "species": species, "release": release, "kind": kind}
        parquet = self.ctx.cache.bulk_ready("ensembl_genomes", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        rel_segment = "current" if release == "current" else f"release-{release}"
        listing_url = f"{_DIVISION_FTP_HOST}/{division}/{rel_segment}/gtf/{species}/"
        listing = self.ctx.http.get(listing_url, db="ensembl_genomes").text
        gtf_name: str | None = None
        for token in listing.split('"'):
            if token.endswith(".gtf.gz") and ".chr." not in token and ".abinitio." not in token:
                gtf_name = token
                break
        if gtf_name is None:
            raise ParseError(
                "ensembl_genomes", f"could not locate primary GTF in {listing_url}"
            )
        gtf_url = listing_url + gtf_name

        raw, parquet_path, _meta = self.ctx.cache.bulk_paths("ensembl_genomes", key)
        self.ctx.http.stream_to_file(gtf_url, raw, db="ensembl_genomes")

        rows: list[tuple[str, str, str, int, int, str, str, str, str]] = []
        with gzip.open(raw, "rt", encoding="utf-8") as fh:
            for line in fh:
                if not line or line.startswith("#"):
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) != 9:
                    continue
                seqname, source, feature, start, end, score, strand, frame, attrs = parts
                rows.append(
                    (seqname, source, feature, int(start), int(end), score, strand, frame, attrs)
                )
        if not rows:
            raise ParseError("ensembl_genomes", f"GTF at {gtf_url} parsed to zero rows")
        df = pl.DataFrame(
            rows,
            schema=[
                ("seqname", pl.Utf8),
                ("source", pl.Utf8),
                ("feature", pl.Utf8),
                ("start", pl.Int64),
                ("end", pl.Int64),
                ("score", pl.Utf8),
                ("strand", pl.Utf8),
                ("frame", pl.Utf8),
                ("attributes", pl.Utf8),
            ],
            orient="row",
        )
        df.write_parquet(parquet_path)
        df.write_csv(raw.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "ensembl_genomes",
            key,
            url=gtf_url,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
