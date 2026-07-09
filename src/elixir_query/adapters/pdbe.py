"""PDBe adapter (Protein Data Bank in Europe).

Docs: https://www.ebi.ac.uk/pdbe/api/doc
Notes: docs/adapter-notes/pdbe.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/pdbe/api
  - /pdb/entry/summary/{pdb_id}       -> entry summary
  - /pdb/entry/experiment/{pdb_id}    -> experimental details
  - /pdb/entry/ligand_monomers/{pdb_id}
  - /mappings/uniprot/{pdb_id}        -> UniProt cross-refs
"""

from __future__ import annotations

import json as _json
from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.core.io import records_to_df
from elixir_query.errors import ParseError
from elixir_query.registry import register

_BASE = "https://www.ebi.ac.uk/pdbe/api"

# Supported «kind» values and their URL templates.
_ENDPOINTS: dict[str, str] = {
    "summary": _BASE + "/pdb/entry/summary/{pdb_id}",
    "experiment": _BASE + "/pdb/entry/experiment/{pdb_id}",
    "ligands": _BASE + "/pdb/entry/ligand_monomers/{pdb_id}",
    "uniprot": _BASE + "/mappings/uniprot/{pdb_id}",
    "publications": _BASE + "/pdb/entry/publications/{pdb_id}",
    "polymer_coverage": _BASE + "/pdb/entry/polymer_coverage/{pdb_id}",
}

_JSON_HEADERS = {"Accept": "application/json"}
_TTL_QUERY_SECONDS = 7 * 24 * 3600


def _flatten(d: Any) -> dict[str, Any]:
    if not isinstance(d, dict):
        return {"value": _json.dumps(d)}
    return {
        k: (_json.dumps(v) if isinstance(v, (dict, list)) else v)
        for k, v in d.items()
    }


@register
class PDBEAdapter(BaseAdapter):
    """PDBe REST API adapter — macromolecular structure entries."""

    meta = AdapterMeta(
        name="pdbe",
        aliases=("pdb_europe", "pdb-europe"),
        homepage="https://www.ebi.ac.uk/pdbe/",
        citation=(
            "Bekker GJ, et al. PDBe: improved findability of macromolecular "
            "structure data. Nucleic Acids Res. 52:D411–D416 (2024)."
        ),
        supports_bulk=False,
        example_params={"pdb_id": "1cbs"},
        description=(
            "PDBe — Protein Data Bank in Europe. Call with pdb_id='1cbs' for "
            "an entry summary, or set kind='experiment'/'ligands'/'uniprot'/"
            "'publications'/'polymer_coverage' for specific data."
        ),
    )

    # ------------------------------------------------------------------- query
    def query(
        self,
        *,
        pdb_id: str | None = None,
        kind: str = "summary",
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch a PDB entry from PDBe.

        Args:
            pdb_id: 4-character PDB ID (e.g. ``"1cbs"``). Case-insensitive;
                normalised to lowercase.
            kind: Which data category to retrieve:
                ``"summary"`` (default), ``"experiment"``, ``"ligands"``,
                ``"uniprot"``, ``"publications"``, ``"polymer_coverage"``.
        """
        if pdb_id is None:
            raise ValueError("pass pdb_id='1cbs' (4-character PDB accession)")

        if kind not in _ENDPOINTS:
            raise ValueError(
                f"kind must be one of {sorted(_ENDPOINTS)}, got {kind!r}"
            )

        pdb_id = pdb_id.lower()
        key = {"kind": kind, "pdb_id": pdb_id}
        cached = self.ctx.cache.get_query("pdbe", key, ttl_seconds=_TTL_QUERY_SECONDS)
        if cached is not None:
            return cached

        url = _ENDPOINTS[kind].format(pdb_id=pdb_id)
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="pdbe")
        data = resp.json()

        if not isinstance(data, dict):
            raise ParseError("pdbe", f"expected dict, got {type(data).__name__}")

        # The response is keyed by PDB ID, value is a list of dicts.
        records = data.get(pdb_id) or data.get(pdb_id.upper())
        if records is None:
            # Some endpoints (e.g. /mappings/uniprot) return nested dicts;
            # in that case flatten the top-level values.
            records = [{"pdb_id": pdb_id, **_flatten(v)} for v in data.values()
                       if isinstance(v, dict)]
        if not isinstance(records, list) or not records:
            raise ParseError("pdbe", f"no records in response for pdb_id={pdb_id!r}")

        df = records_to_df([_flatten(r) for r in records], db="pdbe")
        if df.height == 0:
            raise ParseError("pdbe", f"empty DataFrame for pdb_id={pdb_id!r} kind={kind!r}")
        self.ctx.cache.put_query("pdbe", key, df, url=str(resp.request.url))
        return df
