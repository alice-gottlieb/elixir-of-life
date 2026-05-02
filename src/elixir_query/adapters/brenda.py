"""BRENDA (enzyme database) adapter stub.

Auth required — raises MissingCredentialError.
Notes: docs/adapter-notes/brenda.md (consulted 2026-05-02).

Register at: https://www.brenda-enzymes.org/register.php
Set env var: ELIXIR_BRENDA_PASSWORD
"""

from __future__ import annotations

from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.errors import MissingCredentialError
from elixir_query.registry import register


@register
class BRENDAAdapter(BaseAdapter):
    """BRENDA — enzyme function database. Requires registration."""

    meta = AdapterMeta(
        name="brenda",
        aliases=("brenda_db",),
        homepage="https://www.brenda-enzymes.org",
        citation=(
            "Jeske L, et al. BRENDA in 2019: a European ELIXIR core data resource. "
            "Nucleic Acids Res. 47:D542–D549 (2019)."
        ),
        requires_credentials=True,
        credential_fields=("password",),
        supports_bulk=False,
        example_params={"ec_number": "1.1.1.1"},
        description=(
            "BRENDA — comprehensive enzyme function database. "
            "Requires a registered account (email + password)."
        ),
    )

    def query(self, **_: Any) -> pl.DataFrame:
        raise MissingCredentialError(
            "brenda",
            "password",
            env_var="ELIXIR_BRENDA_PASSWORD",
            config_path=str(self.ctx.credentials.config.config_path),
            signup_url="https://www.brenda-enzymes.org/register.php",
        )
