"""EGA adapter stub tests — no live network needed."""

from __future__ import annotations

import pytest

import elixir_query as eq
from elixir_query.errors import MissingCredentialError


def test_ega_raises_missing_credential():
    """Calling ega.get() raises MissingCredentialError (no auth configured)."""
    with pytest.raises(MissingCredentialError) as exc_info:
        eq.get("ega")

    err = exc_info.value
    assert err.db == "ega"
    assert err.field == "api_key"
    assert "ELIXIR_EGA_API_KEY" in str(err)
    assert err.signup_url == "https://ega-archive.org/register"


def test_ega_signup_url_in_message():
    """Error message contains the registration URL."""
    with pytest.raises(MissingCredentialError, match="ega-archive.org/register"):
        eq.get("ega")


def test_ega_env_var_hint():
    """Error message mentions the env var name."""
    with pytest.raises(MissingCredentialError, match="ELIXIR_EGA_API_KEY"):
        eq.get("ega")
