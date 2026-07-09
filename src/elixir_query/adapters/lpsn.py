"""LPSN — List of Prokaryotic names with Standing in Nomenclature.

v1 stub: requires user-acquired credentials. See
docs/adapter-notes/credentialed_stubs.md.
"""

from __future__ import annotations

from elixir_query.adapters._credentialed_stub import CredentialedStubAdapter
from elixir_query.core.base import AdapterMeta
from elixir_query.registry import register


@register
class LPSNAdapter(CredentialedStubAdapter):
    meta = AdapterMeta(
        name="lpsn",
        aliases=("lpsn_dsmz",),
        homepage="https://lpsn.dsmz.de",
        citation=(
            "Parte AC, et al. LPSN — List of Prokaryotic names with Standing in "
            "Nomenclature: a curated resource for the prokaryotic naming community. "
            "Nucleic Acids Res. 48:D798–D802 (2020)."
        ),
        requires_credentials=True,
        credential_fields=("password",),
        supports_bulk=False,
        example_params={},
        description=(
            "LPSN — List of Prokaryotic names with Standing in Nomenclature, the "
            "authoritative source of validly published bacterial and archaeal names. "
            "Stub adapter in v1: register at https://api.lpsn.dsmz.de/ and export "
            "ELIXIR_LPSN_PASSWORD=... (HTTP Basic auth)."
        ),
    )
    CRED_FIELD = "password"
    SIGNUP_URL = "https://api.lpsn.dsmz.de/"
