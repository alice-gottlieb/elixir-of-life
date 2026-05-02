"""LPSN (List of Prokaryotic names with Standing in Nomenclature) adapter stub.

Auth required — raises MissingCredentialError.
Notes: docs/adapter-notes/lpsn.md (consulted 2026-05-02).

Register at: https://lpsn.dsmz.de/user/register
Set env var: ELIXIR_LPSN_PASSWORD
"""

from __future__ import annotations

from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.errors import MissingCredentialError
from elixir_query.registry import register


@register
class LPSNAdapter(BaseAdapter):
    """LPSN — prokaryotic nomenclature database. Requires registration."""

    meta = AdapterMeta(
        name="lpsn",
        aliases=("lpsn_dsmz",),
        homepage="https://lpsn.dsmz.de",
        citation=(
            "Parte AC, et al. List of Prokaryotic names with Standing in "
            "Nomenclature (LPSN) moves to the DSMZ. "
            "Int. J. Syst. Evol. Microbiol. 70:5607–5612 (2020)."
        ),
        requires_credentials=True,
        credential_fields=("password",),
        supports_bulk=False,
        example_params={"taxon": "Lactobacillus acidophilus"},
        description=(
            "LPSN — authoritative list of prokaryotic names with standing in "
            "nomenclature. Requires a registered account."
        ),
    )

    def query(self, **_: Any) -> pl.DataFrame:
        raise MissingCredentialError(
            "lpsn",
            "password",
            env_var="ELIXIR_LPSN_PASSWORD",
            config_path=str(self.ctx.credentials.config.config_path),
            signup_url="https://lpsn.dsmz.de/user/register",
        )
