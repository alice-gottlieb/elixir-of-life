"""STRING (protein interaction network) adapter.

Docs: https://string-db.org/help/api/
Notes: docs/adapter-notes/string.md (consulted 2026-05-02).

REST base: https://string-db.org/api
  - /tsv/network?identifiers={list}&species={taxon}&caller_identity={app}
  - /tsv/interaction_partners?identifiers={protein}&species={taxon}&limit=N
  - /tsv/get_string_ids?identifiers={name}&species={taxon}
"""

from __future__ import annotations

from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import read_tsv
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://string-db.org/api"
_CALLER = "elixir-query"
_TTL = 7 * 24 * 3600  # 7 days


@register
class STRINGAdapter(BaseAdapter):
    """STRING protein interaction network REST adapter."""

    meta = AdapterMeta(
        name="string",
        aliases=("stringdb", "string_db"),
        homepage="https://string-db.org",
        citation=(
            "Szklarczyk D, et al. The STRING database in 2023: protein–protein "
            "association networks and functional enrichment analyses for any "
            "sequenced genome of interest. Nucleic Acids Res. 51:D638–D646 (2023)."
        ),
        supports_bulk=False,
        example_params={"protein": "TP53", "species": 9606},
        description=(
            "STRING — protein–protein interaction and association network. "
            "Call with protein='TP53', species=9606 for interaction partners, "
            "or proteins=['TP53','BRCA1'] for a network."
        ),
    )

    def query(
        self,
        *,
        protein: str | None = None,
        proteins: list[str] | None = None,
        species: int = 9606,
        limit: int = 10,
        resolve: str | None = None,
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch STRING interaction data.

        Args:
            protein: Single protein name or identifier (e.g. ``"TP53"``).
                Returns up to ``limit`` interaction partners.
            proteins: List of protein names — returns the sub-network.
            species: NCBI taxon ID (default 9606 = human).
            limit: Max partners when using ``protein=``.
            resolve: Protein name to resolve to STRING IDs only.
        """
        if resolve is not None:
            return self._resolve(resolve, species)
        if protein is not None:
            return self._partners(protein, species=species, limit=limit)
        if proteins is not None:
            return self._network(proteins, species=species)
        raise ValueError("pass protein=, proteins=, or resolve=... to string.get()")

    def _resolve(self, name: str, species: int) -> pl.DataFrame:
        key = {"kind": "resolve", "name": name, "species": species}
        cached = self.ctx.cache.get_query("string", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/tsv/get_string_ids"
        params = {"identifiers": name, "species": species, "caller_identity": _CALLER}
        resp = self.ctx.http.get(url, params=params, db="string")
        df = read_tsv(resp.text, db="string")
        if df.height == 0:
            raise ParseError("string", f"no STRING IDs found for {name!r}")
        self.ctx.cache.put_query("string", key, df, url=str(resp.request.url))
        return df

    def _partners(self, protein: str, *, species: int, limit: int) -> pl.DataFrame:
        key = {"kind": "partners", "protein": protein, "species": species, "limit": limit}
        cached = self.ctx.cache.get_query("string", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/tsv/interaction_partners"
        params = {
            "identifiers": protein,
            "species": species,
            "limit": limit,
            "caller_identity": _CALLER,
        }
        resp = self.ctx.http.get(url, params=params, db="string")
        df = read_tsv(resp.text, db="string")
        if df.height == 0:
            raise ParseError("string", f"no interaction partners returned for {protein!r}")
        self.ctx.cache.put_query("string", key, df, url=str(resp.request.url))
        return df

    def _network(self, proteins: list[str], *, species: int) -> pl.DataFrame:
        proteins_str = "%0d".join(proteins)
        key = {"kind": "network", "proteins": sorted(proteins), "species": species}
        cached = self.ctx.cache.get_query("string", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        url = f"{_BASE}/tsv/network"
        params = {
            "identifiers": proteins_str,
            "species": species,
            "caller_identity": _CALLER,
        }
        resp = self.ctx.http.get(url, params=params, db="string")
        df = read_tsv(resp.text, db="string")
        if df.height == 0:
            raise ParseError("string", f"no network edges returned for proteins {proteins!r}")
        self.ctx.cache.put_query("string", key, df, url=str(resp.request.url))
        return df
