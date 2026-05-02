"""PDBe (Protein Data Bank in Europe) adapter.

Docs: https://www.ebi.ac.uk/pdbe/pdbe-rest-api
Notes: docs/adapter-notes/pdbe.md (consulted 2026-05-02).

REST base: https://www.ebi.ac.uk/pdbe/api
  - /pdb/entry/summary/{pdb_id}        -> entry summary
  - /pdb/entry/molecules/{pdb_id}      -> entity / molecule list
  - /pdb/entry/publications/{pdb_id}   -> primary citation
  - /pdb/entry/ligand_monomers/{pdb_id} -> bound ligands
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
_JSON_HEADERS = {"Accept": "application/json"}
_TTL = 7 * 24 * 3600  # 7 days

_SECTIONS = {
    "summary": "pdb/entry/summary",
    "molecules": "pdb/entry/molecules",
    "publications": "pdb/entry/publications",
    "ligands": "pdb/entry/ligand_monomers",
}


def _flatten(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            out[k] = _json.dumps(v)
        else:
            out[k] = v
    return out


@register
class PDBEAdapter(BaseAdapter):
    """PDBe (Protein Data Bank in Europe) entry metadata REST adapter."""

    meta = AdapterMeta(
        name="pdbe",
        aliases=("pdb_europe", "pdbe-kb"),
        homepage="https://www.ebi.ac.uk/pdbe/",
        citation=(
            "Armstrong DR, et al. PDBe: improved findability of macromolecular "
            "structure data in the PDB. Nucleic Acids Res. 48:D335–D343 (2020)."
        ),
        supports_bulk=False,
        example_params={"pdb_id": "1cbs"},
        description=(
            "PDBe — Protein Data Bank in Europe.  Call with pdb_id='1cbs' to "
            "retrieve entry summary (default), or section='molecules' / "
            "'publications' / 'ligands' to fetch those sub-resources."
        ),
    )

    def query(
        self,
        *,
        pdb_id: str | None = None,
        section: str = "summary",
        **_extra: Any,
    ) -> pl.DataFrame:
        """Fetch PDBe entry data.

        Args:
            pdb_id: PDB accession (e.g. ``"1cbs"`` — case-insensitive).
            section: Which data section to fetch: ``"summary"`` (default),
                ``"molecules"``, ``"publications"``, or ``"ligands"``.
        """
        if pdb_id is None:
            raise ValueError("pass pdb_id=... to pdbe.get()")

        pdb_id_lower = pdb_id.strip().lower()
        if section not in _SECTIONS:
            raise ValueError(f"section must be one of {list(_SECTIONS)!r}, got {section!r}")

        key = {"pdb_id": pdb_id_lower, "section": section}
        cached = self.ctx.cache.get_query("pdbe", key, ttl_seconds=_TTL)
        if cached is not None:
            return cached

        path = _SECTIONS[section]
        url = f"{_BASE}/{path}/{pdb_id_lower}"
        resp = self.ctx.http.get(url, headers=_JSON_HEADERS, db="pdbe")
        data = resp.json()

        if not isinstance(data, dict):
            raise ParseError("pdbe", f"expected dict from {url}, got {type(data).__name__}")

        # Response: { "1cbs": [ {...}, ... ] }
        entry_data = data.get(pdb_id_lower)
        if entry_data is None:
            raise ParseError("pdbe", f"no data for PDB ID {pdb_id_lower!r} in response")

        if isinstance(entry_data, list):
            records = [_flatten(r) for r in entry_data if isinstance(r, dict)]
        elif isinstance(entry_data, dict):
            records = [_flatten(entry_data)]
        else:
            raise ParseError("pdbe", f"unexpected entry data type: {type(entry_data).__name__}")

        df = records_to_df(records, db="pdbe")
        if df.height == 0:
            raise ParseError("pdbe", f"empty response for {pdb_id_lower!r} section={section!r}")

        self.ctx.cache.put_query("pdbe", key, df, url=str(resp.request.url))
        return df
