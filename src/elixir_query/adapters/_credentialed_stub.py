"""Shared helper for v1 credentialed-stub adapters.

The four ELIXIR databases that require account credentials (EGA, BRENDA,
BacDive, LPSN) ship as stubs in v1: their `query()` raises
`MissingCredentialError` with the exact env-var name, config path, and
signup URL the user needs. This base class encapsulates the boilerplate so
each individual adapter file is two-line-thin metadata.
"""

from __future__ import annotations

from typing import Any, ClassVar

import polars as pl

from elixir_query.core.base import AdapterMeta, BaseAdapter
from elixir_query.errors import MissingCredentialError


class CredentialedStubAdapter(BaseAdapter):
    """Base for v1 stub adapters that require credentials.

    Subclasses must define ``meta`` and the class-level constants
    ``CRED_FIELD`` and ``SIGNUP_URL``.
    """

    meta: ClassVar[AdapterMeta]
    CRED_FIELD: ClassVar[str] = "api_key"
    SIGNUP_URL: ClassVar[str] = ""

    def query(self, **_params: Any) -> pl.DataFrame:
        """Always raises ``MissingCredentialError`` in v1.

        When credentials become available the underlying credential store is
        consulted first; a present credential triggers ``NotImplementedError``
        so the user knows the stub itself is the gap, not the credential
        plumbing.
        """
        cred_store = self.ctx.credentials
        env_var = f"ELIXIR_{self.meta.name.upper()}_{self.CRED_FIELD.upper()}"
        config_path = str(cred_store.config.config_path)

        # If a credential IS available, fail with a different message that
        # tells the user the v1 implementation is missing (not the credential).
        runtime = cred_store.config.get_runtime_credential(self.meta.name, self.CRED_FIELD)
        if runtime:
            raise NotImplementedError(
                f"adapter {self.meta.name!r} is a v1 stub: a credential was "
                f"provided ({self.CRED_FIELD}) but no upstream call is wired "
                "up yet. See docs/adapter-notes/credentialed_stubs.md for the "
                "implementation plan."
            )

        raise MissingCredentialError(
            self.meta.name,
            self.CRED_FIELD,
            env_var=env_var,
            config_path=config_path,
            signup_url=self.SIGNUP_URL,
        )
