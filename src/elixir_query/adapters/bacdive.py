"""BacDive (bacterial diversity metadatabase) adapter stub.

Auth required — raises MissingCredentialError.
Notes: docs/adapter-notes/bacdive.md (consulted 2026-05-02).

Register at: https://api.bacdive.dsmz.de/user/register/
Set env vars: ELIXIR_BACDIVE_USERNAME and ELIXIR_BACDIVE_PASSWORD
"""

from __future__ import annotations

from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.errors import MissingCredentialError
from elixir_query.registry import register


@register
class BacDiveAdapter(BaseAdapter):
    """BacDive — bacterial diversity metadatabase. Requires registration."""

    meta = AdapterMeta(
        name="bacdive",
        aliases=("bacdive_dsmz",),
        homepage="https://bacdive.dsmz.de",
        citation=(
            "Reimer LC, et al. BacDive in 2022: the knowledge base for "
            "standardized bacterial and archaeal data. "
            "Nucleic Acids Res. 50:D741–D746 (2022)."
        ),
        requires_credentials=True,
        credential_fields=("password",),
        supports_bulk=False,
        example_params={"bacdive_id": 3498},
        description=(
            "BacDive — DSMZ bacterial and archaeal culture collection metadata. "
            "Requires a registered account."
        ),
    )

    def query(self, **_: Any) -> pl.DataFrame:
        raise MissingCredentialError(
            "bacdive",
            "password",
            env_var="ELIXIR_BACDIVE_PASSWORD",
            config_path=str(self.ctx.credentials.config.config_path),
            signup_url="https://api.bacdive.dsmz.de/user/register/",
        )
