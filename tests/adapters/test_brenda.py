"""BRENDA adapter stub tests — no live network needed."""

from __future__ import annotations

import pytest

import elixir_query as eq
from elixir_query.errors import MissingCredentialError


def test_brenda_raises_missing_credential():
    """Calling brenda.get() raises MissingCredentialError."""
    with pytest.raises(MissingCredentialError) as exc_info:
        eq.get("brenda")

    err = exc_info.value
    assert err.db == "brenda"
    assert err.field == "password"
    assert "ELIXIR_BRENDA_PASSWORD" in str(err)
    assert err.signup_url and "brenda-enzymes" in err.signup_url


def test_brenda_signup_url_in_message():
    """Error message contains the registration URL."""
    with pytest.raises(MissingCredentialError, match="brenda-enzymes.org"):
        eq.get("brenda")


def test_brenda_env_var_hint():
    """Error message mentions the env var name."""
    with pytest.raises(MissingCredentialError, match="ELIXIR_BRENDA_PASSWORD"):
        eq.get("brenda")
