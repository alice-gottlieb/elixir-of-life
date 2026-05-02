"""BacDive adapter stub tests — no live network needed."""

from __future__ import annotations

import pytest

import elixir_query as eq
from elixir_query.errors import MissingCredentialError


def test_bacdive_raises_missing_credential():
    """Calling bacdive.get() raises MissingCredentialError."""
    with pytest.raises(MissingCredentialError) as exc_info:
        eq.get("bacdive")

    err = exc_info.value
    assert err.db == "bacdive"
    assert err.field == "password"
    assert "ELIXIR_BACDIVE_PASSWORD" in str(err)
    assert err.signup_url and "bacdive.dsmz.de" in err.signup_url


def test_bacdive_signup_url_in_message():
    """Error message contains the registration URL."""
    with pytest.raises(MissingCredentialError, match="dsmz.de"):
        eq.get("bacdive")


def test_bacdive_env_var_hint():
    """Error message mentions the env var name."""
    with pytest.raises(MissingCredentialError, match="ELIXIR_BACDIVE_PASSWORD"):
        eq.get("bacdive")
