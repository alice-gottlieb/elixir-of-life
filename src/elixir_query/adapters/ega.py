"""EGA (European Genome-phenome Archive) stub adapter.

v1 stub: requires user-acquired credentials. See
docs/adapter-notes/credentialed_stubs.md.
"""

from __future__ import annotations

from elixir_query.adapters._credentialed_stub import CredentialedStubAdapter
from elixir_query.core.base import AdapterMeta
from elixir_query.registry import register


@register
class EGAAdapter(CredentialedStubAdapter):
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
        example_params={},
        description=(
            "EGA — European Genome-phenome Archive. Stores controlled-access "
            "biomedical data; access requires an EGA account and approved "
            "data-access committee permissions. Stub adapter in v1: register "
            "an API key at https://ega-archive.org/register, then export "
            "ELIXIR_EGA_API_KEY=... to enable real queries."
        ),
    )
    CRED_FIELD = "api_key"
    SIGNUP_URL = "https://ega-archive.org/register"
