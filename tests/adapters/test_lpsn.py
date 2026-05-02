"""LPSN adapter stub tests — no live network needed."""

from __future__ import annotations

import pytest

import elixir_query as eq
from elixir_query.errors import MissingCredentialError


def test_lpsn_raises_missing_credential():
    """Calling lpsn.get() raises MissingCredentialError."""
    with pytest.raises(MissingCredentialError) as exc_info:
        eq.get("lpsn")

    err = exc_info.value
    assert err.db == "lpsn"
    assert err.field == "password"
    assert "ELIXIR_LPSN_PASSWORD" in str(err)
    assert err.signup_url and "lpsn.dsmz.de" in err.signup_url


def test_lpsn_signup_url_in_message():
    """Error message contains the registration URL."""
    with pytest.raises(MissingCredentialError, match="lpsn.dsmz.de"):
        eq.get("lpsn")


def test_lpsn_env_var_hint():
    """Error message mentions the env var name."""
    with pytest.raises(MissingCredentialError, match="ELIXIR_LPSN_PASSWORD"):
        eq.get("lpsn")
