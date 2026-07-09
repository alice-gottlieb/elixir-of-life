"""Ensembl adapter (vertebrate genomes).

Docs: https://rest.ensembl.org
Notes: docs/adapter-notes/ensembl.md (consulted 2026-04-27).

REST base: https://rest.ensembl.org
  - /lookup/id/{id}                          -> single feature lookup
  - /lookup/symbol/{species}/{symbol}        -> lookup by gene symbol
  - /overlap/region/{species}/{region}       -> features overlapping a region
  - /xrefs/id/{id}                           -> cross-references for a stable id

The REST API speaks JSON; there is no native tabular format. We flatten the JSON
one level and let the cache layer persist CSV + Parquet.
"""

from __future__ import annotations

import gzip
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://rest.ensembl.org"
_LOOKUP_ID = _BASE + "/lookup/id/{id}"
_LOOKUP_SYMBOL = _BASE + "/lookup/symbol/{species}/{symbol}"
_OVERLAP_REGION = _BASE + "/overlap/region/{species}/{region}"
_XREFS_ID = _BASE + "/xrefs/id/{id}"

_TTL_QUERY_SECONDS = 7 * 24 * 3600  # 7 days

_JSON_HEADERS = {"Accept": "application/json"}


def _flatten(d: dict[str, Any]) -> dict[str, Any]:
    """Flatten a one-level dict, JSON-encoding any nested dict/list values."""
    import json

    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            out[k] = json.dumps(v)
        else:
            out[k] = v
    return out


@register
class EnsemblAdapter(BaseAdapter):
    """Ensembl REST API adapter for vertebrate genomes."""

    meta = AdapterMeta(
        name="ensembl",
        aliases=("ensembl_vertebrates",),
        homepage="https://www.ensembl.org",
        citation="Harrison PW, et al. Ensembl 2024. Nucleic Acids Res. 52(D1):D891–D899 (2024).",
        supports_bulk=True,
        example_params={"id": "ENSG00000139618"},
        description=(
            "Ensembl vertebrate genomes via rest.ensembl.org. Call with id='ENSG...' "
            "for a stable-ID lookup, symbol='BRCA2' + species='homo_sapiens' for a "
            "symbol lookup, or region='13:32315474-32400266' + species=... for "
            "feature overlap."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        id: str | None = None,
        symbol: str | None = None,
        species: str | None = None,
        region: str | None = None,
        feature: str | tuple[str, ...] = "gene",
        expand: int = 0,
        xrefs: bool = False,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch records from the Ensembl REST API.

        Args:
            id: Ensembl stable ID (e.g. "ENSG00000139618"). Triggers /lookup/id/.
            symbol: Gene symbol (e.g. "BRCA2"). Requires ``species``. Triggers
                /lookup/symbol/.
            species: Ensembl species name (e.g. "homo_sapiens").
            region: Genomic region in "chr:start-end" form. Requires ``species``.
                Triggers /overlap/region/.
            feature: Feature type(s) for overlap queries; default "gene".
            expand: Pass through to /lookup/id/ to include child features (0/1).
            xrefs: When True with ``id``, query /xrefs/id/ instead of /lookup/id/.

        Returns:
            Polars DataFrame. Single-record endpoints yield one row; overlap
            and xrefs yield one row per returned feature.
        """
        if id is None and symbol is None and region is None:
            raise ValueError(
                "pass one of id=..., symbol=...+species=..., or region=...+species=..."
            )
        if symbol is not None and species is None:
            raise ValueError("symbol=... requires species=...")
        if region is not None and species is None:
            raise ValueError("region=... requires species=...")

        # ---- xrefs path -----------------------------------------------------
        if id is not None and xrefs:
            params = {"id": id, "kind": "xrefs"}
            cached = self.ctx.cache.get_query("ensembl", params, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = _XREFS_ID.format(id=id)
            resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="ensembl")
            data = resp.json()
            if not isinstance(data, list):
                raise ParseError("ensembl", f"expected list from /xrefs/id/, got {type(data).__name__}")
            df = records_to_df((_flatten(r) for r in data), db="ensembl")
            if df.height == 0:
                raise ParseError("ensembl", f"no xrefs returned for {id!r}")
            self.ctx.cache.put_query("ensembl", params, df, url=str(resp.request.url))
            return df

        # ---- single lookup by id -------------------------------------------
        if id is not None:
            params = {"id": id, "expand": expand, "kind": "lookup_id"}
            cached = self.ctx.cache.get_query("ensembl", params, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = _LOOKUP_ID.format(id=id)
            resp = self.ctx.http.get(
                url, params={"expand": expand}, headers=_JSON_HEADERS, db="ensembl"
            )
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError("ensembl", f"expected dict from /lookup/id/, got {type(data).__name__}")
            df = records_to_df([_flatten(data)], db="ensembl")
            if df.height == 0:
                raise ParseError("ensembl", f"no record returned for id {id!r}")
            self.ctx.cache.put_query("ensembl", params, df, url=str(resp.request.url))
            return df

        # ---- symbol lookup --------------------------------------------------
        if symbol is not None:
            params = {"symbol": symbol, "species": species, "expand": expand, "kind": "lookup_symbol"}
            cached = self.ctx.cache.get_query("ensembl", params, ttl_seconds=_TTL_QUERY_SECONDS)
            if cached is not None:
                return cached
            url = _LOOKUP_SYMBOL.format(species=species, symbol=symbol)
            resp = self.ctx.http.get(
                url, params={"expand": expand}, headers=_JSON_HEADERS, db="ensembl"
            )
            data = resp.json()
            if not isinstance(data, dict):
                raise ParseError(
                    "ensembl", f"expected dict from /lookup/symbol/, got {type(data).__name__}"
                )
            df = records_to_df([_flatten(data)], db="ensembl")
            if df.height == 0:
                raise ParseError("ensembl", f"no record returned for {species}/{symbol}")
            self.ctx.cache.put_query("ensembl", params, df, url=str(resp.request.url))
            return df

        # ---- region overlap -------------------------------------------------
        assert region is not None and species is not None
        feature_list = (feature,) if isinstance(feature, str) else tuple(feature)
        params = {
            "region": region,
            "species": species,
            "feature": list(feature_list),
            "kind": "overlap_region",
        }
        cached = self.ctx.cache.get_query("ensembl", params, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        url = _OVERLAP_REGION.format(species=species, region=region)
        # httpx will repeat the parameter for list values: feature=gene&feature=transcript
        resp = self.ctx.http.get(
            url,
            params=[("feature", f) for f in feature_list],
            headers=_JSON_HEADERS,
            db="ensembl",
        )
        data = resp.json()
        if not isinstance(data, list):
            raise ParseError("ensembl", f"expected list from /overlap/region/, got {type(data).__name__}")
        df = records_to_df((_flatten(r) for r in data), db="ensembl")
        if df.height == 0:
            raise ParseError("ensembl", f"no overlapping {feature_list} for {species}:{region}")
        self.ctx.cache.put_query("ensembl", params, df, url=str(resp.request.url))
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(
        self,
        *,
        species: str = "homo_sapiens",
        release: str = "current",
        kind: str = "gtf",
        **_: Any,
    ) -> pl.LazyFrame:
        """Download an Ensembl FTP GTF dump and return a LazyFrame.

        Args:
            species: Ensembl species name (default ``homo_sapiens``).
            release: ``"current"`` or a numeric release like ``"112"``.
            kind: Currently only ``"gtf"`` is supported.

        Returns:
            LazyFrame with the 9 standard GTF columns.
        """
        if kind != "gtf":
            raise ValueError(f"unsupported bulk kind {kind!r}; only 'gtf' is implemented")
        key = {"species": species, "release": release, "kind": kind}
        parquet = self.ctx.cache.bulk_ready("ensembl", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        dir_segment = "current_gtf" if release == "current" else f"release-{release}/gtf"
        # The Ensembl FTP exposes a directory listing; we resolve the canonical
        # GTF file name by listing the directory once.
        listing_url = f"https://ftp.ensembl.org/pub/{dir_segment}/{species}/"
        listing = self.ctx.http.get(listing_url, db="ensembl").text
        # Pick the primary annotation file (excludes abinitio/chr/_*).
        gtf_name: str | None = None
        for token in listing.split('"'):
            if token.endswith(".gtf.gz") and ".chr." not in token and ".abinitio." not in token:
                gtf_name = token
                break
        if gtf_name is None:
            raise ParseError("ensembl", f"could not locate primary GTF in {listing_url}")
        gtf_url = listing_url + gtf_name

        raw, parquet_path, _meta = self.ctx.cache.bulk_paths("ensembl", key)
        self.ctx.http.stream_to_file(gtf_url, raw, db="ensembl")

        # Stream-parse the gzipped GTF into a DataFrame.
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
            raise ParseError("ensembl", f"GTF at {gtf_url} parsed to zero rows")
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
            "ensembl",
            key,
            url=gtf_url,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
