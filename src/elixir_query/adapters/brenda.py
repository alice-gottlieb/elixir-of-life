"""BRENDA enzyme database stub adapter.

v1 stub: requires user-acquired credentials. See
docs/adapter-notes/credentialed_stubs.md.
"""

from __future__ import annotations

from elixir_query.adapters._credentialed_stub import CredentialedStubAdapter
from elixir_query.core.base import AdapterMeta
from elixir_query.registry import register


@register
class BRENDAAdapter(CredentialedStubAdapter):
    meta = AdapterMeta(
        name="brenda",
        aliases=("brenda_enzymes",),
        homepage="https://www.brenda-enzymes.org",
        citation=(
            "Chang A, et al. BRENDA, the ELIXIR core data resource in 2021: "
            "new developments and updates. Nucleic Acids Res. 49:D498–D508 (2021)."
        ),
        requires_credentials=True,
        credential_fields=("password",),
        supports_bulk=False,
        example_params={},
        description=(
            "BRENDA — comprehensive enzyme functional information system. "
            "Stub adapter in v1: register at "
            "https://www.brenda-enzymes.org/register.php, then export "
            "ELIXIR_BRENDA_PASSWORD=<sha256-of-password> to enable queries."
        ),
    )
    CRED_FIELD = "password"
    SIGNUP_URL = "https://www.brenda-enzymes.org/register.php"
