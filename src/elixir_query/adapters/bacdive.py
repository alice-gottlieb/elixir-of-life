"""BacDive bacterial diversity metadatabase stub adapter.

v1 stub: requires user-acquired credentials. See
docs/adapter-notes/credentialed_stubs.md.
"""

from __future__ import annotations

from elixir_query.adapters._credentialed_stub import CredentialedStubAdapter
from elixir_query.core.base import AdapterMeta
from elixir_query.registry import register


@register
class BacDiveAdapter(CredentialedStubAdapter):
    meta = AdapterMeta(
        name="bacdive",
        aliases=("bacdive_dsmz",),
        homepage="https://bacdive.dsmz.de",
        citation=(
            "Reimer LC, et al. BacDive in 2025: the ELIXIR data hub for prokaryotic "
            "strain-level information. Nucleic Acids Res. 53:D789–D796 (2025)."
        ),
        requires_credentials=True,
        credential_fields=("password",),
        supports_bulk=False,
        example_params={},
        description=(
            "BacDive — bacterial diversity metadatabase covering ~80 000 strains "
            "with morphological, physiological, isolation, and culture-condition "
            "data. Stub adapter in v1: register at https://api.bacdive.dsmz.de/ "
            "and export ELIXIR_BACDIVE_PASSWORD=... (HTTP Basic auth)."
        ),
    )
    CRED_FIELD = "password"
    SIGNUP_URL = "https://api.bacdive.dsmz.de/"
