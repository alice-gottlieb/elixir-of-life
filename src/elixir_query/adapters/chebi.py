"""ChEBI adapter (Chemical Entities of Biological Interest).

Backend: routed through the EBI Ontology Lookup Service (OLS4) because ChEBI's
legacy SOAP API was retired in September 2025 and the new ChEBI 2.0 REST API
is still stabilising. OLS4 exposes ChEBI as an ontology with the same coverage
and a stable, well-documented contract.

Docs: https://www.ebi.ac.uk/ols4/api/swagger-ui/index.html
Notes: docs/adapter-notes/chebi.md (consulted 2026-04-27).
"""

from __future__ import annotations

import json as _json
import urllib.parse as _urlparse
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import gunzip_to_file, read_tsv, records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_OLS_BASE = "https://www.ebi.ac.uk/ols4/api"
_OLS_TERMS = _OLS_BASE + "/ontologies/chebi/terms"
_OLS_SEARCH = _OLS_BASE + "/search"

_BULK_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/chebi/Flat_file_tab_delimited/compounds.tsv.gz"
)

_JSON_HEADERS = {"Accept": "application/json"}
_TTL_QUERY_SECONDS = 7 * 24 * 3600


def _flatten(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            out[k] = _json.dumps(v)
        else:
            out[k] = v
    return out


def _normalise_chebi_id(value: str) -> str:
    """Return the canonical ``CHEBI:NNN`` short-form for ``value``."""
    s = value.strip()
    if s.upper().startswith("CHEBI:"):
        return "CHEBI:" + s.split(":", 1)[1]
    if s.isdigit():
        return f"CHEBI:{s}"
    raise ValueError(f"unrecognised ChEBI identifier {value!r}; expected 'CHEBI:NNN' or digits")


@register
class ChEBIAdapter(BaseAdapter):
    """ChEBI adapter via the EBI Ontology Lookup Service (OLS4)."""

    meta = AdapterMeta(
        name="chebi",
        aliases=("chebi-db", "chebi_db"),
        homepage="https://www.ebi.ac.uk/chebi/",
        citation=(
            "Hastings J, et al. ChEBI in 2016: Improved services and an expanding "
            "collection of metabolites. Nucleic Acids Res. 44:D1214–D1219 (2016)."
        ),
        supports_bulk=True,
        example_params={"id": "CHEBI:15377"},
        description=(
            "ChEBI — chemical entities of biological interest, served via the EBI "
            "Ontology Lookup Service (OLS4). Call with id='CHEBI:15377' for water, "
            "search='caffeine' for a name search, or bulk=True for the full "
            "compounds.tsv flat-file dump."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        id: str | None = None,
        search: str | None = None,
        limit: int = 25,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch ChEBI records.

        Args:
            id: ChEBI identifier in either ``"CHEBI:15377"`` or ``"15377"`` form.
            search: Free-text term searched against ChEBI labels (capped at
                ``limit`` rows).
            limit: Max rows for search results (default 25).
        """
        if id is None and search is None:
            raise ValueError("pass id='CHEBI:NNN' or search='text'")

        # ---------- single-ID lookup ----------
        if id is not None:
            chebi_id = _normalise_chebi_id(id)
            params_key = {"kind": "term", "id": chebi_id}
            cached = self.ctx.cache.get_query(
                "chebi", params_key, ttl_seconds=_TTL_QUERY_SECONDS
            )
            if cached is not None:
                return cached
            resp = self.ctx.http.get(
                _OLS_TERMS,
                params={"short_form": chebi_id},
                headers=_JSON_HEADERS,
                db="chebi",
            )
            data = resp.json()
            terms = (data.get("_embedded") or {}).get("terms") or []
            if not isinstance(terms, list):
                raise ParseError(
                    "chebi", f"expected list under _embedded.terms, got {type(terms).__name__}"
                )
            if not terms:
                # Try the canonical IRI route as a fallback (some ChEBI IDs need this).
                iri = "http://purl.obolibrary.org/obo/" + chebi_id.replace(":", "_")
                double_encoded = _urlparse.quote(_urlparse.quote(iri, safe=""), safe="")
                fb = self.ctx.http.get(
                    f"{_OLS_TERMS}/{double_encoded}", headers=_JSON_HEADERS, db="chebi"
                )
                fb_data = fb.json()
                if isinstance(fb_data, dict) and fb_data.get("iri"):
                    terms = [fb_data]
            if not terms:
                raise ParseError("chebi", f"no term returned for {chebi_id}")
            df = records_to_df([_flatten(terms[0])], db="chebi")
            self.ctx.cache.put_query("chebi", params_key, df, url=str(resp.request.url))
            return df

        # ---------- free-text search ----------
        assert search is not None
        params_key = {"kind": "search", "q": search, "limit": limit}
        cached = self.ctx.cache.get_query("chebi", params_key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached
        resp = self.ctx.http.get(
            _OLS_SEARCH,
            params={"q": search, "ontology": "chebi", "rows": limit},
            headers=_JSON_HEADERS,
            db="chebi",
        )
        data = resp.json()
        docs = (data.get("response") or {}).get("docs") or []
        if not isinstance(docs, list):
            raise ParseError("chebi", f"expected response.docs list, got {type(docs).__name__}")
        if not docs:
            raise ParseError("chebi", f"no search hits for {search!r}")
        df = records_to_df((_flatten(d) for d in docs), db="chebi")
        self.ctx.cache.put_query("chebi", params_key, df, url=str(resp.request.url))
        return df

    # -------------------------------------------------------------------- bulk
    def bulk(self, **_: Any) -> pl.LazyFrame:
        """Stream ChEBI's gzipped flat-file compounds.tsv and return a LazyFrame.

        Columns: ``ID``, ``STATUS``, ``CHEBI_ACCESSION``, ``PARENT_ID``, ``NAME``,
        ``SOURCE``, ``MODIFIED_ON``.
        """
        key = {"kind": "compounds.tsv"}
        parquet = self.ctx.cache.bulk_ready("chebi", key)
        if parquet is not None:
            return pl.scan_parquet(parquet)

        raw_gz, parquet_path, _meta = self.ctx.cache.bulk_paths("chebi", key)
        self.ctx.http.stream_to_file(_BULK_URL, raw_gz, db="chebi")
        decompressed = raw_gz.with_suffix(".tsv")
        gunzip_to_file(raw_gz, decompressed)
        text = decompressed.read_text(encoding="utf-8")
        df = read_tsv(text, db="chebi")
        if df.height == 0:
            raise ParseError("chebi", f"bulk download {_BULK_URL} parsed to zero rows")
        df.write_parquet(parquet_path)
        df.write_csv(raw_gz.with_suffix(".csv"))
        self.ctx.cache.record_bulk(
            "chebi",
            key,
            url=_BULK_URL,
            rows=df.height,
            schema={c: str(t) for c, t in zip(df.columns, df.dtypes, strict=False)},
        )
        return pl.scan_parquet(parquet_path)
