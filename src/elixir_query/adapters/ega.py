"""EGA (European Genome-phenome Archive) adapter stub.

Auth required — raises MissingCredentialError.
Notes: docs/adapter-notes/ega.md (consulted 2026-05-02).

Register at: https://ega-archive.org/register
Set env var: ELIXIR_EGA_API_KEY
"""

from __future__ import annotations

from typing import Any

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.errors import MissingCredentialError
from elixir_query.registry import register


@register
class EGAAdapter(BaseAdapter):
    """EGA (European Genome-phenome Archive) — requires registration."""

    meta = AdapterMeta(
        name="ega",
        aliases=("european_genome_phenome_archive",),
        homepage="https://ega-archive.org",
        citation=(
            "Freeberg MA, et al. The European Genome-phenome Archive in 2021. "
            "Nucleic Acids Res. 50:D980–D987 (2022)."
        ),
        requires_credentials=True,
        credential_fields=("api_key",),
        supports_bulk=False,
        example_params={"dataset_id": "EGAD00001000002"},
        description=(
            "EGA — European Genome-phenome Archive for controlled-access human "
            "genetic and phenotypic data. Requires registration and credentials."
        ),
    )

    def query(self, **_: Any) -> pl.DataFrame:
        raise MissingCredentialError(
            "ega",
            "api_key",
            env_var="ELIXIR_EGA_API_KEY",
            config_path=str(self.ctx.credentials.config.config_path),
            signup_url="https://ega-archive.org/register",
        )
